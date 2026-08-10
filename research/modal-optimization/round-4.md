# Modal hosting optimization — Round 4: definitive execution architecture

**Date:** 2026-08-10  
**Status:** final consolidation; this document supersedes Rounds 1–3 and the deployment topology in [`modal-container-plan.md`](../modal-container-plan.md).  
**Business constraint:** preserve a real `$0.10` entry-price workflow while building an execution system that can support `$100k MRR` and 15+ logical workflows without multiplying public endpoints, secrets, warm containers, or billing authorities.

## Executive decision

Build **one Cloudflare control plane and a small number of private execution pools**:

```text
buyer / API client
  │ Clerk JWT or random Omo API key + Idempotency-Key
  ▼
Cloudflare gateway Worker
  authenticate tenant → resolve immutable release → validate → quote
  atomically create run + reserve credits + write dispatch outbox
  │
  ├── bounded wait for fast work: 200 if done within 8s
  └── otherwise: 202 with durable Omo run_id
  ▼
Cloudflare Workflow — durable orchestrator
  ├── hosted LLM and remote provider adapters directly
  ├── wait for signed provider events without a sleeping container
  ├── stream artifacts into private R2
  └── invoke Modal only for container-native compute
          ├── shared CPU media validation/transcode
          ├── one pool per resident GPU model/dependency shape
          └── single-use restricted sandbox for untrusted code
  ▼
D1 runs/events/ledger + R2 artifacts
  settle or release reservation → owner-authorized GET /api/v1/runs/{run_id}
```

The final division of responsibility is:

- **Cloudflare Worker:** public API, authentication, authorization, checkout, quotes, rate limits, and non-enumerating reads.
- **Cloudflare Workflows:** durable step orchestration, retry ownership, provider waits, reconciliation, and settlement coordination.
- **D1:** business system of record for tenants, immutable releases, quotes, runs, events, reservations, and the append-only credit ledger.
- **R2:** private durable artifact system of record. Provider URLs are temporary inputs, never final marketplace outputs.
- **Modal:** private elastic compute plane. It does not own buyer identity, balances, prices, durable run state, remote-provider waits, or release promotion.
- **Autopilot:** immutable release controller operating within preapproved capabilities. It is not an agent with arbitrary code-generation or production-deployment authority.

This explicitly overturns the original “Modal App per workflow” design. Hosted DeepSeek/OpenAI-compatible calls and HeyGen are remote HTTP operations and run from Cloudflare Workflows. Modal is used only when a native binary, local CPU/GPU model, media workload, or isolated sandbox provides material value.

## 1. Final architecture

### 1.1 System invariants

These are release-blocking invariants, not aspirations:

1. Identity comes only from a verified Clerk token or a random, revocable Omo API key. Request `user_id` is never authoritative.
2. The server selects release, prompt, model, provider operation, price, retry policy, resource ceiling, and artifact destination.
3. One `(tenant_id, workflow_slug, idempotency_key)` binds one canonical request hash to one Omo run. The same key with a different body returns `409`.
4. Delivery is at least once; effects are idempotent. Do not claim distributed “exactly once.” Provider jobs, callbacks, ledger effects, workflow instances, and artifact writes each have unique IDs and reconciliation paths.
5. Credits are reserved before external spend. Settlement or release is a compare-and-set transition backed by one unique ledger effect.
6. Every read or mutation includes `tenant_id`; a foreign run or artifact returns `404`, not a distinguishable `403`.
7. A successful media run requires an Omo-owned, checksummed, validated R2 artifact. A provider URL or `video: null` is not success.
8. Modal receives a bounded one-run capability, not tenant credentials, price, balance, arbitrary URLs, provider IDs, or a general R2 key.
9. Unknown adapters, cost units, models, fields, egress hosts, secrets, or binding expressions fail closed at compilation.
10. Only the versioned traffic-allocation pointer makes a release live. A build, Modal deployment, or QA exit code cannot do so.

### 1.2 Durable request and billing path

The exact paid-run flow is:

1. `authenticateRequest()` derives `tenantId` from Clerk or a stored API-key hash.
2. `resolveLiveRelease(workflowSlug, tenantId)` returns one immutable release and traffic allocation.
3. Validate and canonicalize `input`; compute `requestHash`.
4. `resolveQuote()` returns an immutable, expiring quote containing release and cost-policy versions.
5. In one D1 transactional batch, `createOrReplayRun()` inserts the run, reserves purchased/promotional credits according to policy, appends ledger/run events, and inserts a `dispatch_outbox` record.
6. An outbox dispatcher starts a Cloudflare Workflow instance keyed by `run_id`. Replaying the outbox is harmless; a sweeper repairs a crash between D1 commit and Workflow start.
7. The Workflow performs bounded adapter steps. It uses `run_id` as the provider idempotency/effect namespace and records a provider acknowledgement immediately.
8. Async providers call a dedicated webhook receiver. The receiver verifies the raw-body signature, timestamp, and event ID; matches the stored provider job; persists the event; then signals the waiting Workflow.
9. The Workflow re-reads provider status server-side, streams the artifact to an exact R2 object, records checksum/bytes/media metadata, and performs deterministic validation.
10. `settleRun()` or `releaseReservation()` writes one replay-safe ledger effect and terminal run event. A scheduled `reconcileStaleRuns()` scans stuck outbox, provider, artifact, and settlement states.

