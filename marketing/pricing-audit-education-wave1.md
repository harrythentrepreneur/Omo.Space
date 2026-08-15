# Education wave-1 pricing and COGS audit

**Snapshot:** 2026-08-14  
**Scope:** analysis only; no production canary, deploy, or provider call was performed.

## Executive conclusion

The existing **$0.10/run price is economically sound for all nine tools**. On a
conservative, unamortized runtime assumption and a 95% accepted-output yield,
estimated delivered COGS is **$0.000114-$0.000222 per run** (about
**0.011-0.022 cents**), producing **99.78%-99.89% gross margin** at $0.10. No
tool is below the 70% margin flag, and none is financially unsustainable at
$0.10.

The release risk is quality, not token cost. The best first wave is:

1. `decodable-sentence-creator`
2. `phonics-list-generator`
3. `digraph-spotter`

Keep all three at **$0.10/run for the 200-email pilot**, but do not activate
them merely because the builder gate passed. Their fixtures expose educator-QA
and contract problems that should be fixed before a teacher sees a paid result.

## Cost basis and assumptions

- The shared hosted path in `containers/omo-llm-runner/modal_app.py` permits one
  provider/model combination: **OpenCode Go / `deepseek-v4-flash`**, with
  thinking disabled, one provider attempt, strict JSON output, and at most
  1,200 output tokens. This supersedes the older MiniMax PR context.
- The canonical August 2026 repository snapshot in
  `site/deploy/cost-model.mjs` prices `deepseek-v4-flash` at **$0.14 per million
  input tokens and $0.42 per million output tokens**. The nine generated signed
  manifests instead contain $0.14/$0.28. This audit uses the higher canonical
  $0.42 output rate. The manifest rate is therefore not trusted for launch.
- Prompt-token estimates include the system prompt, realistic fixture input,
  and the strict output schema sent in `response_format`. The repo's stated
  estimator is approximately four English/JSON characters per token. The
  fixture's repeated `360 input / 260 output` usage values are test data, not
  measurements, so they are not treated as actual metering.
- Output-token estimates use the reviewed happy-path outputs. These are typical
  jobs: two short sentences, a short passage with three digraphs, one word, an
  eight-word list, one reading error, one rule with three examples, three story
  ideas, or two words to syllabify.
- The deployed runner shape is 0.5 CPU and 512 MiB. Applying the repo's checked
  Modal rates gives
  `0.5×$0.0000131 + 0.5×$0.00000222 = $0.00000766/second`. This audit charges a
  conservative **eight unamortized seconds/run = $0.00006128**, even though
  concurrency can share that cost. There is no warm-container allocation
  because `min_containers=0`.
- Guarded delivered COGS is `(provider tokens + eight-second runtime) / 0.95`,
  reserving for the pilot's 95% valid-output threshold. It excludes fixed
  engineering, support, tax, and wallet top-up fees. A $5 card top-up at an
  illustrative 2.9% + $0.30 would allocate about **0.89 cents of processing to
  each $0.10 of spend**; even adding that separately leaves roughly 90.9%
  contribution margin.

## COGS per run

Provider math for every row is
`(input_tokens×$0.14 + output_tokens×$0.42) / 1,000,000`.

