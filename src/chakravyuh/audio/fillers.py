# Engineered by uncoalesced
"""Hide the turn gap (docs/BENCHMARKS.md). Two tricks, both audio-side:

- Fillers: a short pre-synthesised "haan ji..." starts the moment the caller stops talking, while STT, the core and
  TTS work. The real reply queues behind it. A slow, hesitant reply is in character for the persona.
- CachedTTS: the persona's scripted lines are fixed text, so their audio is synthesised once at startup.

    stt = with_filler(WhisperSTT(), player, Fillers(tts, "hi"))
    tts = CachedTTS(PiperTTS("hi"), persona_lines("hi"))
ponytail: cache lives in memory and is rebuilt per process (~10 s for the hi pool on CPU); persist to disk if
startup time starts to matter."""
from typing import Callable, Iterable, Iterator

FILLERS = {
    "hi": ["Haan ji...", "Ek second sahab...", "Hmm... haan...", "Achha achha...", "Ji sahab, ruko...", "Haan haan..."],
    "en": ["Yes, yes...", "One second, sir...", "Hmm... okay...", "Oh... alright...", "Just a moment...", "Yes sir..."],
}


def persona_lines(lang: str) -> list:
    """Every scripted line the persona can say in this language (fsm.LINES), for the TTS cache."""
    from chakravyuh.fsm import LINES
    pools = LINES.get(lang, LINES["en"]).values()
    return [x for p in pools for x in (p if isinstance(p, (list, tuple)) else [p])]


class CachedTTS:
    def __init__(self, tts, texts: Iterable[str]):
        self.tts = tts
        self.cache = {t: list(tts.synthesize(t)) for t in dict.fromkeys(texts)}

    def synthesize(self, text: str) -> Iterator[bytes]:
        blocks = self.cache.get(text)
        return iter(blocks) if blocks is not None else self.tts.synthesize(text)


class Fillers:
    """Pre-synthesised fillers for one language, handed out in rotation (never the same one twice running)."""

    def __init__(self, tts, lang: str, lines=None):
        self.clips = [b"".join(tts.synthesize(t)) for t in (lines or FILLERS.get(lang, FILLERS["en"]))]
        self._i = -1

    def next(self) -> bytes:
        self._i = (self._i + 1) % len(self.clips)
        return self.clips[self._i]


def with_filler(stt: Callable[[bytes], str], player, fillers: Fillers) -> Callable[[bytes], str]:
    """Wrap an STT callable: listen() calls it right at the endpoint, so queue a filler, then transcribe.
    Skipped if the persona is still speaking (nothing to hide)."""
    def call(pcm: bytes) -> str:
        if not player.playing:
            player.play(fillers.next())
        return stt(pcm)
    return call
