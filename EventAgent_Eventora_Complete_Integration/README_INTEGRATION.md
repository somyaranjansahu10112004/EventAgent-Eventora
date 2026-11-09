# EventAgent + Eventora — Integration Foundation (Stage 1)

This bundle contains both original applications, kept as separate projects, plus the first shared-database integration layer.

## Architecture
- **EventAgent** remains the private data collection and processing/admin application.
- **Eventora** remains the public discovery website.
- **PostgreSQL** is the shared source of truth for published event records.
- EventAgent is the writer/publisher; Eventora is a read-only consumer.

## Files added or changed
- `SHARED_EVENT_DATABASE.sql` — canonical PostgreSQL schema, event sources, transactional outbox, and pipeline run tables.
- `EventAgent/eventagent/publishing/postgres.py` — optional, idempotent event upsert and outbox publisher; disabled unless `DATABASE_URL` is configured.
- `Eventora/server/src/db.ts` — PostgreSQL read adapter.
- `Eventora/server/src/migrateJsonToPostgres.ts` — safe-to-rerun migration of existing Eventora JSON records.
- Eventora API now reads published records from PostgreSQL when configured and retains the JSON fallback when not configured. `/api/health` reports the active source.
- `.env.example` files contain placeholders only. Real `.env` files and node_modules are intentionally excluded from this delivery.

## Setup order
1. Create a PostgreSQL 14+ database with your hosting provider.
2. Execute `SHARED_EVENT_DATABASE.sql` against that database.
3. Back up EventAgent `data/*.csv` and Eventora `server/data/events.json`. Keep these backups unchanged.
4. Configure the same `DATABASE_URL` in EventAgent and Eventora server environments. For hosted PostgreSQL, set `PGSSLMODE=require` in Eventora.
5. In Eventora's `server` directory run `npm install` (this installs the added `pg` and `@types/pg` dependencies).
6. Run `npm run migrate:json` from Eventora's `server` directory. This imports the existing JSON records into PostgreSQL using upserts.
7. Start Eventora. Check `/api/health`; it should return `dataSource: "postgresql"`. If the database is not configured, it will use the existing JSON dataset.
8. Install updated EventAgent requirements with `pip install -r requirements.txt`. Its PostgreSQL publisher is ready for Stage 2 wiring.

## Important scope note
Stage 1 establishes the schema, database reader, migration path, and EventAgent publishing primitive. It does **not** yet complete unattended live synchronization: the validated EventAgent pipeline still needs to call `publish_events`, and the outbox needs a delivery worker/retry policy and service authentication. Those are Stage 2 tasks. Do not deploy automatic publication until those are implemented and tested.

## Rollback
Unset `DATABASE_URL` in Eventora to return to the original JSON-backed behavior. The JSON and CSV source files remain in the project. Do not delete the backups until production data is reconciled.

## Security
A populated `.env` file was present in the uploaded Eventora archive. It is not included in this bundle. Rotate any credentials that were present in that file, and create local `.env` files from the provided `.env.example` templates. Never commit `.env`.

## Stage 2 — Automatic publishing

See `STAGE2_AUTOMATIC_PUBLISHING.md` for the EventAgent-to-Eventora publishing workflow, eligibility rules, environment variables, and local verification steps. EventAgent now publishes eligible upcoming records to the shared PostgreSQL database after each batch. Eventora refreshes published records from that same database. If PostgreSQL is not configured, EventAgent continues to save CSV output and Eventora continues to use its JSON fallback.
