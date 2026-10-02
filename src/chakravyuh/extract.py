# Engineered by uncoalesced
"""Pull payee/contact identifiers out of (possibly spoken, ASR-mangled) text.
Pure functions, stdlib only. Format validation only: we never claim an identifier is real or fraudulent."""
import re
from .contracts import Intel

_W = {"zero": 0, "shunya": 0, "sifar": 0, "one": 1, "ek": 1, "two": 2, "do": 2, "three": 3, "teen": 3,
      "four": 4, "char": 4, "chaar": 4, "five": 5, "paanch": 5, "panch": 5, "six": 6, "chhe": 6,
      "chheh": 6, "chhah": 6, "seven": 7, "saat": 7, "eight": 8, "aath": 8, "nine": 9, "nau": 9}
_MULT = {"double": 2, "triple": 3, "dabal": 2}
_DEVA = str.maketrans("०१२३४५६७८९", "0123456789")
_E = rf"(?:(?:(?:double|triple|dabal)[\s,\-]+)?(?:{'|'.join(_W)})\b|\d+)"
_RUN = re.compile(rf"\b{_E}(?:[\s,.\-]+{_E})*", re.I)

# Partial lists on purpose: unknown values are still captured, just flagged valid=False.
_PSP = set("""okaxis okhdfcbank okicici oksbi ybl ibl axl paytm apl upi fbl sbi hdfcbank icici axisbank pnb
ptyes ptsbi pthdfc ptaxis airtel freecharge jio postbank kotak yesbank idfcbank indus aubank unionbank
barodampay cnrb boi cbin ikwik""".split())
_BANKS = set("""SBIN HDFC ICIC UTIB PUNB KKBK BARB CNRB IDIB YESB IDFB INDB UBIN MAHB CBIN FDRL AUBL BKID IOBA
SCBL KARB SIBL RATN TMBL DLXB CIUB JAKA""".split())

_UPI = re.compile(r"(?<![\w.\-@])([A-Za-z0-9][\w.\-]{2,48})(?:\s*(@)\s*|\s+at\s+the\s+rate(?:\s+of)?\s+|\s+at\s+)"
                  r"([A-Za-z][A-Za-z0-9]{1,30})(?![\w]|\.[A-Za-z])", re.I)
_STOP = {"id", "upi", "ids", "the", "and"}
_SEP = r"[\s,.\-]*"
_IFSC = re.compile(rf"(?<![A-Za-z0-9])((?:[A-Za-z]{_SEP}){{4}})0{_SEP}((?:[A-Za-z0-9]{_SEP}){{6}})(?![A-Za-z0-9])")
_NUM = re.compile(r"\+?\d[\d\s\-]{6,}\d")
_NOT_ACCOUNT = re.compile(r"utr|ref|transaction|otp|pin", re.I)
_URL = re.compile(r"https?://[^\s<>\"']+|\b(?:bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|is\.gd)/[^\s<>\"']+", re.I)
_APK = re.compile(r"(?<![/\w\-.])[\w\-]+\.apk\b", re.I)


def speech_digits(text: str) -> str:
    """'nine eight seven six' -> '9876', 'double nine' -> '99'. Runs under 4 digits are left alone
    so ordinary words ('ek second', 'do not') survive."""
    def fix(m):
        s = m.group()
        if not re.search(r"[A-Za-z]", s):
            return s
        d, mult = "", 1
        for w in re.findall(r"[A-Za-z]+|\d+", s):
            lw = w.lower()
            if lw in _MULT: mult = _MULT[lw]
            elif lw in _W: d += str(_W[lw]) * mult; mult = 1
            else: d += w
        return d if len(d) >= 4 else s
    return _RUN.sub(fix, text.translate(_DEVA))


def _upi(t, add):
    for m in _UPI.finditer(t):
        local, at, psp = m.group(1).lower(), m.group(2), m.group(3).lower()
        if not at and (psp not in _PSP or local in _STOP or not re.search(r"[a-z]", local)):
            continue   # spoken "at" only counts when the right side is a known UPI handle
        add("upi", f"{local}@{psp}", psp in _PSP, "" if psp in _PSP else "handle not in known list")


def _ifsc(t, add):
    for m in _IFSC.finditer(t):
        code = re.sub(r"[^A-Za-z0-9]", "", m.group(1)).upper() + "0" + re.sub(r"[^A-Za-z0-9]", "", m.group(2)).upper()
        if len(code) == 11:
            ok = code[:4] in _BANKS
            add("ifsc", code, ok, "" if ok else "bank code not in known list")


def _numbers(t, add):
    for m in _NUM.finditer(t):
        raw = re.sub(r"\D", "", m.group())
        ctx = t[max(0, m.start() - 40):m.start()]
        p = raw[2:] if len(raw) == 12 and raw.startswith("91") else raw[1:] if len(raw) == 11 and raw[0] == "0" else raw
        if len(p) == 10 and p[0] in "6789" and not re.search(r"account|a/c|khata", ctx, re.I):
            add("phone", "+91" + p, True)
        elif 9 <= len(raw) <= 18 and not _NOT_ACCOUNT.search(ctx):
            add("account", raw, True, "format only, not verified")


def _urls(t, add):
    for m in _URL.finditer(t):
        v = m.group().rstrip(".,;:)!?")
        add("apk" if v.lower().endswith(".apk") else "url", v, True)
    for m in _APK.finditer(t):
        add("apk", m.group(), True)


def extract(text: str, ts: float = 0.0) -> list:
    out = {}
    def add(kind, value, valid, note=""):
        out.setdefault((kind, value), Intel(kind, value, valid, note, ts))
    for t in (text, speech_digits(text)):
        _upi(t, add); _ifsc(t, add); _numbers(t, add); _urls(t, add)
    return list(out.values())


class Extractor:
    """Rolling extractor: feed final transcripts in order; returns only intel not seen before.
    Keeps the previous utterance as a tail so an identifier split across two chunks still matches."""
    def __init__(self):
        self.seen, self._tail = {}, ""

    def feed(self, text: str, ts: float = 0.0) -> list:
        blob, self._tail = f"{self._tail} {text}".strip(), text
        new = [i for i in extract(blob, ts) if (i.kind, i.value) not in self.seen]
        for i in new:
            self.seen[(i.kind, i.value)] = i
        return new

    @property
    def all(self) -> list:
        return list(self.seen.values())
