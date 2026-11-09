# Handover: cut over from the HomeGate Bosch MQTT entities to the bosch_compress6000 integration

## Context
- Target repo: baranyit/ha-config (production Home Assistant config, YAML-managed MQTT in `mqtt/sensors/bosch.yaml`).
- The replacement is the custom integration `bosch_compress6000` (HACS custom repository
  `baranyit/bosch-compress6000-ha`, version 0.1.1, CI green). It talks to the Bosch/Buderus KM200
  gateway locally (192.168.1.109); no MQTT, no HomeGate.
- Do not touch Wavin. Rules from AGENTS.md apply: never edit `.storage`, `secrets.yaml` or the DB;
  do not commit, push or deploy unless explicitly asked; never print secrets.

## What the integration provides (entity IDs and unique IDs are unchanged)
| Entity ID | unique_id |
|---|---|
| sensor.bosch_total_consumed_energy_kwh | bosch_energymonitoring_total |
| sensor.bosch_compressor_consumed_energy_kwh | bosch_energymonitoring_compressor |
| sensor.bosch_eheater_consumed_energy_kwh | bosch_energymonitoring_eheater |
| sensor.heatpump_outdoor_temperature | bosch_outdoor_temperature |

Same device (heatpump / Bosch / Compress6000), same `kWh`/`energy`/`total` + `last_reset`. On setup the
integration re-points the old `mqtt` registry entries with these unique IDs to itself (registry API,
option "Take over the old MQTT entities", default on), so entity IDs and statistics stay. It also
adds metric sensors and an off-by-default write mode (Extra hot water switch, hot water and heating
settings).

## Your task in this repo (each step a separate explicit change; ask before each)
1. **Check the Energy statistics first.** The three energy sensors were 0.0 after the last restart
   (restored/retained, HomeGate stopped). Report, read-only, whether statistics for the compressor and
   eheater sensors contain bogus 0.0 hours. Do not modify the DB; propose a fix.
2. **Remove `mqtt/sensors/bosch.yaml`** (only on request), check that nothing else references
   `homegate/bosch/*`, validate with `tools/validate-config.sh`, deploy per `DEPLOYMENT.md`, then
   `mqtt.reload`. This must happen **before** the integration is added; otherwise MQTT and the
   integration both claim the unique IDs.
3. Update docs (`HOMELAB_CONTEXT.md`, `AGENTS.md` MQTT section, homelab notes) to say Bosch is handled
   by the integration, like Wavin. No secrets in them.
4. Confirm the Energy dashboard preferences still point to the compressor and eheater sensors and the
   Overview still uses `sensor.heatpump_outdoor_temperature` (nothing needs renaming).

## User steps (not yours)
Install the integration through HACS (custom repository), add it with the gateway address, the
sticker password and the private app password, then check the four entity IDs, the device grouping and
history continuity. Write mode stays off until the user enables it per group.

## Known limits
- Hours between HomeGate stopping and the first integration read are not back-filled.
- Hardware-verified: reads, hourly energy recordings, and one extra hot water start/stop (restored).
  Not verified: the Home Assistant write path on the real gateway, the other writable points.
- `system_pressure` and `heating_manual_setpoint` do not exist on this gateway, so no entities for them.
- A plain-text copy of the real gateway credentials lives in `homegate/bosch-keygen.sh`; rotate it and
  remove it from that project.

## Done when
- `mqtt/sensors/bosch.yaml` is gone and validated, docs updated.
- The integration is added, the four entities have live values under the same IDs, Energy and Overview
  show history continuously.
- Report: entity IDs before/after, any statistics gap, and what was not verified.
