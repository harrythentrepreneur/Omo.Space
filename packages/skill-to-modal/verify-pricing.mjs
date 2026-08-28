#!/usr/bin/env node
// Cross-check generated estimates against the exact repository JS cost model
// named and hash-bound by the generated pricing report.

import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import * as legacyCostModel from '../../site/deploy/cost-model.mjs';
import * as v2CostModel from '../../site/deploy/cost-model-v2.mjs';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
const args = process.argv.slice(2);

function extractSinglePathFlag(flag) {
  const index = args.indexOf(flag);
  if (index === -1) return null;
  if (index + 1 >= args.length || args.indexOf(flag, index + 1) !== -1) {
    throw new Error(`${flag} requires exactly one path`);
  }
  const value = path.resolve(args[index + 1]);
  args.splice(index, 2);
  return value;
}

const reportPath = extractSinglePathFlag('--report');
const profilePath = extractSinglePathFlag('--profile');
const slugs = args;
const selected = slugs.length ? slugs : [
  'audio-symbolic-animation',
  'woven-storybook-pipeline',
];
if ((reportPath || profilePath) && selected.length !== 1) {
  throw new Error('--report and --profile each require exactly one skill slug');
}

const costModels = new Map([
  ['site/deploy/cost-model.mjs', legacyCostModel],
  ['site/deploy/cost-model-v2.mjs', v2CostModel],
]);

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function reportCostModel(report, slug) {
  const sourceModel = String(report.source_model || '');
  const model = costModels.get(sourceModel);
  if (!model) throw new Error(`${slug}: unsupported cost model source`);
  const sourcePath = path.join(root, sourceModel);
  const digest = createHash('sha256').update(fs.readFileSync(sourcePath)).digest('hex');
  if (report.cost_model_sha256 !== digest) {
    throw new Error(`${slug}: cost model digest drift`);
  }
  return model;
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
  const profile = readJson(profilePath || path.join(root, 'packages/skill-to-modal/profiles', `${slug}.json`));
  const report = readJson(reportPath || path.join(root, 'containers', slug, 'pricing-report.json'));
  const costModel = reportCostModel(report, slug);
  for (const estimate of profile.pricing.estimates) {
    const workflow = materializeWorkflow(estimate.workflow);
    const actualCost = costModel.estimateWorkflowCost(workflow).costUsd;
    const actualPrice = costModel.runPrice(workflow);
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
