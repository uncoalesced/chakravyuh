# Engineered by uncoalesced
import json
from datetime import datetime
from conftest import load, replay
from chakravyuh.fsm import PersonaFSM
from chakravyuh.report import build_report, to_json, classify, IST


def run(name, lang):
    f = PersonaFSM(lang=lang)
    replay(load(name), f)
    return f

def test_schema_and_simulated_tags():
    r = build_report(run("electricity_disconnect", "hi"), simulated=True, now=datetime(2026, 10, 2, tzinfo=IST))
    assert r["schema"] == "chakravyuh.report/v1" and r["simulated_session"] is True
    assert r["metrics"]["cost_is_illustrative"] is True and r["generated_at"].endswith("+05:30")
    assert "not verified" in r["for_manual_submission"]["note"] or "format-checked" in r["for_manual_submission"]["note"]
    assert r["for_manual_submission"]["chakshu_numbers"] == ["+919876543210"]
    assert {i["kind"] for i in r["intel"]} >= {"upi", "phone", "account", "ifsc"}
    json.loads(to_json(r))   # serialisable

def test_no_transcript_by_default_and_opt_in_works():
    f = run("parcel_clearance", "en")
    assert "transcript" not in build_report(f, simulated=True)
    assert len(build_report(f, simulated=True, include_transcript=True)["transcript"]) == len(f.history)


def test_cost_math():
    f = PersonaFSM(); f.on_scammer_turn("a", 0); f.on_scammer_turn("b", 120)
    m = build_report(f, simulated=True)["metrics"]
    assert m["engaged_seconds"] == 120.0 and m["illustrative_cost_inr"] == 80.0

def test_classify():
    assert classify("aapka bijli connection kaat denge, power board") == "electricity_disconnection"
    assert classify("a parcel held, clearance fee") == "parcel_or_courier"
    assert classify("hello how are you") == "unclassified"

def test_scam_type_in_report():
    assert build_report(run("electricity_disconnect", "hi"), simulated=True)["call"]["scam_type"] == "electricity_disconnection"
    assert build_report(run("parcel_clearance", "en"), simulated=True)["call"]["scam_type"] == "parcel_or_courier"
