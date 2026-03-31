from __future__ import annotations

from datetime import datetime


class HubOrchestratorService:
    def __init__(self, repository, tts_service, tv_control_service, tv_dashboard_service) -> None:
        self.repository = repository
        self.tts_service = tts_service
        self.tv_control_service = tv_control_service
        self.tv_dashboard_service = tv_dashboard_service

    def bootstrap(self) -> None:
        defaults = {
            "home_mode": "family-hub",
            "dashboard_mode": "always_on",
            "voice_listener_state": "passive",
            "voice_wake_phrase": "Hey Home",
            "voice_last_transcript": "",
            "voice_last_intent": "idle",
            "active_agent": "household-dashboard-agent",
            "orchestrator_last_route": "dashboard.idle",
        }
        for key, value in defaults.items():
            if not self.repository.get_device_state(key):
                self.repository.upsert_device_state(key, value)

    def hub_overview(self) -> dict:
        dashboard = self.tv_dashboard_service.build_payload()
        states = self.repository.list_device_states()
        return {
            "home_mode": states.get("home_mode", "family-hub"),
            "dashboard_mode": states.get("dashboard_mode", "always_on"),
            "voice": self.voice_status(),
            "active_agent": states.get("active_agent", "household-dashboard-agent"),
            "last_route": states.get("orchestrator_last_route", "dashboard.idle"),
            "notifications": dashboard.get("notifications", []),
            "system_tiles": dashboard.get("system_tiles", []),
        }

    def voice_status(self) -> dict:
        states = self.repository.list_device_states()
        return {
            "listener_state": states.get("voice_listener_state", "passive"),
            "wake_phrase": states.get("voice_wake_phrase", "Hey Home"),
            "last_transcript": states.get("voice_last_transcript", ""),
            "last_intent": states.get("voice_last_intent", "idle"),
            "active_agent": states.get("active_agent", "household-dashboard-agent"),
        }

    def refresh_dashboard(self) -> dict:
        self.repository.upsert_device_state("dashboard_mode", "always_on")
        self.repository.upsert_device_state("active_agent", "household-dashboard-agent")
        self.repository.upsert_device_state("orchestrator_last_route", "dashboard.refresh")
        return {"ok": True, "dashboard_mode": "always_on"}

    def announce(self, message: str, priority: str = "normal") -> dict:
        spoken = self.tts_service.speak(message)
        self.repository.upsert_device_state("active_agent", "voice-automation-agent")
        self.repository.upsert_device_state("voice_listener_state", "speaking")
        self.repository.upsert_device_state("orchestrator_last_route", "voice.announce")
        if priority in {"high", "urgent"}:
            self.repository.create_notification(
                {
                    "kind": "spoken_alert",
                    "title": "Voice Alert",
                    "person": "HomeAIHub",
                    "location": "Living Room",
                    "message": message,
                    "event_id": None,
                }
            )
        return {
            "ok": True,
            "spoken": spoken.get("spoken", message),
            "priority": priority,
            "listener_state": "speaking",
        }

    def handle_voice_wake(self, transcript: str) -> dict:
        normalized = " ".join(transcript.strip().split())
        self.repository.upsert_device_state("voice_last_transcript", normalized)
        self.repository.upsert_device_state("voice_listener_state", "active")
        intent = self._detect_intent(normalized)
        self.repository.upsert_device_state("voice_last_intent", intent)

        if intent == "tv.wake":
            self.tv_control_service.wake_tv()
            result = self.tv_control_service.switch_input("dashboard")
            agent = "voice-automation-agent"
        elif intent == "dashboard.refresh":
            result = self.refresh_dashboard()
            agent = "household-dashboard-agent"
        elif intent == "voice.announce":
            message = normalized or "Family reminder incoming"
            result = self.announce(message, priority="high")
            agent = "voice-automation-agent"
        else:
            result = {
                "ok": True,
                "accepted": True,
                "message": normalized or "Listening for a family task",
            }
            agent = "home-orchestrator-agent"

        self.repository.upsert_device_state("active_agent", agent)
        self.repository.upsert_device_state("orchestrator_last_route", intent)
        return {
            "ok": True,
            "intent": intent,
            "agent": agent,
            "result": result,
            "handled_at": datetime.now().isoformat(timespec="seconds"),
        }

    def execute_capability(self, action_name: str, payload: dict) -> dict:
        if action_name == "hub.status":
            return self.hub_overview()
        if action_name == "voice.status":
            return self.voice_status()
        if action_name == "voice.wake":
            return self.handle_voice_wake(payload.get("transcript", ""))
        if action_name == "announce.play":
            return self.announce(payload.get("message", ""), payload.get("priority", "normal"))
        if action_name == "dashboard.refresh":
            return self.refresh_dashboard()
        return {"ok": False, "error": "orchestrator_action_not_supported"}

    def _detect_intent(self, transcript: str) -> str:
        lower = transcript.lower()
        if any(keyword in lower for keyword in ("wake tv", "open tv", "turn on tv", "tv", "screen", "display")):
            return "tv.wake"
        if any(keyword in lower for keyword in ("refresh dashboard", "show dashboard", "dashboard", "board")):
            return "dashboard.refresh"
        if any(keyword in lower for keyword in ("announce", "broadcast", "remind", "speak")):
            return "voice.announce"
        return "orchestrator.listen"
