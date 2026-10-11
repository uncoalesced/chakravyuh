# Engineered by uncoalesced
"""Speech to text on endpointed utterances (T1.2). listen() runs source frames through the Endpointer and yields one
ScammerTurn per final utterance, ready for core.on_scammer_turn(turn.text, turn.ts). Partials are not produced yet.
ponytail: transcribes after the utterance ends; if the harness shows STT dominates the turn gap, decode while the
caller is still talking and only finish the tail at endpoint."""
from typing import Callable, Iterable, Iterator, NamedTuple, Optional

from chakravyuh.audio.source import Frame
from chakravyuh.audio.vad import Endpointer


class ScammerTurn(NamedTuple):
    text: str
    ts: float                    # stream seconds when the caller stopped talking
    start: float                 # stream seconds when they started

    def to_event(self) -> dict:
        return {"type": "transcript", "speaker": "scammer", "text": self.text, "final": True, "ts": self.ts}


def listen(frames: Iterable[Frame], endpointer: Endpointer, stt: Callable[[bytes], str],
           on_speech_start: Optional[Callable[[float], None]] = None) -> Iterator[ScammerTurn]:
    """on_speech_start fires the moment the caller starts talking (barge-in: stop the persona's audio)."""
    for ev in endpointer.run(frames):
        if ev.kind == "start":
            if on_speech_start:
                on_speech_start(ev.ts)
        elif text := stt(ev.pcm).strip():
            yield ScammerTurn(text, ev.ts, ev.start)


class WhisperSTT:
    """faster-whisper on one utterance (16 kHz mono PCM16 bytes) -> text.
    language="en" keeps Hinglish in Roman script but tends to translate it; see bench/README.md for the trade-off."""

    def __init__(self, model="small", device="auto", compute_type: Optional[str] = None, language: Optional[str] = "en",
                 beam_size=1, max_no_speech=0.6):
        import numpy as np
        from faster_whisper import WhisperModel
        self._np = np
        if compute_type is None or (compute_type == "int8" and device == "cuda"):
            compute_type = "float16" if device == "cuda" else "int8" if device == "cpu" else "default"
        self.model = WhisperModel(model, device=device, compute_type=compute_type)
        self.language, self.beam_size, self.max_no_speech = language, beam_size, max_no_speech

    def __call__(self, pcm: bytes) -> str:
        audio = self._np.frombuffer(pcm, dtype="<i2").astype(self._np.float32) / 32768.0
        segs, _ = self.model.transcribe(audio, language=self.language, beam_size=self.beam_size, vad_filter=False,
                                        condition_on_previous_text=False, without_timestamps=True)
        # whisper invents text ("Thank you.") on noise; drop segments it is itself unsure contain speech
        return " ".join(s.text.strip() for s in segs if s.no_speech_prob < self.max_no_speech).strip()
