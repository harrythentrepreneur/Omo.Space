# PhonicsMaker book engine — Omo adapter contract

This is the first Omo runtime slice for the complete PhonicsMaker book
pipeline. It preserves the real teacher-facing payload and result contract:

- required inputs: `phonemes`, `story_idea`, `difficulty_level`;
- optional curriculum, decodability, morphology, series, character, layout,
  font, style, activity, reference-book and page controls;
- full source result keys for book, compressed, book-only, worksheets,
  homework, answer key, PPTX, variations, draft data, scenes, phonemes and
  audio manifest;
- Omo artifact records with hashes and private delivery URLs;
- authenticated-style `POST /v1/runs` → `GET /v1/runs/{call_id}` lifecycle;
- `engine_binding.py`, which patches only storage/callback/task-state boundaries
  around the exact source `generate_story_task` and drains its background upload
  tasks before returning.

The adapter is intentionally **not ready**. Without a bound PhonicsMaker engine
and Omo artifact/provider boundary, submission returns
`PHONICSMAKER_ENGINE_NOT_BOUND` rather than a fake success or placeholder PDF.

Tests: `tests/test_contract.py`.
