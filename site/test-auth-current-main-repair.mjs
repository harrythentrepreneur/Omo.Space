import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (name) => fs.readFileSync(new URL(`./${name}`, import.meta.url), 'utf8');
const clerk = read('clerk.js');
const nav = read('nav.js');
const menuWorkflows = read('menu-workflows.js');
const dashboard = read('dashboard.html');
const billing = read('billing.html');
const api = read('api.html');
const modal = read('signup-modal.js');

assert.match(clerk, /getToken:\s*function \(\)/, 'auth adapter must expose one supported Clerk session-token path');

assert.doesNotMatch(
  dashboard,
  /account\.apiKey|defaultKey\(|omo_apikey_v1/,
  'signed-in dashboard must never fall back to a browser API key',
);
assert.match(
  dashboard,
  /authenticatedRunHeaders[\s\S]*?getClerkSessionToken\(\)[\s\S]*?throw error/,
  'dashboard cloud runs must fail closed when a Clerk token is unavailable',
);
assert.match(
  billing,
  /function allowsLocalAccountFallback\(\)[\s\S]*?window\.location\.protocol === 'file:'[\s\S]*?if \(!allowsLocalAccountFallback\(\)\) return null/,
  'billing must not accept a persisted browser user when Clerk is configured',
);
assert.match(billing, /ClerkAuth\.getToken\(\)/, 'billing must use the shared verified Clerk token path');

assert.doesNotMatch(api, /Math\.random\(|omo_apikey_v1|\/api\/me\?user_id=/, 'API page must not synthesize or persist API keys');
assert.match(
  api,
  /ClerkAuth\.getToken\(\)[\s\S]*?fetch\(API_BASE \+ '\/api\/me',[\s\S]*?Authorization:\s*'Bearer ' \+ token/,
  'API page must call /api/me with the authenticated Clerk bearer token',
);
assert.match(api, /var accountRequestId = 0[\s\S]*?requestId !== accountRequestId/, 'API responses must be bound to the active account request');

assert.match(nav, /authModalPromise = null;[\s\S]*?Login popup unavailable/, 'failed modal loads must be retryable and visibly reported');
assert.match(nav, /aria-busy[\s\S]*?Opening sign-in/, 'shared sign-in controls must expose loading state');
assert.match(nav, /return_to[\s\S]*?validatedAuthDestination/, 'shared sign-in must preserve a validated destination');
assert.match(nav, /function isSignedIn\(\)[\s\S]*?if \(!demoAuthConfigured\(\)\) return false;[\s\S]*?cognition_user/, 'production navigation must not trust a persisted browser user');
assert.match(menuWorkflows, /function allowsLocalUserFallback\(\)[\s\S]*?if \(!allowsLocalUserFallback\(\)\) return false/, 'personalized menu must not trust a persisted production user');

assert.match(modal, /needs_first_factor' \|\| status === 'needs_new_password'[\s\S]*?handoffToClerk/, 'unsupported first-factor and new-password states must hand off to Clerk');
assert.match(modal, /function setBackgroundInert[\s\S]*?aria-hidden[\s\S]*?\.inert/, 'modal must make background content inert and hidden from assistive technology');
assert.match(modal, /validatedReturnTo[\s\S]*?return_to/, 'modal must validate and preserve return destinations');

console.log('PASS current-main auth repair guards credentials, recovery, handoff, and modal semantics');
