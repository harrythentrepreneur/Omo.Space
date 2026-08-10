# Modal hosting optimization — Round 3: autopilot, secrets, and multi-tenancy

**Date:** 2026-08-10  
**Scope:** deep-dive on the source-to-live autopilot, quality gates, human approvals, secret boundaries, tenant/run/billing isolation for 15+ workflows, and validation of the 5× cost model against Modal's live prices.  
**Prior-round decision retained:** Cloudflare is the public, durable control plane; Modal is an elastic compute plane for work that actually benefits from a container. Launch pure-LLM UGC Script Studio first without Modal, HeyGen second as a capped asynchronous beta, and a real GPU workflow only after an offline model/quality/cost benchmark. Do not deploy the current GPU mock.

## Executive verdict

The source-to-live pipeline must not be one autonomous agent loop. It should be an append-only release system with separate trust domains, two publication lanes, immutable artifacts, deterministic gates, and explicit human authority. A prompt/spec change creates a new candidate hash; it never rewrites a failed or live release. Automatic actions may stop spend, quarantine a release, or roll traffic back. They may not expand secrets, egress, packages, models, prices, rights, or production traffic.

The safest production topology for 15+ storefront workflows is not 15 tenant-aware Modal endpoints. It is:

```text
buyer
  │ Clerk JWT or random Omo API key + Idempotency-Key
  ▼
Cloudflare gateway
  authenticate tenant → resolve immutable release → validate → quote
  create run + reserve credits atomically → return Omo run_id
  ▼
durable Cloudflare orchestration
  ├── hosted LLM/provider adapters directly
  ├── wait for signed provider events
  └── invoke one reviewed Modal execution class when container compute is needed
          ├── shared CPU media utility
          ├── one pool per resident GPU model
          └── single-use restricted Function/Sandbox for untrusted code
  ▼
private R2 artifact + D1 ownership/events/ledger → settle or release
  ▼
owner-authorized GET /api/v1/runs/{omo_run_id}
```

Modal must receive an opaque run capability, bounded inputs, exact artifact locations, and a hard compute budget—not buyer credentials, balances, prices, arbitrary provider URLs, or production deployment authority. Fifteen logical workflow releases should normally map to two to four shared execution classes, not 15 Apps or 30 API/runner pools.

The checked-in 5× formula is mathematically correct only in the narrow case where `costUsd` is complete: `price = 5C` gives an 80% gross margin before fixed overhead. The current `costUsd` is not complete. It omits real resource shape and duration, initialization, paid failures, accepted-output yield, warm idle, storage, payment fees, support, and fraud. The `$0.05/30s` Modal bucket is not a Modal price: against current base GPU-only rates it is 10.16× a T4, 5.45× an A10, 1.52× an H100, but only 0.96× a B200 and 0.85× a B300. Replace it with metered resources and price from delivered-sale cost.

## 1. Autopilot must be a release controller, not an agent with deployment rights

### 1.1 Separate records before defining states

A single `workflow.status` column will eventually create unsafe shortcuts. Persist distinct immutable entities:

| Record | Identity | Mutable fields | Purpose |
|---|---|---|---|
| `source_snapshots` | `source_hash` | none | Raw authorized evidence, retrieval metadata, author, license/rights state, asset hashes |
| `candidate_revisions` | `candidate_hash` | lifecycle state via compare-and-set only | Extracted spec, provenance map, unresolved fields, policy version |
| `capability_manifests` | `capability_hash` | none | Adapters, packages, image digest, GPU, secret names, egress, data class, retention |
| `builds` | `build_hash` | status/evidence append-only | Reproducible compiler output, SBOM, scan, image digest |
| `qa_reports` | `qa_report_hash` | none | Test inputs, suite version, evidence, spend, results, reviewer decisions |
| `releases` | `release_hash` | health/promotion event stream | Exact source/spec/compiler/runtime/build/cost-policy combination |
| `traffic_allocations` | monotonic version | current release percentages | The only object that routes buyers; supports atomic canary and rollback |

`release_hash` should cover at least source, canonical spec, prompts, schemas, capability manifest, compiler/runtime versions, base-image digest, resolved dependency lock, adapter versions, model/weight digest, and cost-policy version. Endpoint URLs and timestamps are deployment metadata, not hash inputs.

This prevents the most dangerous failure mode: a release passes QA, then a prompt, dependency, secret binding, model alias, or price changes in place while keeping the old approval.

### 1.2 Two lanes, chosen by a deterministic capability diff

**Spec-only lane:** the draft uses only already approved adapters, operations, dependency set, runtime image, egress hosts, secret capabilities, data class, resource ceiling, and artifact types. The compiler publishes data into an existing execution class. No Modal build or new endpoint is needed.

**New-capability lane:** any new or expanded provider operation, package, native binary, base image, model/weight, GPU class, secret, egress host, public callback, input data class, retention policy, artifact type, or resource/cost ceiling. It always requires human security/license/code review and a new reviewed runtime release. The spec agent cannot classify its own change as “spec-only”; `diffCapabilities(old, candidate)` does that from the canonical manifest.

The capability diff is fail-closed. An unknown field, cost code, provider operation, model alias, package, or binding expression is an expansion, not a default.

### 1.3 Safest lifecycle state machine

Use an acyclic candidate/release pipeline. A repair creates a new candidate revision linked by `supersedes_candidate_hash`; it does not move a failed artifact backward.

```text
DISCOVERED
  ├── REJECTED
  └── RIGHTS_PENDING → EVIDENCE_FROZEN
                         ↓
                      SPEC_DRAFT
                         ├── SPEC_BLOCKED
                         └── STATIC_VALIDATED
                                  ↓
                          CAPABILITY_CLASSIFIED
                           ├── CAPABILITY_REVIEW
                           └── POLICY_APPROVED
                                  ↓
                              COMPILED
                           ├── BUILD_FAILED
                           └── BUILD_VERIFIED
                                  ↓
                          STAGING_DEPLOYED
                                  ↓
                              QA_RUNNING
                           ├── QA_FAILED
                           └── QA_PASSED
                                  ↓
                         PROMOTION_PENDING
                                  ↓
                               CANARY
                           ├── PAUSED
                           ├── QUARANTINED → ROLLED_BACK | RETIRED
                           └── LIVE ───────→ PAUSED | QUARANTINED | RETIRED
```

