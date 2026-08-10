# Cognition — Demo API Deployment (Cloudflare Workers)

Deploy-ready artifacts for the three marketplace demos, served from ONE Worker:

| Route | Demo | Output |
|---|---|---|
| `POST /api/ugc-script-studio` | UGC Script Studio | `{ hook, shots[], captions[], cta }` |
| `POST /api/meta-ads-analyser` | Meta Ads Analyser | `{ verdict, winners[], losers[], quick_wins[], next_move }` |
| `POST /api/product-photo-generator` | Product Photo Generator | `{ shot_plan[], background_suggestion, caption, listing_copy }` |

Files in this directory:
- `worker.js` — merged worker (router + 3 handlers + hardened prompts + normalizers + demo caps)
- `wrangler.toml` — single project config (`cognition-demos`)
- `test-workers.mjs` — offline unit tests for the parse normalizers (`node test-workers.mjs`)

**No real API keys anywhere in this directory.** The LLM key is set as a Cloudflare secret at deploy time.

---

## 1. Prereqs

- Node 18+ (for wrangler)
- Cloudflare account with the **cognition.cv** zone (NS is already `jen/thomas.ns.cloudflare.com` — no nameserver change needed)

## 2. Install + login

```bash
npm i -g wrangler
cd /Users/yifan/marketplace/site/deploy
wrangler login          # opens browser, authorize the account
```

## 3. Set the LLM key as a secret

```bash
wrangler secret put LLM_API_KEY
# paste the opencode/deepseek key when prompted (stays in Cloudflare, never in git)
```

Optional but recommended: `wrangler secret put LLM_BASE_URL` / `LLM_MODEL` if you
don't want the defaults in `wrangler.toml` (`https://opencode.ai/zen/go/v1`, `deepseek-v4-flash`).

## 4. (Optional) Enable per-IP daily demo caps via KV

Without this the worker runs uncapped (still works):

```bash
wrangler kv namespace create BENCH_KV
# copy the returned id into wrangler.toml under [kv_namespaces], then:
wrangler deploy
```

Caps enforced per route: UGC 5/day, Meta 3/day, Photo 5/day (per IP per day), plus input/token caps from `wrangler.toml` vars.

## 4a. Enable credits with Neon (recommended)

The worker uses `NEON_DATABASE_URL` when present, then D1 when bound, then an
in-memory zero-config demo store. Neon queries use the lightweight serverless
driver, a small connection pool, named prepared statements, and no ORM.

```bash
cd /Users/yifan/marketplace/site/deploy
npm install
psql "$NEON_DATABASE_URL" -f schema.sql
npx wrangler secret put NEON_DATABASE_URL
npx wrangler secret put BALANCE_KEY_SECRET
```

`schema.sql` is idempotent and also remains D1-compatible. It creates users,
runs, an immutable credits ledger, and Stripe event/session idempotency tables.
Without either database, each mock account starts with $5 locally.

## 4b. Connect Stripe test, then production

Point a Stripe webhook at `https://<worker>/api/topup` for
`checkout.session.completed`, then set its secret alongside the API secret:

```bash
npx wrangler secret put STRIPE_SECRET_KEY
npx wrangler secret put STRIPE_WEBHOOK_SECRET
```

The same checkout code handles test and production. Use Stripe test secrets
while validating, then replace both Worker secrets with their live equivalents
and change `STRIPE_PUBLISHABLE_KEY` in `site/key-config.js` from a test to a live
publishable key. Never commit any real secret. Checkout credits the account
only after a signed paid webhook, idempotently by Stripe event and session.

## 5. Deploy

```bash
wrangler deploy
# → https://cognition-demos.<your-account-subdomain>.workers.dev
```

## 6. Attach the custom domain (cognition.cv)

