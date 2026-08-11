# Clerk + Neon production status

Last verified: 2026-08-12 (Asia/Bishkek)

## Live production configuration

- Storefront/API origin: `https://omo.space`
- Direct Worker: `https://cognition-demos.harrythentrepreneurr.workers.dev`
- Cloudflare Worker: `cognition-demos`, account `75238d7076eddd427cfc591eeb148d83`
- Deployed Worker version: `91bd6c26-3178-46d7-b41a-dc46230aa980`
- Clerk application: `app_3HluPILc5FgO7BxWkTPsBbE28gb`
- Clerk production instance: `ins_3HlusJb7w4SSFSAdpUJ43GVe4Fc`
- Clerk primary domain: `omo.space`
- Neon project: `soft-mode-71226557`
- Neon branch: `br-gentle-flower-avgxx7bs`; database: `neondb`

The storefront serves a production (`pk_live_`) Clerk publishable key from
`site/key-config.js`. The actual key is intentionally not recorded here.
`window.OMO_API_BASE` is empty, so browser API calls use same-origin `/api/*`;
Vercel forwards those requests to the Worker.

## DNS

The following five additive CNAME records were added at Namecheap with
Automatic TTL. Existing apex, `www`, Vercel, `play`, and SRV records were not
changed.

| Host | Target |
| --- | --- |
| `clerk` | `frontend-api.clerk.services.` |
| `accounts` | `accounts.clerk.services.` |
| `clkmail` | `mail.b5bku8po4jeb.clerk.services.` |
| `clk._domainkey` | `dkim1.b5bku8po4jeb.clerk.services.` |
| `clk2._domainkey` | `dkim2.b5bku8po4jeb.clerk.services.` |

Clerk reports the primary domain **Verified**, DNS configuration **Verified**,
and SSL certificates **Issued**. The Clerk instance is the Production
environment and uses live keys; no Clerk live-mode or DNS action remains.

## Clerk webhook

- Endpoint: `https://omo.space/api/clerk-webhook`
- Description: `Omo signup credit grant`
- Subscribed events: `user.created`, `user.deleted`
- Signing secret: configured in Clerk and as the Worker secret
  `CLERK_WEBHOOK_SECRET`; value intentionally omitted
- Verification: a signed Clerk `user.deleted` example delivery succeeded on
  2026-08-11. This exercises signature verification without creating or
  crediting a user.
- An unsigned empty POST returns HTTP 401 `invalid signature`, confirming the
  route is live and fails closed.

The Worker intentionally grants credits only for `user.created`; other events,
including `user.deleted`, are acknowledged and ignored.

## Worker configuration

`npx wrangler whoami` confirms the expected Cloudflare account. `npx wrangler
secret list` confirms these secret names are configured:

- `NEON_DATABASE_URL` (pooled Neon connection)
- `CLERK_SECRET_KEY`
- `CLERK_WEBHOOK_SECRET`
- `BALANCE_KEY_SECRET`

Non-secret Worker vars include `CLERK_PUBLISHABLE_KEY`, `LLM_BASE_URL`,
`LLM_MODEL`, `MIN_TOPUP_USD`, `MAX_TOPUP_USD`,
`CLERK_CLOCK_SKEW_SECONDS`, and `RUN_RESERVATION_TTL_SECONDS`.

Do not commit secret values. Only publishable keys belong in
`site/key-config.js` or `wrangler.toml`.

## Production verification evidence

- `GET https://omo.space/api/me` without auth: HTTP 401
  `authentication_required`.
- Valid-slug `POST https://omo.space/api/run` without auth: HTTP 401
  `authentication_required`.
- `POST https://omo.space/api/topup` without auth: HTTP 401
  `authentication_required`.
- Direct-Worker browser checks return the same 401 shapes. Terminal `curl` from
  this agent environment timed out connecting to the `workers.dev` hostname;
  the same deployed Worker is reachable through `omo.space` and in Chromium.
- Read-only SQL through the pooled Neon URL confirmed public tables `users` and
  `runs`; both contained 0 rows before the first real signup. The local `psql`
  binary was unavailable, so the equivalent SELECTs were executed with the
  repo's installed official `@neondatabase/serverless` driver.
- Local suites: balance 22/22, router 88/88, cost model 11/11.

## Stripe checkout contract

`POST /api/checkout` is intentionally guest-accessible so landing-page buyers
do not need a Clerk session. It accepts a required catalog `slug`, an optional
`email`, and an optional `Idempotency-Key` header. Any client `priceUsd` is
ignored: the Worker resolves the listing name and one-time price from
`SERVER_CATALOG`, returns 404 for an unknown slug, returns 501 until
`STRIPE_SECRET_KEY` exists, and otherwise returns `{ "url": "https://checkout.stripe.com/..." }`.
Stripe collects the buyer email when it is omitted. Signed-in callers use the
same contract; ownership is durably keyed by the Checkout Session and the
Stripe-collected buyer email after the signed webhook completes.

Useful repeatable checks:

```bash
cd site/deploy
npx wrangler whoami
npx wrangler secret list
node test-balance.mjs
node test-router.mjs
node test-cost.mjs

curl -i https://omo.space/api/me
curl -i -X POST https://omo.space/api/clerk-webhook \
  -H 'Content-Type: application/json' --data '{}'
```

After obtaining a Neon connection string locally, schema verification can be
repeated without putting the value in shell history:

```bash
psql "$NEON_DATABASE_URL" -c \
  "SELECT to_regclass('public.users'), to_regclass('public.runs');"
```

## Remaining user actions

1. **Stripe production credentials and webhook.** Set these two Worker secret
   values (the values themselves must never be committed):

   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`

   Configure Stripe to send `checkout.session.completed` to
   `https://omo.space/api/topup`. That single signed endpoint handles both
   credit top-ups and one-time catalog purchases. After the secrets are set
   and the deployment includes the migration-safe `schema.sql`, no code change
   is needed.
2. **Perform one real identity test.** Sign up at `https://omo.space` with a new
   account. Then confirm the dashboard shows `$5.00` and query Neon for that
   Clerk user ID: `users.balance_cents` must equal `500`. This is the only
   remaining proof of `user.created` -> Clerk webhook -> Neon signup grant.
