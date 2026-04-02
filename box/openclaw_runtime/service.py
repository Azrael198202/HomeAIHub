from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Callable


class OpenClawBoxRuntime:
    def __init__(self, repository) -> None:
        self.repository = repository
        self._agents: dict[str, dict] = {}

    def register_agent(self, agent_name: str, role: str, description: str) -> None:
        agent = self._agents.setdefault(
            agent_name,
            {
                "name": agent_name,
                "role": role,
                "description": description,
                "actions": {},
            },
        )
        agent["role"] = role
        agent["description"] = description

    def register_action(
        self,
        agent_name: str,
        action_name: str,
        target_node: str,
        permission: str,
        handler: Callable[[dict], dict],
        description: str = "",
    ) -> None:
        if agent_name not in self._agents:
            raise ValueError(f"agent_not_registered:{agent_name}")
        self._agents[agent_name]["actions"][action_name] = {
            "target_node": target_node,
            "permission": permission,
            "description": description,
            "handler": handler,
        }
        self.repository.register_node(agent_name, "agent")
        self.repository.register_capability(agent_name, action_name)

    def list_agents(self) -> list[dict]:
        items: list[dict] = []
        for agent in self._agents.values():
            items.append(
                {
                    "name": agent["name"],
                    "role": agent["role"],
                    "description": agent["description"],
                    "actions": [
                        {
                            "name": action_name,
                            "target_node": action["target_node"],
                            "permission": action["permission"],
                            "description": action["description"],
                        }
                        for action_name, action in sorted(agent["actions"].items())
                    ],
                }
            )
        return sorted(items, key=lambda item: item["name"])

    def overview(self, task_limit: int = 12) -> dict:
        return {
            "agents": self.list_agents(),
            "recent_tasks": self.repository.list_openclaw_tasks(task_limit),
        }

    def dispatch_session(self, session_id: str, agent_name: str, action_name: str, payload: dict, source: str = "gateway") -> dict:
        session = self.repository.get_session(session_id)
        if not session:
            return {"ok": False, "error": "session_not_found"}
        self.repository.touch_session(session_id)
        return self._execute(
            session_id=session_id,
            actor_name=session.get("actor_name", "gateway"),
            agent_name=agent_name,
            action_name=action_name,
            payload=payload,
            source=source,
            log_command=True,
        )

    def dispatch_internal(
        self,
        agent_name: str,
        action_name: str,
        payload: dict,
        source: str = "box",
        actor_name: str = "system",
        session_id: str = "",
    ) -> dict:
        return self._execute(
            session_id=session_id,
            actor_name=actor_name,
            agent_name=agent_name,
            action_name=action_name,
            payload=payload,
            source=source,
            log_command=bool(session_id),
        )

    def _execute(
        self,
        session_id: str,
        actor_name: str,
        agent_name: str,
        action_name: str,
        payload: dict,
        source: str,
        log_command: bool,
    ) -> dict:
        agent = self._agents.get(agent_name)
        if not agent:
            return {"ok": False, "error": "agent_not_found"}
        action = agent["actions"].get(action_name)
        if not action:
            return {"ok": False, "error": "action_not_found"}

        request_payload = dict(payload or {})
        task_id = str(uuid.uuid4())
        target_node = action["target_node"]
        self.repository.create_openclaw_task(
            {
                "task_id": task_id,
                "session_id": session_id,
                "source": source,
                "actor_name": actor_name,
                "agent_name": agent_name,
                "action_name": action_name,
                "target_node": target_node,
                "status": "running",
                "request_payload": json.dumps(request_payload, ensure_ascii=False),
                "response_payload": "{}",
            }
        )

        try:
            result = action["handler"](request_payload)
            if not isinstance(result, dict):
                result = {"ok": True, "result": result}
            status = "success" if result.get("ok", True) else "rejected"
        except Exception as exc:  # pragma: no cover - defensive runtime barrier
            result = {"ok": False, "error": f"runtime_exception:{exc}"}
            status = "failed"

        finished_at = datetime.now().isoformat(timespec="seconds")
        self.repository.complete_openclaw_task(
            task_id,
            status,
            json.dumps(result, ensure_ascii=False),
            finished_at,
        )
        if log_command:
            self.repository.log_command(
                session_id=session_id,
                agent_name=agent_name,
                action_name=action_name,
                target_node=target_node,
                status=status,
                request_payload=json.dumps(request_payload, ensure_ascii=False),
                response_payload=json.dumps(result, ensure_ascii=False),
            )
        result.setdefault("ok", status == "success")
        result["task_id"] = task_id
        result["agent"] = agent_name
        result["action"] = action_name
        result["target_node"] = target_node
        result["completed_at"] = finished_at
        return result
