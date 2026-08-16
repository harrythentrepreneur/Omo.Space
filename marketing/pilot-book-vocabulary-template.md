# Pilot-book vocabulary — founder fill-in (5-minute job)

Goal: unblock `decodable-book-maker` (the GATE 1 pilot book at $0.99/run) so it
can host real runs. All machinery is done and fixture-proven. The ONLY missing
piece is the **reviewed content** — the five cumulative stage vocabularies and
the reviewed sight-word list. That is a Harry decision by design; we will not
invent word lists.

## Why this gate exists

Every child-visible word in the finished book must be decodable **within the
selected stage** or be on the reviewed sight-word list (a child's name is the
sole exception). The compiler hard-fails any run that introduces a word outside
both lists (typed `$:semantic_review_words`, zero double-charge, auto-refund),
which is exactly what protects the GATE 1 quality bars (>=95% valid-output,
<5% refunds).

## What to fill in

Paste the JSON below into
`packages/skill-to-modal/profiles/decodable-book-maker.json` as
`reviewed_spec.vocabulary` (add the `reviewed_spec` object if missing), or
hand the filled JSON to the growth loop and we bind it.

Rules (all enforced by the deterministic scanner):
- Stage keys MUST use the exact five enum values below (from the reviewed OSS contract).
- Stages are **cumulative**: stage N contains every word of stages 1..N-1.
- All lowercase; no spaces, punctuation, or duplicates within a list.
- The sight-word list may overlap a stage list — the scanner slots each token deterministically.
- Include enough words per stage for a ~6-page story (a workable floor is ~25–40
  CVC words per stage; stage 5 adds common-digraph words like `ship`, `chat`, `thin`).
- Only words YOU have reviewed belong here. Nothing may be auto-generated.

```json
{
  "vocabulary": {
    "provenance": "reviewed",
    "stages": {
      "short-a-cvc": [
        "... every decodable short-a CVC word that may appear ..."
      ],
      "short-a-plus-short-i-cvc": [
        "... stage 1 words PLUS short-i CVC words ..."
      ],
      "short-a-i-o-cvc": [
        "... stages 1-2 PLUS short-o CVC words ..."
      ],
      "mixed-short-vowel-cvc": [
        "... all previous PLUS words mixing a/i/o/u/e CVC ..."
      ],
      "mixed-cvc-plus-common-digraphs": [
        "... all previous PLUS common sh/ch/th/ck words (e.g. ship, chat, thin, back) ..."
      ]
    },
    "sight_words": [
      "... the reviewed sight list, e.g. the, is, to, of, and, in, on, for, was, with, are, he, she, they, we, you, have, said, look, see, come, there, here, go, no, yes ..."
    ]
  }
}
```

## The five stage enum values (must match exactly)

1. `short-a-cvc` — short-a CVC
2. `short-a-plus-short-i-cvc` — short-a + short-i CVC
3. `short-a-i-o-cvc` — short-a/i/o CVC
4. `mixed-short-vowel-cvc` — mixed short-vowel CVC
5. `mixed-cvc-plus-common-digraphs` — mixed CVC + common digraphs

## What we do the moment it lands

1. Bind it as `reviewed_spec.vocabulary` in the decodable-book-maker profile.
2. Regenerate the container through the canonical compiler.
3. Re-run the whole_book_vocabulary right/wrong needles against the REAL lists
   (stage-1 book with a name exception -> 100% within-stage, zero review words;
   an out-of-stage word -> `$:semantic_review_words`; unknown stage ->
   `$:semantic_unknown_stage`).
4. Flip `can_submit` -> true, generate the run-manifest + catalog row.
5. Deploy still needs the coordinator push + Harry's live-change approval.

## Fastest path for Harry

PhonicsMaker's teachers already live inside stages 1–5 (the product's own
scope). Copy the word bank your decodable-books tooling already trusts into
the five arrays, bump the sight list, and reply — that IS the reviewed source.
Alternative: name the existing PhonicsMaker resource that holds these lists and
we adopt it verbatim as `provenance: reviewed`.
**Time-saver option (2026-08-16):** a fully machine-validated CANDIDATE draft
(sourced from the canonical Dolch pre-primer+primer lists and standard CVC
word families, `provenance: candidate-unreviewed` so it is fail-closed and
cannot bind by accident) is ready at `research/candidate-vocabulary.json` with
the review doc at `research/candidate-vocabulary-draft.md`. Reply `approve
candidate vocabulary` to adopt it (after any edits you make), and the loop
binds/regenerates/flips. Your own bank still takes priority if you have one.

Status: AWAITING HARRY (2026-08-16). No words in this file are real content.