Separate run state from money state:

```text
run: queued → running → awaiting_provider → artifact_copying → validating
       └──────────────────────────────────────────────────────→ succeeded
       └──────────────────────────────────────────────────────→ failed | cancelled | expired

reservation: reserved → settled | released
```

State changes use compare-and-set updates with a `state_version`. Provider calls cannot occur unless the run is reserved. `succeeded` means the typed output and any required owned artifact have passed validation; settlement follows in the same orchestration phase and is independently replayable.

### 1.3 Final public contract: durable async core, bounded sync convenience

There is one API model for every paid workflow:

```http
POST /api/v1/runs
Authorization: Bearer <Clerk JWT or Omo API key>
Idempotency-Key: <client-generated key>
Prefer: wait=8
Content-Type: application/json

{
  "workflow_slug": "ugc-script-studio",
  "input": {"product_description": "...", "brand_voice": "raw", "length_seconds": 30}
}
```

- Authentication, release selection, validation, durable creation, and reservation always finish before execution.
- A fast LLM workflow may return `200` with the completed run if it finishes within eight seconds.
- Otherwise the same request returns `202` with `run_id`, `status`, `price_cents`, `release_hash`, and `status_url`.
- Remote async-provider and GPU/media workflows always return `202`; `Prefer` does not turn them synchronous.
- `GET /api/v1/runs/{run_id}` is owner-authorized and durable. It never accepts or exposes a Modal call ID or provider job ID.
- Immediate request defects are stable `4xx` errors. Execution failures are durable terminal run resources with stable redacted `error.code` values.
- The quote shown, reserved, charged, and returned is identical. A later catalog price change never changes an accepted run.

This contract removes Modal cold starts and provider latency from the public submission SLO without imposing a two-request flow on warm, cheap LLM clients.

### 1.4 Deployment topology for 15+ workflows

Fifteen storefront workflows are fifteen immutable registry releases, not fifteen applications:

| Execution/trust class | Deployment count | Initial scaling | Work placed here |
|---|---:|---|---|
| Hosted LLM / remote HTTP provider | `0` Modal Apps | Cloudflare admission and provider semaphore | Script, caption, HeyGen, and other edge-safe API steps |
| Reviewed CPU media utility | `1` shared Modal App if edge limits require it | `min_containers=0`, `scaledown_window=60` | `ffprobe`, decode, transcode, ASR/media checks |
| Resident GPU model | `1` Modal pool per model plus incompatible VRAM/dependency shape | `min_containers=0`, `scaledown_window=2` initially | Real local inference only |
| Untrusted code | `1` separate Restricted Function/Sandbox class | single-use, zero warm, strict timeout | Minimal submitted/repository code with no production secrets |

A normal prompt/schema/listing addition uses the **spec-only lane** and deploys no code. A new provider operation, binary, model, package, GPU, secret, egress host, callback, data class, or resource ceiling is a new-capability release with human review.

At the current target, `$100,000 / $0.10 = 1,000,000` cheap runs/month: about 33,333/day and `0.386` runs/second on average. Capacity must handle bursts and provider quotas, but this volume does not justify 15 separate warm pools. Admission control applies in this order: tenant concurrency/spend, release limit, provider semaphore, GPU-class queue, environment budget, then workspace budget.

### 1.5 Cold-start policy

Cold starts are handled by class, not by a universal setting:

- **Public submission:** never waits on Modal. Measure gateway p50/p95 separately.
- **Hosted API workflows:** no Modal cold start.
- **Shared CPU media App:** start at `min_containers=0`, `scaledown_window=60`. At the checked base rates, a 0.25-core/0.5-GiB container costs about `$0.000004385/s`, `$0.000263` per idle minute, or `$11.37/month` continuously warm. Set `min_containers=1` only when measured conversion/SLO loss is worth more than `$11.37/month`.
- **GPU pools:** start at `min_containers=0`, `scaledown_window=2`. Raise the window only from observed interarrival and cold/model-load traces. Do not use `buffer_containers` without measured correlated bursts.
- **Untrusted execution:** single-use containers, no warm pool.

