# Engineered by uncoalesced
"""Audio sources. Every source yields fixed-size 16 kHz mono PCM16 frames with a stream timestamp, so VAD/STT
never care whether audio came from a file, the virtual caller or the phone cable (docs/CONTRACTS.md)."""
import time
import wave
from typing import Callable, Iterator, NamedTuple, Protocol

SAMPLE_RATE = 16_000
SAMPLE_WIDTH = 2          # bytes, PCM16 little-endian
CHANNELS = 1


class Frame(NamedTuple):
    pcm: bytes            # exactly frame_ms of audio; the final frame is zero-padded
    ts: float             # seconds since stream start at the first sample of this frame


class AudioSource(Protocol):
    def frames(self) -> Iterator[Frame]: ...


class WavFileSource:
    """Replays a 16 kHz mono PCM16 .wav as if it were live input.

    realtime=True paces delivery: frame i is yielded once (i + 1) * frame_ms has passed on the wall clock, i.e. when a
    live device would have finished capturing it. realtime=False yields as fast as possible (tests, offline runs).
    ponytail: no resampling; convert other formats first (ffmpeg -ar 16000 -ac 1 -sample_fmt s16). Add it here if
    the virtual caller ever needs to replay arbitrary files.
    """

    def __init__(self, path, frame_ms: int = 20, realtime: bool = True,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep):
        if frame_ms <= 0 or (SAMPLE_RATE * frame_ms) % 1000:
            raise ValueError(f"frame_ms must give a whole number of samples at {SAMPLE_RATE} Hz, got {frame_ms}")
        self.path, self.frame_ms, self.realtime = path, frame_ms, realtime
        self._clock, self._sleep = clock, sleep
        self.samples_per_frame = SAMPLE_RATE * frame_ms // 1000
        with wave.open(str(path), "rb") as w:
            fmt = (w.getframerate(), w.getnchannels(), w.getsampwidth())
            if fmt != (SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH):
                raise ValueError(f"{path}: need {SAMPLE_RATE} Hz mono PCM16, got {fmt[0]} Hz, "
                                 f"{fmt[1]} ch, {fmt[2] * 8}-bit")
            self.duration = w.getnframes() / SAMPLE_RATE

    def frames(self) -> Iterator[Frame]:
        step = self.frame_ms / 1000
        frame_bytes = self.samples_per_frame * SAMPLE_WIDTH
        start = self._clock()
        with wave.open(str(self.path), "rb") as w:
            i = 0
            while chunk := w.readframes(self.samples_per_frame):
                if self.realtime:
                    wait = start + (i + 1) * step - self._clock()
                    if wait > 0:
                        self._sleep(wait)
                yield Frame(chunk.ljust(frame_bytes, b"\x00"), round(i * step, 6))
                i += 1
