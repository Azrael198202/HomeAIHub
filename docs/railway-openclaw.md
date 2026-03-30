# Railway OpenClaw Deployment

This is the recommended production shape for HomeAIHub:

```text
Flutter App / Web App
  -> OpenClaw Gateway on Railway
  -> HomeAIHub box at home as OpenClaw node
  -> local box services on the home LAN
```

## Why this is the right split

- Railway hosts the public control plane.
- The home box stays in the user's house.
- The box makes an outbound connection to Gateway, so no home port forwarding is required.
- Mobile clients only need the Railway domain.

According to current OpenClaw docs:

- the Gateway is the WS + control UI server
- nodes connect to the Gateway and use device pairing
- node auth prefers `OPENCLAW_GATEWAY_TOKEN`
- TLS gateways require `openclaw node run --tls`

Sources:

- https://docs.openclaw.ai/start/quickstart
- https://docs.openclaw.ai/nodes
- https://docs.openclaw.ai/gateway/configuration
- https://docs.railway.com/deploy/services
- https://docs.railway.com/public-networking
- https://docs.railway.com/reference/tcp-proxy

## Recommended Railway approach

As of 2026-03-30, Railway's create-project UI may not show an OpenClaw template directly.
Use a manual service deployment from this GitHub repository instead.
Do not deploy the transitional Python `gateway/` service to Railway as the final control plane.

Use Railway for:

- OpenClaw Gateway
- generated public domain
- persistent config/data volume if your OpenClaw setup uses one

Keep at home:

- `python -m box`
- `openclaw node run ...`
- TV dashboard
- OCR / parser / TTS / local DB services

## Railway setup sequence

### 1. Deploy the real OpenClaw Gateway to Railway

In Railway UI:

1. Sign in to Railway.
2. Click `New Project`.
3. Choose `GitHub Repository`.
4. Select this repository.
5. After the first service is created, open that service.
6. Go to `Settings`.
7. Set the service to build from [Dockerfile.openclaw](e:/Workspace/HomeAIHub/Dockerfile.openclaw).
8. Go to `Variables` and add `OPENCLAW_GATEWAY_TOKEN` with a strong random value.
9. Keep `PORT` as Railway default or set it explicitly to `8080`.
10. Redeploy the service.
11. Go to `Settings -> Networking`.
12. In `Public Networking`, click `Generate Domain`.
13. Copy the generated domain.
14. Open that domain in the browser.
15. Complete the OpenClaw setup / onboarding flow.

Useful Railway sections while doing this:

- `Deployments`: inspect build and boot logs
- `Settings -> Source`: select the repo source and Dockerfile path
- `Settings -> Networking`: domain and proxy settings
- `Variables`: set `OPENCLAW_GATEWAY_TOKEN`
- `Metrics`: basic health checks after deploy

Files used by this manual Railway deployment:

- [Dockerfile.openclaw](e:/Workspace/HomeAIHub/Dockerfile.openclaw)
- [openclaw.railway.json5](e:/Workspace/HomeAIHub/deploy/openclaw/openclaw.railway.json5)
- [start-openclaw-railway.sh](e:/Workspace/HomeAIHub/scripts/start-openclaw-railway.sh)

If you see a Railway `502`, it usually means the container booted but the Gateway process failed or exited early. After each change, always check `Deployments` logs first.

You should end up with a public HTTPS domain such as:

```text
https://your-gateway.up.railway.app
```

If Railway asks for a raw TCP proxy instead of HTTP routing, expose the Gateway internal port using Railway TCP Proxy and connect the node to the generated proxy host and port.

### 2. Open the OpenClaw setup page

Open the Railway domain in a browser and complete the OpenClaw setup / onboarding wizard.

The OpenClaw quickstart currently recommends:

```bash
openclaw onboard --install-daemon
```

On Railway you will normally complete the equivalent setup in the deployed environment and UI.

### 3. Create or copy the Gateway token

From the OpenClaw setup or config, capture the Gateway auth token.

A practical UI-oriented sequence is:

1. Finish Gateway onboarding.
2. Open the OpenClaw control UI or config page.
3. Find the gateway auth token or credentials section.
4. Copy the token into a password manager or secure note.
5. Do not embed the token in the mobile app source.
6. Use it only on trusted node hosts or backend services.

OpenClaw docs show that config values can reference env vars such as:

```json5
{
  gateway: { auth: { token: "${OPENCLAW_GATEWAY_TOKEN}" } }
}
```

For the home box node, the simplest path is to set:

```text
OPENCLAW_GATEWAY_TOKEN=<your token>
```

### 4. Start the local HomeAIHub box service at home

On the home box machine:

```bash
python -m box
```

This keeps OCR, parsing, reminders, dashboard rendering, and the local database on the home device.

### 5. Connect the home box to Railway as a node

Windows PowerShell:

```powershell
./scripts/start-openclaw-node.ps1 -GatewayHost your-gateway.up.railway.app -GatewayPort 443 -Tls -GatewayToken "<your token>"
```

The script now supports:

- `-Tls` for HTTPS / WSS gateways
- `-GatewayToken` to export `OPENCLAW_GATEWAY_TOKEN` before launch

Equivalent raw CLI:

```bash
export OPENCLAW_GATEWAY_TOKEN="<your token>"
openclaw node run --host your-gateway.up.railway.app --port 443 --tls --display-name "HomeAIHub Mini Host"
```

If Railway gave you a TCP proxy endpoint instead, use that host and port instead of `443`.

### 6. Approve the node pairing in OpenClaw

OpenClaw node pairing is still required.
Approve the incoming node from the Gateway side.

After approval, your home box becomes a controllable node under the Railway-hosted Gateway.

## How HomeAIHub should use this

At runtime the split should become:

```text
Mobile app
  -> Railway OpenClaw Gateway
  -> HomeAIHub node
  -> local box service on 127.0.0.1:8090
```

That means:

- app traffic goes to Railway
- local box services stay private to the home device
- OpenClaw agents or node tools trigger local actions on the box

## Important current limitation in this repo

The current custom Python `gateway/` code still assumes it can call `box` over direct HTTP.
That is fine for local MVP runs, but it is not the final product topology.

For the final Railway topology, treat this repo as:

- local box runtime
- agent workspaces
- OpenClaw node client startup
- onboarding and pairing prototype

and treat Railway-hosted OpenClaw as the real cloud control plane.

## First check when Railway shows 502

Open Railway and inspect `Deployments` for the OpenClaw service. The most useful clues are usually one of these:

- `openclaw: command not found`
- `OPENCLAW_GATEWAY_TOKEN is required`
- auth / token / bind errors
- invalid config parse errors
- process exited before listening on the Railway port

With the current repo, the intended boot command is now effectively:

```bash
openclaw gateway --allow-unconfigured --port $PORT --bind lan --auth token --token $OPENCLAW_GATEWAY_TOKEN
```

If the service still returns `502` after redeploy, copy the last 30 to 50 log lines from `Deployments` and use that as the next debugging step.