State meanings and authorities:

| State/transition | Required evidence or invariant | Authority |
|---|---|---|
| `DISCOVERED → RIGHTS_PENDING` | Source URL/type/author/retrieval time and immutable raw hash | Ingestion service |
| `RIGHTS_PENDING → EVIDENCE_FROZEN` | Commercial reuse/derivation rights, consent, and platform-access basis resolved | Human rights/product gate |
| `EVIDENCE_FROZEN → SPEC_DRAFT` | `container_spec`, field-level provenance, confidence, and unresolved list | Constrained extractor; no deploy/provider secrets |
| `SPEC_DRAFT → STATIC_VALIDATED` | Canonical schema, DAG, binding, limit, claim, cost, and secret-literal checks all pass; unresolved required fields = 0 | Deterministic validator |
| `STATIC_VALIDATED → CAPABILITY_CLASSIFIED` | Capability diff against approved registry generated and hashed | Deterministic policy engine |
| `CAPABILITY_REVIEW → POLICY_APPROVED` | New capability's code, license, dependency, egress, secret, data, cost, and rollback reviewed | Human security/engineering gate |
| `POLICY_APPROVED → COMPILED` | Reproducible output from exact compiler/runtime versions | Compiler service; no network or secrets |
| `COMPILED → BUILD_VERIFIED` | Two clean builds yield the same source/lock/SBOM and expected image digest; scans pass | Isolated staging builder |
| `BUILD_VERIFIED → STAGING_DEPLOYED` | Staging-only service user; staging secrets/budget; no production registry mutation | Staging deployer |
| `STAGING_DEPLOYED → QA_RUNNING` | Immutable suite/fixture hashes and approved paid-test budget | QA controller |
| `QA_RUNNING → QA_PASSED` | Every mandatory deterministic gate passes; report is signed/hashed | QA controller; judges cannot override hard failures |
| `QA_PASSED → PROMOTION_PENDING` | Exact release, price, COGS guard, rollback target, kill switch, and report linked | Release controller |
| `PROMOTION_PENDING → CANARY` | Human promotion approval; atomic traffic allocation; run/spend/time ceiling | Human product/operations gate |
| `CANARY → LIVE` | Canary sample and time window meet quality, cost, reconciliation, security, and SLO thresholds | Human initially; bounded automation only after maturity criteria |
| `CANARY/LIVE → PAUSED` | Provider outage, cost drift, rate limit, or budget trip | Automatic safe action or operator |
| `CANARY/LIVE → QUARANTINED` | Correctness, security, rights, artifact, or tenant-isolation failure | Automatic safe action or operator |
| `QUARANTINED → ROLLED_BACK` | Traffic pointer atomically selects last healthy compatible release | Automatic safe action |
| resume | External transient condition resolved and smoke/reconciliation pass | Human; a correctness/code fix requires a new release hash |

Every transition must use compare-and-set plus an append-only event in one transactional batch:

```sql
UPDATE candidate_revisions
SET state = ?, state_version = state_version + 1
WHERE candidate_hash = ? AND state = ? AND state_version = ?;
```

The event records `transition_id`, from/to state, expected version, actor identity/type, policy version, all relevant hashes, timestamp, reason, evidence links, paid spend, and idempotency key. Zero updated rows means conflict or replay; it must not be interpreted as success. Only the traffic-allocation pointer changes buyer routing. A `modal deploy` exit code never makes a release live.

### 1.4 Repair loop boundaries

The autonomous repair loop may propose changes to prompt wording, binding expressions, deterministic normalization, and adapter parameters already inside an approved envelope. It may not:

- loosen an input/output schema or quality threshold;
- change source/rights assertions, provider/model/operation, dependency/image, GPU, egress, secret, retention, or public callback;
- raise retries, timeout, container count, concurrency, maximum dollars, or buyer price;
- suppress a test, reinterpret a hard failure, or replace a real artifact check with a judge score.

Allow at most three candidate revisions per candidate family and at most the smaller of `$1` or the release-specific QA budget. Mock/offline repair can iterate within that bound. A paid media test runs once per immutable candidate hash and is deduplicated by `(release_hash, suite_version, fixture_set_hash)`. Exceeding attempts or budget moves to `SPEC_BLOCKED`/`QA_FAILED` for human review; it never silently retries paid providers.

## 2. Quality-test suite: what “good enough to take money” means

The checked-in contract tests are useful scaffolding but not release evidence: they call route functions directly, miss the normal-JSON `body: Any` transport defect, do not enforce `format`, and do not exercise auth, durable state, provider mutation, artifacts, billing, or cross-tenant access. The root test collection also conflicts because every suite is named `test_contract.py`.

### 2.1 Test pyramid and mandatory gates

