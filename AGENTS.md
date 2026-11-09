# AGENTS.md — Bosch Compress 6000 Home Assistant integration

Guidance for AI coding agents (Claude Code, Codex, Copilot, Cursor, etc.) working in this repository.
Read this file fully before making changes. When this file and `docs/` disagree, **`docs/` wins** — then fix this file.

## 1. Project in one paragraph

A native async Python Home Assistant integration for a Bosch Compress 6000 heat pump behind a
Bosch/Buderus **KM200-family gateway** (local encrypted HTTP; no cloud, Java or MQTT). It replaces the
Bosch part of the retired HomeGate bridge (`homegate/bosch/*` MQTT topics) and **keeps its entity IDs,
unique IDs and Energy-dashboard behaviour**. The gateway is a small embedded web server: it is treated
as **fragile**, so requests are serialized and spaced, and **no write may happen unless a user asked**.

## 2. Current status

- **Done (code, mock-tested, not hardware-tested):** crypto + point catalog + read client, hourly
  energy, coordinator, sensors, config/reauth/reconfigure/options flows, legacy MQTT entity takeover,
  diagnostics, en/hu translations, off-by-default write layer (extra hot water switch, hot water and
  heating settings), CI (ruff, mypy strict, pytest, hassfest, HACS).
- **Hardware:** first read-only run done 2026-11-09 (`docs/hardware-validation-2026-11-09.md`).
- **Hardware write test passed** for the extra hot water start/stop (`docs/hardware-write-test-2026-11-09.md`). Other writable points are untested; each needs its own approval.
- **Not done:** hot water / heating write checks on hardware (see
  `docs/02-protocol-specification.md`), any hardware write test, removal of `mqtt/sensors/bosch.yaml`
  in the HA config repo (a separate change, only on request).

## 3. Source of truth (`docs/`)

| File | Use it for |
|---|---|
| `docs/01-source-analysis.md` | What was learned from HomeGate and its defects |
| `docs/02-protocol-specification.md` | Wire format, crypto, endpoint catalog and confidence levels |
| `docs/03-migration.md` | Entity ID/unique ID preservation, statistics, cut-over steps |
| `docs/open-decisions.md` | Open questions and decisions |

## 4. Non-negotiable safety rules

1. **No automatic writes.** Setup, polling, reload, reconnect, diagnostics and unload make **zero**
   POSTs. A write exists only because a user asked (switch/number/select), after a debounce, once.
2. **Write mode is off by default**, with separate group opt-ins (`extra_hot_water`, `hot_water`,
   `heating`). Only catalog points with a `group` can ever be written; the device's own
   `writeable`, `allowedValues`, `minValue`, `maxValue` must agree.
3. **Debounce, latest-value-wins, one write per point, one read-back** of that point afterwards.
   Unwritten commands are dropped on unload and never replayed. Failed writes are not retried.
4. **Never silently round or guess.** Out-of-range or unknown values are rejected before any request.
5. **An hour without data is never 0.0.** `c == 0` means "no sample"; the previous sample stays.
6. **Never change `state_class`/`last_reset` of the energy sensors.** `total` + `last_reset` (start of
   the completed hour) is what the existing statistics expect; switching to `total_increasing` splits them.
7. **Entity IDs and unique IDs of the four legacy entities are fixed** (see `docs/03-migration.md`).
8. **No secrets in the repository**, logs, diagnostics or tests. Test credentials are obvious fakes.
   Real passwords stay in the HA config entry. (Passwords of the real gateway exist in plain text in
   the retired HomeGate project; never copy them here.)

## 5. Transport rules

- One config entry = one gateway = one lock and one limiter shared by reads and writes.
- Request starts are spaced (`REQUEST_SPACING`, 0.5 s); the poll interval has a derived minimum
  (`ceil(requests × spacing × 1.5)`); default 120 s. Do not raise the rate without hardware evidence.
- Per-point failure isolation: a failing point is absent from the snapshot (entity unavailable),
  other points keep working. A wrong key is **not** isolated: it raises `ConfigEntryAuthFailed` (reauth).
- Energy recordings are read once per completed hour (grace 5 min), not every poll.

## 6. Architecture and layout

```
custom_components/bosch_compress6000/
  errors.py const.py crypto.py models.py protocol.py   pure core (no homeassistant imports)
  transport.py client.py http_backend.py               READ path (never references writes)
  write_transport.py write_backend.py commands.py      the ONLY write route
  runtime.py                                           client/transport factories
  coordinator.py entity.py sensor.py switch.py number.py select.py
  config_flow.py diagnostics.py migration.py __init__.py   Home Assistant layer
```

`tests/test_architecture.py` enforces: core modules are HA-free; the read path has no write
references or imports; only the write layer can POST.

## 7. Coding conventions

- Chat with the maintainer is in **Hungarian**. Everything committed (code, docs, commit messages,
  PRs) is in **English**; Hungarian only in `translations/hu.json`.
- Fully async, type-hinted (strict mypy), ruff-formatted. Immutable snapshots.
- User-facing strings: English primary, Hungarian required for every key.
- Keep docs in sync in the same change.

## 8. Quality gates (all must be clean before proposing a change)

Set up once: `uv venv -p 3.13 && uv pip install -e ".[dev]" -C editable_mode=compat`, then `source .venv/bin/activate`.

```
python -m pytest
ruff check . && ruff format --check .
mypy
```

CI additionally runs hassfest and HACS validation. Tests use `tests/fakes.py` (`FakeGateway` speaks the
real encrypted wire format, `VirtualClock` never sleeps). Real-time sleeps in tests stay below 0.5 s.

## 9. Hardware

- **Agents must never connect to the real gateway directly** (no ad-hoc curl/scripts, read-only included).
- Integration test runs may reach it only through the integration's own transport, write mode off,
  one run at a time, on the maintainer's request (`tests/hardware`, opt-in via environment variables).
- Any hardware write needs separate human approval and a recovery plan (one point, observe, restore).

## 10. Versioning

Semantic versioning; every merge to `main` raises the version in the same PR, in four places:
`manifest.json`, `pyproject.toml`, the README status line `(X.Y.Z,` and the top CHANGELOG section.
`tests/test_version.py` fails when they disagree. While `0.x`, a breaking change raises **minor**.
Tags, releases and HACS submission stay the maintainer's explicit step.

## 11. Clean-room rule

HomeGate (Java) is **evidence, not a template**: re-derive behaviour from `docs/`. Do not reintroduce
its defects: 0.0 for missing hours, secrets in scripts, unbounded request bursts, fire-and-forget
writes, swallowed errors.
