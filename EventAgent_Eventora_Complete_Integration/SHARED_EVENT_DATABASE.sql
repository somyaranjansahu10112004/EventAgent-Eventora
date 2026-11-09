-- Shared EventAgent + Eventora schema (PostgreSQL 14+)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  event_name TEXT NOT NULL,
  category TEXT,
  venue TEXT,
  area TEXT,
  city TEXT NOT NULL,
  event_date DATE,
  original_date TEXT,
  event_time TEXT,
  registration_required TEXT,
  source_url TEXT,
  original_source_value TEXT,
  price TEXT,
  host_name TEXT,
  instagram_id TEXT,
  status TEXT NOT NULL DEFAULT 'published' CHECK (status IN ('discovered','processing','needs_review','validated','published','cancelled','postponed','completed','expired','failed')),
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  confidence_score NUMERIC(5,2),
  source_count INTEGER NOT NULL DEFAULT 1,
  extra JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  published_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_events_public_date ON events (event_date) WHERE is_published = TRUE;
CREATE INDEX IF NOT EXISTS idx_events_public_city ON events (LOWER(city)) WHERE is_published = TRUE;
CREATE INDEX IF NOT EXISTS idx_events_public_category ON events (LOWER(category)) WHERE is_published = TRUE;
CREATE TABLE IF NOT EXISTS event_sources (
  id BIGSERIAL PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  source_url TEXT NOT NULL,
  platform TEXT,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(event_id, source_url)
);
CREATE TABLE IF NOT EXISTS sync_outbox (
  id BIGSERIAL PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  action TEXT NOT NULL CHECK (action IN ('upsert','unpublish')),
  payload JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','delivered','failed')),
  attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  delivered_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sync_outbox_pending ON sync_outbox(next_attempt_at) WHERE status IN ('pending','failed');
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  locations JSONB NOT NULL DEFAULT '[]'::jsonb,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
  error TEXT
);
