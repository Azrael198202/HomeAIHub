from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from box.calendar_engine.service import CalendarEngine
from box.event_parser.service import EventParserService
from box.home_api.service import HomeAPI
from box.hub_orchestrator.service import HubOrchestratorService
from box.info_engine.service import InfoEngine
from box.local_db.repository import LocalRepository
from box.ocr_service.service import OCRService
from box.railway_sync.service import RailwaySyncService
from box.reminder_engine.service import ReminderEngine
from box.tts_service.service import TTSService
from box.tv_control_service.service import TVControlService
from box.tv_dashboard.service import TVDashboardService
from shared.config.settings import settings


repository = LocalRepository(settings.database_path)
ocr_service = OCRService()
parser_service = EventParserService()
calendar_engine = CalendarEngine(repository)
reminder_engine = ReminderEngine(repository)
info_engine = InfoEngine(repository)
tts_service = TTSService(repository)
tv_control_service = TVControlService(repository)
tv_dashboard_service = TVDashboardService(repository)
hub_orchestrator_service = HubOrchestratorService(
    repository=repository,
    tts_service=tts_service,
    tv_control_service=tv_control_service,
    tv_dashboard_service=tv_dashboard_service,
)
home_api = HomeAPI(
    repository=repository,
    ocr_service=ocr_service,
    parser_service=parser_service,
    calendar_engine=calendar_engine,
    reminder_engine=reminder_engine,
    info_engine=info_engine,
    tts_service=tts_service,
    tv_control_service=tv_control_service,
    tv_dashboard_service=tv_dashboard_service,
    hub_orchestrator_service=hub_orchestrator_service,
)
home_api.bootstrap()
railway_sync_service = RailwaySyncService(
    base_url=settings.railway_api_base_url,
    home_api=home_api,
    sync_interval_seconds=settings.box_sync_interval_seconds,
    shared_token=settings.box_shared_token,
)
railway_sync_service.start()


class BoxHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json({"ok": True, "service": "box"})
            return
        if parsed.path == "/api/box/dashboard":
            self._send_json(home_api.dashboard())
            return
        if parsed.path == "/api/box/mobile-status":
            self._send_json(home_api.mobile_status())
            return
        if parsed.path == "/api/box/nodes":
            self._send_json({"items": repository.list_nodes()})
            return
        if parsed.path == "/api/box/device":
            self._send_json(home_api.get_device())
            return
        if parsed.path == "/api/box/device/external-status":
            self._send_json(home_api.external_box_status())
            return
        if parsed.path == "/api/box/pairing/payload":
            self._send_json(home_api.get_pairing_payload())
            return
        if parsed.path == "/api/box/control-plane/overview":
            self._send_json(home_api.control_plane_overview())
            return
        if parsed.path == "/api/box/control-plane/sessions":
            self._send_json({"items": repository.list_sessions()})
            return
        if parsed.path == "/api/box/control-plane/commands":
            self._send_json({"items": repository.list_recent_commands(20)})
            return
        if parsed.path == "/api/box/hub/overview":
            self._send_json(hub_orchestrator_service.hub_overview())
            return
        if parsed.path == "/api/box/voice/status":
            self._send_json(hub_orchestrator_service.voice_status())
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        body = self._read_json()
        if parsed.path == "/api/box/device/claim":
            self._send_json(
                home_api.claim_device(
                    actor_user_id=body.get("actor_user_id", "user-demo"),
                    actor_name=body.get("actor_name", "Owner"),
                    family_name=body.get("family_name", "My Family"),
                    claim_token=body.get("claim_token", ""),
                )
            )
            return
        if parsed.path == "/api/box/device/unbind":
            self._send_json(
                home_api.unbind_device(
                    actor_user_id=body.get("actor_user_id", "user-demo"),
                    actor_name=body.get("actor_name", "Owner"),
                )
            )
            return
        if parsed.path == "/api/box/device/reset":
            self._send_json(home_api.reset_pairing())
            return
        if parsed.path == "/api/box/intake/manual":
            self._send_json(home_api.ingest_manual(body.get("text", "")), status=HTTPStatus.CREATED)
            return
        if parsed.path == "/api/box/intake/screenshot":
            self._send_json(home_api.ingest_screenshot(body.get("text", "")), status=HTTPStatus.CREATED)
            return
        if parsed.path == "/api/box/intake/photo":
            self._send_json(home_api.ingest_photo(body.get("text", "")), status=HTTPStatus.CREATED)
            return
        if parsed.path == "/api/box/intake/voice":
            self._send_json(home_api.ingest_voice(body.get("text", "")), status=HTTPStatus.CREATED)
            return
        if parsed.path == "/api/box/relay/receive":
            self._send_json(
                home_api.receive_relay_delivery(
                    relay_id=body.get("relay_id", ""),
                    source_channel=body.get("source_channel", "railway"),
                    content_kind=body.get("content_kind", ""),
                    text=body.get("text", ""),
                    filename=body.get("filename", ""),
                    mime_type=body.get("mime_type", ""),
                    byte_size=int(body.get("byte_size", 0)),
                    content_base64=body.get("content_base64", ""),
                ),
                status=HTTPStatus.CREATED,
            )
            return
        if parsed.path == "/api/box/automation/refresh-dashboard":
            self._send_json(hub_orchestrator_service.refresh_dashboard())
            return
        if parsed.path == "/api/box/automation/play-tts":
            self._send_json(tts_service.speak(body.get("message", "")))
            return
        if parsed.path == "/api/box/automation/announce":
            self._send_json(
                hub_orchestrator_service.announce(
                    body.get("message", ""),
                    body.get("priority", "normal"),
                )
            )
            return
        if parsed.path == "/api/box/automation/tv/wake":
            tv_control_service.wake_tv()
            self._send_json(tv_control_service.switch_input("dashboard"))
            return
        if parsed.path == "/api/box/voice/wake":
            self._send_json(hub_orchestrator_service.handle_voice_wake(body.get("transcript", "")))
            return
        if parsed.path == "/api/box/notifications/ack":
            self._send_json(home_api.acknowledge_notification(int(body["id"])))
            return
        if parsed.path == "/api/box/control-plane/sessions/open":
            self._send_json(
                home_api.open_session(
                    actor_name=body.get("actor_name", "anonymous"),
                    actor_role=body.get("actor_role", "guest"),
                    allowed_agents=body.get("allowed_agents", []),
                ),
                status=HTTPStatus.CREATED,
            )
            return
        if parsed.path == "/api/box/control-plane/commands/execute":
            self._send_json(
                home_api.execute_control_command(
                    session_id=body.get("session_id", ""),
                    agent_name=body.get("agent_name", ""),
                    action_name=body.get("action_name", ""),
                    payload=body.get("payload", {}),
                )
            )
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


def run(host: str | None = None, port: int | None = None) -> None:
    bind_host = host or settings.box_host
    bind_port = port or settings.box_port
    with ThreadingHTTPServer((bind_host, bind_port), BoxHandler) as server:
        print(f"Box service running on http://{bind_host}:{bind_port}")
        try:
            server.serve_forever()
        finally:
            railway_sync_service.stop()
