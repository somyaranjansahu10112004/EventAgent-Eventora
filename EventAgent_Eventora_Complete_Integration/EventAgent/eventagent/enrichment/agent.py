import asyncio
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FAILED_HTML_DIR = PROJECT_ROOT / "diagnostics" / "failed_fb_html"

from ..enrichment.enrichment_search import search_missing_event_info
from ..processing.merge_results import merge_events
from ..scraping.scraper import scrape_page
from ..enrichment.gemini_extractor import extract_event_with_gemini
from ..enrichment.similarity import is_same_event

PROTECTED_FIELDS = {
    "url",
    "platform",
    "source_account",
    "query",
    "content_type"
}

IMPORTANT_FIELDS = [
    "date",
    "time",
    "venue",
    "area"
]


def extract_fb_source_account(html, url):
    patterns = [
        # Prefer human-readable page names first
        r'"short_name":"([^"]+)"',
        r'"page_name":"([^"]+)"',
        r'"actor_name":"([^"]+)"',

        # Then fall back to profile/page URLs
        r'"profile_url":"https:\\/\\/www\.facebook\.com\\/([^"]+?)"',
        r'"url":"https:\\/\\/www\.facebook\.com\\/([^"]+?)"',
    ]

    print("\n========== FACEBOOK DEBUG ==========")

    for pattern in patterns:
        match = re.search(pattern, html)

        print(f"Pattern: {pattern}")
        print("Matched:", bool(match))

        if not match:
            continue

        value = match.group(1)

        # Decode escaped slashes if present
        value = value.replace("\\/", "/")

        # If we matched a URL, extract the page name
        if "/" in value:
            parts = [p for p in value.split("/") if p]

            # Example:
            # people/SoundScene/61578371200189
            if "people" in parts:
                idx = parts.index("people")
                if idx + 1 < len(parts):
                    value = parts[idx + 1]
            else:
                value = parts[-1]

        print("Extracted:", value)

        if value and not value.isdigit():
            print("✅ Facebook Source Account:", value)
            return value

    # Final fallback: event slug
    m = re.search(r"facebook\.com/events/([^/]+)/", url)

    if m:
        slug = m.group(1)

        if not slug.isdigit():
            print("Fallback slug:", slug)
            return slug

    print("❌ No Facebook account found.")
    return None


def should_run_agent(event):
    missing = [
        field
        for field in IMPORTANT_FIELDS
        if not event.get(field)
    ]

    return bool(missing)


async def try_sources(original_event, results, target_location=None):
    merged = original_event.copy()
    FAILED_HTML_DIR.mkdir(parents=True, exist_ok=True)

    for result in results:
        if not result.get('link'):
            continue

        print('=' * 80)
        print(f"Trying Source: {result['link']}")

        try:
            page_data = await scrape_page(result['link'])
            page_html = page_data['html']
            page_text = page_data['text']

            if not page_text:
                continue

            enriched = extract_event_with_gemini(page_text, target_location=target_location)

            if (not enriched.get('source_account')
                    and 'facebook.com' in result['link']):
                account = extract_fb_source_account(page_html, result['link'])
                if account:
                    enriched['source_account'] = account
                else:
                    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', result['link'])[-120:]
                    with open(FAILED_HTML_DIR / f'{safe_name}.html', 'w', encoding='utf-8') as f:
                        f.write(page_html)
                    print(f"⚠️ Saved failed Facebook HTML -> {FAILED_HTML_DIR / (safe_name + '.html')}")

            print('\nGemini Extracted:')
            print(enriched)

            if not enriched.get('is_event', False):
                print('❌ Not an event.')
                continue

            if not is_same_event(merged, enriched):
                print('❌ Different event.')
                continue

            for field in PROTECTED_FIELDS:
                enriched.pop(field, None)

            merged = merge_events(merged, enriched)

            remaining = [f for f in IMPORTANT_FIELDS if not merged.get(f)]
            if not remaining:
                print('\n✅ Event completed.')
                return merged

            print(f'\nStill missing: {remaining}')

        except Exception as e:
            print(f"⚠️ Failed: {result['link']}")
            print(e)

    print('\nNo more useful sources.')
    return merged


async def enrich_event(event, target_location=None):
    print('\n========== AI ENRICHMENT ==========\n')

    if not should_run_agent(event):
        print('✅ All key fields present. Skipping enrichment.')
        return event

    missing = [f for f in IMPORTANT_FIELDS if not event.get(f)]
    print(f'Missing Fields : {missing}')

    results = await asyncio.to_thread(
        search_missing_event_info,
        event_name=event["event_name"],
        organizer=event.get("host_name"),
        venue=event.get("venue"),
        city=event.get("city") or target_location or "India",
        source_account=event.get("source_account"),
    )

    print(f'\nFound {len(results)} candidate sources.')

    if not results:
        return event

    print('\nTop Candidate Sources\n')
    for i, result in enumerate(results[:5], start=1):
        print(f"{i}. {result['title']}")
        print(result['link'])
        print()

    final_event = await try_sources(event, results, target_location=target_location)

    print('\n========== FINAL EVENT ==========\n')
    print(final_event)

    return final_event