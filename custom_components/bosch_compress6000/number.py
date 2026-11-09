"""Remote settings (numbers). Each needs its write opt-in; limits come from the gateway."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import Km200ConfigEntry
from .entity import Km200Entity

NUMBERS: tuple[NumberEntityDescription, ...] = tuple(
    NumberEntityDescription(
        key=key,
        translation_key=key,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=0.5,
    )
    for key in ("dhw_temperature_high", "heating_manual_setpoint")
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Km200ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    readings = entry.runtime_data.coordinator.data.readings
    async_add_entities(
        SettingNumber(entry, description)
        for description in NUMBERS
        if (reading := readings.get(description.key)) is not None
        and reading.writeable
        and not isinstance(reading.value, str)
    )


class SettingNumber(Km200Entity, NumberEntity):
    def __init__(self, entry: Km200ConfigEntry, description: NumberEntityDescription) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        shown = self.coordinator.optimistic(self._key)
        if isinstance(shown, float | int):
            return float(shown)
        reading = self.reading
        if reading is None or isinstance(reading.value, str):
            return None
        return reading.value

    @property
    def native_min_value(self) -> float:
        reading = self.reading
        return reading.minimum if reading and reading.minimum is not None else 5.0

    @property
    def native_max_value(self) -> float:
        reading = self.reading
        return reading.maximum if reading and reading.maximum is not None else 80.0

    async def async_set_native_value(self, value: float) -> None:
        self.submit(value)
