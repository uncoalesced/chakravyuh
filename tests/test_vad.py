# Engineered by uncoalesced
import struct
import pytest
from chakravyuh.audio.source import Frame
from chakravyuh.audio.vad import Endpointer, SileroVAD, WINDOW

WIN_S = WINDOW / 16000          # 0.032 s


def loud(win):                  # fake model: any non-zero sample is speech
    return 0.9 if any(win) else 0.0


def stream(*parts, frame_ms=20):
    """parts: (ms, speech?) pairs -> 20 ms Frames. Speech samples are 1000, silence 0."""
    pcm = b"".join(struct.pack("<h", 1000 if on else 0) * (16 * ms) for ms, on in parts)
    n = 32 * frame_ms
    return [Frame(pcm[i:i + n].ljust(n, b"\0"), round(i / 32000, 6)) for i in range(0, len(pcm), n)]


def events(*parts, **kw):
    return list(Endpointer(loud, **kw).run(stream(*parts)))


def test_one_utterance_gives_start_then_end_with_its_audio():
    ev = events((320, 0), (1600, 1), (1000, 0))
    assert [e.kind for e in ev] == ["start", "end"]
    start, end = ev
    assert start.ts == pytest.approx(0.32, abs=WIN_S) and end.start == start.ts
    assert end.ts == pytest.approx(1.92, abs=WIN_S)
    assert len(end.pcm) % 2 == 0 and len(end.pcm) / 32000 >= 1.6     # whole utterance is in the segment

def test_pause_shorter_than_min_silence_does_not_split_the_sentence():
    ev = events((1000, 1), (400, 0), (1000, 1), (1000, 0))
    assert [e.kind for e in ev] == ["start", "end"]
    assert ev[1].ts - ev[1].start == pytest.approx(2.4, abs=WIN_S)

def test_pause_longer_than_min_silence_ends_the_turn():
    ev = events((1000, 1), (800, 0), (1000, 1), (1000, 0))
    assert [e.kind for e in ev] == ["start", "end", "start", "end"]
    assert ev[1].ts == pytest.approx(1.0, abs=WIN_S) and ev[2].ts == pytest.approx(1.8, abs=WIN_S)

def test_end_fires_after_min_silence_not_before():
    ep, fired = Endpointer(loud, min_silence_ms=600), []
    for f in stream((1000, 1), (2000, 0)):
        if any(e.kind == "end" for e in ep.feed(f)):
            fired.append(f.ts)
    assert len(fired) == 1 and 1.6 <= fired[0] <= 1.6 + 2 * WIN_S

def test_short_clicks_are_ignored():
    assert events((500, 0), (40, 1), (500, 0)) == []

def test_pre_roll_keeps_audio_before_the_onset():
    end = events((1000, 0), (1000, 1), (1000, 0))[-1]
    lead = len(end.pcm) - len(end.pcm.lstrip(b"\0"))
    assert 0.15 <= lead / 32000 <= 0.25

def test_stream_ending_mid_speech_still_closes_the_utterance():
    assert [e.kind for e in events((500, 0), (1000, 1))] == ["start", "end"]

def test_runaway_utterance_is_cut_at_max_length():
    ends = [e for e in events((5000, 1), max_utterance_s=2.0) if e.kind == "end"]
    assert len(ends) == 3 and all(e.ts - e.start <= 2.0 + 1e-6 for e in ends)     # 2 + 2 + 1 s

def test_frame_size_does_not_change_the_result():
    parts = ((320, 0), (1200, 1), (900, 0))
    a = list(Endpointer(loud).run(stream(*parts, frame_ms=20)))
    b = list(Endpointer(loud).run(stream(*parts, frame_ms=30)))
    assert [(e.kind, e.ts) for e in a] == [(e.kind, e.ts) for e in b]

def test_silero_model_says_silence_is_not_speech():
    pytest.importorskip("onnxruntime")
    try:
        vad = SileroVAD()
    except FileNotFoundError:
        pytest.skip("silero model not installed")
    assert max(vad(b"\0" * WINDOW * 2) for _ in range(20)) < 0.2
