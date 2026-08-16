# label-normalizer-canary

Generated Modal candidate for `label-normalizer-canary`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `32a9e56a4c3ff57fce713d5341c48a5a1b54deee7cd7369a5cda7f9eb50fea0a`). Generated files must be changed
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
- Pricing evidence: `pricing-report.json` (`$0.10` per run)

Prompt assets:



## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/label-normalizer-canary/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/label-normalizer-canary.json \
  --out containers/label-normalizer-canary
python3 -m pytest -q -p no:cacheprovider containers/label-normalizer-canary/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/label-normalizer-canary/modal_app.py
```
