"""Config flow for the Dunedin City Council integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import DunedinApiError, async_search_addresses
from .const import CONF_ADDRESS, CONF_PROPERTY_ID, CONF_SWAP_WEEKS, CONF_TERTIARY, DOMAIN
from .coordinator import DunedinConfigEntry


class DunedinCouncilConfigFlow(ConfigFlow, domain=DOMAIN):
    """Search for an address, then pick the matching property."""

    VERSION = 1

    def __init__(self) -> None:
        self._matches: dict[str, dict] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: DunedinConfigEntry) -> OptionsFlow:
        return DunedinOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                results = await async_search_addresses(
                    async_get_clientsession(self.hass), user_input[CONF_ADDRESS]
                )
            except DunedinApiError:
                errors["base"] = "cannot_connect"
            else:
                self._matches = {
                    str(r["tpklpaprop"]): r
                    for r in results
                    if r.get("tpklpaprop") is not None and r.get("fmtaddress")
                }
                if not self._matches:
                    errors["base"] = "no_results"
                else:
                    return await self.async_step_pick()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): str}),
            errors=errors,
        )

    async def async_step_pick(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            property_id = user_input[CONF_PROPERTY_ID]
            match = self._matches[property_id]
            await self.async_set_unique_id(property_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=match["fmtaddress"],
                data={CONF_PROPERTY_ID: property_id, CONF_ADDRESS: match["fmtaddress"]},
                options={CONF_TERTIARY: user_input.get(CONF_TERTIARY, False)},
            )

        options = [
            SelectOptionDict(value=pid, label=row["fmtaddress"])
            for pid, row in self._matches.items()
        ]
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROPERTY_ID): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                    ),
                    vol.Optional(CONF_TERTIARY, default=False): bool,
                }
            ),
        )


class DunedinOptionsFlow(OptionsFlow):
    """Adjust tertiary-area and week-colour settings after setup."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_TERTIARY, default=current.get(CONF_TERTIARY, False)): bool,
                    vol.Optional(
                        CONF_SWAP_WEEKS, default=current.get(CONF_SWAP_WEEKS, False)
                    ): bool,
                }
            ),
        )
