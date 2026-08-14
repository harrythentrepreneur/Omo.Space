-- Omo credits backend — Neon Postgres primary schema.
--
-- Neon (recommended): psql "$NEON_DATABASE_URL" -f schema.sql
-- D1 fallback: use the CREATE TABLE/CREATE INDEX definitions for fresh local
-- databases; the submissions table below includes workflow_version,
-- published_slug, build_evidence, build_claimed_at, and build_attempts for
-- fresh D1 parity. The additive
-- ALTER TABLE ... ADD COLUMN IF NOT EXISTS migration statements are
-- Postgres/Neon syntax. For an existing D1 database, apply equivalent
-- manual ALTER TABLE ADD COLUMN statements in a separate reviewed D1 migration.
--
-- Most columns use TEXT timestamps and INTEGER booleans so the base table
-- shapes remain close to SQLite/D1, but migration syntax is target-specific.

CREATE TABLE IF NOT EXISTS users (
  user_id       TEXT PRIMARY KEY,             -- Clerk user id (user_…)
  balance_cents INTEGER NOT NULL DEFAULT 500, -- $5 signup grant, in cents
  api_key       TEXT NOT NULL,                -- SHA-256 hash material; raw omo_ key is derived only for display
  created_at    TEXT NOT NULL                 -- ISO timestamp
);

