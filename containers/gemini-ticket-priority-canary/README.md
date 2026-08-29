# Gemini Ticket Priority Canary

Generated Modal candidate for `gemini-ticket-priority-canary`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `baf80fbe9b7bd0882ea8ce467307598aeae92e8224778ec159795f8360fd2ff9`). Generated files must be changed
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
  containers/gemini-ticket-priority-canary/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/gemini-ticket-priority-canary.json \
  --out containers/gemini-ticket-priority-canary
python3 -m pytest -q -p no:cacheprovider containers/gemini-ticket-priority-canary/tests/test_contract.py
```

Deploy after the named Modal secret exists and the offline tests pass:

```bash
modal deploy containers/gemini-ticket-priority-canary/modal_app.py
```
