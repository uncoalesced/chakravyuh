# Engineered by uncoalesced
"""Deterministic persona state machine. The FSM owns *what the persona is trying to do*; the LLM (optional)
only words it. Anything the LLM says is filtered, and a scripted line takes over if it fails or misbehaves.
Synchronous: call from one worker thread. The persona is fictional and never gives out real data."""
import re
from enum import Enum
from .contracts import Reply
from .extract import Extractor


class State(str, Enum):
    PANIC = "PANIC"            # fear + compliance
    STALLING = "STALLING"      # operational friction, burns the caller's time
    BAITING = "BAITING"        # feigns willingness to pay, asks for payee details
    EXTRACTING = "EXTRACTING"  # asks for slow repeats and spellings
    WRAPUP = "WRAPUP"          # hands the phone to "my son" and ends


_PAY = re.compile(r"\b(pay\w*|transfer|send|upi|scan|amount|rupees?|rupaye|paisa|bhej\w*|app|link|account|khata)\b|₹", re.I)
_BOT = re.compile(r"\b(bot|robot|recorded|recording|machine)\b|\bAI\b")
_RAIL = ("upi", "account", "ifsc")

LINES = {
    "en": {
        "PANIC": ["Arre sir please, do not do that na! I am an old man, my wife is not well. What should I do baba?",
                  "Sir please, I am a retired teacher only, living on my pension. Tell me properly what to do na, don't shout."],
        "STALLING": ["Arey ek minute sir, my spectacles only I am not finding... where did I keep, wait wait.",
                     "Screen is so small pa, nothing is visible to my eyes. Wait na, why you are getting angry?",
                     "Hello? Hello? Arey your voice is cracking sir, say slowly na, line is bad.",
                     "Arey internet is simply circling circling sir, wait wait, doing doing."],
        "BAITING": ["Haan sir, I will pay only, don't block. But tell clearly na, to which UPI ID to send? Say slowly-slowly, I am writing with pen.",
                    "Which account sir? Tell the account number and IFSC bank code na, pen is in my hand now."],
        "EXTRACTING": ["Arey wait sir, let me read back what I wrote... say it once more na, letter by letter, my handwriting is shaky.",
                       "Is that the same name as on the bill ah sir? Please say the ID one more time na.",
                       "Arey some error it is showing sir, tell me the full details again na."],
        "STALLING_2": ["Aiyyo sir, payment is showing failed only... let me try once again, wait ek minute.",
                       "App is asking something-something sir, wait, where are my glasses..."],
        "BAITING_2": ["Arey baba, it says daily limit exceeded! Give any other UPI ID na, or account number and IFSC code?"],
        "WRAPUP": ["Sir, my son has come home just now, he wants to talk to you. Wait ek minute..."],
        "DEFLECT": ["What bot ya? I am Raghunath only! Speak loudly na, my hearing is weak."],
    },
    "hi": {
        "PANIC": ["Arre baap re, sahab please aisa mat kijiye! Main budha aadmi hoon, meri patni bimaar hai. Ab main kya karun?",
                  "Sahab please, main retired teacher hoon, sirf pension pe jeeta hoon. Bataiye kya karun?"],
        "STALLING": ["Ek minute sahab, mera chashma nahi mil raha... dhoondhne do.",
                     "Phone ki screen bahut chhoti hai sahab, kuch dikhta nahi. Ruko zara.",
                     "Hello? Hello? Aawaaz kat rahi hai sahab, dheere dheere phir se boliye.",
                     "Internet ghoom raha hai sahab, ruko ruko."],
        "BAITING": ["Theek hai sahab, main paisa bhejta hoon. Bas saaf saaf bataiye, kis UPI ID par bhejna hai? Dheere boliye, main pen se likh raha hoon.",
                    "Account number aur IFSC code bataiye sahab, main likh leta hoon."],
        "EXTRACTING": ["Ruko sahab, jo likha hai wo dohra deta hoon... ek baar phir se boliye, ek-ek akshar karke.",
                       "Ye naam wahi hai jo bill pe hai na sahab? ID ek baar aur boliye.",
                       "Kuch error aa raha hai sahab, poori detail phir se bataiye."],
        "STALLING_2": ["Sahab payment fail dikha raha hai... ruko, phir se try karta hoon.",
                       "App kuch pooch raha hai sahab, ruko, chashma..."],
        "BAITING_2": ["Sahab limit exceed bol raha hai. Koi aur UPI ID hai, ya account number aur IFSC bata dijiye?"],
        "WRAPUP": ["Sahab, mera beta abhi ghar aaya hai, wo aapse baat karna chahta hai. Ek minute..."],
        "DEFLECT": ["Kaunsa bot sahab? Main Raghunath hi hoon. Zara zor se boliye, kaan se kam sunta hoon."],
    },
}

