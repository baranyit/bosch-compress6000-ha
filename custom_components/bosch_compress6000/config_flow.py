"""Config, reauth, reconfigure and options flows. Setup only reads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_GATEWAY_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_PRIVATE_PASSWORD,
    CONF_WRITE_ENABLED,
    CONF_WRITE_GROUPS,
    DEFAULT_NAME,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
)
from .crypto import normalize_gateway_password
from .errors import InvalidKeyError, Km200Error, TransportError
from .protocol import WriteGroup
from .runtime import build_client

if TYPE_CHECKING:
    from . import Km200ConfigEntry

PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, vol.UNDEFINED)): str,
            vol.Required(CONF_GATEWAY_PASSWORD): PASSWORD,
            vol.Required(CONF_PRIVATE_PASSWORD): PASSWORD,
        }
    )


class Km200ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _probe(self, data: Mapping[str, Any]) -> tuple[str | None, str | None]:
        """Return (stable unique id, error key). Read-only: two reads of the gateway."""
        client = build_client(
            async_get_clientsession(self.hass),
            data[CONF_HOST],
            data[CONF_GATEWAY_PASSWORD],
            data[CONF_PRIVATE_PASSWORD],
        )
        try:
            await client.probe()
            identity = await client.identity()
        except InvalidKeyError:
            return None, "invalid_auth"
        except TransportError:
            return None, "cannot_connect"
        except Km200Error:
            return None, "unknown"
        return identity or f"host_{data[CONF_HOST]}", None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                **user_input,
                CONF_GATEWAY_PASSWORD: normalize_gateway_password(
                    user_input[CONF_GATEWAY_PASSWORD]
                ),
            }
            unique_id, error = await self._probe(data)
            if error is None and unique_id is not None:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data[CONF_NAME],
                    data=data,
                    options={
                        CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
                        CONF_WRITE_ENABLED: False,
                        CONF_WRITE_GROUPS: [],
                    },
                )
            errors["base"] = error or "unknown"
        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input or {}), errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                **entry.data,
                CONF_GATEWAY_PASSWORD: normalize_gateway_password(
                    user_input[CONF_GATEWAY_PASSWORD]
                ),
                CONF_PRIVATE_PASSWORD: user_input[CONF_PRIVATE_PASSWORD],
            }
            _, error = await self._probe(data)
            if error is None:
                return self.async_update_reload_and_abort(entry, data=data)
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_GATEWAY_PASSWORD): PASSWORD,
                    vol.Required(CONF_PRIVATE_PASSWORD): PASSWORD,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the host. The identity (gateway UUID) never changes."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, CONF_HOST: user_input[CONF_HOST]}
            _, error = await self._probe(data)
            if error is None:
                return self.async_update_reload_and_abort(entry, data=data)
            errors["base"] = error
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Km200ConfigEntry) -> Km200OptionsFlow:
        return Km200OptionsFlow()


class Km200OptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_WRITE_ENABLED] and not user_input[CONF_WRITE_GROUPS]:
                errors[CONF_WRITE_GROUPS] = "no_group_selected"
            else:
                return self.async_create_entry(data=user_input)
        current = user_input or self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=current.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): vol.All(int, vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL)),
                vol.Required(
                    CONF_WRITE_ENABLED, default=current.get(CONF_WRITE_ENABLED, False)
                ): bool,
                vol.Required(
                    CONF_WRITE_GROUPS, default=current.get(CONF_WRITE_GROUPS, [])
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[group.value for group in WriteGroup],
                        multiple=True,
                        translation_key=CONF_WRITE_GROUPS,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
