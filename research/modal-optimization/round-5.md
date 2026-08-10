# Modal hosting optimization — Round 5: Modal runs every workflow

**Date:** 2026-08-10  
**Status:** final runtime reconciliation. This round supersedes Round 4's runtime-placement and build-order decisions. It retains Round 4's security, tenancy, billing, release, artifact, and pricing invariants.  
**Directive:** every marketplace listing compiles to an immutable, API-activated Modal deployment. Cloudflare remains the public gateway, but it no longer executes hosted LLM or remote-provider workflow steps.

## Executive decision

Reverse Round 4's runtime split. **Modal is the universal execution plane for every workflow**:

- hosted LLM calls run from the listing's Modal container;
- remote provider operations such as HeyGen create/status calls run from that container;
- native binaries, media processing, local CPU/GPU models, and restricted sandboxes also run on Modal;
- each listing follows the same path: SKILL.md or catalog evidence → canonical container.yaml → generated modal_app.py → modal deploy → real QA → immutable release → live traffic;
- buyers use one public POST /v1/runs contract, regardless of whether the listing is one LLM call or a multi-step GPU/media workflow.

The cost is deliberate: a pure-LLM run now pays an additional Modal hop, usually a 1–5 second cold start when scaled to zero, small CPU/memory charges while waiting on the provider, per-workflow deployment overhead, and one selected execution region. Those are acceptable at the $0.10 floor and an 80% target margin if warm capacity is selective, images share layers, tiny I/O-bound apps use concurrency, and every release has a hard cost ceiling.

This does **not** make Modal the public control plane or the money authority. The Cloudflare Worker remains the only buyer-facing gateway. D1 remains the system of record for identity-linked business state, accepted quotes, run ownership, events, reservations, and the append-only ledger. R2 remains the artifact store. Modal owns active execution, queues, retries, and workflow step progression; it continuously checkpoints business-relevant state into D1. Modal call state is not sufficient archival storage and is never exposed to buyers.

Cloudflare Workflows is optional only as a small outbox dispatcher, callback relay, or wake-up bridge. It must not contain the listing DAG, call hosted providers, own retries for workflow steps, or become the durable workflow engine.

## 1. Final “Modal runs the workflows” architecture

    Buyer / API client
      Clerk JWT or random Omo API key
      Idempotency-Key + Prefer: wait=8
                    │
                    ▼
    Cloudflare Worker — only public gateway
      authenticate → rate limit → resolve immutable release
      validate/canonicalize input → request hash → quote
      D1 CAS: create/replay run + reserve credits + dispatch outbox
                    │
                    │ private Proxy Token + short-lived signed run capability
                    ▼
    Release-specific Modal App: omo-<slug>-<release_hash>
      protected POST /v1/runs → claim run_id → spawn/execute task graph
                    │
          ┌─────────┼──────────────┬───────────────┬──────────────┐
          ▼         ▼              ▼               ▼              ▼
        LLM      HeyGen/API     native media     GPU model     sandbox
        steps     adapters       binaries         inference     execution
          └─────────┴──────────────┴───────────────┴──────────────┘
                    │
          signed checkpoints / provider IDs / usage / terminal result
                    │
           ┌────────┴────────┐
           ▼                 ▼
      D1 run + ledger     R2 owned artifacts
      reconciliation      checksum + metadata
           │                 │
           └────────┬────────┘
                    ▼
    Worker GET /v1/runs/{run_id}
      owner-authorized durable result; 404 for a foreign run

    Provider webhook
      → Worker verifies signature/timestamp/event ID
      → D1 event inbox
      → direct Modal resume dispatch
        or optional Cloudflare Workflow bridge

### 1.1 Exact request path

1. authenticateRequest derives tenant_id from a verified Clerk JWT or a random Omo API-key hash. A request user_id is ignored or rejected.
2. resolveLiveRelease selects the server-owned release, prompt, schemas, model, adapter operations, price policy, resource limits, Modal endpoint, and rollback target.
3. The Worker validates and canonicalizes input, then computes request_hash.
4. Idempotency is checked on unique (tenant_id, workflow_slug, idempotency_key). Same key and hash returns the existing run. Same key and a different hash returns 409.
5. resolveQuote creates a server-authored quote with a 10-minute TTL, integer price/reservation fields, cost-policy version, and hard maximum cost.
6. One D1 transactional batch creates or replays the run, reserves credits, appends run and ledger events, and writes a dispatch_outbox row. No Modal or provider call may precede reservation.
7. The dispatcher sends run_id, release_hash, request_hash, validated input or an exact R2 input reference, and the hard execution budget to the release-specific Modal endpoint. Modal Proxy Token authentication and a short-lived signed execution capability are both required.
8. The Modal App idempotently claims run_id, records its internal call ID, and executes the complete listing DAG. Every paid mutation uses a run-derived effect key and persists the provider acknowledgement before another attempt.
9. The App emits signed state checkpoints and actual usage to a private Worker callback that performs D1 compare-and-set transitions. Modal does not receive general D1 credentials.
10. Artifacts are written to exact run-scoped R2 keys with method-limited capabilities, then checksummed and validated before success.
11. The Worker waits at most eight seconds when Prefer: wait=8 is present. It returns 200 if the durable run completed; otherwise it returns 202 with the same Omo run resource and status URL.
12. GET /v1/runs/{run_id} reads D1/R2 ownership state. It never accepts or reveals a Modal FunctionCall ID, Modal URL, Proxy Token, provider job ID, or raw provider body.

