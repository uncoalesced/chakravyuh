# Engineered by uncoalesced
"""Piper TTS worker (T1.3): Reply.text -> 16 kHz mono PCM16, one block per sentence, so playback can start on the
first sentence while the rest is still being synthesised. Hindi voices get the text transliterated to Devanagari.
Voices live in models/piper/ (gitignored); see bench/README.md for the download.
ponytail: resampling is linear interpolation (fine for a phone line); swap in a polyphase filter if it sounds rough."""
import math
import pathlib
from typing import Iterator

from chakravyuh.audio.source import SAMPLE_RATE
from chakravyuh.audio.translit import to_devanagari

VOICES = pathlib.Path(__file__).parents[3] / "models" / "piper"
DEFAULT_VOICE = {
    "hi": "hi_IN-rohan-medium",
    "en": "en_IN-spicor-medium" if (VOICES / "en_IN-spicor-medium.onnx").exists() else "en_GB-alan-medium",
}


class PiperTTS:
    def __init__(self, lang="hi", voice=None, length_scale=None, elderly=True,
                 noise_scale=None, noise_w_scale=None):
        import numpy as np
        import scipy.signal
        from piper import PiperVoice, SynthesisConfig
        self._np, self._signal = np, scipy.signal
        name = voice or DEFAULT_VOICE.get(lang)
        if not name:
            raise ValueError(f"no default Piper voice for lang={lang!r}; pass voice=")
        path = pathlib.Path(name) if pathlib.Path(name).suffix == ".onnx" else VOICES / f"{name}.onnx"
        if not path.exists():
            raise FileNotFoundError(f"Piper voice not found: {path}")
        self.voice = PiperVoice.load(str(path))
        self.rate = self.voice.config.sample_rate
        self.devanagari = self.voice.config.espeak_voice.startswith("hi")
        self.elderly = elderly

        if elderly:
            # Elderly persona (Raghunath): slower, hesitant, gravelly with lowered pitch
            self.pitch_shift = 0.86  # ~2.6 semitones down
            target_cadence = length_scale if length_scale is not None else 1.25
            eff_length = target_cadence * self.pitch_shift
            ns = noise_scale if noise_scale is not None else 0.88      # breathiness & vocal roughness
            nws = noise_w_scale if noise_w_scale is not None else 0.85 # timing micro-hesitations
        else:
            self.pitch_shift = 1.0
            eff_length = length_scale if length_scale is not None else 1.0
            ns = noise_scale if noise_scale is not None else 0.72       # natural caller variation
            nws = noise_w_scale if noise_w_scale is not None else 0.82

        self.cfg = SynthesisConfig(length_scale=eff_length, noise_scale=ns, noise_w_scale=nws)

    def synthesize(self, text: str) -> Iterator[bytes]:
        if self.devanagari:
            text = to_devanagari(text)
        for chunk in self.voice.synthesize(text, self.cfg):
            yield self._to_16k(chunk.audio_int16_array)

    def _to_16k(self, x) -> bytes:
        np, signal = self._np, self._signal
        if not len(x):
            return b""
        in_rate = int(self.rate * self.pitch_shift)
        out_rate = SAMPLE_RATE
        if in_rate != out_rate:
            g = math.gcd(out_rate, in_rate)
            up, down = out_rate // g, in_rate // g
            x = signal.resample_poly(x.astype(np.float32), up, down)
        else:
            x = x.astype(np.float32)

        if self.elderly:
            # 1. Warmth in low-mids (320 Hz chest resonance)
            b_warm, a_warm = signal.iirpeak(320, 1.5, fs=out_rate)
            warm = signal.lfilter(b_warm, a_warm, x)
            x = x + 0.3 * warm

            # 2. High roll-off above 4800 Hz (older vocal tract)
            b_lp, a_lp = signal.butter(2, 4800, "lowpass", fs=out_rate)
            x = signal.lfilter(b_lp, a_lp, x)

            # 3. Subtle vocal age micro-tremor (~9.5 Hz)
            t = np.arange(len(x)) / out_rate
            x = x * (1.0 - 0.035 * np.sin(2 * np.pi * 9.5 * t))

            # 4. Asymmetric vocal gravel / rasp (even harmonics)
            m = np.max(np.abs(x))
            if m > 1e-4:
                nx = x / m
                gravel = nx + 0.15 * (nx ** 2) - 0.05 * (nx ** 3)
                x = gravel * (m * 0.95)

        return np.clip(x, -32768, 32767).astype("<i2").tobytes()
