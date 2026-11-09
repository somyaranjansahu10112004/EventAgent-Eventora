import requests

from ..config import SERPER_API_KEY, require_api_key


# ==========================================================
# Trusted Domains
# ==========================================================

DOMAIN_PRIORITY = {
    "bookmyshow.com": 100,
    "district.in": 95,
    "insider.in": 90,
    "eventbrite.com": 85,
    "allevents.in": 80,
    "townscript.com": 75,
    "lbb.in": 70,
    "meetup.com": 65,
}


IGNORE_DOMAINS = [
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
]


BAD_PATHS = [
    "/login",
    "/search",
    "/blog",
    "/news",
    "/category",
    "/privacy",
    "/terms",
]


# ==========================================================
# Domain Ranking
# ==========================================================

def get_domain_score(link: str):

    link = link.lower()

    for domain, score in DOMAIN_PRIORITY.items():
        if domain in link:
            return score

    return 0


# ==========================================================
# Google Serper
# ==========================================================

def search_serper(query):

    print(f"\nSearching: {query}")

    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": require_api_key(SERPER_API_KEY, "SERPER_API_KEY"),
        "Content-Type": "application/json",
    }

    payload = {
        "q": query,
        "num": 10,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=20,
    )

    response.raise_for_status()

    return response.json()


# ==========================================================
# Search Builder
# ==========================================================

def build_queries(
    event_name,
    organizer,
    venue,
    city,
    source_account,
):

    queries = []

    # ------------------------------------------------------
    # General Searches
    # ------------------------------------------------------

    queries += [
        f'"{event_name}" {city}',
        f'"{event_name}" {city} venue',
        f'"{event_name}" {city} location',
        f'"{event_name}" {city} address',
        f'"{event_name}" {city} tickets',
        f'"{event_name}" {city} timing',
        f'"{event_name}" {city} schedule',
        f'"{event_name}" {city} event',
    ]

    # ------------------------------------------------------
    # Trusted Ticketing Platforms
    # ------------------------------------------------------

    trusted_sites = [
        "bookmyshow.com",
        "district.in",
        "insider.in",
        "eventbrite.com",
        "allevents.in",
        "townscript.com",
    ]

    for site in trusted_sites:

        queries.append(
            f'"{event_name}" site:{site}'
        )

    # ------------------------------------------------------
    # Venue Searches
    # ------------------------------------------------------

    if venue:

        queries += [
            f'"{event_name}" "{venue}"',
            f'"{venue}" {city}',
            f'"{venue}" address',
            f'"{venue}" location',
            f'"{venue}" events {city}',
            f'"{venue}" live music {city}',
            f'"{venue}" concerts {city}',
        ]

    # ------------------------------------------------------
    # Organizer Searches
    # ------------------------------------------------------

    if organizer:

        queries += [
            f'"{event_name}" {organizer}',
            f'{organizer} {city}',
            f'{organizer} events {city}',
            f'{organizer} venue {city}',
            f'{organizer} location {city}',
        ]

    # ------------------------------------------------------
    # Instagram Username
    # ------------------------------------------------------

    if source_account:

        username = source_account.replace("@", "")

        queries += [
            f'"{event_name}" {username}',
            f'{username} {city}',
            f'{username} events',
        ]

    # Remove duplicates while preserving order
    return list(dict.fromkeys(queries))


# ==========================================================
# Main Search
# ==========================================================

def search_missing_event_info(
    event_name,
    organizer=None,
    venue=None,
    city="India",
    source_account=None,
):

    queries = build_queries(
        event_name,
        organizer,
        venue,
        city,
        source_account,
    )

    print("\n========== SEARCH QUERIES ==========")

    for q in queries:
        print(q)

    print("====================================")

    seen_links = set()
    results = []

    # Keep enrichment bounded; the most relevant general, venue and organizer queries come first.
    for query in queries[:12]:

        try:

            data = search_serper(query)

        except Exception as e:

            print(f"Search failed: {e}")
            continue

        organic = data.get("organic", [])

        for item in organic:

            link = item.get("link", "")

            if not link:
                continue

            lower = link.lower()

            # Ignore unwanted domains
            if any(domain in lower for domain in IGNORE_DOMAINS):
                continue

            # Ignore utility pages
            if any(path in lower for path in BAD_PATHS):
                continue

            if lower in seen_links:
                continue

            seen_links.add(lower)

            results.append({

                "title": item.get("title", ""),

                "link": link,

                "snippet": item.get("snippet", ""),

                "score": get_domain_score(lower)

            })

        # Plenty of candidates
        if len(results) >= 30:
            break

    # Highest priority domains first
    results.sort(
        key=lambda x: (
            x["score"],
            len(x["title"])
        ),
        reverse=True,
    )

    print(f"\nFiltered Results : {len(results)}")

    print("\n========== TOP RESULTS ==========\n")

    for r in results[:10]:

        print(f"[{r['score']}] {r['title']}")
        print(r["link"])
        print()

    # Remove internal ranking score
    for r in results:
        r.pop("score")

    return results


# ==========================================================
# Testing
# ==========================================================

if __name__ == "__main__":

    results = search_missing_event_info(

        event_name="Standup Comedy Blind Date",

        organizer="kaylircanteen",

        venue="Phoenix Marketcity",

        city="India",

        source_account="@kaylircanteen",

    )

    print("\n========== FINAL RESULTS ==========\n")

    for i, result in enumerate(results, start=1):

        print("=" * 80)

        print(f"Result {i}")

        print("Title   :", result["title"])

        print("Link    :", result["link"])

        print("Snippet :", result["snippet"])