# PhonicsMaker → Omo SKILL.md and Modal plan

**Status:** research and executable specifications only; no source port, Modal
container, registration, deployment, catalog mutation, provider call, or copied
PhonicsMaker content was made.

**Date:** 2026-08-13

**Inspected source:** `/Users/yifan/phonicsmaker-local/phonicsmaker-core`,
`/Users/yifan/phonicsmaker-local/phonicsmaker-web`, and product/metrics notes in
`/Users/yifan/phonicsmaker`.

**Created specifications:** `packages/phonicsmaker/SKILL.md`,
`packages/phonicsmaker/edit-studio/SKILL.md`, and
`packages/phonicsmaker/reading-error-coach/SKILL.md`.

## Executive verdict

The inspected standalone core is an **async RunPod worker**, not a routed
FastAPI application and not a Modal app. Its actual differentiated product is
an illustrated, curriculum-aware phonics story/decodable-book generator plus
two editing paths: command/operation editing and a layout-data Studio re-render.
The current entry point is `runpod.serverless.start({"handler": handler})`, and
the Next.js routes submit to RunPod `/run` and poll `/status`.
[`runpod_handler.py:25-39,338-343`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/runpod_handler.py)
[`generate-pdf/route.ts:19-24,72-104`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/generate-pdf/route.ts)

There is **no standalone worksheet generator, assessment engine, decodable
reader-pack builder, or game-board renderer in this core checkout**. The web
checkout separately exposes nine one-call Gemini teacher utilities and retains
84 more API prompt handlers; 80 appear in commented-out UI configurations and
four have no active UI definition. Product notes
attribute richer worksheet, activity, pack, collection, sharing, school, and a
Modal implementation to fuller monorepos that were not supplied as the code
target here. Those claims are useful roadmap context, not deployable evidence
for this port.
[`toolConfig.ts:19-556`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/shared/toolConfig.ts)
[`CIM-features-inventory.md:29-49`](/Users/yifan/phonicsmaker/CIM-features-inventory.md)

| Candidate | Honest gate now | Modal verdict |
| --- | --- | --- |
| `phonics-reading-error-coach` | SKILL spec exists; one bounded LLM call, no file artifact | **Closest to build-ready**, but still needs a reviewed profile, JSON schemas, fixtures, educator eval, and pricing evidence |
| `phonics-worksheet-generator` | Flagship SKILL spec exists; requested workflow is not present in the inspected core | **Build required / fail closed** until the deterministic content manifest, PDF renderer, approved assets, private artifact delivery, and educator acceptance gate exist |
| `phonics-story-edit-studio` | Existing source can re-render editable layout JSON | **Portable but blocked** on ownership-safe artifact input, immutable versioning, renderer dependencies, UI/runtime separation, and tests |
| `illustrated-decodable-story-maker` | Existing RunPod workflow produces PDF + thumbnail + editable JSON | **Port required**, not a decorator swap: remove RunPod/DB/email coupling, materialize Modal image/assets/secrets, normalize contracts, test, meter, and deliver private artifacts |
| Nine visible toolkit utilities | One Gemini call each, Markdown output | **Good Phase-3 batch**, one reviewed schema/profile/container per listing; do not expose the current unvalidated generic `/api/tools` route |
| 84 prompt-only handlers | Prompt code exists; UI configs are commented out or absent | **Inventory only**, not listings, until each input/output and educational correctness is verified |

The recommended commercial order remains: **Phase 1 hosted worksheet flagship
plus one low-risk tool canary; Phase 2 original downloadable packs; Phase 3
story/editor and the audited toolkit.** “Already on Modal” must not be claimed
for this checkout.

## 1. Product inventory

### 1.1 What the standalone core actually does

The core has one public serverless handler. `mode` chooses generation or edit;
Studio regeneration is a special edit operation. The current output is an
illustrated story/decodable book, not a worksheet. The PDF compositor adds
phoneme highlighting, smart text positioning/contrast, printable variants,
thumbnail creation, editable generation JSON, storage, and optional completion
email.
[`runpod_handler.py:25-39,42-168,171-310`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/runpod_handler.py)
[`story_tasks.py:37-301`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/tasks/story_tasks.py)

