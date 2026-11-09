# Stage 3 — End-to-end integration verification

Stage 3 adds a repeatable smoke test for the real integration path. It creates a temporary event through EventAgent's publisher, verifies that Eventora's public API returns it, updates the same event ID, confirms the update appears, checks that only one canonical database row exists, and removes the test record.

## Prerequisites

- PostgreSQL database created and `SHARED_EVENT_DATABASE.sql` applied.
- The same `DATABASE_URL` configured in `EventAgent/.env` and `Eventora/server/.env`.
- `AUTO_PUBLISH_ENABLED=true` in EventAgent.
- EventAgent Python requirements installed, including `psycopg[binary]`.
- Eventora server dependencies installed and backend running on port 5000 (or set `EVENTORA_API_URL`).
- Both applications must point to the exact same PostgreSQL database.

## Run the test (Windows PowerShell)

Terminal 1 — Eventora backend:

```powershell
cd Eventora\server
npm install
npm run dev
```

Terminal 2 — EventAgent:

```powershell
cd EventAgent
.venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/DATABASE"
$env:AUTO_PUBLISH_ENABLED="true"
$env:EVENTORA_API_URL="http://127.0.0.1:5000"
python ..\integration-tests\smoke_test.py
```

If EventAgent and Eventora are in separate folders, adjust the relative path to `smoke_test.py`. Do not paste real credentials into chat or commit `.env` files.

## Expected result

```text
PASS: create -> publish -> Eventora visibility -> update -> idempotency -> cleanup
```

The script uses a unique temporary event ID and deletes the corresponding event row at the end. It also attempts cleanup after a failure. Run it only against a development/test database, not production.

## Manual checks

1. `GET /api/health` on Eventora should report `dataSource: "postgresql"`.
2. `GET /api/events?includePast=true` should return the temporary event while the test is running.
3. After cleanup, the temporary event should no longer appear.
4. Check EventAgent logs for the publishing summary and Eventora logs for database refresh errors.

## What this test does not prove

This smoke test does not verify third-party Serper/Gemini/Playwright credentials, deployment networking, production TLS settings, scheduled worker uptime, or high-volume concurrency. Those require the user's configured environment and a separate staging deployment test.
