# Bosch Compress 6000 for Home Assistant

Status: beta (0.1.1, unreleased).

A custom integration for a Bosch Compress 6000 heat pump behind a Bosch/Buderus KM200-family
gateway. Local only (encrypted HTTP), no cloud, no MQTT, no HomeGate. It replaces the Bosch part of
the retired HomeGate bridge and keeps its entity IDs and unique IDs, so history and the Energy
dashboard continue.

## What you get

| Kind | Entities |
|---|---|
| Energy (hourly, kept compatible) | `sensor.bosch_total_consumed_energy_kwh`, `sensor.bosch_compressor_consumed_energy_kwh`, `sensor.bosch_eheater_consumed_energy_kwh`, plus new *Heat output energy* |
| Metrics | outdoor, supply, return, room and hot water temperatures, setpoints, modulation, pump modulation, compressor starts, system pressure |
| Remote control (off by default) | **Extra hot water** switch; hot water mode and target temperature; heating mode and manual room setpoint |

Entities for resources the gateway does not have are simply not created.

## Setup

1. Install via HACS (custom repository) or copy `custom_components/bosch_compress6000`.
2. *Add integration → Bosch Compress 6000*: gateway address, the gateway password from its sticker
   (dashes are ignored) and the private password set in the vendor app.
3. Options: poll interval, take over the old MQTT entities (default on), and **write mode**.

Writing is off by default. Enable it per group (`extra_hot_water`, `hot_water`, `heating`); a command
is sent once after a short delay, checked against the limits the gateway reports, and read back.

## Replacing HomeGate

See [docs/03-migration.md](docs/03-migration.md): remove `mqtt/sensors/bosch.yaml` first, then add the
integration; the old MQTT registry entries are re-pointed to it so entity IDs and statistics stay.

## Development

See [AGENTS.md](AGENTS.md). Quality gates: `python -m pytest`, `ruff check . && ruff format --check .`, `mypy`.
