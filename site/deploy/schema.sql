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
  api_key       TEXT NOT NULL,                -- 'omo_' + hash(user_id, secret)
  created_at    TEXT NOT NULL                 -- ISO timestamp
);

CREATE TABLE IF NOT EXISTS runs (
  user_id     TEXT NOT NULL,
  slug        TEXT NOT NULL,
  cost_cents  INTEGER NOT NULL,
  created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_user_created
  ON runs (user_id, created_at DESC);

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
