# Protocol specification (KM200-family gateway)

## Wire format

- `GET http://<host>/<path>` with `User-Agent: TeleHeater`. The body is base64 (the first line may be
  empty) of an AES-256-ECB ciphertext, zero padded; the plain text is JSON.
- Key = `MD5(gateway_password + MAGIC) || MD5(MAGIC + private_password)`, 32 bytes. The gateway
  password is the 16 characters on the sticker without dashes; the private password is the one set in
  the vendor app. `MAGIC` is the fixed 32 byte constant in `crypto.py`. A worked example with
  documentation values is a unit test (`tests/test_crypto.py`).
- `POST` the same encrypted/base64 form of `{"value": <number|string>}` to the resource path (headers
  `User-Agent` and `agent` = `TeleHeater`, JSON content type). Replies 200/204 on success.
- Resource JSON: `type`, `value`, `unitOfMeasure`, `writeable`, `allowedValues` (enums),
  `minValue`/`maxValue` (numbers). A reply without `value` is a directory, not a point.
- Recordings: `GET recordings/<path>?interval=YYYY-MM-DD` returns 24 hourly `{y, c}` samples;
  the hour value is `round(y / c, 2)`, and `c == 0` means no sample.

## Catalog and confidence

`homegate` = read on the real installation by the retired bridge. `standard` = standard KM200
resource, probed at setup and skipped on 404. The first read-only run (2026-11-09, `hardware-validation-2026-11-09.md`) graded them: `systemPressure` and `manualRoomSetpoint` answer 404 on the real gateway, the other standard points are readable.

| Key | Path | Confidence | Writable group |
|---|---|---|---|
| outdoor_temperature | system/sensors/temperatures/outdoor_t1 | homegate | |
| supply_temperature / return_temperature | heatSources/actualSupplyTemperature / returnTemperature | homegate | |
| modulation | heatSources/actualModulation | homegate | |
| pump_modulation / room_temperature / room_setpoint | heatingCircuits/hc1/pumpModulation / roomtemperature / currentRoomSetpoint | homegate | |
| dhw_temperature / dhw_setpoint | dhwCircuits/dhw1/actualTemp / currentSetpoint | homegate | |
| number_of_starts / system_pressure / power_setpoint | heatSources/numberOfStarts / systemPressure / powerSetpoint | standard | |
| dhw_charge | dhwCircuits/dhw1/charge (`start`/`stop`) | homegate (read + write) | extra_hot_water |
| dhw_operation_mode | dhwCircuits/dhw1/operationMode | standard | hot_water |
| dhw_temperature_high | dhwCircuits/dhw1/temperatureLevels/high | standard | hot_water |
| heating_operation_mode | heatingCircuits/hc1/operationMode | homegate (read) | heating |
| heating_manual_setpoint | heatingCircuits/hc1/manualRoomSetpoint | standard | heating |
| total/compressor/eheater_energy | recordings/heatSources/total/energyMonitoring/consumedEnergy / compressor / eheater | homegate | |
| heat_output_energy | recordings/heatSources/total/energyMonitoring/outputProduced | standard (referenced in the old notes) | |

Not used on purpose: the lifetime `heatSources/energyMonitoring/consumption` (unit unverified; the
Energy dashboard uses the hourly sensors), cooling, solar, pool, smart grid and time programs.

## Sampling

- State: every poll (default 120 s), paced 0.5 s per request. Points that return 404 on the first
  cycle are dropped from the plan.
- Energy: once per completed hour. Target hour = start of the newest hour that ended ≥ 5 min ago.
  An hour without a sample is asked for up to 3 times, then left until the next hour.
