"""
webhook.py - small web server that receives the provider's result webhooks.

What this file does:
  * Listens on port 8200 in a background thread (built-in http.server, no extra library).
  * Checks the X-AU-Signature header (HMAC-SHA256 of the body); wrong signature -> 401.
  * Passes a valid result to results.handle_result and answers 200.
"""
import hashlib
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.services import results
from app.config import cfg


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        good = hmac.new(cfg["webhook_secret"].encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(good, self.headers.get("X-AU-Signature", "")):
            self.send_response(401)
            self.end_headers()
            return
        results.handle_result(json.loads(raw))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass  # keep the terminal quiet


def start():
    server = ThreadingHTTPServer(("127.0.0.1", 8200), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