_DIRECTIVE = {
    State.PANIC: "Show fear and eagerness to comply. Ask what you should do.",
    State.STALLING: "Create small, believable delays (glasses, tiny screen, slow internet, bad line). Stay cooperative.",
    State.BAITING: "Say you are ready to pay. Ask the caller to read out the exact UPI ID, or account number and bank code, slowly.",
    State.EXTRACTING: "Ask the caller to repeat or spell the details letter by letter, as if writing them down. Never confirm them as correct.",
    State.WRAPUP: "Say your son has come home and wants to talk, then stop.",
}

_PERSONA = ("You are Raghunath, a fictional 68-year-old retired schoolteacher in Bengaluru, a little hard of hearing, "
            "unfamiliar with phone payments. You are on a phone call. Rules: speak {lang}, at most two short sentences, plain text only, "
            "no emojis, no digits. Never reveal you are an AI or a program. Never give any real personal, banking or card detail, "
            "never read out an OTP or PIN, never install anything, never actually send money. Do not insult the caller. "
            "Current goal: {goal}")
_LANG = {"en": "Indian English", "hi": "Hinglish (Hindi written in Roman script)"}


def _clean(out):
    """Return a speakable line, or None if the LLM output must not be spoken."""
    out = " ".join((out or "").split())
    if not out or len(out.split()) > 60 or re.search(r"\d{4,}|otp|http|as an ai|language model|i am an ai", out, re.I):
        return None
    return out


class PersonaFSM:
    def __init__(self, lang="en", llm=None, *, stall_turns=1, extract_turns=2, max_rounds=2,
                 max_turns=40, max_seconds=600):
        self.lang, self.llm = lang if lang in LINES else "en", llm
        self.stall_turns, self.extract_turns, self.max_rounds = stall_turns, extract_turns, max_rounds
        self.max_turns, self.max_seconds = max_turns, max_seconds
        self.state, self.state_turns, self.rounds, self.turns = State.PANIC, 0, 0, 0
        self.t0 = self.last_ts = None
        self.history, self.extractor, self._used = [], Extractor(), {}

    def on_scammer_turn(self, text: str, ts: float) -> Reply:
        self.t0 = ts if self.t0 is None else self.t0
        self.last_ts, self.turns = ts, self.turns + 1
        new = tuple(self.extractor.feed(text, ts))
        self.history.append({"role": "user", "content": text})
        if _BOT.search(text) and self.state != State.WRAPUP:
            line = self._scripted("DEFLECT")
        else:
            self._advance(text, new)
            line = self._llm_line() or self._scripted(self._pool())
        self.state_turns += 1
        self.history.append({"role": "assistant", "content": line})
        return Reply(line, self.state.value, new, self.state == State.WRAPUP)

    def on_barge_in(self):
        """Audio layer cut the persona off mid-sentence: keep the LLM context honest."""
        if self.history and self.history[-1]["role"] == "assistant":
            self.history[-1]["content"] += " [interrupted]"

    def elapsed(self) -> float:
        return 0.0 if self.t0 is None else self.last_ts - self.t0

    def _go(self, s):
        self.state, self.state_turns = s, 0

    def _advance(self, text, new):
        if self.state == State.WRAPUP:
            return
        if self.turns >= self.max_turns or self.elapsed() >= self.max_seconds:
            return self._go(State.WRAPUP)
        pay, rails = bool(_PAY.search(text)), any(i.kind in _RAIL for i in new)
        for _ in range(3):   # chained transitions allowed within one turn
            s, n = self.state, self.state_turns
            if s == State.PANIC and n >= 1 and (pay or n >= 2):   # always show fear for at least one turn
                self._go(State.STALLING)
            elif s == State.STALLING and ((pay and n >= self.stall_turns) or n >= self.stall_turns + 3):
                self._go(State.BAITING)
            elif s == State.BAITING and rails:
                self._go(State.EXTRACTING)
            elif s == State.EXTRACTING and n >= self.extract_turns:
                self.rounds += 1
                self._go(State.WRAPUP if self.rounds >= self.max_rounds else State.STALLING)
            else:
                break

    def _pool(self):
        return self.state.value + ("_2" if self.rounds and self.state in (State.STALLING, State.BAITING) else "")

    def _scripted(self, pool):
        lines = LINES[self.lang][pool]
        i = self._used.get(pool, 0)
        self._used[pool] = i + 1
        return lines[i % len(lines)]

    def _llm_line(self):
        if not self.llm or self.state == State.WRAPUP:
            return None
        system = _PERSONA.format(lang=_LANG[self.lang], goal=_DIRECTIVE[self.state])
        try:
            return _clean(self.llm(system, self.history[-12:]))
        except Exception:   # any LLM/network failure falls back to the script; the call must never go silent
            return None
