from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timedelta

from shared.config.settings import settings


DEFAULT_DEVICE_ID = "hub-demo-001"
DEFAULT_DEVICE_NAME = "HomeAIHub Box"
DEFAULT_FAMILY_ID = "family-demo"


def build_seed_data() -> list[dict]:
    now = datetime.now().replace(second=0, microsecond=0)
    return [
        {
            "title": "\u4f1a\u8bae",
            "category": "calendar",
            "person": "\u7238\u7238",
            "start_at": now.replace(hour=9, minute=0).isoformat(timespec="minutes"),
            "due_at": now.replace(hour=9, minute=0).isoformat(timespec="minutes"),
            "location": "\u516c\u53f8",
            "summary": "\u7238\u7238 | \u4f1a\u8bae | \u516c\u53f8",
            "priority": "normal",
            "source_type": "seed",
            "source_text": "09:00 \u7238\u7238 \u4f1a\u8bae",
            "status": "active",
        },
        {
            "title": "\u770b\u7259",
            "category": "calendar",
            "person": "\u5988\u5988",
            "start_at": (now + timedelta(minutes=15)).isoformat(timespec="minutes"),
            "due_at": (now + timedelta(minutes=15)).isoformat(timespec="minutes"),
            "location": "\u533b\u9662",
            "summary": "\u5988\u5988 | \u770b\u7259 | \u533b\u9662",
            "priority": "high",
            "source_type": "seed",
            "source_text": "15 \u5206\u949f\u540e\u5988\u5988\u53bb\u533b\u9662\u770b\u7259",
            "status": "active",
        },
        {
            "title": "\u94a2\u7434\u8bfe",
            "category": "calendar",
            "person": "\u5c0f\u5b69",
            "start_at": now.replace(hour=16, minute=0).isoformat(timespec="minutes"),
            "due_at": now.replace(hour=16, minute=0).isoformat(timespec="minutes"),
            "location": "\u94a2\u7434\u6559\u5ba4",
            "summary": "\u5c0f\u5b69 | \u94a2\u7434\u8bfe | \u94a2\u7434\u6559\u5ba4",
            "priority": "normal",
            "source_type": "seed",
            "source_text": "16:00 \u5c0f\u5b69 \u94a2\u7434\u8bfe",
            "status": "active",
        },
        {
            "title": "\u4eca\u65e5\u622a\u6b62\u7f34\u8d39",
            "category": "reminder",
            "person": "\u5168\u5bb6",
            "start_at": "",
            "due_at": now.replace(hour=20, minute=0).isoformat(timespec="minutes"),
            "location": "",
            "summary": "\u5168\u5bb6 | \u4eca\u65e5\u622a\u6b62\u7f34\u8d39",
            "priority": "normal",
            "source_type": "seed",
            "source_text": "\u4eca\u5929\u622a\u6b62\u7f34\u8d39",
            "status": "active",
        },
        {
            "title": "\u5b66\u6821\u901a\u77e5\u66f4\u65b0",
            "category": "info",
            "person": "\u5168\u5bb6",
            "start_at": "",
            "due_at": "",
            "location": "\u5b66\u6821",
            "summary": "\u5b66\u6821\u901a\u77e5\u66f4\u65b0",
            "priority": "low",
            "source_type": "seed",
            "source_text": "\u5b66\u6821\u901a\u77e5\u66f4\u65b0",
            "status": "active",
        },
        {
            "title": "\u5feb\u9012\u5df2\u5230\u8fbe",
            "category": "info",
            "person": "\u5168\u5bb6",
            "start_at": "",
            "due_at": "",
            "location": "\u5bb6\u91cc",
            "summary": "\u5feb\u9012\u5df2\u5230\u8fbe",
            "priority": "low",
            "source_type": "seed",
            "source_text": "\u5feb\u9012\u5df2\u5230\u8fbe",
            "status": "active",
        },
    ]


