"""HTTP-Hülle um ``BoxWebApp`` (Python-Standardbibliothek, ohne Zusatzpaket).

Start: ``python main.py --box-web`` – bindet standardmäßig an alle Adressen,
Port 8080, damit die Box im Heimnetz unter ``http://carendmr-box.local:8080``
erreichbar ist.
"""
from __future__ import annotations

import http.cookies
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .app import SESSION_COOKIE, BoxWebApp, Request, Response

DEFAULT_PORT = 8080
MAX_BODY_BYTES = 64 * 1024


class _Handler(BaseHTTPRequestHandler):
    server_version = "CarenDMRBox"
    protocol_version = "HTTP/1.1"

    @property
    def _app(self) -> BoxWebApp:
        return self.server.box_app  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        parsed = urllib.parse.urlparse(self.path)
        form: dict[str, str] = {}
        if method == "POST":
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length > MAX_BODY_BYTES:
                self._send(Response(status=413, body="Zu viele Daten."))
                return
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            form = {k: v[-1] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}
        else:
            form = {k: v[-1] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        request = Request(method=method, path=parsed.path, form=form, cookies=self._cookies())
        self._send(self._app.handle(request))

    def _cookies(self) -> dict:
        header = self.headers.get("Cookie")
        if not header:
            return {}
        jar = http.cookies.SimpleCookie()
        try:
            jar.load(header)
        except http.cookies.CookieError:
            return {}
        return {key: morsel.value for key, morsel in jar.items()}

    def _send(self, response: Response) -> None:
        body = response.body.encode("utf-8")
        if response.location is not None:
            self.send_response(303)
            self.send_header("Location", response.location)
            body = b""
        else:
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            if response.download_name:
                self.send_header("Content-Disposition", f'attachment; filename="{response.download_name}"')
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if response.set_cookie is not None:
            self._set_cookie(response.set_cookie)
        elif response.clear_cookie:
            self.send_header(
                "Set-Cookie",
                f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict",
            )
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _set_cookie(self, token: str) -> None:
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict",
        )

    def log_message(self, *args) -> None:  # keine Konsolenausgabe pro Anfrage
        pass


def make_server(project_root: Path, *, host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), _Handler)
    server.box_app = BoxWebApp(Path(project_root))  # type: ignore[attr-defined]
    return server


def run_box_web(project_root: Path, *, host: str = "0.0.0.0", port: int = DEFAULT_PORT) -> int:
    try:
        server = make_server(project_root, host=host, port=port)
    except OSError as error:
        print(f"Webserver konnte nicht starten: {error}")
        return 2
    shown = "carendmr-box.local" if host == "0.0.0.0" else host
    print(f"Web-Verwaltung läuft: http://{shown}:{port}  (Ende mit Strg+C)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Webserver beendet.")
    finally:
        server.shutdown()
        server.server_close()
    return 0
