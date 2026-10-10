# Engineered by uncoalesced
"""Autonomous call over a real localhost WebSocket: virtual caller <-> WebSocketCall + run_pipeline. Tone bursts stand
in for both voices and a scripted STT returns the caller's lines, so no models are needed."""
import asyncio, pathlib, sys, threading
import pytest

pytest.importorskip("websockets")
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "bench"))
import virtual_caller as vc  # noqa: E402
from chakravyuh.audio.playback import Player
from chakravyuh.audio.vad import Endpointer
from chakravyuh.audio.ws import WebSocketCall
from chakravyuh.fsm import PersonaFSM
from chakravyuh.pipeline import run_pipeline
from test_vad import loud

SCRIPT = {"id": "mini", "lang": "hi", "turns": [
    {"t": 0, "text": "Aapka bijli connection aaj kaat diya jayega"},
    {"t": 10, "text": "UPI ID likhiye: quickbillpay98@axl"},
    {"t": 20, "text": "Haan quickbillpay98@axl, jaldi bhejiye"},
]}
tone = lambda seconds: b"\x10\x27" * int(16000 * seconds)        # noqa: E731


def start_caller(port, result):
    async def main():
        from websockets.asyncio.server import serve
        done = asyncio.Event()
        async def handler(ws):
            result["turns"] = await vc.run_call(ws, SCRIPT, lambda text: tone(0.3), reply_timeout=5, quiet=0.3,
                                                gap=0.1, log=lambda *a: None)
            result["done"].set()
            done.set()
        async with serve(handler, "127.0.0.1", port, max_size=None):
            result["ready"].set()
            await done.wait()
    threading.Thread(target=lambda: asyncio.run(main()), daemon=True).start()


def test_autonomous_call_completes_and_measures_turn_gaps():
    result = {"ready": threading.Event(), "done": threading.Event()}
    start_caller(8798, result)
    assert result["ready"].wait(5)

    lines = iter(t["text"] for t in SCRIPT["turns"])
    call = WebSocketCall("ws://127.0.0.1:8798")
    player = Player(call.write)
    events = []
    try:
        report = run_pipeline(call, Endpointer(loud), lambda pcm: next(lines, ""), PersonaFSM(lang="hi"),
                              lambda text: [tone(0.25)], player, on_event=events.append)
    finally:
        player.close()

    assert report["simulated_session"] is True
    assert {i["value"] for i in report["intel"]} == {"quickbillpay98@axl"}
    assert [e["type"] for e in events].count("speak") == 3
    assert result["done"].wait(5)                          # the caller writes its log just after hanging up
    turns = result["turns"]
    assert len(turns) == 3 and all(t["gap_s"] is not None for t in turns)
    # gap = VAD endpoint (600 ms silence) + core + first persona chunk; nothing here is slow
    assert all(0.55 < t["gap_s"] < 1.5 for t in turns), [t["gap_s"] for t in turns]

def test_summary_percentiles():
    s = vc.summary([{"gap_s": g} for g in (1.0, 2.0, 3.0, None)])
    assert s == {"turns": 4, "answered": 3, "gap_p50_s": 2.0, "gap_p90_s": 3.0, "gap_max_s": 3.0}
