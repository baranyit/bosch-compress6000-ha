# Hardware validation, first read-only run (2026-11-09)

- What ran: `tests/hardware/test_read_validation.py` once, through the integration's own transport
  (0.5 s spacing, write mode off, zero POSTs), about 12 s, one run. The earlier attempt on the old
  address timed out on its first request.
- Passwords from the retired HomeGate setup decrypted the replies, so both passwords are valid.
- Result: 15 of 17 catalog points readable, 0 failed.

| Result | Points |
|---|---|
| Readable | outdoor, supply, return, modulation, pump modulation, room temperature, room setpoint, DHW temperature, DHW setpoint, number_of_starts, power_setpoint, dhw_charge, dhw_operation_mode, dhw_temperature_high, heating_operation_mode |
| 404 on this gateway (no entity is created) | system_pressure, heating_manual_setpoint |

## Not verified

Energy recordings (the run read state only), `writeable` flags, units and `allowedValues` of the
readable points (not printed), every write, and the effect of `dhw_charge`. Note that
`heating_manual_setpoint` is absent, so the heating select is the only heating control here.

## Second read-only run (same day): energy and point metadata

One run, ~11 s, zero POSTs. Hour read: the last completed hour.

- Energy recordings answer for all four points (hour values: total 2.0, compressor 2.0, eheater 0.0,
  heat output 9.0). The real eheater value is a genuine `0.0` (samples present), not a missing hour.
  Heat output / compressor is about 4.5, consistent with kWh for all of them.
- `writeable` is true exactly for the five catalog points that have a write group; all metrics are false.
- `dhw_charge` allowed: `stop`, `start`. `dhw_operation_mode` allowed: `Off`, `low`, `high`,
  `ownprogram`, `eco` (mixed case; used verbatim). `heating_operation_mode` allowed: `auto`, `manual`.
- `dhw_temperature_high` limits: 30.0 to 43.0 °C. Units: `C`, `%`, and a blank unit for the start counter.

## Still not verified

Any write, what `dhw_charge = start` actually does and for how long, and the day-boundary hours of
the recordings.
