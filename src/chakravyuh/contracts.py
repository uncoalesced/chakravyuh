# Engineered by uncoalesced
"""Message shapes shared by every module. Plain dataclasses -> dicts -> JSON.
Frozen in docs/CONTRACTS.md: change both together, in one PR, reviewed by both owners."""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Intel:
    kind: str          # upi | account | ifsc | phone | url | apk
    value: str         # normalised
    valid: bool        # format-valid only. NEVER means "verified real" or "confirmed fraudulent"
    note: str = ""
    ts: float = 0.0

    def to_event(self) -> dict:
        return {"type": "intel", **asdict(self)}


@dataclass(frozen=True)
class Reply:
    text: str
    state: str
    new_intel: tuple = ()
    end_call: bool = False

    def to_event(self) -> dict:
        return {"type": "speak", "text": self.text, "state": self.state,
                "end_call": self.end_call, "intel": [asdict(i) for i in self.new_intel]}
