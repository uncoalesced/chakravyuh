# Chakravyuh: Autonomous Counter-Scam Defensive Voice Agent

*Submission text and presentation narrative for Next Gen Hackathon 2026 Bengaluru (Track: AI & Robotics — Stream 1: Intelligent Real-World Assistance)*

---

## 1. Project Overview & Pitch

- **Project Name**: Chakravyuh
- **Elevator Pitch**: An autonomous, privacy-preserving voice agent that answers suspicious incoming calls, engages scammers using an adaptive elderly persona to waste their operational time, extracts actionable financial identifiers (UPI VPAs, bank accounts, IFSC codes, phone numbers, and APK links), and compiles a structured incident dossier for manual citizen reporting to Helpline 1930 (NCRP) and Chakshu.
- **Repository**: https://github.com/uncoalesced/chakravyuh (Open Source under MIT License)
- **Track**: AI & Robotics
- **Stream**: Stream 1 — AI: Intelligent Real-World Assistance

---

## 2. Inspiration & Problem Statement

Voice social engineering is among the fastest-growing attack vectors in India. Fraudsters exploit fear and urgency through synthetic scenarios—such as imminent electricity cutoffs, fictitious parcel seizures, and fake digital arrests—coercing vulnerable citizens, especially senior citizens, into hasty transfers.

Over ₹1,750 crore was lost to cyber fraud in the first four months of 2024. (Source: Ministry of Home Affairs, Rajya Sabha unstarred question no. 1475, answered 7 August 2024).

While robust reporting platforms exist (Helpline 1930 / NCRP under I4C, and Chakshu on Sanchar Saathi under DoT), victims under psychological duress rarely capture the fleeting technical coordinates dictated over the phone. Meanwhile, attackers face near-zero marginal cost per call. Chakravyuh bridges this gap with an active defensive layer that absorbs the pressure, preserves structured evidence, and drains the scammer's time.

---

## 3. What Chakravyuh Does

When routed an incoming suspicious call, Chakravyuh acts autonomously without human intervention:

1. **Autonomous Persona De-escalation**:
   Adopts an elderly persona ("Raghunath") who appears cooperative but technologically fumbling (feigning trouble reading tiny text or locating glasses), systematically stretching the call duration.
2. **Deterministic Strategic Stepper**:
   A 5-stage finite state machine (`PANIC` &rarr; `STALLING` &rarr; `BAITING` &rarr; `EXTRACTING` &rarr; `WRAPUP`) guides the interaction. The agent steers the scammer into repeatedly dictating payment coordinates.
3. **High-Precision Multi-Dialect Extraction**:
   Extracts and normalizes conversational Hinglish and Indian English speech artifacts into syntax-validated coordinates:
   - **UPI VPAs**: Cleans spoken patterns (*"case dot verify at the rate ybl"* &rarr; `case.verify@ybl`).
   - **Bank Accounts & IFSC**: Normalizes spelled bank codes and spoken digits (*"K K B K zero zero zero four five six seven"* &rarr; `KKBK0004567`).
   - **Phone Numbers**: Formats 10-digit Indian numbers (*"nine eight seven six..."* &rarr; `+919876543210`).
   - **Malicious APKs & Links**: Flags suspicious domains and Android package downloads.
4. **Structured Incident Dossier (`chakravyuh.report/v1`)**:
   Outputs a structured incident report ready for user review and official filing.
5. **Real-Time Visual Monitoring**:
   A lightweight React + Vite dashboard streams live turn-by-turn transcripts, extracted identifiers, state progression, and an illustrative time-wasted metric with a prominent **[SIMULATED]** badge.

---

## 4. Technical Architecture & Implementation

Chakravyuh is built for total consumer hardware autonomy with **zero cloud dependencies** and **no call audio sent to external servers**:

- **Acoustic Frontend & Endpointing**:
  - **Silero VAD**: Low-latency voice activity detection tuned for 600ms pauses to preserve dictated digits without mid-utterance clipping.
  - **Playback Queue with Barge-In**: Instant playback cancellation (<100ms) if the scammer interrupts persona speech.