| Tool | Realistic modeled job | Input tok. | Output tok. | Provider math | Provider COGS | Guarded delivered COGS |
|---|---|---:|---:|---|---:|---:|
| `decodable-sentence-creator` | 2 short sentences for CVC + `sh`, en-US | 325 | 84 | `(325×.14 + 84×.42)/1M` | $0.00008078 | **$0.00014954** |
| `digraph-spotter` | 32-character sentence, 3 explained matches | 315 | 119 | `(315×.14 + 119×.42)/1M` | $0.00009408 | **$0.00016354** |
| `grapheme-to-phoneme-converter` | `ship`, IPA + rule + examples | 256 | 79 | `(256×.14 + 79×.42)/1M` | $0.00006902 | **$0.00013716** |
| `phoneme-counter` | Count/transcribe `ship` | 213 | 41 | `(213×.14 + 41×.42)/1M` | $0.00004704 | **$0.00011402** |
| `phonics-list-generator` | 8 words for `ch`/`sh`, topic constrained | 334 | 244 | `(334×.14 + 244×.42)/1M` | $0.00014924 | **$0.00022160** |
| `phonics-reading-error-coach` | Compare `lap` with target `lamp` + 2 practices | 288 | 149 | `(288×.14 + 149×.42)/1M` | $0.00010290 | **$0.00017282** |
| `phonics-rule-explainer` | Silent-e explanation + 3 examples | 257 | 118 | `(257×.14 + 118×.42)/1M` | $0.00008554 | **$0.00015455** |
| `story-idea-generator` | 3 age-8-10 gentle-mystery ideas | 249 | 237 | `(249×.14 + 237×.42)/1M` | $0.00013440 | **$0.00020598** |
| `syllable-splitter-and-counter` | Split/count `elephant` and `paper` | 252 | 48 | `(252×.14 + 48×.42)/1M` | $0.00005544 | **$0.00012286** |

The guarded column includes the same runtime/yield calculation in every row:
`(provider COGS + $0.00006128) / 0.95`.

This is a realistic planning estimate, not invoice evidence. At the full 1,200
output-token ceiling, even roughly 1,150 input tokens would cost only about
$0.000665 at the conservative provider rate. Adding the same runtime and yield
guard produces about $0.000765 delivered COGS and 99.24% margin at $0.10.

## Margin at $0.10

Margin is `(0.10 - guarded delivered COGS) / 0.10`.

| Tool | Price | Guarded delivered COGS | Gross profit/run | Gross margin | Flag |
|---|---:|---:|---:|---:|---|
| `decodable-sentence-creator` | $0.10 | $0.00014954 | $0.09985046 | **99.85%** | Pass |
| `digraph-spotter` | $0.10 | $0.00016354 | $0.09983646 | **99.84%** | Pass |
| `grapheme-to-phoneme-converter` | $0.10 | $0.00013716 | $0.09986284 | **99.86%** | Pass |
| `phoneme-counter` | $0.10 | $0.00011402 | $0.09988598 | **99.89%** | Pass |
| `phonics-list-generator` | $0.10 | $0.00022160 | $0.09977840 | **99.78%** | Pass |
| `phonics-reading-error-coach` | $0.10 | $0.00017282 | $0.09982718 | **99.83%** | Pass |
| `phonics-rule-explainer` | $0.10 | $0.00015455 | $0.09984545 | **99.85%** | Pass |
| `story-idea-generator` | $0.10 | $0.00020598 | $0.09979402 | **99.79%** | Pass |
| `syllable-splitter-and-counter` | $0.10 | $0.00012286 | $0.09987714 | **99.88%** | Pass |

**70% threshold:** no flags. Even the manifest's current two-cent provider cost
ceiling would leave exactly 80% gross margin if it were ever reached, before
runtime and failed-output allowance. In practice the 1,200-token limit is far
below that ceiling for these rates.

## First-wave ranking

These scores rank the bounded teacher job, not the correctness of the current
implementation. “Seconds” is an architectural expectation from one bounded
provider call, not a measured SLO; launch copy must wait for real p50/p95
canaries.

| Rank | Tool | Need density | Job speed | Show-a-colleague output | Bounded paid outcome it can replace |
|---:|---|---:|---:|---:|---|
| 1 | `decodable-sentence-creator` | 5/5 | 5/5 | 5/5 | The phonics-specific slice of **Diffit's** differentiated-resource workflow (**$14.99/mo individual Premium**), not Diffit's passage/activity suite |
| 2 | `phonics-list-generator` | 5/5 | 5/5 | 4/5 | One phonics resource-generation job inside **MagicSchool's** 80+ teacher generators (**$12.99/mo Plus**), not its whole planning suite |
| 3 | `digraph-spotter` | 4/5 | 5/5 | 4/5 | The bounded text-to-language-feature analysis behind part of a **Twee** exercise workflow (**$10.50/mo billed annually**), not a CEFR lesson or worksheet |

