# AGENTS.md — Bosch Compress 6000 Home Assistant integration

Guidance for AI coding agents (Claude Code, Codex, Copilot, Cursor, etc.). The project is in
**maintenance mode**: it is released software with users and history, not a prototype. The code and its
docstrings are the documentation (protocol and field facts: `protocol.py`; crypto: `crypto.py`;
entity migration: `migration.py`). There is no `docs/` folder; keep knowledge in code, tests, this file
and `README.md`. Chat with the maintainer is in **Hungarian**; everything committed is in **English**
(Hungarian only in `translations/hu.json`).

## What it is

A native async Home Assistant integration for a Bosch Compress 6000 heat pump behind a Bosch/Buderus
**KM200-family gateway** (local encrypted HTTP, no cloud, no MQTT): metrics, hourly energy, and an
opt-in remote control (extra hot water, hot water and heating settings). The gateway is a small
embedded web server, so it is treated as **fragile**: serialized, spaced requests, and no write unless a
user asked.

## Invariants (a change that breaks one is rejected even if tests pass)

1. **Four legacy entities are frozen**: entity IDs, unique IDs, names and device (see `migration.py`).
   Changing them splits users' history and Energy statistics.
2. **Energy contract**: `state_class: total` + `last_reset` (start of the completed hour) +
   `force_update`. Never `total_increasing`. An hour with `c == 0` is *no sample*, never 0.0: the
   previous sample stays and the state is unknown before the first one.
3. **No automatic writes.** Setup, polling, reload, reconnect, diagnostics and unload make zero POSTs.
   A write exists only because a user used a switch/number/select.
4. **Write mode is off by default**, with separate group opt-ins (`extra_hot_water`, `hot_water`,
   `heating`). Only catalog points with a `group` can be written, and the device's own `writeable`,
   `allowedValues`, `minValue`, `maxValue` must agree. Writes are debounced, latest-value-wins, one
   per point, followed by one read-back. No retries, no replay; unwritten commands are dropped on unload.
5. **Never silently round or guess**: out-of-range or unknown values are rejected before any request.
6. **One lock and one limiter per gateway**, shared by reads and writes; request starts are spaced
   (`REQUEST_SPACING`); the poll interval has a derived minimum. Do not raise the rate without
   hardware evidence. Energy recordings are read once per completed hour, not every poll.
7. **Failure isolation**: a failing point is absent (entity unavailable) while others keep working;
   a wrong key is not isolated, it triggers reauth (`ConfigEntryAuthFailed`).
8. **No secrets** in the repository, logs, diagnostics or tests (diagnostics redact host and
   passwords; test credentials are obvious fakes). Real credentials live only in the HA config entry.

## Layout

```
custom_components/bosch_compress6000/
  errors.py const.py crypto.py models.py protocol.py   pure core (no homeassistant imports)
  transport.py client.py http_backend.py               READ path (never references writes)
  write_transport.py write_backend.py commands.py      the ONLY write route
  runtime.py                                           client/transport factories
  coordinator.py entity.py sensor.py switch.py number.py select.py
  config_flow.py diagnostics.py migration.py __init__.py   Home Assistant layer
  brand/ strings.json translations/{en,hu}.json
tests/        unit + HA tests on tests/fakes.py; tests/hardware is opt-in, never in CI
assets/       logo masters (the brand/ PNGs are resized from them)
```

`tests/test_architecture.py` enforces: core modules are HA-free; the read path has no write references
or imports; only the write layer can POST.

## Working on it

- Adding a point: add it to the catalog in `protocol.py` (read-only unless it needs a write group and a
  hardware-approved test), an entity description, en + hu strings, and a `FakeGateway` entry. New
  entities use unique ID `bosch_<key>`. Standard-confidence points are probed and skipped on 404.
- Keep `strings.json` and `translations/en.json` identical; every key needs a Hungarian translation.
- Update `README.md` and docstrings in the same change as the behaviour.

## Quality gates (all clean before proposing a change)

Set up once: `uv venv -p 3.13 && uv pip install -e ".[dev]" -C editable_mode=compat`, then
`source .venv/bin/activate`.

```
python -m pytest
ruff check . && ruff format --check .
mypy            # strict, custom_components only
```

CI also runs hassfest and HACS validation (the manifest must not list requirements that Home Assistant
itself provides, e.g. `cryptography`, `aiohttp`). Tests use `FakeGateway` (real encrypted wire format)
and `VirtualClock` (never sleeps); real sleeps stay below 0.5 s.

## Hardware

- **Never connect to the real gateway directly** (no ad-hoc curl or scripts, read-only included).
- A run against it goes only through the integration's own transport, write mode off, one at a time,
  on the maintainer's request: `tests/hardware`, credentials from environment variables
  (`BOSCH_HW_HOST`, `BOSCH_HW_GATEWAY_PASSWORD`, `BOSCH_HW_PRIVATE_PASSWORD`), never from the repo.
- Any hardware write needs separate human approval and a recovery plan (one point, observe, restore);
  `tests/hardware/test_write_validation.py` is the pattern and also needs `BOSCH_HW_WRITE_OK=1`.
- Validated so far: reads, hourly recordings and one extra hot water start/stop (details in
  `protocol.py`). Writes to the hot water and heating points are untested on hardware.

## Versioning and releases

Semantic versioning; every merge to `main` raises the version in the same PR, in four places:
`manifest.json`, `pyproject.toml`, the README status line `(X.Y.Z,` and the top `CHANGELOG.md`
section (`tests/test_version.py` fails when they disagree). While `0.x`, a breaking change (changed
entity/unique ID, option or meaning) raises **minor**; fixes and no-behaviour changes raise **patch**.
Tags, GitHub releases and HACS submission are the maintainer's explicit step.
