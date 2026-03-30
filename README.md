# HomeAIHub

HomeAIHub is structured around the product flow below:

```text
HomeAIHub Box
  -> joins the home network
  -> connects to Gateway / control plane
  -> exposes local execution services

Mobile App
  -> scans the box QR / claim payload
  -> claims the box through Gateway
  -> reads device status and sends commands
```

The current repo is a runnable MVP of that flow:

- `box/` is the local execution layer
- `gateway/` is the control-plane-facing access layer
- `apps/mobile_app_mock/` is a mobile app mock UI
- `box/tv_dashboard/` is the TV-side dashboard and onboarding screen

## Current architecture

```text
apps/
  mobile_app_mock/
    web/

box/
  __main__.py
  server.py
  home_api/
  ocr_service/
  event_parser/
  calendar_engine/
  reminder_engine/
  info_engine/
  tts_service/
  tv_control_service/
  tv_dashboard/
  local_db/

gateway/
  openclaw_gateway/
    server.py
    config/
      openclaw.template.json5
    workspaces/
      family-assistant/
      home-automation-assistant/

scripts/
  install-openclaw.ps1
  install-openclaw-macos.sh
  install-openclaw-ubuntu.sh
  prepare-openclaw-config.ps1
  start-openclaw-gateway.ps1
  start-openclaw-node.ps1
  start-box-service.ps1
```

## Pairing logic implemented in this repo

This MVP already includes the product-style onboarding flow:

1. The box boots and creates a device record.
2. The box exposes a short-lived claim token.
3. The TV dashboard switches to pairing mode when the box is unclaimed.
4. The mobile app mock fetches the claim payload from Gateway.
5. The user claims the box with `device_id + claim_token`.
6. After claim succeeds, the dashboard switches from onboarding to family dashboard mode.
7. A paired device can be unbound and returned to onboarding mode.
8. Mobile commands continue to go through Gateway, not directly to the box.

Current device model:

- one demo device id: `hub-demo-001`
- one demo family id after claim: `family-demo`
- claim token expiry: 30 minutes
- pairing state: `pending_claim` -> `paired` -> `pending_claim`

## Local run order

### Option A: simple local MVP run

Start the box service:

```bash
python -m box
```

Start the gateway service in another terminal:

```bash
python -m home_ai_hub
```

Open:

- Mobile app mock: `http://127.0.0.1:8080/mobile`
- TV dashboard: `http://127.0.0.1:8080/dashboard`

### Option B: Docker Compose

```bash
docker compose up --build
```

This repo has Docker files for the custom MVP services, but Docker was not re-verified in this environment during the latest pairing work.

## What you should see

Before claim:

- `/dashboard` shows pairing mode
- the TV page displays device id, claim token, claim URL, and QR payload JSON
- `/mobile` shows the box as waiting to be claimed

After claim:

- `/dashboard` switches to family dashboard mode
- `/mobile` shows device owner and paired status
- `/mobile` can unbind the device and send it back to pairing mode
- manual intake, screenshot intake, TTS, and TV actions still work through Gateway

## Main pages

- Mobile app mock UI: [index.html](e:/Workspace/HomeAIHub/apps/mobile_app_mock/web/index.html)
- Mobile app mock logic: [app.js](e:/Workspace/HomeAIHub/apps/mobile_app_mock/web/app.js)
- TV dashboard logic: [app.js](e:/Workspace/HomeAIHub/box/tv_dashboard/web/app.js)
- Box API server: [server.py](e:/Workspace/HomeAIHub/box/server.py)
- Gateway server: [server.py](e:/Workspace/HomeAIHub/gateway/openclaw_gateway/server.py)
- Box business service: [service.py](e:/Workspace/HomeAIHub/box/home_api/service.py)
- Local repository: [repository.py](e:/Workspace/HomeAIHub/box/local_db/repository.py)

## Pairing and status endpoints

Box endpoints:

- `GET /api/box/device`
- `GET /api/box/pairing/payload`
- `POST /api/box/device/claim`
- `POST /api/box/device/unbind`
- `POST /api/box/device/reset`
- `GET /api/box/dashboard`
- `GET /api/box/mobile-status`

Gateway endpoints:

- `GET /api/gateway/device/status`
- `GET /api/gateway/device/pairing`
- `POST /api/gateway/device/claim`
- `POST /api/gateway/device/unbind`
- `POST /api/gateway/device/reset`
- `GET /api/gateway/family/status`
- `POST /api/gateway/control-plane/sessions/open`
- `POST /api/gateway/control-plane/dispatch`

