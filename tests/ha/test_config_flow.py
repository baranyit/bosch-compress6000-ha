from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bosch_compress6000.const import (
    CONF_GATEWAY_PASSWORD,
    CONF_PRIVATE_PASSWORD,
    CONF_WRITE_ENABLED,
    CONF_WRITE_GROUPS,
    DOMAIN,
)

from ..fakes import GATEWAY_PASSWORD, PRIVATE_PASSWORD, FakeGateway
from .conftest import HOST

USER_INPUT = {
    CONF_NAME: "heatpump",
    CONF_HOST: HOST,
    CONF_GATEWAY_PASSWORD: "AAAA-BBBB-CCCC-DDDD",
    CONF_PRIVATE_PASSWORD: PRIVATE_PASSWORD,
}


async def start(hass: HomeAssistant) -> str:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    return str(result["flow_id"])


async def test_user_flow_creates_a_read_only_entry(
    hass: HomeAssistant, gateway: FakeGateway
) -> None:
    result = await hass.config_entries.flow.async_configure(await start(hass), USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_GATEWAY_PASSWORD] == GATEWAY_PASSWORD  # dashes removed
    assert result["result"].unique_id == "test-gateway-uuid"
    assert result["options"][CONF_WRITE_ENABLED] is False
    assert result["options"][CONF_WRITE_GROUPS] == []
    assert gateway.posts == []


async def test_wrong_password_and_unreachable_gateway(
    hass: HomeAssistant, gateway: FakeGateway
) -> None:
    gateway.key = b"\x02" * 32
    result = await hass.config_entries.flow.async_configure(await start(hass), USER_INPUT)
    assert result["errors"] == {"base": "invalid_auth"}
    gateway.key = FakeGateway().key
    gateway.offline = True
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "cannot_connect"}
    gateway.offline = False
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_the_same_gateway_cannot_be_added_twice(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_configure(await start(hass), USER_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_require_a_group_when_writing_is_on(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    base = {"poll_interval": 120}
    bad = await hass.config_entries.options.async_configure(
        flow["flow_id"], {**base, CONF_WRITE_ENABLED: True, CONF_WRITE_GROUPS: []}
    )
    assert bad["errors"] == {CONF_WRITE_GROUPS: "no_group_selected"}
    ok = await hass.config_entries.options.async_configure(
        flow["flow_id"],
        {**base, CONF_WRITE_ENABLED: True, CONF_WRITE_GROUPS: ["extra_hot_water"]},
    )
    assert ok["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


async def test_reauth_updates_the_passwords(
    hass: HomeAssistant, gateway: FakeGateway, entry: MockConfigEntry
) -> None:
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    done = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_GATEWAY_PASSWORD: GATEWAY_PASSWORD, CONF_PRIVATE_PASSWORD: PRIVATE_PASSWORD},
    )
    assert done["type"] is FlowResultType.ABORT and done["reason"] == "reauth_successful"
    _ = config_entries
