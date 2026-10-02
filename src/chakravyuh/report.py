# Engineered by uncoalesced
"""Structured incident report for a person to review and submit through the official channels.
This is an export, not an automated filing. Demo sessions are tagged simulated."""
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
ILLUSTRATIVE_RS_PER_MIN = 40.0   # assumption for the demo counter, not a measured or sourced figure

_TYPES = {
    "electricity_disconnection": ("bijli", "electricity", "power board", "meter", "connection"),
    "parcel_or_courier": ("parcel", "courier", "package", "consignment", "clearance"),
    "digital_arrest": ("digital arrest", "warrant", "court", "arrest"),
    "kyc_or_bank": ("kyc", "debit card", "credit card", "bank account blocked", "account block"),
}


def classify(text: str) -> str:
    t = text.lower()
    score = {k: sum(t.count(w) for w in ws) for k, ws in _TYPES.items()}
    best = max(score, key=score.get)
    return best if score[best] else "unclassified"


def build_report(fsm, *, simulated: bool, include_transcript: bool = False, now=None, rs_per_min=ILLUSTRATIVE_RS_PER_MIN) -> dict:
    now = now or datetime.now(IST)
    secs = fsm.elapsed()
    scammer_text = " ".join(h["content"] for h in fsm.history if h["role"] == "user")
    intel = [asdict(i) for i in fsm.extractor.all]
    r = {
        "schema": "chakravyuh.report/v1",
        "generated_at": now.isoformat(timespec="seconds"),
        "simulated_session": simulated,
        "call": {"duration_s": round(secs, 1), "turns": fsm.turns, "final_state": fsm.state.value,
                 "scam_type": classify(scammer_text), "language": fsm.lang},
        "intel": intel,
        "metrics": {"engaged_seconds": round(secs, 1), "rate_inr_per_min": rs_per_min,
                    "illustrative_cost_inr": round(secs / 60 * rs_per_min, 2), "cost_is_illustrative": True},
        "for_manual_submission": {
            "channels": ["National Cyber Crime Reporting Portal (cybercrime.gov.in) / helpline 1930",
                         "Chakshu on Sanchar Saathi (sancharsaathi.gov.in)"],
            "chakshu_numbers": [i["value"] for i in intel if i["kind"] == "phone"],
            "note": "Prepared for a person to review and submit. Identifiers are format-checked only; "
                    "nothing here is verified as real or confirmed as fraudulent."},
    }
    if include_transcript:
        r["transcript"] = fsm.history
    return r


def to_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)
