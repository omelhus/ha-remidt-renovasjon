"""Diagnostics support for ReMidt Renovasjon."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import RenovasjonCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: RenovasjonCoordinator = hass.data[DOMAIN][entry.entry_id]

    diagnostics_data: dict[str, Any] = {
        "config_entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": str(coordinator.last_exception)
            if coordinator.last_exception
            else None,
        },
    }

    if coordinator.data:
        diagnostics_data["data"] = {
            "address_id": coordinator.data.address_id,
            "address_name": coordinator.data.address_name,
            "municipality": coordinator.data.municipality,
            "fractions": coordinator.data.fractions,
            "last_update": coordinator.data.last_update.isoformat(),
            "disposals_by_fraction": {
                fraction: [
                    {
                        "date": disposal.date.isoformat(),
                        "fraction": disposal.fraction,
                        "description": disposal.description,
                    }
                    for disposal in disposals
                ]
                for fraction, disposals in coordinator.data.disposals_by_fraction.items()
            },
        }

    return diagnostics_data
