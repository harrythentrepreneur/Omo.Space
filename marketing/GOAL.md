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

- State: payment infrastructure is deployed fail-closed; the storefront now reads one 120-listing catalog, but production is still missing the additive payment/upload tables.
- Done: marketing plan (sol), payment-loop spec + pilot email, loop harness, payment-loop gap audit, fast signup-grant visibility, live secrets/routes, request-safe Neon access, 10/10 unauthenticated live canary, checkout orphan-session expiry, 24-listing honesty audit, four text-free phonics marketplace thumbnails, and 12 locally compiled/tested/priced PhonicsMaker workflow bundles.
- Modal isolation: the account topology is `harrythentrepreneur`, `phonicsmaker`, and the new `omo-space`; the user-local Modal CLI 1.5.0 launcher is authenticated only through the owner-only `/Users/yifan/.modal-omo.toml`, and an isolated `omo-space/main` app listing returned empty. The legacy `~/.modal.toml` remained byte-identical; no PhonicsMaker resource was opened or changed, and nothing was registered or deployed.
- Artifact runtime: a shared deterministic ReportLab renderer, owner-scoped immutable local artifact store, no-refresh Codex subscription image bridge, exact contract/integration notes, and real-PDF smoke test now exist under `tools/render/` for the worksheet, illustrated-story, and edit-studio workflows; targeted renderer/adapter/compiler/host tests are green, with no registration or deployment.
- OSS skills library: all 95 publishable workflows in the 96-tool PhonicsMaker inventory now have public twins in `omo-space/skills`; 85 new skill/README pairs were published atomically in `ab02e824`, all 84 prompt-only tools remain honest draft specs and the story editor remains in review, and the pre-existing private illustrated-story skill was not changed. The library has 97 folders including the separate worksheet skill.
- Strategy artifact: researched and ranked 25 education-SaaS targets in `marketing/edtech-kill-list.md`; first ship queue is Diffit, MagicSchool, Twee, Formative, then Kahoot feature outcomes.
- Category-expansion artifact: researched Education, E-commerce, real-estate listing media, short-form content repurposing, and recruiting/career documents in `marketing/category-expansion.md`; direct per-product, per-image, and metered-result pricing supports that rank order, with E-commerce as the first post-Education test.
- Creator research artifact: ranked 40 verified-or-explicitly-flagged prospects in `marketing/creator-dm-list.md`, led by creators who already demonstrate Diffit, MagicSchool, Twee, Formative, or Kahoot; no outreach was sent.
- Outreach/review drafts: first-wave ranks 1–8 have audience-first DM copy, and the first three PhonicsMaker proof-page skills have a repeatable named-educator review protocol; no outreach or publication was made.
- Unified catalog: `site/catalog.js` now contains the 24 preserved live-priced listings plus 96 PhonicsMaker previews with human-readable names, promises, and fail-closed `Coming soon` state; 95 previews use exact v5 thumbnails and `phonics-story-editor` uses the existing visual fallback because no matching v5 file exists.
- Storefront cleanup: the separate catalog browser, homepage promo/link, projection data, stale 100-item inventory, and import tooling are removed; listing, dashboard, workflow, run, nav, library, host tooling, and MCP reads now converge on the single catalog without changing Worker auth or payment wiring.
- Storefront visibility: every storefront render and direct-detail surface now uses a reversible two-slug whitelist for Japanese Style Story Video and Woven Relationship Book Maker; all 220 catalog objects remain intact, and registry/MCP tooling still reads the full catalog.
- Next: (1) Harry applies the full `site/deploy/schema.sql`; (2) re-run Woven checkout for HTTP 200 plus expiry and an authenticated top-up canary; (3) build the magic-link free-book grant; (4) Harry pulls the 200-person segment.
- Blockers: production `purchases`/top-up/submissions schema; existing signed-in account for authenticated canary; paid download fulfillment; magic-link feature; 200-segment; the shared `omo-llm-runner`; the Tier-1 shared runner; chargeable activation/provider canaries; and reviewed production artifact storage, pricing, and workflow-specific content/moderation/educator acceptance evidence for the three imported heavy PhonicsMaker workflows.

## Metrics (live)

- Signups: 0
- Free books made: 0
- Paid second books: 0
- Paid runs: 0
- Refund/complaint rate: n/a

## Open proposals (awaiting Harry)

- **PhonicsMaker contact audit is blocked:** the public Loops REST API has no bulk contact read endpoint. The discovered `/api/v1/zapier/list/mailingListContact` route returns only five unpaginated webhook events, not current list membership. Provide a Loops CSV export of both target lists (with custom properties) or a confirmed read-only bulk endpoint before generating the pilot segment.

### PROPOSAL schema-001 — apply the additive production schema

From `/Users/yifan/marketplace`, securely provide `NEON_DATABASE_URL` and run
`psql "$NEON_DATABASE_URL" -f site/deploy/schema.sql`, or run it personally.
Then verify `purchases`, `topup_sessions`, `stripe_events`, `stripe_topups`, and
`submissions` exist. Do not paste the connection string into chat or history.

### PROPOSAL phonics-modal-001 — approve any future Modal registration/deploy separately

The Modal CLI is installed and the new `omo-space` workspace has isolated,
verified authentication through `MODAL_CONFIG_PATH=/Users/yifan/.modal-omo.toml`
and `MODAL_PROFILE=omo-space`; its `main` app list is empty. No registration or
deployment was attempted. Only after Harry gives separate explicit approval,
run the nine reviewed single-LLM `host.py --register` gates and actual Modal
deploy/canary steps. Do not deploy the worksheet, illustrated story, or
edit-studio bundles while their profiles remain fail-closed.

## Next tick

Wait for schema-001. Once Harry confirms it, prove one Woven checkout returns a
Stripe URL and expire it, then use an existing signed-in test account for one
top-up session canary. Do not charge, send, or broaden the pilot.
