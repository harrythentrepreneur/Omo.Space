# OMO'S MEGA BUILDER AGENT

## Definitive architecture and build plan for the “boss agent”

**Status:** analysis and implementation blueprint only  
**Date:** 2026-08-11  
**Scope:** the control-plane agent that turns an authorized GitHub repository, `SKILL.md`, or workflow document into a tested Omo workflow candidate and drives it through the existing release autopilot  
**Non-goal:** this document does not deploy anything or change the current Worker, database, billing, Modal Apps, or catalog

This document is canonical for the mega builder's responsibilities and implementation order. [`modal-optimization/round-5.md`](modal-optimization/round-5.md) remains canonical for the paid runtime, tenancy, money, artifact, and release **semantics**. This blueprint makes one newer physical-storage decision explicit: Neon replaces D1 as the single paid-run system of record, while preserving round 5's atomic reservation, compare-and-set, outbox, append-only-ledger, reconciliation, and tenant-isolation requirements. [`positioning.md`](positioning.md) remains canonical for the product promise: a marketplace of proven automations, one public API, pay per use, and a real local-download option. The mega builder must satisfy both.

Throughout this document:

- **Mega agent** means the Hermes/Codex-based agentic builder described here.
- **Autopilot** means the safe, auditable release state machine described in [`modal-container-plan.md`](modal-container-plan.md), not a general coding agent.
- **Candidate** means generated spec, assets, code, tests, evidence, and pricing inputs that have not been promoted.
- **Release** means an immutable, QA-backed deployment identified by `omo-<slug>-<release_hash>`.
- **One shot** means one operator invocation runs until it either returns a verified live Omo endpoint or a typed, resumable blocker. It never means bypassing required identity, rights, capability, spend, price, or production approvals.

---

## 1. Executive summary

The mega agent is Omo's workflow factory. An operator gives it an authorized GitHub URL, local repository, `SKILL.md`, or workflow document. It fingerprints the source, extracts the promised input-to-output behavior, researches missing provider and runtime facts, produces a constrained executable specification, fills a reviewed scaffold, creates tests, compiles the Modal App, exercises it in staging, measures its costs, and submits the resulting candidate to the release autopilot. If every deterministic and human gate passes, the workflow becomes an immutable Modal release callable through Omo's single public `POST /v1/runs` endpoint.

The mega agent is deliberately not the public runtime. It runs in the control plane and may use research tools, web access, a terminal, a browser, source inspection, and isolated experiments. Buyer requests never invoke Hermes or Codex to improvise a workflow. Every buyer run resolves a server-owned immutable release, reserves an accepted quote before spend, and executes a bounded task graph in Modal.

The mega agent is also not the autopilot:

| Concern | Mega agent — agentic builder | Autopilot — safe release machine |
|---|---|---|
| Primary job | Discover what the workflow really requires and build a complete candidate | Decide whether an immutable candidate may move between release states |
| Input | Untrusted source material plus an operator build request | Canonical spec, provenance, capability diff, generated artifacts, QA evidence, approvals |
| Behavior | Researches, proposes, writes candidate assets, diagnoses failures, refines | Applies deterministic validators, deploys reviewed templates, records evidence, promotes/pauses/rolls back |
| Freedom | Broad inside an isolated, no-production-secret builder workspace | Narrow, policy-defined, compare-and-set state transitions |
| Output | Candidate bundle or exact blocker/setup manifest | `LIVE` release, `NEEDS_REVIEW`, `QA_FAILED`, `QUARANTINED`, or `ROLLED_BACK` |
| Forbidden authority | Cannot choose a buyer's identity, charge money, read production secrets, approve rights/new capabilities, or move traffic | Cannot invent workflow behavior, resolve unknown facts, add a provider/package/host, or self-approve a candidate |

This split is what makes the founder's goal safe and scalable:

1. **The builder can handle diversity.** It can understand a simple LLM skill, an asynchronous HeyGen job, a WhatsApp adapter, a native media binary, or a GPU pipeline instead of forcing every source into one hand-authored path.
2. **The live system stays reproducible.** The agent proposes the workflow; a deterministic compiler and reviewed adapter runtime produce the live `modal_app.py`. The same candidate compiles byte-for-byte the same way twice.
3. **Unknowns become work items, not guesses.** The mega agent researches missing provider operations, schemas, credentials, prices, licenses, and quality tests. Anything it cannot resolve is reported in a machine-readable blocker that the autopilot would refuse.
4. **Agent mistakes cannot silently become buyer traffic.** A deployment is not live. Only a versioned release record plus the server-owned traffic pointer can route public runs.

The first milestone is not “the agent generated some code.” It is complete only when the same mega-agent command takes the four acceptance projects—Cognition WhatsApp analyser, Woven, PadelBuddy, and the Japanese-style cartoon maker from voiceover—from their exact source packets to green production canaries through one Omo API. Each must have typed contracts, owned artifacts where applicable, measured costs, an approved price, an immutable release, and a proven rollback.

---

## 2. Architecture diagram