- **Speech Recognition (STT)**:
  - **faster-whisper**: Configured on CUDA with `float16` precision for real-time Hinglish decoding (STT latency p50: **382 ms** on consumer laptop GPU).
- **Core Reasoning Engine**:
  - Deterministic state machine safeguards against prompt injection or hallucinated credentials.
  - Optional local LLM wording via **Ollama (Qwen2.5 7B Q4)** with instant streaming or pre-cached natural responses.
- **Speech Synthesis (TTS)**:
  - **Piper TTS**: Local ONNX synthesis producing natural Indian accents (`hi_IN-rohan` for Hindi, `en_GB-alan` for Indian English).
  - Pre-synthesized endpoint fillers (*"Yes, yes..."*) reduce perceived turn gaps to **641 ms**.
- **Hardware & Telephony Bridge**:
  - WebSocket-based duplex audio line adapter supporting virtual simulation harnesses and physical 3.5mm TRRS line adapters.

---

## 5. Measured Benchmarks & Performance

Every benchmark metric is ground-truthed and logged via automated test harnesses:

- **Target Machine**: Consumer Laptop (AMD Ryzen + NVIDIA GeForce RTX 5050 Laptop GPU, 8GB VRAM)
- **Call Completion**: 11/11 turns answered autonomously (100% completion rate)
- **Caller-Perceived Turn Gap**: **p50 = 641 ms**, **p90 = 657 ms** (Well below the 1.2s conversation budget)
- **Speech-to-Text (CUDA float16)**: **p50 = 382 ms**, **p90 = 444 ms**
- **Test Suite**: 123 automated test cases passing (0 failures, 0 skips) across audio, FSM, extractors, and guardrails.

---

## 6. Guardrails, Ethics & Responsible AI

Our team operates under strict, test-enforced guardrails ([`docs/GUARDRAILS.md`](./GUARDRAILS.md)):

1. **No Institutional Criticism**: Government bodies, law enforcement, and regulatory agencies (I4C, DoT, NPCI, RBI) are respected partners. Chakravyuh explicitly complements official efforts.
2. **Format Verification Only**: Extracted identifiers are tagged as format-valid only; we never unilaterally label numbers or accounts as "confirmed fraud" or "mule accounts".
3. **No Retaliation / No Hack-Back**: The agent never scans remote IP addresses, detonates APKs, or harasses callers.
4. **Strict Local Privacy**: Audio is never written to disk or sent to cloud APIs. All models run 100% locally on the device.
5. **Synthetic Testing**: All benchmark and test scripts strictly use fictional organizations and reserved `.example` domains.

---

## 7. What We Learned & Future Vision

- **Audio Latency Optimization**: Conversational realism depends on immediate acoustic feedback. Combining Silero VAD endpointing with pre-synthesized conversational fillers effectively masks deep STT processing.
- **ASR Resilience**: Real scam interactions feature fast, noisy, and accented speech. Rule-based phonetic normalizers combined with grammar-guided extraction outperform naive regexes.
- **Future Roadmap**:
  - Expansion to regional languages (Kannada, Tamil, Telugu, Marathi).
  - Direct packaging for compact edge hardware (Raspberry Pi / Jetson).
  - One-click export integrations for standard NCRP and Chakshu citizen complaint forms.

---

## 8. Authors & Team Split

- **Joel Anthony** ([@uncoalesced](https://github.com/uncoalesced)): Core Engines (Persona FSM, Extraction Engine, Incident Reporting, LLM Adapter), Corpus A, Problem Definition & Submission Architecture.
- **Jammy** ([@jammy-007](https://github.com/jammy-007)): Audio Pipeline (Silero VAD, faster-whisper, Piper TTS, Barge-in, Fillers), Virtual Caller & Telephony Line Adapter, Dashboard Surface, Corpus B, Architecture Diagrams.
