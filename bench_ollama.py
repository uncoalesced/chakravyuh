# Engineered by uncoalesced
"""Benchmark PersonaFSM with local Ollama on Corpus A."""
import sys
import pathlib

SRC_DIR = pathlib.Path(__file__).parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import json
import time
import urllib.request
from chakravyuh.fsm import PersonaFSM
from chakravyuh.contracts import Reply

CORPUS_DIR = pathlib.Path(__file__).parent / "corpus"
MODEL_NAME = "qwen2.5:7b-instruct-q4_K_M"
OLLAMA_HOST = "http://127.0.0.1:11434"

def warm_up():
    print(f"Warming up Ollama with {MODEL_NAME}...")
    body = {
        "model": MODEL_NAME,
        "prompt": "Hello",
        "stream": False,
        "keep_alive": "30m",
        "options": {"num_predict": 5}
    }
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        json.dumps(body).encode(),
        {"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.load(r)
    elapsed = time.perf_counter() - t0
    load_duration_ms = res.get("load_duration", 0) / 1e6
    eval_duration_ms = res.get("eval_duration", 0) / 1e6
    eval_count = res.get("eval_count", 0)
    tok_per_sec = (eval_count / (eval_duration_ms / 1000)) if eval_duration_ms > 0 else 0
    print(f"Warm-up complete in {elapsed:.2f}s (load: {load_duration_ms:.0f}ms, eval: {tok_per_sec:.1f} tok/s)")

def timed_ollama_llm(latencies):
    def call(system: str, history: list) -> str:
        body = {
            "model": MODEL_NAME,
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": 0.7, "num_predict": 80},
            "messages": [{"role": "system", "content": system}, *history]
        }
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/chat",
            json.dumps(body).encode(),
            {"Content-Type": "application/json"}
        )
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=30.0) as r:
            res = json.load(r)
        elapsed = time.perf_counter() - t0
        eval_count = res.get("eval_count", 0)
        eval_duration_ms = res.get("eval_duration", 0) / 1e6
        prompt_eval_duration_ms = res.get("prompt_eval_duration", 0) / 1e6
        tok_s = (eval_count / (eval_duration_ms / 1000)) if eval_duration_ms > 0 else 0
        latencies.append({
            "elapsed_ms": elapsed * 1000,
            "prompt_eval_ms": prompt_eval_duration_ms,
            "eval_ms": eval_duration_ms,
            "eval_count": eval_count,
            "tok_per_sec": tok_s,
            "text": res["message"]["content"].strip()
        })
        return res["message"]["content"].strip()
    return call

def run_corpus(corpus_name):
    path = CORPUS_DIR / f"{corpus_name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    latencies = []
    llm = timed_ollama_llm(latencies)
    fsm = PersonaFSM(lang=data["lang"], llm=llm)

    print(f"\n--- Running Corpus: {corpus_name} ({data['lang']}) ---")
    replies = []
    for i, turn in enumerate(data["turns"]):
        t_start = time.perf_counter()
        r = fsm.on_scammer_turn(turn["text"], turn["t"])
        t_turn = (time.perf_counter() - t_start) * 1000
        replies.append(r)
        llm_stat = latencies[-1] if latencies else None
        print(f"Turn {i+1:02d} [{r.state:10s}]: TurnGap={t_turn:6.1f}ms | LLM={llm_stat['elapsed_ms']:6.1f}ms ({llm_stat['eval_count']} tok @ {llm_stat['tok_per_sec']:.1f} t/s)")
        print(f"   Scammer: {turn['text'][:70]}...")
        print(f"   Persona: {r.text[:80]}...")

    intel = {i.kind: [x.value for x in fsm.extractor.all if x.kind == i.kind] for i in fsm.extractor.all}
    print(f"Extracted Intel: {intel}")
    return latencies

if __name__ == "__main__":
    warm_up()
    all_latencies = []
    for corpus in ["electricity_disconnect", "parcel_clearance"]:
        lats = run_corpus(corpus)
        all_latencies.extend(lats)

    raw_times = sorted(x["elapsed_ms"] for x in all_latencies)
    p50 = raw_times[len(raw_times) // 2]
    p90 = raw_times[int(len(raw_times) * 0.9)]
    avg_tok_s = sum(x["tok_per_sec"] for x in all_latencies) / len(all_latencies)

    print("\n" + "="*50)
    print("OLLAMA BENCHMARK SUMMARY (Qwen2.5-7B Q4_K_M)")
    print("="*50)
    print(f"Total LLM Turns:  {len(raw_times)}")
    print(f"p50 Latency:      {p50:.1f} ms")
    print(f"p90 Latency:      {p90:.1f} ms")
    print(f"Min Latency:      {min(raw_times):.1f} ms")
    print(f"Max Latency:      {max(raw_times):.1f} ms")
    print(f"Avg Generation:   {avg_tok_s:.1f} tokens/sec")
    print("="*50)
