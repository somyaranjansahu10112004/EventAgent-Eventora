"""EventAgent dashboard API. All metrics are derived from project files and live runs."""
import asyncio, csv, io, json, os, threading, time, uuid, importlib.util
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
HISTORY_FILE = LOG_DIR / "execution_history.json"
INPUT_FILE = DATA_DIR / "social_results.csv"
OUTPUT_FILE = DATA_DIR / "social_filtered_results.csv"

app = FastAPI(title="EventAgent — Social Intelligence API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "https://eventagent-dashboard.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

_lock = threading.Lock()
_state = {"running": False, "execution_id": None, "started_at": None,
          "finished_at": None, "status": "idle", "stage": "Idle",
          "processed": 0, "total": 0, "error": None, "location": "Bengaluru", "locations": []}
_log_lines = []
_log_limit = 600

class StartRequest(BaseModel):
    location: str = Field(default="Bengaluru", min_length=2, max_length=500)
    limit: int = Field(default=50, ge=1, le=500)
    collect_first: bool = True

def _read_csv(path):
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path).fillna("")
    except Exception:
        return pd.DataFrame()

def _history():
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save_history(entry):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    items = _history()
    items.insert(0, entry)
    HISTORY_FILE.write_text(json.dumps(items[:100], indent=2, ensure_ascii=False), encoding="utf-8")

def _log(message):
    stamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] {message}"
    _log_lines.append(line)
    del _log_lines[:-_log_limit]
    _state["stage"] = message[:100]

class _Tee:
    def __init__(self, original):
        self.original = original
    def write(self, value):
        if value and value.strip():
            for line in value.rstrip().splitlines():
                _log(line)
        return self.original.write(value)
    def flush(self):
        self.original.flush()

def _parse_locations(raw):
    # Semicolon separates cities so city names may safely contain spaces/commas.
    values = [part.strip() for part in raw.split(";") if part.strip()]
    unique = list(dict.fromkeys(values))
    if not unique:
        raise ValueError("Enter at least one city or location.")
    if len(unique) > 20:
        raise ValueError("A maximum of 20 locations can be searched in one run.")
    return unique


def _progress(processed, total, stage):
    _state.update(processed=int(processed), total=int(total), stage=str(stage)[:160])


def _run_job(request, execution_id):
    started = datetime.now(timezone.utc)
    locations = _parse_locations(request.location)
    _state.update(running=True, status="running", started_at=started.isoformat(),
                  finished_at=None, execution_id=execution_id, location="; ".join(locations),
                  locations=locations, processed=0, total=0, error=None, stage="Initializing")
    _log(f"Execution {execution_id} initialized for: {', '.join(locations)}")
    run_results = []
    try:
        with redirect_stdout(_Tee(__import__("sys").stdout)), redirect_stderr(_Tee(__import__("sys").stderr)):
            if request.collect_first:
                from eventagent.discovery.social_collector import collect_results
                frames = []
                for location in locations:
                    _log(f"Collecting Instagram and Facebook candidates for {location}")
                    frame = collect_results(location, progress_callback=lambda done, total, stage: _progress(done, total, stage))
                    frames.append(frame)
                    _log(f"{location}: {len(frame)} unique candidate links")
                candidates = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
                if not candidates.empty:
                    candidates = candidates.drop_duplicates(subset=["Link"], keep="first")
                    if "Search_Location" in candidates.columns:
                        candidates["_city_sequence"] = candidates.groupby("Search_Location").cumcount()
                        candidates = candidates.sort_values(["_city_sequence", "Search_Location"], kind="stable").drop(columns=["_city_sequence"])
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                candidates.to_csv(INPUT_FILE, index=False)
                _log(f"Collection completed: {len(candidates)} total candidate links saved")
            else:
                _log("Using the existing social_results.csv input")
            from eventagent.processing.social_pipeline import run_pipeline
            input_df = _read_csv(INPUT_FILE)
            _state.update(processed=0, total=min(len(input_df), request.limit))
            _log(f"Starting scrape → Gemini extraction → enrichment → validation for {len(locations)} location(s)")
            run_results = asyncio.run(run_pipeline(
                limit=request.limit,
                locations=locations,
                progress_callback=_progress,
            ))
            _state["status"] = "completed"
            _log(f"Execution completed: {len(run_results)} upcoming event records processed")
        status, error = "completed", None
    except Exception as exc:
        status, error = "failed", str(exc)
        _state.update(status="failed", error=error)
        _log(f"Execution failed: {error}")
    finally:
        finished = datetime.now(timezone.utc)
        _state.update(running=False, finished_at=finished.isoformat())
        elapsed = round((finished-started).total_seconds(), 2)
        output, candidates = _read_csv(OUTPUT_FILE), _read_csv(INPUT_FILE)
        _save_history({
            "execution_id": execution_id, "started_at": started.isoformat(),
            "finished_at": finished.isoformat(), "duration_seconds": elapsed,
            "status": status, "location": "; ".join(locations), "locations": locations,
            "urls_collected": len(candidates), "events_extracted": len(run_results),
            "valid_records": len(output), "error": error
        })
        _log(f"Run closed · {elapsed}s · status: {status}")

@app.get("/")
def home():
    return {"message": "EventAgent API is running", "version": "2.0.0"}

@app.get("/api/health")
def health():
    from eventagent.config import SERPER_API_KEY, GEMINI_API_KEY
    return {
        "status": "ok", "service": "EventAgent API",
        "integrations": {
            "serper_configured": bool(SERPER_API_KEY),
            "gemini_configured": bool(GEMINI_API_KEY),
            "playwright_installed": importlib.util.find_spec("playwright") is not None,
        },
    }

