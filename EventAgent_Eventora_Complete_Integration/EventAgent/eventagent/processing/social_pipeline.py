"""Resumable social-event pipeline with per-record checkpoints and location scopes."""
import asyncio
import json
import os
import re
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
DIAGNOSTICS_DIR = PROJECT_ROOT / "diagnostics" / "failed_fb_html"
INPUT_FILE = DATA_DIR / "social_results.csv"
OUTPUT_FILE = DATA_DIR / "social_filtered_results.csv"
STATE_FILE = DATA_DIR / "pipeline_state.txt"

from ..scraping.scraper import scrape_page, init_browser, close_browser
from ..enrichment.gemini_extractor import extract_event_with_gemini
from ..enrichment.agent import enrich_event
from ..processing.date_validator import is_upcoming_event


def normalize_name(name):
    if not name:
        return ""
    value = str(name).casefold()
    value = re.sub(r"[^\w ]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def normalize_city(value):
    city = normalize_name(value)
    city = re.sub(r"\bbangalore\b", "bengaluru", city)
    city = re.sub(r"\bgurgaon\b", "gurugram", city)
    return city.replace("bengaluru urban", "bengaluru")


def _checkpoint(position):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(str(max(0, int(position))), encoding="utf-8")
    os.replace(temp, STATE_FILE)


def _read_checkpoint(total_rows):
    try:
        value = int(STATE_FILE.read_text(encoding="utf-8").strip())
        return value if 0 <= value < max(total_rows, 1) else 0
    except (OSError, ValueError):
        return 0


def _blocked_reason(text):
    sample = (text or "").casefold()
    signals = ("log in to facebook", "you must log in", "content isn't available",
               "this content isn't available", "page isn't available", "enable javascript",
               "we restrict certain activity", "sorry, something went wrong")
    return next((signal for signal in signals if signal in sample), None)


def _matches_location(event_city, target_location, allowed_locations):
    if not event_city:
        return True  # Missing city remains visible for later/manual review.
    actual = normalize_city(event_city)
    scopes = [target_location] if target_location else allowed_locations
    scopes = [normalize_city(x) for x in scopes if x]
    if not scopes:
        return True
    return any(actual == scope or actual in scope or scope in actual for scope in scopes)


def _save_output(events):
    columns = ["event_name", "category", "venue", "area", "city", "date", "time",
               "registration_required", "source_url", "price", "host_name"]
    new_df = pd.DataFrame(events).reindex(columns=columns)
    if OUTPUT_FILE.exists():
        old_df = pd.read_csv(OUTPUT_FILE).fillna("")
        for column in columns:
            if column not in old_df:
                old_df[column] = ""
        combined = pd.concat([old_df[columns], new_df.fillna("")], ignore_index=True)
    else:
        combined = new_df
    if not combined.empty:
        combined = combined[combined["date"].apply(is_upcoming_event)]
        combined["_event_key"] = combined.apply(
            lambda row: "|".join((normalize_name(row.get("event_name")), str(row.get("date", "")), normalize_city(row.get("city")))), axis=1
        )
        combined = combined.drop_duplicates(subset=["_event_key"], keep="last").drop(columns=["_event_key"])
        combined = combined.sort_values("date", kind="stable", na_position="last")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT_FILE.with_suffix(".tmp")
    combined.to_csv(temp, index=False)
    os.replace(temp, OUTPUT_FILE)
    return combined


async def run_pipeline(limit=50, locations=None, progress_callback=None):
    """Process a candidate batch. `locations` may contain one or many city names."""
    locations = [str(x).strip() for x in (locations or []) if str(x).strip()]
    allowed_locations = locations[:]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Candidate file not found: {INPUT_FILE}")

    full_df = pd.read_csv(INPUT_FILE).fillna("")
    required = {"Link", "Content_Type"}
    missing = required - set(full_df.columns)
    if missing:
        raise ValueError(f"Candidate CSV is missing required columns: {', '.join(sorted(missing))}")
    full_df = full_df[full_df["Content_Type"].isin(["instagram_post", "instagram_reel", "facebook_event", "facebook_page"])].reset_index(drop=True)
    total_rows = len(full_df)
    if not total_rows:
        _checkpoint(0)
        if progress_callback:
            progress_callback(0, 0, "No eligible social candidates found")
        return []

    start = _read_checkpoint(total_rows)
    end = min(start + max(1, int(limit)), total_rows)
    batch = full_df.iloc[start:end].reset_index(drop=True)
    print(f"Processing candidate rows {start + 1}–{end} of {total_rows}")
    print(f"Location scope: {', '.join(locations) if locations else 'all locations'}")

    results = []
    stats = {"checked": 0, "scraped": 0, "blocked": 0, "extraction_failures": 0,
             "events_detected": 0, "upcoming": 0, "ignored": 0, "not_events": 0}
    await init_browser()
    try:
        for offset, row in batch.iterrows():
            absolute_index = start + offset
            url = str(row.get("Link", "")).strip()
            source_location = str(row.get("Search_Location", "")).strip() or None
            target_location = source_location or (locations[0] if len(locations) == 1 else None)
            stats["checked"] += 1
            if progress_callback:
                progress_callback(offset, len(batch), f"Scraping candidate {offset + 1}/{len(batch)}")
            try:
                page_data = await scrape_page(url)
                page_text = page_data.get("text", "")
                page_html = page_data.get("html", "")
                (LOG_DIR / "latest_page.txt").write_text(page_text, encoding="utf-8")
                (LOG_DIR / "latest_page.html").write_text(page_html, encoding="utf-8")
                if not page_text or len(page_text.strip()) < 100 or _blocked_reason(page_text):
                    stats["blocked"] += 1
                    print(f"Skipped empty or access-restricted page: {url}")
                    continue
                stats["scraped"] += 1
                try:
                    event = extract_event_with_gemini(page_text, target_location=target_location)
                except Exception as exc:
                    stats["extraction_failures"] += 1
                    print(f"Gemini extraction failed for {url}: {exc}")
                    continue
                if not isinstance(event, dict):
                    stats["extraction_failures"] += 1
                    print(f"Gemini returned an invalid response for {url}")
                    continue
                if event.get("extraction_error"):
                    stats["extraction_failures"] += 1
                    print(f"Gemini extraction error for {url}: {event['extraction_error']}")
                    continue
                if not event.get("is_event"):
                    stats["not_events"] += 1
                    continue
                if not event.get("event_name"):
                    stats["extraction_failures"] += 1
                    print(f"Gemini marked the page as an event but returned no event title: {url}")
                    continue
                stats["events_detected"] += 1
                event.update({
                    "url": url, "source_url": url, "title": row.get("Title", ""),
                    "query": row.get("Query", ""), "source_page": row.get("Title", ""),
                    "content_type": row.get("Content_Type", ""),
                })
                event.setdefault("category", None)
                event.setdefault("area", None)
                event.setdefault("price", None)
                event.setdefault("host_name", None)
                event.setdefault("registration_required", False)
                if not _matches_location(event.get("city"), target_location, allowed_locations):
                    stats["ignored"] += 1
                    print(f"Location mismatch: {event.get('city')} (wanted {target_location or allowed_locations})")
                    continue
                with (LOG_DIR / "raw_events.jsonl").open("a", encoding="utf-8") as raw_file:
                    raw_file.write(json.dumps(event, ensure_ascii=False) + "\n")
                if progress_callback:
                    progress_callback(offset, len(batch), f"Enriching: {event.get('event_name') or 'event'}")
                event = await enrich_event(event, target_location=target_location)
                if not _matches_location(event.get("city"), target_location, allowed_locations):
                    stats["ignored"] += 1
                    continue
                if is_upcoming_event(event.get("date")):
                    results.append(event)
                    stats["upcoming"] += 1
                else:
                    stats["ignored"] += 1
            except Exception as exc:
                print(f"Pipeline error for {url}: {exc}")
                with (LOG_DIR / "pipeline_errors.log").open("a", encoding="utf-8") as error_file:
                    error_file.write(f"[{datetime.now().isoformat()}] URL: {url}\n{traceback.format_exc()}\n{'=' * 60}\n")
            finally:
                # Advance only after this row has finished; a crash mid-row retries this row on restart.
                next_position = absolute_index + 1
                _checkpoint(0 if next_position >= total_rows else next_position)
                if progress_callback:
                    progress_callback(offset + 1, len(batch), f"Processed candidate {offset + 1}/{len(batch)}")
            await asyncio.sleep(0.15)
    finally:
        await close_browser()

    saved = _save_output(results)
    # Publish only records processed in this run, not the entire historical CSV.
    # PostgreSQL upsert + outbox are committed atomically by the publisher.
    try:
        from ..publishing.postgres import publish_events
        publish_result = publish_events(results)
        print(f"Eventora publishing: {json.dumps(publish_result, ensure_ascii=False)}")
    except Exception as exc:
        # Preserve successful local extraction even if the shared database is down.
        print(f"Eventora publishing failed; records remain in CSV for retry: {exc}")
        with (LOG_DIR / "pipeline_errors.log").open("a", encoding="utf-8") as error_file:
            error_file.write(f"[{datetime.now().isoformat()}] Eventora publishing failed: {exc}\n")
    print("Pipeline completed")
    print(json.dumps(stats, indent=2))
    print(f"Final dataset contains {len(saved)} records")
    return results


if __name__ == "__main__":
    asyncio.run(run_pipeline())
