"""Tests for the Renovasjon data coordinator."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from ..api import RenovasjonApiError, RenovasjonConnectionError, WasteDisposal
from ..const import CONF_ADDRESS_ID, CONF_ADDRESS_NAME, CONF_MUNICIPALITY
from ..coordinator import RenovasjonCoordinator, RenovasjonData
from .conftest import MOCK_CONFIG_ENTRY_DATA


class TestRenovasjonData:
    """Tests for RenovasjonData container."""

    @pytest.fixture
    def sample_disposals(self) -> dict[str, list[WasteDisposal]]:
        """Create sample disposals grouped by fraction."""
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        past = today - timedelta(days=1)

        return {
            "Restavfall": [
                WasteDisposal(date=tomorrow, fraction="Restavfall", description=None, symbol_id=0),
                WasteDisposal(date=next_week, fraction="Restavfall", description=None, symbol_id=0),
            ],
            "Matavfall": [
                WasteDisposal(date=past, fraction="Matavfall", description=None, symbol_id=0),
                WasteDisposal(date=tomorrow, fraction="Matavfall", description=None, symbol_id=0),
            ],
            "Papir": [],
        }

    @pytest.fixture
    def data(self, sample_disposals: dict) -> RenovasjonData:
        """Create RenovasjonData instance."""
        return RenovasjonData(
            address_id="test-uuid",
            address_name="Test Street 1",
            municipality="Test Municipality",
            disposals_by_fraction=sample_disposals,
        )

    def test_fractions(self, data: RenovasjonData):
        """Test getting list of fractions."""
        fractions = data.fractions

        assert "Restavfall" in fractions
        assert "Matavfall" in fractions
        assert "Papir" in fractions

    def test_get_next_disposal(self, data: RenovasjonData):
        """Test getting next disposal for a fraction."""
        # Restavfall has tomorrow and next week - should return tomorrow
        next_disposal = data.get_next_disposal("Restavfall")
        assert next_disposal is not None
        assert next_disposal.date.date() >= date.today()

        # Matavfall has past and tomorrow - should skip past, return tomorrow
        next_disposal = data.get_next_disposal("Matavfall")
        assert next_disposal is not None
        assert next_disposal.date.date() >= date.today()

        # Papir is empty
        next_disposal = data.get_next_disposal("Papir")
        assert next_disposal is None

        # Unknown fraction
        next_disposal = data.get_next_disposal("Unknown")
        assert next_disposal is None

    def test_get_upcoming_disposals(self, data: RenovasjonData):
        """Test getting upcoming disposals."""
        upcoming = data.get_upcoming_disposals("Restavfall", limit=5)
        assert len(upcoming) == 2

        # With limit
        upcoming = data.get_upcoming_disposals("Restavfall", limit=1)
        assert len(upcoming) == 1

        # Matavfall should exclude past date
        upcoming = data.get_upcoming_disposals("Matavfall")
        assert len(upcoming) == 1
        assert all(d.date.date() >= date.today() for d in upcoming)

    def test_get_days_until(self, data: RenovasjonData):
        """Test getting days until next disposal."""
        # Should be 1 day until tomorrow
        days = data.get_days_until("Restavfall")
        assert days == 1

        # Unknown fraction
        days = data.get_days_until("Unknown")
        assert days is None

        # Empty fraction
        days = data.get_days_until("Papir")
        assert days is None


class TestRenovasjonCoordinator:
    """Tests for RenovasjonCoordinator."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create a mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        return hass

    @pytest.fixture
    def mock_entry(self) -> MagicMock:
        """Create a mock ConfigEntry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.data = MOCK_CONFIG_ENTRY_DATA.copy()
        return entry

    @pytest.fixture
    def coordinator(self, mock_hass: MagicMock, mock_entry: MagicMock) -> RenovasjonCoordinator:
        """Create a coordinator instance."""
        return RenovasjonCoordinator(mock_hass, mock_entry)

    def test_init(self, coordinator: RenovasjonCoordinator, mock_entry: MagicMock):
        """Test coordinator initialization."""
        assert coordinator._address_id == MOCK_CONFIG_ENTRY_DATA[CONF_ADDRESS_ID]
        assert coordinator._address_name == MOCK_CONFIG_ENTRY_DATA[CONF_ADDRESS_NAME]
        assert coordinator._municipality == MOCK_CONFIG_ENTRY_DATA[CONF_MUNICIPALITY]

    @pytest.mark.asyncio
    async def test_async_update_data_success(
        self, coordinator: RenovasjonCoordinator, mock_hass: MagicMock
    ):
        """Test successful data update."""
        mock_disposals = {
            "Restavfall": [
                WasteDisposal(
                    date=datetime.now() + timedelta(days=1),
                    fraction="Restavfall",
                    description=None,
                    symbol_id=0,
                )
            ]
        }

        with (
            patch("renovasjon.coordinator.async_get_clientsession"),
            patch("renovasjon.coordinator.RenovasjonApiClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.get_disposals_by_fraction.return_value = mock_disposals
            mock_client_class.return_value = mock_client

            data = await coordinator._async_update_data()

            assert data is not None
            assert data.address_id == MOCK_CONFIG_ENTRY_DATA[CONF_ADDRESS_ID]
            assert data.address_name == MOCK_CONFIG_ENTRY_DATA[CONF_ADDRESS_NAME]
            assert "Restavfall" in data.fractions

    @pytest.mark.asyncio
    async def test_async_update_data_connection_error(
        self, coordinator: RenovasjonCoordinator, mock_hass: MagicMock
    ):
        """Test data update with connection error."""
        with (
            patch("renovasjon.coordinator.async_get_clientsession"),
            patch("renovasjon.coordinator.RenovasjonApiClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.get_disposals_by_fraction.side_effect = RenovasjonConnectionError(
                "Connection failed"
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(UpdateFailed) as exc_info:
                await coordinator._async_update_data()

            assert "Connection error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_update_data_api_error(
        self, coordinator: RenovasjonCoordinator, mock_hass: MagicMock
    ):
        """Test data update with API error."""
        with (
            patch("renovasjon.coordinator.async_get_clientsession"),
            patch("renovasjon.coordinator.RenovasjonApiClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.get_disposals_by_fraction.side_effect = RenovasjonApiError("API failed")
            mock_client_class.return_value = mock_client

            with pytest.raises(UpdateFailed) as exc_info:
                await coordinator._async_update_data()

            assert "API error" in str(exc_info.value)