For HeyGen and similar asynchronous providers, do not occupy a CPU container for 15 minutes merely to sleep. The listing's Modal App performs the create operation, checkpoints provider_job_id, ends that task, and resumes through a signed callback or bounded, rescheduled Modal status task. The provider operation and continuation logic still live in Modal; the Worker or optional Cloudflare Workflow only verifies and relays the public event.

The durable D1 projection is:

    run: queued → reserved → dispatched → running
                     ├→ awaiting_provider → artifact_copying → validating → succeeded
                     └→ failed | cancelled | expired

    reservation: reserved → settled | released

Modal owns the active task/queue and proposes execution transitions; the Worker's private checkpoint route commits legal compare-and-set transitions and append-only events in D1. A stale-run reconciler compares D1 checkpoints, stored Modal call metadata, provider jobs/events, and R2 artifacts. This makes Modal the workflow engine without pretending that transient FunctionCall retention is the order database.

### 1.2 One public contract

    POST /v1/runs
    Authorization: Bearer <Clerk JWT or Omo API key>
    Idempotency-Key: <client-generated key>
    Prefer: wait=8
    Content-Type: application/json

    {
      "workflow_slug": "ugc-script-studio",
      "input": {
        "product_description": "...",
        "brand_voice": "raw",
        "length_seconds": 30
      }
    }

A fast warm LLM result may return 200. A cold start, slower LLM, remote async provider, GPU job, media job, or sandbox returns 202. Both responses refer to the same durable run_id. Immediate request defects are stable 4xx responses; execution failures are durable run resources with redacted error.code values.

The per-workflow Modal App may expose the same POST /v1/runs shape internally, but it is protected and receives additional signed server fields. There are no buyer-visible per-listing URLs.

## 2. Division of responsibility

| Plane | Owns | Must not own |
|---|---|---|
| **Cloudflare Worker** | Public POST/GET API; Clerk/API-key verification; tenant authorization; CORS; rate and abuse limits; immutable release lookup; input validation; request hashing; 10-minute quotes; idempotency conflict detection; atomic create/reserve/outbox; private Modal dispatch; bounded wait; provider-webhook verification and relay; owner-only result reads | Workflow DAG execution; LLM/HeyGen/GPU steps; buyer-selected prompts/models/prices; long provider polling; arbitrary release selection |
| **Modal** | Every workflow step; per-listing protected App; task/queue semantics; step retries within the accepted budget; hosted LLM and remote-provider clients; provider acknowledgement; native binaries; media checks; GPU/model residency; restricted sandboxes; execution telemetry; signed D1 checkpoints; exact-object R2 I/O | Buyer authentication; balances or price selection; public checkout; unrestricted tenant data; general D1/R2 credentials; release promotion; durable order history by itself |
| **D1** | System of record for tenants, API-key hashes, immutable releases, traffic pointers, accepted quotes, runs, state versions, outbox, run events, provider jobs/events, reservations, ledger effects, artifact metadata, reconciliation and QA evidence | Artifact bytes; secrets; arbitrary generated code; reliance on a transient Modal result as the only history |
| **R2** | Private input/output artifacts, exact run-scoped keys, checksums, byte and media metadata, retention state, owner-authorized delivery | Buyer identity decisions; pricing; execution state; provider URLs as permanent results |
| **Autopilot** | Immutable release controller: evidence ingestion, constrained spec drafting, deterministic compilation from reviewed templates, staging deploy, QA, approval evidence, traffic promotion, pause/quarantine/rollback within recorded authority | Arbitrary Python/Docker/package generation; self-approval of a new provider, package, GPU, secret, egress host, model, rights claim, spend increase, or production authority |

