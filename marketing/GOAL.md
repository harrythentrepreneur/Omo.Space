# Omo Growth Loop — GOAL.md (goal contract + live state)

North star: $100,000 in a single day of Omo revenue.
Honest path: GATE 1 (prove a teacher pays twice) -> $1k/mo -> $10k/mo -> scale.

## Current goal (contract)

Clear GATE 1 of the Omo pilot.

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

- State: tick-001 audit done. Payment loop is ~80% built in code — not a greenfield build.
- Done: marketing plan (sol), payment-loop spec + pilot email, loop harness, payment-loop gap audit (marketing/payment-loop-gap.md), fast signup-grant visibility with authoritative retry.
- Next: (1) Kaviru/Harry set 3 live secrets (Stripe sk_live + webhook + Neon URL) and route omo.space/api/* to the Worker; (2) run canaries; (3) build the magic-link free-book grant; (4) Harry pulls the 200-person segment.
- Blockers: live Stripe/Neon secrets; Worker route + canary; magic-link feature; 200-segment.

## Metrics (live)

- Signups: 0
- Free books made: 0
- Paid second books: 0
- Paid runs: 0
- Refund/complaint rate: n/a

## Open proposals (awaiting Harry)

(none yet)

## Next tick

Check pilot infra status. If the payment loop is not shipped, work only on pieces that need no Harry and no external send/spend (e.g. verify site trust items, prep the exact segment query). Otherwise record "waiting on Kaviru/Harry" and stop.
