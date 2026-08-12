# Issue 8 deployment evidence

Verified on 2026-08-12.

## Modal

- Workspace: `harrythentrepreneur`
- App: `cognition-ugc-script-studio`
- Protected production endpoint: `https://harrythentrepreneur--cognition-ugc-script-studio-api.modal.run`
- Endpoint authentication: Modal Proxy Token (`requires_proxy_auth=True`)
- Unauthenticated health request returned HTTP `401`, confirming the endpoint is not browser-public.
- Real provider-backed canary run: [Modal run](https://modal.com/apps/harrythentrepreneur/main/ap-GICtUKbNlpDpgqatpsH4Wm)
- Sanitized result: `status=completed`; result keys were `captions`, `cta`, `hook`, `shots`; five shots and five captions passed output-schema validation.
- No credential values or raw provider response are recorded here.

## Vercel

`vercel build --yes` completed successfully and compiled `api/v1/runs.js` as a Vercel Function. The route validates the registered workflow input, requires an idempotency key, fails closed when Modal server configuration is absent, and projects only canonical safe fields from Modal.

Required Vercel environment variable names:

- `NEON_DATABASE_URL`
- `CLERK_PUBLISHABLE_KEY`
- `MODAL_UGC_ENDPOINT`
- `MODAL_PROXY_TOKEN_ID`
- `MODAL_PROXY_TOKEN_SECRET`
- `CRON_SECRET`

Values are intentionally not committed.

## Tests

- Python compiler/generated-runtime suites: 15 passed
- Node Vercel control-plane suite: 16 passed
- Existing Cloudflare compatibility suites: 11 + 22 + 91 + 17 passed
- Existing Modal container suites: 38 + 29 + 52 passed
- Deterministic regeneration diff: clean
- Vercel build: passed
