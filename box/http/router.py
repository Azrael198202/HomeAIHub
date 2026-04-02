from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Callable


RouteHandler = Callable[[object, dict], tuple[dict, int] | dict]


@dataclass(slots=True)
class Route:
    method: str
    path: str
    handler: RouteHandler


class RouteRegistry:
    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], RouteHandler] = {}

    def add(self, method: str, path: str, handler: RouteHandler) -> None:
        self._routes[(method.upper(), path)] = handler

    def match(self, method: str, path: str) -> RouteHandler | None:
        return self._routes.get((method.upper(), path))


def send_json(handler, payload: dict, status: int = HTTPStatus.OK) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_json(handler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length).decode("utf-8")
    return json.loads(raw) if raw else {}


def send_file(handler, base_dir: Path, filename: str, content_type: str) -> None:
    path = base_dir / filename
    if not path.exists():
        handler.send_error(HTTPStatus.NOT_FOUND, "File Not Found")
        return
    data = path.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def content_type_for(filename: str) -> str:
    if filename.endswith(".html"):
        return "text/html; charset=utf-8"
    if filename.endswith(".css"):
        return "text/css; charset=utf-8"
    if filename.endswith(".js"):
        return "application/javascript; charset=utf-8"
    if filename.endswith(".svg"):
        return "image/svg+xml; charset=utf-8"
    return "text/plain; charset=utf-8"
