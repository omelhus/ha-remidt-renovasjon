"""Tests for the Renovasjon config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from ..api import (
    AddressSearchResult,
    RenovasjonApiError,
    RenovasjonConnectionError,
)
from ..config_flow import RenovasjonConfigFlow
from ..const import CONF_ADDRESS_ID, CONF_ADDRESS_NAME, CONF_MUNICIPALITY


class TestRenovasjonConfigFlow:
    """Tests for RenovasjonConfigFlow."""

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create a mock HomeAssistant instance."""
        hass = MagicMock(spec=HomeAssistant)
        hass.data = {}
        return hass

    @pytest.fixture
    def flow(self, mock_hass: MagicMock) -> RenovasjonConfigFlow:
        """Create a config flow instance."""
        flow = RenovasjonConfigFlow()
        flow.hass = mock_hass
        return flow

    @pytest.mark.asyncio
    async def test_step_user_shows_form(self, flow: RenovasjonConfigFlow):
        """Test that user step shows the address search form."""
        result = await flow.async_step_user(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert "address" in result["data_schema"].schema

    @pytest.mark.asyncio
    async def test_step_user_search_success(self, flow: RenovasjonConfigFlow):
        """Test successful address search proceeds to selection."""
        mock_addresses = [
            AddressSearchResult(
                id="test-uuid",
                title="Test Street 1",
                municipality="Test Municipality",
            )
        ]

        with (
            patch("renovasjon.config_flow.async_get_clientsession"),
            patch("renovasjon.config_flow.RenovasjonApiClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.search_address.return_value = mock_addresses
            mock_client_class.return_value = mock_client

            result = await flow.async_step_user({"address": "Test Street"})

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "select"

    @pytest.mark.asyncio
    async def test_step_user_no_addresses_found(self, flow: RenovasjonConfigFlow):
        """Test address search with no results shows error."""
        with (
            patch("renovasjon.config_flow.async_get_clientsession"),
            patch("renovasjon.config_flow.RenovasjonApiClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.search_address.return_value = []
            mock_client_class.return_value = mock_client

            result = await flow.async_step_user({"address": "Nonexistent"})

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            assert result["errors"]["address"] == "no_addresses_found"

    @pytest.mark.asyncio
    async def test_step_user_connection_error(self, flow: RenovasjonConfigFlow):
        """Test address search with connection error."""
        with (
            patch("renovasjon.config_flow.async_get_clientsession"),
            patch("renovasjon.config_flow.RenovasjonApiClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.search_address.side_effect = RenovasjonConnectionError("Connection failed")
            mock_client_class.return_value = mock_client

            result = await flow.async_step_user({"address": "Test"})

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            assert result["errors"]["base"] == "cannot_connect"

    @pytest.mark.asyncio
    async def test_step_user_api_error(self, flow: RenovasjonConfigFlow):
        """Test address search with API error."""
        with (
            patch("renovasjon.config_flow.async_get_clientsession"),
            patch("renovasjon.config_flow.RenovasjonApiClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.search_address.side_effect = RenovasjonApiError("API error")
            mock_client_class.return_value = mock_client

            result = await flow.async_step_user({"address": "Test"})

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"
            assert result["errors"]["base"] == "unknown"

    @pytest.mark.asyncio
    async def test_step_select_shows_form(self, flow: RenovasjonConfigFlow):
        """Test that select step shows address options."""
        flow._addresses = [
            AddressSearchResult(
                id="uuid-1",
                title="Street 1",
                municipality="Municipality A",
            ),
            AddressSearchResult(
                id="uuid-2",
                title="Street 2",
                municipality="Municipality B",
            ),
        ]

        result = await flow.async_step_select(user_input=None)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "select"

    @pytest.mark.asyncio
    async def test_step_select_creates_entry(self, flow: RenovasjonConfigFlow):
        """Test selecting an address creates a config entry."""
        flow._addresses = [
            AddressSearchResult(
                id="test-uuid",
                title="Test Street 1",
                municipality="Test Municipality",
            ),
        ]

        with (
            patch("renovasjon.config_flow.async_get_clientsession"),
            patch("renovasjon.config_flow.RenovasjonApiClient") as mock_client_class,
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
        ):
            mock_client = AsyncMock()
            mock_client.get_disposals.return_value = []
            mock_client_class.return_value = mock_client

            result = await flow.async_step_select({"address_id": "test-uuid"})

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["title"] == "Test Street 1, Test Municipality"
            assert result["data"][CONF_ADDRESS_ID] == "test-uuid"
            assert result["data"][CONF_ADDRESS_NAME] == "Test Street 1"
            assert result["data"][CONF_MUNICIPALITY] == "Test Municipality"

    @pytest.mark.asyncio
    async def test_step_select_invalid_address(self, flow: RenovasjonConfigFlow):
        """Test selecting an invalid address shows error."""
        flow._addresses = [
            AddressSearchResult(
                id="valid-uuid",
                title="Valid Street",
                municipality="Municipality",
            ),
        ]

        result = await flow.async_step_select({"address_id": "invalid-uuid"})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "select"
        assert result["errors"]["base"] == "invalid_address"

    @pytest.mark.asyncio
    async def test_step_select_connection_error(self, flow: RenovasjonConfigFlow):
        """Test validation with connection error."""
        flow._addresses = [
            AddressSearchResult(
                id="test-uuid",
                title="Test Street",
                municipality="Municipality",
            ),
        ]

        with (
            patch("renovasjon.config_flow.async_get_clientsession"),
            patch("renovasjon.config_flow.RenovasjonApiClient") as mock_client_class,
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
        ):
            mock_client = AsyncMock()
            mock_client.get_disposals.side_effect = RenovasjonConnectionError("Connection failed")
            mock_client_class.return_value = mock_client

            result = await flow.async_step_select({"address_id": "test-uuid"})

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "cannot_connect"
