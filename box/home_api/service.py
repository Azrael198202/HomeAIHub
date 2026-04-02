from __future__ import annotations

import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta

from shared.config.settings import settings
from box.home_api.control_plane_service import HomeControlPlaneService
from box.home_api.device_service import HomeDeviceService
from box.home_api.intake_service import HomeIntakeService
from box.home_api.voice_task_service import VoiceTaskService


DEFAULT_DEVICE_ID = "hub-demo-001"
DEFAULT_DEVICE_NAME = "HomeAIHub Box"
DEFAULT_FAMILY_ID = "family-demo"
VOICE_PENDING_TASK_KEY = "voice_pending_task_json"


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
        hub_orchestrator_service,
        openclaw_runtime,
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
        self.hub_orchestrator_service = hub_orchestrator_service
        self.openclaw_runtime = openclaw_runtime
        self.voice_task_service = VoiceTaskService(
            repository=repository,
            parser_service=parser_service,
            reminder_engine=reminder_engine,
            runtime=openclaw_runtime,
            tts_service=tts_service,
        )
        self.device_service = HomeDeviceService(
            repository=repository,
            gateway_base_url=settings.gateway_base_url,
            default_device_id=DEFAULT_DEVICE_ID,
            default_device_name=DEFAULT_DEVICE_NAME,
            default_family_id=DEFAULT_FAMILY_ID,
        )
        self.intake_service = HomeIntakeService(
            repository=repository,
            ocr_service=ocr_service,
        )
        self.control_plane_service = HomeControlPlaneService(
            repository=repository,
            calendar_engine=calendar_engine,
            reminder_engine=reminder_engine,
            info_engine=info_engine,
            hub_orchestrator_service=hub_orchestrator_service,
            openclaw_runtime=openclaw_runtime,
            device_service=self.device_service,
        )

    def bootstrap(self) -> None:
        if self.repository.is_empty():
            self.repository.seed_events(build_seed_data())
        self.repository.register_node("mini-host", "node")
        self.repository.register_node("tv-dashboard", "device")
        self.repository.register_node("voice-listener", "service")
        self.repository.register_node("home-orchestrator", "service")
        for capability in (
            "ocr.recognize",
            "calendar.query",
            "reminder.scan",
            "info.query",
            "tts.play",
            "tv.wake",
            "tv.dashboard.refresh",
            "tv.dashboard.render",
            "voice.listen",
            "voice.wake",
            "voice.transcribe",
            "orchestrator.route",
            "orchestrator.announce",
            "device.claim",
            "device.status",
        ):
            self.repository.register_capability("mini-host", capability)
        self.repository.register_capability("tv-dashboard", "display.render")
        self.repository.register_capability("tv-dashboard", "display.popup")
        self.repository.register_capability("voice-listener", "voice.listen")
        self.repository.register_capability("voice-listener", "voice.wake")
        self.repository.register_capability("voice-listener", "voice.transcribe")
        self.repository.register_capability("home-orchestrator", "orchestrator.route")
        self.repository.register_capability("home-orchestrator", "orchestrator.announce")
        self.hub_orchestrator_service.bootstrap()
        self.hub_orchestrator_service.attach_runtime(self.openclaw_runtime)
        self._register_openclaw_agents()
        self.device_service.ensure_device_record()

    def _register_openclaw_agents(self) -> None:
        self.openclaw_runtime.register_agent(
            "family-intake-agent",
            "intake",
            "Accept household text, screenshot, photo, voice, and relay deliveries for the box.",
        )
        self.openclaw_runtime.register_action(
            "family-intake-agent",
            "family.status",
            "mini-host",
            "read",
            self._family_status_direct,
            "Return the current family/mobile status summary.",
        )
        self.openclaw_runtime.register_action(
            "family-intake-agent",
            "intake.manual",
            "mini-host",
            "write",
            self._ingest_manual_direct,
            "Classify and store a text note from the app.",
        )
        self.openclaw_runtime.register_action(
            "family-intake-agent",
            "intake.screenshot",
            "mini-host",
            "write",
            self._ingest_screenshot_direct,
            "Run OCR for a screenshot and store the parsed result.",
        )
        self.openclaw_runtime.register_action(
            "family-intake-agent",
            "intake.photo",
            "mini-host",
            "write",
            self._ingest_photo_direct,
            "Run OCR for a photo and store the parsed result.",
        )
        self.openclaw_runtime.register_action(
            "family-intake-agent",
            "intake.voice",
            "mini-host",
            "write",
            self._ingest_voice_direct,
            "Store and classify a voice transcript.",
        )
        self.openclaw_runtime.register_action(
            "family-intake-agent",
            "relay.receive",
            "mini-host",
            "write",
            self._receive_relay_delivery_direct,
            "Accept a Railway relay delivery and classify it on the box.",
        )

        self.openclaw_runtime.register_agent(
            "household-dashboard-agent",
            "dashboard",
            "Keep the TV dashboard always-on and expose the current family hub state.",
        )
        self.openclaw_runtime.register_action(
            "household-dashboard-agent",
            "dashboard.get",
            "tv-dashboard",
            "read",
            self._dashboard_get_direct,
            "Render the current dashboard payload.",
        )
        self.openclaw_runtime.register_action(
            "household-dashboard-agent",
            "dashboard.refresh",
            "home-orchestrator",
            "execute",
            self.hub_orchestrator_service._refresh_dashboard_direct,
            "Refresh the always-on family dashboard.",
        )

        self.openclaw_runtime.register_agent(
            "voice-automation-agent",
            "voice",
            "Run spoken announcements, TV wake actions, and wake-word flows for the box.",
        )
        self.openclaw_runtime.register_action(
            "voice-automation-agent",
            "tts.play",
            "mini-host",
            "execute",
            self._tts_play_direct,
            "Play synthesized speech on the box.",
        )
        self.openclaw_runtime.register_action(
            "voice-automation-agent",
            "announce.play",
            "home-orchestrator",
            "execute",
            self.hub_orchestrator_service._announce_direct,
            "Broadcast a household reminder with priority.",
        )
        self.openclaw_runtime.register_action(
            "voice-automation-agent",
            "tv.wake",
            "tv-dashboard",
            "execute",
            self.hub_orchestrator_service._wake_tv_direct,
            "Wake the TV and switch to the dashboard input.",
        )
        self.openclaw_runtime.register_action(
            "voice-automation-agent",
            "voice.status",
            "voice-listener",
            "read",
            self.hub_orchestrator_service._voice_status_direct,
            "Return the current wake-word listener state.",
        )
        self.openclaw_runtime.register_action(
            "voice-automation-agent",
            "voice.wake",
            "voice-listener",
            "execute",
            self.hub_orchestrator_service._handle_voice_wake_direct,
            "Interpret a wake transcript and delegate to the correct agent.",
        )

        self.openclaw_runtime.register_agent(
            "home-orchestrator-agent",
            "orchestrator",
            "Coordinate intake, dashboard, and voice capabilities as the household control brain.",
        )
        self.openclaw_runtime.register_action(
            "home-orchestrator-agent",
            "hub.status",
            "home-orchestrator",
            "read",
            self.hub_orchestrator_service._hub_overview_direct,
            "Return the household orchestrator overview.",
        )
        self.openclaw_runtime.register_action(
            "home-orchestrator-agent",
            "voice.status",
            "voice-listener",
            "read",
            self.hub_orchestrator_service._voice_status_direct,
            "Return voice listener state from the orchestrator agent.",
        )
        self.openclaw_runtime.register_action(
            "home-orchestrator-agent",
            "voice.wake",
            "voice-listener",
            "execute",
            self.hub_orchestrator_service._handle_voice_wake_direct,
            "Accept a wake transcript and route it through the orchestrator.",
        )
        self.openclaw_runtime.register_action(
            "home-orchestrator-agent",
            "announce.play",
            "home-orchestrator",
            "execute",
            self.hub_orchestrator_service._announce_direct,
            "Announce a household message from the orchestrator plane.",
        )
        self.openclaw_runtime.register_action(
            "home-orchestrator-agent",
            "dashboard.refresh",
            "home-orchestrator",
            "execute",
            self.hub_orchestrator_service._refresh_dashboard_direct,
            "Refresh dashboard state from the orchestrator plane.",
        )
        self.openclaw_runtime.register_action(
            "home-orchestrator-agent",
            "orchestrator.listen",
            "home-orchestrator",
            "execute",
            self.hub_orchestrator_service._orchestrator_listen_direct,
            "Accept an open-ended household request and keep listening.",
        )

    def _ensure_device_record(self) -> None:
        self.device_service.ensure_device_record()

    def _new_claim(self) -> tuple[str, str]:
        return self.device_service.new_claim()

    def get_device(self) -> dict:
        return self.device_service.get_device()

    def external_box_status(self) -> dict:
        return self.device_service.external_box_status()

    def get_pairing_payload(self) -> dict:
        return self.device_service.get_pairing_payload()

    def claim_device(self, actor_user_id: str, actor_name: str, family_name: str, claim_token: str) -> dict:
        return self.device_service.claim_device(actor_user_id, actor_name, family_name, claim_token)

    def unbind_device(self, actor_user_id: str, actor_name: str) -> dict:
        return self.device_service.unbind_device(actor_user_id, actor_name)

    def reset_pairing(self) -> dict:
        return self.device_service.reset_pairing()

    def ingest_manual(self, text: str) -> dict:
        return self.openclaw_runtime.dispatch_internal(
            "family-intake-agent",
            "intake.manual",
            {"text": text},
            source="box-api",
            actor_name="box-api",
        )

    def ingest_screenshot(self, text: str) -> dict:
        return self.openclaw_runtime.dispatch_internal(
            "family-intake-agent",
            "intake.screenshot",
            {"text": text},
            source="box-api",
            actor_name="box-api",
        )

    def ingest_photo(self, text: str) -> dict:
        return self.openclaw_runtime.dispatch_internal(
            "family-intake-agent",
            "intake.photo",
            {"text": text},
            source="box-api",
            actor_name="box-api",
        )

    def ingest_voice(self, text: str) -> dict:
        return self.openclaw_runtime.dispatch_internal(
            "family-intake-agent",
            "intake.voice",
            {"text": text},
            source="box-api",
            actor_name="box-api",
        )

    def receive_relay_delivery(
        self,
        relay_id: str,
        source_channel: str,
        content_kind: str,
        text: str,
        filename: str,
        mime_type: str,
        byte_size: int,
        content_base64: str,
    ) -> dict:
        return self.openclaw_runtime.dispatch_internal(
            "family-intake-agent",
            "relay.receive",
            {
                "relay_id": relay_id,
                "source_channel": source_channel,
                "content_kind": content_kind,
                "text": text,
                "filename": filename,
                "mime_type": mime_type,
                "byte_size": byte_size,
                "content_base64": content_base64,
            },
            source=source_channel or "railway",
            actor_name="railway-relay",
        )

    def _family_status_direct(self, payload: dict) -> dict:
        result = self.mobile_status()
        result["ok"] = True
        return result

    def _ingest_manual_direct(self, payload: dict) -> dict:
        return self.intake_service.ingest_manual(self._create_event, payload.get("text", ""))

    def _ingest_screenshot_direct(self, payload: dict) -> dict:
        return self.intake_service.ingest_screenshot(self._create_event, payload.get("text", ""))

    def _ingest_photo_direct(self, payload: dict) -> dict:
        return self.intake_service.ingest_photo(self._create_event, payload.get("text", ""))

    def _ingest_voice_direct(self, payload: dict) -> dict:
        return self.intake_service.ingest_voice(
            self._process_voice_task,
            payload.get("text", ""),
        )

    def _receive_relay_delivery_direct(self, payload: dict) -> dict:
        return self.intake_service.receive_relay_delivery(
            payload,
            ingest_manual=lambda text: self._ingest_manual_direct({"text": text}),
            ingest_photo=lambda text: self._ingest_photo_direct({"text": text}),
            ingest_voice=lambda text: self._ingest_voice_direct({"text": text}),
        )

    def _process_voice_task(self, transcript: str) -> dict:
        return self.voice_task_service.process_voice_task(
            transcript,
            create_event=self._create_event,
            create_structured_event=self._create_structured_task_event,
        )

    def _analyze_voice_task(self, text: str) -> dict:
        normalized = " ".join((text or "").strip().split())
        lower = normalized.lower()
        actionable_keywords = (
            "remind me",
            "remember to",
            "need to",
            "i need to",
            "please remind",
            "buy ",
            "call ",
            "book ",
            "schedule ",
            "pick up",
            "drop off",
            "bring ",
            "pay ",
            "renew ",
            "提醒我",
            "记得",
            "需要",
            "要去",
            "安排",
            "预约",
            "买",
            "缴费",
            "接",
            "送",
            "带",
        )
        title = self._extract_voice_task_title(normalized)
        person = self._extract_voice_task_person(normalized)
        due_at = self._extract_voice_task_datetime(normalized)
        location = self._extract_voice_task_location(normalized)
        category = self._detect_voice_task_category(lower, due_at)
        is_actionable = bool(title) and any(keyword in lower for keyword in actionable_keywords)
        if not is_actionable and due_at and title:
            is_actionable = True
        if not is_actionable and title and any(token in lower for token in ("appointment", "meeting", "class", "doctor", "dentist", "提醒", "会议", "上课", "看牙")):
            is_actionable = True
        missing_fields: list[str] = []
        if not title:
            missing_fields.append("title")
        if due_at is None:
            missing_fields.append("time")
        if category == "calendar" and not location:
            missing_fields.append("location")
        draft = {
            "source_text": normalized,
            "title": title or "New task",
            "person": person,
            "due_at": due_at.isoformat(timespec="minutes") if due_at else "",
            "location": location,
            "category": category,
            "priority": self._priority_for_voice_task(lower, due_at),
            "summary": self._build_voice_task_summary(person, title or "New task", due_at, location),
        }
        return {
            "ok": True,
            "is_actionable": is_actionable,
            "missing_fields": missing_fields if is_actionable else [],
            "draft": draft,
        }

    def _extract_voice_task_person(self, text: str) -> str:
        normalized = text.lower()
        person_aliases = {
            "Mom": ("mom", "mother", "妈妈", "妈"),
            "Dad": ("dad", "father", "爸爸", "爸"),
            "Alex": ("alex", "阿历克斯"),
            "Emma": ("emma", "艾玛"),
            "Family": ("family", "everyone", "all of us", "全家", "大家"),
        }
        for person, aliases in person_aliases.items():
            if any(alias in normalized for alias in aliases):
                return person
        return "Family"

    def _extract_voice_task_datetime(self, text: str):
        parser = getattr(self.parser_service, "_extract_datetime", None)
        if callable(parser):
            parsed = parser(text)
            if parsed:
                return parsed

        now = datetime.now()
        lower = text.lower()
        relative = re.search(r"\bin (\d{1,2})\s*(minutes?|hours?)\b", lower)
        if relative:
            value = int(relative.group(1))
            unit = relative.group(2)
            return now + timedelta(hours=value) if unit.startswith("hour") else now + timedelta(minutes=value)

        match = re.search(r"\b(?:(tomorrow|today|tonight|this evening|this afternoon|this morning)\s+)?(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", lower)
        if not match:
            match = re.search(r"\b(?:(tomorrow|today)\s+)?(\d{1,2}):(\d{2})\b", lower)
        if not match:
            return None

        day_hint = (match.group(1) or "").strip()
        hour = int(match.group(2))
        minute = int(match.group(3) or 0)
        meridiem = (match.group(4) or "").lower()
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0

        base_date = now.date()
        if day_hint == "tomorrow":
            base_date = (now + timedelta(days=1)).date()
        elif day_hint in {"tonight", "this evening"} and not meridiem and hour < 12:
            hour += 12
        elif day_hint == "this afternoon" and hour < 12:
            hour += 12
        return datetime.combine(base_date, datetime.min.time()).replace(hour=hour, minute=minute)

    def _extract_voice_task_location(self, text: str) -> str:
        location_match = re.search(r"\b(?:at|in)\s+([A-Za-z][A-Za-z0-9'\- ]{1,30})", text)
        if location_match:
            return location_match.group(1).strip().title()
        for marker in ("在", "去"):
            if marker in text:
                chunk = text.split(marker, 1)[1]
                return re.split(r"[\uff0c\u3002,.\s]", chunk, maxsplit=1)[0][:20]
        return ""

    def _extract_voice_task_title(self, text: str) -> str:
        title = f" {text.strip()} "
        patterns = [
            r"\bhey lumi\b",
            r"\bhei lumi\b",
            r"\bremind me to\b",
            r"\bplease remind me to\b",
            r"\bremember to\b",
            r"\bi need to\b",
            r"\bneed to\b",
            r"\bschedule\b",
            r"\bbook\b",
            r"\bset up\b",
            r"\bfor mom\b",
            r"\bfor dad\b",
            r"\bfor alex\b",
            r"\bfor emma\b",
            r"\btomorrow\b",
            r"\btoday\b",
            r"\btonight\b",
            r"\bthis evening\b",
            r"\bthis afternoon\b",
            r"\bthis morning\b",
            r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b",
            r"\bin\s+\d{1,2}\s*(?:minutes?|hours?)\b",
            r"提醒我",
            r"记得",
            r"需要",
            r"安排",
            r"预约",
        ]
        for pattern in patterns:
            title = re.sub(pattern, " ", title, flags=re.IGNORECASE)
        title = re.sub(r"\b(?:mom|dad|alex|emma|family|everyone)\b", " ", title, flags=re.IGNORECASE)
        title = re.sub(r"[,:;.!?]", " ", title)
        title = " ".join(title.split()).strip(" -")
        return title[:60]

    def _detect_voice_task_category(self, lower: str, due_at) -> str:
        if any(keyword in lower for keyword in ("appointment", "meeting", "class", "doctor", "dentist", "visit", "schedule", "预约", "会议", "上课", "看牙")):
            return "calendar"
        if due_at:
            return "reminder"
        return "reminder"

    def _priority_for_voice_task(self, lower: str, due_at) -> str:
        if any(keyword in lower for keyword in ("urgent", "asap", "right away", "immediately", "赶紧", "马上", "立刻")):
            return "high"
        if due_at and (due_at - datetime.now()).total_seconds() < 3600:
            return "high"
        return "normal"

    def _build_voice_task_summary(self, person: str, title: str, due_at, location: str) -> str:
        parts = [person, title]
        if due_at:
            parts.append(due_at.strftime("%m-%d %H:%M"))
        if location:
            parts.append(location)
        return " | ".join(item for item in parts if item)

    def _analyze_voice_task(self, text: str) -> dict:
        normalized = " ".join((text or "").strip().split())
        lower = normalized.lower()
        actionable_keywords = (
            "remind me",
            "remember to",
            "need to",
            "i need to",
            "please remind",
            "buy ",
            "call ",
            "book ",
            "schedule ",
            "pick up",
            "drop off",
            "bring ",
            "pay ",
            "renew ",
            "todo",
            "task",
            "\u63d0\u9192\u6211",
            "\u8bb0\u5f97",
            "\u9700\u8981",
            "\u5b89\u6392",
            "\u9884\u7ea6",
            "\u4e70",
            "\u7f34\u8d39",
            "\u63a5",
            "\u9001",
            "\u5e26",
            "\u529e",
        )
        title = self._extract_voice_task_title(normalized)
        person = self._extract_voice_task_person(normalized)
        due_at = self._extract_voice_task_datetime(normalized)
        location = self._extract_voice_task_location(normalized)
        category = self._detect_voice_task_category(lower, due_at)
        is_actionable = bool(title) and any(keyword in lower for keyword in actionable_keywords)
        if not is_actionable and due_at and title:
            is_actionable = True
        if not is_actionable and title and any(
            token in lower
            for token in (
                "appointment",
                "meeting",
                "class",
                "doctor",
                "dentist",
                "visit",
                "\u9884\u7ea6",
                "\u4f1a\u8bae",
                "\u4e0a\u8bfe",
                "\u770b\u7259",
                "\u533b\u9662",
            )
        ):
            is_actionable = True
        missing_fields: list[str] = []
        if not title:
            missing_fields.append("title")
        if due_at is None:
            missing_fields.append("time")
        draft = {
            "source_text": normalized,
            "title": title or "New task",
            "person": person,
            "due_at": due_at.isoformat(timespec="minutes") if due_at else "",
            "location": location,
            "category": category,
            "priority": self._priority_for_voice_task(lower, due_at),
            "summary": self._build_voice_task_summary(person, title or "New task", due_at, location),
            "decision": self._build_voice_task_decision(person, due_at, location),
        }
        return {
            "ok": True,
            "is_actionable": is_actionable,
            "missing_fields": missing_fields if is_actionable else [],
            "draft": draft,
        }

    def _extract_voice_task_person(self, text: str) -> str:
        normalized = text.lower()
        person_aliases = {
            "Mom": ("mom", "mother", "\u5988\u5988", "\u5988"),
            "Dad": ("dad", "father", "\u7238\u7238", "\u7238"),
            "Alex": ("alex", "\u4e9a\u5386\u514b\u65af"),
            "Emma": ("emma", "\u827e\u739b"),
            "Family": ("family", "everyone", "all of us", "\u5168\u5bb6", "\u5927\u5bb6"),
        }
        for person, aliases in person_aliases.items():
            if any(alias in normalized for alias in aliases):
                return person
        return "Family"

    def _extract_voice_task_datetime(self, text: str):
        parser = getattr(self.parser_service, "_extract_datetime", None)
        if callable(parser):
            parsed = parser(text)
            if parsed:
                return parsed

        now = datetime.now()
        lower = text.lower()
        relative = re.search(r"\bin (\d{1,2})\s*(minutes?|hours?)\b", lower)
        if relative:
            value = int(relative.group(1))
            unit = relative.group(2)
            return now + timedelta(hours=value) if unit.startswith("hour") else now + timedelta(minutes=value)

        chinese_relative = re.search(r"(\d{1,2})\s*(?:\u5206\u949f|\u5c0f\u65f6)\u540e", text)
        if chinese_relative:
            value = int(chinese_relative.group(1))
            if "\u5c0f\u65f6" in chinese_relative.group(0):
                return now + timedelta(hours=value)
            return now + timedelta(minutes=value)

        match = re.search(r"\b(?:(tomorrow|today|tonight|this evening|this afternoon|this morning)\s+)?(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", lower)
        if not match:
            match = re.search(r"\b(?:(tomorrow|today)\s+)?(\d{1,2}):(\d{2})\b", lower)
        if match:
            day_hint = (match.group(1) or "").strip()
            hour = int(match.group(2))
            minute = int(match.group(3) or 0)
            meridiem = (match.group(4) or "").lower()
            if meridiem == "pm" and hour < 12:
                hour += 12
            if meridiem == "am" and hour == 12:
                hour = 0
            base_date = now.date()
            if day_hint == "tomorrow":
                base_date = (now + timedelta(days=1)).date()
            elif day_hint in {"tonight", "this evening"} and not meridiem and hour < 12:
                hour += 12
            elif day_hint == "this afternoon" and hour < 12:
                hour += 12
            return datetime.combine(base_date, datetime.min.time()).replace(hour=hour, minute=minute)

        cn_match = re.search(
            r"(?:(\u4eca\u5929|\u660e\u5929|\u540e\u5929)\s*)?(?:(\u4e0a\u5348|\u4e2d\u5348|\u4e0b\u5348|\u665a\u4e0a)\s*)?(\d{1,2})[:\uff1a\u70b9](\d{1,2})?",
            text,
        )
        if not cn_match:
            return None
        day_hint = cn_match.group(1) or ""
        meridiem = cn_match.group(2) or ""
        hour = int(cn_match.group(3))
        minute = int(cn_match.group(4) or 0)
        if meridiem in {"\u4e0b\u5348", "\u665a\u4e0a"} and hour < 12:
            hour += 12
        if meridiem == "\u4e2d\u5348" and hour < 11:
            hour += 12
        base_date = now.date()
        if day_hint == "\u660e\u5929":
            base_date = (now + timedelta(days=1)).date()
        elif day_hint == "\u540e\u5929":
            base_date = (now + timedelta(days=2)).date()
        return datetime.combine(base_date, datetime.min.time()).replace(hour=hour, minute=minute)

    def _extract_voice_task_location(self, text: str) -> str:
        location_match = re.search(r"\b(?:at|in)\s+([A-Za-z][A-Za-z0-9'\- ]{1,30})", text)
        if location_match:
            return location_match.group(1).strip().title()
        for marker in ("\u5728", "\u53bb", "\u5230"):
            if marker in text:
                chunk = text.split(marker, 1)[1]
                token = re.split(r"[\uff0c\u3002,.\s]", chunk, maxsplit=1)[0][:20]
                if token and token not in {"\u4e70", "\u529e", "\u63d0\u9192", "\u8bb0\u5f97"}:
                    return token
        return ""

    def _extract_voice_task_title(self, text: str) -> str:
        title = f" {text.strip()} "
        patterns = [
            r"\bhey lumi\b",
            r"\bhei lumi\b",
            r"\bremind me to\b",
            r"\bplease remind me to\b",
            r"\bremember to\b",
            r"\bi need to\b",
            r"\bneed to\b",
            r"\bschedule\b",
            r"\bbook\b",
            r"\bset up\b",
            r"\bfor mom\b",
            r"\bfor dad\b",
            r"\bfor alex\b",
            r"\bfor emma\b",
            r"\btomorrow\b",
            r"\btoday\b",
            r"\btonight\b",
            r"\bthis evening\b",
            r"\bthis afternoon\b",
            r"\bthis morning\b",
            r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b",
            r"\bin\s+\d{1,2}\s*(?:minutes?|hours?)\b",
            r"\u63d0\u9192\u6211",
            r"\u8bf7\u63d0\u9192\u6211",
            r"\u8bb0\u5f97",
            r"\u6211\u9700\u8981",
            r"\u9700\u8981",
            r"\u5b89\u6392",
            r"\u9884\u7ea6",
            r"\u660e\u5929",
            r"\u4eca\u5929",
            r"\u540e\u5929",
            r"\u4e0a\u5348",
            r"\u4e2d\u5348",
            r"\u4e0b\u5348",
            r"\u665a\u4e0a",
            r"\d{1,2}[:\uff1a\u70b9]\d{0,2}",
            r"\d{1,2}\s*(?:\u5206\u949f|\u5c0f\u65f6)\u540e",
        ]
        for pattern in patterns:
            title = re.sub(pattern, " ", title, flags=re.IGNORECASE)
        title = re.sub(r"\b(?:mom|dad|alex|emma|family|everyone)\b", " ", title, flags=re.IGNORECASE)
        title = title.replace("\u7ed9\u5988\u5988", " ").replace("\u7ed9\u7238\u7238", " ").replace("\u7ed9\u5168\u5bb6", " ")
        title = re.sub(r"[,:;.!?]", " ", title)
        title = " ".join(title.split()).strip(" -")
        return title[:60]

    def _detect_voice_task_category(self, lower: str, due_at) -> str:
        if any(
            keyword in lower
            for keyword in (
                "appointment",
                "meeting",
                "class",
                "doctor",
                "dentist",
                "visit",
                "schedule",
                "\u9884\u7ea6",
                "\u4f1a\u8bae",
                "\u4e0a\u8bfe",
                "\u770b\u7259",
                "\u53bb",
            )
        ):
            return "calendar"
        if due_at:
            return "reminder"
        return "reminder"

    def _priority_for_voice_task(self, lower: str, due_at) -> str:
        if any(
            keyword in lower
            for keyword in (
                "urgent",
                "asap",
                "right away",
                "immediately",
                "\u7d27\u6025",
                "\u9a6c\u4e0a",
                "\u7acb\u523b",
            )
        ):
            return "high"
        if due_at and (due_at - datetime.now()).total_seconds() < 3600:
            return "high"
        return "normal"

    def _build_voice_task_decision(self, person: str, due_at, location: str) -> dict:
        return {
            "owner": person or "Family",
            "when": due_at.isoformat(timespec="minutes") if due_at else "",
            "location": location,
            "follow_up_required": not bool(due_at),
            "planner_action": "create_calendar" if due_at and location else "create_reminder",
        }

    def _build_voice_follow_up_question(self, missing_fields: list[str], draft: dict) -> str:
        if "time" in missing_fields and "title" in missing_fields:
            return "I caught a task, but I still need what needs to be done and when it should happen."
        if "location" in missing_fields and "time" in missing_fields:
            return f"When and where should I schedule {draft.get('title', 'this task')}?"
        if "location" in missing_fields:
            return f"Where should I schedule {draft.get('title', 'this task')}?"
        if "time" in missing_fields:
            return f"When should I remind you about {draft.get('title', 'this task')}?"
        if "title" in missing_fields:
            return "What should I add to the task?"
        return "Please tell me a little more so I can save that correctly."

    def _build_voice_confirmation_message(self, draft: dict) -> str:
        when = draft.get("due_at", "")
        owner = draft.get("person", "Family")
        location = draft.get("location", "")
        title = draft.get("title", "this task")
        if when:
            try:
                due_at = datetime.fromisoformat(when)
                due_label = due_at.strftime("%I:%M %p").lstrip("0")
            except ValueError:
                due_label = when
            location_suffix = f" at {location}" if location else ""
            return f"Okay. I will track {title} for {owner} at {due_label}{location_suffix}."
        return f"Okay. I saved {title} for {owner}."

    def _announce_voice_feedback(self, message: str) -> dict:
        if not message:
            return {"ok": False, "spoken": ""}
        if self.runtime:
            return self.runtime.dispatch_internal(
                "voice-automation-agent",
                "announce.play",
                {"message": message, "priority": "normal"},
                source="voice-task",
                actor_name="family-intake-agent",
            )
        result = self.tts_service.speak(message)
        result.setdefault("ok", True)
        return result

    def _set_pending_voice_task(self, payload: dict) -> None:
        self.repository.upsert_device_state(VOICE_PENDING_TASK_KEY, json.dumps(payload, ensure_ascii=False))

    def _get_pending_voice_task(self) -> dict:
        raw = self.repository.get_device_state(VOICE_PENDING_TASK_KEY, "")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _clear_pending_voice_task(self) -> None:
        self.repository.upsert_device_state(VOICE_PENDING_TASK_KEY, "")

    def _create_structured_task_event(self, draft: dict, source_type: str) -> dict:
        due_at = draft.get("due_at", "")
        event_id = self.repository.create_event(
            {
                "title": draft.get("title", "New task"),
                "category": draft.get("category", "reminder"),
                "person": draft.get("person", "Family"),
                "start_at": due_at if draft.get("category") == "calendar" else "",
                "due_at": due_at,
                "location": draft.get("location", ""),
                "summary": draft.get("summary", ""),
                "priority": draft.get("priority", "normal"),
                "source_type": source_type,
                "source_text": draft.get("source_text", ""),
                "status": "active",
            }
        )
        self.reminder_engine.scan_upcoming()
        return {
            "ok": True,
            "event_id": event_id,
            "parsed": {
                "title": draft.get("title", "New task"),
                "category": draft.get("category", "reminder"),
                "person": draft.get("person", "Family"),
                "start_at": due_at or None,
                "location": draft.get("location", ""),
                "priority": draft.get("priority", "normal"),
                "summary": draft.get("summary", ""),
            },
        }

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
            "ok": True,
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

    # Legacy compatibility wrappers. Keep any straggling callers on the extracted service.
    def _analyze_voice_task(self, text: str) -> dict:
        return self.voice_task_service._analyze_voice_task(text)

    def _extract_voice_task_person(self, text: str) -> str:
        return self.voice_task_service._extract_voice_task_person(text)

    def _extract_voice_task_datetime(self, text: str):
        return self.voice_task_service._extract_voice_task_datetime(text)

    def _extract_voice_task_location(self, text: str) -> str:
        return self.voice_task_service._extract_voice_task_location(text)

    def _extract_voice_task_title(self, text: str) -> str:
        return self.voice_task_service._extract_voice_task_title(text)

    def _detect_voice_task_category(self, lower: str, due_at) -> str:
        return self.voice_task_service._detect_voice_task_category(lower, due_at)

    def _priority_for_voice_task(self, lower: str, due_at) -> str:
        return self.voice_task_service._priority_for_voice_task(lower, due_at)

    def _build_voice_task_summary(self, person: str, title: str, due_at, location: str) -> str:
        return self.voice_task_service._build_voice_task_summary(person, title, due_at, location)

    def _build_voice_task_decision(self, person: str, due_at, location: str) -> dict:
        return self.voice_task_service._build_voice_task_decision(person, due_at, location)

    def _build_voice_follow_up_question(self, missing_fields: list[str], draft: dict) -> str:
        return self.voice_task_service._build_voice_follow_up_question(missing_fields, draft)

    def _build_voice_confirmation_message(self, draft: dict) -> str:
        return self.voice_task_service._build_voice_confirmation_message(draft)

    def _announce_voice_feedback(self, message: str) -> dict:
        return self.voice_task_service._announce_voice_feedback(message)

    def _set_pending_voice_task(self, payload: dict) -> None:
        self.voice_task_service._set_pending_voice_task(payload)

    def _get_pending_voice_task(self) -> dict:
        return self.voice_task_service._get_pending_voice_task()

    def _clear_pending_voice_task(self) -> None:
        self.voice_task_service._clear_pending_voice_task()

    def _dashboard_get_direct(self, payload: dict) -> dict:
        result = self.dashboard()
        result["ok"] = True
        return result

    def _tts_play_direct(self, payload: dict) -> dict:
        result = self.tts_service.speak(payload.get("message", ""))
        result["ok"] = True
        return result

    def dashboard(self) -> dict:
        device = self.repository.get_device(DEFAULT_DEVICE_ID) or {}
        if device.get("status") != "paired":
            payload = self.get_pairing_payload()
            return {
                "mode": "pairing",
                "device": device,
                "pairing": payload,
                "onboarding": {
                    "title": "HomeAIHub pairing ready",
                    "subtitle": "Scan once from the family app to bind this box.",
                    "steps": [
                        "Open the mobile app on phone or tablet.",
                        "Scan the claim QR payload on this TV screen.",
                        "Confirm the owner and family binding.",
                        "After pairing, all remote text, photo, and voice data will route here.",
                    ],
                },
            }
        self.reminder_engine.scan_upcoming()
        result = self.tv_dashboard_service.build_payload()
        result["mode"] = "dashboard"
        result["device"] = device
        result["voice"] = self.hub_orchestrator_service.voice_status()
        return result

    def mobile_status(self) -> dict:
        return self.control_plane_service.mobile_status()

    def acknowledge_notification(self, notification_id: int) -> dict:
        self.repository.acknowledge_notification(notification_id)
        return {"ok": True}

    def open_session(self, actor_name: str, actor_role: str, allowed_agents: list[str]) -> dict:
        return self.control_plane_service.open_session(actor_name, actor_role, allowed_agents)

    def control_plane_overview(self) -> dict:
        return self.control_plane_service.control_plane_overview()

    def execute_control_command(self, session_id: str, agent_name: str, action_name: str, payload: dict) -> dict:
        return self.control_plane_service.execute_control_command(session_id, agent_name, action_name, payload)
