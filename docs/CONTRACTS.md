# Contracts

The seam between Joel's core and Jammy's audio and dashboard. Change this file and `src/chakravyuh/contracts.py`
together, in one PR, reviewed by both. Version: `v1`.

## Core API (Python, synchronous, single worker thread)

```python
from chakravyuh.fsm import PersonaFSM
from chakravyuh.llm import ollama_llm

core = PersonaFSM(lang="hi", llm=ollama_llm())      # lang: "en" | "hi"; llm optional (scripted fallback)

reply = core.on_scammer_turn(text, ts)               # text: one final, endpointed utterance; ts: seconds (float)
reply.text        # what the persona says (plain text, no digits, <= ~40 words)
reply.state       # "PANIC" | "STALLING" | "BAITING" | "EXTRACTING" | "WRAPUP"
reply.new_intel   # tuple[Intel] first seen this turn
reply.end_call    # True -> speak reply.text, then hang up

core.on_barge_in()   # call when the caller cut the persona off mid-sentence
core.elapsed()       # seconds engaged so far
```

Rules for the audio side:
- Send **final** transcripts only (after VAD endpointing). Partials are for the dashboard, not the core.
- `ts` must be monotonic within a call.
- If the core takes too long, play a pre-cached filler locally; do not call the core twice for one utterance.
- Never call the core from two threads.

## Events (JSON, for the dashboard feed)

Every event has `"type"`. Times are seconds since call start unless noted.

| Event | Producer | Shape |
|---|---|---|
| `transcript` | audio | `{"type":"transcript","speaker":"scammer"\|"persona","text":"...","final":true,"ts":12.4}` |
| `speak` | core (`Reply.to_event()`) | `{"type":"speak","text":"...","state":"BAITING","end_call":false,"intel":[Intel...]}` |
| `intel` | core (`Intel.to_event()`) | `{"type":"intel","kind":"upi","value":"quickbillpay98@axl","valid":true,"note":"","ts":40.0}` |
| `metrics` | dashboard backend, 1 Hz | `{"type":"metrics","engaged_s":71.2,"illustrative_cost_inr":47.5,"simulated":true}` |
| `report` | core (`build_report`) | the full report object, see below |

`kind` is one of `upi | account | ifsc | phone | url | apk`. `valid` means *format-valid only*.
The dashboard must show the "simulated" tag on the cost counter and on any resolver lookup.

## Report (`chakravyuh.report/v1`)

```json
{
  "schema": "chakravyuh.report/v1",
  "generated_at": "2026-10-22T18:30:00+05:30",
  "simulated_session": true,
  "call": {"duration_s": 130.0, "turns": 10, "final_state": "WRAPUP", "scam_type": "electricity_disconnection", "language": "hi"},
  "intel": [{"kind": "upi", "value": "quickbillpay98@axl", "valid": true, "note": "", "ts": 40.0}],
  "metrics": {"engaged_seconds": 130.0, "rate_inr_per_min": 40.0, "illustrative_cost_inr": 86.67, "cost_is_illustrative": true},
  "for_manual_submission": {"channels": ["..."], "chakshu_numbers": ["+91..."], "note": "..."}
}
```

## Audio source adapter (Jammy)

`AudioSource` is `src/chakravyuh/audio/source.py`; `AudioSink` is `Player` in `src/chakravyuh/audio/playback.py`.

```python
class Frame(NamedTuple):
    pcm: bytes           # 16 kHz mono PCM16, exactly frame_ms long (last frame zero-padded)
    ts: float            # seconds since stream start at the frame's first sample; feeds ScammerTurn ts / on_scammer_turn

class AudioSource:       # WavFileSource (done) | websocket virtual caller | phone cable
    def frames(self) -> Iterator[Frame]: ...      # default 20 ms; use frame_ms=32 for Silero's 512-sample window
class AudioSink:
    def play(self, pcm: bytes) -> None: ...
    def cancel(self) -> None: ...                 # barge-in: drop queued audio immediately
```

Frames carry a timestamp so the audio side derives `ts` from the stream, not the wall clock. That keeps `ts`
monotonic, and file replay gives the same result every run.

## Open questions
- ~~Does Piper's Hindi voice want Devanagari?~~ Yes: Roman input is read with English phonemes. The audio layer
  transliterates (`audio/translit.py`); the core stays Roman-script. Unlisted English words may be mispronounced.
- Where do pre-cached fillers live and who picks one (proposal: audio layer, per language)?
- Kannada: add `"kn"` to `LINES` and the language map once an STT/TTS pair is chosen.
