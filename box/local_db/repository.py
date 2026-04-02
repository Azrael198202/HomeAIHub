from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Optional


class LocalRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    person TEXT NOT NULL,
                    start_at TEXT,
                    due_at TEXT,
                    location TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL DEFAULT 'normal',
                    source_type TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    person TEXT NOT NULL DEFAULT '',
                    location TEXT NOT NULL DEFAULT '',
                    message TEXT NOT NULL,
                    event_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    acknowledged INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(event_id) REFERENCES events(id)
                );

                CREATE TABLE IF NOT EXISTS gateway_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_name TEXT NOT NULL,
                    node_role TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'online',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS node_capabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_name TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(node_name, capability)
                );

                CREATE TABLE IF NOT EXISTS gateway_sessions (
                    session_id TEXT PRIMARY KEY,
                    actor_name TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    allowed_agents TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS gateway_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    target_node TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_payload TEXT NOT NULL DEFAULT '{}',
                    response_payload TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS device_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    device_name TEXT NOT NULL,
                    device_secret TEXT NOT NULL,
                    claim_token TEXT NOT NULL,
                    claim_expires_at TEXT NOT NULL,
                    family_id TEXT NOT NULL DEFAULT '',
                    owner_user_id TEXT NOT NULL DEFAULT '',
                    owner_name TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending_claim',
                    paired_at TEXT NOT NULL DEFAULT '',
                    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS device_claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    claim_token TEXT NOT NULL,
                    actor_user_id TEXT NOT NULL,
                    actor_name TEXT NOT NULL,
                    result TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS relay_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    relay_id TEXT NOT NULL UNIQUE,
                    source_channel TEXT NOT NULL,
                    content_kind TEXT NOT NULL,
                    filename TEXT NOT NULL DEFAULT '',
                    mime_type TEXT NOT NULL DEFAULT '',
                    byte_size INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'received',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TEXT NOT NULL DEFAULT ''
                );
                

                CREATE TABLE IF NOT EXISTS openclaw_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'box',
                    actor_name TEXT NOT NULL DEFAULT 'system',
                    agent_name TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    target_node TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    request_payload TEXT NOT NULL DEFAULT '{}',
                    response_payload TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT NOT NULL DEFAULT ''
                );
                

                CREATE TABLE IF NOT EXISTS voice_input_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voice_session_id TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL DEFAULT 'local-mic',
                    input_kind TEXT NOT NULL DEFAULT 'transcript',
                    transcript TEXT NOT NULL DEFAULT '',
                    asr_backend TEXT NOT NULL DEFAULT 'mock_text',
                    status TEXT NOT NULL DEFAULT 'processing',
                    audio_path TEXT NOT NULL DEFAULT '',
                    result_summary TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT NOT NULL DEFAULT ''
                );
                """
            )

    def is_empty(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()
            return int(row["count"]) == 0

    def create_event(self, payload: dict) -> int:
        fields = (
            "title",
            "category",
            "person",
            "start_at",
            "due_at",
            "location",
            "summary",
            "priority",
            "source_type",
            "source_text",
            "status",
        )
        values = [payload.get(field, "") for field in fields]
        with self._connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO events ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
                values,
            )
            return int(cursor.lastrowid)

    def list_events(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM events
                WHERE status = 'active'
                ORDER BY COALESCE(start_at, due_at, created_at) ASC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def create_notification(self, payload: dict) -> int:
        fields = ("kind", "title", "person", "location", "message", "event_id")
        values = [payload.get(field, "") for field in fields]
        with self._connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO notifications ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
                values,
            )
            return int(cursor.lastrowid)

    def list_active_notifications(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM notifications
                WHERE acknowledged = 0
                ORDER BY created_at DESC
                LIMIT 8
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def notification_exists(self, kind: str, event_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM notifications
                WHERE kind = ? AND event_id = ? AND acknowledged = 0
                LIMIT 1
                """,
                (kind, event_id),
            ).fetchone()
            return row is not None

    def acknowledge_notification(self, notification_id: int) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE notifications SET acknowledged = 1 WHERE id = ?", (notification_id,))

    def seed_events(self, items: Iterable[dict]) -> None:
        for item in items:
            self.create_event(item)

    def upsert_device_state(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO device_state (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_device_state(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM device_state WHERE key = ?", (key,)).fetchone()
            return str(row["value"]) if row else default

    def list_device_states(self) -> dict:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM device_state").fetchall()
            return {row["key"]: row["value"] for row in rows}

    def register_node(self, node_name: str, node_role: str) -> None:
        with self._connect() as conn:
            exists = conn.execute("SELECT 1 FROM gateway_nodes WHERE node_name = ? LIMIT 1", (node_name,)).fetchone()
            if exists:
                conn.execute("UPDATE gateway_nodes SET status = 'online' WHERE node_name = ?", (node_name,))
                return
            conn.execute("INSERT INTO gateway_nodes (node_name, node_role, status) VALUES (?, ?, 'online')", (node_name, node_role))

    def list_nodes(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT node_name, node_role, status, created_at FROM gateway_nodes ORDER BY id ASC").fetchall()
            return [dict(row) for row in rows]

    def register_capability(self, node_name: str, capability: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO node_capabilities (node_name, capability, enabled)
                VALUES (?, ?, 1)
                ON CONFLICT(node_name, capability)
                DO UPDATE SET enabled = 1
                """,
                (node_name, capability),
            )

    def list_capabilities(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT node_name, capability, enabled, created_at FROM node_capabilities ORDER BY node_name ASC, capability ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def create_session(self, session_id: str, actor_name: str, actor_role: str, allowed_agents: str) -> dict:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO gateway_sessions (session_id, actor_name, actor_role, allowed_agents, status)
                VALUES (?, ?, ?, ?, 'active')
                ON CONFLICT(session_id)
                DO UPDATE SET
                    actor_name = excluded.actor_name,
                    actor_role = excluded.actor_role,
                    allowed_agents = excluded.allowed_agents,
                    status = 'active',
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (session_id, actor_name, actor_role, allowed_agents),
            )
        return self.get_session(session_id) or {}

    def get_session(self, session_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT session_id, actor_name, actor_role, allowed_agents, status, created_at, last_seen_at
                FROM gateway_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            return dict(row) if row else None

    def touch_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE gateway_sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE session_id = ?", (session_id,))

    def list_sessions(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT session_id, actor_name, actor_role, allowed_agents, status, created_at, last_seen_at
                FROM gateway_sessions
                ORDER BY created_at DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def log_command(
        self,
        session_id: str,
        agent_name: str,
        action_name: str,
        target_node: str,
        status: str,
        request_payload: str,
        response_payload: str,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO gateway_commands (
                    session_id, agent_name, action_name, target_node, status, request_payload, response_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, agent_name, action_name, target_node, status, request_payload, response_payload),
            )
            return int(cursor.lastrowid)

    def list_recent_commands(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, agent_name, action_name, target_node, status, request_payload, response_payload, created_at
                FROM gateway_commands
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def create_or_update_device(self, payload: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO devices (
                    device_id, device_name, device_secret, claim_token, claim_expires_at,
                    family_id, owner_user_id, owner_name, status, paired_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(device_id)
                DO UPDATE SET
                    device_name = excluded.device_name,
                    device_secret = excluded.device_secret,
                    claim_token = excluded.claim_token,
                    claim_expires_at = excluded.claim_expires_at,
                    family_id = excluded.family_id,
                    owner_user_id = excluded.owner_user_id,
                    owner_name = excluded.owner_name,
                    status = excluded.status,
                    paired_at = excluded.paired_at,
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (
                    payload["device_id"],
                    payload["device_name"],
                    payload["device_secret"],
                    payload["claim_token"],
                    payload["claim_expires_at"],
                    payload.get("family_id", ""),
                    payload.get("owner_user_id", ""),
                    payload.get("owner_name", ""),
                    payload.get("status", "pending_claim"),
                    payload.get("paired_at", ""),
                ),
            )

    def get_device(self, device_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
            return dict(row) if row else None

    def list_devices(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM devices ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]

    def update_device_last_seen(self, device_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE devices SET last_seen_at = CURRENT_TIMESTAMP WHERE device_id = ?", (device_id,))

    def bind_device(self, device_id: str, family_id: str, owner_user_id: str, owner_name: str, status: str, paired_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE devices
                SET family_id = ?, owner_user_id = ?, owner_name = ?, status = ?, paired_at = ?, last_seen_at = CURRENT_TIMESTAMP
                WHERE device_id = ?
                """,
                (family_id, owner_user_id, owner_name, status, paired_at, device_id),
            )

    def rotate_claim_token(self, device_id: str, claim_token: str, claim_expires_at: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE devices SET claim_token = ?, claim_expires_at = ?, status = ?, last_seen_at = CURRENT_TIMESTAMP WHERE device_id = ?",
                (claim_token, claim_expires_at, status, device_id),
            )

    def log_device_claim(self, device_id: str, claim_token: str, actor_user_id: str, actor_name: str, result: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO device_claims (device_id, claim_token, actor_user_id, actor_name, result)
                VALUES (?, ?, ?, ?, ?)
                """,
                (device_id, claim_token, actor_user_id, actor_name, result),
            )

    def list_device_claims(self, device_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM device_claims WHERE device_id = ? ORDER BY id DESC",
                (device_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def create_relay_delivery(self, payload: dict) -> int:
        fields = (
            "relay_id",
            "source_channel",
            "content_kind",
            "filename",
            "mime_type",
            "byte_size",
            "sha256",
            "summary",
            "status",
            "acknowledged_at",
        )
        values = [payload.get(field, "") for field in fields]
        with self._connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO relay_deliveries ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
                values,
            )
            return int(cursor.lastrowid)

    def get_relay_delivery(self, relay_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM relay_deliveries WHERE relay_id = ?", (relay_id,)).fetchone()
            return dict(row) if row else None

    def list_relay_deliveries(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM relay_deliveries
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]


    def create_openclaw_task(self, payload: dict) -> int:
        fields = (
            "task_id",
            "session_id",
            "source",
            "actor_name",
            "agent_name",
            "action_name",
            "target_node",
            "status",
            "request_payload",
            "response_payload",
        )
        values = [payload.get(field, "") for field in fields]
        with self._connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO openclaw_tasks ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
                values,
            )
            return int(cursor.lastrowid)

    def complete_openclaw_task(self, task_id: str, status: str, response_payload: str, completed_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE openclaw_tasks
                SET status = ?, response_payload = ?, completed_at = ?
                WHERE task_id = ?
                """,
                (status, response_payload, completed_at, task_id),
            )

    def get_openclaw_task(self, task_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM openclaw_tasks WHERE task_id = ?", (task_id,)).fetchone()
            return dict(row) if row else None

    def list_openclaw_tasks(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM openclaw_tasks
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]


    def create_voice_input_session(self, payload: dict) -> int:
        fields = (
            "voice_session_id",
            "source",
            "input_kind",
            "transcript",
            "asr_backend",
            "status",
            "audio_path",
        )
        values = [payload.get(field, "") for field in fields]
        with self._connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO voice_input_sessions ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
                values,
            )
            return int(cursor.lastrowid)

    def update_voice_input_session_asr(self, voice_session_id: str, transcript: str, asr_backend: str, audio_path: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE voice_input_sessions
                SET transcript = ?, asr_backend = ?, audio_path = ?
                WHERE voice_session_id = ?
                """,
                (transcript, asr_backend, audio_path, voice_session_id),
            )

    def complete_voice_input_session(self, voice_session_id: str, status: str, result_summary: str, completed_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE voice_input_sessions
                SET status = ?, result_summary = ?, completed_at = ?
                WHERE voice_session_id = ?
                """,
                (status, result_summary, completed_at, voice_session_id),
            )

    def list_voice_input_sessions(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM voice_input_sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_latest_voice_input_session(self, require_transcript: bool = False) -> Optional[dict]:
        query = """
            SELECT *
            FROM voice_input_sessions
        """
        params: tuple = ()
        if require_transcript:
            query += """
                WHERE status = 'completed'
                  AND TRIM(COALESCE(transcript, '')) <> ''
            """
        query += """
            ORDER BY id DESC
            LIMIT 1
        """
        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
            return dict(row) if row else None

    def prune_voice_input_sessions(self, retain_seconds: int, max_records: int) -> int:
        retain_seconds = max(60, int(retain_seconds))
        max_records = max(20, int(max_records))
        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM voice_input_sessions
                WHERE id NOT IN (
                    SELECT id
                    FROM voice_input_sessions
                    ORDER BY id DESC
                    LIMIT ?
                )
                OR created_at < datetime('now', ?)
                """,
                (max_records, f"-{retain_seconds} seconds"),
            )
            return int(cursor.rowcount or 0)