Record `queue_ms`, `container_boot_ms`, `model_init_ms`, `execution_ms`, `provider_wait_ms`, `artifact_ms`, and `warm_idle_allocated_ms` separately. Bake small stable assets into the image; pin large weights by digest in a reproducible storage path; evaluate memory snapshots only after the real model has repeatable cold/warm benchmarks.

For perspective, an illustrative A10 + 2 physical cores + 16 GiB costs about `$0.00036772/s`, or about `$953/month` continuously warm. Fifteen such warm pools would cost roughly `$14,297/month` before region or non-preemptible premiums. That architecture is rejected.

### 1.6 Secrets and isolation

| Secret/capability | Owning plane | Explicitly excluded from |
|---|---|---|
| Clerk verification material, API-key pepper/hashes | Gateway Worker | browser, Modal, specs, logs |
| Stripe secret and webhook key | Billing routes/service | orchestrator, Modal, catalog |
| Provider webhook verification key | Callback receiver | browser, general Modal runtime |
| Hosted LLM and HeyGen keys | Private Cloudflare Workflow service | gateway responses and Modal when Modal does not call that provider |
| Modal production Proxy Token | Private orchestrator secret | browser, D1 plaintext, listing, logs |
| Modal CI service-user token | CI secret manager; separate staging/prod principals | runtime images, agents, specs |
| GPU model-download token | Exact build/init Function only | CPU utility, unrelated models |
| R2 object access | Exact-object, method-limited, expiring URLs | permanent Modal env, buyer input, catalog |
| Base URL, API version, model, region, timeouts | Hashed release configuration | mutable secret override |

Generate Omo API keys with high entropy, show them once, store only hash/prefix/metadata, and support revoke/rotate/last-used. Delete deterministic `apiKeyFor()` behavior. Separate `dev`, `staging`, and `production` Cloudflare/Modal environments and principals.

When Cloudflare invokes Modal, it sends a short-lived signed capability containing only:

```text
run_id, opaque tenant_partition, release_hash, request_hash,
exact input key/digest, exact output key, allowed operation,
max variants, max wall/GPU seconds, not-before, expiry, nonce
```

The Modal Function verifies the signature and release limits. Shared concurrent containers keep all run state in request-local objects and non-guessable temp directories; immutable model caches may be global, tenant inputs/results/credentials may not. Untrusted code runs with Modal-resource access disabled, network blocked by default, no production secrets, and a single-use container.

Do not support buyer-provided provider keys in v1. Per-user Modal Apps/Secrets are an operational and isolation trap.

## 2. Exact build and shipping order

### 2.1 Build sequence

Execute these in order; later work does not begin until the preceding acceptance gate passes.

1. **Close the unsafe path.** Disable the paid behavior of `/api/run`; it must not accept client `user_id`, `system_prompt`, `max_tokens`, model, release, or price. Keep only separately capped anonymous demos while the final API is built. Restrict CORS and stop lazy `$10` account creation from arbitrary identities.
2. **Install migration-backed authority.** Add tenants/API keys, immutable releases/traffic allocations, quotes, runs/events, dispatch outbox, reservations/ledger effects, provider jobs/events, artifacts, and reconciliation indexes. Purchased and promotional balances are separate.
3. **Build authentication, registry, quote, and repositories.** All repository functions require `tenantId`; all transitions are CAS plus append-only events; unknown cost/capability entries fail closed.
4. **Build the final run contract and durable Workflow.** Add `POST/GET /api/v1/runs`, bounded `Prefer: wait=8`, outbox dispatch, Workflow retries, stable errors, kill switches, and stale-run reconciliation.
5. **Prove failure safety before charging.** Run real HTTP tests, 100-way same-key replay, same-key/different-body conflict, cross-tenant matrices, crash injection at every effect boundary, webhook replay/reorder, quote immutability, and ledger reconciliation.
6. **Ship #1: UGC Script Studio.** One bounded DeepSeek-compatible LLM call, strict typed output, actual tokens, no Modal, `$0.10` exact price. This is the first paid production workflow.
7. **Build the minimal release controller.** Canonical spec/provenance/capability schemas, deterministic compiler, state machine, signed QA report, manual canary approval, and atomic rollback. Use Shipment #1 as its first curated release; it may not autonomously promote.
8. **Build and stage the async-provider path.** Implement one HeyGen create operation, durable acknowledgement/event wait, webhook verification, stale-job reconciliation, R2 copy, media/claim QA, invoice reconciliation, and purchased-credit-only policy.
9. **Ship #2: HeyGen 15-second invite beta.** One 9:16 output, curated marketplace avatar/voice enums resolved server-side, `$0.70` provisional price, one expensive run per tenant, explicit beta run/dollar caps, and human review of the first 20 paid artifacts.
10. **Benchmark a real GPU product offline.** Select commercially usable pinned weights, generate real pixels, measure cold/warm load, batch/variant strategy, GPU/CPU/RAM seconds, accepted-output yield, OOM/preemption, R2 upload, fidelity, and safety. The current mock does not count.
11. **Ship #3: real GPU product-image workflow.** Deploy one model-specific private Modal class only if the benchmark passes product quality and cost gates. Price it from the measured guarded accepted-output cost; never reuse the current `$1.10` canary estimate.
12. **Expand via spec-only releases.** Add workflow #4 onward through approved adapters and shared execution classes. Enable automated canary/live promotion only after the maturity gates in §4.5.

