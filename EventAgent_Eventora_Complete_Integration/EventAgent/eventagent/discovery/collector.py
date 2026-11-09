import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
import time

from ..discovery.search import search
from ..discovery.query_generator import generate_queries


# Trusted event platforms
TRUSTED_DOMAINS = [
    "bookmyshow.com",
    "district.in",
    "allevents.in",
    "insider.in",
    "eventify.io",
    "theticket9.com",
    "events",
    "tickets"
]


def collect_results(location):

    queries = generate_queries(location)

    collected = []

    for query in queries:

        print("=" * 80)
        print(f"Searching: {query}")

        results = search(query)

        if "organic" not in results:
            continue

        for item in results["organic"]:

            link = item.get("link", "").lower()

            # Keep trusted websites first
            if not any(domain in link for domain in TRUSTED_DOMAINS):
                continue

            collected.append({

                "Query": query,

                "Title": item.get("title"),

                "Link": item.get("link"),

                "Snippet": item.get("snippet")

            })

        time.sleep(1)

    df = pd.DataFrame(collected)

    if not df.empty:
        df.drop_duplicates(subset=["Link"], inplace=True)

    return df


if __name__ == "__main__":
    import argparse
    import pandas as pd

    parser = argparse.ArgumentParser(description="Collect trusted event-platform results")
    parser.add_argument("--locations", default="Bengaluru", help="Semicolon-separated locations")
    args = parser.parse_args()
    locations = [item.strip() for item in args.locations.split(";") if item.strip()]
    frames = []
    for location in locations:
        frame = collect_results(location)
        frame["Search_Location"] = location
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not df.empty:
        df = df.drop_duplicates(subset=["Link"], keep="first")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_DIR / "search_results.csv", index=False)
    print(f"Saved {len(df)} trusted event-platform results for {', '.join(locations)}")