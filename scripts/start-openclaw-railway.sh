#!/usr/bin/env bash
set -euo pipefail

: "${PORT:=8080}"
: "${OPENCLAW_GATEWAY_TOKEN:?OPENCLAW_GATEWAY_TOKEN is required}"

exec openclaw gateway --allow-unconfigured --bind lan --port "$PORT"
