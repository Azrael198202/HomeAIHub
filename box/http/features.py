from __future__ import annotations

from http import HTTPStatus

from box.http.router import RouteRegistry
from shared.config.settings import settings


def register_static_routes(registry: RouteRegistry, app) -> None:
    registry.add("GET", "/dashboard", lambda handler, body: _serve_dashboard(handler, app))
    registry.add("GET", "/health", lambda handler, body: ({"ok": True, "service": "box"}, HTTPStatus.OK))


def register_read_routes(registry: RouteRegistry, app) -> None:
    registry.add("GET", "/api/box/dashboard", lambda handler, body: app.home_api.dashboard())
    registry.add("GET", "/api/box/mobile-status", lambda handler, body: app.home_api.mobile_status())
    registry.add("GET", "/api/box/nodes", lambda handler, body: {"items": app.repository.list_nodes()})
    registry.add("GET", "/api/box/device", lambda handler, body: app.home_api.get_device())
    registry.add("GET", "/api/box/device/external-status", lambda handler, body: app.home_api.external_box_status())
    registry.add("GET", "/api/box/pairing/payload", lambda handler, body: app.home_api.get_pairing_payload())
    registry.add("GET", "/api/box/control-plane/overview", lambda handler, body: app.home_api.control_plane_overview())
    registry.add("GET", "/api/box/control-plane/sessions", lambda handler, body: {"items": app.repository.list_sessions()})
    registry.add("GET", "/api/box/control-plane/commands", lambda handler, body: {"items": app.repository.list_recent_commands(20)})
    registry.add("GET", "/api/box/openclaw/overview", lambda handler, body: app.openclaw_runtime.overview(20))
    registry.add("GET", "/api/box/hub/overview", lambda handler, body: app.hub_orchestrator_service.hub_overview())
    registry.add("GET", "/api/box/voice/status", lambda handler, body: app.hub_orchestrator_service.voice_status())
    registry.add("GET", "/api/box/voice/input/status", lambda handler, body: app.voice_input_service.status())
    registry.add("GET", "/api/box/voice/input/devices", lambda handler, body: app.voice_input_service.list_devices())
    registry.add("GET", "/api/box/voice/input/sessions", lambda handler, body: app.voice_input_service.list_sessions(20))
    registry.add("GET", "/api/box/voice/input/transcripts/latest", lambda handler, body: app.voice_input_service.latest_transcript())
    registry.add("GET", "/api/box/voice/input/listener/status", lambda handler, body: app.voice_input_service.status())


