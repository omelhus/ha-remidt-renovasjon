"""Tests for the ReMidt Renovasjon calendar platform."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..api import WasteDisposal
from ..calendar import RenovasjonCalendar
from ..const import DOMAIN
from ..coordinator import RenovasjonCoordinator, RenovasjonData
from .conftest import MOCK_CONFIG_ENTRY_DATA

# Fixed test dates for deterministic tests
TEST_TODAY = date(2026, 1, 4)
TEST_TOMORROW = datetime(2026, 1, 5)
TEST_NEXT_WEEK = datetime(2026, 1, 11)
TEST_TWO_WEEKS = datetime(2026, 1, 18)


class TestRenovasjonCalendar:
    """Tests for RenovasjonCalendar."""

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
        """Create sample RenovasjonData with fixed dates."""
        return RenovasjonData(
            address_id="test-uuid",
            address_name="Test Street 1",
            municipality="Test Municipality",
            disposals_by_fraction={
                "Restavfall": [
                    WasteDisposal(
                        date=TEST_TOMORROW,
                        fraction="Restavfall",
                        description=None,
                        symbol_id=15,
                    ),
                    WasteDisposal(
                        date=TEST_NEXT_WEEK,
                        fraction="Restavfall",
                        description=None,
                        symbol_id=15,
                    ),
                    WasteDisposal(
                        date=TEST_TWO_WEEKS,
                        fraction="Restavfall",
                        description=None,
                        symbol_id=15,
                    ),
                ],
                "Matavfall": [
                    WasteDisposal(
                        date=TEST_TOMORROW,
                        fraction="Matavfall",
                        description="Food waste",
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
    def calendar(self, mock_coordinator: MagicMock) -> RenovasjonCalendar:
        """Create a calendar instance."""
        return RenovasjonCalendar(coordinator=mock_coordinator)

    def test_calendar_init(self, calendar: RenovasjonCalendar, mock_coordinator: MagicMock):
        """Test calendar initialization."""
        assert calendar._attr_has_entity_name is True
        assert calendar._attr_name == "Renovasjon"

    def test_calendar_unique_id(self, calendar: RenovasjonCalendar):
        """Test calendar unique ID."""
        assert calendar._attr_unique_id == "test_entry_id_calendar"

    def test_calendar_device_info(self, calendar: RenovasjonCalendar):
        """Test calendar device info."""
        device_info = calendar._attr_device_info

        assert device_info is not None
        assert ("remidt_renovasjon", "test_entry_id") in device_info["identifiers"]
        assert "Renovasjon Sigden 6" in device_info["name"]
        assert device_info["manufacturer"] == "Renovasjonsportal"
        assert device_info["model"] == "Kristiansund kommune"

    def test_calendar_event_returns_next_event(self, calendar: RenovasjonCalendar):
        """Test that event property returns the next upcoming event."""
        # Use _get_events_for_range directly with fixed dates to test logic
        events = calendar._get_events_for_range(TEST_TODAY, TEST_TODAY + timedelta(days=365))

        assert len(events) > 0
        first_event = events[0]
        assert isinstance(first_event, CalendarEvent)
        assert first_event.start == TEST_TOMORROW.date()

    def test_calendar_event_no_data(
        self, mock_coordinator: MagicMock, calendar: RenovasjonCalendar
    ):
        """Test event property when no data available."""
        mock_coordinator.data = None

        event = calendar.event

        assert event is None

    @pytest.mark.asyncio
    async def test_async_get_events(self, mock_hass: MagicMock, calendar: RenovasjonCalendar):
        """Test async_get_events returns events within range."""
        start = datetime(2026, 1, 4)
        end = datetime(2026, 2, 4)

        events = await calendar.async_get_events(mock_hass, start, end)

        assert len(events) == 4  # 3 Restavfall + 1 Matavfall

    @pytest.mark.asyncio
    async def test_async_get_events_filtered_by_date(
        self, mock_hass: MagicMock, calendar: RenovasjonCalendar
    ):
        """Test async_get_events filters by date range."""
        # Only get events in the next 3 days
        start = datetime(2026, 1, 4)
        end = datetime(2026, 1, 7)

        events = await calendar.async_get_events(mock_hass, start, end)

        # Should only get tomorrow's events (1 Restavfall + 1 Matavfall)
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_async_get_events_no_data(
        self, mock_hass: MagicMock, mock_coordinator: MagicMock, calendar: RenovasjonCalendar
    ):
        """Test async_get_events when no data available."""
        mock_coordinator.data = None

        start = datetime(2026, 1, 4)
        end = datetime(2026, 2, 4)

        events = await calendar.async_get_events(mock_hass, start, end)

        assert events == []

    def test_event_has_correct_structure(self, calendar: RenovasjonCalendar):
        """Test that calendar events have correct structure."""
        events = calendar._get_events_for_range(
            date(2026, 1, 4),
            date(2026, 2, 4),
        )

        for event in events:
            assert isinstance(event, CalendarEvent)
            assert event.summary in ["Restavfall", "Matavfall"]
            assert event.start is not None
            assert event.end is not None
            # End should be one day after start (all-day event)
            assert event.end == event.start + timedelta(days=1)
            assert event.uid is not None

    def test_event_with_description(self, calendar: RenovasjonCalendar):
        """Test that event description is included."""
        events = calendar._get_events_for_range(
            date(2026, 1, 4),
            date(2026, 2, 4),
        )

        matavfall_events = [e for e in events if e.summary == "Matavfall"]
        assert len(matavfall_events) == 1
        assert matavfall_events[0].description == "Food waste"

    def test_events_are_sorted(self, calendar: RenovasjonCalendar):
        """Test that events are sorted by date."""
        events = calendar._get_events_for_range(
            date(2026, 1, 4),
            date(2026, 2, 4),
        )

        dates = [e.start for e in events]
        assert dates == sorted(dates)


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
    async def test_async_setup_entry_creates_calendar(
        self, mock_hass: MagicMock, mock_entry: MagicMock
    ):
        """Test that async_setup_entry creates a calendar entity."""
        from ..calendar import async_setup_entry

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

        # Should create one calendar entity
        assert len(entities_added) == 1
        assert isinstance(entities_added[0], RenovasjonCalendar)
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()