### 2.2 The three shipments

| Order | Product | Public behavior | Launch price | Why this position |
|---:|---|---|---:|---|
| **1** | UGC Script Studio | Strict JSON script; `200` within 8s or durable `202` | **`$0.10`** | Cheapest truthful buyer value; proves final auth, quote, ledger, run, and telemetry path without media risk |
| **2** | HeyGen 15s beta | Async 9:16 MP4, approved avatar/voice, owned R2 artifact | **`$0.70` provisional** | Adds paid async mutation, callback, media, reconciliation, and refund risk after the substrate works |
| **3** | Real product-image GPU workflow | Async owned images from a pinned licensed local model | Formula after benchmark | Adds Modal/model/cold-start risk only after the first two classes are operational |

The checked-in Claude SEO container remains a **private transport/contract fixture**, not a public “site audit” or agency replacement. The current GPU hash-to-fake-URL implementation is never deployed.

## 3. Final cost model

### 3.1 One economic definition

Use integer cents for buyer money and integer nano-USD for COGS. A micro-dollar is too coarse for cheap token accounting.

Every immutable release carries three costs:

1. `C_static`: conservative input/duration/resource bound before launch.
2. `C_success_p95`: recent p95 cost of successful attempts.
3. `C_delivered`: all variable cohort cost divided by completed, retained, chargeable outcomes. It includes provider/Modal/Cloudflare/R2, paid failures, retries, duplicates, refunds, payment-fee allocation, promo/fraud loss, and variable support.

```text
C_guard = max(
  C_static,
  C_success_p95,
  max(C_delivered_7d, C_delivered_30d) × (1 + tail_reserve)
)

price_cents = max(
  10,
  ceil(100 × C_guard_usd / (1 - target_margin))
)
```

Default `target_margin_bps = 8000` (80%), equivalent to 5× only when cost is complete. Use a 10% tail reserve for mature LLM releases, 15% for remote media, and 20% for GPU until 30 clean days. Round upward to the next cent. There is **no future global 1.25× switch**; 1.25× is only 20% margin before omitted costs.

Each accepted quote stores:

```text
quote_id, release_hash, price_cents, reserve_cents,
estimated_cost_nanos, max_cost_nanos, cost_version,
target_margin_bps, expires_at
```

Quote TTL is 10 minutes. Runtime retries share the same hard `max_cost_nanos`; they do not receive a new budget. Exceeding the hard ceiling stops further spend and reconciles the current run. Cost-table expiry, invoice variance, or falling accepted-output yield automatically pauses the release.

### 3.2 Final launch numbers

| Workflow | Cost basis | Guarded COGS | Buyer price | Margin on guard | Hard rule |
|---|---:|---:|---:|---:|---|
| UGC Script Studio | Up to ~900 input + 800 output tokens at checked DeepSeek rates: `$0.000462`; edge/storage adds fractions | **`$0.001`** | **`$0.10`** | **99.0%** before fixed overhead | `max_cost=$0.002`; pause rather than silently switch model |
| HeyGen 15s beta | Repository nominal `$0.12045`; × 1.15 media tail = `$0.13852` | **`$0.14`** | **`$0.70`** | **80.0%** | No second charged render if it would breach `$0.14`; reprice/pause from invoice data |
| GPU image, illustrative A10 2-core/16-GiB | Metered at `$0.00036772/s` before other cost | Not known until accepted-output benchmark | `ceil(max($0.10, C_guard/0.20) × 100)/100` | 80% target | No public release or price from mock/fake outputs |

The HeyGen decision resolves prior-round inconsistency: `$0.15` is economically unsafe; `$0.60` rounds below the exact guarded 80%-margin result. `$0.70` is the provisional beta quote derived from a `$0.14` guard. If invoice-backed delivered cost becomes `$0.22`, the exact 80%-margin price becomes `$1.10` or the release pauses.

