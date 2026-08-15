# Omo AI SEO / GEO Playbook

**Research date:** 2026-08-13

**Scope:** Organic discovery for Omo Space, beginning with PhonicsMaker teacher workflows.

**Business constraint:** approximately $200, no paid ads, no subscription, and no external publishing or outreach without Harry's explicit approval.

## Evidence labels

- **GROUNDED — PRIMARY:** supported by an engine's own documentation or Google Search policy.
- **GROUNDED — OBSERVATIONAL:** supported by a study or case study, but not proof of causation.
- **GROUNDED — ANECDOTAL:** a named practitioner/community report; useful as a field signal, not a general rule.
- **REASONED:** a judgment for Omo based on the evidence and the repository. It has not been proven directly.

## The decision in one page

**GROUNDED — PRIMARY:** There is no separate technical “GEO trick.” Google says its AI search features use the same core Search ranking and quality systems, require pages to be indexed and eligible for a snippet, and need no special AI markup, AI text files, or AI-specific rewriting. Its current guide explicitly says Google ignores `llms.txt`. The durable work is still crawlability, useful original content, clear page structure, and a good page experience. ([Google: AI features and your website](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide))

**GROUNDED — PRIMARY:** AI discovery is nevertheless different in distribution. Google may “fan out” a question into several related searches before composing an answer. Bing exposes which URLs were cited and sampled grounding queries in its AI Performance report. That means one broad keyword ranking is a poor model for the whole journey; a page must be a strong source for a specific sub-question. ([Google AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [Bing Webmaster Tools AI Performance](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview))

**GROUNDED — OBSERVATIONAL:** Large brand-visibility studies find that broad web mentions and YouTube mentions correlate much more strongly with AI answer visibility than raw content volume. This is correlation, from samples tilted toward established sites, not evidence that manufacturing mentions will cause recommendations. ([Ahrefs: 75,000-brand AI visibility study](https://ahrefs.com/blog/ai-brand-visibility-correlations/))

**REASONED:** Omo's best near-term “AI SEO” is therefore a three-part system:

1. Make every valuable workflow crawlable at a unique, static URL.
2. Publish a small number of genuinely useful proof assets—real inputs, outputs, prices, limitations, and evaluation data.
3. Earn independent corroboration by letting real teachers and creators test those assets, then repurpose the same evidence across the listing, open-source repository, article, and video.

The target is not “more AI-written articles.” It is **more retrievable evidence that a teacher can verify and an answer engine can cite accurately**.

## How AI answer engines select sources and recommendations

The most useful model has four stages. A tactic can help at one stage and do nothing at another.

| Stage | What is known | Controllable Omo lever | Confidence |
|---|---|---|---|
| 1. Eligibility | Google requires crawlable, indexed pages that are eligible to show a snippet. ChatGPT search uses `OAI-SearchBot`; blocking it prevents a site from appearing in search answers except possibly navigational links. Perplexity says `PerplexityBot` obeys `robots.txt`. | Server-rendered/static workflow URLs, clean internal links, XML sitemap, intentional bot rules, no important facts hidden behind interaction. | **GROUNDED — PRIMARY** ([Google](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [OpenAI](https://developers.openai.com/api/docs/bots), [Perplexity](https://www.perplexity.ai/help-center/en/articles/10354969-how-does-perplexity-follow-robots-txt)) |
| 2. Retrieval | Google uses its index and can issue multiple related searches (“query fan-out”). Bing recommends accurate, fresh, well-structured pages with consistent entity and product information, while making clear that citation count is not a rank or authority score. | One page per real job-to-be-done; descriptive titles/H1s; direct answers; explicit price, grade/skill, input, output, date tested, and limitations. | **GROUNDED — PRIMARY** ([Google](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [Bing](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview)) |
| 3. Synthesis and citation | Engines need passages they can accurately use: evidence, examples, sources, clear sections, tables, and concise definitions all improve human comprehensibility. Research distinguishes being selected for retrieval from actually being used in the generated answer. | Put the answer and proof on the page, not only in screenshots; include a worked example, evaluation rubric, source notes, and a compact comparison table where useful. | **GROUNDED — PRIMARY/RESEARCH**, but format is not a guaranteed ranking factor. ([Bing](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview), [citation selection vs. absorption paper](https://arxiv.org/abs/2604.25707)) |
| 4. Brand recommendation | Recommendation and comparison prompts often draw from review sites, forums, and third-party discussion, while factual product prompts more often cite official pages. Across 75,000 brands, YouTube and general web mentions had strong correlations with AI visibility; page count had very little. | Earn accurate creator demonstrations, teacher quotes with permission, GitHub references, and relevant community discussion. Keep official product facts consistent everywhere. | **GROUNDED — OBSERVATIONAL**, not causal. ([Semrush prompt-intent study](https://www.semrush.com/blog/ai-search-visibility-study-findings/), [Ahrefs brand study](https://ahrefs.com/blog/ai-brand-visibility-correlations/)) |

### Engine-specific facts—not folklore

**Google AI Overviews / AI Mode — GROUNDED — PRIMARY.** Google says the usual Search requirements and policies apply, with no extra schema or “AI optimization” file. The system can use query fan-out and may surface a wider set of supporting links than classic search. Structured data remains useful only when it describes visible content and qualifies the page for an existing search feature. ([Google AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [Google AI features documentation](https://developers.google.com/search/docs/appearance/ai-features))

**ChatGPT search — GROUNDED — PRIMARY.** OpenAI documents crawl eligibility, not a public source-ranking formula. `OAI-SearchBot` controls search discovery independently of `GPTBot`, which controls potential training use; `ChatGPT-User` is user-initiated and is not the crawler that determines automatic search inclusion. Claims that a particular word count, schema, or prompt score “ranks in ChatGPT” are not official OpenAI guidance. ([OpenAI crawler documentation](https://developers.openai.com/api/docs/bots))

**Perplexity — GROUNDED — PRIMARY.** Perplexity says blocked pages will not have their full text indexed by `PerplexityBot`. Its public bot documentation establishes accessibility, not a deterministic ranking recipe. ([Perplexity robots.txt documentation](https://www.perplexity.ai/help-center/en/articles/10354969-how-does-perplexity-follow-robots-txt))

**Copilot / Bing — GROUNDED — PRIMARY.** Bing's current Webmaster Tools can report total citations, cited pages, grounding queries, and trends for Bing AI answers and Copilot. Bing recommends depth, evidence, readable sections, freshness, and consistent entity/product facts; it explicitly warns that citations are not an authority score. Sitemaps and IndexNow help discovery and freshness, especially for changing product information. ([Bing AI Performance](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview), [Bing on sitemaps in AI search](https://blogs.bing.com/webmaster/July-2025/Keeping-Content-Discoverable-with-Sitemaps-in-AI-Powered-Search))

### What actually appears to move the needle

1. **Crawlability and stable URLs — GROUNDED — PRIMARY.** If an engine cannot retrieve the page, no writing tactic matters. Google also warns that JavaScript rendering adds complexity. ([Google AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide))
2. **First-hand, differentiated evidence — GROUNDED — PRIMARY.** Google asks for original reporting, analysis, complete treatment, clear authorship, and evidence of first-hand experience. Generic summaries are a weak asset because they add no information gain. ([Google helpful content guidance](https://developers.google.com/search/docs/fundamentals/creating-helpful-content))
3. **Clear, internally consistent product facts — GROUNDED — PRIMARY.** Exact visible facts—price, capability, limitations, last-tested date—make product pages easier for Bing and users to interpret. Appropriate structured data should match the page; it is not a special AI-ranking layer. ([Bing AI Performance](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview), [Google AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide))
4. **Independent, relevant mentions — GROUNDED — OBSERVATIONAL.** Ahrefs found branded web mentions correlated roughly 0.66–0.71 with visibility across several AI surfaces, while page count was around 0.19. YouTube mentions were the strongest measured correlate, around 0.74. The study sampled established sites and cannot prove that buying or seeding mentions works. ([Ahrefs brand study](https://ahrefs.com/blog/ai-brand-visibility-correlations/))
5. **Relevant forum and review evidence for recommendation prompts — GROUNDED — OBSERVATIONAL.** Semrush found source mix changes by prompt intent; comparison and recommendation prompts relied more on review/community sources. Its separate 248,000-URL Reddit study found that modest-engagement, tightly relevant Q&A threads were frequently cited, so relevance mattered more than raw votes. The exact percentages and platform mix are volatile. ([Semrush visibility study](https://www.semrush.com/blog/ai-search-visibility-study-findings/), [Semrush Reddit study](https://www.semrush.com/blog/reddit-ai-search-visibility-study/))
6. **Demonstrated expertise and attributable authorship — GROUNDED — PRIMARY.** Google recommends making “who, how, and why” clear. E-E-A-T is a useful evaluation lens, but Google says it is not a single, specific ranking factor; trust is the most important component. ([Google helpful content guidance](https://developers.google.com/search/docs/fundamentals/creating-helpful-content))

### Claims to reject

- **“Add `llms.txt` and AI engines will cite us.” — GROUNDED — PRIMARY: false for Google.** Google says it ignores `llms.txt`; OpenAI's official discovery control is normal `robots.txt` access for `OAI-SearchBot`. Do not spend Omo's first week on an unproven file. ([Google](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [OpenAI](https://developers.openai.com/api/docs/bots))
- **“FAQ schema or a GEO schema makes us rank in AI answers.” — GROUNDED — PRIMARY: unsupported.** Google says no special schema is required. Use valid, ordinary schema only when it accurately represents visible page content. ([Google](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide))
- **“Every paragraph must be an isolated answer chunk.” — GROUNDED — PRIMARY: unsupported.** Clear writing helps people and synthesis, but Google explicitly rejects the need to create special AI-friendly chunks. ([Google](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide))
- **“More pages means more AI visibility.” — GROUNDED — PRIMARY/OBSERVATIONAL: usually wrong.** Google warns against mass-producing query variants, and Ahrefs found little relationship between page count and AI brand visibility. ([Google](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [Ahrefs](https://ahrefs.com/blog/ai-brand-visibility-correlations/))
- **“A citation means a recommendation or sale.” — GROUNDED — OBSERVATIONAL: false.** Semrush found many citations do not mention the cited brand, and its own case study warns that citation and recommendation share are different measurements. ([Semrush ghost citations](https://www.semrush.com/blog/the-ghost-citations-study/), [Semrush visibility case study](https://www.semrush.com/blog/how-we-are-using-semrush-to-drive-llm-visibility/))
- **“GEO position is stable and trackable like rank #1.” — GROUNDED — RESEARCH/ANECDOTAL: false.** Current research finds generative source selection variable across systems and repeated runs. Practitioner discussions likewise warn that prompt trackers are directional samples, not ground truth. ([2026 generative-search source study](https://arxiv.org/abs/2604.27790), [r/DigitalMarketing: “The GEO Bullshit — State of GEO in 2026”](https://www.reddit.com/r/DigitalMarketing/comments/1ro9ipx/the_geo_bullshit_state_of_geo_in_2026/))

## SEO writing consensus in 2026

### The standard: people-first, evidence-first, answer-first where useful

**GROUNDED — PRIMARY:** Google's current test is whether content exists to help an intended audience and demonstrates first-hand expertise, original information or analysis, sufficient depth, clear sourcing, and a satisfying answer. It asks publishers to disclose who created content, how it was made, and why it exists when those facts would reasonably matter. ([Google helpful content guidance](https://developers.google.com/search/docs/fundamentals/creating-helpful-content))

**REASONED:** “Answer-first” should mean respecting the reader, not writing robotic fragments. State the direct answer near the top, then provide proof, examples, trade-offs, and the next action. Do not force every page to the same length: a study of 174,000 pages found both short and long pages in AI Overviews, with no defensible universal word count. ([Ahrefs: short vs. long content in AI Overviews](https://ahrefs.com/blog/short-vs-long-content-in-ai-overviews/))

**GROUNDED — PRIMARY:** E-E-A-T is not a single ranking factor or a box that can be “added” to copy. It is a way of assessing signals around experience, expertise, authoritativeness, and especially trust. For Omo, the concrete implementation is named authors/reviewers, real workflow runs, sourced claims, honest limitations, accurate pricing, and a visible update date. ([Google helpful content guidance](https://developers.google.com/search/docs/fundamentals/creating-helpful-content))

### AI-generated content

**GROUNDED — PRIMARY:** Google does not ban AI-assisted content. It says generative AI can be useful for research and structure. The violation is producing many pages without added value for the purpose of manipulating rankings; Google's scaled-content-abuse policy applies regardless of whether the content was made by a human, automation, or both. ([Google on generative AI content](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content), [Google spam policies](https://developers.google.com/search/docs/essentials/spam-policies))

**REASONED:** Omo can use AI for outlines, transcription, editing, and extracting structured facts from a tested workflow. A human should still:

- run the workflow and retain the real input/output;
- verify every factual and comparative claim;
- add the observation an untested model could not know;
- name the reviewer and testing date;
- remove invented statistics, quotes, testimonials, and citations;
- disclose automation when a reasonable reader would expect to know.

If nobody performed the test described on the page, the page is not ready.

### Programmatic pages

**GROUNDED — PRIMARY:** Programmatic production is not automatically spam, but scaled pages created mainly to rank and offering little original value can violate Google's scaled-content policy. ([Google spam policies](https://developers.google.com/search/docs/essentials/spam-policies))

**GROUNDED — PRACTITIONER:** Ahrefs' programmatic SEO guidance treats unique data, useful functionality, and genuinely different intent as the defensible basis for templates. ([Ahrefs programmatic SEO guide](https://ahrefs.com/blog/programmatic-seo/))

**REASONED:** Omo should not generate hundreds of “phonics worksheet for [word family]” pages now. A page is allowed to exist only if its body contains a unique, verified artifact or function: a downloadable worksheet, evaluated output, live generator, original benchmark, or distinct curriculum mapping. Start with three manually reviewed pages. Scale only after one format earns impressions, qualified visits, and paid runs.

### Omo's minimum publishable page brief

Each workflow or proof page should contain:

1. **A descriptive title and H1:** the teacher job and resulting artifact, not “AI workflow #12.”
2. **A 40–80 word direct answer:** what it produces, for whom, and the exact current pay-per-use price.
3. **A real worked example:** the full safe input, a representative output, and a download/preview where possible.
4. **A test note:** who ran it, date, model/workflow version, elapsed time, number of revisions, and evaluation rubric.
5. **Limitations:** what it gets wrong, what still needs teacher review, and who should not use it.
6. **Evidence and sources:** curriculum or pedagogy sources for educational claims; no unsourced outcome claims.
7. **A clear next action:** run the workflow, inspect the open-source recipe, or download the sample.
8. **Machine-readable consistency:** unique canonical URL, static title/description, visible facts matching valid `Product`, `Offer`, or other appropriate schema. Never invent ratings or reviews.

**REASONED:** This brief gives classic search, AI retrieval, teachers, and creators the same source of truth. The clarity is useful; it is not a guaranteed citation formula.

## Omo repository diagnosis

The following is a local audit, not an external ranking claim.

**REASONED FROM REPOSITORY:** Omo already has the right raw material: three education workflow repositories under `oss/`, four phonics cover assets, pay-per-use positioning, an owned 4,500-person teacher list, and a creator/demo strategy. The missing layer is a crawlable evidence package connecting each workflow to a stable page, real sample, and independently useful explanation. See [`oss/`](../oss/), [`gtm-strategy.md`](gtm-strategy.md), and [`edtech-kill-list.md`](edtech-kill-list.md).

**REASONED FROM REPOSITORY:** The highest-risk technical gap is the workflow detail architecture. [`site/workflow.html`](../site/workflow.html) uses the same query-string template for every listing and replaces the title and description in client-side JavaScript. There is no `site/robots.txt`, XML sitemap, or static per-workflow page in the current tree. Google can render JavaScript, but it documents additional complexity, and other crawlers need not behave identically. Unique server-rendered or static workflow URLs are therefore a higher-ROI first move than publishing a volume blog. ([Google JavaScript/search guidance within the AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide))

**REASONED FROM REPOSITORY:** The homepage already provides a useful base—static metadata, `Organization`/`WebSite` structured data, and an item list—but the new phonics workflows are not yet represented in the storefront catalog found during this audit. The open-source folders for worksheet generation, story editing, and reading-error coaching exist; a complete Phonics Book Maker repository was not found. Do not create public claims or repository links for an asset that is not actually ready.

## The highest-ROI tactics for a $200 budget

### 1. Fix retrieval before creating more content — $0

**Why first — GROUNDED/REASONED:** Crawlability is a prerequisite, and the repository has a concrete gap. Create one static or server-rendered URL per education workflow; add crawlable links, a sitemap, intentional bot rules, canonical metadata, and visible price/input/output facts. Validate the pages in Google Search Console and Bing Webmaster Tools. Permit `OAI-SearchBot` if ChatGPT search inclusion is desired; decide `GPTBot` access separately because it governs training, not search. ([Google](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [OpenAI](https://developers.openai.com/api/docs/bots))

**Expected payoff:** every later listing, article, repository, video, and community answer can point to one authoritative URL.

### 2. Build three proof assets, not thirty articles — $0–$120

**Why second — GROUNDED/REASONED:** Original evidence and first-hand experience satisfy both people-first guidance and the need for citable facts. Spend, only with Harry's approval, up to $120 total on three teacher review honoraria; generation and editing stay internal. ([Google helpful content guidance](https://developers.google.com/search/docs/fundamentals/creating-helpful-content))

Proposed first three assets:

1. **CVC worksheet sample and evaluation:** printable output, answer key, decodability check, errors found, exact run cost, and teacher review.
2. **Phonics story editing before/after:** original passage, revised passage, target grapheme constraints, edits accepted/rejected, and why.
3. **Pay-per-use versus subscription calculator for occasional teacher use:** transparent break-even math using dated public prices and declared assumptions. Compare outcomes and cost structure; do not copy competitors' wording or design.

These are not a keyword map. They are proof objects from which later queries and formats can be learned.

### 3. Make the open-source recipes independently useful — $0

**Why third — REASONED:** The three existing `SKILL.md` repositories can become credible primary sources only if a stranger can understand and test them. Each repository needs a plain-language README, license, versioned recipe, safe sample input/output, evaluation checklist, known limitations, honest self-hosting requirements, and a link to the matching Omo page. The Omo page should link back to source. Publish externally only after explicit approval.

**Expected payoff:** a verifiable artifact that can earn GitHub links and creator references without requiring a sales pitch. Do not describe “open source” as free execution; distinguish the recipe from model/runtime costs.

### 4. Turn each proof asset into one creator demonstration — $0–$80

**Why fourth — GROUNDED — OBSERVATIONAL/REASONED:** YouTube mentions were the strongest correlate in the Ahrefs brand study, but the finding is not causal. Omo's existing creator-first strategy makes a demonstration a low-cost test anyway. Use one real workflow run per video, link to the matching proof page, and embed a transcript or concise summary on that page. Recut the same demonstration for reels rather than inventing separate claims. ([Ahrefs brand study](https://ahrefs.com/blog/ai-brand-visibility-correlations/))

The optional $80 is a reserve for captions/sample polish, not distribution. Any payment and any public post require explicit approval.

### 5. Earn community corroboration—never seed fake consensus — $0

**Why fifth — GROUNDED — OBSERVATIONAL/REASONED:** Relevant Q&A discussions can appear in recommendation answers, but fake promotion risks trust, moderator action, and a weak brand footprint. After the proof pages exist, answer real teacher or AI-workflow questions where Omo has first-hand evidence; disclose affiliation, give the useful answer in the post, and link only when the artifact genuinely adds value. ([Semrush Reddit study](https://www.semrush.com/blog/reddit-ai-search-visibility-study/), [Google warning against inauthentic mentions](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide))

External posts, comments, DMs, and requests for reviews require Harry's explicit approval.

## What to do first, second, and third

### First: establish the technical and measurement floor

Complete these in order before publishing a content series:

1. Ship static/server-rendered URLs for the three ready phonics workflows, with the minimum page brief above.
2. Add `robots.txt` and an XML sitemap. Allow the search crawlers Omo deliberately wants, including `OAI-SearchBot` and `PerplexityBot`; keep the training decision for `GPTBot` separate.
3. Put all important product facts in initial HTML and normal text: exact current price, audience, inputs, output, limitations, sample, and last-tested date.
4. Add only accurate, visible-content structured data and validate it. No fake ratings, fake reviews, AI-only schema, or `llms.txt` project.
5. Register/verify Google Search Console and Bing Webmaster Tools when external-state approval is available. Submit the sitemap. Use Bing's AI Performance and Google's current generative-AI reporting where available. ([Google](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), [Bing](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview))
6. Record a baseline of 12 real buyer questions across ChatGPT, Perplexity, Google AI Mode/Overviews, and Copilot. Run each three times, logged out where practical. Track whether Omo is mentioned, cited, described accurately, and clicked—not an invented “rank.”

**REASONED stop condition:** If checkout and the first paid second-book event are not working, finish that gate before driving traffic. Organic discovery cannot rescue a broken value loop.

### Second: create and review the three proof assets

For each asset:

1. Run the workflow five times with declared test inputs.
2. Record price, latency, revisions, failure cases, and rubric results.
3. Have a real teacher review the representative output; obtain explicit permission before attributing a quote.
4. Publish the sample and enough method to reproduce the evaluation.
5. Connect the proof page, workflow listing, and open-source repository bidirectionally.

**REASONED acceptance bar:** each page must contain at least one fact or artifact that could not have been produced by summarizing the current top search results.

### Third: distribute the evidence and learn from response

1. Produce one full creator demo and short cuts for each winning proof asset.
2. Invite the existing teacher cohort to test the workflow only after the product gate is ready; do not ask for a positive review. Ask for observed failures and permission to quote accurate feedback.
3. Answer a small number of existing, relevant community questions with disclosed affiliation. Do not manufacture threads about Omo.
4. Refresh the official page when price, behavior, or evaluation changes; submit changed URLs through the normal search tools.
5. After 30 days, expand only the proof format that generated qualified impressions, referrals, first paid runs, or repeat runs.

## 30/60/90-day execution list

| Rank | Window | Action | Asset mapping | Done when |
|---:|---|---|---|---|
| 1 | Days 1–7 | Create three crawlable phonics listing URLs and discovery files. | Storefront + phonics cover assets | Unique initial HTML, canonical, internal link, sitemap entry, valid visible-content schema, and successful crawler inspection. |
| 2 | Days 1–7 | Establish manual AI/search baseline and conversion events. | Storefront analytics | 12 buyer questions × 4 engines × 3 repeats logged; referral, first paid run, and repeat paid run separable. |
| 3 | Days 8–21 | Produce the three proof assets and teacher-review them. | Blog/proof pages + listings | Real samples, rubric, test method, limitations, dated price, reviewer permission, and clear CTA. |
| 4 | Days 15–30 | Complete and connect the three existing education repositories. | `oss/phonics-worksheet-generator`, `oss/phonics-story-edit-studio`, `oss/phonics-reading-error-coach` | Each is independently understandable and linked to exactly one matching Omo page. |
| 5 | Days 22–45 | Publish one creator demonstration per validated asset. | Creator content + page transcript | Each video shows a real run, links to its evidence page, and makes no unverified outcome claim. |
| 6 | Days 30–60 | Earn teacher and community corroboration. | 4,500-person teacher list + Reddit/teacher communities | At least five substantive failure reports or permissioned observations; no incentivized positive sentiment. |
| 7 | Days 45–90 | Scale one proven content format cautiously. | Blog/tool pages | The original three pages have measurable qualified discovery or conversions; every new page has unique data/artifact. |
| 8 | Day 90 | Decide continue, revise, or stop. | Whole funnel | Decision uses paid runs and repeat runs first, qualified referrals second, mentions/citations third. |

## Measurement that will not lie to us

### Primary business metrics

1. Paid first workflow runs from organic/AI referrals.
2. Paid repeat runs or second-book events.
3. Revenue per qualified organic visit.

### Discovery diagnostics

- indexed/crawlable workflow and proof URLs;
- non-brand impressions and clicks in Search Console;
- cited pages and grounding-query samples in Bing AI Performance;
- ChatGPT, Perplexity, Copilot, and Google referrals where the referrer is available;
- manual prompt sample: mention rate, citation rate, factual accuracy, and source URL;
- permissioned third-party mentions and demos.

**GROUNDED — OBSERVATIONAL:** Track brand mentions, citations, and cited pages separately; a source can be cited without the brand being recommended. ([Semrush ghost citations](https://www.semrush.com/blog/the-ghost-citations-study/))

**GROUNDED — ANECDOTAL:** Referrer data usually does not reveal the user's exact private chatbot prompt. A recent r/SaaS discussion correctly distinguishes known referral sessions from guessed triggering questions. Use sampled prompts for diagnosis, not individual-user attribution. ([r/SaaS: “Traffic from ChatGPT or other chatbot”](https://www.reddit.com/r/SaaS/comments/1vlce61/traffic_from_chatgpt_or_other_chatbot/))

Suggested weekly log:

| Week | Indexed proof pages | Qualified organic visits | AI referrals | Paid runs | Repeat runs | Prompt mention/citation/accuracy | New independent mentions | Decision |
|---|---:|---:|---:|---:|---:|---|---:|---|
| YYYY-MM-DD |  |  |  |  |  | `mentions / citations / accurate of 144` |  | keep / revise / stop |

**REASONED:** Do not buy a GEO tracking subscription within the first $200. A 144-response monthly sample (12 questions × 4 engines × 3 repeats) is enough to spot gross discovery and accuracy problems while revenue is small. It is not a population estimate or stable “share of voice.”

## What will not work fast

- **Trying to outrank Diffit or MagicSchool for broad head terms. — REASONED.** Their domain strength, brand demand, content footprint, and free tiers make “AI tools for teachers” an expensive first contest. Omo should win specific jobs and pay-per-use economics first. The competitor work in [`edtech-kill-list.md`](edtech-kill-list.md) is a product/outcome reference, not permission to copy brand language or design.
- **Publishing 100 generic AI articles. — GROUNDED — PRIMARY/REASONED.** This creates review burden and scaled-content risk without differentiated proof. ([Google AI content guidance](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content))
- **Buying links, reviews, mentions, Reddit accounts, or synthetic “community.” — GROUNDED — PRIMARY/REASONED.** Inauthentic mentions are not a shortcut, and they undermine the trust signal Omo needs. ([Google AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide))
- **Treating structured data as a GEO ranking hack. — GROUNDED — PRIMARY.** Use it for correct entity/product understanding and eligible search features, not as a citation guarantee. ([Google](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide))
- **Publishing comparison pages before Omo has tested evidence. — REASONED.** Unverified tables become stale and indistinguishable from affiliate copy. A dated, transparent cost calculator is defensible; a generic “10 best AI teacher tools” list is not.
- **Expecting citations to create traffic immediately. — GROUNDED — OBSERVATIONAL/REASONED.** AI answers can satisfy the user without a click, and citations need not name the brand. Conversion from a cited page must be measured directly. ([Semrush ghost citations](https://www.semrush.com/blog/the-ghost-citations-study/))
- **Assuming one successful prompt is a rank. — GROUNDED — RESEARCH.** Engine outputs and source sets vary across repeated runs. ([2026 source-selection study](https://arxiv.org/abs/2604.27790))

## Reddit field check: useful signals and limits

The required communities were searched directly: **r/SEO, r/juststart, r/bigseo, r/marketing, r/DigitalMarketing, r/ArtificialInteligence, r/GPT3, and r/SaaS**. Useful evidence concentrated in the SEO, bigSEO, marketing, DigitalMarketing, juststart, and SaaS threads. The searched r/ArtificialInteligence results were sparse; r/GPT3 produced mainly a low-engagement promotional tool post. Neither is used as decision-grade evidence.

What the stronger threads add:

- **GROUNDED — ANECDOTAL:** r/SEO broadly converged on “normal SEO fundamentals still apply” after Google's guidance, while commenters debated traffic loss and reporting. This agrees with the primary Google source. ([r/SEO: “Google confirms normal SEO works for AI Overviews”](https://www.reddit.com/r/SEO/comments/1m9k0kg/google_confirms_normal_seo_works_for_ai_overviews/))
- **GROUNDED — ANECDOTAL:** Practitioners testing AI visibility openly report small samples, partial overlap, tool promotion, and disagreement about causality. This is a reason to keep measurement modest, not evidence for a ranking tactic. ([r/SEO: “Early Experiments with Tracking AI Overview/LLM Visibility”](https://www.reddit.com/r/SEO/comments/1nfulcr/early_experiments_with_tracking_ai_overviewllm/), [r/bigseo: “GEO/AIO is essentially just a scam”](https://www.reddit.com/r/bigseo/comments/1nkh6ux/geoaio_is_essentially_just_a_scam/))
- **GROUNDED — ANECDOTAL:** When asked what a GEO deliverable should be, r/bigseo responses mixed classic technical/content work, brand mentions, Reddit/YouTube, query fan-out, and manual monitoring; several emphasized that audience relevance comes before the new label. This supports the staged playbook, not any single tactic. ([r/bigseo: “My client just asked me to ‘do GEO’”](https://www.reddit.com/r/bigseo/comments/1rkqq7o/my_client_just_asked_me_to_do_geo_what_do_i_even/))
- **GROUNDED — ANECDOTAL:** r/marketing practitioners proposed separating AI visibility from ordinary organic reports and manually checking a short list of buyer questions; others argued that prompt tracking can become theater. ([r/marketing: “How are you formatting client reports…?”](https://www.reddit.com/r/marketing/comments/1vgefrc/how_are_you_formatting_client_reports_when_they/))
- **GROUNDED — ANECDOTAL:** A r/juststart case credited answer-first sections, numbers, tables, FAQs, and `llms.txt`, but disclosed no controlled dataset and promoted its own GitHub asset; commenters called out the promotion. Google's primary documentation contradicts the `llms.txt` and special-chunking claims. It is included as a cautionary example, not a recommendation. ([r/juststart: “ChatGPT sends my niche site more buyers than Google”](https://www.reddit.com/r/juststart/comments/1ve3olr/chatgpt_sends_my_niche_site_more_buyers_than/), [Google](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide))
- **GROUNDED — ANECDOTAL:** One r/SaaS operator reported 514 ChatGPT sessions and 42 registrations across many micro-tools without deliberate GEO work. This is consistent with useful action pages being discoverable, but it does not establish why ChatGPT selected them. ([r/SaaS: “Nobody talks about ChatGPT as a traffic source…”](https://www.reddit.com/r/SaaS/comments/1rrncoy/nobody_talks_about_chatgpt_as_a_traffic_source_i/))

The Reddit conclusion is deliberately modest: **practitioners see real AI referrals, but the community has not discovered a reliable shortcut.** The best threads are more skeptical of GEO certainty than vendor guides.

## Source hierarchy and caveats

1. **Engine and policy documentation controls technical decisions.** Google, OpenAI, Bing, and Perplexity are the primary sources for their own crawling and reporting behavior.
2. **Large studies guide experiments, not promises.** Ahrefs and Semrush have useful datasets but also sell SEO/GEO products. Correlations, prompt samples, and historical source shares can change.
3. **Reddit supplies field observations and failure modes.** It is not a substitute for controlled evidence; self-promotion and survivorship bias are common.
4. **Academic GEO research is useful but narrower than headlines imply.** The foundational GEO paper reported up to 40% improvement from additions such as citations, quotations, and statistics, but its main tests supplied a fixed source set to the model; its Perplexity test uploaded source text and instructed the model to answer from those files. That evaluates how retrieved material is absorbed, not whether an unknown public webpage will be retrieved in the first place. ([GEO paper](https://arxiv.org/abs/2311.09735))
5. **The field is unsettled.** A 2026 survey describes heterogeneous definitions, metrics, and experimental designs across dozens of studies. Treat confident universal recipes as suspect. ([2026 systematic GEO survey](https://arxiv.org/abs/2607.14035))

Practitioner guides consulted for triangulation—not treated as engine policy—include [Backlinko's 2026 GEO guide](https://backlinko.com/generative-engine-optimization-geo), [Neil Patel's GEO guide](https://neilpatel.com/blog/generative-engine-optimization-geo/), and [Search Engine Journal's report on Google's 2026 guidance](https://www.searchenginejournal.com/googles-new-ai-search-guide-calls-aeo-and-geo-still-seo/575026/). Their durable recommendations—technical SEO, first-hand evidence, clear authorship, original data, and useful formatting—are included only where they agree with stronger primary evidence.

## Final operating rule

**REASONED:** Omo should optimize for **proof density per page**, not keywords per page or pages per month. A strong asset gives a teacher an answer, lets them inspect a real result, states the current cents-to-dollars price, exposes limitations, names the reviewer, links to a reproducible recipe, and makes the next paid action obvious. If that system works for three phonics workflows, scale it. If it does not produce qualified visits and paid repeat use, stop adding content and fix the product or distribution loop.
