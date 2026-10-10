# Jammy's Delegation Hub - Chakravyuh

Welcome Jammy! This folder is your mission control for **Chakravyuh**—an open-source (MIT) counter-scam voice agent for India targeting the **Next Gen Hackathon 2026 Bengaluru** (Deadline: **23 Oct 2026, 5:00 pm IST**).

We operate on a strict **50/50 split** of work and responsibilities.

---

## 1. Territory & Folder Boundaries

| Owner | Primary Focus | Directories & Files |
|---|---|---|
| **Jammy** | **Audio Pipeline, Surface & Corpus B** | `src/chakravyuh/audio/` (VAD, STT, TTS, barge-in, routing), `dashboard/` (frontend + WS feed), latency harness, `corpus/` (Corpus B: digital arrest, KYC) |
| **Joel** | **Core Engines, Extraction & Corpus A** | `src/chakravyuh/fsm.py` (persona state machine), `src/chakravyuh/extract.py` (UPI, bank, IFSC, phone, URL), `src/chakravyuh/report.py`, `src/chakravyuh/llm.py`, `corpus/` (Corpus A: electricity, parcel) |
| **Shared Boundary** | **Contracts & Seams** | `src/chakravyuh/contracts.py`, `docs/CONTRACTS.md`, `tests/` |

> **Rule on Boundaries**: If a task requires modifying files in Joel's territory or changing `src/chakravyuh/contracts.py`, pause and align with Joel first using the communication prompts below.

---

## 2. Environment Setup

```bash
# 1. Clone repo
git clone https://github.com/uncoalesced/chakravyuh.git
cd chakravyuh

# 2. Virtual environment (Python 3.11 recommended)
python -m venv venv
source venv/bin/activate  # Or on Windows: .\venv\Scripts\Activate.ps1

# 3. Install core dependencies & test tools
pip install -e .[dev]

# 4. Verify existing tests (all 46 tests must pass)
pytest

# 5. Audio tools setup (Phase 0/1)
pip install faster-whisper silero-vad piper-tts
```

---

## 3. Jammy's Immediate Roadmap

### Phase 0 Exit Check (Current Focus)
- [x] Set up local repo access and run `pytest` (assert 46 passed).
- [x] Build **audio-source adapter with file replay** (feed WAV files into the pipeline as if they were live mic input).
- [x] Run **STT benchmark** on Hinglish audio clips to measure character/word error rate and latency.

### Phase 1: Audio Pipeline & Live Queue
- [x] **Silero VAD Endpointing**: Clean speech detection to detect when the caller stops speaking.
- [x] **Streaming STT with faster-whisper**: Generate transcripts with low initial latency.
- [x] **Piper TTS Integration**: Synthesize persona audio locally (default Hindi/English voice).
- [x] **Playback Queue & Barge-In**: Cancel persona audio immediately if the scammer interrupts.

### Phase 2: Dashboard & Corpus B
- [x] **Dashboard Frontend**: React + Vite interface with live WebSocket feed displaying turns, extracted intel, and caller time wasted counter (with visible "simulated" badge).
- [x] **Corpus B**: Author synthetic scam scripts for *digital arrest* and *fake KYC/bank update* scenarios.

---

## 4. When to Ask Joel (Copyable Prompts)

> **On Contract Changes**:  
> *"Hey Joel, I need to modify `Reply` / `ScammerTurn` in `src/chakravyuh/contracts.py` to support `<field_or_audio_state>`. Can you check if this breaks any FSM assumptions?"*

> **On Latency Tuning**:  
> *"Hey Joel, I benchmarked Whisper on Hinglish audio. Turn-gap p50 is currently `<ms>`. Should we look into sentence streaming or a smaller model?"*

> **On Hardware / Phone Bridge**:  
> *"Hey Joel, are we testing the audio loop via the virtual caller WebSocket or the physical 3.5mm TRRS cable on the Redmi Note 11 today?"*

---

For detailed breakdown of all tasks with acceptance criteria, see [`delegation/TASKS.md`](./TASKS.md).
