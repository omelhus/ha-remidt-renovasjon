# Renovasjonsportal - Home Assistant Integration

A Home Assistant custom integration for Norwegian waste collection schedules via [Renovasjonsportal](https://renovasjonsportal.no).

## Features

- Automatic sensor creation for each waste fraction at your address
- Shows next collection date for each waste type
- Supports multiple waste types: Restavfall, Matavfall, Papir, Plastemballasje, Glass og metallemballasje
- Extra attributes include days until collection and upcoming dates
- Norwegian (Bokmal) and English translations

## Installation

### Manual Installation

1. Copy the `renovasjon` folder to your Home Assistant `custom_components` directory:
   ```
   custom_components/
   └── renovasjon/
       ├── __init__.py
       ├── api.py
       ├── config_flow.py
       ├── const.py
       ├── coordinator.py
       ├── manifest.json
       ├── sensor.py
       ├── strings.json
       └── translations/
   ```

2. Restart Home Assistant

### HACS Installation

This integration is not yet available in HACS. Use manual installation.

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Renovasjonsportal"
4. Enter your street address (e.g., "Storgata 1, Oslo")
5. Select your address from the search results

## Sensors

The integration creates one sensor per waste fraction found for your address. Each sensor:

- Has device class `date` showing the next collection date
- Includes attributes:
  - `days_until`: Days until next collection
  - `next_date`: Next collection date (ISO format)
  - `upcoming_dates`: List of upcoming collection dates
  - `address`: Your configured address
  - `municipality`: Your municipality

## Development

### Setup

```bash
uv sync --extra dev
```

### Running Tests

```bash
uv run pytest
uv run pytest tests/test_api.py -v  # verbose single file
uv run pytest -k test_search_address_success  # single test
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

### Project Structure

```
renovasjon/
├── api.py           # API client for renovasjonsportal.no
├── config_flow.py   # Setup wizard (address search and selection)
├── const.py         # Constants and configuration
├── coordinator.py   # Data update coordinator
├── sensor.py        # Sensor entities
└── tests/           # Unit tests
```

## API

This integration uses the public API at `https://kalender.renovasjonsportal.no/api`:

- `GET /address/{query}` - Search for addresses
- `GET /address/{id}/details` - Get disposal schedule for an address

## License

MIT
