# dummy-word-list-organizer

Generated Modal candidate for `dummy-word-list-organizer`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `83e896077638d8f7796e648229bd361f3b517ab4199e45086a7ffcd1d95e045e`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**READY for authenticated staging runs.** `POST /v1/runs` validates the input schema before spawning a provider-backed job.

- None for this reviewed runtime scope.

Required environment variable names (values never belong in this repository):



## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{run_id}?call_id={call_id}&access_token={access_token}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn when `readiness.can_submit` is false
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (`$0.10` per run)

Prompt assets:



## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/dummy-word-list-organizer/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/dummy-word-list-organizer.json \
  --out containers/dummy-word-list-organizer
python3 -m pytest -q -p no:cacheprovider containers/dummy-word-list-organizer/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/dummy-word-list-organizer/modal_app.py
```
