# Omo storefront — Clerk, Stripe, and credits

The storefront ships safely in demo mode. With the placeholder keys, Clerk
uses `cognition_user`, purchases use `cognition_purchases_v1`, and credit
top-ups update `omo_balance_v1` in localStorage. No card is charged.

## Go live

### 1. Configure the browser once

Create a Clerk app, then copy its publishable key from **Clerk Dashboard → API
Keys**. In Stripe test mode, copy the publishable key from **Developers → API
keys**. Put both keys and the deployed worker URL in `site/key-config.js`:

```js
window.CLERK_PUBLISHABLE_KEY = 'pk_test_...';
window.STRIPE_PUBLISHABLE_KEY = 'pk_test_...';
window.OMO_API_BASE = 'https://<worker-url>';
```

`index.html`, `dashboard.html`, and `api.html` all load this file before Clerk
or Stripe, so this single edit activates the real flow everywhere. A real
Clerk key starts with `pk_test_` or `pk_live_`; a real Stripe key starts with
`pk_test_` or `pk_live_`.

### 2. Create D1 and apply the schema

```bash
cd site/deploy
npx wrangler login
npx wrangler d1 create omo-balances
```

Paste the returned `database_id` into the `[[d1_databases]]` block in
`wrangler.toml`, uncomment that block, then run:

```bash
npx wrangler d1 execute omo-balances --remote --file=schema.sql
```

The schema creates `users`, `runs`, and the idempotent `stripe_topups` ledger.
The D1 binding name must remain `BALANCE_DB`.

### 3. Set worker secrets and deploy

```bash
npx wrangler secret put STRIPE_SECRET_KEY
npx wrangler secret put CLERK_WEBHOOK_SECRET
npx wrangler secret put STRIPE_WEBHOOK_SECRET
npx wrangler secret put BALANCE_KEY_SECRET
npx wrangler secret put LLM_API_KEY
npx wrangler deploy
```

Use the Stripe test secret key (`sk_test_...`) while the browser uses a test
publishable key. Secrets live only in Cloudflare.

### 4. Connect the webhooks

In **Clerk Dashboard → Webhooks**, add:

- Endpoint: `https://<worker-url>/api/clerk-webhook`
- Event: `user.created`
- Copy its signing secret into `wrangler secret put CLERK_WEBHOOK_SECRET`

The signed `user.created` delivery provisions the user with 1000 cents
($10.00) of free credits. Repeat deliveries do not grant twice.

In **Stripe Dashboard → Developers → Webhooks**, add:

- Endpoint: `https://<worker-url>/api/topup`
- Event: `checkout.session.completed`
- Copy its signing secret into `wrangler secret put STRIPE_WEBHOOK_SECRET`

Stripe Checkout carries the Clerk user id in session metadata. After a paid
top-up, the signed webhook credits D1 exactly once; the return URL
`dashboard.html?topup=success` refreshes `/api/me`. Cancellation returns to
`dashboard.html?topup=cancelled` without changing the balance.

## Live behavior

- Clerk loads `https://cdn.clerk.com/v1/clerk.browser.js`, opens real sign-in
  and sign-up modals, and exposes the current `{ id, email, username }`.
- `/api/me` returns the D1 balance, deterministic `omo_` key, and recent runs.
- `/api/run` reserves and debits the run price; insufficient credit returns
  JSON with status `402` and `error: "insufficient_balance"`.
- `/api/checkout` creates one-time Stripe Checkout sessions for store items.
- `/api/topup` accepts only the dashboard presets: $5, $10, $25, or $50.

## Verify before launch

Use Stripe's test card `4242 4242 4242 4242`, then verify this sequence:

1. Sign up with Clerk → dashboard shows `$10.00` and an `omo_` API key.
2. Run a helper → balance decreases and the usage row appears.
3. Top up → Stripe Checkout → dashboard returns with `?topup=success` and the
   balance increases once.
4. Re-send the same Stripe webhook → the balance does not increase again.

Run the offline checks from the repository root:

```bash
node --check site/clerk.js
node --check site/stripe.js
node --check site/deploy/worker.js
node site/deploy/test-balance.mjs
node site/deploy/test-router.mjs
node site/deploy/test-cost.mjs
```
