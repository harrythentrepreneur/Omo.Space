# Omo MCP integration

`mcp-server.mjs` exports `handleMcpRequest(request, env)`. It implements MCP over Streamable HTTP with JSON-RPC 2.0 and shares the REST worker's balance and cost modules.

## Worker wiring

Add the import at the top of `worker.js`, then route `/mcp` immediately after the request URL is created and before the `ROUTES` lookup. The complete three-line wiring is:

```js
import { handleMcpRequest } from './mcp-server.mjs';
const url = new URL(request.url);
if (url.pathname === '/mcp') return handleMcpRequest(request, env);
```

`worker.js` already creates `url`, so keep its existing declaration and add only the import plus the `if` line. Route before `const route = ROUTES[url.pathname]`; otherwise the REST router will return its unknown-route response.

In Cloudflare, attach this Worker to the narrow production route `omo.best/mcp*` (or create an equivalent Vercel rewrite to the Worker). The narrow route lets Vercel continue serving the rest of `site/`, including the two catalogue JavaScript files and the discovery document.

The MCP module uses the same environment bindings as the REST routes:

- `NEON_DATABASE_URL` (preferred), `BALANCE_DB` (D1 fallback), or in-memory mock storage
- `BALANCE_KEY_SECRET` and `SIGNUP_GRANT_USD`
- `LLM_API_KEY`, with optional `LLM_BASE_URL` and `LLM_MODEL`
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

The self-test covers `initialize`, the initialized notification, `tools/list`, every `tools/call`, request-id matching, and JSON-RPC errors. It must finish with `SELFTEST PASS`.

## Smoke-test the deployed endpoint

Initialize (the response includes `Mcp-Session-Id`):

```sh
curl -i https://omo.best/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
```

Copy the returned session header, then list tools:

```sh
curl https://omo.best/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Mcp-Session-Id: PASTE_SESSION_ID' \
  --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Also verify discovery:

```sh
curl -i https://omo.best/.well-known/mcp.json
```

Top-ups are deliberately outside MCP v1. `omo_topup_options` returns the supported amounts and sends users to `https://omo.best/dashboard.html` for Stripe Checkout.
