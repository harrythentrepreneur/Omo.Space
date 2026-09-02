# Autonomous Reply Urgency Classifier

Generated Modal candidate for `autonomous-reply-urgency-classifier`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `e518520523e3d9cef7c487c5646cff47447252659497acd28151b7478f980859`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**READY for authenticated staging runs.** `POST /v1/runs` validates the input schema before spawning a provider-backed job.

- None for this reviewed runtime scope.

Required environment variable names (values never belong in this repository):

- `GEMINI_API_KEY`

## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{call_id}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn when `readiness.can_submit` is false
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (`$0.10` per run)

Prompt assets:

- `prompts/system.txt`
- `prompts/workflow.txt`

## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/autonomous-reply-urgency-classifier/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/autonomous-reply-urgency-classifier.json \
  --out containers/autonomous-reply-urgency-classifier
python3 -m pytest -q -p no:cacheprovider containers/autonomous-reply-urgency-classifier/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/autonomous-reply-urgency-classifier/modal_app.py
```