| Teacher tool / feature | Produces | Exact source input fields | Invocation today | Omo marketplace potential |
| --- | --- | --- | --- | --- |
| **Illustrated phonics story / decodable-book generator** | A cover plus illustrated story pages compiled to PDF; current handler returns `pdf_url`, `thumbnail_url`, `task_id`; generation also persists editable JSON. Paid scene count is clamped to 7-21; free mode forces six scenes. | Golden fixture top level is `input`; inside: `mode`, `phonemes`, `story_idea`, `difficulty_level`, `is_free`, `user_email`, `language_variant`, `curriculum`, `highlight_text`, `printable`, `art_style`, `page_count`, `progressive_highlighting`, `debug_config`; debug fixture also uses `avoid_upload`, `load_from_task_id`, `save_intermediates`, `start_from_step`, `use_mock_generation`. | Next.js `POST /api/generate-pdf` → RunPod `POST /run` → `handler` → `process_generate_job` → `generate_story_task`; client polls status. | **High differentiation.** Sell as `illustrated-decodable-story-maker`, a runnable $4-$8 candidate only after costs/yield are measured. Do not call it a worksheet generator. |
| **Natural-language story/PDF editor** | Revised PDF + thumbnail; existing flow returns source task ID, backup PDF/JSON URLs and applied operations, and overwrites the current URLs. | Golden fixture: `input.mode`, `input.user_email`, `input.edit_config.task_id`, `input.edit_config.command`. Gemini maps the command into supported operations. | Next.js `POST /api/edit-pdf` → RunPod `/run` with `mode: edit` → `AgentService` → `edit_pdf`. | **Useful add-on**, not a safe standalone runtime yet. Omo should require source ownership, show/confirm normalized operations, and version output instead of overwriting. |
| **Structured story/PDF editor** | Same revised PDF/thumbnail plus operation audit; can preserve the original images for text/title/highlight changes or regenerate one image. | `edit_config.task_id`, `edit_config.operations[]`; implemented operations are `change_scene_text(scene_number,new_text)`, `change_story_title(new_title)`, `toggle_highlighting(highlight)`, and `regenerate_scene_image(scene_number,user_request)`. | Same RunPod edit path, bypassing natural-language interpretation. The web image-refinement route submits `regenerate_scene_image`. | **Strongest safe editor core.** Make this the hosted execution contract; natural language is only an optional preprocessor. Text/layout tier can be cheaper than image refinement. |
| **Interactive Edit Studio save/re-render** | Browser canvas can download a rasterized PDF; server save sends edited story layout JSON and produces new PDF + thumbnail + updated editable JSON. | Golden fixture still uses `mode`, `user_email`, `edit_config.task_id`, `edit_config.operations`; first operation is `operation: regenerate_pdf_from_data` with `story_data`. Story keys: `task_id`, `story_title`, `original_story_title`, `pages`, `phonemes`, `difficulty_level`, `is_free`, `highlight_text`, `printable`, `art_style`, `page_count`, `progressive_highlighting`, `language_variant`, `curriculum`, `created_at`, `version`, `last_modified`, `highlightEnabled`, `highlightColor`. Page keys: `pageNumber`, `image_url`, `image_prompt`, `objects`; objects include bounded text/layout/style fields. | Browser GETs editable JSON from Spaces; local Zustand/Konva UI edits it; `POST /api/studio/regenerate-pdf` submits `regenerate_pdf_from_data` to RunPod. | **High retention value, lower standalone discovery.** List as `phonics-story-edit-studio` once Omo has an owned source artifact. The SKILL is the save/export worker, not the interactive React editor. |
| **PDF composition modes** | Normal or printable PDF, optional phoneme highlighting, progressive highlighting, dynamically selected text/stroke colors, cover/scene layouts, thumbnail. | Generation fields `printable`, `highlight_text`, `progressive_highlighting`, `art_style`; Studio adds per-object position/typography and `highlightColor`. | Internal generation/edit services, not a separate endpoint. | **Feature set, not separate listings.** Use as variants/options inside story and worksheet products. |
| **Curriculum/language controls** | Story text constrained by level, language instructions, curriculum context and NGSL examples. | Backend enums: difficulty `"1"`…`"6"`; languages `en_au`, `en_uk`, `en_us`, `fr`; curricula `general`, `vic`, `sg_moe`, `us_ccss`. | Story service loads `knowledge_base.json` and adds matching context before Gemini generation. | **Differentiator only after educator review.** Avoid “aligned” claims until a reviewer verifies the exact output/test set. |

Evidence for the gold shapes is in
[`test_input_generate.json`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/test_input_generate.json),
[`test_input_edit.json`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/test_input_edit.json),
[`test_input_edit_studio.json`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/test_input_edit_studio.json),
[`test_input_debug.json`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/test_input_debug.json),
and [`test_input.json`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/test_input.json).
Operation implementation is at
[`edit_operations.py:98-188`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/editing/edit_operations.py);
the Studio field model is at
[`studioStore.ts:5-68`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/stores/studioStore.ts).

#### Current invocation, end to end

```text
Dashboard form
  -> Next.js /api/generate-pdf or /api/edit-pdf
  -> https://api.runpod.ai/v2/<endpoint>/run
  -> runpod_handler.handler({id, input})
       generate -> Gemini text/prompt calls -> Runware images
                -> image/text compositor -> WeasyPrint PDF
                -> Spaces + PostgreSQL + optional Resend
       edit     -> optional Gemini function calling
                -> load/backup Spaces JSON/PDF -> patch -> render -> overwrite
       studio   -> regenerate_pdf_from_data -> render supplied layout -> overwrite
  -> Next.js polls RunPod /status/<id>
  -> URL result shown/downloaded
```

The public README agrees that the serverless surface is RunPod `/run` or
`/runsync`, though parts of its enum documentation drift from the implementation.
[`README.md:178-238`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/README.md)

### 1.2 The nine visible web toolkit tools

These are not `phonicsmaker-core` routes. They are live configurations in the
standalone web app. Every tool posts `{tool, payload}` to one generic Next.js
route, which calls `gemini-2.0-flash` and returns `{result, description}` as
Markdown-like text. The current route has no per-tool JSON schema, auth,
entitlement, bounded output contract, or provider-usage envelope; the form also
does not initialize configured defaults or enforce `required` before submit.
[`tools/route.ts:1-37`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/tools/route.ts)
[`toolkit-form.tsx:50-95,153-266`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/[lang]/dashboard/toolkit/_components/toolkit-form.tsx)

| Visible tool | Input field names and configured bounds | Current output / Omo listing |
| --- | --- | --- |
| **Phonics Word List Generator** | `phonemes[]`, `topic`, `difficultyLevel` = `beginner|intermediate|advanced` | Sorted Markdown word list with target graphemes highlighted and brief notes. `phonics-word-list-generator`; $0.10 hosted-call candidate or $3 skill download after QA. |
| **Syllable Splitter and Counter** | `wordList` textarea | Word, syllable split and count. `syllable-splitter-counter`; one-call candidate, but pronunciation/dialect accuracy needs fixtures. |
| **Story Idea Generator** | `genre?`, `numCharacters?` 1-10, `settingKeywords?`, `numIdeas` 1-10 | Numbered short ideas. `phonics-story-idea-generator`; only market as phonics-specific after the input/output actually enforces phonics scope. |
| **Digraph Spotter** | `textInput`, `digraphType` = `all|consonant|vowel`, `includeExplanations` = `yes|no` | Marked text + unique digraph summary/explanations. `digraph-spotter`; good deterministic+LLM hybrid candidate. |
| **Phoneme Counter** | `wordInput`, `showTranscription` = `yes|no` | Count and optional IPA. `phoneme-counter`; requires explicit dialect and pronunciation ambiguity output before sale. |
| **Decodable Sentence Creator** | `phonicsPattern[]`, `numSentences` 1-5, `sentenceLength` = `short|medium|long`, `includeSightWords` = `yes|no` | One sentence per line. `decodable-sentence-creator`; strong teacher utility after machine decodability validation replaces prompt-only trust. |
| **Phonics Rule Explainer** | `phonicsRule`, `targetAudience` = `early_reader|elementary|teacher_parent`, `numExamples` 2-5 | Rule, audience-adjusted explanation, examples and optional exceptions. `phonics-rule-explainer`; low-cost one-call candidate with educator eval. |
| **Grapheme-to-Phoneme Converter** | `textInput`, `includeRulesExplanation`, `includeExampleWords` | Simplified sound representation, optional rule/examples. `grapheme-phoneme-converter`; must distinguish pedagogical notation from IPA and add dialect. |
| **Decoding Error Analyzer** | `misreadWord`, `actualWord`, `includeDetailedExplanation`, `suggestPractice` | Possible confusion plus 1-2 practice suggestions. Wrapped here as `phonics-reading-error-coach`; add uncertainty and a non-diagnostic gate. |

