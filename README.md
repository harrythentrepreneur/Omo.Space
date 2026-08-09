# Cognition — the AI helper store

Fiverr for the new age: an AI workflow/tool marketplace. Browse AI helpers (automated versions of Fiverr-style gigs — UGC scripts, product photos, ad copy, video, SEO, Shopify ops), try a free demo, then own the files (download) or run them through our API on our cloud.

**Live frontend:** deployed on Vercel (see DEPLOY.md for the exact steps).

## Layout

- `site/` — the storefront (single-file vanilla HTML/JS/CSS: `index.html` + listing catalogs `ig-workflows.js` / `ig-more.js`, auth `clerk.js`, payments `stripe.js`, library `library.js`, creator page `creators.html`, `SETUP.md` for keys)
- `site/deploy/` — Cloudflare demo worker (`worker.js`: `/api/run` demo + `/api/checkout` Stripe) + cost model (`cost-model.mjs`: runPrice = max(cost×5, $0.10), 5x launch markup) + tests
- `containers/` — Modal workflow containers (ugc-heygen async video, claude-seo-skill pure-LLM, gpt-image-seedance-ad LLM+GPU image gen) — the backend engine
- `research/` — market research, acquisition playbook, Modal container plan
- `landing/` — earlier landing-page explorations (archive)

## Pricing model

FREE (some helpers, prompts given away) · ONE-TIME $3–200 (download the workflow + prompts) · PER-USE API (we run it on our cloud, keys handled; 5x launch markup on cost, floor $0.10).

## Domain

`omo.best` — the live storefront domain (Vercel).

## Stack

Static storefront on Vercel · Cloudflare Worker demo API · Modal for workflow containers · Clerk auth · Stripe Checkout.

---

Built by Hermes Agent for Cognition. The user is the co-pilot (domain, accounts, keys); the assistant is the operator.
