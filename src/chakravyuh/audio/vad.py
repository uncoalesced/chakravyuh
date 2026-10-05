# Engineered by uncoalesced
"""Voice activity detection and endpointing (T1.1).

Endpointer turns a stream of Frames into speech events: "start" as soon as the caller starts talking (barge-in hook)
and "end" with the whole utterance once they have been quiet for min_silence_ms (the final transcript goes to STT,
then to the core). It is plain Python over any prob(window) -> float, so the logic is tested without a model.
SileroVAD is that function for the real model, run through onnxruntime (no torch)."""
import pathlib
from typing import Callable, Iterable, Iterator, NamedTuple

from chakravyuh.audio.source import SAMPLE_RATE, SAMPLE_WIDTH, Frame

WINDOW = 512                     # Silero v5 window at 16 kHz (32 ms)
_WIN_BYTES = WINDOW * SAMPLE_WIDTH
_WIN_S = WINDOW / SAMPLE_RATE


class VadEvent(NamedTuple):
    kind: str                    # "start" | "end"
    ts: float                    # start: speech onset; end: last voiced moment (seconds, stream time)
    start: float = 0.0           # end only: onset of this utterance
    pcm: bytes = b""             # end only: utterance audio incl. pre-roll, 16 kHz mono PCM16


class Endpointer:
    """Hysteresis endpointing. Speech starts after min_speech_ms of prob >= threshold; it ends after min_silence_ms of
    prob < threshold - 0.15. Pauses shorter than min_silence_ms stay inside the utterance, so a breath mid-sentence
    does not split it. pre_roll_ms of audio before the onset is kept so the first syllable is not clipped."""

    def __init__(self, prob: Callable[[bytes], float], threshold=0.5, min_speech_ms=96, min_silence_ms=600,
                 pre_roll_ms=200, max_utterance_s=30.0):
        self.prob, self.on, self.off = prob, threshold, max(threshold - 0.15, 0.01)
        self.need_speech = max(1, round(min_speech_ms / 1000 / _WIN_S))
        self.need_silence = max(1, round(min_silence_ms / 1000 / _WIN_S))
        self.pre_roll = round(pre_roll_ms / 1000 / _WIN_S)
        self.max_windows = int(max_utterance_s / _WIN_S)
        self.reset()

    def reset(self):
        self._buf, self._buf_ts = b"", None
        self._history = []           # recent (ts, window) while idle, for pre-roll and the onset run
        self._speaking, self._run, self._quiet = False, 0, 0
        self._utt, self._onset, self._last_voiced = [], 0.0, 0.0

    def feed(self, frame: Frame) -> list:
        """Push one frame; returns the events it completed (usually none)."""
        if self._buf_ts is None:
            self._buf_ts = frame.ts
        self._buf += frame.pcm
        events = []
        while len(self._buf) >= _WIN_BYTES:
            win, self._buf = self._buf[:_WIN_BYTES], self._buf[_WIN_BYTES:]
            ts, self._buf_ts = self._buf_ts, self._buf_ts + _WIN_S
            events += self._window(round(ts, 6), win, self.prob(win))
        return events

    def flush(self) -> list:
        """End of stream: close an open utterance."""
        if not self._speaking:
            return []
        ev = self._end()
        self.reset()
        return [ev]

    def run(self, frames: Iterable[Frame]) -> Iterator[VadEvent]:
        for f in frames:
            yield from self.feed(f)
        yield from self.flush()

    def _window(self, ts, win, p):
        if not self._speaking:
            self._history.append((ts, win))
            self._run = self._run + 1 if p >= self.on else 0
            if self._run < self.need_speech:
                del self._history[:-(self.pre_roll + self.need_speech)]
                return []
            self._speaking, self._quiet = True, 0
            self._onset = self._history[-self._run][0]
            self._utt, self._history = [w for _, w in self._history], []
            self._last_voiced = ts + _WIN_S
            return [VadEvent("start", self._onset)]
        self._utt.append(win)
        if p >= self.off:
            self._quiet, self._last_voiced = 0, ts + _WIN_S
        else:
            self._quiet += 1
        if self._quiet >= self.need_silence or len(self._utt) >= self.max_windows:
            ev = self._end()
            self._speaking, self._run, self._utt = False, 0, []
            return [ev]
        return []

    def _end(self):
        keep = len(self._utt) - max(self._quiet - self.pre_roll, 0)     # trim trailing silence, keep a short tail
        return VadEvent("end", round(self._last_voiced, 6), self._onset, b"".join(self._utt[:keep]))


class SileroVAD:
    """Silero VAD v5 via onnxruntime. Call with one 512-sample PCM16 window; returns speech probability 0..1.
    Model file: model_path, else models/silero_vad.onnx, else the copy shipped in the silero-vad package
    (`pip install silero-vad --no-deps` fetches just the file, without torch)."""
    CONTEXT = 64

    def __init__(self, model_path=None):
        import numpy as np
        import onnxruntime as ort
        self._np = np
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = opts.intra_op_num_threads = 1
        self._sess = ort.InferenceSession(str(model_path or _find_model()), opts, providers=["CPUExecutionProvider"])
        self._sr = np.array(SAMPLE_RATE, dtype=np.int64)
        self.reset()

    def reset(self):
        np = self._np
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, self.CONTEXT), dtype=np.float32)

    def __call__(self, window: bytes) -> float:
        np = self._np
        x = np.frombuffer(window, dtype="<i2").astype(np.float32).reshape(1, -1) / 32768.0
        x = np.concatenate([self._context, x], axis=1)
        out, self._state = self._sess.run(None, {"input": x, "state": self._state, "sr": self._sr})
        self._context = x[:, -self.CONTEXT:]
        return float(out[0][0])


def _find_model():
    local = pathlib.Path(__file__).parents[3] / "models" / "silero_vad.onnx"
    if local.exists():
        return local
    try:
        import silero_vad
    except ImportError:
        raise FileNotFoundError("Silero model not found: put silero_vad.onnx in models/ or "
                                "`pip install silero-vad --no-deps`") from None
    return pathlib.Path(silero_vad.__file__).parent / "data" / "silero_vad.onnx"
