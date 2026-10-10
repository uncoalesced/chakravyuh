# Engineered by uncoalesced
"""Ollama adapter (stdlib only). Returns a callable(system, history) -> str or Iterator[str] for PersonaFSM.
Supports both non-streaming (full response) and sentence streaming to cut time-to-first-audio below 600ms."""
import json
import re
import urllib.request
from typing import Callable, Iterable, Iterator, List, Optional

_SENTENCE_END = re.compile(r"([.!?।\n]+)")


def split_sentences(tokens: Iterable[str]) -> Iterator[str]:
    """Buffer tokens and yield completed sentences on terminal punctuation (.!?।\n).
    Remaining trailing text is yielded when the token stream finishes."""
    buf = ""
    for token in tokens:
        buf += token
        while True:
            m = _SENTENCE_END.search(buf)
            if not m:
                break
            end = m.end()
            sentence = buf[:end].strip()
            buf = buf[end:]
            if sentence:
                yield sentence
    tail = buf.strip()
    if tail:
        yield tail


def ollama_stream(system: str, history: List[dict], model: str = "qwen2.5:7b-instruct-q4_K_M",
                  host: str = "http://127.0.0.1:11434", timeout: float = 4.0,
                  num_predict: int = 80) -> Iterator[str]:
    """Stream raw tokens from Ollama /api/chat NDJSON stream."""
    body = {
        "model": model, "stream": True, "keep_alive": "30m",
        "options": {"temperature": 0.7, "num_predict": num_predict},
        "messages": [{"role": "system", "content": system}, *history]
    }
    req = urllib.request.Request(f"{host}/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for line in r:
            if not line.strip():
                continue
            chunk = json.loads(line.decode("utf-8"))
            if content := chunk.get("message", {}).get("content"):
                yield content
            if chunk.get("done", False):
                break


def ollama_stream_sentences(model: str = "qwen2.5:7b-instruct-q4_K_M", host: str = "http://127.0.0.1:11434",
                            timeout: float = 4.0, num_predict: int = 80) -> Callable[[str, List[dict]], Iterator[str]]:
    """Returns a callable(system, history) -> Iterator[str] yielding sentences as soon as they complete."""
    def call(system: str, history: List[dict]) -> Iterator[str]:
        return split_sentences(ollama_stream(system, history, model=model, host=host,
                                             timeout=timeout, num_predict=num_predict))
    return call


def ollama_llm(model="qwen2.5:7b-instruct-q4_K_M", host="http://127.0.0.1:11434", timeout=4.0, num_predict=80,
               stream: bool = False):
    """Returns a callable(system, history). If stream=True, returns an Iterator[str] of sentences.
    If stream=False, returns the complete trimmed text string."""
    if stream:
        return ollama_stream_sentences(model=model, host=host, timeout=timeout, num_predict=num_predict)

    def call(system: str, history: list) -> str:
        body = {"model": model, "stream": False, "keep_alive": "30m",
                "options": {"temperature": 0.7, "num_predict": num_predict},
                "messages": [{"role": "system", "content": system}, *history]}
        req = urllib.request.Request(f"{host}/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)["message"]["content"].strip()
    return call
