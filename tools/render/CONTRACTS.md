# Contract diagnosis

This records the source `SKILL.md` declarations and the reviewed profile schemas
that precede the shared renderer. The public request schemas remain authoritative;
the render manifest is a trusted internal, post-generation contract.

## `phonics-worksheet-generator`

Source: `packages/phonicsmaker/SKILL.md`; reviewed profile:
`packages/skill-to-modal/profiles/phonics-worksheet-generator.json`.

Public input schema:

- `grade`: `prek | k | 1 | 2 | 3`
- `focus_type`: `sound | grapheme | word_family`
- `focus_patterns`: 1-6 unique strings, each 1-20 characters
- `activity`: `map-write | sort | sentence | passage | game | classroom-check`
- `page_count`: integer 1-12
- `difficulty`: `introduce | practice | review | mixed`
- `dialect`: `en-US | en-GB | en-AU`
- `print_mode`: `blackline | color`
- `theme`: string 1-80 characters
- `include_answer_key`: boolean
- `teacher_notes`: string up to 1,000 characters

All fields are required by the reviewed JSON schema. This conflicts with the
SKILL prose, which calls `teacher_notes` optional. Resolve that mismatch before
readiness.

Declared result envelope: `run_id`, completed status, fixed workflow version,
one or two artifacts, `content_report`, and `usage`. The primary artifact is a
PDF with role `worksheet`; `answer_key` is a second PDF when requested. Each
descriptor requires object key, filename, `application/pdf`, byte count,
SHA-256, and page count. The current happy-path input requests a key but its
fixture returns only the worksheet, and the output schema does not conditionally
require the key. The renderer enforces answer completeness and emits the key;
the reviewed fixture/schema should be aligned before readiness.

## `illustrated-decodable-story-maker`

Source: `packages/phonicsmaker/illustrated-decodable-story-maker/SKILL.md`;
reviewed profile:
`packages/skill-to-modal/profiles/illustrated-decodable-story-maker.json`.

Public input schema:

- `phonemes`: 1-12 unique strings, each 1-20 characters
- `story_idea`: string 3-500 characters
- `difficulty_level`: `1 | 2 | 3 | 4 | 5 | 6`
- `language_variant`: `en_au | en_uk | en_us | fr`
- `curriculum`: `general | vic | sg_moe | us_ccss`
- `page_count`: integer 7-21
- `highlight_text`, `progressive_highlighting`, `printable`: booleans
- `art_style`: `2d | watercolor | paper-cut`

All fields are required. The result envelope requires `run_id`, completed
status, fixed workflow version, title, exactly three artifacts,
`content_report`, `qa`, and `usage`. SKILL.md declares PDF story, editable JSON,
and JPEG thumbnail, each with object key, filename, MIME, bytes, and SHA-256.
The reviewed output schema currently checks only that `artifacts` has length
three; it does not constrain descriptor shape/kind/MIME. Tighten it before
readiness.

## `phonics-story-edit-studio`

Source: `packages/phonicsmaker/edit-studio/SKILL.md`; reviewed profile:
`packages/skill-to-modal/profiles/phonics-story-edit-studio.json`.

Public input schema:

- `source_story`: object key, constant `application/json` MIME, 1-10,000,000
  bytes, and lowercase 64-character SHA-256
- `operations`: 1-50 objects whose `operation` is one of
  `change_scene_text`, `change_story_title`, `toggle_highlighting`,
  `set_highlight_color`, `set_text_style`, `set_text_position`, or
  `regenerate_scene_image`
- `output_filename`: safe 1-100 character stem

All fields are required by the profile. This conflicts with SKILL prose calling
`output_filename` optional. The profile also does not validate operation-specific
arguments; a reviewed executor schema must do so before applying edits.

The result requires run/source/new version IDs, completed status, fixed workflow
version, applied operations, 2-3 artifacts, `qa`, and `usage`. Required artifacts
are revised-story PDF and editable JSON; thumbnail is optional. The current
output schema does not constrain individual artifact descriptors. Tighten it
before readiness. `ArtifactStore` models local owner scoping, checksum checks,
and immutable writes, but production authentication/authorization remains the
control plane's responsibility.
