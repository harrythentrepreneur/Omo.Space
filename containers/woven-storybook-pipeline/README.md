# woven-storybook-pipeline

Generated Modal candidate for `woven-storybook-pipeline`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `6297f14dfc8d4815efc041316e5c19df7faf4cb31dae3f73a0badc09101b90bf`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**NOT READY for live runs or charging.** `POST /v1/runs` is protected with
Modal Proxy Token auth and returns `503 WORKFLOW_NOT_READY` before spawning or
spending while these blockers remain:

- `EXECUTOR_NOT_VENDORED` — The reviewed TypeScript implementation lives in /Users/yifan/woven/backend and is not a pinned, versioned dependency of this repository.
- `DEEPSEEK_SECRET_MISSING` — A least-privilege Modal secret containing DEEPSEEK_API_KEY must exist before a real generation can run.
- `PRIVATE_DATA_PLANE_MISSING` — Private upload, mode-700 run workspaces, TTL deletion, signed download, and raw-chat deletion need a hosted implementation and tests.
- `COST_INCOMPLETE` — Chromium/Ghostscript compute, Modal resources, storage, egress, retries, and delivered-output yield are not measured.
- `LIVE_FIXTURE_QA_PENDING` — The safe demo fixture must pass the vendored backend suite and one full Modal run before readiness can change.

Required environment variable names (values never belong in this repository):

- `DEEPSEEK_API_KEY`

## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{call_id}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (display estimate `$0.40`, not chargeable)

Prompt assets:

- `prompts/chapter.txt`
- `prompts/editorial.txt`
- `prompts/essence.txt`
- `prompts/plan.txt`

## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/woven-storybook-pipeline/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/woven-storybook-pipeline.json \
  --out containers/woven-storybook-pipeline
python3 -m pytest -q -p no:cacheprovider containers/woven-storybook-pipeline/tests/test_contract.py
```

Deployment is intentionally gated on readiness review. Once the generated
manifest says `can_submit: true`, required provider capabilities exist, and
tests pass:

```bash
modal deploy containers/woven-storybook-pipeline/modal_app.py
```
