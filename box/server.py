from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from box.bootstrap import create_box_application
from box.http.features import build_box_registry
from box.http.router import content_type_for, read_json, send_file, send_json
from shared.config.settings import settings


app = create_box_application()
registry = build_box_registry(app)


class BoxHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/dashboard-static/"):
            filename = parsed.path.replace("/dashboard-static/", "", 1)
            send_file(self, app.tv_dashboard_web_dir, filename, content_type_for(filename))
            return
        route = registry.match("GET", parsed.path)
        if not route:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return
        result = route(self, {})
        if result is None:
            return
        payload, status = result if isinstance(result, tuple) else (result, HTTPStatus.OK)
        send_json(self, payload, status=status)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route = registry.match("POST", parsed.path)
        if not route:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return
        result = route(self, read_json(self))
        if result is None:
            return
        payload, status = result if isinstance(result, tuple) else (result, HTTPStatus.OK)
        send_json(self, payload, status=status)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def run(host: str | None = None, port: int | None = None) -> None:
    bind_host = host or settings.box_host
    bind_port = port or settings.box_port
    with ThreadingHTTPServer((bind_host, bind_port), BoxHandler) as server:
        print(f"Box service running on http://{bind_host}:{bind_port}")
        try:
            server.serve_forever()
        finally:
            app.shutdown()
