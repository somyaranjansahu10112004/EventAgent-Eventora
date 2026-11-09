"""Collect Instagram/Facebook candidate links for one or more locations."""
import time
import pandas as pd
from pathlib import Path
from ..discovery.search import search
from ..discovery.social_query_generator import generate_queries

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TRUSTED_DOMAINS = ("instagram.com", "facebook.com")


def get_content_type(link):
    link = (link or "").lower()
    if "instagram.com/reel/" in link:
        return "instagram_reel"
    if "instagram.com/p/" in link:
        return "instagram_post"
    if "instagram.com/" in link:
        return "instagram_profile"
    if "facebook.com/events/" in link:
        return "facebook_event"
    if "facebook.com/" in link:
        return "facebook_page"
    return "unknown"


def collect_results(location, progress_callback=None):
    location = str(location).strip()
    if not location:
        raise ValueError("A non-empty location is required")
    queries = generate_queries(location)
    collected, seen = [], set()
    for index, query in enumerate(queries, start=1):
        print(f"Searching {index}/{len(queries)}: {query}")
        try:
            results = search(query)
        except Exception as exc:
            print(f"Search query failed and was skipped: {exc}")
            continue
        for item in results.get("organic", []):
            link = item.get("link", "")
            if not link or not any(domain in link.lower() for domain in TRUSTED_DOMAINS):
                continue
            normalized = link.split("?")[0].rstrip("/").lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            collected.append({
                "Query": query,
                "Content_Type": get_content_type(link),
                "Title": item.get("title", ""),
                "Link": link,
                "Snippet": item.get("snippet", ""),
                "Search_Location": location,
            })
        if progress_callback:
            progress_callback(index, len(queries), f"Discovering {location}: query {index}/{len(queries)}")
        time.sleep(0.25)
    return pd.DataFrame(collected, columns=["Query", "Content_Type", "Title", "Link", "Snippet", "Search_Location"])


if __name__ == "__main__":
    df = collect_results("Bengaluru")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_DIR / "social_results.csv", index=False)
    print(f"Saved {len(df)} unique social links")
