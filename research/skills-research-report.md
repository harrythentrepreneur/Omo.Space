# The most verifiable and helpful user-made AI skills/workflows

**Research date:** 2026-08-12

**Decision goal:** What should Omo host, verify, and market as an automated `SKILL.md` experience?

**Dataset:** 10 high-signal hubs, 23 shortlisted skills, 13 verbatim Reddit quotes from 5 threads.

## Executive conclusion

The strongest demand-and-proof cluster is not “general agents.” It is **small, outcome-specific marketing procedures with reusable company context**: Meta/Facebook ads, Google ad variants, landing-page copy, cold email, SEO audits, and churn save offers. The clearest evidence is Corey Haines’s `marketingskills`: **44,020 GitHub stars**, 49 inspectable `SKILL.md` files, and a **165-upvote r/SideProject user report** that says four skills produced a positioning document, landing page, outreach sequence, and product poster in 30 minutes. The poster’s author is not identified as the repository maker, but their independence is not proven and commenters suspected promotion; treat it as public outcome evidence, not a controlled test.

The product opportunity is not another file directory. GitHub already supplies thousands of files. Omo should sell **verified execution**: a safe preview, generated input form, reusable brand/account context, one-click hosted run, visible sample output, cost and permissions, and test receipts. Repository stars help discover candidates, but they do not validate an individual skill. Omo can own the missing per-skill evidence layer.

## Method

### Collection routes and dates

- **GitHub, 2026-08-12:** ran the requested unauthenticated repository searches for `claude skills`, `agent skills`, `SKILL.md`, `awesome skills`, `claude code skills`, and `prompt workflows`, sorted by stars, 10 results each. After de-duplication there were **48 repositories**. I then fetched live repository metadata and recursive trees for 14 shortlisted repositories and inspected 24 actual skill files. Checkpoints: `/tmp/skills_research/github_hubs_checkpoint.json`, `/tmp/skills_research/github_shortlist_checkpoint.json`, repository trees, and individual skill files under `/tmp/skills_research/`.
- **Reddit direct routes, 2026-08-12:** used `curl -L -A 'Mozilla/5.0'` against old.reddit RSS and thread HTML. The first RSS request returned HTTP 403. A second subreddit RSS request after 95 seconds and a top-thread HTML request after another 112 seconds also returned HTTP 403, not the documented 429 quota response. Headers were preserved under `/tmp/skills_research/reddit_*_headers.txt`; the blocked routes were not retried further.
- **Reddit fallback, 2026-08-12:** used four spaced web searches (under the 10-query ceiling) only for discovery, then opened full indexed Reddit thread pages to capture bodies, authors, and comments. Upvotes are recorded only where the search result exposed a number. The structured checkpoint is `/tmp/skills_rss.json`.
- **Known route constraint:** old.reddit’s working RSS route is normally limited to roughly one request per 75 seconds per IP. This run respected that cadence, but Reddit’s edge blocked this IP with 403 before quota headers were usable.

### What “verified” means here

| Tier | Required evidence | Interpretation |
|---|---|---|
| **A — outcome evidence** | Inspectable artifact plus a public non-maker-identified user describing a concrete run/output; public adoption signal also shown | Best candidates for Omo to reproduce; poster identity/independence can still be unknown |
| **B — adoption + artifact** | Actual `SKILL.md`/scripts inspected, active repository, substantial stars/forks; no public outcome report fetched | Real and popular, but Omo should run its own eval |
| **C — maker claim** | Artifact exists, but performance claim comes from the maker or README only | Never repeat the claim as proven |

Stars are a repository-level discovery signal, not downloads, successful runs, or per-skill approval. Reddit scores are snapshots and can change. “File inspected” proves the skill exists and is more than a landing page; it does not prove output quality. No download totals or paid transaction totals were available, so none are invented.

## 1. Verifiable hubs

GitHub counts below are live API snapshots from 2026-08-12. “Files” is the number of paths ending in `SKILL.md` (case-insensitive) in the fetched default-branch tree.

