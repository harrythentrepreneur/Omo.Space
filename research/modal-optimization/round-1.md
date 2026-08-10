# Modal hosting optimization — Round 1 first-pass audit

**Date:** 2026-08-10  
**Scope:** [`modal-container-plan.md`](../modal-container-plan.md), the three checked-in containers, the Cloudflare Worker, cost model, D1 schema, and go-live automation.  
**Decision:** keep the plan's core Modal architecture and keep full HeyGen UGC as the first **paid production workflow**, but reverse the immediate build order: secure and make the Cloudflare control plane durable before connecting a paid Modal provider.

## Executive verdict

The plan has the right long-term separation—untrusted discovery, constrained spec generation, deterministic compilation, allowlisted adapters, authenticated Modal execution, and QA-gated publication. It also correctly treats Modal deployments as persistent definitions whose containers scale to zero, not deployments to create and destroy per buyer request.

The repository is not yet a production path, however. The most urgent work is outside Modal:

1. The public Worker has no buyer authentication or authorization. It trusts client-supplied `user_id`, prompt, workflow slug, token limit, and checkout price.
2. D1 has no durable workflow state, client idempotency, ownership, release version, provider job ID, artifacts, reservation state, or actual cost ledger.
3. All three Modal endpoints fail for normal JSON requests. Their FastAPI handlers declare `body: Any`, which FastAPI interprets as a required query parameter; a real `POST ... json={...}` returns `422` before executing the workflow.
4. The HeyGen adapter is unresolved and disabled, and the GPU workflow returns deterministic fake URLs. Only the pure-LLM SEO implementation performs its claimed core operation—and its product value is deliberately limited because it cannot browse or crawl.
5. Pricing has already drifted: the plan and UGC container use 1.25x-era `$0.15` HeyGen pricing, while the authoritative [`cost-model.mjs`](../../site/deploy/cost-model.mjs) now uses `MARKUP = 5.0`, making the modeled price `$0.60`.

This is a good architecture plan plus three useful canaries, not an integrated marketplace engine. Do not expose paid provider execution until P0 identity, run-state, and billing work is complete.

## Audit evidence snapshot

| Check | Result | Production meaning |
|---|---|---|
| UGC tests | 29 pass | Good schema/parser/unit coverage; no HeyGen, durable state, or real HTTP proof |
| SEO tests | 38 pass | Good offline single-LLM coverage; normal JSON HTTP request still returns `422` |
| Image tests | 52 pass | Good contract scaffolding; GPU result is explicitly `MOCK` and produces no pixels |
| Combined container test command | Fails during collection | All suites are named `test_contract.py` without package isolation; shared CI is not working |
| Worker/router tests | 66 pass | They validate current behavior, including unauthenticated, client-selected identity/pricing |
| Cost/balance tests | 33 pass | Math is internally consistent at 5x, except one stale test label says “25% markup” |
| `go-live.sh` dry run | Passes | Deploys only Cloudflare, not Modal, and omits the Stripe webhook secret required to credit top-ups |
| UGC `spec_hash` and source hash | Recomputed and match | The one implemented content-digest mechanism is sound |
| Canonical spec schema/compiler/release registry | Absent | `container.yaml` is descriptive; nothing centrally validates or compiles it yet |

The reported “29/38/52 tests” are therefore real but narrower than they appear. The endpoint tests call Python route functions directly instead of sending ASGI HTTP requests, which is why the `body: Any` defect escaped.

## The five highest-leverage optimizations

### 1. Make Cloudflare the authoritative authenticated control plane

**Leverage:** critical security, revenue protection, and a stable front door for every future workflow.

The Worker must derive identity from a verified Clerk session/JWT or a verified Omo API key. It must never accept `user_id` as authority. Today:

- [`handleGenericRun`](../../site/deploy/worker.js) reads `body.user_id`, `body.system_prompt`, `body.slug`, and `body.max_tokens`.
- [`handleMe`](../../site/deploy/worker.js) accepts any `user_id` and returns that account's balance, run history, and deterministic API key.
- [`handleCheckout`](../../site/deploy/worker.js) accepts buyer-supplied `priceUsd`.
- [`handleTopup`](../../site/deploy/worker.js) accepts buyer-supplied `user_id`.
- `getUserRecord` lazily creates any supplied identity with `$10` of credits.
- CORS is `*` and does not allow an `Authorization` header.

