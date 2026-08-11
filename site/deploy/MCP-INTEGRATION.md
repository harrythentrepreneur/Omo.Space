# Omo MCP integration

`mcp-server.mjs` exports `handleMcpRequest(request, env)`. It implements stateless MCP over Streamable HTTP with JSON-RPC 2.0 and shares the REST worker's balance and cost modules. It does not issue or require `Mcp-Session-Id`: an instance-local session map is unsafe under Worker scaling. `worker.js` mounts it at `/mcp` and supplies an in-process binding back to the same REST router, so video runs have one billing/state authority.

## Worker wiring

The wiring is already present in `worker.js`:

```js
import { handleMcpRequest } from './mcp-server.mjs';
// /mcp is routed before the REST route lookup; its OMO_API binding invokes
// the same Worker handler for /api/run and /api/run/{id}.
```

If MCP is deployed as a separate Worker, bind `OMO_API` as a Cloudflare service binding to the Omo API Worker. `OMO_API_BASE_URL` is the network fallback for non-Workers runtimes. Do not point MCP at Modal: it must call the buyer-facing Worker contract so reservation, idempotency, ownership, progress, settlement, and refunds remain centralized.

In Cloudflare, attach this Worker to the narrow production route `omo.best/mcp*` (or create an equivalent Vercel rewrite to the Worker). The narrow route lets Vercel continue serving the rest of `site/`, including the two catalogue JavaScript files and the discovery document.

The MCP module uses the same environment bindings as the REST routes:

- `NEON_DATABASE_URL` (preferred), `BALANCE_DB` (D1 fallback), or in-memory mock storage
- `BALANCE_KEY_SECRET` and `SIGNUP_GRANT_USD`
- `LLM_API_KEY`, with optional `LLM_BASE_URL` and `LLM_MODEL`
- `OMO_API` (recommended service binding for a separate MCP Worker), or `OMO_API_BASE_URL`
- optional Workers Static Assets binding `ASSETS`, or `OMO_SITE_ORIGIN=https://omo.best`, to refresh catalogue data from `/ig-workflows.js` and `/ig-more.js`

If static catalogue fetches are unavailable, the module uses its server-owned runtime-safe snapshot. Client prompts, workflows, and prices are never trusted.

## Discovery file

The discovery document lives at `site/.well-known/mcp.json`, which is the correct path under this repository's Vercel `outputDirectory: "site"`. After deployment, verify that `https://omo.best/.well-known/mcp.json` returns JSON rather than a clean-URL rewrite or 404.

Vercel normally serves files inside `.well-known` from the output directory. If a deployment pipeline strips dot-directories, explicitly copy `site/.well-known/mcp.json` into the final `site/.well-known/` output during the build (or add an equivalent Vercel rewrite to a non-dot static copy). Do not move the public URL: MCP clients expect `/.well-known/mcp.json`.

## Test locally

Run the syntax check and complete offline self-test:

```sh
node --check site/deploy/mcp-server.mjs
node site/deploy/mcp-server.mjs --selftest
```

The self-test covers stateless `initialize`, the initialized notification, `tools/list`, every `tools/call`, request-id matching, JSON-RPC errors, ownership checks, mandatory video idempotency, an async video submit, progress polling, and result delivery. Use the count printed by the current self-test as the gate.

## Async video tools

`omo_run_helper` keeps its existing behavior for the other helpers. For `japanese-style-story-video`, it requires both the owning `omo_` API key and a caller-owned `idempotency_key`, calls `POST /api/run`, and immediately returns `run_id`, `status`, `phase`, `progress_pct`, `status_url`, `input_notice`, and billing metadata. The key is 8–128 safe characters and must be reused for retries of identical inputs. The listing quotes $0.10, but this nonpaid milestone returns `billed_amount_usd:0`, `billing_mode:"nonpaid_milestone"`, and `paid_traffic_ready:false`.

The hosted milestone accepts only `audio_ref=sample-demello-10s`; arbitrary HTTPS audio is rejected before dispatch/provider spend. Compatibility topic text, if supplied, is explicitly replaced with the bundled sample and the resulting `input_notice` is forwarded by run, progress, and result tools.

Use `omo_get_run_progress` with `{run_id, api_key}` while the run is active. It returns `{status, phase, progress_pct, progress_source, ready, input_notice}`. `progress_source` is `modal` for Modal-native checkpoints, `webhook` for authenticated callbacks, or `derived` for the explicitly labeled elapsed-time fallback.

Use `omo_get_run_result` with the same owner credentials. Before completion it returns `ready:false`; after delivery it returns `ready:true`, `video_url`, and (when present) `contact_sheet_url`. Signed Modal Volume URLs expire, so fetch the result again if a download URL has aged out.

## Smoke-test the deployed endpoint

Initialize. The response intentionally does not include `Mcp-Session-Id`:

```sh
curl -i https://omo.best/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
```

Each request is independent, so list tools without a session header:

```sh
curl https://omo.best/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Also verify discovery:

```sh
curl -i https://omo.best/.well-known/mcp.json
```

`omo_get_balance` requires possession of the owning `omo_` key. It does not accept arbitrary Clerk user IDs, create accounts, or return any raw/hashed credential. Top-ups are deliberately outside MCP v1. `omo_topup_options` returns the supported amounts and sends users to `https://omo.best/dashboard.html` for authenticated Stripe Checkout.
