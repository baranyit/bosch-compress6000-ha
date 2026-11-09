# Migration from the HomeGate MQTT entities

## Entity IDs before / after

| Entity ID (unchanged) | unique_id (unchanged) | Before | After |
|---|---|---|---|
| sensor.bosch_total_consumed_energy_kwh | bosch_energymonitoring_total | MQTT `consumption.consumedEnergy` | `total_energy` |
| sensor.bosch_compressor_consumed_energy_kwh | bosch_energymonitoring_compressor | MQTT `consumption.compressor` | `compressor_energy` |
| sensor.bosch_eheater_consumed_energy_kwh | bosch_energymonitoring_eheater | MQTT `consumption.eheater` | `eheater_energy` |
| sensor.heatpump_outdoor_temperature | bosch_outdoor_temperature | MQTT `state.outdoorTemp` | `outdoor_temperature` |

Unchanged: `kWh`/`energy`/`total` + `last_reset` (start of the completed hour) + `force_update`; `°C`/`temperature`;
device `heatpump` / Bosch / Compress6000. New entities use `bosch_<key>` unique IDs.

## How the IDs survive

The entity registry maps `(platform, unique_id)` to the entity ID. The old entries belong to platform
`mqtt`, so a plain new integration would get `_2` IDs and split the statistics. On setup (option
*Take over the old MQTT entities*, default on) the integration re-points those registry entries to
itself with `EntityRegistry.async_update_entity_platform` (the registry API, never `.storage`),
keeping entity ID, name and statistics, and moves them to the new device.

## Cut-over steps (each one a separate, explicit step)

1. Verify statistics first (known issue): Developer tools → Statistics for the compressor and
   eheater sensors; the three energy states were `0.0` after the last restart (restored/retained,
   HomeGate stopped). Fix any bogus `0.0` hours before relying on the Energy dashboard.
2. In the HA config repo, remove `mqtt/sensors/bosch.yaml` (only on request), validate with
   `tools/validate-config.sh`, deploy per `DEPLOYMENT.md`, then `mqtt.reload`. The YAML entities
   must be gone first, otherwise MQTT and this integration both claim the unique IDs.
3. Install the integration (HACS custom repository), add it, enter the passwords.
4. Check the four entity IDs, the device grouping and that the Energy dashboard shows history
   continuously. Expect **no gap in the hourly statistics** only if HomeGate's last hour and the first
   hour read by the integration are adjacent; hours between are not back-filled (see below).
5. Enable write mode only when wanted, per group.

## Statistics gap

Hours between HomeGate's stop and the first integration read are not back-filled: the sensor shows
only the last completed hour. Back-fill would need a statistics import and is out of scope.

## Not verified yet

Everything against the real gateway (see `open-decisions.md`), the real unit of the recordings
(kWh assumed from the existing sensors), and the Energy preferences (`bosch_total_consumed_energy_kwh`
was not in them).
