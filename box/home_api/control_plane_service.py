from __future__ import annotations

import uuid


class HomeControlPlaneService:
    def __init__(self, repository, calendar_engine, reminder_engine, info_engine, hub_orchestrator_service, openclaw_runtime, device_service) -> None:
        self.repository = repository
        self.calendar_engine = calendar_engine
        self.reminder_engine = reminder_engine
        self.info_engine = info_engine
        self.hub_orchestrator_service = hub_orchestrator_service
        self.openclaw_runtime = openclaw_runtime
        self.device_service = device_service

    def mobile_status(self) -> dict:
        return {
            "calendar_count": len(self.calendar_engine.list_items()),
            "reminder_count": len(self.reminder_engine.list_items()),
            "info_count": len(self.info_engine.list_items()),
            "notifications": self.repository.list_active_notifications(),
            "nodes": self.repository.list_nodes(),
            "sessions": self.repository.list_sessions(),
            "recent_commands": self.repository.list_recent_commands(8),
            "relay_deliveries": self.repository.list_relay_deliveries(8),
            "openclaw_tasks": self.repository.list_openclaw_tasks(8),
            "voice_input_sessions": self.repository.list_voice_input_sessions(8),
            "voice": self.hub_orchestrator_service.voice_status(),
            "hub": self.hub_orchestrator_service.hub_overview(),
            "device": self.device_service.get_device(),
        }

    def open_session(self, actor_name: str, actor_role: str, allowed_agents: list[str]) -> dict:
        session_id = str(uuid.uuid4())
        return self.repository.create_session(session_id, actor_name, actor_role, ",".join(allowed_agents))

    def control_plane_overview(self) -> dict:
        return {
            "nodes": self.repository.list_nodes(),
            "capabilities": self.repository.list_capabilities(),
            "sessions": self.repository.list_sessions(),
            "recent_commands": self.repository.list_recent_commands(12),
            "device_state": self.repository.list_device_states(),
            "devices": self.repository.list_devices(),
            "relay_deliveries": self.repository.list_relay_deliveries(12),
            "pairing": self.device_service.get_pairing_payload(),
            "hub": self.hub_orchestrator_service.hub_overview(),
            "openclaw": self.openclaw_runtime.overview(12),
            "voice_input_sessions": self.repository.list_voice_input_sessions(12),
        }

    def execute_control_command(self, session_id: str, agent_name: str, action_name: str, payload: dict) -> dict:
        return self.openclaw_runtime.dispatch_session(
            session_id=session_id,
            agent_name=agent_name,
            action_name=action_name,
            payload=payload,
            source="gateway",
        )
