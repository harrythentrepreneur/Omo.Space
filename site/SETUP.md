# Omo storefront — Clerk, Stripe, and credits

Omo has two deliberate modes:

- **Demo/mock:** no Clerk key, payment secret, or durable database. The browser
  keeps its local balance and the worker preserves the legacy `user_id` demo
  requests. `LLM_API_KEY` may still be set to power demos.
- **Real:** enabled by Clerk, Stripe/payment secrets, `BALANCE_KEY_SECRET`,
  Neon, or D1. Account routes fail closed and never trust body/query
  `user_id`. A payment-only partial setup therefore cannot expose mock credit
  accounts.

## 1. Configure the browser

Create Clerk and Stripe applications, then put their publishable keys and the
deployed Worker URL in `site/key-config.js` as described by that file. The
storefront obtains a Clerk session token and sends it as:

```http
Authorization: Bearer <Clerk session JWT>
```

## 2. Create the credits database

Neon is recommended:

```bash
cd site/deploy
psql "$NEON_DATABASE_URL" -f schema.sql
npx wrangler secret put NEON_DATABASE_URL
```

For D1, create the database, uncomment `[[d1_databases]]` in
`wrangler.toml`, and apply the same schema:

```bash
npx wrangler d1 create omo-balances
npx wrangler d1 execute omo-balances --remote --file=schema.sql
```

The schema includes hashed API-key ownership, the credit ledger, pending
Stripe top-ups, and the `run_requests` state machine. Reapply it before
deploying this worker version.

## 3. Set Worker configuration

```bash
npx wrangler secret put CLERK_PUBLISHABLE_KEY
npx wrangler secret put CLERK_WEBHOOK_SECRET
npx wrangler secret put STRIPE_SECRET_KEY
npx wrangler secret put STRIPE_WEBHOOK_SECRET
npx wrangler secret put BALANCE_KEY_SECRET
npx wrangler secret put LLM_API_KEY
npx wrangler deploy
```

`CLERK_PUBLISHABLE_KEY` must be the same Clerk instance used by the browser.
The Worker decodes its Frontend API hostname, fetches
`/.well-known/jwks.json`, caches the JWKS, and verifies RS256 signature,
issuer, subject, time claims, and authorized party. The default clock skew is
5 seconds.

`wrangler.toml` sets a $5 minimum, $1,000 maximum top-up, and a five-minute
stale run-reservation timeout. Override those vars only with deliberate
values.

## 4. Connect webhooks

In Clerk, subscribe `user.created` to:

```text
https://<worker>/api/clerk-webhook
```

In Stripe, subscribe `checkout.session.completed` to:

```text
https://<worker>/api/topup
```

Real-mode Clerk deliveries require a valid Svix signature; a missing signing
secret returns 503. Stripe top-ups are credited only when the signed, paid USD
session matches the server-created pending record's session, user, and amount.
Repeat deliveries do not credit twice.

## Real API behavior

- `/api/me` and `/api/topup` require a verified Clerk session token.
- `/api/run` accepts either a Clerk token or the owning `omo_` API key via
  `Authorization: Bearer` (also `X-API-Key`).
- Real `/api/run` requires `Idempotency-Key` (8–128 safe characters). Replays
  return the stored result/state and do not charge or call the LLM again.
- Run prompt, model, token cap, workflow metadata, and price are resolved by
  slug from the Worker catalog. Unknown real-mode slugs are rejected.
- `/api/checkout` ignores client prices and uses catalog slug/name/price.
- Real CORS allows `https://omo.space`, the temporary compatibility origin `https://omo.best`, and `http://localhost:<port>` only.

## Verify before launch

Use Stripe test mode and confirm: sign up → $5 balance; run with one
idempotency key → one debit; replay → same run and balance; top up → one
credit; replay webhook → no second credit.

Run the offline checks from the repository root:

```bash
node --check site/deploy/worker.js
node site/deploy/test-balance.mjs
node site/deploy/test-router.mjs
node site/deploy/test-cost.mjs
git diff --check
```
