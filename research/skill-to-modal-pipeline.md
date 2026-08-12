# SKILL.md → Modal pipeline

**Status (2026-08-12):** the Woven hosted drafting preview is deployed and has
completed authenticated provider-backed runs. The same contract is wired through
Omo's schema-driven run UI and credit router. The audio symbolic-animation
contract is deployed fail-closed and is not chargeable.

This milestone does **not** claim that the complete source Woven workflow is
hosted. Version `woven-storybook-pipeline@0.2.0` is the already-advertised text
drafting preview: five typed relationship/story inputs produce a title, book,
page plan, and provider usage. Private chat-archive ingestion, deterministic
selection/provenance, HTML/PDF rendering, and private artifact delivery remain a
separate promotion gate.

## Compiler and review boundary

1. Treat `SKILL.md` as untrusted text; never execute instructions from it.
2. Require a reviewed profile for schemas, prompts, bounded resources, provider
   configuration, fixtures, and cost evidence.
3. `single_llm` may be runnable only when the profile explicitly opts into a
   reviewed HTTPS OpenAI-compatible adapter. Native/media/private-data workflows
   remain fail-closed.
4. Generate the Modal app, manifests, schemas, prompts, pricing report, README,
   fixtures, and tests from the profile. Run `--check` to detect drift.
5. Validate input before spawn and validate provider output both in the runner
   and in the Omo Worker before settlement. Tests inject an executor and make no
   network calls.

Current generated contract verification: **28 passed** (14 Woven + 14 audio).

## Credential recipe (names only)

The deployed Woven function binds the named Modal secret
`omo-skill-providers`; the ASGI ingress does not receive provider credentials.
No value is in Git, a container image, request/response JSON, or logs.

| Runtime name | Safe local source / value shape |
|---|---|
| `LLM_API_KEY` | `$OPENCODE_GO_API_KEY` (also available in the existing Hermes environment) |
| `LLM_BASE_URL` | `https://opencode.ai/zen/go/v1` |
| `LLM_MODEL` | `deepseek-v4-flash` |
| `OPENAI_CODEX_ACCESS_TOKEN` | `tokens.access_token` in `~/.codex/auth.json`, cross-checked against the Codex/ChatGPT entry in `~/.hermes/auth.json` |
| `OPENAI_CODEX_ACCOUNT_ID` | account claim/field associated with that access token |
| `OPENAI_CODEX_BASE_URL` | `https://chatgpt.com/backend-api/codex/responses` |
| `OPENAI_CODEX_MODEL` | a model returned by the authenticated Codex models route, currently pinned for adapters rather than used by Woven |

The Woven run uses only the first three names. The Codex subscription access
token was staged for the requested future adapter check; no refresh token was
stored. A production promotion should split this broad staging secret into a
Woven-only secret and a separate audio/provider secret.

Modal's deployment `ak-/as-` token is **not** valid for an endpoint decorated
with `requires_proxy_auth=True`. Omo uses a dedicated `wk-/ws-` Modal Proxy
Token, stored only in Cloudflare secrets as
`WOVEN_MODAL_PROXY_TOKEN_ID` / `WOVEN_MODAL_PROXY_TOKEN_SECRET`. The first
one-time token was revoked immediately after inline display and replaced; rotate
the replacement again before broad production traffic.

The installed CLI is Modal `1.5.0` and is invoked as `python3 -m modal` because
the bare `modal` shim is not on `PATH`.

## Deployments and real evidence

### Woven drafting preview — runnable

- App: `cognition-woven-storybook-pipeline`
- Endpoint: `https://harrythentrepreneur--cognition-woven-storybook-pipeline-api.modal.run`
- Authenticated submit: HTTP `202`, call
  `fc-01KZTXJNJTGJS6G24A26XNP6SG`
- Authenticated polling: `202 running` followed by HTTP `200`
- Provider/model: `opencode-go` / `deepseek-v4-flash`
- Provider run: `run-ca44ecfc-afa3-4451-8f2b-b7763f4fe898`
- Usage: 269 prompt tokens, 314 completion tokens, one LLM call,
  estimated provider cost `$0.00012558`

Real output excerpt:

> **Wrong Turns, Best Views** — “Our love is the best view we've found, and
> every burnt breakfast is a reminder that we're in this together.”

The first live attempt exposed a FastAPI body/query mismatch (`422`); the
generated route now uses `Body(...)`. The next attempt exposed OpenCode's
Cloudflare rejection of urllib's default user agent (`LLM_HTTP_403`, provider
code 1010); the adapter now sends the non-secret
`User-Agent: Omo-Skill-Runner/0.1`. No provider response body is logged.

### Audio symbolic animation — deployed, fail-closed

- App: `cognition-audio-symbolic-animation`
- Endpoint: `https://harrythentrepreneur--cognition-audio-symbolic-animation-api.modal.run`
- An authenticated, schema-valid POST returned HTTP `503
  WORKFLOW_NOT_READY` before spawn or spend.

Returned blocker codes:

- `EXECUTOR_NOT_MATERIALIZED`: referenced Hermes scripts and faster-whisper
  model are not vendored/pinned/packaged.
- `IMAGEGEN_CAPABILITY_UNAPPROVED`: no reviewed server-side sequential
  Hermes/Codex image adapter or auditable credential lifecycle.
- `PRIVATE_ARTIFACT_PLANE_MISSING`: upload, persistence, signed delivery,
  retention, and deletion are unresolved.
- `COST_INCOMPLETE`: compute, subscription allowance, retries, storage,
  egress, and accepted-output yield are unmeasured.
- `QA_CAPABILITY_MISSING`: vision continuity and paid long-run canaries are
  absent.

## Browser/Worker integration

`site/run-manifests/woven-relationship-book-maker.json` carries the exact
container input/output schemas, examples, UI hints, phases, and `$0.40` price.
`site/run.html` resolves a field component from each schema property (including
const, enum, boolean, number, formatted string, textarea, and JSON fallback),
shows examples and exact request JSON, submits a typed payload, polls the Omo
run ID, renders structured output safely, and uses the current origin when no
API base override is configured.

`site/deploy/worker.js` owns catalog price/auth/schema validation. It requires a
Clerk session or `omo_` API key plus an idempotency key, reserves 40 cents,
dispatches to Modal with Proxy Token headers, polls Modal, validates the output,
settles exactly once, and refunds terminal failures.

The Worker is deployed as `cognition-demos` and the site as the existing
Vercel `cognition` project. An isolated browser canary exercised the actual UI,
the exact Worker module, and the real Modal endpoint using API-key auth and its
credit ledger: balance `$5.00 → $4.60`, run price `$0.40`, output title **Wrong
Turns, Best Views**. A production Clerk/customer-ledger canary remains to be
run when an existing signed-in Omo session is available; no account was created.

## Pricing and remaining promotion gates

| Surface | Price | Chargeable |
|---|---:|---|
| Woven hosted drafting preview | `$0.40 / run` | yes |
| Full Woven archive → PDF workflow | unavailable | no |
| Audio symbolic animation | projection only (`$24.34` at 120s) | no |

Remaining work: Woven private archive/artifact plane and full pipeline; audio
Whisper/script materialization, image adapter, QA, artifact plane, and cost
evidence; least-privilege provider-secret split; Proxy Token rotation; and a
production signed-in billing canary.