```text
CONTROL PLANE — build time; no buyer traffic

  Operator
  scripts/mega-build.sh <github-url|doc|repo> [--slug <slug>]
       |
       v
  +-----------------------------------------------------------------------+
  | MEGA AGENT — Hermes/Codex orchestrator                                |
  | tools: source reader, web research, terminal, browser, test runner     |
  | trust: isolated builder identity; staging keys only; no money/traffic  |
  +-----------------------------------------------------------------------+
       |
       +--> [1] INPUT
       |      GitHub URL / pinned repo / SKILL.md / workflow document
       |      -> authorized snapshot + commit/content hash + license facts
       |
       +--> [2] ANALYSE + EXTRACT
       |      promised input/output -> container-spec contract
       |      -> provenance map + unresolved[] + proposed QA rubric
       |
       +--> [3] RESEARCH LOOP
       |      primary provider docs -> official SDK/OpenAPI -> code search
       |      -> sandbox probes with test keys -> setup-manifest.yaml
       |      resolves what the autopilot must otherwise refuse
       |
       +--> [4] BUILD IN HARDCODED SCAFFOLD
       |      agent fills workflow DAG, bindings, prompts, schemas, tests,
       |      adapter configuration/proposals, resources and pricing inputs
       |      deterministic compiler emits:
       |      container.yaml + modal_app.py + worker-release.json + locks
       |
       +--> [5] TEST + REFINE (bounded)
       |      static -> build -> contract -> negative -> replay -> artifact
       |      -> semantic -> staging live probe -> cost
       |                failure ----> diagnose ----> new candidate hash
       |                    ^              |              |
       |                    +--------------+  max 3 revisions / paid budget
       |
       +--> [6] SUBMIT CANDIDATE TO AUTOPILOT
                              |
                              v
  AUTOPILOT — deterministic release controller

  DISCOVERED -> EXTRACTED -> SPEC_DRAFT
       -> NEEDS_REVIEW | STATIC_VALIDATED
       -> STAGING_DEPLOYED -> TESTING
       -> QA_FAILED --(bounded repair request)--> new immutable candidate
       -> APPROVED
                              |
                         [7] PRICING
                  versioned cost inputs -> C_guard
                  -> guarded price -> human-approvable release quote
                              |
                         [8] RELEASE
                  omo-<slug>-<release_hash>
                  signed QA + registry record + rollback target
                              |
                         traffic pointer only
                              |
                              v

DATA PLANE — run time; no builder agent

  Buyer
    |
    | [9] POST /v1/runs
    | Authorization + Idempotency-Key + workflow_slug + input
    v
  Cloudflare Worker — the only public gateway
    authenticate -> rate-limit -> choose immutable release -> validate
    -> quote -> atomic reserve/outbox -> private signed Modal dispatch
           |                         |
           v                         v
  Neon durable run/money state Modal omo-<slug>-<release_hash>
  + append-only ledger         executes every workflow step
           ^                         |
           | signed checkpoints      +--> LLM / external API / native / GPU
           |                         |
           +-------------------------+
           |
           +<---- R2 private owned inputs/outputs + checksums
           |
  GET /v1/runs/{run_id} -> owner-authorized durable result
```

There are no buyer-visible Modal URLs, Proxy Tokens, FunctionCall IDs, provider job IDs, raw provider errors, or storage keys. Cloudflare Workflows may later relay an outbox item or callback, but it never owns a listing DAG or executes provider steps.

---

## 3. The hardcoded foundation

The mega agent builds **on** the platform; it does not rebuild the platform per workflow.

### 3.1 Fixed product infrastructure

The following components are reviewed, versioned platform code:

1. **Cloudflare Worker gateway.** It owns public `POST /v1/runs` and `GET /v1/runs/{run_id}`, Clerk/API-key authentication, tenant derivation, rate limits, input validation, release selection, quotes, idempotency, reservation, dispatch, bounded waiting, provider-webhook verification, private checkpoints, and owner-only reads. A workflow contributes registry data, not a new public route.
2. **Neon database, run store, and ledger.** Neon is the one production authority for tenants, hashed API keys, immutable releases, traffic pointers, accepted quotes, run ownership/state versions, dispatch outbox, reservations, provider events, artifact metadata, Stripe events, promo/purchased credit buckets, and append-only ledger effects. One SQL transaction creates/replays the run, reserves credits, appends the ledger/run events, and creates the outbox row before dispatch. R2 owns artifact bytes.
3. **D1 reconciliation.** Round 5 names D1 because it requires an edge-local atomic CAS ledger. This blueprint preserves the requirement and changes the implementation to a Neon transaction reached from the Worker. D1 may later cache non-authoritative catalog/read data, but it cannot reserve, settle, release, or independently transition a paid run. The current `site/deploy/worker.js` and `site/deploy/schema.sql` already contain a Neon-first account/balance path plus D1/in-memory fallbacks; the shared platform team must expand that schema through numbered migrations for the full production model. D1 and in-memory fallbacks are development/compatibility paths and must fail closed for paid production. There must never be two money authorities or best-effort dual writes. This entire database layer is hardcoded infrastructure and outside the mega agent's write scope.
4. **Identity and authentication.** Clerk identifies browser users; random, revocable Omo API keys are stored only as hashes. The deterministic FNV demo key and client-supplied `user_id` patterns in the current Worker are not the production `/v1/runs` contract.
5. **Credits and billing.** Stripe top-ups, promo/purchased credit buckets, reservation, settlement, release/refund, `402 insufficient_balance`, spending limits, and creator accounting are shared services. Signup grants, suggested top-ups, and storefront copy remain centrally configured; generated workflows cannot alter them.
6. **Modal base images and runner.** The platform owns reviewed CPU, native-media, sandbox, and GPU image families; the adapter registry; input/output validators; task/checkpoint protocol; usage telemetry; R2 client; retry primitives; and secret binding mechanism.
7. **One public run contract.** Every workflow uses the same public request and durable result resource:

   ```http
   POST /v1/runs
   Authorization: Bearer <Clerk JWT or random Omo API key>
   Idempotency-Key: <client-generated key>
   Prefer: wait=8
   Content-Type: application/json

   {
     "workflow_slug": "ugc-script-studio",
     "input": { "...": "validated against the live release schema" }
   }
   ```

   Validation/auth/idempotency failures are stable `4xx` responses. Insufficient credits is `402` before Modal dispatch. A completed warm run may return `200`; otherwise `202` returns the same durable `run_id` and `status_url`. `GET /v1/runs/{run_id}` returns a non-enumerating `404` for a foreign run.
8. **Autopilot gates.** Canonical schema validation, capability diff, deterministic compilation, staging deployment, QA, approval evidence, quarantine, rollback, and traffic promotion are not generated per workflow.
9. **Release registry.** It stores source/spec/compiler/runtime/image/dependency/model/cost/QA hashes, internal Modal deployment metadata, approval records, health state, and the prior healthy rollback target. Only its traffic pointer can make a release live.

**Current-state gate:** `site/deploy/worker.js` is a demo, not this finished foundation. It still exposes `/api/run` with client-supplied `system_prompt`, `max_tokens` and `user_id`, permissive CORS, direct Worker-to-LLM execution, and development persistence fallbacks. The current shared schema also lacks the complete release/quote/run-state/outbox/reservation/provider/artifact model. Before any mega-built release receives paid traffic, the platform team must close paid behavior on `/api/run`, install numbered Neon migrations, switch to verified identity and random hashed API keys, and pass the atomic reserve/idempotency/tenant suite. The mega agent detects these prerequisites and returns `PLATFORM_NOT_READY`; it does not patch around them per workflow.

### 3.2 The only workflow-specific surface

The mega agent may fill or propose:

- typed input and output schemas;
- workflow step IDs, dependencies, bindings, final projection, timeouts, and idempotency keys;
- prompts and `SKILL.md` content;
- configuration for already approved provider/native/GPU adapters;
- a new adapter **proposal** plus fixtures when no approved adapter exists;
- resource requirements selected from approved profiles;
- egress and secret **names**, never secret values;
- contract, negative, replay, failure, artifact, semantic, and cost tests;
- versioned physical pricing inputs and QA budgets;
- local-download documentation and examples.

