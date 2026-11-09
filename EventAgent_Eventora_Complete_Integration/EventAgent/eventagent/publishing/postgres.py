"""Publish validated EventAgent records to the shared Eventora PostgreSQL database.

Publishing is idempotent: canonical event IDs are stable, event rows are upserted,
and an outbox entry is written in the same transaction. No database URL means
publishing stays disabled and the existing CSV workflow continues unchanged.
"""
from __future__ import annotations

import hashlib
import os
from datetime import date, datetime
from typing import Any


def _event_id(record: dict[str, Any]) -> str:
    explicit = str(record.get("id") or record.get("event_id") or "").strip()
    if explicit:
        return explicit
    fields = ("event_name", "eventName", "name", "date", "event_date", "city", "venue")
    values = [str(next((record.get(k) for k in (field,) if record.get(k)), "") or "").strip().casefold() for field in fields]
    return "evt-" + hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()[:24]


def _iso_date(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        # Preserve unambiguous ISO dates; day-first parsing is only for human dates.
        try:
            return date.fromisoformat(raw[:10]).isoformat()
        except ValueError:
            pass
        from dateutil.parser import parse
        parsed = parse(raw, fuzzy=False, dayfirst=True)
        if not re_full_date(raw, parsed):
            return None
        return parsed.date().isoformat()
    except (ValueError, OverflowError, TypeError):
        return None


def re_full_date(raw: str, parsed: datetime) -> bool:
    """Reject year-only strings and date values with no meaningful date tokens."""
    import re
    return bool(re.search(r"\d", raw) or re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", raw, re.I)) and len(raw) >= 4


def eligible_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Require a title, city, concrete future date and traceable source URL."""
    from eventagent.processing.date_validator import is_upcoming_event
    eligible: list[dict[str, Any]] = []
    rejected = 0
    for record in records:
        name = str(record.get("event_name") or record.get("eventName") or record.get("name") or "").strip()
        city = str(record.get("city") or record.get("location") or "").strip()
        source = str(record.get("source_url") or record.get("sourceUrl") or record.get("url") or "").strip()
        raw_date = record.get("date") or record.get("event_date")
        iso_date = _iso_date(raw_date)
        if not (name and city and source.startswith(("https://", "http://")) and iso_date and is_upcoming_event(iso_date)):
            rejected += 1
            continue
        normalized = dict(record)
        normalized.update({"event_name": name, "city": city, "date": iso_date, "source_url": source})
        eligible.append(normalized)
    return eligible, rejected


def publish_events(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Upsert eligible events and enqueue an audit/delivery record atomically."""
    if os.getenv("AUTO_PUBLISH_ENABLED", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        return {"enabled": False, "published": 0, "rejected": len(records), "reason": "AUTO_PUBLISH_ENABLED is false"}
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn:
        return {"enabled": False, "published": 0, "rejected": 0, "reason": "DATABASE_URL is not configured; CSV output remains active"}
    eligible, rejected = eligible_records(records)
    if not eligible:
        return {"enabled": True, "published": 0, "rejected": rejected}
    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError as exc:
        raise RuntimeError("Install psycopg[binary] to enable automatic publishing") from exc

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for record in eligible:
                event_id = _event_id(record)
                payload = {**record, "id": event_id, "eventName": record["event_name"], "date": record["date"]}
                cur.execute("""INSERT INTO events
                    (id,event_name,category,venue,area,city,event_date,original_date,event_time,
                     registration_required,source_url,original_source_value,price,host_name,instagram_id,
                     status,is_published,confidence_score,extra,updated_at,published_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'published',TRUE,%s,%s,NOW(),NOW())
                    ON CONFLICT(id) DO UPDATE SET event_name=EXCLUDED.event_name,category=EXCLUDED.category,
                    venue=EXCLUDED.venue,area=EXCLUDED.area,city=EXCLUDED.city,event_date=EXCLUDED.event_date,
                    original_date=EXCLUDED.original_date,event_time=EXCLUDED.event_time,
                    registration_required=EXCLUDED.registration_required,source_url=EXCLUDED.source_url,
                    original_source_value=EXCLUDED.original_source_value,price=EXCLUDED.price,
                    host_name=EXCLUDED.host_name,status='published',is_published=TRUE,
                    confidence_score=EXCLUDED.confidence_score,extra=EXCLUDED.extra,updated_at=NOW(),
                    published_at=COALESCE(events.published_at,NOW())""",
                    (event_id, record["event_name"], record.get("category"), record.get("venue"),
                     record.get("area"), record["city"], record["date"], record.get("original_date") or record.get("originalDate"),
                     record.get("time"), str(record.get("registration_required") or record.get("registrationRequired") or ""),
                     record["source_url"], record.get("original_source_value") or record.get("originalSourceValue"),
                     record.get("price"), record.get("host_name") or record.get("hostName"), record.get("instagram_id") or record.get("instagramId"),
                     record.get("confidence_score"), Jsonb(payload)))
                cur.execute("INSERT INTO event_sources(event_id,source_url,platform) VALUES(%s,%s,%s) ON CONFLICT(event_id,source_url) DO NOTHING",
                            (event_id, record["source_url"], "social"))
                cur.execute("INSERT INTO sync_outbox(event_id,action,payload) VALUES(%s,'upsert',%s)",
                            (event_id, Jsonb(payload)))
    return {"enabled": True, "published": len(eligible), "rejected": rejected}
