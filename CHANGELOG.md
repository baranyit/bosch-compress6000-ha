# Changelog

## 0.2.0 (unreleased, beta)

Breaking: the integration is a standalone project, so the entity take-over feature is removed (the
`migration.py` module and the "take over" option). The four original entities keep their entity IDs
and unique IDs. Stored options that still contain the removed key are ignored.

## 0.1.2 (unreleased, beta)

Patch: documentation moved into the code and AGENTS.md (the `docs/` folder is gone), official logo,
and hassfest and HACS validation run as their own
workflows (README status badges, weekly schedule). No behaviour change.

## 0.1.1 (unreleased, beta)

Patch: hassfest rejects requirements that Home Assistant itself provides; `cryptography` and
`aiohttp` are removed from the manifest (no behaviour change).

## 0.1.0 (unreleased, beta)

First version.

- Local KM200 gateway polling (encrypted HTTP, no cloud); serialized, spaced requests.
- Entities: `sensor.bosch_total_consumed_energy_kwh`, `sensor.bosch_compressor_consumed_energy_kwh`,
  `sensor.bosch_eheater_consumed_energy_kwh`, `sensor.heatpump_outdoor_temperature`.
- Hourly energy keeps `state_class: total` with `last_reset`, and an hour without data is never 0.0.
- Extra metrics: supply/return/room/hot water temperatures, modulation, pump modulation, starts,
  pressure, heat output energy.
- Optional, off-by-default remote control in separate groups: extra hot water, hot water settings,
  heating settings.
