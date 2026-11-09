from datetime import date

from eventagent.processing.date_validator import is_upcoming_event
from eventagent.processing.social_pipeline import normalize_city, _matches_location
from eventagent.api.app import _parse_locations


def test_upcoming_iso_date():
    assert is_upcoming_event("2026-11-28", today=date(2026, 11, 7))


def test_past_iso_date():
    assert not is_upcoming_event("2025-08-24", today=date(2026, 11, 7))


def test_date_range_uses_end_date():
    assert is_upcoming_event("2026-11-01 - 2026-11-28", today=date(2026, 11, 7))


def test_yearless_date_uses_current_year():
    assert is_upcoming_event("December 12", today=date(2026, 11, 7))


def test_bangalore_alias_matches_bengaluru():
    assert normalize_city("Bangalore, India") == "bengaluru india"
    assert _matches_location("Bangalore, India", "Bengaluru", [])


def test_multi_city_scope():
    assert _matches_location("Hyderabad", None, ["Bengaluru", "Hyderabad"])
    assert not _matches_location("Pune", None, ["Bengaluru", "Hyderabad"])


def test_location_list_deduplicates():
    assert _parse_locations("Bengaluru; Chennai; Bengaluru") == ["Bengaluru", "Chennai"]


def test_bare_year_is_not_a_concrete_event_date():
    assert not is_upcoming_event("2027", today=date(2026, 11, 7))


def test_gemini_failure_is_reported_separately_from_non_event(monkeypatch):
    from eventagent.enrichment import gemini_extractor

    def fail_model():
        raise RuntimeError("simulated API failure")

    monkeypatch.setattr(gemini_extractor, "_get_model", fail_model)
    result = gemini_extractor.extract_event_with_gemini("A test event announcement")
    assert result["is_event"] is False
    assert result["extraction_error"] == "simulated API failure"


def test_pipeline_checkpoint_advances_after_each_completed_candidate(tmp_path, monkeypatch):
    import asyncio
    import pandas as pd
    from eventagent.processing import social_pipeline as pipeline

    data_dir = tmp_path / "data"
    log_dir = tmp_path / "logs"
    data_dir.mkdir()
    log_dir.mkdir()
    monkeypatch.setattr(pipeline, "DATA_DIR", data_dir)
    monkeypatch.setattr(pipeline, "LOG_DIR", log_dir)
    monkeypatch.setattr(pipeline, "INPUT_FILE", data_dir / "social_results.csv")
    monkeypatch.setattr(pipeline, "OUTPUT_FILE", data_dir / "social_filtered_results.csv")
    monkeypatch.setattr(pipeline, "STATE_FILE", data_dir / "pipeline_state.txt")

    pd.DataFrame([
        {"Link": "https://instagram.com/p/one", "Content_Type": "instagram_post", "Title": "One", "Query": "Bengaluru event", "Search_Location": "Bengaluru"},
        {"Link": "https://instagram.com/p/two", "Content_Type": "instagram_post", "Title": "Two", "Query": "Bengaluru event", "Search_Location": "Bengaluru"},
    ]).to_csv(pipeline.INPUT_FILE, index=False)

    async def fake_scrape(url):
        return {"text": "This is a sufficiently long event announcement page for testing the EventAgent pipeline safely with more than one hundred characters of visible text.", "html": "<html></html>"}

    async def fake_enrich(event, target_location=None):
        return event

    async def no_op():
        return None

    monkeypatch.setattr(pipeline, "scrape_page", fake_scrape)
    monkeypatch.setattr(pipeline, "init_browser", no_op)
    monkeypatch.setattr(pipeline, "close_browser", no_op)
    monkeypatch.setattr(pipeline, "enrich_event", fake_enrich)
    monkeypatch.setattr(pipeline, "extract_event_with_gemini", lambda text, target_location=None: {
        "is_event": True, "event_name": "Future Music Event", "city": "Bengaluru",
        "date": "2027-01-10", "time": "7 PM", "venue": "Test Arena",
    })

    first = asyncio.run(pipeline.run_pipeline(limit=1, locations=["Bengaluru"]))
    assert len(first) == 1
    assert pipeline.STATE_FILE.read_text().strip() == "1"

    second = asyncio.run(pipeline.run_pipeline(limit=1, locations=["Bengaluru"]))
    assert len(second) == 1
    assert pipeline.STATE_FILE.read_text().strip() == "0"
    final = pd.read_csv(pipeline.OUTPUT_FILE)
    assert len(final) == 1  # Same event/date is deduplicated across batches.


def test_auto_publisher_requires_source_city_title_and_future_date():
    from datetime import date, timedelta
    from eventagent.publishing.postgres import eligible_records

    future = (date.today() + timedelta(days=30)).isoformat()
    accepted, rejected = eligible_records([
        {"event_name": "Future Music Fest", "city": "Bengaluru", "date": future,
         "source_url": "https://example.com/event"},
        {"event_name": "Missing source", "city": "Bengaluru", "date": future},
        {"event_name": "Missing city", "date": future, "source_url": "https://example.com/event"},
        {"city": "Bengaluru", "date": future, "source_url": "https://example.com/event"},
    ])
    assert len(accepted) == 1
    assert rejected == 3
    assert accepted[0]["date"] == future


def test_auto_publisher_is_disabled_without_database_url(monkeypatch):
    from eventagent.publishing.postgres import publish_events
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AUTO_PUBLISH_ENABLED", "true")
    result = publish_events([{"event_name": "Test", "city": "Bengaluru"}])
    assert result["enabled"] is False
    assert result["published"] == 0
