# Engineered by uncoalesced
"""Ollama adapter (stdlib only). Returns a callable(system, history) -> str for PersonaFSM(llm=...).
Non-streaming for now. ponytail: add sentence streaming once the latency harness shows first-token time matters."""
import json
import urllib.request


def ollama_llm(model="qwen2.5:7b-instruct-q4_K_M", host="http://127.0.0.1:11434", timeout=4.0, num_predict=80):
    def call(system: str, history: list) -> str:
        body = {"model": model, "stream": False, "keep_alive": "30m",
                "options": {"temperature": 0.7, "num_predict": num_predict},
                "messages": [{"role": "system", "content": system}, *history]}
        req = urllib.request.Request(f"{host}/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)["message"]["content"].strip()
    return call
