# V02 Release Label Sorter Test

Generated Modal candidate for `v02-release-label-sorter-test`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `fe59ced44b15bf574dd6df387b8f4f08554f54b2bf2d878ff60e05faeee5578f`). Generated files must be changed
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
  containers/v02-release-label-sorter-test/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/v02-release-label-sorter-test.json \
  --out containers/v02-release-label-sorter-test
python3 -m pytest -q -p no:cacheprovider containers/v02-release-label-sorter-test/tests/test_contract.py
```

Deploy after the offline tests pass; this deterministic runtime uses no provider secret:

```bash
modal deploy containers/v02-release-label-sorter-test/modal_app.py
```
