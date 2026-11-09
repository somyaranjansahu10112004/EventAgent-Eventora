# Stage 2 — Automatic EventAgent → Eventora publishing

## What changed

- EventAgent now calls the PostgreSQL publisher after each successful pipeline batch.
- Only records with an event title, city, concrete upcoming date, and HTTP(S) source URL are eligible.
- Eligible records are upserted into the shared `events` table and their source URL is recorded.
- Each successful upsert creates a `sync_outbox` record in the same database transaction.
- Eventora already reads only rows with `is_published = TRUE AND status = 'published'`; its refresh loop picks up changes at `EVENT_REFRESH_INTERVAL_MS` (default 30 seconds).
- Eventora acknowledges outbox records after a successful full read of the published dataset.
- If PostgreSQL is unavailable, EventAgent retains its CSV output and logs the publishing failure; it does not lose the extracted records.

## Configuration

Use the same PostgreSQL database URL in both services. Do not put database credentials in frontend environment variables.

EventAgent `.env`:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
AUTO_PUBLISH_ENABLED=true
```

Eventora `server/.env`:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
PGSSLMODE=require
EVENT_REFRESH_INTERVAL_MS=30000
```

Run `SHARED_EVENT_DATABASE.sql` once against the database before starting either service.

## Important behavior

- This is automatic publication after deterministic eligibility checks, not unconditional publication of every scraped URL.
- Records missing a title, city, valid future date, or traceable source URL remain in the local CSV and are not published.
- EventAgent and Eventora must both use the same schema and database.
- Eventora continues to use `events.json` when `DATABASE_URL` is absent, preserving local development fallback.
- The outbox currently records publication/consumption history. Because both services share PostgreSQL, Eventora reads the canonical published table directly; no separate webhook is required.

## Local verification

1. Apply `SHARED_EVENT_DATABASE.sql`.
2. Configure the same `DATABASE_URL` in EventAgent and Eventora backend `.env` files.
3. Install EventAgent requirements, including `psycopg[binary]`.
4. Start Eventora backend and check `GET /api/health`; `dataSource` should be `postgresql`.
5. Run an EventAgent batch with real API credentials.
6. Check the `events` table for `status='published' AND is_published=true`.
7. Within the refresh interval, check Eventora `GET /api/events` for the new event.

No live database credentials were supplied, so a real cross-service database transaction and deployed sync test have not been run in this environment.
