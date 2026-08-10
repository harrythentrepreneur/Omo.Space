#!/bin/bash
# Omo Modal-hosting optimization ladder — rounds 2-4 (round 1 already done).
# Each round: FRESH sol context, reads ALL prior round files that exist, ALWAYS writes its own.
set -e
cd /Users/yifan/marketplace
mkdir -p research/modal-optimization
OUT="research/modal-optimization"

BRIEF_CORE=$(cat <<'EOF'
You are an elite infrastructure architect analyzing the OMO marketplace's Modal hosting plan with a FRESH context window.
GOAL: optimize and refine the plan to yield the best possible production result for a $100k-MRR AI workflow marketplace.
PRODUCT REALITY: Omo (omo.best) = "Fiverr for the new age": 21 AI-workflow helpers (UGC ads, product photos, SEO, Shopify ops, video), try-a-demo, buy one-time (download files+prompts $3-200) or per-use API (we run on our cloud). 5x cost markup (runPrice = max(cost*5, $0.10), dials to 1.25x later). Credits: $10 signup, runs debit, Stripe top-ups (worker /api/topup, D1 balance). Cloudflare worker: /api/run, /api/checkout, /api/me, /api/topup, /api/clerk-webhook. Backend engine = workflows containerized on Modal, API-activated, typed INPUT->OUTPUT contracts, autopilot pipeline (discover IG reel/GitHub -> extract -> container spec -> deploy to Modal -> quality-test -> live).
MANDATORY READING: research/modal-container-plan.md (THE plan), containers/ugc-heygen/, containers/claude-seo-skill/, containers/gpt-image-seedance-ad/, site/deploy/cost-model.mjs, site/deploy/worker.js, site/deploy/schema.sql, scripts/go-live.sh.
PRIOR ROUND NOTES: read every file matching research/modal-optimization/round-*.md that EXISTS on disk. If a round file does not exist yet, that is FINE — do not ask for it, do not wait, simply write your own round file anyway. Your round is independent; prior rounds are context, not a precondition.
EOF
)

run_round() {
  local N="$1"
  local TASK="$2"
  echo "=== ROUND $N ==="
  codex exec -m gpt-5.6-sol --sandbox workspace-write "$BRIEF_CORE

ROUND $N OF 4 — $TASK

OUTPUT REQUIREMENT (MANDATORY): write your analysis to research/modal-optimization/round-$N.md — CREATE this file yourself. If it does not exist yet, that is expected: you are the round that creates it. Do not stop, do not ask for the file, do not reference it as missing — WRITE IT.
Cover, as relevant to your round: architecture, cold-start strategy, cost optimization, async vs sync contract tradeoffs, secret handling, autopilot pipeline, scaling to 15+ workflows, what to build FIRST, what to cut, risks, concrete file-level recommendations (name files, functions, prices, trade-offs). Do NOT edit any other repo files — analysis only.
Final answer: <200 words summary of your round's key findings + confirm the file you wrote." 2>&1 | tail -4
  echo "round $N done"
  ls -la "$OUT/"
}

run_round 2 "ADVERSARIAL REFINEMENT. You have the round-1 notes. Attack the round-1 recommendations and the base plan: what did round 1 miss or get wrong? Which optimizations create new risks? Propose refinements, alternatives, and a stricter cost/cold-start model. Re-evaluate the 'build HeyGen UGC first' decision vs the in-between GPU container vs pure-LLM. Produce the refined, defensible plan deltas."

run_round 3 "DEEP-DIVE + AUTOPILOT. You have rounds 1-2 notes. Deep-dive the two hardest subsystems: (a) the AUTOPILOT pipeline (discover->extract->container spec->deploy->quality-test->live) — design the safest state machine, the quality-test suite, and the human-in-the-loop gates; (b) SECRETS + MULTI-TENANCY — how keys, billing, and per-user runs stay isolated when 15+ workflows run on Modal. Also validate the cost model math (5x markup) against real Modal GPU prices."

run_round 4 "FINAL CONSOLIDATION. You have rounds 1-3 notes. Produce THE definitive optimized plan: a single coherent architecture document that supersedes inconsistencies, with (1) final architecture decision, (2) the exact build order (what ships first, second, third), (3) the final cost model with numbers, (4) the autopilot spec, (5) the 10 top risks with mitigations, (6) what to cut entirely. This is the plan we execute against."

echo "=== ALL ROUNDS COMPLETE ==="
ls -la "$OUT/"
