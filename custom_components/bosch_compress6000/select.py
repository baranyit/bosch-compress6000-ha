"""Operation modes (selects). Options come from the gateway; each needs its write opt-in."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import Km200ConfigEntry
from .entity import Km200Entity

SELECTS: tuple[SelectEntityDescription, ...] = tuple(
    SelectEntityDescription(key=key, translation_key=key)
    for key in ("dhw_operation_mode", "heating_operation_mode")
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Km200ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    readings = entry.runtime_data.coordinator.data.readings
    async_add_entities(
        ModeSelect(entry, description)
        for description in SELECTS
        if (reading := readings.get(description.key)) is not None
        and reading.writeable
        and isinstance(reading.value, str)
    )


class ModeSelect(Km200Entity, SelectEntity):
    def __init__(self, entry: Km200ConfigEntry, description: SelectEntityDescription) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def options(self) -> list[str]:
        reading = self.reading
        return list(reading.allowed) if reading else []

    @property
    def current_option(self) -> str | None:
        shown = self.coordinator.optimistic(self._key)
        if isinstance(shown, str):
            return shown
        reading = self.reading
        return reading.value if reading and isinstance(reading.value, str) else None

    async def async_select_option(self, option: str) -> None:
        self.submit(option)
