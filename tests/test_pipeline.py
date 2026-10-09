# Engineered by uncoalesced
from typing import Iterator

from chakravyuh.audio.playback import Player
from chakravyuh.audio.source import AudioSource, Frame
from chakravyuh.audio.vad import Endpointer
from chakravyuh.fsm import PersonaFSM, State
from chakravyuh.pipeline import run_pipeline


class MockSource(AudioSource):
    def __init__(self, turns, silence_ms=700, frame_ms=32):
        self.turns = turns
        self.silence_ms = silence_ms
        self.frame_ms = frame_ms

    def frames(self) -> Iterator[Frame]:
        # 16kHz mono PCM16 = 32 samples per ms -> frame_ms * 32 samples = frame_ms * 64 bytes
        frame_bytes = self.frame_ms * 64
        t = 0.0
        dt = self.frame_ms / 1000.0

        for speech_frames, tag in self.turns:
            # tag 1 = speech, tag 0 = silence
            for _ in range(speech_frames):
                pcm = (b"\x10\x00" if tag else b"\x00\x00") * (frame_bytes // 2)
                yield Frame(pcm, round(t, 4))
                t += dt

        # Trailing silence to ensure endpointing
        for _ in range(int(self.silence_ms / self.frame_ms)):
            yield Frame(b"\x00\x00" * (frame_bytes // 2), round(t, 4))
            t += dt


def test_pipeline_autonomous_run():
    events = []
    def on_event(ev):
        events.append(ev)

    # Sequence:
    # 1. 5 frames silence
    # 2. 10 frames speech (turn 1)
    # 3. 25 frames silence (> 600ms endpoint)
    # 4. 10 frames speech (turn 2)
    # 5. 25 frames silence
    turns = [
        (5, 0),
        (10, 1),
        (25, 0),
        (10, 1),
        (25, 0),
    ]
    source = MockSource(turns)

    # Mock VAD prob: speech if non-zero byte in PCM
    def prob(win: bytes) -> float:
        return 0.9 if b"\x10" in win else 0.0

    endpointer = Endpointer(prob, threshold=0.5, min_speech_ms=64, min_silence_ms=500)

    # Mock STT: returns distinct texts on successive calls
    texts = [
        "Aapka bijli connection cut hoga, jaldi transfer karo.",
        "UPI ID likho quickbillpay98@axl abhi bhej do.",
    ]
    stt_idx = 0
    def mock_stt(pcm: bytes) -> str:
        nonlocal stt_idx
        if stt_idx < len(texts):
            res = texts[stt_idx]
            stt_idx += 1
            return res
        return ""

    fsm = PersonaFSM(lang="hi", stall_turns=1)

    played = []
    def mock_write(pcm: bytes):
        played.append(pcm)

    player = Player(mock_write, chunk_ms=20)

    def mock_tts(text: str):
        return [b"\x01\x02" * 100]

    report = run_pipeline(
        source,
        endpointer,
        mock_stt,
        fsm,
        tts=mock_tts,
        player=player,
        simulated=True,
        on_event=on_event,
    )

    player.close()

    assert report["schema"] == "chakravyuh.report/v1"
    assert report["simulated_session"] is True
    assert report["call"]["turns"] == 2
    assert any(i["value"] == "quickbillpay98@axl" for i in report["intel"])

    event_types = [e["type"] for e in events]
    assert "call_start" in event_types
    assert "transcript" in event_types
    assert "intel" in event_types
    assert "speak" in event_types
    assert "report" in event_types


def test_pipeline_barge_in_cancels_playback():
    events = []
    # Test that when scammer speaks while player is playing, barge-in is triggered
    source = MockSource([(10, 1), (25, 0)])
    endpointer = Endpointer(lambda w: 0.9 if b"\x10" in w else 0.0, min_speech_ms=32, min_silence_ms=400)

    def slow_write(pcm: bytes):
        import time
        time.sleep(0.05)

    player = Player(slow_write, chunk_ms=20)
    # Pre-queue audio to simulate player currently playing
    player.play(b"\x01\x02" * 5000)

    fsm = PersonaFSM(lang="en")

    run_pipeline(
        source,
        endpointer,
        lambda pcm: "stop now",
        fsm,
        player=player,
        on_event=lambda ev: events.append(ev),
    )
    player.close()

    barge_in_events = [e for e in events if e["type"] == "barge_in"]
    assert len(barge_in_events) >= 1
