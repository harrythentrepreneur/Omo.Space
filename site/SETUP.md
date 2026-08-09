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

## 3. Flip from demo to live (checklist)

- [ ] Real Clerk key in `index.html` (`window.CLERK_PUBLISHABLE_KEY`)
- [ ] Real Stripe publishable key in `index.html` (`window.STRIPE_PUBLISHABLE_KEY`)
- [ ] `STRIPE_SECRET_KEY` set on the worker (`wrangler secret put STRIPE_SECRET_KEY`)
- [ ] Worker deployed (`cd site/deploy && npx wrangler deploy`)
- [ ] Storefront deployed to Cloudflare Pages (`cd site && npx wrangler pages deploy . --project-name cognition-storefront`)
- [ ] Verify: sign up with a real email → buy → Stripe Checkout → success URL → purchase in library

Still demoing? The simulated flow never charges anything, so it's safe to
exercise on the live URL until the keys are in.

## Worker tests

```bash
cd site/deploy
node test-router.mjs   # includes /api/checkout (501 without secret, session with)
node test-cost.mjs
```
