#!/usr/bin/env node
// Cross-check generated estimates against the actual repository JS cost model.

import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { estimateWorkflowCost, runPrice } from '../../site/deploy/cost-model.mjs';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
const args = process.argv.slice(2);
const reportFlag = args.indexOf('--report');
let reportPath = null;
if (reportFlag !== -1) {
  if (reportFlag + 1 >= args.length || args.indexOf('--report', reportFlag + 1) !== -1) {
    throw new Error('--report requires exactly one path');
  }
  reportPath = path.resolve(args[reportFlag + 1]);
  args.splice(reportFlag, 2);
}
const slugs = args;
const selected = slugs.length ? slugs : [
  'audio-symbolic-animation',
  'woven-storybook-pipeline',
];
if (reportPath && selected.length !== 1) {
  throw new Error('--report requires exactly one skill slug');
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function materializeWorkflow(workflow) {
  const steps = [];
  for (const source of workflow.steps || []) {
    const qty = Number(source.qty || 1);
    for (let index = 0; index < qty; index += 1) {
      if (source.type === 'llm') {
        steps.push({
          type: 'llm',
          role: source.role,
          model: source.model,
          // Four characters per declared token exercises estimateTokens exactly.
          system: 'x'.repeat(Number(source.estimated_input_tokens || 0) * 4),
          user: '',
          max_output: Number(source.max_output_tokens || 500),
        });
      } else {
        steps.push({ type: 'api', api: source.api, qty: 1 });
      }
    }
  }
  return { steps };
}

for (const slug of selected) {
  const profile = readJson(path.join(root, 'packages/skill-to-modal/profiles', `${slug}.json`));
  const report = readJson(reportPath || path.join(root, 'containers', slug, 'pricing-report.json'));
  for (const estimate of profile.pricing.estimates) {
    const workflow = materializeWorkflow(estimate.workflow);
    const actualCost = estimateWorkflowCost(workflow).costUsd;
    const actualPrice = runPrice(workflow);
    const generated = report.estimates.find((row) => row.tier === estimate.tier);
    if (!generated) throw new Error(`${slug}/${estimate.tier}: missing generated estimate`);
    if (Math.abs(actualCost - generated.modeled_cost_usd) > 0.000001) {
      throw new Error(`${slug}/${estimate.tier}: cost drift ${actualCost} != ${generated.modeled_cost_usd}`);
    }
    if (actualPrice !== generated.cost_model_run_price_usd) {
      throw new Error(`${slug}/${estimate.tier}: price drift ${actualPrice} != ${generated.cost_model_run_price_usd}`);
    }
  }
  process.stdout.write(`${slug}: pricing verified\n`);
}