The GPU base-compute lower bounds are:

| A10 + 2 cores + 16 GiB billed time | Base compute COGS | Minimum 80%-target price after upward cent rounding |
|---:|---:|---:|
| 30s | `$0.01103` | `$0.10` floor |
| 60s | `$0.02206` | `$0.12` |
| 120s | `$0.04413` | `$0.23` |
| 180s | `$0.06619` | `$0.34` |
| 300s | `$0.11032` | `$0.56` |

These are not approved prices: add model load, warm idle, storage, LLM/provider calls, failed/rejected outputs, and region/non-preemptible premiums, then divide by accepted deliverables. The current `$0.22020`/`$1.10` image estimate is deleted because it simultaneously charges three remote `openai_image` calls and two generic local GPU buckets while producing no pixels.

### 3.3 `$100k MRR` operating scenarios

| Revenue mix | Monthly paid runs | Guarded variable COGS | Contribution before fixed payroll/overhead |
|---|---:|---:|---:|
| All `$0.10` Script Studio | `1,000,000` | at most `$1,000` at the `$0.001` guard | about `$99,000` |
| All `$0.70` HeyGen beta | about `142,857` | `$20,000` at the `$0.14` guard | `$80,000` |
| Mixed catalog | Depends on actual per-release run counts and prices | Sum of release guarded/delivered COGS | Enforce ≥80% by release, not only on the blended total |

At one million runs and an illustrative five Workflow steps/run, 5 million steps are generated. Using the Round 2 checked allowance of 500,000 and `$0.80` per additional 100,000 steps, incremental Workflow step cost is about `$36/month`; provider/model cost and failure control dominate. Revalidate the account rate before launch.

Never charge Stripe for each `$0.10` run. Use prepaid credit packs so payment fees are amortized. Promotional credit may fund only cheap, bounded LLM demos at launch. A `$10` promo can fund 100 Script Studio runs with at most `$0.10` guarded model spend; the same grant could fund 14 HeyGen runs and expose `$1.96` guarded spend per fake signup. HeyGen and GPU therefore require purchased credits or a payment-backed verified account.

Modal Starter is sufficient until a real GPU workload exists. Upgrade to the checked `$250 + compute/month` Team plan before paid GPU GA if its budgets, logs, rollback, and concurrency headroom are still required; `$250` is 0.25% of `$100k MRR`.

## 4. Autopilot specification

### 4.1 Autopilot is an immutable release system

Persist separate entities rather than one mutable workflow record:

| Entity | Immutable identity | Purpose |
|---|---|---|
| `source_snapshots` | `source_hash` | Authorized raw evidence, author, retrieval metadata, rights and asset hashes |
| `candidate_revisions` | `candidate_hash` | Extracted canonical spec, provenance, unresolved facts, policy version |
| `capability_manifests` | `capability_hash` | Adapters, packages, image, GPU, secrets, egress, data/retention, cost ceiling |
| `builds` | `build_hash` | Reproducible compiler output, lock, SBOM, scan, image digest |
| `qa_reports` | `qa_report_hash` | Suite/fixture hashes, redacted evidence, actual spend, results, approvals |
| `releases` | `release_hash` | Exact source/spec/prompt/schema/capability/compiler/runtime/build/cost combination |
| `traffic_allocations` | monotonic version | Only mutable buyer-routing pointer; canary, live, rollback |

`release_hash` covers source, canonical spec, prompts, contracts, capability manifest, compiler/runtime versions, resolved dependency lock, base-image and model/weight digests, adapter versions, and cost-policy version. A changed prompt, dependency, model alias, secret binding, limit, or price creates a new release hash.

### 4.2 Two deterministic lanes

- **Spec-only lane:** only previously approved adapter operations, dependencies, image, egress, secret capabilities, data class, retention, artifact types, and resource ceilings. Compilation publishes registry data into an existing execution class; it generates no Python and deploys no Modal App.
- **New-capability lane:** any new or expanded operation, package, native binary, image, model/weight, GPU, secret, egress host, callback, data class, retention, artifact type, or dollar/resource ceiling. It requires human security, license, code, cost, and rollback review plus a new runtime release.

`diffCapabilities()` chooses the lane. The extracting/spec agent cannot classify itself. Unknowns are expansions and fail closed.

### 4.3 Release lifecycle and authorities

```text
DISCOVERED → RIGHTS_PENDING → EVIDENCE_FROZEN → SPEC_DRAFT
→ STATIC_VALIDATED → CAPABILITY_CLASSIFIED
→ [CAPABILITY_REVIEW if expanded] → POLICY_APPROVED
→ COMPILED → [BUILD_VERIFIED if code/image changed]
→ STAGING_DEPLOYED → QA_RUNNING → QA_PASSED
→ PROMOTION_PENDING → CANARY → LIVE

CANARY/LIVE → PAUSED | QUARANTINED → ROLLED_BACK | RETIRED
```

