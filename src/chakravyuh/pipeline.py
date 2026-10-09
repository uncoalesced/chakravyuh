# Engineered by uncoalesced
"""End-to-end autonomous call pipeline.
Wired: AudioSource -> Endpointer -> STT -> PersonaFSM -> TTS -> Player (AudioSink).
Emits real-time event callbacks for dashboard/logging, and generates a structured incident report on call wrapup."""
from typing import Any, Callable, Optional

from chakravyuh.audio.playback import Player
from chakravyuh.audio.source import AudioSource
from chakravyuh.audio.stt import listen
from chakravyuh.audio.vad import Endpointer
from chakravyuh.fsm import PersonaFSM
from chakravyuh.report import build_report


def run_pipeline(
    source: AudioSource,
    endpointer: Endpointer,
    stt: Callable[[bytes], str],
    fsm: PersonaFSM,
    tts: Optional[Any] = None,
    player: Optional[Player] = None,
    *,
    simulated: bool = True,
    on_event: Optional[Callable[[dict], None]] = None,
) -> dict:
    """Run an autonomous scam call session from audio source frames through to the incident report.

    Args:
        source: AudioSource yielding Frame tuples.
        endpointer: Endpointer instance detecting speech onset and silence endpoints.
        stt: Callable taking PCM bytes and returning transcribed text.
        fsm: PersonaFSM tracking conversation state, generating persona replies, and extracting intel.
        tts: Optional TTS synthesizer (e.g. PiperTTS or callable) producing PCM byte chunks.
        player: Optional AudioSink/Player for non-blocking playback with barge-in cancellation.
        simulated: Flag indicating whether this session was simulated or live.
        on_event: Optional callback receiving real-time event dictionaries.

    Returns:
        Structured incident report dict compliant with chakravyuh.report/v1 schema.
    """
    def emit(ev: dict) -> None:
        if on_event:
            on_event(ev)

    emit({
        "type": "call_start",
        "ts": 0.0,
        "lang": fsm.lang,
        "state": fsm.state.value,
        "simulated": simulated,
    })

    def on_speech_start(ts: float) -> None:
        if player and player.playing:
            player.cancel()
            fsm.on_barge_in()
            emit({"type": "barge_in", "ts": ts})

    for turn in listen(source.frames(), endpointer, stt, on_speech_start=on_speech_start):
        emit(turn.to_event())

        reply = fsm.on_scammer_turn(turn.text, turn.ts)
        for intel in reply.new_intel:
            emit(intel.to_event())

        emit(reply.to_event())

        if tts and player:
            chunks = tts.synthesize(reply.text) if hasattr(tts, "synthesize") else tts(reply.text)
            for chunk in chunks:
                player.play(chunk)

        if reply.end_call:
            break

    if player:
        player.wait(timeout=2.0)

    report = build_report(fsm, simulated=simulated, include_transcript=True)
    emit({"type": "report", "report": report})
    return report
