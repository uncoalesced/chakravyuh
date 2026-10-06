# Engineered by uncoalesced
"""Playback queue with barge-in (T1.4). Implements the AudioSink contract: play() queues PCM, cancel() drops
everything queued and stops the current block within one chunk (20 ms by default).

The output is any write(pcm) that blocks for roughly the chunk's duration, like a sound device or a paced socket.
Wire barge-in as: listen(..., on_speech_start=lambda ts: player.playing and (player.cancel(), core.on_barge_in()))."""
import collections
import threading
import time
from typing import Callable, Optional

from chakravyuh.audio.source import SAMPLE_RATE, SAMPLE_WIDTH


class Player:
    def __init__(self, write: Callable[[bytes], None], chunk_ms: int = 20):
        self._write = write
        self._chunk = SAMPLE_RATE * chunk_ms // 1000 * SAMPLE_WIDTH
        self._queue = collections.deque()
        self._cv = threading.Condition()
        self._gen = 0                      # bumped by cancel(); a block stops when the generation changes
        self._busy = False
        self._closed = False
        self._thread = threading.Thread(target=self._run, name="chakravyuh-playback", daemon=True)
        self._thread.start()

    @property
    def playing(self) -> bool:
        with self._cv:
            return self._busy or bool(self._queue)

    def play(self, pcm: bytes) -> None:
        with self._cv:
            self._queue.append(pcm)
            self._cv.notify()

    def cancel(self) -> None:
        with self._cv:
            self._gen += 1
            self._queue.clear()
            self._cv.notify_all()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until everything queued has been played (or cancelled). False on timeout."""
        with self._cv:
            return self._cv.wait_for(lambda: not self._busy and not self._queue, timeout)

    def close(self) -> None:
        with self._cv:
            self._closed = True
            self._gen += 1
            self._queue.clear()
            self._cv.notify_all()
        self._thread.join(timeout=1)

    def _run(self):
        while True:
            with self._cv:
                self._cv.wait_for(lambda: self._queue or self._closed)
                if self._closed:
                    return
                pcm, gen, self._busy = self._queue.popleft(), self._gen, True
            for i in range(0, len(pcm), self._chunk):
                if self._gen != gen:
                    break
                self._write(pcm[i:i + self._chunk])
            with self._cv:
                self._busy = False
                self._cv.notify_all()


def paced_null_output(chunk_ms: int = 20) -> Callable[[bytes], None]:
    """Discards audio at real-time speed. Stand-in for a device in tests and headless runs."""
    def write(pcm: bytes):
        time.sleep(len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH))
    return write


def sounddevice_output():
    """Speaker output via sounddevice (optional dependency). Each write blocks until the chunk is buffered."""
    import sounddevice as sd
    stream = sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", latency="low")
    stream.start()
    return stream.write
