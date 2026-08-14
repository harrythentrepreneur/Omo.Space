# Omo Growth Loop — GOAL.md (goal contract + live state)

North star: $100,000 in a single day of Omo revenue.
Honest path: GATE 1 (prove a teacher pays twice) -> $1k/mo -> $10k/mo -> scale.

## Current goal (contract)

Get Omo to $1,000/month contribution margin. Immediate step: clear GATE 1 of the Omo pilot.

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

- State: production payment loop is LIVE (per the marketplace dev agent's session, 2026-08-12) — the additive Neon schema is applied (all 12 tables), the three live Worker secrets (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, NEON_DATABASE_URL) are set, and a Woven checkout returned a real Stripe Checkout URL. The storefront is now pinned to a reversible two-listing whitelist (Japanese Style Story Video + Woven Relationship Book Maker); all 220 catalog objects remain intact.
- Done: marketing plan (sol), payment-loop spec + pilot email, loop harness, payment-loop gap audit, fast signup-grant visibility, live secrets/routes, request-safe Neon access, 10/10 unauthenticated live canary, checkout orphan-session expiry, 24-listing honesty audit, four text-free phonics marketplace thumbnails, and 12 locally compiled/tested/priced PhonicsMaker workflow bundles.
- Pilot cohort: the exact 200-contact GATE 1 cohort is built from the 5,087-row Loops export at the protected Hermes data path; it contains 182 intent+segment contacts and 18 segment-fill contacts, excludes unsubscribed/junk/current-active-subscriber rows, and passes count, format, uniqueness, and subscription checks. No email was sent.
- Modal isolation: the account topology is `harrythentrepreneur`, `phonicsmaker`, and the new `omo-space`; the user-local Modal CLI 1.5.0 launcher is authenticated only through the owner-only `/Users/yifan/.modal-omo.toml`, and an isolated `omo-space/main` app listing returned empty. The legacy `~/.modal.toml` remained byte-identical; no PhonicsMaker resource was opened or changed, and nothing was registered or deployed.
- Education hosting gate: Gate 1R3 regenerated the nine 0.2.3 runtimes with target-word containment, a reviewed weak-evidence denylist, and syllable spelling/separator validation. The unchanged 27 real-provider cases reached 25/27 schema-valid and 25/27 semantic at USD 0.00348992 of wrapper-reported successful-run cost; every tool retained at least two semantic passes, but phonics-list #2 and syllable #3 failed closed after their bounded retries. The 27/27 schema release requirement failed, so no Modal deployment, marketplace activation, or hosted canary was attempted. The proxy preflight was not rerun because access to its separate credential file lacked explicit authorization; AL's prior 2/2 HTTP 200 remains historical evidence only. Every case and exact failure is recorded in `research/one-shot-rounds.md`.
- Artifact runtime: a shared deterministic ReportLab renderer, owner-scoped immutable local artifact store, no-refresh Codex subscription image bridge, exact contract/integration notes, and real-PDF smoke test now exist under `tools/render/` for the worksheet, illustrated-story, and edit-studio workflows; targeted renderer/adapter/compiler/host tests are green, with no registration or deployment.
- OSS skills library: all 95 publishable workflows in the 96-tool PhonicsMaker inventory now have public twins in `omo-space/skills`; 85 new skill/README pairs were published atomically in `ab02e824`, all 84 prompt-only tools remain honest draft specs and the story editor remains in review, and the pre-existing private illustrated-story skill was not changed. The library has 97 folders including the separate worksheet skill.
- Strategy artifact: researched and ranked 25 education-SaaS targets in `marketing/edtech-kill-list.md`; first ship queue is Diffit, MagicSchool, Twee, Formative, then Kahoot feature outcomes.
- Category-expansion artifact: researched Education, E-commerce, real-estate listing media, short-form content repurposing, and recruiting/career documents in `marketing/category-expansion.md`; direct per-product, per-image, and metered-result pricing supports that rank order, with E-commerce as the first post-Education test.
- Creator research artifact: ranked 40 verified-or-explicitly-flagged prospects in `marketing/creator-dm-list.md`, led by creators who already demonstrate Diffit, MagicSchool, Twee, Formative, or Kahoot; no outreach was sent.
- Outreach/review drafts: first-wave ranks 1–8 have audience-first DM copy, and the first three PhonicsMaker proof-page skills have a repeatable named-educator review protocol; no outreach or publication was made.
- Education launch content: a live-rule-checked Reddit channel plan plus four YouTube Shorts, four Instagram Reels, three lead-workflow copy blocks, and the first three review drafts are complete in `marketing/education-launch-content-plan.md`; all copy is gated on workflow activation, final pricing, educator review, and a same-day community-rule recheck, and nothing was posted or sent.
- Unified catalog: `site/catalog.js` now contains the 24 preserved live-priced listings plus 96 PhonicsMaker previews with human-readable names, promises, and fail-closed `Coming soon` state; 95 previews use exact v5 thumbnails and `phonics-story-editor` uses the existing visual fallback because no matching v5 file exists.
- Storefront cleanup: the separate catalog browser, homepage promo/link, projection data, stale 100-item inventory, and import tooling are removed; listing, dashboard, workflow, run, nav, library, host tooling, and MCP reads now converge on the single catalog without changing Worker auth or payment wiring.
- Storefront visibility: every storefront render and direct-detail surface now uses a reversible two-slug whitelist for Japanese Style Story Video and Woven Relationship Book Maker; all 220 catalog objects remain intact, and registry/MCP tooling still reads the full catalog.
- Next: (1) after Harry approves Gate 1R4, add profile-driven corrective guidance for complete replacement word lists and orthographic syllable parts, then rerun the unchanged 27-case provider gate once; (2) obtain explicit authorization to source the separate Modal proxy pair for preflight and the hosted canary; (3) push the two-listing visibility commit live; (4) re-run an authenticated top-up + Woven checkout canary to confirm the live loop; (5) move Omo onto its own Stripe account (LIVE is currently on the shared PhonicsMaker account); (6) rotate the live sk exposed in chat; (7) decide Japanese Style Story Video (audio fail-closed) vs Facebook Ads Copywriter for the second visible listing; (8) build the magic-link free-book grant; (9) obtain Harry's explicit approval before any pilot email send.
- Blockers: the education gate is 25/27 schema and semantic because phonics-list #2 ended its retry with only 1 of 10 reviewed `ai`/`ay` words and syllable #3 repeated spelling-altering transcriptions for all three words; fresh proxy preflight and the future hosted canary cannot access `.env.modal-proxy` without Harry's separate explicit authorization; Stripe LIVE runs on the shared PhonicsMaker Stripe account (account-level branding off-limits; conflicts with a PhonicsMaker sale); a live sk was exposed in chat (rotation pending); Japanese Style Story Video is audio fail-closed (hosted run pinned to the bundled 10s sample); magic-link free-book grant not built; existing signed-in account for an authenticated canary; the shared `omo-llm-runner` and Tier-1 runner; chargeable activation/provider canaries; paid download fulfillment.

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

### RESOLVED — phonics-modal-001 (conditional deploy approved in Brief AN; gate not passed)

The Modal CLI is installed and the new `omo-space` workspace has isolated,
verified authentication through `MODAL_CONFIG_PATH=/Users/yifan/.modal-omo.toml`
and `MODAL_PROFILE=omo-space`; its `main` app list is empty. No registration or
deployment was attempted. Brief AN explicitly approved the nine reviewed
single-LLM Modal deployments only after Gate 1 passes. Gate 1R3 failed, so that
conditional authorization was not exercised. Do not deploy the worksheet,
illustrated story, or edit-studio bundles while their profiles remain fail-closed.

### PROPOSAL education-gate-1r4 — approve one more unchanged provider rerun

Add only profile-driven corrective guidance for a complete replacement word
list and spelling-preserving orthographic syllable parts, keep the single
bounded retry, rerun the unchanged 27 cases once, and stop again unless schema
is 27/27, semantic is at least 24/27, and every tool retains a semantic pass.
Expected provider cost remains approximately USD 0.005.

### PROPOSAL modal-proxy-credential-001 — authorize the separate proxy pair

Explicitly authorize loading `MODAL_PROXY_TOKEN_ID` and
`MODAL_PROXY_TOKEN_SECRET` from `/Users/yifan/marketplace/.env.modal-proxy`
inside non-logging child processes for the required two read-only preflights
and, only after Gate 1 passes and deployment completes, one real hosted submit.

## Next tick

Wait for Harry's decisions on `education-gate-1r4` and
`modal-proxy-credential-001`. If approved, strengthen only the profile-driven
corrective guidance and rerun the exact same 27 provider cases once. Do not
deploy or activate the education wave unless schema is 27/27, semantic is at
least 24/27, and every tool retains at least one semantic pass.