| Layer | Required tests | Release-blocking pass condition |
|---|---|---|
| Provenance/rights | Source hash, author, license/permission, asset/voice/avatar consent, claims vs facts, prompt-injection corpus | No unresolved commercial right, consent, or required implementation fact |
| Canonical spec | JSON Schema + `FormatChecker`, extra fields, DAG cycles, binding reachability/types, stable IDs, final projection, bounded loops/sizes/timeouts/retries/resources/dollars | 100% deterministic pass; unknowns fail closed |
| Capability/policy | Adapter/operation/model/package/image/GPU/secret/egress/data/retention diff | Exactly approved capabilities; no secret-like literal; no mutable provider base URL |
| Reproducible build | Clean build twice, resolved lock/hashes, SBOM, vulnerability/license policy, base-image digest, import test, generated-source diff | Reproducible reviewed output; zero disallowed dependency/license/high-severity exception |
| Offline contract | At least 3 happy fixtures, min/max boundaries, missing/extra/wrong types, Unicode, oversized input, malformed/fenced/prose LLM output, full response envelope | Provider never called on invalid input; all successful envelopes pass strict schema and semantic invariants |
| Real HTTP | Worker and retained Modal ASGI surfaces through actual `POST ... json=...`; auth, CORS, content type, timeout, `Prefer: wait`, `202/200/4xx`, stable errors | Browser never sees Modal credential/call ID; normal JSON works; errors reveal no provider body |
| Tenant/security | Missing/expired/wrong auth, cross-tenant run/artifact lookup, guessed IDs, price/release/model tampering, SSRF, forged/replayed callbacks, log/response secret canaries | Unauthorized work stops before reservation/provider/Modal; foreign resources return non-enumerating `404`; zero secret canary leakage |
| Idempotency/ledger | 100 concurrent same-key/same-body submits; same key/different body; same key in two tenants; duplicate/reordered webhook; duplicate settlement/refund | One Omo run, reservation, provider mutation, settlement, and owned artifact per tenant-scoped request; conflict is `409`; ledger reconciles to cached balance |
| Crash boundaries | Kill after run insert, reservation, orchestration start, provider send/ack, provider completion, R2 write, validation, settlement; replay reconciliation | At-least-once execution yields idempotent effects; no unowned artifact, duplicate paid job, double charge/refund, or terminal run without an event trail |
| Provider behavior | Fixture and live 401/409/429/5xx, timeout, delayed/missing/out-of-order callback, artifact-not-ready, provider schema drift | Stable internal errors, bounded jittered retry owned by orchestrator, circuit breaker, stale-run reconciliation, hard dollar/time cap |
| Artifact | Exact key ownership, MIME/magic bytes, checksum, size, decode, metadata, expiry, signed URL scope and TTL | Artifact is private, Omo-owned, owner-authorized, durable, and matches declared type |
| Product quality | Deterministic rubrics first; separate evaluator and human sample second | No unsupported claim or safety violation; release-specific acceptance threshold met; judge cannot waive a hard failure |
| Cost | Static quote, physical-call count, metered CPU/RAM/GPU seconds, retries/failures, artifact costs, accepted-output yield, invoice reconciliation | Actual per-run ceiling never exceeded; quote uses guarded cost; unresolved/unknown cost unit blocks promotion |
| Load/cold start | Scale-from-zero, warm burst, 15 logical releases, per-tenant/provider/GPU admission, 429/queue behavior, cancellation | Public submit path remains independent of Modal; no provider/quota oversubscription; queue age and execution SLO remain within release limits |
| Rollback/incident | Kill switch, canary reduction, previous-release pointer, provider outage, cost-table invalidation | Spend stops promptly; in-flight runs reconcile; previous compatible release serves without data/schema corruption |

Minimum counts are a floor, not a proof of statistical quality. Run mock/contract/security tests on every compiler/runtime change. Run paid provider and media tests only for the exact release hash under the candidate-family spend cap. Store outputs and redacted traces with the QA report so a human can inspect the same evidence.

### 2.2 Release-specific product gates

**Pure-LLM UGC Script Studio:** strict typed output; every factual/product claim traceable to input; zero forbidden regulated claims; actual token usage recorded; repeated fixture evaluation against a versioned rubric; provider timeout and malformed-output behavior release the reservation once. Use `Prefer: wait=8` for convenience, but persist the run before execution.

**HeyGen 15-second beta:** Omo-owned MP4; video and audio streams decode; portrait ratio matches 9:16 within container/codec tolerance; duration initially within 13.5–16.5 seconds; ASR materially matches the approved script; captions correspond to approved lines; no extra unsupported spoken/on-screen claim; checksum/bytes/MIME/dimensions/duration stored. The first 20 paid artifacts require human review. The ASR threshold must be calibrated for accent/noise before becoming an automatic rejection; deterministic “missing or added material claim” detection remains authoritative.

**Future image GPU release:** real decodable pixels, no mock domain, pinned commercially usable weights, expected dimensions/aspect, product/logo/text fidelity against reference, prompt adherence, safety checks, private R2 ownership, and accepted-image yield. Price per accepted deliverable, not per GPU attempt. Three requested variants must state whether they are one batch, serial calls, or parallel calls and meter that physical execution.

### 2.3 Human-in-the-loop gates

| Gate | Human decision | Can it later be automated? |
|---|---|---|
| H0 — rights/product | May Omo legally derive, market, and operate this workflow and its source assets? Is the listing claim honest? | No for ambiguous rights/consent; known owned templates may use policy preapproval |
| H1 — capability/security | Approve every new/expanded adapter, operation, package, image, binary, model/license, GPU, egress, secret, callback, data class, or retention rule | No; a previously approved capability can enter the spec-only lane |
| H2 — paid QA | Authorize staging credentials and exact provider-spend ceiling for the hash | Can be policy-automated only below a small release/family budget after billing maturity |
| H3 — canary promotion | Inspect QA report, first real artifacts, price/COGS guard, rollback target, and kill switch | Keep manual for the first three real workflow classes and every new capability |
| H4 — live graduation | Review canary quality, cost, reconciliation, support/refunds, and incident-free window | May automate for spec-only releases after maturity criteria |
| H5 — incident resume | Confirm cause resolved and reconciliation/smoke pass | Transient provider pause may later auto-resume; security/correctness quarantine remains manual/new release |

Do not permit autonomous live graduation until Omo has at least one manually operated pure-LLM release, one asynchronous provider release, and one real Modal GPU release; 30 days of cost/failure/quality telemetry; a successful rollback and quarantine drill; and zero unresolved billing reconciliation items. Even then, only spec-only releases inside an approved capability envelope may auto-canary/live. New capabilities always retain H1/H3.