- **H0 rights/product:** human approval for commercial rights, consent, and honest listing claims.
- **H1 capability/security:** human approval for every new/expanded capability. Never automated.
- **H2 paid QA:** human authorizes exact staging spend until billing maturity.
- **H3 canary:** human inspects exact release, QA, price/COGS, rollback target, and kill switch.
- **H4 live:** human initially reviews canary quality, cost, reconciliation, refunds, and incident window.
- **H5 resume:** human resumes security/correctness quarantine; a code/config fix is a new release.

Every transition is CAS plus an append-only event with actor, role, policy/hashes, evidence, spend, reason, and idempotency key. Automatic safe actions may stop spend, pause, quarantine, or roll traffic back. Automation may never expand authority or silently resume a correctness failure.

### 4.4 QA and bounded repair

Mandatory release suites are: provenance/rights, canonical schema/DAG/bindings, capability policy, reproducible build/SBOM/license, offline contract, real HTTP, tenant/security, 100-way idempotency and ledger, crash boundaries, provider callback/retry, artifact ownership/media validation, deterministic product quality, cost/invoice, load/cold start, and rollback/kill switch.

An LLM evaluator is supplemental. It cannot waive a contract, security, money, artifact, rights, or deterministic claim failure.

Autonomous repair may change only prompt wording, deterministic normalization, bindings, and parameters already inside the approved capability envelope. It may not loosen schemas/tests/quality, change rights/provider/model/package/image/GPU/secret/egress/data/retention, raise price/retry/time/container/dollar limits, or suppress a failing test.

Allow at most three candidate revisions per family and at most the smaller of `$1` or the release-specific QA budget. A paid media fixture runs once per exact `(release_hash, suite_version, fixture_set_hash)`. Exceeding the bound sends the candidate to human review.

### 4.5 Canary and autonomy gates

Initial canaries use 1–5% traffic, at most 20 paid runs, an explicit dollar ceiling, one expensive run per tenant, and an expiry that returns traffic to zero if not approved. One confirmed tenant leak, duplicate paid mutation, ledger mismatch, secret exposure, corrupt/unowned artifact, unsupported material claim, or hard cost breach immediately quarantines and rolls back.

Do not allow autonomous live graduation until all are true:

1. One manually operated pure-LLM release, one remote async-provider release, and one real Modal GPU release are live.
2. Each has 30 days of cost/failure/quality telemetry.
3. Rollback and quarantine drills have succeeded.
4. Billing/provider invoices reconcile with no unresolved items.
5. Only spec-only releases inside a previously approved capability envelope are eligible.

New capabilities always retain H1 and H3 human gates.

## 5. Concrete file-level execution map

### Cloudflare control plane

