# Engineered by uncoalesced
import struct
import pytest

pytest.importorskip("numpy")
from chakravyuh.audio.monitor import SpeakerMonitor, mix
from chakravyuh.audio.source import Frame

pcm = lambda *s: struct.pack(f"<{len(s)}h", *s)    # noqa: E731


def test_mix_sums_and_clips():
    assert mix(pcm(100, -100, 30000), pcm(5, 5, 10000)) == pcm(105, -95, 32767)

def test_both_sides_reach_the_speaker_and_silence_fills_gaps():
    mon = SpeakerMonitor(start=False)
    mon.feed("caller", pcm(10, 20))
    mon.feed("persona", pcm(1))
    assert mon.take(6) == pcm(11, 20, 0)

def test_buffers_are_capped_so_the_speaker_never_lags():
    mon = SpeakerMonitor(max_lag_s=0.01, start=False)        # 160 samples
    mon.feed("caller", pcm(*range(1000)))
    out = mon.take(2000)
    assert out[:2] == pcm(840) and len(out) == 2000          # oldest audio dropped, newest kept

def test_tap_passes_audio_through_unchanged():
    mon = SpeakerMonitor(start=False)
    class Src:
        def frames(self): yield Frame(pcm(7, 7), 0.0)
    sent = []
    src, write = mon.tap(Src(), sent.append)
    assert [f.pcm for f in src.frames()] == [pcm(7, 7)]
    write(pcm(3))
    assert sent == [pcm(3)] and mon.take(4) == pcm(10, 7)
