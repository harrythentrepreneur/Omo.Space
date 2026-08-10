# Modal hosting optimization — Round 2 adversarial refinement

**Date:** 2026-08-10

**Scope:** adversarial review of [`modal-container-plan.md`](../modal-container-plan.md), Round 1, all three checked-in container prototypes, [`cost-model.mjs`](../../site/deploy/cost-model.mjs), [`worker.js`](../../site/deploy/worker.js), [`schema.sql`](../../site/deploy/schema.sql), and [`go-live.sh`](../../scripts/go-live.sh).

**Refined decision:** overturn “HeyGen is the first paid production workflow.” Launch an honest pure-LLM **UGC Script Studio** first through the final authenticated run/ledger contract; launch a constrained 15-second HeyGen workflow second as a capped beta; do not deploy the GPU mock. Use Modal as an elastic compute plane, not as the durable orchestrator for remote APIs.

## Executive verdict

Round 1 correctly identified the immediate security, billing, transport, and durability blockers. Its most important findings stand: the Worker is client-authoritative and unauthenticated, D1 is not a run ledger, normal JSON requests fail at the current FastAPI surfaces, HeyGen is disabled, the GPU output is fake, prices have drifted, and production cannot rely on Modal `FunctionCall` retention.

Round 1 nevertheless preserves too much of the base plan's framing. The base plan chooses the first workflow according to how many infrastructure concepts it exercises. A $100k-MRR marketplace should choose the first public workflow according to the shortest safe loop to a valuable, supportable buyer outcome. Architecture coverage belongs in staged integration tests, not in the blast radius of the first paid release.