Fields are defined at
[`toolConfig.ts:19-556`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/shared/toolConfig.ts),
and behavior prompts at
[`prompts.ts:5-200,803-840,1093-1182,2236-2282,4130-4356`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/tools/prompts.ts).

### 1.3 The “rest of the tools”: real prompt inventory, not ready listings

`src/app/api/tools/prompts.ts` contains **93** named prompt handlers. Nine have
active UI configs above. The remaining **84** retain commented-out UI configs
or have no active UI config, although the generic API can be called directly by
tool name. That is an unsafe accidental API surface, not proof that 84 products
work. Each needs a recovered field schema, default/required handling, negative
fixtures, bounded structured output, educator QA and a listing decision.

The 84 prompt-only names are:

```text
word-family-builder, text-summarizer, math-word-problem-explainer,
vocabulary-enhancer, historical-event-explainer, science-concept-explainer,
simplified-text-rewriter, multiple-choice-quiz-generator,
fill-in-the-blanks-generator, analogy-generator, debate-topic-generator,
learning-plan-outline-creator, rhyming-words-generator,
figurative-language-identifier, essay-outline-generator,
vowel-sound-categorizer, sight-word-flashcard-maker, blend-identifier,
letter-sound-matcher, cvc-word-creator, missing-letter-finder,
sentence-unscrambler, initial-sound-sorter, final-sound-sorter,
minimal-pairs-generator, high-frequency-word-checker, homophone-helper,
prefix-suffix-identifier, root-word-extractor, definition-lookup,
sentence-complexity-scorer, read-aloud-text-player, pronunciation-guide,
spelling-bee-practice-list, word-chain-game-starter,
acrostic-poem-assistant, alphabetical-order-checker, noun-finder,
verb-spotter, adjective-identifier, punctuation-placer,
capitalization-helper, contraction-tool, synonym-suggester,
antonym-suggester, onset-rime-splitter, word-ladder-creator,
cloze-passage-generator, auditory-discrimination-practice,
reading-fluency-timer, word-search-puzzle-maker, crossword-clue-generator,
character-trait-lister, setting-describer-ideas, story-sequence-suggester,
trigraph-detector, vowel-team-finder, r-controlled-vowel-spotter,
open-closed-syllable-identifier, silent-letter-highlighter,
plural-noun-generator, past-tense-verb-converter,
compare-contrast-word-pairer, cause-effect-sentence-starter,
fact-opinion-sorter, homograph-helper, compound-word-splitter,
analogy-completer, sentence-fragment-detector,
predictable-text-generator, echo-reading-prompter,
choral-reading-text-selector, elkonin-box-assistant,
sound-wall-categorizer, language-experience-story-starter,
joke-generator-phonics-based, tongue-twister-creator,
word-shape-puzzle-generator, literacy-game-idea-suggester,
phoneme-blending-practice, phoneme-segmentation-practice,
vocabulary-tier-sorter, code-snippet-explainer,
progress-monitoring-note-taker
```

Source inventory:
[`prompts.ts:5-4490`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/tools/prompts.ts).
Commented UI inventory begins at
[`toolConfig.ts:557`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/shared/toolConfig.ts).

Consequences for marketplace claims:

- A multiple-choice quiz prompt, progress-note prompt, word-search prompt, or
  literacy-game-idea prompt is **not** an assessment engine or PDF game-board
  generator.
- “80+ tools” can be described internally as a prompt inventory, not as 80+
  verified/runnable Omo listings.
- The sale-context notes say a fuller codebase has stand-alone worksheets,
  story-linked activities, answer keys, packs and collections, but none should
  be copied or marked ready until that exact owner-authorized source is supplied
  and audited.

## 2. The SKILL.md wrap

The house style used here follows
[`packages/ugc-script-studio/SKILL.md`](/Users/yifan/marketplace/packages/ugc-script-studio/SKILL.md)
and generated sources such as
[`containers/facebook-ads-copywriter/source/SKILL.md`](/Users/yifan/marketplace/containers/facebook-ads-copywriter/source/SKILL.md):
scalar YAML `name`/`description`, clear “When to use,” explicit inputs, ordered
workflow, output contract and hard rules. A SKILL remains reviewed source text;
the checked-in profile—not Markdown—must provide exact schemas, fixtures,
capability decisions, prompt/provider config, resources and pricing evidence.
[`packages/skill-to-modal/README.md:1-24`](/Users/yifan/marketplace/packages/skill-to-modal/README.md)

| Created spec | What it wraps | Runtime class / readiness |
| --- | --- | --- |
| [`packages/phonicsmaker/SKILL.md`](/Users/yifan/marketplace/packages/phonicsmaker/SKILL.md) | `phonics-worksheet-generator`: grade, focus sound/grapheme/word family, activity, page count, difficulty, dialect, print mode, theme → original worksheet PDF, optional key, content report | `complex_external` / **not ready**. It is the requested flagship contract, explicitly honest that the inspected core has no standalone worksheet executor. |
| [`packages/phonicsmaker/edit-studio/SKILL.md`](/Users/yifan/marketplace/packages/phonicsmaker/edit-studio/SKILL.md) | `phonics-story-edit-studio`: owner-authorized editable JSON + bounded operations → immutable revised JSON/PDF and QA audit | `private_artifact + deterministic_render`, optional image provider / **not ready**. It intentionally replaces in-place overwrite with immutable versioning. |
| [`packages/phonicsmaker/reading-error-coach/SKILL.md`](/Users/yifan/marketplace/packages/phonicsmaker/reading-error-coach/SKILL.md) | `phonics-reading-error-coach`: misread word, target, dialect, learner stage, detail → cautious structured hypothesis and practice ideas | `single_llm` / **candidate after profile + educator eval**. No diagnostic claim, no child identity, no file artifact. |

