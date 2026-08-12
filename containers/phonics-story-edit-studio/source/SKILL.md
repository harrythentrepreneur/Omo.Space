---
name: phonics-story-edit-studio
description: Apply reviewed text, layout, highlighting, title, or optional image changes to an owned PhonicsMaker story and return a new versioned PDF without overwriting the source.
---

# Phonics Story Edit Studio

This skill specifies the hosted save/export worker behind a PhonicsMaker-style
editor. The interactive browser canvas remains a separate UI concern. The
worker consumes an owned editable-story JSON artifact and explicit operations,
then produces a new JSON version and PDF.

## When to use

- A teacher wants to correct story text or title before classroom use.
- A teacher wants to change text position, size, colors, outline, or phoneme
  highlighting and regenerate the PDF.
- A teacher needs an immutable revised version while preserving the original.

## Inputs

- `source_story`: an owner-authorized JSON artifact descriptor with
  `object_key`, `content_type`, `bytes`, and `sha256`.
- `operations`: 1-50 bounded operations. Supported deterministic operations are
  `change_scene_text`, `change_story_title`, `toggle_highlighting`,
  `set_highlight_color`, `set_text_style`, and `set_text_position`.
- `regenerate_scene_image` is an optional image-provider tier and must include
  `scene_number` plus a bounded `user_request`; it stays unavailable until its
  provider, cost, moderation, and continuity QA are approved.
- `output_filename`: optional safe filename stem.

The source JSON is versioned and contains `task_id`, `story_title`,
`original_story_title`, `pages`, `phonemes`, `difficulty_level`, `is_free`,
`highlight_text`, `printable`, `art_style`, `page_count`,
`progressive_highlighting`, `language_variant`, `curriculum`, `created_at`,
`version`, `last_modified`, `highlightEnabled`, and `highlightColor`. Each page
contains `pageNumber`, `image_url` or an approved image artifact reference,
`image_prompt`, and `objects`; text objects carry bounded position, dimensions,
text, typography, fill, stroke, alignment, spacing, and highlight metadata.

## Workflow

1. **Authorize and validate:** Resolve `source_story` server-side, verify its
   owner, size, checksum, MIME, version, and schema, and reject arbitrary URLs or
   cross-user task IDs before work begins.
2. **Create an immutable working version:** Preserve the source JSON/PDF. Assign
   a new run/version ID; never reproduce the current RunPod behavior of replacing
   the original URL.
3. **Normalize operations:** Validate scene/object indices and convert only the
   declared operations into a deterministic patch. Natural-language commands,
   if offered by a UI, must first become this bounded operation list and be
   shown for confirmation.
4. **Apply changes:** Update text/layout/highlighting without changing unrelated
   fields. If the approved image tier is used, refine only the selected scene,
   record prompt/provider lineage, and preserve the established character and
   page style.
5. **Render:** Use the reviewed story compositor, bundled fonts, and local copies
   of authorized page images. Produce a PDF and thumbnail; regenerate editable
   JSON from the same final state.
6. **Verify:** Render all pages, compare untouched pages to the source, confirm
   every requested patch and no unrequested patch, validate bounds and contrast,
   open the PDF, and calculate bytes/SHA-256.
7. **Deliver privately:** Return new versioned artifact descriptors through the
   approved Omo artifact plane. Do not expose source bucket credentials or
   permanent public URLs.

## Output contract

Return one JSON object with `run_id`, `source_version`, `new_version`, `status`,
`workflow_version`, `operations_applied`, `artifacts`, `qa`, and measured
`usage`. Required artifacts are a `kind: "pdf"` revised story and a
`kind: "json"` editable source; an image thumbnail is optional. Every artifact
includes `role`, `object_key`, `filename`, `content_type`, `bytes`, and
`sha256`.

## Hard rules

- Never overwrite, delete, or mutate the source artifact.
- Never accept a bare remote PDF/image URL as proof of ownership.
- Never apply an unknown operation or silently ignore an invalid one.
- Do not weaken phonics scope, change dialect, or invent story facts unless an
  explicit, validated operation requests it.
- Image changes must be text-free, child-safe, original, and continuity-checked.
- Do not send notifications, publish, charge, or deploy from this skill.
