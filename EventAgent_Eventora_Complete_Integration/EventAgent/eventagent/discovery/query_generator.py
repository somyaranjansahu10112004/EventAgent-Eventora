EVENT_CATEGORIES = [
    "stand up comedy",
    "concert",
    "live music",
    "music festival",
    "dj night",

    "workshop",
    "conference",
    "seminar",
    "hackathon",
    "tech meetup",
    "startup meetup",

    "food festival",
    "cultural event",
    "art exhibition",
    "theatre",
    "dance performance",

    "sports event",
    "marathon",
    "cricket match",
    "football match",

    "kids event",
    "family event",

    "college fest",
    "fashion show",
    "book fair",
    "gaming tournament",
    "anime convention",
    "movie screening"
]


EVENT_PATTERNS = [

    # General
    "Upcoming {event} in {city}",
    "{event} in {city} today",
    "{event} in {city} this weekend",

    # Event Platforms
    "site:bookmyshow.com {city} {event}",
    "site:district.in {city} {event}",
    "site:allevents.in {city} {event}",
    "site:insider.in {city} {event}",
    "site:eventify.io {city} {event}",
    "site:theticket9.com {city} {event}",

    # Official pages
    "{event} {city} tickets",
    "{event} {city} official"
]


def generate_queries(location):

    queries = []

    for event in EVENT_CATEGORIES:

        for pattern in EVENT_PATTERNS:

            queries.append(
                pattern.format(
                    city=location,
                    event=event
                )
            )

    return queries


if __name__ == "__main__":

    queries = generate_queries("Bengaluru")

    print(f"Generated {len(queries)} queries.\n")

    for query in queries:
        print(query)