That permits account enumeration, API-key disclosure, arbitrary balance draining, unlimited arbitrary-prompt LLM proxying, price tampering, and farming of signup credits.

Replace the public contract with server-authoritative operations:

```text
POST /api/runs              {workflow_slug, input}
GET  /api/runs/{run_id}
POST /api/topups            {amount_usd}
GET  /api/me
POST /api/checkouts         {listing_slug}
```

The Worker should:

1. Verify the Clerk bearer token or Omo API key and derive `user_id`.
2. Resolve `workflow_slug` in a server-side immutable release registry.
3. Load the input schema, prompt/spec hash, price, max tokens, and Modal route from that release.
4. Reject all client-supplied system prompts, provider names, prices, release hashes, and resource limits.
5. Call Modal using environment-scoped Proxy Token credentials stored only as Worker secrets. Browsers should never see Modal URLs or credentials.
6. Authorize every result lookup by `(run_id, user_id)`.

**Concrete files:** refactor `handleGenericRun`, `handleMe`, `handleCheckout`, and `handleTopup` in [`worker.js`](../../site/deploy/worker.js); add a server-owned `site/deploy/workflow-registry.mjs`; replace weak FNV-derived keys in [`balance.mjs`](../../site/deploy/balance.mjs) with random, revocable keys whose hashes are stored at rest; restrict CORS to Omo origins and allow `Authorization`, `Idempotency-Key`, and `Content-Type`.

### 2. Build a durable, idempotent run and credit ledger before the HeyGen adapter

**Leverage:** prevents duplicate paid renders, lost balances, cross-tenant result access, and irreconcilable support cases.

The current [`schema.sql`](../../site/deploy/schema.sql) records a completed debit as only `(user_id, slug, cost_cents, created_at)`. The Worker debits, calls the provider, then inserts this row. A crash after debit loses the audit record; a successful provider call followed by an `addRun` failure is refunded and returned as failed, letting a retry spend provider money twice. There is no idempotency key.

Modal `FunctionCall` is an execution handle, not business storage. Modal currently retains Function inputs/outputs for **up to seven days**, while Omo needs order history, callback handling, refunds, and durable artifact access. The public API must return only an Omo `run_id`; keep `modal_call_id` internal.

Replace/extend `runs` with at least:

```text
run_id TEXT PRIMARY KEY
user_id TEXT NOT NULL
workflow_slug TEXT NOT NULL
release_hash TEXT NOT NULL
idempotency_key TEXT NOT NULL
request_hash TEXT NOT NULL
status TEXT NOT NULL
price_cents INTEGER NOT NULL
reserved_cents INTEGER NOT NULL
actual_cost_microusd INTEGER
modal_call_id TEXT
provider_job_id TEXT
result_object_key TEXT
error_code TEXT
created_at / started_at / completed_at / updated_at
UNIQUE(user_id, workflow_slug, idempotency_key)
```

Add append-only `credit_ledger`, `run_events`, and `artifacts` records. Separate purchased credits from promotional credits so `$10` signup grants can be restricted or expired without corrupting cash balances. Use a D1 transaction/batch or a database trigger to atomically create the idempotent run and reserve credits; settlement, failure refund, and top-up must also be idempotent state transitions. Cloudflare documents D1 `batch()` as transactional and rollback-on-failure, so contention and replay tests should exercise that guarantee.

Require `Idempotency-Key` on paid submissions. Same key plus same request hash returns the existing run; same key plus a different hash returns `409`. Persist the HeyGen job ID immediately after creation and use the marketplace `run_id` as provider idempotency input.

**Concrete files:** redesign [`schema.sql`](../../site/deploy/schema.sql), replace `reserveRunCredits`/`refundRunCredits`/`addRun` with a run-state repository in `worker.js`, and add concurrency/replay/crash-boundary tests to [`test-router.mjs`](../../site/deploy/test-router.mjs).

### 3. Standardize one public run contract and one shared runtime/test harness

**Leverage:** fixes the current endpoints and prevents 15 incompatible code forks.

