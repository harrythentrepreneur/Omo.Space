# Upload Smoke Label Sorter

Generated Modal candidate for `upload-smoke-label-sorter`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `7f05fdef2c6c87d3ad12587eca677d101a5a03b847e0da027794c0ca821d4dbc`). Generated files must be changed
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
  containers/upload-smoke-label-sorter/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/upload-smoke-label-sorter.json \
  --out containers/upload-smoke-label-sorter
python3 -m pytest -q -p no:cacheprovider containers/upload-smoke-label-sorter/tests/test_contract.py
```

Deploy after the offline tests pass; this deterministic runtime uses no provider secret:

```bash
modal deploy containers/upload-smoke-label-sorter/modal_app.py
```
