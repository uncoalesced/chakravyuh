# Engineered by uncoalesced
"""Lint for docs/GUARDRAILS.md. Narrative rules are enforced by a test, not by good intentions."""
import pathlib, re

ROOT = pathlib.Path(__file__).parent.parent
PROSE = [ROOT / "README.md", *(ROOT / "docs").glob("*.md"), *(ROOT / "src").rglob("*.py"), *(ROOT / "corpus").glob("*")]
SKIP = {"GUARDRAILS.md"}   # that file quotes the banned phrases on purpose

CRITICISM = re.compile(r"\b(has|have) failed\b|failed to protect|incompeten|corrupt|negligen|anti-national|useless", re.I)
REAL_AGENCY = re.compile(r"\b(CBI|NCB|TRAI|Enforcement Directorate|Income Tax|FedEx|DHL|BESCOM|Delhi Police|Mumbai Police|Customs Department)\b")
MONEY_STAT = re.compile(r"\bcrore\b", re.I)


def files():
    return [p for p in PROSE if p.is_file() and p.name not in SKIP]

def test_there_is_something_to_lint():
    assert len(files()) >= 8

def test_no_criticism_or_institutional_failure_claims():
    bad = [(p.name, m.group()) for p in files() for m in CRITICISM.finditer(p.read_text(encoding="utf-8"))]
    assert not bad, bad

def test_persona_and_corpus_name_no_real_agencies_or_brands():
    scoped = [p for p in files() if p.parent.name == "corpus" or p.name == "fsm.py"]
    bad = [(p.name, m.group()) for p in scoped for m in REAL_AGENCY.finditer(p.read_text(encoding="utf-8"))]
    assert not bad, bad

def test_money_statistics_carry_a_source_on_the_same_line():
    bad = [(p.name, ln.strip()[:60]) for p in files() for ln in p.read_text(encoding="utf-8").splitlines()
           if MONEY_STAT.search(ln) and "Source:" not in ln]
    assert not bad, bad

def test_no_audio_or_models_committed():
    assert not [p for p in ROOT.rglob("*") if ".git" not in p.parts and p.suffix in {".wav", ".mp3", ".gguf"}]
