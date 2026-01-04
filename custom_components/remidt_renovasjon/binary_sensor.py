"""Binary sensor platform for ReMidt Renovasjon integration."""

from __future__ import annotations

import logging
from datetime import date

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ADDRESS_NAME,
    CONF_MUNICIPALITY,
    DOMAIN,
    WASTE_FRACTIONS,
)
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
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

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

        # Entity attributes
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{fraction}_today"
        self._attr_translation_key = f"{translation_key}_today"
        self._attr_icon = "mdi:calendar-check"

        # Fallback name
        self._attr_name = f"{fraction} today"

        # Device info - group all entities under one device per address
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=f"Renovasjon {coordinator.config_entry.data[CONF_ADDRESS_NAME]}",
            manufacturer="Renovasjonsportal",
            model=coordinator.config_entry.data[CONF_MUNICIPALITY],
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if there is a collection today."""
        if self.coordinator.data is None:
            return None

        next_disposal = self.coordinator.data.get_next_disposal(self._fraction)
        if next_disposal is None:
            return False

        return next_disposal.date.date() == date.today()

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return extra state attributes."""
        return {"fraction": self._fraction}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