Suggested initial canary: 1–5% traffic, at most 20 paid runs, at most the release's explicit canary dollars, one tenant expensive run at a time, and an expiry that automatically returns allocation to zero if H4 does not occur. Auto-quarantine on any tenant leak, duplicate paid mutation, ledger mismatch, secret exposure, unsupported material claim, corrupt/unowned artifact, or hard cost-ceiling breach. Failure-rate/cost/latency thresholds should use minimum sample sizes to avoid noisy flapping, but security and money invariants require only one confirmed event.

## 3. Secrets and multi-tenancy

### 3.1 Threat model and non-negotiable invariants

At 15+ workflows, the likely failures are not hypervisor escapes. They are application mistakes: trusting `user_id`, exposing an opaque-but-foreign run ID, sharing a mutable global between concurrent inputs, reusing a temp filename, attaching a provider bundle to every Function, returning a presigned provider URL, double-settling a replay, or letting one workflow exhaust a workspace/provider quota.

Required invariants:

1. Identity is derived from a verified Clerk JWT or random Omo API key; never from request `user_id`.
2. Every durable row and object has one `tenant_id`; every read/mutation includes the authenticated tenant predicate.
3. One `(tenant_id, workflow_slug, idempotency_key)` binds one canonical request hash to one Omo run.
4. The server chooses release, prompt, model, provider operation, price, retry/resource limit, and artifact prefix.
5. Credits reserve before external spend; every financial effect has a globally unique effect ID; terminal settlement/refund is replay-safe.
6. Provider job/event IDs are unique and tied to one stored run; callbacks do not choose tenancy.
7. Modal call IDs, URLs, Proxy Tokens, service-user tokens, provider keys, and raw R2 credentials never reach buyers.
8. Modal outputs are execution evidence only. D1/R2 remain durable truth; Modal documents Function input/output retention of at most seven days.
9. A release may access only its declared capability. A storefront workflow name is not a security boundary.
10. A per-tenant limit, per-release limit, provider semaphore, GPU-class queue, production-environment budget, and workspace budget all apply before enqueue.

### 3.2 Credential placement and blast radius

| Credential/configuration | Owner and location | Must never be present in |
|---|---|---|
| Clerk verification material, Omo API-key pepper/hashes | Public gateway secret store | Browser, Modal, workflow spec, logs |
| Stripe secret/webhook key | Billing gateway only | Orchestrator, Modal, catalog, client |
| Provider webhook verification key | Dedicated public callback receiver | Browser, general Modal runtime |
| Hosted LLM/HeyGen platform keys | Private Cloudflare orchestrator that makes those calls | Modal when Modal does not call that provider; public gateway/client |
| Modal CI service-user token | CI secret manager; separate staging/prod principals, least-privilege environment roles | Runtime image, Worker response, spec, extractor/QA agent |
| Modal invocation Proxy Token | Private orchestrator/gateway secret, production-environment scoped where RBAC is available | Browser, listing, D1 plaintext, logs |
| GPU model download token | Only the exact build/init Function that needs it; prefer build-time artifact with license controls | Shared CPU utility, ASGI ingress, unrelated GPU model |
| Artifact capability | Prefer exact-object, method-limited, expiring GET/PUT URLs or an internal broker token for one run | Catalog, durable logs, another run |
| Provider base URL/model/API version | Immutable reviewed release configuration | Mutable Secret/environment override |
| Buyer money, quote, limits | D1/release registry integer fields | Modal environment variables or buyer input |

