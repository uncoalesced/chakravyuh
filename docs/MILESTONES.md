# Milestones

Anchored to the real deadline: submission closes **23 Oct 2026, 5:00 pm IST** (event 23-25 Oct 2026, Tripura Vasini
Palace Grounds, Bengaluru). Read from the official Devpost page on 2 Oct 2026. Target: submit by noon IST on 23 Oct.
Plan written 2 Oct 2026; 21 days remain.

| Phase | Dates (IST) | Joel | Jammy | Exit check |
|---|---|---|---|---|
| 0 Foundation | Fri 2 - Sun 4 Oct | Extraction, FSM, report, corpus A, docs (done in scaffold) | Repo access, env setup (Python, Ollama, faster-whisper), audio-source adapter with file replay, STT benchmark on Hinglish clips | Suite green; Jammy runs it locally |
| 1 Components | Mon 5 - Fri 9 Oct | Persona prompts en/hi tuned on the real model, filter hardening, corpus A extended | VAD endpointing, streaming STT, Piper TTS, playback queue with barge-in cancel | Each part demoed standalone |
| 2 Vertical slice | Sat 10 - Wed 14 Oct | Metrics model, report wiring, LLM latency tuning | Dashboard + live event feed, virtual-caller source | Scripted caller -> persona -> intel on dashboard, end to end |
| 3 Real line | Thu 15 - Sun 18 Oct | Corpus A final, edge cases from real ASR output | Phone bridge (cable or fallback), latency harness, corpus B | Measured turn-gap p50 recorded; phone demo works once |
| 4 Polish + docs | Mon 19 - Wed 21 Oct | Problem-definition doc, pitch narrative | Architecture + data-loop diagram exports, demo runbook | All `SUBMISSION.md` items ticked; **code freeze Wed 21 Oct night** |
| 5 Buffer + submit | Thu 22 - Fri 23 Oct | Rehearsal, fixes only | Rehearsal, fixes only | Devpost submitted, offline registration confirmed |

Rehearse the live demo at least 20 times across phases 3-5. Daily 10-minute sync; blockers raised the same day.

## Risks
| Risk | Mitigation |
|---|---|
| Hinglish STT accuracy is poor | Benchmark in phase 0; the repeat-and-spell turns exist for this; try a larger Whisper model if VRAM allows |
| 8 GB VRAM pressure (Whisper + 7B Q4 + context) | Measure early; fall back to a smaller model or shorter context |
| Phone bridge is flaky | Virtual-caller source is the default demo path; the cable is a bonus. Record a fallback video |
| Latency above target | Quote the measured number; filler audio; sentence streaming if the harness says it matters |
| Hackathon rules unclear (fees, demo format, code policy) | Email the organisers this week (see `SUBMISSION.md`) |
| College exams or other commitments | Each person flags busy days now; phase 5 buffer absorbs one lost day |
