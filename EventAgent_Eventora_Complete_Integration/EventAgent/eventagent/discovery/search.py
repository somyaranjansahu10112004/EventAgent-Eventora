"""Serper search client with bounded timeouts and retries."""
import time
import requests
from ..config import SERPER_API_KEY, require_api_key

URL = "https://google.serper.dev/search"


def search(query, retries=2, timeout=20):
    headers = {
        "X-API-KEY": require_api_key(SERPER_API_KEY, "SERPER_API_KEY"),
        "Content-Type": "application/json",
    }
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = requests.post(URL, headers=headers, json={"q": query}, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2 ** attempt, 4))
    raise RuntimeError(f"Serper search failed after {retries + 1} attempts: {last_error}") from last_error


if __name__ == "__main__":
    from .social_query_generator import generate_queries
    for query in generate_queries("Bengaluru"):
        print(f"\nSearching: {query}")
        print(search(query).get("organic", []))
        time.sleep(1)
