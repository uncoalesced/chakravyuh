# Engineered by uncoalesced
import json, pathlib

CORPUS = pathlib.Path(__file__).parent.parent / "corpus"


def load(name):
    return json.loads((CORPUS / f"{name}.json").read_text(encoding="utf-8"))


def replay(script, fsm):
    """Feed a corpus script through an FSM; return the replies."""
    return [fsm.on_scammer_turn(t["text"], t["t"]) for t in script["turns"]]
