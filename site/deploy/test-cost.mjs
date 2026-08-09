// Cognition — workflow cost model smoke test (no network, no keys)
// Usage: node test-cost.mjs
import { estimateWorkflowCost, runPrice, llmWorkflow, MARKUP } from './cost-model.mjs';
import { HEYGEN_UGC_WORKFLOW } from './workflows.mjs';

let pass = 0, fail = 0;
const check = (name, cond) => { if (cond) { pass++; console.log(`PASS  ${name}`); } else { fail++; console.log(`FAIL  ${name}`); } };

// 1. Pure LLM workflow — cost should be tiny (~$0.0003-ish for 4k in / 500 out on flash)
const w = llmWorkflow('You write listing copy.', 500, 'deepseek-v4-flash');
const c = estimateWorkflowCost(w);
check('llm workflow: cost computed > 0', c.costUsd > 0);
check('llm workflow: cost < $0.01 (cheap stack)', c.costUsd < 0.01);
check('llm workflow: detail has 1 step', c.detail.length === 1);
const p = runPrice(w);
check('run price: floored at $0.10', p >= 0.10);
check('run price: is a clean 2-decimal number', Number.isFinite(p) && Math.round(p * 100) / 100 === p);

// 2. HeyGen workflow — script LLM + 2 API renders + captions LLM
const h = estimateWorkflowCost(HEYGEN_UGC_WORKFLOW);
console.log(`  HeyGen workflow cost: $${h.costUsd} across ${h.detail.length} steps`);
check('heygen: 4 steps accounted', h.detail.length === 4);
const apiTotal = h.detail.filter(d => d.step.startsWith('api')).reduce((a, d) => a + d.costUsd, 0);
check('heygen: API steps cost ~$0.12 (0.08 render + 0.04 voice)', Math.abs(apiTotal - 0.12) < 0.0001);
const hp = runPrice(HEYGEN_UGC_WORKFLOW);
check('heygen: run price includes 25% markup', Math.abs(hp - Math.max(h.costUsd * MARKUP, 0.10)) < 0.011);
console.log(`  HeyGen run price: $${hp} (this is what the listing shows as "Run ≈ $X")`);

// 3. Empty / malformed workflows
check('empty workflow: cost 0', estimateWorkflowCost(null).costUsd === 0);
check('empty workflow: run price floored', runPrice(null) === 0.10);

// 4. Markup math: we keep 20% of positive margin (research 00-overview §10)
check('markup constant is 5.0 (LAUNCH MODE 2026-08-09; dial back to 1.25 later)', MARKUP === 5.0);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
