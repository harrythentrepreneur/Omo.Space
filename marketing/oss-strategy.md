# Omo Open-Source Strategy

Status: **founder-set strategy — everything free to download, hosted runs are
the paid product** (updated 2026-08-16 after the first real publish). Canonical
policy: `oss/POLICY.md`. Implementation spec: `research/oss-publish-spec.md`.
R4 publish gate: live in `tools/host-skill/process-submissions.py`.

## The model: everything free to download, paid to run

- **Every** Omo `SKILL.md` is open source (MIT) in the public repo
  **github.com/omo-space/skills** — one repo, `skills/<slug>/` per skill.
  Download and self-host are free, forever. The founder's directive: *"let's
  just make everything for free for now."*
- The PAID product is the **hosted run**: pay per use on omo.space (cents per
  run, no subscription). Typical education run: **$0.10**; the loader
  (`skill-md-to-hosted-workflow`): **$5.00/run** (guarded analysis floor);
  `decodable-book-maker`: $0.99/run; `woven-relationship-book-maker`:
  $0.40/run; `japanese-style-story-video`: $0.10/run.
- Each published folder carries SKILL.md + policy header + LICENSE +
  manifest.json (slug, version, hosted run price, inputs/outputs, source
  SHA-256) and links back to the omo.space listing — **the free file is the ad
  for the paid run.**
- **Conversion note (the founder's playbook):** people download the free
  skill.md, try to self-host, and hit the setup tax (API keys, infrastructure,
  validation, privacy boundary). *"Lots of people get fed up and just use the
  cloud version."* The free file is deliberately runnable-but-annoying-to-host;
  omo.space is the one-click escape hatch, and every published page points at
  it.

## The 30,000-skill vision (SEO + listings at scale)

- Target: **a marketplace of ~30,000 genuinely good `SKILL.md` files**. Scale
  is the moat: 30,000 crawlable skill folders × SEO-friendly names + topics
  (skill-md, ai-skill, phonics, education, agents) = a long-tail search
  library no competitor will out-seo ("phonics worksheet generator", "syllable
  splitter", "decodable sentence creator", ... each its own search landing).
- Every skill folder in the repo AND every `/workflows/<slug>/` listing page
  is an indexed, crawlable surface; the sitemap is generated from the live
  whitelist (`site/catalog.js` `OMO_VISIBLE_SLUGS`), so each new activation
  auto-updates SEO.
- Listings at scale compound: more free skills → more inbound links → higher
  repo/listing rank → more teachers finding Omo → more paid runs.

## The community flywheel (build → post → signup → download → cloud-run)

The founder's growth loop, verbatim: **"I go to the communities, and build
free skills for people then post it."**

1. **Build** a free skill.md for a specific community (a teacher group's
   phonics pain, a creator group's workflow gap, a niche use case).
2. **Post** it in that community — the GitHub link or the omo.space listing
   page.
3. **Signup** — the free download pulls people into the funnel (GitHub stars /
   omo.space accounts).
4. **Download** — they take the MIT file and self-host (or just browse).
5. **Cloud-run conversion** — setup friction + "just use the cloud version"
   converts a slice of downloaders to paid hosted runs.

Every repo README and every listing points at omo.space. GitHub topics,
stars/forks/clones, and CONTRIBUTING.md turn the repo itself into a discovery
channel. Facebook groups / community posts are the demand-side accelerator:
teachers are the highest word-of-mouth vertical (FB group `Omo Space
Community` — pending the founder's identity confirmation, per
research/social-setup.md).

## Creator economics (85/15)

- Makers keep **85%** of marketplace-found sales; **95/5** when the creator
  brings the buyer; plus **20% of positive hosting/API-run margin**.
  (Sources: `copy-change-log.md`,
  `research/marketing-strategy-sol-2026-08-12.md:153`.)
- Splits are public, not negotiated — part of the product ("Money in
  daylight").
- The OSS repo is the top of funnel for both buyers and future creators: a
  creator who sees a free skill.md on GitHub sees the paid-run economics on
  the listing — and the 30,000-skill vision is their invitation to build on
  Omo.

## Premium exception list (never published) — ONE entry

| Slug | Why it stays private |
| --- | --- |
| `illustrated-decodable-story-maker` | The ONLY premium exception. Flagship Phonics Book Maker; SKILL.md sold for **$400** (oss/POLICY.md). It was mistakenly published in the 2026-08-12 batch; **removed from github.com/omo-space/skills on 2026-08-16 (commit c2dd051) and permanently excluded from the R4 gate**. |

Everything else — including the former premium-class `woven-relationship-book-maker`
($29 license → now free download, $0.40/run hosted), `japanese-style-story-video`,
and `decodable-book-maker` — is **free to download** per the founder's
everything-free directive. The R4 gate's exclusion set
(`OSS_PREMIUM_EXCLUSIONS` in process-submissions.py) contains ONLY the
flagship, so no future release can accidentally re-publish it.

## R4 publish gate (implemented 2026-08-16)

- After R3 (live worker-registry smoke), every FREE released slug is published
  to github.com/omo-space/skills `skills/<slug>/` (SKILL.md + policy header +
  LICENSE + manifest.json), committed as `release(<slug>): v<version> oss
  publish` and pushed to main.
- Idempotent (identical re-releases produce no new commit); fail-closed via
  typed `OssPublishBlocker` (clone/prepare/commit/push) — any failure blocks
  the release. Premium slugs skip R4 silently and are never published.
- 7 dedicated tests; 113/113 pass in `tools/host-skill/tests/`.

## Current state

- Repo: github.com/omo-space/skills — public, **102 skills**, MIT.
- 2026-08-16 first real publish (commit **104a2b3**): **15 free skills** in
  the full format — 12 staged live free slugs + `japanese-style-story-video`
  (v0.2.0, $0.10/run) + `decodable-book-maker` (v1.0.0, $0.99/run) +
  `woven-relationship-book-maker` (v0.3.0, $0.40/run); public SKILL.mds only
  (no container internals, no credentials); root `POLICY.md` added.
- Flagship `illustrated-decodable-story-maker` removed from the public repo
  (commit **c2dd051**) — policy restored.
- Backlog: the remaining headerless folders from the 2026-08-12 batch still
  need the LICENSE/manifest/header backfill (same R4 artifact builder); every
  future release publishes automatically via R4.
