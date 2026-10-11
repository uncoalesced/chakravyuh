# Engineered by uncoalesced
"""Corpus B (digital arrest, KYC block). Replay and state order are covered by test_fsm via NAMES; this file pins
extraction precision: the call should capture exactly the identifiers the caller gave, nothing invented."""
import re
import pytest
from conftest import load
from chakravyuh.extract import Extractor, extract

EXPECTED_KINDS = ("upi", "phone", "account", "ifsc", "apk")


def captured(name):
    ex = Extractor()
    for t in load(name)["turns"]:
        ex.feed(t["text"], t["t"])
    return {(i.kind, i.value) for i in ex.all}


@pytest.mark.parametrize("name", ["digital_arrest", "kyc_block"])
def test_scripts_are_synthetic(name):
    text = " ".join(t["text"] for t in load(name)["turns"])
    assert all(u.split("/")[2].endswith(".example") for u in re.findall(r"https?://\S+", text))


@pytest.mark.parametrize("name", ["digital_arrest", "kyc_block"])
def test_capture_is_exactly_what_the_caller_said(name):
    exp = load(name)["expect"]
    assert captured(name) == {(k, v) for k in EXPECTED_KINDS for v in exp.get(k, [])}


@pytest.mark.parametrize("phrase", ["UPI se bhejo abhi ke abhi", "Sir are you doing it or not?"])
def test_everyday_phrases_are_not_ifsc(phrase):
    assert not [i for i in extract(phrase) if i.kind == "ifsc"]
