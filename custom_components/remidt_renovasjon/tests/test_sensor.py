"""Tests for the Renovasjon sensor platform."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..api import WasteDisposal
from ..const import (
    ATTR_ADDRESS,
    ATTR_DAYS_UNTIL,
    ATTR_FRACTION,
    ATTR_MUNICIPALITY,
    ATTR_NEXT_DATE,
    ATTR_UPCOMING_DATES,
    DOMAIN,
)
from ..coordinator import RenovasjonCoordinator, RenovasjonData
from ..sensor import RenovasjonSensor
from .conftest import MOCK_CONFIG_ENTRY_DATA


class TestRenovasjonSensor:
    """Tests for RenovasjonSensor."""

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
    def sample_data(self) -> RenovasjonData:
        """Create sample RenovasjonData."""
        tomorrow = datetime.now() + timedelta(days=1)
        next_week = datetime.now() + timedelta(days=7)
        two_weeks = datetime.now() + timedelta(days=14)

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
                    WasteDisposal(
                        date=two_weeks,
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
    def mock_coordinator(
        self, mock_hass: MagicMock, mock_entry: MagicMock, sample_data: RenovasjonData
    ) -> MagicMock:
        """Create a mock coordinator."""
        coordinator = MagicMock(spec=RenovasjonCoordinator)
        coordinator.hass = mock_hass
        coordinator.config_entry = mock_entry
        coordinator.data = sample_data
        return coordinator

    @pytest.fixture
    def sensor(self, mock_coordinator: MagicMock) -> RenovasjonSensor:
        """Create a sensor instance."""
        return RenovasjonSensor(
            coordinator=mock_coordinator,
            fraction="Restavfall",
        )

    def test_sensor_init(self, sensor: RenovasjonSensor, mock_coordinator: MagicMock):
        """Test sensor initialization."""
        assert sensor._fraction == "Restavfall"
        assert sensor._attr_has_entity_name is True
        assert sensor._attr_device_class == SensorDeviceClass.DATE
        assert sensor._attr_icon == "mdi:trash-can"

    def test_sensor_unique_id(self, sensor: RenovasjonSensor):
        """Test sensor unique ID."""
        assert "test_entry_id" in sensor._attr_unique_id
        assert "Restavfall" in sensor._attr_unique_id

    def test_sensor_native_value(self, sensor: RenovasjonSensor):
        """Test sensor native value returns next collection date."""
        value = sensor.native_value

        assert value is not None
        assert isinstance(value, date)
        assert value == (datetime.now() + timedelta(days=1)).date()

    def test_sensor_native_value_no_data(
        self, mock_coordinator: MagicMock, sensor: RenovasjonSensor
    ):
        """Test sensor native value when no data available."""
        mock_coordinator.data = None

        value = sensor.native_value

        assert value is None

    def test_sensor_extra_state_attributes(self, sensor: RenovasjonSensor):
        """Test sensor extra state attributes."""
        attrs = sensor.extra_state_attributes

        assert attrs[ATTR_FRACTION] == "Restavfall"
        assert attrs[ATTR_ADDRESS] == "Test Street 1"
        assert attrs[ATTR_MUNICIPALITY] == "Test Municipality"
        assert attrs[ATTR_DAYS_UNTIL] == 1
        assert ATTR_NEXT_DATE in attrs
        assert ATTR_UPCOMING_DATES in attrs
        assert len(attrs[ATTR_UPCOMING_DATES]) == 3  # All 3 upcoming dates

    def test_sensor_extra_state_attributes_no_data(
        self, mock_coordinator: MagicMock, sensor: RenovasjonSensor
    ):
        """Test sensor extra state attributes when no data available."""
        mock_coordinator.data = None

        attrs = sensor.extra_state_attributes

        assert attrs[ATTR_FRACTION] == "Restavfall"
        assert ATTR_ADDRESS not in attrs
        assert ATTR_DAYS_UNTIL not in attrs

    def test_sensor_device_info(self, sensor: RenovasjonSensor):
        """Test sensor device info."""
        device_info = sensor._attr_device_info

        assert device_info is not None
        assert ("remidt_renovasjon", "test_entry_id") in device_info["identifiers"]
        assert "Renovasjon Test Street 1" in device_info["name"]
        assert device_info["manufacturer"] == "Renovasjonsportal"
        assert device_info["model"] == "Test Municipality"

    def test_sensor_for_unknown_fraction(self, mock_coordinator: MagicMock):
        """Test sensor for a fraction not in WASTE_FRACTIONS."""
        sensor = RenovasjonSensor(
            coordinator=mock_coordinator,
            fraction="Custom Waste Type",
        )

        # Should use default icon
        assert sensor._attr_icon == "mdi:trash-can-outline"
        assert sensor._attr_name == "Custom Waste Type"

    def test_sensor_matavfall(self, mock_coordinator: MagicMock):
        """Test sensor for Matavfall fraction."""
        sensor = RenovasjonSensor(
            coordinator=mock_coordinator,
            fraction="Matavfall",
        )

        assert sensor._attr_icon == "mdi:food-apple"
        assert sensor.native_value is not None


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
        return entry

    @pytest.mark.asyncio
    async def test_async_setup_entry_creates_sensors(
        self, mock_hass: MagicMock, mock_entry: MagicMock
    ):
        """Test that async_setup_entry creates sensors for each fraction."""
        from ..sensor import async_setup_entry

        sample_data = RenovasjonData(
            address_id="test-uuid",
            address_name="Test Street",
            municipality="Municipality",
            disposals_by_fraction={
                "Restavfall": [],
                "Matavfall": [],
                "Papir": [],
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

        # Should create one sensor per fraction
        assert len(entities_added) == 3

        fractions = {e._fraction for e in entities_added}
        assert "Restavfall" in fractions
        assert "Matavfall" in fractions
        assert "Papir" in fractions
