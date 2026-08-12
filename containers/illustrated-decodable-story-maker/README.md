# illustrated-decodable-story-maker

Generated Modal candidate for `illustrated-decodable-story-maker`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `f9f8469f7e3ccba305fece7395813f74ab390da02d395f3e306783bc0dca48e3`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**NOT READY for live runs or charging.** `POST /v1/runs` is protected with Modal Proxy Token auth and returns `503 WORKFLOW_NOT_READY` before spawning or spending while these blockers remain:

- `MULTI_PROVIDER_PORT_MISSING` — The core RunPod workflow has not been decoupled into a reviewed Modal runtime.
- `IMAGE_AND_ARTIFACT_PLANES_MISSING` — Image generation, moderation, PDF composition, and private artifact delivery are not materialized.
- `COST_AND_ACCEPTANCE_EVIDENCE_MISSING` — Per-page cost, retry yield, decodability, curriculum, and educator acceptance evidence are unresolved.

Required environment variable names (values never belong in this repository):



## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{call_id}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn when `readiness.can_submit` is false
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (display estimate `$1.62`, not chargeable)

Prompt assets:



## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/illustrated-decodable-story-maker/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/illustrated-decodable-story-maker.json \
  --out containers/illustrated-decodable-story-maker
python3 -m pytest -q -p no:cacheprovider containers/illustrated-decodable-story-maker/tests/test_contract.py
```

Deployment is intentionally gated on readiness review. Once the generated manifest says `can_submit: true`, required provider capabilities exist, and tests pass:

```bash
modal deploy containers/illustrated-decodable-story-maker/modal_app.py
```
