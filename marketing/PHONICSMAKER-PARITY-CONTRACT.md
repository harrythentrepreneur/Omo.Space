# PhonicsMaker → Omo Space parity contract

**Reset date:** 2026-08-17
**Status:** active product contract; inventory and implementation are in progress.

## Goal

Omo Space must provide the complete current PhonicsMaker product surface as hosted marketplace capabilities. This is a parity project, not a prompt-wrapper project.

For every PhonicsMaker capability that is in the source snapshot, Omo must provide:

- the same teacher-facing inputs, field names, defaults, options, bounds, and validation behavior;
- the same generation rules and quality controls, including book, worksheet, activity, audio, image, editing, and export behavior;
- the same output meaning, artifact types, page/content structure, answer-key relationship, and editable data where applicable;
- the same failure behavior: no fake success, no paid placeholder, no silent weakening of constraints;
- a proper Omo-hosted runtime, marketplace listing, authenticated run lifecycle, private artifact delivery, metering, and refund-on-failure behavior;
- a repeatable parity test proving the result against the PhonicsMaker source implementation.

Omo may add its own authenticated result envelope, ownership fields, billing ledger, and private artifact identifiers. Those are transport/platform concerns. They must not change the teacher-visible inputs or the educational output contract.

## Source snapshot

The current working source is split across:

- `/root/work/phonicsmaker/web` — Next.js product UI, input forms, dashboard features, tool configuration, collections, games, school/admin flows, billing and result surfaces.
- `/root/work/phonicsmaker/core` — Python generation/runtime code, story and worksheet pipelines, activities, audio, PDF/PPTX rendering, image processing, storage and task orchestration.

The checked-out feature snapshots at the time of this reset are:

- web: branch `feat/interest-age-selector`, commit `3ab74dceeb7691dc6464ced2728f6edef56c694a`;
- core: branch `feat/interest-age-decoupled-from-reading-level`, commit `4c31dc2aae366ae8c75f4c3f0580208a65904f7c`.

These branches must be reconciled with each repository's `origin/main` before an implementation release is called current. No secrets, customer dumps, `.env` files, or credentials are part of the source snapshot.

## What counts as the product surface

The audit must cover both repositories, not only the existing nine marketplace cards.

### Web/product journeys

At minimum, inventory and map every current user-facing journey under `web/src/app`, including:

- illustrated book generation and result/download flows;
- worksheet generator, worksheet approval, library, collections, schedules, curricula, DOCX/PDF exports and editable views;
- book sets, planning, progress pages, storybook editor and Edit Studio;
- toolkit forms and every configured/prompt-backed tool;
- phonics games, sound boxes, dictation, high-frequency-word tests and syllable builder;
- journal/stories and listening/audio surfaces;
- audience-specific generation journeys (parents, schools, tutors, ESL, special education, homeschool and related routes);
- sharing, saved work, preferences, support, team/school administration and entitlements;
- free-book/trial/upgrade/payment-result behavior where it affects access to product capabilities.

### Core/runtime behavior

At minimum, inventory and map every callable pipeline and output in `core/app/phonics_maker`, including:

- story generation, character/image generation and reference-book reuse;
- worksheet generation and its generator/evaluator/revision loop;
- all activity types and their template data;
- phonics, curriculum, dialect, age/interest and decodability rules;
- PDF, printable PDF, compressed PDF, book-only/homework/answer-key variants;
- PPTX/export paths, editable JSON/layout data and thumbnail generation;
- narration/audio manifests, QR/listen assets and locale/voice settings;
- editing operations, Studio re-rendering, image refinement and versioning;
- task lifecycle, progress callbacks, retry/error behavior, storage and result contracts.

A file name or old plan is not evidence of parity. Each row requires a live code path, input contract, output contract, and test or reproducible probe.

## Architecture decision

Use Omo's structure for hosting, but do not reduce PhonicsMaker behavior to generic unbounded LLM prompts.

- Keep the PhonicsMaker engines and educational rules as a versioned, source-owned runtime layer (`omo-phonicsmaker-*` family), with thin Omo adapters for authentication, job lifecycle, billing, private artifacts and marketplace registration.
- Reuse exact source logic or a behaviorally equivalent port for books, worksheets, activities, audio, exports and editors. A new implementation is acceptable only when the parity harness proves it against the source.
- Use one reviewed capability/profile and generated container per marketplace capability, backed by shared pinned PDF/audio/image/artifact layers.
- Keep the generic Omo Worker registry and run envelope. Do not add a hand-written route switch or client-controlled provider/prompt.
- Preserve the PhonicsMaker input schemas at the teacher boundary. Internal fields such as email identity, provider job IDs, storage URLs, billing state and task ownership are replaced by Omo-owned equivalents and never exposed as arbitrary client controls.
- A capability is not `ready`, `chargeable`, visible as a completed product, or deployable merely because a schema and prompt exist.

## Parity gates

Every capability must pass all gates before it is marked hosted:

1. **Inventory gate** — mapped to exact source paths, symbols, routes, templates and current behavior.
2. **Input gate** — same fields, defaults, enum values, limits, normalization, required/optional behavior and negative cases.
3. **Execution gate** — source logic or proven equivalent implementation is exercised; no placeholder or generic prompt substitution.
4. **Output gate** — same logical result, artifact roles, content structure, page count, answer/key linkage, editable fields and export variants.
5. **Educational QA gate** — spelling, phonics/decodability, curriculum/dialect behavior, age suitability, answer uniqueness and non-diagnostic boundaries.
6. **Artifact QA gate** — PDFs open, render, paginate and print correctly; fonts/assets are present; audio decodes; PPTX/JSON/thumbnail outputs are valid; hashes are recorded.
7. **Differential gate** — the same sanitized fixture inputs run through PhonicsMaker and Omo; canonicalized outputs match exactly where deterministic, and approved quality/equivalence checks pass where provider generation is stochastic.
8. **Hosted lifecycle gate** — authenticated submit/poll, ownership, idempotency, bounded retries, usage metering, output validation, private delivery and automatic refund on failed paid work.
9. **Marketplace gate** — listing copy, schemas, examples, price evidence, capability manifest, run manifest, catalog and Worker registry agree; no hidden unsupported controls.
10. **Release gate** — direct hosted canary, Worker canary, regression suite and independent review pass. Production deployment remains a separate Harry approval.

The project is not complete while any source capability is absent, partial, unhosted, or only represented by a draft listing.

## Delivery order

1. Freeze and reconcile the source snapshot; produce the complete feature/route/runtime matrix.
2. Build the differential harness and sanitized golden fixtures before porting more capabilities.
3. Port the shared PhonicsMaker runtime layers: task lifecycle, PDF/layout/fonts/assets, image, audio, artifact storage and result normalization.
4. Port the flagship book/worksheet flows and all exports/activities, then prove parity.
5. Port editors, Studio, collections, curricula, planning, games, dictation, high-frequency-word and listening surfaces.
6. Port every toolkit tool and prompt-backed capability with the actual PhonicsMaker input/output contract, not a guessed schema.
7. Register every completed capability through Omo's generated marketplace structure and keep incomplete rows fail-closed/unpublished.
8. Run full differential, visual, audio, export, ownership, billing/refund and hosted canaries.
9. Only after the complete matrix is green: prepare the production release proposal for Harry's explicit approval.

## Release language

Until the full matrix and release gates pass, Omo must say **parity in progress** or **hosted subset**, never “PhonicsMaker complete,” “same quality,” or “all tools live.”

Production deployment, public activation, billing changes, external sends and any provider spend remain approval-gated under `/root/marketplace/AGENTS.md`.
