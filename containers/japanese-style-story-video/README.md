# japanese-style-story-video

Generated Modal candidate for `japanese-style-story-video`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `e8ad3662a6852a90a5fe02bea4b9987cdafc266358c57b7c17381932f0bda764`). Generated files must be changed
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

- `prompts/director.txt`
- `prompts/frame.txt`

## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/japanese-style-story-video/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/japanese-style-story-video.json \
  --out containers/japanese-style-story-video
python3 -m pytest -q -p no:cacheprovider containers/japanese-style-story-video/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/japanese-style-story-video/modal_app.py
```
