# Engineered by uncoalesced
"""Piper TTS worker (T1.3): Reply.text -> 16 kHz mono PCM16, one block per sentence, so playback can start on the
first sentence while the rest is still being synthesised. Hindi voices get the text transliterated to Devanagari.
Voices live in models/piper/ (gitignored); see bench/README.md for the download.
ponytail: resampling is linear interpolation (fine for a phone line); swap in a polyphase filter if it sounds rough."""
import pathlib
from typing import Iterator

from chakravyuh.audio.source import SAMPLE_RATE
from chakravyuh.audio.translit import to_devanagari

VOICES = pathlib.Path(__file__).parents[3] / "models" / "piper"
DEFAULT_VOICE = {"hi": "hi_IN-rohan-medium", "en": "en_GB-alan-medium"}


class PiperTTS:
    def __init__(self, lang="hi", voice=None, length_scale=1.15):
        import numpy as np
        from piper import PiperVoice, SynthesisConfig
        self._np = np
        name = voice or DEFAULT_VOICE.get(lang)
        if not name:
            raise ValueError(f"no default Piper voice for lang={lang!r}; pass voice=")
        path = pathlib.Path(name) if pathlib.Path(name).suffix == ".onnx" else VOICES / f"{name}.onnx"
        if not path.exists():
            raise FileNotFoundError(f"Piper voice not found: {path}")
        self.voice = PiperVoice.load(str(path))
        self.rate = self.voice.config.sample_rate
        self.devanagari = self.voice.config.espeak_voice.startswith("hi")
        self.cfg = SynthesisConfig(length_scale=length_scale)   # >1 = slower; the persona is elderly

    def synthesize(self, text: str) -> Iterator[bytes]:
        if self.devanagari:
            text = to_devanagari(text)
        for chunk in self.voice.synthesize(text, self.cfg):
            yield self._to_16k(chunk.audio_int16_array)

    def _to_16k(self, x) -> bytes:
        np = self._np
        if self.rate != SAMPLE_RATE and len(x):
            n = int(len(x) * SAMPLE_RATE / self.rate)
            x = np.interp(np.arange(n) * (self.rate / SAMPLE_RATE), np.arange(len(x)), x.astype(np.float32))
        return np.asarray(x).astype("<i2").tobytes()