Cloudflare Workflows, if used, is a replaceable bridge for dispatch-outbox retries or callback wake-ups. Removing it must not change a workflow's DAG, business state, quote, ledger, or artifact model.

## 3. Per-workflow deployment is the core engine

The catalog objects in [site/ig-workflows.js](../../site/ig-workflows.js) and [site/ig-more.js](../../site/ig-more.js) already carry workflow.steps arrays. They are useful source material, but their api values are mostly accounting tags, not executable adapter contracts: they lack stable step IDs, typed bindings, provider operations, retry/idempotency behavior, final projections, and strict input/output schemas. The compiler must enrich and validate them; it must not execute them directly.

Every listing gets this release path:

    source snapshot / SKILL.md / catalog listing
                ↓
    canonical container.yaml + provenance + capability manifest
                ↓ deterministic, fail-closed compiler
    generated modal_app.py + prompts + schemas + tests + resolved lock
                ↓
    modal deploy to staging as <slug>-<release_hash>
                ↓
    real HTTP, security, replay, cost, artifact and quality QA
                ↓ human approval where required
    immutable release registry + atomic traffic pointer
                ↓
    live, with previous healthy release retained for rollback

### 3.1 What “one App per workflow” means

- One logical listing release maps to one independently deployable Modal App. The deployment identity includes the release hash; a live artifact is never overwritten in place.
- Apps use one versioned shared runtime package and a small number of reviewed base images. Per-workflow prompts, schemas, specs, and adapter wiring are immutable additions. Shared image layers reduce build/image-pull cost even though warm containers are not shared across Apps.
- Pure-LLM Apps remain CPU-only. Remote API orchestration never receives a GPU merely because Modal is the platform.
- An App may contain a protected ingress Function plus one or more background Functions or Classes needed by that listing. Keep min_containers on only one latency-critical CPU surface; do not accidentally keep both ingress and runner pools warm.
- Provider secrets are capability-scoped to the exact Function that calls the provider. Base URLs, model IDs, timeouts, release hashes, and cost versions are immutable configuration, not mutable secret overrides.
- Deploy once and invoke many. Never run modal deploy or modal app stop in a buyer request.

### 3.2 Compiler and release-controller boundary

The approved-spec lane still produces and deploys a new immutable per-workflow Modal release. It may only combine preapproved adapters, operations, packages, images, egress hosts, secret names, data classes, artifact types, and resource ceilings through a deterministic template.

Any new or expanded provider operation, dependency, native binary, base image, model/weight, GPU class, secret, egress host, callback, retention policy, artifact type, or maximum cost enters the new-capability lane. Human security, license, rights, code, cost, and rollback review is mandatory. Unknown values are expansions and fail closed.

The release hash covers source, canonical spec, prompts, schemas, capability manifest, compiler/runtime versions, dependency lock, base-image digest, adapter versions, model/weight digests, secret binding names, resource limits, and cost-policy version. Repair creates a new candidate and release hash; it never mutates the artifact that passed QA.

## 4. Non-negotiable runtime-agnostic safety invariants

1. Identity comes only from a verified Clerk JWT or random, revocable Omo API key. Never trust client user_id.
2. The server chooses the immutable release, prompt, model, provider operation, buyer price, retry policy, resource ceiling, hard cost ceiling, and artifact destination.
3. One (tenant_id, workflow_slug, idempotency_key) binds one canonical request hash to one Omo run. Same key and different body is 409.
4. Delivery is at least once. Effects are idempotent and reconciled; the system never promises distributed exactly once.
5. Credits are reserved before any Modal invocation that can create billable compute or external provider spend.
6. Run, reservation, settlement, release/refund, provider acknowledgement, callback, artifact write, and ledger effects use unique IDs and compare-and-set transitions.
7. Every read and mutation includes tenant_id. Foreign run and artifact requests return a non-enumerating 404.
8. D1 is durable business truth. Modal call/task state is active execution evidence and may be reconstructed from D1 checkpoints; it is not the only run record.
9. A media success requires an Omo-owned R2 artifact with checksum, bytes, MIME/magic validation, decode, and release-specific quality checks. A temporary provider URL is not success.
10. Quotes are immutable for accepted runs, expire after 10 minutes before acceptance, and record release_hash, price_cents, reserve_cents, cost version, target margin, and max_cost.
11. Unknown models, providers, billing units, cost codes, bindings, capabilities, secrets, or egress hosts are compile errors. The fallbacks in [cost-model.mjs](../../site/deploy/cost-model.mjs) are not production behavior.
12. Only the versioned traffic-allocation pointer makes a release live. A successful modal deploy or QA process cannot promote itself.

