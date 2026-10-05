# Engineered by uncoalesced
import time
from chakravyuh.audio.playback import Player, paced_null_output
from chakravyuh.audio.stt import listen
from chakravyuh.audio.vad import Endpointer
from test_vad import loud, stream

SECOND = b"\1\0" * 16000


class Device:
    """Paced fake device that records when each chunk was written."""
    def __init__(self):
        self.times, self.bytes, self._pace = [], 0, paced_null_output()
    def __call__(self, pcm):
        self.times.append(time.perf_counter()); self.bytes += len(pcm); self._pace(pcm)


def test_plays_queued_blocks_in_order_and_completely():
    got = []
    p = Player(lambda pcm: got.append(pcm))
    p.play(b"\1\0" * 400); p.play(b"\2\0" * 400)
    assert p.wait(1) and b"".join(got) == b"\1\0" * 400 + b"\2\0" * 400
    assert [len(c) for c in got] == [640, 160, 640, 160]           # 20 ms chunks, per block
    p.close()

def test_cancel_stops_playback_within_100ms_and_drops_the_queue():
    dev = Device(); p = Player(dev)
    p.play(SECOND); p.play(SECOND)
    time.sleep(0.3)
    t_cancel = time.perf_counter(); p.cancel()
    assert p.wait(0.2)
    last = max(dev.times) + 0.02                          # the chunk in flight finishes playing
    assert last - t_cancel < 0.1, last - t_cancel
    assert dev.bytes < 0.5 * len(SECOND)                  # neither the rest of block 1 nor block 2 played
    assert not p.playing
    p.close()

def test_player_is_reusable_after_cancel():
    got = []; p = Player(lambda pcm: got.append(pcm))
    p.cancel(); p.play(b"\3\0" * 320)
    assert p.wait(1) and b"".join(got) == b"\3\0" * 320
    p.close()

def test_scammer_interrupt_via_vad_cancels_persona_audio():
    dev = Device(); p = Player(dev); barged = []
    def on_start(ts):
        if p.playing:
            t = time.perf_counter(); p.cancel(); p.wait(0.2); barged.append(max(dev.times) + 0.02 - t)
    p.play(SECOND * 3)                                    # persona is mid-sentence
    time.sleep(0.1)
    list(listen(stream((200, 0), (800, 1), (900, 0)), Endpointer(loud), lambda pcm: "ruko", on_speech_start=on_start))
    assert len(barged) == 1 and barged[0] < 0.1
    assert not p.playing and dev.bytes < len(SECOND)
    p.close()
