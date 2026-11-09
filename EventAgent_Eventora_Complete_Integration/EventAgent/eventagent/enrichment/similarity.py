from rapidfuzz import fuzz


# Similarity thresholds
NAME_THRESHOLD = 70
ORGANIZER_THRESHOLD = 80
VENUE_THRESHOLD = 75


def normalize(text):
    """
    Normalize text for comparison.
    """
    if not text:
        return ""

    value = str(text).casefold().strip()
    value = " ".join(value.replace(",", " ").split())
    aliases = {"bangalore": "bengaluru", "gurgaon": "gurugram"}
    return aliases.get(value, value)


def similarity(a, b):
    """
    Compute fuzzy similarity between two strings.
    """

    if not a or not b:
        return 0

    return fuzz.token_sort_ratio(
        normalize(a),
        normalize(b)
    )


def is_same_event(event1, event2):
    """
    Decide whether two extracted events represent the same event.

    Rules:
    1. Event names must be similar.
    2. Dates must match if both exist.
    3. Organizer mismatch only lowers confidence.
    4. Venue mismatch only warns.
    5. City mismatch rejects.
    """

    print("\n========== EVENT SIMILARITY ==========\n")

    # --------------------------------------------------
    # Event Name
    # --------------------------------------------------
    name_score = similarity(
        event1.get("event_name"),
        event2.get("event_name")
    )

    print(f"Event Name Similarity : {name_score:.1f}")

    if name_score < NAME_THRESHOLD:
        print("❌ Different event names.")
        return False

    # --------------------------------------------------
    # Date
    # --------------------------------------------------
    date1 = normalize(event1.get("date"))
    date2 = normalize(event2.get("date"))

    if date1 and date2:

        print(f"Date 1 : {date1}")
        print(f"Date 2 : {date2}")

        if date1 != date2:
            print("❌ Date mismatch.")
            return False

    # --------------------------------------------------
    # City
    # --------------------------------------------------
    city1 = normalize(event1.get("city"))
    city2 = normalize(event2.get("city"))

    if city1 and city2:

        print(f"City 1 : {city1}")
        print(f"City 2 : {city2}")

        if city1 != city2:
            print("❌ City mismatch.")
            return False

    # --------------------------------------------------
    # Organizer (Warning only)
    # --------------------------------------------------
    organizer1 = event1.get("organizer")
    organizer2 = event2.get("organizer")

    if organizer1 and organizer2:

        organizer_score = similarity(
            organizer1,
            organizer2
        )

        print(f"Organizer Similarity : {organizer_score:.1f}")

        if organizer_score < ORGANIZER_THRESHOLD:
            print("⚠️ Organizer differs.")

    # --------------------------------------------------
    # Venue (Warning only)
    # --------------------------------------------------
    venue1 = event1.get("venue")
    venue2 = event2.get("venue")

    if venue1 and venue2:

        venue_score = similarity(
            venue1,
            venue2
        )

        print(f"Venue Similarity : {venue_score:.1f}")

        if venue_score < VENUE_THRESHOLD:
            print("⚠️ Venue differs.")

    print("\n✅ Same Event")

    return True


if __name__ == "__main__":

    instagram_event = {
        "event_name": "Standup Comedy Blind Date",
        "date": "2026-07-25",
        "venue": "Phoenix Marketcity",
        "city": "Chennai",
        "organizer": "@kaylircanteen",
    }

    bookmyshow_event = {
        "event_name": "Blind Date - Standup Comedy",
        "date": "2026-07-25",
        "venue": "Phoenix Marketcity, Velachery",
        "city": "Chennai",
        "organizer": "Evam Standup Tamasha",
    }

    print("\nResult:", is_same_event(instagram_event, bookmyshow_event))