It may not add arbitrary executable binding expressions, handwritten public Worker routes, mutable buyer-selected prompts/models/prices, unpinned install hooks, or production secret values.

### 3.3 Scaffold repository layout

```text
scripts/
  mega-build.sh                         # one-shot entrypoint

mega-agent/
  cli.mjs
  orchestrator.mjs
  schemas/
    build-request.v1.json
    extraction-result.v1.json
    setup-manifest.v1.json
    build-report.v1.json
  extractors/
    github.mjs
    document.mjs
    skill-md.mjs
  research/
    research-loop.mjs
    evidence-store.mjs
    provider-probe.mjs
  builder/
    materialize-candidate.mjs
  tester/
    refine-loop.mjs

autopilot/
  schemas/
    container-spec.v1.json
    provenance.v1.json
    capability-manifest.v1.json
  registries/
    adapters.json
    operations.json
    images.json
    packages.json
    models.json
    cost-units.json
  compiler/
    compile.mjs                        # pure: no network, shell or secrets
    templates/
      modal_app.py.tmpl
      worker-release.json.tmpl
  qa/
    contract/
    negative/
    security/
    idempotency/
    billing/
    provider/
    artifact/
    quality/
    load/
    cost/
    rollback/
  state-machine.mjs
  policy.mjs
  release-controller.mjs

containers/
  omo-<slug>/
    container.yaml                     # canonical constrained workflow spec
    provenance.json                    # field -> evidence/confidence/source
    capability-manifest.json           # exact requested privileges
    setup-manifest.yaml                # required accounts/keys/human actions
    modal_app.py                       # compiler output; never hand-edited
    worker-release.json                # registry glue, not public route code
    resolved.lock                      # exact dependencies/adapters/models
    sbom.spdx.json
    README.md                          # portable/local-run instructions
    prompts/
      <step-id>.txt
    schemas/
      input.json
      output.json
      <step-id>.json
    tests/
      cases.json
      contract/
      negative/
      failures/
      artifacts/
      quality/
    qa/
      policy.json
      expected-metrics.json
```

Generated paths are reproducible products of `container.yaml + prompts + schemas + compiler_version`. A changed prompt, schema, package, adapter, secret binding, host, resource limit, price policy, or model produces a new hash. Per-workflow Worker glue is declarative release registration; the gateway stays hardcoded.

The provenance/build report also records the Hermes profile, builder model, tool-policy version, and extractor/research prompt hashes. Those values explain how the candidate was produced; they do not give Hermes a place in the buyer runtime.

---

## 4. The agentic research loop

### 4.1 Unknown-resolution protocol

Extraction returns three required objects:

1. `container_spec_draft` — everything supported by evidence so far;
2. `provenance_map` — source location, retrieval hash, confidence, and inference method for every material field;
3. `unresolved[]` — each missing contract, operation, provider fact, credential, license, quality rule, cost unit, or artifact rule.

Each unresolved item has:

```json
{
  "id": "U-HEYGEN-CREATE-001",
  "class": "provider_operation",
  "question": "Which current create operation and idempotency behavior are valid?",
  "required_for": ["compile", "live_probe", "price"],
  "risk": "paid_mutation",
  "status": "open",
  "evidence": [],
  "resolution": null
}
```

For each item, the mega agent runs at most four evidence passes:

1. **Primary documentation.** Current official provider docs, pricing, OpenAPI, rate limits, auth, webhooks, data retention, and terms.
2. **Official implementation evidence.** Official SDK source, examples, changelog, and versioned schemas. Third-party tutorials may identify a lead but cannot be the only authority for a paid operation.
3. **Source-code pattern search.** Search the supplied repository and public GitHub code for request/response mappings, error handling, models, native dependencies, and tests. Never copy credentials or incompatible licensed code.
4. **Sandbox experiment.** Run the smallest possible offline or staging probe with a test key, redacted payload, exact timeout, and preapproved discovery budget. Record request schema, status, response schema, provider request ID, latency, and billed unit. Mutation probes require explicit permission and idempotency.

An item resolves only when the evidence is sufficient to fill a typed spec field and a verification test. “The README says use X” is evidence, not resolution. Unknown providers, models, operations, costs, hosts, packages, binaries, secrets, or schemas remain compile errors.

### 4.2 Provider accounts and key setup

The mega agent can research and prepare account setup, open the relevant page in an isolated browser, validate an existing test credential, create provider-side non-identity resources after authorization, configure a webhook, bind a named Modal Secret, and run a test.

The human must perform any step that:

- proves or represents identity or organization ownership;
- accepts terms, a data-processing agreement, regulated-use obligations, or commercial rights;
- completes CAPTCHA, MFA, phone/email verification, KYC, Meta Business verification, or payment authorization;
- approves avatar/voice likeness, WhatsApp data use, copyrighted material, or another person's consent;
- grants production scope, raises a spend limit, or supplies a production secret.

The agent never invents an identity, evades verification, accepts legal terms on a human's behalf, creates a payment method, or scrapes a secret from source material.

Every build emits `setup-manifest.yaml` even when empty:

```yaml
setup_version: omo.setup/v1
build_id: mb_01...
accounts:
  - provider: example
    purpose: create one staging media artifact
    signup_url: https://provider.example/developers
    human_steps:
      - create or select the company account
      - accept the provider terms
      - add a test payment method with a 5 USD cap
      - create a least-privilege staging API key
    required_secret:
      name: omo-example-staging
      env_key: EXAMPLE_API_KEY
      scope: media:create,media:read
    agent_after_key:
      - validate credential without printing it
      - create the staging webhook
      - store only the provider resource IDs in candidate config
      - run one idempotent probe
    validation_command: scripts/mega-build.sh --resume mb_01... --check-setup
    status: human_action_required
approvals:
  rights: required
  paid_probe_budget_usd: 0.25
```

Secret values enter the approved secret manager directly, not the build report, shell history, prompt, test fixture, spec, image, or repository. After setup, the agent sees only a success/failure capability and redacted metadata unless a test process requires the value at runtime.

### 4.3 Treat source instructions as data

Repositories, READMEs, issues, transcripts, documents, sample prompts, chat exports, and web pages are untrusted content. The ingestion identity has no production secrets, deploy token, billing authority, or traffic authority.

