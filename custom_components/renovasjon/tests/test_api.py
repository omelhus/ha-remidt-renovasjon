"""Tests for the Renovasjon API client."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from aiohttp import ClientError, ClientSession

from ..api import (
    AddressSearchResult,
    RenovasjonAddressNotFoundError,
    RenovasjonApiClient,
    RenovasjonConnectionError,
    WasteDisposal,
)
from .conftest import (
    MOCK_ADDRESS_SEARCH_EMPTY,
    MOCK_ADDRESS_SEARCH_RESPONSE,
    MOCK_DISPOSALS_EMPTY,
    MOCK_DISPOSALS_RESPONSE,
    create_mock_response,
)


class TestAddressSearchResult:
    """Tests for AddressSearchResult dataclass."""

    def test_from_dict(self):
        """Test creating AddressSearchResult from dict."""
        data = {
            "id": "test-uuid",
            "title": "Test Street 1",
            "subTitle": "Test Municipality",
        }
        result = AddressSearchResult.from_dict(data)

        assert result.id == "test-uuid"
        assert result.title == "Test Street 1"
        assert result.municipality == "Test Municipality"

    def test_from_dict_missing_subtitle(self):
        """Test creating AddressSearchResult with missing subTitle."""
        data = {
            "id": "test-uuid",
            "title": "Test Street 1",
        }
        result = AddressSearchResult.from_dict(data)

        assert result.id == "test-uuid"
        assert result.title == "Test Street 1"
        assert result.municipality == ""


class TestWasteDisposal:
    """Tests for WasteDisposal dataclass."""

    def test_from_dict(self):
        """Test creating WasteDisposal from dict."""
        data = {
            "date": "2026-01-05T00:00:00",
            "description": "Test description",
            "type": None,
            "fraction": "Restavfall",
            "symbolId": 15,
        }
        result = WasteDisposal.from_dict(data)

        assert result.date.year == 2026
        assert result.date.month == 1
        assert result.date.day == 5
        assert result.fraction == "Restavfall"
        assert result.description == "Test description"
        assert result.symbol_id == 15

    def test_from_dict_with_timezone(self):
        """Test creating WasteDisposal from dict with timezone."""
        data = {
            "date": "2026-01-05T00:00:00Z",
            "description": None,
            "type": None,
            "fraction": "Matavfall",
            "symbolId": 0,
        }
        result = WasteDisposal.from_dict(data)

        assert result.date.year == 2026
        assert result.fraction == "Matavfall"


class TestRenovasjonApiClient:
    """Tests for RenovasjonApiClient."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock aiohttp session."""
        return MagicMock(spec=ClientSession)

    @pytest.fixture
    def client(self, mock_session: MagicMock) -> RenovasjonApiClient:
        """Create an API client with mock session."""
        return RenovasjonApiClient(mock_session)

    @pytest.mark.asyncio
    async def test_search_address_success(
        self, client: RenovasjonApiClient, mock_session: MagicMock
    ):
        """Test successful address search."""
        mock_response = create_mock_response(MOCK_ADDRESS_SEARCH_RESPONSE)
        mock_session.get = MagicMock(return_value=mock_response)

        results = await client.search_address("Sigden 6")

        assert len(results) == 2
        assert results[0].id == "8c098e45-eeca-4fbb-af2a-7044b88930ce"
        assert results[0].title == "Sigden 6"
        assert results[0].municipality == "Kristiansund kommune"

    @pytest.mark.asyncio
    async def test_search_address_empty(self, client: RenovasjonApiClient, mock_session: MagicMock):
        """Test address search with no results."""
        mock_response = create_mock_response(MOCK_ADDRESS_SEARCH_EMPTY)
        mock_session.get = MagicMock(return_value=mock_response)

        results = await client.search_address("Nonexistent Street")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_address_url_encoding(
        self, client: RenovasjonApiClient, mock_session: MagicMock
    ):
        """Test that address search properly URL encodes the query."""
        mock_response = create_mock_response(MOCK_ADDRESS_SEARCH_EMPTY)
        mock_session.get = MagicMock(return_value=mock_response)

        await client.search_address("Storgata 1, Oslo")

        # Verify the URL was called with encoded query
        call_args = mock_session.get.call_args
        url = call_args[0][0]
        assert "Storgata%201%2C%20Oslo" in url

    @pytest.mark.asyncio
    async def test_search_address_connection_error(
        self, client: RenovasjonApiClient, mock_session: MagicMock
    ):
        """Test address search with connection error."""
        mock_session.get = MagicMock(side_effect=ClientError("Connection failed"))

        with pytest.raises(RenovasjonConnectionError):
            await client.search_address("Test")

    @pytest.mark.asyncio
    async def test_search_address_timeout(
        self, client: RenovasjonApiClient, mock_session: MagicMock
    ):
        """Test address search with timeout."""
        mock_session.get = MagicMock(side_effect=TimeoutError())

        with pytest.raises(RenovasjonConnectionError):
            await client.search_address("Test")

    @pytest.mark.asyncio
    async def test_get_disposals_success(
        self, client: RenovasjonApiClient, mock_session: MagicMock
    ):
        """Test successful disposal retrieval."""
        mock_response = create_mock_response(MOCK_DISPOSALS_RESPONSE)
        mock_session.get = MagicMock(return_value=mock_response)

        disposals = await client.get_disposals("test-uuid")

        assert len(disposals) == 7
        assert disposals[0].fraction == "Glass og metallemballasje"
        # Verify sorting by date
        for i in range(len(disposals) - 1):
            assert disposals[i].date <= disposals[i + 1].date

    @pytest.mark.asyncio
    async def test_get_disposals_empty(self, client: RenovasjonApiClient, mock_session: MagicMock):
        """Test disposal retrieval with empty result."""
        mock_response = create_mock_response(MOCK_DISPOSALS_EMPTY)
        mock_session.get = MagicMock(return_value=mock_response)

        disposals = await client.get_disposals("test-uuid")

        assert len(disposals) == 0

    @pytest.mark.asyncio
    async def test_get_disposals_not_found(
        self, client: RenovasjonApiClient, mock_session: MagicMock
    ):
        """Test disposal retrieval with 404 error."""
        mock_response = create_mock_response({}, status=404)
        mock_session.get = MagicMock(return_value=mock_response)

        with pytest.raises(RenovasjonAddressNotFoundError):
            await client.get_disposals("nonexistent-uuid")

    @pytest.mark.asyncio
    async def test_get_disposals_by_fraction(
        self, client: RenovasjonApiClient, mock_session: MagicMock
    ):
        """Test disposal retrieval grouped by fraction."""
        mock_response = create_mock_response(MOCK_DISPOSALS_RESPONSE)
        mock_session.get = MagicMock(return_value=mock_response)

        by_fraction = await client.get_disposals_by_fraction("test-uuid")

        assert "Restavfall" in by_fraction
        assert "Matavfall" in by_fraction
        assert "Papir" in by_fraction
        assert "Plastemballasje" in by_fraction
        assert "Glass og metallemballasje" in by_fraction

        # Matavfall should have 2 entries
        assert len(by_fraction["Matavfall"]) == 2
        # Papir should have 2 entries
        assert len(by_fraction["Papir"]) == 2

    @pytest.mark.asyncio
    async def test_get_disposals_invalid_data(
        self, client: RenovasjonApiClient, mock_session: MagicMock
    ):
        """Test disposal retrieval with invalid data in response."""
        response_with_invalid = {
            "disposals": [
                {
                    "date": "2026-01-05T00:00:00",
                    "fraction": "Valid",
                    "symbolId": 0,
                },
                {
                    # Missing required 'date' field
                    "fraction": "Invalid",
                    "symbolId": 0,
                },
                {
                    "date": "2026-01-06T00:00:00",
                    "fraction": "Also Valid",
                    "symbolId": 0,
                },
            ]
        }
        mock_response = create_mock_response(response_with_invalid)
        mock_session.get = MagicMock(return_value=mock_response)

        # Should skip invalid entries and return valid ones
        disposals = await client.get_disposals("test-uuid")

        assert len(disposals) == 2
        assert disposals[0].fraction == "Valid"
        assert disposals[1].fraction == "Also Valid"
