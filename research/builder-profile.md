# Omo Builder Hermes Profile

**Status:** Profile created and locally usable for authorized research, spec, compile, test, verify, generator-fix, and pricing work. Production promotion remains human-gated.  
**Profile:** `omo-builder`  
**Profile root:** `/Users/yifan/.hermes/profiles/omo-builder`  
**Created:** 2026-08-14 via the Hermes CLI, not by cloning another profile.

## What was installed

The profile was created with:

```bash
hermes profile create omo-builder --no-alias \
  --description "Isolated Omo workflow builder: turns approved SKILL.md and SOP sources into tested, priced release candidates; never self-promotes to production."
```

Hermes created a fresh profile and synced its standard bundle of 82 skills. It did not clone `omo-space`, did not create a wrapper alias, did not start a gateway, and did not install a cron job, daemon, or system service. The current Hermes version records the role description in `profile.yaml`; it has not generated a profile `config.yaml` because no model/provider setup was run. Hermes reports that the profile has no API keys configured.

Core files:

- `/Users/yifan/.hermes/profiles/omo-builder/SOUL.md` — the eight-section operating contract.
- `/Users/yifan/.hermes/profiles/omo-builder/memories/MEMORY.md` — sanitized Omo builder context. It intentionally excludes credential locations, personal data, permissive deployment notes, and other-profile instructions from `omo-space` memory.
- `/Users/yifan/.hermes/profiles/omo-builder/profile.yaml` — Hermes role description.
- `/Users/yifan/.hermes/profiles/omo-builder/skills/` — standard local Hermes skill bundle.

The profile can be opened explicitly without changing the sticky default:

```bash
cd /Users/yifan/marketplace
hermes -p omo-builder chat
```

## The SOUL's eight sections

| Section | Contract |
|---|---|
| 1. My mission | Approved `SKILL.md`/workflow/SOP to proven, priced release candidate; one shot where possible; never self-promote. |
| 2. I understand Omo before I build | Read canonical repo state first and preserve the generated `modal_app.py`, schema-driven UI/result, canonical manifest/pricing, and fail-closed house pattern. |
| 3. My authorized inputs and intake | Support the protected upload queue and Harry's manual-path workflow; hash source and treat it as hostile data. |
| 4. My builder loop | Source packet → research → spec → materialize → build → test → verify → fix the generator/shared layer → bounded rerun → price → handback. |
| 5. I research providers and prepare signups | Research official requirements and emit exact setup instructions; Harry owns all identity, terms, verification, password, payment, and dashboard steps. |
| 6. I price, stage, and return | Use canonical current rates/markup/floor; separate local, PR/CI, Modal, Worker, billing, publication, and traffic gates. |
| 7. My safety and least privilege | Embed the canonical irreversible-action rules verbatim, prohibit secret access, and enforce the private illustrated-story exclusion. |
| 8. My typed result contract and current gates | End every run as `READY`, `BLOCKED-<TYPED_REASON>`, or `NEEDS-HARRY`, with exact evidence and resume instructions. |

## What the profile can and cannot do

The profile is a build-time control-plane agent, not a buyer-time runtime and not a production release controller.

It can, when the source and repository write are authorized:

- read the repository's current goal/state and Omo conventions;
- fingerprint and inspect approved source as untrusted data;
- research official provider/API/pricing/setup requirements;
- create or refine a reviewed runtime profile, strict schemas, fixtures, negative tests, capability requests, and marketplace metadata;
- run the deterministic compiler and local test/verification/pricing gates;
- fix reusable generator/compiler/runtime/adapter defects and regenerate;
- prepare a local branch/diff and, only when explicitly authorized, a remote PR;
- return a typed candidate, blocker, or exact Harry handoff.

It cannot without Harry's explicit, specific approval:

- create accounts, accept terms, handle CAPTCHA/MFA/KYC, log into dashboards, type credentials, or authorize payment;
- spend money or run paid tests;
- send messages, publish, push to a remote, open a remote PR, merge, deploy, migrate, change live configuration, run a production canary, or move traffic;
- read, print, copy, hash, or move `.env`, token, key, password, cookie, or credential files;
- modify another Hermes profile or install a daemon/service;
- turn a missing provider, invalid result, renderer gap, unpriced cost, or failed test into a placeholder success.

### Credential and isolation boundary

No existing profile config, `.env`, auth state, session, gateway, cron state, or credential file was cloned into `omo-builder`. No Cloudflare, Neon, Stripe, Modal, GitHub, provider, messaging, or production credential was added. The gateway is stopped and no profile alias was added.

