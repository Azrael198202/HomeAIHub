#!/usr/bin/env bash
set -euo pipefail

: "${PORT:=8080}"
: "${OPENCLAW_GATEWAY_TOKEN:?OPENCLAW_GATEWAY_TOKEN is required}"
: "${OPENCLAW_CONFIG_PATH:=/app/deploy/openclaw/openclaw.railway.json5}"

exec openclaw gateway --allow-unconfigured --port "$PORT" --bind lan --auth token --token "$OPENCLAW_GATEWAY_TOKEN"
