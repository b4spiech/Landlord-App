"""Time-zone helpers. Store instants in UTC; show/choose times in a property's local zone."""

from __future__ import annotations

from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Landlord's own zone, for notifications ("4:00 pm your time").
LANDLORD_TIME_ZONE = "America/Detroit"

# Default zone per state when a property has none set. States that span zones
# use the zone covering most of the population.
STATE_DEFAULT_TZ = {
    "AZ": "America/Phoenix",  # no daylight saving (except the Navajo Nation)
    "MI": "America/Detroit",
    "CA": "America/Los_Angeles", "OR": "America/Los_Angeles", "WA": "America/Los_Angeles",
    "NV": "America/Los_Angeles",
    "CO": "America/Denver", "NM": "America/Denver", "UT": "America/Denver", "MT": "America/Denver",
    "WY": "America/Denver", "ID": "America/Boise",
    "TX": "America/Chicago", "IL": "America/Chicago", "MN": "America/Chicago", "WI": "America/Chicago",
    "MO": "America/Chicago", "IA": "America/Chicago", "OK": "America/Chicago", "KS": "America/Chicago",
    "NE": "America/Chicago", "LA": "America/Chicago", "AR": "America/Chicago", "MS": "America/Chicago",
    "AL": "America/Chicago", "TN": "America/Chicago", "ND": "America/Chicago", "SD": "America/Chicago",
    "FL": "America/New_York", "GA": "America/New_York", "NY": "America/New_York", "OH": "America/New_York",
    "IN": "America/Indiana/Indianapolis", "KY": "America/New_York", "NC": "America/New_York",
    "SC": "America/New_York", "VA": "America/New_York", "PA": "America/New_York", "NJ": "America/New_York",
    "MA": "America/New_York", "MD": "America/New_York", "CT": "America/New_York", "DC": "America/New_York",
    "DE": "America/New_York", "ME": "America/New_York", "NH": "America/New_York", "VT": "America/New_York",
    "RI": "America/New_York", "WV": "America/New_York",
    "AK": "America/Anchorage", "HI": "Pacific/Honolulu",
}

FALLBACK_TZ = "America/Phoenix"


def validate_time_zone(value: Optional[str]) -> Optional[str]:
    """Pydantic validator: empty -> None; otherwise must be a real IANA zone."""
    if value is None or not str(value).strip():
        return None
    value = str(value).strip()
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"Unknown time zone '{value}'. Use an IANA name like America/Phoenix.")
    return value


def property_time_zone(prop) -> str:
    """The zone a property's tour times are in."""
    if getattr(prop, "time_zone", None):
        return prop.time_zone
    return STATE_DEFAULT_TZ.get((prop.state or "").upper(), FALLBACK_TZ)
