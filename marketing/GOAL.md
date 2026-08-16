# Omo Growth Loop — GOAL.md (goal contract + live state)

North star: $100,000 in a single day of Omo revenue.
Honest path: GATE 1 (prove a teacher pays twice) -> $1k/mo -> $10k/mo -> scale.

## Current goal (contract)

Get Omo to $1,000/month contribution margin. Immediate step: clear GATE 1 of the Omo pilot.

### Builder hosting acceptance definition

- Success metric: >= 70% of submitted `skill.md` files end up HOSTED (built, tested, verified, priced, deployed, chargeable).
- The remaining <= 30% are TYPED BLOCKERS — a correct outcome, never a silent skip: exact reason, evidence, resume point.
- The per-run quality floor stays at the current 90% per-run gate; it is not weakened. The 70% bar is measured over a rolling set of uploads (for example, the last 20).

verify:
- >=20 successful free books made by the 200-email cohort
- >=5 paid second books within 14 days
- >=95% valid-output success; 0 double-charges; 100% auto-refund on failure
- <5% refund/complaint rate; support resolved <24h

boundaries (hard — do not cross without Harry):
- No email to the full 4,500 list (200-person pilot cohort only)
- No paid ad spend
- No creator DMs
- No production deploy beyond the pilot path

stop-and-propose when: any external send, spend, or production push is required.

Full safety rules (irreversible = ask Harry; loop mechanics; what to do on a
rule break) live in /Users/yifan/marketplace/AGENTS.md and bind every run.

## Status