Hermes profile isolation is not an operating-system sandbox: a process can inherit variables from the shell that launches it, and the CLI explicitly warns that a keyless profile can inherit shell credentials. Therefore the operational launch contract is an allowlisted environment containing only the minimum build-worker values needed for the queue (`BUILD_WORKER_BASE_URL`, opaque `BUILD_WORKER_TOKEN`, private review-root/lock/time-limit values) plus separately approved, narrowly scoped staging capabilities. Do not start this profile from a broad production shell environment. Values remain opaque and must never enter prompts, logs, command arguments, memory, or repo files.

## Intake wiring

### Upload queue

The intended queue path is:

```text
signed-in creator
  -> POST /api/submit
  -> Worker validates public Markdown as untrusted data
  -> 202 queued (same creator + same source is idempotent)
  -> BUILD_WORKER protected claim: queued -> processing
  -> tools/host-skill/process-submissions.py validates, hashes, classifies
  -> new valid slug without reviewed profile:
       needs_review / reviewed_profile_required
  -> source persisted only under an owner-owned 0700 review root
       as exclusive-create 0600 SKILL.md; hash rechecked
  -> tools/host-skill/automation/dispatch-queued-submission.py
       passes only submission ID, slug, SHA-256, and verified private path
  -> hermes -p omo-builder
  -> builder produces reviewed profile + generated candidate + tests + price
  -> queue/release adapter records exact state and evidence
```

The source Markdown is never placed in the dispatcher prompt, command arguments, or logs. `process-submissions.py` does not itself launch Hermes; the separate dispatcher supplies that bridge.

Repository automation assets exist at:

- `tools/host-skill/automation/dispatch-queued-submission.py`
- `tools/host-skill/automation/omo-builder-dispatch.service`
- `tools/host-skill/automation/omo-builder-dispatch.timer`

They are Linux deployment templates and were **not** installed or enabled by this work. Their current server paths and environment must be reviewed for the target host, the private review root must pass its owner/mode/symlink checks, and installation is a separate system-state action requiring Harry's approval. Do not claim queue-to-profile wake-up is operational merely because the templates and local profile exist.

Current queue states are `queued -> processing -> needs_review -> ready_for_deploy -> ready_for_publish -> deployed`. Current release phases include `compiled`, `pr_open`, `ci_passed`, `merged_verified`, `promoted`, and `failed`. A `READY` handback must name the exact queue and release phase.

### Manual path

Harry can start the full candidate loop by opening the profile in the repository and supplying an approved local path, for example:

```text
Build the approved workflow at /absolute/path/to/SKILL.md through the full
local source/research/spec/compile/test/verify/fix/price loop. Do not push,
deploy, publish, spend, access secrets, or create accounts. Return a typed result.
```

The builder verifies a regular file and SHA-256 before treating the source as authorized data. A manual path authorizes candidate work only; it does not silently authorize rights decisions, spend, remote writes, deployment, publication, or traffic.

## Build, test, verify, fix, and price

Today's executable local path is `tools/host-skill/host.py`. For a reviewed single-LLM workflow it generates schemas, prompt assets, `modal_app.py`, fixtures, contract tests, manifests, capability analysis, and pricing evidence. The profile must keep the generated container reproducible. If generated behavior fails a contract, it fixes the generator/compiler/runtime template/shared adapter or the reviewed source profile, regenerates, and reruns the affected gates; it does not hand-edit generated output to fake green.

The required quality layers are:

1. source identity, authorization, provenance, and rights/setup completeness;
2. bounded Draft 2020-12 input/output schemas and negative cases;
3. safe real local fixtures and semantic sanity against the source promise;
4. generated contract, host/compiler, repository, and security tests;
5. provider/usage evidence when a separately approved canary is available;
6. artifact open/decode/MIME/magic/checksum/ownership checks for artifact workflows;
7. cost/latency/failure evidence and canonical pricing;
8. exact handback state, remaining gates, and rollback target.

For the current lane, pricing is computed from `site/deploy/cost-model.mjs`, which currently applies a 5x launch markup and a $0.10 floor. The file, not memory or copied numbers, is canonical. Unknown provider, compute, storage, artifact, retry, or acceptance-yield costs block chargeability. The future p95 guarded physical-cost pricing described by the mega-agent blueprint is not yet implemented and must not be claimed.

## Promotion boundary

These are separate evidence gates:

```text
local compile/test/price
  -> PR/required CI
  -> reviewed merge
  -> direct Modal staging canary
  -> registration + generated registry drift checks
  -> Worker suites/deploy
  -> marketplace publication
  -> signed-in Omo billing canary
  -> separately authorized production traffic
```