The migration-backed tenants, API keys, releases, quotes, runs, outbox, events, reservations, append-only ledger, provider jobs/events, and artifacts must exist before paid execution. The unsafe /api/run path is closed before any new Modal release receives buyer traffic.

## 5. Honest cost and latency of Modal everywhere

### 5.1 CPU/container overhead

At the checked Modal base rates, a 0.25-core, 0.5-GiB container costs:

    0.25 × $0.0000131 + 0.5 × $0.00000222
    = $0.000004385 per second

| CPU-container behavior | Base Modal cost |
|---|---:|
| 1 second of cold/active overhead | $0.0000044 |
| 5 seconds of cold/active overhead | $0.0000219 |
| 8-second bounded synchronous window | $0.0000351 |
| 30 seconds waiting on a hosted LLM | $0.0001316 |
| 60 idle seconds | $0.0002631 |
| One container continuously warm for 30 days | about $11.37 |
| 15 continuously warm per-listing CPU containers | about $170.55/month |

The 1–5 second cold-start range is a planning band for the small LLM-only image, not a guaranteed SLO. Measure queue, base boot, imports, client initialization, provider time, and total time independently for every release.

This overhead is economically acceptable for UGC Script Studio under the $0.10 floor: even 30 billed CPU seconds are about $0.000132. It is still a real latency penalty versus a direct edge call, and it becomes wasteful if every low-traffic listing is kept warm.

### 5.2 Cold-start and warm-pool policy

- Use a reviewed small CPU base image for LLM/provider Apps; pin dependencies and bake prompts/schemas so startup performs no downloads.
- Default new/low-traffic listings to min_containers=0 and a measured 30–60 second scaledown window, not the checked-in universal 2 seconds.
- Set min_containers=1 only for the few listings whose measured cold-start conversion or SLO loss is worth about $11.37/month each. Never turn it on catalog-wide.
- Add Modal input concurrency, for example @modal.concurrent(max_inputs=N), for I/O-bound LLM/provider Functions only after thread/async, cancellation, client-safety, and tenant-isolation load tests. A warm concurrent container amortizes provider waits across runs.
- Use buffer containers only for demonstrated bursts. Keep GPU minimums at zero until demand and model-load economics justify warmth.
- Share base image layers and runtime code across Apps. This improves build/pull behavior, but it does not create one shared warm pool; each App's warm capacity is still billed separately.
- Honor Prefer: wait=8 at the Worker. Warm/fast runs return 200; cold or slow runs fall back to 202 without changing the API or failing the request.

### 5.3 Single-region latency

Every run adds Worker → selected Modal region → provider/R2 network latency. A globally distributed Worker does not remove the single execution-region hop. Select each release's Modal region near the dominant buyer cohort and, for remote API workflows, near the provider endpoint; record it in the immutable release and benchmark it rather than letting it drift.

If a selected-region premium is used, the checked planning multiplier is 1.5–1.75× base. Add that premium to C_static and actual metering. Only introduce multiple regional release variants after traffic and provider-latency data justify the operational duplication. The async 202 path is the mitigation for users far from the chosen region; it is not a claim that the latency disappears.

### 5.4 Correct GPU table

The generic $0.05 per 30 seconds modal_gpu_30s bucket is wrong because it names neither a GPU nor a complete resource shape. The checked raw GPU-only range is **$0.00492–$0.05916 per 30 seconds from T4 through B300**, before CPU, RAM, load/init, storage, warm idle, failed outputs, region, or non-preemptible premiums.

| GPU | Base USD/second | Raw 30 seconds | 5× raw 30 seconds |
|---|---:|---:|---:|
| T4 | $0.000164 | $0.00492 | $0.02460 |
| L4 | $0.000222 | $0.00666 | $0.03330 |
| A10 | $0.000306 | $0.00918 | $0.04590 |
| L40S | $0.000542 | $0.01626 | $0.08130 |
| A100 40 GB | $0.000583 | $0.01749 | $0.08745 |
| A100 80 GB | $0.000694 | $0.02082 | $0.10410 |
| RTX PRO 6000 | $0.000842 | $0.02526 | $0.12630 |
| H100 | $0.001097 | $0.03291 | $0.16455 |
| H200 | $0.001261 | $0.03783 | $0.18915 |
| B200 | $0.001736 | $0.05208 | $0.26040 |
| B300 | $0.001972 | $0.05916 | $0.29580 |

For the illustrative A10 + 2 physical cores + 16 GiB shape used in Rounds 3–4:

    rate = $0.000306
         + 2 × $0.0000131
         + 16 × $0.00000222
         = $0.00036772 per second

