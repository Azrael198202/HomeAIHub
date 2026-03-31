from __future__ import annotations

import json
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class RailwaySyncService:
    def __init__(self, base_url: str, home_api, sync_interval_seconds: int = 10, shared_token: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.home_api = home_api
        self.sync_interval_seconds = max(3, sync_interval_seconds)
        self.shared_token = shared_token
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def enabled(self) -> bool:
        return bool(self.base_url)

    def start(self) -> None:
        if not self.enabled() or self._thread:
            return
        self._thread = threading.Thread(target=self._run_loop, name="railway-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._sync_once()
            except Exception:
                pass
            self._stop_event.wait(self.sync_interval_seconds)

    def _sync_once(self) -> None:
        status = self.home_api.external_box_status()
        payload = {
            "device_id": status["device_id"],
            "device_name": status["device_name"],
            "pairing_status": status["status"],
            "owner_name": status["owner_name"],
            "family_id": status["family_id"],
            "box_status": "online" if status["box_service_healthy"] else "offline",
            "dashboard_path": status["dashboard_path"],
        }
        self._post("/api/railway/box/register", payload)
        self._post("/api/railway/box/heartbeat", payload)
        jobs = self._get(f"/api/railway/relay/pending?{urlencode({'device_id': status['device_id']})}")
        for job in jobs.get("items", []):
            result = self.home_api.receive_relay_delivery(
                relay_id=job.get("relay_id", ""),
                source_channel=job.get("source_channel", "railway"),
                content_kind=job.get("content_kind", ""),
                text=job.get("text", ""),
                filename=job.get("filename", ""),
                mime_type=job.get("mime_type", ""),
                byte_size=int(job.get("byte_size", 0)),
                content_base64=job.get("content_base64", ""),
            )
            if result.get("ok"):
                self._post(
                    "/api/railway/relay/ack",
                    {
                        "relay_id": job.get("relay_id", ""),
                        "device_id": status["device_id"],
                    },
                )

    def _get(self, path: str) -> dict:
        request = Request(f"{self.base_url}{path}", headers=self._headers(), method="GET")
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=self._headers({"Content-Type": "application/json"}),
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def _headers(self, base: dict | None = None) -> dict:
        headers = dict(base or {})
        if self.shared_token:
            headers["X-HomeAIHub-Box-Token"] = self.shared_token
        return headers