## Quick verification flow

1. Open `/dashboard` and confirm the page is in pairing mode.
2. Open `/mobile` and confirm the claim token is visible in the Claim Payload section.
3. Use the Claim Box form with a name and family name.
4. Refresh `/dashboard` and confirm it switches to dashboard mode.
5. Use `Unbind Device` in `/mobile` and confirm `/dashboard` returns to pairing mode.
6. Claim again if needed, then open a session in `/mobile`.
7. Send a manual item like `today 3pm mom dentist`.
8. Trigger `Play TTS` or `Wake TV`.

## Real OpenClaw integration

The repo also includes scaffolding for replacing the transitional Python gateway with real OpenClaw as the control plane.

Recommended production deployment:

- Railway hosts the real OpenClaw Gateway
- the home box runs `python -m box` locally
- the home box joins the Railway Gateway as an OpenClaw node

See the full Railway guide here:

- [railway-openclaw.md](e:/Workspace/HomeAIHub/docs/railway-openclaw.md)
- [openclaw-node-actions.md](e:/Workspace/HomeAIHub/docs/openclaw-node-actions.md)
- [Dockerfile.openclaw](e:/Workspace/HomeAIHub/Dockerfile.openclaw)
- [start-openclaw-railway.sh](e:/Workspace/HomeAIHub/scripts/start-openclaw-railway.sh)

### Official OpenClaw install commands

Verified against current official docs:

- Windows PowerShell:

```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

- macOS / Linux / WSL2:

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

Sources:

- https://docs.openclaw.ai/install/index
- https://docs.openclaw.ai/install/installer
- https://docs.openclaw.ai/start/getting-started
- https://docs.openclaw.ai/platforms/windows

Current docs also indicate:

- Node 24 is recommended
- Node 22 LTS is still supported for compatibility
- On Windows, WSL2 is still the recommended path

### Platform choice

Pick exactly one:

- [ ] Windows PowerShell
- [ ] macOS
- [ ] Ubuntu

### Ordered setup steps for real OpenClaw

#### 1. Install OpenClaw

Choose one:

- [ ] Windows PowerShell

```powershell
./scripts/install-openclaw.ps1
```

- [ ] macOS

```bash
bash ./scripts/install-openclaw-macos.sh
```

- [ ] Ubuntu

```bash
bash ./scripts/install-openclaw-ubuntu.sh
```

#### 2. Start the HomeAIHub local box service

Windows PowerShell:

```powershell
./scripts/start-box-service.ps1
```

macOS / Ubuntu:

```bash
python -m box
```

#### 3. Generate the repo-local OpenClaw config

Windows PowerShell:

```powershell
./scripts/prepare-openclaw-config.ps1
```

If you are on macOS or Ubuntu, use [openclaw.template.json5](e:/Workspace/HomeAIHub/gateway/openclaw_gateway/config/openclaw.template.json5), replace `__PROJECT_ROOT__`, and save it as:

```text
gateway/openclaw_gateway/config/openclaw.local.json5
```

#### 4. Start the real OpenClaw Gateway

Windows PowerShell:

```powershell
./scripts/start-openclaw-gateway.ps1
```

macOS / Ubuntu:

```bash
OPENCLAW_CONFIG="$PWD/gateway/openclaw_gateway/config/openclaw.local.json5" openclaw gateway
```

#### 5. Start this machine as an OpenClaw node

Windows PowerShell:

```powershell
./scripts/start-openclaw-node.ps1
```

macOS / Ubuntu:

```bash
openclaw node run --host 127.0.0.1 --port 18789 --display-name "HomeAIHub Mini Host"
```

#### 6. Approve the node pairing

Use the normal OpenClaw approval flow from the Gateway side.

## Current limitation in this environment

This environment does not currently have:

- `openclaw` CLI
- `node`

So the real OpenClaw Gateway and real node pairing were not executed here. What was verified locally is the runnable Python MVP path:

- box service
- gateway service
- device claim flow
- dashboard pairing mode
- post-claim command flow

## Notes

- The current Python gateway should be treated as transitional scaffolding until real OpenClaw takes over the control plane.
- There are generated test databases under [data](e:/Workspace/HomeAIHub/data) from local validation runs.
