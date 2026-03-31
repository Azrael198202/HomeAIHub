# HomeAIHub Box Architecture

This is the target operating model for the home box in this repository.

## Module Diagram

```text
Mobile App / Tablet
  -> Gateway
  -> Family Intake Agent
  -> Home Box

Home Box
  -> Hub Orchestrator
     -> Intake Pipeline
        -> OCR
        -> Event Parser
        -> Calendar / Reminder / Info storage
     -> Always-on TV Dashboard
        -> TV Dashboard Service
        -> HDMI-connected TV
        -> Popup / acknowledgement flow
     -> Voice Wake Loop
        -> Wake phrase listener state
        -> Voice intent router
        -> TTS / announcement playback
     -> Automation Surface
        -> TV control
        -> Spoken alerts
        -> Future smart-home actions
     -> OpenClaw Agent Surface
        -> Family Intake Agent
        -> Household Dashboard Agent
        -> Voice Automation Agent
        -> Home Orchestrator Agent
```

## Responsibility Split

- `gateway/` is only the public app edge, pairing surface, and remote relay.
- `box/` is the private household brain and source of truth.
- `box/hub_orchestrator/` coordinates household routes and active agent state.
- `box/event_parser/service.py` still provides the local OCR, parsing, reminder scan, TTS, TV control, and dashboard payload assembly used by the box.
- `box/tv_dashboard/web/` is the passive HDMI family surface.
- `scripts/box_node_bridge.py` is the stable bridge for OpenClaw node exec.

## Current Runtime Flows

### 1. Always-on TV dashboard

1. Box stays paired and keeps `dashboard_mode=always_on`.
2. Dashboard service reads schedule, reminders, info, notifications, active agent, and voice state.
3. TV surface shows a passive family board plus a priority alert strip.
4. Urgent notifications can still raise an acknowledgement modal.

### 2. Voice wake loop

1. Voice listener remains in `passive` state.
2. A wake phrase or transcript enters `/api/box/voice/wake`.
3. Hub orchestrator classifies the transcript into a route.
4. Route dispatches to TV wake, dashboard refresh, spoken alert, or generic listen mode.

### 3. OpenClaw orchestration

1. Gateway session opens with a role policy.
2. OpenClaw agent chooses a capability-level action.
3. Gateway relays the action to the box control plane.
4. Hub orchestrator or domain service executes locally.
5. Result is logged in the box command history.

## Next Refactor Checklist

1. Split `box/event_parser/service.py` into real modules so parser, reminders, info, TTS, TV control, and dashboard payloads are no longer co-located.
2. Replace transcript-only `voice.wake` with a real wake-word listener and ASR adapter.
3. Add device registry models for HDMI display, microphones, speakers, and future smart-home nodes.
4. Add explicit routine engines for morning brief, leave-home reminder, and emergency alert escalation.
5. Replace the MVP `gateway/openclaw_gateway/server.py` router with the real OpenClaw Gateway plus node tools in production.
6. Add a smart-home action bus so orchestration can target lights, locks, sensors, and appliance scenes.
7. Add richer authorization so guest and child roles can see status without triggering high-risk automation.