| Billed load + execution + allocated idle | Base compute COGS | Minimum 80%-target price, rounded up |
|---:|---:|---:|
| 30s | $0.01103 | $0.10 floor |
| 60s | $0.02206 | $0.12 |
| 120s | $0.04413 | $0.23 |
| 180s | $0.06619 | $0.34 |
| 300s | $0.11032 | $0.56 |

These are lower bounds, not a price for Shipment #3.

## 6. Final guarded cost model

For each immutable release:

1. C_static is the conservative bounded cost of the selected model/provider, Modal resources including cold/init and allocated idle, R2/Cloudflare, allowed retries, and worst approved input.
2. C_success_p95 is the recent p95 actual cost of successful attempts.
3. C_delivered is total variable cohort cost divided by completed, retained, chargeable deliverables. It includes paid failures, retries, duplicate incidents, refunds, payment-fee allocation, promo/fraud loss, rejected-output yield, and variable support.

    C_guard = max(
      C_static,
      C_success_p95,
      max(C_delivered_7d, C_delivered_30d) × (1 + tail_reserve)
    )

    buyer_price = ceil_to_cent(
      max($0.10, C_guard / (1 - 0.80))
    )

Use a 10% tail reserve for mature LLM releases, 15% for remote media, and 20% for GPU until 30 clean days. There is no catalog-wide future 1.25× switch. A 1.25× multiplier is only a 20% margin before omissions.

Every accepted quote has a 10-minute TTL and stores quote_id, release_hash, price_cents, reserve_cents, estimated_cost_nanos, max_cost_nanos, cost_version, target_margin_bps, and expires_at. Retries share one max_cost ceiling. Crossing it stops new spend and sends the run to reconciliation.

### 6.1 Shipment economics

| Workflow | Static/guarded basis | Buyer price | Guard margin | Hard acceptance rule |
|---|---:|---:|---:|---|
| **Shipment #1 — UGC Script Studio in Modal** | LLM estimate up to about $0.000462 plus small Modal CPU; C_static rounded conservatively to **$0.001** | **$0.10** | **99.0%** on guard | max_cost=$0.002; one bounded LLM call; no silent model switch; actual tokens and Modal phase time recorded |
| **Shipment #2 — HeyGen 15s beta in Modal** | Repository nominal $0.12045; short submit/resume Modal tasks keep compute near fractions of a cent; 15% media tail rounds C_guard to **$0.14** | **$0.70 provisional** | **80.0%** on guard | max_cost=$0.14; no second charged render; purchased credits; pause/reprice from invoice data |
| **Shipment #3 — real GPU product image** | Actual GPU/CPU/RAM seconds, model load, R2, accepted-output yield, failures and 20% tail | Formula only after offline benchmark | 80% target | No public price, deployment, or quality claim from the current mock |

The $0.70 HeyGen quote assumes event-driven or short rescheduled Modal continuation. If the implementation instead holds a 0.25-core/0.5-GiB container for 15 minutes, base CPU/memory adds about $0.00395 per attempt and the guarded price must rise; a sleeping runner is therefore cut from production.

## 7. Revised 12-step build order and acceptance gates

The core difference from Round 4 is that the container-agent/release pipeline moves ahead of Shipment #1 and applies to every listing. UGC Script Studio must prove Modal, not bypass it. Cloudflare Workflows is removed as the workflow engine.

