# PhonicsMaker SaaS — complete feature map

Status: canonical parity reference. Reset 2026-08-17.
Source: local code, not live-site guessing. `phonicsmaker.com` is behind a
Vercel Security Checkpoint and is not the source of truth; the checked-out
repositories are.

Repositories:

- `web/` — `harrythentrepreneur/phonicsmaker-web-v1` (Next.js, 168 page routes, 120 API routes).
- `core/` — `harrythentrepreneur/phonicsmaker-core-v1` (FastAPI + Modal + RunPod).

The full product surface is the union of the web journeys and the core engine.
The core engine is the "same quality books" contract; the web surface is the
"same features" contract.

---

## 1. Core book / story engine

Entry points: `core/runpod_handler.py` (`process_job`), `core/modal_app.py`
(`generate`, `generate_draft`, `render_pdf`, `refine_image`), and
`core/app/phonics_maker/tasks/story_tasks.py` (`generate_story_task`).

### 1.1 Required inputs

- `phonemes` — target graphemes/phonemes.
- `story_idea` — the story brief.
- `difficulty_level` — reading level.

### 1.2 Optional generation controls (the real quality surface)

| Field | Meaning |
| --- | --- |
| `language_variant` | dialect/language (en_au, en_uk, en_us, fr) |
| `curriculum` | curriculum code (general, vic, sg_moe, us_ccss) |
| `year_level` | school year level |
| `student_age` | interest-level age band |
| `vocabulary_mode` | `decodable` \| `instructional` \| `authentic` |
| `focus_mode` | `phonics` \| `morphology` \| `both` |
| `morphology_focus` | selected prefixes/suffixes |
| `known_phonemes` | GPCs the learner already knows |
| `focus_phonemes` | 1-5 new GPCs being taught |
| `sight_words` | permitted irregular high-frequency words |
| `strict_decodable` | every word must be decodable |
| `story_format` | `storybook` \| `passage` |
| `highlight_text` | phoneme highlighting in rendered text |
| `illustration_style` | visual style (vivid_cartoon, soft_watercolor, accessibility, …) |
| `story_type` | `narrative` \| `rhyming_poem` |
| `book_layout` | `classic` \| `picture_top` \| `side_by_side` |
| `book_font` | `comic_neue` \| `lexie_readable` |
| `page_count` | number of pages |
| `include_activities` | include end-of-book activities |
| `activity_config` | per-activity enable flags (25 types) |
| `series_info` | `{book_position, total_books, series_name}` |
| `book_title` | explicit title |
| `series_characters` | recurring character continuity |
| `series_theme` | recurring theme |
| `character_pronouns` | `he/him` \| `she/her` \| `they/them` |
| `reference_task_id` | reuse a past book's characters/style |
| `reference_character_description` | explicit character continuity |
| `reference_seed` | deterministic image seed continuity |

Internal / removed for Omo: `user_email`, `api_key`, `debug_config`, `is_free`.

### 1.3 Output artifacts (one book run can emit all of these)

- `pdf_url` — full book PDF
- `pdf_compressed_url` — compressed PDF
- `thumbnail_url` — cover thumbnail
- `cover_image_url` + `preview_images` — cover and scene image strip
- `worksheets_url` — end-of-book worksheet PDF
- `book_only_url` — book-only PDF (no worksheets)
- `homework_url` — homework PDF
- `answer_key_url` — answer key PDF
- `pptx_url` — PowerPoint export
- `variations` — parallel differentiated PDFs per difficulty level
- `draft_data` — full editable scene/layout JSON (Studio source of truth)
- `audio_manifest` — per-scene narration manifest + QR + listen URL

### 1.4 Pipeline stages

1. Generate story text (multi-agent; vocab/focus/decodability constraints).
2. Generate cover + per-scene image prompts; optional character reference image.
3. Generate/validate images (ACE++ and non-ACE paths; per-scene refine).
4. Build end-of-book activities + answer key.
5. Render PDF (book, compressed, book-only, worksheets, homework, answer key).
6. Export PPTX + editable layout JSON + thumbnail.
7. Upload private artifacts; callback with result.
8. Optional: draft → refine image → re-render (Studio loop).

---

## 2. Worksheet engine

`core/app/phonics_maker/worksheet_generation/worksheet_service.py`.

- Three-agent loop: generator → curriculum evaluator → print/format evaluator.
- Up to 3 revision rounds with feedback carried into the next draft.
- Emits a full HTML worksheet plus a generation report; answer key derives
  from the same item manifest.

---

## 3. Activities engine (25 types)

`core/app/phonics_maker/activity_generation/activity_service.py` +
`activity_types.py`.

1. word_hunt
2. sound_matching
3. fill_in_the_blank
4. tracing
5. circle_sound
6. word_scramble
7. cut_and_sort
8. sentence_building
9. phoneme_spotter
10. rhyming_pairs
11. phoneme_position
12. sound_swap
13. syllable_count
14. word_ladder
15. read_and_draw
16. phoneme_count
17. odd_one_out
18. missing_sound
19. real_or_nonsense
20. word_building
21. crossword
22. comprehension_questions
23. vocabulary_building
24. synonyms
25. inferred_meaning

