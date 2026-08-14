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

- State: production payment loop is LIVE (per the marketplace dev agent's session, 2026-08-12) — the additive Neon schema is applied (all 12 tables), the three live Worker secrets (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, NEON_DATABASE_URL) are set, and a Woven checkout returned a real Stripe Checkout URL. The local release state now has a reversible 13-listing whitelist: the existing four listings plus nine ready, chargeable education tools; the coordinator still owns the production push.
- Done: marketing plan (sol), payment-loop spec + pilot email, loop harness, payment-loop gap audit, fast signup-grant visibility, live secrets/routes, request-safe Neon access, 10/10 unauthenticated live canary, checkout orphan-session expiry, 24-listing honesty audit, four text-free phonics marketplace thumbnails, and 12 locally compiled/tested/priced PhonicsMaker workflow bundles.
- Pilot cohort: the exact 200-contact GATE 1 cohort is built from the 5,087-row Loops export at the protected Hermes data path; it contains 182 intent+segment contacts and 18 segment-fill contacts, excludes unsubscribed/junk/current-active-subscriber rows, and passes count, format, uniqueness, and subscription checks. No email was sent.
- Modal isolation: the account topology is `harrythentrepreneur`, `phonicsmaker`, and `omo-space`; the user-local Modal CLI 1.5.0 launcher is authenticated only through the owner-only `/Users/yifan/.modal-omo.toml`. The nine education apps are deployed in `omo-space/main` and each reports `state=deployed`; no PhonicsMaker resource was opened or changed.
- Education hosting release: the founder accepted the 70% hosted-success bar and Gate 1R3 provides 25/27 schema-valid plus 25/27 semantic runs, with every one of the nine tools retaining at least 2/3 passes. All nine are now generated, registered, priced at $0.10, deployed, chargeable, and locally activated; the two known limits remain typed, fail-closed catalog disclosures. A real authenticated education-app POST returned HTTP 202 with the accepted run shape. Exact suites pass compiler 20/20, host 82/82, generated containers 99/99, Worker helpers 17/17, and router 173/173.
- Artifact runtime: a shared deterministic ReportLab renderer, owner-scoped immutable local artifact store, no-refresh Codex subscription image bridge, exact contract/integration notes, and real-PDF smoke test now exist under `tools/render/` for the worksheet, illustrated-story, and edit-studio workflows; targeted renderer/adapter/compiler/host tests are green, with no registration or deployment.
- Woven builder-capability release: the shared compiler now materializes default-off `book_pdf` artifacts and bounded `whatsapp_zip` input adapters; Woven 0.3.0 was regenerated from its reviewed profile, registered at $0.40, deployed to `omo-space` with `state=deployed`, and proven with a real two-pass WhatsApp ZIP run producing a visually verified five-page signed keepsake PDF. The clean staged snapshot passes compiler 22/22, Woven 20/20, host 77/77, and renderer 9/9 (128/128); the current worktree including concurrent host/renderer tests passes 158/158. Catalog and listing copy are locally republished, with no push.
- Japanese media-executor candidate: the compiler now materializes the reviewed de Mello procedural sumi-e modules and bundled 10-second audio as a slug-locked skill-owned resource, generating a ready/chargeable owner-scoped async runtime at $0.10. A real local run produced and full-decoded a 10.000-second 1080x1920 H.264/AAC MP4 with 30 generated frames, 300 output frames, five exact-digest artifacts, zero provider spend, and $0.00061482 measured compute; compiler 28/28, host 88/88, container contracts 361/361, render 34/34, Worker helpers 17/17, cost 11/11, and router 180/180 pass. The live Modal deploy and hosted 202 smoke remain blocked on Harry's explicit specific approval; arbitrary audio remains rejected before work.
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
- Storefront visibility: every storefront render and direct-detail surface now uses a reversible 13-slug whitelist containing the existing four listings plus the nine education tools. Local Chromium renders 13/13 cards on both homepage and dashboard; `skill-md-to-hosted-workflow` remains preserved but intentionally excluded for coordinator activation.
- SEO sitemap visibility: the prerender generator reads `OMO_VISIBLE_SLUGS` at build time, so `site/sitemap.xml` contains the 13 visible workflow slugs plus seven core pages; all 222 prerendered workflow directories remain on disk.
- Next: (1) obtain Harry's explicit specific approval for `modal deploy containers/japanese-style-story-video/modal_app.py` to the isolated `omo-space` profile and one authenticated 202 smoke using the pre-authorized proxy pair; (2) coordinator pushes the local `SHIPPED-13-READY` plus Woven builder-capability commits and verifies the 13 production cards, Woven copy, and deployed Worker registry; (3) coordinator activates the preserved builder listing separately; (4) re-run an authenticated top-up + Woven checkout canary to confirm the live payment loop; (5) move Omo onto its own Stripe account; (6) rotate the live sk exposed in chat; (7) build the magic-link free-book grant; (8) obtain Harry's explicit approval before any pilot email send.
- Blockers: Japanese Style Story Video's regenerated app cannot be deployed or canaried until Harry explicitly approves that exact live infrastructure change; its hosted input remains intentionally pinned to the bundled 10-second sample and arbitrary audio remains unpriced. The broader local release awaits the coordinator-owned push; Stripe LIVE runs on the shared PhonicsMaker Stripe account (account-level branding off-limits; conflicts with a PhonicsMaker sale); a live sk was exposed in chat (rotation pending); magic-link free-book grant not built; existing signed-in account for a payment canary; the shared `omo-llm-runner` and Tier-1 runner; paid download fulfillment.

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

## Next tick

Wait for Harry's explicit approval of `japanese-modal-deploy-001`; then deploy
only the generated Japanese app and run the single bounded 202 smoke. Otherwise
hand the local `SHIPPED-13-READY` and Woven builder-capability commits to the
coordinator for push, production 13-card/Worker-registry and Woven listing-copy
verification, and separate activation of the preserved builder listing. Do not
push from this profile.
