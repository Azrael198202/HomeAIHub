from __future__ import annotations

import hashlib
from datetime import datetime


class HomeIntakeService:
    def __init__(self, repository, ocr_service) -> None:
        self.repository = repository
        self.ocr_service = ocr_service

    def ingest_manual(self, create_event, text: str) -> dict:
        return create_event(text=text, source_type="manual")

    def ingest_screenshot(self, create_event, text: str) -> dict:
        recognized = self.ocr_service.recognize(text)
        return create_event(text=recognized, source_type="screenshot")

    def ingest_photo(self, create_event, text: str) -> dict:
        recognized = self.ocr_service.recognize(text)
        return create_event(text=recognized, source_type="photo")

    def ingest_voice(self, process_voice_task, transcript: str) -> dict:
        return process_voice_task(transcript)

    def receive_relay_delivery(self, payload: dict, ingest_manual, ingest_photo, ingest_voice) -> dict:
        relay_id = payload.get("relay_id", "")
        source_channel = payload.get("source_channel", "railway")
        content_kind = payload.get("content_kind", "")
        text = payload.get("text", "")
        filename = payload.get("filename", "")
        mime_type = payload.get("mime_type", "")
        byte_size = int(payload.get("byte_size", 0))
        content_base64 = payload.get("content_base64", "")
        summary = text.strip() or filename or content_kind
        existing = self.repository.get_relay_delivery(relay_id) if relay_id else None
        if existing:
            return {
                "ok": True,
                "relay_id": relay_id,
                "received": True,
                "acknowledged_at": existing.get("acknowledged_at", ""),
                "content_kind": existing.get("content_kind", content_kind),
                "duplicate": True,
            }

        sha256 = hashlib.sha256(content_base64.encode("utf-8")).hexdigest() if content_base64 else ""
        if content_kind == "message":
            intake_result = ingest_manual(text)
        elif content_kind == "photo":
            intake_result = ingest_photo(text or filename or "photo received")
        elif content_kind == "voice":
            intake_result = ingest_voice(text or filename or "voice received")
        else:
            return {"ok": False, "error": "unsupported_content_kind"}

        acknowledged_at = datetime.now().isoformat(timespec="seconds")
        self.repository.create_relay_delivery(
            {
                "relay_id": relay_id,
                "source_channel": source_channel,
                "content_kind": content_kind,
                "filename": filename,
                "mime_type": mime_type,
                "byte_size": byte_size,
                "sha256": sha256,
                "summary": summary[:200],
                "status": "acknowledged",
                "acknowledged_at": acknowledged_at,
            }
        )
        return {
            "ok": True,
            "relay_id": relay_id,
            "received": True,
            "acknowledged_at": acknowledged_at,
            "content_kind": content_kind,
            "intake": intake_result,
        }
