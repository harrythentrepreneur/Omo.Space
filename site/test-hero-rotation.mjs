import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('./index.html', import.meta.url), 'utf8');

assert.match(
  html,
  /The easy way to run <span[^>]+>Claude workflows<\/span>\./,
  'hero should rotate complete product phrases',
);
assert.match(
  html,
  /var toolNames = \['Claude workflows', 'Codex workflows', 'Hermes Profiles', 'Hermes Bots'\];/,
  'rotation should include both workflow and Hermes product types',
);
assert.match(
  html,
  /\.rotating-tool \{[\s\S]*?width: 10\.5em;[\s\S]*?white-space: nowrap;/,
  'rotation slot should fit the longest phrase without layout shift',
);

console.log('hero rotation: 3/3 checks passed');