@app.get("/api/status")
def status():
    return dict(_state)

@app.get("/api/dashboard")
def dashboard():
    candidates, events = _read_csv(INPUT_FILE), _read_csv(OUTPUT_FILE)
    logs = _log_lines[-100:]
    history = _history()
    content_types = candidates["Content_Type"].value_counts().to_dict() if "Content_Type" in candidates else {}
    categories = events["category"].replace("", "Uncategorized").value_counts().to_dict() if "category" in events else {}
    dates = events["date"].value_counts().to_dict() if "date" in events else {}
    return {
        "metrics": {
            "searches": int(candidates["Query"].nunique()) if "Query" in candidates else 0,
            "links_collected": len(candidates),
            "pages_scraped": None,
            "events_extracted": len(events),
            "events_enriched": None,
            "upcoming_events": len(events),
            "duplicates_removed": None,
            "final_records": len(events)
        },
        "platforms": content_types, "categories": categories, "event_dates": dates,
        "integrations": {
            "serper_configured": bool(__import__("eventagent.config", fromlist=["SERPER_API_KEY"]).SERPER_API_KEY),
            "gemini_configured": bool(__import__("eventagent.config", fromlist=["GEMINI_API_KEY"]).GEMINI_API_KEY),
            "playwright_installed": importlib.util.find_spec("playwright") is not None,
        },
        "recent_runs": history[:5], "logs": logs, "input_columns": list(candidates.columns),
        "output_columns": list(events.columns), "data_available": INPUT_FILE.exists() or OUTPUT_FILE.exists()
    }

@app.get("/api/events")
def events(q: str = "", category: str = "", sort: str = "date", page: int = 1, page_size: int = 25):
    df = _read_csv(OUTPUT_FILE)
    if q:
        mask = df.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False, regex=False)).any(axis=1)
        df = df[mask]
    if category and "category" in df:
        df = df[df["category"].astype(str).str.lower() == category.lower()]
    if sort in df.columns:
        df = df.sort_values(sort, kind="stable")
    total = len(df)
    page_size = max(1, min(page_size, 100))
    start = (max(page, 1)-1)*page_size
    return {"items": df.iloc[start:start+page_size].to_dict("records"), "total": total,
            "page": max(page,1), "page_size": page_size, "columns": list(df.columns)}

@app.get("/api/candidates")
def candidates(q: str = "", page: int = 1, page_size: int = 30):
    df = _read_csv(INPUT_FILE)
    if q:
        df = df[df.astype(str).apply(lambda c: c.str.contains(q, case=False, na=False, regex=False)).any(axis=1)]
    total = len(df); size = max(1, min(page_size,100)); start=(max(page,1)-1)*size
    return {"items": df.iloc[start:start+size].to_dict("records"), "total": total,
            "columns": list(df.columns), "page": max(page,1), "page_size": size}

@app.get("/api/queries")
def queries():
    from eventagent.discovery.social_query_generator import generate_queries
    return {"items": [{"query": q, "platform": "Instagram + Facebook"} for location in (_state.get("locations") or ["Bengaluru"]) for q in generate_queries(location)]}

@app.get("/api/logs")
def logs(after: int = 0):
    return {"items": _log_lines[after:], "total": len(_log_lines), "state": dict(_state)}

@app.get("/api/history")
def history():
    return {"items": _history()}

@app.get("/api/settings")
def settings():
    from eventagent.config import SERPER_API_KEY, GEMINI_API_KEY, GEMINI_MODEL
    return {"project": "EventAgent", "data_directory": "data/",
            "input_file": "data/social_results.csv", "output_file": "data/social_filtered_results.csv",
            "gemini_model": GEMINI_MODEL, "serper_configured": bool(SERPER_API_KEY),
            "gemini_configured": bool(GEMINI_API_KEY),
            "playwright_installed": importlib.util.find_spec("playwright") is not None,
            "features": {"start_agent": True, "pause": False, "resume": False, "stop": False,
                         "query_execution": False, "record_editing": False}}

@app.post("/api/start")
def start(request: StartRequest):
    if not INPUT_FILE.exists() and not request.collect_first:
        raise HTTPException(400, "Input CSV is missing. Enable collection or add data/social_results.csv.")
    try:
        _parse_locations(request.location)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    with _lock:
        if _state["running"]:
            raise HTTPException(409, "An agent execution is already running.")
        execution_id = str(uuid.uuid4())[:8]
        _log_lines.clear()
        thread = threading.Thread(target=_run_job, args=(request, execution_id), daemon=True)
        thread.start()
    return {"accepted": True, "execution_id": execution_id, "message": "Agent execution started."}

@app.get("/api/export")
def export():
    if not OUTPUT_FILE.exists():
        raise HTTPException(404, "No final event dataset is available yet.")
    return StreamingResponse(OUTPUT_FILE.open("rb"), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="eventagent_events.csv"'})

# Retain the existing lightweight consumer endpoint.
class SearchRequest(BaseModel):
    location: str
@app.post("/search-and-filter")
async def search_and_filter(request: SearchRequest):
    df = _read_csv(OUTPUT_FILE)
    if "city" in df.columns:
        df = df[df["city"].astype(str).str.contains(request.location, case=False, na=False)]
    return {"status": "success", "location": request.location, "count": len(df),
            "events": df.to_dict(orient="records")}
