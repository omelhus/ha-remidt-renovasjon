"""Data coordinator for Renovasjonsportal integration."""

from __future__ import annotations

import logging
from datetime import date, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    RenovasjonApiClient,
    RenovasjonApiError,
    RenovasjonConnectionError,
    WasteDisposal,
)
from .const import (
    CONF_ADDRESS_ID,
    CONF_ADDRESS_NAME,
    CONF_MUNICIPALITY,
    DOMAIN,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class RenovasjonData:
    """Container for Renovasjon data."""

    def __init__(
        self,
        address_id: str,
        address_name: str,
        municipality: str,
        disposals_by_fraction: dict[str, list[WasteDisposal]],
    ) -> None:
        """Initialize data container."""
        self.address_id = address_id
        self.address_name = address_name
        self.municipality = municipality
        self.disposals_by_fraction = disposals_by_fraction
        self.last_update = datetime.now()

    @property
    def fractions(self) -> list[str]:
        """Get list of all waste fractions."""
        return list(self.disposals_by_fraction.keys())

    def get_next_disposal(self, fraction: str) -> WasteDisposal | None:
        """Get next disposal for a fraction."""
        disposals = self.disposals_by_fraction.get(fraction, [])
        now = datetime.now()

        for disposal in disposals:
            # Compare dates only (ignore time component)
            if disposal.date.date() >= now.date():
                return disposal

        return None

    def get_upcoming_disposals(self, fraction: str, limit: int = 5) -> list[WasteDisposal]:
        """Get upcoming disposals for a fraction."""
        disposals = self.disposals_by_fraction.get(fraction, [])
        now = datetime.now()

        upcoming = [d for d in disposals if d.date.date() >= now.date()]
        return upcoming[:limit]

    def get_days_until(self, fraction: str) -> int | None:
        """Get days until next disposal for a fraction."""
        next_disposal = self.get_next_disposal(fraction)
        if next_disposal is None:
            return None

        today = date.today()
        delta = next_disposal.date.date() - today
        return delta.days


class RenovasjonCoordinator(DataUpdateCoordinator[RenovasjonData]):
    """Coordinator for Renovasjonsportal data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.config_entry = entry
        self._address_id: str = entry.data[CONF_ADDRESS_ID]
        self._address_name: str = entry.data[CONF_ADDRESS_NAME]
        self._municipality: str = entry.data[CONF_MUNICIPALITY]

    async def _async_update_data(self) -> RenovasjonData:
        """Fetch data from API."""
        session = async_get_clientsession(self.hass)
        client = RenovasjonApiClient(session)

        try:
            disposals_by_fraction = await client.get_disposals_by_fraction(self._address_id)

            _LOGGER.debug(
                "Updated data for %s: %d fractions",
                self._address_name,
                len(disposals_by_fraction),
            )

            return RenovasjonData(
                address_id=self._address_id,
                address_name=self._address_name,
                municipality=self._municipality,
                disposals_by_fraction=disposals_by_fraction,
            )

        except RenovasjonConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except RenovasjonApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching data")
            raise UpdateFailed(f"Unexpected error: {err}") from err
