#!/usr/bin/env bash
set -euo pipefail

: "${PORT:=8080}"
: "${HOMEAIHUB_HOST:=0.0.0.0}"
: "${HOMEAIHUB_PORT:=$PORT}"

export HOMEAIHUB_HOST
export HOMEAIHUB_PORT

exec python -m home_ai_hub
