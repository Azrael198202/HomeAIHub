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
    asr_backend: str = os.getenv("HOMEAIHUB_ASR_BACKEND", "auto")
    asr_whisper_command: str = os.getenv("HOMEAIHUB_ASR_WHISPER_COMMAND", "")
    asr_whisper_model: str = os.getenv("HOMEAIHUB_ASR_WHISPER_MODEL", "base")
    asr_whisper_language: str = os.getenv("HOMEAIHUB_ASR_WHISPER_LANGUAGE", "auto")
    asr_whisper_cache_dir_env: str = os.getenv("HOMEAIHUB_ASR_WHISPER_CACHE_DIR", "").rstrip()
    google_stt_api_key: str = os.getenv("HOMEAIHUB_GOOGLE_STT_API_KEY", os.getenv("GOOGLE_STT_API_KEY", os.getenv("HOMEAIHUB_GOOGLE_TTS_API_KEY", ""))).strip()
    google_stt_language_code: str = os.getenv("HOMEAIHUB_GOOGLE_STT_LANGUAGE_CODE", "en-US")
    google_stt_alternative_language_codes_env: str = os.getenv("HOMEAIHUB_GOOGLE_STT_ALTERNATIVE_LANGUAGE_CODES", "").strip()
    google_stt_model: str = os.getenv("HOMEAIHUB_GOOGLE_STT_MODEL", "latest_long")
    google_stt_enable_automatic_punctuation: bool = os.getenv("HOMEAIHUB_GOOGLE_STT_ENABLE_AUTOMATIC_PUNCTUATION", "true").lower() in {"1", "true", "yes", "on"}
    mic_backend: str = os.getenv("HOMEAIHUB_MIC_BACKEND", "auto")
    mic_duration_seconds: int = int(os.getenv("HOMEAIHUB_MIC_DURATION_SECONDS", "4"))
    mic_min_duration_seconds: float = float(os.getenv("HOMEAIHUB_MIC_MIN_DURATION_SECONDS", "2.5"))
    mic_max_duration_seconds: float = float(os.getenv("HOMEAIHUB_MIC_MAX_DURATION_SECONDS", "10"))
    mic_silence_seconds: float = float(os.getenv("HOMEAIHUB_MIC_SILENCE_SECONDS", "1.2"))
    mic_silence_threshold: int = int(os.getenv("HOMEAIHUB_MIC_SILENCE_THRESHOLD", "450"))
    mic_sample_rate: int = int(os.getenv("HOMEAIHUB_MIC_SAMPLE_RATE", "16000"))
    mic_channels: int = int(os.getenv("HOMEAIHUB_MIC_CHANNELS", "1"))
    mic_device_index: int = int(os.getenv("HOMEAIHUB_MIC_DEVICE_INDEX", "-1"))
    mic_listener_poll_seconds: int = int(os.getenv("HOMEAIHUB_MIC_LISTENER_POLL_SECONDS", "2"))
    voice_input_cleanup_after_process: bool = os.getenv("HOMEAIHUB_VOICE_INPUT_CLEANUP_AFTER_PROCESS", "true").lower() in {"1", "true", "yes", "on"}
    voice_input_retention_seconds: int = int(os.getenv("HOMEAIHUB_VOICE_INPUT_RETENTION_SECONDS", "900"))
    voice_input_max_temp_files: int = int(os.getenv("HOMEAIHUB_VOICE_INPUT_MAX_TEMP_FILES", "24"))
    voice_input_session_retention_seconds: int = int(os.getenv("HOMEAIHUB_VOICE_INPUT_SESSION_RETENTION_SECONDS", "604800"))
    voice_input_session_max_records: int = int(os.getenv("HOMEAIHUB_VOICE_INPUT_SESSION_MAX_RECORDS", "500"))
    voice_input_transcript_dir_env: str = os.getenv("HOMEAIHUB_VOICE_INPUT_TRANSCRIPT_DIR", "").rstrip()
    voice_listener_autostart: bool = os.getenv("HOMEAIHUB_VOICE_LISTENER_AUTOSTART", "true").lower() in {"1", "true", "yes", "on"}
    voice_session_timeout_seconds: int = int(os.getenv("HOMEAIHUB_VOICE_SESSION_TIMEOUT_SECONDS", "20"))
    railway_cleanup_interval_seconds: int = int(os.getenv("HOMEAIHUB_RAILWAY_CLEANUP_INTERVAL_SECONDS", "60"))
    railway_job_retention_seconds: int = int(os.getenv("HOMEAIHUB_RAILWAY_JOB_RETENTION_SECONDS", "86400"))
    railway_box_stale_after_seconds: int = int(os.getenv("HOMEAIHUB_RAILWAY_BOX_STALE_AFTER_SECONDS", "90"))
    tv_dashboard_url_env: str = os.getenv("HOMEAIHUB_TV_DASHBOARD_URL", "").rstrip("/")
    tv_dashboard_browser_autolaunch: bool = os.getenv("HOMEAIHUB_TV_DASHBOARD_BROWSER_AUTOLAUNCH", "true").lower() in {"1", "true", "yes", "on"}
    tts_backend: str = os.getenv("HOMEAIHUB_TTS_BACKEND", "auto")
    tts_voice_name: str = os.getenv("HOMEAIHUB_TTS_VOICE_NAME", "")
    tts_rate: int = int(os.getenv("HOMEAIHUB_TTS_RATE", "0"))
    google_tts_api_key: str = os.getenv("HOMEAIHUB_GOOGLE_TTS_API_KEY", os.getenv("GOOGLE_TTS_API_KEY", "")).strip()
    google_tts_voice_name: str = os.getenv("HOMEAIHUB_GOOGLE_TTS_VOICE_NAME", "en-US-Neural2-F")
    google_tts_language_code: str = os.getenv("HOMEAIHUB_GOOGLE_TTS_LANGUAGE_CODE", "en-US")
    google_tts_gender: str = os.getenv("HOMEAIHUB_GOOGLE_TTS_GENDER", "FEMALE")
    google_tts_speaking_rate: float = float(os.getenv("HOMEAIHUB_GOOGLE_TTS_SPEAKING_RATE", "1.0"))
    google_tts_cache_dir_env: str = os.getenv("HOMEAIHUB_GOOGLE_TTS_CACHE_DIR", "").rstrip()
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

    @property
    def asr_whisper_cache_dir(self) -> Path:
        if self.asr_whisper_cache_dir_env:
            return Path(self.asr_whisper_cache_dir_env)
        return self.project_root / "data" / "whisper-cache"

    @property
    def google_stt_alternative_language_codes(self) -> list[str]:
        raw = self.google_stt_alternative_language_codes_env
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def tv_dashboard_url(self) -> str:
        if self.tv_dashboard_url_env:
            return self.tv_dashboard_url_env
        return f"{self.box_base_url}/dashboard"

    @property
    def google_tts_cache_dir(self) -> Path:
        if self.google_tts_cache_dir_env:
            return Path(self.google_tts_cache_dir_env)
        return self.project_root / "data" / "google-tts-cache"

    @property
    def voice_input_transcript_dir(self) -> Path:
        if self.voice_input_transcript_dir_env:
            return Path(self.voice_input_transcript_dir_env)
        return self.project_root / "data" / "voice-transcripts"


settings = Settings()
