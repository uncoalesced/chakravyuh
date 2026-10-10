# Problem Definition: The Voice Scam Asymmetry in India

## 1. Executive Summary
Voice-based social engineering has emerged as one of the most pervasive cyber threats in India. Scammers routinely deploy high-pressure telephone scripts—such as imminent electricity disconnections, fictitious parcel seizures, and fraudulent banking blocks—to induce panic and extort immediate payments. Senior citizens and non-technical individuals are disproportionately targeted due to unfamiliarity with digital payment interfaces and procedural safeguards.

While official authorities maintain robust reporting mechanisms, a fundamental operational bottleneck persists: in high-stress phone calls, targeted citizens rarely record the fleeting technical identifiers (UPI VPAs, mule bank accounts, IFSC codes, calling numbers, and malicious APK URLs) needed by law enforcement to take corrective action.

Chakravyuh addresses this challenge by providing an autonomous, privacy-preserving voice agent that answers suspicious incoming calls, absorbs the scammer's pressure, wastes their operational capital, extracts structured identifiers, and compiles a clean incident dossier for citizen review and manual submission through official channels.

---

## 2. The Nature of the Threat

### 2.1 The Attack Vector: High-Urgency Social Engineering
Unlike technical phishing or malware distribution, voice social engineering relies entirely on behavioral manipulation:
- **Urgency and Coercion**: Callers demand immediate action within minutes (e.g., "pay within 30 minutes or power will be disconnected at 9:00 PM").
- **Impersonation**: Callers pose as utility boards, logistics desks, or regulatory authorities.
- **Linguistic Fluidity**: Scammers operate across colloquial Indian English, Hindi, and regional dialects (Hinglish), fluidly mixing technical jargon with authoritative commands.

### 2.2 Magnitude of the Problem
The scale of digital financial fraud has expanded significantly with the rapid adoption of instant retail payments. Over ₹1,750 crore was lost to cyber fraud in the first four months of 2024. (Source: Ministry of Home Affairs, Rajya Sabha unstarred question no. 1475, answered 7 August 2024).

---

## 3. The Current Defensive Landscape

### 3.1 Official Reporting Infrastructure
The Government of India has established comprehensive response infrastructure:
- **National Cyber Crime Reporting Portal (NCRP) & Helpline 1930**: Operated by the Indian Cyber Crime Coordination Centre (I4C) under the Ministry of Home Affairs, facilitating rapid lien-marking on suspicious beneficiary accounts.
- **Chakshu & Sanchar Saathi**: Administered by the Department of Telecommunications (DoT) to report suspected fraudulent communications and blacklist calling numbers and IMEI devices.

### 3.2 The Operational Gap
While these reporting channels are well-established, citizen participation is often hindered by the frantic nature of live scam interactions:
1. **Intel Evaporation**: Victims subjected to psychological pressure focus on de-escalation rather than evidence preservation. Phone numbers, UPI IDs, and bank account numbers read over the phone are forgotten once the call ends.
2. **Zero Opportunity Cost for Attackers**: Scammers operate with near-zero marginal cost per call. A scammer can place dozens of calls daily, abandoning unproductive calls instantly without friction.
3. **Complementary Active Defense**: Public awareness campaigns provide vital educational guidance. Chakravyuh complements awareness efforts with an active layer that engages scammers directly during the call, converting wasted human time into structured evidence.

---

## 4. Chakravyuh's Solution Architecture

Chakravyuh functions as an autonomous counter-agent with four core responsibilities:

1. **Psychological De-escalation & Time Sinks**:
   The agent adopts an adaptive elderly persona ("Raghunath") who appears compliant but technologically challenged. By fumbling for glasses, struggling with screen text, and requesting slow repetition, the agent consumes valuable scammer time.

2. **Targeted Identifier Extraction**:
   While feigning readiness to pay, the persona prompts the scammer to provide actionable payment coordinates:
   - UPI Virtual Payment Addresses (VPAs).
   - Bank Account Numbers and IFSC codes.
   - Calling and callback telephone numbers.
   - Malicious APK download links and domain shorteners.

3. **Format Validation & Noise Resilience**:
   An extraction engine normalizes Indian English and Hindi speech artifacts (e.g., spoken digits, transliterated numbers, "at the rate" phrasing, and ASR homophones), validating identifier syntax against RBI and NPCI standards.

4. **Structured Incident Dossier**:
   Upon call conclusion, Chakravyuh outputs a structured report (`chakravyuh.report/v1`) containing:
   - Chronological call transcript and duration metrics.
   - Format-validated technical identifiers.
   - Pre-formatted submission fields for review and manual reporting to NCRP (1930) and Chakshu.

---

## 5. Ethical Principles and System Boundaries

- **Complementary Public Mission**: Official institutions (I4C, DoT, NPCI, RBI) are the intended destinations of generated dossiers. The system does not claim institutional failure or bypass statutory workflows.
- **Strict Privacy**: The entire stack runs locally on consumer hardware (faster-whisper, Silero VAD, Ollama Qwen2.5, Piper TTS). No call audio leaves the device; audio is not recorded to disk by default.
- **No Retaliation**: The agent does not probe remote servers, detonate external APKs, or initiate hostile interactions.
- **Format-Only Verification**: Extracted data is strictly checked for syntax compliance. Identifiers are never labeled as "confirmed fraud" without official adjudication.
