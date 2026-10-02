# Jammy's Task Backlog & Acceptance Criteria

Milestones anchored to Hackathon submission: **23 Oct 2026, 5:00 pm IST**.

---

## Phase 0: Foundations & Local Benchmark (Due Oct 4)
- [ ] **T0.1 Environment Setup**:
  - Clone repo, create virtualenv, run `pip install -e .[dev]`.
  - Acceptance: `pytest` exits 0 with 46 tests passing.
- [ ] **T0.2 Audio Source Adapter (File Replay)**:
  - Implement an audio source interface that reads a 16kHz mono `.wav` file in simulated real-time chunks (e.g. 20ms chunks) to emulate incoming microphone/telephony audio.
  - Acceptance: Unit test asserting audio chunks are yielded with accurate timestamps.
- [ ] **T0.3 STT Benchmark on Hinglish**:
  - Benchmark `faster-whisper` (`base`, `small`, or `distil-whisper`) on 5 sample Hinglish audio clips.
  - Acceptance: Log transcription accuracy, word error rate (WER), and latency per second of audio.

---

## Phase 1: Audio Pipeline & Live Queue (Due Oct 9)
- [ ] **T1.1 Silero VAD Integration**:
  - Integrate Silero VAD to detect speech start, speech end, and silence thresholds (endpointing).
  - Acceptance: VAD reliably triggers on speech pause > 600ms without chopping mid-sentence.
- [ ] **T1.2 Streaming STT Pipeline**:
  - Hook VAD-segmented audio directly into faster-whisper.
  - Acceptance: Produces clean `ScammerTurn(text, timestamp)` emitted into the FSM.
- [ ] **T1.3 Piper TTS Worker**:
  - Integrate local Piper TTS with an elderly voice model (Hindi / Indian English).
  - Acceptance: Synthesizes `Reply(text)` into 16kHz PCM audio stream in < 300ms.
- [ ] **T1.4 Playback Queue & Barge-In**:
  - Build audio playback queue that halts playback immediately if VAD detects scammer speech while persona audio is playing.
  - Acceptance: Test simulating scammer interrupt cancels current playback within 100ms.

---

## Phase 2: Dashboard Surface & Corpus B (Due Oct 14)
- [ ] **T2.1 Dashboard Frontend (React + Vite)**:
  - Create a modern, clean live monitoring dashboard (`uncoalesced` palette, Apple-style tokens).
  - Live components:
    - Call Status & State (`PANIC`, `STALLING`, `BAITING`, `EXTRACTING`, `WRAPUP`).
    - Scrolling conversation transcript.
    - Extracted Intel card (UPI VPAs, bank accounts, IFSC, phone numbers, APK URLs).
    - Scammer time wasted counter (with prominent **[SIMULATED]** badge).
  - Acceptance: Connects over WebSocket and renders incoming turns in real-time.
- [ ] **T2.2 Corpus B Authoring**:
  - Write synthetic test scripts for:
    1. *Digital Arrest / Fake Police scam* (`corpus/digital_arrest.json`).
    2. *Fake KYC / Bank account block scam* (`corpus/kyc_block.json`).
  - Acceptance: Scripts follow JSON schema and validate against extraction engine with expected ground-truth intel.

---

## Phase 3: Telephony Bridge & Latency Harness (Due Oct 18)
- [ ] **T3.1 Virtual Scammer WebSocket Server**:
  - Build automated scammer simulation audio server that speaks corpus scripts to test end-to-end autonomous loops.
  - Acceptance: Autonomous call completes with 0 human intervention and full intel report generated.
- [ ] **T3.2 Latency Harness**:
  - Measure total turn gap (Scammer stops talking &rarr; Persona begins speaking).
  - Acceptance: Measured p50 latency recorded and logged in `docs/BENCHMARKS.md`.
