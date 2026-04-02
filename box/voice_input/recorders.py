from __future__ import annotations

import tempfile
import uuid
import wave
from pathlib import Path


class BaseMicRecorder:
    backend_name = "base"

    def list_devices(self) -> list[dict]:
        return []

    def choose_default_device(self) -> int | None:
        devices = self.list_devices()
        return devices[0]["index"] if devices else None

    def capture(self, duration_seconds: int, sample_rate: int, channels: int, device: int | None = None) -> dict:
        raise NotImplementedError

    def capture_until_silence(
        self,
        min_duration_seconds: float,
        max_duration_seconds: float,
        silence_seconds: float,
        silence_threshold: int,
        sample_rate: int,
        channels: int,
        device: int | None = None,
    ) -> dict:
        return self.capture(int(max_duration_seconds), sample_rate, channels, device=device)


class NullMicRecorder(BaseMicRecorder):
    backend_name = "none"

    def capture(self, duration_seconds: int, sample_rate: int, channels: int, device: int | None = None) -> dict:
        return {"ok": False, "error": "microphone_backend_unavailable", "backend": self.backend_name}


class SoundDeviceMicRecorder(BaseMicRecorder):
    backend_name = "sounddevice"

    def __init__(self) -> None:
        import sounddevice as sd

        self.sd = sd
        self.temp_dir = Path(tempfile.gettempdir()) / "homeaihub-voice-capture"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def list_devices(self) -> list[dict]:
        items = []
        for device in self.sd.query_devices():
            if int(device.get("max_input_channels", 0)) > 0:
                name = str(device.get("name", ""))
                items.append(
                    {
                        "index": int(device.get("index", -1)),
                        "name": name,
                        "max_input_channels": int(device.get("max_input_channels", 0)),
                        "default_samplerate": float(device.get("default_samplerate", 0.0)),
                        "score": self._score_device(name, int(device.get("max_input_channels", 0))),
                    }
                )
        return sorted(items, key=lambda item: (-item["score"], item["index"]))

    def choose_default_device(self) -> int | None:
        devices = self.list_devices()
        return devices[0]["index"] if devices else None

    def capture(self, duration_seconds: int, sample_rate: int, channels: int, device: int | None = None) -> dict:
        duration = max(1, int(duration_seconds))
        target_device = device if device is not None else self.choose_default_device()
        frames = int(duration * sample_rate)
        recording = self.sd.rec(
            frames,
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            device=target_device,
        )
        self.sd.wait()
        output_path = self.temp_dir / f"{uuid.uuid4()}.wav"
        with wave.open(str(output_path), "wb") as handle:
            handle.setnchannels(channels)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(recording.tobytes())
        return {
            "ok": True,
            "backend": self.backend_name,
            "audio_path": str(output_path),
            "filename": output_path.name,
            "mime_type": "audio/wav",
            "byte_size": output_path.stat().st_size,
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "channels": channels,
            "device": target_device,
        }

    def capture_until_silence(
        self,
        min_duration_seconds: float,
        max_duration_seconds: float,
        silence_seconds: float,
        silence_threshold: int,
        sample_rate: int,
        channels: int,
        device: int | None = None,
    ) -> dict:
        import numpy as np

        target_device = device if device is not None else self.choose_default_device()
        min_duration = max(0.5, float(min_duration_seconds))
        max_duration = max(min_duration, float(max_duration_seconds))
        quiet_window = max(0.3, float(silence_seconds))
        threshold = max(1, int(silence_threshold))
        block_duration = 0.2
        block_frames = max(1, int(sample_rate * block_duration))
        captured_blocks = []
        elapsed_seconds = 0.0
        quiet_seconds = 0.0

        with self.sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            blocksize=block_frames,
            device=target_device,
        ) as stream:
            while elapsed_seconds < max_duration:
                data, overflowed = stream.read(block_frames)
                if overflowed:
                    pass
                captured_blocks.append(np.array(data, copy=True))
                elapsed_seconds += len(data) / float(sample_rate)
                level = float(np.abs(data).mean()) if len(data) else 0.0
                if elapsed_seconds >= min_duration:
                    if level <= threshold:
                        quiet_seconds += len(data) / float(sample_rate)
                    else:
                        quiet_seconds = 0.0
                    if quiet_seconds >= quiet_window:
                        break

        recording = np.concatenate(captured_blocks, axis=0) if captured_blocks else np.zeros((0, channels), dtype="int16")
        actual_duration = len(recording) / float(sample_rate) if len(recording) else 0.0
        output_path = self.temp_dir / f"{uuid.uuid4()}.wav"
        with wave.open(str(output_path), "wb") as handle:
            handle.setnchannels(channels)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(recording.tobytes())
        return {
            "ok": True,
            "backend": self.backend_name,
            "audio_path": str(output_path),
            "filename": output_path.name,
            "mime_type": "audio/wav",
            "byte_size": output_path.stat().st_size,
            "duration_seconds": round(actual_duration, 2),
            "sample_rate": sample_rate,
            "channels": channels,
            "device": target_device,
            "capture_mode": "silence_stop",
            "silence_threshold": threshold,
            "silence_seconds": quiet_window,
        }

    def _score_device(self, name: str, channels: int) -> int:
        lower = name.lower()
        score = channels * 10
        if "usb" in lower:
            score += 40
        if "microphone" in lower or "mic" in lower:
            score += 25
        if "realtek" in lower:
            score += 15
        if "stereo mix" in lower:
            score -= 60
        if "mapper" in lower or "driver" in lower:
            score -= 20
        if "headset" in lower and "hands-free" in lower:
            score -= 10
        return score


def build_mic_recorder(backend: str) -> BaseMicRecorder:
    normalized = (backend or "auto").strip().lower()
    if normalized in {"none", "disabled"}:
        return NullMicRecorder()
    if normalized in {"auto", "sounddevice"}:
        try:
            return SoundDeviceMicRecorder()
        except Exception:
            return NullMicRecorder()
    return NullMicRecorder()
