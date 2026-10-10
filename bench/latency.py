# Engineered by uncoalesced
"""Latency harness (T3.2). Runs one autonomous call (bench/virtual_caller.py <-> the real audio pipeline) in a single
process and breaks every turn gap into stages:

    gap = endpoint wait (VAD silence) + STT + core (FSM, LLM if enabled) + TTS to first audio + transport

The gap itself is measured by the caller, where a person on the phone would hear it. Writes
bench/results/latency_<corpus>_<timestamp>.json and prints a Markdown table for docs/BENCHMARKS.md.

    python bench/latency.py --corpus digital_arrest --whisper base --label "laptop CPU"
    python bench/latency.py --corpus kyc_block --whisper small --device cuda --llm --label "demo GPU"
"""
import argparse
import asyncio
import json
import pathlib
import platform
import sys
import threading
import time
from datetime import datetime

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))
import virtual_caller as vc  # noqa: E402


def timed(fn, sink):
    def wrap(*a, **kw):
        t0 = time.perf_counter()
        try:
            return fn(*a, **kw)
        finally:
            sink.append(time.perf_counter() - t0)
    return wrap


class TimedTTS:
    """Records time to the first audio block (what the caller waits for), not the whole synthesis."""
    def __init__(self, tts, sink):
        self.tts, self.sink = tts, sink

    def synthesize(self, text):
        t0, first = time.perf_counter(), True
        for block in self.tts.synthesize(text):
            if first:
                self.sink.append(time.perf_counter() - t0)
                first = False
            yield block


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(int(q * len(xs)), len(xs) - 1)] if xs else None


def run(corpus, whisper, device, use_llm, port):
    from chakravyuh.audio.playback import Player
    from chakravyuh.audio.stt import WhisperSTT
    from chakravyuh.audio.tts import PiperTTS
    from chakravyuh.audio.vad import Endpointer, SileroVAD
    from chakravyuh.audio.ws import WebSocketCall
    from chakravyuh.fsm import PersonaFSM
    from chakravyuh.pipeline import run_pipeline

    script = vc.load_script(corpus)
    caller_tts = vc.piper_voice(script["lang"])
    result, ready = {}, threading.Event()

    async def caller():
        from websockets.asyncio.server import serve
        done = asyncio.Event()
        async def handler(ws):
            result["turns"] = await vc.run_call(ws, script, caller_tts)
            done.set()
        async with serve(handler, "127.0.0.1", port, max_size=None):
            ready.set()
            await done.wait()
    t = threading.Thread(target=lambda: asyncio.run(caller()), daemon=True)
    t.start()
    ready.wait(10)

    stt_s, core_s, tts_s = [], [], []
    endpointer = Endpointer(SileroVAD())
    llm = None
    if use_llm:
        from chakravyuh.llm import ollama_llm
        llm = ollama_llm()
    fsm = PersonaFSM(lang=script["lang"], llm=llm)
    fsm.on_scammer_turn = timed(fsm.on_scammer_turn, core_s)
    stt = timed(WhisperSTT(whisper, device=device), stt_s)
    tts = TimedTTS(PiperTTS(script["lang"]), tts_s)
    call = WebSocketCall(f"ws://127.0.0.1:{port}")
    player = Player(call.write)
    try:
        report = run_pipeline(call, endpointer, stt, fsm, tts, player)
    finally:
        player.close()
    t.join(15)
    return script, result.get("turns", []), stt_s, core_s, tts_s, endpointer, report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Turn-gap latency harness")
    ap.add_argument("--corpus", default="digital_arrest")
    ap.add_argument("--whisper", default="base")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--llm", action="store_true", help="use Ollama for persona wording (default: scripted lines)")
    ap.add_argument("--port", type=int, default=8767)
    ap.add_argument("--label", default="")
    a = ap.parse_args(argv)

    script, turns, stt_s, core_s, tts_s, ep, report = run(a.corpus, a.whisper, a.device, a.llm, a.port)
    gaps = [x["gap_s"] for x in turns if x["gap_s"] is not None]
    endpoint_s = ep.need_silence * 512 / 16000
    stages = {"gap": gaps, "stt": stt_s, "core": core_s, "tts_first_audio": tts_s}
    summary = {k: {"n": len(v), "p50": round(pct(v, .5), 3), "p90": round(pct(v, .9), 3)} for k, v in stages.items() if v}
    summary["endpoint_wait"] = {"n": len(gaps), "p50": round(endpoint_s, 3), "p90": round(endpoint_s, 3)}

    rows = [("Endpoint wait (VAD silence)", "endpoint_wait"), ("Speech to text", "stt"), ("Persona core", "core"),
            ("TTS to first audio", "tts_first_audio"), ("**Turn gap (caller hears)**", "gap")]
    print(f"\n{a.label or 'unlabelled run'} | corpus {a.corpus} | whisper {a.whisper} | "
          f"persona {'LLM' if a.llm else 'scripted'} | {len(gaps)}/{len(turns)} turns answered\n")
    print("| Stage | p50 | p90 |\n|---|---|---|")
    for name, k in rows:
        if k in summary:
            print(f"| {name} | {summary[k]['p50'] * 1000:.0f} ms | {summary[k]['p90'] * 1000:.0f} ms |")

    out = ROOT / "bench" / "results" / f"latency_{a.corpus}_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"label": a.label, "machine": platform.processor() or platform.machine(),
                               "corpus": a.corpus, "whisper": a.whisper, "device": a.device, "llm": a.llm,
                               "summary": summary, "stages": stages, "turns": turns,
                               "intel": report.get("intel", [])}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nlog: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
