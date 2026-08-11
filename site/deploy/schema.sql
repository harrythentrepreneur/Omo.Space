-- Omo credits backend — Neon Postgres + D1-compatible schema.
--
-- Neon (recommended): psql "$NEON_DATABASE_URL" -f schema.sql
-- D1 fallback: npx wrangler d1 execute omo-balances --file=schema.sql
--
-- Deliberately uses TEXT timestamps and INTEGER booleans so this idempotent
-- schema is accepted by both Postgres and SQLite/D1. The worker inserts ids.

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
  cost_cents      INTEGER NOT NULL,
  state           TEXT NOT NULL CHECK (state IN ('reserved', 'running', 'succeeded', 'refunded')),
  response_json   TEXT,
  http_status     INTEGER,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  UNIQUE (user_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_run_requests_user_updated
  ON run_requests (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_run_requests_stale
  ON run_requests (state, updated_at);

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
