from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    host: str = os.getenv("HOMEAIHUB_HOST", "127.0.0.1")
    port: int = int(os.getenv("HOMEAIHUB_PORT", "8080"))
    box_host: str = os.getenv("HOMEAIHUB_BOX_HOST", "127.0.0.1")
    box_port: int = int(os.getenv("HOMEAIHUB_BOX_PORT", "8090"))
    project_root: Path = Path(__file__).resolve().parents[2]
    database_name: str = os.getenv("HOMEAIHUB_DB_NAME", "home_ai_hub.db")

    @property
    def database_path(self) -> Path:
        return self.project_root / self.database_name

    @property
    def box_base_url(self) -> str:
        return f"http://{self.box_host}:{self.box_port}"


settings = Settings()
