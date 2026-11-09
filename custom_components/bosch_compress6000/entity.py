"""Base entity. Properties read the coordinator snapshot only; no I/O."""

from __future__ import annotations

from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import Km200ConfigEntry, device_identifier
from .const import DEVICE_MANUFACTURER, DEVICE_MODEL, DOMAIN, LEGACY_MQTT_UNIQUE_IDS
from .coordinator import Km200Coordinator
from .errors import CommandRejectedError
from .models import Reading


def unique_id_for(key: str) -> str:
    """Legacy IDs are kept; everything new is ``bosch_<key>``."""
    return LEGACY_MQTT_UNIQUE_IDS.get(key, f"bosch_{key}")


class Km200Entity(CoordinatorEntity[Km200Coordinator]):
    _attr_has_entity_name = True

    def __init__(self, entry: Km200ConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._key = key
        self._attr_unique_id = unique_id_for(key)
        self._attr_device_info = DeviceInfo(
            identifiers={device_identifier(entry)},
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
            name=entry.title,
        )

    @property
    def reading(self) -> Reading | None:
        data = self.coordinator.data
        return data.readings.get(self._key) if data else None

    @property
    def available(self) -> bool:
        return super().available and self.reading is not None

    def submit(self, value: float | str) -> None:
        """Queue a user command, turning a refusal into a visible error."""
        try:
            self.coordinator.submit(self._key, value)
        except CommandRejectedError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="command_rejected",
                translation_placeholders={"reason": str(err)},
            ) from err
