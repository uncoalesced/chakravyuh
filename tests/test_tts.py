# Engineered by uncoalesced
import re
import pytest
from chakravyuh.audio.translit import LEXICON, to_devanagari, _rules
from chakravyuh.fsm import LINES


def hindi_lines():
    return [x for v in LINES["hi"].values() for x in (v if isinstance(v, (list, tuple)) else [v])]

def test_every_scripted_persona_word_is_in_the_lexicon():
    words = {w.lower() for line in hindi_lines() for w in re.findall(r"[A-Za-z]+", line)}
    assert not sorted(words - LEXICON.keys())

def test_transliteration_leaves_no_latin_and_keeps_punctuation():
    out = to_devanagari("Arre baap re, sahab! Payment fail ho gaya?")
    assert out == "अरे बाप रे, साहब! पेमेंट फ़ेल हो गया?"
    assert not any(to_devanagari(l) and re.search("[A-Za-z]", to_devanagari(l)) for l in hindi_lines())

@pytest.mark.parametrize("roman, deva", [("raha", "रहा"), ("bachcha", "बच्चा"), ("namaste", "नमस्ते"),
                                         ("dukaan", "दुकान"), ("ghar", "घर"), ("chhupa", "छुपा")])
def test_spelling_rules_for_unlisted_words(roman, deva):
    assert _rules(roman) == deva

def test_piper_voice_gives_16k_pcm_per_sentence():
    pytest.importorskip("piper")
    from chakravyuh.audio.tts import PiperTTS
    try:
        tts = PiperTTS("hi")
    except FileNotFoundError:
        pytest.skip("Piper Hindi voice not downloaded")
    blocks = list(tts.synthesize("Ek minute sahab. Mera chashma nahi mil raha."))
    assert len(blocks) == 2 and all(len(b) % 2 == 0 and len(b) > 16000 for b in blocks)   # >0.5 s each
