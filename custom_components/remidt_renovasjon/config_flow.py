"""Config flow for Renovasjonsportal integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    AddressSearchResult,
    RenovasjonApiClient,
    RenovasjonApiError,
    RenovasjonConnectionError,
)
from .const import (
    CONF_ADDRESS_ID,
    CONF_ADDRESS_NAME,
    CONF_MUNICIPALITY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("address"): str,
    }
)


class RenovasjonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Renovasjonsportal."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._addresses: list[AddressSearchResult] = []
        self._search_query: str = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return RenovasjonOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step - address search."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._search_query = user_input["address"]

            try:
                session = async_get_clientsession(self.hass)
                client = RenovasjonApiClient(session)
                self._addresses = await client.search_address(self._search_query)

                if not self._addresses:
                    errors["address"] = "no_addresses_found"
                else:
                    # Proceed to address selection
                    return await self.async_step_select()

            except RenovasjonConnectionError:
                errors["base"] = "cannot_connect"
            except RenovasjonApiError:
                errors["base"] = "unknown"
            except Exception:
                _LOGGER.exception("Unexpected exception during address search")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "example": "Storgata 1, Oslo",
            },
        )

    async def async_step_select(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle address selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_id = user_input["address_id"]

            # Find the selected address
            selected_address = None
            for addr in self._addresses:
                if addr.id == selected_id:
                    selected_address = addr
                    break

            if selected_address is None:
                errors["base"] = "invalid_address"
            else:
                # Check if already configured
                await self.async_set_unique_id(selected_address.id)
                self._abort_if_unique_id_configured()

                # Validate we can get data for this address
                try:
                    session = async_get_clientsession(self.hass)
                    client = RenovasjonApiClient(session)
                    disposals = await client.get_disposals(selected_address.id)

                    if not disposals:
                        _LOGGER.warning(
                            "No disposals found for address %s, but continuing setup",
                            selected_address.title,
                        )

                except RenovasjonConnectionError:
                    errors["base"] = "cannot_connect"
                except RenovasjonApiError:
                    errors["base"] = "unknown"
                except Exception:
                    _LOGGER.exception("Unexpected exception during validation")
                    errors["base"] = "unknown"

                if not errors:
                    # Create the config entry
                    return self.async_create_entry(
                        title=f"{selected_address.title}, {selected_address.municipality}",
                        data={
                            CONF_ADDRESS_ID: selected_address.id,
                            CONF_ADDRESS_NAME: selected_address.title,
                            CONF_MUNICIPALITY: selected_address.municipality,
                        },
                    )

        # Build address selection options
        address_options = {
            addr.id: f"{addr.title} ({addr.municipality})" for addr in self._addresses
        }

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema(
                {
                    vol.Required("address_id"): vol.In(address_options),
                }
            ),
            errors=errors,
            description_placeholders={
                "count": str(len(self._addresses)),
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration - allows changing address."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            self._search_query = user_input["address"]

            try:
                session = async_get_clientsession(self.hass)
                client = RenovasjonApiClient(session)
                self._addresses = await client.search_address(self._search_query)

                if not self._addresses:
                    errors["address"] = "no_addresses_found"
                else:
                    return await self.async_step_reconfigure_select()

            except RenovasjonConnectionError:
                errors["base"] = "cannot_connect"
            except RenovasjonApiError:
                errors["base"] = "unknown"
            except Exception:
                _LOGGER.exception("Unexpected exception during address search")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "address",
                        default=reconfigure_entry.data.get(CONF_ADDRESS_NAME, ""),
                    ): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "example": "Storgata 1, Oslo",
            },
        )

    async def async_step_reconfigure_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle address selection during reconfiguration."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            selected_id = user_input["address_id"]

            selected_address = None
            for addr in self._addresses:
                if addr.id == selected_id:
                    selected_address = addr
                    break

            if selected_address is None:
                errors["base"] = "invalid_address"
            else:
                # Check if this address is already configured by another entry
                if selected_address.id != reconfigure_entry.unique_id:
                    await self.async_set_unique_id(selected_address.id)
                    self._abort_if_unique_id_configured()

                # Validate we can get data for this address
                try:
                    session = async_get_clientsession(self.hass)
                    client = RenovasjonApiClient(session)
                    await client.get_disposals(selected_address.id)

                except RenovasjonConnectionError:
                    errors["base"] = "cannot_connect"
                except RenovasjonApiError:
                    errors["base"] = "unknown"
                except Exception:
                    _LOGGER.exception("Unexpected exception during validation")
                    errors["base"] = "unknown"

                if not errors:
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        unique_id=selected_address.id,
                        title=f"{selected_address.title}, {selected_address.municipality}",
                        data={
                            CONF_ADDRESS_ID: selected_address.id,
                            CONF_ADDRESS_NAME: selected_address.title,
                            CONF_MUNICIPALITY: selected_address.municipality,
                        },
                    )

        address_options = {
            addr.id: f"{addr.title} ({addr.municipality})" for addr in self._addresses
        }

        return self.async_show_form(
            step_id="reconfigure_select",
            data_schema=vol.Schema(
                {
                    vol.Required("address_id"): vol.In(address_options),
                }
            ),
            errors=errors,
            description_placeholders={
                "count": str(len(self._addresses)),
            },
        )


class RenovasjonOptionsFlow(OptionsFlow):
    """Handle options flow for ReMidt Renovasjon."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_HOURS
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=current_interval,
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=48)),
                }
            ),
        )
