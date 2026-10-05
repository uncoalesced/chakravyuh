# Engineered by uncoalesced
import struct, wave
import pytest
from chakravyuh.audio import Frame, WavFileSource


def write_wav(path, samples, rate=16000, channels=1, width=2):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels); w.setsampwidth(width); w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples) if width == 2 else bytes(len(samples)))
    return path


class FakeClock:
    def __init__(self): self.now = 100.0
    def __call__(self): return self.now
    def sleep(self, s): assert s > 0; self.now += s


def test_frames_have_fixed_size_and_accurate_timestamps(tmp_path):
    src = WavFileSource(write_wav(tmp_path / "a.wav", list(range(16000))), frame_ms=20, realtime=False)
    frames = list(src.frames())
    assert src.duration == 1.0 and len(frames) == 50
    assert all(isinstance(f, Frame) and len(f.pcm) == 640 for f in frames)
    assert [f.ts for f in frames] == [round(i * 0.02, 6) for i in range(50)]
    assert struct.unpack("<320h", frames[1].pcm)[0] == 320          # samples arrive in order, unaltered

def test_last_partial_frame_is_zero_padded(tmp_path):
    frames = list(WavFileSource(write_wav(tmp_path / "a.wav", [7] * 500), frame_ms=30, realtime=False).frames())
    assert [f.ts for f in frames] == [0.0, 0.03]
    assert struct.unpack("<480h", frames[1].pcm) == (7,) * 20 + (0,) * 460

def test_realtime_paces_each_frame_to_the_wall_clock(tmp_path):
    clock, seen = FakeClock(), []
    src = WavFileSource(write_wav(tmp_path / "a.wav", [0] * 1600), frame_ms=20, clock=clock, sleep=clock.sleep)
    for f in src.frames():
        seen.append((round(clock.now - 100.0, 6), f.ts))
    # a live device hands over frame i only after it has finished capturing it
    assert seen == [(round((i + 1) * 0.02, 6), round(i * 0.02, 6)) for i in range(5)]

def test_realtime_does_not_sleep_when_the_consumer_is_behind(tmp_path):
    clock = FakeClock()
    src = WavFileSource(write_wav(tmp_path / "a.wav", [0] * 1600), clock=clock, sleep=clock.sleep)
    it = src.frames()
    next(it); clock.now += 1.0                                         # consumer stalls for a second
    assert [f.ts for f in it] == [0.02, 0.04, 0.06, 0.08] and clock.now == pytest.approx(101.02)

def test_empty_file_yields_nothing(tmp_path):
    assert list(WavFileSource(write_wav(tmp_path / "a.wav", []), realtime=False).frames()) == []

@pytest.mark.parametrize("kw", [{"rate": 44100}, {"rate": 8000}, {"channels": 2}, {"width": 1}])
def test_rejects_anything_but_16k_mono_pcm16(tmp_path, kw):
    with pytest.raises(ValueError, match="16000 Hz mono PCM16"):
        WavFileSource(write_wav(tmp_path / "a.wav", [0] * 320, **kw))

def test_rejects_non_positive_frame_size(tmp_path):
    with pytest.raises(ValueError):
        WavFileSource(write_wav(tmp_path / "a.wav", [0] * 320), frame_ms=0)
