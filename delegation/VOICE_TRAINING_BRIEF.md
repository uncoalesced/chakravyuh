# Voice training brief: Vikram + Raghunath v2

For Aaron's coding agent. Read this whole file, then start with step 1 of section 4.

## 0. Ground rules

- Repo: `github.com/uncoalesced/chakravyuh`. Branch off `finishing-touch` into `feat/voice-training`. No push to `main`; open a PR.
- Aaron owns `src/chakravyuh/audio/`, `for_jammy/` and the voice tooling. Do not edit `contracts.py`, `fsm.py`, `extract.py`, `report.py` or `llm.py` (Joel's). Ask Joel first if a change there is unavoidable.
- Never commit `*.wav`, `models/`, datasets or zips (gitignored). Handoff notes go in the vault, not the repo.
- Reuse what exists. Do not rebuild the recorder, the notebook or the transliterator; extend them.
- No secrets, emails or tokens in the repo or in a notebook.
- Training data is Aaron's own voice (consented), performing characters. No other person's voice, no cloning of real people. Fake numbers, UPI handles and IFSC codes only, like the existing corpora.

## 1. Goal

Two good single-speaker Piper voices as ONNX in `models/piper/`:

**Every new voice is recorded by Aaron (Jammy), each as a clearly different character with a different accent, so the voices sound like different people.** One consistent character per voice for the whole dataset; do not drift between takes.

- `vikram_scammer-medium` (+ `.onnx.json`): Aaron as Inspector Vikram. Urgent, authoritative Indian call-centre cadence, Hindi/Hinglish. Suggested accent: North Indian / Delhi police, clipped and fast. Aaron may choose another.
- `raghunath_elderly_v2-medium` (+ `.onnx.json`): Aaron playing a different character, a 68-year-old, hesitant, confused, warm. Hinglish. Suggested: slower, softer, slightly raspy, a regional lilt unlike Vikram's. Replaces Joel's v1 only if it wins a listening A/B.
- Optional extra characters (e.g. a second scammer, "Son" persona lines in `jammy_voice_prompts.txt` 043-048): only after both above are done; same pipeline, new `VOICE` name.
- Character sheet: before recording, write `voice_studio/characters.md` with one short entry per voice (age, accent, pace, pitch, mood, a 3-line sample). Aaron reads it before each session. Keep each voice's recording environment (mic, room, distance, gain) identical across all its sessions.
- Joel's existing v1 Raghunath (his own voice) stays untouched as the baseline.

Quality bar: no garbling on digits, UPI handles, IFSC codes or 15 s sentences; no clipping; stable over a 10-turn call. Good balance: enough data to be robust, not a month of recording. Target about 45+ minutes of clean audio (500+ lines) per voice.

## 2. What already exists (read first)

- `train_raghunath_colab.ipynb`: proven end to end. Python 3.10 `uv` venv, torch 1.13.1+cu117, pins `setuptools<70 torchmetrics<1 six protobuf<4 tensorboard==2.11.2`. Base checkpoint `hi_IN-rohan-medium` at epoch 3190 (806 MB, public Hugging Face URL in the notebook). Preprocess: `--language hi --dataset-format ljspeech --sample-rate 22050`. `--max_epochs` = base epoch + N. **Do not change the environment pins.**
- `for_jammy/record_prompts.py`: teleprompter recorder. 22,050 Hz mono, trims silence, normalizes, runs `translit.to_devanagari`, writes LJSpeech `metadata.csv` + `wav/`. Diff it against `voice_studio/record_prompts.py` (Joel's copy) and port any fixes. Some docs say 16 kHz; the code and training use 22,050. Fix the docs.
- Prompt files: `for_jammy/jammy_voice_prompts.txt` (54 lines, format `ID|hi/en|text`), an older 72-line copy in `voice_studio/`, and `voice_studio/voice_prompts.txt` (Raghunath, 69 lines). Persona lines are in `src/chakravyuh/fsm.py` (`LINES`) and `src/chakravyuh/audio/fillers.py`. Scammer scripts are in `corpus/*.json`.
- Raghunath v1 dataset: 41 clips, 3.95 min, peak 0.90, no clipping.
- Aaron's raw WhatsApp `.ogg` notes (11 files, ~7 min): noisy. Fallback and listening reference only.
- `src/chakravyuh/audio/tts.py`: a voice is "custom" if its filename contains `raghunath` or `custom` (length_scale 1.05, noise 0.75/0.80, volume 0.8). `vikram` is not wired.
- Colab gotchas:
  - `/content` is wiped on runtime reset; free Colab recycles runtimes overnight.
  - `files.upload()` needs a manual "Choose Files" click.
  - `drive.mount` hangs inside Claude's browser pane; it works in a normal browser tab, so Aaron can use Drive for backup.
  - "amplitude out of range, auto clipped" log warnings are about model output; ignore.
  - Agent control of a Colab tab: `colab.global.notebook.cells[i].getText()/setText()/manualExecute()/isRunning()`, `colab.global.notebook.kernel.interrupt()`. Keep each JS call under 45 s.

## 3. Deliverables

1. **Line generator + prompt sets.** At least 520 lines per voice as `ID|lang|text`, Roman Hinglish in source, Devanagari via `translit`.
   - Length mix: ~15% 1-3 s, ~55% 3-8 s, ~25% 8-12 s, ~5% up to 15 s. Reject anything over 15 s.
   - Phoneme coverage: a checker script (espeak-ng `hi`) that reports missing and rare phonemes and diphones. Iterate until every Hindi phoneme appears at least 30 times. Cover retroflex, aspirates, nasals, conjuncts and nukta letters.
   - Domain coverage: all four corpora (`digital_arrest`, `electricity_disconnect`, `kyc_block`, `parcel_clearance`) re-voiced with many paraphrases.
     - Vikram: digits (spoken and numerals), UPI handles, spelled IFSC letters, amounts, phone numbers, pressure, threats, urgency.
     - Raghunath: stalling, confusion, "beta", asking to repeat, hearing trouble, grandson, tablets/BP/glasses, fumbling the phone, fear, polite deflection, plus every `LINES` pool and filler.
   - Mix statements, questions and exclamations; vary commas and pauses; ~10% short backchannels ("haan ji", "achha", "hmm").
   - Dedupe (exact and near-duplicate). Do not mix Joel's 41 v1 clips into v2 (different speaker); v2 is Aaron-only.
   - **Hold out 40 eval lines per voice**, never used for training.
   - English: default is Hindi/Hinglish for everything, English-origin words through `to_devanagari`. Test 20 English-origin lines through the `hi` phonemizer and report. If poor, propose a separate `en` track; do not silently drop lines.
   - Split into ~60-line sessions (~8 min each) so recording can happen in sittings.
2. **Recorder upgrade** (extend `record_prompts.py`, do not rewrite): resume from the last recorded ID; session select; per-take checks (peak, clipping, noise floor, 1.5-15 s length) with automatic re-prompt; target peak about -3 dBFS; optional faster-whisper round trip to flag misreads; progress and minutes recorded; works on Windows.
3. **`validate_dataset.py`**: metadata/wav parity, 22,050 Hz mono 16-bit, durations, total minutes, peak and clipping, edge silence, duplicate text, non-Devanagari leakage, loudness spread, outliers. Pass/fail table. Packs `<voice>_dataset.zip`. Gate: at least 45 min usable and at most 2% clips failing.
4. **One parameterised Colab notebook** `train_voice_colab.ipynb` (`VOICE = "vikram" | "raghunath_v2"` in cell 1), built from the proven notebook with the same pins, plus:
   - Preflight: GPU, disk, Python, base-checkpoint URL reachable, dataset zip present.
   - Dataset upload via Drive or manual upload.
   - Resumable chunked training. Every ~1,000 steps: export an ONNX, render the 40 held-out lines, zip and back up (Drive if mounted, else `files.download`). A reset loses at most one chunk; a resume cell picks up the latest checkpoint.
   - Budget by steps, not epochs: a 50-step dry run measures s/step and prints an ETA, then sets `max_epochs = base_epoch + ceil(target_steps / steps_per_epoch)`. Starting target ~8-12k steps for ~45 min of data; stop at plateau (validation loss plus listening). State whether free Colab (12 h cap) can finish and what to use if not (Colab Pro, Kaggle, or resume across sessions).
   - Batch size 16 by default; try 32 if VRAM allows. Keep fp16.
   - Final: choose the best checkpoint by held-out WER and listening; export `<name>.onnx` + `.onnx.json`, SHA256, zip.
5. **`eval_voice.py`**: loads an ONNX through `PiperTTS`; renders the held-out lines, a digit/UPI stress set and a 15 s sentence; reports peak, clipping, real-time factor and Whisper round-trip WER; writes WAVs and a comparison page for A/B listening (like `raghunath_variants/`). Compare Raghunath v1 vs v2.
6. **Wiring**: add `vikram` as a custom voice in `tts.py` (no elderly DSP, length_scale at most 1.0, tune noise and volume by ear and tests). Make `bench/virtual_caller.py` use Vikram for the demo scammer, falling back to pratham/ryan if the file is missing. `pytest -q` must stay green (125 passing at last count); add tests for voice selection.
7. **`JOEL_TODO.md`** (do this FIRST, before building anything else): the exact, minimal list of what Joel must do and when. Joel no longer records; Aaron records all voices. Joel's part is review and approval (listen to A/B, pick winners), any Colab steps that need his account or a manual click (sign-in, Choose Files, GPU runtime), merging the PR, and anything in his territory (`fsm.py` etc.) that the new voices need. Include expected wall-clock time and what to send back. Self-contained and copy-pasteable; Joel will run it in a separate session.

## 4. Order of work

1. Read the repo and this brief. Write the `JOEL_TODO.md` draft and send Aaron a short status.
2. Line generator, coverage report and prompt sets for both voices. Aaron reviews.
3. Recorder upgrade and validator. Dry-run 5 lines on Aaron's machine.
4. Notebook and eval script. Smoke-test 100 steps on the existing 41-clip Raghunath set to prove the new notebook still trains.
5. Aaron records Vikram, then validate, train, eval, wire in.
6. Aaron records Raghunath v2 in the different character/accent, then the same loop.
7. A/B v1 vs v2 and ship the winner.

## 5. Definition of done

Do not call anything done without: validator pass output, eval WAVs, and `pytest -q` output. If a pinned dependency breaks, report the exact error to Joel rather than changing pins.

## 6. Report back

Short report: what is built (paths); numbers (lines, minutes, phoneme coverage, s/step, ETA); open decisions (English handling, free-Colab limits); link to `JOEL_TODO.md`; and what you skipped or could not verify.
