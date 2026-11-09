from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bosch_compress6000.const import (
    CONF_WRITE_ENABLED,
    CONF_WRITE_GROUPS,
    DOMAIN,
)

from ..fakes import REC, FakeGateway, hourly
from .conftest import make_entry

LEGACY_ENTITY_IDS = {
    "bosch_energymonitoring_total": "sensor.bosch_total_consumed_energy_kwh",
    "bosch_energymonitoring_compressor": "sensor.bosch_compressor_consumed_energy_kwh",
    "bosch_energymonitoring_eheater": "sensor.bosch_eheater_consumed_energy_kwh",
    "bosch_outdoor_temperature": "sensor.heatpump_outdoor_temperature",
}


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_legacy_entity_ids_and_unique_ids_are_preserved(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    registry = er.async_get(hass)
    for unique_id, entity_id in LEGACY_ENTITY_IDS.items():
        found = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert found == entity_id, unique_id
    assert hass.states.get("sensor.heatpump_outdoor_temperature").state == "4.3"


async def test_energy_sensors_keep_the_energy_dashboard_contract(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    state = hass.states.get("sensor.bosch_compressor_consumed_energy_kwh")
    assert state is not None and state.state == "1.2"
    assert state.attributes["device_class"] == "energy"
    assert state.attributes["state_class"] == "total"  # total + last_reset, never total_increasing
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert datetime.fromisoformat(state.attributes["last_reset"]) == datetime(
        2026, 11, 9, 14, tzinfo=UTC
    )
    assert hass.states.get("sensor.bosch_total_consumed_energy_kwh").state == "1.5"
    assert hass.states.get("sensor.bosch_eheater_consumed_energy_kwh").state == "0.3"


async def test_an_hour_without_data_is_unknown_not_zero(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    gateway.recordings[REC + "eheater"] = hourly({})
    await setup(hass, entry)
    assert hass.states.get("sensor.bosch_eheater_consumed_energy_kwh").state == STATE_UNKNOWN
    assert hass.states.get("sensor.bosch_total_consumed_energy_kwh").state == "1.5"


async def test_the_device_groups_all_entities(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "test-gateway-uuid")})
    assert device is not None
    assert (device.name, device.manufacturer, device.model) == ("heatpump", "Bosch", "Compress6000")
    entities = er.async_entries_for_device(er.async_get(hass), device.id)
    assert {e.entity_id for e in entities} >= set(LEGACY_ENTITY_IDS.values())


async def test_old_mqtt_registry_entries_are_taken_over(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    registry = er.async_get(hass)
    for unique_id, entity_id in LEGACY_ENTITY_IDS.items():
        domain, object_id = entity_id.split(".")
        registry.async_get_or_create(domain, "mqtt", unique_id, suggested_object_id=object_id)
    await setup(hass, entry)
    for unique_id, entity_id in LEGACY_ENTITY_IDS.items():
        claimed = registry.async_get(entity_id)
        assert claimed is not None and claimed.platform == DOMAIN
        assert claimed.unique_id == unique_id  # statistics follow the entity ID
        assert claimed.config_entry_id == entry.entry_id
        assert hass.states.get(entity_id).state != STATE_UNKNOWN or "energy" in entity_id
    assert registry.async_get_entity_id("sensor", "mqtt", "bosch_outdoor_temperature") is None


async def test_claiming_can_be_turned_off(hass: HomeAssistant, gateway: FakeGateway) -> None:
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        "mqtt",
        "bosch_outdoor_temperature",
        suggested_object_id="heatpump_outdoor_temperature",
    )
    await setup(hass, make_entry(claim_legacy_entities=False))
    old = registry.async_get_entity_id("sensor", "mqtt", "bosch_outdoor_temperature")
    assert old == "sensor.heatpump_outdoor_temperature"


async def test_setup_and_polling_make_zero_writes(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    coordinator = entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await coordinator.async_refresh()
    assert gateway.posts == []
    assert entry.runtime_data.executor is None


async def test_points_missing_on_this_gateway_get_no_entity(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    ids = {
        e.entity_id for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    }
    assert not any("power_setpoint" in entity_id for entity_id in ids)
    assert hass.states.get("sensor.heatpump_supply_temperature").state == "32.1"
    assert hass.states.get("sensor.heatpump_system_pressure").state == "1.6"


async def test_writing_is_refused_while_write_mode_is_off(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.heatpump_extra_hot_water"}, blocking=True
        )
    assert gateway.posts == []


async def test_extra_hot_water_is_written_once_after_the_debounce_and_read_back(
    hass: HomeAssistant, gateway: FakeGateway
) -> None:
    entry = make_entry(**{CONF_WRITE_ENABLED: True, CONF_WRITE_GROUPS: ["extra_hot_water"]})
    await setup(hass, entry)
    assert hass.states.get("switch.heatpump_extra_hot_water").state == STATE_OFF
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.heatpump_extra_hot_water"}, blocking=True
    )
    assert gateway.posts == []  # debounced
    assert hass.states.get("switch.heatpump_extra_hot_water").state == STATE_ON  # optimistic
    await asyncio.sleep(0.3)
    await hass.async_block_till_done()
    assert gateway.posts == [("dhwCircuits/dhw1/charge", "start")]
    assert hass.states.get("switch.heatpump_extra_hot_water").state == STATE_ON  # read back


async def test_a_group_that_is_not_enabled_stays_read_only(
    hass: HomeAssistant, gateway: FakeGateway
) -> None:
    entry = make_entry(**{CONF_WRITE_ENABLED: True, CONF_WRITE_GROUPS: ["extra_hot_water"]})
    await setup(hass, entry)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.heatpump_hot_water_target_temperature", "value": 50},
            blocking=True,
        )
    assert gateway.posts == []


async def test_number_and_select_write_within_device_limits(
    hass: HomeAssistant, gateway: FakeGateway
) -> None:
    entry = make_entry(**{CONF_WRITE_ENABLED: True, CONF_WRITE_GROUPS: ["hot_water", "heating"]})
    await setup(hass, entry)
    state = hass.states.get("number.heatpump_hot_water_target_temperature")
    assert (state.attributes["min"], state.attributes["max"]) == (40.0, 65.0)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.heatpump_hot_water_target_temperature", "value": 70},
            blocking=True,
        )
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.heatpump_hot_water_target_temperature", "value": 52.5},
        blocking=True,
    )
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.heatpump_heating_mode", "option": "manual"},
        blocking=True,
    )
    await asyncio.sleep(0.4)
    await hass.async_block_till_done()
    assert sorted(gateway.posts) == [
        ("dhwCircuits/dhw1/temperatureLevels/high", 52.5),
        ("heatingCircuits/hc1/operationMode", "manual"),
    ]
    assert hass.states.get("select.heatpump_heating_mode").state == "manual"


async def test_unreachable_gateway_retries_setup(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    gateway.offline = True
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_wrong_password_starts_reauth(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    gateway.key = b"\x01" * 32
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert any(
        flow["context"]["source"] == "reauth" for flow in hass.config_entries.flow.async_progress()
    )


async def test_unload_and_reload(hass: HomeAssistant, gateway: FakeGateway) -> None:
    entry = make_entry(**{CONF_WRITE_ENABLED: True, CONF_WRITE_GROUPS: ["extra_hot_water"]})
    await setup(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert gateway.posts == []
