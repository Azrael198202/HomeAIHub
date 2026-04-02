# Box Deployment Modes

HomeAIHub Box should support two deployment modes using the same `python -m box` runtime.

## Mode 1: Host Install

This mode targets an existing Mac, Windows, or Linux machine.

Behavior:
- The machine boots into its normal desktop or server OS.
- HomeAIHub Box starts automatically on boot.
- The box process keeps running in the background as a local service.
- Local voice and TV/dashboard functions stay available even before pairing.
- Remote app control becomes available only after pairing.

Startup assets in this repo:
- Windows startup task installer: `deploy/box/windows/register-box-startup-task.ps1`
- Linux startup service: `deploy/box/systemd/homeaihub-box.service.template`
- macOS launchd service: `deploy/box/launchd/com.homeaihub.box.plist.template`
- Cross-platform launcher: `scripts/start-box-service.ps1` and `scripts/start-box-service.sh`

Recommended setup:
1. Install Python and project dependencies.
2. Configure `box/env/.env.prod`.
3. Install the platform startup definition.
4. Reboot and confirm the box process starts automatically.

## Mode 2: Appliance / IPC Install

This mode targets an industrial PC, mini host, or dedicated appliance.

Behavior:
- The device is dedicated to HomeAIHub Box.
- On power-on, the OS boots and immediately starts the box runtime.
- The box behaves like a household appliance rather than a desktop app.
- Optional kiosk mode can auto-open the dashboard on the attached display.

Recommended appliance baseline:
- Linux OS with `systemd`
- Auto-start `homeaihub-box.service`
- Optional kiosk service for a local browser display: `deploy/box/systemd/homeaihub-dashboard-kiosk.service.template`
- Optional read-only or hardened OS image later

Boot sequence:
1. Power on IPC.
2. OS starts.
3. `systemd` launches HomeAIHub Box.
4. Box connects outward to Railway.
5. If unpaired, it shows pairing QR and still accepts local voice input.
6. If paired, it continues local automation and remote relay handling.

## Product rule shared by both modes

Before pairing:
- Box is online.
- Box can show dashboard / QR.
- Box can accept local voice wake and local automation.
- Box cannot accept remote app relay tasks.

After pairing:
- App requests target the paired `device_id` through Railway.
- Box polls Railway and executes tasks through the local OpenClaw runtime.

## What stays identical in both modes

- Same `box/` runtime
- Same local OpenClaw execution model
- Same Railway sync flow
- Same pairing logic
- Same local voice and dashboard behavior

The difference is only packaging and boot management.
