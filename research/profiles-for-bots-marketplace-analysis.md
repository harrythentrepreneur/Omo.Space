# Profiles for Bots → Omo Space product analysis

**Date:** 2026-08-18  
**Scope:** Live homepage, browse/search/filter flow, profile listing, getting-started flow, creator submission flow, public source tree, trust panel, CLI installer, secret scanner, resolver and install counter; compared with the live Omo storefront.

## Executive decision

Profiles for Bots is a strong **developer registry and software-supply-chain prototype**. Omo is already a stronger **buyer marketplace**.

Omo should copy its:

1. transparent trust panel;
2. immutable source/version model;
3. repository-derived listing metadata;
4. explicit privilege and dependency disclosure;
5. machine-readable resolver;
6. real usage counters;
7. submission scanning and CI gates;
8. source-at-exact-version links;
9. low-friction “copy this into another agent” action.

Omo should not copy its:

- terminal-first visual system;
- CLI-first buyer journey;
- raw component counts as the main proof;
- GitHub pull request as the required creator experience;
- goal of catalog size before demand and quality;
- permanent “nothing is vetted” posture;
- weak output proof and review layer.

The strategic translation is:

> **Make every Omo workflow inspectable, versioned, proven and easy to submit, while keeping the buyer experience focused on the finished result.**

## 1. What the product is

Profiles for Bots distinguishes a skill from a complete profile: a skill is one document an agent can load, while a profile includes identity, skills, scheduled jobs and tool connections pinned to a git ref.[1] Its sharpest category line is “Come here to install someone, not a paragraph.”[1]

This is clear positioning for Hermes power users. It explains why the directory exists despite existing skill hubs.

### Omo translation

Omo should keep its stronger commercial headline:

> **Buy the result, not another subscription.**

The supporting sentence should explain Omo’s category distinction in buyer language:

> **Run proven AI workflows without setup—or download the files and keep them.**

The current live supporting sentence says Omo is the easy way to run “Codex workflows” seen on reels.[6] That is now too narrow. Omo includes PhonicsMaker, PDFs, books, images, videos, reports and creator workflows. The copy should not tie the marketplace to one model or one discovery channel.

## 2. Live functionality audit

| Surface | What works | Strategic value |
|---|---|---|
| Homepage | Clear product distinction, primary browse CTA, getting-started CTA, featured listings and category counts.[1] | Fast category comprehension |
| Browse | Instant text search, All/Featured/New controls, category filters, result count, compact rows, installs, stars and freshness.[2] | High-density discovery |
| Empty state | A zero-result message asks the user to change the term or clear the category filter. | Prevents dead ends |
| Listing | Version, author, licence, Hermes requirement, pinned ref, install command, copy actions, trust panel, source and README.[5] | Strong pre-install transparency |
| Trust panel | Model, skill list, cron, MCP, hooks and required environment variables; privileged components get warning markers.[5] | Makes code risk legible |
| CLI | Resolver fetch, strict record parsing, privilege summary, user confirmation, then pinned Hermes install.[4] | Safe, repeatable install |
| Resolver | Cloudflare Worker serves immutable listing records and counts CLI installs via a Durable Object.[4] | Machine-readable marketplace |
| Submit | Repository, slug, immutable ref, category and tagline validation; generated YAML; GitHub new-file handoff.[3][4] | No marketplace account required |
| Indexer | Repository-derived catalog, schema validation and credential-shaped value scanning with masked findings.[3][4] | Supply-chain hygiene |
| Public artifacts | Public catalog JSON and `llms.txt` exist in the source tree.[4] | Agent-readable discovery |

This is not only presentation copy. The public source contains the Next.js pages, CLI installer, resolver Worker, Durable Object counter, registry YAML files, source indexer, schema, secret scanner, trust panel, submit form and tests.[4]

## 3. Homepage and visual design

### Strengths

The star-field background, ASCII wordmark, monospace type and purple/cyan palette create a distinctive identity. The product feels native to Hermes users rather than like a generic SaaS template.

The information hierarchy is simple:

1. define the category;
2. browse profiles;
3. explain installation;
4. show featured supply;
5. expose category counts.[1]

