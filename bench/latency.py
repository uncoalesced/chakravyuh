# Engineered by uncoalesced
"""Latency harness (T3.2). Runs one autonomous call (bench/virtual_caller.py <-> the real audio pipeline) in a single
process and breaks every turn gap into stages:

    gap = endpoint wait (VAD silence) + STT + core (FSM, LLM if enabled) + TTS to first audio + transport

With fillers on (default) the caller hears a filler right after the endpoint, so the gap it measures is the filler's.
"reply ready" is logged separately: endpoint to the moment the real reply's first audio is queued.

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
    """Records time to the first audio block (what the caller waits for), not the whole synthesis, and the
    monotonic moment that block is ready (same clock as the virtual caller, so it lines up with ended_at)."""
    def __init__(self, tts, sink, ready_at):
        self.tts, self.sink, self.ready_at = tts, sink, ready_at

    def synthesize(self, text):
        t0, first = time.perf_counter(), True
        for block in self.tts.synthesize(text):
            if first:
                self.sink.append(time.perf_counter() - t0)
                self.ready_at.append(time.monotonic())
                first = False
            yield block


def reply_gaps(turns, ready_at):
    """Per caller turn: first reply ready after its speech ended and before the next turn began."""
    out = []
    for i, t in enumerate(turns):
        end = t.get("ended_at")
        nxt = turns[i + 1]["spoke_at"] if i + 1 < len(turns) else float("inf")
        hits = [r for r in ready_at if end is not None and end < r < nxt]
        if hits:
            out.append(min(hits) - end)
    return out


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(int(q * len(xs)), len(xs) - 1)] if xs else None


def run(corpus, whisper, device, use_llm, port, fillers=True, cache=True):
    from chakravyuh.audio.fillers import CachedTTS, Fillers, persona_lines, with_filler
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

    stt_s, core_s, tts_s, ready_at = [], [], [], []
    endpointer = Endpointer(SileroVAD())
    llm = None
    if use_llm:
        from chakravyuh.llm import ollama_llm
        llm = ollama_llm()
    fsm = PersonaFSM(lang=script["lang"], llm=llm)
    fsm.on_scammer_turn = timed(fsm.on_scammer_turn, core_s)
    stt = timed(WhisperSTT(whisper, device=device), stt_s)
    voice = PiperTTS(script["lang"])
    tts = TimedTTS(CachedTTS(voice, persona_lines(script["lang"])) if cache else voice, tts_s, ready_at)
    filler_bank = Fillers(voice, script["lang"]) if fillers else None
    call = WebSocketCall(f"ws://127.0.0.1:{port}")
    player = Player(call.write)
    if filler_bank:
        stt = with_filler(stt, player, filler_bank)
    try:
        report = run_pipeline(call, endpointer, stt, fsm, tts, player)
    finally:
        player.close()
    t.join(15)
    return script, result.get("turns", []), stt_s, core_s, tts_s, ready_at, endpointer, report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Turn-gap latency harness")
    ap.add_argument("--corpus", default="digital_arrest")
    ap.add_argument("--whisper", default="base")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--llm", action="store_true", help="use Ollama for persona wording (default: scripted lines)")
    ap.add_argument("--port", type=int, default=8767)
    ap.add_argument("--no-fillers", action="store_true", help="disable the filler played at each endpoint")
    ap.add_argument("--no-cache", action="store_true", help="synthesise scripted lines live instead of caching")
    ap.add_argument("--label", default="")
    a = ap.parse_args(argv)

    script, turns, stt_s, core_s, tts_s, ready_at, ep, report = run(
        a.corpus, a.whisper, a.device, a.llm, a.port, fillers=not a.no_fillers, cache=not a.no_cache)
    gaps = [x["gap_s"] for x in turns if x["gap_s"] is not None]
    endpoint_s = ep.need_silence * 512 / 16000
    stages = {"gap": gaps, "reply_ready": reply_gaps(turns, ready_at), "stt": stt_s, "core": core_s,
              "tts_first_audio": tts_s}
    summary = {k: {"n": len(v), "p50": round(pct(v, .5), 3), "p90": round(pct(v, .9), 3)} for k, v in stages.items() if v}
    summary["endpoint_wait"] = {"n": len(gaps), "p50": round(endpoint_s, 3), "p90": round(endpoint_s, 3)}

    rows = [("Endpoint wait (VAD silence)", "endpoint_wait"), ("Speech to text", "stt"), ("Persona core", "core"),
            ("TTS to first audio", "tts_first_audio"), ("Reply ready (endpoint to real reply queued)", "reply_ready"),
            ("**Turn gap (caller hears first audio)**", "gap")]
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
                               "fillers": not a.no_fillers, "cache": not a.no_cache,
                               "summary": summary, "stages": stages, "turns": turns,
                               "intel": report.get("intel", [])}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nlog: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