| Step | Build | Acceptance gate before proceeding |
|---:|---|---|
| **1** | **Close the unsafe path.** Disable paid behavior on /api/run; remove client authority over user_id, system prompt, model, token cap, price, release and provider IDs; restrict CORS and arbitrary lazy grants. | Unauthenticated/tampered requests cannot reserve credits, call Modal, call a provider, create a paid account, or read another tenant. |
| **2** | **Install numbered D1 migrations first.** Add tenants, random hashed API keys, immutable releases/traffic allocations, quotes, runs/state versions, dispatch outbox, events, provider jobs/events, artifacts, reservations, purchased/promo buckets and append-only ledger effects. | Clean migration and upgrade-from-current-schema tests pass; create/reserve is atomic; cached balances reconcile exactly; illegal transitions update zero rows. |
| **3** | **Build the thin public gateway.** Implement POST /v1/runs and GET /v1/runs/{run_id}, Clerk/API-key auth, server release selection, canonical validation/hash, rate limits, 10-minute quotes, idempotency, reservation, bounded wait and owner-only reads. | 100 concurrent same-key/same-body calls produce one run/reservation/outbox item; changed body is 409; cross-tenant matrix is non-enumerating; shown/reserved/charged quote fields match. |
| **4** | **Freeze the canonical container spec and registries.** Normalize provider names, stable step IDs, DAG/bindings, schemas, final projection, adapter operation, secret/egress capabilities, resources, retries, artifact rules and physical cost units. Convert catalog workflow.steps only as evidence. | Every checked-in container.yaml validates or produces an explicit migration error; unknown model/API/cost/binding fails closed; the current vocabulary drift cannot compile silently. |
| **5** | **Build the deterministic per-listing Modal compiler/runtime.** Generate modal_app.py from reviewed templates, shared runtime/base images, strict Pydantic or explicit JSON bodies, explicit provider timeouts/retry ownership, protected ingress, run capability verification and actual usage events. | Two clean compiles are reproducible; resolved lock/SBOM/license/security gates pass; a real JSON ASGI request works; no generated arbitrary shell/package/code path exists. |
| **6** | **Build the immutable release controller.** Stage modal deploy under slug + release hash, record endpoint/deployment/image/spec hashes, run QA, require approval, and atomically move the D1 traffic pointer. Retain a healthy rollback target. | Deploy success alone cannot route traffic; changed prompt/model/secret binding/limit/price creates a new hash; rollback and quarantine drills restore the exact prior release. |
| **7** | **Build Modal ↔ D1/R2 execution plumbing.** Signed dispatch envelope, outbox replay, idempotent run claim, internal call-ID storage, signed checkpoints, exact R2 capabilities, provider callback inbox/resume, stale-run sweeper and settlement/release reconciliation. | Crash injection after reservation, dispatch, provider send/ack, R2 write, validation and settlement produces no duplicate paid effect, double ledger effect, foreign artifact or orphan terminal run. |
| **8** | **Prove platform failure safety and latency.** Real Worker-to-Modal HTTP tests, Proxy Token failures, capability replay/expiry, 100-way execution replay, 429/5xx/timeouts, cold/warm traces, concurrency/cancellation, cost ceilings and secret-canary inspection. | At-least-once delivery converges to one effect; cold or slow Prefer: wait=8 returns a durable 202; warm completion can return 200; logs/responses contain no secret/provider body. |
| **9** | **Ship #1: UGC Script Studio as a pure-LLM Modal App at $0.10.** It uses the final compiler, deployment, gateway, reservation, execution, checkpoint and settlement path. | Strict typed output and claim grounding pass; same key causes one Modal task and one LLM call; actual tokens and Modal cost phases are stored; max_cost=$0.002; scale-to-zero and selected keep-warm policy meet measured SLO. |
| **10** | **Build and ship #2: HeyGen 15s invite beta at $0.70 provisional.** Upgrade [containers/ugc-heygen](../../containers/ugc-heygen) to one real v3 operation, curated server-side avatar/voice enums, provider idempotency, callback/rescheduled continuation, R2 copy, media/claim QA and first-20 human review. | One render under replay; missing callback reconciles without a second render; owned MP4 decodes, has audio, is 9:16 and approximately 15s; purchased credits, $0.14 ceiling, run/dollar/concurrency caps and kill switch work. |
| **11** | **Benchmark Shipment #3 offline.** Replace the premise of [containers/gpt-image-seedance-ad](../../containers/gpt-image-seedance-ad) with a licensed pinned local model and real pixels; measure cold/warm load, model init, variants/batching, GPU/CPU/RAM seconds, OOM/preemption, R2 upload, fidelity, safety and accepted-output yield. | No mock domain; reproducible licensed weights; real images pass decode/dimensions/product-fidelity/safety gates; p50/p95 and C_static/C_delivered support an 80% quote within a buyer-acceptable SLO. |
| **12** | **Ship #3, then expand every listing through the same engine.** Deploy the model-specific App only after Step 11; compile workflow #4 onward from the catalog through immutable per-listing Modal releases. | The GPU release respects queue/cost limits and rollback. Automated promotion remains disabled until one manual LLM, remote-provider and GPU release each has 30 clean days, successful rollback/quarantine drills and zero unresolved billing reconciliation. |

## 8. Release-specific gates

### Shipment #1 — UGC Script Studio

- The Modal App is part of the paid path; a direct Worker-to-LLM shortcut is prohibited.
- One valid request creates a D1 run and reservation before the protected Modal call.
- A real JSON request is accepted. The body: Any transport defect in the checked-in Apps is not carried into the template.
- Same key/body creates one run, one Modal task, one provider request and one settlement under concurrent replay.
- Prefer: wait=8 returns 200 only after D1 records the terminal result; otherwise it returns 202.
- Provider timeout, malformed output or cost ceiling releases the reservation exactly once.
- Actual token usage, provider request ID, queue/cold/init/execution/provider timing, Modal resource shape, release hash and cost version are recorded.

