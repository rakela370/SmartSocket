"""Local-only offline HTTP application; no packages, network or cloud required.

Launch: python -m backend.web_server
Open:   http://127.0.0.1:8765
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .simulation_service import SimulationService

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
HOST = "127.0.0.1"
PORT = 8765


def make_handler(service: SimulationService):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, data: dict, status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/api/state":
                self._json(service.state())
                return
            files = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/style.css": ("style.css", "text/css; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            }
            if path not in files:
                self.send_error(404)
                return
            name, mime = files[path]
            body = (FRONTEND / name).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            # Refuse cross-site browser requests to this localhost-only demo.
            origin = self.headers.get("Origin", "")
            allowed_origin = f"http://{HOST}:{self.server.server_port}"
            if origin and origin != allowed_origin:
                self._json({"error": "Nedozvoljen izvor zahtjeva."}, 403)
                return
            if self.headers.get("X-Socket-UI") != "1":
                self._json({"error": "Nedozvoljen zahtjev."}, 403)
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self._json({"error": "Očekuje se application/json."}, 415)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 <= size <= 1024:
                    raise ValueError("Neispravna veličina zahtjeva.")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("Podaci moraju biti JSON objekat.")
                path = urlsplit(self.path).path
                if path == "/api/limit":
                    service.set_limit(payload["value"])
                elif path == "/api/duration":
                    service.set_duration(payload["value"])
                elif path == "/api/load":
                    service.set_requested_power(payload["value"])
                elif path == "/api/start":
                    service.start()
                elif path == "/api/stop":
                    service.stop()
                elif path == "/api/reset":
                    service.reset()
                else:
                    self._json({"error": "Nepoznata komanda."}, 404)
                    return
                self._json(service.state())
            except (KeyError, ValueError, TypeError, RuntimeError) as exc:
                print(f"[ODBIJENA KOMANDA] {exc}")
                self._json({"error": str(exc), "state": service.state()}, 400)

        def log_message(self, fmt, *args) -> None:
            # Display only important commands in terminal, not each UI poll.
            if self.command == "POST":
                print(f"[KOMANDA] {self.path} | HTTP {args[1] if len(args)>1 else '?'}")

    return Handler


def main() -> None:
    service = SimulationService()
    server = ThreadingHTTPServer((HOST, PORT), make_handler(service))
    service.start_worker()
    print(f"Pametna uticnica | OFFLINE | http://{HOST}:{PORT}")
    print("Za zaustavljanje pritisni Ctrl+C.")
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        print("\nZaustavljanje: izlaz ISKLJUCEN.")
    finally:
        server.server_close()
        service.shutdown()


if __name__ == "__main__":
    main()
