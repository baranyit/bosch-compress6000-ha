"""Claim the entities of an earlier MQTT-based setup, so history and Energy continue.

Entity IDs, unique IDs and the device are fixed for these four sensors::

    sensor.bosch_total_consumed_energy_kwh       bosch_energymonitoring_total
    sensor.bosch_compressor_consumed_energy_kwh  bosch_energymonitoring_compressor
    sensor.bosch_eheater_consumed_energy_kwh     bosch_energymonitoring_eheater
    sensor.heatpump_outdoor_temperature          bosch_outdoor_temperature

The entity registry maps (platform, unique_id) to an entity_id. The old MQTT entries carry the same
unique IDs this integration uses, so a plain new integration would get ``_2`` IDs and split the
statistics. They are re-pointed to this integration through the registry API (never by editing
``.storage``), keeping entity ID, name and statistics, and moved to the new device.

Cut-over order: remove the MQTT YAML definitions first (otherwise MQTT and this integration both
claim the unique IDs; the YAML entity then loses its duplicate), then add the integration. Hours
between the old setup stopping and the first read here are not back-filled.
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
