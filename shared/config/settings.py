from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    host: str = os.getenv("HOMEAIHUB_HOST", "127.0.0.1")
    port: int = int(os.getenv("HOMEAIHUB_PORT", "8080"))
    box_host: str = os.getenv("HOMEAIHUB_BOX_HOST", "127.0.0.1")
    box_port: int = int(os.getenv("HOMEAIHUB_BOX_PORT", "8090"))
    gateway_base_url_env: str = os.getenv("HOMEAIHUB_GATEWAY_BASE_URL", "").rstrip("/")
    railway_public_base_url_env: str = os.getenv("HOMEAIHUB_RAILWAY_PUBLIC_BASE_URL", "").rstrip("/")
    railway_api_base_url_env: str = os.getenv("HOMEAIHUB_RAILWAY_API_BASE_URL", "").rstrip("/")
    relay_temp_dir_env: str = os.getenv("HOMEAIHUB_RELAY_TEMP_DIR", "").rstrip()
    box_sync_interval_seconds: int = int(os.getenv("HOMEAIHUB_BOX_SYNC_INTERVAL_SECONDS", "10"))
    box_shared_token: str = os.getenv("HOMEAIHUB_BOX_SHARED_TOKEN", "")
    railway_cleanup_interval_seconds: int = int(os.getenv("HOMEAIHUB_RAILWAY_CLEANUP_INTERVAL_SECONDS", "60"))
    railway_job_retention_seconds: int = int(os.getenv("HOMEAIHUB_RAILWAY_JOB_RETENTION_SECONDS", "86400"))
    railway_box_stale_after_seconds: int = int(os.getenv("HOMEAIHUB_RAILWAY_BOX_STALE_AFTER_SECONDS", "90"))
    project_root: Path = Path(__file__).resolve().parents[2]
    database_name: str = os.getenv("HOMEAIHUB_DB_NAME", "home_ai_hub.db")

    @property
    def database_path(self) -> Path:
        return self.project_root / self.database_name

    @property
    def box_base_url(self) -> str:
        return f"http://{self.box_host}:{self.box_port}"

    @property
    def gateway_base_url(self) -> str:
        if self.gateway_base_url_env:
            return self.gateway_base_url_env
        return f"http://{self.host}:{self.port}"

    @property
    def railway_public_base_url(self) -> str:
        if self.railway_public_base_url_env:
            return self.railway_public_base_url_env
        return self.gateway_base_url

    @property
    def railway_api_base_url(self) -> str:
        if self.railway_api_base_url_env:
            return self.railway_api_base_url_env
        return self.railway_public_base_url

    @property
    def relay_temp_dir(self) -> Path:
        if self.relay_temp_dir_env:
            return Path(self.relay_temp_dir_env)
        return Path(tempfile.gettempdir()) / "homeaihub-relay"


settings = Settings()