Externally, use one asynchronous resource contract even when a workflow is fast:

```json
POST /api/runs
{
  "workflow_slug": "ugc-heygen-video",
  "input": {"...": "..."}
}

202
{
  "run_id": "run_...",
  "status": "queued",
  "status_url": "/api/runs/run_..."
}
```

For LLM-only workflows, support `Prefer: wait=10` (or a bounded server option) so a warm, fast completion may return `200` without creating a second client API. The run still exists durably. Long provider/GPU jobs always return `202`.

Internally, retain execution classes rather than workflow-specific frameworks:

- shared CPU LLM/provider runtime;
- asynchronous provider adapter runtime;
- model-specific GPU Functions/Classes;
- deterministic local transforms.

Do not deploy 15 copies of FastAPI, JSON recovery, schema loading, error mapping, OpenAI setup, and response envelopes. Those functions are already triplicated across the three `modal_app.py` files. The YAML vocabulary has also drifted: `openai_compatible` versus `openai-compatible`, `output_schema` versus `output_schema_ref`, `cost_tags` versus `cost_buckets`, and different binding roots. GPT image's top-level YAML says max 10 containers/300 seconds while its GPU Function uses 5/180.

Immediate fixes:

- Replace `body: Any` with a Pydantic model or `body: dict = Body(...)` in all three apps.
- Add real ASGI tests using `TestClient.post(..., json=...)`, auth failure tests, and response-envelope schemas.
- Give test modules unique names or package each tests directory so one root pytest command passes.
- Extract JSON/schema/prompt/provider/error code into a versioned shared runtime package.
- Add the missing `container-spec.schema.json` and validate all YAML in CI before building the compiler.
- Configure the OpenAI client explicitly. The installed SDK defaults observed here are a 600-second read timeout and two retries, contradicting the SEO/image spec's `max_provider_retries: 0` and exceeding the SEO Function's 150-second timeout.

### 4. Tune cold starts by runtime class; remove polling containers from production

**Leverage:** lower tail latency, higher concurrency, and less operational complexity for bursty traffic.

`min_containers=0` is correct at launch. `scaledown_window=2` for every Function is not a measured production setting; it nearly guarantees a cold start between human-paced requests. Modal says warm-up can range from seconds to minutes and the default idle window is 60 seconds.

At current base rates, one 0.25-core/512-MiB CPU container costs approximately:

```text
0.25 × $0.0000131 + 0.5 × $0.00000222 = $0.000004385/second
60 idle seconds = $0.000263
30 days continuously warm = $11.37
```

Therefore:

- Keep `min_containers=0` for execution pools.
- Start the small shared CPU ingress/runtime at `scaledown_window=30–60`, then tune against p50/p95 cold starts and arrival gaps. Even 15 one-minute idle CPU containers cost only about `$0.00395` for that minute.
- Do not set one warm container on every workflow. One continuously warm CPU pool is about `$11.37/month`; 15 separate pools are about `$170.49/month`, or roughly `$340.98/month` if each workflow keeps both API and runner pools warm.
- Add `@modal.concurrent` to network-bound shared ASGI/LLM work after load testing so concurrent waits do not force a new container per request.
- Keep GPU `min_containers=0`; bake model weights into the image or a versioned Volume and evaluate CPU/GPU memory snapshots only after a real model is selected and profiled.

The 15-minute HeyGen polling loop would cost about `$0.00395` in CPU/memory at the same base rates. That is only ~3.3% of the current `$0.12045` modeled COGS, but it occupies one of `max_containers=10` for the full render. At the later 1.25x price, it also consumes ~13.4% of the modeled `$0.02955` gross profit. More importantly, ten long polls cap that runner at ten concurrent jobs.

For the smoke test, polling is acceptable. For paid production, HeyGen should call a public Cloudflare webhook whose signature, timestamp, and event ID are verified. The Worker updates D1, resumes/finalizes the run, and copies media to R2. The Modal container should end after provider submission instead of sleeping.

### 5. Make cost and promotional-credit policy runtime truth, not constants

**Leverage:** protects gross margin and limits fraud while allowing prices to fall safely later.

Current modeled launch economics are:

