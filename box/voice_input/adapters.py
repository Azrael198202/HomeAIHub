from __future__ import annotations

import base64
import json
import re
import subprocess
import wave
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class BaseASRAdapter:
    backend_name = "base"

    def transcribe_file(self, audio_path: Path, mime_type: str = "") -> dict:
        raise NotImplementedError


class MockTextASRAdapter(BaseASRAdapter):
    backend_name = "mock_text"

    def transcribe_file(self, audio_path: Path, mime_type: str = "") -> dict:
        try:
            transcript = audio_path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError:
            transcript = f"audio received from {audio_path.name}"
        return {
            "ok": True,
            "backend": self.backend_name,
            "transcript": transcript or f"audio received from {audio_path.name}",
            "confidence": 0.25,
        }


class WhisperCLIAdapter(BaseASRAdapter):
    backend_name = "whisper_cli"

    def __init__(self, command: str) -> None:
        self.command = command.strip()

    def transcribe_file(self, audio_path: Path, mime_type: str = "") -> dict:
        if not self.command:
            return {"ok": False, "error": "missing_whisper_command"}
        completed = subprocess.run(
            [self.command, str(audio_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        transcript = completed.stdout.strip()
        if completed.returncode != 0:
            return {
                "ok": False,
                "error": "whisper_cli_failed",
                "stderr": completed.stderr.strip(),
                "backend": self.backend_name,
            }
        return {
            "ok": True,
            "backend": self.backend_name,
            "transcript": transcript,
            "confidence": 0.8 if transcript else 0.0,
        }


class WhisperLocalAdapter(BaseASRAdapter):
    backend_name = "whisper_local"

    def __init__(self, model_name: str = "base", language: str = "", cache_dir: str = "") -> None:
        import whisper

        self.whisper = whisper
        self.model_name = model_name or "base"
        self.language = language.strip()
        self.cache_dir = cache_dir.strip()
        self._model = None

    def _load_model(self):
        if self._model is None:
            kwargs = {}
            if self.cache_dir:
                Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
                kwargs["download_root"] = self.cache_dir
            self._model = self.whisper.load_model(self.model_name, **kwargs)
        return self._model

    def _prompt_text(self) -> str:
        return "hey lumi"

    def _base_options(self) -> dict:
        return {
            "fp16": False,
            "condition_on_previous_text": False,
            "temperature": 0.0,
            "beam_size": 5,
            "best_of": 5,
            "no_speech_threshold": 0.45,
            "logprob_threshold": -1.0,
            "initial_prompt": self._prompt_text(),
        }

    def _candidate_languages(self) -> list[str | None]:
        normalized = self.language.lower() if self.language else ""
        if normalized in {"", "auto", "mixed", "multilingual"}:
            return ["en", None]
        return [self.language]

    def _score_result(self, result: dict) -> tuple[int, int]:
        transcript = (result.get("text") or "").strip()
        segments = len(result.get("segments") or [])
        return (len(transcript), segments)

    def _collapse_repetition(self, transcript: str) -> str:
        normalized = " ".join((transcript or "").strip().split())
        if not normalized:
            return ""

        lowered = normalized.lower().strip(" ,.;!?")
        parts = [part.strip(" ,.;!?") for part in re.split(r"[,.!?]+", normalized) if part.strip()]
        if len(parts) >= 3 and len(set(part.lower() for part in parts)) == 1:
            return parts[0]

        tokens = lowered.split()
        if len(tokens) >= 6 and len(tokens) % 2 == 0:
            half = len(tokens) // 2
            if tokens[:half] == tokens[half:]:
                return " ".join(tokens[:half])

        for size in range(3, min(12, len(tokens) // 2 + 1)):
            phrase = tokens[:size]
            repeats = 1
            index = size
            while index + size <= len(tokens) and tokens[index:index + size] == phrase:
                repeats += 1
                index += size
            if repeats >= 3 and index >= len(tokens) - 1:
                return " ".join(phrase)
        return normalized

    def _segment_metrics(self, result: dict) -> tuple[float, float]:
        segments = result.get("segments") or []
        if not segments:
            return (0.0, 0.0)
        no_speech_values = [float(segment.get("no_speech_prob", 0.0) or 0.0) for segment in segments]
        avg_logprob_values = [float(segment.get("avg_logprob", 0.0) or 0.0) for segment in segments]
        avg_no_speech = sum(no_speech_values) / len(no_speech_values)
        avg_logprob = sum(avg_logprob_values) / len(avg_logprob_values)
        return (avg_no_speech, avg_logprob)

    def _repeated_prefix_count(self, transcript: str) -> int:
        lowered = " ".join((transcript or "").lower().strip().split())
        tokens = lowered.split()
        if len(tokens) < 6:
            return 1
        best = 1
        for size in range(2, min(8, len(tokens) // 2 + 1)):
            phrase = tokens[:size]
            repeats = 1
            index = size
            while index + size <= len(tokens) and tokens[index:index + size] == phrase:
                repeats += 1
                index += size
            best = max(best, repeats)
        return best

    def _looks_like_noise(self, transcript: str, result: dict) -> bool:
        normalized = " ".join((transcript or "").strip().split())
        if not normalized:
            return False
        lowered = normalized.lower()
        tokens = lowered.split()
        unique_ratio = (len(set(tokens)) / len(tokens)) if tokens else 1.0
        avg_no_speech, avg_logprob = self._segment_metrics(result)
        repeated_prefix = self._repeated_prefix_count(normalized)
        obvious_command_markers = (
            "hey lumi",
            "hei lumi",
            "hi lumi",
            "wake tv",
            "refresh dashboard",
            "remind me",
            "remember to",
            "call ",
            "buy ",
            "book ",
            "schedule ",
        )
        looks_actionable = any(marker in lowered for marker in obvious_command_markers)
        if repeated_prefix >= 4:
            return True
        if len(tokens) >= 10 and unique_ratio <= 0.45:
            return True
        if not looks_actionable and avg_no_speech >= 0.55 and avg_logprob <= -0.4:
            return True
        return False

    def transcribe_file(self, audio_path: Path, mime_type: str = "") -> dict:
        try:
            model = self._load_model()
            best_result = None
            best_language = ""
            for candidate_language in self._candidate_languages():
                options = self._base_options()
                if candidate_language:
                    options["language"] = candidate_language
                result = model.transcribe(str(audio_path), **options)
                if best_result is None or self._score_result(result) > self._score_result(best_result):
                    best_result = result
                    best_language = candidate_language or result.get("language", "")
                if (result.get("text") or "").strip():
                    break
            result = best_result or {}
            transcript = self._collapse_repetition((result.get("text") or "").strip())
            if self._looks_like_noise(transcript, result):
                transcript = ""
                confidence = 0.0
            else:
                confidence = 0.8 if transcript else 0.0
            return {
                "ok": True,
                "backend": self.backend_name,
                "model": self.model_name,
                "language": result.get("language", best_language or self.language or ""),
                "transcript": transcript,
                "segments": len(result.get("segments") or []),
                "confidence": confidence,
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": f"whisper_local_failed:{exc}",
                "backend": self.backend_name,
                "model": self.model_name,
            }


class GoogleCloudSTTAdapter(BaseASRAdapter):
    backend_name = "google_stt"

    def __init__(
        self,
        api_key: str,
        language_code: str = "en-US",
        alternative_language_codes: list[str] | None = None,
        model: str = "latest_long",
        enable_automatic_punctuation: bool = True,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.language_code = (language_code or "en-US").strip()
        self.alternative_language_codes = [item.strip() for item in (alternative_language_codes or []) if item.strip()]
        self.model = (model or "latest_long").strip()
        self.enable_automatic_punctuation = bool(enable_automatic_punctuation)

    def is_available(self) -> bool:
        return bool(self.api_key)

    def transcribe_file(self, audio_path: Path, mime_type: str = "") -> dict:
        if not self.is_available():
            return {"ok": False, "backend": self.backend_name, "error": "missing_google_stt_api_key"}
        try:
            sample_rate_hertz = self._sample_rate_for(audio_path)
            audio_content = base64.b64encode(audio_path.read_bytes()).decode("utf-8")
            config = {
                "encoding": "LINEAR16",
                "sampleRateHertz": sample_rate_hertz,
                "languageCode": self.language_code,
                "model": self.model,
                "enableAutomaticPunctuation": self.enable_automatic_punctuation,
            }
            if self.alternative_language_codes:
                config["alternativeLanguageCodes"] = self.alternative_language_codes
            body = {
                "config": config,
                "audio": {"content": audio_content},
            }
            request = Request(
                f"https://speech.googleapis.com/v1/speech:recognize?key={self.api_key}",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            results = payload.get("results") or []
            transcript_parts: list[str] = []
            confidence = 0.0
            for result in results:
                alternatives = result.get("alternatives") or []
                if not alternatives:
                    continue
                best = alternatives[0]
                transcript_parts.append((best.get("transcript") or "").strip())
                confidence = max(confidence, float(best.get("confidence", 0.0) or 0.0))
            transcript = " ".join(part for part in transcript_parts if part).strip()
            return {
                "ok": True,
                "backend": self.backend_name,
                "language": self.language_code,
                "transcript": transcript,
                "segments": len(results),
                "confidence": confidence if transcript else 0.0,
            }
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return {"ok": False, "backend": self.backend_name, "error": f"google_stt_http_error:{exc.code}:{detail}"}
        except URLError as exc:
            return {"ok": False, "backend": self.backend_name, "error": f"google_stt_network_error:{exc.reason}"}
        except Exception as exc:
            return {"ok": False, "backend": self.backend_name, "error": f"google_stt_failed:{exc}"}

    def _sample_rate_for(self, audio_path: Path) -> int:
        with wave.open(str(audio_path), "rb") as handle:
            return int(handle.getframerate())


class FallbackASRAdapter(BaseASRAdapter):
    backend_name = "auto"

    def __init__(self, primary: BaseASRAdapter, fallback: BaseASRAdapter) -> None:
        self.primary = primary
        self.fallback = fallback

    def transcribe_file(self, audio_path: Path, mime_type: str = "") -> dict:
        primary_result = self.primary.transcribe_file(audio_path, mime_type)
        if primary_result.get("ok") and (primary_result.get("transcript") or "").strip():
            return primary_result
        fallback_result = self.fallback.transcribe_file(audio_path, mime_type)
        if fallback_result.get("ok"):
            fallback_result.setdefault("fallback_from", getattr(self.primary, "backend_name", "unknown"))
        return fallback_result if fallback_result.get("ok") or not primary_result.get("ok") else primary_result


def build_asr_adapter(
    backend: str,
    whisper_command: str = "",
    whisper_model: str = "base",
    whisper_language: str = "",
    whisper_cache_dir: str = "",
    google_api_key: str = "",
    google_language_code: str = "en-US",
    google_alternative_language_codes: list[str] | None = None,
    google_model: str = "latest_long",
    google_enable_automatic_punctuation: bool = True,
) -> BaseASRAdapter:
    normalized = (backend or "auto").strip().lower()
    google_adapter = GoogleCloudSTTAdapter(
        api_key=google_api_key,
        language_code=google_language_code,
        alternative_language_codes=google_alternative_language_codes or [],
        model=google_model,
        enable_automatic_punctuation=google_enable_automatic_punctuation,
    )
    whisper_local_adapter = None
    try:
        whisper_local_adapter = WhisperLocalAdapter(whisper_model, whisper_language, whisper_cache_dir)
    except Exception:
        whisper_local_adapter = None
    if normalized == "whisper_cli":
        return WhisperCLIAdapter(whisper_command)
    if normalized == "google_stt":
        if google_adapter.is_available():
            return google_adapter
        if whisper_local_adapter is not None:
            return whisper_local_adapter
        return MockTextASRAdapter()
    if normalized == "whisper_local":
        if whisper_local_adapter is not None:
            return whisper_local_adapter
        return MockTextASRAdapter()
    if normalized in {"auto", "whisper_local"}:
        if google_adapter.is_available() and whisper_local_adapter is not None:
            return FallbackASRAdapter(google_adapter, whisper_local_adapter)
        if google_adapter.is_available():
            return google_adapter
        if whisper_local_adapter is not None:
            return whisper_local_adapter
    return MockTextASRAdapter()
