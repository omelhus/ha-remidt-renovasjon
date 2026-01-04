"""The Renovasjonsportal integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import RenovasjonCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR, Platform.BINARY_SENSOR]

SERVICE_REFRESH = "refresh"
SERVICE_REFRESH_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Renovasjonsportal from a config entry."""
    _LOGGER.debug("Setting up Renovasjon integration for %s", entry.title)

    # Create coordinator
    coordinator = RenovasjonCoordinator(hass, entry)

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services (only once)
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):

        async def async_refresh_service(call: ServiceCall) -> None:
            """Handle the refresh service call."""
            entry_id = call.data.get("entry_id")

            if entry_id:
                # Refresh specific entry
                if entry_id not in hass.data[DOMAIN]:
                    raise ServiceValidationError(
                        f"Unknown entry_id: {entry_id}",
                        translation_domain=DOMAIN,
                        translation_key="unknown_entry_id",
                        translation_placeholders={"entry_id": entry_id},
                    )
                coordinator = hass.data[DOMAIN][entry_id]
                await coordinator.async_refresh()
                _LOGGER.debug("Refreshed data for entry %s", entry_id)
            else:
                # Refresh all entries
                for coord in hass.data[DOMAIN].values():
                    await coord.async_refresh()
                _LOGGER.debug("Refreshed data for all entries")

        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH,
            async_refresh_service,
            schema=SERVICE_REFRESH_SCHEMA,
        )

    return True


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinator: RenovasjonCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.update_interval_from_options()
    _LOGGER.debug("Options updated for %s", entry.title)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Renovasjon integration for %s", entry.title)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        # Unregister services if no more entries
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH)

    return unload_ok
