# Omo Mega Builder Agent — Future Blueprint

> **STATUS: PLANNED — not yet implemented. The platform foundation (round-5) must be built first; this is the roadmap for the builder agent that comes after.**

**Date:** 2026-08-11  
**Document type:** architecture blueprint and sequenced delivery plan  
**Implementation status:** no mega-agent, autopilot, or one-shot builder scaffold exists today

This document describes a future control-plane builder that could turn an authorized repository, `SKILL.md`, or workflow document into a tested Omo release candidate. It is not evidence that the builder, paid platform, release controller, or public run API has been shipped.

**[review] F-01/F-29 — Current-repository truth:** `mega-agent/`, `autopilot/`, and `scripts/mega-build.sh` do not exist. The checked-in `containers/ugc-heygen`, `containers/gpt-image-seedance-ad`, and `containers/claude-seo-skill` are handwritten design or compatibility fixtures; disabled HeyGen behavior, mock GPU URLs, and direct Modal routes are not proof of the planned runtime. Every path and command labeled **planned** below is a future artifact, not an instruction that works now.

## Table of contents

1. [Purpose, authority, and scope](#1-purpose-authority-and-scope)
2. [Planned architecture and responsibility split](#2-planned-architecture-and-responsibility-split)
3. [Prerequisites: build the platform before the builder](#3-prerequisites-build-the-platform-before-the-builder)
4. [Planned hardcoded foundation and frozen contracts](#4-planned-hardcoded-foundation-and-frozen-contracts)
5. [Planned mega-agent behavior](#5-planned-mega-agent-behavior)
6. [Planned one-shot candidate pipeline](#6-planned-one-shot-candidate-pipeline)
7. [Four-project acceptance epic](#7-four-project-acceptance-epic)
8. [Pricing and cost automation](#8-pricing-and-cost-automation)
9. [Safety, rights, and release invariants](#9-safety-rights-and-release-invariants)
10. [Ordered roadmap and milestone gates](#10-ordered-roadmap-and-milestone-gates)
11. [Explicitly deferred work](#11-explicitly-deferred-work)
12. [Appendix A — Top 10 next actions](#12-appendix-a--top-10-next-actions)

---

## 1. Purpose, authority, and scope

### 1.1 Product objective

The future mega agent is Omo's workflow factory. Given an authorized, immutable source packet, it should:

1. identify the promised input-to-output job;
2. research facts the source does not establish;
3. draft a constrained workflow spec with provenance and unresolved items;
4. materialize prompts, schemas, tests, capability requests, and cost inputs inside a reviewed scaffold;
5. submit an immutable candidate to the **planned autopilot** for deterministic compilation, staging, QA, and approval;
6. stop with a typed, resumable blocker whenever identity, rights, capability, cost, setup, or production authority is missing.

The buyer-facing promise remains the one in [`positioning.md`](positioning.md): proven automations, one public API, pay per use, and a real local-download door. “Proven” is earned only by a typed contract, real example, known price, repeatable QA, measured cost/latency/failure behavior, and a versioned downloadable package.

### 1.2 Document authority

- [`positioning.md`](positioning.md) is canonical for product positioning and creator economics.
- [`modal-optimization/round-5.md`](modal-optimization/round-5.md) is canonical for the final runtime shape and shipment ladder, except for its D1 choice, which the founder has superseded with Neon subject to the ADR in §3.2.
- [`modal-container-plan.md`](modal-container-plan.md) §3.3 supplies the draft minimal container-spec fields, §4 supplies the HeyGen reference workflow, and §5 supplies the **planned** autopilot state machine. Its buyer-visible Modal API and sleeping poller examples are superseded by round 5.
- This document is canonical only for the future mega-agent boundary and the order in which it should eventually be built.

**[review] F-31 — Correct reference:** “minimal executable spec” always means [`modal-container-plan.md` §3.3](modal-container-plan.md#33-minimal-executable-container-spec), not this document's scaffold section.

**[review] F-33 — Go/XML conflict:** positioning currently names Go services and a canonical XML workflow format, while earlier drafts here proposed JavaScript modules and `container.yaml`. Before implementation, the platform team must ratify one language/serialization boundary or amend positioning. This blueprint uses logical schema names and keeps `container.yaml` only as a provisional human-readable candidate representation; it does not silently overrule the Go/XML direction.

### 1.3 Vocabulary

- **Mega agent:** the future Hermes/Codex-based, agentic control-plane builder described here.
- **Planned autopilot:** the future deterministic candidate/release state machine described by round 5 and the container plan. It does not exist today.
- **Candidate:** proposed spec, source/provenance manifests, assets, locks, tests, QA inputs, and pricing inputs that have not been promoted.
- **Release:** a future immutable deployment identified by `omo-<slug>-<release_hash>` and selected only through a server-owned traffic pointer.
- **One shot:** one future operator invocation progresses until it returns a candidate approved for promotion or a typed, resumable blocker. It never means bypassing human approval or ending a staging command in production.
- **Source packet:** an immutable, rights-approved source plus the owner-approved job, fixtures, provider setup, and acceptance rubric.

### 1.4 Non-goals

This plan does not authorize or perform changes to the current Worker, database, billing, Modal Apps, catalog, `mega-agent/`, `autopilot/`, or `scripts/mega-build.sh`. The mega agent will not be the public runtime, a buyer-time coding agent, a provider-account identity bot, a rights approver, or an automatic production promoter.

---

## 2. Planned architecture and responsibility split

### 2.1 Target architecture

```text
FUTURE CONTROL PLANE — build time; no buyer traffic

  Operator + frozen source packet
       |
       | planned: scripts/mega-build.sh <source> --slug <slug>
       v
  +--------------------------------------------------------------------+
  | MEGA AGENT — agentic builder                                      |
  | isolated source reader + research + browser + terminal + QA tools  |
  | no production secrets, money authority, or traffic authority      |
  +--------------------------------------------------------------------+
       |
       +--> acquire/fingerprint source + rights evidence
       +--> extract spec draft + provenance + unresolved[]
       +--> bounded official-doc/SDK/code/probe research
       +--> fill reviewed candidate scaffold
       +--> offline tests + bounded refinement (maximum 3 revisions)
       |
       v
  PLANNED AUTOPILOT — deterministic candidate/release controller
       canonical validation -> capability diff -> deterministic compile
       -> staging deploy -> signed QA -> cost evidence -> approval record
       -> APPROVED_FOR_PROMOTION
       |
       | separate, human-authorized production promotion
       v
  immutable release + traffic pointer

FUTURE DATA PLANE — buyer time; no builder agent

  Buyer
    |
    | POST /v1/runs
    | verified auth + Idempotency-Key + workflow_slug + input
    v
  Cloudflare Worker — only public gateway
    authenticate -> select server-owned release -> validate -> quote
    -> atomic run/reservation/outbox -> private signed Modal dispatch
       |                         |
       v                         v
  Neon paid state          Modal omo-<slug>-<release_hash>
  + append-only ledger     executes every listing step
       ^                         |
       | signed checkpoints     +--> LLM / async API / native / GPU
       +-------------------------+
       |
       +<---- R2 private inputs/outputs + checksums
       |
  GET /v1/runs/{run_id} -> owner-authorized durable result
```

Modal is the universal execution plane. The Worker is the only public gateway. Neon is intended to own paid business state after the ADR is ratified. R2 owns artifact bytes. Buyer requests never invoke Hermes/Codex to improvise behavior, and buyers never see Modal URLs, Proxy Tokens, FunctionCall IDs, provider job IDs, raw provider errors, or storage keys.

### 2.2 Mega agent versus planned autopilot

| Concern | Mega agent — agentic builder | Planned autopilot — safe release machine |
|---|---|---|
| Job | Discover requirements and assemble a candidate | Enforce legal, reproducible state transitions |
| Input | Untrusted source packet and build request | Canonical candidate, provenance, capability diff, QA, approvals |
| Behavior | Research, propose, write candidate assets, diagnose, refine | Validate, compile reviewed templates, deploy staging, record evidence, pause/quarantine/rollback |
| Freedom | Broad only inside an isolated no-trust workspace | Narrow and policy-defined |
| Output | Candidate or exact blocker/setup manifest | `APPROVED_FOR_PROMOTION`, `NEEDS_REVIEW`, `QA_FAILED`, `QUARANTINED`, or `ROLLED_BACK` |
| Forbidden authority | Money, customer data, production secrets, rights/capability approval, traffic | Invent behavior, guess facts, add capabilities, self-approve promotion |

The split preserves diversity in the builder while keeping live releases deterministic. Unknowns become explicit work items, not guessed implementations. Deployment success is never equivalent to live traffic.

---

## 3. Prerequisites: build the platform before the builder

### 3.1 Round-5 platform sequence is mandatory

**[review] F-02/F-27 — Ordering correction:** platform work is not a final “integration” step for the mega agent. Round-5 Steps 1–8 are prerequisites. The reusable shipment ladder is then pure LLM → asynchronous HeyGen → real GPU/media. Only after those lanes work should Omo build the general extractor/research/refinement agent or run the four-project battery.

The required order is:

1. close unsafe paid/demo surfaces;
2. install production migrations and transactional state;
3. build authenticated `POST /v1/runs` and owner-only `GET /v1/runs/{run_id}`;
4. freeze public/private contracts, container spec, adapter ABI, registries, vocabulary, and hash rules;
5. build the deterministic compiler/runtime;
6. build the immutable release controller;
7. build signed Worker↔Modal, Neon/R2, callback, settlement, and reconciliation plumbing;
8. prove replay, crash, tenancy, artifact, cost, secret, cold/warm, and rollback safety;
9. ship one compiler-produced pure-LLM release manually;
10. ship one asynchronous HeyGen release;
11. benchmark and then ship one real GPU/media release;
12. only then build the mega agent and execute the frozen four-project epic.

A generic extractor may be explored earlier, but it cannot claim end-to-end acceptance or drive production before these prerequisites exist.

### 3.2 ADR stub: Neon is the founder's chosen paid state store

**Decision intent:** the founder chose **Neon** as the single paid-run system of record. That decision must be ratified in a future [`research/adr-paid-state-store.md`](adr-paid-state-store.md), which will explicitly supersede round 5's D1 statements.

**[review] F-03 — ADR requirement:** this blueprint records the founder's choice but does not pretend the operational decision is complete. The ADR must freeze:

- transaction isolation and the atomic create/replay + quote acceptance + reservation + ledger/run events + outbox transaction;
- compare-and-set transition semantics and unique effect IDs;
- Worker connection strategy, pooling limits, regional latency, timeouts, and fail-closed behavior;
- backup, point-in-time recovery, migration, failover, and reconciliation policy;
- removal of paid D1/in-memory/mock fallbacks and the rule against dual-write money authorities;
- whether D1 remains only a non-authoritative catalog/read cache.

No production migration or paid gateway implementation should proceed until this ADR is approved and round 5 is updated consistently.

### 3.3 Current `/api/run` is demo-only and unsafe for paid use

> **[review] F-04/F-05 — DEMO-ONLY WARNING:** the current `site/deploy/worker.js` `/api/run` route must not host paid or mega-built releases. It accepts client-supplied `user_id`, `system_prompt`, and token cap; calls the LLM directly; uses permissive CORS; has no durable idempotency contract; and records runs only after success. The current schema lacks tenants, random hashed API keys, immutable releases, traffic pointers, quotes, durable run IDs/state versions, reservations, outbox, provider events, artifacts, reconciliation, and the required append-only ledger.

`site/deploy/schema.sql`, `site/deploy/test-router.mjs`, and `site/deploy/wrangler.toml` reflect this demo contract and are not production migrations, paid-path acceptance coverage, or an R2 artifact plane. Before paid traffic, `/api/run` must have paid behavior disabled. The future `/v1/runs` gateway must derive identity from verified Clerk JWTs or random revocable hashed Omo keys, enforce restrictive production CORS, make release/prompt/model/price/resources server-owned, reserve before dispatch, and fail closed when production state is unavailable.

### 3.4 Frozen source packets are a parallel prerequisite

**[review] F-06/F-25/F-34 — Acceptance-input correction:** the four project names are not executable requirements. Exact packets are absent, “Woven” and “PadelBuddy” are ambiguous, and the cartoon input conflicts with positioning's story-based anchor. Before the battery is scheduled, check in a rights-approved `acceptance/sources.v1.json` or equivalent reviewed manifest with, for every project:

- immutable URL/path, commit/ref, and content hash;
- owner authorization and source/dependency license facts;
- exact promised input → output job and explicit out-of-scope behavior;
- golden fixtures, negative fixtures, quality rubric, and domain-owner approval;
- data/privacy/retention, voice/likeness/style, and commercial-use rights;
- required provider accounts/resources and bounded paid-test budget;
- expected artifact types, portability expectations, and acceptance owner.

Freezing these packets can happen while the platform slice is built. It must finish before project-specific implementation, not after the extractor invents a rubric.

### 3.5 Versioned platform-readiness gate

The future builder must read a signed, versioned `PLATFORM_READY` manifest covering the storage ADR, migrations, gateway, auth, contracts, registries, compiler/runtime, release controller, Worker↔Modal protocol, artifact plane, usage ledger, QA signer, and rollback drills. If absent or stale, it returns `PLATFORM_NOT_READY` without deploying or spending.

---

## 4. Planned hardcoded foundation and frozen contracts

The mega agent will build **on** this shared platform. It will not regenerate it for each workflow.

### 4.1 Fixed platform components

1. **Worker gateway:** future public POST/GET API, verified identity, tenant derivation, input validation, release selection, quotes, idempotency, reservation, outbox dispatch, bounded wait, webhook verification, checkpoints, and owner-only reads.
2. **Neon state and ledger:** future authority for tenants, key hashes, releases/traffic, quotes, run versions, outbox, reservations, provider events, artifact metadata, Stripe events, credit buckets, ledger effects, reconciliation, and QA evidence.
3. **R2 artifact plane:** future private artifact bytes, exact run/tenant-scoped keys, checksum/metadata, retention/deletion state, quarantine, and owner-authorized delivery.
4. **Identity and billing:** Clerk, random revocable Omo keys, Stripe top-ups, promo/purchased buckets, reservation/settlement/release, `402 insufficient_balance`, limits, and creator accounting.
5. **Modal runtime:** reviewed CPU, provider, native-media, hostile-sandbox, and GPU profiles plus typed adapters, validators, checkpointing, usage telemetry, R2 capabilities, retries, and secret bindings.
6. **Planned autopilot:** canonical validation, capability diff, deterministic compilation, staging deployment, QA, approval records, immutable registry, promotion, quarantine, and rollback.
7. **Release registry:** source/spec/compiler/runtime/image/dependency/model/cost/QA hashes, non-secret capability/credential fingerprints, deployment metadata, approvals, health, and rollback target.

### 4.2 Public and private API contracts

The planned public contract is shared by every workflow:

```http
POST /v1/runs
Authorization: Bearer <verified Clerk JWT or random Omo API key>
Idempotency-Key: <client-generated key>
Prefer: wait=8
Content-Type: application/json

{
  "workflow_slug": "ugc-script-studio",
  "input": { "...": "validated against the selected release schema" }
}
```

Same tenant/workflow/key and same canonical body returns the same run. The same key with a changed body returns `409`. Insufficient credits returns `402` before Modal dispatch. Warm completion may return `200`; otherwise `202` returns the durable Omo `run_id` and status URL. A foreign run or artifact returns non-enumerating `404`.

Before implementation, freeze JSON Schemas for submit/result/error/artifact resources and private signed dispatch, claim, checkpoint, usage, callback, settlement, and reconciliation envelopes. Every envelope needs version, tenant/run/release/request hashes, actor, nonce/expiry, signature rules, and replay semantics.

### 4.3 Artifact contract

**[review] F-07 — Missing-plane correction:** R2 references are not usable until the platform defines upload-initiate/finalize, exact object capabilities, ownership checks, checksum contract, stable authorized download, encryption, quarantine, and retention/deletion transitions. Capabilities must be run/tenant scoped, method limited, short lived, and bound to exact size/MIME/magic/archive rules. A provider URL is intermediate evidence, never successful delivery.

### 4.4 Container spec, adapter ABI, and vocabulary

The canonical spec must cover the fields in [`modal-container-plan.md` §3.3](modal-container-plan.md#33-minimal-executable-container-spec): source hash; image/runtime; CPU/RAM/GPU and scale limits; protected endpoint; secret and egress capabilities; strict input/output schemas; stable step IDs and DAG; typed bindings; adapter operations; timeout/retry/idempotency; output projection; tests; artifacts; and budget.

Bindings are limited to `$.input...`, `$.steps...`, `$.run...`, `$.spec...`, and explicit literals. No Python, shell, JavaScript, Jinja, arbitrary URL, Dockerfile, or source-authored install hook may execute from a spec.

**[review] F-10/F-28 — ABI and vocabulary correction:** freeze `adapter.v1`, `operation.v1`, `usage-event.v1`, `provider-ack.v1`, and `callback-event.v1` plus one error taxonomy. An operation record must define create/status/cancel, webhook verification, idempotency support/window, retry ownership, normalized errors, limits, residency, usage units, callback replay, and continuation. Normalize namespace, provider enums (`openai_compatible` versus `openai-compatible`), GPU names, endpoint names, and environment interpolation before compiling current fixtures. Existing container YAML files are migration tests, not canonical examples.

### 4.5 Release hashing and secret lifecycle

**[review] F-17 — One hash contract:** publish a canonical hash manifest with sorted paths, canonical serialization, normalized encoding/line endings, symlink policy, timestamp exclusions, and signature identity. The release hash covers source, canonical spec, prompts, schemas, capability manifest, compiler/runtime/template versions, dependency lock, base-image digest, adapter versions, model/weight digests, non-secret secret-binding identifiers, resource limits, artifact/retention policy, and cost-policy version.

**[review] F-18 — Secret correction:** secret values are never hashed or stored in candidates. Releases store a non-secret binding/version/fingerprint/capability ID. Secrets are least privilege per Modal Function, test access is brokered, rotation has overlap/revocation rules, and a behavior-changing credential rotation requires a new canary.

### 4.6 QA and evidence contracts

**[review] F-22 — Executable QA correction:** define `qa-policy.v1`, `fixture.v1`, `fault-plan.v1`, and `qa-report.v1`; one harness command; deterministic contract/security/billing/artifact validators; redacted provider record/replay; controlled fault points; concurrency driver; evaluator isolation; and CI-held evidence-signing keys. Signed QA means a canonical report hash signed by a named CI identity, not an agent assertion.

Required platform tests include 100 concurrent same-key calls, illegal CAS transitions, crashes after reservation/dispatch/provider send/provider acknowledgement/R2 write/validation/settlement, callback replay, tenant isolation, artifact validation, cost ceiling, secret canaries, cold/warm timing, and rollback.

### 4.7 Local-download execution contract

**[review] F-26 — Portability correction:** every paid workflow needs more than a README. Freeze a supported local runner, OS/architecture matrix, secret/config interface, provider substitution rules, model/weight acquisition and licenses, deterministic smoke command, artifact paths, and the definition of “same job” when a hosted-only provider is unavailable. The package includes the canonical workflow form, `SKILL.md`, prompts, schemas, tests, locks/SBOM/notices, supporting files, and instructions.

### 4.8 Proposed future repository layout

The following paths are a plan only. They are intentionally not created by this blueprint:

```text
scripts/
  mega-build.sh                         # planned candidate-build entrypoint

mega-agent/                             # planned; language choice unresolved
  cli
  orchestrator
  schemas/
    build-request.v1.json
    build-status.v1.json
    extraction-result.v1.json
    setup-manifest.v1.json
    build-report.v1.json
  extractors/                           # pinned repo, SKILL.md, document
  research/                             # loop, evidence store, brokered probes
  builder/                              # candidate materializer
  tester/                               # bounded refiner

autopilot/                              # planned release controller
  schemas/
    container-spec.v1.json
    provenance.v1.json
    capability-manifest.v1.json
    adapter.v1.json
    operation.v1.json
    qa-policy.v1.json
    fixture.v1.json
    fault-plan.v1.json
    qa-report.v1.json
  registries/
    adapters.json
    operations.json
    images.json
    packages.json
    models.json
    cost-units.json
  compiler/                             # pure: no network, shell, or secrets
  qa/
  state-machine
  policy
  release-controller

containers/omo-<slug>/                  # future generated candidate
  container.yaml                        # provisional serialization
  provenance.json
  capability-manifest.json
  setup-manifest.yaml
  release-hash-manifest.json
  modal_app.py                          # compiler output, never hand-edited
  worker-release.json                   # registry data, never public route code
  resolved.lock
  sbom.spdx.json
  README.md
  prompts/
  schemas/
  tests/
  qa/
```

The eventual Go/XML decision may rename source modules and canonical serialization without changing these logical boundaries.

---

## 5. Planned mega-agent behavior

### 5.1 Extraction output and provenance

Every extraction produces exactly three logical objects:

1. `container_spec_draft` — fields supported by evidence;
2. `provenance_map` — source location/hash, confidence, and inference method for every material field;
3. `unresolved[]` — missing contracts, operations, credentials, rights, quality rules, cost units, or artifact rules.

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

Unknown provider, model, operation, cost, host, package, binary, secret, schema, or right remains a compile blocker. A README claim is evidence, not resolution.

### 5.2 Agentic research loop

Each unresolved item gets at most four evidence passes:

1. current official provider docs, pricing, OpenAPI, limits, auth, webhook, retention, and terms;
2. official SDK source, examples, changelog, and versioned schemas;
3. supplied-source and public-code pattern search for mappings, errors, dependencies, and tests;
4. the smallest authorized sandbox probe with redacted data, exact timeout, one-operation credentials, idempotency, and a preapproved budget.

Resolution requires enough evidence to fill a typed field and create a verification test. Third-party tutorials may supply leads but cannot be sole authority for paid operations.

### 5.3 Account and setup boundary

The agent may prepare setup instructions, open provider documentation in an isolated browser, validate an existing staging capability, configure authorized non-identity resources, and run a bounded test. A human must prove identity, accept terms/DPA, complete CAPTCHA/MFA/KYC/Meta verification, authorize payment, grant production scope, and approve data/voice/likeness/style/commercial rights.

Every build emits `setup-manifest.yaml`, even when empty. It records account purpose, signup URL, human steps, required secret name/scope, post-key actions, validation command, approvals, and limits. Example future resume command:

```bash
scripts/mega-build.sh --resume mb_01... --check-setup
```

Secret values enter the approved manager directly, never reports, shell history, prompts, fixtures, specs, images, or Git.

### 5.4 Hostile-source ingestion and prompt separation

**[review] F-08/F-19/F-20 — Containment correction:** source material is hostile data. Acquisition uses a separate no-trust Modal workspace/project with no production or staging provider secrets, no shared volumes, strict CPU/RAM/process/time/disk/file/count/depth limits, and default-deny egress through an audited proxy. Probes get short-lived, one-operation brokered credentials.

The ingest service must pin and verify a commit/content hash; disable credential helpers, hooks, submodules, LFS filters/smudge, and repository-configured helpers by default; bound history/blobs/files/archives; reject path traversal, unsafe symlinks, nested repositories, and archive bombs; quarantine scan; and use explicitly scoped private-repo tokens.

The orchestrator separates instructions from content, taints source-derived strings, forbids source-derived tool arguments without typed approval, and uses brokered browser/network allowlists. Runtime prompt templates delimit untrusted repository/chat content and explicitly prohibit tool invocation from that content.

### 5.5 Bounded research and refinement

- Initial candidate plus at most **three revisions**.
- At most four evidence passes and two non-mutating probes per unresolved item.
- Discovery spend defaults to `$0.00`; a human may approve up to `$0.25` for one provider mutation.
- Default paid QA is the smaller of `$1.00` and `qa.max_paid_test_usd`.
- One paid media fixture per exact `(release_hash, suite_version, fixture_set_hash)`.
- The agent may fix wording, bindings, normalization, adapter parameters, tests, or declared resources; it may not weaken contracts, quality, rights, security, or cost gates.

**[review] F-23 — Honest QA budget:** `$1` is a default stop, not a promise that media QA fits. Separate free deterministic tests, recorded-provider replay, and one paid canary. If a release-specific suite needs more, return `QA_BUDGET_REQUIRED` with the exact evidence and requested cap; only a human may raise it.

After limits are reached, return `RESEARCH_BLOCKED`, `SETUP_REQUIRED`, `CAPABILITY_REVIEW_REQUIRED`, `RIGHTS_REVIEW_REQUIRED`, `QA_BUDGET_REQUIRED`, or `QA_FAILED` with exact evidence and resume data.

---

## 6. Planned one-shot candidate pipeline

This pipeline is implemented only after `PLATFORM_READY` exists.

### 6.1 Future operator and machine contract

Planned invocation:

```bash
scripts/mega-build.sh <github-url|local-repo|workflow-doc> \
  --slug <workflow-slug> \
  --environment staging \
  --non-interactive
```

Allowed intent flags include `--source-ref`, `--fixture-set`, `--max-paid-test-usd`, and `--resume <build_id>`. They cannot select buyer price, live release, provider operation, prompt/model, production credentials, or resources above policy.

**[review] F-15/F-32 — CLI and authority correction:** freeze `build-request.v1` and `build-status.v1`, stable exit codes, JSON stdout, diagnostic stderr, durable build-event storage, atomic checkpoints, CAS resume, concurrent-build locks, cancellation, source-hash verification on resume, and persistent paid-test dedupe before writing the shell wrapper. A staging/non-interactive build can end at `APPROVED_FOR_PROMOTION`, never `LIVE`.

Expected statuses:

- `APPROVED_FOR_PROMOTION` — immutable candidate, signed QA, approved price, and rollback plan; no traffic moved;
- `SETUP_REQUIRED`, `CAPABILITY_REVIEW_REQUIRED`, `RIGHTS_REVIEW_REQUIRED`, `PRICE_REVIEW_REQUIRED`, or `QA_BUDGET_REQUIRED`;
- `PLATFORM_NOT_READY` — missing/stale platform manifest;
- `QA_FAILED` or `RESEARCH_BLOCKED` — bounded failure with evidence and resume token;
- `CANCELLED` — safe checkpoint with no new spend.

Production promotion is a separate release-controller transition consuming a narrowly scoped signed approval containing actor, release hash, price, traffic percentage, environment, expiry, and nonce.

### 6.2 Candidate-build steps and gates

| # | Future action | Artifact | Gate |
|---:|---|---|---|
| 1 | Verify `PLATFORM_READY`, build request, frozen source identity, and authorization. | `build-request.json` | Platform/version/source supported; exact immutable ref and owner recorded. |
| 2 | Ingest into the hostile-source workspace and fingerprint every asset. | `source-manifest.json` | Hashes, paths, author, rights state, size limits, and quarantine result exist; host ran no source code. |
| 3 | Extract promised job, inputs/outputs, steps, examples, quality claims, human actions, dependencies, and runtime clues. | Draft spec, `provenance.json`, `unresolved.json` | Every required field has evidence or an unresolved item; display prose is not schema. |
| 4 | Research unresolved items with official evidence and bounded probes. | `research-report.json` | Operation, schemas, auth, rates, callbacks, hosts, license, and test method resolve or block; no guessed paid step. |
| 5 | Emit/check setup and rights manifests; validate brokered staging capabilities after human action. | `setup-manifest.yaml`, rights attestations | Accounts, resource IDs, consents, and budget present; no secret values in artifacts. |
| 6 | Diff requested capabilities against approved adapter/image/package/model/host/secret/resource registries. | `capability-manifest.json` + diff | Zero unreviewed expansion; new capability becomes a reviewed proposal and blocker. |
| 7 | Materialize DAG, schemas, prompts, approved adapter config, artifacts, tests, cost inputs, and local package. | Candidate bundle | DAG/bindings/final outputs valid; retry/idempotency/timeouts/resources/egress/artifacts bounded; unresolved empty. |
| 8 | Compile twice with the deterministic compiler; emit lock/SBOM/notices and hash manifest. | Generated bundle + reproducibility report | Byte-identical clean compiles; no arbitrary execution/unpinned dependency; `STATIC_VALIDATED`. |
| 9 | Run offline/recorded QA and bounded repair: contract, negative, injection, replay, retry, cost, artifact, quality, and security. | Signed local QA evidence | Three happy plus six negative/failure fixtures unless stricter; invalid input causes zero spend; duplicate effect prevented. |
| 10 | Ask planned autopilot for staging deployment and real HTTP tests across Worker→Modal→Neon/R2. | Staging release + signed QA | Auth, tenancy, `200/202`, callbacks, artifacts, usage, failures, cost, reconciliation, and rollback pass. |
| 11 | Compute guarded hosted price and independent demo/download surfaces. | `pricing-report.json` + approval | Persisted physical evidence; no unknown cost; human approves initial price and any exception. |
| 12 | Record immutable candidate and promotion request. | Final build report | Status is `APPROVED_FOR_PROMOTION`; genesis rollback-to-disabled or prior healthy target tested. |

After a separate human-authorized promotion, the public example will use the shared endpoint:

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

No buyer-facing report exposes a Modal endpoint or identifier.

---

## 7. Four-project acceptance epic

The battery is a later epic-level exit criterion, after the platform, pure-LLM, async-provider, hostile-sandbox, and real GPU/media reference lanes exist. All numbers below are discovery envelopes, not buyer quotes.

### 7.1 Acceptance packet gate

No project enters implementation until its frozen packet (§3.4) is checked in, rights approved, and signed by its domain owner. A safe blocker is correct behavior but does not count as a green deployment.

### 7.2 Cognition WhatsApp analyser

**Provisional job:** authorized WhatsApp export → grounded conversation analysis with evidence linked to normalized message IDs. Live WhatsApp ingestion is a separate capability.

| Area | Provisional contract to freeze |
|---|---|
| Inputs | Exact R2 `.txt`/approved `.zip` reference; analysis-goal enum; timezone/language; aliases; consent attestation. No arbitrary local path/URL. |
| Outputs | Typed summary/themes/timeline/metrics; traceable citations; limitations/actions; optional private HTML/PDF. No diagnosis or high-stakes conclusion without reviewed scope. |
| Steps | Artifact validation → deterministic Android/iOS parser → normalize/dedupe → PII policy → chunk → LLM map/synthesis → evidence verifier → report. |
| Capabilities | CPU/native parser + LLM for export v1. Meta app/webhook/phone/media are separate reviewed capabilities. |
| Cost envelope | `$0.02–$0.70` by size/model/passes. The `$1` positioning anchor and 80% formula conflict at the top of this range; benchmark before price. |
| Tests | Android/iOS, multiline/Unicode/system/media placeholders, duplicate times, 1/10/100k messages, injected instructions, PII/retention, citations, cross-tenant denial, malformed archive before spend. |

**Green gate:** founder-approved export returns a schema-valid report with sampled claims traced to source messages, no unauthorized transcript retention, accepted cost ceiling, and tested deletion.

### 7.3 Woven

**Provisional job:** unknown until the exact packet arrives. If it is an analytics/change-agent repo, use the shape below; otherwise replace it rather than adapting the wrong product.

| Area | Provisional contract to freeze |
|---|---|
| Inputs | Pinned repo/snapshot; task; optional sanitized dbt metadata; report-only versus patch-proposal policy. |
| Outputs | Impact graph, file/model/column evidence, test plan, downloadable diff, risk summary. No merge, warehouse mutation, or Slack post initially. |
| Steps | Static ingest → license/dependency scan → metadata graph → LLM analysis → evidence validator → isolated patch/test → R2 report bundle. |
| Capabilities | Git read, native Git/dbt/parser, LLM, optional read-only warehouse. Notification is separate. |
| Cost envelope | `$0.02–$1.00`; too broad for a quote until repo size and benchmark are bounded. |
| Tests | Malicious README, symlink/path escape, submodule/filter refusal, secret scan, invalid graph, no-network mode, deterministic diff, build failure, read-only enforcement, evidence links. |

**[review] F-09 — Sandbox boundary:** untrusted project code never enters a normal listing container. A separate approved sandbox ABI accepts source snapshot + declared build/test plan and returns patch/log/test artifacts, with no repo token, secrets, upstream write, host mount, shared volume, or open network.

**Green gate:** the exact fixture completes through the public API, returns the promised evidence/artifact, and proves source instructions cannot obtain secrets or write upstream.

### 7.4 PadelBuddy

**Provisional job:** positioning's player-input hosted utility, not a camera/highlight product. The frozen source must resolve product identity.

| Area | Provisional contract to freeze |
|---|---|
| Inputs | Opaque player IDs, ratings, availability/preferences/history, court/time constraints, and operation enum such as `balance_teams`. |
| Outputs | Feasible teams/plan, score/confidence, trade-offs, alternatives, and optional notification preview. |
| Steps | Validate → normalize → pinned optimizer/solver → optional explanation → feasibility verifier → result; notification is a separate idempotent effect. |
| Capabilities | CPU + pinned solver, optional LLM. Messaging/calendar/booking require separate approval. Camera interpretation requires an entirely different video/hardware contract. |
| Cost envelope | Pure matching `$0.001–$0.05`, normally `$0.10` hosted floor; video could be `$0.10–$2.00+`. |
| Tests | Odd/even counts, ties, impossible constraints, fairness bounds, deterministic seed, load, malformed IDs, cross-tenant history, replayed notification, solver timeout, objective regression. |

**[review] F-24 — Domain-state decision:** before acceptance, decide whether history/club state is supplied per run, stored as tenant artifacts, or managed by a versioned state adapter. Freeze authorization, schema migrations, consistency, deletion, and cross-tenant tests.

**Green gate:** founder fixtures satisfy every hard constraint and approved balance metric; replay is stable; any notification sends at most once.

### 7.5 Japanese-style cartoon maker

**Provisional job:** authorized voiceover → short rights-safe Japanese-inspired cartoon video. The frozen packet must resolve whether the founder's newer voiceover request supersedes positioning's story → named-style animation anchor.

| Area | Provisional contract to freeze |
|---|---|
| Inputs | Exact R2 voiceover; optional transcript; curated rights-safe style preset; ratio/resolution; authorized character/reference assets; subtitle/motion settings. |
| Outputs | Omo-owned MP4, storyboard, shot/frame manifest, SRT, thumbnail, checksums, and media metadata. |
| Steps | MIME/magic/`ffprobe` → ASR if needed → timing/storyboard → image/local-GPU generation → consistency/rights/safety → animation → FFmpeg mux/subtitles → decode/A-V/quality → R2. |
| Capabilities | LLM, ASR, licensed image/local GPU model, optional video provider, FFmpeg/ffprobe, R2. TTS is not default because voiceover is input. |
| Cost envelope | `$0.10–$1.50`. A `$0.30` price under the 80% guard requires `C_guard <= $0.06`; otherwise optimize or raise the price. |
| Tests | 15/30/60s, MP3/WAV, corrupt/oversized media, duration, decode, audio, A-V/subtitle sync, speech completeness, consistency, rights/consent, unsafe prompt, duplicate mutation, GPU OOM/preemption, ownership/rollback. |

**Green gate:** approved audio yields a private Omo-owned MP4 that decodes, preserves audible content, passes duration/A-V/style/consistency/rights gates, and remains below the accepted ceiling.

### 7.6 Battery-wide exit criteria

Each frozen project must have:

- no unresolved technical fact and recorded approval for every non-technical decision;
- one immutable manually promoted canary through the shared `POST /v1/runs` and owner-only GET;
- at least three happy and six negative/failure fixtures plus project-specific quality/artifact gates;
- concurrent replay proving one durable run/effect and crash reconciliation;
- persisted actual usage/cost, human-approved guarded price, and pre-call hard ceiling;
- signed QA, R2 ownership where applicable, and a tested rollback target;
- a local-download package meeting §4.7.

---

## 8. Pricing and cost automation

### 8.1 Evidence before formula

`site/deploy/cost-model.mjs` is seed evidence only. Its `5x` launch multiplier, `$0.10` floor, unknown-model/API fallbacks, generic `modal_gpu_30s`, incomplete costs, and nearest-cent rounding are not production pricing.

**[review] F-11/F-12 — Measurement correction:** `5C` and `C / (1 - 0.80)` are algebraically equal, but current inputs are incomplete. Build a versioned physical-rate registry and normalized usage ledger for Modal queue/boot/init/CPU/RAM/GPU/idle, shared-concurrency allocation, provider invoice units, R2/Cloudflare, retries, rejected outputs, refunds, and accepted-output cohorts. Reconcile invoices. Mocks and discovery ranges never produce a paid quote; unknown units fail closed. Use integer/nanodollar arithmetic and round buyer prices upward to cents.

For every immutable release:

```text
C_guard = max(
  C_static,
  C_success_p95,
  max(C_delivered_7d, C_delivered_30d) * (1 + tail_reserve)
)

buyer_price_floor = ceil_to_cent(
  max($0.10, C_guard / (1 - 0.80))
)
```

Tail reserve is `10%` for mature LLM, `15%` for remote media, and `20%` for GPU until 30 clean days justify a reviewed change.

| `C_guard` | Guarded hosted floor |
|---:|---:|
| `$0.001` | `$0.10` |
| `$0.06` | `$0.30` |
| `$0.14` | `$0.70` |
| `$0.70` | `$3.50` |

Round-5 planning anchors remain: pure-LLM Shipment #1 at `$0.10` with `max_cost=$0.002`; HeyGen 15s beta at `$0.70` provisional with `$0.14` ceiling; GPU price only after real accepted-output benchmarking. Current provider/rate facts must be refreshed at release time.

### 8.2 Payment and creator economics

**[review] F-13 — Economics correction:** percentage payment fees cannot simply be placed inside `C_static`, because they depend on price. The pricing report must solve them algebraically and show taxes/refunds separately. For third-party workflows:

```text
positive_creator_margin = max(0, buyer_price - direct_cost - fixed_fee
                                  - percentage_fee * buyer_price
                                  - approved variable reserves)
creator_payout = 0.85 * positive_creator_margin
omo_contribution = 0.15 * positive_creator_margin
```

The 80% direct-cost guard is a safety floor, not a promise of 80% Omo contribution after creator payout. The report shows direct-cost guard margin and post-creator Omo contribution. First-party workflows retain the full positive contribution.

### 8.3 Quote, reservation, and real cost ceiling

A future 10-minute server-authored quote stores `quote_id`, `release_hash`, `price_cents`, `reserve_cents`, `estimated_cost_nanos`, `max_cost_nanos`, `cost_version`, `target_margin_bps`, and `expires_at`. Repricing never changes an accepted quote.

**[review] F-14 — Ceiling correction:** `max_cost_nanos` is not made hard by measuring after spend. Before every provider mutation or compute phase, debit a conservative unit bound from the remaining execution budget; reject admission when the bound does not fit. Local compute must be interruptibly metered, and each adapter must declare a provider maximum-charge guarantee. `price_cents` is buyer charge, `reserve_cents` is the credit hold, and `max_cost_nanos` is the maximum permitted direct execution spend across all retries.

Default `AUTO_PRICE_CEILING_CENTS = 500` (`$5/run`). First price above `$5`, increase above `25%`, or a range-only guard returns `PRICE_REVIEW_REQUIRED`. Provider/workflow/day/workspace budgets and kill switches remain outer limits.

### 8.4 Independent product surfaces

**[review] F-30 — Surface correction:** replace mutually exclusive `priceLadder` behavior with independent fields:

- `demo`: optional zero-price lead magnet with strict quota/sponsor budget and no unbounded provider spend;
- `download`: value-priced portable package, with the current `$39 one-time` only a storefront default;
- `hosted_run`: never below the guarded floor, optionally raised by approved outcome value.

Every paid workflow may expose both download and hosted doors as positioning requires.

---

## 9. Safety, rights, and release invariants

### 9.1 Non-negotiable runtime rules

1. Server-verified identity supplies `tenant_id`; client `user_id` is rejected or ignored.
2. The server owns release, prompt, model, operation, price, retry policy, resources, ceiling, and artifact destination.
3. One `(tenant_id, workflow_slug, idempotency_key)` binds one request hash to one Omo run; changed body is `409`.
4. Delivery is at least once; effects are idempotent and reconciled. Never promise distributed exactly once.
5. No billable Modal/provider work occurs before durable quote acceptance and reservation.
6. Every transition/effect uses unique IDs, tenant predicates, and compare-and-set rules.
7. Neon is intended durable business truth after ADR ratification; Modal state is execution evidence, not order history.
8. Media success requires Omo-owned R2 bytes, checksum, MIME/magic, decode, metadata, and quality validation.
9. Async providers checkpoint and end work, then resume through verified callback or short rescheduled task; no 15-minute sleeping production container.
10. Unknown or expanded provider, operation, model/weight, package, native binary, image, secret, host, callback, artifact, retention, GPU, or ceiling enters human capability review.
11. Deploy and QA do not move traffic; only a recorded approval and traffic-pointer CAS do.
12. Automatic promotion remains disabled until one manual LLM, remote-provider, and GPU release each has 30 clean days, rollback/quarantine drills, and zero unresolved billing reconciliation.

### 9.2 Rights and compliance

**[review] F-21 — Rights correction:** create machine-readable attestations and policy for source, dependencies, model weights, datasets, media, voices, likenesses, and styles; an SPDX compatibility matrix; NOTICE/source-offer generation; commercial-use rules; exception owner/expiry; and removal procedure. Named living artists/studios and unclear commercial rights require counsel/owner approval. Download bundles include required notices and source obligations.

### 9.3 Rollback and promotion

**[review] F-16 — Genesis rollback:** a first release has no prior healthy release. Its rollback target is `disabled/zero-traffic`; later releases can restore the retained prior hash. Both paths are drilled. In-flight runs remain pinned to their original release hash and accepted quote.

Safe automation may pause, quarantine, or execute an already authorized rollback. It may not grant itself recovery from correctness/security quarantine or production promotion authority.

### 9.4 Security control summary

| Risk | Builder control | Planned autopilot/runtime gate |
|---|---|---|
| Prompt injection | Hostile content separation, taint, no source-driven tools | Typed prompts, capability broker, injection fixtures |
| Secret exposure | No broad secrets; redaction; brokered probe | Least-privilege versioned bindings; log/canary scan; rotation |
| Supply chain | Bounded static ingest; separate sandbox | Allowlisted pins/images/binaries; lock, SBOM, license/vulnerability gate |
| Egress | Default-deny audited proxy | Adapter-enforced scheme/host/path; undeclared host fails compile |
| Cost/retry | Physical bounds, dedupe, bounded revisions | Reserve before dispatch; pre-call budget; effect IDs; kill switches |
| Tenancy | Synthetic builder tenants only | Auth-derived tenant on every read/mutation; foreign resource `404` |
| Bad artifact | Real fixture and verifier | Exact R2 key, checksum/bytes/MIME/magic/decode/quality |
| Self-grading | Deterministic checks + separate evaluator | Judge cannot override schema, rights, artifact, security, or cost |

---

## 10. Ordered roadmap and milestone gates

### Milestone 0 — Decisions and acceptance inputs

Approve the Neon ADR, resolve Go/XML/canonical vocabulary, freeze public/private/artifact/adapter/QA/hash/local-run contracts, and acquire the four rights-approved source packets.

**Exit:** decision records approved; exact packet hashes and owner rubrics exist. No mega-agent implementation.

### Milestone 1 — One vertical platform slice

**[review] F-27 — Re-scoped milestone:** close paid `/api/run`; install numbered Neon migrations; build verified public POST/GET; atomic quote/reservation/outbox; compiler-produced pure-LLM Modal release; signed checkpoints/actual usage; settlement; manual canary; rollback-to-disabled.

**Exit:** 100-way same-key replay creates one run/reservation/outbox/effect; changed body is `409`; cross-tenant reads are non-enumerating; invalid input spends zero; `max_cost=$0.002`; actual token and Modal phase costs persist; manual promotion and genesis rollback pass.

The mega agent itself is not part of Milestone 1.

### Milestone 2 — Asynchronous provider reference lane

Implement the full adapter ABI and HeyGen v3 create/callback-or-resume/idempotency/R2 path. Use one real 15-second invite beta, `$0.70` provisional price, `$0.14` cost ceiling, first-20 human review, and no sleeping poller.

**Exit:** replay causes one render; missing callback reconciles without a second render; owned 9:16 MP4 decodes, has audio, and meets duration/claim gates; kill switches work.

### Milestone 3 — Real GPU/media reference lane

Replace mock output with licensed pinned weights and real pixels. Benchmark load/init, variants/batching, GPU/CPU/RAM seconds, OOM/preemption, R2 upload, fidelity/safety, and accepted-output yield offline before price or promotion.

**Exit:** reproducible licensed model; real outputs pass deterministic and human rubric; p50/p95 and delivered cost support an approved formula price; manual canary and rollback pass.

### Milestone 4 — Mega-agent MVP

Only now create the planned builder scaffold. Support one source kind at a time: pinned local/Git source, then `SKILL.md`, then documents/research. Implement durable CLI/resume, extraction/provenance/unresolved, bounded official research, setup/rights blockers, capability diff, candidate materialization, and three-revision QA.

**Exit:** a frozen reference source produces a reproducible candidate and `APPROVED_FOR_PROMOTION` through the already-proven platform. The build command cannot move traffic.

### Milestone 5 — Four-project acceptance epic

Run Cognition WhatsApp analyser, exact Woven, exact PadelBuddy, and the resolved cartoon-maker packet only after their required LLM, async, sandbox, domain-state, artifact, and GPU lanes exist.

**Exit:** every project satisfies §7.6 through the shared API. This is the mega-agent program's generality proof, not Milestone 1.

---

## 11. Explicitly deferred work

Defer until the above evidence demands it:

1. visual editor and any unratified XML/YAML interchange beyond the frozen canonical format;
2. Cloudflare Workflows as anything beyond optional outbox/callback relay;
3. shared multi-workflow, per-user Modal Apps/Secrets, or buyer provider keys;
4. arbitrary “run this repo,” generated Worker routes, Dockerfiles, install hooks, shell, or runtime code;
5. automated identity/KYC/CAPTCHA/MFA/terms/payment/rights actions;
6. long provider pollers, generic cost fallbacks, `modal_gpu_30s`, or global `1.25x` repricing;
7. catalog-wide warmth, speculative regions/GPU residency, or automatic production promotion;
8. hardware PadelBuddy, live WhatsApp ingestion, Woven writes, or remote cartoon video unless frozen scope requires them;
9. broad creator ingestion/payout automation before one-run economics and four-source proof;
10. fine-tuning or model training before accepted-output evidence justifies it;
11. claims that ingestion, compilation, or deployment alone makes a workflow “proven.”

---

## 12. Appendix A — Top 10 next actions

These actions incorporate and reorder the independent review so decisions, source truth, and the platform slice precede mega-agent work.

1. **Ratify storage authority.** Write `research/adr-paid-state-store.md` documenting Neon as founder-chosen paid truth and covering isolation, atomic create/reserve/outbox, CAS, Worker pooling/latency, failover/PITR, migrations, reconciliation, and removal of paid fallbacks. Update round 5 consistently.
2. **Acquire and freeze the four source packets.** Record immutable URL/ref/hash, authorization, license/rights, exact job, fixtures, accounts, artifact/privacy rules, and owner rubric. Resolve story versus voiceover, optimizer versus camera, and exact Woven identity.
3. **Deliver Milestone 1's platform slice.** Authenticated POST/GET, atomic quote/reservation/outbox, compiler-produced pure-LLM Modal release, actual usage, settlement, manual canary, and rollback-to-disabled.
4. **Close the unsafe Worker surface.** Disable paid `/api/run`, client identity/prompt/model/token authority, arbitrary lazy grants, permissive production CORS, and paid mock/D1/in-memory compatibility. Define stable `/v1/runs` errors and auth/tenant/idempotency tests.
5. **Create numbered production migrations and transactional state.** Add tenants, key hashes, releases/traffic, quotes, runs/versions, outbox/events, reservations, provider jobs/events, artifacts, Stripe events, credit buckets, ledger, and QA evidence; prove install/upgrade/replay/crash/reconciliation.
6. **Freeze public/private/artifact/CLI contracts.** Define signed envelopes, state/actor/approval tables, `PLATFORM_READY`, artifact capabilities, build schemas, exit codes, durable events, cancellation, and resume semantics before the shell entrypoint.
7. **Freeze the canonical spec, vocabulary, registries, adapter ABI, and hash rules.** Resolve Go/XML versus provisional YAML, migrate current containers as compatibility fixtures, and make every unknown fail closed.
8. **Build compiler/runtime/release controller and the shipment ladder.** Prove byte-identical pure-LLM first, asynchronous HeyGen second, and licensed real GPU third through the final gateway, each manually promoted and rollback-tested.
9. **Build security, rights, cost, and evidence substrates.** Hostile-source workspace, default-deny proxy, brokered credentials, bounded ingest, SBOM/license/rights policy, QA schemas/VCR/fault hooks/signing, normalized usage/rates, guarded pricing, ceiling semantics, invoice reconciliation, and creator economics.
10. **Add the mega agent incrementally, then run the battery.** Pinned source first, then `SKILL.md`, then documents/research; blockers before refinement; four exact projects only after LLM, async, sandbox, domain-state, artifact, and GPU/media lanes exist.
