# HomeAIHub

HomeAIHub is structured around the product flow below:

```text
Mobile App
  -> talks only to Gateway
  -> finds pairable home boxes
  -> claims a box through Gateway
  -> uploads text / photo / voice data through Gateway

HomeAIHub Box
  -> stays inside the home network
  -> connects outward to Gateway / control plane
  -> receives relayed data from Gateway
  -> runs OCR / parsing / reminders / TV dashboard / TTS locally
```

The current repo is a runnable MVP of that split:

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
      family-intake-agent/
      household-dashboard-agent/
      voice-automation-agent/
      home-orchestrator-agent/

scripts/
  install-openclaw.ps1
  install-openclaw-macos.sh
  install-openclaw-ubuntu.sh
  prepare-openclaw-config.ps1
  start-openclaw-gateway.ps1
  start-openclaw-node.ps1
  start-box-service.ps1
```

## Product responsibility split

- `gateway/` is the app-facing edge for phones and tablets.
- `gateway/` is responsible for box discovery metadata, pairing, session creation, and remote intake relay.
- `box/` is the home-side core that stores data, classifies it, creates reminders, drives the TV dashboard, and exposes local device actions.
- TV, HDMI dashboard, voice broadcast, wake-word follow-up, and future smart-home orchestration belong to `box/`, not `gateway/`.
- In production, Railway can run the Python `gateway/` directly as the public API edge. OpenClaw is optional and should be treated as a separate orchestration concern, not the default Railway runtime.

## Box runtime modules

- `Hub Orchestrator`: central route layer for dashboard, voice wake, and automation.
- `Always-on TV Dashboard`: HDMI family board with alerts, reminders, and orchestration state.
- `Voice Wake Loop`: passive listening state, wake-phrase routing, and spoken alert execution.
- `OpenClaw Agent Surface`: intake agent, dashboard agent, voice automation agent, and home orchestrator agent.

See [box-architecture.md](e:/Workspace/HomeAIHub/docs/box-architecture.md) for the current module diagram and next-step refactor checklist.

## Pairing logic implemented in this repo

This MVP already includes the product-style onboarding flow:

1. The box boots and creates a device record.
2. The box exposes a short-lived claim token and pairing metadata.
3. The TV dashboard switches to pairing mode when the box is unclaimed.
4. The mobile app mock fetches the claim payload from Gateway.
5. The user claims the box with `device_id + claim_token`.
6. After claim succeeds, the dashboard switches from onboarding to family dashboard mode.
7. A paired device can be unbound and returned to onboarding mode.
8. Mobile uploads continue to go through Gateway, not directly to the box.
9. Gateway relays the payload to the home box, where local services classify and store it.

Current MVP device model:

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
- text, photo, and voice intake still go through Gateway and land in the local box database
- TTS and TV actions remain box-side capabilities triggered through Gateway

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
- `POST /api/gateway/intake/text`
- `POST /api/gateway/intake/photo`
- `POST /api/gateway/intake/voice`
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

## Railway deployment

The default Railway deployment in this repo is now the Python public API gateway, not OpenClaw.

Recommended production deployment:

- Railway runs `python -m home_ai_hub`
- the home box runs `python -m box` locally
- the app talks to Railway for pairing, status, and relay APIs
- the home box sends outbound heartbeats to Railway and polls pending relay jobs
- Railway sync endpoints are protected with `HOMEAIHUB_BOX_SHARED_TOKEN`

See the Railway guide here:

- [railway-openclaw.md](e:/Workspace/HomeAIHub/docs/railway-openclaw.md)
- [Dockerfile.railway](e:/Workspace/HomeAIHub/Dockerfile.railway)
- [start-railway-gateway.sh](e:/Workspace/HomeAIHub/scripts/start-railway-gateway.sh)

Compatibility aliases are still present if an existing Railway service points at them:

- [Dockerfile.openclaw](e:/Workspace/HomeAIHub/Dockerfile.openclaw)
- [start-openclaw-railway.sh](e:/Workspace/HomeAIHub/scripts/start-openclaw-railway.sh)

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
