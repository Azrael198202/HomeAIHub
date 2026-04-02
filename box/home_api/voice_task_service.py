from __future__ import annotations

import json
import re
from datetime import datetime, timedelta


VOICE_PENDING_TASK_KEY = "voice_pending_task_json"


class VoiceTaskService:
    def __init__(self, repository, parser_service, reminder_engine, runtime, tts_service) -> None:
        self.repository = repository
        self.parser_service = parser_service
        self.reminder_engine = reminder_engine
        self.runtime = runtime
        self.tts_service = tts_service

    def process_voice_task(self, transcript: str, create_event, create_structured_event) -> dict:
        normalized = " ".join((transcript or "").strip().split())
        pending = self._get_pending_voice_task()
        combined_text = normalized
        continued = False
        if pending and normalized:
            combined_text = f"{pending.get('source_text', '')} {normalized}".strip()
            continued = True

        analysis = self._analyze_voice_task(combined_text)
        if not analysis["is_actionable"]:
            self._clear_pending_voice_task()
            result = create_event(text=normalized, source_type="voice")
            result["status"] = "captured"
            result["analysis_mode"] = "archive"
            return result

        if analysis["missing_fields"]:
            question = self._build_voice_follow_up_question(analysis["missing_fields"], analysis["draft"])
            self._set_pending_voice_task(
                {
                    "source_text": combined_text,
                    "missing_fields": analysis["missing_fields"],
                    "question": question,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            spoken = self._announce_voice_feedback(question)
            return {
                "ok": True,
                "status": "needs_clarification",
                "continued": continued,
                "question": question,
                "spoken": spoken.get("spoken", question),
                "missing_fields": analysis["missing_fields"],
                "draft": analysis["draft"],
            }

        self._clear_pending_voice_task()
        result = create_structured_event(analysis["draft"], source_type="voice")
        confirmation = self._build_voice_confirmation_message(analysis["draft"])
        spoken = self._announce_voice_feedback(confirmation)
        result["status"] = "task_created"
        result["continued"] = continued
        result["spoken"] = spoken.get("spoken", confirmation)
        result["draft"] = analysis["draft"]
        return result

    def _analyze_voice_task(self, text: str) -> dict:
        normalized = " ".join((text or "").strip().split())
        lower = normalized.lower()
        title = self._extract_voice_task_title(normalized)
        person = self._extract_voice_task_person(normalized)
        due_at = self._extract_voice_task_datetime(normalized)
        location = self._extract_voice_task_location(normalized)
        category = self._detect_voice_task_category(lower, due_at)
        is_actionable = self._is_actionable(lower, title, due_at)

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
            "decision": self._build_voice_task_decision(person, due_at, location),
        }
        return {
            "ok": True,
            "is_actionable": is_actionable,
            "missing_fields": missing_fields if is_actionable else [],
            "draft": draft,
        }

    def _is_actionable(self, lower: str, title: str, due_at) -> bool:
        action_keywords = (
            "remind me",
            "please remind",
            "remember to",
            "need to",
            "i need to",
            "todo",
            "task",
            "buy ",
            "call ",
            "pay ",
            "renew ",
            "pick up",
            "drop off",
            "bring ",
            "send ",
            "text ",
            "email ",
            "schedule ",
            "book ",
            "set up ",
            "visit ",
            "go to ",
        )
        calendar_keywords = (
            "appointment",
            "meeting",
            "class",
            "doctor",
            "dentist",
            "visit",
            "pickup",
            "drop-off",
            "dropoff",
        )
        if title and any(keyword in lower for keyword in action_keywords):
            return True
        if title and due_at:
            return True
        if title and any(keyword in lower for keyword in calendar_keywords):
            return True
        return False

    def _extract_voice_task_person(self, text: str) -> str:
        normalized = text.lower()
        person_aliases = {
            "Mom": ("mom", "mother", "mum"),
            "Dad": ("dad", "father"),
            "Alex": ("alex",),
            "Emma": ("emma",),
            "Family": ("family", "everyone", "all of us", "all", "us"),
        }
        for person, aliases in person_aliases.items():
            if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases):
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

        long_match = re.search(
            r"\b(?:(today|tomorrow|tonight|this evening|this afternoon|this morning)\s+)?(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
            lower,
        )
        if long_match:
            return self._build_datetime_from_match(now, long_match.group(1) or "", int(long_match.group(2)), int(long_match.group(3) or 0), long_match.group(4) or "")

        short_match = re.search(r"\b(?:(today|tomorrow)\s+)?(\d{1,2}):(\d{2})\b", lower)
        if short_match:
            return self._build_datetime_from_match(now, short_match.group(1) or "", int(short_match.group(2)), int(short_match.group(3)), "")

        return None

    def _build_datetime_from_match(self, now: datetime, day_hint: str, hour: int, minute: int, meridiem: str):
        meridiem = meridiem.lower()
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        if day_hint in {"tonight", "this evening", "this afternoon"} and not meridiem and hour < 12:
            hour += 12
        base_date = now.date()
        if day_hint == "tomorrow":
            base_date = (now + timedelta(days=1)).date()
        return datetime.combine(base_date, datetime.min.time()).replace(hour=hour, minute=minute)

    def _extract_voice_task_location(self, text: str) -> str:
        location_match = re.search(r"\b(?:at|in)\s+([A-Za-z][A-Za-z0-9'\- ]{1,40})", text)
        if location_match:
            return location_match.group(1).strip().title()
        return ""

    def _extract_voice_task_title(self, text: str) -> str:
        title = f" {text.strip()} ".lower()
        patterns = [
            r"\bhey lumi\b",
            r"\bhei lumi\b",
            r"\bhi lumi\b",
            r"\bhello lumi\b",
            r"\bremind me to\b",
            r"\bplease remind me to\b",
            r"\bplease remind\b",
            r"\bremember to\b",
            r"\bi need to\b",
            r"\bneed to\b",
            r"\bschedule\b",
            r"\bbook\b",
            r"\bset up\b",
            r"\btoday\b",
            r"\btomorrow\b",
            r"\btonight\b",
            r"\bthis evening\b",
            r"\bthis afternoon\b",
            r"\bthis morning\b",
            r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b",
            r"\bin\s+\d{1,2}\s*(?:minutes?|hours?)\b",
            r"\bfor mom\b",
            r"\bfor dad\b",
            r"\bfor alex\b",
            r"\bfor emma\b",
            r"\bfor family\b",
            r"\bfor everyone\b",
            r"\bat [a-z][a-z0-9'\- ]{1,40}\b",
            r"\bin [a-z][a-z0-9'\- ]{1,40}\b",
        ]
        for pattern in patterns:
            title = re.sub(pattern, " ", title, flags=re.IGNORECASE)
        title = re.sub(r"\b(?:mom|mother|mum|dad|father|alex|emma|family|everyone|all of us)\b", " ", title, flags=re.IGNORECASE)
        title = re.sub(r"[,:;.!?]", " ", title)
        title = " ".join(title.split()).strip(" -")
        return title[:60].title()

    def _detect_voice_task_category(self, lower: str, due_at) -> str:
        if any(keyword in lower for keyword in ("appointment", "meeting", "class", "doctor", "dentist", "visit", "schedule", "pickup", "drop-off", "dropoff")):
            return "calendar"
        return "reminder" if due_at else "reminder"

    def _priority_for_voice_task(self, lower: str, due_at) -> str:
        if any(keyword in lower for keyword in ("urgent", "asap", "right away", "immediately")):
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
