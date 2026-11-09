from ..processing.date_validator import is_upcoming_event

tests = [
    "Saturday, 7 Feb 2026",
    "7 Feb 2026",
    "July 15, 2026",
    "May 03rd",
    "June 14, June 20, June 21",
    "August 24, 2025"
]

for t in tests:
    print(t, "->", is_upcoming_event(t))