The largest missed optimization is architectural: DeepSeek and HeyGen are remote APIs. A Modal CPU container adds another deployment, cold start, secret copy, execution handle, failure domain, and billable wait without providing compute. Cloudflare already owns identity, money, durable records, public callbacks, and R2. Cloudflare Workflows can durably execute steps and wait for provider events without charging CPU while idle; Modal should be invoked only for work that benefits from a container, such as real GPU inference, media validation/transcoding that exceeds the edge runtime, or sandboxed third-party code. Cloudflare documents durable steps and `waitForEvent`, and says waiting Workflows do not consume CPU time ([overview](https://developers.cloudflare.com/workflows/), [pricing](https://developers.cloudflare.com/workflows/reference/pricing/)).

The defensible end state is therefore:

```text
buyer
  │ Clerk JWT or random Omo API key + Idempotency-Key
  ▼
Cloudflare Worker
  authenticate → resolve immutable release → validate → quote
  atomically create run + reserve credits
  ▼
Cloudflare Workflow instance (durable orchestration)
  ├── hosted LLM / HeyGen adapters directly
  ├── wait for signed provider event without a sleeping CPU container
  └── invoke Modal only for a declared compute capability
             │
             ├── CPU media validation/transcode, if needed
             └── model-specific GPU inference
  ▼
R2 artifacts + D1 run/ledger/events → settle or release reservation
  ▼
GET /api/v1/runs/{omo_run_id}
```

If Cloudflare Workflows is rejected after a production spike/replay evaluation, use Queues plus a Durable Object or an explicitly transactional D1 state machine. Do not fall back to a 15-minute polling Modal Function.

## What Round 1 missed or got wrong

### 1. “Exactly once” is not a realizable system promise

Round 1 repeatedly asks for “exactly-once settlement semantics.” Across Worker, D1, Modal, HeyGen, callbacks, R2, and Stripe, the realistic model is **at-least-once delivery plus idempotent effects**. A process can always fail after a remote side effect but before locally recording its acknowledgement.

The invariant must be narrower and testable:

- one `(tenant_id, workflow_slug, idempotency_key)` maps to one immutable request hash and one Omo run;
- every provider mutation uses the same run-derived idempotency key when the provider supports one;
- provider job IDs and event IDs have unique constraints;
- each credit transition has a unique ledger operation ID;
- settlement/refund handlers are replay-safe state transitions;
- a reconciliation job repairs `provider_submitted` runs whose acknowledgement or callback was lost;
- a duplicate provider charge is detected, quarantined, and reconciled rather than declared impossible.

This language matters. “Exactly once” encourages unsafe assumptions around the precise crash boundary the system most needs to survive.

### 2. A webhook is not a complete production continuation design

Round 1 correctly removes the Modal polling loop, but “use a webhook” leaves several gaps:

- a callback can be delayed, duplicated, reordered, forged, or never delivered;
- signature verification does not prove the referenced provider job belongs to the Omo run;
- a provider can say `completed` before its presigned artifact is downloadable;
- copying a large media response through a Worker can exceed practical resource limits;
- a successful R2 copy can occur before D1 settlement, or vice versa;
- callback schemas and signing algorithms can version independently of the create API.

Required refinement: persist the provider job ID immediately, verify signature/timestamp/event ID, match the job to the stored run, signal a durable waiting workflow, re-read provider status server-side, copy and checksum the artifact, validate it, and only then settle. Add a periodic reconciliation scan for stale `awaiting_provider` and `artifact_copying` runs. Store raw callback bodies only if encrypted/redacted and retention-bounded.

### 3. Modal is the wrong orchestration layer for the first two production candidates

The base plan and Round 1 treat the Modal runner as the workflow engine. For pure LLM and HeyGen, it is an HTTP client that waits. That duplicates Cloudflare's role while weakening durability.

Use Modal when at least one of these is true:

- a pinned local model needs GPU/CPU/RAM unavailable at the edge;
- native binaries such as `ffmpeg` or a media model need a controlled image;
- the workload is untrusted and requires an isolated sandbox;
- batching, model residency, memory snapshots, or GPU concurrency materially reduce unit cost;
- a measured workload exceeds Worker CPU/runtime constraints.

Do not use Modal merely because a workflow contains multiple remote HTTP calls. Direct remote-provider orchestration belongs in the Cloudflare Workflow already tied to the buyer's durable run.

### 4. “One logical deployment per workflow initially” will manufacture cold starts and drift

Round 1 also says to share one runtime for 15+ workflows, but retains one logical deployment per workflow. Those goals conflict. Fifteen FastAPI deployments duplicate ingress, images, scaling knobs, secrets, logs, and patch points even if their source package is shared.

Use deployment boundaries by **execution class and trust boundary**, not storefront listing:

1. no Modal deployment for edge-safe hosted-API workflows;
2. one shared CPU media/utility deployment, if measurements justify it;
3. one deployment/class per resident GPU model or incompatible dependency set;
4. a separate sandbox class for untrusted code;
5. per-workflow immutable specs/releases in the registry, not per-workflow HTTP servers.

A new prompt/spec using existing adapters should publish data and tests; it should not build another image or create another public endpoint. New adapter code or a new GPU model is a deployment event and requires review.

### 5. Round 1's `p95 cost` pricing rule is incomplete

The p95 of successful-run cost omits the most dangerous costs: paid failures, refunded results, duplicate provider mutations, promo abuse, artifact retry, variable payment fees, and support. Pricing must use **cost per delivered and retained sale**, not only cost per successful attempt.

The current repository model has additional structural defects:

- unknown LLM models silently use the DeepSeek rate;
- unknown API tags silently cost `$0.05`;
- buyer input tokens are omitted from catalog templates;
- maximum output tokens substitute for actual usage;
- HeyGen duration does not affect cost;
- avatar and voice may double-count one physical create call, or may undercount the provider's real commercial unit;
- the image workflow charges both three remote `openai_image` calls and two local GPU buckets despite claiming local generation;
- `toFixed(2)` rounds to nearest cent and can round below the intended margin;
- one global markup cannot express workflow risk, refund rate, or sales channel economics.

At 1.25×, gross margin is only 20% before any of those omissions. There should be no scheduled global switch to 1.25×.

### 6. The blanket `min_containers=0` conclusion is too absolute

Scale-to-zero is correct for unproven GPU workloads and for execution that is not buyer-interactive. It is not a principle worth defending after revenue and latency are measured. At the current checked Modal base rates, one 0.25-core/0.5-GiB CPU container is about `$11.37/month` continuously warm. At $100k MRR, that is about 0.011% of revenue. If a shared Modal service sits on a latency-critical path and a warm container materially improves conversion or SLO compliance, `min_containers=1` can be the rational choice.

The better result here is to remove Modal from the submission path, making the Worker response independent of Modal cold starts. Then keep CPU/GPU executors at zero unless their own execution SLO and traffic justify warmth.

### 7. D1 schema expansion alone does not define legal state transitions

Adding columns to `runs` is necessary but insufficient. The application needs a transition matrix and database invariants. For example, `completed → running`, two settlements, refund-before-reservation, or a provider job attached to two runs must be impossible or rejected.

Use compare-and-set updates such as `UPDATE ... WHERE run_id=? AND status IN (...)`, unique effect IDs, and append-only events. D1 databases process queries serially, but that does not make separate Worker calls transactional ([D1 limits](https://developers.cloudflare.com/d1/platform/limits/)). `reserveRunCredits`, provider submission, `addRun`, and refund in the current Worker remain separate crash boundaries.

### 8. The current contract validation is less strict than claimed

All three Python apps call `Draft202012Validator(...).validate(...)` without a `FormatChecker`; JSON Schema `format: uri` is therefore annotation-only in these tests. The UGC schema does not truly validate media URLs. The image schema's `^https://` pattern checks the scheme, not reachability, content type, bytes, dimensions, or ownership.

The LLM parsers also deliberately accept prose before/after the first valid JSON object. That may be operationally useful, but it is not “return exactly JSON.” Track repair/noncompliance as a quality metric, and never let recovered trailing content influence another tool step.

### 9. Secret scope is still too broad and configuration can bypass policy

`containers/ugc-heygen/container.yaml` declares `HEYGEN_API_KEY` for a canary that cannot call HeyGen. `gpt-image-seedance-ad.generate_images_gpu` receives the shared provider Secret despite needing neither LLM nor image-provider credentials. `LLM_BASE_URL` is dynamically configurable while `egress_allowlist` is unenforced. A mutable base URL in a broad Secret defeats the claim that provider egress is allowlisted.

Use capability-scoped secret references per adapter/function. Keep base URLs, model IDs, and provider API versions in reviewed immutable release configuration. Store only credentials in secrets. Do not duplicate a provider key across Cloudflare and Modal: the platform that makes the call owns the key. Give Modal an R2 credential limited to the required bucket/prefix and operation, not a general account token.

### 10. The go-live path is not a migration or release system

`scripts/go-live.sh` only deploys the Worker. It does not deploy/smoke a Modal release, configure an R2 binding, publish a workflow registry, or test auth, idempotency, top-up settlement, callbacks, or rollback. It omits `STRIPE_WEBHOOK_SECRET`, accepts only Stripe test keys, and prints a `cognition.cv` checkout success URL while the product reality is `omo.best`.

More subtly, rerunning it generates and uploads a new `BALANCE_KEY_SECRET` each time. That is uncontrolled credential-key rotation. Existing stored deterministic keys remain, while newly provisioned/recreated identities derive under a different secret. The script also applies only `CREATE TABLE IF NOT EXISTS`; it cannot migrate an existing old `runs` table to the required production schema.

Replace this with numbered D1 migrations, stable secret provisioning/rotation procedures, a release registry migration, a pre-deploy backup/restore point, staged deployment, automated smoke checks, and an explicit promotion/rollback command. Never source a general shell `.env` as part of a production deploy if a narrow secret source can be used.

## Re-evaluating what to build first

| Candidate | Real implementation readiness | Buyer value | Proves durable marketplace path | Modal-specific value | Cost/quality uncertainty | Decision |
|---|---|---|---|---|---|---|
| Claude SEO | Highest | Low/ambiguous because it cannot crawl | Good | None | Low | Private operational canary only; fix the “audit/agency replacement” positioning |
| UGC Script Studio, pure LLM | High; prompt and normalization exist | Medium and honest | Excellent for auth, quote, reserve, idempotency, settle, telemetry | None | Lowest | **First paid production workflow** at the `$0.10` floor |
| HeyGen UGC, 15s | Provider adapter absent; async/artifacts absent | High if media quality is good | Excellent once the base path works | Almost none; remote APIs | High: invoice unit, failure charging, rights, render quality, refunds | **Second**, invite-only/capped paid beta |
| GPT-image/Seedance GPU | No model, pixels, weights, license, upload, or quality benchmark | Potentially high | Poor until real | Highest | Highest; current path is a fake URL on paid A10 | **Third**; benchmark offline before any public deployment |

The “in-between GPU container” is not actually between the others in production readiness. It is the furthest away. Running SHA-256 on an A10 proves only that Omo can buy an A10. It says nothing about model load time, image fidelity, product preservation, VRAM, throughput, storage, safety, or unit economics.

The pure-LLM first release should be UGC Script Studio rather than the checked-in SEO canary. It has a truthful, useful output and reuses the product's existing UGC prompt. It should use the final durable contract and ledger, so it is not throwaway work. It need not run on Modal; forcing it through Modal would measure the wrong architecture.

HeyGen remains the right second workflow because it establishes remote-job submission, callback continuation, artifacts, media QA, and refund handling without introducing local GPU/model risk. Limit v0.2 to one 15-second, 9:16 format and server-resolved approved avatar/voice styles. Do not assume 15 seconds is cheaper until the invoice confirms the provider billing unit.

## Refined synchronous versus asynchronous contract

Round 1's universal asynchronous resource is directionally right for durability, but a mandatory two-request client flow is poor for fast demos and LLM API consumers. Keep one resource model with bounded synchronous convenience:

```text
POST /api/v1/runs
Authorization: Bearer ...
Idempotency-Key: ...
Prefer: wait=8
{"workflow_slug":"ugc-script-studio","input":{...}}
```

- Validate auth, release, input, budget, and idempotency before any provider call.
- Create the durable Omo run and reservation for every paid request.
- Return `200` with the final run resource if it finishes inside the declared wait window.
- Return `202` with the same run resource and `status_url` otherwise.
- Long provider/GPU work returns `202` immediately regardless of `Prefer`.
- `GET /api/v1/runs/{run_id}` returns the owner-authorized durable resource; it never accepts or exposes a Modal call ID.
- Immediate request defects use `4xx`; execution failure is a durable terminal run with a stable `error.code`.
- Webhooks acknowledge only after authentication/deduplication and durable event enqueue, not after the entire artifact pipeline.

Recommended state machine:

```text
queued → reserved → running
                   ├── awaiting_provider → artifact_copying → validating → completed → settled
                   ├── failed → released_or_refunded
                   ├── cancelled → released_or_refunded
                   └── expired → reconciliation → failed | awaiting_provider | completed
```

Never call a result `completed` with `video: null`; the current UGC canary needs `mode: canary`/`status: simulated` or a separate canary response schema.

## Stricter cost and price model

### Three costs, not one constant

For each immutable release, maintain:

1. **Quote estimate** before acceptance: duration/input-aware upper estimate shown to the buyer and reserved.
2. **Accrued run cost**: actual provider usage/invoice units, Modal resource seconds, Cloudflare steps, R2/egress, and retries for that run.
3. **Delivered-sale cost**: cohort cost divided by completed, retained, chargeable outcomes; this captures paid failures, refunds, duplicates, and fraud.

For a cohort:

```text
C_delivered =
  (provider invoices
   + Modal CPU/GPU/memory/idle allocation
   + Cloudflare Workflow/Worker usage
   + R2 storage/operations/egress
   + payment-fee allocation
   + costs of refunded/failed/duplicate runs
   + promo/fraud loss
   + variable support allowance)
  / max(completed retained paid runs, 1)
```

Define a guarded cost from a static bounded scenario, recent observed unit costs, and delivered-sale cohorts:

```text
C_guard = max(static_release_budget,
              recent_p95_success_cost,
              7d_and_30d_delivered_sale_cost + tail_reserve)

price = ceil_to_cent(max(product_floor, C_guard / (1 - target_contribution_margin)))
```

Use a per-release target contribution margin, normally 70–80% during launch uncertainty. A 5× multiplier implies 80% only when the cost is complete. A 1.25× multiplier implies 20% and is unsafe for media workflows. Put a hard maximum accrued cost on each run; retries cannot exceed it.

### HeyGen sensitivity, not a false `$0.60` certainty

The repository's `$0.12045` is a hypothesis, not COGS. `$0.60` is an acceptable **beta floor pending invoice reconciliation**, not a defensible GA price.

| Scenario | Delivered variable cost before support/payment overhead | Margin at `$0.60` |
|---|---:|---:|
| Repository nominal, no paid failures | `$0.12045` | `79.9%` |
| Nominal plus one expected 5% chargeable failed attempt | about `$0.1265` | about `78.9%` |
| Actual billed unit `$0.20`, 10% failed/retried spend | `$0.22` | `63.3%` |
| Actual billed unit `$0.30`, no reserve | `$0.30` | `50.0%` |

These are sensitivity cases, not provider-price claims. Record actual invoice units and failure-charge policy before promotion. If `C_guard=$0.22`, an 80% target implies `$1.10`; a 70% target implies `$0.74`, rounded upward. The registry, checkout, reservation, and response must all use the same versioned quote.

### Cloudflare orchestration cost is not the decision driver

Cloudflare's current paid allowance includes 500,000 Workflow steps/month, then lists `$0.80` per additional 100,000; waiting consumes no CPU ([pricing](https://developers.cloudflare.com/workflows/reference/pricing/)). Illustratively, 100,000 five-step runs use the included 500,000 steps; one million five-step runs would add about `$36/month` in step charges before storage/other usage. The exact step count and current contract must be measured, but this is orders of magnitude below the provider and support risk. Durability, replay behavior, and operational fit should drive the choice.

### GPU cost must include boot, init, inference, and premium multipliers

Modal currently lists A10 at `$0.000306/s`, CPU at `$0.0000131/core/s`, and memory at `$0.00000222/GiB/s`; region selection is listed at 1.5–1.75× base pricing and non-preemptible execution at 3× ([Modal pricing](https://modal.com/pricing)). For A10 alone:

| A10 seconds billed | Base GPU cost |
|---:|---:|
| 20 | `$0.00612` |
| 60 | `$0.01836` |
| 120 | `$0.03672` |
| 300 | `$0.09180` |

The checked-in `$0.05 per 30s` bucket is therefore neither a measured cost nor a stable proxy. Measure separately: queue time, container boot, dependency import, weights-to-memory initialization, generation per variant, validation/upload, warm idle, GPU type, region, and preemption mode. Three variants must say whether they batch, run serially, or use separate calls. Price from metered seconds and delivered images, not `qty: 2`.

## A cold-start model that can make a decision

`scaledown_window=2` versus `60` cannot be chosen from intuition. Under a simple one-container Poisson arrival approximation with request rate `λ` and idle window `T`:

```text
P(cold next request) = exp(-λT)
expected idle seconds charged per request = (1 - exp(-λT)) / λ
expected added latency = P(cold) × (queue + boot + init)
```

For the current 0.25-core/0.5-GiB CPU shape, the base resource rate is about `$0.000004385/s`:

| Mean interarrival | Window | Approx. cold probability | Idle seconds/request | Idle cost/request |
|---:|---:|---:|---:|---:|
| 10 minutes | 2s | 99.67% | 2.0 | `$0.0000088` |
| 10 minutes | 60s | 90.48% | 57.1 | `$0.000250` |
| 10 minutes | 300s | 60.65% | 236.1 | `$0.001035` |
| 1 minute | 2s | 96.72% | 2.0 | `$0.0000086` |
| 1 minute | 60s | 36.79% | 37.9 | `$0.000166` |
| 1 minute | 300s | 0.67% | 59.6 | `$0.000261` |

This is a planning approximation; concurrency, burstiness, autoscaler behavior, and multiple warm containers require trace replay. It demonstrates why separate low-traffic workflow apps remain cold almost all the time and why a shared execution-class pool has better economics.

Policy:

- Submission/control path: no Modal dependency; Worker p95 is measured separately.
- Hosted-API workflows: no Modal cold start.
- Shared CPU utility runtime: start `min_containers=0`, `scaledown_window=60`; switch to one warm container only if measured cold penalty violates the SLO and revenue supports it.
- GPU: `min_containers=0`, `scaledown_window=2` initially. Increase the window only from observed interarrival traces; idle A10 seconds are much more expensive.
- Use `buffer_containers` only for demonstrated correlated bursts, not as a default. Modal explicitly describes it as active-period overprovisioning ([cold-start guide](https://modal.com/docs/guide/cold-start)).
- For I/O-bound Modal utilities, add input concurrency only after thread-safety/async load tests. Modal notes that synchronous concurrent inputs use threads and a cancellation can terminate the whole container ([input concurrency](https://modal.com/docs/guide/concurrent-inputs)).
- Record `queue_ms`, `boot_init_ms`, `execution_ms`, provider wait, artifact time, and total time by release. Do not collapse them into one p95.
- Capacity limits are global per provider/compute class. `max_containers=10` in 15 independent apps is not a provider quota.

At `$100k MRR`, average workload is not automatically large: `$1` average usage revenue is roughly 100,000 runs/month (about 0.04/s average); `$0.10` is one million runs/month (about 0.39/s). Design for burst and provider quotas, but do not pre-optimize for hundreds of steady containers.

## Secret and security refinements

- **Worker only:** Clerk verification material, Stripe secrets, provider webhook verification secrets, Omo API-key hashes, and Modal invocation credential if an HTTP bridge remains.
- **Cloudflare Workflow only:** hosted LLM and HeyGen keys when it directly calls those providers.
- **Modal function/class only:** the credentials its exact compute capability requires, such as a prefix-limited R2 writer; never attach the full provider bundle.
- **Release config, not Secret:** provider base URL, API version, model ID, region, prompt/spec hash, schema hash, timeouts, and cost-table version.
- **No public Modal endpoint where direct invocation suffices.** If HTTP is retained, use environment-specific Proxy Tokens, rotate with overlap, and never expose the endpoint/call ID to buyers.
- **No raw provider bodies in responses.** `worker.js::callLLM` currently returns the first 200 characters of an upstream error; replace it with a redacted internal trace and stable code.
- **Explicit timeouts and retry ownership.** `callLLM` in the Worker has no abort timeout; Python OpenAI clients have no release-aligned timeout/retry configuration. Only the durable orchestrator owns step retries. Modal's deployed functions can reschedule work after container crashes, so paid mutations must remain idempotent even when application retries are zero ([Modal retries](https://modal.com/docs/guide/retries/)).
- **Enforced egress:** a YAML `egress_allowlist` is documentation until network/runtime policy enforces it. Adapter code must pin host and path; untrusted sandbox workloads need an actual restricted proxy/network policy.
- **Supply chain:** exact top-level pins are not a lock. Produce a resolved lock, hashes/SBOM, license/vulnerability results, base-image digest, and signed build provenance.
- **API keys:** generate random high-entropy values once, store only a hash plus prefix/metadata, support revoke/rotate/last-used. Delete deterministic `apiKeyFor` behavior.

## Autopilot refinements for 21 workflows

The original pipeline—discover a reel/repository, extract, generate container spec, deploy, quality-test, live—still grants an agent too much semantic authority. Split it into two tracks:

### Spec-only publication path

For a workflow using already approved adapters and execution classes:

1. ingest evidence and rights metadata;
2. create a draft immutable spec and provenance map;
3. validate against the one canonical schema;
4. compile bindings/cost/contract deterministically;
5. run offline, mock, and limited real-provider tests;
6. publish a staged registry release without deploying code;
7. canary a traffic percentage with spend and failure limits;
8. promote or quarantine.

### New-capability path

Any new provider operation, package, native binary, model weight, GPU class, egress host, or secret capability requires human code/security/license review, a new runtime deployment, and an explicit adapter version. The agent cannot self-approve it.

Every release record should include:

- input/output/envelope schema hashes;
- prompt and adapter versions;
- provider operation/API version and retry/idempotency behavior;
- secret capabilities and enforced egress destinations;
- data classification, retention, deletion, and artifact TTL;
- static and measured cost budgets;
- content/rights policy and human approval evidence;
- cold/warm latency profile and concurrency class;
- QA report, canary percentage, rollback target, and kill-switch state.

Do not let the repair loop change schema, model, provider, price, safety rules, or secret/egress capabilities. It may propose prompt/binding changes for review. Full paid QA must be deduplicated by release hash and capped in dollars, not merely attempt count.

Before autonomous promotion, require at least three manually operated real workflows spanning pure LLM, remote async provider, and Modal GPU; 30 days of run/failure/cost telemetry; successful rollback/quarantine drills; and zero unresolved billing reconciliation items. The number is a release gate proposal, not a claim that three workflows prove all adapters.

## Concrete file-level deltas

### [`site/deploy/worker.js`](../../site/deploy/worker.js)

- Delete or make internal `handleGenericRun`; never accept `system_prompt`, `max_tokens`, model, price, release, or `user_id` as authority.
- Add `POST /api/v1/runs`, `GET /api/v1/runs/:id`, and a server-owned release registry lookup.
- Verify Clerk JWT/Omo API key before lazy provisioning or balance access. `/api/me` derives identity and never returns a reusable secret after creation.
- Require `Idempotency-Key` for paid calls; canonicalize and hash the input after schema validation.
- Atomically create/reserve a run, start a Cloudflare Workflow instance keyed by `run_id`, and support bounded `Prefer: wait`.
- Separate `/api/v1/provider-webhooks/heygen` from `/api/topup`; verify/deduplicate then signal the waiting workflow.
- Resolve checkout product/price and top-up user server-side. Fix checkout URLs/domain and make webhook fulfillment independent of browser redirects.
- Remove raw LLM output/provider error text from buyer responses; add `AbortController` deadlines, stable error codes, trace IDs, and structured redacted logs.
- Restrict CORS to Omo origins and required headers. Add authenticated per-user and global provider admission limits; an optional unbound KV cannot be the safety boundary.
- Keep free demos on a separate, severely bounded path with no signup balance creation.

### [`site/deploy/schema.sql`](../../site/deploy/schema.sql)

Replace one bootstrap file as the production mechanism with numbered migrations. Add:

- `workflow_releases` with immutable spec/schema/prompt/adapter/cost hashes and status;
- `runs` with owner, request hash, idempotency key, release, explicit status, quote/reservation/settlement, workflow instance, provider job, error, and timestamps;
- unique `(user_id, workflow_slug, idempotency_key)`, provider job ID, and workflow instance ID constraints;
- append-only `run_events` and `credit_ledger` with unique effect/idempotency IDs;
- separate purchased and promotional credit buckets plus expiration/restriction metadata;
- `provider_events` for callback deduplication and reconciliation;
- `artifacts` with R2 key, checksum, bytes, media metadata, validation state, retention, and ownership;
- integer cents for buyer money and integer micro-USD (or finer documented unit) for provider cost;
- state/age/provider indexes for callbacks, reconciliation, support, and quarantine.

Define legal state transitions in code and tests. A cached balance must reconcile exactly to the append-only ledger.

### [`site/deploy/cost-model.mjs`](../../site/deploy/cost-model.mjs)

- Make unknown models, providers, cost codes, currencies, and billing units compile errors.
- Replace global `MARKUP` with per-release `target_margin_bps`, product floor, channel policy, quote TTL, and hard cost ceiling.
- Make provider billing duration/quality/quantity aware and distinguish physical calls from accounting tags.
- Return integer quote fields: `price_cents`, `reserve_cents`, `estimated_cost_microusd`, `max_cost_microusd`, `cost_version`, `expires_at`.
- Round prices upward, never nearest, when enforcing margin.
- Record actual usage and cohort delivered cost; alert/quarantine on cost-table variance.
- Remove `openai_image` charges from a local-only GPU release and remove generic `modal_gpu_30s` once measured resource formulas exist.
- Preserve 5× only as a launch default for complete cost; never automatically dial all workflows to 1.25×.

### [`scripts/go-live.sh`](../../scripts/go-live.sh)

- Stop generating a new credential derivation secret on every deploy; move to random hashed API keys and explicit rotation.
- Use D1 migrations, not `CREATE IF NOT EXISTS` schema probing; create a restore point and verify migration version.
- Provision/check `STRIPE_WEBHOOK_SECRET`, Workflow/R2 bindings, registry data, auth config, and any Modal invocation secret.
- Separate test and production modes intentionally; do not hard-code only `sk_test_` as the sole release path.
- Deploy staging, run auth/idempotency/ledger/top-up/provider-callback/R2/Modal smoke tests, then promote the exact artifact.
- Do not source an executable general-purpose shell env file during production release.
- Add a rollback command and run reconciliation before/after promotion.

### All three `modal_app.py` files and tests

- Replace `body: Any` with Pydantic request models or explicit `Body(...)`; send real ASGI JSON requests with `TestClient`/`httpx` in tests.
- Use unique test module/package names so one root suite collects.
- Validate complete public run envelopes and use `FormatChecker` plus semantic/artifact validation.
- Configure provider connect/read/total timeouts and disable SDK retries when the durable orchestrator owns retry policy.
- Extract shared parsing/schema/error/telemetry code only for work that remains on Modal.
- Remove per-workflow ASGI endpoints when Cloudflare is the sole public control plane.
- Emit actual usage/latency/resource data; hardcoded `usage` values are fixture metadata, not runtime truth.

### [`containers/ugc-heygen`](../../containers/ugc-heygen)

- Keep it as an offline contract/provenance fixture while moving orchestration to Cloudflare.
- Remove raw `avatar_id`/`voice_id`; expose curated marketplace enums resolved server-side.
- Split canary and production output schemas; production `completed` requires an owned, validated artifact.
- Delete `HEYGEN_API_KEY` from canary capabilities; later bind it only where the HeyGen adapter runs.
- Replace `$0.15` with a registry quote; treat `$0.60` as a provisional beta floor, not embedded output.
- Add provider callback fixtures, stale/missing callback reconciliation, artifact-not-ready retry, duplicate event/job, charged failure, and unsupported-claim tests.

### [`containers/claude-seo-skill`](../../containers/claude-seo-skill)

- Keep only as a private control-plane/transport canary unless renamed and marketed as an SEO action plan, not a site audit or agency replacement.
- Fix JSON transport, full envelope schema, explicit timeouts/retries, and actual usage.
- It does not justify a dedicated Modal app; execute the hosted LLM step from the durable edge orchestration path.

### [`containers/gpt-image-seedance-ad`](../../containers/gpt-image-seedance-ad)

- Do not deploy the mock A10 function. Keep `_mock_images_inside_container` strictly offline.
- Select a real model only after license, product-identity preservation, VRAM, load time, batch/variant strategy, and safety review.
- Build a benchmark harness first: cold/warm start, three variants, GPU seconds, R2 upload, decode/dimensions, prompt adherence, product fidelity, and cost per accepted image.
- Remove provider secrets from the GPU function. Pin model weights/image digest and use a prefix-limited artifact credential.
- Change the public contract to async; real multi-image generation and upload should not depend on one synchronous request.
- Reconcile top-level and Function resource limits, and replace mixed remote-image/GPU buckets with actual metering.

## Refined build order

1. **P0 — stop unsafe exposure:** disable paid generic execution and client-selected identity/prompt/price; require verified auth and restrictive CORS.
2. **P0 — migration-backed authority:** implement release registry, durable run state, idempotency, append-only ledger, purchased/promo separation, legal transitions, and R2 artifact records.
3. **P0 — durable orchestration:** add a Cloudflare Workflow for run lifecycle, explicit retry budgets, callback event wait, reconciliation, and settlement; keep D1 as business truth.
4. **P0 — honest HTTP tests:** real Worker and ASGI requests, concurrent duplicate submissions, crash-boundary replays, unauthorized reads, quote consistency, webhook replay, and ledger reconciliation.
5. **P1 — first paid production:** pure-LLM UGC Script Studio through the final contract. Use `Prefer: wait`, actual token usage, `$0.10` floor, and no Modal dependency.
6. **P1 — minimal canonical spec:** freeze one schema/vocabulary and existing-adapter compiler before adding workflow #2; publication should not generate Python.
7. **P1 — HeyGen staging:** one approved avatar/voice/style, 15s/9:16, real account invoice, provider idempotency, signed callback, reconciliation, R2 copy, media/claim QA, and hard spend cap.
8. **P1 — HeyGen invite beta:** provisional server quote, purchased-credit requirement, per-user/provider concurrency caps, kill switch, alerts, and manual review of early outputs.
9. **P2 — real GPU benchmark:** select and profile a licensed image model offline; deploy only after it produces owned pixels within latency/quality/cost gates.
10. **P2 — execution-class consolidation:** one shared CPU utility pool if needed, one class per resident GPU model, and global provider admission control.
11. **P3 — autopilot:** spec-only automation for approved adapters; human approval for every new capability; canary/rollback/quarantine based on real telemetry.

## Cut list

- Modal CPU orchestration for hosted LLM/HeyGen calls.
- Buyer-visible Modal endpoints and `FunctionCall` IDs.
- Long-lived polling/sleeping Modal runners.
- One FastAPI deployment per workflow.
- Public SEO “audit/replaces agency” positioning without crawl evidence.
- Any deployment of the fake GPU URL generator.
- Client-supplied prompt, model, token budget, provider IDs, user ID, price, or release.
- A universal two-second scale-down setting or universal `min_containers=0` doctrine.
- A global future 1.25× markup switch.
- Autonomous source-to-code/package/deploy behavior.
- “Exactly once” claims; use explicit idempotent effect guarantees and reconciliation.

## Promotion gates by stage

### Pure-LLM first paid release

- Authenticated identity and owner-only result lookup.
- One key/body creates one run, one reservation, one provider call, and one settlement under concurrent replay.
- Same key/different body returns `409`.
- Fast completion may return `200`; the same run remains queryable.
- Provider timeouts/errors release the reservation exactly once and expose no provider body.
- Actual tokens/cost, release hash, quote version, and latency phases are recorded.
- Promo abuse limits and global spend kill switch work.

### HeyGen invite beta

- All pure-LLM gates plus provider job/event uniqueness and stale-run reconciliation.
- Callback signature/timestamp/event ID verified and matched to the stored job.
- A missing callback is recovered without a duplicate render.
- Artifact is Omo-owned in R2, checksummed, decodable, portrait, audible, near 15 seconds, and speech/claims match the approved script.
- Charged failures, refunds, and duplicates are included in delivered-sale cost.
- Invoice-derived billing unit is known; price/reservation hard budget is server-authored.
- Purchased credits/payment verification required; invite, daily spend, and provider concurrency caps enabled.

### GPU release

- Real pixels, pinned licensed weights, reproducible image, and no mock domains.
- Cold/warm p50/p95, initialization and inference seconds, accepted-image yield, and OOM/preemption behavior measured.
- Product fidelity, prompt adherence, decode/dimensions, policy, and R2 delivery gates pass.
- Cost uses actual GPU/CPU/memory/region seconds and failed-output yield.
- Queue/admission behavior stays within buyer SLO at workspace GPU limits.

## Bottom line

Keep Modal, but narrow its job. Modal is excellent for elastic, container-native compute; it is unnecessary ceremony for the first pure-LLM workflow and for most of the HeyGen orchestration. The production milestone is not “a complex workflow ran on Modal.” It is “an authenticated buyer obtained a durable, correctly charged, supportable result under replay and failure.” Prove that cheaply with UGC Script Studio, then add HeyGen's asynchronous artifact risk, then earn the right to introduce a real GPU model.