The builder may stop at any gate. Passing one never implies a later gate passed. A production action needs Harry's exact approval for the release, environment, and scope; the canary must validate the real schema/result and relevant billing/refund invariants before traffic. The profile never self-promotes.

## Typed handback

Every build returns one of:

- `READY`: release candidate with source hash, manifests, canonical price/cost version, schema/sanity/security/test/artifact/canary evidence, diff/branch or authorized PR, exact queue/release/deploy/traffic state, rollback target, and remaining human gate.
- `BLOCKED-<TYPED_REASON>`: failed gate, bounded evidence, safe work completed, exact fix, and resume data. Examples: `PLATFORM_NOT_READY`, `RESEARCH_BLOCKED`, `CAPABILITY_REVIEW_REQUIRED`, `RIGHTS_REVIEW_REQUIRED`, `PRICE_REVIEW_REQUIRED`, `QA_BUDGET_REQUIRED`, `QA_FAILED`, `SOURCE_IDENTITY_MISMATCH`, `SLUG_COLLISION`, `REVIEWED_PROFILE_REQUIRED`, `GENERATOR_FAILED`, `ARTIFACT_ADAPTER_REQUIRED`, `HOSTED_AUTH_401`, `PRIVATE_PRODUCT`, `CANCELLED`.
- `NEEDS-HARRY`: exactly one identity/dashboard/credential/rights/spend/remote-write/deploy/publish/traffic step, why it is needed, official destination, minimum scope, what must not be pasted into chat, expected non-secret success signal, and verification/resume action.

`READY` means candidate-ready unless the handback separately proves later states. It never silently means live, public, or chargeable.

## Private product exclusion

`illustrated-decodable-story-maker` is Harry's $400 private product. The builder must never publish it, submit it, enqueue it, add it to a public catalog/repository, or include its source/contract in a public PR. A request to create a public listing for that slug returns `BLOCKED-PRIVATE_PRODUCT`.

## Open dependencies and honest current verdict

1. **One-shot TEST/VERIFY/FIX gate:** Agent Z's `research/one-shot-rounds.md` was not present when this profile was built. The SOUL references it conditionally as the future test gate. Existing compiler/host/generated-contract/pricing tests are the honest interim local gate.
2. **Hosted 401:** the Modal Proxy Token/dashboard step gates live hosted canaries and deployment. It is `NEEDS-HARRY`; the builder must not retrieve, type, or print token values.
3. **PDF/artifact adapter:** a local deterministic PDF renderer exists, but the renderer adapter plus production artifact authorization/storage/checksum/delivery contract still gates artifact-complete chargeable workflows. A local PDF smoke result is not hosted readiness.
4. **Queue automation installation:** dispatcher/service/timer templates exist but were not installed on this machine. Installation and credential provisioning are separate approved operations.
5. **Planned architecture:** `research/mega-agent-blueprint.md` remains a future blueprint. This Hermes identity and today's local pipeline do not make the planned autopilot, immutable release controller, or full one-shot platform complete.

## Verification performed

- `hermes profile show omo-builder`: profile exists at the expected path, gateway stopped, 82 standard skills, SOUL present, and no profile model configured.
- SOUL structure check: exactly eight numbered top-level sections; all three typed results, both intake routes, canonical pricing, private exclusion, and all dependency gates are present.
- Intake bridge tests: `36 passed` across `test_dispatch_queued_submission.py` and `test_process_submissions.py` with the pytest cache disabled.
- Isolated compile/test/price smoke: Facebook Ads Copywriter compiled to a new `/private/tmp` output; compiler suite `88 passed`, generated contract suite `14 passed`, pricing verified, `registered: false`, `chargeable: true`, price `$0.10`. No provider call, credential access, registration, remote write, deployment, publication, or spend occurred.
- Strict checked-in drift gate: the existing `containers/facebook-ads-copywriter/modal_app.py` differs from current generator output, so `host.py ... --check` correctly failed closed with `generated bundle drift: modal_app.py`. This work did not modify that unrelated container. The clean temporary build proves the local compiler/test/price lane works; it does not erase the repository drift that a future authorized builder task should fix at the generator/generated-bundle level.
- `git diff --check -- research/builder-profile.md`: clean.
- `research/one-shot-rounds.md`: still absent at final verification, so it remains an explicit pending gate.

**Verdict:** `PROFILE-READY` for manual, local authorized builder work and for the queue bridge once that bridge is separately installed and verified. Live deployment remains gated by typed dependencies and Harry's explicit production approval.
