from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class ParsedItem:
    title: str
    category: str
    person: str
    start_at: Optional[datetime]
    due_at: Optional[datetime]
    location: str
    summary: str
    priority: str
    source_type: str
    source_text: str
    requires_confirmation: bool = True


@dataclass(slots=True)
class Notification:
    id: int
    kind: str
    title: str
    person: str
    location: str
    message: str
    event_id: Optional[int]
    created_at: str


@dataclass(slots=True)
class GatewayCommandResult:
    ok: bool
    route: str
    message: str


@dataclass(slots=True)
class GatewaySession:
    session_id: str
    actor_name: str
    actor_role: str
    allowed_agents: str
    status: str


@dataclass(slots=True)
class GatewayCommandRecord:
    session_id: str
    agent_name: str
    action_name: str
    target_node: str
    status: str
