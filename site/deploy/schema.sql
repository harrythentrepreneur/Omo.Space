-- Omo credits backend — D1 schema (apply with wrangler d1 execute).
--
--   npx wrangler d1 create omo-balances          # once, note the database_id
--   npx wrangler d1 execute omo-balances --file=schema.sql
--
-- Three tables:
--   users — one row per account: balance in cents (start $10 = 1000),
--           deterministic api key, created_at.
--   runs  — per-run debits: which helper, how much it cost, when.
--   stripe_topups — idempotent Stripe Checkout fulfillment ledger.

CREATE TABLE IF NOT EXISTS users (
  user_id       TEXT PRIMARY KEY,             -- Clerk user id (user_…)
  balance_cents INTEGER NOT NULL DEFAULT 1000,-- $10.00 signup grant, in cents
  api_key       TEXT NOT NULL,                -- 'omo_' + hash(user_id, secret)
  created_at    TEXT NOT NULL                 -- ISO timestamp
);

CREATE TABLE IF NOT EXISTS runs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     TEXT NOT NULL,                  -- Clerk user id
  slug        TEXT NOT NULL,                  -- helper slug (e.g. arcads-node-ugc-builder)
  cost_cents  INTEGER NOT NULL,               -- run price in cents (≥ 10)
  created_at  TEXT NOT NULL                   -- ISO timestamp
);

CREATE INDEX IF NOT EXISTS idx_runs_user_created
  ON runs (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS stripe_topups (
  session_id   TEXT PRIMARY KEY,              -- Stripe cs_… Checkout session
  user_id      TEXT NOT NULL,                 -- credited Clerk user
  amount_cents INTEGER NOT NULL,              -- paid amount in cents
  applied      INTEGER NOT NULL DEFAULT 0,    -- 1 once credited
  created_at   TEXT NOT NULL                  -- ISO timestamp
);
