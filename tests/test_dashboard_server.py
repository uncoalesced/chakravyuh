# Engineered by uncoalesced
import asyncio, json, pathlib, sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "dashboard"))
import server  # noqa: E402


class Clock:
    def __init__(self): self.now = 0.0
    def __call__(self): return self.now


def test_corpus_replay_emits_contract_events_in_order():
    events, waits = [], []
    server.replay_corpus("kyc_block", events.append, speed=2.0, sleep=waits.append)
    kinds = [e["type"] for e in events]
    assert kinds[0] == "call_start" and kinds[-1] == "report" and events[0]["simulated"] is True
    assert kinds.count("transcript") == kinds.count("speak") == 11
    assert {e["value"] for e in events if e["type"] == "intel"} >= {"kyc.desk@okaxis", "YESB0000771", "334455667788"}
    assert waits[:3] == [0.0, 7.0, 7.0]                           # paced by the script's t, at 2x
    assert events[-1]["report"]["simulated_session"] is True
    assert all(e["type"] != "speak" or e["state"] for e in events)

def test_late_subscriber_gets_the_current_call_only():
    hub = server.Hub()
    hub.publish({"type": "call_start", "simulated": True}); hub.publish({"type": "transcript", "text": "old"})
    hub.publish({"type": "call_start", "simulated": True}); hub.publish({"type": "transcript", "text": "new"})
    got = []; hub.subscribe(got.append)
    assert [json.loads(m).get("text") for m in got] == [None, "new"]
    hub.publish({"type": "speak", "text": "live"})
    assert json.loads(got[-1])["text"] == "live"
    hub.unsubscribe(got.append); hub.publish({"type": "speak", "text": "gone"})
    assert len(got) == 3

def test_metrics_follow_the_call_clock_and_freeze_at_report():
    clock = Clock(); hub = server.Hub(rate=60.0, clock=clock)
    assert hub.metrics() is None
    clock.now = 100.0; hub.publish({"type": "call_start", "simulated": True})
    clock.now = 130.0
    assert hub.metrics() == {"type": "metrics", "engaged_s": 30.0, "illustrative_cost_inr": 30.0, "simulated": True}
    hub.publish({"type": "report", "report": {}}); clock.now = 500.0
    assert hub.metrics()["engaged_s"] == 30.0

def test_websocket_clients_receive_backlog_and_live_events():
    pytest.importorskip("websockets")
    from websockets.asyncio.client import connect

    async def go():
        hub = server.Hub()
        hub.publish({"type": "call_start", "simulated": True})
        task = asyncio.create_task(server.serve(hub, 8799))
        await asyncio.sleep(0.2)
        try:
            async with connect("ws://127.0.0.1:8799") as ws:
                first = json.loads(await asyncio.wait_for(ws.recv(), 2))
                hub.publish({"type": "speak", "text": "Ek minute sahab"})
                second = json.loads(await asyncio.wait_for(ws.recv(), 2))
                metrics = json.loads(await asyncio.wait_for(ws.recv(), 2))
        finally:
            task.cancel()
        return first, second, metrics

    first, second, metrics = asyncio.run(go())
    assert first["type"] == "call_start" and second["text"] == "Ek minute sahab"
    assert metrics["type"] == "metrics" and metrics["simulated"] is True
