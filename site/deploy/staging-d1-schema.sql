-- Issue #141 dedicated staging-only public canary state.
-- SQLite/D1 syntax only. This database must never be bound to production.

CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  balance_cents INTEGER NOT NULL DEFAULT 500,
  api_key TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_keys (
  key_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  user_id TEXT NOT NULL,
  slug TEXT NOT NULL,
  cost_cents INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_user_created
  ON runs (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS run_requests (
  run_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  slug TEXT NOT NULL,
  workflow_version TEXT NOT NULL DEFAULT '1.0.0',
  cost_cents INTEGER NOT NULL,
  state TEXT NOT NULL DEFAULT 'reserved'
    CHECK (state IN ('reserved', 'running', 'succeeded', 'refunded')),
  execution_status TEXT NOT NULL DEFAULT 'claimed'
    CHECK (execution_status IN ('claimed', 'queued', 'dispatching', 'succeeded', 'failed')),
  billing_status TEXT NOT NULL DEFAULT 'unbilled'
    CHECK (billing_status IN ('unbilled', 'reserved', 'captured', 'refund_due', 'refunded')),
  input_json TEXT,
  accepted_json TEXT,
  result_json TEXT,
  artifact_json TEXT,
  error_json TEXT,
  response_json TEXT,
  http_status INTEGER,
  dispatch_owner TEXT,
  dispatch_lease_expires_at TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  dispatched_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_run_requests_user_updated
  ON run_requests (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_run_requests_stale
  ON run_requests (execution_status, dispatch_lease_expires_at, updated_at);

CREATE TABLE IF NOT EXISTS run_progress (
  run_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  phase TEXT NOT NULL
    CHECK (phase IN ('reserved', 'running', 'transcribing', 'directing', 'generating', 'assembling', 'delivered', 'failed')),
  progress_pct INTEGER NOT NULL CHECK (progress_pct >= 0 AND progress_pct <= 100),
  progress_source TEXT NOT NULL CHECK (progress_source IN ('derived', 'webhook', 'modal')),
  modal_status TEXT NOT NULL,
  modal_status_url TEXT NOT NULL,
  video_url TEXT,
  contact_sheet_url TEXT,
  result_json TEXT,
  input_notice TEXT,
  started_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  terminal_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_run_progress_user_updated
  ON run_progress (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS credits_ledger (
  event_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  balance_cents INTEGER NOT NULL,
  reference_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_credits_ledger_user_created
  ON credits_ledger (user_id, created_at DESC);
