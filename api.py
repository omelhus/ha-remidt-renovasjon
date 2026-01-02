"""API client for Renovasjonsportal."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

import aiohttp
from aiohttp import ClientError, ClientResponseError, ClientTimeout

from .const import API_ADDRESS_DETAILS, API_ADDRESS_SEARCH

_LOGGER = logging.getLogger(__name__)

# Timeout for API requests
REQUEST_TIMEOUT = ClientTimeout(total=30)


class RenovasjonApiError(Exception):
    """Base exception for Renovasjon API errors."""


class RenovasjonConnectionError(RenovasjonApiError):
    """Exception for connection errors."""


class RenovasjonAddressNotFoundError(RenovasjonApiError):
    """Exception when address is not found."""


@dataclass
class AddressSearchResult:
    """Represents an address search result."""

    id: str
    title: str
    municipality: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AddressSearchResult:
        """Create from API response dict."""
        return cls(
            id=data["id"],
            title=data["title"],
            municipality=data.get("subTitle", ""),
        )


@dataclass
class WasteDisposal:
    """Represents a waste disposal event."""

    date: datetime
    fraction: str
    description: str | None
    symbol_id: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WasteDisposal:
        """Create from API response dict."""
        # Parse ISO format date
        date_str = data["date"]
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        return cls(
            date=date,
            fraction=data["fraction"],
            description=data.get("description"),
            symbol_id=data.get("symbolId", 0),
        )


class RenovasjonApiClient:
    """API client for Renovasjonsportal."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client.

        Args:
            session: aiohttp client session for making requests
        """
        self._session = session

    async def _request(self, url: str) -> dict[str, Any]:
        """Make an API request.

        Args:
            url: The URL to request

        Returns:
            JSON response as dict

        Raises:
            RenovasjonConnectionError: On connection errors
            RenovasjonApiError: On API errors
        """
        try:
            async with self._session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "HomeAssistant/Renovasjon",
                },
            ) as response:
                response.raise_for_status()
                return await response.json()

        except TimeoutError as err:
            _LOGGER.error("Timeout connecting to Renovasjonsportal API: %s", err)
            raise RenovasjonConnectionError("Timeout connecting to Renovasjonsportal API") from err

        except ClientResponseError as err:
            _LOGGER.error("API response error: %s", err)
            if err.status == 404:
                raise RenovasjonAddressNotFoundError("Address not found") from err
            raise RenovasjonApiError(f"API error: {err.status} {err.message}") from err

        except ClientError as err:
            _LOGGER.error("Connection error to Renovasjonsportal API: %s", err)
            raise RenovasjonConnectionError(f"Connection error: {err}") from err

    async def search_address(self, query: str) -> list[AddressSearchResult]:
        """Search for an address.

        Args:
            query: The address to search for

        Returns:
            List of matching addresses

        Raises:
            RenovasjonConnectionError: On connection errors
            RenovasjonApiError: On API errors
        """
        # URL encode the query
        encoded_query = quote(query, safe="")
        url = API_ADDRESS_SEARCH.format(query=encoded_query)

        _LOGGER.debug("Searching for address: %s", query)

        data = await self._request(url)

        results = []
        for item in data.get("searchResults", []):
            results.append(AddressSearchResult.from_dict(item))

        # Also include alternate results
        for item in data.get("alternateSearchResults", []):
            results.append(AddressSearchResult.from_dict(item))

        _LOGGER.debug("Found %d addresses", len(results))
        return results

    async def get_disposals(self, address_id: str) -> list[WasteDisposal]:
        """Get waste disposal schedule for an address.

        Args:
            address_id: The UUID of the address

        Returns:
            List of upcoming waste disposals

        Raises:
            RenovasjonConnectionError: On connection errors
            RenovasjonAddressNotFoundError: If address not found
            RenovasjonApiError: On API errors
        """
        url = API_ADDRESS_DETAILS.format(address_id=address_id)

        _LOGGER.debug("Getting disposals for address: %s", address_id)

        data = await self._request(url)

        disposals = []
        for item in data.get("disposals", []):
            try:
                disposals.append(WasteDisposal.from_dict(item))
            except (KeyError, ValueError) as err:
                _LOGGER.warning("Failed to parse disposal: %s - %s", item, err)

        # Sort by date
        disposals.sort(key=lambda d: d.date)

        _LOGGER.debug("Found %d disposals", len(disposals))
        return disposals

    async def get_disposals_by_fraction(self, address_id: str) -> dict[str, list[WasteDisposal]]:
        """Get waste disposals grouped by fraction.

        Args:
            address_id: The UUID of the address

        Returns:
            Dict mapping fraction name to list of disposals
        """
        disposals = await self.get_disposals(address_id)

        by_fraction: dict[str, list[WasteDisposal]] = {}
        for disposal in disposals:
            if disposal.fraction not in by_fraction:
                by_fraction[disposal.fraction] = []
            by_fraction[disposal.fraction].append(disposal)

        return by_fraction
