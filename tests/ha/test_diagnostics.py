from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bosch_compress6000.diagnostics import async_get_config_entry_diagnostics

from ..fakes import GATEWAY_PASSWORD, PRIVATE_PASSWORD, FakeGateway
from .conftest import HOST


async def test_diagnostics_redact_secrets_and_the_host(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    text = str(diagnostics)
    for secret in (GATEWAY_PASSWORD, PRIVATE_PASSWORD, HOST):
        assert secret not in text
    assert diagnostics["readings"]["outdoor_temperature"]["value"] == 4.3
    assert diagnostics["write"]["enabled"] is False