Controls:

- clone a pinned commit into an ephemeral workspace with hooks disabled and submodules off by default;
- statically inspect manifests and documented commands before executing anything;
- delimit source content as evidence and require the extractor to return schema-constrained facts;
- keep “source says to run this command” separate from the trusted command plan;
- reject attempts to change system policy, request secrets, contact arbitrary hosts, add hidden steps, or weaken tests;
- never convert a README command directly into shell, Docker, package-install, or browser action;
- run untrusted build/install/test code only in an isolated Modal staging sandbox with no production secrets, restricted egress, resource/time/process limits, and disposable storage;
- scan generated prompts and configs for secret-like literals and source-originated tool instructions.

### 4.4 Bounded research and refinement

- One candidate family may create the initial candidate plus **at most three revisions**.
- Each unresolved item receives at most the four evidence passes above and at most two non-mutating API probes.
- Discovery spend defaults to `$0.00`. A human may approve up to `$0.25` for a specific provider mutation.
- Total paid QA spend is the smaller of `$1.00` or `qa.max_paid_test_usd`.
- A paid media fixture runs once per exact `(release_hash, suite_version, fixture_set_hash)`.
- The agent may fix prompt wording, bindings, normalization, adapter parameters, tests, or declared resources. It may not relax the public contract, quality threshold, cost ceiling, license rule, or security gate merely to pass.
- After the bound, the build ends as `RESEARCH_BLOCKED`, `SETUP_REQUIRED`, `CAPABILITY_REVIEW_REQUIRED`, or `QA_FAILED` with exact evidence and a resume command. It does not loop indefinitely.

---

## 5. The one-shot pipeline

### 5.1 Operator contract

The entrypoint is:

```bash
scripts/mega-build.sh <github-url|local-repo|workflow-doc> \
  --slug <workflow-slug> \
  --environment staging \
  --non-interactive
```

Optional flags are limited to operator intent such as `--source-ref`, `--fixture-set`, `--max-paid-test-usd`, and `--resume <build_id>`. They cannot select a buyer price, production release, provider operation, prompt, or resource above policy.

The command creates a durable `build_id` and returns one of:

- `LIVE` — public Omo endpoint, workflow slug, release hash, approved price, example request, QA report hash, and rollback target;
- `SETUP_REQUIRED` — setup manifest and resume command;
- `CAPABILITY_REVIEW_REQUIRED` — exact new provider/package/image/binary/host/secret/resource diff;
- `RIGHTS_REVIEW_REQUIRED` — unresolved license, data, voice, likeness, or content rights;
- `PRICE_REVIEW_REQUIRED` — complete cost evidence but a price/increase above the automatic review threshold;
- `PLATFORM_NOT_READY` — the shared Worker/Neon/auth/ledger/release prerequisites have not passed their platform suite;
- `QA_FAILED` or `RESEARCH_BLOCKED` — bounded failure report with evidence.

This is honest one-shot behavior. When credentials and approvals already exist, the first invocation may reach `LIVE`. When they do not, the first invocation still completes useful work and stops at the one boundary only a human can cross. `--resume` continues the same build without repeating paid work.

### 5.2 Twelve steps and acceptance gates

| # | Agent action | Required artifact | Acceptance gate |
|---:|---|---|---|
| **1** | Validate the build request and acquire the authorized source. Reject mutable or inaccessible inputs. | `build-request.json` | Source kind is supported; owner/authorization is recorded; URL/ref is resolved. |
| **2** | Clone/copy into isolated staging, disable hooks/submodules by default, fingerprint every source and referenced asset. | `source-manifest.json` | Commit SHA or content hash, retrieval time, author/owner, source paths, and license status exist; host workspace executed no source code. |
| **3** | Extract the promised job, examples, inputs, outputs, steps, quality claims, human actions, dependencies, and runtime clues against `container-spec.v1.json`. | Draft `container.yaml`, `provenance.json`, `unresolved.json` | Every required field has evidence or an explicit unresolved item; no display string masquerades as JSON Schema. Autopilot reaches `EXTRACTED/SPEC_DRAFT` only. |
| **4** | Research unresolved items through official docs, SDKs, code patterns, and bounded sandbox probes. | `research-report.json` | Provider operation, models, request/response schemas, auth class, pricing unit, rate limits, callbacks, hosts, license, and test method are either resolved or blocked. No guessed paid step. |
| **5** | Produce and check the setup manifest; validate named staging capabilities after the human supplies them. | `setup-manifest.yaml` | All required accounts, keys, resource IDs, consents, and paid-probe budgets are present. Secret values are absent from artifacts. Otherwise return `SETUP_REQUIRED`. |
| **6** | Compare the requested capability manifest with approved adapters/images/packages/models/hosts/secrets/resources. | `capability-manifest.json` and diff | Zero unreviewed capability expansion. A new capability becomes a reviewable adapter PR and `CAPABILITY_REVIEW_REQUIRED`, never an implicit install. |
| **7** | Materialize the workflow in `containers/omo-<slug>/`: DAG, schemas, prompts, adapters/config, artifact rules, tests, cost inputs, local README. | Complete candidate bundle | Bindings resolve; DAG is acyclic; final outputs are reachable; retries/idempotency/timeouts/resources/egress/artifacts are bounded; unresolved is empty. |
| **8** | Run the pure deterministic compiler twice. It generates `modal_app.py` and `worker-release.json` from reviewed templates and emits lock/SBOM hashes. | Generated bundle and reproducibility report | Both clean compiles are byte-identical; imports/static policy pass; no shell/Jinja/arbitrary expression or unpinned dependency path exists. Autopilot may enter `STATIC_VALIDATED`. |
| **9** | Run offline/mock tests and the bounded repair loop: schema, contract, negative, injection, replay, retry, cost-ceiling, artifact and semantic cases. | Signed local QA evidence | At least three happy fixtures and six negative/failure fixtures pass unless the release-specific rubric is stricter; invalid input causes no provider call; same effect key causes no duplicate mutation. |
| **10** | Submit to the autopilot for release-specific staging deploy and real HTTP tests. Exercise cold/warm, `200/202`, callbacks, Neon checkpoints, R2 artifacts, auth, tenancy, replay, provider errors and rollback. | Staging deployment + signed QA report | Real Worker-to-Modal path passes; provider artifacts are owned and validated; cost remains under `max_cost`; secrets/provider bodies do not appear in logs. Autopilot reaches `APPROVED`, not `LIVE`. |
| **11** | Compute guarded cost and the hosted/download/free price proposal; show the exact inputs, margin, tail reserve, ceiling, and quote fields. | `pricing-report.json` and approval record | No unknown cost code; human approves new release pricing; price is at or below automatic ceiling or `PRICE_REVIEW_REQUIRED` is resolved. |
| **12** | Ask the release controller to record `omo-<slug>-<release_hash>`, retain the rollback target, move an allowlisted/canary traffic pointer, and perform one public smoke run. | Immutable release record + final build report | Public `POST /v1/runs` returns the durable Omo run; `GET` returns the owner-authorized result; billing settles once; rollback drill succeeds. Only now is status `LIVE`. |

