// Cognition — workflow cost model + runner support (shared by catalog listings)
//
// Every marketplace listing is a WORKFLOW we run automatically. A workflow is a
// sequence of steps: LLM calls (script writing, analysis) + external API calls
// (HeyGen render, ElevenLabs voice, etc.). Each step has a known API cost.
// The listing's "Run" price = total workflow cost × our markup, shown to the
// buyer BEFORE they run it ("money in daylight").
//
// Usage from worker.js:
//   import { estimateWorkflowCost, runWorkflowSteps } from './cost-model.mjs';

// ── LLM cost table (USD per 1M tokens, approx, 2026-08) ────────────────────
// deepseek-v4-flash is the default cheap stack (research/00-overview.md).
export const LLM_RATES = {
  'deepseek-v4-flash': { input: 0.14, output: 0.42 },   // per 1M tokens
  'gpt-5-mini':        { input: 0.15, output: 0.60 },
  'claude-haiku-4-5':  { input: 1.00, output: 5.00 },
};

// ── External API step costs (USD per call, approx, 2026-08) ────────────────
// These are per-render/per-call list prices; we add margin on top. Update as
// vendor pricing changes — keep them honest, they're shown to buyers.
export const API_STEP_COSTS = {
  heygen_avatar_render: 0.08,     // per 60s avatar video render (HeyGen API)
  heygen_voiceover:      0.04,     // per video voice track
  elevenlabs_tts:        0.03,     // per 60s TTS
  modal_gpu_30s:         0.05,     // per 30s GPU sandbox run
  browserbase_session:   0.10,     // per browser automation session
  e2b_sandbox:           0.06,     // per sandbox session
  openai_image:          0.04,     // per generated image (gpt-image medium)
  replicate_run:         0.06,     // per Replicate model run
};

export const MARKUP = 5.0; // LAUNCH MODE (2026-08-09, user directive): 5x markup for profit while the store is small.
// Plan: dial back to 1.25x once volume grows (user: "later we can turn that down to just like *1.25x markup").
// runPrice = max(cost * MARKUP, $0.10) — see runPrice() below.

// Estimate tokens for a prompt: ~4 chars/token for English, or use counts if given.
export function estimateTokens(text) {
  if (!text) return 0;
  return Math.ceil(String(text).length / 4);
}

// Estimate the cost of one LLM call.
export function llmCallCost(model, systemText, userText, maxOutputTokens) {
  const rate = LLM_RATES[model] || LLM_RATES['deepseek-v4-flash'];
  const inTok = estimateTokens(systemText) + estimateTokens(userText);
  const outTok = maxOutputTokens || 500;
  return (inTok / 1e6) * rate.input + (outTok / 1e6) * rate.output;
}

// Estimate the full workflow cost.
// workflow = { steps: [{ type: 'llm', model?, system?, max_output?, tokens_in? },
//                      { type: 'api', api: 'heygen_avatar_render', qty? }] }
// Returns { costUsd, detail: [{step, costUsd}] }.
export function estimateWorkflowCost(workflow, overrides = {}) {
  if (!workflow || !Array.isArray(workflow.steps)) {
    return { costUsd: 0, detail: [] };
  }
  let total = 0;
  const detail = [];
  for (const step of workflow.steps) {
    let cost = 0;
    if (step.type === 'llm') {
      const model = overrides.model || step.model || 'deepseek-v4-flash';
      cost = llmCallCost(model, step.system || '', step.user || '', step.max_output);
    } else if (step.type === 'api') {
      const unit = API_STEP_COSTS[step.api] || 0.05;
      cost = unit * (step.qty || 1);
    }
    total += cost;
    detail.push({ step: step.type === 'llm' ? `llm(${step.role || 'call'})` : `api(${step.api})`, costUsd: +cost.toFixed(5) });
  }
  return { costUsd: +total.toFixed(5), detail };
}

// The buyer-facing run price: cost × markup, floored at $0.10 so tiny workflows
// still clear a payable amount, rounded to a clean price point.
export function runPrice(workflow, overrides = {}) {
  const { costUsd } = estimateWorkflowCost(workflow, overrides);
  const withMargin = costUsd * MARKUP;
  const floored = Math.max(withMargin, 0.10);
  return +floored.toFixed(2);
}

/*
 * Storefront pricing ladder: free lead magnets give away prompts; "own" is a
 * one-time local download; "api" runs the workflow on our cloud per use.
 * The current $0.10 floor is the interim boundary for the one-time lane.
 */
export function priceLadder(runPriceUsd, free) {
  if (free === true) return { tier: 'free', label: 'Free' };
  const run = Number(runPriceUsd);
  if (!Number.isFinite(run) || run <= 0.10) return { tier: 'own', label: '$39 one-time' };
  return { tier: 'api', label: `per-use ≈ $${run.toFixed(2)}` };
}

// Convenience: one-call LLM workflow (the 90% case — most skills are pure LLM).
export function llmWorkflow(systemPrompt, maxOutput = 500, model = 'deepseek-v4-flash') {
  return {
    steps: [
      { type: 'llm', role: 'main', model, system: systemPrompt, user: '', max_output: maxOutput },
    ],
  };
}
