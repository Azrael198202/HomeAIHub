from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from box.calendar_engine.service import CalendarEngine
from box.event_parser.service import EventParserService
from box.home_api.service import HomeAPI
from box.hub_orchestrator.service import HubOrchestratorService
from box.info_engine.service import InfoEngine
from box.local_db.repository import LocalRepository
from box.ocr_service.service import OCRService
from box.openclaw_runtime.service import OpenClawBoxRuntime
from box.railway_sync.service import RailwaySyncService
from box.reminder_engine.service import ReminderEngine
from box.tts_service.service import TTSService
from box.tv_control_service.service import TVControlService
from box.tv_dashboard.service import TVDashboardService
from box.voice_input.service import VoiceInputService
from shared.config.settings import settings


@dataclass(slots=True)
class BoxApplication:
    repository: LocalRepository
    home_api: HomeAPI
    hub_orchestrator_service: HubOrchestratorService
    openclaw_runtime: OpenClawBoxRuntime
    voice_input_service: VoiceInputService
    railway_sync_service: RailwaySyncService
    tts_service: TTSService
    tv_control_service: TVControlService
    tv_dashboard_web_dir: Path

    def shutdown(self) -> None:
        self.voice_input_service.stop_listener()
        self.railway_sync_service.stop()


def create_box_application() -> BoxApplication:
    repository = LocalRepository(settings.database_path)
    tv_dashboard_web_dir = settings.project_root / "box" / "tv_dashboard" / "web"
    ocr_service = OCRService()
    parser_service = EventParserService()
    calendar_engine = CalendarEngine(repository)
    reminder_engine = ReminderEngine(repository)
    info_engine = InfoEngine(repository)
    tts_service = TTSService(
        repository,
        backend=settings.tts_backend,
        voice_name=settings.tts_voice_name,
        rate=settings.tts_rate,
        google_api_key=settings.google_tts_api_key,
        google_voice_name=settings.google_tts_voice_name,
        google_language_code=settings.google_tts_language_code,
        google_gender=settings.google_tts_gender,
        google_speaking_rate=settings.google_tts_speaking_rate,
        google_cache_dir=str(settings.google_tts_cache_dir),
    )
    tv_control_service = TVControlService(
        repository,
        dashboard_url=settings.tv_dashboard_url,
        browser_autolaunch=settings.tv_dashboard_browser_autolaunch,
    )
    tv_dashboard_service = TVDashboardService(repository)
    openclaw_runtime = OpenClawBoxRuntime(repository)
    hub_orchestrator_service = HubOrchestratorService(
        repository=repository,
        tts_service=tts_service,
        tv_control_service=tv_control_service,
        tv_dashboard_service=tv_dashboard_service,
        voice_session_timeout_seconds=settings.voice_session_timeout_seconds,
    )
    home_api = HomeAPI(
        repository=repository,
        ocr_service=ocr_service,
        parser_service=parser_service,
        calendar_engine=calendar_engine,
        reminder_engine=reminder_engine,
        info_engine=info_engine,
        tts_service=tts_service,
        tv_control_service=tv_control_service,
        tv_dashboard_service=tv_dashboard_service,
        hub_orchestrator_service=hub_orchestrator_service,
        openclaw_runtime=openclaw_runtime,
    )
    home_api.bootstrap()
    voice_input_service = VoiceInputService(
        repository=repository,
        hub_orchestrator_service=hub_orchestrator_service,
        asr_backend=settings.asr_backend,
        whisper_command=settings.asr_whisper_command,
        whisper_model=settings.asr_whisper_model,
        whisper_language=settings.asr_whisper_language,
        whisper_cache_dir=str(settings.asr_whisper_cache_dir),
        google_api_key=settings.google_stt_api_key,
        google_language_code=settings.google_stt_language_code,
        google_alternative_language_codes=settings.google_stt_alternative_language_codes,
        google_model=settings.google_stt_model,
        google_enable_automatic_punctuation=settings.google_stt_enable_automatic_punctuation,
        mic_backend=settings.mic_backend,
        mic_duration_seconds=settings.mic_duration_seconds,
        mic_min_duration_seconds=settings.mic_min_duration_seconds,
        mic_max_duration_seconds=settings.mic_max_duration_seconds,
        mic_silence_seconds=settings.mic_silence_seconds,
        mic_silence_threshold=settings.mic_silence_threshold,
        mic_sample_rate=settings.mic_sample_rate,
        mic_channels=settings.mic_channels,
        mic_device_index=settings.mic_device_index,
        listener_poll_seconds=settings.mic_listener_poll_seconds,
        cleanup_after_process=settings.voice_input_cleanup_after_process,
        retention_seconds=settings.voice_input_retention_seconds,
        max_temp_files=settings.voice_input_max_temp_files,
        session_retention_seconds=settings.voice_input_session_retention_seconds,
        session_max_records=settings.voice_input_session_max_records,
        transcript_dir=str(settings.voice_input_transcript_dir),
    )
    railway_sync_service = RailwaySyncService(
        base_url=settings.railway_api_base_url,
        home_api=home_api,
        sync_interval_seconds=settings.box_sync_interval_seconds,
        shared_token=settings.box_shared_token,
    )
    railway_sync_service.start()
    if settings.voice_listener_autostart:
        voice_input_service.start_listener()
    return BoxApplication(
        repository=repository,
        home_api=home_api,
        hub_orchestrator_service=hub_orchestrator_service,
        openclaw_runtime=openclaw_runtime,
        voice_input_service=voice_input_service,
        railway_sync_service=railway_sync_service,
        tts_service=tts_service,
        tv_control_service=tv_control_service,
        tv_dashboard_web_dir=tv_dashboard_web_dir,
    )