- [`site/deploy/worker.js`](../../site/deploy/worker.js): remove paid `handleGenericRun`; replace public routing with `handleCreateRun`, `handleGetRun`, authenticated `handleMe`, server-priced checkout/top-up, dedicated verified callbacks, restrictive CORS, stable redacted errors, and no raw provider output. Keep anonymous demos isolated and capped.
- **New `site/deploy/auth.mjs`:** `authenticateRequest`, `hashApiKey`, `issueApiKey`, `rotateApiKey`, `authorizeTenantResource`.
- **New `site/deploy/run-repository.mjs`:** `createOrReplayRun`, `authorizeRun`, `transitionRun`, `recordProviderJob`, `recordProviderEvent`, `recordArtifact`, `reconcileStaleRuns`.
- **New `site/deploy/ledger.mjs`:** `reserveCredits`, `settleRun`, `releaseReservation`, `applyTopup`, `reconcileBalance`. These replace the separate crash-prone `reserveRunCredits`, `refundRunCredits`, and `addRun` effects in `worker.js`.
- **New `site/deploy/release-registry.mjs`:** `resolveLiveRelease`, `resolveQuote`, `assertCapability`, `setTrafficAllocation`, `pauseRelease`, `quarantineRelease`.
- **New `site/deploy/run-workflow.mjs`:** Cloudflare Workflow entry with outbox dispatch, bounded step retries/cost, provider event wait, artifact processing, settlement, and reconciliation.
- **New `site/deploy/adapters/llm.mjs`:** strict model allowlist, explicit connect/read/total deadlines, no SDK retries outside Workflow ownership, actual token/request telemetry, strict envelope validation.
- **New `site/deploy/adapters/heygen.mjs`:** curated ID resolution, one physical create operation, run-derived idempotency, signed event normalization, server-side status re-read, no buyer-visible provider body/ID.
- [`site/deploy/schema.sql`](../../site/deploy/schema.sql): retain only as an optional local bootstrap. Production uses numbered files under **new `site/deploy/migrations/`** for identity/API keys, releases/traffic, runs/outbox/events, quotes/reservations/ledger, providers/artifacts, and QA/reconciliation. Add unique tenant idempotency, workflow instance, provider job/event, and ledger effect constraints.
- [`site/deploy/balance.mjs`](../../site/deploy/balance.mjs): delete FNV/deterministic `apiKeyFor`; keep only pure display/math helpers that do not mutate balances. Ledger code owns money.
- [`site/deploy/cost-model.mjs`](../../site/deploy/cost-model.mjs): replace `MARKUP`, fallback rates, and `modal_gpu_30s` with `quoteRelease`, `modalComputeCost`, `deliveredSaleCost`, `ceilPriceCents`, versioned rates, nano-USD output, quote TTL, and hard ceilings. Unknown model/provider/unit/currency is an error.
- [`site/deploy/wrangler.toml`](../../site/deploy/wrangler.toml): bind D1, R2, Workflow, outbox/reconciliation schedule, and production rate-limit state; store no secrets in the file.
- [`site/deploy/test-router.mjs`](../../site/deploy/test-router.mjs) plus focused new suites: exercise real HTTP/auth/CORS, replay, tenant isolation, crash injection, callback replay/order, artifact authorization, quote immutability, ledger reconciliation, and rollback.
- [`scripts/go-live.sh`](../../scripts/go-live.sh): stop rotating a key-derivation secret, stop treating `CREATE IF NOT EXISTS` as migration, provision/check all bindings and webhook secrets, deploy staging first, smoke the exact artifact, and promote the registry pointer only after gates. Add **new `scripts/promote-release.sh`** and **`scripts/rollback-release.sh`**.

### Autopilot control plane

- **New `autopilot/schemas/container-spec.v1.json`:** canonical contracts, DAG/bindings, adapter operations, resources, secret capabilities, egress, retention, artifacts, and cost policy.
- **New `autopilot/schemas/provenance.v1.json`** and **`capability-manifest.v1.json`:** field-level evidence/confidence and deterministic privilege representation.
- **New `autopilot/state-machine.mjs`:** `transitionCandidate`, `transitionRelease`, legal roles/evidence/CAS matrix.
- **New `autopilot/policy.mjs`:** `validateSpec`, `diffCapabilities`, `classifyLane`, `assertRepairAllowed`, `assertSpendBudget`; fail closed.
- **New `autopilot/compiler/compile.mjs`:** pure deterministic compilation with no network, secrets, source execution, shell, arbitrary JavaScript/Python/Jinja, or executable binding expressions.
- **New `autopilot/qa/`:** contract, security, tenancy, billing, provider, artifact, quality, load, cost, and rollback suites plus immutable report signing.
- **New `autopilot/release-controller.mjs`:** staging deployment, QA trigger, approval records, expiring canary, pause/quarantine/rollback. It can mutate traffic only within recorded authority and never sees provider secret values.

### Modal execution plane

- Do not expand the three workflow-specific `modal_app.py` files into production forks. Fix `body: Any`/real ASGI tests only while they remain fixtures; the target architecture removes their public per-workflow ingress.
- **New `containers/modal-media/modal_app.py`:** private shared `validate_media`/transcode capability with no buyer/provider/billing secrets, exact signed R2 objects, run-local temp paths, and actual resource telemetry.
- **Future `containers/modal-imagegen/modal_app.py`:** one pinned licensed real model class with verified release/model digests, no fake URLs, exact-object output, accepted-image benchmark, and scale-to-zero.
- **New `containers/modal-untrusted/`:** Restricted Function/Sandbox, single-use, no Modal-resource access, blocked/allowlisted network, no production secrets, strict timeout, minimal copied source.
- [`containers/gpt-image-seedance-ad/modal_app.py`](../../containers/gpt-image-seedance-ad/modal_app.py): never deploy `_mock_images_inside_container` or `generate_images_gpu` as paid code.
- [`containers/ugc-heygen/`](../../containers/ugc-heygen): retain as contract/provenance fixtures; move provider orchestration to Cloudflare, remove raw buyer avatar/voice IDs, require an owned validated artifact for success, and delete stale `$0.15` and unused broad secret capability.
- [`containers/claude-seo-skill/`](../../containers/claude-seo-skill): private fixture only; a hosted LLM call does not justify a dedicated Modal App.

## 6. Top 10 risks and mitigations

