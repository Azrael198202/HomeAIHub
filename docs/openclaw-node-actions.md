# OpenClaw Node Actions For HomeAIHub

This repo now includes a local bridge script for the home box:

- [box_node_bridge.py](e:/Workspace/HomeAIHub/scripts/box_node_bridge.py)

It is meant to run on the home box machine, through OpenClaw node exec, and forward actions to the local box API at `127.0.0.1:8090`.

## Why use a bridge script

Instead of allowing agents to run arbitrary commands on the node, keep node exec focused on one stable command surface:

```text
python scripts/box_node_bridge.py <action>
```

That gives you:

- one auditable entrypoint
- simpler exec approvals
- stable local API routing
- clearer mapping from OpenClaw agent intent to HomeAIHub actions

## Supported actions

Read actions:

```bash
python scripts/box_node_bridge.py health
python scripts/box_node_bridge.py device-status
python scripts/box_node_bridge.py pairing-payload
python scripts/box_node_bridge.py dashboard
python scripts/box_node_bridge.py hub-overview
python scripts/box_node_bridge.py voice-status
python scripts/box_node_bridge.py mobile-status
```

Family actions:

```bash
python scripts/box_node_bridge.py manual-intake "today 3pm mom dentist"
python scripts/box_node_bridge.py screenshot-intake "school notice parent meeting 2026-04-12 15:00"
python scripts/box_node_bridge.py photo-intake "package left at door"
python scripts/box_node_bridge.py voice-intake "tomorrow 8am take medicine"
```

Automation actions:

```bash
python scripts/box_node_bridge.py refresh-dashboard
python scripts/box_node_bridge.py wake-tv
python scripts/box_node_bridge.py tts "Leave home in 15 minutes"
python scripts/box_node_bridge.py announce "Emergency weather alert" --priority urgent
python scripts/box_node_bridge.py voice-wake "Hey Home, wake the TV"
```

Pairing actions:

```bash
python scripts/box_node_bridge.py claim-device --claim-token "<token>" --actor-user-id user-mom --actor-name Mom --family-name "My Family"
python scripts/box_node_bridge.py unbind-device --actor-user-id user-mom --actor-name Mom
python scripts/box_node_bridge.py reset-pairing
```

Notifications:

```bash
python scripts/box_node_bridge.py ack-notification 3
```

## Environment variable

If your local box service is not on `127.0.0.1:8090`, set:

```text
HOMEAIHUB_LOCAL_BOX_URL=http://127.0.0.1:8090
```

## OpenClaw approvals

OpenClaw docs recommend explicit exec approvals for node exec.
Useful commands:

```bash
openclaw approvals get --node <node-name>
openclaw approvals allowlist add --node <node-name> "/path/to/python"
```

Docs:

- https://docs.openclaw.ai/cli/approvals

Because approval policy is environment-specific, the safest approach is:

1. allow the local Python interpreter you actually use on the box
2. run only the exact bridge script from this repo
3. keep the box API private on localhost

## Intended agent usage

For real OpenClaw usage, `family-intake-agent`, `household-dashboard-agent`, `voice-automation-agent`, and `home-orchestrator-agent` should prefer node exec of this bridge script rather than direct arbitrary shell commands.
