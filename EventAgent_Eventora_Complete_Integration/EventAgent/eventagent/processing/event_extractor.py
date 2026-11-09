import re


IGNORE_PHRASES = [
    "log in",
    "sign up",
    "never miss",
    "follow",
    "instagram",
    "terms of use",
    "privacy policy",
    "likes",
    "reply",
    "suggested for you",
    "meta",
    "create new account"
]


DEFAULT_INDIAN_CITIES = [
    "Bengaluru", "Bangalore", "Chennai", "Hyderabad", "Mumbai", "Delhi",
    "New Delhi", "Pune", "Kolkata", "Kochi", "Ahmedabad", "Jaipur",
    "Lucknow", "Indore", "Bhubaneswar", "Gurugram", "Noida", "Coimbatore",
]


def extract_event(text, locations=None):

    result = {
        "platform": "Instagram",
        "username": None,
        "event_name": None,
        "city": None,
        "hashtags": [],
        "caption": None
    }

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # ---------------- Username ----------------

    for line in lines:

        if (
            line.islower()
            and " " not in line
            and len(line) < 40
            and line not in ["log", "login", "sign", "signup", "follow"]
        ):
            result["username"] = line
            break

    # ---------------- Caption ----------------

    caption_lines = []

    for line in lines:

        lower = line.lower()

        if any(ignore in lower for ignore in IGNORE_PHRASES):
            continue

        caption_lines.append(line)

    result["caption"] = "\n".join(caption_lines)

    # ---------------- City ----------------

    city_options = locations if locations is not None else DEFAULT_INDIAN_CITIES
    for city in city_options:
        if city and city.casefold() in text.casefold():
            result["city"] = city
            break

    # ---------------- Hashtags ----------------

    result["hashtags"] = re.findall(r"#(\w+)", text)

    # ---------------- Event Name ----------------

    for line in lines:

        lower = line.lower()

        # Ignore Instagram boilerplate
        if any(ignore in lower for ignore in IGNORE_PHRASES):
            continue

        # Ignore usernames
        if line == result["username"]:
            continue

        # Ignore hashtags
        if line.startswith("#"):
            continue

        # Ignore very short lines
        if len(line) < 10:
            continue

        # Ignore very long paragraphs
        if len(line) > 100:
            continue

        result["event_name"] = line
        break

    return result