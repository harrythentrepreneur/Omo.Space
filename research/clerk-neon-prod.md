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
- Local suites: balance 22/22, router 91/91, cost model 11/11.

## Stripe readiness audit and founder runbook

Last audited 2026-08-12. The supported-listing test-card loop is ready to
configure, but broad live catalog sales are **not yet fulfillment-ready**.

### Live route and code audit

- `POST /api/checkout` is guest-accessible, resolves name and price from the
  server catalog, ignores client pricing, creates a hosted Checkout Session,
  and records a pending purchase. The signed paid webhook advances that row
  idempotently (`site/deploy/worker.js:1036-1095`, `1320-1347`, `2233-2303`).
- Authenticated `POST /api/topup` enforces the server user and $5-$1,000 range,
  sends success/cancel back to the dashboard, records the pending session, and
  credits Neon exactly once after a signed paid event
  (`site/deploy/worker.js:1175-1317`, `2306-2446`).
- Stripe signatures are checked against the raw body with a five-minute
  timestamp tolerance (`site/deploy/worker.js:2520-2538`). The one shared
  webhook route is `POST /api/topup`; it handles both catalog purchases and
  credit top-ups when the `Stripe-Signature` header is present.
- Read-only invalid-signature probes returned HTTP 501 `stripe webhook not
  configured` from both `https://omo.space/api/topup` (Vercel rewrite) and
  `https://cognition-demos.harrythentrepreneurr.workers.dev/api/topup`
  (Cloudflare). A valid-slug checkout probe also returned HTTP 501 `stripe not
  configured`. This proves both origins currently serve the intended handler
  and neither Stripe Worker secret is configured. Use the stable public URL
  `https://omo.space/api/topup` in Stripe.
- Local verification passes: balance 22/22, router 91/91, cost model 11/11.

### Checkout branding isolation (implemented 2026-08-13)

The earlier assumption that hosted Checkout only supports account-level
branding is no longer correct. Stripe added Checkout Session
`branding_settings` in API version `2025-09-30.clover`; it explicitly overrides
the account's branding for that Session. Omo now pins **only** the two Session
creation requests to that version and sends a complete per-session appearance:

- display name `Omo`, the existing Omo logo and square icon by public HTTPS URL;
- canvas `#F8F7F5`, pine button `#17352C`, rounded controls, and Nunito;
- `locale=auto`, `submit_type=pay`, flow-specific `custom_text`, and clear inline
  product names/descriptions (`<workflow title>` or `Omo credits` plus the exact
  amount);
- purchase metadata for type/flow/slug/workflow/amount/currency and, when the
  request carries a verified Clerk token, user ID; top-up metadata always has
  the verified user ID plus type/flow/amount/currency;
- purchase success returns to the existing catalog success handler and cancel
  returns to the originating Omo page (with the workflow listing as fallback);
  top-ups return to `billing.html` for both success and cancellation.

Stripe's `custom_text.after_submit` is displayed below the payment button
**before** payment, not on the success page. The copy therefore says “after
payment” instead of claiming that credits/workflow access already exists.
Terms-acceptance text is intentionally omitted: enabling it would require
`consent_collection[terms_of_service]=required` and an account-configured terms
URL, neither of which this change needs.

This does not mutate the shared Account object or Dashboard settings, so it
does not restyle PhonicsMaker Checkout. The isolation is not complete outside
the Checkout page: Stripe documents that the account business name can still
appear in terms, receipts, and other surfaces, and Checkout-created invoices
still use Dashboard branding. A **separate Stripe account for Omo is the
recommended clean boundary** for checkout, receipts, legal identity, disputes,
and reporting; creating/activating it requires the founder's identity and bank
steps. Changing shared account-level branding remains not recommended because
it would affect PhonicsMaker.

