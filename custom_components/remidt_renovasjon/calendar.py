"""Calendar platform for ReMidt Renovasjon integration."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CALENDAR_LOOKAHEAD_DAYS,
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
    """Set up ReMidt Renovasjon calendar based on a config entry."""
    coordinator: RenovasjonCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Wait for first data fetch
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([RenovasjonCalendar(coordinator)])


class RenovasjonCalendar(CoordinatorEntity[RenovasjonCoordinator], CalendarEntity):
    """Calendar entity for waste collection events."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RenovasjonCoordinator) -> None:
        """Initialize the calendar entity."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_calendar"
        self._attr_name = "Renovasjon"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=f"Renovasjon {coordinator.config_entry.data[CONF_ADDRESS_NAME]}",
            manufacturer="Renovasjonsportal",
            model=coordinator.config_entry.data[CONF_MUNICIPALITY],
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        if self.coordinator.data is None:
            return None

        events = self._get_events_for_range(
            date.today(),
            date.today() + timedelta(days=CALENDAR_LOOKAHEAD_DAYS),
        )

        if not events:
            return None

        return events[0]

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return self._get_events_for_range(start_date.date(), end_date.date())

    def _get_events_for_range(
        self,
        start: date,
        end: date,
    ) -> list[CalendarEvent]:
        """Get all waste collection events within a date range."""
        if self.coordinator.data is None:
            return []

        events: list[CalendarEvent] = []

        for fraction, disposals in self.coordinator.data.disposals_by_fraction.items():
            fraction_config = WASTE_FRACTIONS.get(fraction, {})
            translation_key = fraction_config.get(
                "translation_key", fraction.lower().replace(" ", "_")
            )

            for disposal in disposals:
                event_date = disposal.date.date()

                if start <= event_date <= end:
                    events.append(
                        CalendarEvent(
                            start=event_date,
                            end=event_date + timedelta(days=1),
                            summary=fraction,
                            description=disposal.description,
                            uid=f"{self._attr_unique_id}_{translation_key}_{event_date.isoformat()}",
                        )
                    )

        events.sort(key=lambda e: e.start)
        return events

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
