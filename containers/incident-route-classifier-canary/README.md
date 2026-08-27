# Incident Route Classifier Canary

Generated Modal candidate for `incident-route-classifier-canary`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `2f9625e2f74501a41806258bcb835116eb0bec4e49529b250d1d6c5d3b2f70bb`). Generated files must be changed
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

- `prompts/system.txt`
- `prompts/workflow.txt`

## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/incident-route-classifier-canary/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/incident-route-classifier-canary.json \
  --out containers/incident-route-classifier-canary
python3 -m pytest -q -p no:cacheprovider containers/incident-route-classifier-canary/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/incident-route-classifier-canary/modal_app.py
```
