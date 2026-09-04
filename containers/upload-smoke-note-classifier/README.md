# Upload Smoke Note Classifier

Generated Modal candidate for `upload-smoke-note-classifier`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `c3a9e5741363d3adc618567dd474418555fa23c44ef388cbe8feb3074f860936`). Generated files must be changed
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
  containers/upload-smoke-note-classifier/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/upload-smoke-note-classifier.json \
  --out containers/upload-smoke-note-classifier
python3 -m pytest -q -p no:cacheprovider containers/upload-smoke-note-classifier/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/upload-smoke-note-classifier/modal_app.py
```
