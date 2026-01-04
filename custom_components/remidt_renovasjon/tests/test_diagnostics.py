"""Tests for the ReMidt Renovasjon diagnostics."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..api import WasteDisposal
from ..const import DOMAIN
from ..coordinator import RenovasjonCoordinator, RenovasjonData
from ..diagnostics import async_get_config_entry_diagnostics
from .conftest import MOCK_CONFIG_ENTRY_DATA


class TestDiagnostics:
    """Tests for diagnostics."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create a mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {}}
        return hass

    @pytest.fixture
    def mock_entry(self) -> MagicMock:
        """Create a mock ConfigEntry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.version = 1
        entry.domain = DOMAIN
        entry.title = "Test Address"
        entry.data = MOCK_CONFIG_ENTRY_DATA.copy()
        entry.options = {"update_interval": 12}
        return entry

    @pytest.fixture
    def sample_data(self) -> RenovasjonData:
        """Create sample RenovasjonData."""
        tomorrow = datetime.now() + timedelta(days=1)

        return RenovasjonData(
            address_id="test-uuid",
            address_name="Test Street 1",
            municipality="Test Municipality",
            disposals_by_fraction={
                "Restavfall": [
                    WasteDisposal(
                        date=tomorrow,
                        fraction="Restavfall",
                        description="Test description",
                        symbol_id=15,
                    ),
                ],
            },
        )

    @pytest.fixture
    def mock_coordinator(
        self, mock_hass: MagicMock, mock_entry: MagicMock, sample_data: RenovasjonData
    ) -> MagicMock:
        """Create a mock coordinator."""
        coordinator = MagicMock(spec=RenovasjonCoordinator)
        coordinator.hass = mock_hass
        coordinator.config_entry = mock_entry
        coordinator.data = sample_data
        coordinator.last_update_success = True
        coordinator.last_exception = None
        return coordinator

    @pytest.mark.asyncio
    async def test_diagnostics_with_data(
        self,
        mock_hass: MagicMock,
        mock_entry: MagicMock,
        mock_coordinator: MagicMock,
    ):
        """Test diagnostics returns correct data structure."""
        mock_hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator

        result = await async_get_config_entry_diagnostics(mock_hass, mock_entry)

        # Check config_entry section
        assert "config_entry" in result
        assert result["config_entry"]["entry_id"] == "test_entry_id"
        assert result["config_entry"]["version"] == 1
        assert result["config_entry"]["domain"] == DOMAIN
        assert result["config_entry"]["title"] == "Test Address"
        assert result["config_entry"]["options"] == {"update_interval": 12}

        # Check coordinator section
        assert "coordinator" in result
        assert result["coordinator"]["last_update_success"] is True
        assert result["coordinator"]["last_exception"] is None

        # Check data section
        assert "data" in result
        assert result["data"]["address_id"] == "test-uuid"
        assert result["data"]["address_name"] == "Test Street 1"
        assert result["data"]["municipality"] == "Test Municipality"
        assert "Restavfall" in result["data"]["fractions"]
        assert "disposals_by_fraction" in result["data"]
        assert "Restavfall" in result["data"]["disposals_by_fraction"]

    @pytest.mark.asyncio
    async def test_diagnostics_without_data(
        self,
        mock_hass: MagicMock,
        mock_entry: MagicMock,
        mock_coordinator: MagicMock,
    ):
        """Test diagnostics when coordinator has no data."""
        mock_coordinator.data = None
        mock_hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator

        result = await async_get_config_entry_diagnostics(mock_hass, mock_entry)

        # Should still have config_entry and coordinator sections
        assert "config_entry" in result
        assert "coordinator" in result

        # Should not have data section when coordinator.data is None
        assert "data" not in result

    @pytest.mark.asyncio
    async def test_diagnostics_with_exception(
        self,
        mock_hass: MagicMock,
        mock_entry: MagicMock,
        mock_coordinator: MagicMock,
    ):
        """Test diagnostics when coordinator has an exception."""
        mock_coordinator.last_update_success = False
        mock_coordinator.last_exception = ValueError("Test error")
        mock_hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator

        result = await async_get_config_entry_diagnostics(mock_hass, mock_entry)

        assert result["coordinator"]["last_update_success"] is False
        assert "Test error" in result["coordinator"]["last_exception"]

    @pytest.mark.asyncio
    async def test_diagnostics_disposal_format(
        self,
        mock_hass: MagicMock,
        mock_entry: MagicMock,
        mock_coordinator: MagicMock,
    ):
        """Test that disposals are correctly formatted in diagnostics."""
        mock_hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator

        result = await async_get_config_entry_diagnostics(mock_hass, mock_entry)

        disposals = result["data"]["disposals_by_fraction"]["Restavfall"]
        assert len(disposals) == 1
        assert "date" in disposals[0]
        assert "fraction" in disposals[0]
        assert disposals[0]["fraction"] == "Restavfall"
        assert disposals[0]["description"] == "Test description"
