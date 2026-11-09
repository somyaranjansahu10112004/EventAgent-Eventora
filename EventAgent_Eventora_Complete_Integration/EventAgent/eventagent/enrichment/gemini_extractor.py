import json
import re
from datetime import date

from ..config import GEMINI_API_KEY, GEMINI_MODEL, require_api_key

def _get_model():
    """Initialize the Gemini SDK lazily so API/dashboard imports work without credentials."""
    import google.generativeai as genai
    genai.configure(api_key=require_api_key(GEMINI_API_KEY, "GEMINI_API_KEY"))
    return genai.GenerativeModel(GEMINI_MODEL)


def extract_event_with_gemini(text: str, target_location: str | None = None):

    # Handle empty input safely
    if not text:
        return {
            "is_event": False,
            "event_name": None,
            "date": None,
            "time": None,
            "venue": None,
            "area": None,
            "city": None,
            "category": None,
            "price": None,
            "host_name": None,
            "registration_required": False
        }

    # Facebook pages often contain a lot of boilerplate before the
    # actual event description, so allow Gemini to see more content.
    MAX_TEXT_LENGTH = 20000
    text = text[:MAX_TEXT_LENGTH]

    today = date.today().isoformat()

    prompt = f"""
You are an expert AI event extraction system specialized in extracting structured event information from Instagram posts, Instagram reels, Facebook event pages, Facebook posts, and official event announcements.

The input is raw scraped text from a webpage or social media page.

Today's date is {today}.

====================================================
YOUR TASK
====================================================

Determine whether this content is announcing ONE real event.

If yes, extract the event details.

If no, return is_event=false.

====================================================
IMPORTANT RULES
====================================================

1. Return ONLY valid JSON.
2. Never explain anything.
3. Never use markdown.
4. Never return text outside JSON.
5. Use null for unavailable fields.
6. Extract ONLY ONE event.
7. If multiple events are present, extract ONLY the first upcoming event relevant to the requested location.
8. Ignore advertisements that are not promoting a specific event.
9. Ignore memes, motivational posts, random reels, personal updates and news.
10. Ignore organizer profile pages unless an actual event is mentioned.
11. Ticket booking pages are valid event pages.

====================================================
LOCATION FILTER
====================================================

Requested location: {target_location or "Not specified; identify the event city from the content"}.

Prefer events taking place in the requested location when one is supplied.
Return the actual city where the event takes place in the city field.
Do not force a Chennai-only restriction. If the city cannot be determined, return null.

====================================================
EVENT NAME
====================================================

Choose the ACTUAL event title.

Usually this is

• concert title
• workshop title
• meetup title
• exhibition title
• stand-up show title
• festival name

Prefer poster titles over promotional captions.

GOOD

The One

Thenisai Thendral Deva Live

Startup Mixer Chennai

BAD

Book Now

Limited Seats

Don't Miss It

====================================================
DATE
====================================================

Return ONLY

YYYY-MM-DD

Examples

2026-07-24

2026-08-05

If relative dates exist, convert them using today's date.

Examples

Tomorrow

This Saturday

Next Sunday

This Weekend

Next Weekend

Convert them into YYYY-MM-DD.

If multiple dates exist,
return ONLY the next upcoming date.

Otherwise return null.

====================================================
TIME
====================================================

Examples

7 PM

7:30 PM

10:00 AM

Return null if unavailable.

====================================================
VENUE
====================================================

Extract venue names only.

Examples

YMCA Grounds

Express Avenue

Phoenix Marketcity

Forum Mall

Anna Centenary Library

Do NOT return city names as venue.

====================================================
AREA
====================================================

Extract the locality or neighbourhood where the venue is located.

Examples:

Phoenix Marketcity, Velachery
→ area = Velachery

Express Avenue, Royapettah
→ area = Royapettah

YMCA Grounds, Nandanam
→ area = Nandanam

Return only the locality name.
If unavailable return null.

====================================================
CITY
====================================================

Return the actual event city if clearly mentioned. Otherwise null.

====================================================
CATEGORY
====================================================

Choose ONE category

Concert
Workshop
Stand-up Comedy
Meetup
Conference
Networking
Food Festival
Exhibition
Theatre
Dance
Sports
Gaming
College Fest
Other

====================================================
PRICE
====================================================

Extract the ticket price.

Examples:

FREE
Free Entry
₹499
₹499/PERSON
Rs.250
INR 999

Return ONLY the price text exactly as shown.
If no price is mentioned, return null.

====================================================
HOST NAME
====================================================

Extract the host/person/company shown as:
BY Meet & Mingle
BY Dr. Janaki Rangarajan
Hosted by XYZ

Return only the host name.

Examples:
Meet & Mingle
Dr. Janaki Rangarajan
Rotaract Club

Return null if unavailable.

====================================================
REGISTRATION REQUIRED
====================================================

Return true if attending requires any of the following:

Registration
RSVP
Sign Up
Book Tickets
Buy Tickets
Get Tickets
Reserve Seat
Advance Booking
Entry Pass

Return false if the event is open to everyone, walk-ins are allowed, or no prior registration or booking is mentioned.

====================================================
OUTPUT FORMAT
====================================================

If event

{{
"is_event": true,
"event_name": "",
"date": "",
"time": "",
"venue": "",
"area": "",
"city": "",
"category": "",
"price": "",
"host_name": "",
"registration_required": false
}}

If not

{{
"is_event": false,
"event_name": null,
"date": null,
"time": null,
"venue": null,
"area": null,
"city": null,
"category": null,
"price": null,
"host_name": null,
"registration_required": false
}}

====================================================
SCRAPED CONTENT
====================================================

{text}
"""

    try:

        response = _get_model().generate_content(prompt)

        if not response.text:
            raise ValueError("Gemini returned an empty response.")

        output = response.text.strip()

        if output.startswith("```json"):
            output = output.replace("```json", "").replace("```", "").strip()

        elif output.startswith("```"):
            output = output.replace("```", "").strip()

        data = json.loads(output)

        defaults = {
            "is_event": False,
            "event_name": None,
            "date": None,
            "time": None,
            "venue": None,
            "area": None,
            "city": None,
            "category": None,
            "price": None,
            "host_name": None,
            "registration_required": False
        }

        for key, value in defaults.items():
            data.setdefault(key, value)

        # =====================================================
        # Registration Keyword Fallback
        # =====================================================

        if not data.get("registration_required"):

            reg_keywords = [
                "register",
                "registration",
                "rsvp",
                "sign up",
                "signup",
                "book now",
                "book ticket",
                "book tickets",
                "buy ticket",
                "buy tickets",
                "get tickets",
                "ticket",
                "tickets",
                "reserve",
                "reservation",
                "reserve seat",
                "entry pass",
                "limited seats",
                "book your seat",
                "apply now",
                "register now",
                "book here",
                "reserve now",
                "join now",
                "enroll",
                "sold out"
            ]

            lower_text = text.lower()

            if any(keyword in lower_text for keyword in reg_keywords):
                data["registration_required"] = True

        return data

    except Exception as e:

        print("\nGemini Error:")
        print(e)

        return {
            "is_event": False,
            "event_name": None,
            "date": None,
            "time": None,
            "venue": None,
            "area": None,
            "city": None,
            "category": None,
            "price": None,
            "host_name": None,
            "registration_required": False,
            "extraction_error": str(e),
        }


if __name__ == "__main__":

    with open("page_text.txt", "r", encoding="utf-8") as f:
        page_text = f.read()

    result = extract_event_with_gemini(page_text)

    print(json.dumps(result, indent=4))

    with open("event_details.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)