Official references: [Clover branding change](https://docs.stripe.com/changelog/clover/2025-09-30/checkout-sessions-branding-settings),
[Session create parameters](https://docs.stripe.com/api/checkout/sessions/create?api-version=2025-09-30.clover),
[hosted Checkout appearance](https://docs.stripe.com/payments/checkout/customization/appearance?payment-ui=stripe-hosted&integration=api),
and [multiple Stripe accounts](https://docs.stripe.com/get-started/account/multiple-accounts).

### Gaps to fix in a follow-up code change

1. `woven-relationship-book-maker` is exposed by the storefront
   (`site/ig-more.js:406`) but is absent from `SERVER_CATALOG`
   (`site/deploy/worker.js:154-187`), so its buy button receives 404 at
   `site/deploy/worker.js:1040-1042`.
2. Many valid custom two-decimal top-ups are rejected: the Worker requires
   `amount_usd * 100` to be an exact safe integer
   (`site/deploy/worker.js:1194-1197`), but binary floating point makes values
   such as 5.02 become 501.999... cents. The preset $20/$50/$100/$200 chips
   work; custom cents need a follow-up fix.
3. A paid catalog purchase only becomes a completed Neon row. The success URL
   returns to the home page (`site/deploy/worker.js:1058`), where the query
   parameters are trusted directly into local storage without server
   verification (`site/menu-workflows.js:34-58`). The Library then labels that
   local value purchased (`site/library.js:52-55`, `116-146`), but no verified
   ownership/download API or file delivery exists. Payment recording works;
   fulfillment does not, and the local ownership display is forgeable.
4. The workflow-page checkout omits an `Idempotency-Key`
   (`site/workflow.html:1139-1142`), and top-up session creation sends none to
   Stripe (`site/deploy/worker.js:1229-1235`). A retry can create another unpaid
   session; fulfillment itself remains idempotent.
5. Only `checkout.session.completed` is handled, and only when
   `payment_status=paid` (`site/deploy/worker.js:1269-1279`). Keep delayed
   payment methods disabled for now or add `checkout.session.async_payment_succeeded`.
6. The dashboard makes one delayed balance refresh after return
   (`site/dashboard.html:1397-1400`); a slow webhook can leave a stale balance
   until manual reload.
7. The publishable key is only a browser configuration/demo flag and loads
   Stripe.js; hosted Checkout is created by the Worker. The code does not
   enforce test/live pairing (`site/stripe.js:14-20`, `120-137`). Always install
   matching-mode publishable, secret, and webhook keys.
8. Before payments, confirm production Neon has `purchases`, `topup_sessions`,
   `stripe_events`, and `stripe_topups` from `site/deploy/schema.sql`; only
   `users` and `runs` were previously production-verified.

### Exact founder steps: Stripe test mode

Identity-bound actions (email, password, phone, 2FA, identity/business details,
and bank access) are founder-only; never give them to an agent.

1. Open `https://dashboard.stripe.com`. Create an account if needed, enter the
   founder email/password, verify email and phone, and enable 2FA. Leave **Test
   mode** on. Account activation, business details, and bank details can wait
   while proving the test loop.
2. In Stripe, open **Developers -> API keys**. Confirm Test mode, then copy the
   test publishable key and reveal/copy the test secret key. Keep them in the
   founder's password manager; never paste either into chat or commit history.
3. Open **Developers (or Workbench) -> Webhooks -> Add endpoint/destination**.
   Choose the account events source, set endpoint URL to
   `https://omo.space/api/topup`, select only `checkout.session.completed`, and
   create it. Open the endpoint and reveal/copy its signing secret. Test and
   live webhook signing secrets are different.
4. Put values in these locations (names only):
   - Test publishable key -> `site/key-config.js`,
     `STRIPE_PUBLISHABLE_KEY` (public by design).
   - Test secret key -> Worker secret `STRIPE_SECRET_KEY`.
   - Test webhook signing secret -> Worker secret `STRIPE_WEBHOOK_SECRET`.

   From `site/deploy`, let Wrangler prompt securely; do not put values in the
   command line:

   ```bash
   cd /Users/yifan/marketplace/site/deploy
   npx wrangler secret put STRIPE_SECRET_KEY
   npx wrangler secret put STRIPE_WEBHOOK_SECRET
   npx wrangler deploy
   ```

5. Deploy the publishable-key change from the repository root:

   ```bash
   cd /Users/yifan/marketplace
   npx vercel --prod --yes
   ```

   Do not skip the Worker deploy after setting the Worker secrets.
6. Verify a supported listing such as **UGC Script Studio**: click Buy, confirm
   Stripe-hosted Checkout opens, use test card `4242 4242 4242 4242`, any
   future expiry, any CVC/postcode, and complete payment. In Stripe, open the
   webhook endpoint's Events/Deliveries and require HTTP 200. In Neon,
   `purchases.state` must become `completed` once, with the expected slug and
   cents. The current site does not yet deliver the purchased file.
7. Sign in to Omo, top up at least $5, use the same test card, and return to
   `dashboard.html?topup=success`. Require a 200 webhook delivery, an `applied`
   `topup_sessions` row, one top-up ledger entry, and the exact balance increase.
   Reload once if the webhook arrives after the dashboard's refresh.

### Promote to live mode later

Complete Stripe's activation checklist personally: business/legal profile,
representative verification, customer-facing details, and payout bank account.
Switch Stripe to Live mode; obtain the live publishable and secret keys; create
a **live-mode** webhook to the same `https://omo.space/api/topup` URL; then
replace all three matching-mode values and deploy the Worker and storefront
again. Do not use Stripe test cards in live mode. Fix the fulfillment gaps above
before inviting real catalog buyers.

## Waitlist contract

`POST /api/waitlist` is public and accepts JSON `{ "email": "person@example.com", "source": "creators" }`.
`source` is optional. The Worker trims and lowercases the email, returns HTTP
400 for an invalid address, and inserts it into Neon's `waitlist` table. A
first submission returns `{ "ok": true, "status": "added" }`; a repeat returns
HTTP 200 with `{ "ok": true, "status": "already" }`.

The migration-safe schema is `waitlist(id SERIAL PRIMARY KEY, email TEXT NOT
NULL UNIQUE, source TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now())`.
The unique email constraint is the endpoint's duplicate/idempotency guard.

Production verification on 2026-08-12 exercised a unique temporary address:
the first POST returned `added`, a case-variant repeat returned `already`, and
an invalid address returned HTTP 400. Neon showed the normalized row and its
source. The temporary row was then deleted; a follow-up count returned zero.

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
