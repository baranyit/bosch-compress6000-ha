<p align="center">
  <img src="custom_components/bosch_compress6000/brand/logo@2x.png" alt="Bosch Compress 6000 for Home Assistant" width="640">
</p>

# Bosch Compress 6000 for Home Assistant

[![Hassfest](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hassfest.yml/badge.svg)](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hassfest.yml)
[![HACS validation](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hacs.yml/badge.svg)](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hacs.yml)

Status: beta (0.2.0, unreleased).

A custom integration for a Bosch Compress 6000 heat pump behind a Bosch/Buderus KM200-family
gateway. Local only (encrypted HTTP), no cloud.

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
3. Options: poll interval and **write mode**.

Writing is off by default. Enable it per group (`extra_hot_water`, `hot_water`, `heating`); a command
is sent once after a short delay, checked against the limits the gateway reports, and read back.

## Development

See [AGENTS.md](AGENTS.md). Quality gates: `python -m pytest`, `ruff check . && ruff format --check .`, `mypy`.
