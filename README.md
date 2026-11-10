<p align="center">
  <img src="custom_components/bosch_compress6000/brand/logo@2x.png" alt="Bosch Compress 6000 for Home Assistant" width="640">
</p>

# Bosch Compress 6000 for Home Assistant

[![Hassfest](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hassfest.yml/badge.svg)](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hassfest.yml)
[![HACS validation](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hacs.yml/badge.svg)](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hacs.yml)

Status: beta (0.1.2, unreleased).

A custom integration for a Bosch Compress 6000 heat pump behind a Bosch/Buderus KM200-family
gateway. Local only (encrypted HTTP), no cloud, no MQTT. It can take over the entities of an earlier
MQTT-based setup and keeps their entity IDs and unique IDs, so history and the Energy dashboard continue.

## What you get

| Kind | Entities |
|---|---|
| Energy (hourly, Energy-dashboard compatible) | `sensor.bosch_total_consumed_energy_kwh`, `sensor.bosch_compressor_consumed_energy_kwh`, `sensor.bosch_eheater_consumed_energy_kwh`, plus *Heat output energy* |
| Metrics | outdoor, supply, return, room and hot water temperatures, setpoints, modulation, pump modulation, compressor starts, system pressure |
| Remote control (off by default) | **Extra hot water** switch; hot water mode and target temperature; heating mode and manual room setpoint |

Entities for resources the gateway does not have are simply not created.

## Setup

1. Install via HACS (custom repository `baranyit/bosch-compress6000-ha`) or copy `custom_components/bosch_compress6000`.
2. *Add integration → Bosch Compress 6000*: gateway address, the gateway password from its sticker
   (dashes are ignored) and the private password set in the vendor app.
3. Options: poll interval, take over the old MQTT entities (default on), and **write mode**.

Writing is off by default. Enable it per group (`extra_hot_water`, `hot_water`, `heating`); a command
is sent once after a short delay, checked against the limits the gateway reports, and read back.

## Replacing an MQTT setup

The four sensors above keep their entity IDs and unique IDs. Order matters:

1. Check the Energy statistics for bogus `0.0` hours first (old setups published `0.0` for missing hours).
2. Remove the old MQTT sensor definitions and reload MQTT. If they stay, MQTT and this integration both
   claim the same unique IDs.
3. Add the integration. The old MQTT registry entries are re-pointed to it, so entity IDs, names and
   statistics stay (turn this off in the options if unwanted).
4. Hours between the old setup stopping and the first read here are not back-filled.

## Development

See [AGENTS.md](AGENTS.md). Quality gates: `python -m pytest`, `ruff check . && ruff format --check .`, `mypy`.