### Shipment #2 — HeyGen 15-second beta

- All Shipment #1 platform gates pass.
- Buyer inputs contain curated marketplace styles, not raw avatar_id or voice_id.
- Provider job and callback event IDs are unique and matched to one stored run.
- Callback signature, timestamp and event ID are verified before Modal resume.
- Missing/delayed/reordered callbacks reconcile without a duplicate render.
- The final MP4 is private and Omo-owned in R2; checksum, bytes, MIME, dimensions, duration and audio metadata are stored.
- ASR materially matches the approved grounded script; unsupported material claims fail publication.
- The first 20 paid artifacts receive human review; purchased credits and explicit beta spend/concurrency caps apply.

### Shipment #3 — real GPU product image

- The current A10 hash-to-fake-URL code is not deployment or benchmark evidence.
- Weights and licenses are pinned and approved; the image is reproducible.
- Cold/warm queue, boot, import, model-init, generation, validation and R2 timings are separate.
- Product fidelity, prompt adherence, decode/dimensions, safety and accepted-image yield meet the versioned rubric.
- Cost uses the selected GPU's real seconds plus CPU, RAM, idle, premiums, storage and rejected attempts.
- The public price is derived only after the accepted-output benchmark; the existing $0.22020/$1.10 mixed remote-image-plus-generic-GPU estimate is retired.

## 9. Top 10 risks and mitigations

| Rank | Risk created or amplified by this design | Mitigation and tripwire |
|---:|---|---|
| 1 | **Client authority or cross-tenant access** | Auth-derived tenant, server release/quote, mandatory tenant predicates, foreign 404, random hashed keys and full tenant matrix. One confirmed leak quarantines affected releases and gateway traffic. |
| 2 | **Duplicate Modal task or paid provider mutation under replay** | Tenant idempotency + request hash, D1 outbox, Modal run claim, run-derived provider key, unique job/event/effect IDs and stale-run reconciliation. Duplicate paid jobs auto-pause the adapter. |
| 3 | **Ledger drift across Worker, Modal and provider crash boundaries** | Reserve before dispatch, append-only ledger, CAS transitions, signed checkpoints, idempotent settle/release and crash injection at every boundary. Any mismatch blocks automated settlement and promotion. |
| 4 | **Per-workflow App sprawl and security/config drift** | One compiler/runtime/base-image family, immutable release hashes, generated code only, shared patches, deployment inventory/retirement and quotas. Fifteen Apps are manageable; app/version counts are monitored before Modal plan limits. |
| 5 | **Cold-start and single-region latency harms conversion** | Small images, no startup downloads, selective min_containers, I/O concurrency, 30–60s measured window, region near cohort/provider, latency phase telemetry and Prefer: wait=8 → 202 fallback. |
| 6 | **Long remote-provider waits consume containers or exhaust queues** | Submit/checkpoint/end, verified webhook or short rescheduled Modal status tasks, provider semaphore, maximum queue age and no production sleeping poller. Fallback polling cost triggers repricing. |
| 7 | **Cost drift, GPU mispricing or retry explosion** | Physical CPU/RAM/GPU metering, corrected GPU table, C_static/C_success_p95/C_delivered, 10–20% tail reserve, upward rounding, hard run/canary/provider/workspace caps and invoice reconciliation. Breach pauses before retry. |
| 8 | **Secret/egress blast radius across many Apps** | Capability-specific versioned Modal Secrets, immutable provider hosts/models, exact-object R2 capabilities, no D1 general credential, no secret values in specs/logs and overlap rotation. One secret canary leak quarantines the image family. |
| 9 | **Modal outage, capacity limit or vendor concentration stops every workflow** | D1 outbox retains reserved work, bounded queue TTL and refunds, environment/workspace budgets, provider/GPU admission below infrastructure ceilings, health-based pause, documented restore/redeploy from immutable releases and no buyer exposure to Modal IDs. |
| 10 | **Autopilot turns untrusted sources into code, rights violations or bad outputs** | Evidence-only ingestion, human rights gate, canonical schema, deterministic templates, capability diff, locks/SBOM/license scans, isolated staging, hard QA, separate evaluator and human approval for every new capability. Automation may pause/rollback, never expand authority. |

## 10. What to cut

Cut these from the target architecture:

