# GATE 1 — deploy commands + magic-link spec (for Kaviru)

## Part A: Deploy the payment loop (copy-paste, in order)

```bash
cd /Users/yifan/marketplace/site/deploy
npm install                                   # if node_modules missing

# 1. Secrets — get values from Harry (Stripe dashboard / Neon console)
npx wrangler secret put STRIPE_SECRET_KEY     # paste sk_live_...
npx wrangler secret put STRIPE_WEBHOOK_SECRET # paste whsec_...
npx wrangler secret put NEON_DATABASE_URL     # paste Neon pooled URL

# 2. Apply the ledger schema to Neon
psql "$NEON_DATABASE_URL" -f schema.sql

# 3. Route omo.space/api/* to the Worker
#    In wrangler.toml, uncomment the [[routes]] block and set custom_domain = true:
#      [[routes]]
#      pattern = "omo.space/api/*"
#      custom_domain = true

# 4. Deploy
npx wrangler deploy
```

Without the three secrets the Worker runs in MOCK mode and /api/checkout and
/api/topup return 501. With them + the route, the loop is live.

## Part B: Canary (run after deploy, before any email)

```bash
cd /Users/yifan/marketplace/site/deploy
node test-balance.mjs
node test-router.mjs
node test-cost.mjs
node test-workers.mjs
```

Plus the 20-run manual canary checklist in marketing/payment-loop-spec.md
(bad input, timeout, duplicate submit, provider failure, refund path, magic
link reuse/expiry, concurrent runs). Gate: >=95% valid-output success, 0
double-charges, 100% auto-refund on failure, <5% refunds.

## Part C: Magic-link feature (the ONE new build)

Goal: signed one-click email link -> Clerk auth -> deep-link into the book
builder with a one-free-book grant. No signup form, no homepage detour.

1. Generate (server-side):
   POST /api/magic-link { email, slug }
   -> creates a single-use, signed, short-TTL (15 min) token, stores it,
      returns https://omo.space/magic?token=<t> (or a /magic route).
   Reuse Clerk's magic-link/sign-in token if it supports a redirect; otherwise
   a small HMAC token table in Neon is fine.

2. Click flow:
   /magic?token=... validates the token (single-use, not expired), starts
   Clerk sign-in for that email, then redirects to
   /run.html?slug=<slug>&grant=free_book
   — authenticated, already inside the book builder.

3. Free-book grant:
   On first arrival after magic auth, set a one-time free_book_grant flag
   (ledger row or users column). The first successful book run consumes it and
   charges $0. The second book charges normally.
   NOTE (Harry's decision): KEEP the existing $5 signup grant. The free book is
   an additional pilot lead-magnet, not a replacement.

4. Acceptance:
   - Link works once, expires, and cannot be replayed.
   - User lands authenticated, directly in the book builder, first book $0.
   - Second book debits credits correctly (idempotent, no double-charge).

## Part D: Trust cleanup (storefront)

Hide or label "not available yet" every listing that cannot currently be bought
and delivered. A "proven workflows" storefront cannot open with ambiguous proof.
