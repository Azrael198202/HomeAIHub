#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BOX_USER="${SUDO_USER:-${USER}}"
ENVIRONMENT="prod"
ENABLE_KIOSK=0
CONFIGURE_LIGHTDM=0
BROWSER_BIN="/usr/bin/chromium"
DESKTOP_SESSION="LXDE"
SYSTEMD_DIR="/etc/systemd/system"
LIGHTDM_DIR="/etc/lightdm/lightdm.conf.d"

usage() {
  cat <<EOF
Usage: sudo ./scripts/install-box-appliance-linux.sh [options]

Options:
  --repo-root PATH              Repo root, default: current repo
  --box-user USER               Linux user that runs HomeAIHub Box
  --environment ENV             Box environment file suffix, default: prod
  --enable-kiosk                Install dashboard kiosk service
  --configure-lightdm-autologin Install a LightDM autologin drop-in
  --browser-bin PATH            Browser binary for kiosk, default: /usr/bin/chromium
  --desktop-session NAME        LightDM desktop session, default: LXDE
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="$2"
      shift 2
      ;;
    --box-user)
      BOX_USER="$2"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --enable-kiosk)
      ENABLE_KIOSK=1
      shift
      ;;
    --configure-lightdm-autologin)
      CONFIGURE_LIGHTDM=1
      shift
      ;;
    --browser-bin)
      BROWSER_BIN="$2"
      shift 2
      ;;
    --desktop-session)
      DESKTOP_SESSION="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ $EUID -ne 0 ]]; then
  echo "Run this script with sudo/root." >&2
  exit 1
fi

START_SCRIPT="$REPO_ROOT/scripts/start-box-service.sh"
ENV_FILE="$REPO_ROOT/box/env/.env.$ENVIRONMENT"
BOX_TEMPLATE="$REPO_ROOT/deploy/box/systemd/homeaihub-box.service.template"
KIOSK_TEMPLATE="$REPO_ROOT/deploy/box/systemd/homeaihub-dashboard-kiosk.service.template"
LIGHTDM_TEMPLATE="$REPO_ROOT/deploy/box/lightdm/50-homeaihub-autologin.conf.template"
BOX_SERVICE_OUT="$SYSTEMD_DIR/homeaihub-box.service"
KIOSK_SERVICE_OUT="$SYSTEMD_DIR/homeaihub-dashboard-kiosk.service"
LIGHTDM_OUT="$LIGHTDM_DIR/50-homeaihub.conf"

if [[ ! -f "$START_SCRIPT" ]]; then
  echo "Missing start script: $START_SCRIPT" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi
if [[ ! -f "$BOX_TEMPLATE" ]]; then
  echo "Missing box service template: $BOX_TEMPLATE" >&2
  exit 1
fi

chmod +x "$START_SCRIPT"
mkdir -p "$SYSTEMD_DIR"

sed   -e "s|__REPO_ROOT__|$REPO_ROOT|g"   -e "s|__BOX_USER__|$BOX_USER|g"   -e "s|start-box-service.sh prod|start-box-service.sh $ENVIRONMENT|g"   "$BOX_TEMPLATE" > "$BOX_SERVICE_OUT"

systemctl daemon-reload
systemctl enable homeaihub-box.service
systemctl restart homeaihub-box.service

if [[ $ENABLE_KIOSK -eq 1 ]]; then
  if [[ ! -f "$KIOSK_TEMPLATE" ]]; then
    echo "Missing kiosk service template: $KIOSK_TEMPLATE" >&2
    exit 1
  fi
  sed     -e "s|__BOX_USER__|$BOX_USER|g"     -e "s|/usr/bin/chromium|$BROWSER_BIN|g"     "$KIOSK_TEMPLATE" > "$KIOSK_SERVICE_OUT"
  systemctl daemon-reload
  systemctl enable homeaihub-dashboard-kiosk.service
fi

if [[ $CONFIGURE_LIGHTDM -eq 1 ]]; then
  if [[ ! -f "$LIGHTDM_TEMPLATE" ]]; then
    echo "Missing LightDM template: $LIGHTDM_TEMPLATE" >&2
    exit 1
  fi
  mkdir -p "$LIGHTDM_DIR"
  sed     -e "s|__BOX_USER__|$BOX_USER|g"     -e "s|__DESKTOP_SESSION__|$DESKTOP_SESSION|g"     "$LIGHTDM_TEMPLATE" > "$LIGHTDM_OUT"
fi

cat <<EOF
Installed HomeAIHub appliance mode.
- Service: $BOX_SERVICE_OUT
- User: $BOX_USER
- Environment: $ENVIRONMENT
- Box env file: $ENV_FILE
EOF

if [[ $ENABLE_KIOSK -eq 1 ]]; then
  echo "- Kiosk service: $KIOSK_SERVICE_OUT"
fi
if [[ $CONFIGURE_LIGHTDM -eq 1 ]]; then
  echo "- LightDM autologin: $LIGHTDM_OUT"
fi
