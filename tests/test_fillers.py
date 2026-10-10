# Engineered by uncoalesced
import re
from chakravyuh.audio.fillers import FILLERS, CachedTTS, Fillers, persona_lines, with_filler
from chakravyuh.audio.translit import LEXICON


class FakeTTS:
    def __init__(self): self.calls = []
    def synthesize(self, text):
        self.calls.append(text)
        return iter([text.encode(), b"|"])


class FakePlayer:
    def __init__(self, playing=False): self.playing, self.queued = playing, []
    def play(self, pcm): self.queued.append(pcm)


def test_cached_lines_are_served_without_synthesis():
    tts = FakeTTS()
    cached = CachedTTS(tts, ["Ek minute sahab.", "Ek minute sahab.", "Ruko zara."])
    assert tts.calls == ["Ek minute sahab.", "Ruko zara."]               # synthesised once each, at startup
    assert list(cached.synthesize("Ruko zara.")) == [b"Ruko zara.", b"|"]
    assert list(cached.synthesize("Kuch naya.")) == [b"Kuch naya.", b"|"]  # unknown text goes to the voice
    assert tts.calls[-1] == "Kuch naya."

def test_persona_lines_cover_every_scripted_pool():
    from chakravyuh.fsm import LINES
    assert len(persona_lines("hi")) == sum(len(v) if isinstance(v, (list, tuple)) else 1 for v in LINES["hi"].values())

def test_fillers_rotate_without_immediate_repeats():
    f = Fillers(FakeTTS(), "hi")
    picks = [f.next() for _ in range(12)]
    assert all(a != b for a, b in zip(picks, picks[1:])) and len(set(picks)) == len(FILLERS["hi"])

def test_filler_is_queued_before_transcription_starts():
    player, order = FakePlayer(), []
    stt = with_filler(lambda pcm: order.append(("stt", len(player.queued))) or "text", player, Fillers(FakeTTS(), "en"))
    assert stt(b"pcm") == "text" and order == [("stt", 1)]

def test_no_filler_while_the_persona_is_still_talking():
    player = FakePlayer(playing=True)
    with_filler(lambda pcm: "x", player, Fillers(FakeTTS(), "en"))(b"pcm")
    assert player.queued == []

def test_hindi_fillers_transliterate_cleanly():
    words = {w.lower() for line in FILLERS["hi"] for w in re.findall(r"[A-Za-z]+", line)}
    assert words <= LEXICON.keys()