These files contain workflow specifications only. They do not reproduce core
prompts, curriculum text, fixture stories, image URLs, customer data, or
proprietary content.

## 3. Modal mapping

### 3.1 Target container shape

Every future runtime gets its own generated folder and release evidence:

```text
containers/<slug>/
  modal_app.py                 # @modal.asgi_app(requires_proxy_auth=True)
  source/SKILL.md              # exact reviewed source
  schemas/input.json
  schemas/output.json
  tests/cases.json
  tests/test_contract.py       # offline: no key, network, email or spend
  manifest.json
  capability-manifest.json
  pricing-report.json
  README.md
```

Ingress remains `POST /v1/runs` + `GET /v1/runs/{call_id}`, protected with
Modal Proxy Auth. Input validates before spawn/spend; output validates before
settlement. The Omo Worker owns auth, price, idempotency, reservation,
dispatch/polling, output validation, settlement/refund, and artifact
authorization. This matches the existing Facebook Ads/Woven generated pattern.
[`facebook-ads-copywriter/modal_app.py`](/Users/yifan/marketplace/containers/facebook-ads-copywriter/modal_app.py)
[`facebook-ads-copywriter/tests/test_contract.py`](/Users/yifan/marketplace/containers/facebook-ads-copywriter/tests/test_contract.py)

### 3.2 Source-to-contract normalization

The raw RunPod envelope `{id, input}` must not become the public Omo schema.
Omo supplies its own run ID; `mode`, `is_free`, `user_email`, `debug_config`,
RunPod job IDs and storage URLs are internal or removed. The source-parity
generate schema below records the gold fields while tightening actual enums and
bounds:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "phonemes": {
      "type": "array",
      "items": {"type": "string", "minLength": 1, "maxLength": 12},
      "minItems": 1,
      "maxItems": 12,
      "uniqueItems": true
    },
    "story_idea": {"type": "string", "minLength": 8, "maxLength": 1200},
    "difficulty_level": {"enum": ["1", "2", "3", "4", "5", "6"]},
    "language_variant": {"enum": ["en_au", "en_uk", "en_us", "fr"], "default": "en_au"},
    "curriculum": {"enum": ["general", "vic", "sg_moe", "us_ccss"], "default": "general"},
    "highlight_text": {"type": "boolean", "default": true},
    "printable": {"type": "boolean", "default": false},
    "art_style": {"enum": ["2d", "3d"], "default": "2d"},
    "page_count": {"type": "integer", "minimum": 7, "maximum": 21, "default": 7},
    "progressive_highlighting": {"type": "boolean", "default": false}
  },
  "required": [
    "phonemes", "story_idea", "difficulty_level", "language_variant",
    "curriculum", "highlight_text", "printable", "art_style",
    "page_count", "progressive_highlighting"
  ]
}
```

The raw fixture includes `page_count: 2`, which the current paid code silently
clamps to seven. Omo should reject or offer a documented smaller product tier,
not charge for a silently changed request. The current `page_count=None` path
can also fail before the comparison in `generate_short_scenes`; make it required
at the boundary.
[`story_service.py:32-64`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/story_generation/story_service.py)

The flagship worksheet contract is new rather than falsely derived from that
story fixture. Its reviewed profile must implement this shape from the created
SKILL:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "grade": {"enum": ["prek", "k", "1", "2", "3"]},
    "focus_type": {"enum": ["sound", "grapheme", "word_family"]},
    "focus_patterns": {
      "type": "array",
      "items": {"type": "string", "minLength": 1, "maxLength": 12},
      "minItems": 1,
      "maxItems": 6,
      "uniqueItems": true
    },
    "activity": {"enum": ["map-write", "sort", "sentence", "passage", "game", "classroom-check"]},
    "page_count": {"type": "integer", "minimum": 1, "maximum": 12},
    "difficulty": {"enum": ["introduce", "practice", "review", "mixed"]},
    "dialect": {"enum": ["en-US", "en-GB", "en-AU"]},
    "print_mode": {"enum": ["blackline", "color"]},
    "theme": {"type": "string", "minLength": 1, "maxLength": 64},
    "include_answer_key": {"type": "boolean"},
    "teacher_notes": {"type": "string", "maxLength": 800, "default": ""}
  },
  "required": [
    "grade", "focus_type", "focus_patterns", "activity", "page_count",
    "difficulty", "dialect", "print_mode", "theme",
    "include_answer_key", "teacher_notes"
  ]
}
```

For Studio, preserve the gold story-data fields but replace a bare `task_id` or
arbitrary `image_url` with an owner-authorized artifact descriptor. The public
input is `source_story` plus bounded `operations`; the worker resolves content
server-side, validates checksum/schema/version, and returns a new version. The
natural-language command path may exist in the UI but is not executed until the
user sees/accepts the normalized operation list.

### 3.3 PDF output envelope

Current code returns public-looking `pdf_url` and `thumbnail_url`. Omo should
normalize generated files into its output library's artifact shape. A PDF is
recognized by `kind: "pdf"`, `contentMediaType: "application/pdf"`, or
`format: "pdf-url"`; private `object_key` values are exchanged server-side and
never rendered as local paths.
[`research/output-ui-library.md:92-106`](/Users/yifan/marketplace/research/output-ui-library.md)

