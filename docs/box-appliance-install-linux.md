# Linux Appliance Install

This is the recommended production-style install for an IPC or dedicated HomeAIHub appliance.

## Fixed choice for the appliance build

Use this baseline:
- Linux with `systemd`
- `python -m box` as the box runtime
- `scripts/start-box-service.sh prod` as the boot launcher
- `homeaihub-box.service` as the required boot service
- optional Chromium kiosk display for the dashboard

## Files used from this repo

- Box boot launcher: `scripts/start-box-service.sh`
- Appliance installer: `scripts/install-box-appliance-linux.sh`
- Box service template: `deploy/box/systemd/homeaihub-box.service.template`
- Dashboard kiosk template: `deploy/box/systemd/homeaihub-dashboard-kiosk.service.template`
- LightDM autologin template: `deploy/box/lightdm/50-homeaihub-autologin.conf.template`

## Step-by-step install commands

Assume:
- repo root is `/opt/HomeAIHub`
- runtime user is `homeaihub`
- environment file is `box/env/.env.prod`

### 1. Create a runtime user

```bash
sudo useradd -m -s /bin/bash homeaihub || true
```

### 2. Place the repo

```bash
sudo mkdir -p /opt
sudo rsync -a ./ /opt/HomeAIHub/
sudo chown -R homeaihub:homeaihub /opt/HomeAIHub
```

### 3. Configure the box env file

Edit:

```bash
sudo -u homeaihub nano /opt/HomeAIHub/box/env/.env.prod
```

At minimum set:

```env
HOMEAIHUB_RAILWAY_API_BASE_URL=https://your-api.up.railway.app
HOMEAIHUB_BOX_SHARED_TOKEN=replace-with-a-long-random-secret
HOMEAIHUB_BOX_SYNC_INTERVAL_SECONDS=10
HOMEAIHUB_BOX_HOST=0.0.0.0
HOMEAIHUB_BOX_PORT=8090
```

### 4. Install the appliance boot service

Box service only:

```bash
cd /opt/HomeAIHub
sudo ./scripts/install-box-appliance-linux.sh   --repo-root /opt/HomeAIHub   --box-user homeaihub   --environment prod
```

Box service plus kiosk display:

```bash
cd /opt/HomeAIHub
sudo ./scripts/install-box-appliance-linux.sh   --repo-root /opt/HomeAIHub   --box-user homeaihub   --environment prod   --enable-kiosk
```

Box service plus kiosk plus LightDM autologin:

```bash
cd /opt/HomeAIHub
sudo ./scripts/install-box-appliance-linux.sh   --repo-root /opt/HomeAIHub   --box-user homeaihub   --environment prod   --enable-kiosk   --configure-lightdm-autologin   --desktop-session LXDE
```

## Validation commands

Check service status:

```bash
systemctl status homeaihub-box.service --no-pager
```

Check kiosk status:

```bash
systemctl status homeaihub-dashboard-kiosk.service --no-pager
```

Check local health:

```bash
curl http://127.0.0.1:8090/health
```

Check OpenClaw runtime overview:

```bash
curl http://127.0.0.1:8090/api/box/openclaw/overview
```

## Expected appliance behavior

On power-on:
1. Linux boots.
2. `systemd` starts `homeaihub-box.service`.
3. Box connects to Railway.
4. If unpaired, box still stays active locally and can accept local voice operations.
5. If kiosk is enabled, the dashboard opens on the attached screen.
6. Once paired, remote app actions route to this box through Railway.
