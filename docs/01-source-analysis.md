# Source analysis: the HomeGate Bosch bridge

Evidence only; HomeGate is not a template (AGENTS.md §11). Source: `homegate/src/main/java/hu/btnet/homegate/bosch`.

## What it did

- Polled the gateway over HTTP with `User-Agent: TeleHeater`, decrypted the replies (AES-256-ECB,
  base64) and published JSON to MQTT.
- `homegate/bosch/state` every 10 min: 11 floats/strings (outdoor, supply, return, modulation, room,
  pump modulation, DHW temperatures, `charge`, lifetime consumption).
- `homegate/bosch/consumption` at minute 5 of every hour: the previous hour of three daily
  recordings (`consumedEnergy`, `compressor`, `eheater`), `dateTime` = start of that hour.
- Subscribed to `homegate/bosch/water-pump` (`start`/`stop`) and POSTed `{"value": ...}` to
  `dhwCircuits/dhw1/charge` (the "extra hot water" function).

## Defects not to reproduce

| Defect | Here |
|---|---|
| Missing hour (`c == 0`) published as `0.0` | Hour without data stays `unknown`/previous sample (rule 5) |
| Secrets in a shell script in the repository | Passwords only in the HA config entry; redacted in diagnostics |
| ~11 requests back to back, no spacing | Serialized, spaced requests, derived minimum poll interval |
| Fire-and-forget write, no validation, no read-back | Opt-in groups, device limits, debounce, read-back |
| `catch`-and-rethrow loses the failing path | Typed errors, per-point isolation |
