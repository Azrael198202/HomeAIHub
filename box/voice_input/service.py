from __future__ import annotations

import base64
import binascii
import tempfile
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from box.voice_input.adapters import build_asr_adapter
from box.voice_input.recorders import build_mic_recorder


class VoiceInputService:
    def __init__(
        self,
        repository,
        hub_orchestrator_service,
        asr_backend: str = "auto",
        whisper_command: str = "",
        whisper_model: str = "tiny",
        whisper_language: str = "zh",
        whisper_cache_dir: str = "",
        google_api_key: str = "",
        google_language_code: str = "en-US",
        google_alternative_language_codes: list[str] | None = None,
        google_model: str = "latest_long",
        google_enable_automatic_punctuation: bool = True,
        mic_backend: str = "auto",
        mic_duration_seconds: int = 6,
        mic_min_duration_seconds: float = 2.5,
        mic_max_duration_seconds: float = 10.0,
        mic_silence_seconds: float = 1.2,
        mic_silence_threshold: int = 450,
        mic_sample_rate: int = 16000,
        mic_channels: int = 1,
        mic_device_index: int = -1,
        listener_poll_seconds: int = 2,
        cleanup_after_process: bool = True,
        retention_seconds: int = 900,
        max_temp_files: int = 24,
        session_retention_seconds: int = 604800,
        session_max_records: int = 500,
        transcript_dir: str = "",
    ) -> None:
        self.repository = repository
        self.hub_orchestrator_service = hub_orchestrator_service
        self.asr_adapter = build_asr_adapter(
            asr_backend,
            whisper_command,
            whisper_model,
            whisper_language,
            whisper_cache_dir,
            google_api_key=google_api_key,
            google_language_code=google_language_code,
            google_alternative_language_codes=google_alternative_language_codes or [],
            google_model=google_model,
            google_enable_automatic_punctuation=google_enable_automatic_punctuation,
        )
        self.mic_recorder = build_mic_recorder(mic_backend)
        self.default_duration_seconds = max(1, int(mic_duration_seconds))
        self.min_duration_seconds = max(0.5, float(mic_min_duration_seconds))
        self.max_duration_seconds = max(self.min_duration_seconds, float(mic_max_duration_seconds))
        self.silence_seconds = max(0.3, float(mic_silence_seconds))
        self.silence_threshold = max(1, int(mic_silence_threshold))
        self.default_sample_rate = max(8000, int(mic_sample_rate))
        self.default_channels = max(1, int(mic_channels))
        preferred = mic_device_index if int(mic_device_index) >= 0 else None
        self.default_device_index = preferred if preferred is not None else self.mic_recorder.choose_default_device()
        self.default_sample_rate = self._resolve_sample_rate(self.default_device_index, self.default_sample_rate)
        self.listener_poll_seconds = max(1, int(listener_poll_seconds))
        self.cleanup_after_process = bool(cleanup_after_process)
        self.retention_seconds = max(60, int(retention_seconds))
        self.max_temp_files = max(4, int(max_temp_files))
        self.session_retention_seconds = max(3600, int(session_retention_seconds))
        self.session_max_records = max(20, int(session_max_records))
        self.temp_dir = Path(tempfile.gettempdir()) / "homeaihub-voice-input"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_dir = Path(transcript_dir) if transcript_dir else (self.temp_dir / "transcripts")
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self._listener_thread: threading.Thread | None = None
        self._listener_stop = threading.Event()
        self.repository.upsert_device_state("voice_listener_mode", "manual")
        if self.default_device_index is not None:
            self.repository.upsert_device_state("voice_default_device_index", str(self.default_device_index))
        self._cleanup_temp_files()

    def status(self) -> dict:
        sessions = self.repository.list_voice_input_sessions(8)
        states = self.repository.list_device_states()
        return {
            "ok": True,
            "asr_backend": getattr(self.asr_adapter, "backend_name", "unknown"),
            "mic_backend": getattr(self.mic_recorder, "backend_name", "unknown"),
            "listener_state": states.get("voice_listener_state", "passive"),
            "listener_mode": states.get("voice_listener_mode", "manual"),
            "wake_phrase": states.get("voice_wake_phrase", "hey lumi"),
            "wake_ack_message": states.get("voice_wake_ack_message", "Hey master, Need any help"),
            "default_duration_seconds": self.default_duration_seconds,
            "min_duration_seconds": self.min_duration_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "silence_seconds": self.silence_seconds,
            "silence_threshold": self.silence_threshold,
            "default_sample_rate": self.default_sample_rate,
            "default_channels": self.default_channels,
            "default_device_index": self.default_device_index,
            "listener_poll_seconds": self.listener_poll_seconds,
            "listener_running": bool(self._listener_thread and self._listener_thread.is_alive()),
            "cleanup_after_process": self.cleanup_after_process,
            "retention_seconds": self.retention_seconds,
            "max_temp_files": self.max_temp_files,
            "session_retention_seconds": self.session_retention_seconds,
            "session_max_records": self.session_max_records,
            "transcript_dir": str(self.transcript_dir),
            "recent_sessions": sessions,
        }

    def list_devices(self) -> dict:
        return {
            "ok": True,
            "backend": getattr(self.mic_recorder, "backend_name", "unknown"),
            "default_device_index": self.default_device_index,
            "items": self.mic_recorder.list_devices(),
        }

    def start_listener(self, device_index: int | None = None) -> dict:
        if self._listener_thread and self._listener_thread.is_alive():
            return {"ok": True, "listener_running": True, "message": "listener_already_running"}
        if device_index is not None and int(device_index) >= 0:
            self.default_device_index = int(device_index)
            self.default_sample_rate = self._resolve_sample_rate(self.default_device_index, self.default_sample_rate)
            self.repository.upsert_device_state("voice_default_device_index", str(self.default_device_index))
        self._listener_stop.clear()
        self.repository.upsert_device_state("voice_listener_mode", "continuous")
        self.repository.upsert_device_state("voice_listener_state", "listening")
        self._listener_thread = threading.Thread(target=self._listener_loop, name="voice-listener-loop", daemon=True)
        self._listener_thread.start()
        return {"ok": True, "listener_running": True, "device_index": self.default_device_index}

    def stop_listener(self) -> dict:
        self._listener_stop.set()
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=self.default_duration_seconds + 2)
        self.repository.upsert_device_state("voice_listener_mode", "manual")
        self.repository.upsert_device_state("voice_listener_state", "passive")
        return {"ok": True, "listener_running": False}

    def capture_from_microphone(self, duration_seconds: int | None = None, device_index: int | None = None, source: str = "local-mic") -> dict:
        duration = duration_seconds or self.default_duration_seconds
        device = self.default_device_index if device_index is None or int(device_index) < 0 else int(device_index)
        session_id = self._create_session(source=source, input_kind="microphone", transcript="")
        if float(duration) <= 0:
            capture = self.mic_recorder.capture_until_silence(
                min_duration_seconds=self.min_duration_seconds,
                max_duration_seconds=self.max_duration_seconds,
                silence_seconds=self.silence_seconds,
                silence_threshold=self.silence_threshold,
                sample_rate=self.default_sample_rate,
                channels=self.default_channels,
                device=device,
            )
        else:
            capture = self.mic_recorder.capture(
                duration_seconds=int(duration),
                sample_rate=self.default_sample_rate,
                channels=self.default_channels,
                device=device,
            )
        if not capture.get("ok"):
            self._complete_session(session_id, "failed", capture)
            return {**capture, "voice_session_id": session_id}

        return self._transcribe_and_route(
            session_id=session_id,
            audio_path=Path(capture["audio_path"]),
            mime_type=capture.get("mime_type", "audio/wav"),
            capture=capture,
            allow_idle=False,
        )

    def submit_transcript(self, transcript: str, source: str = "local-mic") -> dict:
        normalized = " ".join((transcript or "").strip().split())
        session_id = self._create_session(source=source, input_kind="transcript", transcript=normalized)
        if not normalized:
            result = {"ok": False, "error": "empty_transcript"}
            self._complete_session(session_id, "failed", result)
            return {**result, "voice_session_id": session_id}

        result = self.hub_orchestrator_service.handle_voice_wake(normalized)
        self._complete_session(session_id, "completed" if result.get("ok") else "failed", result)
        result["voice_session_id"] = session_id
        return result

    def submit_audio(self, content_base64: str, filename: str, mime_type: str, source: str = "local-mic") -> dict:
        session_id = self._create_session(source=source, input_kind="audio", transcript="")
        try:
            raw_bytes = base64.b64decode((content_base64 or "").encode("utf-8"), validate=True)
        except binascii.Error as exc:
            result = {"ok": False, "error": f"invalid_audio_base64:{exc}"}
            self._complete_session(session_id, "failed", result)
            return {**result, "voice_session_id": session_id}

        suffix = Path(filename or "voice-input.bin").suffix or ".bin"
        temp_path = self.temp_dir / f"{session_id}{suffix}"
        temp_path.write_bytes(raw_bytes)
        return self._transcribe_and_route(
            session_id=session_id,
            audio_path=temp_path,
            mime_type=mime_type,
            capture={"ok": True, "backend": "uploaded-audio", "audio_path": str(temp_path), "filename": temp_path.name, "mime_type": mime_type},
            allow_idle=False,
        )

    def _transcribe_and_route(self, session_id: str, audio_path: Path, mime_type: str, capture: dict, allow_idle: bool) -> dict:
        try:
            asr_result = self.asr_adapter.transcribe_file(audio_path, mime_type)
            transcript = " ".join((asr_result.get("transcript") or "").strip().split()) if asr_result.get("ok") else ""
            self.repository.update_voice_input_session_asr(
                session_id,
                transcript=transcript,
                asr_backend=asr_result.get("backend", "unknown"),
                audio_path=str(audio_path),
            )
            self._export_transcript_file(session_id, transcript)
            if not asr_result.get("ok"):
                result = {"ok": False, "error": asr_result.get("error", "asr_failed"), "capture": capture, "asr": asr_result}
                self._complete_session(session_id, "failed", result)
                return {**result, "voice_session_id": session_id}
            if not transcript and not allow_idle:
                result = {"ok": True, "capture": capture, "transcript": transcript, "asr": asr_result, "wake": {"ok": True, "intent": "voice.noop", "ignored": True}}
                self._complete_session(session_id, "completed", result)
                result["voice_session_id"] = session_id
                return result
            if self._should_ignore_transcript(transcript):
                result = {
                    "ok": True,
                    "capture": capture,
                    "transcript": transcript,
                    "asr": asr_result,
                    "wake": {"ok": True, "intent": "voice.deduped", "ignored": True},
                }
                self._complete_session(session_id, "completed", result)
                result["voice_session_id"] = session_id
                return result

            wake_result = self.hub_orchestrator_service.handle_voice_wake(transcript)
            self._remember_processed_transcript(transcript)
            result = {
                "ok": wake_result.get("ok", False),
                "capture": capture,
                "transcript": transcript,
                "asr": asr_result,
                "wake": wake_result,
            }
            self._complete_session(session_id, "completed" if result.get("ok") else "failed", result)
            result["voice_session_id"] = session_id
            return result
        finally:
            if self.cleanup_after_process:
                self._safe_delete_temp_file(audio_path)
            self._cleanup_temp_files()

    def _listener_loop(self) -> None:
        while not self._listener_stop.is_set():
            if self._is_suppressed():
                self._listener_stop.wait(0.4)
                continue
            session_id = self._create_session(source="continuous-listener", input_kind="microphone", transcript="")
            try:
                capture = self.mic_recorder.capture_until_silence(
                    min_duration_seconds=self.min_duration_seconds,
                    max_duration_seconds=self.max_duration_seconds,
                    silence_seconds=self.silence_seconds,
                    silence_threshold=self.silence_threshold,
                    sample_rate=self.default_sample_rate,
                    channels=self.default_channels,
                    device=self.default_device_index,
                )
                if capture.get("ok"):
                    self._transcribe_and_route(
                        session_id=session_id,
                        audio_path=Path(capture["audio_path"]),
                        mime_type=capture.get("mime_type", "audio/wav"),
                        capture=capture,
                        allow_idle=False,
                    )
                else:
                    self._complete_session(session_id, "failed", capture)
            except Exception as exc:
                self._complete_session(session_id, "failed", {"error": f"listener_exception:{exc}"})
                self.repository.upsert_device_state("voice_listener_state", f"error:{exc}")
            self._listener_stop.wait(self.listener_poll_seconds)
        self.repository.upsert_device_state("voice_listener_state", "passive")

    def _resolve_sample_rate(self, device_index: int | None, fallback: int) -> int:
        for item in self.mic_recorder.list_devices():
            if item.get("index") == device_index:
                sample_rate = int(float(item.get("default_samplerate") or fallback))
                return max(8000, sample_rate)
        return fallback

    def _create_session(self, source: str, input_kind: str, transcript: str) -> str:
        session_id = str(uuid.uuid4())
        self.repository.create_voice_input_session(
            {
                "voice_session_id": session_id,
                "source": source,
                "input_kind": input_kind,
                "transcript": transcript,
                "asr_backend": getattr(self.asr_adapter, "backend_name", "unknown"),
                "status": "processing",
                "audio_path": "",
            }
        )
        self.repository.upsert_device_state("voice_last_source", source)
        return session_id

    def _complete_session(self, session_id: str, status: str, result: dict) -> None:
        self.repository.complete_voice_input_session(
            voice_session_id=session_id,
            status=status,
            result_summary=(
                result.get("message")
                or result.get("error")
                or result.get("intent")
                or result.get("transcript")
                or ""
            )[:200],
            completed_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.repository.prune_voice_input_sessions(
            retain_seconds=self.session_retention_seconds,
            max_records=self.session_max_records,
        )

    def list_sessions(self, limit: int = 20) -> dict:
        return {
            "ok": True,
            "items": self.repository.list_voice_input_sessions(limit),
            "transcript_dir": str(self.transcript_dir),
        }

    def latest_transcript(self) -> dict:
        item = self.repository.get_latest_voice_input_session(require_transcript=True)
        if not item:
            item = self.repository.get_latest_voice_input_session(require_transcript=False)
        if not item:
            return {"ok": False, "error": "no_voice_sessions"}
        return {
            "ok": True,
            "voice_session_id": item["voice_session_id"],
            "transcript": item.get("transcript", ""),
            "transcript_file": str(self.transcript_dir / f"{item['voice_session_id']}.txt"),
            "status": item.get("status", ""),
            "created_at": item.get("created_at", ""),
            "completed_at": item.get("completed_at", ""),
        }

    def _is_suppressed(self) -> bool:
        raw = self.repository.get_device_state("voice_suppress_until", "")
        if not raw:
            return False
        try:
            return datetime.fromisoformat(raw) >= datetime.now()
        except ValueError:
            return False

    def _should_ignore_transcript(self, transcript: str) -> bool:
        normalized = " ".join((transcript or "").strip().lower().split())
        if not normalized:
            return False
        raw_text = self.repository.get_device_state("voice_last_processed_transcript", "")
        raw_time = self.repository.get_device_state("voice_last_processed_at", "")
        if not raw_text or not raw_time:
            return False
        try:
            processed_at = datetime.fromisoformat(raw_time)
        except ValueError:
            return False
        if processed_at < datetime.now() - timedelta(seconds=8):
            return False
        return normalized == " ".join(raw_text.strip().lower().split())

    def _remember_processed_transcript(self, transcript: str) -> None:
        normalized = " ".join((transcript or "").strip().split())
        if not normalized:
            return
        self.repository.upsert_device_state("voice_last_processed_transcript", normalized)
        self.repository.upsert_device_state("voice_last_processed_at", datetime.now().isoformat(timespec="seconds"))

    def _managed_temp_dirs(self) -> list[Path]:
        candidates = [self.temp_dir, self.transcript_dir]
        recorder_temp_dir = getattr(self.mic_recorder, "temp_dir", None)
        if recorder_temp_dir:
            candidates.append(Path(recorder_temp_dir))
        unique: list[Path] = []
        seen: set[str] = set()
        for path in candidates:
            resolved = str(Path(path).resolve())
            if resolved not in seen:
                seen.add(resolved)
                unique.append(Path(path))
        return unique

    def _safe_delete_temp_file(self, audio_path: Path) -> None:
        try:
            target = Path(audio_path).resolve()
        except Exception:
            return
        managed_roots = [root.resolve() for root in self._managed_temp_dirs()]
        if not any(root == target.parent or root in target.parents for root in managed_roots):
            return
        try:
            if target.exists() and target.is_file():
                target.unlink()
        except OSError:
            pass

    def _cleanup_temp_files(self) -> None:
        cutoff = datetime.now() - timedelta(seconds=self.retention_seconds)
        for directory in self._managed_temp_dirs():
            try:
                directory.mkdir(parents=True, exist_ok=True)
                files = [path for path in directory.iterdir() if path.is_file()]
            except OSError:
                continue
            files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
            for index, path in enumerate(files):
                try:
                    modified = datetime.fromtimestamp(path.stat().st_mtime)
                except OSError:
                    continue
                if index >= self.max_temp_files or modified < cutoff:
                    self._safe_delete_temp_file(path)

    def _export_transcript_file(self, session_id: str, transcript: str) -> None:
        try:
            target = self.transcript_dir / f"{session_id}.txt"
            target.write_text(transcript or "", encoding="utf-8")
        except OSError:
            pass
