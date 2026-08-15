# skill-md-to-hosted-workflow

Generated Modal candidate for `skill-md-to-hosted-workflow`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `cfc7e2c683709bf40db6140e3b8cee608ed98781327f96b98072bdc96d59b8ae`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**READY for authenticated staging runs.** `POST /v1/runs` validates the input schema before spawning a provider-backed job.

- None for this reviewed runtime scope.

Required environment variable names (values never belong in this repository):



## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{call_id}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn when `readiness.can_submit` is false
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (`$5.00` per run)

Prompt assets:



## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/skill-md-to-hosted-workflow/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/skill-md-to-hosted-workflow.json \
  --out containers/skill-md-to-hosted-workflow
python3 -m pytest -q -p no:cacheprovider containers/skill-md-to-hosted-workflow/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/skill-md-to-hosted-workflow/modal_app.py
```
