# EventAgent + Eventora — Combined Integration Package (Stages 1–3)

This ZIP combines the cumulative code and documentation from Stages 1, 2 and 3 into one project bundle. It contains two separate applications:

- `EventAgent/` — private Python/FastAPI event discovery and processing application. It writes eligible event records to PostgreSQL when configured and keeps its CSV outputs.
- `Eventora/` — public React/Node application. Its backend reads published events from PostgreSQL when configured and retains the original JSON fallback.
- `SHARED_EVENT_DATABASE.sql` — shared PostgreSQL schema.
- `integration-tests/smoke_test.py` — end-to-end development smoke test.

## Important status

This is the combined Stage 1–3 code package. It is **not proof of a live integration**: no real PostgreSQL credentials or deployed service environment were available when this ZIP was assembled. Run the smoke test against a development database before production use. Stage 3 is complete only after that test passes in your environment.

## Setup order

### 1. Create the database

Create a PostgreSQL 14+ database. Back up these existing data files before migrating:

- `EventAgent/data/*.csv`
- `Eventora/server/data/events.json`

Apply `SHARED_EVENT_DATABASE.sql` to the new database using your PostgreSQL client/provider console.

### 2. Configure EventAgent

Copy `EventAgent/.env.example` to `EventAgent/.env` and fill in your existing API credentials plus:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
AUTO_PUBLISH_ENABLED=true
```

From PowerShell:

```powershell
cd EventAgent
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the backend/admin API using the existing project instructions in `EventAgent/README.md`.

### 3. Configure Eventora backend

Copy `Eventora/.env.example` to `Eventora/server/.env` (or the location expected by its server configuration) and set:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
PGSSLMODE=require
EVENT_REFRESH_INTERVAL_MS=30000
```

For local PostgreSQL, use the SSL setting appropriate for your database; `require` is generally for hosted PostgreSQL providers.

Install server dependencies and migrate the existing JSON dataset:

```powershell
cd Eventora\server
npm install
npm run migrate:json
npm run dev
```

Check `GET http://127.0.0.1:5000/api/health`. It should report PostgreSQL as the active data source when configured. If it reports JSON, verify the server's `.env` location and restart it.

### 4. Start the Eventora frontend

In a separate terminal:

```powershell
cd Eventora\client
npm install
npm run dev
```

Use the local URL printed by Vite.

### 5. Run the end-to-end integration test

Keep the Eventora backend running and use a **development/test database only**. From the repository root, configure `DATABASE_URL` and `EVENTORA_API_URL`, activate the EventAgent virtual environment, then run:

```powershell
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DATABASE"
$env:AUTO_PUBLISH_ENABLED="true"
$env:EVENTORA_API_URL="http://127.0.0.1:5000"
python .\integration-tests\smoke_test.py
```

Expected success message:

```text
PASS: create -> publish -> Eventora visibility -> update -> idempotency -> cleanup
```

The smoke test creates and deletes a temporary event. Do not run it against production data.

## How the automatic flow works

1. EventAgent discovers and extracts candidate events.
2. The publishing layer applies eligibility checks (including title, city, future date and source URL).
3. Eligible records are upserted into the shared `events` table and recorded in the outbox.
4. Eventora's backend reads records marked as published from the same PostgreSQL database.
5. Eventora's refresh interval (default 30 seconds) makes newly published/updated records visible to the website.

Events that fail eligibility checks are not automatically published. EventAgent retains its local CSV output. Eventora retains the JSON fallback when PostgreSQL is not configured.

## Security and deployment notes

- Never commit `.env` files or put database credentials in frontend variables.
- Use HTTPS and strong service/database credentials in hosted environments.
- Rotate any API keys that were present in previously shared `.env` files.
- Keep the CSV and JSON backups until migration and reconciliation are confirmed.
- Test on a staging database before production.
- The smoke test does not prove production networking, third-party API access, scheduled worker uptime, or high-volume behavior.

## Stage documentation

- `README_INTEGRATION.md` — Stage 1 foundation notes.
- `STAGE2_AUTOMATIC_PUBLISHING.md` — Stage 2 publishing behavior and configuration.
- `STAGE3_INTEGRATION_TESTING.md` — Stage 3 test details and limitations.