| Workflow | Modeled COGS | Current 5x/floor price | Modeled gross margin before infra/failures |
|---|---:|---:|---:|
| Claude SEO | `$0.00020` | `$0.10` | `99.8%` |
| HeyGen UGC | `$0.12045` | `$0.60` | `79.9%` |
| GPT image/Seedance canary | `$0.22020` | `$1.10` | `80.0%` |

The plan's `$0.15` HeyGen price and the UGC YAML's `production_buyer_run_price_usd_pending: 0.15` are stale. At 1.25x, `$0.15` yields only 19.7% modeled gross margin before Modal, retries, failed renders, R2, egress, support, and refunds. Do not apply a global future 1.25x switch. Price each release from the greater of its validated estimate and recent p95 actual COGS, add retry/failure reserve, and enforce a target contribution margin.

The generic cost model also silently substitutes a `$0.05` API cost and the DeepSeek rate for unknown codes/models. Compilation and publication must fail on unknown cost codes. Runtime responses must not hardcode usage constants; record actual provider token usage, request IDs, Modal duration/resource class, storage, retry count, and cost-table version.

The GPU estimate is internally inconsistent with the intended implementation. The image workflow charges three `openai_image` calls (`$0.12`) **and** two local Modal GPU buckets (`$0.10`), even though the design says image generation will be local. At Modal's current base A10 rate of `$0.000306/second`, 30 seconds is `$0.00918`; the generic `$0.05` bucket equals about 163 A10 seconds. Remove remote image charges when the final path is local and price from measured GPU seconds plus storage.

Finally, `$10` of unrestricted promotional credit has material abuse exposure:

- 16 HeyGen runs fit at `$0.60`, costing about `$1.93` in modeled providers per signup.
- 9 image runs fit at `$1.10`, costing about `$1.98` per signup.
- 1,000 farmed signups would therefore create roughly `$1,900–$2,000` of modeled provider exposure before infrastructure.

Keep the headline credit if it is important for conversion, but split promo/purchased balances. Allow promo credit on cheap LLM demos initially; require verified email/anti-abuse controls and preferably a payment method or first top-up before external video/GPU spend.

## The three biggest risks

### Risk 1 — Critical: unauthenticated identity, pricing, and arbitrary execution

An attacker can submit another `user_id`, read their API key through `/api/me`, spend their balance, create unlimited lazy users with grants, choose an arbitrary system prompt, and set checkout price. Optional KV caps are not bound in `wrangler.toml`, and a request with any `user_id` skips the anonymous cap anyway. This must block production deployment.

**Required mitigation:** verified identity at the Worker, server-owned registry and prices, no client prompts/resource limits, strict CORS/rate limits, random revocable API keys, promo-credit controls, and private Worker-to-Modal authentication.

### Risk 2 — Critical: the tested execution path is neither functional nor durable

All three real JSON HTTP submissions currently return `422`; HeyGen is disabled; GPU output is fake; and the business has no durable run state or idempotency. A paid retry can duplicate external spend, while a Modal call/result disappears as durable history after its retention window. The current tests give false confidence because they bypass HTTP transport and paid providers.

**Required mitigation:** ASGI integration tests, D1 run state/ownership/idempotency, transactional reservations, real provider staging tests, signed webhook handling, R2 artifacts, and exactly-once settlement semantics.

### Risk 3 — High: source-of-truth drift plus premature autopilot

Prompts, schemas, spec vocabulary, resource settings, costs, and markup already disagree across the plan, Worker, workflow catalog, YAML, and Python. `egress_allowlist` is declarative only; Modal Functions have general network egress unless the application/runtime constrains it. An autopilot that generates packages or code before a spec schema/compiler/adapter policy exists would amplify drift into supply-chain, secret, and cost incidents.

**Required mitigation:** one versioned spec schema, deterministic compiler, shared adapter runtime, pinned allowlisted dependencies, function-scoped secrets, application-enforced provider operations, release hashes, manual approval for new paid adapters, and no autonomous public promotion until several manually built workflows have production telemetry.

## What the existing plan gets right

These decisions should be preserved in later rounds rather than re-litigated:

