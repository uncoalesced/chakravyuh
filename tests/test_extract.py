# Engineered by uncoalesced
import pytest
from chakravyuh.extract import extract, speech_digits, Extractor


def got(text, kind):
    return {i.value: i for i in extract(text) if i.kind == kind}


def test_upi_literal_and_case():
    assert "quickbillpay98@axl" in got("UPI ID likhiye: QuickBillPay98@AXL", "upi")

def test_upi_known_handle_valid_unknown_flagged():
    u = got("send to refund.desk@ybl or shop@zzzbank", "upi")
    assert u["refund.desk@ybl"].valid and not u["shop@zzzbank"].valid

def test_upi_spoken_at_the_rate_of():
    assert "ramesh.kumar@oksbi" in got("ramesh.kumar at the rate of oksbi", "upi")

def test_upi_spoken_at_needs_known_handle():
    assert got("ramesh at oksbi", "upi") and not got("I will be at office tomorrow", "upi")

def test_email_is_not_upi():
    assert not got("mail me john@gmail.com", "upi")

def test_ifsc_compact_valid_and_unknown_bank():
    i = got("IFSC SBIN0001234 and QQQQ0123456", "ifsc")
    assert i["SBIN0001234"].valid and not i["QQQQ0123456"].valid

def test_ifsc_spelled_with_spoken_digits():
    assert "SBIN0001234" in got("S B I N zero zero zero one two three four", "ifsc")

def test_ifsc_wrong_shape_ignored():
    assert not got("SBIN1001234", "ifsc") and not got("SBIN000123", "ifsc")

@pytest.mark.parametrize("s", ["+91 98765 43210", "09876543210", "919876543210", "98765-43210", "9876543210"])
def test_phone_formats(s):
    assert "+919876543210" in got(f"call me on {s}", "phone")

def test_phone_hindi_spoken_digits():
    assert "+919876543210" in got("number hai nau aath saat chhe paanch chaar teen do ek shunya", "phone")

def test_phone_double_and_triple():
    assert "+919988776655" in got("double nine double eight double seven double six double five", "phone")
    assert "+919888777655" in got("nine triple eight triple seven six double five", "phone")

def test_plus_91_spoken():
    assert "+919876543210" in got("plus nine one nine eight seven six five four three two one zero", "phone")

def test_account_number_and_account_context_beats_phone():
    a = got("account number 123456789012", "account")
    assert "123456789012" in a
    assert "9876543210" in got("khata number 9876543210", "account")

def test_short_numbers_amounts_otp_are_ignored():
    t = "pay Rs 3,450 by 9 PM, otp 482913, ref 412345678901"
    assert not [i for i in extract(t) if i.kind in ("account", "phone")]

def test_urls_apk_and_shortener():
    t = "open http://parcel-clearance.example/clear.apk. also bit.ly/abc123 and update.apk"
    kinds = {(i.kind, i.value) for i in extract(t)}
    assert ("apk", "http://parcel-clearance.example/clear.apk") in kinds
    assert ("url", "bit.ly/abc123") in kinds and ("apk", "update.apk") in kinds
    assert not any(v == "clear.apk" for _, v in kinds)   # no duplicate bare match inside a URL

def test_speech_digits_leaves_words_alone():
    assert speech_digits("ek second, do not worry") == "ek second, do not worry"
    assert speech_digits("nine eight seven six") == "9876"
    assert speech_digits("९८७६५४३२१०") == "9876543210"

def test_extractor_dedupes_and_joins_split_utterances():
    e = Extractor()
    assert [i.value for i in e.feed("UPI ID is quickbillpay98")] == []
    assert [i.value for i in e.feed("@axl")] == ["quickbillpay98@axl"]
    assert e.feed("haan quickbillpay98@axl") == []
    assert len(e.all) == 1
