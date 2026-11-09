# Changelog

## Fixed v4 — reliability and multi-city support

- Added single-city and semicolon-separated multi-city discovery.
- Stored search location on each social candidate and interleaved multi-city candidates so early batches cover each selected city.
- Removed Chennai-only Gemini prompt and pipeline filtering.
- Added city alias normalization for Bengaluru/Bangalore and Gurugram/Gurgaon.
- Reduced social discovery query templates to 38 focused queries per city.
- Added atomic per-candidate checkpoints and retry-on-restart behavior for an interrupted candidate.
- Added extraction-error reporting distinct from a valid non-event classification.
- Added blocked-page detection and safe Playwright initialization cleanup.
- Improved date parsing for date ranges and rejected bare-year values as event dates.
- Made final CSV updates atomic, upcoming-only and deduplicated by event/date/city.
- Added bounded Serper requests and moved synchronous enrichment search off the async event loop.
- Added real batch progress callbacks and more accurate integration configuration indicators.
- Restricted the local API server to loopback and limited CORS to the local Vite development origins.
- Fixed search pagination reset behavior, full-dataset category options and candidate location display.
- Pinned Python and frontend package versions; added regression tests and updated setup documentation.
