"""Claim the entities of the retired HomeGate MQTT bridge, so history and Energy continue.

The entity registry maps (platform, unique_id) to an entity_id. The MQTT entries carry the same
unique IDs this integration uses, so they are re-pointed to this integration through the registry
API (never by editing ``.storage``). Their entity IDs, names and statistics stay. Run it after the
MQTT YAML definitions are gone; a definition that is still active simply loses its duplicate.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, LEGACY_MQTT_UNIQUE_IDS

_LOGGER = logging.getLogger(__name__)


@callback
def async_claim_legacy_entities(
    hass: HomeAssistant, entry: ConfigEntry[Any], device_id: str
) -> list[str]:
    """Re-point the old MQTT registry entries to this config entry; return their entity IDs."""
    registry = er.async_get(hass)
    claimed: list[str] = []
    for unique_id in LEGACY_MQTT_UNIQUE_IDS.values():
        entity_id = registry.async_get_entity_id(SENSOR_DOMAIN, "mqtt", unique_id)
        if entity_id is None:
            continue
        registry.async_update_entity_platform(
            entity_id,
            DOMAIN,
            new_config_entry_id=entry.entry_id,
            new_device_id=device_id,
        )
        claimed.append(entity_id)
        _LOGGER.info("Claimed legacy MQTT entity %s", entity_id)
    return claimed
