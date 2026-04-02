from __future__ import annotations

from datetime import datetime, timedelta


class HubOrchestratorService:
    def __init__(self, repository, tts_service, tv_control_service, tv_dashboard_service, voice_session_timeout_seconds: int = 20) -> None:
        self.repository = repository
        self.tts_service = tts_service
        self.tv_control_service = tv_control_service
        self.tv_dashboard_service = tv_dashboard_service
        self.runtime = None
        self.voice_session_timeout_seconds = max(5, int(voice_session_timeout_seconds))

    def attach_runtime(self, runtime) -> None:
        self.runtime = runtime

    def bootstrap(self) -> None:
        defaults = {
            "home_mode": "family-hub",
            "dashboard_mode": "always_on",
            "voice_listener_state": "passive",
            "voice_listener_mode": "manual",
            "voice_wake_phrase": "hey lumi",
            "voice_wake_ack_message": "Hey master, Need any help",
            "voice_last_transcript": "",
            "voice_last_reply": "",
            "voice_last_intent": "idle",
            "voice_session_expires_at": "",
            "voice_command_mode": "inactive",
            "voice_command_mode_expires_at": "",
            "active_agent": "household-dashboard-agent",
            "orchestrator_last_route": "dashboard.idle",
        }
        for key, value in defaults.items():
            if not self.repository.get_device_state(key):
                self.repository.upsert_device_state(key, value)

    def hub_overview(self) -> dict:
        return self._hub_overview_direct({})

    def voice_status(self) -> dict:
        return self._voice_status_direct({})

    def refresh_dashboard(self) -> dict:
        if self.runtime:
            return self.runtime.dispatch_internal(
                "household-dashboard-agent",
                "dashboard.refresh",
                {},
                source="box-automation",
                actor_name="hub-orchestrator",
            )
        return self._refresh_dashboard_direct({})

    def announce(self, message: str, priority: str = "normal") -> dict:
        if self.runtime:
            return self.runtime.dispatch_internal(
                "voice-automation-agent",
                "announce.play",
                {"message": message, "priority": priority},
                source="box-automation",
                actor_name="hub-orchestrator",
            )
        return self._announce_direct({"message": message, "priority": priority})

    def handle_voice_wake(self, transcript: str) -> dict:
        return self._handle_voice_wake_direct({"transcript": transcript})

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

    def _hub_overview_direct(self, payload: dict) -> dict:
        dashboard = self.tv_dashboard_service.build_payload()
        states = self.repository.list_device_states()
        return {
            "ok": True,
            "home_mode": states.get("home_mode", "family-hub"),
            "dashboard_mode": states.get("dashboard_mode", "always_on"),
            "voice": self._voice_status_direct({}),
            "active_agent": states.get("active_agent", "household-dashboard-agent"),
            "last_route": states.get("orchestrator_last_route", "dashboard.idle"),
            "notifications": dashboard.get("notifications", []),
            "system_tiles": dashboard.get("system_tiles", []),
        }

    def _voice_status_direct(self, payload: dict) -> dict:
        states = self.repository.list_device_states()
        return {
            "ok": True,
            "listener_state": states.get("voice_listener_state", "passive"),
            "wake_phrase": states.get("voice_wake_phrase", "hey lumi"),
            "wake_ack_message": states.get("voice_wake_ack_message", "Hey master, Need any help"),
            "listener_mode": states.get("voice_listener_mode", "manual"),
            "last_transcript": states.get("voice_last_transcript", ""),
            "last_reply": states.get("voice_last_reply", ""),
            "last_intent": states.get("voice_last_intent", "idle"),
            "session_active": self._is_voice_session_active(states),
            "command_mode_active": self._is_command_mode_active(states),
            "command_mode_expires_at": states.get("voice_command_mode_expires_at", ""),
            "session_expires_at": states.get("voice_session_expires_at", ""),
            "active_agent": states.get("active_agent", "household-dashboard-agent"),
            "pending_task": states.get("voice_pending_task_json", ""),
        }

    def _refresh_dashboard_direct(self, payload: dict) -> dict:
        self.repository.upsert_device_state("dashboard_mode", "always_on")
        self.repository.upsert_device_state("active_agent", "household-dashboard-agent")
        self.repository.upsert_device_state("orchestrator_last_route", "dashboard.refresh")
        return {"ok": True, "dashboard_mode": "always_on"}

    def _announce_direct(self, payload: dict) -> dict:
        message = payload.get("message", "")
        priority = payload.get("priority", "normal")
        suppress_until = datetime.now() + timedelta(seconds=min(8, max(3, len((message or "").split()) // 2 + 2)))
        self.repository.upsert_device_state("voice_suppress_until", suppress_until.isoformat(timespec="seconds"))
        spoken = self.tts_service.speak(message)
        spoken_text = spoken.get("spoken", message)
        self.repository.upsert_device_state("active_agent", "voice-automation-agent")
        self.repository.upsert_device_state("voice_listener_state", "speaking")
        self.repository.upsert_device_state("voice_last_reply", spoken_text)
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
        listener_mode = self.repository.get_device_state("voice_listener_mode", "manual")
        self.repository.upsert_device_state("voice_listener_state", "listening" if listener_mode == "continuous" else "passive")
        return {
            "ok": True,
            "spoken": spoken_text,
            "priority": priority,
            "listener_state": "listening" if listener_mode == "continuous" else "passive",
        }

    def _wake_tv_direct(self, payload: dict) -> dict:
        self.tv_control_service.wake_tv()
        result = self.tv_control_service.switch_input("dashboard")
        self.repository.upsert_device_state("active_agent", "voice-automation-agent")
        self.repository.upsert_device_state("orchestrator_last_route", "tv.wake")
        return {"ok": True, **result}

    def _handle_voice_wake_direct(self, payload: dict) -> dict:
        normalized = " ".join(payload.get("transcript", "").strip().split())
        self.repository.upsert_device_state("voice_last_transcript", normalized)
        self.repository.upsert_device_state("voice_listener_state", "active")
        wake_phrase = self.repository.get_device_state("voice_wake_phrase", "hey lumi")
        wake_ack_message = self.repository.get_device_state("voice_wake_ack_message", "Hey master, Need any help")
        states = self.repository.list_device_states()
        session_active = self._is_voice_session_active(states)
        command_mode_active = self._is_command_mode_active(states)
        normalized_for_route = self._strip_wake_phrase(normalized, wake_phrase)
        has_wake_phrase = bool(normalized) and normalized_for_route != normalized
        normalized_intent_target = normalized_for_route or normalized

        if normalized and has_wake_phrase and normalized_for_route == "":
            intent = "voice.wake_ack"
            self.repository.upsert_device_state("voice_last_intent", intent)
            self.tv_control_service.wake_tv()
            self.tv_control_service.switch_input("dashboard")
            self.repository.upsert_device_state("dashboard_mode", "wake_overlay")
            self.repository.upsert_device_state("voice_last_wake_at", datetime.now().isoformat(timespec="seconds"))
            self._open_voice_session()
            self.repository.upsert_device_state("active_agent", "voice-automation-agent")
            self.repository.upsert_device_state("orchestrator_last_route", intent)
            result = self.announce(wake_ack_message, priority="normal") if self.runtime else self._announce_direct({"message": wake_ack_message, "priority": "normal"})
            return {
                "ok": True,
                "intent": intent,
                "agent": "voice-automation-agent",
                "result": {
                    "tv": {"power": "on", "input": "dashboard"},
                    "voice": result,
                },
                "handled_at": datetime.now().isoformat(timespec="seconds"),
            }

        if normalized and has_wake_phrase and self._detect_intent(normalized_intent_target) == "command.mode.enter":
            self._open_voice_session()
            self._enter_command_mode()
            self.repository.upsert_device_state("voice_last_intent", "command.mode.enter")
            self.repository.upsert_device_state("active_agent", "home-orchestrator-agent")
            self.repository.upsert_device_state("orchestrator_last_route", "command.mode.enter")
            result = self.announce("Command mode is on. Tell me what to handle.", priority="normal") if self.runtime else self._announce_direct({"message": "Command mode is on. Tell me what to handle.", "priority": "normal"})
            return {
                "ok": True,
                "intent": "command.mode.enter",
                "agent": "home-orchestrator-agent",
                "result": result,
                "handled_at": datetime.now().isoformat(timespec="seconds"),
            }

        if (normalized and not has_wake_phrase and not session_active and not command_mode_active):
            self.repository.upsert_device_state("voice_last_intent", "voice.await_wake")
            self.repository.upsert_device_state("orchestrator_last_route", "voice.await_wake")
            return {
                "ok": True,
                "intent": "voice.await_wake",
                "agent": "voice-automation-agent",
                "result": {"ok": True, "ignored": True, "message": "Wake phrase required"},
                "handled_at": datetime.now().isoformat(timespec="seconds"),
            }

        intent = self._detect_intent(normalized_intent_target)
        self.repository.upsert_device_state("voice_last_intent", intent)
        if normalized:
            self._open_voice_session()

        if intent == "command.mode.exit":
            self._exit_command_mode()
            self.repository.upsert_device_state("active_agent", "home-orchestrator-agent")
            self.repository.upsert_device_state("orchestrator_last_route", "command.mode.exit")
            result = self.announce("Command mode is off.", priority="normal") if self.runtime else self._announce_direct({"message": "Command mode is off.", "priority": "normal"})
            return {
                "ok": True,
                "intent": "command.mode.exit",
                "agent": "home-orchestrator-agent",
                "result": result,
                "handled_at": datetime.now().isoformat(timespec="seconds"),
            }

        if intent == "tv.wake":
            agent = "voice-automation-agent"
            action = "tv.wake"
            action_payload = {}
        elif intent == "dashboard.refresh":
            agent = "household-dashboard-agent"
            action = "dashboard.refresh"
            action_payload = {}
        elif intent == "voice.announce":
            agent = "voice-automation-agent"
            action = "announce.play"
            action_payload = {"message": normalized_intent_target or "Family reminder incoming", "priority": "high"}
        else:
            agent = "home-orchestrator-agent"
            action = "orchestrator.listen"
            action_payload = {"transcript": normalized_intent_target}

        if self.runtime:
            result = self.runtime.dispatch_internal(
                agent,
                action,
                action_payload,
                source="voice-wake",
                actor_name="voice-listener",
            )
        else:
            result = {
                "ok": True,
                "accepted": True,
                "message": normalized or "Listening for a family task",
            }

        self.repository.upsert_device_state("active_agent", agent)
        self.repository.upsert_device_state("orchestrator_last_route", intent)
        return {
            "ok": True,
            "intent": intent,
            "agent": agent,
            "result": result,
            "handled_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _orchestrator_listen_direct(self, payload: dict) -> dict:
        transcript = payload.get("transcript", "")
        if self.runtime:
            return self.runtime.dispatch_internal(
                "family-intake-agent",
                "intake.voice",
                {"text": transcript},
                source="orchestrator-listen",
                actor_name="home-orchestrator-agent",
            )
        return {
            "ok": True,
            "accepted": True,
            "message": transcript or "Listening for a family task",
        }

    def _open_voice_session(self) -> None:
        expires_at = datetime.now() + timedelta(seconds=self.voice_session_timeout_seconds)
        self.repository.upsert_device_state("voice_session_expires_at", expires_at.isoformat(timespec="seconds"))
        if self._is_command_mode_active():
            self.repository.upsert_device_state("voice_command_mode_expires_at", expires_at.isoformat(timespec="seconds"))

    def _is_voice_session_active(self, states: dict | None = None) -> bool:
        current_states = states or self.repository.list_device_states()
        raw = current_states.get("voice_session_expires_at", "")
        if not raw:
            return False
        try:
            expires_at = datetime.fromisoformat(raw)
        except ValueError:
            return False
        return expires_at >= datetime.now()

    def _is_command_mode_active(self, states: dict | None = None) -> bool:
        current_states = states or self.repository.list_device_states()
        if current_states.get("voice_command_mode", "inactive") != "active":
            return False
        raw = current_states.get("voice_command_mode_expires_at", "")
        if not raw:
            return False
        try:
            expires_at = datetime.fromisoformat(raw)
        except ValueError:
            return False
        if expires_at < datetime.now():
            self._exit_command_mode()
            return False
        return True

    def _enter_command_mode(self) -> None:
        expires_at = datetime.now() + timedelta(seconds=self.voice_session_timeout_seconds)
        self.repository.upsert_device_state("voice_command_mode", "active")
        self.repository.upsert_device_state("voice_command_mode_expires_at", expires_at.isoformat(timespec="seconds"))
        self.repository.upsert_device_state("dashboard_mode", "command_mode")
        self.repository.upsert_device_state("voice_last_wake_at", datetime.now().isoformat(timespec="seconds"))

    def _exit_command_mode(self) -> None:
        self.repository.upsert_device_state("voice_command_mode", "inactive")
        self.repository.upsert_device_state("voice_command_mode_expires_at", "")
        if self.repository.get_device_state("dashboard_mode", "always_on") == "command_mode":
            self.repository.upsert_device_state("dashboard_mode", "always_on")

    def _looks_like_direct_command(self, transcript: str) -> bool:
        lower = (transcript or "").lower()
        command_markers = (
            "remind me",
            "remember to",
            "need to",
            "buy ",
            "call ",
            "book ",
            "schedule ",
            "pick up",
            "drop off",
            "refresh dashboard",
            "wake tv",
            "visit ",
            "go to ",
            "send ",
            "email ",
        )
        return any(marker in lower for marker in command_markers)

    def _normalize_voice_text(self, text: str) -> str:
        normalized = (text or "").lower()
        for char in [",", ".", "?", "!", ":", ";"]:
            normalized = normalized.replace(char, " ")
        return " ".join(normalized.split())

    def _wake_phrase_candidates(self, wake_phrase: str) -> list[str]:
        phrase = self._normalize_voice_text(wake_phrase or "hey lumi")
        candidates = [phrase]
        if "lumi" in phrase:
            candidates.extend(
                [
                    "hey lumi",
                    "hei lumi",
                    "hi lumi",
                    "hello lumi",
                    "hey loomy",
                    "hi loomy",
                ]
            )
        seen: list[str] = []
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.append(candidate)
        return seen

    def _strip_wake_phrase(self, transcript: str, wake_phrase: str) -> str:
        normalized = self._normalize_voice_text(transcript)
        for phrase in self._wake_phrase_candidates(wake_phrase):
            if normalized == phrase:
                return ""
            if normalized.startswith(phrase + " "):
                return normalized[len(phrase):].strip()
        return transcript

    def _detect_intent(self, transcript: str) -> str:
        lower = transcript.lower()
        if any(keyword in lower for keyword in ("exit command mode", "leave command mode", "stop command mode")):
            return "command.mode.exit"
        if any(keyword in lower for keyword in ("turn to command mode", "enter command mode", "start command mode", "command mode")):
            return "command.mode.enter"
        if any(keyword in lower for keyword in ("wake tv", "open tv", "turn on tv", "tv", "screen", "display")):
            return "tv.wake"
        if any(keyword in lower for keyword in ("refresh dashboard", "show dashboard", "dashboard", "board")):
            return "dashboard.refresh"
        if any(keyword in lower for keyword in ("announce", "broadcast", "speak")):
            return "voice.announce"
        return "orchestrator.listen"
