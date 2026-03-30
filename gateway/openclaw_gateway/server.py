from __future__ import annotations

import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from shared.config.settings import settings
from shared.schemas.models import GatewayCommandResult


PROJECT_ROOT = settings.project_root
MOBILE_WEB_DIR = PROJECT_ROOT / "apps" / "mobile_app_mock" / "web"
DASHBOARD_WEB_DIR = PROJECT_ROOT / "box" / "tv_dashboard" / "web"

AGENT_REGISTRY = {
    "family-assistant": {
        "role": "family",
        "description": "Handle family schedule lookup, manual intake, and screenshot confirmation flows.",
        "actions": {
            "family.status": {"box_action": "family.status", "permission": "read"},
            "intake.manual": {"box_action": "intake.manual", "permission": "write"},
            "intake.screenshot": {"box_action": "intake.screenshot", "permission": "write"},
            "dashboard.get": {"box_action": "dashboard.get", "permission": "read"},
        },
    },
    "home-automation-assistant": {
        "role": "automation",
        "description": "Refresh dashboard, play TTS, and control TV devices.",
        "actions": {
            "dashboard.refresh": {"box_action": "dashboard.refresh", "permission": "execute"},
            "tts.play": {"box_action": "tts.play", "permission": "execute"},
            "tv.wake": {"box_action": "tv.wake", "permission": "execute"},
            "dashboard.get": {"box_action": "dashboard.get", "permission": "read"},
        },
    },
}

ROLE_POLICIES = {
    "admin": {"agents": ["family-assistant", "home-automation-assistant"], "permissions": ["read", "write", "execute"]},
    "parent": {"agents": ["family-assistant", "home-automation-assistant"], "permissions": ["read", "write", "execute"]},
    "child": {"agents": ["family-assistant"], "permissions": ["read"]},
    "guest": {"agents": ["family-assistant"], "permissions": ["read"]},
}


class BoxClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, path: str) -> dict:
        return self._request("GET", path)

    def post(self, path: str, payload: dict) -> dict:
        return self._request("POST", path, payload)

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"box_http_error:{exc.code}:{detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"box_unreachable:{exc.reason}") from exc


class OpenClawGateway:
    def __init__(self, box_client: BoxClient) -> None:
        self.box_client = box_client

    def health(self) -> dict:
        return {"ok": True, "service": "gateway", "box": self.box_client.get("/health")}

    def overview(self) -> dict:
        overview = self.box_client.get("/api/box/control-plane/overview")
        overview["agents"] = [
            {"name": name, "role": config["role"], "description": config["description"], "actions": list(config["actions"].keys())}
            for name, config in AGENT_REGISTRY.items()
        ]
        overview["role_policies"] = ROLE_POLICIES
        return overview

    def open_session(self, actor_name: str, actor_role: str) -> dict:
        role_policy = ROLE_POLICIES.get(actor_role, ROLE_POLICIES["guest"])
        return self.box_client.post(
            "/api/box/control-plane/sessions/open",
            {"actor_name": actor_name, "actor_role": actor_role, "allowed_agents": role_policy["agents"]},
        )

    def dispatch(self, session_id: str, agent_name: str, action_name: str, payload: dict) -> dict:
        session = self._get_session(session_id)
        if not session:
            return {"ok": False, "error": "session_not_found"}
        policy = ROLE_POLICIES.get(session["actor_role"], ROLE_POLICIES["guest"])
        agent = AGENT_REGISTRY.get(agent_name)
        if not agent:
            return {"ok": False, "error": "agent_not_found"}
        if agent_name not in policy["agents"]:
            return {"ok": False, "error": "agent_not_allowed"}
        action = agent["actions"].get(action_name)
        if not action:
            return {"ok": False, "error": "action_not_found"}
        if action["permission"] not in policy["permissions"]:
            return {"ok": False, "error": "permission_denied"}
        return self.box_client.post(
            "/api/box/control-plane/commands/execute",
            {"session_id": session_id, "agent_name": agent_name, "action_name": action["box_action"], "payload": payload},
        )

    def family_status(self) -> dict:
        return self.box_client.get("/api/box/mobile-status")

    def dashboard(self) -> dict:
        return self.box_client.get("/api/box/dashboard")

    def device_status(self) -> dict:
        return self.box_client.get("/api/box/device")

    def pairing_payload(self) -> dict:
        return self.box_client.get("/api/box/pairing/payload")

    def claim_device(self, actor_user_id: str, actor_name: str, family_name: str, claim_token: str) -> dict:
        return self.box_client.post(
            "/api/box/device/claim",
            {
                "actor_user_id": actor_user_id,
                "actor_name": actor_name,
                "family_name": family_name,
                "claim_token": claim_token,
            },
        )

    def unbind_device(self, actor_user_id: str, actor_name: str) -> dict:
        return self.box_client.post(
            "/api/box/device/unbind",
            {
                "actor_user_id": actor_user_id,
                "actor_name": actor_name,
            },
        )

    def reset_device(self) -> dict:
        return self.box_client.post("/api/box/device/reset", {})

    def list_nodes(self) -> dict:
        return self.box_client.get("/api/box/nodes")

    def acknowledge_notification(self, notification_id: int) -> dict:
        return self.box_client.post("/api/box/notifications/ack", {"id": notification_id})

    def _get_session(self, session_id: str) -> dict | None:
        sessions = self.box_client.get("/api/box/control-plane/sessions")["items"]
        for session in sessions:
            if session["session_id"] == session_id:
                return session
        return None


