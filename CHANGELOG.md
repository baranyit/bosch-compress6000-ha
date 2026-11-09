# Changelog

## 0.1.1 (unreleased, beta)

Patch: hassfest rejects requirements that Home Assistant itself provides; `cryptography` and
`aiohttp` are removed from the manifest (no behaviour change).

## 0.1.0 (unreleased, beta)

First version: replaces the Bosch part of the retired HomeGate MQTT bridge.

- Local KM200 gateway polling (encrypted HTTP, no cloud, no MQTT); serialized, spaced requests.
- Entities with unchanged IDs: `sensor.bosch_total_consumed_energy_kwh`,
  `sensor.bosch_compressor_consumed_energy_kwh`, `sensor.bosch_eheater_consumed_energy_kwh`,
  `sensor.heatpump_outdoor_temperature` (unique IDs kept; the old MQTT registry entries are taken
  over, so history and the Energy dashboard continue).
- Hourly energy keeps `state_class: total` with `last_reset`, and an hour without data is never 0.0.
- Extra metrics: supply/return/room/hot water temperatures, modulation, pump modulation, starts,
  pressure, heat output energy.
- Optional, off-by-default remote control in separate groups: extra hot water, hot water settings,
  heating settings.
