---
name: illustrated-decodable-story-maker
description: Create an original illustrated phonics story, editable source, thumbnail, and print-ready PDF from a bounded phonics and reading-level brief.
---

# Illustrated Decodable Story Maker

Specify the hosted PhonicsMaker generation workflow that turns a phonics brief
into a versioned illustrated storybook. The inspected implementation is a
multi-provider RunPod worker; this contract does not claim it is already a
single-call Modal workflow.

## When to use

- A teacher wants an illustrated story focused on selected phonemes.
- A literacy specialist needs a printable or color story with reviewed text highlighting.
- A teacher wants editable story source plus a PDF and thumbnail.

## Inputs

- `phonemes`: 1-12 reviewed sound or grapheme targets.
- `story_idea`: 3-500 characters of child-safe story direction.
- `difficulty_level`: one of `1`, `2`, `3`, `4`, `5`, or `6`.
- `language_variant`: `en_au`, `en_uk`, `en_us`, or `fr`.
- `curriculum`: `general`, `vic`, `sg_moe`, or `us_ccss`.
- `page_count`: integer from 7 through 21.
- `highlight_text`: boolean.
- `progressive_highlighting`: boolean.
- `printable`: boolean.
- `art_style`: one reviewed art-style identifier.

## Workflow

1. **Validate the brief:** Reject unknown fields, unsupported combinations, unsafe content, and out-of-range page counts before provider work.
2. **Generate story text:** Produce a title and bounded scenes using only reviewed curriculum context and the declared language variant and difficulty.
3. **Plan illustrations:** Create a cover brief and one text-free scene-image brief per story scene with consistent characters and art direction.
4. **Generate and moderate images:** Use an approved image provider, record lineage and cost, and reject unsafe, text-bearing, or continuity-breaking images.
5. **Compose editable pages:** Place text and images, apply declared phoneme highlighting, and save the same final layout as an immutable editable JSON artifact.
6. **Render and verify:** Produce PDF and thumbnail, render every page, check text accuracy, page order, clipping, contrast, highlighting, artifact hashes, and file bounds.
7. **Deliver privately:** Store versioned artifacts through Omo's authorized artifact plane and return only schema-defined descriptors.

## Output contract

Return one JSON object with `run_id`, `status`, `workflow_version`, `title`,
`artifacts`, `content_report`, `qa`, and measured `usage`. Required artifacts are
a `pdf` story, `json` editable source, and image thumbnail. Each includes
`object_key`, `filename`, `content_type`, `bytes`, and `sha256`.

## Hard rules

- Never claim a story is fully decodable or curriculum-aligned without a reviewed machine and educator check recorded in `qa`.
- Never fabricate artifact URLs, provider success, usage, or page verification.
- Images must be original, child-safe, text-free, and continuity-checked.
- Do not expose permanent public bucket URLs, local paths, credentials, or learner identity.
- Do not email, publish, overwrite a prior version, charge, or deploy from this skill.
