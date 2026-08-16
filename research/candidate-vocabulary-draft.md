# Candidate vocabulary draft — for Harry's review ONLY (NOT reviewed content)

Date: 2026-08-16. Status: **AWAITING HARRY REVIEW**. Nothing here is bound,
nothing flips `can_submit`. This is a time-saver option, not a decision.

## What this is

The last gate before `decodable-book-maker` ($0.99 GATE 1 pilot book) can host
real runs is the **reviewed vocabulary content** (five cumulative stage lists +
sight-word list). The template at
`marketing/pilot-book-vocabulary-template.md` asks you to fill that in by hand.
This draft does 90% of that job for you **from canonical public sources**, so
your review is a check-and-sign, not an authoring session.

Machine artifact: `research/candidate-vocabulary.json` (exact shape the
compiler expects as `reviewed_spec.vocabulary`).

## What this is NOT — read this

- **NOT reviewed.** The JSON carries `"provenance": "candidate-unreviewed"`.
  The compiler's `whole_book_vocabulary` selector fires ONLY on
  `provenance: reviewed`, so this resource is rejected fail-closed and can
  never be bound or activated by accident. The loop will not flip it to
  `reviewed` without your explicit sign-off.
- **NOT PhonicsMaker's proprietary bank.** phonicsmaker.com is unreachable
  behind a Vercel checkpoint and no public PhonicsMaker word source exists
  (evidence: `research/decodable-vocabulary-source-hunt.md`). If your
  decodable-books tooling has its own word bank, **that takes priority** — paste
  it into the template instead and ignore this draft.
- **NOT auto-invented vocabulary.** Sourcing is documented per list below.

## Sources

1. **Sight words (92):** the Dolch word list, pre-primer (40) + primer (52)
   only, fetched live this tick from
   https://en.wikipedia.org/wiki/Dolch_word_list (public domain, 1936). Scope
   rationale: stages 1–5 are short-vowel CVC + common digraphs (kindergarten /
   early-grade-1 decoding); Grade-1+ Dolch words (e.g. `after`, `know`,
   `would`) are not decodable inside this scope and would be review words, so
   they are intentionally excluded. Overlap with stage lists (11 words, e.g.
   `can`, `big`, `that`) is allowed by the scanner and is normal in decodable
   readers.
2. **Stage pools (50 / 96 / 132 / 186 / 261 cumulative words):** standard
   short-vowel CVC word families per the conventional early-reading
   scope-and-sequence used by published phonics programs. Machine-checked
   invariants: every word is a real one-syllable word with exactly one vowel
   (a/e/i/o/u), no blends (`st-`, `pl-`…), no r-controlled vowels, no long
   vowels, no irregular pronunciations. Stage 5 adds only the common single
   digraphs sh / ch / th / ck / wh in CVC-shaped words (`ship`, `chat`,
   `thin`, `back`, `when`).

## What Harry needs to do (two options)

- **(a) Fastest:** reply `approve candidate vocabulary` — the loop flips
  provenance to `reviewed`, binds it into
  `packages/skill-to-modal/profiles/decodable-book-maker.json`, regenerates the
  container, re-runs the whole_book_vocabulary right/wrong needles against the
  real lists, and flips `can_submit`. (You can edit the JSON first — add/remove
  words — and reply `approve candidate vocabulary after my edits`.)
- **(b) Preferred if you have it:** paste the word bank your own PhonicsMaker
  decodable-books tooling trusts into
  `marketing/pilot-book-vocabulary-template.md`, per the template's fastest path.

## Validation evidence (this tick, run from the committed file)

```
stage counts: short-a-cvc 50 | short-a-i-cvc 96 | short-a-i-o-cvc 132 |
              mixed-short-vowel-cvc 186 | mixed-cvc-plus-common-digraphs 261
sight count: 92 = fetched Dolch pre-primer+primer exactly (diff: 0 extra, 0 missing)
single-vowel check: PASS (every stage token has exactly one vowel)
lowercase / no-punctuation / no-duplicates: PASS
cumulative property (stage N contains all of stage N-1): PASS
provenance: candidate-unreviewed (selector rejects -> fail-closed, schema_only)
```

Validator: `research/validate-candidate-vocabulary.py` (rerun anytime).
