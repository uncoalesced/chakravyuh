# Engineered by uncoalesced
"""Live dashboard backend (T2.1). Runs one call at a time in a worker thread and pushes its events
(docs/CONTRACTS.md) to every connected browser over WebSocket, plus a 1 Hz `metrics` event.

    python dashboard/server.py --corpus electricity_disconnect --speed 2 --loop     # text replay, no models
    python dashboard/server.py --wav bench/clips/0*.wav                             # full audio pipeline

WebSocket on ws://127.0.0.1:8765; the built page (dashboard/web/dist) on http://127.0.0.1:8000.
Binds to localhost only: the feed carries captured identifiers (docs/GUARDRAILS.md section 6)."""
import argparse
import asyncio
import functools
import http.server
import json
import pathlib
import sys
import threading
import time

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
from chakravyuh.fsm import PersonaFSM  # noqa: E402
from chakravyuh.report import ILLUSTRATIVE_RS_PER_MIN, build_report  # noqa: E402

CORPUS = ROOT / "corpus"
DIST = pathlib.Path(__file__).parent / "web" / "dist"


class Hub:
    """Collects events from the call thread and fans them out. Keeps the current call's events so a browser that
    connects (or reloads) mid-call catches up. publish() is thread-safe; send is any callable(str)."""

    def __init__(self, rate=ILLUSTRATIVE_RS_PER_MIN, clock=time.monotonic):
        self.rate, self.clock = rate, clock
        self._lock = threading.Lock()
        self._log, self._subs = [], set()
        self._t0, self._end, self.simulated = None, None, True

    def subscribe(self, send):
        with self._lock:
            self._subs.add(send)
            backlog = list(self._log)
        for msg in backlog:
            send(msg)

    def unsubscribe(self, send):
        with self._lock:
            self._subs.discard(send)

    def publish(self, ev: dict):
        if ev["type"] == "call_start":
            with self._lock:
                self._log, self._t0, self._end = [], self.clock(), None
                self.simulated = ev.get("simulated", True)
        elif ev["type"] == "report":
            self._end = self.clock()
        msg = json.dumps(ev, ensure_ascii=False)
        with self._lock:
            self._log.append(msg)
            subs = list(self._subs)
        for send in subs:
            send(msg)

    def metrics(self):
        """The contract's metrics event, or None when no call has started. Freezes when the call ends."""
        if self._t0 is None:
            return None
        secs = (self._end or self.clock()) - self._t0
        return {"type": "metrics", "engaged_s": round(secs, 1),
                "illustrative_cost_inr": round(secs / 60 * self.rate, 2), "simulated": self.simulated}


def replay_corpus(name, publish, speed=1.0, sleep=time.sleep):
    """Text-only virtual caller: feeds a corpus script to the core at its own pace (t / speed) and emits the same
    events as chakravyuh.pipeline.run_pipeline. Always a simulated session."""
    sc = json.loads((CORPUS / f"{name}.json").read_text(encoding="utf-8"))
    fsm = PersonaFSM(lang=sc["lang"])
    publish({"type": "call_start", "ts": 0.0, "lang": fsm.lang, "state": fsm.state.value, "simulated": True,
             "scenario": sc["title"]})
    prev = 0.0
    for turn in sc["turns"]:
        sleep(max(turn["t"] - prev, 0) / speed)
        prev = turn["t"]
        publish({"type": "transcript", "speaker": "scammer", "text": turn["text"], "final": True, "ts": turn["t"]})
        reply = fsm.on_scammer_turn(turn["text"], turn["t"])
        for intel in reply.new_intel:
            publish(intel.to_event())
        publish(reply.to_event())
        if reply.end_call:
            break
    publish({"type": "report", "report": build_report(fsm, simulated=True, include_transcript=True)})


def run_wavs(paths, publish, lang="hi", whisper="small"):
    """Full audio pipeline over recorded clips (played back to back). Persona audio goes to a paced null sink so
    barge-in timing is real; swap in sounddevice_output() to hear it."""
    from chakravyuh.audio.playback import Player, paced_null_output
    from chakravyuh.audio.source import WavFileSource
    from chakravyuh.audio.stt import WhisperSTT
    from chakravyuh.audio.tts import PiperTTS
    from chakravyuh.audio.vad import Endpointer, SileroVAD
    from chakravyuh.pipeline import run_pipeline

    class Clips:
        def frames(self):
            offset = 0.0
            for p in paths:
                src = WavFileSource(p)
                for f in src.frames():
                    yield f._replace(ts=round(f.ts + offset, 6))
                offset += src.duration

    player = Player(paced_null_output())
    try:
        run_pipeline(Clips(), Endpointer(SileroVAD()), WhisperSTT(whisper), PersonaFSM(lang=lang),
                     PiperTTS(lang), player, simulated=True, on_event=publish)
    finally:
        player.close()


async def serve(hub, port):
    from websockets.asyncio.server import serve as ws_serve
    loop = asyncio.get_running_loop()

    async def handler(ws):
        q = asyncio.Queue()
        send = lambda msg: loop.call_soon_threadsafe(q.put_nowait, msg)   # noqa: E731
        hub.subscribe(send)
        try:
            while True:
                await ws.send(await q.get())
        except Exception:
            pass                                    # browser went away
        finally:
            hub.unsubscribe(send)

    async def tick():
        while True:
            await asyncio.sleep(1)
            if (m := hub.metrics()) is not None:
                hub.publish(m)

    async with ws_serve(handler, "127.0.0.1", port):
        await tick()


def serve_static(port):
    if not DIST.exists():
        print(f"no build at {DIST}; run `npm run build` in dashboard/web, or use `npm run dev`")
        return
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"dashboard: http://127.0.0.1:{port}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Chakravyuh live dashboard backend")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--corpus", help="corpus script id, e.g. digital_arrest")
    src.add_argument("--wav", nargs="+", help="16 kHz mono wav clips, played as one call")
    ap.add_argument("--speed", type=float, default=1.0, help="corpus replay speed-up")
    ap.add_argument("--loop", action="store_true", help="restart the call when it ends (demo kiosk)")
    ap.add_argument("--lang", default="hi", help="persona language for --wav")
    ap.add_argument("--ws-port", type=int, default=8765)
    ap.add_argument("--http-port", type=int, default=8000)
    a = ap.parse_args(argv)

    speed = a.speed if a.corpus else 1.0
    hub = Hub(clock=lambda: time.monotonic() * speed)        # counter runs on script time, like the transcript

    def calls():
        time.sleep(1.5)                             # let a browser connect before the first event
        while True:
            if a.corpus:
                replay_corpus(a.corpus, hub.publish, a.speed)
            else:
                run_wavs(a.wav, hub.publish, a.lang)
            if not a.loop:
                return
            time.sleep(8)

    threading.Thread(target=calls, name="chakravyuh-call", daemon=True).start()
    serve_static(a.http_port)
    print(f"events: ws://127.0.0.1:{a.ws_port}")
    try:
        asyncio.run(serve(hub, a.ws_port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
