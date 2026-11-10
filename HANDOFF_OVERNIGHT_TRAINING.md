# Handoff: Raghunath Voice Training & Google Colab Debugging

**Date & Time:** October 15, 2026, 00:15 IST  
**Target:** Next Gen Hackathon 2026 Bengaluru (Deadline: Oct 23, 2026, 5:00 PM IST)  
**Owners:** Joel Anthony (`uncoalesced`) & Jammy (`Aaron`)  
**Persona to Train:** **Raghunath** (68-year-old elderly victim honeypot persona, voiced by Joel)  
**Base Architecture:** Piper TTS (VITS fine-tuning from `hi_IN-rohan-medium`)  

---

## 1. Executive Summary & Current State

Both voice datasets have been collected and verified on disk. Joel attempted overnight training via Google Colab, but the setup failed at **Step 2** due to a Python version / wheel incompatibility with `piper-phonemize`, preventing preprocessing and training from executing.

This document provides the exact technical post-mortem, dataset inventory, and turnkey instructions for the incoming agent to resolve the dependency mismatch and launch training in the new session.

---

## 2. Dataset Status & Inventory

### A. Joel's Dataset (Raghunath — Elderly Victim Persona) — **100% READY**
* **Location:** `C:\Users\Joel Anthony\Documents\Phile\Heafod\Heafod\Chakravyuh\voice_studio\data\dataset`
* **Audio Files:** 41 normalized, silence-trimmed WAV files (22,050 Hz mono) in `wav/` (`PROMPT_001.wav` – `PROMPT_060.wav`). Total duration: **3.95 minutes (236.9 seconds)**.
* **Metadata:** `metadata.csv` (LJSpeech format `clip_id|text`), with Roman Hindi properly transliterated to Devanagari Hindi for Piper's phonemizer.
* **Packaged Archive:** `voice_studio\data\raghunath_dataset.zip` (6.27 MB, self-contained and ready to upload).

### B. Jammy's Dataset (The Scammer / Virtual Callers) — **RAW AUDIO COLLECTED**
* **Location:** `C:\Users\Joel Anthony\Documents\Phile\Heafod\Heafod\Chakravyuh\voice_studio\data\dataset-jammy`
* **Files:** 11 WhatsApp voice notes (`.ogg` files, ~7 minutes total) containing Inspector Vikram Rathore fake FIR, bank details, and scam lines.
* **Note:** Joel confirmed we are training the **victim's voice (Raghunath)** first. Jammy's audio does not block Raghunath training; it will be sliced and aligned via Whisper when training the scammer caller persona later.

---

## 3. Post-Mortem: Why Google Colab Failed Tonight

### The Root Cause (Step 2 Dependency Resolution Failure)
In Google Colab, executing `pip install -r requirements.txt` or `pip install -e .` inside `piper/src/python` fails with:
```text
ERROR: Could not find a version that satisfies the requirement piper-phonemize~=1.1.0 (from versions: none)
ERROR: No matching distribution found for piper-phonemize~=1.1.0
```

### Why this happens:
1. `piper-phonemize` on PyPI only published pre-compiled binary Linux wheels for **Python 3.9 and Python 3.10** (`cp39`, `cp310`).
2. Google Colab's default Linux runtime now runs **Python 3.11 / Python 3.12**.
3. Because no matching wheel exists on PyPI for the newer Python runtime, `pip` aborts dependency installation.
4. **The Cascade:**
   * Step 2 failed to install dependencies (`piper-phonemize`, `pytorch-lightning`).
   * Step 5 failed with `ModuleNotFoundError: No module named 'piper_phonemize'`.
   * Step 6 failed with `ModuleNotFoundError: No module named 'pytorch_lightning'`.
   * Step 7 failed with `FileNotFoundError: Training hasn't produced checkpoints yet.` because training never actually started.

---

## 4. Immediate Solutions for the New Session

In the new session, the incoming agent must update **Step 2** using one of the following two verified solutions:

### Solution A: Install `piper-phonemize-fix` (Quickest & Cleanest)
A community-maintained PyPI wheel specifically built for newer Python versions exists:
```bash
%cd /content/piper/src/python
# Patch requirements.txt to use the updated wheel
!sed -i 's/piper-phonemize~=1.1.0/piper-phonemize-fix/g' requirements.txt
!sed -i 's/piper-phonemize~=1.1.0/piper-phonemize-fix/g' setup.py

!pip install -r requirements.txt
!bash build_monotonic_align.sh
!pip install -e .
```

### Solution B: Create a Python 3.10 Environment via Conda / UV in Colab
Run Piper training inside a dedicated Python 3.10 sub-shell where the official `piper-phonemize-1.1.0-cp310-cp310-manylinux_2_28_x86_64.whl` installs natively:
```bash
!pip install uv
!uv venv --python 3.10 /content/piper_env
!/content/piper_env/bin/pip install --upgrade pip
!/content/piper_env/bin/pip install torch torchvision torchaudio pytorch-lightning
!/content/piper_env/bin/pip install -r /content/piper/src/python/requirements.txt
!cd /content/piper/src/python && bash build_monotonic_align.sh
!/content/piper_env/bin/pip install -e /content/piper/src/python
```
Then invoke preprocessing and training using `/content/piper_env/bin/python3 -m piper_train ...`.

### Solution C: Modern `piper1-gpl` / OHF-Voice Trainer
Development of Piper has moved to `OHF-Voice/piper1-gpl`, which has embedded `espeak-ng` directly into modern wheels without needing standalone `piper-phonemize`.

---

## 5. Critical Checkpoint & Path References

* **Base Model Download URL:**
  `https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/hi/hi_IN/rohan/medium/epoch=3190-step=309852.ckpt`  
  *(Publicly verified, 806 MB, downloads without HF tokens)*.
* **Preprocessed Dataset Output:** `/content/dataset_preprocessed`
* **Training Logs & Checkpoints Location:** `/content/dataset_preprocessed/lightning_logs/version_0/checkpoints/*.ckpt`
* **Target ONNX Output:** `raghunath_elderly-medium.onnx` and `raghunath_elderly-medium.onnx.json`
* **Local Repo Integration:** Dropping these two files into `E:\Chakravyuh\models\piper\` immediately activates Raghunath in `src/chakravyuh/audio/tts.py`.

---

## 6. Action Checklist for Next Session
1. [ ] Check Colab Python version (`!python --version`).
2. [ ] Apply Solution A (`piper-phonemize-fix`) or Solution B (Python 3.10 venv via `uv`) in Step 2.
3. [ ] Verify `import piper_phonemize` and `import pytorch_lightning` succeed.
4. [ ] Run Step 5 (preprocess 41 audio files with Hindi phonemes).
5. [ ] Run Step 6 (train for 100 epochs, expected duration: ~60–80 minutes on T4 GPU).
6. [ ] Export ONNX model via Step 7.
7. [ ] Download `raghunath_model_exported.zip` and place in `E:\Chakravyuh\models\piper\`.
