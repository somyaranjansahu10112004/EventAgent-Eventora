"""End-to-end EventAgent -> PostgreSQL -> Eventora smoke test.

Run from the EventAgent directory after installing requirements and setting
DATABASE_URL. Eventora API must be running against the same database.
The script creates, updates, verifies, and removes one clearly named test event.
"""
from __future__ import annotations
import os, sys, time, uuid
from datetime import date, timedelta
from urllib.error import URLError, HTTPError
from urllib.request import urlopen
import json

API_BASE = os.getenv("EVENTORA_API_URL", "http://127.0.0.1:5000").rstrip("/")
if not os.getenv("DATABASE_URL"):
    raise SystemExit("ERROR: DATABASE_URL is not set. Configure the same database in both backends.")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "EventAgent")))
from eventagent.publishing.postgres import publish_events  # noqa: E402
import psycopg  # noqa: E402

suffix = uuid.uuid4().hex[:10]
name1 = f"EventAgent Integration Test {suffix}"
name2 = name1 + " Updated"
city = "Bengaluru"
event_date = (date.today() + timedelta(days=14)).isoformat()
source = f"https://example.org/eventagent-integration-test/{suffix}"
record = {"id": f"integration-{suffix}", "event_name": name1, "city": city,
          "date": event_date, "source_url": source, "category": "Integration Test",
          "venue": "Test Venue", "description": "Temporary integration test record"}


def fetch_event():
    with urlopen(f"{API_BASE}/api/events?includePast=true&limit=100", timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return next((e for e in payload.get("events", []) if e.get("id") == record["id"]), None)

try:
    print("[1/5] Publishing a test event through EventAgent...")
    result = publish_events([record])
    if result.get("published") != 1:
        raise RuntimeError(f"EventAgent did not publish the test record: {result}")

    print("[2/5] Waiting for Eventora to load the shared database...")
    found = None
    for _ in range(20):
        try:
            found = fetch_event()
            if found:
                break
        except (URLError, HTTPError):
            pass
        time.sleep(2)
    if not found:
        raise RuntimeError("Event not visible through Eventora API. Check DATABASE_URL, API health, and refresh interval.")
    if found.get("eventName") != name1:
        raise RuntimeError(f"Unexpected Eventora event payload: {found}")

    print("[3/5] Updating the same event ID through EventAgent...")
    record["event_name"] = name2
    result2 = publish_events([record])
    if result2.get("published") != 1:
        raise RuntimeError(f"Event update failed: {result2}")

    print("[4/5] Confirming Eventora reflects the update...")
    found = None
    for _ in range(20):
        found = fetch_event()
        if found and found.get("eventName") == name2:
            break
        time.sleep(2)
    if not found or found.get("eventName") != name2:
        raise RuntimeError("Eventora did not reflect the updated event within 40 seconds.")

    print("[5/5] Checking database idempotency and cleaning up...")
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events WHERE id=%s", (record["id"],))
            count = cur.fetchone()[0]
            if count != 1:
                raise RuntimeError(f"Expected one canonical row, found {count}")
            cur.execute("DELETE FROM events WHERE id=%s", (record["id"],))
    print("PASS: create -> publish -> Eventora visibility -> update -> idempotency -> cleanup")
except Exception as exc:
    # Best-effort cleanup; preserve the original diagnostic.
    try:
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM events WHERE id=%s", (record["id"],))
    except Exception:
        pass
    raise SystemExit(f"FAIL: {exc}")
