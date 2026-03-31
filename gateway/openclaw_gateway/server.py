from __future__ import annotations

import base64
import binascii
import hashlib
import json
import tempfile
import uuid
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from gateway.railway_relay import RailwayMaintenanceService, RailwayRelayStore
from shared.config.settings import settings
from shared.schemas.models import GatewayCommandResult


PROJECT_ROOT = settings.project_root
MOBILE_WEB_DIR = PROJECT_ROOT / "apps" / "mobile_app_mock" / "web"
DASHBOARD_WEB_DIR = PROJECT_ROOT / "box" / "tv_dashboard" / "web"
railway_relay_store = RailwayRelayStore(settings.database_path, settings.relay_temp_dir)
railway_maintenance_service = RailwayMaintenanceService(
    relay_store=railway_relay_store,
    cleanup_interval_seconds=settings.railway_cleanup_interval_seconds,
    job_retention_seconds=settings.railway_job_retention_seconds,
    box_stale_after_seconds=settings.railway_box_stale_after_seconds,
)
railway_maintenance_service.start()

AGENT_REGISTRY = {
    "family-intake-agent": {
        "role": "intake",
        "description": "Relay family text, photo, screenshot, and voice data from mobile clients into the home box.",
        "actions": {
            "family.status": {"box_action": "family.status", "permission": "read"},
            "intake.manual": {"box_action": "intake.manual", "permission": "write"},
            "intake.screenshot": {"box_action": "intake.screenshot", "permission": "write"},
            "intake.photo": {"box_action": "intake.photo", "permission": "write"},
            "intake.voice": {"box_action": "intake.voice", "permission": "write"},
        },
    },
    "household-dashboard-agent": {
        "role": "dashboard",
        "description": "Keep the TV dashboard always-on and expose the current family hub state.",
        "actions": {
            "dashboard.get": {"box_action": "dashboard.get", "permission": "read"},
            "dashboard.refresh": {"box_action": "dashboard.refresh", "permission": "execute"},
            "hub.status": {"box_action": "hub.status", "permission": "read"},
        },
    },
    "voice-automation-agent": {
        "role": "voice",
        "description": "Run spoken announcements, TV wake actions, and voice wake flows for the home box.",
        "actions": {
            "tts.play": {"box_action": "tts.play", "permission": "execute"},
            "announce.play": {"box_action": "announce.play", "permission": "execute"},
            "tv.wake": {"box_action": "tv.wake", "permission": "execute"},
            "voice.status": {"box_action": "voice.status", "permission": "read"},
            "voice.wake": {"box_action": "voice.wake", "permission": "execute"},
        },
    },
    "home-orchestrator-agent": {
        "role": "orchestrator",
        "description": "Coordinate intake, dashboard, and voice capabilities as the household control brain.",
        "actions": {
            "hub.status": {"box_action": "hub.status", "permission": "read"},
            "voice.status": {"box_action": "voice.status", "permission": "read"},
            "voice.wake": {"box_action": "voice.wake", "permission": "execute"},
            "announce.play": {"box_action": "announce.play", "permission": "execute"},
            "dashboard.refresh": {"box_action": "dashboard.refresh", "permission": "execute"},
        },
    },
}

