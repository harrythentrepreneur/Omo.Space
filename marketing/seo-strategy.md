# Omo long-tail SEO strategy: PhonicsMaker proof pages

## PART 2 — Long-tail as proof objects

**REASONED from the playbook and repository:** One page exists only if it carries one unique, verified proof object. For Omo, that means a real workflow run, the real printable or structured output, the exact current pay-per-use price, honest limitations, a named reviewer, and the date tested. A reviewed fixture is a test brief, not publishable proof. If nobody ran and reviewed the example, if the output cannot be inspected, or if the price is only a projection, the page does not ship.

**GROUNDED — PRIMARY:** This rule implements the playbook's evidence-first reading of Google's people-first guidance: original information, first-hand experience, clear sourcing, authorship, and a satisfying answer matter more than content volume. See [What actually appears to move the needle](ai-seo-playbook.md#what-actually-appears-to-move-the-needle) and [Omo's minimum publishable page brief](ai-seo-playbook.md#omos-minimum-publishable-page-brief).

**Explicit rejection — GROUNDED — PRIMARY/REASONED:** Do not create separate pages for “phonics worksheet for -at,” “phonics worksheet for -an,” “phonics worksheet for -ad,” or other pattern substitutions. Those are inputs to one useful worksheet page, not distinct intents or proof objects. The playbook explicitly rejects hundreds of “phonics worksheet for [word family]” pages and cites [Google's scaled-content-abuse policy](https://developers.google.com/search/docs/essentials/spam-policies): scaled query variants with little original value can violate policy regardless of how they were produced. Page count is not the goal; **proof density per page** is.

**REASONED operating test:** A new URL is allowed only when all seven answers are “yes”:

1. Does it answer a different teacher job, rather than substitute one input value?
2. Was the exact workflow run at least five times with declared safe inputs?
3. Can a visitor inspect the representative output in ordinary page text and, for file-producing workflows, preview or download the real artifact?
4. Does the page state the current buyer price exactly? If a workflow is unavailable or only provisionally priced, the page remains unpublished.
5. Are the reviewer name, test date, workflow/model version, elapsed time, revisions, and rubric recorded?
6. Are failure cases, teacher-review needs, dialect limits, and non-diagnostic/non-alignment boundaries visible?
7. Is the page a stable, crawlable URL whose visible facts match its canonical metadata and valid schema?

## PART 3 — The keyword-to-page map

**REASONED:** The queries below are editorial hypotheses derived directly from each reviewed skill title, inputs, and output contract. They are not claimed search volumes. Each supporting query belongs on the same page as its primary query; it is not permission to create a second variant page. Search Console query data and Bing grounding-query samples can later confirm or revise the phrasing.

**GROUNDED — REPOSITORY:** Titles, capabilities, bounds, and artifacts come from the 12 `packages/phonicsmaker` skill contracts. Target price/readiness comes from the matching reviewed profiles and pricing reports. Nine structured-result workflows have a reviewed **$0.10/run** target price. That does not prove a live storefront runner or checkout. The worksheet, illustrated-story, and edit-studio workflows are currently non-chargeable; their **$2.50**, **$1.62**, and **$1.00** figures are projections, not offers.

| Skill slug | Primary long-tail query | Search intent | Proof artifact that must back the page | Target price |
|---|---|---|---|---|
| **FIRST 1 — `phonics-list-generator`** | **Primary:** phonics word list generator by sound and difficulty<br>**Supporting:** create a dialect-aware phonics word list by topic | Generate a bounded classroom word list with target coverage and pronunciation cautions. | Five real runs of the reviewed `ch` + `sh`, beginner, farm-animals, eight-word brief; publish the actual list, match positions, coverage, ambiguity warnings, exact cost, and educator review. Validate theme relevance rather than assuming the fixture is correct. | **$0.10/run target**; live runner/checkout not yet proven |
| **FIRST 2 — `decodable-sentence-creator`** | **Primary:** decodable sentence generator by phonics pattern<br>**Supporting:** create short decodable sentences with sight words marked | Generate a small, teacher-reviewable practice set for a declared code scope. | Five real runs from the reviewed `cvc` + `sh_digraph`, two-short-sentence brief; show the full input, representative JSON/readable sentences, target-word coverage, disclosed sight/irregular words, run cost, failures, and named educator review. | **$0.10/run target**; live runner/checkout not yet proven |
| **FIRST 3 — `digraph-spotter`** | **Primary:** find consonant and vowel digraphs in a passage<br>**Supporting:** highlight digraphs in text with explanations | Analyze supplied text and locate exact digraph spans without changing the passage. | Five real runs including “The chick sat by the green shed”; publish source text, exact zero-based spans, mechanical substring verification, classifications, context cautions, cost, and review. | **$0.10/run target**; live runner/checkout not yet proven |
| `phonics-reading-error-coach` | **Primary:** analyze a misread word for possible phonics confusion<br>**Supporting:** phonics practice ideas for one reading error | Get a cautious teaching hypothesis and up to two reviewable practice ideas—not an assessment or diagnosis. | Five real runs including the reviewed `lap` attempt versus `lamp` target; show the observation, possible confusion, suggestions, uncertainty language, rubric results, exact cost, and named educator review. Never include learner identity. | **$0.10/run target**; live runner/checkout not yet proven |
| `phoneme-counter` | **Primary:** count phonemes in an English word by dialect<br>**Supporting:** phoneme counter with IPA transcription | Check a word's likely phoneme segmentation, count, optional IPA, and pronunciation uncertainty. | Five real runs including `ship` in `en-US`; show the actual segment list, count-equals-list check, IPA, alternate-pronunciation note, cost, and review. | **$0.10/run target**; live runner/checkout not yet proven |
| `syllable-splitter-and-counter` | **Primary:** split and count syllables in a word list by dialect<br>**Supporting:** syllable counter with hyphenated word breaks | Analyze up to 30 supplied words and return spelling-preserving splits, counts, and ambiguity notes. | Five real runs including `elephant` and `paper`; publish input-preserving splits, count checks, dialect/ambiguity notes, cost, and review. Validate spoken-boundary conventions. | **$0.10/run target**; live runner/checkout not yet proven |
| `grapheme-to-phoneme-converter` | **Primary:** convert an English word from graphemes to phonemes<br>**Supporting:** grapheme to phoneme converter with IPA by dialect | Convert one word or grapheme to a likely sound representation with examples and uncertainty. | Five real runs including `ship` in `en-US`; show phonemes, IPA, mapping explanation, genuine examples, uncertainty, exact cost, and review. | **$0.10/run target**; live runner/checkout not yet proven |
| `phonics-rule-explainer` | **Primary:** explain a phonics rule with examples and exceptions<br>**Supporting:** phonics rule explainer for teachers and parents | Understand one reviewed pattern at a selected audience level without presenting it as exceptionless. | Five real runs including `silent_e`, elementary audience, three examples; show the explanation, examples, exceptions note, teacher-review flag, cost, and named review. Validate every example rather than treating the fixture as educational proof. | **$0.10/run target**; live runner/checkout not yet proven |
| `story-idea-generator` | **Primary:** story idea generator for students by age and setting<br>**Supporting:** child-safe classroom writing prompt generator | Generate bounded, original premises for writing or lesson planning. | Five real runs including gentle mystery, two characters, school garden, age 8–10; publish the actual distinct premises/hooks, constraint check, safety review, cost, and named review. | **$0.10/run target**; live runner/checkout not yet proven |
| `phonics-worksheet-generator` | **Primary:** printable phonics worksheet generator with answer key<br>**Supporting:** create a phonics worksheet for a target grapheme | Generate and download a bounded, print-ready worksheet and key for one declared phonics scope. | After the runtime exists: five real runs of the reviewed Grade 1 `ch` sort brief; publish the actual two-page PDF and key, content manifest/report, rendered-page QA, hashes, limitations, exact final price, and educator review. No pages by word-family value. | **BLOCKED:** $2.50 projection only; no current sale price |
| `phonics-story-edit-studio` | **Primary:** edit a phonics story and export a new PDF<br>**Supporting:** change phoneme highlighting in a decodable story PDF | Revise an owned editable story while preserving the original and export a new version. | After owner-authorized storage/rendering exists: five real owned-source edits; show v1/v2 PDF and JSON, operation diff, untouched-page comparison, source-preserved QA, artifact hashes, exact final price, and reviewer. | **BLOCKED:** $1.00 projection only; no current sale price |
| `illustrated-decodable-story-maker` | **Primary:** illustrated decodable story generator with printable PDF<br>**Supporting:** make a phonics story with editable source and highlighting | Generate an original illustrated story, editable source, thumbnail, and print-ready PDF from a bounded phonics brief. | After the multi-provider runtime exists: five real 7–21-page runs; publish one actual PDF/JSON/thumbnail set, text/image/continuity and decodability QA, hashes, retries, exact final price, limitations, and educator review. | **BLOCKED:** $1.62 projection only; no current sale price |

**Why these three are first — REASONED:** `phonics-list-generator` and `decodable-sentence-creator` map directly to repeated lesson-preparation jobs and to the education wedge's decodable-text/CVC-word-sheet outcomes. `digraph-spotter` is a reusable paste-a-passage utility whose exact source spans can be mechanically verified, making it the cheapest objective proof of the remaining skills. All three produce bounded text/JSON, have a reviewed $0.10 target price, and are cheaper to run, inspect, and correct than PDF/image or interpretation-heavy workflows. Once the live price is verified, their “$0.10 for this bounded result, no subscription” contrast is clear for occasional use. That is a cost-structure claim only—not a claim that any one workflow equals a competitor's full curriculum, roster, analytics, assessment, or content suite.

**Why not the playbook's worksheet/edit proof assets first — REASONED from newer repository evidence:** Those formats remain strong once real, but the current reviewed profiles explicitly block submission because their renderers, artifact plane, ownership or educator-acceptance evidence, and final costs are unresolved. Publishing them now would violate the playbook's proof-object rule. No content priority can override runtime and pricing truth.

## PART 4 — Page template, sequencing, scaling rules, and measurement

### A. Minimum publishable page template

**GROUNDED/REASONED:** Use the playbook's [minimum publishable page brief](ai-seo-playbook.md#omos-minimum-publishable-page-brief) as a release checklist, not a writing suggestion.

1. **Static metadata and canonical URL**
   - URL: `/workflows/{skill-slug}/`.
   - Title: `{{Concrete outcome}} for {{teacher constraint}} — ${{exact price}} per run | Omo`.
   - H1: `{{Skill title}}: {{inspectable outcome}}`.
   - The title, H1, description, price, input, output, last-tested date, and limitations must be present in initial HTML, not injected only after interaction.

2. **40–80 word direct answer**
   - Template: “Omo's {{skill title}} turns {{bounded input}} into {{specific output}} for {{audience}}. A hosted run currently costs exactly **${{price}}**, with no subscription. The sample below was run on {{date}} and reviewed by {{full reviewer name and role}}. {{One decisive limitation or review requirement}}.”
   - Count the words before release. Do not say “from,” “about,” or “a few cents” where the exact current price is known.

3. **Worked example and proof object**
   - Show the complete safe input as text.
   - Show the representative output in readable HTML; do not make a screenshot the only source of facts.
   - Link the real preview/download for PDF/image artifacts and publish run ID, workflow version, bytes/hash where useful for reproducibility.
   - State actual elapsed time, revisions, charged price, and whether the representative run was selected from five declared tests.

4. **Test note**
   - Required fields: `Tested by`, `Educator reviewer`, `Date tested`, `Workflow version`, `Model/provider version`, `5-run input set`, `Elapsed time`, `Revision count`, `Success/failure count`, and `Rubric`.
   - The rubric must evaluate contract-specific facts: target coverage and irregular-word disclosure for sentences/lists; source-span fidelity for the digraph tool; uncertainty/non-diagnostic language for the coach; count consistency and dialect ambiguity for converters/counters; rendering, artifact agreement, ownership, and continuity for PDF/image workflows.
   - Never fabricate a reviewer, rating, quote, or successful run. Lack of a named educator review blocks publication.

5. **Limitations and sources**
   - Say exactly what still needs teacher review and what the workflow may get wrong.
   - Preserve each skill's hard boundary: no unsupported “fully decodable,” curriculum/standards/Science of Reading alignment, universal pronunciation, assessment, diagnosis, or efficacy claim.
   - Cite reviewed curriculum or pedagogy sources for educational claims; omit claims that have no source.

6. **Next action**
   - Primary: `Run this workflow for ${{exact price}}` only when checkout and fulfillment work end to end.
   - Secondary: `Inspect the open-source recipe` or `Download the tested sample` when the corresponding asset really exists.
   - A blocked workflow gets no “run” CTA and no public sales page. Its projected price is internal planning data, not an offer.

7. **Schema and machine-readable consistency**
   - Use one canonical URL and ordinary schema that matches visible content.
   - For a live workflow, use valid `Product` plus `Offer` only if the price, currency, availability, seller, and URL shown in schema exactly match the page.
   - Do not add ratings/reviews that do not exist, special “GEO schema,” or AI-only content. Validate the rendered page and structured data before publication.

### B. Build sequence

**GROUNDED/REASONED prerequisite:** The playbook says not to drive traffic into a broken value loop. Publication waits until checkout, fulfillment, attribution, and the first paid/repeat event can be measured. Creating local drafts and test plans is allowed; deploying, publishing, paying reviewers, or contacting teachers requires Harry's explicit approval.

1. **Pages 1–3:** phonics word list generator → decodable sentence creator → digraph spotter. Run each five times, obtain named educator review, build static pages from the template, and verify runner, checkout, price, CTA, fulfillment, and analytics before publication.
2. **Pages 4–6:** reading error coach → phoneme counter → syllable splitter and counter. These remain bounded, inspectable, and have a $0.10 target price; build only after the first expansion gate below passes.
3. **Pages 7–9:** grapheme-to-phoneme converter → phonics rule explainer → story idea generator. These are still cheap to prove, but their explanation/creative outputs require more qualitative review than exact spans and counts.
4. **Pages 10–12:** phonics worksheet generator → phonics story edit studio → illustrated decodable story maker. This is a readiness queue, not a publication promise. Each remains blocked until its reviewed profile is chargeable, all capabilities exist, five real runs pass artifact and educator QA, and a final exact price replaces the projection.

### C. Scaling gates

**All thresholds below are REASONED operating judgments.** Impressions and citations are diagnostics, never sufficient reasons to scale. Paid and repeat use decide whether content expansion is warranted.

**Gate 0 — release floor for pages 1–3 (all required):** checkout and fulfillment succeed without double charge; organic/AI landing, workflow start, paid run, revenue, and repeat run are separable; all three pages have real five-run proof, a named educator reviewer, exact current price, limitations, static canonical HTML, and valid visible-content schema. If any item fails, do not publish.

**Gate 1 — permission to build pages 4–6 (assess after 30 days with all first three indexed):** all three URLs are indexed/crawlable; together they record at least **100 non-brand impressions** and **20 qualified organic/AI visits**; and those visits produce at least **5 attributable paid runs**, including **2 repeat paid runs by at least 2 distinct teachers**. All conditions are required. “Qualified visit” means a non-bot visit landing on a proof page that inspects the sample or starts the matching workflow; it is not any pageview.

**Gate 2 — permission to build pages 7–9 (next 30-day cohort):** pages 1–6 together produce at least **20 attributable paid runs**, **5 distinct paying teachers**, and **3 distinct teachers who repeat a paid workflow within 30 days**. At least one of pages 4–6 must produce a paid run; otherwise revise the map instead of expanding it.

**Gate 3 — permission to build pages 10–12:** pages 1–9 together produce at least **50 attributable paid runs** and **10 distinct repeat-paying teachers within 60 days**. In addition, every artifact workflow must independently pass its runtime gate: chargeable reviewed profile, exact current price, five successful real runs, inspectable artifact delivery, no double charges, teacher-reviewable output, and named educator approval. A business signal cannot waive an artifact-readiness blocker.

**Stop/revise rules — REASONED:** If pages are not indexed, fix retrieval before copy. If there are impressions but fewer than 20 qualified visits, revise query/title/snippet fit rather than add pages. If qualified visits occur but there are no paid runs, inspect price, trust, sample, CTA, checkout, and fulfillment. If first paid runs occur but no repeat use does, stop scaling content and fix usefulness or product reliability. Do not lower the proof standard to manufacture a pass.

### D. Measurement that will not lie

**GROUNDED — playbook business metrics, in priority order:**

1. Paid first workflow runs attributable to organic/AI referrals.
2. Paid repeat runs or second-book events.
3. Revenue per qualified organic visit.

**GROUNDED — playbook discovery diagnostics:**

- indexed/crawlable workflow and proof URLs;
- non-brand impressions and clicks in Search Console;
- cited pages and grounding-query samples in Bing AI Performance;
- ChatGPT, Perplexity, Copilot, and Google referrals where a referrer is available;
- a manual prompt sample recording mention rate, citation rate, factual accuracy, and source URL;
- permissioned third-party mentions and demonstrations.

**REASONED implementation:** Record landing URL, workflow slug, referral class, sample inspection, workflow start, successful paid run, revenue, customer pseudonymous ID, and whether it is that customer's repeat run. Preserve privacy and do not infer a private chatbot prompt from referrer data. Report brand mentions, citations, cited pages, recommendation, referral visits, paid runs, and repeat runs separately.

Run the playbook's baseline and monthly diagnostic sample: **12 real buyer questions × 4 engines × 3 repeats = 144 responses**. Log whether Omo is mentioned, cited, described accurately, and clicked; do not turn the sample into a stable “rank” or population-level share of voice. Do not buy a GEO tracker inside the first $200.

Use this weekly decision log:

| Week | Indexed proof pages | Qualified organic visits | AI referrals | Paid runs | Repeat runs | Revenue / qualified visit | Prompt mentions / citations / accurate of 144 | New permissioned mentions | Decision |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| `YYYY-MM-DD` |  |  |  |  |  |  |  |  | keep / revise / stop |

**Decision rule — GROUNDED/REASONED:** Paid runs and repeat runs lead; qualified referrals come second; mentions, citations, and impressions diagnose discovery. Never call a citation a recommendation or a sale, never treat one prompt result as a rank, and never scale because pageviews or content count rose.