Modal [Secrets](https://modal.com/docs/guide/secrets) are injected as environment variables at `@app.function`/`@app.cls` scope; later Secret objects overwrite colliding keys. Therefore do not layer broad Secrets or rely on key collisions. Use one versioned, capability-specific Secret reference per Function, and keep non-secret endpoints/models in the hashed release. A secret edit must not silently alter an approved warm release: bind a new secret name/version, deploy the exact release, smoke/canary it, move traffic, then revoke the old credential after an overlap window.

Modal [Environments](https://modal.com/docs/guide/environments) isolate Apps, Secrets, Dicts, and Volumes by default. Use separate `dev`, `staging`, and `production` Environments and never make an implicit cross-environment lookup. Use separate least-privilege [service users](https://modal.com/docs/guide/service-users); the staging deployer has no production role, and the production deployer is not available to extraction, compiler, or runtime. Proxy Tokens protect retained Web Functions, which otherwise default public; they are infrastructure authentication, not buyer authorization ([Proxy Tokens](https://modal.com/docs/guide/webhook-proxy-auth)).

Prefer no public Modal HTTP endpoint at all when the orchestrator can invoke a deployed Function directly. If HTTP is retained, require Proxy Token auth, accept only signed Omo execution capabilities, and expose neither endpoint nor call ID to buyers.

### 3.3 Per-run execution capability

The orchestrator should sign a short-lived capability containing only:

```text
run_id, opaque tenant_partition, release_hash, request_hash,
input artifact key/digest, exact output key/prefix,
allowed operation, max variants, max wall/GPU seconds,
not-before, expiry, nonce
```

Modal verifies the signature using a public key baked into reviewed configuration, then revalidates the release and limits. It returns result metadata under `run_id`; it cannot select the buyer, price, balance, release, provider URL, or destination. Prefer pre-created exact-object GET/PUT artifact URLs with a TTL longer than the bounded run plus reconciliation cushion. That removes permanent R2 write credentials from Modal and prevents one compromised Function from listing or overwriting another tenant's artifacts.

Do not support buyer-supplied provider keys in v1. Per-user Modal Secrets would create operational explosion, and environment variables persist for the container and are shared across concurrent inputs. If BYOK is later required, store encrypted credentials behind a tenant-aware credential broker; mint a one-run provider capability or make the provider call in the broker/orchestrator. A Modal worker should never receive a long-lived buyer key as a normal argument. Any exceptional secret-bearing execution must use a single-use, non-concurrent container and memory-only handling with zero secret logging.

### 3.4 Shared-container hygiene

`@modal.concurrent` means inputs can share a process, environment, globals, caches, and filesystem. For trusted platform-key workloads, concurrency is acceptable only when:

- all run state is local to the request/task, never a module-level mutable `current_user/current_run`;
- each run uses a non-guessable dedicated temp directory and exact artifact key;
- caches contain only immutable model/runtime data, never tenant prompts/results/credentials;
- clients do not mutate per-request auth headers or base URLs globally;
- cleanup occurs in `finally`, while output is copied before cleanup;
- cancellation and thread/async behavior are load-tested; logs carry opaque run IDs, not raw buyer data.

For LLM-generated or repository code, use a distinct restricted execution class. Modal's [Restricted Functions](https://modal.com/docs/guide/restricted-access) can disable access to other Modal resources; use `restrict_modal_access=True`, `single_use_containers=True`, a strict timeout, minimum source files, and `block_network=True` by default. If a process interface is needed, a [Sandbox](https://modal.com/docs/guide/sandbox-networking) defaults to no inbound access or Modal-resource access, but outbound public networking is open by default: explicitly block it or use a TLS domain/CIDR allowlist. Never run untrusted source in a normal shared Function with production Secrets merely because gVisor exists.

### 3.5 Durable tenant and billing flow

```text
1 authenticate → tenant_id
2 resolve live release server-side
3 validate/canonicalize input → request_hash
4 create-or-replay run and reserve credits atomically
5 enqueue durable workflow using run_id as instance/effect namespace
6 invoke provider/Modal with run-derived idempotency and bounded capability
7 persist provider job ID before waiting; dedupe callbacks/events
8 obtain private artifact → checksum/validate → record ownership
9 settle once if accepted; release/refund once otherwise
10 reconcile stale nonterminal states and invoice/usage cohorts
```

Use integer cents for buyer money and integer nano-USD or another documented high-resolution integer for COGS; micro-USD is too coarse for the cheapest LLM steps if individual token accounting matters. Keep purchased and promotional balances separate. Promo credits should initially be valid only for cheap demos/LLM runs; require verified/payment-backed users for external video/GPU spend.

The database must enforce unique `(tenant_id, workflow_slug, idempotency_key)`, `provider_job_id`, `provider_event_id`, `workflow_instance_id`, and ledger `effect_id`. `authorizeRun(tenant_id, run_id)` must be the only result/artifact entry point. Return `404`, not a distinguishable `403`, for a foreign resource. D1 is a shared database without application row-level security; isolation therefore depends on repository functions that make the tenant predicate unavoidable plus adversarial tests for every path.

Reserve from a server quote containing `release_hash`, `price_cents`, `reserve_cents`, `max_cost_nanos`, `cost_version`, and expiry. A run records the exact quote; later catalog repricing cannot change it. Workspace/environment budgets are only outer circuit breakers, not tenant billing. Modal notes that environment budgets are Team/Enterprise-only and exclude some workspace charges such as storage/reservations ([budgets](https://modal.com/docs/guide/budgets)).

### 3.6 Scaling 15+ workflows on Modal

Define pools by execution/trust class:

| Class | Deployment | Initial scaling | Isolation/capacity policy |
|---|---|---|---|
| Hosted LLM / HeyGen / other edge-safe HTTP API | No Modal | Cloudflare orchestration | Provider semaphore and per-tenant spend/concurrency |
| CPU media validation/transcode | One shared small reviewed App if edge limits require it | `min_containers=0`, start `scaledown_window=60`; concurrency only after tests | Immutable runtime cache; run-local temp/artifact paths |
| Resident GPU model | One `Cls`/pool per model + incompatible dependency/VRAM shape, not per listing | `min_containers=0`, short 2s window initially; tune from interarrival/cold-init traces | Global GPU queue, max wall/GPU seconds, batch only compatible tenants safely |
| Untrusted code | Separate Restricted Function or Sandbox App | Single-use, scale to zero, strict timeout | No Secrets/Modal access; network blocked/allowlisted; minimal source |

Modal's live Starter limits are currently 100 containers, 10 GPU concurrency, and 200 deployed Apps; Team lists 5,000 containers, 50 GPU concurrency, 1,000 Apps, 30-day logs, environment budgets, and a `$250 + compute/month` plan price ([pricing](https://modal.com/pricing)). Fifteen logical GPU workflows can queue on Starter, but 15 simultaneous GPU executions exceed its advertised GPU concurrency. At the assumed `$100k MRR` target, Team's fixed `$250` is 0.25% of monthly revenue and is justified before paid GPU GA for budgets, logs, rollback features, and headroom—not before a real GPU workload exists.

Modal also documents 2,000 pending inputs per Function (one million for `.spawn()` jobs) and 25,000 total inputs, but those are infrastructure ceilings, not product admission targets ([scaling](https://modal.com/docs/guide/scale)). Omo should queue much earlier based on per-tenant fairness, provider quotas, GPU availability, maximum queue age, and prepaid exposure. `max_containers=10` in each of 15 Apps is not a global provider or spend limit.

## 4. Async versus sync contract and cold starts

Use one durable run resource for every paid call:

```http
POST /api/v1/runs
Authorization: Bearer ...
Idempotency-Key: ...
Prefer: wait=8

{"workflow_slug":"ugc-script-studio","input":{...}}
```

- Auth, release resolution, validation, quote, durable run creation, and reservation always occur before execution.
- A fast LLM run may return `200` with the completed resource inside the bounded wait.
- Otherwise return `202` with the same `run_id`, status, and owner-authorized status URL.
- Remote async providers and GPU/media jobs always return `202`; never hold the public request open for them.
- `GET /api/v1/runs/{run_id}` is durable and authorized. Modal `FunctionCall` IDs and provider IDs remain internal.
- Immediate request defects are `4xx`; execution errors are durable terminal/intermediate run states with stable codes.

This removes Modal cold starts from the buyer submission SLO. Hosted-provider workflows have no Modal cold start. For the shared CPU utility, start scale-to-zero with a 60-second window; one 0.25-core/0.5-GiB continuously warm container is about `$11.37/month` at current base rates, so a warm minimum becomes rational if measured latency affects conversion. For GPU, keep zero minimum until traces prove otherwise. A continuously warm A10 + 2 cores + 16 GiB is about `$953/month` base; 15 such pools would be about `$14,297/month` before premiums, which is precisely why logical workflow count must not determine warm-pool count.

Modal's pricing FAQ says billable time includes application load, input processing, and the default 60-second post-input idle window; scale-to-zero stops charges. Record `queue_ms`, `container_boot_ms`, `model_init_ms`, `execution_ms`, `artifact_ms`, and `warm_idle_allocated_ms` separately. Bake small stable assets into the image, place large pinned weights in the fastest reproducible supported storage path, initialize clients/models once per container, and evaluate memory snapshots only after the real model has a reproducible cold/warm benchmark. Do not hide boot/init inside an “inference seconds” bucket.

## 5. Modal price validation and the 5× model

### 5.1 Live base prices

Modal's [pricing page](https://modal.com/pricing), checked 2026-08-10, lists CPU at `$0.0000131/physical-core-second`, memory at `$0.00000222/GiB-second`, and the following GPU-only base rates. CPU and memory are additional. Region selection is listed at `1.5–1.75×` base and non-preemptible execution at `3×`; do not assume how multiple premiums combine without the account invoice.

| GPU | USD/second | Raw 30s | 5× raw 30s | Repo `$0.05` / raw 30s |
|---|---:|---:|---:|---:|
| B300 | `$0.001972` | `$0.05916` | `$0.29580` | `0.85×` |
| B200 | `$0.001736` | `$0.05208` | `$0.26040` | `0.96×` |
| H200 | `$0.001261` | `$0.03783` | `$0.18915` | `1.32×` |
| H100 | `$0.001097` | `$0.03291` | `$0.16455` | `1.52×` |
| RTX PRO 6000 | `$0.000842` | `$0.02526` | `$0.12630` | `1.98×` |
| A100 80 GB | `$0.000694` | `$0.02082` | `$0.10410` | `2.40×` |
| A100 40 GB | `$0.000583` | `$0.01749` | `$0.08745` | `2.86×` |
| L40S | `$0.000542` | `$0.01626` | `$0.08130` | `3.08×` |
| A10 | `$0.000306` | `$0.00918` | `$0.04590` | `5.45×` |
| L4 | `$0.000222` | `$0.00666` | `$0.03330` | `7.51×` |
| T4 | `$0.000164` | `$0.00492` | `$0.02460` | `10.16×` |

The current generic bucket is conservative for 30 raw seconds on most accelerators but is not a physical or stable calculation. It underestimates B200/B300 before CPU/RAM, and it can still underestimate a cheaper GPU when cold initialization, multiple variants, retries, warm idle, regional selection, or rejected outputs extend billed time. Conversely it materially overstates a short warm A10/T4 job. A catalog cannot infer margin from that bucket.

### 5.2 Realistic A10 shape example

For an illustrative A10 Function with 2 physical cores and 16 GiB:

```text
rate = 0.000306
     + 2 × 0.0000131
     + 16 × 0.00000222
     = $0.00036772/second
```

| Billed load + execution + allocated idle | Base compute COGS | 5× | Buyer price rounded **up** to cent/floor |
|---:|---:|---:|---:|
| 30s | `$0.011032` | `$0.055158` | `$0.10` floor |
| 60s | `$0.022063` | `$0.110316` | `$0.12` |
| 120s | `$0.044126` | `$0.220632` | `$0.23` |
| 180s | `$0.066190` | `$0.330948` | `$0.34` |
| 300s | `$0.110316` | `$0.551580` | `$0.56` |

These figures exclude storage, network, provider/LLM calls, retries, failed/rejected images, payment/support/fraud, and premiums. At 60 seconds, a 1.75× selected-region base would be about `$0.03861`; 3× non-preemptible would be about `$0.06619`, before other costs. Price from the actual release configuration and invoice reconciliation.

### 5.3 What 5× does and does not guarantee

When complete `C` is multiplied by 5, `(5C-C)/(5C)=80%`. The `$0.10` floor yields a higher percentage on tiny costs. Cent rounding can reduce the intended margin: current `toFixed(2)` rounds nearest, so `$0.110316` becomes `$0.11`; use `ceil(price*100)/100`, which yields `$0.12`.

The current image canary's `$0.2202` estimate and `$1.10` price are not validated economics. It charges three `openai_image` buckets plus two generic GPU buckets while the described end state is local generation, and the deployed A10 code only hashes a prompt into fake URLs. Remove the remote image charge if the real path is local; remove the GPU charge if the real path is remote. Then measure the selected model's boot, load, batch/variant execution, artifact validation/upload, OOM/preemption, warm idle, and accepted-image yield.

Use:

```text
Modal_attempt = premium × (
    Σ gpu_seconds[g] × gpu_rate[g]
  + cpu_core_seconds × cpu_rate
  + memory_gib_seconds × memory_rate)
  + storage + egress

C_delivered = (
    provider + Modal attempts + Cloudflare + R2
  + paid failures/retries/duplicates + payment fees
  + promo/fraud loss + variable support/refund allowance)
  / max(accepted, 1)

C_guard = max(static worst-case release budget,
              recent p95 successful cost,
              7d/30d delivered-sale cost + tail reserve)

price_cents = ceil(max(product_floor,
                       C_guard / (1-target_margin)) × 100)
```

Keep 5×/80% as a launch target for releases with complete cost evidence. Do not schedule a global 1.25× switch: that is a 20% margin before missing costs and is unsafe for paid media. Reconcile runtime estimates to Modal/provider invoices daily during canary and at least weekly after stability. Auto-pause a release when cost-table version expires, estimate/invoice variance exceeds its threshold, accepted-output yield falls, or accrued run cost approaches the hard ceiling.

## 6. Concrete file-level recommendations

These are recommendations only; this round changes no implementation files.

### Cloudflare control plane

- **`site/deploy/worker.js`:** retire public `handleGenericRun`; add authenticated `POST /api/v1/runs` and owner-only `GET /api/v1/runs/:id`. Never accept `user_id`, `system_prompt`, model, token limit, price, release, provider IDs, or artifact destination as authority. Split webhook receiver and private orchestration responsibilities as the system matures. Remove raw provider-body excerpts from `callLLM` errors.
- **New `site/deploy/auth.mjs`:** `authenticateRequest`, `hashApiKey`, `rotateApiKey`, and non-enumerating authorization helpers. Generate random high-entropy Omo keys; store hashes/prefix/metadata only.
- **New `site/deploy/run-repository.mjs`:** `createOrReplayRun`, `authorizeRun`, `transitionRun`, `recordProviderJob`, `recordArtifact`, `reconcileStaleRuns`. Every method requires `tenantId`; transitions use compare-and-set.
- **New `site/deploy/ledger.mjs`:** `reserveCredits`, `settleRun`, `releaseReservation`, `applyTopup`, `reconcileBalance`; append-only unique effect IDs and purchased/promo buckets. Replace `reserveRunCredits`, `refundRunCredits`, and `addRun` as separate crash-prone effects.
- **New `site/deploy/release-registry.mjs`:** `resolveLiveRelease`, `resolveQuote`, `assertCapability`, `setTrafficAllocation`, `quarantineRelease`; registry owns all prompts/models/limits/prices.
- **New `site/deploy/run-workflow.mjs`:** durable Cloudflare Workflow entry with step-level retry/time/dollar budgets, provider event wait, reconciliation, artifact validation, and settlement. Hosted LLM/HeyGen calls occur here, not in a sleeping Modal Function.
- **`site/deploy/schema.sql`:** replace as a production migration mechanism with `site/deploy/migrations/0001...`; add tenants/API keys, workflow candidates/releases/traffic allocations, runs/events/effects, quotes/reservations/ledger, provider jobs/events, artifacts, QA reports, and reconciliation indexes/constraints. Preserve the bootstrap only for local setup if useful.
- **`site/deploy/cost-model.mjs`:** make unknown models/cost codes fatal; replace `modal_gpu_30s` with `modalComputeCost(resourceUsage, priceVersion)`; add `quoteRelease`, integer COGS, upward rounding, target margin, quote TTL, hard ceiling, actual usage and delivered-sale reconciliation. Remove global automatic `MARKUP` policy from runtime truth.
- **`site/deploy/test-router.mjs` and new focused tests:** real auth/HTTP, 100-way replay, tenant matrix, crash injection at every effect boundary, callback replay/reorder, artifact authorization, quote immutability, ledger reconciliation, and kill-switch/rollback.
- **`scripts/go-live.sh`:** stop rotating a derivation secret on every run; use numbered migrations and stable secret rotation; deploy staged immutable artifacts; verify auth, run/ledger, Workflow/R2, Modal invocation, webhook, cost and rollback; provision `STRIPE_WEBHOOK_SECRET`; do not source a general executable `.env` for production.

### Autopilot control plane

- **New `autopilot/schemas/container-spec.v1.json`:** canonical vocabulary for contracts, stable DAG/bindings, adapter operations, resources, secret capabilities, egress, data/retention, artifact and cost policy.
- **New `autopilot/schemas/provenance.v1.json` and `capability-manifest.v1.json`:** field-level evidence/confidence and deterministic privilege diff.
- **New `autopilot/state-machine.mjs`:** `transitionCandidate` and `transitionRelease` with the legal matrix, roles, CAS version, event/evidence requirements, and idempotency.
- **New `autopilot/policy.mjs`:** `diffCapabilities`, `validateSpec`, `classifyLane`, `assertRepairAllowed`, `assertSpendBudget`; fail closed.
- **New `autopilot/compiler/compile.mjs`:** pure deterministic compiler; no network, source execution, secrets, or arbitrary Python/shell/Jinja/JavaScript expressions.
- **New `autopilot/qa/`:** `contract`, `security`, `idempotency`, `billing`, `provider`, `artifact`, `quality`, `load`, `cost`, and `rollback` suites plus report signer. Cache only exact hash tuples.
- **New `autopilot/release-controller.mjs`:** staging deploy, QA trigger, human approval record, expiring canary allocation, automatic pause/quarantine/rollback. It receives release authority but never provider secret values.

### Modal execution plane

- **Do not expand the three workflow-specific `modal_app.py` files.** Fix their JSON-body/real-ASGI tests only if they remain useful fixtures. Remove per-workflow public ingress in the target architecture.
- **New `containers/modal-media/modal_app.py`:** shared reviewed `validate_media`/transcode capability with no buyer/provider/billing secrets; exact signed input/output objects; run-local temp directories; actual resource telemetry.
- **Future `containers/modal-imagegen/modal_app.py`:** one real pinned licensed model class, release-hash/model-digest verification, no mock URLs, model-only Secret, scale-to-zero, accepted-image benchmark, and no broad provider bundle.
- **New `containers/modal-untrusted/`:** minimal Restricted Function/Sandbox package with single-use containers, no Modal-resource access, blocked/allowlisted network, timeout, no production Secrets, and no unrelated repository source.
- **All retained Functions:** dev/staging/prod environment separation, capability-specific versioned Secrets, signed run capability verification, no mutable global tenant/client auth, exact artifact path, stable redacted errors, phase/resource metrics, and tests for concurrency/cancellation/cleanup.
- **`containers/gpt-image-seedance-ad/modal_app.py`:** never deploy `_mock_images_inside_container` or `generate_images_gpu` as a paid release; it buys an A10 to produce no pixels and attaches a provider Secret the GPU function does not need.
- **`containers/ugc-heygen/`:** retain as provenance/contract fixture; move the real provider orchestration to Cloudflare, remove raw avatar/voice IDs from buyer input, make completed output require a validated owned artifact, and remove stale `$0.15`/broad canary secret capability.

## 7. What to build first, what to cut

### Build first

1. **Stop client authority:** authenticated tenant derivation, random API keys, server release/price/prompt/model, restrictive CORS, private execution.
2. **Durable money and run state:** migration-backed runs/events/quotes/reservations/append-only ledger/artifacts with legal CAS transitions, idempotency, ownership, purchased/promo separation, and reconciliation.
3. **Final public contract:** durable run resource plus bounded `Prefer: wait`; no buyer-visible Modal dependency.
4. **Pure-LLM UGC Script Studio:** first paid workflow through the final auth/quote/reserve/settle/telemetry path at the `$0.10` floor, without Modal.
5. **Minimal spec-only autopilot:** canonical schemas, provenance, capability diff, deterministic compiler, state machine, offline/security/billing QA, signed report. Use one manually curated workflow; no autonomous live promotion.
6. **HeyGen 15s invite beta:** durable provider events/reconciliation, private artifacts, media/claim QA, invoice-derived cost, purchased-credit requirement, first-20 human review, hard spend/concurrency kill switch.
7. **Real GPU benchmark:** select licensed model; measure cold/warm/accepted yield on current resource prices; only then build one GPU execution class and upgrade Modal plan if required.
8. **Canary automation:** after three workflow classes, 30 days telemetry, rollback drill, and clean billing reconciliation.

### Cut or postpone

- One Modal App/API/runner pair per storefront workflow.
- Modal CPU wrappers and long polling for hosted LLM/HeyGen orchestration.
- Buyer-visible Modal URLs, Proxy Tokens, call IDs, or provider IDs.
- Per-user Modal Secrets/Apps and BYOK in v1.
- Agent-generated arbitrary Python, Dockerfiles, packages, install hooks, shell, or executable binding expressions.
- Autonomous approval of rights, new capabilities, paid QA escalation, or first production promotion.
- Reusing the same release hash after a repair or capability/config change.
- The fake A10 image generator and any cost conclusion based on it.
- The generic `$0.05/30s` GPU bucket once resource metering exists.
- A universal two-second scale-down policy, 15 warm GPU pools, or a universal `min_containers=0` doctrine after measured latency economics.
- A scheduled global reduction to 1.25× markup.

## 8. Top residual risks and controls

| Risk | Control |
|---|---|
| Source prompt injection/supply-chain execution | Evidence-only ingestion, no deploy secrets, constrained schema, deterministic compiler, isolated restricted build/test, allowlisted locked dependencies |
| Rights/consent ambiguity | H0 blocks evidence freeze/publication; source and approval hashes retained |
| Cross-tenant read/write | Auth-derived tenant, mandatory repository predicates, non-enumerating lookup, exact signed artifact capability, concurrency/temp-path tests |
| Shared platform-key blast radius | Calls occur only in owning plane; capability-specific Function Secrets; global/provider/tenant admission; rapid rotation/kill switch |
| Duplicate paid provider work | Tenant-scoped idempotency, run-derived provider key, unique job/event/effect IDs, persisted acknowledgement, stale-run reconciliation |
| Double charge/refund or balance drift | Append-only ledger, atomic reserve/create, CAS terminal effects, crash injection, cached-balance reconciliation |
| Webhook missing/forged/reordered | Raw-byte signature/timestamp, event dedupe, job-to-run match, server re-read, durable event wait, periodic reconciliation |
| Cost/5× false confidence | Physical resource metering, premiums, accepted yield, paid failures, invoice reconciliation, guarded cost, upward rounding, hard run/canary/environment/workspace caps |
| GPU cold start/queue surprise | No Modal dependency in submit path, pools by model, zero warm initially, trace phases, global admission and queue-age SLO, Team upgrade before GA if needed |
| Self-grading quality drift | Deterministic gates authoritative, separate evaluator, human artifact sample, canary telemetry, immutable rubric/suite hashes, auto-quarantine |

## Bottom line

At `$100k` scale, the optimization target is not shaving fractions of a cent from a fake GPU canary. It is preventing one autonomous capability expansion, tenant leak, duplicate paid render, stale price, or unbounded retry from becoming a support and margin incident. Build the authenticated run/ledger/release substrate first; allow autopilot to automate evidence, spec, deterministic compilation, and testing inside a preapproved envelope; keep humans at rights, capability, spend, and promotion boundaries. Keep Modal narrow, private, capability-scoped, and pooled by compute/trust class. That architecture can add 15 or 150 logical workflows without multiplying secrets, cold starts, public endpoints, or billing authorities.

## Primary current references

- Modal [pricing and plan limits](https://modal.com/pricing)
- Modal [Secrets](https://modal.com/docs/guide/secrets), [Environments](https://modal.com/docs/guide/environments), [service users](https://modal.com/docs/guide/service-users), and [Proxy Tokens](https://modal.com/docs/guide/webhook-proxy-auth)
- Modal [scaling](https://modal.com/docs/guide/scale), [budgets](https://modal.com/docs/guide/budgets), and [security/data retention](https://modal.com/docs/guide/security)
- Modal [Restricted Functions](https://modal.com/docs/guide/restricted-access) and [Sandbox networking/security](https://modal.com/docs/guide/sandbox-networking)

Prices, plan limits, SDK behavior, provider APIs, and billing units are time-sensitive. Pin the actual runtime/release, capture the account plan/region/preemptibility, and reconcile usage to invoices before each paid promotion.