| Hub / maker | Stars / forks | Files | Last push | Why it matters / caveat |
|---|---:|---:|---|---|
| [obra/superpowers](https://github.com/obra/superpowers) | 271,143 / 24,231 | 14 | 2026-08-12 | Coherent software-development methodology: planning, TDD, debugging, review, verification. MIT. Strongest adoption signal in the shortlist. |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 214,791 / 18,531 | 35 | 2026-08-07 | Concrete engineering and productivity procedures from Matt Pocock’s own agent setup. MIT. Also recommended by a user in the fetched “Do Claude skills actually work?” thread. |
| [anthropics/skills](https://github.com/anthropics/skills) | 168,470 / 20,068 | 18 | 2026-08-07 | Official, not user-made; included as the format/quality baseline. It proves document, spreadsheet, presentation, design, and testing skills are first-class categories. Repository API did not expose an SPDX license. |
| [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) | 132,297 / 19,463 | 9 | 2026-08-10 | Large open-source agent/RAG application library with a smaller set of actual agent skills. Apache-2.0. More application hub than pure skill catalog. |
| [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) | 72,350 / 8,237 | 864 | 2026-08-10 | Huge discoverable catalog, including competitive-ad extraction and hundreds of connector automations. Quantity is not per-skill validation; many entries are generated integration wrappers. |
| [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 52,198 / 4,559 | 0 embedded | 2026-08-12 | Widely adopted curated index of skills, agents, plugins, hooks, and tooling. It links outward rather than embedding `SKILL.md` files, so availability can drift. |
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | 47,737 / 5,948 | 130 | 2026-08-03 | Deep video-production stack: local FFmpeg plus paid generation, dubbing, speech, animation, and rendering integrations. AGPL-3.0. Valuable but many hosted runs are compute/API intensive. |
| [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 44,020 / 6,922 | 49 | 2026-07-29 | Best cross-source proof: inspectable marketing playbooks plus a [165-upvote user-reported field run](https://www.reddit.com/r/SideProject/comments/1spqw1p/found_a_github_repo_20k_stars_that_turns_ai/). Commenters suspected promotion, so Omo should reproduce it. MIT. |
| [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | 42,172 / 3,359 | 4 | 2026-08-11 | Four unusually deep research/write/review/orchestration skills with explicit stages, modes, integrity checks, and versions. No SPDX license was exposed; expensive to run and needs factuality evals. |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) | 30,109 / 3,236 | 0 embedded | 2026-08-12 | Cross-agent index claiming 1,000+ linked skills. MIT. Useful discovery surface; Omo still needs to resolve source commits and validate each linked artifact. |

### Hub takeaway

The market already has breadth. The largest inspected catalog contains 864 files, while linked indexes advertise 1,000+. The defensible gap is **trust per skill**: source provenance, executable dependencies, safety, maintained version, input/output examples, and repeatable outcome tests.

## 2. Top skills found

The 23 entries below all point to an inspected artifact. Evidence applies to the named skill only where explicitly stated; a parent repository’s star count is not presented as a per-skill rating.

### Marketing, ads, SEO, and ecommerce

| Skill | What it solves | Maker | Evidence |
|---|---|---|---|
| [Paid Ads](https://github.com/coreyhaines31/marketingskills/blob/main/skills/ads/SKILL.md) | Campaign goals, budgets, audience/keyword targeting, bidding, CPA/ROAS, and optimization for Google, Meta/Facebook/Instagram, LinkedIn, and X | `coreyhaines31` | **B.** Actual v2.2 file; 44,020-star parent. A self-described company AI lead reports building a [home-grown Meta Ads context skill](https://www.reddit.com/r/ClaudeAI/comments/1u8t66a/what_claude_skills_have_you_built_that_are/), validating the niche rather than this exact file. |
| [Ad Creative](https://github.com/coreyhaines31/marketingskills/blob/main/skills/ad-creative/SKILL.md) | Generates and iterates headlines, primary text, hooks, static concepts, and video-ad ideas for Meta, Google RSAs, LinkedIn, TikTok, and X | `coreyhaines31` | **A.** Actual v2.8 file; 44,020-star parent. The [165-upvote field test](https://www.reddit.com/r/SideProject/comments/1spqw1p/found_a_github_repo_20k_stars_that_turns_ai/) used it among four skills and produced a product poster in a 30-minute run. |
| [Copywriting](https://github.com/coreyhaines31/marketingskills/blob/main/skills/copywriting/SKILL.md) | Conversion copy for homepages, landing pages, pricing pages, feature pages, product pages, headlines, and CTAs | `coreyhaines31` | **A.** Actual v2.0.1 file. The same field test says it generated a complete PAS landing page with specific proof/price framing; parent has 44,020 stars. |
| [Cold Email](https://github.com/coreyhaines31/marketingskills/blob/main/skills/cold-email/SKILL.md) | B2B outreach subject lines, personalized openers, body, CTA, and multi-touch follow-up sequences | `coreyhaines31` | **A.** Actual v2.0 file. The field test reports a three-email influencer outreach sequence tied to observed content and product differentiation. |
| [Programmatic SEO](https://github.com/coreyhaines31/marketingskills/blob/main/skills/programmatic-seo/SKILL.md) | Plans template/data-driven landing pages such as comparison, integration, directory, and keyword-plus-location pages while guarding against thin content | `coreyhaines31` | **B.** Actual v2.0 file; 44,020-star parent. A [24-upvote marketer demand thread](https://www.reddit.com/r/ClaudeAI/comments/1qi080n/what_are_the_musthave_claude_skills_for_marketers/) explicitly asks for SEO orchestration. No outcome for this exact file was fetched. |
| [SEO Audit](https://github.com/coreyhaines31/marketingskills/blob/main/skills/seo-audit/SKILL.md) | Diagnoses technical/on-page SEO, crawl/indexing, ranking drops, metadata, page speed, and Core Web Vitals | `coreyhaines31` | **B.** Actual v2.0 file; 44,020-star parent and repeated SEO demand on Reddit. Requires live site/search-console data for strong hosted output. |
| [Churn Prevention](https://github.com/coreyhaines31/marketingskills/blob/main/skills/churn-prevention/SKILL.md) | Builds cancel flows, exit surveys, reason-specific save offers, plan pauses/downgrades, win-back, and failed-payment recovery | `coreyhaines31` | **B.** Actual v2.0 file; 44,020-star parent. The 165-upvote tester highlighted its dynamic save-offer design but explicitly said they had **not** tested it. Do not upgrade this to Tier A yet. |
| [Offer Design](https://github.com/coreyhaines31/marketingskills/blob/main/skills/offers/SKILL.md) | Improves value framing, bonuses, guarantees, risk reversal, scarcity, naming, upsells, and payment structure | `coreyhaines31` | **B.** Actual v1.0 file; 44,020-star parent. Clear real-world job and cheap text-only run, but no public result was fetched. |

### Content and video

| Skill | What it solves | Maker | Evidence |
|---|---|---|---|
| [Create Video](https://github.com/calesthio/OpenMontage/blob/main/.agents/skills/create-video/SKILL.md) | One-shot prompt-to-video generation: script, avatar, visuals, voiceover, pacing, and captions | `calesthio` / OpenMontage | **B.** Actual file in a 47,737-star repository; explicit HeyGen API/key requirements. Verifiable integration, but paid API cost and output quality need Omo tests. |
| [Video Edit](https://github.com/calesthio/OpenMontage/blob/main/.agents/skills/video-edit/SKILL.md) | Deterministic local FFmpeg trim, concatenate, resize, speed, overlay, audio extraction/replacement, compression, and conversion | `calesthio` / OpenMontage | **B.** Actual file in a 47,737-star repository. Especially hostable because commands are concrete and no paid model is required; compute/storage, not token cost, is the constraint. |
| [Video Translate](https://github.com/calesthio/OpenMontage/blob/main/.agents/skills/video-translate/SKILL.md) | Dubs existing video into other languages with lip-sync or audio-only translation | `calesthio` / OpenMontage | **B.** Actual file with HeyGen endpoint and key requirements; parent has 47,737 stars. Useful, but API-dependent and not cheap. |
| [md2wechat](https://github.com/geekjourneyx/md2wechat-skill/blob/main/skills/md2wechat/SKILL.md) | Converts Markdown to WeChat Official Account HTML, previews it, generates cover/infographic assets, suggests titles, and uploads drafts | `geekjourneyx` | **B.** Actual artifact plus CLI in a 3,492-star, 398-fork repository pushed 2026-08-07. Narrow, complete publishing outcome; good example of a high-intent regional niche. |

### Coding and codebase work

| Skill | What it solves | Maker | Evidence |
|---|---|---|---|
| [Systematic Debugging](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md) | Enforces root-cause investigation before fixes for bugs, test failures, and unexpected behavior | `obra` | **B.** Actual procedural file in the 271,143-star Superpowers repo. Strong adoption and clear completion gates; no controlled outcome was fetched. |
| [Test-Driven Development](https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md) | Requires a failing test before minimal implementation, then refactoring | `obra` | **B.** Actual file; 271,143-star parent. Cheap instruction layer, but Omo should evaluate compliance on seeded feature/bug tasks. |
| [Verification Before Completion](https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md) | Prevents unsupported “done/fixed/passing” claims by requiring fresh verification output before completion or commit | `obra` | **B.** Actual file; 271,143-star parent. Highly testable with planted failures, making it an excellent Omo benchmark skill. |
| [Two-axis Code Review](https://github.com/mattpocock/skills/blob/main/skills/engineering/code-review/SKILL.md) | Reviews a branch against both repository standards and the originating spec, then reports findings side by side | `mattpocock` | **B.** Actual file; parent has 214,791 stars. A separate commenter in a fetched [r/ClaudeAI discussion](https://www.reddit.com/r/ClaudeAI/comments/1ugrff7/do_claude_skills_actually_work/) recommends Pocock’s repository, but did not publish this skill’s test result. |
| [Graphify](https://github.com/Graphify-Labs/graphify/blob/v8/graphify/skill.md) | Converts code, docs, schemas, PDFs, images, and video into a persistent knowledge graph with HTML, JSON, query/path/explain, and audit trail | `Graphify-Labs` | **B.** Actual skill and implementation in a 105,576-star, 10,290-fork Apache-2.0 repository pushed on the research date. Heavier than a prompt skill, but output is inspectable. |

### Research, design, and productivity

| Skill | What it solves | Maker | Evidence |
|---|---|---|---|
| [Deep Research](https://github.com/Imbad0202/academic-research-skills/blob/main/deep-research/SKILL.md) | Literature search, source verification, synthesis, fact-checking, systematic review, bias assessment, and optional meta-analysis | `Imbad0202` | **B.** Actual versioned 13-agent procedure; parent has 42,172 stars. High-value but expensive and high-risk; must be evaluated for citation validity. |
| [Academic Paper](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-paper/SKILL.md) | Plans, drafts, revises, formats, citation-checks, and audits rebuttals/disclosures across paper types and formats | `Imbad0202` | **B.** Actual versioned 12-agent procedure; 42,172-star parent. Useful workflow depth; no expert-verified paper-quality outcome was fetched. |
| [Academic Paper Reviewer](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-paper-reviewer/SKILL.md) | Simulates journal-fit, methodology, domain, cross-disciplinary, and devil’s-advocate reviews, then synthesizes a revision roadmap | `Imbad0202` | **B.** Actual versioned five-reviewer design; 42,172-star parent. Needs blinded comparison against expert reviewers before a “proven” label. |
| [Academic Pipeline](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/SKILL.md) | Orchestrates research → write → integrity check → two review/revision cycles → finalization with resumable checkpoints | `Imbad0202` | **B.** Actual orchestrator with explicit dependencies and stages; 42,172-star parent. Strong packaging pattern, but costly to host. |
| [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/ui-ux-pro-max/SKILL.md) | Searchable design intelligence: styles, palettes, typography, UX/accessibility rules, icons, motion, charts, and 22 implementation stacks | `nextlevelbuilder` | **B.** Actual skill plus local reference database; repository has 116,049 stars and 12,450 forks, MIT, pushed 2026-08-12. Omo should test visual output, not just rule recall. |
| [Caveman Compress](https://github.com/JuliusBrussee/caveman/blob/main/skills/caveman-compress/SKILL.md) | Compresses memory/instruction Markdown while preserving code, URLs, and structure; stores a human-readable backup outside auto-loaded directories | `JuliusBrussee` | **B for existence/adoption, C for performance.** Actual scripts/procedure; repository has 97,720 stars. The repository’s “65% token reduction” is a maker claim not reproduced here. It overwrites the source after backup, so hosted use needs a diff/approval gate. |

### Important exclusions

- The 167-upvote “Universal Full-Stack Web App Builder” Reddit post is **not** in the top list despite its popularity. Its prompt requires “realistic” commit hashes, simulated browser results, “100% pass,” and Lighthouse/security scores; commenters flagged scope bloat and unrealistic expectations. A claimed demo was linked, but no maintained source repository or reproducible test suite was fetched.
- Generated connector catalogs are real artifacts but were not promoted individually without a concrete user outcome.
- The academic suite’s elaborate agent counts and quality gates are maker-authored architecture, not proof that papers or citations are correct.

## 3. Reddit signal

These are verbatim excerpts from full indexed thread pages. The number beside a thread is the post score only where surfaced by search; it is not the score of each comment.

### Concrete outcomes and useful work

> “30 minutes, 4 skills, and I had a positioning doc, landing page copy, email sequence, and a product poster.”

— `u/Inevitable-View-2925`, [r/SideProject field test, 165 upvotes](https://www.reddit.com/r/SideProject/comments/1spqw1p/found_a_github_repo_20k_stars_that_turns_ai/)

> “This actually gives me a useful start from which I can build on”

— `u/martin-1858`, [same field-test thread](https://www.reddit.com/r/SideProject/comments/1spqw1p/found_a_github_repo_20k_stars_that_turns_ai/)

> “Built a full-stack Paris Café WiFi Scout with this skill.md: maps quiet spots, real-time WiFi speeds, outlet info, user reviews, offline save.”

— `u/stackattackpro`, [r/ClaudeAI auto-builder thread, 167 upvotes](https://www.reddit.com/r/ClaudeAI/comments/1qb1024/ultimate_claude_skillmd_autobuilds_any_fullstack/)

> “A Meta Ads skill that loads our ad account structure, naming conventions, campaign framework, and best practices so Claude doesn't need that context re-explained every time.”

— `u/CommissionDry8792`, [r/ClaudeAI marketing-skills thread](https://www.reddit.com/r/ClaudeAI/comments/1u8t66a/what_claude_skills_have_you_built_that_are/)

### What makes a skill work

> “The skill only earns its keep if it forces a real second pass over the finished draft, not just a list of tells described up front.”

— `u/Ornery_Car6086`, [r/ClaudeAI marketing-skills thread](https://www.reddit.com/r/ClaudeAI/comments/1u8t66a/what_claude_skills_have_you_built_that_are/)

> “Skills work better as small, triggered procedures than as a second system prompt.”

— `u/anasgoblins`, [“Do Claude skills actually work?”](https://www.reddit.com/r/ClaudeAI/comments/1ugrff7/do_claude_skills_actually_work/)

> “I have to convert pngs to .c files often, so I had Claude code make a skill to do the conversion.”

— `u/_Wily-Wizard_`, [same skills-effectiveness thread](https://www.reddit.com/r/ClaudeAI/comments/1ugrff7/do_claude_skills_actually_work/)

> “the shared context file is the actual insight here and it's underrated.”

— `u/Deep_Ad1959`, [r/SideProject field test](https://www.reddit.com/r/SideProject/comments/1spqw1p/found_a_github_repo_20k_stars_that_turns_ai/)

### Skepticism, vaporware, and the marketplace gap

> “All these “agent specs” repos are hype. Not bad, just mainly hype and we should pick one that suits our needs and not based on stars.”

— `u/Reebzy`, [r/SideProject field test](https://www.reddit.com/r/SideProject/comments/1spqw1p/found_a_github_repo_20k_stars_that_turns_ai/)

> “Massive scope bloat — 14-18 phases for every app (overkill for MVPs)”

— `u/kashaziz`, [r/ClaudeAI auto-builder thread](https://www.reddit.com/r/ClaudeAI/comments/1qb1024/ultimate_claude_skillmd_autobuilds_any_fullstack/)

> “find a skill on GitHub, check if it's actually good (most aren't), figure out if the SKILL.md is even formatted right, then hope it doesn't break anything.”

— `u/BadMenFinance`, [Agensi marketplace launch, 35 upvotes](https://www.reddit.com/r/claude/comments/1rkjqjf/i_built_a_marketplace_for_skillmd_skills_because/)

> “I don't see any reason to believe the skills in this marketplace would be any higher quality than that.”

— `u/Positive-Peach7730`, [same marketplace thread](https://www.reddit.com/r/claude/comments/1rkjqjf/i_built_a_marketplace_for_skillmd_skills_because/)

> “it would be nice to preview the md file before selecting download / install.”

— `u/OGMiniMalist`, [same marketplace thread](https://www.reddit.com/r/claude/comments/1rkjqjf/i_built_a_marketplace_for_skillmd_skills_because/)

### Signal synthesis

The positive reports converge on four properties: a narrow trigger, a concrete procedure, reusable real context, and an observable artifact. The negative reports converge on the inverse: persona prompts, giant “do everything” loops, simulated verification, vague triggering, and star-count shopping. This is the basis for Omo’s verification standard.

## 4. What this means for Omo

### Host these first

| Priority | Hosted product | Why evidence supports it | Run economics / required guardrail |
|---:|---|---|---|
| 1 | **Facebook/Meta Ads Copy & Creative** | A company AI lead describes building Meta account context into a skill; Ad Creative has inspected platform-specific instructions and appears in the 165-upvote field test | Cheap text generation. Ask for offer, audience, proof, objective, format, and brand context. Never publish or activate ads automatically. |
| 2 | **Google Ads RSA Headline & Description Generator** | Same inspected Ad Creative file explicitly handles Google RSAs; high-intent, structured output with hard character constraints | Very cheap and easy to validate mechanically: counts, lengths, duplication, prohibited claims. |
| 3 | **Landing Page Copy + Offer Reviewer** | Copywriting produced the most detailed user-reported result; offer design fixes the underlying proposition rather than polishing weak text | Cheap. Show before/after, persuasion framework, unsupported-claim flags, and CTA variants. |
| 4 | **Cold Email Sequence Builder** | Three-message sequence publicly reported; narrow deliverable and clear inputs | Cheap. Require proof and personalization source; flag invented facts and spam/compliance risk. |
| 5 | **SEO Audit Brief** | Actual structured skill plus repeated marketer demand for SEO orchestration | Medium if browsing/crawling is included. Separate observed site facts from recommendations and timestamp every fetch. |
| 6 | **AI-copy Flagger / Humanizer** | A company user built it; commenters say the useful implementation is an explicit second-pass rewrite, preferably by content unit | Cheap. Avoid false “AI detection” claims; describe it as style-pattern editing. |
| 7 | **Churn Save-offer Builder** | Concrete cancel-flow logic and direct SaaS pain; noticed by the Reddit tester, though not field-tested in the fetched report | Cheap text/decision-tree output. Keep billing changes human-approved; test reason-to-offer mapping. |
| 8 | **Verification-before-completion for code** | Massive adoption signal and unusually testable behavior | Cheap instruction layer. Seed a failing test and grade whether the skill refuses an unsupported success claim. |

Start with pure-text outcomes because they are cheap to run, easy to demo, and easy to evaluate. Defer full academic pipelines and generated/dubbed video until Omo has cost metering, asynchronous jobs, and provider-key handling. Local FFmpeg editing is a reasonable second wave because its result can be mechanically inspected.

### The automated-modal product should add what GitHub lacks

1. **Parse and preview:** render name, trigger, author, exact source commit, license, required tools/secrets, network/file-write permissions, and the complete Markdown for free skills.
2. **Generate the modal:** infer required inputs from the skill but let a human curator edit field labels, defaults, examples, and dangerous-action confirmations.
3. **Run safely:** default to read-only, sandbox files/network, redact secrets, keep irreversible/external actions behind a confirmation, and show expected compute/API cost.
4. **Prove behavior:** ship 3–10 public test fixtures per skill, including negative triggers and adversarial inputs. Show pass/fail history by skill version and model.
5. **Show real output:** provide a runnable sample and a permanent output receipt. “Works” should mean a user can inspect the input, version, cost, output, and evaluator—not that a repository has stars.
6. **Preserve context:** let users save a reusable product/brand profile. The strongest marketing test attributes consistency to a shared product-marketing context file.
7. **Measure per skill:** successful runs, rerun rate, saves, paid conversions, refunds, user ratings after an actual run, median cost/latency, and last verified date. Do not inherit the parent repo’s stars as the skill’s rating.

### `skill.md for X` SEO niches with observed demand

| Target page / query cluster | Demand basis | Omo page angle |
|---|---|---|
| `skill.md for facebook ads`, `claude skill for meta ads` | User reports an internal Meta Ads context skill; inspected Paid Ads and Ad Creative files | “Generate Meta ad copy with your account structure and brand context; ads stay paused.” |
| `skill.md for google ads`, `google RSA skill.md` | Ad Creative explicitly supports Google RSA headlines/descriptions | Live character-count validator plus bulk export. |
| `skill.md for ad copy`, `facebook ad copy skill` | 165-upvote field test and 44,020-star collection | Split campaign strategy from creative generation; show multiple hooks and test matrix. |
| `skill.md for seo audit` | Actual skill plus 24-upvote marketer thread asking for SEO orchestration | Crawl a URL, separate facts from recommendations, export prioritized fixes. |
| `skill.md for programmatic seo` | Actual template/data-driven workflow | Upload CSV + template; generate page schema and thin-content checks, not hundreds of unreviewed pages. |
| `skill.md for cold email` | Independently reported three-email sequence | Research-backed personalization with invented-fact guardrail. |
| `skill.md for landing page copy` | Most concrete field-test output | Product-context intake, PAS/AIDA variants, claim/evidence checks. |
| `skill.md for brand voice`, `claude marketing brand voice skill` | Marketing thread asks for approved-example-driven voice; 24-upvote thread names brand consistency | Upload 8–10 approved examples, expose extracted style rules, then run a second-pass rewrite. |
| `skill.md for churn prevention`, `cancel flow AI skill` | Concrete inspected workflow; Reddit tester highlighted dynamic reason-based save offers | Interactive cancellation decision tree and save-offer copy. Mark “community-interest, Omo test pending.” |
| `skill.md for video editing` | 47,737-star OpenMontage and deterministic FFmpeg skill | Upload media, choose operation, preview command/output/cost. |

Create one canonical page per outcome, not thin permutations. Each page should contain the source file, author, last verified date, permissions, real sample input/output, test results, and a “Run this skill” modal. That is both better SEO content and the product proof.

### Pricing and marketplace signals

- The Agensi launch offered creators **80%** and said premium listings were planned. It started with six free maker-authored skills; the founder later reported **42 skills** in a follow-up comment. This is supply growth, not proof of buyer demand.
- No fetched source exposed actual price points, paid transaction counts, creator revenue, or per-skill downloads. **Willingness to pay for raw Markdown remains unverified.**
- A commenter’s core objection is economically important: users can ask Claude to generate a skill and iterate. Omo should therefore keep raw/open files free where licenses allow and monetize **hosted execution, setup/context, scheduled runs, integrations, verification, and support**.
- Use the 80% creator share only as a competitor benchmark, not as proof it is sustainable. Omo should measure gross margin after model, browser, storage, and third-party API cost before fixing a share.
- Pricing hypothesis to test, not a researched fact: one free verified sample run, usage-based hosted runs for occasional tools, and subscriptions only for recurring monitoring/reporting workflows. Do not charge a recurring fee for a static prompt with no ongoing service.

### Competitor gaps Omo can own

| Gap | Evidence | Omo response |
|---|---|---|
| Repository stars substitute for quality | Reddit explicitly warns that high-star “agent specs” can be hype | Per-skill evals and run receipts; no inherited star rating |
| Catalogs optimize quantity | 864 embedded files in one hub; 1,000+ linked elsewhere | Small verified catalog with clear rejection reasons |
| Skill marketplaces cannot prove paid-file quality | Buyer asks why marketplace files beat self-generated prompts | Public fixtures, blind A/B baseline, refund/failed-run policy |
| Security claims are not enough | User asks to preview Markdown before download and says safety must be personally inspectable | Full free-file preview; paid-file frontmatter, permissions, scan findings, sandboxed sample run, and creator identity |
| Skills lose context or fail to trigger | Reddit distinguishes triggered procedures from persistent rules | Explicit run button, visible trigger, saved context profile, and acceptance criteria |
| Mega-skills are brittle and expensive | Auto-builder commenters flag 14–18-phase scope and simulated results | Compose small skills with human approval between phases |
| Marketing outputs start from zero | Independent tester says shared context is the key design | First-class reusable product/brand context object |

## 5. Top 10 insights

1. **Marketing is the clearest beachhead:** 44,020 stars plus a 165-upvote user-reported field run beats generic “agent” hype, subject to Omo reproduction.
2. **`skill.md for Facebook ads` is a real niche:** users already maintain Meta-specific account-context skills and ask for daily marketing workflows.
3. **The winning unit is a small procedure, not a persona:** trigger, steps, pitfalls, and observable done criteria.
4. **Shared business context is the multiplier:** one product/brand source prevents copy, email, and ads from describing different products.
5. **Stars find candidates; tests earn the badge:** no collection star count should become a per-skill score.
6. **Raw Markdown is hard to monetize:** hosting, integrations, repeatability, verification, and support are the paid value.
7. **Second-pass skills are credible:** copy cleanup works when it re-reads and rewrites the finished artifact, not when it merely lists style rules.
8. **Deterministic edges are ideal launch inventory:** character limits, test commands, FFmpeg outputs, and claim checks are cheaply verifiable.
9. **Security must be inspectable:** scans help, but users also want source/permissions previews and sandboxed execution.
10. **Avoid mega-skills at launch:** research/video pipelines can be valuable, but their cost, brittleness, and unverifiable intermediate claims make them poor first hosted products.

## Counts and audit trail

- **Hubs reported:** 10
- **Top skills reported:** 23
- **Reddit quotes reported:** 13 from 5 threads
- **GitHub searches:** 6; 48 unique top results after de-duplication
- **Shortlisted repositories deeply inspected:** 14
- **Actual skill artifacts fetched:** 24 (23 reported; one lifecycle-email file retained only in the checkpoint)
- **Direct Reddit requests:** 3, all HTTP 403; no quote was taken from a failed response
- **Web discovery searches:** 4; full indexed Reddit pages opened for quote extraction
- **Primary checkpoints:** `/tmp/skills_research/github_hubs_checkpoint.json`, `/tmp/skills_research/github_shortlist_checkpoint.json`, `/tmp/skills_rss.json`
