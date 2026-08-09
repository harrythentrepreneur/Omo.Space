# Cognition storefront — going live with Clerk + Stripe

The storefront ships in **demo mode**: signing in fakes a local user, and buying
records a simulated purchase. Nothing is charged and no accounts are created
until you drop in real keys. This page walks you from demo → live.

## How demo mode works today (zero keys)

| Piece | Demo behavior |
| --- | --- |
| Auth (`clerk.js`) | Placeholder `pk_test_placeholder` → "sign in" fakes `cognition_user` in localStorage |
| Payments (`stripe.js`) | Placeholder `pk_test_placeholder` → buy records to `cognition_purchases_v1`, shows "It's yours — check your library." |
| Worker (`/api/checkout`) | No `STRIPE_SECRET_KEY` → returns `501`, frontend falls back to the simulated purchase |
| Credits (`/api/me`, `/api/topup`, `/api/run`, `/api/clerk-webhook`) | No `BALANCE_DB` binding → MOCK MODE: in-memory Map grants every user $10 + a deterministic `omo_` API key; the dashboard reads `omo_balance_v1` / `omo_apikey_v1` / `omo_usage_v1` from localStorage and top-ups are simulated |

Both placeholders live at the top of the inline script in `site/index.html`:

```html
window.CLERK_PUBLISHABLE_KEY = 'pk_test_placeholder';
window.STRIPE_PUBLISHABLE_KEY = 'pk_test_placeholder';
```

Anything containing `placeholder` counts as "not configured" — the demo flow
stays on until you really swap them.

## 1. Clerk (real sign-in / sign-up)

1. Create a free app at <https://dashboard.clerk.com> (Sign in → **Add application**; name it `cognition`).
2. In the app, go to **API Keys**.
3. Copy the **Publishable key** (starts `pk_test_` or `pk_live_`).
4. Paste it into `site/index.html`:

```html
window.CLERK_PUBLISHABLE_KEY = 'pk_test_your_real_key_here';
```

That's it — `clerk.js` loads the real Clerk SDK, and "Sign in" opens the real
Clerk modal (sign-in + sign-up). Sign-out and the user object (id, email,
username) come from the real session. Library stays keyed to the same
localStorage purchases, so nothing else changes.

> Optional: in the Clerk dashboard, under **Domains**, add your production
> domain (`https://cognition.cv`) once deployed; Clerk allows localhost during
> development.

## 2. Stripe (real payments)

Two keys are needed: a **publishable** key for the storefront, and a **secret**
key for the worker (the secret must never ship in the browser).

1. Create an account at <https://dashboard.stripe.com> (test mode is on by default and free).
2. Go to **Developers → API keys**.
3. Copy the **Publishable key** (`pk_test_...`) into `site/index.html`:

```html
window.STRIPE_PUBLISHABLE_KEY = 'pk_test_your_real_key_here';
```

4. Give the worker the **Secret key** (`sk_test_...`) as a secret — never in code:

```bash
cd site/deploy
npx wrangler login
npx wrangler secret put STRIPE_SECRET_KEY   # paste sk_test_... when prompted
npx wrangler deploy
```

The worker's `/api/checkout` route (added in `site/deploy/worker.js`) now
creates a real Checkout Session and the storefront redirects the buyer to
Stripe's hosted page. Test checkout with Stripe's test card `4242 4242 4242 4242`.

### Checkout URLs (worker)

- success → `https://cognition.cv/?purchased=<slug>` (the storefront can read
  this param to auto-open the library — not wired yet)
- cancelled → `https://cognition.cv/?purchased=cancelled`

## 3. Credits + dashboard backend (balance, API key, top-ups)

Every Omo account starts with **$10 of free credits**. Signed-in API runs debit
the balance at the cost-model run price (5x markup, **$0.10 floor**); when the
balance is too low the worker returns `402 insufficient_balance` and the
storefront says "top up on your dashboard". Top-ups go through Stripe Checkout.
API keys are deterministic: `omo_` + a hash of `(user_id, secret)` — no key
database, the same user always gets the same key.

The flow: **Try demo → Clerk signup → redirected to `dashboard.html`** (once per
browser — the `omo_seen_dashboard` flag) → top-right shows **Balance $10.00**
pill + masked API key chip (click to reveal, click again to copy) → Top up
form → Usage list of recent runs.

### Mock mode today (zero keys)

`dashboard.html` works from `file://` or any static host with no backend:

- Balance defaults to `$10.00`, API key is derived from the (demo) user id —
  both in localStorage (`omo_balance_v1`, `omo_apikey_v1`).
- "Top up with Stripe" simulates adding the amount (`omo_balance_v1`).
- Usage lists localStorage entries (`omo_usage_v1`).
- The worker's `/api/me` does the same server-side from an in-memory Map when
  no D1 binding exists (`mock: true` in the response).

### Going live: D1 (balances)

```bash
cd site/deploy
npx wrangler d1 create omo-balances            # note the database_id it prints
```

Uncomment the `[d1_databases]` block in `wrangler.toml` and paste the
`database_id` (binding must be `BALANCE_DB`), then apply the schema:

```bash
npx wrangler d1 execute omo-balances --file=schema.sql
```

Two tables: `users` (`user_id`, `balance_cents` — starts at 1000, `api_key`,
`created_at`) and `runs` (`user_id`, `slug`, `cost_cents`, `created_at`).

### Going live: Clerk webhook (the $10 grant)

1. Clerk dashboard → **Webhooks** → **Add endpoint**.
2. Endpoint URL: `https://<your-worker>/api/clerk-webhook`.
3. Event: **user.created** (that's the grant trigger — `INSERT OR IGNORE`, so
   repeat deliveries never double-grant, and a user who was already
   provisioned by `/api/me` keeps their balance).
4. Copy the **Signing secret** and set it on the worker:
   ```bash
   npx wrangler secret put CLERK_WEBHOOK_SECRET
   ```
   Without it the signature check is skipped (mock/local); with it, every
   webhook is HMAC-verified (svix headers, ±5 min timestamp window).

### Going live: Stripe top-ups

- `STRIPE_SECRET_KEY` is already how `/api/checkout` works — `/api/topup`
  reuses it. `POST /api/topup {user_id, amount_usd}` creates a Checkout
  Session (`success_url` → `https://omo.best/dashboard.html?topup=success`).
  Without the secret it returns `501` and the dashboard simulates the top-up.
- The session carries `client_reference_id` + `metadata[user_id]` so the
  credits can be applied server-side. **Crediting after payment** needs one
  more webhook: Stripe → Developers → Webhooks → add `checkout.session.completed`
  → `https://<your-worker>/api/stripe-webhook` (not built yet — until then,
  paid top-ups are recorded in Stripe but not auto-applied to D1; the mock
  path applies instantly).

### API key entropy

Keys are deterministic per `(user_id, secret)`. The secret comes from
`BALANCE_KEY_SECRET` (set it), falling back to `LLM_API_KEY`, then a dev
constant. `npx wrangler secret put BALANCE_KEY_SECRET` is recommended before
launch.

### Dashboard API base

`site/dashboard.html` (and the storefront demo runner) read
`window.OMO_API_BASE` — set it to the deployed worker
(e.g. `'https://demo.omo.best'`) in the inline script of both pages; empty =
same-origin.

## 4. Flip from demo to live (checklist)

- [ ] Real Clerk key in `index.html` (`window.CLERK_PUBLISHABLE_KEY`)
- [ ] Real Stripe publishable key in `index.html` (`window.STRIPE_PUBLISHABLE_KEY`)
- [ ] `STRIPE_SECRET_KEY` set on the worker (`wrangler secret put STRIPE_SECRET_KEY`)
- [ ] D1 created + schema applied + `[d1_databases]` uncommented in `wrangler.toml`
- [ ] `CLERK_WEBHOOK_SECRET` set + webhook endpoint configured in the Clerk dashboard
- [ ] `BALANCE_KEY_SECRET` set on the worker
- [ ] `OMO_API_BASE` pointed at the deployed worker in `index.html` + `dashboard.html`
- [ ] Worker deployed (`cd site/deploy && npx wrangler deploy`)
- [ ] Storefront deployed to Cloudflare Pages (`cd site && npx wrangler pages deploy . --project-name cognition-storefront`)
- [ ] Verify: sign up with a real email → redirected to the dashboard ($10 balance + API key) → run a helper (balance debits) → top up → Stripe Checkout → `?topup=success` → refreshed balance

Still demoing? The simulated flow never charges anything, so it's safe to
exercise on the live URL until the keys are in.

## Worker tests

```bash
cd site/deploy
node test-router.mjs   # routes incl. /api/checkout, /api/me, /api/topup, /api/clerk-webhook
node test-cost.mjs
node test-balance.mjs  # credits core: $10 grant, debits, 402 semantics, api keys, top-ups
```
