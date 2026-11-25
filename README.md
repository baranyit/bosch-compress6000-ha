<p align="center">
  <img src="custom_components/bosch_compress6000/brand/logo@2x.png" alt="Bosch Compress 6000 for Home Assistant" width="640">
</p>

# Bosch Compress 6000 for Home Assistant

[![Hassfest](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hassfest.yml/badge.svg)](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hassfest.yml)
[![HACS validation](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hacs.yml/badge.svg)](https://github.com/baranyit/bosch-compress6000-ha/actions/workflows/hacs.yml)

Status: beta (0.3.0, 2026-11-25).

A custom integration for a Bosch Compress 6000 heat pump behind a Bosch/Buderus KM200-family
gateway. Local only (encrypted HTTP), no cloud.

## What you get

| Kind | Entities |
|---|---|
| Energy (hourly, Energy-dashboard compatible) | `sensor.bosch_total_consumed_energy_kwh`, `sensor.bosch_compressor_consumed_energy_kwh`, `sensor.bosch_eheater_consumed_energy_kwh`, plus *Heat output energy* |
| Metrics | outdoor, supply, return, room and hot water temperatures, setpoints, modulation, pump modulation, compressor starts, system pressure |
| Settings (read-only) | hot water mode and target temperature, heating mode and manual room setpoint |
| Remote control (off by default) | **Extra hot water** switch |

Entities for resources the gateway does not have are simply not created.

## Setup

1. Install via HACS: search for *Bosch Compress 6000* and download it. Until it is listed in the HACS
   default store, add `baranyit/bosch-compress6000-ha` as a custom repository (type *Integration*)
   first. Or copy `custom_components/bosch_compress6000` into your config folder.
2. *Add integration → Bosch Compress 6000*: gateway address, the gateway password from its sticker
   (dashes are ignored) and the private password set in the vendor app.
3. Options: poll interval and **write mode**.

Writing is off by default. When enabled, the only writable group is `extra_hot_water` (start or stop
one extra hot water charge); a command is sent once after a short delay, checked against the limits the
gateway reports, and read back.

## Hardware validation

Tested on one real Compress 6000 behind its KM200-family gateway (2026-11-09):

| What | Result |
|---|---|
| Reading all metrics and hourly energy recordings | verified |
| Extra hot water start, then stop (15 s) | verified: accepted by the gateway and read back |
| Physical effect and run time of an extra hot water charge | not measured |
| Hot water mode and target temperature, heating mode and manual room setpoint | **read-only**: the gateway reports them as writeable, but writing them has not been tried on hardware, so the integration does not offer to |

A setting becomes writable only after a hardware-approved test (one point, observe, restore). If you
can run such a test on your own heat pump, please open an issue with the result.

## Development

See [AGENTS.md](AGENTS.md). Quality gates: `python -m pytest`, `ruff check . && ruff format --check .`, `mypy`.
