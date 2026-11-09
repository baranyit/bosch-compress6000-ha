"""Redacted diagnostics. Passwords and the host never appear."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from . import Km200ConfigEntry
from .const import CONF_GATEWAY_PASSWORD, CONF_PRIVATE_PASSWORD

TO_REDACT = {CONF_HOST, CONF_GATEWAY_PASSWORD, CONF_PRIVATE_PASSWORD, "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: Km200ConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data.coordinator
    executor = entry.runtime_data.executor
    snapshot = coordinator.data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "poll_interval_s": coordinator.update_interval.total_seconds()
        if coordinator.update_interval
        else None,
        "requests_started": entry.runtime_data.client.transport.requests_started,
        "readings": {
            key: {
                "value": reading.value,
                "unit": reading.unit,
                "writeable": reading.writeable,
                "allowed": list(reading.allowed),
                "min": reading.minimum,
                "max": reading.maximum,
            }
            for key, reading in (snapshot.readings if snapshot else {}).items()
        },
        "energy": {
            key: {"value": sample.value, "hour_start": sample.hour_start.isoformat()}
            for key, sample in (snapshot.energy if snapshot else {}).items()
        },
        "failed": list(snapshot.failed) if snapshot else [],
        "missing": list(snapshot.missing) if snapshot else [],
        "write": {
            "enabled": executor is not None,
            "writes_sent": executor.writes_sent if executor else 0,
            "errors": list(executor.errors) if executor else [],
        },
    }
