# host-skill

`host.py` is Omo's repeatable SKILL.md hosting command. Hermes runs this at
creator-intake/release time: it delegates bundle generation to the reviewed
`packages/skill-to-modal/compiler.py`, runs the
compiler and container test suites, verifies pricing against
`site/deploy/cost-model.mjs`, and optionally registers the result in the
storefront and generated Worker registry.

```bash
python3 tools/host-skill/host.py packages/facebook-ads-copywriter/SKILL.md --register
python3 tools/host-skill/host.py packages/facebook-ads-copywriter/SKILL.md --register --check
```

The SKILL.md is parsed as untrusted text and is never executed. Existing
reviewed profiles at `packages/skill-to-modal/profiles/<slug>.json` remain
supported byte-for-byte. For a new supported `pure_data` or `single_llm`
submission, the isolated author writes only a small versioned IR under
`packages/skill-to-modal/workflow-irs/`. A trusted parent validates that IR
against the authoritative machine schema and deterministically owns identity,
source binding, provider/runtime/resources, readiness, pricing, deployment and
release policy when it materializes the full profile. Unsupported code,
media/browser/private-data/provider selection and arbitrary capabilities stop
with a typed blocker; they are never turned into executable resources.

Validation repair stays inside one builder dispatch: at most three authoring
attempts share one 1,800-second and 24-proxy-request budget. Only fixed error
codes and JSON pointers are returned to the isolated author. Source and identity
remain immutable, and exhaustion is a terminal non-Retry blocker.

During reviewed release preparation, the profile can set `runtime_preference`
to `auto`, `worker-native`, or `modal-hosted`. Hermes records the recommended,
requested, and effective placement. Worker compatibility requires an explicit
allowlist of execution kind and capabilities with no native packages or
artifacts; unknown capabilities fail closed to Modal. Profiles created before
this policy remain Modal unless explicitly migrated. The generated Worker
registry is metadata-only until its executable adapter and canary are shipped;
creator-facing preference persistence is also follow-up work. Customers keep
using the same control plane and do not choose or need to know the runtime.

See `research/hosting-runbook.md` for the complete deploy and canary procedure.

## Creator upload queue

`POST /api/submit` stores authenticated, public creator Markdown in Neon as
`queued`. It validates the same scalar `name` and `description` frontmatter as
the compiler, caps UTF-8 content at 200 KiB, derives the slug server-side, and
makes retries idempotent per creator and source hash. It never executes the
Markdown.

An Omo agent processes the queue:

```bash
python3 tools/host-skill/process-submissions.py
python3 tools/host-skill/process-submissions.py --id sub_… --deploy
```

Unknown workflows stop at `needs_review`; the upload alone cannot create the
trusted profile that owns schemas, provider access, fixtures, resources,
pricing, marketplace copy, and the expected Modal endpoint. `--deploy` is for
an already-reviewed profile: it runs `host.py`, Modal deploy + direct canary,
registration/drift checks, all four Worker suites, and Worker deploy. It leaves
the item at `ready_for_publish` until the agent commits/pushes, verifies the
Vercel production listing and billing canary, then explicitly marks it:

```bash
python3 tools/host-skill/process-submissions.py --export-review sub_… --review-dir /private/tmp/omo-review
python3 tools/host-skill/process-submissions.py --mark-deployed sub_…
```

### Trusted post-merge finalization groundwork

The private Worker bridge owns a separate finalization lease and authorization
boundary. Finalization routes fail closed unless a distinct
`RELEASE_FINALIZER_TOKEN` is configured; the untrusted builder token cannot
claim, advance, promote or mark releases deployed. A trusted deterministic
controller may claim one `ready_for_deploy` / `merged_verified` submission by
posting only its selected immutable target-main SHA to
`/api/internal/finalizations/claim`. The returned `fin_…` generation is bound
to that SHA, source hash, release head/merge SHAs, artifact hash, runtime and a
one-hour lease.

Generation-bound status updates follow the runtime-aware sequence
`claimed -> deploying_modal -> deploying_worker -> verifying_public`
for Modal-hosted workflows, while Worker-native workflows skip
`deploying_modal`. From `verifying_public`, the finalizer-only promotion route
atomically stores sanitized R1-R4 evidence, marks the release promoted and
ready for publication, and completes the exact generation. Legacy builder
status, deployment and release routes cannot create publish readiness or a
promoted release. The protected detail endpoint returns only allowlisted
identity/state fields. Typed failures become terminal and are not automatically
reclaimed; only an expired active infrastructure lease can produce a new
generation. The separate finalizer-only `deployed` transition fails closed
unless atomic promotion completed with durable sanitized R1-R4 evidence.
If the controller crashes after atomic promotion but before the deployed
transition, `/api/internal/finalizations/resume-completed` returns one
exact-target, immutable, completed `ready_for_publish` generation. It is
finalizer-only and read-only. Publish-ready rows are preferred; if a crash
occurred after the deployed write committed, the same endpoint returns the
exact-target deployed receipt so the controller can finish idempotently.

