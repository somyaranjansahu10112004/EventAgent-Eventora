"""Compact query templates to keep multi-city discovery bounded."""

EVENT_TYPES = [
    "concert", "live music", "dj night", "stand up comedy", "open mic",
    "workshop", "startup meetup", "tech meetup", "food festival", "flea market",
    "art exhibition", "theatre", "dance performance", "music festival",
    "cultural event", "college fest", "gaming tournament", "marathon",
    "photography walk",
]


def generate_queries(location):
    location = str(location).strip()
    if not location:
        raise ValueError("Location cannot be empty")
    queries = []
    for event_type in EVENT_TYPES:
        queries.extend([
            f"site:instagram.com {location} {event_type} event",
            f"site:facebook.com/events {location} {event_type}",
        ])
    return queries
