# Guardrails

These rules protect the project, its authors and the people it is meant to help. They apply to code, docs,
demo scripts, the pitch deck and every public post. `tests/test_guardrails.py` enforces the mechanical ones.
Both authors review any public statement before it goes out.

## 1. Government and institutions are partners, never a foil
- I4C and helpline 1930, the National Cyber Crime Reporting Portal, Chakshu and Sanchar Saathi, NPCI and RBI appear
  only as the channels our reports are prepared for.
- No claim that any authority, programme or campaign has failed, is slow, or is inadequate. No political framing of any kind.
- Approved framing: "Chakravyuh complements awareness efforts with an active layer."
  "Prepared for review and submission through the official channels."
- Not allowed: "awareness campaigns have failed", "the system is broken", or any variation.

## 2. No real organisations or people in scripts
- Simulated scammer scripts and persona lines use fictional organisations only (for example "Sunrise Power Board",
  "Swift Parcel Express"). No real agency, official, utility, courier, bank or brand speaks as a scammer.
- All identifiers in the repo are synthetic: UPI IDs, accounts, numbers, links (reserved `.example` domains).
- The lint rejects a short list of real agency names inside `corpus/` and `fsm.py`.

## 3. Numbers need sources
- Any statistic about losses, victims or crime carries a citation with publisher and date on the same line ("Source: ...").
  The lint rejects an unsourced line that mentions "crore".
- Pitch lines are derived from cited official figures or are left out. No invented "while you were sitting here" tallies.
- Demo counters are labelled illustrative or simulated on screen.

## 4. Claims we can defend
- Reports are exports for a person to review and submit. We never say "automatically filed" or "dispatched".
- Extraction is format validation. We never say an identifier is "a mule account", "confirmed fraud" or "verified".
- Latency figures come from the measurement harness. Anything simulated says so.

## 5. No retaliation, no exposure
- No hack-back, no scanning or probing of caller infrastructure, no logging of a caller's connection details,
  no contacting or confronting identified people, no public naming of captured numbers or accounts.
- Out of scope by decision: voiceprint matching, APK detonation, remote-access capture, SIP-header analysis.

## 6. Privacy by default
- No call audio is stored by default. Transcripts stay local and only when explicitly enabled.
- Captured identifiers are personal data of third parties; keep them local, minimal and deletable.
- Only the owner's own line is used. Deployment beyond a demo needs a legal review first. This project is not legal advice.

## 7. Tone
- Neutral and factual. We describe what the software does and what it does not do.
- Review checklist for any public text: (1) names a real institution in a negative light? (2) unsourced number?
  (3) overclaims what the system verified or filed? (4) names a real person or brand? If yes to any, rewrite.
