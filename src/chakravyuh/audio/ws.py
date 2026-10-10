# Engineered by uncoalesced
"""Agent side of a call carried over WebSocket (virtual caller now, a phone bridge later). Binary messages both
ways are 16 kHz mono PCM16. The far end streams continuously in real time (silence included), like a phone line;
we send persona audio back only while the persona speaks. Text messages are control/metadata and are ignored here.

    call = WebSocketCall("ws://127.0.0.1:8766")
    run_pipeline(call, Endpointer(SileroVAD()), stt, fsm, tts, Player(call.write))"""
import time
from typing import Iterator

from chakravyuh.audio.source import SAMPLE_RATE, SAMPLE_WIDTH, Frame


class WebSocketCall:
    def __init__(self, url: str, frame_ms: int = 20, open_timeout: float = 5.0):
        from websockets.sync.client import connect
        self.ws = connect(url, max_size=None, open_timeout=open_timeout).__enter__()   # websockets>=17 wants a CM
        self.frame_ms = frame_ms

    def frames(self) -> Iterator[Frame]:
        """AudioSource: fixed frames stamped by stream position, so ts stays monotonic whatever the network does."""
        from websockets.exceptions import ConnectionClosed
        n = SAMPLE_RATE * self.frame_ms // 1000 * SAMPLE_WIDTH
        step, buf, i = self.frame_ms / 1000, b"", 0
        try:
            for msg in self.ws:
                if isinstance(msg, str):
                    continue
                buf += msg
                while len(buf) >= n:
                    yield Frame(buf[:n], round(i * step, 6))
                    buf, i = buf[n:], i + 1
        except ConnectionClosed:
            return

    def write(self, pcm: bytes) -> None:
        """Player output: send one chunk and block for its duration, like a sound device."""
        from websockets.exceptions import ConnectionClosed
        try:
            self.ws.send(pcm)
        except ConnectionClosed:
            return
        time.sleep(len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH))

    def close(self) -> None:
        self.ws.close()
