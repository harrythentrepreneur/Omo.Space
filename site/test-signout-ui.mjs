import assert from 'node:assert/strict';
import fs from 'node:fs';

const dashboard = fs.readFileSync(new URL('./dashboard.html', import.meta.url), 'utf8');
const nav = fs.readFileSync(new URL('./nav.js', import.meta.url), 'utf8');

assert.match(
  dashboard,
  /try \{ signOutResult = window\.ClerkAuth\.signOut\(\); \}[\s\S]*?Promise\.resolve\(signOutResult\)[\s\S]*?window\.location\.assign\('index\.html'\)/,
  'dashboard must await sign-out before redirecting',
);
assert.match(
  dashboard,
  /function clearAccountState\(\)[\s\S]*?accountRequestId \+= 1[\s\S]*?account\.apiKey = ''/,
  'dashboard must invalidate pending account requests and clear in-memory account data',
);
assert.match(
  dashboard,
  /Sign-out failed\. You are still signed in\. Please try again\./,
  'dashboard must show a visible retryable sign-out failure',
);
assert.match(
  dashboard,
  /var refreshRequestId = requestId[\s\S]*?refreshRequestId !== accountRequestId[\s\S]*?current\.id !== userId/,
  'delayed top-up refresh must not cross logout or account changes',
);
assert.match(
  dashboard,
  /catch \(error\) \{[\s\S]*?button\.disabled = false;[\s\S]*?button\.textContent = 'Log out';[\s\S]*?return;/,
  'synchronous dashboard sign-out failures must restore the control',
);
assert.match(
  nav,
  /link\.setAttribute\('aria-busy', 'true'\)[\s\S]*?Promise\.resolve\(result\)/,
  'shared navigation must show progress while awaiting sign-out',
);
assert.match(
  nav,
  /Log out failed — try again/,
  'shared navigation must visibly report sign-out failure',
);

console.log('PASS sign-out UI awaits completion and handles failures');