### 1. Decodable Sentence Creator

This is the strongest pilot wedge because teachers repeatedly need fresh
practice sentences tied to the code they have just taught. The job is tiny,
requires no file upload or rendering, and the result is immediately legible in
a lesson plan, slide, or message to a colleague. It also gives the clearest
before/after demonstration: select patterns, receive annotated sentences.

The honest competitor claim is narrow: Omo replaces one phonics-specific
differentiated text-generation job that a teacher might otherwise use Diffit
Premium for. It does **not** replace Diffit's leveled passages, activities,
exports, or broader product.

### 2. Phonics List Generator

Word-list preparation is high-frequency lesson work, and position plus
pronunciation annotations make the output more useful than an unreviewed list
from a general chatbot. Eight to thirty items are quick to scan and easy to
share in a planning team. This is the closest of the nine to a repeat weekly
utility.

The scoped replacement is one phonics resource generator within MagicSchool's
paid generator bundle. Do not claim replacement of its lesson plans,
worksheets, feedback, student tools, or integrations.

### 3. Digraph Spotter

Pasting a short passage and receiving exact spans can remove a tedious markup
step. It is fast and potentially viral when the UI renders the occurrences as
visible highlights. The current JSON alone is less shareable; the product card
should not imply a polished highlighted worksheet until that presentation
exists.

The closest kill-list comparison is Twee's paid text-to-language-exercise
outcome. The honest claim is one bounded text-analysis step, not a full ESL
lesson, worksheet, audio/video workflow, or CEFR alignment.

### Why the other six are not wave 1

- `grapheme-to-phoneme-converter`, `phoneme-counter`, and
  `syllable-splitter-and-counter` are quick but isolated-word pronunciation is
  context- and dialect-sensitive. A visible wrong answer destroys more trust
  than the few seconds saved, and the outputs have low colleague-showing value.
- `phonics-reading-error-coach` addresses a real need but makes an inference
  about a learner from one attempted word. That is too close to assessment or
  diagnosis for the first paid impression.
- `phonics-rule-explainer` is easy to obtain elsewhere, not especially viral,
  and its current fixture already contains a questionable silent-e example.
- `story-idea-generator` is shareable but generic, weakly connected to the
  PhonicsMaker audience, and readily substituted by free general-purpose AI.

## Final price recommendations and grant math

Keep the pilot price uniform. COGS does not justify a higher floor; the pilot
needs evidence of repeat use and output acceptance before value-based repricing.

| Pick | Final price | Guarded COGS | Margin | `$5 ÷ price` | Recommended grant wording |
|---|---:|---:|---:|---:|---|
| `decodable-sentence-creator` | **10 cents/run** | $0.00014954 | **99.85%** | **50 runs** | “$5 credit = 50 sentence-creator runs” |
| `phonics-list-generator` | **10 cents/run** | $0.00022160 | **99.78%** | **50 runs** | “$5 credit = 50 word-list runs” |
| `digraph-spotter` | **10 cents/run** | $0.00016354 | **99.84%** | **50 runs** | “$5 credit = 50 digraph checks” |

The existing **“$5 = 24 books”** framing must not be reused for these tools.
They are not books, and at ten cents the arithmetic is 50 full runs. Exactly 24
runs would imply $0.20833/run, which the integer-cent ledger cannot represent:
$0.20 yields 25 runs, while $0.21 yields 23 full runs plus $0.17 credit.

## Risks and release blockers

### Critical before any paid teacher run

1. **The signed rate is stale or internally inconsistent.** All nine reviewed
   manifests use $0.28/M output while their referenced August cost-model hash
   resolves to a file stating $0.42/M. The runner meters and enforces its cost
   ceiling from the manifest value, so it currently underreports output COGS by
   33%. Regenerate/re-sign against one canonical rate registry and verify it
   against actual provider billing before activation.
2. **There is no real accepted-output or latency evidence.** The checked
   fixtures repeat synthetic usage numbers. A builder/schema pass does not
   establish phonics correctness, p95 completion time, or 95% valid-output
   success. Run educator-reviewed goldens and real provider/Worker/debit
   canaries before making “seconds” or paid-quality claims.