ROLE_POLICIES = {
    "admin": {
        "agents": [
            "family-intake-agent",
            "household-dashboard-agent",
            "voice-automation-agent",
            "home-orchestrator-agent",
        ],
        "permissions": ["read", "write", "execute"],
    },
    "parent": {
        "agents": [
            "family-intake-agent",
            "household-dashboard-agent",
            "voice-automation-agent",
            "home-orchestrator-agent",
        ],
        "permissions": ["read", "write", "execute"],
    },
    "child": {
        "agents": ["family-intake-agent", "household-dashboard-agent"],
        "permissions": ["read", "write"],
    },
    "guest": {
        "agents": ["family-intake-agent", "household-dashboard-agent"],
        "permissions": ["read"],
    },
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

    def external_box_info(self) -> dict:
        status = railway_relay_store.get_primary_box() or {
            "device_id": "hub-demo-001",
            "device_name": "HomeAIHub Box",
            "pairing_status": "pending_claim",
            "owner_name": "",
            "family_id": "",
            "box_status": "offline",
            "dashboard_path": "/dashboard",
        }
        return {
            "box": {
                "device_id": status.get("device_id", ""),
                "device_name": status.get("device_name", ""),
                "paired": status.get("pairing_status") == "paired",
                "status": status.get("pairing_status", "pending_claim"),
                "family_id": status.get("family_id", ""),
                "owner_name": status.get("owner_name", ""),
                "last_seen_at": status.get("last_seen_at", ""),
                "box_service_healthy": status.get("box_status") == "online",
                "dashboard_path": status.get("dashboard_path", "/dashboard"),
            },
            "links": {
                "dashboard": f"{settings.railway_public_base_url}/dashboard",
                "mobile": f"{settings.railway_public_base_url}/mobile",
                "pairing": f"{settings.railway_public_base_url}/api/gateway/device/pairing",
                "status": f"{settings.railway_public_base_url}/api/railway/box/status",
            },
        }

    def relay_delivery(
        self,
        content_kind: str,
        text: str,
        filename: str,
        mime_type: str,
        content_base64: str,
        source_channel: str = "railway",
    ) -> dict:
        relay_id = str(uuid.uuid4())
        result: dict
        try:
            if content_base64:
                base64.b64decode(content_base64.encode("utf-8"), validate=True)
            box = railway_relay_store.get_primary_box()
            if not box:
                return {"ok": False, "error": "no_registered_box"}
            job = railway_relay_store.create_relay_job(
                {
                    "relay_id": relay_id,
                    "device_id": box["device_id"],
                    "content_kind": content_kind,
                    "text": text,
                    "filename": filename,
                    "mime_type": mime_type,
                    "content_base64": content_base64,
                }
            )
            result = {
                "ok": True,
                "relay_id": relay_id,
                "queue_status": job.get("status", "pending"),
                "target_device_id": box["device_id"],
                "box_ack": None,
            }
        except binascii.Error as exc:
            result = {"ok": False, "error": f"invalid_base64:{exc}"}
        result["deleted_from_railway"] = False
        return result

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


class FamilyIntakeAgent:
    def __init__(self, gateway: OpenClawGateway) -> None:
        self.gateway = gateway

    def family_status(self) -> dict:
        return self.gateway.family_status()

    def manual_intake(self, session_id: str, text: str) -> dict:
        return self.gateway.dispatch(session_id, "family-intake-agent", "intake.manual", {"text": text})

    def screenshot_intake(self, session_id: str, text: str) -> dict:
        return self.gateway.dispatch(session_id, "family-intake-agent", "intake.screenshot", {"text": text})

    def photo_intake(self, session_id: str, text: str) -> dict:
        return self.gateway.dispatch(session_id, "family-intake-agent", "intake.photo", {"text": text})

    def voice_intake(self, session_id: str, text: str) -> dict:
        return self.gateway.dispatch(session_id, "family-intake-agent", "intake.voice", {"text": text})


class HouseholdDashboardAgent:
    def __init__(self, gateway: OpenClawGateway) -> None:
        self.gateway = gateway

    def hub_status(self, session_id: str) -> dict:
        return self.gateway.dispatch(session_id, "household-dashboard-agent", "hub.status", {})

    def refresh_dashboard(self, session_id: str) -> GatewayCommandResult:
        result = self.gateway.dispatch(session_id, "household-dashboard-agent", "dashboard.refresh", {})
        return GatewayCommandResult(ok=result.get("ok", True), route="household-dashboard-agent", message=result.get("error", "dashboard_refreshed"))


class VoiceAutomationAgent:
    def __init__(self, gateway: OpenClawGateway) -> None:
        self.gateway = gateway

    def play_tts(self, session_id: str, message: str) -> GatewayCommandResult:
        result = self.gateway.dispatch(session_id, "voice-automation-agent", "tts.play", {"message": message})
        return GatewayCommandResult(ok=result.get("ok", True), route="voice-automation-agent", message=result.get("error", "tts_played"))

    def announce(self, session_id: str, message: str, priority: str = "normal") -> GatewayCommandResult:
        result = self.gateway.dispatch(
            session_id,
            "voice-automation-agent",
            "announce.play",
            {"message": message, "priority": priority},
        )
        return GatewayCommandResult(ok=result.get("ok", True), route="voice-automation-agent", message=result.get("error", "announcement_played"))

    def wake_tv(self, session_id: str) -> GatewayCommandResult:
        result = self.gateway.dispatch(session_id, "voice-automation-agent", "tv.wake", {})
        return GatewayCommandResult(ok=result.get("ok", True), route="voice-automation-agent", message=result.get("error", "tv_woken"))

    def voice_status(self, session_id: str) -> dict:
        return self.gateway.dispatch(session_id, "voice-automation-agent", "voice.status", {})

    def wake_by_voice(self, session_id: str, transcript: str) -> dict:
        return self.gateway.dispatch(session_id, "voice-automation-agent", "voice.wake", {"transcript": transcript})


box_client = BoxClient(settings.box_base_url)
openclaw_gateway = OpenClawGateway(box_client)
family_assistant = FamilyIntakeAgent(openclaw_gateway)
dashboard_agent = HouseholdDashboardAgent(openclaw_gateway)
automation_assistant = VoiceAutomationAgent(openclaw_gateway)


def _box_auth_valid(headers) -> bool:
    expected = settings.box_shared_token
    if not expected:
        return True
    return headers.get("X-HomeAIHub-Box-Token", "") == expected


class GatewayHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
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
            if parsed.path == "/api/gateway/hub/overview":
                self._send_json(openclaw_gateway.box_client.get("/api/box/hub/overview"))
                return
            if parsed.path == "/api/gateway/voice/status":
                self._send_json(openclaw_gateway.box_client.get("/api/box/voice/status"))
                return
            if parsed.path == "/api/gateway/device/status":
                self._send_json(openclaw_gateway.device_status())
                return
            if parsed.path == "/api/gateway/device/pairing":
                self._send_json(openclaw_gateway.pairing_payload())
                return
            if parsed.path == "/api/railway/box":
                self._send_json(openclaw_gateway.external_box_info())
                return
            if parsed.path == "/api/railway/box/status":
                primary_box = railway_relay_store.get_primary_box() or {"box_status": "offline"}
                pending_jobs = 0
                if primary_box.get("device_id"):
                    pending_jobs = len(railway_relay_store.list_pending_jobs(primary_box["device_id"], limit=100))
                self._send_json({**primary_box, "pending_jobs": pending_jobs})
                return
            if parsed.path == "/api/railway/box/link":
                self._send_json(
                    {
                        "dashboard": f"{settings.railway_public_base_url}/dashboard",
                        "mobile": f"{settings.railway_public_base_url}/mobile",
                        "pairing": f"{settings.railway_public_base_url}/api/gateway/device/pairing",
                    }
                )
                return
            if parsed.path == "/api/railway/boxes":
                self._send_json({"items": railway_relay_store.list_boxes()})
                return
            if parsed.path == "/api/railway/relay/pending":
                if not _box_auth_valid(self.headers):
                    self._send_json({"ok": False, "error": "box_auth_invalid"}, status=HTTPStatus.UNAUTHORIZED)
                    return
                device_id = (query.get("device_id") or [""])[0]
                self._send_json({"items": railway_relay_store.list_pending_jobs(device_id)})
                return
            if parsed.path == "/api/railway/relay/status":
                relay_id = (query.get("relay_id") or [""])[0]
                job = railway_relay_store.get_relay_job(relay_id) or {}
                payload = {
                    "relay_id": job.get("relay_id", relay_id),
                    "device_id": job.get("device_id", ""),
                    "content_kind": job.get("content_kind", ""),
                    "status": job.get("status", "unknown"),
                    "created_at": job.get("created_at", ""),
                    "acknowledged_at": job.get("acknowledged_at", ""),
                    "filename": job.get("filename", ""),
                    "byte_size": job.get("byte_size", 0),
                    "available_on_railway": bool(job.get("temp_path", "") and Path(job.get("temp_path", "")).exists()),
                }
                self._send_json(payload)
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
            if parsed.path == "/api/gateway/intake/text":
                self._send_json(family_assistant.manual_intake(session_id, body.get("text", "")), status=HTTPStatus.CREATED)
                return
            if parsed.path == "/api/gateway/intake/photo":
                self._send_json(family_assistant.photo_intake(session_id, body.get("text", "")), status=HTTPStatus.CREATED)
                return
            if parsed.path == "/api/gateway/intake/voice":
                self._send_json(family_assistant.voice_intake(session_id, body.get("text", "")), status=HTTPStatus.CREATED)
                return
            if parsed.path == "/api/railway/relay/message":
                self._send_json(
                    openclaw_gateway.relay_delivery(
                        content_kind="message",
                        text=body.get("text", ""),
                        filename=body.get("filename", "message.txt"),
                        mime_type=body.get("mime_type", "text/plain"),
                        content_base64=body.get("content_base64", ""),
                    ),
                    status=HTTPStatus.CREATED,
                )
                return
            if parsed.path == "/api/railway/relay/photo":
                self._send_json(
                    openclaw_gateway.relay_delivery(
                        content_kind="photo",
                        text=body.get("text", ""),
                        filename=body.get("filename", "photo.bin"),
                        mime_type=body.get("mime_type", "application/octet-stream"),
                        content_base64=body.get("content_base64", ""),
                    ),
                    status=HTTPStatus.CREATED,
                )
                return
            if parsed.path == "/api/railway/relay/voice":
                self._send_json(
                    openclaw_gateway.relay_delivery(
                        content_kind="voice",
                        text=body.get("text", ""),
                        filename=body.get("filename", "voice.bin"),
                        mime_type=body.get("mime_type", "application/octet-stream"),
                        content_base64=body.get("content_base64", ""),
                    ),
                    status=HTTPStatus.CREATED,
                )
                return
            if parsed.path == "/api/railway/box/register":
                if not _box_auth_valid(self.headers):
                    self._send_json({"ok": False, "error": "box_auth_invalid"}, status=HTTPStatus.UNAUTHORIZED)
                    return
                self._send_json(
                    railway_relay_store.register_box(
                        {
                            "device_id": body.get("device_id", ""),
                            "device_name": body.get("device_name", "HomeAIHub Box"),
                            "pairing_status": body.get("pairing_status", "pending_claim"),
                            "owner_name": body.get("owner_name", ""),
                            "family_id": body.get("family_id", ""),
                            "box_status": body.get("box_status", "online"),
                            "dashboard_path": body.get("dashboard_path", "/dashboard"),
                        }
                    ),
                    status=HTTPStatus.CREATED,
                )
                return
            if parsed.path == "/api/railway/box/heartbeat":
                if not _box_auth_valid(self.headers):
                    self._send_json({"ok": False, "error": "box_auth_invalid"}, status=HTTPStatus.UNAUTHORIZED)
                    return
                self._send_json(
                    railway_relay_store.heartbeat_box(
                        {
                            "device_id": body.get("device_id", ""),
                            "device_name": body.get("device_name", "HomeAIHub Box"),
                            "pairing_status": body.get("pairing_status", "pending_claim"),
                            "owner_name": body.get("owner_name", ""),
                            "family_id": body.get("family_id", ""),
                            "box_status": body.get("box_status", "online"),
                            "dashboard_path": body.get("dashboard_path", "/dashboard"),
                        }
                    )
                )
                return
            if parsed.path == "/api/railway/relay/ack":
                if not _box_auth_valid(self.headers):
                    self._send_json({"ok": False, "error": "box_auth_invalid"}, status=HTTPStatus.UNAUTHORIZED)
                    return
                self._send_json(railway_relay_store.acknowledge_job(body.get("relay_id", "")))
                return
            if parsed.path == "/api/gateway/automation/refresh-dashboard":
                self._send_json(asdict(dashboard_agent.refresh_dashboard(session_id)))
                return
            if parsed.path == "/api/gateway/automation/play-tts":
                self._send_json(asdict(automation_assistant.play_tts(session_id, body.get("message", ""))))
                return
            if parsed.path == "/api/gateway/automation/announce":
                self._send_json(
                    asdict(
                        automation_assistant.announce(
                            session_id,
                            body.get("message", ""),
                            body.get("priority", "normal"),
                        )
                    )
                )
                return
            if parsed.path == "/api/gateway/automation/tv/wake":
                self._send_json(asdict(automation_assistant.wake_tv(session_id)))
                return
            if parsed.path == "/api/gateway/voice/wake":
                self._send_json(
                    automation_assistant.wake_by_voice(
                        session_id,
                        body.get("transcript", ""),
                    )
                )
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
        try:
            server.serve_forever()
        finally:
            railway_maintenance_service.stop()
