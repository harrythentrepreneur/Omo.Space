# woven-storybook-pipeline

Generated Modal candidate for `woven-storybook-pipeline`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `6297f14dfc8d4815efc041316e5c19df7faf4cb31dae3f73a0badc09101b90bf`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**READY for authenticated staging runs.** `POST /v1/runs` validates the input schema before spawning a provider-backed job.

- None for this reviewed runtime scope.

Required environment variable names (values never belong in this repository):

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{call_id}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn when `readiness.can_submit` is false
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (`$0.40` per run)

Prompt assets:

- `prompts/run.txt`

## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/woven-storybook-pipeline/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/woven-storybook-pipeline.json \
  --out containers/woven-storybook-pipeline
python3 -m pytest -q -p no:cacheprovider containers/woven-storybook-pipeline/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/woven-storybook-pipeline/modal_app.py
```
