#!/bin/bash
# Omo Modal-hosting optimization ladder — 4 rounds, each with a FRESH sol context,
# each round reading ALL prior rounds' notes. Sequential by design.
set -e
cd /Users/yifan/marketplace
mkdir -p research/modal-optimization
OUT=research/modal-optimization

BASE_BRIEF=$(cat <<'EOF'
You are an elite infrastructure architect analyzing the OMO marketplace's Modal hosting plan with a FRESH context window.
GOAL: optimize and refine the plan to yield the best possible production result for a $100k-MRR AI workflow marketplace.

PRODUCT REALITY (the goal service):
- Omo (omo.best) = "Fiverr for the new age": buyers browse 21 AI-workflow helpers (UGC ads, product photos, SEO, Shopify ops, video), try a demo, then buy one-time (download files+prompts, $3-200) or pay per-use (API, we run it on our cloud).
- Pricing: 5x markup on cost (runPrice = max(cost*5, $0.10)); later dial back to 1.25x.
- Credits system: $10 free signup credits, runs debit the balance, Stripe top-ups (worker /api/topup, D1 balance).
- Worker (Cloudflare): /api/run (LLM demo), /api/checkout, /api/me, /api/topup, /api/clerk-webhook ($10 grant).
- The backend engine = workflows containerized on Modal (modal.com), activated via API, each with a typed INPUT->OUTPUT contract. Autopilot pipeline: discover (IG reel/GitHub) -> extract -> container spec -> deploy to Modal -> quality-test -> live.

MANDATORY READING (the current plan + artifacts):
1. research/modal-container-plan.md — THE plan (1200+ lines): container agent pipeline, SKILL.md->container bridge, workflow #1 walkthrough, autopilot, cost/scaling, 5-day build order, risks.
2. containers/ugc-heygen/ — async HeyGen UGC container (canary, 29 tests)
3. containers/claude-seo-skill/ — pure-LLM sync container (38 tests)
4. containers/gpt-image-seedance-ad/ — LLM + Modal GPU image-gen (in-between tier, 52 tests)
5. site/deploy/cost-model.mjs — cost model (LLM_RATES, API_STEP_COSTS incl modal_gpu_30s, MARKUP 5.0)
6. site/deploy/worker.js — the Cloudflare worker (run/checkout/me/topup/webhook)
7. site/deploy/schema.sql + scripts/go-live.sh — D1 + deploy automation

ROUND TASK:
[ROUND_SPECIFIC]

OUTPUT: write your analysis to research/modal-optimization/round-[N].md (markdown, thorough but skimmable).
Cover, as relevant to your round: architecture, cold-start strategy, cost optimization, async vs sync contract tradeoffs, secret handling, autopilot pipeline, scaling to 15+ workflows, what to build FIRST, what to cut, risks, and concrete file-level recommendations.
Be concrete: name files, functions, prices, and trade-offs. Do NOT edit any repo files — analysis only.
Final answer: <200 words summary of your round's key findings + the file path.
EOF
)

cat > /tmp/round_briefs.txt <<'BRIEFS'
ROUND1|Round 1 of 4 — FIRST-PASS AUDIT. Do a rigorous first-pass audit of the existing plan and the 3 containers. Identify: the 5 highest-leverage optimizations (cost, cold start, architecture, DX), the 3 biggest risks, and what the plan gets RIGHT (so later rounds don't re-litigate it). Recommend the concrete first production workflow. Be specific and quantitative where possible (costs, latencies, trade-offs).
ROUND2|Round 2 of 4 — ADVERSARIAL REFINEMENT. You have the round-1 notes. Attack the round-1 recommendations and the base plan: what did round 1 miss or get wrong? Which optimizations create new risks? Propose refinements, alternatives, and a stricter cost/cold-start model. Re-evaluate the "build HeyGen UGC first" decision vs the in-between GPU container vs pure-LLM. Produce the refined, defensible plan deltas.
ROUND3|Round 3 of 4 — DEEP-DIVE + AUTOPILOT. You have rounds 1-2 notes. Deep-dive the two hardest subsystems: (a) the AUTOPILOT pipeline (discover->extract->container spec->deploy->quality-test->live) — design the safest state machine, the quality-test suite, and the human-in-the-loop gates; (b) SECRETS + MULTI-TENANCY — how keys, billing, and per-user runs stay isolated when 15+ workflows run on Modal. Also validate the cost model math (5x markup) against real Modal GPU prices.
ROUND4|Round 4 of 4 — FINAL CONSOLIDATION. You have rounds 1-3 notes. Produce THE definitive optimized plan: a single coherent architecture document that supersedes inconsistencies, with (1) final architecture decision, (2) the exact build order (what ships first, second, third), (3) the final cost model with numbers, (4) the autopilot spec, (5) the 10 top risks with mitigations, (6) what to cut entirely. This is the plan we execute against.
BRIEFS

# Round 1
echo "=== ROUND 1 ==="
BRIEF=$(grep '^ROUND1|' /tmp/round_briefs.txt | cut -d'|' -f2)
codex exec -m gpt-5.6-sol --sandbox workspace-write "$(echo "$BASE_BRIEF" | sed "s/\[ROUND_SPECIFIC\]/$BRIEF/; s|round-\[N\]|round-1|")" 2>&1 | tail -4
echo "round 1 done"

# Round 2
echo "=== ROUND 2 ==="
BRIEF=$(grep '^ROUND2|' /tmp/round_briefs.txt | cut -d'|' -f2)
codex exec -m gpt-5.6-sol --sandbox workspace-write "$(echo "$BASE_BRIEF" | sed "s/\[ROUND_SPECIFIC\]/$BRIEF/; s|round-\[N\]|round-2|")
PRIOR ROUND NOTES (read research/modal-optimization/round-1.md before writing):" 2>&1 | tail -4
echo "round 2 done"

# Round 3
echo "=== ROUND 3 ==="
BRIEF=$(grep '^ROUND3|' /tmp/round_briefs.txt | cut -d'|' -f2)
codex exec -m gpt-5.6-sol --sandbox workspace-write "$(echo "$BASE_BRIEF" | sed "s/\[ROUND_SPECIFIC\]/$BRIEF/; s|round-\[N\]|round-3|")
PRIOR ROUND NOTES (read research/modal-optimization/round-1.md AND round-2.md before writing):" 2>&1 | tail -4
echo "round 3 done"

# Round 4
echo "=== ROUND 4 ==="
BRIEF=$(grep '^ROUND4|' /tmp/round_briefs.txt | cut -d'|' -f2)
codex exec -m gpt-5.6-sol --sandbox workspace-write "$(echo "$BASE_BRIEF" | sed "s/\[ROUND_SPECIFIC\]/$BRIEF/; s|round-\[N\]|round-4|")
PRIOR ROUND NOTES (read research/modal-optimization/round-1.md, round-2.md, round-3.md before writing):" 2>&1 | tail -4
echo "round 4 done — ALL COMPLETE"

ls -la $OUT/