- **Deploy once, invoke many, scale containers to zero.** Never run `modal deploy` or `modal app stop` in a buyer request.
- **CPU for remote API orchestration.** HeyGen and the hosted LLM do not justify a Modal GPU.
- **Typed, fail-closed contracts.** Draft 2020-12 schemas, `additionalProperties: false`, strict parsing, negative fixtures, and cross-field semantic checks are the right foundation.
- **Control-plane/data-plane separation.** Discovery/spec agents must not receive production provider secrets or deployment authority.
- **Constrained specs and deterministic compilation.** Source posts, READMEs, and SKILL.md are evidence, not executable instructions.
- **Stable step IDs, bindings, provenance, immutable hashes, and unresolved-field rejection.** The UGC hash implementation recomputes correctly.
- **Named secrets and Modal Proxy Tokens.** Modal endpoints should remain private and provider secrets should be injected at Function scope.
- **Asynchronous API shape for long work.** Submit/status is correct for video and GPU; expose Omo run IDs rather than Modal IDs.
- **Idempotent paid provider mutations.** One marketplace run ID must follow the request through provider submission, callback, billing, and artifact storage.
- **Owned artifact storage.** Provider URLs may expire; copy successful output to R2 and record checksum/metadata.
- **Layered QA and bounded repair.** Deterministic contract/media/cost/security gates outrank an LLM judge, and full paid tests should run once per immutable release hash.
- **One shared runtime for 15+ workflows.** Separate immutable specs do not require 15 independent provider/runtime forks.
- **Rights, consent, claims, and provenance gates.** These are product requirements, not optional compliance paperwork.

## Container-by-container audit

### `containers/ugc-heygen`

**Keep:** strongest public contract, separate API and runner, protected Modal endpoint, strict schemas, prompt assets, matching spec/source hashes, captions length check, no unnecessary GPU, and an explicit unresolved/disabled paid step.

**Fix before staging:** real JSON body model; durable marketplace ownership/idempotency; HeyGen adapter and normalized error/retry behavior; explicit SDK timeout/retry; webhook path; R2 copy; actual usage ledger; production output schema that requires a non-null video on `completed`; curated server-side avatar/voice choices rather than raw provider IDs; current 5x price (`$0.60` pending reconciliation), not `$0.15`.

The API container correctly lacks provider secrets. Keep that least-privilege split.

### `containers/claude-seo-skill`

**Keep:** cheapest operational canary, one bounded LLM step, strict output schema, good anti-hallucination prompt language, and no false claim that it crawls.

**Do not make it the first public paid workflow:** it cannot inspect the supplied URL, so its result is a niche-specific checklist rather than an audit. The listing claim that it replaces a `$2k/mo` agency risks product disappointment. Use it internally to prove authentication, registry resolution, Modal invocation, D1 settlement, and a warm/cold SLO at approximately `$0.0002` provider cost.

**Fix:** JSON body model; `@modal.concurrent` after load testing; explicit OpenAI timeouts/retries; stable provider error codes; a schema for the full `{status,result,usage}` response; shared runtime extraction.

### `containers/gpt-image-seedance-ad`

**Keep:** useful future GPU contract, aspect/dimension validation, LLM-to-image binding, protected endpoint, and clear admission that the current output is a mock.

**Cut now:** do not deploy an A10 merely to SHA-256 a prompt and return nonexistent `mock.cognition.market` URLs. That validates neither model loading, cold start, pixels, storage, nor GPU cost. Keep the mock as an offline adapter until a model, license, weight strategy, quality bar, and artifact store are selected.

**Fix before revival:** remove `provider_secret` from `generate_images_gpu` because that Function does not need LLM/OpenAI credentials; pick and pin the actual model; reconcile YAML versus Function resource limits; replace mixed OpenAI-image/GPU cost buckets with measured resources; use async run state; add image decode/content/identity tests; bake or volume-mount weights and evaluate snapshots.

## Target production request path

