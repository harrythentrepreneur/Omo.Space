# customer-feedback-theme-finder

Generated Modal candidate for `customer-feedback-theme-finder`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `3503deb0509f31462dba7fd771cfa11f7cfade7c325a9d7b53df0d8e7e5f7e27`). Generated files must be changed
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
- Pricing evidence: `pricing-report.json` (`$0.10` per run)

Prompt assets:

- `prompts/run.txt`

## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/customer-feedback-theme-finder/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/customer-feedback-theme-finder.json \
  --out containers/customer-feedback-theme-finder
python3 -m pytest -q -p no:cacheprovider containers/customer-feedback-theme-finder/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/customer-feedback-theme-finder/modal_app.py
```
