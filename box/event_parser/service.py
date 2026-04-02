from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import webbrowser
from collections import defaultdict
from datetime import datetime, timedelta

from box.tts_service.google_cloud import GoogleCloudTTSBackend
from shared.schemas.models import ParsedItem


DAD = "\u7238\u7238"
MOM = "\u5988\u5988"
KID = "\u5c0f\u5b69"
KID_ALT = "\u5b69\u5b50"
FAMILY = "\u5168\u5bb6"

KNOWN_LOCATIONS = (
    "\u533b\u9662",
    "\u5b66\u6821",
    "\u5bb6\u91cc",
    "\u516c\u53f8",
    "\u94a2\u7434\u6559\u5ba4",
)

PERSON_COLORS = {
    DAD: "blue",
    MOM: "pink",
    KID: "orange",
    KID_ALT: "orange",
    FAMILY: "green",
}


class OCRService:
    def recognize(self, text: str) -> str:
        return " ".join(text.strip().split())


class EventParserService:
    people = (DAD, MOM, KID, KID_ALT, FAMILY)
    info_keywords = ("\u901a\u77e5", "\u5feb\u9012", "\u5929\u6c14", "\u66f4\u65b0", "\u4fe1\u606f")
    reminder_keywords = ("\u7f34\u8d39", "\u51fa\u95e8", "\u622a\u6b62", "\u63d0\u9192", "\u5bb6\u957f\u4f1a")

    def parse(self, source_text: str, source_type: str) -> ParsedItem:
        normalized = " ".join(source_text.strip().split())
        person = self._extract_person(normalized)
        start_at = self._extract_datetime(normalized)
        category = self._detect_category(normalized, source_type, start_at)
        due_at = start_at if category != "info" else None
        location = self._extract_location(normalized)
        title = self._extract_title(normalized, category, location)
        priority = self._priority_for(category, normalized)
        summary = self._build_summary(person, title, start_at, location)
        return ParsedItem(
            title=title,
            category=category,
            person=person,
            start_at=start_at,
            due_at=due_at,
            location=location,
            summary=summary,
            priority=priority,
            source_type=source_type,
            source_text=source_text.strip(),
            requires_confirmation=(source_type in {"screenshot", "photo"}),
        )

    def _extract_person(self, text: str) -> str:
        for person in self.people:
            if person in text:
                return KID if person == KID_ALT else person
        return FAMILY

    def _extract_datetime(self, text: str) -> datetime | None:
        now = datetime.now()
        month_day = re.search(
            r"(?:(\d{1,2})\u6708(\d{1,2})\u65e5)?\s*(\u4e0a\u5348|\u4e0b\u5348|\u665a\u4e0a)?\s*(\d{1,2})[:\uff1a\u70b9](\d{1,2})?",
            text,
        )
        if month_day:
            month = int(month_day.group(1) or now.month)
            day = int(month_day.group(2) or now.day)
            meridiem = month_day.group(3) or ""
            hour = int(month_day.group(4))
            minute = int(month_day.group(5) or 0)
            if meridiem in ("\u4e0b\u5348", "\u665a\u4e0a") and hour < 12:
                hour += 12
            try:
                return datetime(now.year, month, day, hour, minute)
            except ValueError:
                return None

        relative = re.search(r"(\d{1,2})\s*\u5206\u949f\u540e", text)
        if relative:
            return now + timedelta(minutes=int(relative.group(1)))
        return None

    def _detect_category(self, text: str, source_type: str, start_at: datetime | None) -> str:
        if any(keyword in text for keyword in self.info_keywords) and start_at is None:
            return "info"
        if any(keyword in text for keyword in self.reminder_keywords):
            return "reminder"
        if source_type == "screenshot" and "\u901a\u77e5" in text and start_at is None:
            return "info"
        return "calendar"

    def _extract_location(self, text: str) -> str:
        for location in KNOWN_LOCATIONS:
            if location in text:
                return location
        for marker in ("\u5728", "\u53bb"):
            if marker in text:
                chunk = text.split(marker, 1)[1]
                return re.split(r"[\uff0c\u3002,.\s]", chunk, maxsplit=1)[0][:20]
        return ""

    def _extract_title(self, text: str, category: str, location: str) -> str:
        text = re.sub(r"\d{1,2}\u6708\d{1,2}\u65e5", "", text)
        text = re.sub(r"(\u4eca\u5929|\u660e\u5929|\u540e\u5929)", "", text)
        text = re.sub(r"(\u4e0a\u5348|\u4e0b\u5348|\u665a\u4e0a)?\s*\d{1,2}[:\uff1a\u70b9]\d{0,2}", "", text)
        text = re.sub(r"\d{1,2}\s*\u5206\u949f\u540e", "", text)
        for person in self.people:
            text = text.replace(person, "")
        if location:
            text = text.replace(location, "")
        text = text.replace("\u53bb", " ").replace("\u5728", " ")
        text = re.sub(r"[\uff1a:\uff0c\u3002,.\[\]]", " ", text)
        text = " ".join(text.split()).strip()
        if not text:
            return {
                "calendar": "\u65b0\u7684\u65e5\u7a0b",
                "reminder": "\u65b0\u7684\u63d0\u9192",
                "info": "\u65b0\u7684\u4fe1\u606f",
            }[category]
        return text[:40]

    def _priority_for(self, category: str, text: str) -> str:
        if "\u51fa\u95e8" in text or "15\u5206\u949f\u540e" in text:
            return "high"
        if category == "info":
            return "low"
        return "normal"

    def _build_summary(self, person: str, title: str, start_at: datetime | None, location: str) -> str:
        parts = [person, title]
        if start_at:
            parts.append(start_at.strftime("%m-%d %H:%M"))
        if location:
            parts.append(location)
        return " | ".join(parts)