Cards use concise, high-signal language. Examples such as “Failing test first. Smallest diff. Proof before done.” and “Inbox to next actions. Three active projects. No fake dates.” communicate operating behaviour rather than vague AI claims.[1]

### Weaknesses

- All seven listings appear as featured, so “Featured” currently means “everything.”
- Small monospace text and the animated/noisy background reduce long-session readability.
- The page is designed for insiders who understand Hermes, profiles, skills, MCP, cron and git.
- Component counts communicate composition and danger, not output quality.
- The cards have no screenshots, sample outputs, success rates, reviews or repeat-use evidence.
- Empty categories are displayed with zero listings; this makes the marketplace look unfinished.

### Omo decision

Do **not** copy the visual system. Omo’s warm, minimal, result-led storefront is better for teachers, creators and business buyers.[6]

Copy these content patterns:

- one behaviour-specific sentence per listing;
- visible category totals;
- a compact evidence row;
- freshness/version signals;
- selective featured status;
- buyer-readable capability disclosure.

## 4. Browse and discovery

The live browse screen is dense and efficient. Each row displays name, author, what it installs, install count, star count, update time and promise.[2]

The text search works across listing content and updates the count immediately. Category and mode controls are easy to scan. Category query parameters are shareable, although free-text search remains local to the page.

### Where it will break at 100 listings

- No output-type filtering.
- No price or cost filtering because it is a free registry.
- No creator reputation layer.
- No verified-quality filter.
- No sort by repeat use, completion rate or satisfaction.
- Install count can reward curiosity rather than successful ongoing use.
- Stars are currently zero and provide visual noise rather than trust.
- Compact rows have no visual examples.

### Omo browse specification

Keep Omo’s current visual-card view, but add a **Compact view** for serious comparison.

#### Browse modes

- Recommended
- Proven
- New
- Free to download
- Education

#### Sort controls

- Recommended
- Most used
- Most repeated
- Recently verified
- New
- Lowest price

Do not expose “highest rated” until reviews are verified against completed paid or granted runs.

#### Filters

- Category
- Creator
- Output: PDF, image, video, spreadsheet, text, ZIP, audio
- Input: form, file, image, audio, URL, chat export
- Price: free, under $0.25, under $1, $1+
- Delivery: hosted, download, both
- Evidence: hosted tested, human reviewed, customer proven, repeat-use proven
- Typical run time

#### Compact row

```text
Phonics Book Maker    PhonicsMaker    $0.99/run
PDF + worksheets      20 hosted tests · verified 2d ago · 6 repeat users
```

## 5. Omo card changes

The live Omo cards are commercially stronger than Profiles for Bots: they show visual examples, creator, promise and per-run price.[6]

Current problems:

1. Cards are tall, so discovery is slow.
2. Titles and descriptions truncate.
3. PhonicsMaker thumbnails use a louder, text-heavy visual language than first-party Omo cards.
4. Every active listing looks equally proven.
5. There is no visible run count, repeat rate, last-tested date or evidence level.
6. Price has high visual priority, but expected time and output type are absent.

### Revised card structure

```text
[visual preview]                       PDF

Phonics Book Maker
Create a decodable illustrated book with worksheets.
by PhonicsMaker

$0.99/run       45–90 sec
✓ Hosted tested · 20 fixtures · verified 2d ago
```

For an unverified listing:

```text
Preview only · Hosted proof pending
```

Rules:

- Two title lines, never one-line ellipsis.
- Two promise lines.
- Consistent thumbnail aspect ratio and text policy.
- Output-type badge on the image.
- Evidence row below price.
- Never invent ratings or use empty stars.

## 6. Listing detail and trust panel

The strongest Profiles for Bots pattern is the trust panel placed before the README. It shows exactly what will be installed and flags unattended jobs, local processes and shell hooks.[5]

Omo should adapt this to a **What this run uses** panel.

### Omo buyer-facing trust panel

```text
WHAT THIS RUN USES

Input            Text + one PDF upload
External calls   Image generation and document rendering
Files created    Book PDF, worksheets PDF, PPTX, editable JSON
Web access       None
Code execution   None
Stored data      Private artifacts retained for 7 days
Typical time     45–90 seconds
Failure policy   Automatic credit refund
Version           v1.4.0 · build 8d942…
Last verified    18 Aug 2026
```

