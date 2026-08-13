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

The SKILL.md is parsed as untrusted text and is never executed. A reviewed
profile at `packages/skill-to-modal/profiles/<slug>.json` is mandatory. Only
reviewed `single_llm` profiles can become runnable automatically; every other
execution kind stays fail-closed until its artifacts and capabilities are
materialized and reviewed.

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

Use `--dry-run tools/host-skill/tests/fixtures/sample-submission.json` to test
the intake/review decision without database writes or deployment.
