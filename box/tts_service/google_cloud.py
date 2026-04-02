from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GoogleCloudTTSBackend:
    def __init__(
        self,
        api_key: str,
        voice_name: str = "en-US-Neural2-F",
        language_code: str = "en-US",
        gender: str = "FEMALE",
        speaking_rate: float = 1.0,
        cache_dir: str = "",
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.voice_name = (voice_name or "en-US-Neural2-F").strip()
        self.language_code = (language_code or "en-US").strip()
        self.gender = (gender or "FEMALE").strip().upper()
        self.speaking_rate = float(speaking_rate or 1.0)
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else Path(tempfile.gettempdir()) / "homeaihub-google-tts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def is_available(self) -> bool:
        return bool(self.api_key)

    def synthesize_and_play(self, text: str) -> dict:
        if not self.is_available():
            return {"ok": False, "engine": "google_cloud_tts", "error": "missing_google_tts_api_key"}
        audio_path = self._get_or_create_audio(text)
        return self._play_audio(audio_path, text)

    def _get_or_create_audio(self, text: str) -> Path:
        signature = self._request_signature(text)
        audio_path = self.cache_dir / f"{signature}.wav"
        if audio_path.exists() and audio_path.stat().st_size > 0:
            return audio_path
        payload = self._synthesize_request(text)
        audio_content = payload.get("audioContent", "")
        if not audio_content:
            raise RuntimeError("google_tts_returned_no_audio")
        audio_path.write_bytes(base64.b64decode(audio_content))
        return audio_path

    def _request_signature(self, text: str) -> str:
        raw = f"{self.voice_name}|{self.language_code}|{self.gender}|{self.speaking_rate}|{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _synthesize_request(self, text: str) -> dict:
        body = {
            "input": {"text": text},
            "voice": {
                "languageCode": self.language_code,
                "name": self.voice_name,
                "ssmlGender": self.gender,
            },
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "speakingRate": self.speaking_rate,
            },
        }
        request = Request(
            f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"google_tts_http_error:{exc.code}:{detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"google_tts_network_error:{exc.reason}") from exc

    def _play_audio(self, audio_path: Path, text: str) -> dict:
        if os.name == "nt":
            return self._play_windows(audio_path, text)
        if shutil.which("afplay"):
            return self._play_command(["afplay", str(audio_path)], text)
        if shutil.which("aplay"):
            return self._play_command(["aplay", str(audio_path)], text)
        return {"ok": False, "engine": "google_cloud_tts", "error": "no_audio_player_available", "audio_path": str(audio_path)}

    def _play_windows(self, audio_path: Path, text: str) -> dict:
        try:
            import winsound

            winsound.PlaySound(str(audio_path), winsound.SND_FILENAME)
            return {"ok": True, "engine": "google_cloud_tts", "spoken": text, "audio_path": str(audio_path)}
        except Exception as exc:
            return {"ok": False, "engine": "google_cloud_tts", "error": f"windows_audio_play_failed:{exc}", "audio_path": str(audio_path)}

    def _play_command(self, command: list[str], text: str) -> dict:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            return {
                "ok": False,
                "engine": "google_cloud_tts",
                "error": (completed.stderr or completed.stdout or "audio_playback_failed").strip(),
            }
        return {"ok": True, "engine": "google_cloud_tts", "spoken": text}