```text
Buyer / API client
        │ Clerk JWT or Omo API key + Idempotency-Key
        ▼
Cloudflare Worker — public control plane
  authenticate → resolve immutable release → validate input
  create run + reserve credits atomically → return Omo run_id
        │ private Modal Proxy Token
        ▼
Shared Modal ingress / execution-class dispatcher
        ├── CPU LLM/provider adapter
        ├── async paid-provider submitter
        └── model-specific GPU Function
                    │
                    ▼
Provider callback → Cloudflare signed webhook
  update D1 → copy/check artifact in R2 → settle/refund ledger
                    │
                    ▼
GET /api/runs/{run_id} — owner-authorized durable result
```

This keeps Clerk, balances, prices, ownership, and business state at the edge; Modal owns bounded execution; R2 owns files; D1 owns workflow state and money events. Modal Proxy Tokens and provider secrets never reach the browser.

## Concrete first production workflow

Build **`ugc-heygen-video@0.2.0`: one 15-second, 9:16 UGC video using a curated avatar and voice**.

Public input should be:

```json
{
  "product_description": "10–2000 characters",
  "brand_voice": "raw | honest | hype | luxury | funny",
  "avatar_style": "creator-a | creator-b | creator-c",
  "voice_style": "warm | energetic | premium"
}
```

Resolve provider `avatar_id` and `voice_id` server-side. Output must include the grounded script, captions, an Omo-owned MP4 URL, duration, checksum/artifact metadata, and a stable usage/price record. Start with one duration to constrain quality and provider variance; add 30/60-second tiers only after actual invoices and latency are observed.

At the current repository estimate, launch price is `$0.60` at 5x (`$0.12045 × 5 = $0.60225`, rounded by current code). Publish that only after reconciling the HeyGen account invoice and measuring p95 full cost. A safer pricing function rounds upward to the next cent and uses `max(recent_p95_COGS, release_estimate) × target_multiple`.

Why this is first:

- It delivers an actual buyer artifact, unlike the SEO checklist and fake image URLs.
- It is CPU-only on Modal and modeled below the `$0.20` release budget.
- It exercises the architecture Omo must solve once: async state, provider idempotency, callbacks, artifact storage, billing settlement, and media QA.
- It has approximately 80% modeled gross margin at current 5x pricing before unmodeled overhead.

The SEO container should run **first operationally** as a private zero-risk canary. It should not be the first production listing.

## What to build first, and what to cut

### Build order

1. **P0 — identity and authority:** Clerk/API-key verification, server-owned workflow registry/prices, restrictive CORS, no client `user_id`/prompt/token/price.
2. **P0 — durable money/run state:** D1 run state, idempotency, ownership, transactional reserve/settle/refund, promo/purchased credit separation, R2 artifact metadata.
3. **P0 — honest integration tests:** repair JSON body declarations; test real ASGI requests; make the combined test command pass; test replay, concurrency, unauthorized reads, and crash boundaries.
4. **P1 — private SEO canary:** Worker → private shared Modal endpoint → D1 settlement, with warm/cold latency and actual LLM usage recorded.
5. **P1 — HeyGen production adapter:** curated choices, idempotent submit, signed callback, R2 copy, media/claim checks, real cost reconciliation, one production smoke run.
6. **P1 — limited paid beta:** cap concurrency/spend, deny expensive promo-credit use, alert on failure/cost/duplicate/render latency.
7. **P2 — spec schema/compiler/shared adapters:** generalize only the patterns proven by the first real workflow, then migrate more workflows.
8. **P3 — discovery and bounded repair autopilot:** enable after release/rollback/quarantine telemetry exists.

### Cut or postpone

- Public SEO “audit” as the first paid product.
- Deployed GPU mock and any A10 spend before a real model is selected.
- Per-workflow FastAPI/parser/OpenAI/error-handling forks.
- Production polling during long provider renders.
- Client-supplied prompts, prices, resource limits, raw provider IDs, or Modal call IDs.
- A universal two-second CPU scale-down window and any `min_containers=1` rollout across 15 apps.
- Fully autonomous post/repository-to-live publication before the spec validator/compiler and manual adapter approval exist.
- A scheduled global reduction to 1.25x markup; make margin workflow- and telemetry-specific.

## File-level recommendation map

