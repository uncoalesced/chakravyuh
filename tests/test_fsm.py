# Engineered by uncoalesced
import re
import pytest
from conftest import load, replay
from chakravyuh.fsm import PersonaFSM, LINES

NAMES = ["electricity_disconnect", "parcel_clearance"]


def collapse(seq):
    out = []
    for s in seq:
        if not out or out[-1] != s: out.append(s)
    return out


@pytest.mark.parametrize("name", NAMES)
def test_corpus_replay_captures_expected_intel_and_states(name):
    sc = load(name)
    f = PersonaFSM(lang=sc["lang"])
    replies = replay(sc, f)
    ex = sc["expect"]
    for kind in ("upi", "phone", "account", "ifsc", "apk"):
        have = {i.value for i in f.extractor.all if i.kind == kind}
        assert set(ex.get(kind, [])) <= have, (kind, have)
    assert collapse(r.state for r in replies) == ex["states_in_order"]


def test_wrapup_ends_the_call_once_rounds_are_spent():
    sc = load("electricity_disconnect")
    replies = replay(sc, PersonaFSM(lang="hi"))
    assert replies[-1].end_call and not any(r.end_call for r in replies[:-1])

@pytest.mark.parametrize("lang", ["en", "hi"])
def test_scripted_lines_never_leak_digits_or_secrets(lang):
    for pool in LINES[lang].values():
        for line in pool:
            assert not re.search(r"\d|otp|pin\b", line, re.I) and len(line.split()) <= 40

def test_bot_question_gets_deflection_without_state_change():
    f = PersonaFSM()
    f.on_scammer_turn("Pay the bill now", 0)
    before = f.state
    r = f.on_scammer_turn("Are you a bot? Are you a recording?", 5)
    assert r.text in LINES["en"]["DEFLECT"] and f.state == before

def test_unsafe_llm_output_falls_back_to_script():
    for bad in ["My account is 123456789 sir", "I am an AI language model", "your OTP is ok", "visit http://x.example", ""]:
        f = PersonaFSM(llm=lambda s, h, b=bad: b)
        assert f.on_scammer_turn("Hello pay now", 0).text in LINES["en"]["PANIC"] + LINES["en"]["STALLING"]

def test_llm_failure_never_silences_the_call():
    def boom(s, h): raise TimeoutError
    assert PersonaFSM(llm=boom).on_scammer_turn("hello", 0).text

def test_good_llm_output_is_used_and_prompt_carries_state_goal():
    seen = {}
    def llm(system, history):
        seen["system"], seen["n"] = system, len(history)
        return "Oh sir, please wait one minute."
    r = PersonaFSM(llm=llm).on_scammer_turn("Your power will be cut", 0)
    assert r.text == "Oh sir, please wait one minute." and "fear" in seen["system"] and seen["n"] == 1

def test_time_cap_forces_wrapup():
    f = PersonaFSM(max_seconds=60)
    f.on_scammer_turn("hello", 0)
    assert f.on_scammer_turn("hello again", 61).end_call

def test_turn_cap_forces_wrapup():
    f = PersonaFSM(max_turns=3)
    rs = [f.on_scammer_turn("hello", t) for t in range(3)]
    assert rs[-1].end_call

def test_barge_in_marks_last_persona_line():
    f = PersonaFSM()
    f.on_scammer_turn("hello", 0); f.on_barge_in()
    assert f.history[-1]["content"].endswith("[interrupted]")

def test_unknown_language_defaults_to_english():
    assert PersonaFSM(lang="xx").lang == "en"
