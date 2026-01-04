"""Tests for the ReMidt Renovasjon binary sensor platform."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..api import WasteDisposal
from ..binary_sensor import RenovasjonCollectionTodaySensor, async_setup_entry
from ..const import DOMAIN
from ..coordinator import RenovasjonCoordinator, RenovasjonData
from .conftest import MOCK_CONFIG_ENTRY_DATA


class TestRenovasjonCollectionTodaySensor:
    """Tests for RenovasjonCollectionTodaySensor."""

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
        entry.options = {}
        return entry

    @pytest.fixture
    def sample_data_with_today(self) -> RenovasjonData:
        """Create sample RenovasjonData with a disposal today."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        return RenovasjonData(
            address_id="test-uuid",
            address_name="Test Street 1",
            municipality="Test Municipality",
            disposals_by_fraction={
                "Restavfall": [
                    WasteDisposal(
                        date=today,
                        fraction="Restavfall",
                        description=None,
                        symbol_id=15,
                    ),
                    WasteDisposal(
                        date=tomorrow,
                        fraction="Restavfall",
                        description=None,
                        symbol_id=15,
                    ),
                ],
                "Matavfall": [
                    WasteDisposal(
                        date=tomorrow,
                        fraction="Matavfall",
                        description=None,
                        symbol_id=0,
                    ),
                ],
            },
        )

    @pytest.fixture
    def sample_data_without_today(self) -> RenovasjonData:
        """Create sample RenovasjonData without a disposal today."""
        tomorrow = datetime.now() + timedelta(days=1)
        next_week = datetime.now() + timedelta(days=7)

        return RenovasjonData(
            address_id="test-uuid",
            address_name="Test Street 1",
            municipality="Test Municipality",
            disposals_by_fraction={
                "Restavfall": [
                    WasteDisposal(
                        date=tomorrow,
                        fraction="Restavfall",
                        description=None,
                        symbol_id=15,
                    ),
                    WasteDisposal(
                        date=next_week,
                        fraction="Restavfall",
                        description=None,
                        symbol_id=15,
                    ),
                ],
            },
        )

    @pytest.fixture
    def mock_coordinator_with_today(
        self, mock_hass: MagicMock, mock_entry: MagicMock, sample_data_with_today: RenovasjonData
    ) -> MagicMock:
        """Create a mock coordinator with disposal today."""
        coordinator = MagicMock(spec=RenovasjonCoordinator)
        coordinator.hass = mock_hass
        coordinator.config_entry = mock_entry
        coordinator.data = sample_data_with_today
        return coordinator

    @pytest.fixture
    def mock_coordinator_without_today(
        self, mock_hass: MagicMock, mock_entry: MagicMock, sample_data_without_today: RenovasjonData
    ) -> MagicMock:
        """Create a mock coordinator without disposal today."""
        coordinator = MagicMock(spec=RenovasjonCoordinator)
        coordinator.hass = mock_hass
        coordinator.config_entry = mock_entry
        coordinator.data = sample_data_without_today
        return coordinator

    def test_sensor_init(self, mock_coordinator_with_today: MagicMock):
        """Test binary sensor initialization."""
        sensor = RenovasjonCollectionTodaySensor(
            coordinator=mock_coordinator_with_today,
            fraction="Restavfall",
        )

        assert sensor._attr_has_entity_name is True
        assert sensor._attr_unique_id == "test_entry_id_Restavfall_today"
        assert sensor._fraction == "Restavfall"

    def test_sensor_is_on_when_collection_today(self, mock_coordinator_with_today: MagicMock):
        """Test sensor is ON when there is a collection today."""
        sensor = RenovasjonCollectionTodaySensor(
            coordinator=mock_coordinator_with_today,
            fraction="Restavfall",
        )

        assert sensor.is_on is True

    def test_sensor_is_off_when_no_collection_today(self, mock_coordinator_with_today: MagicMock):
        """Test sensor is OFF when there is no collection today."""
        sensor = RenovasjonCollectionTodaySensor(
            coordinator=mock_coordinator_with_today,
            fraction="Matavfall",  # Matavfall is tomorrow, not today
        )

        assert sensor.is_on is False

    def test_sensor_is_off_when_collection_tomorrow(
        self, mock_coordinator_without_today: MagicMock
    ):
        """Test sensor is OFF when next collection is tomorrow."""
        sensor = RenovasjonCollectionTodaySensor(
            coordinator=mock_coordinator_without_today,
            fraction="Restavfall",
        )

        assert sensor.is_on is False

    def test_sensor_is_none_when_no_data(self, mock_coordinator_with_today: MagicMock):
        """Test sensor returns None when no data available."""
        # Create sensor with valid data first
        sensor = RenovasjonCollectionTodaySensor(
            coordinator=mock_coordinator_with_today,
            fraction="Restavfall",
        )

        # Then simulate data becoming unavailable
        mock_coordinator_with_today.data = None

        assert sensor.is_on is None

    def test_sensor_icon_when_on(self, mock_coordinator_with_today: MagicMock):
        """Test sensor icon when collection is today."""
        sensor = RenovasjonCollectionTodaySensor(
            coordinator=mock_coordinator_with_today,
            fraction="Restavfall",
        )

        assert sensor.icon == "mdi:calendar-check"

    def test_sensor_icon_when_off(self, mock_coordinator_without_today: MagicMock):
        """Test sensor icon when no collection today (uses fraction icon)."""
        sensor = RenovasjonCollectionTodaySensor(
            coordinator=mock_coordinator_without_today,
            fraction="Restavfall",
        )

        # Should use the fraction-specific icon
        assert sensor.icon == "mdi:trash-can"

    def test_sensor_extra_attributes(self, mock_coordinator_with_today: MagicMock):
        """Test sensor extra state attributes."""
        sensor = RenovasjonCollectionTodaySensor(
            coordinator=mock_coordinator_with_today,
            fraction="Restavfall",
        )

        attrs = sensor.extra_state_attributes
        assert attrs["fraction"] == "Restavfall"

    def test_sensor_device_info(self, mock_coordinator_with_today: MagicMock):
        """Test sensor device info."""
        sensor = RenovasjonCollectionTodaySensor(
            coordinator=mock_coordinator_with_today,
            fraction="Restavfall",
        )

        device_info = sensor._attr_device_info

        assert device_info is not None
        assert ("remidt_renovasjon", "test_entry_id") in device_info["identifiers"]
        assert "Renovasjon Test Street 1" in device_info["name"]
        assert device_info["manufacturer"] == "Renovasjonsportal"
        assert device_info["model"] == "Test Municipality"


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

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
        entry.data = MOCK_CONFIG_ENTRY_DATA.copy()
        entry.options = {}
        return entry

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_sensors(
        self, mock_hass: MagicMock, mock_entry: MagicMock
    ):
        """Test that async_setup_entry creates binary sensor entities."""
        sample_data = RenovasjonData(
            address_id="test-uuid",
            address_name="Test Street",
            municipality="Municipality",
            disposals_by_fraction={
                "Restavfall": [],
                "Matavfall": [],
            },
        )

        mock_coordinator = MagicMock(spec=RenovasjonCoordinator)
        mock_coordinator.data = sample_data
        mock_coordinator.config_entry = mock_entry
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()

        mock_hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator

        entities_added = []

        def capture_entities(entities):
            entities_added.extend(entities)

        await async_setup_entry(mock_hass, mock_entry, capture_entities)

        # Should create one binary sensor per fraction
        assert len(entities_added) == 2
        assert all(isinstance(e, RenovasjonCollectionTodaySensor) for e in entities_added)
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()
