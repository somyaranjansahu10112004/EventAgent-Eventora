# EventAgent — Premium Command Center

EventAgent discovers social event announcements, extracts structured details with Gemini, enriches incomplete records using trusted event sources, validates dates, and presents the results in a React + Vite dashboard.

## What changed in this fixed version

### Discovery and locations
- Search one city or multiple cities in a single run.
- Enter multiple locations separated by semicolons, for example `Bengaluru; Chennai; Hyderabad`.
- Each collected candidate records its `Search_Location`, allowing the pipeline to apply the correct city context while processing.
- Replaced the Chennai-only extraction instruction with a requested-location-aware prompt.
- Reduced redundant social search templates from five per event category to two per category to make multi-city runs less expensive and faster.
- Bengaluru/Bangalore and Gurgaon/Gurugram are normalized for matching.

### Pipeline reliability
- Batch checkpoints are written atomically after each candidate finishes.
- If the process stops during a candidate, that candidate is retried on the next run.
- The checkpoint advances only after a candidate has completed or been safely classified as skipped/failed.
- Browser cleanup runs in a `finally` block.
- Empty and access-restricted pages are counted as blocked rather than treated as successful extraction.
- Gemini failures are logged separately from genuine non-event results.
- Final CSV writes are atomic, old records are deduplicated, and expired/undated records are removed from the upcoming-events output.

### API and dashboard
- Real per-batch progress callbacks update the execution monitor.
- Health endpoints report API-key configuration and whether Playwright is installed; they do not claim external API connectivity without a live request.
- Local API binding and restricted local CORS origins are used by default.
- Search filters treat user text literally rather than as a regular expression.
- Existing dashboard layout and navigation are retained; the location control now supports semicolon-separated cities.

## Project structure

```text
EventAgent/
├── eventagent/
│   ├── api/                 # FastAPI dashboard endpoints
│   ├── discovery/           # Serper search and social query collection
│   ├── enrichment/          # Gemini extraction and trusted-source enrichment
│   ├── processing/          # Pipeline, date validation, merge and classification
│   └── scraping/            # Playwright browser scraping
├── frontend/                # React + Vite dashboard
├── data/                    # Candidate and final CSVs, checkpoint
├── logs/                    # Runtime logs and execution history
├── diagnostics/             # Saved diagnostic HTML samples
├── tests/                   # Lightweight processing tests
├── run_api.py
├── run_social_collector.py
└── run_social_pipeline.py
```

## Requirements

- Python 3.11+
- Node.js 20+
- Serper API key
- Google Gemini API key
- Chromium browser installed through Playwright

## Setup — Windows PowerShell

From the project root:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
Copy-Item .env.example .env
```

Open `.env` and add your own credentials:

```env
SERPER_API_KEY=your_serper_api_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=models/gemini-flash-lite-latest
```

Never commit `.env` or paste API keys into source files. If a real key has ever been committed or shared, revoke it and create a replacement.

## Start the dashboard

Open two VS Code terminals.

**Terminal 1 — backend** (project root, virtual environment activated):

```powershell
python run_api.py
```

Backend: `http://127.0.0.1:8000`
API docs: `http://127.0.0.1:8000/docs`

**Terminal 2 — frontend:**

```powershell
cd frontend
npm install
npm run dev
```

Dashboard: `http://127.0.0.1:5173`

## Run event discovery

In the dashboard, open **AI Agent**.

- One city: `Bengaluru`
- Multiple cities: `Bengaluru; Chennai; Hyderabad; Mumbai`
- Choose the maximum processing batch (1–500).
- Keep **Collect fresh social links first** enabled to collect current candidates, or disable it to process the existing `data/social_results.csv`.
- Select **Start agent**.

The collector searches the locations sequentially, stores the location alongside each candidate, then the pipeline scrapes and processes the requested batch.

## Run from the command line

Collect candidates for one city:

```powershell
python run_social_collector.py --location Bengaluru
```

Collect candidates for multiple cities:

```powershell
python run_social_collector.py --locations "Bengaluru;Chennai;Hyderabad"
```

Process the current candidate batch:

```powershell
python run_social_pipeline.py --limit 50
```

Process candidates scoped to multiple cities:

```powershell
python run_social_pipeline.py --limit 100 --locations "Bengaluru;Chennai;Hyderabad"
```

## Checkpoint and recovery

`data/pipeline_state.txt` stores the next candidate row to process. It is updated after each candidate. To restart the candidate CSV from its first row, stop the backend and set the file content to `0`.

The checkpoint is an integer row offset for the current `social_results.csv`; if you replace the candidate CSV with a substantially different file, reset the checkpoint to `0` first.

## Output files

- `data/social_results.csv` — collected social candidates, including `Search_Location`.
- `data/social_filtered_results.csv` — upcoming, deduplicated event records.
- `data/pipeline_state.txt` — resumable processing offset.
- `logs/execution_history.json` — dashboard execution history.
- `logs/pipeline_errors.log` — candidate-level processing errors.
- `logs/raw_events.jsonl` — events detected before final validation.

## Tests

Run lightweight local checks:

```powershell
python -m pytest -q
```

The tests cover date parsing, date ranges, location aliases, multi-city filtering and location parsing. They do not make external Serper/Gemini calls or validate platform-specific scraping access.

## Operational notes and limitations

- Instagram/Facebook pages may be unavailable, login-gated, rate-limited or changed by the platform. EventAgent detects common blocked-page signals but cannot bypass access controls.
- Serper and Gemini usage depends on your account quota and API billing/limits.
- A city with no explicit event city in the source text is retained for review; a clearly conflicting city is rejected.
- The dashboard intentionally does not expose pause/resume/stop until safe cooperative cancellation is implemented.
- API-key presence and Playwright installation are configuration checks, not proof that a live third-party request will succeed.
- The frontend dependency versions are pinned. Run `npm install` in `frontend/` to generate a local lockfile for your platform.
