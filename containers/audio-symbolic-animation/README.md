# audio-symbolic-animation

Generated Modal candidate for `audio-symbolic-animation`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `50d5ba9538ea5b8eab24b192df87f22b8723322f1c0874b8e24110057368fe1f`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**NOT READY for live runs or charging.** `POST /v1/runs` is protected with Modal Proxy Token auth and returns `503 WORKFLOW_NOT_READY` before spawning or spending while these blockers remain:

- `EXECUTOR_NOT_MATERIALIZED` — The referenced Hermes scripts and faster-whisper model are not vendored, pinned, or packaged in this repository.
- `IMAGEGEN_CAPABILITY_UNAPPROVED` — The skill requires sequential Hermes/Codex subscription image generation; no reviewed server-side Modal adapter or auditable credential lifecycle exists.
- `PRIVATE_ARTIFACT_PLANE_MISSING` — Exact private input upload, output persistence, signed delivery, retention, and deletion are unresolved.
- `COST_INCOMPLETE` — Modal transcription/assembly compute, subscription allowance, retries, storage, egress, and accepted-output yield are not measured.
- `QA_CAPABILITY_MISSING` — The required vision continuity gate and long-run paid canary have not been implemented or approved.

Required environment variable names (values never belong in this repository):

- `DEEPSEEK_API_KEY`
- `OPENAI_CODEX_ACCESS_TOKEN`
- `OPENAI_CODEX_REFRESH_TOKEN`
- `OPENAI_CODEX_ACCOUNT_ID`

## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{call_id}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn when `readiness.can_submit` is false
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (display estimate `$24.34`, not chargeable)

Prompt assets:

- `prompts/brief.txt`
- `prompts/concept.txt`
- `prompts/passage-selection.txt`

## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/audio-symbolic-animation/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/audio-symbolic-animation.json \
  --out containers/audio-symbolic-animation
python3 -m pytest -q -p no:cacheprovider containers/audio-symbolic-animation/tests/test_contract.py
```

Deployment is intentionally gated on readiness review. Once the generated manifest says `can_submit: true`, required provider capabilities exist, and tests pass:

```bash
modal deploy containers/audio-symbolic-animation/modal_app.py
```
