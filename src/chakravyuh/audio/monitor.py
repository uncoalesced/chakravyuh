# Engineered by uncoalesced
"""Play both sides of a call on the local speaker, so a room can hear a demo (the call itself runs over the line).

    mon = SpeakerMonitor()
    source, write = mon.tap(call, call.write)        # caller audio in, persona audio out
    run_pipeline(source, endpointer, stt, fsm, tts, Player(write))

Each side has its own buffer, capped at max_lag_s so the speaker can never drift behind the call; the output callback
mixes them. Needs `sounddevice` (PortAudio)."""
import threading

from chakravyuh.audio.source import SAMPLE_RATE, SAMPLE_WIDTH


def mix(a: bytes, b: bytes) -> bytes:
    """Sum two PCM16 blocks of equal length, clipped to int16."""
    import numpy as np
    x = np.frombuffer(a, "<i2").astype(np.int32) + np.frombuffer(b, "<i2").astype(np.int32)
    return np.clip(x, -32768, 32767).astype("<i2").tobytes()


class SpeakerMonitor:
    def __init__(self, max_lag_s: float = 0.4, start: bool = True):
        self._bufs = {"caller": bytearray(), "persona": bytearray()}
        self._cap = int(max_lag_s * SAMPLE_RATE) * SAMPLE_WIDTH
        self._lock = threading.Lock()
        self.stream = None
        if start:
            import sounddevice as sd
            self.stream = sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                             blocksize=SAMPLE_RATE // 50, callback=self._callback)
            self.stream.start()

    def feed(self, side: str, pcm: bytes) -> None:
        with self._lock:
            buf = self._bufs[side]
            buf += pcm
            if len(buf) > self._cap:
                del buf[:len(buf) - self._cap]

    def take(self, n: int) -> bytes:
        """Next n bytes of mixed audio (silence where a side has nothing)."""
        with self._lock:
            parts = []
            for buf in self._bufs.values():
                chunk = bytes(buf[:n])
                del buf[:n]
                parts.append(chunk.ljust(n, b"\0"))
        return mix(*parts)

    def _callback(self, outdata, frames, time_info, status):
        outdata[:] = self.take(frames * SAMPLE_WIDTH)

    def tap(self, source, write):
        """Wrap an AudioSource and a Player output so both sides are also sent to the speaker."""
        mon = self

        class Tapped:
            def frames(self):
                for f in source.frames():
                    mon.feed("caller", f.pcm)
                    yield f

        def tapped_write(pcm: bytes):
            mon.feed("persona", pcm)
            write(pcm)

        return Tapped(), tapped_write

    def close(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
