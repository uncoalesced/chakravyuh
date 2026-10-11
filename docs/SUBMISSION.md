# Submission checklist

Source: official event pages read on 2 Oct 2026: https://next-gen-hackathon.devpost.com/ , its `/rules` page,
https://nextgenexpo.raaif.org/ and https://nextgenexpo.raaif.org/hack-ai-robotics.html . Re-read before submitting;
pages can change.

## Where we fit
Track **AI & Robotics**, innovation option **Stream 1: AI - Intelligent Real-World Assistance** (software or hardware
AI solution using, among others, Speech AI, Agentic AI or multimodal LLMs, addressing practical challenges including
public services). Chakravyuh is a speech-and-agent system that assists people targeted by scam calls.

## Facts from the pages
- Event: 23-25 Oct 2026, Tripura Vasini Palace Grounds, Bengaluru. Organiser: RAAIF.
- Deadline: 23 Oct 2026, 5:00 pm IST (Devpost).
- Team size: 2 to 4 on Devpost ("1 - 4" on the track page). We are 2.
- Eligibility: "Colleges & Startups" on the track page; "ALL students" on the rules page.
- Judging focus: innovation, problem relevance, technical implementation, functionality, real-world impact.
  Stream 1 also lists: meaningful use of ML or LLM reasoning, operational reliability, real-world applicability.
- Judges named on Devpost: Dr. Arun Janarthanan (HCL Tech), Latha Rajinikanth (The Ashram).
- The Devpost blurb says "registration from off web is neccessary" [sic].

## Required deliverables -> where they come from
| Required | Our artifact | Status |
|---|---|---|
| Working physical prototype, or simulation with a physical interface | Virtual caller simulation with speaker monitor (`python dashboard/server.py --demo kyc_block --loop --speakers`); phone cable optional fallback | done |
| Problem definition document | `docs/PROBLEM.md` (Joel) | done |
| System architecture diagram | `docs/diagrams/architecture.png` (source `.svg`) | done |
| AI framework / data-loop diagram | `docs/diagrams/data-loop.png` (source `.svg`) | done |
| Live demonstration of autonomous task completion | `python dashboard/server.py --demo kyc_block --loop --speakers`; script in `docs/DEMO_RUNBOOK.md` | ready, rehearse |
| Devpost project page, video, repo link | `docs/DEVPOST.md` (submission text, pitch narrative, architecture summary) | done |

## Actions that need a human
- [ ] Complete **both** registrations: the Devpost registration and the official offline/web registration form at nextgenexpo.raaif.org.
- [ ] The registration form asks for "Startup Founder/Representative" or "College/Academic Team Leader". Joel and Jammy attend different
      colleges: ask the organisers which is correct for a two-college team.
- [ ] Ask the organisers (info@raaif.org, +91 97909 63640) for what the pages do not say: registration fee, demo format and time slot,
      power and table setup, whether open-source code and AI tools are allowed, whether a laptop speaker and a phone on stage are fine.
- [ ] Confirm whether the repo may be public before the event (we plan to open it after the project is done).