The final endpoint report always shows the shared public endpoint, for example:

```bash
curl -sS https://api.omo.best/v1/runs \
  -H "Authorization: Bearer $OMO_API_KEY" \
  -H "Idempotency-Key: demo-001" \
  -H "Prefer: wait=8" \
  -H "Content-Type: application/json" \
  --data-binary '{
    "workflow_slug": "<slug>",
    "input": {}
  }'
```

It never tells a buyer to call Modal directly.

---

## 6. Test corpus to spec map

The four names are acceptance requirements, not sufficient source packets. No matching project documents are currently present in this repository. Public names are also ambiguous: “PadelBuddy” is used for both a [camera/highlight product](https://padelbuddy.ai/) and a [community/booking product](https://padelbuddy.net/), while one public [Woven product](https://www.woven.dev/biz-change-agent) concerns analytics changes and may or may not be the founder's project. The input gate therefore requires the founder's exact GitHub URL or workflow document for each. The mega agent passes this test by refusing silent name resolution while still producing the following provisional shapes.

All cost figures below are **discovery envelopes**, not buyer quotes. The candidate must replace each range with current physical rates and observed usage before `STATIC_VALIDATED`.

### 6.1 Cognition WhatsApp analyser

**Expected job:** ingest an authorized WhatsApp conversation export or, only if the source requires it, messages acquired through an approved WhatsApp Business integration; return a grounded conversation analysis with evidence traceable to message IDs.

| Spec area | Provisional shape |
|---|---|
| Inputs | `chat_export` as an exact R2 object reference (`.txt` or approved `.zip`); `analysis_goal` enum; `timezone`; `language`; optional participant aliases and consent attestation. The API must not accept an arbitrary local path or URL. |
| Outputs | Typed summary, themes, timeline, participant metrics, sentiment/interaction patterns, evidence citations to normalized message IDs, limitations, and action items; optional private HTML/PDF report in R2. No diagnosis or high-stakes conclusion without an explicit reviewed product scope. |
| Steps | R2 fetch → MIME/magic/size scan → deterministic Android/iOS export parser → normalize/deduplicate → PII policy/redaction → token-aware chunking → LLM map analyses → deterministic aggregate/LLM synthesis → evidence verifier → report renderer. |
| Providers/capabilities | CPU/native parser and LLM are sufficient for export-only v1. WhatsApp Cloud API, Meta app/webhook, phone-number verification, and media download are separate new capabilities only if the source contract requires live ingestion. |
| Secrets/egress | LLM secret/host; optional Meta staging secret and Graph API host. Never put chat text in logs or research prompts unrelated to the run. |
| Provisional cost | Text-only planning band `$0.02–$0.70` per export, dominated by length/model and repeated passes. The positioning anchor of `$1` with about `$0.30` profit implies a direct-cost ceiling near `$0.70`, but the 80% guarded formula would price a `$0.70` guard at `$3.50`. The agent must measure a versioned corpus before choosing either figure. |
| Required tests | Android/iOS formats, multiline messages, Unicode, deleted/system/media placeholders, duplicate timestamps, 1/10/100k-message sizes, prompt injection inside messages, PII retention, exact citation traceability, cross-tenant artifact denial, deterministic parser snapshots, malformed archive rejection before LLM spend. |
| Must research | Exact source and promised rubric; export versus Cloud API; supported sizes/languages/media; privacy region/retention/deletion; consent and regulated-use boundaries; model/context/chunk strategy; report format; WhatsApp terms and current API pricing if live ingestion is required. |

**Green gate:** one public run over a founder-approved golden export returns a schema-valid report whose sampled claims trace to source messages, stores no unauthorized raw transcript, stays under the accepted ceiling, and can be deleted under the retention policy.

### 6.2 Woven

**Expected job:** unknown until the exact source is supplied. If the intended Woven is the analytics/change-agent workflow suggested by the name, the provisional contract below applies. If it is another product, Step 1 must replace this shape rather than adapting the wrong project.

| Spec area | Provisional analytics/change-agent shape |
|---|---|
| Inputs | Pinned GitHub repo/ref or exact R2 source snapshot; task/change request; optional sanitized dbt manifest/catalog and read-only warehouse metadata reference; policy flags controlling whether output is report-only or a patch proposal. |
| Outputs | Impact graph, findings with file/model/column evidence, test plan, proposed patch as a downloadable diff, and machine-readable risk summary. No automatic merge, warehouse mutation, or Slack post in milestone 1. |
| Steps | Static clone → license/dependency scan → parse Git/dbt metadata → optional read-only Snowflake metadata query → build dependency graph → LLM analysis → deterministic evidence validator → patch/test in isolated Modal sandbox → report/R2 bundle. |
| Providers/capabilities | GitHub read adapter; native Git/dbt/parser binaries; LLM; optional Snowflake read-only adapter. Slack is output notification only and deferred unless source acceptance requires it. |
| Secrets/egress | Fine-grained GitHub token, optional read-only warehouse credential; exact GitHub/warehouse/LLM hosts. No general repository write token in the runner. |
| Provisional cost | `$0.02–$1.00` depending on repository size, warehouse calls, and sandbox time. This range is intentionally too broad for pricing; extraction must produce bounded file/model counts and an exact benchmark. |
| Required tests | Small/large fixture repos, malicious README/instructions, symlink/path escape, submodule refusal, secret scanning, invalid dbt graph, no-network mode, deterministic diff, compile/test failure, read-only credential enforcement, evidence links to file+line/model IDs. |
| Must research | Exact project identity/URL/license; actual input and promised output; supported languages/frameworks; whether “Woven” requires GitHub, dbt, Snowflake, Slack, or none of them; native build commands; write authority; data residency; completion rubric and expected latency. |

**Green gate:** the founder's exact Woven fixture completes through the public API, produces the promised artifact/report, executes untrusted project code only in the restricted Modal staging/runtime sandbox, and demonstrates that source instructions cannot obtain secrets or write upstream.

### 6.3 PadelBuddy

**Expected job:** provisionally, the positioning document's “player inputs → hosted padel utility,” not a hardware camera product. Name resolution is a mandatory gate because that difference changes the entire runtime.

| Spec area | Provisional hosted-utility shape |
|---|---|
| Inputs | Players with stable opaque IDs, ratings/levels, availability, preferences and recent match history; venue/court/time constraints; requested operation such as `balance_teams`, `recommend_match`, or `schedule_round`. |
| Outputs | Balanced teams or match plan, score/confidence, explanation of constraints/trade-offs, alternatives, and optional calendar/WhatsApp notification preview. Persistent club state is referenced by tenant-owned IDs, not supplied as arbitrary DB credentials. |
| Steps | Strict validation → deterministic rating/constraint normalization → optimizer/solver native step → optional LLM plain-language explanation → schema/feasibility verifier → result. Notification sending is a separate idempotent effect after core success. |
| Providers/capabilities | CPU and a pinned solver library/native binary; optional LLM. WhatsApp/Calendar/booking adapters require separate approval and must use idempotent provider keys. If the source is the camera/highlight product, replace this spec with video ingest, rolling buffer, clip extraction, encoding, storage and hardware-auth contracts. |
| Secrets/egress | None for pure optimizer beyond platform services; provider-scoped secrets for notifications/booking only. |
| Provisional cost | Pure matching `$0.001–$0.05`, normally the `$0.10` hosted floor. A camera/video interpretation could be `$0.10–$2.00+` per artifact and cannot inherit the utility price. |
| Required tests | Odd/even player counts, rating ties, impossible constraints, fairness bounds, deterministic seed, large club load, malformed IDs, cross-tenant history, replayed notification, solver timeout, and objective-score regression fixtures. |
| Must research | Exact repository/license and whether the product is matching, booking, coaching, community, or camera highlights; algorithm and fairness rubric; persistent schema; provider integrations; real-time versus one-shot behavior; hardware dependency; notification consent; local-download behavior. |

**Green gate:** on founder-supplied fixtures, every proposed match satisfies hard constraints, meets the versioned balance metric, returns a stable typed result under replay, and—if notification is in scope—sends at most one approved message.

### 6.4 Japanese-style cartoon maker from voiceover

**Expected job:** turn an authorized voiceover into a short Japanese-inspired cartoon video while preserving the supplied audio and producing owned, validated media artifacts.

| Spec area | Provisional shape |
|---|---|
| Inputs | Voiceover as exact R2 object reference; optional transcript; `style_preset` from curated rights-safe presets; aspect ratio; resolution; optional character/reference assets with rights attestations; subtitle and motion settings. |
| Outputs | Omo-owned MP4, storyboard JSON, shot timing, image/frame manifest, captions/SRT, thumbnail, checksums and media metadata. Provider URLs are intermediate, never final success. |
| Steps | MIME/magic/`ffprobe` validation → ASR only when transcript absent → segment/timing analysis → LLM storyboard/prompt plan → N image or local-GPU frame generations → consistency/rights/safety checks → image-to-video or bounded pan/zoom animation → FFmpeg audio mux/subtitles → decode/A-V sync/quality validation → R2 copy. |
| Providers/capabilities | LLM; ASR; image generation or licensed local GPU model; optional image-to-video provider; FFmpeg/ffprobe; R2. TTS is **not** a default step because voiceover is the input. |
| Secrets/egress | Provider-specific least-privilege staging secrets and hosts; no arbitrary model download at startup. Local weights, image digest and licenses are pinned in the release. |
| Provisional cost | `$0.10–$1.50` depending on duration, number of frames, remote video use and accepted-output yield. The positioning target of about `$0.30` is possible under the 80% rule only if `C_guard <= $0.06`; the mega agent must benchmark a cheaper local/batched path or propose a higher price rather than hide cost. |
| Required tests | 15/30/60s audio, MP3/WAV, corrupt/oversized media, exact duration band, decode, audio presence, A-V sync, subtitle timing, no truncated speech, character consistency, style rubric, reference-asset consent, unsafe prompt, duplicate provider mutation, GPU OOM/preemption, R2 ownership and rollback. |
| Must research | Exact source workflow and intended aesthetic; whether “Japanese-style” refers to a general visual language or a named artist/studio; rights policy; models/providers and current prices; maximum duration/frames; consistency technique; ASR languages; image-to-video versus local animation; GPU/region/SLO; acceptance examples. |

**Green gate:** a founder-approved voiceover produces a private Omo-owned MP4 that decodes, preserves the full audible content, meets duration/A-V/style/consistency rubrics, contains no unapproved likeness or style claim, and stays below the accepted cost ceiling.

### 6.5 Acceptance battery definition

The mega-agent milestone is not complete until all four exact source packets have:

- an empty unresolved list or recorded human approvals for every non-technical fact;
- at least one immutable production-canary release reachable through `POST /v1/runs`;
- three happy fixtures and at least six negative/failure fixtures, plus project-specific artifact/quality gates;
- one replay test proving no duplicate paid effect;
- actual usage and cost stored under the Omo `run_id`;
- a human-approved guarded price and hard execution ceiling;
- a signed QA report, R2 ownership for artifact outputs, and a tested exact rollback target.

A source that correctly returns `SETUP_REQUIRED` or `CAPABILITY_REVIEW_REQUIRED` demonstrates safe behavior, but it does not count as a green corpus deployment.

---

## 7. Pricing automation

### 7.1 Replace estimates with a guarded release cost

The current `site/deploy/cost-model.mjs` is useful seed evidence: it has approximate LLM/API units, a `5x` launch markup, a `$0.10` floor, and a free/one-time/API display ladder. It is not the production price authority because it has unknown-model and unknown-API fallbacks, a generic `modal_gpu_30s` bucket, incomplete input/retry/infrastructure costs, and nearest-cent rounding.

For each immutable candidate the mega agent produces:

- `C_static` — worst approved input, physical provider units, CPU/RAM/GPU type and seconds, cold/init and allocated idle, region premium, R2/Cloudflare, allowed retries, failed-output allowance, and payment-variable costs;
- `C_success_p95` — p95 actual cost of successful attempts when available;
- `C_delivered_7d` and `C_delivered_30d` — all variable cohort cost divided by completed, retained, chargeable outputs, including failures, retries, duplicates, refunds, fraud/promo allocation and rejected-output yield;
- a versioned `cost_version` and source/effective date for every rate.

```text
C_guard = max(
  C_static,
  C_success_p95,
  max(C_delivered_7d, C_delivered_30d) * (1 + tail_reserve)
)

buyer_price = ceil_to_cent(
  max($0.10, C_guard / (1 - 0.80))
)
```

Tail reserve is `10%` for mature LLM workflows, `15%` for remote media, and `20%` for GPU until 30 clean days justify a lower approved value. Unknown cost units fail compilation; they never default to `$0.05`.

Examples:

| `C_guard` | Guarded hosted price |
|---:|---:|
| `$0.001` | `$0.10` floor |
| `$0.06` | `$0.30` |
| `$0.14` | `$0.70` |
| `$0.70` | `$3.50` |

### 7.2 Price surfaces

Free, one-time, and per-use are product surfaces, not a cost-based either/or:

- **Free demo:** optional lead magnet with a zero buyer price, strict per-user/IP quota, sponsor budget, no unbounded paid provider call, and no “proven paid workflow” implication.
- **One-time download:** the portable `container.yaml`, `SKILL.md`, prompts, schemas, tests, supporting files, and instructions. The creator/human approves its value-based price; the current `$39 one-time` display may be a storefront default, but the mega agent does not derive download value from a `$0.10` run cost.
- **Hosted per-use:** always uses the guarded formula for the immutable release, then may be raised by an approved outcome-value price. It is never set below the guarded floor.

Before production promotion, the build report shows the estimated and observed costs, tail reserve, target margin, proposed hosted price, optional download price, hard cost ceiling, and change from the previous release. A human approves every new workflow's initial price.

Before each buyer run, the Worker creates a server-authored 10-minute quote containing `quote_id`, `release_hash`, `price_cents`, `reserve_cents`, `estimated_cost_nanos`, `max_cost_nanos`, `cost_version`, `target_margin_bps`, and `expires_at`. The accepted quote never changes if the listing is repriced later.

### 7.3 Fail-safe

- Milestone default `AUTO_PRICE_CEILING_CENTS = 500` (`$5/run`).
- Any first price above `$5`, any increase above `25%` versus the live release, or any candidate whose `C_guard` is based only on a broad discovery range enters `PRICE_REVIEW_REQUIRED`.
- A human may approve a higher release-specific ceiling with evidence; the agent cannot.
- Every release has `max_cost_nanos` shared across all retries. Crossing it stops new spend, checkpoints the run for reconciliation, and settles/releases credits exactly once.
- Provider/workflow/day/workspace budgets and kill switches remain outer limits. An automated repair cannot raise them.

---

## 8. Safety and guardrails

The mega agent has freedom to **build**; the autopilot and release system bound what can go **live**.

| Risk | Builder control | Autopilot/runtime gate |
|---|---|---|
| Prompt injection in repo/docs/chat data | Treat content as evidence; no deploy credentials; schema-constrained extraction; source commands never execute directly | Secret/instruction scan, capability diff, deterministic compiler, injection fixtures |
| Secret exposure | Test-only identity; secret values enter secret manager directly; redact commands/results | Named capability-scoped Modal Secrets; no values in spec/image/log/response; canary secret scan; rotation |
| Arbitrary code/supply chain | Static inspection on host; untrusted code/install hooks run only in disposable restricted Modal staging sandbox | Allowlisted pinned packages/images/binaries, lock, digest, SBOM, vulnerability/license review; no generated shell |
| Egress abuse | Research/probe host list and exact operation; no arbitrary source URL | Adapter clients enforce scheme/host/path; runtime egress proxy/network policy where available; undeclared host is a compile error |
| Cost/retry explosion | Physical cost model, paid-test dedupe and budget, max three revisions | Reserve before dispatch; run-derived effect IDs; bounded step retries; `max_cost`; provider/workspace kill switch |
| Duplicate paid effects | Probe and tests use stable effect keys | Tenant/workflow/idempotency-key request hash, outbox replay, Modal run claim, provider idempotency, unique acknowledgements/effects, reconciliation |
| Identity/tenancy leak | Builder uses synthetic tenants and no production customer data | Auth-derived tenant only; tenant predicate on every read/mutation; foreign run/artifact returns `404` |
| License/rights/consent | Record source license, dependency licenses, model/weight license, data/voice/likeness attestations | Human gate for unresolved rights/new commercial use; no public listing without provenance |
| Bad or fake artifact | Real fixture and project-specific verifier; provider URL is not success | R2-owned exact key, checksum/bytes/MIME/magic/decode/metadata/quality validation |
| Same-model self-grading | Deterministic assertions plus separate evaluator/rubric | Deterministic failures are authoritative; judge cannot override schema, rights, artifact or cost gate |
| Mutable release/drift | Every repair creates a new candidate hash | Release hash covers source/spec/prompts/schemas/capabilities/compiler/runtime/locks/images/models/secrets/resources/cost policy |
| Unsafe promotion | Builder can request, never move traffic | Successful deploy and QA are not live; only recorded approval plus CAS traffic pointer; automatic pause/quarantine and exact rollback |

Additional round-5 invariants:

1. The server chooses release, prompt, model, operation, price, retries, resources, ceiling, and artifact destination.
2. Delivery is at least once; the guarantee is one durable Omo run plus idempotent/reconciled effects, not distributed exactly once.
3. No billable Modal/provider work occurs before a durable accepted quote and reservation.
4. Neon is the paid runtime truth; Modal call state is execution evidence, not order history. D1/in-memory compatibility paths cannot accept paid production traffic.
5. Media success requires an Omo-owned R2 artifact, never a temporary provider URL.
6. Async providers checkpoint and end work, then resume through a verified callback or short rescheduled Modal task. A production container never sleeps for 15 minutes.
7. A new provider, operation, model, weight, package, native binary, base image, secret, host, callback, artifact type, retention policy, GPU class, or higher ceiling is a new-capability lane with human review.
8. Automatic promotion remains disabled until the round-5 clean-history requirements are met. Automation may safely pause, quarantine, or roll back within recorded authority.

Rollback is a traffic-pointer CAS to the retained prior healthy immutable release, followed by a smoke test and reconciliation of in-flight runs against their original release hashes. Rollback never rewrites an old release or changes an accepted quote.

---

## 9. Build order for the mega agent

### Step 1 — Scaffold repo, canonical schemas, and registries

Create `scripts/mega-build.sh`, the `mega-agent/` skeleton, `autopilot/schemas/`, reviewed template/compiler boundaries, adapter/image/package/model/cost registries, and `containers/omo-<slug>/` materializer.

**Acceptance criteria:**

- a hand-authored pure-LLM fixture validates against `container-spec.v1.json`;
- every field from the `3.3` minimal executable spec has a canonical name;
- unknown adapter/model/cost/host/secret/resource fails closed;
- two clean fixture compiles are byte-identical;
- generated `modal_app.py` accepts real JSON and exposes only the protected internal contract.

### Step 2 — Extractor

Implement GitHub, document, and `SKILL.md` acquisition; immutable fingerprinting; safe frontmatter parsing; contract/example extraction; provenance; unresolved reporting; and prompt-injection fixtures.

**Acceptance criteria:**

- pinned GitHub, local doc, and `SKILL.md` fixtures each produce `container_spec_draft + provenance_map + unresolved[]`;
- a prose-only skill remains `SPEC_DRAFT` rather than becoming executable;
- malicious README commands do not run or alter agent policy;
- license absent, mutable branch-only input, missing output schema, and paid API label without operation remain explicit blockers.

### Step 3 — Research loop and setup manifests

Implement primary-doc/SDK/code-search/probe adapters, evidence scoring, provider operation records, cost-source capture, account boundary handling, and resumable setup manifests.

**Acceptance criteria:**

- one existing approved LLM operation resolves from docs through a mocked probe and produces a versioned cost unit;
- one fake/unknown provider fails closed;
- an identity-verified provider case returns `SETUP_REQUIRED` with exact human and agent-after-key steps;
- secret values never appear in reports/fixtures/logs;
- evidence/probe and `$0.25` discovery limits stop automatically.

### Step 4 — Builder and deterministic compiler

Implement candidate materialization, DAG/binding resolver, capability diff, approved-adapter wiring, prompt/schema/test generation, resource-profile selection, release hash, lock/SBOM, Modal template compiler, and declarative Worker release manifest.

**Acceptance criteria:**

- pure LLM, async remote API, native binary, and GPU fixture specs compile through approved profiles;
- new provider/native/GPU capabilities generate a reviewable proposal and cannot compile live;
- no source-authored shell, Dockerfile, package hook, Python/JS/Jinja binding, public Worker route, or arbitrary URL reaches generated runtime;
- source/spec/prompt/schema/capability/compiler/runtime/lock/image/model/cost changes each change the release hash.

### Step 5 — Tester and bounded refiner

Implement offline/static/build/contract/negative/injection/replay/failure/artifact/semantic/security/cost suites, staging live probes, separate evaluation, evidence signing, spend dedupe, and the three-revision loop.

**Acceptance criteria:**

- three happy plus six negative/failure fixtures pass for the reference workflow;
- invalid input causes zero paid calls;
- 100 same-key concurrent replays converge to one run/effect in the integration fixture;
- crash injection after reservation, dispatch, provider send/ack, artifact write, validation and settlement produces no duplicate spend or ledger effect;
- revision four and spend above the lesser of `$1`/QA budget stop as `QA_FAILED`;
- the refiner cannot lower a contract/quality/security/cost threshold.

### Step 6 — Autopilot integration and four-project acceptance run

Connect candidate submission to the legal state machine, staging deploy, Worker↔Modal signed dispatch/checkpoints, Neon/R2, guarded pricing, approvals, immutable registry, canary traffic, quarantine and rollback. Run the exact four founder source packets.

**Acceptance criteria:**

- deploy success alone cannot route traffic;
- public `POST /v1/runs` and owner-only `GET` work for every corpus workflow;
- each run reserves before dispatch, records actual usage, stores required owned artifacts, and settles/releases once;
- each project satisfies its `6` green gate and returns through the same API shape;
- every release has a human-approved price, signed QA, hard ceiling, prior healthy target, successful rollback drill, and zero unresolved billing reconciliation;
- **all four acceptance projects are green production canaries. Until then, the mega-agent milestone remains incomplete.**

---

## 10. What to cut or defer

The first milestone includes only what is needed to turn the four exact sources into safe, repeatable Omo releases.

Cut or defer:

1. **A visual editor and canonical XML format.** Use `container.yaml` as the build contract now. A future editor/XML interchange may map to it after the compiler is stable.
2. **Cloudflare Workflows as workflow engine.** It may later relay outbox/callback events; Modal runs every listing step.
3. **Shared multi-workflow or per-user Modal Apps.** Use one immutable App per listing release with shared base layers/runtime.
4. **Buyer-provided provider keys, prompts, models, prices, retries, IDs, URLs, resource limits, or artifact destinations.**
5. **Fully automated identity/account creation.** Setup manifests and post-key automation are in scope; KYC, CAPTCHA, MFA, terms, payment, and rights approval stay human.
6. **Arbitrary “run this GitHub repo” execution.** Almost any authorized source may be ingested; only a bounded, typed, licensed workflow with approved capabilities may be deployed.
7. **Agent-written production Worker routes, Dockerfiles, install hooks, or unconstrained runtime code.** New adapter code is a reviewed capability PR; live Apps come from the deterministic compiler.
8. **Long sleeping provider pollers.** Use verified webhooks or short rescheduled Modal tasks.
9. **Generic cost fallbacks, `modal_gpu_30s`, automatic `1.25x` repricing, or price claims based on mocks.**
10. **Catalog-wide warm containers, multi-region variants, or speculative GPU residency.** Default to scale-to-zero and benchmark per release.
11. **Automatic production promotion or recovery from correctness/security quarantine.** Safe automatic pause/rollback may come first; promotion waits for the round-5 clean-history requirement.
12. **Hardware integrations for PadelBuddy, live WhatsApp ingestion, Snowflake/Slack writes for Woven, or remote image-to-video for the cartoon maker** unless the founder's exact source makes that capability necessary for its acceptance contract.
13. **Broad creator marketplace/payout automation and catalog ingestion.** Prove the four-source builder and one-run economics first.
14. **Polished local-run UX.** Do not cut portability: every release still ships the spec, prompts, schemas, tests, locks and README. Defer installers, GUIs and cross-platform packaging.
15. **Fine-tuning or training new models.** Use approved hosted models or pinned licensed weights until real acceptance data shows training is necessary.
16. **Claims that source ingestion equals “proven.”** Only the completed `LIVE` gates earn that label.

The milestone should remain intentionally narrow: one command, one candidate format, one deterministic compiler, one release state machine, one public API, four materially different workflows, and no path around the gates.
