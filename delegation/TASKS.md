# Jammy's Task Backlog & Acceptance Criteria

Milestones anchored to Hackathon submission: **23 Oct 2026, 5:00 pm IST**.

---

## Phase 0: Foundations & Local Benchmark (Due Oct 4)
- [x] **T0.1 Environment Setup**:
  - Clone repo, create virtualenv, run `pip install -e .[dev]`.
  - Acceptance: `pytest` exits 0 with 46 tests passing.
- [x] **T0.2 Audio Source Adapter (File Replay)**:
  - Implement an audio source interface that reads a 16kHz mono `.wav` file in simulated real-time chunks (e.g. 20ms chunks) to emulate incoming microphone/telephony audio.
  - Acceptance: Unit test asserting audio chunks are yielded with accurate timestamps.
- [x] **T0.3 STT Benchmark on Hinglish**:
  - Benchmark `faster-whisper` (`base`, `small`, or `distil-whisper`) on 5 sample Hinglish audio clips.
  - Acceptance: Log transcription accuracy, word error rate (WER), and latency per second of audio.

---

## Phase 1: Audio Pipeline & Live Queue (Due Oct 9)
- [x] **T1.1 Silero VAD Integration**:
  - Integrate Silero VAD to detect speech start, speech end, and silence thresholds (endpointing).
  - Acceptance: VAD reliably triggers on speech pause > 600ms without chopping mid-sentence.
- [x] **T1.2 Streaming STT Pipeline**:
  - Hook VAD-segmented audio directly into faster-whisper.
  - Acceptance: Produces clean `ScammerTurn(text, timestamp)` emitted into the FSM.
- [x] **T1.3 Piper TTS Worker**:
  - Integrate local Piper TTS with an elderly voice model (Hindi / Indian English).
  - Acceptance: Synthesizes `Reply(text)` into 16kHz PCM audio stream in < 300ms.
- [x] **T1.4 Playback Queue & Barge-In**:
  - Build audio playback queue that halts playback immediately if VAD detects scammer speech while persona audio is playing.
  - Acceptance: Test simulating scammer interrupt cancels current playback within 100ms.

---

## Phase 2: Dashboard Surface & Corpus B (Due Oct 14)
- [x] **T2.1 Dashboard Frontend (React + Vite)**:
  - Create a modern, clean live monitoring dashboard (`uncoalesced` palette, Apple-style tokens).
  - Live components:
    - Call Status & State (`PANIC`, `STALLING`, `BAITING`, `EXTRACTING`, `WRAPUP`).
    - Scrolling conversation transcript.
    - Extracted Intel card (UPI VPAs, bank accounts, IFSC, phone numbers, APK URLs).
    - Scammer time wasted counter (with prominent **[SIMULATED]** badge).
  - Acceptance: Connects over WebSocket and renders incoming turns in real-time.
- [x] **T2.2 Corpus B Authoring**:
  - Write synthetic test scripts for:
    1. *Digital Arrest / Fake Police scam* (`corpus/digital_arrest.json`).
    2. *Fake KYC / Bank account block scam* (`corpus/kyc_block.json`).
  - Acceptance: Scripts follow JSON schema and validate against extraction engine with expected ground-truth intel.

---

## Phase 3: Telephony Bridge & Latency Harness (Due Oct 18)
- [x] **T3.1 Virtual Scammer WebSocket Server**:
  - Build automated scammer simulation audio server that speaks corpus scripts to test end-to-end autonomous loops.
  - Acceptance: Autonomous call completes with 0 human intervention and full intel report generated.
- [x] **T3.2 Latency Harness**:
  - Measure total turn gap (Scammer stops talking &rarr; Persona begins speaking).
  - Acceptance: Measured p50 latency recorded and logged in `docs/BENCHMARKS.md`.

---

## Phase 4: Polish, Live Demo & Hardening (Due Oct 21)
- [x] **T4.1 Architecture & Data-Loop Diagrams** (Jammy):
  - Export system architecture and AI framework / data-loop SVG diagrams and 2x PNGs.
  - Acceptance: High-resolution diagrams linked in `docs/ARCHITECTURE.md`.
- [x] **T4.2 One-Command Audible Demo** (Jammy):
  - Add `--demo CORPUS` and `--speakers` monitor in `dashboard/server.py`.
  - Acceptance: `python dashboard/server.py --demo kyc_block --loop --speakers` streams audible call locally.
- [x] **T4.3 Demo Runbook & Guardrails Review** (Jammy & Joel):
  - Create `docs/DEMO_RUNBOOK.md` covering judge-facing beats, checklists, fallback ladder, and likely Q&A reviewed against `docs/GUARDRAILS.md`.
  - Acceptance: Runbook verified and aligned with team guardrails.
- [x] **T4.4 Core Identifier Extraction Hardening** (Joel):
  - Harden IFSC regex against false positives from natural language and normalize spoken spelled UPI usernames while pruning sub-matches.
  - Acceptance: 100% precision on Corpus B ground-truth intel with 0 extra or missing matches (all 123 tests passing).
- [x] **T4.5 Demo GPU Benchmark Telemetry** (Joel):
  - Run latency harness on Demo GPU (NVIDIA RTX 5050 Laptop GPU with CUDA float16).
  - Acceptance: Measured latency recorded in `docs/BENCHMARKS.md` (turn gap p50 641ms).

---

## Phase 5: Rehearsal, Buffer & Submission (Due Oct 23, 5:00 pm IST)
- [ ] **T5.1 Demo Rehearsal**:
  - Rehearse live audible demo >= 20 times across both English (`kyc_block`) and Hindi (`digital_arrest`) scenarios.
  - Fallback check: Verify text replay fallback (`--corpus kyc_block --speed 1.5`) and record fallback video.
- [ ] **T5.2 Devpost & Presentation Deliverables**:
  - Prepare Devpost project description, architecture overview, and pitch deck narrative grounded in `docs/PROBLEM.md` and `docs/GUARDRAILS.md`.
- [ ] **T5.3 Administrative & Registration Verification**:
  - Verify offline registration form submission on `nextgenexpo.raaif.org`.
  - Confirm table logistics, power, audio equipment policy, and college team credentials with RAAIF organisers.
