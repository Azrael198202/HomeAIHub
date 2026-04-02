from __future__ import annotations

import secrets
from datetime import datetime, timedelta


class HomeDeviceService:
    def __init__(
        self,
        repository,
        gateway_base_url: str,
        default_device_id: str,
        default_device_name: str,
        default_family_id: str,
    ) -> None:
        self.repository = repository
        self.gateway_base_url = gateway_base_url
        self.default_device_id = default_device_id
        self.default_device_name = default_device_name
        self.default_family_id = default_family_id

    def ensure_device_record(self) -> None:
        existing = self.repository.get_device(self.default_device_id)
        if existing:
            self.repository.update_device_last_seen(self.default_device_id)
            return
        claim_token, expires_at = self.new_claim()
        self.repository.create_or_update_device(
            {
                "device_id": self.default_device_id,
                "device_name": self.default_device_name,
                "device_secret": secrets.token_hex(16),
                "claim_token": claim_token,
                "claim_expires_at": expires_at,
                "status": "pending_claim",
            }
        )

    def new_claim(self) -> tuple[str, str]:
        token = secrets.token_urlsafe(10)
        expires_at = (datetime.now() + timedelta(minutes=30)).isoformat(timespec="seconds")
        return token, expires_at

    def get_device(self) -> dict:
        self.repository.update_device_last_seen(self.default_device_id)
        device = self.repository.get_device(self.default_device_id) or {}
        return {
            "device": device,
            "pairing": self.get_pairing_payload(),
            "online": True,
            "box_service_healthy": True,
        }

    def external_box_status(self) -> dict:
        device = self.repository.get_device(self.default_device_id) or {}
        paired = device.get("status") == "paired"
        return {
            "device_id": self.default_device_id,
            "device_name": device.get("device_name", self.default_device_name),
            "paired": paired,
            "status": device.get("status", "pending_claim"),
            "family_id": device.get("family_id", ""),
            "owner_name": device.get("owner_name", ""),
            "last_seen_at": device.get("last_seen_at", ""),
            "box_service_healthy": True,
            "dashboard_path": "/dashboard",
            "local_voice_enabled": True,
            "local_automation_enabled": True,
            "remote_control_enabled": paired,
        }

    def get_pairing_payload(self) -> dict:
        device = self.repository.get_device(self.default_device_id) or {}
        claim_url = (
            f"{self.gateway_base_url}/mobile"
            f"?device_id={self.default_device_id}&claim_token={device.get('claim_token', '')}"
        )
        return {
            "device_id": self.default_device_id,
            "device_name": device.get("device_name", self.default_device_name),
            "claim_token": device.get("claim_token", ""),
            "claim_expires_at": device.get("claim_expires_at", ""),
            "claim_url": claim_url,
            "qr_payload": {
                "type": "homeaihub-claim",
                "device_id": self.default_device_id,
                "claim_token": device.get("claim_token", ""),
                "gateway": self.gateway_base_url,
                "claim_endpoint": f"{self.gateway_base_url}/api/gateway/device/claim",
            },
            "paired": device.get("status") == "paired",
            "pairing_scope": "gateway_only",
            "transport": "mobile -> gateway -> home box",
        }

    def claim_device(self, actor_user_id: str, actor_name: str, family_name: str, claim_token: str) -> dict:
        device = self.repository.get_device(self.default_device_id)
        if not device:
            return {"ok": False, "error": "device_not_found"}
        if device["status"] == "paired":
            self.repository.log_device_claim(self.default_device_id, claim_token, actor_user_id, actor_name, "already_paired")
            return {"ok": False, "error": "device_already_paired"}
        if claim_token != device["claim_token"]:
            self.repository.log_device_claim(self.default_device_id, claim_token, actor_user_id, actor_name, "invalid_token")
            return {"ok": False, "error": "invalid_claim_token"}
        if datetime.fromisoformat(device["claim_expires_at"]) < datetime.now():
            self.repository.log_device_claim(self.default_device_id, claim_token, actor_user_id, actor_name, "expired")
            return {"ok": False, "error": "claim_token_expired"}

        family_id = self.default_family_id
        paired_at = datetime.now().isoformat(timespec="seconds")
        self.repository.bind_device(
            device_id=self.default_device_id,
            family_id=family_id,
            owner_user_id=actor_user_id,
            owner_name=actor_name,
            status="paired",
            paired_at=paired_at,
        )
        self.repository.log_device_claim(self.default_device_id, claim_token, actor_user_id, actor_name, "claimed")
        self.repository.create_notification(
            {
                "kind": "device_claimed",
                "title": "Device Claimed",
                "person": actor_name,
                "location": family_name,
                "message": f"{actor_name} paired {self.default_device_name}",
                "event_id": None,
            }
        )
        return {
            "ok": True,
            "device_id": self.default_device_id,
            "family_id": family_id,
            "family_name": family_name,
            "owner_user_id": actor_user_id,
            "owner_name": actor_name,
            "paired_at": paired_at,
        }

    def unbind_device(self, actor_user_id: str, actor_name: str) -> dict:
        device = self.repository.get_device(self.default_device_id)
        if not device:
            return {"ok": False, "error": "device_not_found"}
        if device["status"] != "paired":
            return {"ok": False, "error": "device_not_paired"}

        claim_token, expires_at = self.new_claim()
        self.repository.create_or_update_device(
            {
                "device_id": self.default_device_id,
                "device_name": device["device_name"],
                "device_secret": device["device_secret"],
                "claim_token": claim_token,
                "claim_expires_at": expires_at,
                "status": "pending_claim",
                "family_id": "",
                "owner_user_id": "",
                "owner_name": "",
                "paired_at": "",
            }
        )
        self.repository.log_device_claim(self.default_device_id, claim_token, actor_user_id, actor_name, "unbound")
        self.repository.create_notification(
            {
                "kind": "device_unbound",
                "title": "Device Unbound",
                "person": actor_name,
                "location": "",
                "message": f"{actor_name} removed the device binding",
                "event_id": None,
            }
        )
        return {
            "ok": True,
            "device_id": self.default_device_id,
            "status": "pending_claim",
            "pairing": self.get_pairing_payload(),
        }

    def reset_pairing(self) -> dict:
        device = self.repository.get_device(self.default_device_id)
        if not device:
            return {"ok": False, "error": "device_not_found"}
        claim_token, expires_at = self.new_claim()
        self.repository.create_or_update_device(
            {
                "device_id": self.default_device_id,
                "device_name": device["device_name"],
                "device_secret": device["device_secret"],
                "claim_token": claim_token,
                "claim_expires_at": expires_at,
                "status": "pending_claim",
                "family_id": "",
                "owner_user_id": "",
                "owner_name": "",
                "paired_at": "",
            }
        )
        return {"ok": True, "pairing": self.get_pairing_payload()}
