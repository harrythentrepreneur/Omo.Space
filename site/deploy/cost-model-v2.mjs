// Cognition — workflow cost model + runner support (shared by catalog listings)
//
// Authoring-spec v2 adds Gemini 2.5 Flash while preserving the immutable v1
// cost-model snapshot in cost-model.mjs.

// ── LLM cost table (USD per 1M tokens, approx, 2026-08) ────────────────────
export const LLM_RATES = {
  'deepseek-v4-flash': { input: 0.14, output: 0.42 },
  'gemini-2.5-flash': { input: 0.30, output: 2.50 }, // Google standard paid tier, 2026-08
  'gpt-5-mini':        { input: 0.15, output: 0.60 },
  'claude-haiku-4-5':  { input: 1.00, output: 5.00 },
};

export const API_STEP_COSTS = {
  heygen_avatar_render: 0.08,
  heygen_voiceover:      0.04,
  elevenlabs_tts:        0.03,
  modal_gpu_30s:         0.05,
  browserbase_session:   0.10,
  e2b_sandbox:           0.06,
  openai_image:          0.04,
  replicate_run:         0.06,
};

export const MARKUP = 5.0;

export function estimateTokens(text) {
  if (!text) return 0;
  return Math.ceil(String(text).length / 4);
}

export function llmCallCost(model, systemText, userText, maxOutputTokens) {
  const rate = LLM_RATES[model] || LLM_RATES['deepseek-v4-flash'];
  const inTok = estimateTokens(systemText) + estimateTokens(userText);
  const outTok = maxOutputTokens || 500;
  return (inTok / 1e6) * rate.input + (outTok / 1e6) * rate.output;
}

export function estimateWorkflowCost(workflow, overrides = {}) {
  if (!workflow || !Array.isArray(workflow.steps)) return { costUsd: 0, detail: [] };
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

export function runPrice(workflow, overrides = {}) {
  const { costUsd } = estimateWorkflowCost(workflow, overrides);
  const withMargin = costUsd * MARKUP;
  const floored = Math.max(withMargin, 0.10);
  return +floored.toFixed(2);
}

export function priceLadder(runPriceUsd, free) {
  if (free === true) return { tier: 'free', label: 'Free' };
  const run = Number(runPriceUsd);
  if (!Number.isFinite(run) || run <= 0.10) return { tier: 'own', label: '$39 one-time' };
  return { tier: 'api', label: `per-use ≈ $${run.toFixed(2)}` };
}

export function llmWorkflow(systemPrompt, maxOutput = 500, model = 'deepseek-v4-flash') {
  return { steps: [{ type: 'llm', role: 'main', model, system: systemPrompt, user: '', max_output: maxOutput }] };
}
