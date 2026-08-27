# Release Tag Sorter Canary

Generated Modal candidate for `release-tag-sorter-canary`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `05e3f9edd5b7a57a68ea32ba703975c6793721a62c17904cab63152f375d0a57`). Generated files must be changed
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
  containers/release-tag-sorter-canary/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/release-tag-sorter-canary.json \
  --out containers/release-tag-sorter-canary
python3 -m pytest -q -p no:cacheprovider containers/release-tag-sorter-canary/tests/test_contract.py
```

Deploy after the offline tests pass; this deterministic runtime uses no provider secret:

```bash
modal deploy containers/release-tag-sorter-canary/modal_app.py
```