def register_write_routes(registry: RouteRegistry, app) -> None:
    registry.add(
        "POST",
        "/api/box/device/claim",
        lambda handler, body: app.home_api.claim_device(
            actor_user_id=body.get("actor_user_id", "user-demo"),
            actor_name=body.get("actor_name", "Owner"),
            family_name=body.get("family_name", "My Family"),
            claim_token=body.get("claim_token", ""),
        ),
    )
    registry.add(
        "POST",
        "/api/box/device/unbind",
        lambda handler, body: app.home_api.unbind_device(
            actor_user_id=body.get("actor_user_id", "user-demo"),
            actor_name=body.get("actor_name", "Owner"),
        ),
    )
    registry.add("POST", "/api/box/device/reset", lambda handler, body: app.home_api.reset_pairing())
    registry.add("POST", "/api/box/intake/manual", lambda handler, body: (app.home_api.ingest_manual(body.get("text", "")), HTTPStatus.CREATED))
    registry.add("POST", "/api/box/intake/screenshot", lambda handler, body: (app.home_api.ingest_screenshot(body.get("text", "")), HTTPStatus.CREATED))
    registry.add("POST", "/api/box/intake/photo", lambda handler, body: (app.home_api.ingest_photo(body.get("text", "")), HTTPStatus.CREATED))
    registry.add("POST", "/api/box/intake/voice", lambda handler, body: (app.home_api.ingest_voice(body.get("text", "")), HTTPStatus.CREATED))
    registry.add(
        "POST",
        "/api/box/relay/receive",
        lambda handler, body: (
            app.home_api.receive_relay_delivery(
                relay_id=body.get("relay_id", ""),
                source_channel=body.get("source_channel", "railway"),
                content_kind=body.get("content_kind", ""),
                text=body.get("text", ""),
                filename=body.get("filename", ""),
                mime_type=body.get("mime_type", ""),
                byte_size=int(body.get("byte_size", 0)),
                content_base64=body.get("content_base64", ""),
            ),
            HTTPStatus.CREATED,
        ),
    )
    registry.add("POST", "/api/box/automation/refresh-dashboard", lambda handler, body: app.hub_orchestrator_service.refresh_dashboard())
    registry.add("POST", "/api/box/automation/play-tts", lambda handler, body: app.tts_service.speak(body.get("message", "")))
    registry.add(
        "POST",
        "/api/box/automation/announce",
        lambda handler, body: app.hub_orchestrator_service.announce(body.get("message", ""), body.get("priority", "normal")),
    )
    registry.add(
        "POST",
        "/api/box/automation/tv/wake",
        lambda handler, body: _wake_tv(app),
    )
    registry.add("POST", "/api/box/voice/wake", lambda handler, body: app.hub_orchestrator_service.handle_voice_wake(body.get("transcript", "")))
    registry.add(
        "POST",
        "/api/box/voice/input/transcript",
        lambda handler, body: (app.voice_input_service.submit_transcript(body.get("transcript", "")), HTTPStatus.CREATED),
    )
    registry.add(
        "POST",
        "/api/box/voice/input/audio",
        lambda handler, body: (
            app.voice_input_service.submit_audio(
                content_base64=body.get("content_base64", ""),
                filename=body.get("filename", "voice-input.txt"),
                mime_type=body.get("mime_type", "application/octet-stream"),
            ),
            HTTPStatus.CREATED,
        ),
    )
    registry.add(
        "POST",
        "/api/box/voice/input/capture",
        lambda handler, body: (
            app.voice_input_service.capture_from_microphone(
                duration_seconds=int(body.get("duration_seconds", settings.mic_duration_seconds)),
                device_index=int(body.get("device_index", settings.mic_device_index)),
            ),
            HTTPStatus.CREATED,
        ),
    )
    registry.add(
        "POST",
        "/api/box/voice/input/listener/start",
        lambda handler, body: (
            app.voice_input_service.start_listener(device_index=int(body.get("device_index", settings.mic_device_index))),
            HTTPStatus.CREATED,
        ),
    )
    registry.add("POST", "/api/box/voice/input/listener/stop", lambda handler, body: app.voice_input_service.stop_listener())
    registry.add("POST", "/api/box/notifications/ack", lambda handler, body: app.home_api.acknowledge_notification(int(body["id"])))
    registry.add(
        "POST",
        "/api/box/control-plane/sessions/open",
        lambda handler, body: (
            app.home_api.open_session(
                actor_name=body.get("actor_name", "anonymous"),
                actor_role=body.get("actor_role", "guest"),
                allowed_agents=body.get("allowed_agents", []),
            ),
            HTTPStatus.CREATED,
        ),
    )
    registry.add(
        "POST",
        "/api/box/control-plane/commands/execute",
        lambda handler, body: app.home_api.execute_control_command(
            session_id=body.get("session_id", ""),
            agent_name=body.get("agent_name", ""),
            action_name=body.get("action_name", ""),
            payload=body.get("payload", {}),
        ),
    )


def build_box_registry(app) -> RouteRegistry:
    registry = RouteRegistry()
    register_static_routes(registry, app)
    register_read_routes(registry, app)
    register_write_routes(registry, app)
    return registry


def _serve_dashboard(handler, app):
    from box.http.router import content_type_for, send_file

    send_file(handler, app.tv_dashboard_web_dir, "index.html", content_type_for("index.html"))
    return None


def _wake_tv(app) -> dict:
    app.tv_control_service.wake_tv()
    return app.tv_control_service.switch_input("dashboard")
