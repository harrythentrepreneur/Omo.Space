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

- State: production payment loop is LIVE (per the marketplace dev agent's session, 2026-08-12) — the additive Neon schema is applied (all 12 tables), the three live Worker secrets (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, NEON_DATABASE_URL) are set, and a Woven checkout returned a real Stripe Checkout URL. The local release state now has a reversible 14-listing whitelist: the existing four listings, nine ready education tools, and the ready $5/run Skill.md loader; the coordinator still owns the production push.
- Done: marketing plan (sol), payment-loop spec + pilot email, loop harness, payment-loop gap audit, fast signup-grant visibility, live secrets/routes, request-safe Neon access, 10/10 unauthenticated live canary, checkout orphan-session expiry, 24-listing honesty audit, four text-free phonics marketplace thumbnails, and 12 locally compiled/tested/priced PhonicsMaker workflow bundles.
- Pilot cohort: the exact 200-contact GATE 1 cohort is built from the 5,087-row Loops export at the protected Hermes data path; it contains 182 intent+segment contacts and 18 segment-fill contacts, excludes unsubscribed/junk/current-active-subscriber rows, and passes count, format, uniqueness, and subscription checks. No email was sent.
- Modal isolation: the account topology is `harrythentrepreneur`, `phonicsmaker`, and `omo-space`; the user-local Modal CLI 1.5.0 launcher is authenticated only through the owner-only `/Users/yifan/.modal-omo.toml`. The nine education apps are deployed in `omo-space/main` and each reports `state=deployed`; no PhonicsMaker resource was opened or changed.
- Education hosting release: the founder accepted the 70% hosted-success bar and Gate 1R3 provides 25/27 schema-valid plus 25/27 semantic runs, with every one of the nine tools retaining at least 2/3 passes. All nine are now generated, registered, priced at $0.10, deployed, chargeable, and locally activated; the two known limits remain typed, fail-closed catalog disclosures. A real authenticated education-app POST returned HTTP 202 with the accepted run shape. Exact suites pass compiler 20/20, host 82/82, generated containers 99/99, Worker helpers 17/17, and router 173/173.
- Creator builder infrastructure: issue #63 moved creator-build dispatch off Hetzner through Cloudflare cron -> protected Modal endpoint -> Worker-authoritative atomic claim -> one revision/source-bound ephemeral Hermes build. Issues #65/#67 add recovery and safe failure stages; issue #69 repairs immutable-checkout processor sibling imports. Full issue/PR canary evidence is still pending.
- Artifact runtime: a shared deterministic ReportLab renderer, owner-scoped immutable local artifact store, no-refresh Codex subscription image bridge, exact contract/integration notes, and real-PDF smoke test now exist under `tools/render/` for the worksheet, illustrated-story, and edit-studio workflows; targeted renderer/adapter/compiler/host tests are green, with no registration or deployment.
- Woven builder-capability release: the shared compiler now materializes default-off `book_pdf` artifacts and bounded `whatsapp_zip` input adapters; Woven 0.3.0 was regenerated from its reviewed profile, registered at $0.40, deployed to `omo-space` with `state=deployed`, and proven with a real two-pass WhatsApp ZIP run producing a visually verified five-page signed keepsake PDF. The clean staged snapshot passes compiler 22/22, Woven 20/20, host 77/77, and renderer 9/9 (128/128); the current worktree including concurrent host/renderer tests passes 158/158. Catalog and listing copy are locally republished, with no push.
- Japanese media-executor candidate: the compiler now materializes the reviewed de Mello procedural sumi-e modules and bundled 10-second audio as a slug-locked skill-owned resource, generating a ready/chargeable owner-scoped async runtime at $0.10. A real local run produced and full-decoded a 10.000-second 1080x1920 H.264/AAC MP4 with 30 generated frames, 300 output frames, five exact-digest artifacts, zero provider spend, and $0.00061482 measured compute; compiler 28/28, host 88/88, container contracts 361/361, render 34/34, Worker helpers 17/17, cost 11/11, and router 180/180 pass. The live Modal deploy and hosted 202 smoke remain blocked on Harry's explicit specific approval; arbitrary audio remains rejected before work.
- Skill.md loader release: the deterministic build/analysis service is generated from a compiler-owned profile/resource, uses proxy-authenticated owner-scoped async endpoints, compiles explicit machine contracts through the canonical compiler, runs five fixture-only checks with zero provider calls, and fails closed on typed blockers or unknown cost. R1 proves one loader runtime row in the 14-row registry; R2 deployed Worker version `8c0b7456-eeac-45e8-b65e-c0c7fcdccfd3`; and R3 returns `authentication_required`, not `unknown_catalog_slug`. Under founder authorization `loader-modal-redeploy-002`, the compiler-owned import fix was redeployed to `omo-space/main` and the one owner-scoped tiny-uppercase fixture canary returned HTTP 202 then completed `ready` at $0.10 with 5/5 checks and `provider_calls: 0`. The local listing remains active/chargeable at $5/run, the canonical live URL returns HTTP 200, and suites pass 154 Python, 183 router, 17 Worker-parser, 22 billing, 11 cost, and 19 support checks. Sanitized evidence is `/tmp/loader-live/final-release-gates.json`; public static activation still awaits the coordinator push.
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
- Next: (1) coordinator pushes the local loader/catalog/listing plus corrective-fix commits and verifies the 14 production cards; (2) obtain Harry's explicit specific approval for the isolated Japanese Modal deploy and canary; (3) re-run an authenticated top-up + Woven checkout canary to confirm the live payment loop; (4) move Omo onto its own Stripe account; (5) rotate the live sk exposed in chat; (6) build the magic-link free-book grant; (7) obtain Harry's explicit approval before any pilot email send.
- Blockers: the public static loader activation awaits the coordinator-owned push. Japanese Style Story Video's regenerated app separately awaits its exact live-change approval; Stripe LIVE runs on the shared PhonicsMaker Stripe account; a live sk was exposed in chat (rotation pending); magic-link free-book grant not built; existing signed-in account for a payment canary; the shared `omo-llm-runner` and Tier-1 runner; paid download fulfillment.

## Metrics (live)

- Signups: 0
- Free books made: 0
- Paid second books: 0
- Paid runs: 0
- Refund/complaint rate: n/a

## Open proposals (awaiting Harry)

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

First obtain approval for `loader-modal-redeploy-002` and finish the blocked
direct loader canary. For builder breadth, implement the reusable semantic evidence adapters for the
remaining schema-valid skills; the tabular domain orchestrator family and
data-analysis endpoint routing are fixture-complete. Founder-desk holds remain
the bounded search backend key, isolated safe-exec design, and image-generation
provider approval. Separately, wait for Harry's explicit approval of
`japanese-modal-deploy-001`; do not push from this profile.
