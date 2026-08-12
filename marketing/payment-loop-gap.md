# Payment-loop gap analysis (tick-001)

Finding: the payment loop is ~80% built in code. The remaining work is
deployment + one pilot feature, NOT a greenfield build. Do not rebuild.

## Already implemented (verified in code)

- Storefront: live Stripe publishable key + Clerk live key wired (site/key-config.js).
- Checkout: server-created hosted Stripe Checkout (POST /api/checkout), server-priced.
- Top-up: POST /api/topup, $5 min, Stripe Checkout + signed fulfillment.
- Idempotency: run_requests row is claimed BEFORE debit (account-scoped key) — concurrent retries cannot double-charge.
- Billing state machine: reserved/running/succeeded/refunded + billing_status unbilled/reserved/captured/refund_due/refunded (site/deploy/schema.sql).
- Auto-refund: on insufficient balance (402 + state refunded) and on terminal timeout (DEMELLO_RUN_TIMEOUT_SECONDS).
- $5 signup grant: /api/clerk-webhook user.created -> grantSignupCredits.
- Balance: Neon users.balance_cents via authenticated GET /api/me.
- Worker LLM routing already uses deepseek-v4-flash (wrangler.toml vars).

## Remaining to ship GATE 1 (in order)

1. Secrets (Harry + Kaviru): `wrangler secret put STRIPE_SECRET_KEY` (sk_live),
   `STRIPE_WEBHOOK_SECRET`, `NEON_DATABASE_URL`; then apply schema.sql to Neon.
   Without these the Worker runs MOCK mode and checkout/topup return 501.
2. Route omo.space/api/* to the Worker (uncomment [[routes]] custom_domain or set
   the Workers route) — the "final authorization + canary" in the hosting runbook.
3. Canary: run the repo suites against the live Worker (test-balance, test-router,
   test-workers) plus the 20-run canary checklist in payment-loop-spec.md.
4. NEW pilot feature — magic link: signed one-click link -> Clerk auth -> deep-link
   into the book builder with a one-free-book grant (not blanket $5). This is the
   only genuinely new code.
5. Trust: hide or relabel storefront listings that cannot currently be bought and
   delivered.
6. Minor: top-up client has no idempotency key (low risk with Checkout redirect,
   but add one for safety).

## Blocked on Harry

- Stripe live secret + webhook secret (from Stripe dashboard) or confirm Kaviru pulls them.
- Decide: keep the $5 blanket signup grant or switch to the pilot "one free book" grant (sol recommended the latter).
- Pull the 200-person segment (recently active + opted-in + non-paying; exclude unsubscribes and active subscribers).
