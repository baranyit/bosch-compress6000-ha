"""Bosch Compress 6000 integration for Home Assistant (local KM200 gateway, no cloud, no MQTT).

Read-only by default. Setup, polling, reload, diagnostics and unload never write. Only with write
mode enabled in the options, for explicitly selected groups, a command a user asked for is written
once after a debounce and confirmed by one read-back. The protocol core (``protocol``, ``crypto``,
``models``, ``errors``, ``transport``, ``client``, ``commands``, ``runtime``, ...) stays free of
Home Assistant imports.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import Km200ReadClient
from .commands import CommandExecutor, CommandPermissions
from .const import (
    COMMAND_DEBOUNCE,
    CONF_CLAIM_LEGACY,
    CONF_GATEWAY_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_PRIVATE_PASSWORD,
    CONF_WRITE_ENABLED,
    CONF_WRITE_GROUPS,
    DEFAULT_POLL_INTERVAL,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    DOMAIN,
)
from .coordinator import Km200Coordinator
from .migration import async_claim_legacy_entities
from .protocol import POINTS, WriteGroup
from .runtime import build_client, build_writable_client
from .write_transport import WritableTransport

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.SELECT]


@dataclass(slots=True)
class Km200RuntimeData:
    coordinator: Km200Coordinator
    client: Km200ReadClient
    executor: CommandExecutor | None


type Km200ConfigEntry = ConfigEntry[Km200RuntimeData]


def device_identifier(entry: ConfigEntry[Any]) -> tuple[str, str]:
    return (DOMAIN, entry.unique_id or entry.entry_id)


def permissions_from_options(options: Mapping[str, Any]) -> CommandPermissions:
    groups: set[WriteGroup] = set()
    for item in options.get(CONF_WRITE_GROUPS) or []:
        try:
            groups.add(WriteGroup(item))
        except ValueError:
            continue
    return CommandPermissions(bool(options.get(CONF_WRITE_ENABLED, False)), frozenset(groups))


async def async_setup_entry(hass: HomeAssistant, entry: Km200ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    host: str = entry.data[CONF_HOST]
    gateway_password: str = entry.data[CONF_GATEWAY_PASSWORD]
    private_password: str = entry.data[CONF_PRIVATE_PASSWORD]
    permissions = permissions_from_options(entry.options)
    writable = permissions.write_enabled and bool(permissions.groups)

    transport: WritableTransport | None = None
    if writable:
        transport, client = build_writable_client(session, host, gateway_password, private_password)
    else:
        client = build_client(session, host, gateway_password, private_password)

    interval = int(entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))
    coordinator = Km200Coordinator(hass, entry, client, interval)
    await coordinator.async_config_entry_first_refresh()

    executor: CommandExecutor | None = None
    if transport is not None:
        executor = CommandExecutor(
            transport,
            permissions,
            debounce=COMMAND_DEBOUNCE,
            read_back=coordinator.read_back,
            on_change=coordinator.async_update_listeners,
        )
        coordinator.executor = executor
    entry.runtime_data = Km200RuntimeData(coordinator, client, executor)

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={device_identifier(entry)},
        manufacturer=DEVICE_MANUFACTURER,
        model=DEVICE_MODEL,
        name=entry.data[CONF_NAME],
    )
    if entry.options.get(CONF_CLAIM_LEGACY, True):
        async_claim_legacy_entities(hass, entry, device.id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Km200ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        if entry.runtime_data.executor is not None:
            await entry.runtime_data.executor.close()
        await entry.runtime_data.coordinator.async_shutdown()
    return unloaded


__all__ = ["POINTS", "Km200ConfigEntry", "Km200RuntimeData", "async_setup_entry"]
