# meta-creative-audit

Generated Modal candidate for `meta-creative-audit`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `68779b410928469d7a4ddb362742703844073d465112917af3f30d4a1a59a4e6`). Generated files must be changed
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
  containers/meta-creative-audit/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/meta-creative-audit.json \
  --out containers/meta-creative-audit
python3 -m pytest -q -p no:cacheprovider containers/meta-creative-audit/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/meta-creative-audit/modal_app.py
```
