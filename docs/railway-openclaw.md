# Railway Public API Deployment

This repo's Railway deployment no longer needs OpenClaw if Railway is only used as the public app API.

Recommended production shape:

```text
Flutter App / Web App
  -> Railway Public API
  -> queued relay jobs

HomeAIHub Box at home
  -> outbound heartbeat to Railway
  -> poll pending relay jobs
  -> local intake and acknowledgement
```

## When OpenClaw is not needed on Railway

If Railway only needs to do these jobs:

- expose the public app API
- return box pairing and status information
- relay text, photo, and voice payloads
- delete temporary transfer files after the box confirms receipt

then Railway does not need to run OpenClaw.

In this repo, the Railway service should simply run the Python gateway.

## Public endpoints

- `GET /api/railway/box`
- `GET /api/railway/box/status`
- `GET /api/railway/box/link`
- `GET /api/railway/boxes`
- `GET /api/railway/relay/status?relay_id=...`
- `POST /api/railway/relay/message`
- `POST /api/railway/relay/photo`
- `POST /api/railway/relay/voice`
- `POST /api/railway/box/register`
- `POST /api/railway/box/heartbeat`
- `GET /api/railway/relay/pending?device_id=...`
- `POST /api/railway/relay/ack`

## Relay behavior

- external apps talk only to Railway
- Railway writes pending relay jobs into its local queue
- Railway may create a short-lived temp file during transfer
- the home box initiates outbound sync to Railway
- the home box polls pending relay jobs, processes them locally, and posts an acknowledgement
- once Railway receives the acknowledgement, it deletes the temp file
- the initial app response includes `relay_id` and queue status
- the app can query `GET /api/railway/relay/status?relay_id=...` to confirm delivery

Example payload:

```json
{
  "text": "package left at the front door",
  "filename": "doorbell.jpg",
  "mime_type": "image/jpeg",
  "content_base64": "<base64-data>"
}
```

## Railway deployment files

Use these files for Railway:

- [Dockerfile.railway](e:/pw/HomeAIHub/Dockerfile.railway)
- [start-railway-gateway.sh](e:/pw/HomeAIHub/scripts/start-railway-gateway.sh)

The old OpenClaw-specific Railway files are no longer required for this deployment mode.

## Recommended Railway variables

```env
HOMEAIHUB_RAILWAY_PUBLIC_BASE_URL=https://your-api.up.railway.app
HOMEAIHUB_GATEWAY_BASE_URL=https://your-api.up.railway.app
HOMEAIHUB_HOST=0.0.0.0
HOMEAIHUB_PORT=8080
PORT=8080
```

If Railway needs a writable temp location:

```env
HOMEAIHUB_RELAY_TEMP_DIR=/tmp/homeaihub-relay
HOMEAIHUB_BOX_SHARED_TOKEN=replace-with-a-long-random-secret
HOMEAIHUB_RAILWAY_CLEANUP_INTERVAL_SECONDS=60
HOMEAIHUB_RAILWAY_JOB_RETENTION_SECONDS=86400
HOMEAIHUB_RAILWAY_BOX_STALE_AFTER_SECONDS=90
```

## Railway setup

1. Create a new Railway project from this repository.
2. Set the service to build from [Dockerfile.railway](e:/pw/HomeAIHub/Dockerfile.railway).
3. Add the environment variables listed above.
4. Generate a public domain in Railway Networking.
5. Set `HOMEAIHUB_RAILWAY_PUBLIC_BASE_URL` and `HOMEAIHUB_GATEWAY_BASE_URL` to that domain.
6. Redeploy.

## Home box setup

On the home box machine, start the box service with the Railway API base URL:

```env
HOMEAIHUB_RAILWAY_API_BASE_URL=https://your-api.up.railway.app
HOMEAIHUB_BOX_SYNC_INTERVAL_SECONDS=10
HOMEAIHUB_BOX_SHARED_TOKEN=replace-with-a-long-random-secret
```

Then run:

```bash
python -m box
```

The box process will:

- register itself with Railway
- send heartbeats
- poll pending relay jobs
- process them locally
- acknowledge completed jobs so Railway can delete temp files

## Important limitation

This polling-based setup removes the need for Railway to connect inbound to the home box.
If you later want agent orchestration or node execution, OpenClaw can still be added back as a separate concern instead of being the Railway runtime itself.

## Curl examples

Query the current public box status:

```bash
curl https://your-api.up.railway.app/api/railway/box/status
```

Queue a text relay job:

```bash
curl -X POST https://your-api.up.railway.app/api/railway/relay/message \
  -H "Content-Type: application/json" \
  -d '{
    "text": "mom dentist tomorrow 3pm",
    "filename": "message.txt",
    "mime_type": "text/plain"
  }'
```

Queue a photo relay job:

```bash
curl -X POST https://your-api.up.railway.app/api/railway/relay/photo \
  -H "Content-Type: application/json" \
  -d '{
    "text": "front door snapshot",
    "filename": "door.jpg",
    "mime_type": "image/jpeg",
    "content_base64": "<base64-data>"
  }'
```

Check relay status:

```bash
curl "https://your-api.up.railway.app/api/railway/relay/status?relay_id=<relay-id>"
```

Manual box registration test:

```bash
curl -X POST https://your-api.up.railway.app/api/railway/box/register \
  -H "Content-Type: application/json" \
  -H "X-HomeAIHub-Box-Token: replace-with-a-long-random-secret" \
  -d '{
    "device_id": "hub-demo-001",
    "device_name": "HomeAIHub Box",
    "pairing_status": "paired",
    "owner_name": "Mom",
    "family_id": "family-demo",
    "box_status": "online",
    "dashboard_path": "/dashboard"
  }'
```

Manual box polling test:

```bash
curl -H "X-HomeAIHub-Box-Token: replace-with-a-long-random-secret" \
  "https://your-api.up.railway.app/api/railway/relay/pending?device_id=hub-demo-001"
```
