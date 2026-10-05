# Engineered by uncoalesced
"""Metric code in bench/stt_bench.py. The benchmark itself needs faster-whisper and audio, so it is not run here."""
import pathlib, sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "bench"))
import stt_bench as b  # noqa: E402


def test_normalise_drops_punctuation_but_keeps_upi_ids():
    assert b.normalise("Haan, quickbillpay98@axl. Bhejiye!") == ["haan", "quickbillpay98@axl", "bhejiye"]

def test_wer_counts_substitutions_insertions_and_deletions():
    assert b.wer("jaldi karo baba", "jaldi karo baba") == 0
    assert b.wer("jaldi karo baba", "jaldi kar baba") == pytest.approx(1 / 3)
    assert b.wer("jaldi karo baba", "jaldi karo") == pytest.approx(1 / 3)
    assert b.wer("jaldi karo", "jaldi karo baba ji") == 1.0
    assert b.wer("Jaldi, karo!", "jaldi karo") == 0

def test_cer_is_character_level():
    assert b.cer("karo", "kara") == pytest.approx(1 / 4)

def test_devanagari_share():
    assert b.devanagari_share("jaldi karo") == 0
    assert b.devanagari_share("जल्दी karo") > 0.4

def test_intel_recall_survives_spoken_forms_and_spots_losses():
    ref = "UPI ID likhiye: quickbillpay98@axl"
    assert b.intel_recall(ref, "upi id likhiye quickbillpay98 at the rate axl") == (1, 1)
    assert b.intel_recall(ref, "upi id likhiye quick bill pay") == (0, 1)
    assert b.intel_recall("jaldi karo", "jaldi karo") == (0, 0)

def test_manifest_points_at_real_corpus_lines():
    clips = list(b.load_clips(b.BENCH / "stt_clips.json"))
    assert len(clips) == 5 and all(ref for _, ref in clips)
    assert sum(b.intel_recall(ref, ref)[1] for _, ref in clips) >= 4    # the set exercises identifiers, not just chat
