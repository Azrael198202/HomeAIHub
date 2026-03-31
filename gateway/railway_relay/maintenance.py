from __future__ import annotations

import threading


class RailwayMaintenanceService:
    def __init__(self, relay_store, cleanup_interval_seconds: int, job_retention_seconds: int, box_stale_after_seconds: int) -> None:
        self.relay_store = relay_store
        self.cleanup_interval_seconds = max(10, cleanup_interval_seconds)
        self.job_retention_seconds = max(60, job_retention_seconds)
        self.box_stale_after_seconds = max(30, box_stale_after_seconds)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread:
            return
        self._thread = threading.Thread(target=self._run_loop, name="railway-maintenance", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.relay_store.mark_stale_boxes_offline(self.box_stale_after_seconds)
                self.relay_store.cleanup_acknowledged_jobs(self.job_retention_seconds)
            except Exception:
                pass
            self._stop_event.wait(self.cleanup_interval_seconds)
