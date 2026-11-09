"""Sensors: live metrics and the hourly energy consumption."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import Km200ConfigEntry
from .entity import Km200Entity
from .protocol import ENERGY_POINTS


def _temperature(key: str) -> SensorEntityDescription:
    return SensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    )


def _percentage(key: str) -> SensorEntityDescription:
    return SensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    )


STATE_SENSORS: tuple[SensorEntityDescription, ...] = (
    _temperature("outdoor_temperature"),
    _temperature("supply_temperature"),
    _temperature("return_temperature"),
    _temperature("room_temperature"),
    _temperature("room_setpoint"),
    _temperature("dhw_temperature"),
    _temperature("dhw_setpoint"),
    _percentage("modulation"),
    _percentage("pump_modulation"),
    SensorEntityDescription(
        key="number_of_starts",
        translation_key="number_of_starts",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="system_pressure",
        translation_key="system_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key="power_setpoint",
        translation_key="power_setpoint",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

# The three consumption sensors keep the names of the retired MQTT entities, so their entity IDs
# (sensor.bosch_total_consumed_energy_kwh, ...) and statistics continue unchanged.
LEGACY_ENERGY_NAMES = {
    "total_energy": "Bosch total consumed energy (kwh)",
    "compressor_energy": "Bosch compressor consumed energy (kwh)",
    "eheater_energy": "Bosch eheater consumed energy (kwh)",
}


@dataclass(frozen=True, kw_only=True)
class EnergyDescription(SensorEntityDescription):
    legacy_name: str | None = None


ENERGY_SENSORS: tuple[EnergyDescription, ...] = tuple(
    EnergyDescription(
        key=point.key,
        translation_key=point.key,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        legacy_name=LEGACY_ENERGY_NAMES.get(point.key),
    )
    for point in ENERGY_POINTS
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Km200ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    snapshot = entry.runtime_data.coordinator.data
    entities: list[SensorEntity] = [
        StateSensor(entry, description)
        for description in STATE_SENSORS
        if description.key in snapshot.readings
    ]
    entities.extend(EnergySensor(entry, description) for description in ENERGY_SENSORS)
    async_add_entities(entities)


class StateSensor(Km200Entity, SensorEntity):
    def __init__(self, entry: Km200ConfigEntry, description: SensorEntityDescription) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        reading = self.reading
        if reading is None or isinstance(reading.value, str):
            return None
        return reading.value


class EnergySensor(Km200Entity, SensorEntity):
    """Consumption of the last completed hour.

    ``state_class`` stays ``total`` with ``last_reset`` = start of that hour, exactly like the
    retired MQTT sensors, so the Energy dashboard statistics are compatible. A missing hour never
    becomes 0.0: the previous sample stays until a newer one arrives.
    """

    _attr_force_update = True
    entity_description: EnergyDescription

    def __init__(self, entry: Km200ConfigEntry, description: EnergyDescription) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description
        if description.legacy_name is not None:
            self._attr_has_entity_name = False
            self._attr_name = description.legacy_name

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> float | None:
        sample = self.coordinator.data.energy.get(self._key)
        return sample.value if sample else None

    @property
    def last_reset(self) -> datetime | None:
        sample = self.coordinator.data.energy.get(self._key)
        return sample.hour_start if sample else None
