#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const files = ['site/ig-workflows.js', 'site/ig-more.js'];
const context = { window: {} };
vm.createContext(context);

for (const relative of files) {
  const source = fs.readFileSync(path.join(root, relative), 'utf8');
  vm.runInContext(source, context, { filename: relative });
}

const listings = [
  ...context.window.COGNITION_IG_WORKFLOWS,
  ...context.window.COGNITION_IG_MORE,
];

const tools = listings.map((listing) => ({
  slug: listing.slug,
  name: listing.name,
  description: listing.desc || listing.promise || '',
  promise: listing.promise || '',
  maker: listing.makerName || listing.maker || 'Omo',
  maker_handle: listing.maker || '',
  category: listing.category || 'other',
  tags: Array.isArray(listing.tags) ? listing.tags : [],
  listing_type: listing.type || 'run',
  license_price_cents: Math.round(Number(listing.priceOwn || 0) * 100),
  run_price_cents: Math.round(Number(listing.runPrice || 0) * 100),
  version_label: listing.version || 'v1.0.0',
  run_manifest: listing.runManifest || null,
  workflow_step_types: Array.isArray(listing.workflow?.steps)
    ? listing.workflow.steps.map((step) => step.type || 'unknown')
    : [],
}));

process.stdout.write(`${JSON.stringify({ source_files: files, tools }, null, 2)}\n`);
