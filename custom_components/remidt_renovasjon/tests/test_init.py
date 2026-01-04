"""Tests for the Renovasjon integration setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from ..const import DOMAIN
from .conftest import MOCK_CONFIG_ENTRY_DATA


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create a mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()
        hass.services.has_service.return_value = False
        hass.services.async_register = MagicMock()
        return hass

    @pytest.fixture
    def mock_entry(self) -> MagicMock:
        """Create a mock ConfigEntry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.title = "Test Address"
        entry.data = MOCK_CONFIG_ENTRY_DATA.copy()
        entry.options = {}
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        entry.async_on_unload = MagicMock()
        return entry

    @pytest.mark.asyncio
    async def test_async_setup_entry_success(self, mock_hass: MagicMock, mock_entry: MagicMock):
        """Test successful setup of config entry."""
        from .. import async_setup_entry

        with patch("remidt_renovasjon.RenovasjonCoordinator") as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator_class.return_value = mock_coordinator

            result = await async_setup_entry(mock_hass, mock_entry)

            assert result is True
            assert DOMAIN in mock_hass.data
            assert mock_entry.entry_id in mock_hass.data[DOMAIN]
            assert mock_hass.data[DOMAIN][mock_entry.entry_id] == mock_coordinator

            # Verify platforms were set up
            mock_hass.config_entries.async_forward_entry_setups.assert_called_once()
            call_args = mock_hass.config_entries.async_forward_entry_setups.call_args
            assert mock_entry in call_args[0]
            assert Platform.SENSOR in call_args[0][1]


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create a mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {DOMAIN: {"test_entry_id": MagicMock()}}
        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass.services = MagicMock()
        hass.services.async_remove = MagicMock()
        return hass

    @pytest.fixture
    def mock_entry(self) -> MagicMock:
        """Create a mock ConfigEntry."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry_id"
        entry.title = "Test Address"
        entry.data = MOCK_CONFIG_ENTRY_DATA.copy()
        entry.options = {}
        return entry

    @pytest.mark.asyncio
    async def test_async_unload_entry_success(self, mock_hass: MagicMock, mock_entry: MagicMock):
        """Test successful unload of config entry."""
        from .. import async_unload_entry

        result = await async_unload_entry(mock_hass, mock_entry)

        assert result is True
        assert mock_entry.entry_id not in mock_hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_async_unload_entry_failure(self, mock_hass: MagicMock, mock_entry: MagicMock):
        """Test failed unload of config entry."""
        from .. import async_unload_entry

        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        result = await async_unload_entry(mock_hass, mock_entry)

        assert result is False
        # Entry should still be in data if unload failed
        assert mock_entry.entry_id in mock_hass.data[DOMAIN]
