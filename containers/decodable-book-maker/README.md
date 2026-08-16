# decodable-book-maker

Generated Modal candidate for `decodable-book-maker`. The source skill is vendored
at `source/SKILL.md` (SHA-256 `d01ae61d577c1555b1b32761b15ea7c08c4c5fe1203756d18132a77bcb8785d7`). Generated files must be changed
through the compiler profile, not edited by hand.

## Readiness

**NOT READY for live runs or charging.** `POST /v1/runs` is protected with Modal Proxy Token auth and returns `503 WORKFLOW_NOT_READY` before spawning or spending while these blockers remain:

- `DECODABILITY_VOCABULARY_MISSING` — The reviewed OSS contract requires every child-visible word to pass a compiler-owned stage vocabulary plus a reviewed sight-word list, recomputed deterministically, and a runnable result must contain no review words. No such vocabulary resource exists in this repo or in the OSS twin (which publishes only SKILL.md, manifest.json, README, LICENSE), and the compiler has no vocabulary-based normalizer kind for whole-book enforcement. Resume: author the five cumulative stage vocabularies + reviewed sight-word list from PhonicsMaker's reviewed inventory (or Harry supplies them), add a deterministic vocabulary normalizer to the runtime template, fixture-test right/wrong needles, then flip can_submit. The paper price ($0.99) and schemas are reviewed and stay fixed.

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
- Pricing evidence: `pricing-report.json` (display estimate `$0.10`, not chargeable)

Prompt assets:

- `prompts/run.txt`

## Rebuild and test

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/decodable-book-maker/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/decodable-book-maker.json \
  --out containers/decodable-book-maker
python3 -m pytest -q -p no:cacheprovider containers/decodable-book-maker/tests/test_contract.py
```

Deployment is intentionally gated on readiness review. Once the generated manifest says `can_submit: true`, required provider capabilities exist, and tests pass:

```bash
modal deploy containers/decodable-book-maker/modal_app.py
```
