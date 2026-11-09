"""Conservative event-date validation with support for ISO dates and ranges."""
from datetime import date, datetime
from dateutil import parser
import re


def parse_event_date(value, today=None):
    if value is None or not str(value).strip():
        return None
    today = today or date.today()
    text = str(value).strip()
    # For a date range, validate the end date so currently-running festivals remain upcoming.
    parts = re.split(r"\s+(?:-|–|to)\s+", text, maxsplit=1, flags=re.I)
    candidate = parts[-1].strip()
    # Do not interpret a bare year or month/year as a concrete event date.
    has_day = bool(re.search(r"\b(?:0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?\b", candidate, re.I))
    has_numeric_date = bool(re.search(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", candidate))
    if not (has_day or has_numeric_date):
        return None
    # ISO dates are unambiguous and should not be reinterpreted.
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", candidate)
    if iso:
        try:
            return date.fromisoformat(iso.group(1))
        except ValueError:
            return None
    # Reject strings containing multiple independent dates rather than guessing.
    try:
        parsed = parser.parse(candidate, fuzzy=True, default=datetime(today.year, 1, 1))
    except (ValueError, OverflowError, TypeError):
        return None
    if not re.search(r"\b(?:19|20)\d{2}\b", candidate):
        parsed = parsed.replace(year=today.year)
        # If a yearless date has already passed, it is ambiguous; do not silently roll it forward.
    return parsed.date()


def is_upcoming_event(event_date, today=None):
    parsed = parse_event_date(event_date, today=today)
    return bool(parsed and parsed >= (today or date.today()))
