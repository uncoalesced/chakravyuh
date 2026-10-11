# Demo runbook

The live demonstration for judges: a simulated scam call that Chakravyuh answers and runs to the end with no human input,
while the dashboard shows the persona's state, the conversation and the details being captured. About 4 minutes per
judge group, including a short intro. Rehearse at least 20 times between phases 3 and 5 (docs/MILESTONES.md).

## What the judges see

| Time | On screen and on the speaker | What we say (short, factual) |
|---|---|---|
| 0:00 | Dashboard, waiting for a call | "Scam callers depend on a frightened person. Chakravyuh answers instead, as a confused elderly persona, on the owner's own phone line." |
| 0:20 | Call starts. Caller voice threatens a KYC block or a fake arrest | "This caller is simulated: a script we wrote, read by a synthetic voice. Nothing here is a real person or organisation." |
| 0:40 | Persona panics, then stalls ("my spectacles…"). Stepper moves PANIC → STALLING | "A state machine decides what the persona is trying to do. The language model only words the line, and every line is filtered." |
| 1:30 | Persona offers to pay and asks for the payee. Stepper: BAITING | "It steers toward the moment the caller has to read out where the money should go." |
| 2:00 | Caller reads a UPI ID / account and IFSC. Captured details card fills in; persona asks for a slow repeat | "Details are captured with a format check only. We never claim an ID is verified or fraudulent." |
| 3:00 | Second round after a "payment failed", then WRAPUP and hang-up. Report card appears | "At the end it prepares a report for a person to review and submit through 1930, cybercrime.gov.in or Chakshu. Nothing is filed automatically." |
| 3:30 | Point at the time counter (SIMULATED badge) | "The caller spent this time on a persona that cannot be harmed. The cost figure is illustrative, at an assumed rate." |

If asked about speed, quote the measured number from `docs/BENCHMARKS.md`, for the machine on the table.

## The day before
- [ ] `git pull`, then `pip install -e ".[dev,audio,dashboard]"` and `pip install silero-vad --no-deps sounddevice`.
- [ ] Models in `models/piper/`: `hi_IN-rohan-medium`, `hi_IN-pratham-medium`, `en_GB-alan-medium`, `en_US-ryan-medium`
      (`.onnx` + `.onnx.json`). Whisper weights cached by one run of `bench/stt_bench.py` or the demo itself.
- [x] `pytest -q` is green across all 123 tests.
- [ ] `cd dashboard/web && npm install && npm run build`.
- [ ] Run the full demo twice on the demo laptop, once per script. Watch for: every turn answered, report card appears.
- [ ] Run `python bench/latency.py --corpus kyc_block --whisper small --device cuda --label "demo laptop"` and copy the
      result into `docs/BENCHMARKS.md`. This is the only latency number we quote.
- [ ] Record a fallback screen capture of one complete good run (with audio).
- [ ] Turn off OS notifications, sleep and auto-updates. Close every other app. Charge the laptop.
- [ ] Everything runs offline. Disconnect Wi-Fi in one rehearsal to prove it.

## At the table (30 minutes before)
1. Power in, screen brightness up, speaker volume tested at conversation level.
2. One terminal in the repo with the venv active. Browser full screen on the dashboard tab.
3. Start the demo and let the first call run as a warm-up (it loads models and fills the voice cache, ~20 s):
   ```
   python dashboard/server.py --demo kyc_block --loop --speakers
   ```
   Open http://127.0.0.1:8000. `--loop` restarts the call 8 s after it ends, so it is always ready for the next group.
4. For a Hindi-speaking panel, use `--demo digital_arrest` instead (Hindi persona and caller).

Optional: with the LLM. Start Ollama with the model warm (`ollama run qwen2.5:7b-instruct-q4_K_M "hi"`) and only use it if
the rehearsal on this laptop shows it stays inside the turn budget. Without it, the persona uses its scripted lines,
which is the default and the most reliable path.

## If something goes wrong
Work down the ladder; do not debug in front of the judges.

| Symptom | Do this |
|---|---|
| A turn is slow or misheard | Keep talking over it. The persona's fillers and stalling are in character. |
| Audio pipeline fails or hangs (no new turns for 20 s) | `Ctrl+C`, then the text replay, which needs no models: `python dashboard/server.py --corpus kyc_block --speed 1.5 --loop`. Say "this replays the same script as text". |
| Dashboard does not update | Reload the page (it catches up with the current call). If still dead, restart the server. |
| Laptop or projector fails | Play the recorded fallback video. Say it is a recording. |

## Between groups
Nothing to do with `--loop`: the next call starts on its own and the page resets on `call_start`. If a call is mid-way when
a new group arrives, either let it finish (about 3 minutes) or restart the server.

## Claims cheat sheet (docs/GUARDRAILS.md)
Say:
- "Prepared for review and submission through the official channels."
- "Format-checked", "captured", "simulated call", "illustrative cost".
- "Complements awareness efforts with an active layer."
- Measured numbers, with the machine they were measured on.

Never say:
- "Automatically filed / reported / sent to police."
- "Verified", "confirmed fraud", "mule account" about any captured detail.
- Anything negative about any agency, programme or institution.
- A loss statistic without its source (use the cited figure in `docs/PROBLEM.md`, with the source).
- That the demo caller or organisation is real.

## Likely questions
- **Is this legal to use?** It is designed for the owner's own phone line. Deployment beyond a demo needs a legal review
  first; we do not give legal advice.
- **Does it store recordings?** No call audio is stored by default. Captured details stay on the machine until the person
  exports the report.
- **What if the caller realises it is a bot?** The persona deflects bot questions in character; the call simply ends, and
  nothing is lost for the person it protects.
- **Why a state machine and not just an LLM?** Behaviour stays predictable and testable; the model cannot decide to give out
  data or abandon the plan. Any model failure falls back to a scripted line, so the call never goes silent.
- **How accurate is the speech recognition on Hinglish?** Honest answer: it is the weakest part today; see the human-recording
  benchmark in `docs/BENCHMARKS.md`. The persona asks for slow repeats and spellings to compensate.
- **Does it work on a real phone?** The audio pipeline reads from an adapter; the same WebSocket line protocol is meant for a phone
  bridge. Show it only if the bridge has passed rehearsal.
