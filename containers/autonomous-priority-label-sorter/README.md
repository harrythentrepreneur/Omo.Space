# Autonomous Priority Label Sorter

Generated Modal candidate for `autonomous-priority-label-sorter`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `fbaa1cbb1eff8232bb8538d1350ee97132fac9f1cd32c125e69be4ee51dc8d66`). Generated files must be changed
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
  containers/autonomous-priority-label-sorter/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/autonomous-priority-label-sorter.json \
  --out containers/autonomous-priority-label-sorter
python3 -m pytest -q -p no:cacheprovider containers/autonomous-priority-label-sorter/tests/test_contract.py
```

Deploy after the offline tests pass; this deterministic runtime uses no provider secret:

```bash
modal deploy containers/autonomous-priority-label-sorter/modal_app.py
```
