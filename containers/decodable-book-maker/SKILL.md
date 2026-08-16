---
name: decodable-book-maker
description: Make a reviewed en-US decodable phonics story and deliver it as a multi-page PDF book.
---

> **Omo open source.** This `SKILL.md` is published under the MIT License per the
> [Omo open-source policy](https://github.com/omo-space/skills/blob/main/POLICY.md). Download and reuse it freely; to run it
> without setup, use the hosted run on [omo.space](https://omo.space) — pay per
> run, no subscription.

# Decodable Book Maker

Create a short early-reader story for one reviewed cumulative phonics stage.
The buyer supplies a stage, a theme or topic, and optionally a child's name.
The primary deliverable is a real multi-page PDF book under the PhonicsMaker
identity, with the structured story and an auditable decodability report kept
alongside it.

## Workflow

1. Validate the selected cumulative phonics stage, bounded theme, and optional name.
2. Draft a title and at least three short Markdown story sections in en-US.
3. Restrict every child-visible title, heading, and story word to the compiler-owned vocabulary for the selected stage, the reviewed sight-word list, or the optional name.
4. Give an invalid draft one bounded repair; if it still cannot compile into the finite language, use a compiler-owned fluent stage-safe motif rather than deleting words into broken prose. Adapt the theme to what the selected vocabulary can express, and omit exact topic wording that is out of stage.
5. Recompute the decodability report deterministically and never deliver an out-of-stage provider draft.
6. Render the approved story with the reusable `book_pdf` renderer, persist it as an immutable run artifact, and return a signed PDF link.

## Input contract

- `phonics_stage` is one of five reviewed cumulative stages: short-a CVC;
  short-a plus short-i CVC; short-a/i/o CVC; mixed short-vowel CVC; or mixed
  CVC plus common consonant digraphs.
- `theme` is inspiration for the plot, not permission to introduce vocabulary
  beyond the selected stage. Very early stages may adapt it to a fluent
  stage-safe motif and omit topic words that the child has not reached.
- `child_name` is optional. When supplied, it is the sole special-word
  exception and is counted separately from decodable and sight words.

## Output contract

- `title`, `book`, and `page_plan` form the reviewed book source.
- `decodability` records the en-US dialect, selected stage, audited word counts,
  sight words used, optional-name occurrences, within-stage percentage, and
  any review words. A runnable result must contain no review words.
- `artifact` describes a real PDF with byte count, SHA-256, and page count.
- `artifact_url` is a short-lived signed download path for the PDF.
- `usage` reports provider/model calls, tokens, and estimated provider cost.

## Hard rules

- Dialect is en-US only in this release.
- Every child-visible title, heading, and prose word must pass the selected
  stage vocabulary check; reviewed sight words are disclosed separately.
- The optional name is never represented as stage-decodable unless it already
  belongs to the selected vocabulary.
- Keep at least three story sections and enough prose for a useful short book.
- Do not claim diagnosis, intervention, curriculum alignment, grade mastery, or
  suitability for a particular learner.
- Teacher or caregiver review is advised before use, especially for a learner's
  sequence, pronunciation, dialect, and school scope.
- The first release is text-led. The PDF has designed typography and color but
  does not promise generated illustrations.
- If a capability, artifact dependency, provider result, schema, semantic gate,
  or storage/signing dependency is unavailable, fail with a typed blocker
  before delivery or charging; never substitute a fake PDF.
