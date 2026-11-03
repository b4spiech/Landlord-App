"""Tour slot rules. All decisions are made in the property's local time zone;
instants are stored in UTC."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.services.timezones import LANDLORD_TIME_ZONE

TOUR_MINUTES = 30
FIRST_START = time(8, 0)
LAST_START = time(19, 30)  # tour ends by 8:00 pm
MIN_LEAD = timedelta(hours=2)  # time to review the request and send the code
MAX_DAYS_AHEAD = 60
ID_PHOTO_RETENTION = timedelta(days=30)


def slot_times() -> list[time]:
    out, t = [], datetime.combine(date.today(), FIRST_START)
    end = datetime.combine(date.today(), LAST_START)
    while t <= end:
        out.append(t.time())
        t += timedelta(minutes=TOUR_MINUTES)
    return out


SLOT_TIMES = slot_times()


def local_to_utc(day: date, start: time, tz: str) -> datetime:
    return datetime.combine(day, start, tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)


def check_slot(day: date, start: time, tz: str, now: datetime | None = None) -> str | None:
    """Return a human-readable problem with this slot, or None if it's bookable."""
    now = now or datetime.now(timezone.utc)
    if start not in SLOT_TIMES:
        return "Pick a start time between 8:00 am and 7:30 pm, on the hour or half hour."
    start_utc = local_to_utc(day, start, tz)
    if start_utc < now + MIN_LEAD:
        return "Please choose a time at least 2 hours from now."
    if start_utc > now + timedelta(days=MAX_DAYS_AHEAD):
        return f"Tours can be booked up to {MAX_DAYS_AHEAD} days ahead."
    return None


def fmt_local(dt_utc: datetime, tz: str) -> str:
    """e.g. 'Sat, Nov 8 at 2:00 PM MST'."""
    local = dt_utc.astimezone(ZoneInfo(tz))
    hour = local.strftime("%I").lstrip("0")
    return f"{local:%a, %b} {local.day} at {hour}:{local:%M %p} {local.tzname()}"


def fmt_time(dt_utc: datetime, tz: str) -> str:
    local = dt_utc.astimezone(ZoneInfo(tz))
    return f"{local.strftime('%I').lstrip('0')}:{local:%M %p} {local.tzname()}"


def fmt_for_landlord(dt_utc: datetime, tz: str) -> str:
    """Property-local time, plus the landlord's time when it differs."""
    text = fmt_local(dt_utc, tz)
    if dt_utc.astimezone(ZoneInfo(tz)).utcoffset() != dt_utc.astimezone(ZoneInfo(LANDLORD_TIME_ZONE)).utcoffset():
        text += f" ({fmt_time(dt_utc, LANDLORD_TIME_ZONE)} your time)"
    return text