Proposed common output schema fragment:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "run_id": {"type": "string", "minLength": 8},
    "status": {"const": "completed"},
    "workflow_version": {"type": "string", "minLength": 5},
    "artifacts": {
      "type": "array",
      "minItems": 1,
      "maxItems": 4,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "kind": {"enum": ["pdf", "image", "json"]},
          "role": {"enum": ["worksheet", "answer_key", "story", "thumbnail", "editable_source"]},
          "object_key": {"type": "string", "minLength": 3},
          "filename": {"type": "string", "minLength": 5, "maxLength": 180},
          "content_type": {"enum": ["application/pdf", "image/jpeg", "image/png", "application/json"]},
          "bytes": {"type": "integer", "minimum": 1},
          "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
          "page_count": {"type": "integer", "minimum": 1, "maximum": 64}
        },
        "required": ["kind", "role", "object_key", "filename", "content_type", "bytes", "sha256"]
      }
    },
    "usage": {
      "type": "object",
      "description": "Measured provider calls/tokens/images plus Modal duration, storage, egress, retries, accepted-output status and estimated cost."
    }
  },
  "required": ["run_id", "status", "workflow_version", "artifacts", "usage"]
}
```

The final per-skill schema must further constrain required artifact roles and
its `usage` object; the generic fragment is not enough for compilation.

### 3.4 Executor/provider map

| Tool family | Calls in current code | Proposed Modal executor | Required capability decision |
| --- | --- | --- | --- |
| Illustrated story | For `N` scenes: approximately `N+2` Gemini text calls (story, cover prompt, per-scene prompts) plus `N+1` Runware image calls (cover + scenes), then CPU PDF/image work | Extract pure `execute_story(payload, services)`; inject provider/storage interfaces; run async Modal function with bounded parallelism and long timeout; no DB/email import | `multi_provider + image + private_artifact + native_pdf`; fail closed until all are reviewed and costed |
| Natural-language edit | One Gemini function-calling request; image operation adds a Gemini refinement + Runware image call | Split `interpret_command` from `apply_operations`; deterministic edit does not require LLM | Text-only interpretation may be `single_llm`; image edits remain `image + private_artifact` |
| Studio save/export | No LLM unless image refinement; CPU image/text composition + PDF | Owner-authorized JSON artifact → deterministic patch/render → new artifacts | `private_artifact + native_pdf`; interactive Konva/React UI is not in the container |
| Worksheet flagship | No matching current executor | LLM may draft a strict item manifest, but deterministic validators/layout/key generation decide acceptance; runtime reuses approved assets | `llm + native_pdf + private_artifact`; image generation should be build-time, not per-run v1 |
| Nine active utilities | One `gemini-2.0-flash` call per tool | Separate reviewed `single_llm` profile/container per slug with JSON—not Markdown—output | Existing compiler lane can support after schemas, prompt review, eval and model pricing |
| Reading Error Coach | Current analyzer uses one `gemini-2.0-flash` call | One schema-constrained reviewed model call with uncertainty + non-diagnostic guardrails | Best first canary; still requires educator acceptance benchmark |
| 84 prompt-only tools | Usually one Gemini prompt; some names imply audio/timer/puzzle behavior not actually implemented | Audit and classify individually; deterministic tools should not use an LLM by default | Do not mass-compile unknown/unbounded prompts |

Current provider evidence:

- Core text/story/image-prompt model: Google `gemini-2.0-flash` via REST.
  [`ai_config.py:23-27,45-118`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/core/ai/ai_config.py)
- Natural-language editing model: Google
  `gemini-2.5-pro-preview-05-06` with four function tools.
  [`agent_service.py:14-59,69-136`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/editing/agent_service.py)
- Images: Runware `runware:101@1`, 768×1024 JPEG, 28 steps, CFG 3.5;
  the 2D path adds LoRA `civitai:128568@747534`.
  [`ai_config.py:157-269`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/core/ai/ai_config.py)
- Toolkit route: Google JS SDK `gemini-2.0-flash`.
  [`tools/route.ts:1-23`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/tools/route.ts)

No model/provider should be silently substituted. The reviewed profile must
name exact provider/model/rates, output constraints, timeouts, retries and
secret **names**; tests never access secret values.

### 3.5 Modal image and external dependencies

The Python project pins Python 3.12 and includes FastAPI/Uvicorn, Jinja,
SQLAlchemy/psycopg2, Pydantic, WeasyPrint, Gemini, Runware, NumPy,
scikit-image/learn, OpenCV, boto3, Resend, RunPod, Clerk and Sentry.
[`pyproject.toml:9-45`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/pyproject.toml)

The current Dockerfile installs only `gcc`, `ffmpeg`, and `curl` after Python
dependencies. A Modal port must prove—not guess—the Debian runtime packages for
the pinned WeasyPrint/Pango/Cairo/Harfbuzz and OpenCV build, and should consider
`opencv-python-headless` if GUI libraries are unused. It must bundle, with
license evidence:

- `static/fonts/LexieReadable-Regular.ttf` and Comic Neue font files;
- `templates/cover_page_template.html`, scene, printable and trial templates;
- `static/images` assets actually required by rendering;
- `app/phonics_maker/curriculum_data/knowledge_base.json` and NGSL data;
- email templates only if notifications are explicitly kept outside the run
  path (recommended: omit them from the hosted executor).

Sources:
[`Dockerfile:1-43`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/Dockerfile),
[`templates/`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/templates), and
[`static/`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/static).

Use `/tmp/<run_id>` for ephemeral work, clean it in `finally`, and never rely on
the current relative `temp/` or `debug_data/`. The Modal image should copy only
required source/assets and pin every dependency; it should not embed `.env`, a
database URL, customer emails, public bucket credentials, or the full web app.

### 3.6 Pricing evidence and proposed gates

The existing Omo hosting process applies the repository cost model, 5× launch
markup and $0.10 minimum; an unpriced capability is non-chargeable.
[`research/hosting-runbook.md:239-255`](/Users/yifan/marketplace/research/hosting-runbook.md)
PhonicsMaker has no complete per-accepted-output evidence for Gemini retries,
Runware images, Modal CPU duration, storage/egress, artifact retention, refunds,
or failed-output yield. Therefore every media price below is a **marketplace
target, not an approved quote**.

| Listing/tier | Target buyer treatment | Pricing gate |
| --- | --- | --- |
| Reading Error Coach / other one-call utilities | $0.10 per completed call; optional $3 standalone SKILL download | Generate `pricing-report.json` from exact chosen model rates. Raise price if accepted-output cost × 5 exceeds $0.10. |
| Worksheet Generator v1 | Fixed 3-page worksheet + key at **$2/run**; add a 5-12 page **$5/run** tier only after v1 evidence | Charge only after accepted-output COGS (LLM, Modal, storage, QA retries, amortized build-time asset cost where policy includes it) is known and the target remains above the model floor. |
| Illustrated story | Candidate **$4** short / **$8** long successful artifact | Price by actual `N` Gemini/Runware calls, retries, compute and accepted yield. Current code's 7-21 scene range is too variable for one unmetered flat price. |
| Studio text/layout re-render | Candidate **$1** per immutable revision | Separate from image refinement; measure renderer/storage cost. |
| Studio image refinement | No quote yet | Runware/model/license/continuity acceptance cost is unresolved; stay non-chargeable. |
| Finished original PDF singles | **$2-$8** one-time download | Content product, not runtime pricing. Include review, asset creation, support, fees/refunds and license scope in margin. |
| Finished original bundles | **$15-$40** one-time download | Bundle only final approved products; comparison price/savings must be real. |

## 4. Marketplace listing plan

### Phase 1 — hosted flagship and safe canary

| Slug | Title | Treatment | Initial scope / target price |
| --- | --- | --- | --- |
| `phonics-worksheet-generator` | **Phonics Worksheet Generator — Print-Ready PDF + Answer Key** | Runnable cloud workflow; flagship | Start with one bounded 3-page K-1 CVC/digraph `map-write|sort|sentence` product, blackline/neutral, en-US or the founder-approved first dialect, at a target $2 completed run. Expand only after ≥95% educator-accepted output. |
| `phonics-reading-error-coach` | **Reading Error Coach — Possible Phonics Confusion + Practice Ideas** | Runnable one-call workflow; infrastructure/quality canary | Structured note, no PDF, no diagnosis, $0.10 target after exact model pricing and educator eval. This proves the PhonicsMaker SKILL→Modal path without pretending the PDF lane is ready. |

The flagship listing stays “coming after QA” until artifacts and acceptance are
real. A successful text-only canary is not evidence that PDF/image hosting is
complete.

### Phase 2 — original downloads

Use the same reviewed manifest/template/asset system to create static products,
then list them as downloadable content rather than runnable workflows:

| Download slug | Product | Target price |
| --- | --- | ---: |
| `cvc-word-families-printable-pack` | CVC read/map/write practice + answer keys | $6 |
| `digraphs-blends-worksheets-centers` | Digraph/blend worksheets, reusable centers and game pages | $8 |
| `decodable-readers-set-1` | Original short controlled readers + comprehension/retell and decodability report | $15 |
| `phonics-classroom-starter-bundle` | Final approved singles bundled together | $25-$35 |

Every pack is newly authored; do not extract fixture stories, production PDFs,
seller resources, or richer-monorepo proprietary content. The prior download
research supports focused $2-$8 resources and $15-$40 bundles, and already
defines appropriate print/educator QA gates.
[`research/tpt-phonics-plan.md:334-406`](/Users/yifan/marketplace/research/tpt-phonics-plan.md)

### Phase 3 — existing story/editor and audited tool shelf

| Slug / group | Title / treatment | Plan |
| --- | --- | --- |
| `illustrated-decodable-story-maker` | **Illustrated Decodable Story Maker** — runnable | Port the existing core only after RunPod extraction, private artifacts, image/provider licensing, cost/yield benchmark and educator story eval. |
| `phonics-story-edit-studio` | **Phonics Story Edit Studio** — runnable add-on | Accept only an owned Omo/PhonicsMaker editable artifact; text/layout first, image refinement later. A separate interactive front end may call the same contract. |
| Nine visible tools | Separate runnable listings; optional **Phonics Teacher Toolkit Starter** $15 SKILL bundle | Start with Reading Error Coach, Decodable Sentence Creator, Word List, Rule Explainer; add counters/converters only after dialect/linguist fixtures. |
| 84 prompt-only handlers | No bulk publish | Audit in risk/value batches: phonics foundations; word/vocabulary; literacy practice; puzzles/games; assessment/planning; general subjects. Delete or archive duplicates/unrelated concepts at product-review time rather than filling the catalog. |

### Listing truth labels

- **Runnable:** only after a protected deployed container, direct canary,
  schema-valid result, cost evidence, Worker billing/refund canary and approved
  catalog release.
- **Download:** a buyer receives an actual versioned PDF/ZIP or SKILL package;
  a repository file alone is not proof delivery works.
- **Planned:** SKILL/spec exists, but the listing cannot accept paid runs.
- **Existing PhonicsMaker feature:** verified in the inspected source but not
  necessarily ported to Omo.
- **Prompt inventory:** code name exists; no reliability or marketplace claim.

## 5. Luna build specification

### 5.1 Repeatable Phase-1 build sequence

For each Phase-1 tool, Luna follows this exact local-to-release sequence:

1. Read the relevant checked-in `SKILL.md` as source text and verify frontmatter,
   workflow, output contract, hard rules and provenance. Do not execute Markdown.
2. Create the reviewed `packages/skill-to-modal/profiles/<slug>.json` with exact
   Draft 2020-12 input/output schemas, happy fixture, multiple negative fixtures,
   bounded provider/resources, named secret requirements, marketplace metadata,
   fail-closed capability decisions and physical-unit pricing inputs.
3. Materialize only the approved executor. Generate
   `containers/<slug>/modal_app.py`, `source/SKILL.md`, schemas, prompt/assets,
   manifests, offline cases/tests, pricing report and README through the existing
   compiler/host pattern. Keep `requires_proxy_auth=True`.
4. Run schema validation and offline contract tests with injected fakes: invalid
   input fails before spawn; executor runs exactly once; missing capability/key
   fails closed; completed output validates; no network, email or spend occurs.
5. Run tool-specific quality evaluation below. Fix the source manifest or
   executor, not only a rendered artifact. Record accepted/rejected outputs,
   reasons, retries, cost and final hashes.
6. Generate/verify `pricing-report.json`. Any unpriced provider, compute,
   storage, egress, retry or accepted-yield unit makes the release
   non-chargeable.
7. Only after Harry authorizes production deployment: deploy to Modal, run one
   authenticated direct safe canary, register through the hosting pipeline,
   run drift checks and Worker suites, then separately approve catalog publish
   and a production billing/refund canary. Never treat a local test as a later
   gate.

The exact existing host sequence and gates are documented at
[`research/hosting-runbook.md:150-277`](/Users/yifan/marketplace/research/hosting-runbook.md).

### 5.2 Tool-specific work

#### A. `phonics-worksheet-generator`

Luna reads `packages/phonicsmaker/SKILL.md`; freezes the initial narrow scope;
authors a structured item/answer/provenance manifest; writes deterministic
phonics validators; builds original HTML/CSS worksheet/key components; bundles
licensed fonts and approved assets; renders with the selected PDF engine;
stores the PDFs privately; and returns the artifact/content-report envelope.
Tests cover every enum/bound, target-position accuracy, duplicates, dialect,
decodability exceptions, exact key agreement, missing assets, renderer failure,
file/page limits, checksum, artifact authorization and no paid placeholder.
The first evaluation set should contain at least 100 varied briefs reviewed by a
qualified K-2 literacy educator, with ≥95% accepted-output success and zero
wrong answer keys before a paid launch claim.

#### B. `phonics-reading-error-coach`

Luna reads the created coach SKILL; defines a small structured JSON output;
uses one reviewed schema-constrained provider call; adds dialect and uncertainty
checks; and creates an educator-labelled test set covering vowel substitutions,
consonant/digraph/blend changes, omissions/additions, silent-letter ambiguity,
homographs, non-words and inconclusive attempts. Tests prove no diagnosis,
certainty, learner-profile inference or more than two practice suggestions.
Price from actual provider usage. This can use the existing `single_llm` lane
once the evaluation and profile are approved.

The Studio spec is authored now but is Phase 3. Its build must additionally add
owner authorization, immutable versions, JSON migration, unchanged-page diffs,
per-operation tests, PDF visual regression and optional image-continuity QA.

### 5.3 Image/style needs

Use ChatGPT Images **at build time** to create only missing reusable clipart,
never as an unbounded v1 runtime step. Freeze a provenance-tracked style lock:

> `OMO_PHONICS_FRIENDS_V1`: an original friendly owl teacher mascot and a small
> cast of original animal learners; flat 2D storybook/vector feel; rounded dark
> teal outlines; warm coral, mustard, sky blue and leaf green palette; simple
> geometric shapes; inclusive, calm classroom energy; one unmistakable object
> or action; clean white/transparent background; readable at 1-1.5 inches; no
> letters, words, numbers, logos, watermarks, speech bubbles, branded clothing,
> protected characters, or decorative clutter.

Generate and approve a character sheet, pose sheet and object-icon set once.
Record prompt, model, date, provider/reference ID if available, asset ID, SHA-256,
review state, color/blackline derivative and every page where used. Luna places
all instructional text, graphemes, counters, boxes, grids and answers with code.
Runtime theme selection resolves approved asset IDs; it never regenerates the
same mascot per worksheet.

### 5.4 QA release checklist

#### Instructional

- [ ] Chosen dialect is explicit; every visible word is spelled accordingly.
- [ ] Target sound/grapheme occurs in the declared position and taught scope.
- [ ] Sentences/passages have a machine decodability report; exceptions are
      declared and justified.
- [ ] Every answer is unique or accepted alternatives are explicit.
- [ ] Answer keys derive from the same manifest and are independently checked.
- [ ] “Curriculum/standards aligned,” efficacy and diagnostic claims are absent
      unless separately evidenced and approved.
- [ ] Qualified educator review is signed, versioned and linked to the release.

#### Visual/PDF

- [ ] No image contains accidental text/logo or resembles a protected character.
- [ ] Image/object meaning is unambiguous in the selected dialect.
- [ ] Color and blackline variants work; color is never the only signal.
- [ ] All pages render to PNG for contact-sheet review; no clipping/overflow.
- [ ] Page order/count, embedded/licensed fonts, selectable text, safe margins,
      print-at-100%, file size, MIME, bytes and SHA-256 are verified.
- [ ] Worksheet, answer key, preview and thumbnail all match the listing promise.

#### Runtime/security/commerce

- [ ] Draft 2020-12 schemas are bounded with `additionalProperties: false`.
- [ ] Invalid input and missing capability/key fail before spend.
- [ ] Modal ingress uses Proxy Auth; Omo owns endpoint, schema and price.
- [ ] No `.env`, secret value, customer email, child name, local path or
      permanent public artifact URL appears in code, output or logs.
- [ ] Artifacts are owner-authorized, private, versioned, expiring and retained/
      deleted under a declared policy.
- [ ] Provider/model/license, dependencies, assets, prompts and datasets have
      provenance; SBOM/locks/notices are complete.
- [ ] Actual calls/tokens/images, retries, compute duration, storage/egress,
      failure/acceptance yield and estimated cost are recorded.
- [ ] Failure refunds once; idempotent replay cannot double-charge or duplicate
      provider mutations.
- [ ] Local tests, direct Modal canary, Worker deploy/canary and catalog publish
      are reported as separate gates.

## 6. Honest gaps and founder steps

### Deployment blockers today

1. **Wrong executor for the flagship.** The inspected core generates illustrated
   stories, not standalone worksheets. The worksheet SKILL is a product/build
   specification; Luna must materialize its manifest, renderer and validators or
   obtain and separately audit the fuller owner-authorized source.
2. **No Modal entry point here.** The standalone repo ends in RunPod startup;
   FastAPI is a dependency but no FastAPI route/asgi app is exposed. Product
   notes mentioning a fuller Modal implementation do not change this checkout's
   status.
3. **RunPod is coupled through the stack.** `job["id"]` supplies task identity and
   progress updates appear throughout story/edit/regeneration tasks. Modal needs
   Omo-owned IDs, injected progress and pure executor boundaries.
4. **Import-time infrastructure coupling.** Services are instantiated globally;
   database, storage, email and provider config are assumed. Modal must lazily
   initialize only required services and omit user email/Resend from the paid
   execution contract.
5. **System image unproven.** WeasyPrint/OpenCV/native libraries, fonts,
   templates, curriculum assets and licenses are not proven in a Modal image.
   Current Docker installs only gcc/ffmpeg/curl and has no render smoke test.
6. **Private artifact plane is not materialized for this workflow.** Existing
   core publishes to DigitalOcean Spaces and editing replaces URLs. Omo needs
   owned authorization, versioning, signed delivery, retention/deletion, size/
   checksum validation and refund-safe settlement.
7. **Contract drift.** Paid web forces 20 pages and loses the highlighting toggle
   because it reads `highlight_phonemes` while the form sends `highlight_text`;
   free web emits difficulty strings incompatible with backend enum `"1"`-`"6"`;
   README enum examples also drift. Normalize before porting.
   [`generate-pdf/route.ts:31-88`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/generate-pdf/route.ts)
   [`main-section.tsx:286-295`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/[lang]/dashboard/_components/main-section.tsx)
   [`free-generate/route.ts:30-56`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/free-generate/route.ts)
8. **Concurrency/timeout/cost unknown.** Scene prompts and images fan out in
   parallel; image calls allow 120 seconds and retry. There is no accepted-output
   cost/yield benchmark for 7-21 scenes.
9. **Tests are not release gates.** `test_edit_functionality.py` prints examples;
   other tests reference stale/missing services/templates or merely print. There
   is no schema contract, render regression, provider fake, end-to-end story,
   artifact, ownership, billing or educator-acceptance suite.
10. **Toolkit is prompt-first, not product-ready.** The generic API accepts any
    named prompt handler and raw payload; defaults/required fields are not
    enforced, outputs are free-form Markdown and educational accuracy is not
    benchmarked. Audit one tool at a time.
11. **Provider/asset rights and lifecycle.** Gemini/Runware secrets must use
    named Modal secrets; the Runware model/LoRA, fonts, curriculum data and image
    assets need commercial-use/provenance confirmation. Do not copy production
    customer files or prompts into Omo to solve this.
12. **External side effects.** Current generation can update PostgreSQL, upload
    public artifacts and email a user. An Omo run must not send email or mutate
    PhonicsMaker production data; control-plane registration/deploy/publish are
    separate authorized actions.

### Founder steps

**None are needed to accept this research/spec deliverable.** Before real build
or production release, Harry must explicitly:

1. authorize which PhonicsMaker source/assets may be reused and confirm the
   commercial rights for fonts, curriculum data, Runware model/LoRA and existing
   illustrations;
2. choose the Phase-1 buyer/dialect/license and name a qualified literacy
   reviewer (recommended first scope: K-1, one dialect, CVC/digraphs); and
3. approve any paid provider/ImageGen work, new secrets, production Modal/Worker
   deploy, catalog publication or external promotion under the repository safety
   rules.

Recommendation: use separate least-privilege Omo provider/storage secrets and a
new artifact namespace; do not reuse the PhonicsMaker production database,
email service or customer bucket for marketplace runs.

## Source index

### PhonicsMaker core

- Current entry/invocation and outputs:
  [`runpod_handler.py`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/runpod_handler.py)
- Golden request shapes:
  [`test_input_generate.json`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/test_input_generate.json),
  [`test_input_edit.json`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/test_input_edit.json),
  [`test_input_edit_studio.json`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/test_input_edit_studio.json),
  [`test_input_debug.json`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/test_input_debug.json)
- Story orchestration:
  [`story_tasks.py`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/tasks/story_tasks.py)
- Story/curriculum prompting:
  [`story_service.py`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/story_generation/story_service.py),
  [`curriculum_data_service.py`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/curriculum_data/curriculum_data_service.py)
- Providers/models:
  [`ai_config.py`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/core/ai/ai_config.py),
  [`agent_service.py`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/editing/agent_service.py)
- Editing/rendering:
  [`edit_service.py`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/editing/edit_service.py),
  [`edit_operations.py`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/editing/edit_operations.py),
  [`pdf_service.py`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/pdf_generation/pdf_service.py),
  [`PDF_EDIT_FUNCTIONALITY.md`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/PDF_EDIT_FUNCTIONALITY.md)
- Dependencies/image:
  [`pyproject.toml`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/pyproject.toml),
  [`Dockerfile`](/Users/yifan/phonicsmaker-local/phonicsmaker-core/Dockerfile)

### PhonicsMaker web/product context

- Toolkit config and prompt inventory:
  [`toolConfig.ts`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/shared/toolConfig.ts),
  [`prompts.ts`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/tools/prompts.ts),
  [`tools/route.ts`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/tools/route.ts)
- RunPod web adapters:
  [`generate-pdf/route.ts`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/generate-pdf/route.ts),
  [`edit-pdf/route.ts`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/edit-pdf/route.ts),
  [`studio/regenerate-pdf/route.ts`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/studio/regenerate-pdf/route.ts)
- Studio UI/data:
  [`studioStore.ts`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/stores/studioStore.ts),
  [`studio/[taskId]/page.tsx`](/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/[lang]/dashboard/studio/[taskId]/page.tsx)
- Qualified fuller-product claims:
  [`CIM-features-inventory.md`](/Users/yifan/phonicsmaker/CIM-features-inventory.md)

### Omo conventions

- Hosting contract/gates:
  [`research/hosting-runbook.md`](/Users/yifan/marketplace/research/hosting-runbook.md),
  [`research/skill-to-modal-pipeline.md`](/Users/yifan/marketplace/research/skill-to-modal-pipeline.md)
- Existing generated patterns:
  [`containers/facebook-ads-copywriter`](/Users/yifan/marketplace/containers/facebook-ads-copywriter),
  [`containers/woven-storybook-pipeline`](/Users/yifan/marketplace/containers/woven-storybook-pipeline)
- PDF/artifact renderer contract:
  [`research/output-ui-library.md`](/Users/yifan/marketplace/research/output-ui-library.md)
- Original phonics-download build/QA precedent:
  [`research/tpt-phonics-plan.md`](/Users/yifan/marketplace/research/tpt-phonics-plan.md)
