# V02 Release Label Sorter

Generated Modal candidate for `v02-release-label-sorter`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `d52e7984117e3986f0ce2a1a765c01b57d9f9b2b029a2c493571641c5ac605e9`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**READY for authenticated staging runs.** `POST /v1/runs` validates the input schema before spawning a deterministic provider-free job.

- None for this reviewed runtime scope.

Required environment variable names (values never belong in this repository):



## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{run_id}?call_id={call_id}&access_token={access_token}` → `202 running` or the validated output
- Invalid input: `422` before spawn

- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (`$0.10` per run)

Prompt assets:



## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/v02-release-label-sorter/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/v02-release-label-sorter.json \
  --out containers/v02-release-label-sorter
python3 -m pytest -q -p no:cacheprovider containers/v02-release-label-sorter/tests/test_contract.py
```

Deploy after the offline tests pass; this deterministic runtime uses no provider secret:

```bash
modal deploy containers/v02-release-label-sorter/modal_app.py
```
