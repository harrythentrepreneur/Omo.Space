# phonics-worksheet-generator

Generated Modal candidate for `phonics-worksheet-generator`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `3766b71879a8a53f77634ef9ebf5f516e1502a7d0e11a1a1cceca3cc0b0a69a1`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**NOT READY for live runs or charging.** `POST /v1/runs` is protected with Modal Proxy Token auth and returns `503 WORKFLOW_NOT_READY` before spawning or spending while these blockers remain:

- `WORKSHEET_RUNTIME_MISSING` — The supplied PhonicsMaker core has no standalone worksheet content-manifest or renderer.
- `ARTIFACT_PLANE_UNREVIEWED` — Private artifact write, PDF QA, fonts, and approved assets are not materialized.
- `EDUCATOR_ACCEPTANCE_MISSING` — Reviewed correctness and decodability fixtures do not exist.

Required environment variable names (values never belong in this repository):



## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{call_id}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn when `readiness.can_submit` is false
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (display estimate `$2.50`, not chargeable)

Prompt assets:



## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/phonics-worksheet-generator/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/phonics-worksheet-generator.json \
  --out containers/phonics-worksheet-generator
python3 -m pytest -q -p no:cacheprovider containers/phonics-worksheet-generator/tests/test_contract.py
```

Deployment is intentionally gated on readiness review. Once the generated manifest says `can_submit: true`, required provider capabilities exist, and tests pass:

```bash
modal deploy containers/phonics-worksheet-generator/modal_app.py
```
