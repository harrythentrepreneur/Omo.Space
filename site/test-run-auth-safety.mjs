import assert from 'node:assert/strict';
import fs from 'node:fs';

const runPage = fs.readFileSync(new URL('./run.html', import.meta.url), 'utf8');

function sourceBetween(start, end) {
  const startIndex = runPage.indexOf(start);
  const endIndex = runPage.indexOf(end, startIndex + start.length);
  assert.notEqual(startIndex, -1, `missing ${start}`);
  assert.notEqual(endIndex, -1, `missing ${end}`);
  return runPage.slice(startIndex, endIndex);
}

const currentUser = sourceBetween('function currentUser()', 'function signedIn()');
const authenticatedHeaders = sourceBetween('function authenticatedHeaders(', 'function newIdempotencyKey()');

assert.match(
  currentUser,
  /if \(window\.ClerkAuth[\s\S]*?return null;[\s\S]*?cognition_user/,
  'run page must not accept a persisted local user after the Clerk adapter reports signed out',
);
assert.match(
  runPage,
  /function allowsLocalCredentialFallback\(\)[\s\S]*?window\.location\.protocol === 'file:'[\s\S]*?pk_\(test\|live\)_/,
  'run page must distinguish local preview auth from configured Clerk auth',
);
assert.match(
  authenticatedHeaders,
  /catch\(function \(error\) \{[\s\S]*?if \(!allowsLocalCredentialFallback\(\)\) throw error;[\s\S]*?omo_apikey_v1/,
  'configured Clerk sessions must not fall back to a browser-persisted API key',
);

console.log('PASS run page rejects stale local credentials when Clerk is configured');
