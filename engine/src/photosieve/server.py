"""Small local HTTP boundary. No filesystem writes and deliberately no delete route."""

import hmac
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .contracts import MAX_BODY_BYTES, parse_request


class SieveServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, scorer, token: str):
        if len(token) < 24:
            raise ValueError("Pairing token must have at least 24 characters")
        self.scorer = scorer
        self.token = token
        self.slots = threading.BoundedSemaphore(2)
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "PhotoSieve/0.1"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def log_message(self, *_args):
        # HTTP paths, tokens, prompts, and images must not enter request logs.
        pass

    def send_json(self, status: int, payload: dict):
        encoded = json.dumps(payload, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        try:
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

    def authenticated(self) -> bool:
        supplied = self.headers.get("Authorization", "").encode()
        expected = f"Bearer {self.server.token}".encode()
        if not hmac.compare_digest(supplied, expected):
            self.send_json(401, {"error": "Pairing token is missing or incorrect"})
            return False
        return True

    def do_GET(self):
        if not self.authenticated():
            return
        if self.path == "/v1/health":
            self.send_json(200, {"api_version": 1, "status": "ready", "storage": "memory-only"})
        else:
            self.send_json(404, {"error": "Unknown route"})

    def do_POST(self):
        if not self.authenticated():
            return
        if self.path != "/v1/score":
            self.send_json(404, {"error": "Unknown route"})
            return
        if self.headers.get("Transfer-Encoding"):
            self.send_json(400, {"error": "Chunked requests are not supported"})
            return
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"error": "Use application/json"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Invalid Content-Length"})
            return
        if not 0 < length <= MAX_BODY_BYTES:
            self.send_json(413, {"error": "Request must be between 1 byte and 3 MiB"})
            return
        if not self.server.slots.acquire(blocking=False):
            self.send_json(429, {"error": "Engine is busy; try again"})
            return
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("Incomplete request body")
            request = parse_request(json.loads(body))
            self.send_json(200, self.server.scorer.score(request))
        except (ValueError, UnicodeDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except socket.timeout:
            self.send_json(408, {"error": "Request timed out"})
        except Exception:
            self.send_json(500, {"error": "Scoring failed; check model installation/device"})
        finally:
            self.server.slots.release()
