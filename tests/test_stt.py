# Engineered by uncoalesced
import pytest
from chakravyuh.audio.stt import ScammerTurn, listen
from chakravyuh.audio.vad import Endpointer
from chakravyuh.fsm import PersonaFSM
from test_vad import loud, stream


def fake_stt(texts):
    it = iter(texts)
    return lambda pcm: next(it)


def test_each_utterance_becomes_one_final_turn_with_stream_times():
    frames = stream((300, 0), (1000, 1), (900, 0), (800, 1), (900, 0))
    turns = list(listen(frames, Endpointer(loud), fake_stt(["Bijli kaat di jayegi", "Jaldi karo"])))
    assert [t.text for t in turns] == ["Bijli kaat di jayegi", "Jaldi karo"]
    assert turns[0].ts == pytest.approx(1.3, abs=0.04) and turns[0].start == pytest.approx(0.3, abs=0.04)
    assert turns[0].ts < turns[1].start < turns[1].ts                     # monotonic, as the core requires

def test_speech_start_hook_fires_before_the_turn_is_transcribed():
    log = []
    def stt(pcm): log.append("stt"); return "hello"
    list(listen(stream((1000, 1), (900, 0)), Endpointer(loud), stt, on_speech_start=lambda ts: log.append("start")))
    assert log == ["start", "stt"]

def test_empty_transcripts_are_dropped():
    assert list(listen(stream((1000, 1), (900, 0)), Endpointer(loud), fake_stt(["  "]))) == []

def test_turn_event_matches_the_contract():
    assert ScammerTurn("hi", 4.2, 3.0).to_event() == {"type": "transcript", "speaker": "scammer", "text": "hi",
                                                      "final": True, "ts": 4.2}

def test_turns_drive_the_core():
    fsm = PersonaFSM(lang="hi")
    frames = stream((1000, 1), (900, 0), (1000, 1), (900, 0))
    replies = [fsm.on_scammer_turn(t.text, t.ts) for t in
               listen(frames, Endpointer(loud), fake_stt(["Aapka bijli connection kaat diya jayega", "UPI ID likhiye: quickbillpay98@axl"]))]
    assert len(replies) == 2 and all(r.text for r in replies)
    assert [i.value for r in replies for i in r.new_intel] == ["quickbillpay98@axl"]