Use buyer language first. Put provider/model names under **Technical details**, not in the main promise.

### Evidence ladder

Omo should not use one vague “Verified” badge. Use exact levels:

1. Source available
2. Schema tested
3. Fixture tested
4. Hosted tested
5. Output reviewed
6. Customer proven
7. Repeat-use proven

Example:

```text
Hosted tested
20 fixture runs
Educator review pending
```

That is more honest and more useful than a five-star score.

## 7. Creator publishing flow

Profiles for Bots asks creators to:

1. export and sanitize distribution-owned files;
2. replace literal secrets with environment references;
3. create a manifest;
4. tag an immutable version;
5. test installation;
6. complete a registry form;
7. open a GitHub change.[3]

This is appropriate for a developer registry. It is too much work for Omo creators.

### What Omo should copy

- Creator retains repository ownership and version history.
- Submission is pinned to an immutable source revision.
- Secret scanning is mandatory.
- Submission schema and CI schema are the same.
- Findings are masked.
- Branch names are not accepted as release identities.
- Creator sees the generated machine contract before publication.
- Source remains downloadable even when hosted execution is offered.

### What Omo should improve

The creator should upload or link a `SKILL.md` and receive value immediately. Omo’s MEGA-agent advantage is that the platform can do the preparation work.

#### Recommended creator flow

```text
1. Add workflow
   Upload SKILL.md, paste text, or connect a repository.

2. We inspect it
   Secrets · inputs · outputs · required tools · external services

3. We build it
   Runtime · tests · sample · artifact checks · estimated cost

4. You review it
   Promise · form · example result · price · known limits

5. Publish
   Hosted run + free source download
```

#### Status ladder

```text
Uploaded → Scanned → Contract ready → Building → Testing → Pricing → Ready
```

Every failure must be typed and resumable:

```text
Needs one credential
Unsupported browser action
Output contract unclear
Artifact renderer missing
Human review required
```

Do not make creators write YAML or open a pull request before Omo has shown that it can host the workflow.

## 8. Safety architecture

Profiles for Bots correctly treats profiles as code. It warns that profiles can schedule jobs, spawn local processes and execute shell scripts, and that listings are not vetted or sandboxed.[1][5]

Its scanner catches known key prefixes and suspicious long values assigned to names such as token, secret, password or authorization. It accepts environment-variable references and masks findings.[4]

### Important limitation

Regex secret scanning is a safety net, not proof of safety. It does not establish benign behaviour. It can miss encoded credentials, indirect exfiltration, malicious dependencies or safe-looking shell hooks.

### Omo advantage

Omo runs hosted workflows inside controlled infrastructure. It can provide stronger guarantees than a local profile registry:

- isolated runtime;
- no customer-controlled shell;
- network allowlist;
- owner-scoped artifacts;
- bounded inputs;
- cost limits;
- timeout limits;
- secret isolation;
- exact version execution;
- automatic refund on failed output;
- retained execution evidence.

This should become a visible marketplace advantage:

> **Runs in an isolated Omo container. The creator never receives your credentials.**

Only show this when technically true for that workflow.

## 9. Usage, reviews and reputation

Profiles for Bots counts installs from its CLI instead of GitHub clones.[2][4] This is better than repository download counts, but it still measures installation rather than value.

Omo can measure stronger signals:

- completed runs;
- valid-output rate;
- repeat users;
- second paid runs;
- refund rate;
- artifact downloads;
- review linked to a completed run;
- last successful hosted test;
- creator response time.

### Public signals

Show:

```text
128 completed runs
97.6% valid outputs
31 repeat users
Verified 2 days ago
```

Do not show metrics for tiny samples as percentages. Use:

```text
8 of 8 hosted tests passed
```

until volume is meaningful.

## 10. Agent-readable marketplace

Profiles for Bots includes a resolver API, public catalog JSON and `llms.txt` in its public source.[4]

Omo should expose:

- `/llms.txt`
- `/catalog.json`
- `/api/workflows/{slug}`
- `/api/workflows/{slug}/schema`
- `/api/workflows/{slug}/evidence`
- `/api/workflows/{slug}/versions`

Each workflow record should include:

- buyer promise;
- input schema;
- output schema;
- price;
- expected time;
- output artifacts;
- current version;
- evidence level;
- known limits;
- hosted/download availability;
- creator;
- source URL;
- run endpoint documentation.

This supports both human browsing and agent-to-agent purchasing.

## 11. Features to reject

### Do not copy the “100 templates” goal

Catalog count is not Omo’s constraint. Omo already has a large workflow inventory. The bottleneck is proven hosted supply, repeat use and distribution.

Omo’s better target is:

```text
20 workflows
20 fixture tests each
5 real users each
2 repeat buyers each
```

Then expand.

### Do not copy no-signup as a universal rule

No signup is good for source download and public browsing. Hosted paid runs need identity for credits, ownership, refunds, artifact access and abuse prevention.

Use:

- browse without signup;
- download public source without signup;
- run demo fixtures without signup where safe;
- authenticate before private uploads or paid runs.

### Do not copy raw model-first metadata

Buyers do not want to choose a model. They want the promised artifact. Provider/model information belongs in technical details and version evidence.

### Do not copy terminal aesthetics

It suits Hermes insiders but conflicts with Omo’s warm, result-led, Skool-like simplicity.

## 12. Prioritized Omo roadmap

### P0 — immediately valuable

1. Add evidence row to catalog cards.
2. Add output-type and typical-time badges.
3. Add “What this run uses” trust panel to workflow pages.
4. Add exact version and last-tested date.
5. Add source/download link at the exact version.
6. Add explicit current limitations.
7. Standardize PhonicsMaker and Omo card thumbnail treatment.

### P1 — marketplace trust

1. Verified completed-run counts.
2. Repeat-user counts.
3. Valid-output rate with sample size.
4. Review only after completed run.
5. Automatic evidence level.
6. Public workflow version history.
7. Public machine-readable evidence endpoint.

### P2 — creator growth

1. One-field SKILL.md/repository submission.
2. Automatic secret scan.
3. Automatic contract extraction.
4. Build/test/price status ladder.
5. Creator review screen.
6. Immutable release publication.
7. Typed blockers with one-click resume.

### P3 — agent distribution

1. Catalog resolver API.
2. Agent-readable install/run prompt.
3. `llms.txt` catalog index.
4. “Copy request for an agent” action.
5. MCP/API discovery surface.

## 13. Default validation volume

A single canary only proves wiring. It does not prove quality.

For new Omo hosted workflows, the default proposal should be a meaningful batch:

- 20 deterministic fixtures for normal text workflows;
- 10 complete artifact runs for PDF/image/video workflows;
- 3 repeated runs for each stochastic fixture;
- one wrong-input test per major validation rule;
- one provider-failure/refund test;
- one owner-isolation test;
- measured cost and latency distribution.

Provider-backed execution still needs an explicit dollar cap before spend, but the default should be large enough to estimate failure rate and output variance rather than a token one-run proof.

## Final recommendation

Build a **Proof Layer** for Omo, inspired by Profiles for Bots’ Trust Panel:

- proof on cards;
- detailed trust on listings;
- immutable source/version links;
- machine-readable evidence;
- real usage and repeat signals;
- automatic creator submission gates.

Do not redesign Omo around the competitor. Omo already has the better buyer-facing shell. Add the competitor’s strongest infrastructure ideas underneath and expose them as buyer trust.

## Sources

[1] https://profiles-for-bots.pages.dev/start — Profiles for Bots — Getting Started
[2] https://profiles-for-bots.pages.dev/profiles — Profiles for Bots — Browse
[3] https://profiles-for-bots.pages.dev/submit — Profiles for Bots — Publish
[4] https://github.com/capthvnsen/importprofile — Profiles for Bots — Public Source
[5] https://github.com/capthvnsen/hermes-profile-pe/tree/v0.1.0 — PE Analyst Profile Source v0.1.0
[6] https://omo.space — Omo Space — Live Storefront