CREATE TABLE IF NOT EXISTS api_keys (
  key_hash   TEXT PRIMARY KEY,                 -- SHA-256(raw omo_ key)
  user_id    TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  user_id     TEXT NOT NULL,
  slug        TEXT NOT NULL,
  cost_cents  INTEGER NOT NULL,
  created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_user_created
  ON runs (user_id, created_at DESC);

-- Durable idempotency + billing state machine. A unique account/key pair is
-- claimed before credits are reserved, preventing concurrent retry charges.
CREATE TABLE IF NOT EXISTS run_requests (
  run_id          TEXT PRIMARY KEY,
  user_id         TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  request_hash    TEXT NOT NULL,
  slug            TEXT NOT NULL,
  workflow_version TEXT NOT NULL DEFAULT '1.0.0',
  cost_cents      INTEGER NOT NULL,
  state           TEXT NOT NULL DEFAULT 'reserved' CHECK (state IN ('reserved', 'running', 'succeeded', 'refunded')),
  execution_status TEXT NOT NULL DEFAULT 'claimed' CHECK (execution_status IN ('claimed', 'queued', 'dispatching', 'succeeded', 'failed')),
  billing_status TEXT NOT NULL DEFAULT 'unbilled' CHECK (billing_status IN ('unbilled', 'reserved', 'captured', 'refund_due', 'refunded')),
  input_json      TEXT,
  accepted_json   TEXT,
  result_json     TEXT,
  artifact_json   TEXT,
  error_json      TEXT,
  response_json   TEXT,
  http_status     INTEGER,
  dispatch_owner  TEXT,
  dispatch_lease_expires_at TEXT,
  attempt_count   INTEGER NOT NULL DEFAULT 0,
  dispatched_at   TEXT,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  UNIQUE (user_id, idempotency_key)
);

ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS workflow_version TEXT NOT NULL DEFAULT '1.0.0';
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS execution_status TEXT NOT NULL DEFAULT 'claimed';
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS billing_status TEXT NOT NULL DEFAULT 'unbilled';
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS input_json TEXT;
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS accepted_json TEXT;
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS result_json TEXT;
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS artifact_json TEXT;
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS error_json TEXT;
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS dispatch_owner TEXT;
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS dispatch_lease_expires_at TEXT;
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE run_requests ADD COLUMN IF NOT EXISTS dispatched_at TEXT;

UPDATE run_requests
SET execution_status = CASE
    WHEN state = 'succeeded' THEN 'succeeded'
    WHEN state = 'refunded' THEN 'failed'
    WHEN state = 'running' THEN 'dispatching'
    ELSE execution_status
  END,
  billing_status = CASE
    WHEN state = 'succeeded' THEN 'captured'
    WHEN state = 'refunded' THEN 'refunded'
    WHEN state IN ('reserved', 'running') AND billing_status = 'unbilled' THEN 'reserved'
    ELSE billing_status
  END
WHERE execution_status = 'claimed' OR billing_status = 'unbilled';

CREATE INDEX IF NOT EXISTS idx_run_requests_user_updated
  ON run_requests (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_run_requests_stale
  ON run_requests (execution_status, dispatch_lease_expires_at, updated_at);

-- Async execution telemetry is separate from the billing state machine so
-- existing installations can add it without rewriting run_requests. Progress
-- is monotonic; progress_source distinguishes elapsed estimates from signed
-- webhook checkpoints and Modal terminal status.
CREATE TABLE IF NOT EXISTS run_progress (
  run_id            TEXT PRIMARY KEY,
  user_id           TEXT NOT NULL,
  phase             TEXT NOT NULL CHECK (phase IN ('reserved', 'running', 'transcribing', 'directing', 'generating', 'assembling', 'delivered', 'failed')),
  progress_pct      INTEGER NOT NULL CHECK (progress_pct >= 0 AND progress_pct <= 100),
  progress_source   TEXT NOT NULL CHECK (progress_source IN ('derived', 'webhook', 'modal')),
  modal_status      TEXT NOT NULL,
  modal_status_url  TEXT NOT NULL,
  video_url         TEXT,
  contact_sheet_url TEXT,
  result_json       TEXT,
  input_notice      TEXT,
  started_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL,
  terminal_at       TEXT
);

CREATE INDEX IF NOT EXISTS idx_run_progress_user_updated
  ON run_progress (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS credits_ledger (
  event_id      TEXT PRIMARY KEY,             -- signup:…, run:…, stripe:…
  user_id       TEXT NOT NULL,
  kind          TEXT NOT NULL,                -- signup_grant|run_debit|run_refund|topup
  amount_cents  INTEGER NOT NULL,             -- signed balance delta
  balance_cents INTEGER NOT NULL,             -- balance after transition
  reference_id  TEXT NOT NULL,
  created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_credits_ledger_user_created
  ON credits_ledger (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS stripe_events (
  event_id     TEXT PRIMARY KEY,              -- Stripe evt_… webhook event
  session_id   TEXT NOT NULL,
  user_id      TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  applied      INTEGER NOT NULL DEFAULT 0,
  created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stripe_topups (
  session_id   TEXT PRIMARY KEY,              -- Stripe cs_… Checkout session
  user_id      TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  applied      INTEGER NOT NULL DEFAULT 0,    -- 1 once credited
  created_at   TEXT NOT NULL
);

-- Created by /api/topup before returning the Stripe URL. The signed webhook
-- must match this server-owned user, amount, and currency before crediting.
CREATE TABLE IF NOT EXISTS topup_sessions (
  session_id   TEXT PRIMARY KEY,
  user_id      TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  currency     TEXT NOT NULL CHECK (currency = 'usd'),
  state        TEXT NOT NULL CHECK (state IN ('pending', 'applied')),
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
);

-- One-time catalog ownership. /api/checkout creates the pending row from
-- server-owned catalog data before returning the hosted Stripe URL; the
-- signed checkout.session.completed webhook fills the Stripe-collected buyer
-- email and advances it exactly once. session_id and stripe_event_id provide
-- independent retry/idempotency guards.
CREATE TABLE IF NOT EXISTS purchases (
  session_id      TEXT PRIMARY KEY,              -- Stripe cs_... Checkout session
  stripe_event_id TEXT UNIQUE,                   -- Stripe evt_... completion delivery
  slug            TEXT NOT NULL,
  listing_name    TEXT NOT NULL,
  amount_cents    INTEGER NOT NULL,
  currency        TEXT NOT NULL CHECK (currency = 'usd'),
  buyer_email     TEXT NOT NULL DEFAULT '',       -- supplied or collected by Stripe
  state           TEXT NOT NULL CHECK (state IN ('pending', 'completed')),
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  completed_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_purchases_buyer_created
  ON purchases (buyer_email, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_purchases_slug_state
  ON purchases (slug, state);

-- Public launch-interest capture. The unique email constraint makes repeat
-- submissions idempotent while retaining the first recorded source.
CREATE TABLE IF NOT EXISTS waitlist (
  id         SERIAL PRIMARY KEY,
  email      TEXT NOT NULL UNIQUE,
  source     TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Creator Markdown intake. Content remains untrusted data until an agent adds
-- a reviewed profile and the compile/test/deploy gates complete. The unique
-- owner/hash pair makes retries idempotent without exposing source content.
CREATE TABLE IF NOT EXISTS submissions (
  id            TEXT PRIMARY KEY,                -- sub_… generated by Worker
  user_id       TEXT NOT NULL,                   -- verified Clerk owner
  name          TEXT NOT NULL,                   -- canonical frontmatter name
  slug          TEXT NOT NULL,
  content       TEXT NOT NULL,                   -- untrusted Markdown, <= 200 KiB
  source_sha256 TEXT NOT NULL,
  requested_runtime TEXT NOT NULL DEFAULT 'auto' CHECK (requested_runtime IN ('auto', 'worker-native', 'modal-hosted')),
  selected_runtime  TEXT CHECK (selected_runtime IN ('worker-native', 'modal-hosted')),
  runtime_policy    TEXT,
  runtime_compatibility TEXT,
  workflow_version  TEXT,
  published_slug    TEXT,
  build_evidence    TEXT,
  build_claimed_at  TEXT,
  build_attempts    INTEGER NOT NULL DEFAULT 0,
  deployment_metadata TEXT,
  release_phase     TEXT,
  release_issue_url TEXT,
  release_pr_url    TEXT,
  release_pr_number INTEGER,
  release_branch    TEXT,
  release_head_sha  TEXT,
  release_merge_sha TEXT,
  release_artifact_hash TEXT,
  modal_app         TEXT,
  modal_url         TEXT,
  canary_evidence   TEXT,
  status        TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'needs_review', 'ready_for_deploy', 'ready_for_publish', 'deployed', 'failed')),
  failure_code  TEXT,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL,
  deployed_at   TEXT,
  UNIQUE (user_id, source_sha256)
);

ALTER TABLE submissions ADD COLUMN IF NOT EXISTS requested_runtime TEXT NOT NULL DEFAULT 'auto';
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS selected_runtime TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS runtime_policy TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS runtime_compatibility TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS workflow_version TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS published_slug TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS build_evidence TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS build_claimed_at TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS build_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS deployment_metadata TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_phase TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_issue_url TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_pr_url TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_pr_number INTEGER;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_branch TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_head_sha TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_merge_sha TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_artifact_hash TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS modal_app TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS modal_url TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS canary_evidence TEXT;

CREATE INDEX IF NOT EXISTS idx_submissions_status_created
  ON submissions (status, created_at);

CREATE INDEX IF NOT EXISTS idx_submissions_user_created
  ON submissions (user_id, created_at DESC);