class CalendarEngine:
    def __init__(self, repository) -> None:
        self.repository = repository

    def list_items(self) -> list[dict]:
        return [item for item in self.repository.list_events() if item["category"] == "calendar"]


class ReminderEngine:
    def __init__(self, repository) -> None:
        self.repository = repository

    def list_items(self) -> list[dict]:
        return [item for item in self.repository.list_events() if item["category"] == "reminder"]

    def scan_upcoming(self) -> list[dict]:
        created = []
        now = datetime.now()
        upcoming = now + timedelta(minutes=20)
        for event in self.repository.list_events():
            if event["category"] not in {"calendar", "reminder"}:
                continue
            raw_time = event["due_at"] or event["start_at"]
            if not raw_time:
                continue
            event_time = datetime.fromisoformat(raw_time)
            if now <= event_time <= upcoming:
                if self.repository.notification_exists("upcoming_reminder", int(event["id"])):
                    continue
                minutes = max(0, int((event_time - now).total_seconds() // 60))
                notification_id = self.repository.create_notification(
                    {
                        "kind": "upcoming_reminder",
                        "title": "\u5373\u5c06\u63d0\u9192",
                        "person": event["person"],
                        "location": event["location"],
                        "message": f"{minutes} \u5206\u949f\u540e\uff1a{event['title']}",
                        "event_id": event["id"],
                    }
                )
                created.append({"id": notification_id, "event_id": event["id"]})
        return created


class InfoEngine:
    def __init__(self, repository) -> None:
        self.repository = repository

    def list_items(self) -> list[dict]:
        return [item for item in self.repository.list_events() if item["category"] == "info"]


class TTSService:
    def __init__(
        self,
        repository,
        backend: str = "auto",
        voice_name: str = "",
        rate: int = 0,
        google_api_key: str = "",
        google_voice_name: str = "en-US-Neural2-F",
        google_language_code: str = "en-US",
        google_gender: str = "FEMALE",
        google_speaking_rate: float = 1.0,
        google_cache_dir: str = "",
    ) -> None:
        self.repository = repository
        self.backend = (backend or "auto").strip().lower()
        self.voice_name = (voice_name or "").strip()
        self.rate = int(rate)
        self.google_backend = GoogleCloudTTSBackend(
            api_key=google_api_key,
            voice_name=google_voice_name,
            language_code=google_language_code,
            gender=google_gender,
            speaking_rate=google_speaking_rate,
            cache_dir=google_cache_dir,
        )
        self.repository.upsert_device_state("tts_last_message", "\u8bed\u97f3\u5f85\u673a\u4e2d")

    def speak(self, message: str) -> dict:
        spoken = (message or "").strip()
        self.repository.upsert_device_state("tts_last_message", spoken)
        if not spoken:
            return {"spoken": "", "engine": "mock-tts", "ok": False, "error": "empty_message"}
        result = self._speak_with_backend(spoken)
        if result.get("ok"):
            self.repository.upsert_device_state("tts_last_engine", result.get("engine", "mock-tts"))
            return result
        fallback = {"spoken": spoken, "engine": "mock-tts", "ok": True, "fallback": True}
        if result.get("error"):
            fallback["backend_error"] = result["error"]
            self.repository.upsert_device_state("tts_last_error", result["error"])
        self.repository.upsert_device_state("tts_last_engine", "mock-tts")
        return fallback

    def _speak_with_backend(self, message: str) -> dict:
        preferred = self.backend
        if preferred in {"", "auto"}:
            if self.google_backend.is_available():
                result = self.google_backend.synthesize_and_play(message)
                if result.get("ok"):
                    return result
            if os.name == "nt":
                return self._speak_windows(message)
            if shutil.which("say"):
                return self._speak_macos(message)
            if shutil.which("espeak"):
                return self._speak_espeak(message)
            return {"ok": False, "engine": "mock-tts", "error": "no_tts_backend_available"}
        if preferred == "google_cloud":
            return self.google_backend.synthesize_and_play(message)
        if preferred == "windows_sapi":
            return self._speak_windows(message)
        if preferred == "say":
            return self._speak_macos(message)
        if preferred == "espeak":
            return self._speak_espeak(message)
        if preferred == "mock":
            return {"ok": True, "spoken": message, "engine": "mock-tts"}
        return {"ok": False, "engine": preferred, "error": "unsupported_tts_backend"}

    def _speak_windows(self, message: str) -> dict:
        escaped = message.replace("'", "''")
        voice_clause = ""
        if self.voice_name:
            voice_name = self.voice_name.replace("'", "''")
            voice_clause = f"$synth.SelectVoice('{voice_name}');"
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$synth.Rate = {self.rate};"
            f"{voice_clause}"
            f"$synth.Speak('{escaped}');"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return {
                "ok": False,
                "spoken": message,
                "engine": "windows_sapi",
                "error": (completed.stderr or completed.stdout or "windows_sapi_failed").strip(),
            }
        return {"ok": True, "spoken": message, "engine": "windows_sapi"}

    def _speak_macos(self, message: str) -> dict:
        command = ["say"]
        if self.voice_name:
            command.extend(["-v", self.voice_name])
        command.append(message)
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            return {
                "ok": False,
                "spoken": message,
                "engine": "say",
                "error": (completed.stderr or completed.stdout or "say_failed").strip(),
            }
        return {"ok": True, "spoken": message, "engine": "say"}

    def _speak_espeak(self, message: str) -> dict:
        command = ["espeak"]
        if self.voice_name:
            command.extend(["-v", self.voice_name])
        if self.rate:
            command.extend(["-s", str(max(80, 175 + (self.rate * 20)))])
        command.append(message)
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            return {
                "ok": False,
                "spoken": message,
                "engine": "espeak",
                "error": (completed.stderr or completed.stdout or "espeak_failed").strip(),
            }
        return {"ok": True, "spoken": message, "engine": "espeak"}


class TVControlService:
    def __init__(self, repository, dashboard_url: str = "", browser_autolaunch: bool = True) -> None:
        self.repository = repository
        self.dashboard_url = dashboard_url.strip()
        self.browser_autolaunch = browser_autolaunch
        self._dashboard_browser_opened = False
        self.repository.upsert_device_state("tv_power", "on")
        self.repository.upsert_device_state("tv_input", "dashboard")
        if self.dashboard_url:
            self.repository.upsert_device_state("tv_dashboard_url", self.dashboard_url)

    def wake_tv(self) -> dict:
        self.repository.upsert_device_state("tv_power", "on")
        return {"power": "on"}

    def switch_input(self, input_name: str) -> dict:
        self.repository.upsert_device_state("tv_input", input_name)
        if input_name == "dashboard" and self.browser_autolaunch and self.dashboard_url:
            self._open_dashboard_browser()
        return {"input": input_name}

    def _open_dashboard_browser(self) -> None:
        if self._dashboard_browser_opened:
            self.repository.upsert_device_state("tv_browser_state", "reused_existing_tab")
            return
        self.repository.upsert_device_state("tv_dashboard_url", self.dashboard_url)
        threading.Thread(target=self._open_dashboard_browser_worker, daemon=True).start()

    def _open_dashboard_browser_worker(self) -> None:
        try:
            webbrowser.open(self.dashboard_url, new=0, autoraise=True)
            self._dashboard_browser_opened = True
            self.repository.upsert_device_state("tv_browser_state", "opened")
        except Exception as exc:
            self.repository.upsert_device_state("tv_browser_state", f"error:{exc}")


class TVDashboardService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def build_payload(self) -> dict:
        events = self.repository.list_events()
        notifications = self.repository.list_active_notifications()
        states = self.repository.list_device_states()
        now = datetime.now()
        calendar_items = [self._serialize_event(item) for item in events if item["category"] == "calendar"]
        reminder_items = [self._serialize_event(item) for item in events if item["category"] == "reminder"]
        info_items = [self._serialize_event(item) for item in events if item["category"] == "info"]
        timeline = defaultdict(list)
        for item in calendar_items:
            timeline[item["person"]].append(item)
        dashboard_mode = self._resolve_dashboard_mode(states, now)
        hero_alert = self._pick_hero_alert(notifications)
        wake_overlay = self._build_wake_overlay(states, now, dashboard_mode)
        pending_confirmations = [item for item in notifications if item.get("kind") == "recognition_confirmation"]
        return {
            "generated_at": now.isoformat(timespec="seconds"),
            "dashboard_mode": dashboard_mode,
            "header": {
                "time": now.strftime("%H:%M"),
                "date": now.strftime("%Y-%m-%d"),
                "weekday": ["??", "??", "??", "??", "??", "??", "??"][now.weekday()],
                "weather": "? 22?C",
                "status": "ONLINE",
                "tv_power": states.get("tv_power", "on"),
                "tv_input": states.get("tv_input", "dashboard"),
            },
            "hero_alert": hero_alert,
            "wake_overlay": wake_overlay,
            "command_mode": self._build_command_mode_overlay(states, dashboard_mode),
            "focus": {
                "title": "Household Focus",
                "summary": self._focus_summary(calendar_items, reminder_items, info_items),
                "pending_confirmations": len(pending_confirmations),
                "next_up": calendar_items[0] if calendar_items else None,
            },
            "system_tiles": [
                {"label": "Home Mode", "value": states.get("home_mode", "family-hub"), "tone": "green"},
                {"label": "Dashboard", "value": dashboard_mode, "tone": "blue"},
                {"label": "Voice", "value": states.get("voice_listener_state", "passive"), "tone": "orange"},
                {"label": "Agent", "value": states.get("active_agent", "household-dashboard-agent"), "tone": "pink"},
            ],
            "today_schedule": calendar_items,
            "timeline": [
                {
                    "person": person,
                    "color": PERSON_COLORS.get(person, "green"),
                    "events": sorted(items, key=lambda item: item["sort_time"]),
                }
                for person, items in timeline.items()
            ],
            "reminders": reminder_items[:6],
            "infos": info_items[:6],
            "notifications": notifications,
            "footer": {
                "voice_status": states.get("tts_last_message", "?????"),
                "summary": f"???? {len(reminder_items)} ???",
                "recent_update": hero_alert["message"] if hero_alert else "??????",
                "active_agent": states.get("active_agent", "household-dashboard-agent"),
                "last_route": states.get("orchestrator_last_route", "dashboard.idle"),
            },
        }

    def _resolve_dashboard_mode(self, states: dict, now: datetime) -> str:
        mode = states.get("dashboard_mode", "always_on")
        if states.get("voice_command_mode", "inactive") == "active":
            raw_expires_at = states.get("voice_command_mode_expires_at", "")
            if raw_expires_at:
                try:
                    expires_at = datetime.fromisoformat(raw_expires_at)
                    if expires_at >= now:
                        return "command_mode"
                except ValueError:
                    pass
        if mode == "command_mode":
            raw_expires_at = states.get("voice_command_mode_expires_at", "")
            if not raw_expires_at:
                return "always_on"
            try:
                expires_at = datetime.fromisoformat(raw_expires_at)
            except ValueError:
                return "always_on"
            return "command_mode" if expires_at >= now else "always_on"
        if mode != "wake_overlay":
            return mode
        raw_wake_at = states.get("voice_last_wake_at", "")
        if not raw_wake_at:
            return "always_on"
        try:
            wake_at = datetime.fromisoformat(raw_wake_at)
        except ValueError:
            return "always_on"
        if (now - wake_at).total_seconds() <= 12:
            return "wake_overlay"
        return "always_on"

    def _pick_hero_alert(self, notifications: list[dict]) -> dict | None:
        high_priority = [item for item in notifications if item.get("priority") == "high"]
        if high_priority:
            return high_priority[0]
        return notifications[0] if notifications else None

    def _build_wake_overlay(self, states: dict, now: datetime, dashboard_mode: str) -> dict | None:
        if dashboard_mode != "wake_overlay":
            return None
        return {
            "title": "Lumi is listening",
            "message": states.get("tts_last_message", "Hey master, Need any help"),
            "agent": states.get("active_agent", "voice-automation-agent"),
            "time": now.strftime("%H:%M:%S"),
        }

    def _build_command_mode_overlay(self, states: dict, dashboard_mode: str) -> dict | None:
        if dashboard_mode != "command_mode":
            return None
        return {
            "title": "Command mode",
            "message": states.get("voice_last_transcript", "") or "Waiting for a task to handle.",
            "reply": states.get("voice_last_reply", "") or states.get("tts_last_message", "Tell me what to handle."),
            "agent": states.get("active_agent", "home-orchestrator-agent"),
        }

    def _focus_summary(self, calendar_items: list[dict], reminder_items: list[dict], info_items: list[dict]) -> str:
        if reminder_items:
            return reminder_items[0]["title"]
        if calendar_items:
            return f"Next: {calendar_items[0]['title']}"
        if info_items:
            return info_items[0]["title"]
        return "Home is calm and ready"

    def _serialize_event(self, item: dict) -> dict:
        raw_time = item["start_at"] or item["due_at"]
        display_time = ""
        sort_time = "9999-12-31T23:59"
        if raw_time:
            dt = datetime.fromisoformat(raw_time)
            display_time = dt.strftime("%H:%M")
            sort_time = dt.isoformat(timespec="minutes")
        return {
            "id": item["id"],
            "title": item["title"],
            "person": item["person"],
            "location": item["location"],
            "priority": item["priority"],
            "time": display_time,
            "sort_time": sort_time,
            "summary": item["summary"],
            "category": item["category"],
            "color": PERSON_COLORS.get(item["person"], "green"),
        }
