#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-develop}"
case "$ENVIRONMENT" in
  develop|stage|prod) ;;
  *)
    echo "Unsupported environment: $ENVIRONMENT" >&2
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/box/env/.env.$ENVIRONMENT"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Environment file not found: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

cd "$REPO_ROOT"
echo "Starting box with environment: $ENVIRONMENT"
echo "Loaded env file: $ENV_FILE"
exec python -m box
