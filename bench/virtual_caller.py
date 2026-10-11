# Engineered by uncoalesced
"""Virtual scammer (T3.1): a WebSocket "phone line" that speaks a corpus script and waits for the persona to answer.

It streams 20 ms frames in real time without gaps (speech, else silence), so the agent sees what a phone line
would give it. After each scripted turn it waits for persona audio to come back and finish, then speaks the next
turn. Because it knows when it stopped talking and when the persona's audio arrived, it logs the real turn gap,
measured where a caller would hear it (input to the T3.2 latency harness).

    python bench/virtual_caller.py --corpus digital_arrest           # then point the agent at ws://127.0.0.1:8766
    python dashboard/server.py --caller ws://127.0.0.1:8766           # agent + live dashboard

The caller voice is Piper (pratham for Hindi, ryan for English), different from the persona's voice."""
import argparse
import asyncio
import json
import pathlib
import sys
import time
from datetime import datetime

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

FRAME_MS = 20
FRAME_BYTES = 16 * FRAME_MS * 2
SILENCE = b"\0" * FRAME_BYTES
CALLER_VOICE = {"hi": "hi_IN-pratham-medium", "en": "en_US-ryan-medium"}


def load_script(name):
    return json.loads((ROOT / "corpus" / f"{name}.json").read_text(encoding="utf-8"))


def piper_voice(lang):
    from chakravyuh.audio.tts import PiperTTS
    tts = PiperTTS(lang, voice=CALLER_VOICE[lang], length_scale=0.98, elderly=False)
    return lambda text: b"".join(tts.synthesize(text))


class Line:
    """One call. Sender, receiver and the script run as tasks on the same event loop."""

    def __init__(self, ws, clock=time.monotonic):
        self.ws, self.clock = ws, clock
        self.speech = bytearray()
        self.drained = asyncio.Event()
        self.drained.set()
        self.persona_first = self.persona_last = None    # times persona audio arrived, reset per turn
        self.closed = False

    async def send_loop(self):
        start, i = self.clock(), 0
        while not self.closed:
            if self.speech:
                chunk = bytes(self.speech[:FRAME_BYTES]).ljust(FRAME_BYTES, b"\0")
                del self.speech[:FRAME_BYTES]
                if not self.speech:
                    self.drained.set()
            else:
                chunk = SILENCE
            try:
                await self.ws.send(chunk)
            except Exception:
                self.closed = True
                self.drained.set()
                return
            i += 1
            await asyncio.sleep(max(start + i * FRAME_MS / 1000 - self.clock(), 0))

    async def recv_loop(self):
        try:
            async for msg in self.ws:
                if isinstance(msg, bytes):
                    now = self.clock()
                    self.persona_first = self.persona_first or now
                    self.persona_last = now
        except Exception:
            pass
        self.closed = True
        self.drained.set()

    async def say(self, pcm: bytes) -> float:
        """Queue speech, wait until the last frame has gone out; returns that moment."""
        self.persona_first = self.persona_last = None
        self.drained.clear()
        self.speech += pcm
        await self.drained.wait()
        return self.clock()

    async def await_reply(self, timeout: float, quiet: float):
        """Wait for persona audio to start (<= timeout) and then stop for `quiet` seconds. Returns (first, last)."""
        t0 = self.clock()
        while not self.closed and self.persona_first is None and self.clock() - t0 < timeout:
            await asyncio.sleep(0.01)
        while not self.closed and self.persona_last is not None and self.clock() - self.persona_last < quiet:
            await asyncio.sleep(0.01)
        return self.persona_first, self.persona_last


async def run_call(ws, script, tts, *, reply_timeout=20.0, quiet=0.9, gap=0.4, log=print):
    line = Line(ws)
    tasks = [asyncio.create_task(line.send_loop()), asyncio.create_task(line.recv_loop())]
    turns = []
    try:
        await ws.send(json.dumps({"type": "caller_hello", "corpus": script["id"], "lang": script["lang"]}))
        await asyncio.sleep(0.5)
        for i, turn in enumerate(script["turns"]):
            if line.closed:
                break
            pcm = tts(turn["text"])
            t_start = line.clock()
            t_end = await line.say(pcm)
            first, last = await line.await_reply(reply_timeout, quiet)
            rec = {"turn": i, "text": turn["text"], "speech_s": round(len(pcm) / 32000, 2),
                   "spoke_at": round(t_start, 3), "ended_at": round(t_end, 3), "gap_s": round(first - t_end, 3) if first else None,
                   "reply_s": round(last - first, 2) if first else None}
            turns.append(rec)
            log(f"turn {i:02d}  gap={rec['gap_s'] if rec['gap_s'] is not None else '  none'}s  | {turn['text'][:60]}")
            await asyncio.sleep(gap)
    finally:
        line.closed = True
        for t in tasks:
            t.cancel()
        await ws.close()
    return turns


def summary(turns):
    gaps = sorted(t["gap_s"] for t in turns if t["gap_s"] is not None)
    if not gaps:
        return {"turns": len(turns), "answered": 0}
    pick = lambda q: gaps[min(int(q * len(gaps)), len(gaps) - 1)]   # noqa: E731
    return {"turns": len(turns), "answered": len(gaps), "gap_p50_s": pick(0.5), "gap_p90_s": pick(0.9),
            "gap_max_s": gaps[-1]}


async def serve(script, tts, port, once, label, **kw):
    from websockets.asyncio.server import serve as ws_serve
    done = asyncio.Event()

    async def handler(ws):
        print(f"agent connected: {script['id']} ({script['lang']})")
        turns = await run_call(ws, script, tts, **kw)
        s = summary(turns)
        print("summary:", s)
        out = ROOT / "bench" / "results" / f"call_{script['id']}_{datetime.now():%Y%m%d_%H%M%S}.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({"label": label, "corpus": script["id"], "summary": s, "turns": turns},
                                  indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"log: {out.relative_to(ROOT)}")
        if once:
            done.set()

    async with ws_serve(handler, "127.0.0.1", port, max_size=None):
        print(f"virtual caller waiting on ws://127.0.0.1:{port}")
        await (done.wait() if once else asyncio.Future())     # without parens this would not await the Future


def main(argv=None):
    ap = argparse.ArgumentParser(description="Virtual scammer over WebSocket")
    ap.add_argument("--corpus", default="electricity_disconnect")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--once", action="store_true", help="exit after one call")
    ap.add_argument("--reply-timeout", type=float, default=20.0)
    ap.add_argument("--label", default="", help="stored in the log, e.g. 'laptop CPU, whisper base'")
    a = ap.parse_args(argv)
    script = load_script(a.corpus)
    asyncio.run(serve(script, piper_voice(script["lang"]), a.port, a.once, a.label, reply_timeout=a.reply_timeout))


if __name__ == "__main__":
    main()
