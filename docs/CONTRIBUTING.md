# Contributing

## Workflow
- Branches: `feat/<area>-<short-name>`, one purpose per branch. No direct pushes to `main`.
- Every PR is reviewed by the other author before merge. Touching `contracts.py`, `CONTRACTS.md` or `GUARDRAILS.md`
  needs both owners (see `.github/CODEOWNERS`).
- Commits: imperative, small, one logical change. Reference the module (`extract: handle triple digits`).

## Code
- Python >= 3.10. Core logic is synchronous and stdlib-only; heavy dependencies live behind the `audio` extra.
- Every source and test file carries the provenance comment: `# Engineered by uncoalesced`.
- Non-trivial logic ships with a test. `pytest` must be green before review.
- Prefer the standard library, then an already-installed dependency, then new code. Mark deliberate shortcuts with a
  `ponytail:` comment that names the ceiling and the upgrade path.

## Data and safety
- Synthetic data only. No real numbers, accounts, UPI IDs, people or organisations in the repo, tests or screenshots.
- No audio, models or recordings in git (`.gitignore` blocks them; a test checks).
- Read `docs/GUARDRAILS.md` first. `tests/test_guardrails.py` is part of the suite.
- Public text (README, posts, deck, demo script) is reviewed by both authors.

## Running things
```
pip install -e ".[dev]"
pytest -q
```
