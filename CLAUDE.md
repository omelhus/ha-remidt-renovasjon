# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom integration for ReMidt Renovasjon - Norwegian waste collection schedules via renovasjonsportal.no. Creates sensors for each waste fraction (restavfall, matavfall, papir, plastemballasje, glass/metall) showing the next collection date.

## Commands

Install dependencies:
```bash
uv sync --extra dev
```

Run tests:
```bash
uv run pytest
uv run pytest custom_components/remidt_renovasjon/tests/test_api.py  # single file
uv run pytest -k test_search_address_success  # single test by name
```

Lint:
```bash
uv run ruff check .
uv run ruff format .
```

## Architecture

Standard Home Assistant integration pattern in `custom_components/remidt_renovasjon/`:

- `api.py` - Async API client using aiohttp. Dataclasses: `AddressSearchResult`, `WasteDisposal`. Custom exceptions: `RenovasjonApiError`, `RenovasjonConnectionError`, `RenovasjonAddressNotFoundError`
- `coordinator.py` - `RenovasjonCoordinator` extends `DataUpdateCoordinator`, fetches data every 12 hours. `RenovasjonData` container provides helper methods for accessing disposal schedules
- `sensor.py` - `RenovasjonSensor` extends `CoordinatorEntity`, one sensor per waste fraction, device_class=DATE
- `config_flow.py` - Two-step flow: address search then selection from results
- `const.py` - Domain, API endpoints, config keys, waste fraction definitions

## API

Base URL: `https://kalender.renovasjonsportal.no/api`
- Address search: `/address/{query}`
- Address details: `/address/{address_id}/details`

## Testing

Tests in `custom_components/remidt_renovasjon/tests/`. Mock responses defined in `conftest.py`. Use `create_mock_response()` helper for aiohttp response mocks.
