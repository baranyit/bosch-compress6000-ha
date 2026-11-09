# Hardware write test: extra hot water (2026-11-09)

Approved by the maintainer in chat for exactly this: one `start`, observe, `stop`.
`tests/hardware/test_write_validation.py`, run once, about 41 s, through the integration's own
write transport (validated command, shared lock and limiter), nothing else written.

| Step | `dhwCircuits/dhw1/charge` |
|---|---|
| before | `stop` |
| POST `start`, read +5 s / +10 s / +15 s | `start` / `start` / `start` |
| POST `stop`, read +3 s | `stop` (restored) |

Result: the encrypted POST format works, the gateway accepts `start` and `stop` and reflects them on
the next read. State restored. The cycle ended `stop` in the `finally` block by design.

Not verified: that the heat pump really started heating (no metric was watched), how long a
`start` runs when not stopped, behaviour of the other four writable points (`hot_water`, `heating`
groups: still untested, each needs its own approval), and the Home Assistant write path
(switch, debounce, read-back) against the real gateway.