3. **No deterministic phonics verifier backs the LLM.** Schema validation proves
   shape, not that a word contains the requested phoneme, a sentence stays
   within the taught code, an IPA string is right, or a syllable boundary is
   defensible.

### Tool-specific brand risk

- **`decodable-sentence-creator` — high.** “Decodable” is relative to a
  learner's exact scope and sequence, but the input supplies only broad pattern
  enums. The prompt correctly avoids claiming full decodability; the product
  name and marketing can still overpromise. A sentence can quietly introduce
  untaught code. Require word-level code coverage and named educator review.
- **`phonics-list-generator` — high and already visible in its fixture.** The
  requested topic is “farm animals,” but half the fixture list (`chest`,
  `shell`, `bench`, `brush`) does not honor that topic. The annotations can also
  confuse grapheme labels (`ch`) with phonemes. Shipping this sample would look
  careless. Add deterministic constraint checks and an educator-approved
  phoneme notation policy.
- **`digraph-spotter` — medium/high.** Exact character spans are mechanically
  verifiable, but deciding that adjacent letters form one sound is contextual.
  More seriously, `occurrences` has `minItems: 1`, so a passage with no matching
  digraph cannot return the correct empty result. Fix the schema and add
  zero-match, overlap, capitalization, punctuation, and dialect goldens.
- **`grapheme-to-phoneme-converter` — high.** An isolated spelling cannot
  resolve heteronyms such as “read,” “lead,” or “record.” LLM-generated IPA is
  easy to get subtly wrong and hard for many buyers to verify. Require context
  or return explicit alternatives backed by a pronunciation lexicon.
- **`phoneme-counter` — high.** A confident integer looks objective even when
  dialect, rhoticity, coalescence, and transcription conventions change the
  answer. This is precisely the kind of tiny wrong answer teachers remember.
- **`phonics-reading-error-coach` — very high.** One misread cannot establish a
  learning pattern. The disclaimer helps, but generated “possible confusions”
  and practice advice can still be received as assessment of a child. Do not
  wave-1 this without literacy-specialist review, stronger UI framing, and a
  prohibition on diagnostic/clinical use.
- **`phonics-rule-explainer` — high.** The fixture uses `theme` as a silent-e
  example, a pedagogically questionable choice for a basic CVCe explanation.
  A polished but wrong rule explanation would directly embarrass the brand.
  Replace free generation with a reviewed rule/example bank or validate every
  generated example against one.
- **`story-idea-generator` — medium.** Originality and age suitability are
  subjective and not automatically verifiable. It can produce generic,
  repetitive, culturally awkward, or accidentally derivative premises. It is
  also not a phonics outcome, so it weakens the pilot's positioning.
- **`syllable-splitter-and-counter` — high.** Spoken syllabification and
  orthographic teaching splits are not the same thing, yet the output does not
  declare which convention it uses. Reasonable sources and dialects disagree
  on some boundaries and counts. Pick one reviewed convention, label it, and
  support alternatives before charging.

### Commercial risks outside model COGS

- At ten cents, support time and refunds dominate token cost. One manual support
  interaction can consume the gross profit from hundreds of runs.
- Per-run card charging would be uneconomic; wallet top-ups are essential.
- The proposed 95% affiliate share is not included in gross margin. If Omo kept
  only 5% of a ten-cent referred run, payment allocation plus COGS could exceed
  Omo's share. Affiliate economics need a separate contribution-margin rule.
- A cold or distant Modal/provider path may take longer than the “seconds, not
  minutes” job promise. Measure p50/p95 and use a durable async fallback before
  launch copy makes a speed claim.

## Decision

**Approve $0.10 as the pilot price floor, not production activation.** First
activate the three ranked tools only after the rate mismatch, zero-result
contract, educator goldens, real metering, accepted-output yield, and p95
latency are resolved. Revisit value-based pricing after the cohort supplies
repeat-use and willingness-to-pay evidence; COGS is not the limiting variable.
