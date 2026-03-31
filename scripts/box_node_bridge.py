from __future__ import annotations

import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BOX_URL = os.getenv("HOMEAIHUB_LOCAL_BOX_URL", "http://127.0.0.1:8090")


class BoxBridgeError(RuntimeError):
    pass


def request_json(method: str, path: str, payload: dict | None = None) -> dict:
    base = DEFAULT_BOX_URL.rstrip("/")
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise BoxBridgeError(f"http_error:{exc.code}:{detail}") from exc
    except URLError as exc:
        raise BoxBridgeError(f"connection_error:{exc.reason}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge local HomeAIHub box APIs for OpenClaw node exec.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")
    sub.add_parser("device-status")
    sub.add_parser("pairing-payload")
    sub.add_parser("dashboard")
    sub.add_parser("hub-overview")
    sub.add_parser("voice-status")
    sub.add_parser("mobile-status")
    sub.add_parser("refresh-dashboard")
    sub.add_parser("wake-tv")

    manual = sub.add_parser("manual-intake")
    manual.add_argument("text")

    screenshot = sub.add_parser("screenshot-intake")
    screenshot.add_argument("text")

    photo = sub.add_parser("photo-intake")
    photo.add_argument("text")

    voice = sub.add_parser("voice-intake")
    voice.add_argument("text")

    tts = sub.add_parser("tts")
    tts.add_argument("message")

    announce = sub.add_parser("announce")
    announce.add_argument("message")
    announce.add_argument("--priority", default="normal")

    wake = sub.add_parser("voice-wake")
    wake.add_argument("transcript")

    claim = sub.add_parser("claim-device")
    claim.add_argument("--actor-user-id", default="user-demo")
    claim.add_argument("--actor-name", default="Owner")
    claim.add_argument("--family-name", default="My Family")
    claim.add_argument("--claim-token", required=True)

    unbind = sub.add_parser("unbind-device")
    unbind.add_argument("--actor-user-id", default="user-demo")
    unbind.add_argument("--actor-name", default="Owner")

    reset = sub.add_parser("reset-pairing")

    ack = sub.add_parser("ack-notification")
    ack.add_argument("notification_id", type=int)

    return parser


def dispatch(args: argparse.Namespace) -> dict:
    if args.command == "health":
        return request_json("GET", "/health")
    if args.command == "device-status":
        return request_json("GET", "/api/box/device")
    if args.command == "pairing-payload":
        return request_json("GET", "/api/box/pairing/payload")
    if args.command == "dashboard":
        return request_json("GET", "/api/box/dashboard")
    if args.command == "hub-overview":
        return request_json("GET", "/api/box/hub/overview")
    if args.command == "voice-status":
        return request_json("GET", "/api/box/voice/status")
    if args.command == "mobile-status":
        return request_json("GET", "/api/box/mobile-status")
    if args.command == "refresh-dashboard":
        return request_json("POST", "/api/box/automation/refresh-dashboard", {})
    if args.command == "wake-tv":
        return request_json("POST", "/api/box/automation/tv/wake", {})
    if args.command == "manual-intake":
        return request_json("POST", "/api/box/intake/manual", {"text": args.text})
    if args.command == "screenshot-intake":
        return request_json("POST", "/api/box/intake/screenshot", {"text": args.text})
    if args.command == "photo-intake":
        return request_json("POST", "/api/box/intake/photo", {"text": args.text})
    if args.command == "voice-intake":
        return request_json("POST", "/api/box/intake/voice", {"text": args.text})
    if args.command == "tts":
        return request_json("POST", "/api/box/automation/play-tts", {"message": args.message})
    if args.command == "announce":
        return request_json(
            "POST",
            "/api/box/automation/announce",
            {"message": args.message, "priority": args.priority},
        )
    if args.command == "voice-wake":
        return request_json("POST", "/api/box/voice/wake", {"transcript": args.transcript})
    if args.command == "claim-device":
        return request_json(
            "POST",
            "/api/box/device/claim",
            {
                "actor_user_id": args.actor_user_id,
                "actor_name": args.actor_name,
                "family_name": args.family_name,
                "claim_token": args.claim_token,
            },
        )
    if args.command == "unbind-device":
        return request_json(
            "POST",
            "/api/box/device/unbind",
            {
                "actor_user_id": args.actor_user_id,
                "actor_name": args.actor_name,
            },
        )
    if args.command == "reset-pairing":
        return request_json("POST", "/api/box/device/reset", {})
    if args.command == "ack-notification":
        return request_json("POST", "/api/box/notifications/ack", {"id": args.notification_id})
    raise BoxBridgeError(f"unsupported_command:{args.command}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = dispatch(args)
    except BoxBridgeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