Dashboard route (recommended):
1. Cloudflare dashboard → **Workers & Pages** → `cognition-demos`
2. **Settings** → **Domains & Routes** → **Add custom domain**
3. Enter `demo.cognition.cv` (or `cognition.cv` for the apex)
4. Cloudflare auto-creates the proxied DNS record (orange cloud). Verify in **DNS → Records**:
   - Subdomain: `CNAME demo → cognition-demos.<account-subdomain>.workers.dev` (proxied), or
   - Apex: `A cognition.cv` (proxied) with CNAME flattening — replace the current 401 nginx placeholder records (`172.67.201.168` / `104.21.21.254`) as the worker takes over.
5. NS stays `jen/thomas.ns.cloudflare.com`. No DNS provider change.

Alternative (deploy-time, no dashboard clicks): uncomment the `[[routes]]` block in `wrangler.toml`:
```toml
[[routes]]
pattern = "demo.cognition.cv/api/*"
custom_domain = true
```

## 7. Storefront (site/index.html) on Cloudflare Pages

The `/api/*` paths belong to the Worker; everything else is the storefront static site.

Option A — wrangler pages deploy (no GitHub needed):
```bash
cd /Users/yifan/marketplace/site
npx wrangler pages deploy . --project-name cognition-storefront
# then in the dashboard: Pages project → Custom domains → add www.cognition.cv or cognition.cv
```

Option B — GitHub integration:
1. Push `/Users/yifan/marketplace` to GitHub (or a repo containing `site/`)
2. Dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
3. Repo → build command: `none`, output directory: `site`
4. After first build: **Custom domains** → `cognition.cv` (apex) or `www.cognition.cv`

DNS notes for Pages:
- Apex `cognition.cv` → Pages auto-creates proxied `A`/`AAAA` records (CNAME flattening); remove the nginx placeholder A records.
- `www.cognition.cv` → proxied `CNAME www → cognition-storefront.pages.dev`.

## 8. Smoke-test the live endpoints

`<BASE>` = `https://cognition-demos.<account-subdomain>.workers.dev` or `https://demo.cognition.cv`.

```bash
# UGC Script Studio
curl -sS -X POST "$BASE/api/ugc-script-studio" \
  -H 'Content-Type: application/json' \
  -d '{"product":"A silk pillowcase that prevents sleep creases, $60, hypoallergenic, 30-day trial","voice":"raw","length":30}'

# Meta Ads Analyser (goal: roas|cpa|ctr|scale)
curl -sS -X POST "$BASE/api/meta-ads-analyser" \
  -H 'Content-Type: application/json' \
  -d '{"goal":"roas","ads_export":"campaign,spend,impressions,clicks,purchases,revenue\nprospecting-v1,412.00,82000,3100,38,1876.00\nretarget-v2,198.00,14000,980,52,2210.00\nbrand-test,150.00,61000,220,2,87.00"}'

# Product Photo Generator (style: clean|lifestyle|hero)
curl -sS -X POST "$BASE/api/product-photo-generator" \
  -H 'Content-Type: application/json' \
  -d '{"product_description":"Handmade ceramic coffee mug, 12oz, matte sage glaze","photo_url":"","style":"lifestyle"}'

# Error paths
curl -sS -i -X OPTIONS "$BASE/api/ugc-script-studio"      # 200 + CORS headers
curl -sS -i "$BASE/api/ugc-script-studio"                 # 405 POST only
curl -sS -i -X POST "$BASE/api/nope"                      # 404 unknown route
curl -sS -i -X POST "$BASE/api/ugc-script-studio" \
  -H 'Content-Type: application/json' -d '{}'             # 400 missing product
```

Expected success shape (ugc): `{ "ok": true, "script": { ... }, "raw": "..." }`.
If you hit the daily cap: `429 { "error": "Free demo limit reached for today. ..." }`.

## 9. Rollback / updates

- Redeploy after edits: `wrangler deploy` (same project, instant).
- Version history + instant rollback: dashboard → Worker → **Deployments**.
- `wrangler tail` to watch live requests while testing.
