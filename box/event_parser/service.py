from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta

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
            requires_confirmation=(source_type == "screenshot"),
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
    def __init__(self, repository) -> None:
        self.repository = repository
        self.repository.upsert_device_state("tts_last_message", "\u8bed\u97f3\u5f85\u673a\u4e2d")

    def speak(self, message: str) -> dict:
        self.repository.upsert_device_state("tts_last_message", message)
        return {"spoken": message, "engine": "mock-tts"}


class TVControlService:
    def __init__(self, repository) -> None:
        self.repository = repository
        self.repository.upsert_device_state("tv_power", "on")
        self.repository.upsert_device_state("tv_input", "dashboard")

    def wake_tv(self) -> dict:
        self.repository.upsert_device_state("tv_power", "on")
        return {"power": "on"}

    def switch_input(self, input_name: str) -> dict:
        self.repository.upsert_device_state("tv_input", input_name)
        return {"input": input_name}


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
        return {
            "generated_at": now.isoformat(timespec="seconds"),
            "header": {
                "time": now.strftime("%H:%M"),
                "date": now.strftime("%Y-%m-%d"),
                "weekday": ["\u5468\u4e00", "\u5468\u4e8c", "\u5468\u4e09", "\u5468\u56db", "\u5468\u4e94", "\u5468\u516d", "\u5468\u65e5"][now.weekday()],
                "weather": "\u6674 22\u00b0C",
                "status": "ONLINE",
                "tv_power": states.get("tv_power", "on"),
                "tv_input": states.get("tv_input", "dashboard"),
            },
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
                "voice_status": states.get("tts_last_message", "\u8bed\u97f3\u5f85\u673a\u4e2d"),
                "summary": f"\u4eca\u65e5\u5171\u6709 {len(reminder_items)} \u4e2a\u63d0\u9192",
                "recent_update": notifications[0]["message"] if notifications else "\u7cfb\u7edf\u8fd0\u884c\u6b63\u5e38",
            },
        }

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
