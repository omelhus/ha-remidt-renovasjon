"""Fixtures for Renovasjon tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ..const import CONF_ADDRESS_ID, CONF_ADDRESS_NAME, CONF_MUNICIPALITY

# Sample API responses
MOCK_ADDRESS_SEARCH_RESPONSE = {
    "searchResults": [
        {
            "id": "8c098e45-eeca-4fbb-af2a-7044b88930ce",
            "title": "Sigden 6",
            "subTitle": "Kristiansund kommune",
        },
        {
            "id": "12345678-1234-1234-1234-123456789abc",
            "title": "Sigden 8",
            "subTitle": "Kristiansund kommune",
        },
    ],
    "alternateSearchResults": [],
}

MOCK_ADDRESS_SEARCH_EMPTY = {
    "searchResults": [],
    "alternateSearchResults": [],
}

MOCK_DISPOSALS_RESPONSE = {
    "disposals": [
        {
            "date": "2026-01-05T00:00:00",
            "description": None,
            "type": None,
            "fraction": "Glass og metallemballasje",
            "symbolId": 0,
        },
        {
            "date": "2026-01-05T00:00:00",
            "description": None,
            "type": None,
            "fraction": "Plastemballasje",
            "symbolId": 2,
        },
        {
            "date": "2026-01-08T00:00:00",
            "description": None,
            "type": None,
            "fraction": "Papir",
            "symbolId": 0,
        },
        {
            "date": "2026-01-08T00:00:00",
            "description": None,
            "type": None,
            "fraction": "Matavfall",
            "symbolId": 0,
        },
        {
            "date": "2026-01-22T00:00:00",
            "description": None,
            "type": None,
            "fraction": "Restavfall",
            "symbolId": 15,
        },
        {
            "date": "2026-01-22T00:00:00",
            "description": None,
            "type": None,
            "fraction": "Matavfall",
            "symbolId": 0,
        },
        {
            "date": "2026-02-05T00:00:00",
            "description": None,
            "type": None,
            "fraction": "Papir",
            "symbolId": 0,
        },
    ],
}

MOCK_DISPOSALS_EMPTY = {"disposals": []}

MOCK_CONFIG_ENTRY_DATA = {
    CONF_ADDRESS_ID: "8c098e45-eeca-4fbb-af2a-7044b88930ce",
    CONF_ADDRESS_NAME: "Sigden 6",
    CONF_MUNICIPALITY: "Kristiansund kommune",
}


@pytest.fixture
def mock_address_search_response() -> dict:
    """Return mock address search response."""
    return MOCK_ADDRESS_SEARCH_RESPONSE


@pytest.fixture
def mock_disposals_response() -> dict:
    """Return mock disposals response."""
    return MOCK_DISPOSALS_RESPONSE


@pytest.fixture
def mock_config_entry_data() -> dict:
    """Return mock config entry data."""
    return MOCK_CONFIG_ENTRY_DATA.copy()


@pytest.fixture
def mock_aiohttp_session() -> Generator[MagicMock, None, None]:
    """Create a mock aiohttp session."""
    with patch("aiohttp.ClientSession") as mock_session:
        session_instance = MagicMock()
        mock_session.return_value = session_instance
        yield session_instance


@pytest.fixture
def mock_api_client() -> Generator[AsyncMock, None, None]:
    """Create a mock API client."""
    with patch("renovasjon.api.RenovasjonApiClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        yield mock_client


def create_mock_response(json_data: dict, status: int = 200) -> MagicMock:
    """Create a mock aiohttp response."""
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=json_data)
    mock_response.raise_for_status = MagicMock()

    if status >= 400:
        from aiohttp import ClientResponseError

        mock_response.raise_for_status.side_effect = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=status,
            message="Error",
        )

    # Make it work as async context manager
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    return mock_response