Each type has a deterministic `generate_*` method plus template data; a shared
answer key is produced from the same data.

---

## 4. Audio / narration engine

`core/app/phonics_maker/audio_generation/audio_service.py` +
`audio_types.py`.

- Per-scene narration with voice styles (warm, playful, calm, dramatic).
- Speed, locale (en_us, en_au, en_gb, en_nz, en_ca, fr, es), mp3.
- Book audio manifest with total duration, listen URL, QR code for back cover.
- Currently disabled in production (`include_audio = False`) pending provider
  balance; the code is complete and is part of parity.

---

## 5. Image engine

`core/app/phonics_maker/image_generation/image_service.py`.

- Cover validation and structured cover prompts.
- Character description extraction + character reference image generation.
- Illustration styles with per-style prompt/negative-prompt instructions.
- ACE++ and non-ACE generation paths; seed-based deterministic generation.
- Per-scene image refinement (`rewrite_prompt_with_change`).

---

## 6. Web SaaS surface (the "features")

168 page routes. Grouped into real product journeys:

### 6.1 Generation journeys (audience-specific)
`parents`, `schools`, `private-tutors`, `esl-educators`,
`special-education`, `homeschooling`, `older-and-neurodivergent-readers`,
`app`, `start`, `create`. Each has start → generate → result.

### 6.2 Dashboard product features
- **Worksheet generator** — generate, view, my-worksheets, my-collections,
  library, curricula, collection scheduling.
- **Book sets** — collections, custom book sets, per-set progress, planning.
- **Studio** — interactive edit/refine/re-render of a generated book.
- **Storybook editor** — editable layout JSON.
- **Toolkit** — the configured tool forms.
- **Games** — sound boxes, cosmic launch, crossword, phonics quest, phonics
  match, phonics fishing, phonics scramble, phonics games hub.
- **Dictation** — study and test per level/set.
- **High-frequency words** — graded test sets (G1/G2/G3, sets 2-10).
- **Syllable builder**.
- **Journal** — write, stories, per-story view.
- **Listening** — `/listen/[bookId]` narration player.
- **Digraph spotter**, **team personas**, **staffroom**, **share**, **roadmap**,
  **settings**, **support**, **about**.

### 6.3 School / team administration
- `join-school`, `school-admin` (invite, upgrade seats, remove member, resend
  invite, transfer ownership, update role, analytics, settings), `my-school`.
- `validate-school-code`, `create-school-license`, `admin/*` (schools,
  invite, analytics, email health/stats/backfill).

### 6.4 Sales / billing / auth
- Sales pages: lifetime, team, team-v2, sale, parents-old, free-trial.
- Checkout: create-checkout-session, school checkout/offer/lifetime, invoice,
  portal session, switch-to-annual, cancel/resume/recover subscription,
  activate-free-trial, subscription-info/check.
- Auth: login/signup (Clerk), verify-email, auto-signin.
- Webhooks: stripe, stripe-test, clerk, resend, loops, email-reply.

### 6.5 Marketing / content
- Blog (list + per-slug, RSS feed.xml), llms.txt, resources, pricing, faq,
  contact, about, ai-phonics-story landing, free-book funnel, legal pages.

---

## 7. Toolkit (teacher utilities)

`web/src/app/api/tools/prompts.ts` (`toolPromptMap`) + `shared/toolConfig.ts`.

- 66 configured tools (active forms).
- 81 prompt-only tools (reachable through the generic `/api/tools` route, no
  active form). Source snapshot inventory lists 147 distinct keys.
- Current generic route is unsafe for Omo (arbitrary tool name/payload,
  unbounded Markdown). Each tool must become a reviewed Omo capability with its
  exact input/output contract recovered from `prompts.ts` + `toolConfig.ts`.

---

## 8. Omo gap (honest)

Omo's current PhonicsMaker-related surface (`profiles/`, `containers/`,
`catalog.js`) is a thin slice:

- `decodable-book-maker` / `illustrated-decodable-story-maker` do not carry the
  full book contract above (vocabulary_mode, focus_mode, morphology, series,
  character continuity, page_count, book_layout/font/style, variations,
  draft/refine/render, pptx, homework/answer-key/book-only/compressed exports).
- The worksheet engine's 3-agent revision loop, the 25-activity engine, the
  audio narration engine, and the image refinement engine are not present as
  hosted Omo runtimes.
- The web journeys (games, dictation, high-frequency words, syllable builder,
  journal, studio, school admin) have no Omo equivalent yet.
- The differential harness has so far confirmed drift on only one tool
  (`phonics-list-generator`): field renames and Markdown-vs-JSON output.

Parity is not met until every section above has a hosted Omo runtime whose
teacher-facing inputs and logical outputs pass the differential harness.