The Phase 1 control-plane foundation did not include a deployment adapter,
GitHub trigger, production credential, automatic deploy or production write.

### Credential-free deterministic finalizer simulation

`release_finalizer.py` implements the Phase 2 orchestration contract with
injected adapters and a fake-only scenario CLI. It verifies latest green main,
head/merge/target ancestry, source and full artifact hashes, detached checkout
identity, required registry preservation, runtime-aware ordering, public and
publication receipts, Phase 1-compatible failure codes, promotion/deployed
readback and crash recovery. Provider effects are idempotently keyed by
submission, target SHA, artifact hash and operation rather than lease ID.

```bash
python3 tools/host-skill/release_finalizer.py --scenario /path/to/synthetic-scenario.json
```

The CLI accepts no provider, URL, account, workspace, command or credential
selection. It has no network client, provider SDK, environment lookup or shell
deployment path. Real adapters and triggers remain later reviewed phases.

### Credential-free GitHub trigger

`release_trigger.py` reduces the untrusted `workflow_run` event to a bounded,
sorted decision. It accepts only a successful completed
`generated-workflow-contracts` push to this repository's `main`, from this
repository, with a valid immutable head SHA and positive run identity.

`.github/workflows/trusted-release-trigger.yml` runs with `contents: read`,
uses an immutable `actions/checkout` revision, disables persisted credentials,
loads the validator from trusted `main`, and checks out the eligible target
only through the validator's SHA output. It has no secrets, artifacts,
provider adapters, deployment command, write permission or manual dispatch.
This trigger remains an inert controller foundation; it records eligibility but
does not deploy or finalize a release.

### Protected autonomous release-PR merge

`.github/workflows/trusted-release-merge.yml` loads only the controller from
trusted `main`. Review submission, successful contract completion, and a bounded
five-minute reconciliation schedule are candidate hints, never authority. The
controller re-reads the fixed repository and verifies a server-derived release
branch, fixed owner author, strict current branch protection, green `contracts`,
and a distinct trusted human approval on the exact head commit. It merges with
`--match-head-commit`; a main push then activates the existing exact-merge
finalizer. Stale/dismissed/same-author reviews, forks, moving heads, missing
checks and weak protection all remain blocked. The release commit preserves the
small authoring IR beside the compiler-owned profile as an immutable receipt.

### Staging deployment foundation

`staging_release_adapters.py` defines pure, non-executing command and receipt
contracts for the first deterministic `label-normalizer-canary` staging proof.
Modal is fixed to environment `omo-release-staging` and app
`cognition-staging-label-normalizer-canary`. Cloudflare is fixed to the
non-routed, unscheduled `cognition-demos-staging` Worker. Wrangler is an exact
local development dependency; finalization cannot download a moving CLI.

Every deployment receipt is bound to the exact target SHA and artifact hash.
Modal history uses the installed 1.3.4 `Version`/`Tag` JSON contract; Cloudflare
reads version annotations separately from deployment traffic/version IDs using
the pinned Wrangler 4.125.0 contract. Before/after snapshots derive whether the
exact revision was reused and prove the immediate rollback predecessor for every
new deployment. Caller-supplied reuse claims are not accepted.

The finalizer validates the exact provider, staging target, environment, SHA,
artifact hash, version and rollback binding, then durably records the bounded
receipt before canary/smoke. A later failure attempts rollback in reverse
Worker-then-Modal order, continues to Modal even if Worker rollback fails, and
never rolls back a readback-proven reused deployment. Wrangler dry-run evidence
hashes only compiled `worker.js`; timestamped README and outdir-dependent source
maps are explicitly non-authoritative.

The module cannot run subprocesses, read credentials, call providers or select
production. Controlled transports, real staging deployment and the public
canary remain separate reviewed gates.

`staging_release_transport.py` is the controlled subprocess boundary for those
commands. It constructs a fresh provider-specific child environment, forwards
only allowlisted keys, fixes non-secret process flags, uses argument arrays with
`shell=False`, enforces each command timeout, caps stdout at 1 MiB and reduces
all command/JSON/timeout failures to typed codes without provider output. Live
mutation is denied unless the transport is explicitly constructed with
`allow_mutation=True`; dry-run and metadata readback remain available by
default. This transport does not create environments, provision credentials or
choose a production target.

Use `--dry-run tools/host-skill/tests/fixtures/sample-submission.json` to test
the intake/review decision without database writes or deployment.