| Rank | Risk | Mitigation and tripwire |
|---:|---|---|
| 1 | **Client authority or cross-tenant access** | Auth-derived tenant, server registry, mandatory tenant predicates, foreign `404`, random hashed keys, adversarial tenant matrix; one confirmed leak quarantines all affected releases |
| 2 | **Duplicate paid provider mutation** | Tenant-scoped idempotency, run-derived provider key, unique job/event/effect IDs, immediate acknowledgement persistence, outbox and stale-run reconciliation; duplicate job auto-pauses provider adapter |
| 3 | **Double charge/refund or balance drift** | Atomic create/reserve/outbox batch, append-only ledger, CAS effects, cached-balance reconciliation, crash injection at every boundary; any mismatch blocks promotion and settlement automation |
| 4 | **Missing, forged, delayed, or reordered webhook** | Raw-body signature/timestamp verification, event dedupe, job-to-run match, server status re-read, durable event wait, periodic polling reconciliation; callback never chooses tenant or artifact key |
| 5 | **Cost drift, retry explosion, or false 5× confidence** | Complete guarded cost, upward rounding, hard run/canary/provider/environment limits, invoice reconciliation, accepted-output yield, cost-version expiry; breach pauses spend before retry |
| 6 | **Promo-credit/Sybil fraud and key resale** | Promo/purchased buckets, verified identity, rate/device/payment controls, cheap-LLM-only promo, purchased credits for media/GPU, provider/global circuit breakers |
| 7 | **Source prompt injection or supply-chain execution** | Evidence-only ingestion, immutable source hash, no secrets/deploy token, constrained schemas, deterministic compiler, resolved locks/SBOM/license scans, isolated build; unknown capability fails closed |
| 8 | **Rights, avatar/voice consent, or unsupported claims** | Human H0, curated consented assets, provenance/claim grounding, deterministic material-claim checks, first-20 media human review; rights/claim failure quarantines rather than repairs in place |
| 9 | **Secret/egress blast radius or shared-container tenant leakage** | Owning-plane keys, capability-specific versioned secrets, immutable provider hosts, exact R2 capabilities, run-local state/temp paths, no mutable auth clients, restricted single-use untrusted execution |
| 10 | **GPU cold start, OOM, queue, or poor accepted-output yield** | No GPU in submit SLO, pool by pinned model, zero warm initially, phase/resource telemetry, offline cold/warm/load benchmark, global fair queue, accepted-output pricing, Team upgrade only before proven GA |

Release/config drift and self-grading are controlled across all ten risks by immutable hashes, deterministic gates, a separate evaluator, human capability/promotion authority, versioned traffic allocation, and automatic rollback.

## 7. What to cut entirely

Remove these from the execution plan; none is required to reach `$100k MRR`:

1. The client-authoritative paid `/api/run` contract and every accepted client `user_id`, system prompt, model, token cap, price, release, provider ID, or artifact destination.
2. One Modal App, FastAPI endpoint, API pool, and runner pool per storefront workflow.
3. Modal CPU wrappers for hosted LLM/HeyGen calls and any sleeping/polling Modal runner.
4. Buyer-visible Modal URLs, Proxy Tokens, `FunctionCall` IDs, or raw provider IDs/bodies.
5. Deterministic FNV API keys, lazy `$10` grants from arbitrary identities, and unrestricted promo use on paid media/GPU.
6. The fake A10 image generator and every quality/economic conclusion derived from its fake URLs.
7. Generic/fallback cost entries, `modal_gpu_30s`, mixed local-plus-remote image charges, nearest-cent margin rounding, and the scheduled global 1.25× markup.
8. Agent-generated arbitrary Python, Dockerfiles, packages, install hooks, shell, executable bindings, and self-approved capability expansion.
9. Autonomous approval of rights, new secrets/egress/models, paid-test escalation, initial canary, or first live promotion.
10. Public “SEO audit” or “replaces an agency” claims from a workflow that does not crawl the site.
11. Distributed “exactly once” promises. The contract is at-least-once delivery with one durable run and replay-safe effects plus reconciliation.
12. Universal `scaledown_window=2`, universal warm containers, and any capacity rule based on logical workflow count rather than measured execution-class traffic.

## Final execution standard

The milestone is not “a complicated workflow ran on Modal.” It is: **an authenticated buyer receives a durable, typed, supportable outcome whose release, price, spend, artifact, ownership, and ledger survive retries and failures.**

Ship that once with UGC Script Studio at `$0.10`; add asynchronous media risk with HeyGen at a guarded `$0.70`; add Modal GPU risk only after real accepted-output evidence. Then scale the catalog by publishing immutable specs into shared capability pools. This preserves the marketplace's hosted-execution moat while keeping the public contract stable, cheap, and operable at 15 or 150 workflows.
