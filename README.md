# ReMidt Renovasjon - Home Assistant Integration

A Home Assistant custom integration for Norwegian waste collection schedules via [Renovasjonsportal](https://renovasjonsportal.no).

## Features

- Automatic sensor creation for each waste fraction at your address
- **Calendar integration** - view collection dates in Home Assistant's calendar
- **Binary sensors** - "collection today" sensors for each waste type
- Shows next collection date for each waste type
- Supports multiple waste types: Restavfall, Matavfall, Papir, Plastemballasje, Glass og metallemballasje
- Extra attributes include days until collection and upcoming dates
- **Configurable update interval** via options
- **Refresh service** to force data update on demand
- Norwegian (Bokmal) and English translations

## Installation

### HACS Installation (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=omelhus&repository=ha-remidt-renovasjon&category=integration)

Or manually:

1. Open HACS in your Home Assistant instance
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add `https://github.com/omelhus/ha-remidt-renovasjon` and select "Integration" as the category
5. Click "Add"
6. Search for "ReMidt Renovasjon" and install it
7. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/remidt_renovasjon` folder from this repository
2. Copy it to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "ReMidt Renovasjon"
4. Enter your street address (e.g., "Storgata 1, Kristiansund")
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

## Calendar

The integration also creates a calendar entity that displays all waste collection dates. Each collection appears as an all-day event with the waste fraction name as the event title.

To view the calendar:
1. Go to your Home Assistant calendar view
2. The "Renovasjon" calendar will show all upcoming collection dates

## Binary Sensors

The integration creates a "collection today" binary sensor for each waste fraction. These sensors are `on` when collection is scheduled for today, making them ideal for automations.

## Services

### `remidt_renovasjon.refresh`

Force refresh of waste collection data from the API.

| Parameter | Description |
|-----------|-------------|
| `entry_id` | (Optional) Specific config entry to refresh. If omitted, all entries are refreshed. |

## Options

After setup, you can configure the integration by clicking "Configure" on the integration card:

- **Update interval**: How often to fetch new data (1-48 hours, default: 12)

## Example Automations

### Notification the day before collection

```yaml
automation:
  - alias: "Waste collection reminder"
    trigger:
      - platform: numeric_state
        entity_id: sensor.renovasjon_restavfall
        attribute: days_until
        below: 2
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "Waste Collection Tomorrow"
          message: "Remember to put out the residual waste bin!"
```

### Turn on reminder light when collection is today

```yaml
automation:
  - alias: "Collection day indicator"
    trigger:
      - platform: state
        entity_id: binary_sensor.renovasjon_restavfall_today
        to: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.kitchen_indicator
        data:
          color_name: red
```

### Daily notification for any collection

```yaml
automation:
  - alias: "Daily collection check"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: or
        conditions:
          - condition: state
            entity_id: binary_sensor.renovasjon_restavfall_today
            state: "on"
          - condition: state
            entity_id: binary_sensor.renovasjon_matavfall_today
            state: "on"
          - condition: state
            entity_id: binary_sensor.renovasjon_papir_today
            state: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Waste Collection Today"
          message: "Don't forget to put out your bins!"
```

## Development

### Setup

```bash
uv sync --extra dev
```

### Running Tests

```bash
uv run pytest
uv run pytest custom_components/remidt_renovasjon/tests/test_api.py -v  # verbose single file
uv run pytest -k test_search_address_success  # single test
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

### Project Structure

```
custom_components/remidt_renovasjon/
├── api.py           # API client for renovasjonsportal.no
├── binary_sensor.py # "Collection today" binary sensors
├── calendar.py      # Calendar entity for collection events
├── config_flow.py   # Setup wizard, options, and reconfigure flows
├── const.py         # Constants and configuration
├── coordinator.py   # Data update coordinator
├── diagnostics.py   # Integration diagnostics
├── sensor.py        # Sensor entities
├── services.yaml    # Service definitions
└── tests/           # Unit tests
```

## API

This integration uses the public API at `https://kalender.renovasjonsportal.no/api`:

- `GET /address/{query}` - Search for addresses
- `GET /address/{id}/details` - Get disposal schedule for an address

## License

MIT