| File | Recommendation |
|---|---|
| [`site/deploy/worker.js`](../../site/deploy/worker.js) | Replace generic client-authoritative runner with authenticated `/api/runs`; authorize `/api/me`; server-resolve checkout price; normalize errors; call private Modal; add signed provider webhook |
| [`site/deploy/schema.sql`](../../site/deploy/schema.sql) | Add durable runs, idempotency/ownership/release state, run events, credit ledger, promo balances, provider IDs, artifact metadata, and state indexes |
| [`site/deploy/balance.mjs`](../../site/deploy/balance.mjs) | Remove FNV API-key generation; use random revocable credentials and ledger-backed money transitions |
| [`site/deploy/cost-model.mjs`](../../site/deploy/cost-model.mjs) | Reject unknown models/cost codes; version tables; include variable input, retries/failures, measured Modal resources/storage; use p95/release pricing and upward rounding |
| [`site/deploy/test-cost.mjs`](../../site/deploy/test-cost.mjs) | Rename stale “25% markup” assertion and test the `$0.60` HeyGen launch price explicitly |
| [`scripts/go-live.sh`](../../scripts/go-live.sh) | Upload `STRIPE_WEBHOOK_SECRET` and Modal Proxy Token secrets; add production-key mode intentionally; deploy/smoke Modal releases or invoke a separate release script; verify top-up settlement, auth, and a private Modal call |
| [`site/deploy/wrangler.toml`](../../site/deploy/wrangler.toml) | Bind rate-limit/anti-abuse state for production, document Omo domains, add only non-secret registry/config bindings |
| All three `modal_app.py` | Fix JSON body declarations; add ASGI tests; share runtime; explicit provider timeout/retry; full response schemas and stable errors |
| [`containers/ugc-heygen`](../../containers/ugc-heygen) | Implement production adapter/webhook contract/R2/usage; require video in completed schema; update price and buyer-safe choices |
| [`containers/gpt-image-seedance-ad`](../../containers/gpt-image-seedance-ad) | Keep offline until real pixels; remove unnecessary GPU secret; choose model/license/weights; measure actual GPU seconds |
| New `container-spec.schema.json` + compiler | Canonicalize provider names, resources, bindings, costs, secrets, egress policy, hashes, and release gates; reject unresolved paid steps |

## Production gates for the first paid run

Do not mark HeyGen UGC live until all are true:

- An unauthenticated request is rejected before D1 or Modal work.
- A caller cannot choose another user, prompt, price, provider ID, token limit, or release.
- A real JSON request passes Worker and Modal transport validation.
- Same idempotency key/body creates one Omo run and one paid provider job; changed body returns `409`.
- Reservation, completion settlement, and failure refund are replay-safe and auditable.
- Provider callback signature/timestamp/event ID are verified and deduplicated.
- Result lookup is owner-authorized and survives beyond Modal's seven-day Function output retention.
- MP4 is copied to R2, decodes, has audio, is 9:16, and is near 15 seconds.
- Speech matches the approved grounded script; unsupported claims fail publication.
- Actual COGS, retries, latency, provider request ID, release hash, and cost-table version are recorded.
- The price shown, reserved, charged, and returned is identical and server-authored.
- Spend, failure-rate, duplicate-job, provider-429, and p95-latency alerts exist; a kill switch can quarantine the release.

## Current external facts used in this audit

- Modal [cold-start guidance](https://modal.com/docs/guide/cold-start) documents 2 seconds to 20 minutes for `scaledown_window`, a 60-second default, and seconds-to-minutes warm-up depending on initialization.
- Modal [pricing](https://modal.com/pricing) currently lists `$0.0000131/core-second`, `$0.00000222/GiB-second`, and A10 at `$0.000306/second`; region/non-preemptible multipliers may add cost.
- Modal [security/data retention](https://modal.com/docs/guide/security) states Function inputs and outputs are retained for up to seven days.
- Modal [Proxy Tokens](https://modal.com/docs/guide/webhook-proxy-auth) protect Web Functions that are otherwise public.
- Cloudflare D1 [`batch()` documentation](https://developers.cloudflare.com/d1/worker-api/d1-database/) describes sequential transactional execution and rollback on statement failure.

Provider interfaces and prices remain time-sensitive. Reconcile the selected HeyGen account, Modal plan/region, and LLM provider immediately before the production release; the repository's static estimates are not invoices.
