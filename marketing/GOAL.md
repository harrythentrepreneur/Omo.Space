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

- State: payment infrastructure is deployed fail-closed; Stripe/routing work, but production is missing the additive payment/upload tables.
- Done: marketing plan (sol), payment-loop spec + pilot email, loop harness, payment-loop gap audit, fast signup-grant visibility, live secrets/routes, request-safe Neon access, 10/10 unauthenticated live canary, checkout orphan-session expiry, 24-listing honesty audit, four text-free phonics marketplace thumbnails, and 12 locally compiled/tested/priced PhonicsMaker workflow bundles.
- Local OSS prep: three complete skill directories are staged under oss/ for later publication; phonics-book-maker remains unprepared because the requested source path is missing.
- Strategy artifact: researched and ranked 25 education-SaaS targets in `marketing/edtech-kill-list.md`; first ship queue is Diffit, MagicSchool, Twee, Formative, then Kahoot feature outcomes.
- Creator research artifact: ranked 40 verified-or-explicitly-flagged prospects in `marketing/creator-dm-list.md`, led by creators who already demonstrate Diffit, MagicSchool, Twee, Formative, or Kahoot; no outreach was sent.
- Next: (1) Harry applies the full `site/deploy/schema.sql`; (2) re-run Woven checkout for HTTP 200 plus expiry and an authenticated top-up canary; (3) build the magic-link free-book grant; (4) Harry pulls the 200-person segment.
- Blockers: production `purchases`/top-up/submissions schema; existing signed-in account for authenticated canary; paid download fulfillment; magic-link feature; 200-segment; Modal CLI/authentication for nine ready PhonicsMaker single-LLM deployments; unresolved artifact/image/PDF capabilities for the other three PhonicsMaker workflows.

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

### PROPOSAL phonics-modal-001 — enable the reviewed Modal deployment gate

Provide an environment with the Modal CLI installed and authenticated, then
rerun `modal config show`. Only after that succeeds, run the nine reviewed
single-LLM `host.py --register` gates and actual Modal deploy/canary steps. Do
not deploy the worksheet, illustrated story, or edit-studio bundles while their
profiles remain fail-closed.

## Next tick

Wait for schema-001. Once Harry confirms it, prove one Woven checkout returns a
Stripe URL and expire it, then use an existing signed-in test account for one
top-up session canary. Do not charge, send, or broaden the pilot.
