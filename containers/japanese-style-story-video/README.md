# japanese-style-story-video

Generated Modal candidate for `japanese-style-story-video`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `c4db870d3055d1a5b3772e53812c64f5673014013f17eaff08ca5cc66e458cd7`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**NOT READY for live runs or charging.** `POST /v1/runs` is protected with Modal Proxy Token auth and returns `503 WORKFLOW_NOT_READY` before spawning or spending while these blockers remain:

- `MEDIA_EXECUTION_KIND_UNSUPPORTED` — The reviewed skill compiler currently allowlists only single_llm as ready and does not yet materialize the existing demello-awake media executor for this container.
- `HOSTED_SAMPLE_INTEGRATION_PENDING` — The real sample, procedural frame lane, FFmpeg assembly, and QA exist in containers/demello-awake, but the generated hosted container does not yet package that code or its owner-scoped artifact delivery contract.
- `CONTROL_PLANE_PRICE_COLLISION` — site/deploy/worker.js still routes this slug through the legacy nonpaid de Mello branch quoted at $0.10; it must be reconciled with the requested $0.90 generated hosted profile before charging.
- `PROVIDER_BENCHMARKS_PENDING` — Arbitrary-audio transcription, semantic direction, and image-generation providers do not yet have accepted-output latency, cost, and retry benchmarks for this listing.
- `PRE_SPEND_CONTROLS_PENDING` — The arbitrary-audio lane lacks reviewed per-phase reservations, hard cost ceilings before provider calls, and delivered-cost reconciliation.
- `ARBITRARY_AUDIO_DISABLED` — The hosted input schema intentionally accepts only sample-demello-10s; user uploads and URLs remain out of scope.

Required environment variable names (values never belong in this repository):

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

## Contract

- Submit: `POST /v1/runs` → `202` with `run_id`, `call_id`, and `result_url`
- Poll: `GET /v1/runs/{call_id}` → `202 running` or the validated output
- Invalid input: `422` before spawn
- Blocked release: `503` before spawn when `readiness.can_submit` is false
- Input/UI contract: `manifest.json`
- Pricing evidence: `pricing-report.json` (display estimate `$0.90`, not chargeable)

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

Deployment is intentionally gated on readiness review. Once the generated manifest says `can_submit: true`, required provider capabilities exist, and tests pass:

```bash
modal deploy containers/japanese-style-story-video/modal_app.py
```