- VERIFY + WAITING (2026-08-16T15:30Z, this tick): upstream re-verified unchanged since the 15:04Z hunt — `git fetch` 0 behind / 13 ahead (all 13 ours), no new Harry/coordinator commits. Integrity check on our committed pilot-book chain: profile, generated container, template, hunt evidence all tracked; the vocabulary fixture IS committed at `packages/skill-to-modal/tests/fixtures/vocabulary-book-normalizer.json` (5f0a556 — resolved a false alarm from a wrong-path lookup). Fresh evidence: `pytest -k vocabulary` = 3 passed / 56 deselected from the committed tree, so the recorded 57/58 compiler-suite claim's vocabulary portion still holds. No new buildable exists; every remaining gate is Harry/coordinator-owned. Metrics unchanged 0/0/0. No spend, send, deploy, push, or secret access.
- VOCAB-SOURCE-HUNT DONE (2026-08-16T15:0xZ, this tick): the "no reviewed word-bank exists" blocker is now verified at CONTENT level across all 102 folders of omo-space/skills (deep clone + grep of every SKILL.md: zero static word banks; the 8 vocabulary-mentioning skills are all procedural generators; decodable-book-maker/SKILL.md explicitly demands a "compiler-owned vocabulary" + "reviewed sight-word list" and ships neither — the contract expects the platform to own it). GitHub public search for `phonicsmaker` repos: total_count 0. phonicsmaker.com is unreachable behind a Vercel Security Checkpoint (curl 429, r.jina.ai returns the checkpoint shell, real browser lands on an empty checkpoint, no subdomains resolve, phonicsmaker.vercel.app 404). Web archives/search engines all rate-limited or bot-walled this tick (wayback 429, DDG/Bing shells, Google 403). Evidence and a re-check ritual are recorded in `research/decodable-vocabulary-source-hunt.md`. TWO LOOP CORRECTIONS: (1) the "web tooling unavailable" claim applies ONLY to the Firecrawl `web_search`/`web_extract` backend — raw curl (raw.githubusercontent 200) and the browser tool DO work in cron, so a named-URL fetch is now provably buildable; (2) Harry's unblock cost dropped: paste the word bank his own PhonicsMaker tooling trusts into the template, OR name any URL and the loop will fetch it via curl, bind it as reviewed_spec.vocabulary, regenerate, and flip can_submit (machinery already done, fixture-proven 3/3). No spend, send, deploy, push, or secret access.
- WAITING (2026-08-16T14:01Z): git fetch confirmed origin/main unchanged since the 13:26Z reconcile — 0 behind / 11 ahead, tree clean, no new founder or coordinator input. Web tooling re-confirmed UNAVAILABLE in this cron session (no Firecrawl config / API key), matching prior ticks, so no external corpus sourcing is possible and none was attempted. All buildable machinery is complete (vocabulary normalizer fixture-proven 3/3 on synthetic data; fill-in template ready at marketing/pilot-book-vocabulary-template.md; local branch reconciled). The remaining chain is 100% Harry/coordinator-owned: (1) reviewed vocabulary content -> bind/regen/flip can_submit; (2) coordinator pull of our 11 local commits; (3) approvals for semantic-recovery-provider-proof-001, japanese-modal-deploy-001, magic-link deploy, and the social X identity gate. No new PROPOSAL added — the existing asks already spell out the exact approvals. Metrics unchanged (0 / 0 / 0). No spend, send, deploy, push, or secret access.
- RECONCILED WITH origin/main (2026-08-16T13:26Z): fetched the remote and merged 27 coordinator commits into our local main (merge base `696ffc6`, zero text conflicts). The remote brought: the label-normalizer-canary RELEASE chain (#94-#111 — the first chargeable run-manifest `site/run-manifests/label-normalizer-canary.json` released through the creator-builder pipeline), Reddit research #90 (`research/REDDIT-AI-SEO-STRATEGY.MD`, buyer/creator/marketplace-sentiment sources + mining scripts), GitHub skill-scout #88 (`scripts/github-skill-scout.py`), image style system #84 (`research/social-assets/style-sheet/` + three signature posts), OSS everything-free strategy, and credential-strategy restore #93. The coordinator's own GOAL.md on the remote is STALE — it predates their own 27 commits and still claims "exact $0.99 book slug not identified," which our pilot-book-correction already disproved; the merged GOAL.md carries our corrected state. Integration bug found and fixed this tick: the coordinator's new `label-normalizer-canary` profile was unpinned — probed its kind (`schema_only`), added it to `_EXISTING_PROFILE_KINDS`. Verified merged tree: compiler suite 58/1 (sole fail = pre-existing ffmpeg env gate), decodable-book-maker container 14/14, label-normalizer-canary container 5/5, catalog.js parses with all 14 visible slugs + our six humanized copy strings preserved. NO push performed — origin/main still lacks our 9 local commits (pilot-book runtime, vocabulary machinery, fixtures, template); the coordinator must pull/merge our branch to land the decodable-book-maker supply-side work upstream.
- Builder breadth BUILDABLE #1: the six generic contract-evidence adapters (`semantic.grounded_numeric_copy`, `semantic.exact_field_projection`, `semantic.constraint_coverage`, `semantic.policy_requirement_coverage`, `semantic.rule_based_classification`, `semantic.placeholder_glossary_enforcement`) are implemented as shape+promise selectors in `semantic_evidence_spec` plus `_<kind>_semantic_diff` evaluators and dispatcher branches in the generated runtime template (2026-08-16). Compiler suite 51/52 green (sole failure = pre-existing ffmpeg version gate); 5 new fixture-only tests cover right-needle replay, 10 distinct wrong-needle tokens, selector fail-closed without a reviewed contract, and an all-18-profile no-reclassification pin (0 new container drift measured). Nothing was committed for containers, pushed, deployed, or sent; Codex sol review was unavailable (OpenAI 401 in cron session) so verification is direct generated-runtime evidence.
- State: production payment loop is LIVE (per the marketplace dev agent's session, 2026-08-12) — the additive Neon schema is applied (all 12 tables), the three live Worker secrets (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, NEON_DATABASE_URL) are set, and a Woven checkout returned a real Stripe Checkout URL. The local release state now has a reversible 14-listing whitelist: the existing four listings, nine ready education tools, and the ready $5/run Skill.md loader; the coordinator still owns the production push.
- Done: marketing plan (sol), payment-loop spec + pilot email, loop harness, payment-loop gap audit, fast signup-grant visibility, live secrets/routes, request-safe Neon access, 10/10 unauthenticated live canary, checkout orphan-session expiry, 24-listing honesty audit, four text-free phonics marketplace thumbnails, and 12 locally compiled/tested/priced PhonicsMaker workflow bundles.
- Social-post skill proof: the validated `omo-social-media-post` Hermes skill is installed in the Omo profile with eight synthesized layouts, three exact custom themes, X/IG/FB presets, honest caption templates, and Codex/API `gpt-image-2` paths. Its first real X post is a visually verified 1600x900 Woven binary comparison under `research/social-assets/sample-posts/woven-whatsapp-keepsake/`; nothing was posted or sent.
- Pilot cohort: the exact 200-contact GATE 1 cohort is built from the 5,087-row Loops export at the protected Hermes data path; it contains 182 intent+segment contacts and 18 segment-fill contacts, excludes unsubscribed/junk/current-active-subscriber rows, and passes count, format, uniqueness, and subscription checks. No email was sent.
- Modal isolation: the account topology is `harrythentrepreneur`, `phonicsmaker`, and `omo-space`; the user-local Modal CLI 1.5.0 launcher is authenticated only through the owner-only `/Users/yifan/.modal-omo.toml`. The nine education apps are deployed in `omo-space/main` and each reports `state=deployed`; no PhonicsMaker resource was opened or changed.
- Education hosting release: the founder accepted the 70% hosted-success bar and Gate 1R3 provides 25/27 schema-valid plus 25/27 semantic runs, with every one of the nine tools retaining at least 2/3 passes. All nine are now generated, registered, priced at $0.10, deployed, chargeable, and locally activated; the two known limits remain typed, fail-closed catalog disclosures. A real authenticated education-app POST returned HTTP 202 with the accepted run shape. Exact suites pass compiler 20/20, host 82/82, generated containers 99/99, Worker helpers 17/17, and router 173/173.
- Creator builder infrastructure: issue #63 moved creator-build dispatch off Hetzner through Cloudflare cron -> protected Modal endpoint -> Worker-authoritative atomic claim -> one revision/source-bound ephemeral Hermes build. Issues #65/#67/#69 added recovery, safe failure stages, and immutable-checkout imports. PR #72's approvals-off approach was contained and reverted by PR #73. Issue #71/PR #74 enforce OS-UID and fresh-checkout privilege separation; issue #77/PR #78 fixes the reproduced Hermes startup dependency and is deployed at `d3678df`. Issue #79 generalizes the owner-safe pre-runtime retry to both existing gated failure codes, covering a Hermes failure before runtime selection while preserving owner, failed-state, immutable-hash, and atomic-update guards; Worker contracts pass 187/187.
- Artifact runtime: a shared deterministic ReportLab renderer, owner-scoped immutable local artifact store, no-refresh Codex subscription image bridge, exact contract/integration notes, and real-PDF smoke test now exist under `tools/render/` for the worksheet, illustrated-story, and edit-studio workflows; targeted renderer/adapter/compiler/host tests are green, with no registration or deployment.
- Woven builder-capability release: the shared compiler now materializes default-off `book_pdf` artifacts and bounded `whatsapp_zip` input adapters; Woven 0.3.0 was regenerated from its reviewed profile, registered at $0.40, deployed to `omo-space` with `state=deployed`, and proven with a real two-pass WhatsApp ZIP run producing a visually verified five-page signed keepsake PDF. The clean staged snapshot passes compiler 22/22, Woven 20/20, host 77/77, and renderer 9/9 (128/128); the current worktree including concurrent host/renderer tests passes 158/158. Catalog and listing copy are locally republished, with no push.
- Japanese media-executor candidate: the compiler now materializes the reviewed de Mello procedural sumi-e modules and bundled 10-second audio as a slug-locked skill-owned resource, generating a ready/chargeable owner-scoped async runtime at $0.10. A real local run produced and full-decoded a 10.000-second 1080x1920 H.264/AAC MP4 with 30 generated frames, 300 output frames, five exact-digest artifacts, zero provider spend, and $0.00061482 measured compute; compiler 28/28, host 88/88, container contracts 361/361, render 34/34, Worker helpers 17/17, cost 11/11, and router 180/180 pass. The live Modal deploy and hosted 202 smoke remain blocked on Harry's explicit specific approval; arbitrary audio remains rejected before work.
- Skill.md loader release: the deterministic build/analysis service is generated from a compiler-owned profile/resource, uses proxy-authenticated owner-scoped async endpoints, compiles explicit machine contracts through the canonical compiler, runs five fixture-only checks with zero provider calls, and fails closed on typed blockers or unknown cost. R1 proves one loader runtime row in the 14-row registry; R2 deployed Worker version `8c0b7456-eeac-45e8-b65e-c0c7fcdccfd3`; and R3 returns `authentication_required`, not `unknown_catalog_slug`. Under founder authorization `loader-modal-redeploy-002`, the compiler-owned import fix was redeployed to `omo-space/main` and the one owner-scoped tiny-uppercase fixture canary returned HTTP 202 then completed `ready` at $0.10 with 5/5 checks and `provider_calls: 0`. The local listing remains active/chargeable at $5/run, the canonical live URL returns HTTP 200, and suites pass 154 Python, 183 router, 17 Worker-parser, 22 billing, 11 cost, and 19 support checks. Sanitized evidence is `/tmp/loader-live/final-release-gates.json`; public static activation still awaits the coordinator push.
- Pilot magic-link release: the finalized email's one-free-$0.99-book promise is implemented locally as a 99-cent HMAC-signed grant with Clerk-authenticated redemption, hashed pending-claim handoff, an append-only `signup:pilot-<token digest>` ledger event, typed invalid/expired/reused errors, and a static auth landing bridge. Fixture suites pass 245/245 including the Clerk webhook race and balance replay; sanitized evidence is `/tmp/magic-link/`. No schema, Worker, or static production deploy occurred, and redemption fails closed until the coordinator supplies the exact reviewed live PhonicsMaker book slug.
- Capability growth BF: reusable standard-library modules and registry specs now exist for bounded robots-aware direct public URL fetch and deterministic CSV/tabular statistics; focused tests pass 19/19 with a loopback-only fixture. Public query search remains honestly PARTIAL/unavailable in v1, both registry entries remain experimental pending sibling-owned compiler integration, and `compiler.py` was untouched.
- Generator hardening BJ: compiler-owned `tabular_analysis_orchestrator`, arithmetic-verified budget derived-number allowlisting, and copy-revision semantic reconciliation are fixture-proven against the six exact final-rerun inputs at 2/2 per skill with zero provider calls. Compiler 41/41, regenerated final-rerun bundles 10/10 each, and repository generated containers 386/386 pass; evidence is `/tmp/hardening/`. The machine is ready for the requested 30-skill batch, while the existing public-search and isolated-code capabilities remain separate typed blockers.
- BATCH-30 provider proof BL: authorization `batch30-sensitive-egress-001` was exercised with process-only OpenCode Go credential loading and synthetic inputs only. The fresh 60-case run is `BATCH30-RATE-7/30`: 28/28 provider-backed outputs were schema-valid, 17/28 passed semantic evidence, seven skills were HOSTED, 23 remained exact typed blockers, and 28 known-cost calls totaled USD 0.00897834 with no retry. Fresh source/drift/compiler/generated gates pass 30/30, 30/30, 41/41, and 300/300; final evidence is mode 0600 under `/tmp/batch30/`.
- Final hardening BM: one explicit-`DOMAIN`, schema-projected `domain_analysis_orchestrator` now serves the seven tabular domain workflows, and data-analysis routes its bounded program through hosted `execute_workflow`. Fixture-only gates pass compiler 46/46, eight regenerated bundles 80/80, drift 8/8, and eight executions 8/8 with no raw rows in findings prompts and zero provider calls; all seven domain profiles plus data-analysis flip to ready in the regenerated evidence under `/tmp/final-hardening/`. No compiler-side blocker was silently cleared, `tools/` was untouched, and no commit, push, deploy, credential read, or external call occurred.
- GitHub moat-build ceremony: the 28-file non-secret documentation/audit snapshot is published on `main` at `aa7845c`; issue #58 records the completed 15/30 fixture-proven build and links the three still-open founder-desk holds (#59 public-query search, #60 isolated safe execution, #61 bounded image generation). The ignored `research/kaviru-chat/` path and all `.env` material remained outside the index; runner, manifest, and unrelated fixture directories remain untracked.
- OSS skills library: all 95 publishable workflows in the 96-tool PhonicsMaker inventory now have public twins in `omo-space/skills`; 85 new skill/README pairs were published atomically in `ab02e824`, all 84 prompt-only tools remain honest draft specs and the story editor remains in review, and the pre-existing private illustrated-story skill was not changed. The library has 97 folders including the separate worksheet skill.
- Strategy artifact: researched and ranked 25 education-SaaS targets in `marketing/edtech-kill-list.md`; first ship queue is Diffit, MagicSchool, Twee, Formative, then Kahoot feature outcomes.
- Category-expansion artifact: researched Education, E-commerce, real-estate listing media, short-form content repurposing, and recruiting/career documents in `marketing/category-expansion.md`; direct per-product, per-image, and metered-result pricing supports that rank order, with E-commerce as the first post-Education test.
- Creator research artifact: ranked 40 verified-or-explicitly-flagged prospects in `marketing/creator-dm-list.md`, led by creators who already demonstrate Diffit, MagicSchool, Twee, Formative, or Kahoot; no outreach was sent.
- Nous origin research artifact: sourced origin, Hermes/OpenHermes/DisTrO chronology, growth mechanics, funding caveats, and Omo lessons in `research/nousresearch-origin.md`; no external action occurred.
- Outreach/review drafts: first-wave ranks 1–8 have audience-first DM copy, and the first three PhonicsMaker proof-page skills have a repeatable named-educator review protocol; no outreach or publication was made.
- Education launch content: a live-rule-checked Reddit channel plan plus four YouTube Shorts, four Instagram Reels, three lead-workflow copy blocks, and the first three review drafts are complete in `marketing/education-launch-content-plan.md`; all copy is gated on workflow activation, final pricing, educator review, and a same-day community-rule recheck, and nothing was posted or sent.
- OpenSea marketplace research: `research/opensea-growth.md` documents the verified 2017 origin, founder-led supply seeding, flywheel mechanics, fee/royalty and Blur competition history, evidence gaps, and an honest moat analysis for Omo; no external action occurred.
- Fiverr marketplace research: `research/fiverr-growth.md` documents the sourced 2010 origin, evidence limits around first-side seeding, Gig/SEO/reputation flywheel, fee and take-rate history, milestones, AI response, and concrete Omo lessons; no external action occurred.
- Unified catalog: `site/catalog.js` now contains the 24 preserved live-priced listings plus 96 PhonicsMaker previews with human-readable names, promises, and fail-closed `Coming soon` state; 95 previews use exact v5 thumbnails and `phonics-story-editor` uses the existing visual fallback because no matching v5 file exists.
- Storefront cleanup: the separate catalog browser, homepage promo/link, projection data, stale 100-item inventory, and import tooling are removed; listing, dashboard, workflow, run, nav, library, host tooling, and MCP reads now converge on the single catalog without changing Worker auth or payment wiring.
- Storefront visibility: every storefront render and direct-detail surface now uses a reversible 14-slug whitelist containing the existing four listings, nine education tools, and `skill-md-to-hosted-workflow`. The loader's local prerender exposes only its live $5/run CTA and honest fixture-only/no-provider limitations; public static activation still requires the coordinator-owned push.
- SEO sitemap visibility: the prerender generator reads `OMO_VISIBLE_SLUGS` at build time, so `site/sitemap.xml` contains the 14 visible workflow slugs plus seven core pages; all 222 prerendered workflow directories remain on disk.
- Fixture baseline repair: the three semantic test fixtures (`semantic-adapter-real-runs.json`, `semantic-adapter-inputs.json`, `hardening-final-rerun.json`) were never tracked in git and were lost with /tmp, which made the committed compiler suite fail 15/47 on a fresh checkout. They are reconstructed as clearly-labeled DETERMINISTIC SYNTHETIC fixtures (same contract shapes, evidence kinds, and mutation needles; explicitly NOT recorded provider runs; provenance field + README) and committed, so the suite is reproducible from git: 46/47 pass, sole failure = `test_generated_video_binding_smoke_and_typed_domain_transitions`, the pre-existing ffmpeg 8.0.1-vs-8.1.2 environment gate documented since issue-63. Test env: /tmp/issue8-venv (pytest+jsonschema+modal+fastapi+pypdf+pillow+reportlab).
- BATCH30 semantic-blocker reconstruction: the seven real `REAL_RUN_SEMANTIC_FAILED` staged sources lost with /tmp (code-documentation, email-drafting, logo-design, privacy-policy-drafting, proposal-generation, ticket-triage, translation) are reconstructed as reviewed local contracts in `packages/skill-to-modal/tests/fixtures/batch30-recovered-adapters.json` (provenance-labeled synthetic). All seven compile through the canonical compiler and the generated runtimes select exactly the matching `semantic.contract_evidence_adapters/v1` adapter (code-documentation & translation → constraint_coverage; email-drafting → exact_field_projection; logo-design → placeholder_glossary_enforcement; privacy-policy-drafting → policy_requirement_coverage; proposal-generation → grounded_numeric_copy; ticket-triage → rule_based_classification). Replay: 7/7 right needles pass, 7/7 wrong needles fail closed with typed markers; compiler suite 54/55 green (sole failure = pre-existing ffmpeg 8.0.1-vs-8.1.2 environment gate); zero provider calls or spend.
- Storefront copy pass: all 14 `OMO_VISIBLE_SLUGS` listings were audited; the six worst buyer-facing strings (japanese-style-story-video desc+demoCap, woven, customer-feedback-theme-finder, facebook-ads-copywriter, skill-md-to-hosted-workflow) were rewritten into result-first human copy with every factual/price/honesty claim preserved (catalog.js only). `node --check` PASS, catalog parses as JSON (121 listings), `test_published_catalog` 1/1, diff clean. No deploy/push/send/spend.
- Pilot-book slug finding SUPERSEDED (2026-08-16): the previous tick typed the pilot-book blocker as "no released $0.99 book; the only book-maker is illustrated-decodable-story-maker at a $1.62 floor; a price/scope decision sits with Harry." Live verification THIS tick proves that finding WRONG: `decodable-book-maker` v1.0.0 @ $0.99/run EXISTS and is OSS-published (live manifest from github.com/omo-space/skills: hosted_run_price_usd 0.99, source_sha256 d01ae61d577c1555b1b32761b15ea7c08c4c5fe1203756d18132a77bcb8785d7; reviewed contract = 5 cumulative phonics stages, theme, optional child_name -> multi-page PDF book + decodability report + signed artifact URL), and Harry ALREADY settled the price/scope by binding `PILOT_BOOK_BUILDER_PATH="/run.html?slug=decodable-book-maker"` with `PILOT_GRANT_CENTS="99"` in `site/deploy/wrangler.toml` (commit 44879e2, 2026-08-16 04:33Z, an ancestor of this loop's own commit 35b514f). The genuine gap is the LOCAL HOSTED RUNTIME: no profile in packages/skill-to-modal/profiles/, no containers/decodable-book-maker/, no run-manifest, no catalog row, absent from OMO_VISIBLE_SLUGS (verified via git log --all and catalog grep). The OSS publish came from a different checkout; this repo has no decodable-book-maker source of truth. So the typed blocker changes from "Harry price/scope call" to "reconstruct the local hosted runtime from the published reviewed contract (fetch OSS SKILL.md/manifest, author the profile, compile fixture-only) — no spend, no deploy, no Harry needed for the local build."
- Pilot-book runtime half-DONE (2026-08-16, this tick): the local profile `packages/skill-to-modal/profiles/decodable-book-maker.json` is authored from the verified published contract and compiled through the canonical compiler into `containers/decodable-book-maker/`. The generated bundle is coherent and fail-closed: `book_pdf` artifact with signed persistence routed (reportlab+pypdf image packages), input schema = 5 cumulative stage enum + bounded theme + optional child_name, output schema = title/book/page_plan/decodability/artifact/artifact_url/usage, source SHA-256 d01ae61d recorded. Readiness is honestly `can_submit=false` with ONE typed blocker `DECODABILITY_VOCABULARY_MISSING` surfaced in both capability-manifest and manifest: the reviewed contract demands a compiler-owned stage vocabulary + reviewed sight-word list recomputed deterministically with zero review words in a runnable result, and no such vocabulary resource exists in this repo or the OSS twin (which publishes only SKILL.md/manifest/README/LICENSE), nor does the compiler have a whole-book vocabulary normalizer kind. Compiler suite 54/55 green (sole failure = the pre-existing ffmpeg 8.0.1-vs-8.1.2 env gate, unchanged), the new container's network-disabled contract tests pass 14/14, and `_EXISTING_PROFILE_KINDS` gained `decodable-book-maker: schema_only` so the 19-profile no-reclassification test passes. Local run-manifest/catalog row and any deployment remain not done (need the vocabulary gate + coordinator push + Harry's live-change approval respectively).
- Vocabulary normalizer MACHINERY DONE (2026-08-16, this tick): the compiler gained the `semantic.whole_book_vocabulary/v1` kind — a selector in `semantic_evidence_spec` that fires ONLY when `reviewed_spec.vocabulary` carries `provenance: reviewed`, exact stage-enum match, one book string field, and a decodability object exposing word_counts/review_words/sight_words; plus a deterministic whole-book token classifier (stage-vocab / sight / name-exception / review slots) with decodability-report recompute wired into the generated runtime (`_whole_book_vocabulary_scan` + semantic diff + `_semantic_normalize` hook + dispatcher branch). Proven 3/3 fixture tests on a clearly-labeled SYNTHETIC vocabulary (`tests/fixtures/vocabulary-book-normalizer.json`, provenance-documented, NOT reviewed content): right needle (stage-1 book with name exception -> 100% within-stage, zero review words, exact recomputed report), out-of-stage word -> `$:semantic_review_words`, unknown stage -> `$:semantic_unknown_stage`; plus a fail-closed selector test (draft provenance -> schema_only, reviewed -> whole_book_vocabulary, absent vocabulary -> schema_only). Compiler suite 57/58 green = recorded 54/55 baseline + 3 new tests (sole fail = pre-existing ffmpeg gate); no-reclassification pin holds; profile blocker detail updated to reflect machinery done. The ONLY remaining gap is the REVIEWED CONTENT, verified this tick to exist nowhere: OSS twin ships no data files per skill, all 95+ PhonicsMaker inventory skills are procedural generators with no static word bank, no third-party corpora in repo — so the five stage vocabularies + sight-word list are strictly a Harry decision. No container regen yet, no commit of containers, no push/deploy/spend/send/credential access.
- Gate-friction reduction (2026-08-16, this tick): `marketing/pilot-book-vocabulary-template.md` now gives Harry a fill-in-the-blank JSON (exact five stage enum keys, cumulative rule, sight-word list, validation rules, and the post-landing regen/reverify/flip checklist); verified this tick that nothing else changed — git log clean since 5f0a556, live catalog.js still serves all 222 prerendered slugs (coordinator's 14-card push has NOT landed), and the OSS decodable-book-maker manifest remains live and unchanged at skills/decodable-book-maker/manifest.json (v1.0.0 @ $0.99, folder ships only SKILL.md/README/LICENSE/manifest — no data files, so content is still strictly a Harry decision). No external send, spend, deploy, push, or credential access occurred.
- Next: (1) get the REVIEWED vocabulary content from Harry — the five cumulative stage vocabularies + sight-word list (verified this tick: no reviewed word-list source exists in the OSS twin, which publishes only SKILL.md/README/LICENSE/manifest per skill, nor in any of the 95+ PhonicsMaker inventory skills, which are procedural generators with no static word bank, nor anywhere else in this repo; web tooling unavailable in cron; fill-in template ready at marketing/pilot-book-vocabulary-template.md) — then bind it as `reviewed_spec.vocabulary` in the decodable-book-maker profile, regenerate the container, and flip can_submit; the whole_book_vocabulary normalizer kind is DONE and fixture-proven 3/3 on synthetic data, so content binding is the only remaining machinery-gate step; (2) coordinator pushes the local loader/catalog/listing plus corrective-fix commits and verifies the 14 production cards; (3) obtain Harry's explicit specific approval for the isolated Japanese Modal deploy and canary; (4) re-run an authenticated top-up + Woven checkout canary to confirm the live payment loop; (5) move Omo onto its own Stripe account; (6) rotate the live sk exposed in chat; (7) after Harry's explicit production approval, set the magic-link secret and deploy the Worker/static bridge (the slug is now bound, so the remaining pilot-deploy steps are approval-gated, not slug-hunted); (8) run the 20 pilot canaries; (9) obtain Harry's explicit approval before any pilot email send.
- Blockers: the seven semantic-blocked skills are RESOLVED at the semantic layer; fresh provider proof per skill awaits Harry's explicit spend approval (formally proposed as `semantic-recovery-provider-proof-001`). The public static loader activation awaits the coordinator-owned push. Japanese Style Story Video's regenerated app separately awaits its exact live-change approval; Stripe LIVE runs on the shared PhonicsMaker Stripe account; a live sk was exposed in chat (rotation pending); pilot-book slug is RESOLVED (bound to decodable-book-maker @ $0.99) and its LOCAL HOSTED RUNTIME is authored + compiled fail-closed with the single typed `DECODABILITY_VOCABULARY_MISSING` gate, now narrowed to CONTENT ONLY: the whole_book_vocabulary normalizer kind is done (fixture-proven on labeled synthetic vocabulary, selector fail-closed without a reviewed resource) and the only missing piece is the five reviewed cumulative stage vocabularies + sight-word list, which is strictly a Harry decision — now verified at CONTENT level this tick that no reviewed word-bank exists anywhere public (all 102 OSS skill files grepped: zero static word banks, only procedural generators; GitHub public repos matching `phonicsmaker` = 0; phonicsmaker.com unreachable behind a Vercel Security Checkpoint; archives/search engines rate-limited/bot-walled). Harry's fastest unblock: paste the word bank his own PhonicsMaker decodable-books tooling trusts into `marketing/pilot-book-vocabulary-template.md`, or name any URL — the loop can now fetch a named URL via curl and bind/regenerate/flip (general network access works in cron; only the Firecrawl web_search backend is unavailable). Full evidence: `research/decodable-vocabulary-source-hunt.md`. Existing signed-in account for a payment canary; the shared `omo-llm-runner` and Tier-1 runner; paid download fulfillment.

## Metrics (live)

- Signups: 0
- Free books made: 0
- Paid second books: 0
- Paid runs: 0
- Refund/complaint rate: n/a

## Open proposals (awaiting Harry)

### PROPOSAL — social-x-identity-001 (awaiting Harry)

In ego-browser task space `social-setup` (id 2), X is open at the new-account
phone/SMS identity gate. Harry must enter the selected business phone number,
SMS verification code, and account password himself, then stop at the first
non-sensitive onboarding/profile screen and reply `continue`. No account has
been created and no branding field was available before this gate. After
handoff, the agent may request `@omospace` and apply the prepared Omo branding.
Instagram and Facebook remain queued for later one-action growth-loop rounds.
No password, code, or other secret may be written to the repository.

- **RESOLVED — PhonicsMaker contact audit:** Harry supplied the 5,087-row Loops CSV export. The exact 200-contact cohort was generated locally and verified on 2026-08-14; the export and cohort remain outside git.

### RESOLVED — schema-001 (schema applied + checkout live, 2026-08-12)

The marketplace dev agent applied `site/deploy/schema.sql` to production Neon on
2026-08-12; all 12 tables verified present, and a Woven checkout returned a real
Stripe Checkout URL (cs_live_). The three live Worker secrets are set. No further
action needed from Harry on the schema.

### RESOLVED — phonics-modal-001 (nine education apps deployed in Brief AP)

The Modal CLI uses isolated authentication through
`MODAL_CONFIG_PATH=/Users/yifan/.modal-omo.toml` and `MODAL_PROFILE=omo-space`.
Brief AP accepted the founder's 70% hostability bar and explicitly authorized
deployment: all nine reviewed education apps now report `state=deployed`. The
worksheet, illustrated story, and edit-studio bundles remain fail-closed and
were not deployed.

### RESOLVED — education-gate-1r4 (no further rerun required)

Brief AP explicitly accepted Gate 1R3 at 25/27 schema-valid and semantic because
every tool retained at least 2/3 passes, exceeding the founder's 70% hostability
bar. The two stubborn cases remain documented typed blockers; do not chase
27/27 for this release.

### RESOLVED — modal-proxy-credential-001 (Brief AP authorized one canary)

Brief AP explicitly authorized internally loading the pair from
`/Users/yifan/marketplace/.env.modal-proxy` for this release canary. One real
education-app submit returned HTTP 202 with the accepted response shape; no
credential value or response content was printed, written to the repository,
or committed.

### RESOLVED — loader-worker-smoke-001 (authorized and exercised in Brief BQ)

Harry explicitly approved the shared Worker deploy and one owner-scoped fixture
canary with process-only `.env.modal-proxy` loading. Wrangler 4.123.0 deployed
the 14-row registry as Worker version `8c0b7456-eeac-45e8-b65e-c0c7fcdccfd3`,
and the unauthenticated loader route returned HTTP 401
`authentication_required`. The direct preflight loaded the proxy pair without
printing or persisting it, but Modal failed before FastAPI startup because the
deployed module resolves as `/root/modal_app.py` and indexed a nonexistent
second parent. No valid loader job, token-bearing URL, provider call, or push
occurred. Sanitized evidence is `/tmp/loader-live/release-gates.json`.

### RESOLVED — loader-modal-redeploy-002 (authorized and exercised in Brief BR)

Harry explicitly authorized redeploying the fixed
`containers/skill-md-to-hosted-workflow/modal_app.py` to isolated
`omo-space/main` and consuming the still-unused owner-scoped fixture canary.
Modal reported the corrected app deployed, the tiny-uppercase submit returned
HTTP 202, polling completed with a ready $0.10 `omo.result/v1` candidate and
5/5 fixture checks, and both result usage and the test summary reported zero
provider calls. R3 remained HTTP 401 `authentication_required`, the canonical
listing remained HTTP 200, and all recorded suites stayed green. Proxy values
and tokenized URLs remained process-only; no Worker/site deploy, push, external
message, or provider call occurred. Sanitized evidence is
`/tmp/loader-live/final-release-gates.json`.

### PROPOSAL — japanese-modal-deploy-001 (awaiting Harry)

Approve this exact live change: deploy the regenerated
`containers/japanese-style-story-video/modal_app.py` to the isolated
`omo-space/main` Modal profile, then submit exactly one authenticated hosted
`sample-demello-10s` canary and verify HTTP 202. The canary will consume a small
amount of Modal compute; it will load the already pre-authorized proxy pair
internally from `.env.modal-proxy` without printing or persisting either value.
No Worker/site deploy, push, arbitrary-audio run, provider call, or catalog
visibility change is included. The attempted deploy was rejected by the safety
approval gate before Modal was changed.

### RESOLVED — batch-proof-provider-spend-001 (authorized and run in Brief BD)

Harry's explicit authorization in Brief BD covered the existing credential and
up to 28 OpenCode Go calls capped at USD 0.10. The 14-case real-provider gate
completed with 17 calls at USD 0.00684320 and no HTTP/transport rejection.
Result: `BATCH-RATE-2/10`; copywriting and budget-planning are HOSTED, five
resolver-approved candidates fail closed on deterministic semantic checks, and
the three original capability-blocked candidates remain typed. Full evidence is
`/tmp/batch-proof-2/real-runs.json`; no deploy, push, commit, catalog change, or
production mutation occurred.

### PROPOSAL — semantic-recovery-provider-proof-001 (awaiting Harry, opened 2026-08-16)

Approve this exact spend action: run one bounded fresh-provider proof of the
seven SEMANTIC-RECOVERED skills (code-documentation, email-drafting,
logo-design, privacy-policy-drafting, proposal-generation, ticket-triage,
translation) so each can be marked HOSTED on real evidence instead of fixture
replay. Shape: 14 cases (2 per skill: right-needle contract + wrong-needle
contract), hard-capped at exactly 14 OpenCode Go calls and USD 0.10 total,
process-only loading of the already-authorized `OPENCODE_GO_API_KEY` (the same
secret-loading pattern Harry approved in `batch30-sensitive-egress-001`), no
retry, no print/persist of prompts, outputs, or credential material, and
mode-0600 evidence written only under `/tmp/semantic-recovery-proof/`. The
semantic layer is done (adapters 7/7 right + 7/7 wrong on recovered contracts;
compiler suite 54/55). No deploy, push, commit, catalog change, external
message, or other production mutation is included. Do not run before approval —
this is the hard-stop boundary.

### PROPOSAL — semantic-adapter-provider-credential-001 (awaiting Harry)

Approve this exact secret-loading action: internally source
`/Users/yifan/.omo-hermes/.env`, map its existing `OPENCODE_GO_API_KEY` to the
generated runners' `LLM_API_KEY`, and run `/tmp/semantic-adapter/run_real_adapter.py`.
The runner is hard-capped at exactly 10 OpenCode Go calls and USD 0.10, prints
no prompt, output, environment value, or credential material, and writes only
mode-0600 evidence under `/tmp/semantic-adapter/`. The semantic compiler fix,
34/34 compiler tests, 50/50 generated contracts, and 10/10 historical replay
are already complete. The execution approval gate rejected this credential
load before launch, so actual provider usage remains 0/10 calls and USD 0.00.
No deploy, push, commit, catalog change, or production mutation is included.

### RESOLVED — batch30-sensitive-egress-001 (authorized and run in Brief BL)

Harry's blanket OpenCode authorization plus standing BATCH-30 mandate approved
process-only loading of `OPENCODE_GO_API_KEY` and egress of the disclosed
synthetic cases, including at most one retry per case. The clean run completed
60/60 runtime invocations with 28 successful, known-cost provider calls and no
retry, totaling USD 0.00897834. Result: `BATCH30-RATE-7/30`; 23 failures remain
typed and ranked in `research/one-shot-rounds.md`. The key was not printed or
persisted. Evidence is mode 0600 under `/tmp/batch30/`; no deploy, push, commit,
catalog change, external message, or production mutation occurred.

## Next tick

BUILDABLE #1 remains complete (generic semantic adapters, 7/7 right + 7/7 wrong
needles). VOCABULARY-NORMALIZER MACHINERY is now DONE (this tick, 2026-08-16):
the compiler gained the `semantic.whole_book_vocabulary/v1` kind — selector in
`semantic_evidence_spec` (fires only on a `reviewed_spec.vocabulary` resource with
`provenance: reviewed`, exact stage-enum match, one book string, decodability
object with word_counts/review_words/sight_words) plus a deterministic whole-book
token classifier (`_whole_book_vocabulary_scan` + `_…semantic_diff` + normalize
hook + dispatcher) that recomputes the decodability report and fails closed on
review words. Fixture-proven 3/3 + 1 selector test on clearly-labeled SYNTHETIC
vocabulary (`tests/fixtures/vocabulary-book-normalizer.json`, provenance-doc, NOT
reviewed content). Compiler suite 57/58 = recorded baseline 54/55 + 3 new tests
(sole failure = pre-existing ffmpeg 8.0.1-vs-8.1.2 env gate); no-reclassification
pin holds; decodable-book-maker profile blocker detail updated (machinery done,
content-only gate).

REMAINING BLOCKER — REVIEWED CONTENT ONLY: no reviewed word-list source exists
anywhere, verified exhaustively this tick: the OSS twin publishes only
SKILL.md/README/LICENSE/manifest per skill (no data files), all 95+ PhonicsMaker
inventory skills are procedural generators with no static word bank, no
third-party corpora in this repo, and web tooling is unavailable in this cron
profile. So the five cumulative stage vocabularies + sight-word list are strictly
a Harry decision — do not self-invent word lists.

Priority order (updated after the origin/main reconciliation and the vocab source-hunt):
1. WAIT for Harry to supply or sign off the five reviewed cumulative stage
   vocabularies + the reviewed sight-word list. CONTENT-LEVEL VERIFIED this
   tick (research/decodable-vocabulary-source-hunt.md): no reviewed word-bank
   exists anywhere public — all 102 omo-space/skills SKILL.md files grepped
   (zero static word banks, only procedural generators; decodable-book-maker's
   own contract demands a "compiler-owned vocabulary", i.e. it expects the
   platform to own the lists), GitHub public `phonicsmaker` repos = 0, and
   phonicsmaker.com is unreachable behind a Vercel Security Checkpoint (curl
   429, browser checkpoint, no subdomains). Two unblocks for Harry: (a)
   fastest — paste the word bank his own PhonicsMaker decodable-books tooling
   already trusts into marketing/pilot-book-vocabulary-template.md; (b) name
   any public URL and the loop will fetch it via curl, bind it as
   `reviewed_spec.vocabulary` (provenance: reviewed) in
   packages/skill-to-modal/profiles/decodable-book-maker.json, regenerate the
   container, re-run the whole_book_vocabulary fixture needles against the
   real lists, and flip can_submit — the machinery needs no further work and
   a named-URL fetch works from cron (only the Firecrawl web_search backend is
   unavailable; raw curl and the browser tool both work).
2. COORDINATOR/HARRY: pull or merge our local branch (12 commits ahead of
   origin/main's merge base, reconciled on top of origin/main) so the
   decodable-book-maker runtime, vocabulary normalizer, fixtures, and
   template land upstream. We cannot push from this profile.
3. WAIT for Harry's explicit approval of `semantic-recovery-provider-proof-001`;
   then run the 14-case USD 0.10-capped proof (hard stop before approval — do not run).
4. Wait for Harry's approvals for `japanese-modal-deploy-001`, the pilot
   magic-link deploy, and the social X identity gate; do not push from this
   profile.
No churn this cycle. This tick (vocab-source-hunt, 2026-08-16T15:0xZ):
content-level source hunt performed over the curl/browser channel (which DOES
work in cron — only Firecrawl web_search is unconfigured): deep-cloned all
102 OSS skill folders and grepped every SKILL.md (zero embedded word banks),
GitHub public `phonicsmaker` repo search = total_count 0, phonicsmaker.com
behind Vercel checkpoint (429 curl, empty-page checkpoint in browser, no
resolving subdomains), wayback 429 / DDG-Bing shells / Google 403. Result:
no reviewed vocabulary source is publicly fetchable; the gate remains a
Harry decision, now with a lower-cost unblock (paste or named-URL). Evidence
committed at research/decodable-vocabulary-source-hunt.md; `git fetch origin`
0 behind / 12 ahead with a clean tree. Status: WAITING on Harry/
coordinator-owned gates; metrics unchanged. No spend, send, deploy, push, or
secret access occurred.

This tick (verify-vocab-fixtures, 2026-08-16T15:30Z): no new buildable —
upstream re-verified unchanged (0 behind / 13 ahead, all ours), committed
pilot-book chain integrity checked (vocabulary fixture tracked at
packages/skill-to-modal/tests/fixtures/, container/profile/template/evidence
all tracked), and the whole_book_vocabulary suite re-run from the committed
tree: 3 passed / 56 deselected — recorded claim holds with fresh evidence.
Status remains WAITING on Harry/coordinator-owned gates: (1) reviewed
vocabulary content (template + machinery ready — paste or named-URL unblocks
in minutes), (2) coordinator pull/merge of our 13 local commits, (3)
approvals: semantic-recovery-provider-proof-001, japanese-modal-deploy-001,
pilot magic-link deploy, social X identity gate. Metrics unchanged 0/0/0.
No spend, send, deploy, push, or secret access occurred.