class HomeAPI:
    def __init__(
        self,
        repository,
        ocr_service,
        parser_service,
        calendar_engine,
        reminder_engine,
        info_engine,
        tts_service,
        tv_control_service,
        tv_dashboard_service,
    ) -> None:
        self.repository = repository
        self.ocr_service = ocr_service
        self.parser_service = parser_service
        self.calendar_engine = calendar_engine
        self.reminder_engine = reminder_engine
        self.info_engine = info_engine
        self.tts_service = tts_service
        self.tv_control_service = tv_control_service
        self.tv_dashboard_service = tv_dashboard_service

    def bootstrap(self) -> None:
        if self.repository.is_empty():
            self.repository.seed_events(build_seed_data())
        self.repository.register_node("mini-host", "node")
        self.repository.register_node("tv-dashboard", "device")
        for capability in (
            "ocr.recognize",
            "calendar.query",
            "reminder.scan",
            "info.query",
            "tts.play",
            "tv.wake",
            "tv.dashboard.refresh",
            "tv.dashboard.render",
            "device.claim",
            "device.status",
        ):
            self.repository.register_capability("mini-host", capability)
        self.repository.register_capability("tv-dashboard", "display.render")
        self.repository.register_capability("tv-dashboard", "display.popup")
        self._ensure_device_record()

    def _ensure_device_record(self) -> None:
        existing = self.repository.get_device(DEFAULT_DEVICE_ID)
        if existing:
            self.repository.update_device_last_seen(DEFAULT_DEVICE_ID)
            return
        claim_token, expires_at = self._new_claim()
        self.repository.create_or_update_device(
            {
                "device_id": DEFAULT_DEVICE_ID,
                "device_name": DEFAULT_DEVICE_NAME,
                "device_secret": secrets.token_hex(16),
                "claim_token": claim_token,
                "claim_expires_at": expires_at,
                "status": "pending_claim",
            }
        )

    def _new_claim(self) -> tuple[str, str]:
        token = secrets.token_urlsafe(10)
        expires_at = (datetime.now() + timedelta(minutes=30)).isoformat(timespec="seconds")
        return token, expires_at

    def get_device(self) -> dict:
        self.repository.update_device_last_seen(DEFAULT_DEVICE_ID)
        device = self.repository.get_device(DEFAULT_DEVICE_ID) or {}
        pairing_payload = self.get_pairing_payload()
        return {
            "device": device,
            "pairing": pairing_payload,
            "online": True,
            "box_service_healthy": True,
        }

    def get_pairing_payload(self) -> dict:
        device = self.repository.get_device(DEFAULT_DEVICE_ID) or {}
        claim_url = f"{settings.box_base_url}/claim?device_id={DEFAULT_DEVICE_ID}&claim_token={device.get('claim_token', '')}"
        return {
            "device_id": DEFAULT_DEVICE_ID,
            "device_name": device.get("device_name", DEFAULT_DEVICE_NAME),
            "claim_token": device.get("claim_token", ""),
            "claim_expires_at": device.get("claim_expires_at", ""),
            "claim_url": claim_url,
            "qr_payload": {
                "type": "homeaihub-claim",
                "device_id": DEFAULT_DEVICE_ID,
                "claim_token": device.get("claim_token", ""),
                "server": settings.box_base_url,
            },
            "paired": device.get("status") == "paired",
        }

    def claim_device(self, actor_user_id: str, actor_name: str, family_name: str, claim_token: str) -> dict:
        device = self.repository.get_device(DEFAULT_DEVICE_ID)
        if not device:
            return {"ok": False, "error": "device_not_found"}
        if device["status"] == "paired":
            self.repository.log_device_claim(DEFAULT_DEVICE_ID, claim_token, actor_user_id, actor_name, "already_paired")
            return {"ok": False, "error": "device_already_paired"}
        if claim_token != device["claim_token"]:
            self.repository.log_device_claim(DEFAULT_DEVICE_ID, claim_token, actor_user_id, actor_name, "invalid_token")
            return {"ok": False, "error": "invalid_claim_token"}
        if datetime.fromisoformat(device["claim_expires_at"]) < datetime.now():
            self.repository.log_device_claim(DEFAULT_DEVICE_ID, claim_token, actor_user_id, actor_name, "expired")
            return {"ok": False, "error": "claim_token_expired"}

        family_id = DEFAULT_FAMILY_ID
        paired_at = datetime.now().isoformat(timespec="seconds")
        self.repository.bind_device(
            device_id=DEFAULT_DEVICE_ID,
            family_id=family_id,
            owner_user_id=actor_user_id,
            owner_name=actor_name,
            status="paired",
            paired_at=paired_at,
        )
        self.repository.log_device_claim(DEFAULT_DEVICE_ID, claim_token, actor_user_id, actor_name, "claimed")
        self.repository.create_notification(
            {
                "kind": "device_claimed",
                "title": "Device Claimed",
                "person": actor_name,
                "location": family_name,
                "message": f"{actor_name} paired {DEFAULT_DEVICE_NAME}",
                "event_id": None,
            }
        )
        return {
            "ok": True,
            "device_id": DEFAULT_DEVICE_ID,
            "family_id": family_id,
            "family_name": family_name,
            "owner_user_id": actor_user_id,
            "owner_name": actor_name,
            "paired_at": paired_at,
        }

    def unbind_device(self, actor_user_id: str, actor_name: str) -> dict:
        device = self.repository.get_device(DEFAULT_DEVICE_ID)
        if not device:
            return {"ok": False, "error": "device_not_found"}
        if device["status"] != "paired":
            return {"ok": False, "error": "device_not_paired"}

        claim_token, expires_at = self._new_claim()
        self.repository.create_or_update_device(
            {
                "device_id": DEFAULT_DEVICE_ID,
                "device_name": device["device_name"],
                "device_secret": device["device_secret"],
                "claim_token": claim_token,
                "claim_expires_at": expires_at,
                "status": "pending_claim",
                "family_id": "",
                "owner_user_id": "",
                "owner_name": "",
                "paired_at": "",
            }
        )
        self.repository.log_device_claim(DEFAULT_DEVICE_ID, claim_token, actor_user_id, actor_name, "unbound")
        self.repository.create_notification(
            {
                "kind": "device_unbound",
                "title": "Device Unbound",
                "person": actor_name,
                "location": "",
                "message": f"{actor_name} removed the device binding",
                "event_id": None,
            }
        )
        return {
            "ok": True,
            "device_id": DEFAULT_DEVICE_ID,
            "status": "pending_claim",
            "pairing": self.get_pairing_payload(),
        }

    def reset_pairing(self) -> dict:
        device = self.repository.get_device(DEFAULT_DEVICE_ID)
        if not device:
            return {"ok": False, "error": "device_not_found"}
        claim_token, expires_at = self._new_claim()
        self.repository.create_or_update_device(
            {
                "device_id": DEFAULT_DEVICE_ID,
                "device_name": device["device_name"],
                "device_secret": device["device_secret"],
                "claim_token": claim_token,
                "claim_expires_at": expires_at,
                "status": "pending_claim",
                "family_id": "",
                "owner_user_id": "",
                "owner_name": "",
                "paired_at": "",
            }
        )
        return {"ok": True, "pairing": self.get_pairing_payload()}

    def ingest_manual(self, text: str) -> dict:
        return self._create_event(text=text, source_type="manual")

    def ingest_screenshot(self, text: str) -> dict:
        recognized = self.ocr_service.recognize(text)
        return self._create_event(text=recognized, source_type="screenshot")

    def _create_event(self, text: str, source_type: str) -> dict:
        parsed = self.parser_service.parse(text, source_type)
        event_id = self.repository.create_event(
            {
                "title": parsed.title,
                "category": parsed.category,
                "person": parsed.person,
                "start_at": parsed.start_at.isoformat(timespec="minutes") if parsed.start_at else "",
                "due_at": parsed.due_at.isoformat(timespec="minutes") if parsed.due_at else "",
                "location": parsed.location,
                "summary": parsed.summary,
                "priority": parsed.priority,
                "source_type": parsed.source_type,
                "source_text": parsed.source_text,
                "status": "active",
            }
        )
        if parsed.requires_confirmation:
            self.repository.create_notification(
                {
                    "kind": "recognition_confirmation",
                    "title": "New Event Detected",
                    "person": parsed.person,
                    "location": parsed.location,
                    "message": parsed.summary,
                    "event_id": event_id,
                }
            )
        self.reminder_engine.scan_upcoming()
        return {
            "event_id": event_id,
            "parsed": {
                "title": parsed.title,
                "category": parsed.category,
                "person": parsed.person,
                "start_at": parsed.start_at.isoformat(timespec="minutes") if parsed.start_at else None,
                "location": parsed.location,
                "priority": parsed.priority,
                "summary": parsed.summary,
            },
        }

    def dashboard(self) -> dict:
        device = self.repository.get_device(DEFAULT_DEVICE_ID) or {}
        if device.get("status") != "paired":
            payload = self.get_pairing_payload()
            return {
                "mode": "pairing",
                "device": device,
                "pairing": payload,
            }
        self.reminder_engine.scan_upcoming()
        result = self.tv_dashboard_service.build_payload()
        result["mode"] = "dashboard"
        result["device"] = device
        return result

    def mobile_status(self) -> dict:
        return {
            "calendar_count": len(self.calendar_engine.list_items()),
            "reminder_count": len(self.reminder_engine.list_items()),
            "info_count": len(self.info_engine.list_items()),
            "notifications": self.repository.list_active_notifications(),
            "nodes": self.repository.list_nodes(),
            "sessions": self.repository.list_sessions(),
            "recent_commands": self.repository.list_recent_commands(8),
            "device": self.get_device(),
        }

    def acknowledge_notification(self, notification_id: int) -> dict:
        self.repository.acknowledge_notification(notification_id)
        return {"ok": True}

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
            "pairing": self.get_pairing_payload(),
        }

    def execute_control_command(self, session_id: str, agent_name: str, action_name: str, payload: dict) -> dict:
        session = self.repository.get_session(session_id)
        if not session:
            response = {"ok": False, "error": "session_not_found"}
            self.repository.log_command(session_id, agent_name, action_name, "gateway", "rejected", json.dumps(payload), json.dumps(response))
            return response

        self.repository.touch_session(session_id)
        status = "success"
        target_node = "mini-host"
        if action_name == "family.status":
            response = self.mobile_status()
        elif action_name == "intake.manual":
            response = self.ingest_manual(payload.get("text", ""))
        elif action_name == "intake.screenshot":
            response = self.ingest_screenshot(payload.get("text", ""))
        elif action_name == "dashboard.refresh":
            response = {"ok": True, "dashboard": self.dashboard().get("mode", "dashboard")}
        elif action_name == "tts.play":
            response = self.tts_service.speak(payload.get("message", ""))
        elif action_name == "tv.wake":
            self.tv_control_service.wake_tv()
            response = self.tv_control_service.switch_input("dashboard")
        elif action_name == "dashboard.get":
            response = self.dashboard()
            target_node = "tv-dashboard"
        else:
            status = "rejected"
            response = {"ok": False, "error": "action_not_supported"}

        self.repository.log_command(
            session_id=session_id,
            agent_name=agent_name,
            action_name=action_name,
            target_node=target_node,
            status=status,
            request_payload=json.dumps(payload, ensure_ascii=False),
            response_payload=json.dumps(response, ensure_ascii=False),
        )
        return response
