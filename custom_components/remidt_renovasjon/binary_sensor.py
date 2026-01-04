"""Binary sensor platform for ReMidt Renovasjon integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, WASTE_FRACTIONS
from .coordinator import RenovasjonCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ReMidt Renovasjon binary sensors based on a config entry."""
    coordinator: RenovasjonCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Wait for first data fetch
    await coordinator.async_config_entry_first_refresh()

    entities: list[BinarySensorEntity] = []

    # Add a "collection today" binary sensor for each fraction
    if coordinator.data:
        for fraction in coordinator.data.fractions:
            entities.append(
                RenovasjonCollectionTodaySensor(
                    coordinator=coordinator,
                    fraction=fraction,
                )
            )

    async_add_entities(entities)


class RenovasjonCollectionTodaySensor(CoordinatorEntity[RenovasjonCoordinator], BinarySensorEntity):
    """Binary sensor that indicates if there is a collection today for a waste fraction."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RenovasjonCoordinator,
        fraction: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)

        self._fraction = fraction

        # Get fraction config if available
        fraction_config = WASTE_FRACTIONS.get(fraction, {})
        translation_key = fraction_config.get("translation_key", fraction.lower().replace(" ", "_"))
        self._icon = fraction_config.get("icon", "mdi:calendar-check")

        # Entity attributes
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{fraction}_today"
        self._attr_translation_key = f"{translation_key}_today"

        # Fallback name
        self._attr_name = f"{fraction} today"

        # Device info - group all entities under one device per address
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=f"Renovasjon {coordinator.data.address_name}",
            manufacturer="Renovasjonsportal",
            model=coordinator.data.municipality,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def icon(self) -> str:
        """Return the icon based on state."""
        if self.is_on:
            return "mdi:calendar-check"
        return self._icon

    @property
    def is_on(self) -> bool | None:
        """Return true if there is a collection today."""
        if self.coordinator.data is None:
            return None

        # Check if any disposal for this fraction is scheduled for today
        disposals = self.coordinator.data.disposals_by_fraction.get(self._fraction, [])
        today = dt_util.now().date()
        return any(d.date.date() == today for d in disposals)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return extra state attributes."""
        return {"fraction": self._fraction}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
