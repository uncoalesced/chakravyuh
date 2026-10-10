# Benchmarks

Every number here comes from a logged harness run (`bench/latency.py`, `bench/stt_bench.py`); the label says what
machine and models were used. Calls are simulated: a synthetic caller voice (Piper) reads a synthetic corpus script.
Numbers quoted in the pitch must come from the demo machine, not from this file's laptop rows.

## Turn gap

Measured by the virtual caller: from the last frame of caller speech to the first persona audio arriving back on
the line. Stages are timed inside the agent for the same turns.

### Laptop CPU, no GPU (10 Oct 2026)
`python bench/latency.py --corpus kyc_block --whisper base --device cpu` · whisper base int8 · Piper en_GB-alan ·
scripted persona (no LLM) · 11/11 turns answered · log `latency_kyc_block_20261010_210300.json`

| Stage | p50 | p90 | Target (ARCHITECTURE.md) |
|---|---|---|---|
| Endpoint wait (VAD silence) | 608 ms | 608 ms | <= 300 ms |
| Speech to text | 586 ms | 844 ms | <= 300 ms |
| Persona core (scripted) | 1 ms | 1 ms | first LLM token <= 400 ms |
| TTS to first audio | 241 ms | 335 ms | <= 200 ms |
| **Turn gap** | **1484 ms** | **1781 ms** | **p50 < 1.2 s** |

One outlier turn (6.9 s) was whisper looping on a spoken URL; it is in the log, not hidden.

#### Same call with fillers and the TTS cache (10 Oct 2026)
Same command and models, plus `audio/fillers.py`: a pre-synthesised filler ("Yes, yes...") starts at each endpoint,
and the persona's scripted lines are synthesised at startup. 11/11 answered · log `latency_kyc_block_20261010_211325.json`

| | Before | After |
|---|---|---|
| **Turn gap, caller hears first audio** | 1484 / 1781 ms | **656 / 671 ms** (p50 / p90) |
| Reply ready (caller stops to real reply queued) | ~1450 ms (stage sum) | 1188 / 1297 ms |
| TTS to first audio | 241 / 335 ms | 0 / 0 ms (cached) |
| Speech to text | 586 / 844 ms | 554 / 656 ms |

The caller now hears the persona about 50 ms after the endpoint wait ends. The real reply follows the filler; it is about
300 ms sooner than before because cached lines skip synthesis. LLM-worded lines are not cached and still pay TTS.

Hindi run of the same setup (`digital_arrest`, whisper base, 11/11 answered): turn gap p50 2.9 s, p90 5.3 s.
Hindi turns are longer and whisper spends longer on them.

### Demo GPU
Not measured yet. Run on the demo machine with the LLM enabled:
`python bench/latency.py --corpus kyc_block --whisper small --device cuda --llm --label "demo GPU"`.

## What the breakdown says
- **Endpoint wait is fixed at 600 ms**, set by T1.1's "pause > 600 ms" rule, and already twice the 300 ms budget. Dropping it
  to ~400 ms saves 200 ms on every turn but splits more dictated IDs across turns (see `bench/README.md`).
- **STT is the main variable cost**, and on CPU it grows with utterance length. A GPU, or decoding while the caller is
  still talking, is the fix.
- **TTS is close to budget** for live text; scripted lines are now cached (0 ms).
- **Fillers hide the rest**: what the caller waits for is now the endpoint wait plus ~50 ms.
- With the LLM enabled, the core stage will add the first-sentence time from Ollama; measure it on the demo GPU.

## Recognition quality in these runs
The caller voice is synthetic, so this understates real-call accuracy for Hindi and overstates nothing; see
`bench/stt_bench.py` runs on human recordings. In the KYC run the account number survived, while the UPI ID and IFSC did
not, and the extractor added false IFSC matches from ordinary words (tracked in `tests/test_corpus_b.py`).

## STT on human Hinglish recordings (5 Oct 2026)
`python bench/stt_bench.py` on five corpus lines read by a person, laptop CPU int8, greedy decoding.

| Model | Language | WER | ms per audio second | Identifiers recovered |
|---|---|---|---|---|
| base | en | 1.14 | 125 | 1/5 |
| base | hi | 1.12 | 323 | 1/5 |
| small | en | 1.20 | 225 | 1/5 |
| small | hi | 1.81 | 1400 | 0/5 |
