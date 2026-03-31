from __future__ import annotations

import base64
import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


class RailwayRelayStore:
    def __init__(self, db_path: str | Path, relay_temp_dir: str | Path) -> None:
        self.db_path = str(db_path)
        self.relay_temp_dir = Path(relay_temp_dir)
        self.relay_temp_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS registered_boxes (
                    device_id TEXT PRIMARY KEY,
                    device_name TEXT NOT NULL,
                    pairing_status TEXT NOT NULL DEFAULT 'pending_claim',
                    owner_name TEXT NOT NULL DEFAULT '',
                    family_id TEXT NOT NULL DEFAULT '',
                    box_status TEXT NOT NULL DEFAULT 'offline',
                    dashboard_path TEXT NOT NULL DEFAULT '/dashboard',
                    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_sync_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS relay_jobs (
                    relay_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    content_kind TEXT NOT NULL,
                    text TEXT NOT NULL DEFAULT '',
                    filename TEXT NOT NULL DEFAULT '',
                    mime_type TEXT NOT NULL DEFAULT '',
                    byte_size INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT NOT NULL DEFAULT '',
                    temp_path TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TEXT NOT NULL DEFAULT ''
                );
                """
            )

    def register_box(self, payload: dict) -> dict:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO registered_boxes (
                    device_id, device_name, pairing_status, owner_name, family_id,
                    box_status, dashboard_path, last_seen_at, last_sync_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(device_id)
                DO UPDATE SET
                    device_name = excluded.device_name,
                    pairing_status = excluded.pairing_status,
                    owner_name = excluded.owner_name,
                    family_id = excluded.family_id,
                    box_status = excluded.box_status,
                    dashboard_path = excluded.dashboard_path,
                    last_seen_at = CURRENT_TIMESTAMP,
                    last_sync_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    payload["device_id"],
                    payload.get("device_name", "HomeAIHub Box"),
                    payload.get("pairing_status", "pending_claim"),
                    payload.get("owner_name", ""),
                    payload.get("family_id", ""),
                    payload.get("box_status", "online"),
                    payload.get("dashboard_path", "/dashboard"),
                ),
            )
        return self.get_box(payload["device_id"]) or {}

    def heartbeat_box(self, payload: dict) -> dict:
        return self.register_box(payload)

    def get_box(self, device_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM registered_boxes WHERE device_id = ?", (device_id,)).fetchone()
            return dict(row) if row else None

    def get_primary_box(self) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM registered_boxes
                ORDER BY last_seen_at DESC, updated_at DESC
                LIMIT 1
                """
            ).fetchone()
            return dict(row) if row else None

    def list_boxes(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM registered_boxes
                ORDER BY last_seen_at DESC, updated_at DESC
                LIMIT ?
                """
                , (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def create_relay_job(self, payload: dict) -> dict:
        temp_path = ""
        raw_bytes = b""
        content_base64 = payload.get("content_base64", "")
        if content_base64:
            raw_bytes = base64.b64decode(content_base64.encode("utf-8"), validate=True)
            filename = payload.get("filename", "")
            suffix = Path(filename).suffix if filename else ""
            job_path = self.relay_temp_dir / f"{payload['relay_id']}{suffix}"
            job_path.write_bytes(raw_bytes)
            temp_path = str(job_path)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO relay_jobs (
                    relay_id, device_id, content_kind, text, filename, mime_type,
                    byte_size, sha256, temp_path, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    payload["relay_id"],
                    payload["device_id"],
                    payload["content_kind"],
                    payload.get("text", ""),
                    payload.get("filename", ""),
                    payload.get("mime_type", ""),
                    len(raw_bytes),
                    hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else "",
                    temp_path,
                ),
            )
        return self.get_relay_job(payload["relay_id"]) or {}

    def get_relay_job(self, relay_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM relay_jobs WHERE relay_id = ?", (relay_id,)).fetchone()
            return dict(row) if row else None

    def list_pending_jobs(self, device_id: str, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM relay_jobs
                WHERE device_id = ? AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (device_id, limit),
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            temp_path = item.get("temp_path", "")
            if temp_path and Path(temp_path).exists():
                item["content_base64"] = base64.b64encode(Path(temp_path).read_bytes()).decode("utf-8")
            else:
                item["content_base64"] = ""
            items.append(item)
        return items

    def acknowledge_job(self, relay_id: str) -> dict:
        job = self.get_relay_job(relay_id)
        if not job:
            return {"ok": False, "error": "relay_job_not_found"}

        temp_path = job.get("temp_path", "")
        deleted = False
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink(missing_ok=True)
            deleted = True

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE relay_jobs
                SET status = 'acknowledged', acknowledged_at = CURRENT_TIMESTAMP
                WHERE relay_id = ?
                """,
                (relay_id,),
            )
        updated = self.get_relay_job(relay_id) or {}
        return {
            "ok": True,
            "relay_id": relay_id,
            "deleted_from_railway": deleted,
            "status": updated.get("status", "acknowledged"),
            "acknowledged_at": updated.get("acknowledged_at", ""),
        }

    def cleanup_acknowledged_jobs(self, retention_seconds: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=retention_seconds)
        cutoff_text = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT relay_id, temp_path
                FROM relay_jobs
                WHERE status = 'acknowledged' AND acknowledged_at != '' AND acknowledged_at < ?
                """
                , (cutoff_text,),
            ).fetchall()
            for row in rows:
                temp_path = row["temp_path"]
                if temp_path and Path(temp_path).exists():
                    Path(temp_path).unlink(missing_ok=True)
            conn.execute(
                """
                DELETE FROM relay_jobs
                WHERE status = 'acknowledged' AND acknowledged_at != '' AND acknowledged_at < ?
                """
                , (cutoff_text,),
            )
            return len(rows)

    def mark_stale_boxes_offline(self, stale_after_seconds: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_after_seconds)
        cutoff_text = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE registered_boxes
                SET box_status = 'offline', updated_at = CURRENT_TIMESTAMP
                WHERE last_seen_at < ? AND box_status != 'offline'
                """
                , (cutoff_text,),
            )
            return int(cursor.rowcount)