class FamilyAssistant:
    def __init__(self, gateway: OpenClawGateway) -> None:
        self.gateway = gateway

    def family_status(self) -> dict:
        return self.gateway.family_status()

    def manual_intake(self, session_id: str, text: str) -> dict:
        return self.gateway.dispatch(session_id, "family-assistant", "intake.manual", {"text": text})

    def screenshot_intake(self, session_id: str, text: str) -> dict:
        return self.gateway.dispatch(session_id, "family-assistant", "intake.screenshot", {"text": text})


class HomeAutomationAssistant:
    def __init__(self, gateway: OpenClawGateway) -> None:
        self.gateway = gateway

    def refresh_dashboard(self, session_id: str) -> GatewayCommandResult:
        result = self.gateway.dispatch(session_id, "home-automation-assistant", "dashboard.refresh", {})
        return GatewayCommandResult(ok=result.get("ok", True), route="home-automation-assistant", message=result.get("error", "dashboard_refreshed"))

    def play_tts(self, session_id: str, message: str) -> GatewayCommandResult:
        result = self.gateway.dispatch(session_id, "home-automation-assistant", "tts.play", {"message": message})
        return GatewayCommandResult(ok=result.get("ok", True), route="home-automation-assistant", message=result.get("error", "tts_played"))

    def wake_tv(self, session_id: str) -> GatewayCommandResult:
        result = self.gateway.dispatch(session_id, "home-automation-assistant", "tv.wake", {})
        return GatewayCommandResult(ok=result.get("ok", True), route="home-automation-assistant", message=result.get("error", "tv_woken"))


box_client = BoxClient(settings.box_base_url)
openclaw_gateway = OpenClawGateway(box_client)
family_assistant = FamilyAssistant(openclaw_gateway)
automation_assistant = HomeAutomationAssistant(openclaw_gateway)


class GatewayHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/mobile"}:
            self._send_file(MOBILE_WEB_DIR, "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/dashboard":
            self._send_file(DASHBOARD_WEB_DIR, "index.html", "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/mobile-static/"):
            filename = parsed.path.replace("/mobile-static/", "", 1)
            self._send_file(MOBILE_WEB_DIR, filename, self._content_type(filename))
            return
        if parsed.path.startswith("/dashboard-static/"):
            filename = parsed.path.replace("/dashboard-static/", "", 1)
            self._send_file(DASHBOARD_WEB_DIR, filename, self._content_type(filename))
            return
        try:
            if parsed.path == "/health":
                self._send_json(openclaw_gateway.health())
                return
            if parsed.path == "/api/gateway/family/status":
                self._send_json(family_assistant.family_status())
                return
            if parsed.path == "/api/box/dashboard":
                self._send_json(openclaw_gateway.dashboard())
                return
            if parsed.path == "/api/gateway/nodes":
                self._send_json(openclaw_gateway.list_nodes())
                return
            if parsed.path == "/api/gateway/control-plane/overview":
                self._send_json(openclaw_gateway.overview())
                return
            if parsed.path == "/api/gateway/device/status":
                self._send_json(openclaw_gateway.device_status())
                return
            if parsed.path == "/api/gateway/device/pairing":
                self._send_json(openclaw_gateway.pairing_payload())
                return
        except RuntimeError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        body = self._read_json()
        session_id = body.get("session_id", "")
        try:
            if parsed.path == "/api/gateway/control-plane/sessions/open":
                self._send_json(
                    openclaw_gateway.open_session(body.get("actor_name", "guest"), body.get("actor_role", "guest")),
                    status=HTTPStatus.CREATED,
                )
                return
            if parsed.path == "/api/gateway/control-plane/dispatch":
                self._send_json(
                    openclaw_gateway.dispatch(
                        session_id=session_id,
                        agent_name=body.get("agent_name", ""),
                        action_name=body.get("action_name", ""),
                        payload=body.get("payload", {}),
                    )
                )
                return
            if parsed.path == "/api/gateway/device/claim":
                self._send_json(
                    openclaw_gateway.claim_device(
                        actor_user_id=body.get("actor_user_id", "user-demo"),
                        actor_name=body.get("actor_name", "Owner"),
                        family_name=body.get("family_name", "My Family"),
                        claim_token=body.get("claim_token", ""),
                    )
                )
                return
            if parsed.path == "/api/gateway/device/unbind":
                self._send_json(
                    openclaw_gateway.unbind_device(
                        actor_user_id=body.get("actor_user_id", "user-demo"),
                        actor_name=body.get("actor_name", "Owner"),
                    )
                )
                return
            if parsed.path == "/api/gateway/device/reset":
                self._send_json(openclaw_gateway.reset_device())
                return
            if parsed.path == "/api/gateway/family/intake/manual":
                self._send_json(family_assistant.manual_intake(session_id, body.get("text", "")), status=HTTPStatus.CREATED)
                return
            if parsed.path == "/api/gateway/family/intake/screenshot":
                self._send_json(family_assistant.screenshot_intake(session_id, body.get("text", "")), status=HTTPStatus.CREATED)
                return
            if parsed.path == "/api/gateway/automation/refresh-dashboard":
                self._send_json(asdict(automation_assistant.refresh_dashboard(session_id)))
                return
            if parsed.path == "/api/gateway/automation/play-tts":
                self._send_json(asdict(automation_assistant.play_tts(session_id, body.get("message", ""))))
                return
            if parsed.path == "/api/gateway/automation/tv/wake":
                self._send_json(asdict(automation_assistant.wake_tv(session_id)))
                return
            if parsed.path == "/api/box/notifications/ack":
                self._send_json(openclaw_gateway.acknowledge_notification(int(body["id"])))
                return
        except RuntimeError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, base_dir: Path, filename: str, content_type: str) -> None:
        path = base_dir / filename
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File Not Found")
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _content_type(self, filename: str) -> str:
        if filename.endswith(".css"):
            return "text/css; charset=utf-8"
        if filename.endswith(".js"):
            return "application/javascript; charset=utf-8"
        return "text/plain; charset=utf-8"


def run(host: str | None = None, port: int | None = None) -> None:
    bind_host = host or settings.host
    bind_port = port or settings.port
    with ThreadingHTTPServer((bind_host, bind_port), GatewayHandler) as server:
        print(f"Gateway running on http://{bind_host}:{bind_port}")
        server.serve_forever()
