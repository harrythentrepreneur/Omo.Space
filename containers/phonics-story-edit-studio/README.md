# phonics-story-edit-studio

Generated Modal candidate for `phonics-story-edit-studio`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `5b4515dfb8f6d5aefafdf583c12f8e0fcc4b83480faf75e809ad40969a0320c0`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**NOT READY for live runs or charging.** `POST /v1/runs` is protected with Modal Proxy Token auth and returns `503 WORKFLOW_NOT_READY` before spawning or spending while these blockers remain:

- `OWNED_ARTIFACT_PLANE_MISSING` — Owner-authorized source resolution and immutable artifact output are not implemented.
- `RENDERER_NOT_PORTED` — The PhonicsMaker compositor, fonts, image inputs, and PDF QA are not packaged for Modal.
- `IMAGE_TIER_UNREVIEWED` — Optional image regeneration lacks approved provider cost, moderation, and continuity gates.

Required environment variable names (values never belong in this repository):



## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{call_id}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn when `readiness.can_submit` is false
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (display estimate `$1.00`, not chargeable)

Prompt assets:



## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/phonics-story-edit-studio/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/phonics-story-edit-studio.json \
  --out containers/phonics-story-edit-studio
python3 -m pytest -q -p no:cacheprovider containers/phonics-story-edit-studio/tests/test_contract.py
```

Deployment is intentionally gated on readiness review. Once the generated manifest says `can_submit: true`, required provider capabilities exist, and tests pass:

```bash
modal deploy containers/phonics-story-edit-studio/modal_app.py
```