1. Cloudflare Workflows as the primary workflow engine, and direct Worker calls to hosted LLM, HeyGen, Replicate, ElevenLabs, or other workflow providers.
2. Round 4's shared execution-pool topology as the listing runtime. Base layers and runtime code remain shared, but each listing release gets its own Modal App.
3. The spec-only “publish data without deploying code” lane. Approved specs still compile and deploy an immutable per-listing Modal release.
4. Buyer-visible Modal endpoints, Proxy Tokens, FunctionCall IDs, provider IDs, raw error bodies, or artifact destinations.
5. Client-supplied user_id, prompt, model, max tokens, release, price, provider operation/ID, retry/resource limit, or R2 key.
6. Handwritten/ad hoc modal_app.py forks and agent-generated arbitrary Python, Dockerfiles, packages, install hooks, shell or executable binding expressions.
7. Sleeping 15-minute provider polling containers. Use short Modal tasks plus callback/rescheduled continuation.
8. The fake GPU URL generator and any launch claim or price derived from it.
9. Generic/fallback cost codes, the $0.05/30s GPU bucket, mixed local-plus-remote image charges, nearest-cent margin rounding and a scheduled global 1.25× markup.
10. Catalog-wide min_containers=1, a universal two-second scaledown window, or warming both ingress and runner for every workflow.
11. Per-user Modal Apps/Secrets and buyer-provided provider keys in v1.
12. Autonomous approval of rights, new capabilities, paid-test escalation, production promotion, spend increases, or recovery from a correctness/security quarantine.
13. Public SEO “audit” or “replaces an agency” claims from [containers/claude-seo-skill](../../containers/claude-seo-skill) while it cannot crawl the site.
14. Distributed exactly-once claims. The guarantee is at-least-once delivery, one durable Omo run, idempotent effects and reconciliation.

## 11. Concrete file-level direction

| Existing or planned area | Round 5 direction |
|---|---|
| [site/deploy/worker.js](../../site/deploy/worker.js) | Become the thin authenticated gateway; close /api/run; add public POST/GET /v1/runs, private Modal event/callback routes, restrictive CORS, stable errors and no workflow-provider adapters |
| [site/deploy/schema.sql](../../site/deploy/schema.sql) | Retain only for local bootstrap if useful; production uses numbered migrations for tenants, releases, quotes, runs/outbox/events, provider events, artifacts, reservations and append-only ledger |
| [site/deploy/cost-model.mjs](../../site/deploy/cost-model.mjs) | Remove fallbacks, global MARKUP policy and modal_gpu_30s; add versioned physical rates, upward cents, 10-minute quotes, hard ceilings and guarded/delivered cost |
| [site/ig-workflows.js](../../site/ig-workflows.js) and [site/ig-more.js](../../site/ig-more.js) | Treat workflow.steps as catalog evidence. Compile each listing into stable IDs, bindings, schemas, operations, capabilities and a per-workflow Modal release |
| [containers/ugc-heygen](../../containers/ugc-heygen) | Evolve to immutable v0.2 production candidate: real HeyGen adapter inside Modal, curated IDs, no sleeping poller, D1 checkpoints, R2 artifact and $0.70 provisional quote |
| [containers/gpt-image-seedance-ad](../../containers/gpt-image-seedance-ad) | Offline only until a real licensed model produces pixels and an accepted-output benchmark replaces the mock and mixed cost model |
| [containers/claude-seo-skill](../../containers/claude-seo-skill) | Keep as a private contract fixture or honestly rename/reposition; fix real HTTP JSON handling before using its runtime pattern |
| New autopilot compiler/release controller | Canonical container-spec schema, provenance/capability manifest, deterministic Modal templates, immutable release state machine, signed QA, manual capability/canary gates and automatic safe pause/rollback |

## Final execution standard

The reconciled milestone is:

**An authenticated buyer submits one POST /v1/runs request; the Worker reserves a server-authored quote; the selected immutable per-workflow Modal container executes every step; D1 and R2 preserve ownership, money, state and artifacts; and retries converge without duplicate spend.**

Shipment #1 proves that complete path with UGC Script Studio at $0.10, including Modal's real cold/warm behavior. Shipment #2 adds remote asynchronous media through the same Modal engine at $0.70 provisional. Shipment #3 adds a real GPU model only after offline accepted-output evidence. From then on, the autopilot scales the catalog by producing reviewed immutable Modal releases, not by acquiring arbitrary code-generation authority.

## Source basis

This decision reconciles [Round 4](round-4.md) with the original [Modal container plan](../modal-container-plan.md), while retaining the safety and economic refinements from [Round 1](round-1.md), [Round 2](round-2.md), and [Round 3](round-3.md). Cost figures use the checked 2026-08-10 Modal rates recorded in Rounds 3–4. Provider interfaces, account pricing, region premiums and Modal plan limits remain release-time inputs and must be revalidated against the actual account before paid promotion.
