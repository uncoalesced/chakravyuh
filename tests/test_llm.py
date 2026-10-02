# Engineered by uncoalesced
import json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from chakravyuh.llm import ollama_llm
from chakravyuh.fsm import PersonaFSM


def serve(reply):
    box = {}
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            box["path"] = self.path
            box["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            data = json.dumps(reply).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def log_message(self, *a): pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, box

def test_request_shape_and_end_to_end_with_fsm():
    srv, box = serve({"message": {"content": " Oh sir, one minute please. "}})
    try:
        llm = ollama_llm(host=f"http://127.0.0.1:{srv.server_port}", num_predict=60)
        r = PersonaFSM(llm=llm).on_scammer_turn("Your power will be cut tonight", 0)
    finally:
        srv.shutdown()
    b = box["body"]
    assert box["path"] == "/api/chat" and b["stream"] is False and b["options"]["num_predict"] == 60
    assert b["messages"][0]["role"] == "system" and b["messages"][-1] == {"role": "user", "content": "Your power will be cut tonight"}
    assert r.text == "Oh sir, one minute please."

def test_unreachable_ollama_falls_back_to_script():
    r = PersonaFSM(llm=ollama_llm(host="http://127.0.0.1:9", timeout=0.5)).on_scammer_turn("pay now", 0)
    assert r.text
