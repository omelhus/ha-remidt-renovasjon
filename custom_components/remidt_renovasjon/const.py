"""Constants for the ReMidt Renovasjon integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "remidt_renovasjon"

# API endpoints
API_BASE_URL: Final = "https://kalender.renovasjonsportal.no/api"
API_ADDRESS_SEARCH: Final = f"{API_BASE_URL}/address/{{query}}"
API_ADDRESS_DETAILS: Final = f"{API_BASE_URL}/address/{{address_id}}/details"

# Config keys
CONF_ADDRESS_ID: Final = "address_id"
CONF_ADDRESS_NAME: Final = "address_name"
CONF_MUNICIPALITY: Final = "municipality"

# Update interval - default is 12 hours, configurable via options
DEFAULT_UPDATE_INTERVAL_HOURS: Final = 12
UPDATE_INTERVAL: Final = timedelta(hours=DEFAULT_UPDATE_INTERVAL_HOURS)

# Options keys
CONF_UPDATE_INTERVAL: Final = "update_interval"

# Calendar lookahead for finding next event
CALENDAR_LOOKAHEAD_DAYS: Final = 365

# Waste fractions with icons and translations
WASTE_FRACTIONS: Final = {
    "Restavfall": {
        "icon": "mdi:trash-can",
        "translation_key": "restavfall",
    },
    "Matavfall": {
        "icon": "mdi:food-apple",
        "translation_key": "matavfall",
    },
    "Papir": {
        "icon": "mdi:newspaper",
        "translation_key": "papir",
    },
    "Plastemballasje": {
        "icon": "mdi:bottle-soda-outline",
        "translation_key": "plastemballasje",
    },
    "Glass og metallemballasje": {
        "icon": "mdi:bottle-wine",
        "translation_key": "glass_metall",
    },
}

# Attribute keys
ATTR_DAYS_UNTIL: Final = "days_until"
ATTR_NEXT_DATE: Final = "next_date"
ATTR_UPCOMING_DATES: Final = "upcoming_dates"
ATTR_FRACTION: Final = "fraction"
ATTR_ADDRESS: Final = "address"
ATTR_MUNICIPALITY: Final = "municipality"
