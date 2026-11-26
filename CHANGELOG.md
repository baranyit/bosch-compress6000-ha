# Changelog

## 0.4.0 (beta)

New read-only sensors from a full read-only survey of the gateway: appliance supply temperature,
supply setpoint, health status (`ok`/`maintenance`/`error`) and hot water flow. The default poll
interval is now 60 s (was 120 s; the minimum stays 30 s and is still raised to the derived minimum
for the number of points). The survey found no TC0/TC3, circulation pump, defrost, fault list or
system pressure on this gateway: compressor and evaporator temperature, compressor power and eHeater
status exist in its tree but answer HTTP 403, so they are not catalogued. Existing installations keep
their stored poll interval; only new setups get 60 s. No entity was changed or removed.

## 0.3.0 (beta)

Breaking: only writes verified on real hardware stay available. Hot water mode, hot water target
temperature, heating mode and manual room setpoint are now read-only **sensors**
(`sensor.heatpump_hot_water_mode`, `..._hot_water_target_temperature`, `..._heating_mode`,
`..._manual_room_setpoint`) instead of select and number entities, and the `hot_water` and `heating`
write groups are gone (stored options naming them are ignored). Extra hot water (`extra_hot_water`)
is unchanged. The old `select.*` / `number.*` entities become unavailable and can be deleted. The
four original entities are untouched. README: hardware validation section, HACS-search-first install.

## 0.2.1 (beta)

Patch: GitHub Actions are pinned to commit SHAs and Dependabot (Actions and pip, weekly) keeps them
current, and `SECURITY.md` describes private vulnerability reporting. The `main` branch is protected by a ruleset (pull request and passing checks required).
No behaviour change.

## 0.2.0 (beta)

Breaking: the integration is a standalone project, so the entity take-over feature is removed (the
`migration.py` module and the "take over" option). The four original entities keep their entity IDs
and unique IDs. Stored options that still contain the removed key are ignored.

## 0.1.2 (beta)

Patch: documentation moved into the code and AGENTS.md (the `docs/` folder is gone), official logo,
and hassfest and HACS validation run as their own
workflows (README status badges, weekly schedule). No behaviour change.

## 0.1.1 (beta)

Patch: hassfest rejects requirements that Home Assistant itself provides; `cryptography` and
`aiohttp` are removed from the manifest (no behaviour change).

## 0.1.0 (beta)

First version.

- Local KM200 gateway polling (encrypted HTTP, no cloud); serialized, spaced requests.
- Entities: `sensor.bosch_total_consumed_energy_kwh`, `sensor.bosch_compressor_consumed_energy_kwh`,
  `sensor.bosch_eheater_consumed_energy_kwh`, `sensor.heatpump_outdoor_temperature`.
- Hourly energy keeps `state_class: total` with `last_reset`, and an hour without data is never 0.0.
- Extra metrics: supply/return/room/hot water temperatures, modulation, pump modulation, starts,
  pressure, heat output energy.
- Optional, off-by-default remote control in separate groups: extra hot water, hot water settings,
  heating settings.
