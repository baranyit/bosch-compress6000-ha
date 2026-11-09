"""Extra hot water: start or stop one DHW charge. Needs the ``extra_hot_water`` write opt-in."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import Km200ConfigEntry
from .entity import Km200Entity
from .protocol import CHARGE_START, CHARGE_STOP

KEY = "dhw_charge"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Km200ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    reading = entry.runtime_data.coordinator.data.readings.get(KEY)
    if reading is not None and reading.writeable:
        async_add_entities([ExtraHotWaterSwitch(entry)])


class ExtraHotWaterSwitch(Km200Entity, SwitchEntity):
    _attr_translation_key = KEY

    def __init__(self, entry: Km200ConfigEntry) -> None:
        super().__init__(entry, KEY)

    @property
    def is_on(self) -> bool | None:
        shown = self.coordinator.optimistic(KEY)
        value = shown if shown is not None else (self.reading.value if self.reading else None)
        return None if value is None else value == CHARGE_START

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.submit(CHARGE_START)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.submit(CHARGE_STOP)
