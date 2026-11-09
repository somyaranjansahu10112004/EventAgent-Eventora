EVENT_KEYWORDS = [
    "live",
    "concert",
    "show",
    "festival",
    "event",
    "tickets",
    "book now",
    "register",
    "venue",
    "performing",
    "performance",
    "music",
    "party",
    "dj",
    "open mic",
    "comedy",
    "workshop",
    "meetup",
    "food festival",
    "flea market",
    "art exhibition",
    "theatre",
    "dance"
]


def classify_post(text):
    text = text.lower()

    matched = []

    for keyword in EVENT_KEYWORDS:
        if keyword in text:
            matched.append(keyword)

    return {
        "is_event": len(matched) >= 2,
        "matched_keywords": matched
    }