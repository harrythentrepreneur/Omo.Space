// Cognition demo worker — router dispatch smoke test (no network, no keys)
//
// Usage:  node test-router.mjs
//
// Loads the merged worker.js in a vm sandbox and exercises the export default
// fetch handler with a STUBBED global fetch (returns canned LLM JSON) and a
// fake env. Verifies: OPTIONS CORS, 405 on GET, 404 on unknown route, and a
// successful dispatch + parsed envelope for all three /api routes.

import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { webcrypto } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const clerkFrontendApi = 'example.clerk.accounts.dev';
const clerkPublishableKey = `pk_test_${Buffer.from(`${clerkFrontendApi}$`).toString('base64url')}`;
const clerkKeyPair = await webcrypto.subtle.generateKey(
  { name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' },
  true,
  ['sign', 'verify'],
);
const clerkJwk = { ...(await webcrypto.subtle.exportKey('jwk', clerkKeyPair.publicKey)), kid: 'test-kid', alg: 'RS256', use: 'sig' };

async function clerkToken(userId) {
  const now = Math.floor(Date.now() / 1000);
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const header = encode({ alg: 'RS256', typ: 'JWT', kid: 'test-kid' });
  const payload = encode({ sub: userId, iss: `https://${clerkFrontendApi}`, azp: 'https://omo.best', iat: now, nbf: now - 1, exp: now + 60 });
  const input = `${header}.${payload}`;
  const signature = await webcrypto.subtle.sign('RSASSA-PKCS1-v1_5', clerkKeyPair.privateKey, new TextEncoder().encode(input));
  return `${input}.${Buffer.from(signature).toString('base64url')}`;
}

async function modalArtifactUrl(runId, objectName, ttlSeconds = 300) {
  const expires = Math.floor(Date.now() / 1000) + ttlSeconds;
  const key = await webcrypto.subtle.importKey(
    'raw', new TextEncoder().encode('private-modal-test-secret'),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
  );
  const signature = await webcrypto.subtle.sign(
    'HMAC', key, new TextEncoder().encode(`GET\n${runId}\n${objectName}\n${expires}`),
  );
  return `https://modal.invalid/v1/artifacts/${runId}/${objectName}?expires=${expires}&signature=${Buffer.from(signature).toString('hex')}`;
}

async function expectedModalIdempotencyKey(userId, callerKey) {
  const input = new TextEncoder().encode(`omo-demello-modal-idempotency-v1\u0000${userId}\u0000${callerKey}`);
  const digest = await webcrypto.subtle.digest('SHA-256', input);
  return `omo-${Buffer.from(digest).toString('hex')}`;
}

// worker.js imports balance.mjs + cost-model.mjs (bundled at deploy time).
// The vm sandbox can't resolve imports, so concatenate them first with the
// `export`/`import` keywords stripped — they are dependency-free modules, so
// plain concatenation is safe and keeps a single source of truth.
function stripModule(p) {
  return fs.readFileSync(path.join(here, p), 'utf8')
    .replace(/^import .*$/gm, '')
    .replace(/^export /gm, '');
}
const prelude = stripModule('balance.mjs') + '\n' + stripModule('cost-model.mjs') + '\n';
const workerSrc = fs.readFileSync(path.join(here, 'worker.js'), 'utf8').replace(/^import .*$/gm, '');
const cjs = prelude + workerSrc.replace('export default', 'const __workerExport =');

// Stubbed LLM endpoint: returns a different canned shape per route, always
// wrapped in a markdown fence to prove the normalizers strip it.
const canned = {
  '/api/ugc-script-studio':
    '```json\n{"hook":"stop scrolling","shots":["CU on product"],"captions":["try this"],"cta":"grab one"}\n```',
  '/api/meta-ads-analyser':
    '```json\n{"verdict":"retargeting wins","winners":["retarget-v2 — ROAS 11.2"],"losers":["brand-test — ROAS 0.6"],"quick_wins":["shift 20%"],"next_move":"scale retarget-v2"}\n```',
  '/api/product-photo-generator':
    '```json\n{"shot_plan":["Hero: mug on walnut table"],"background_suggestion":"warm neutral","caption":"ritual upgrade","listing_copy":"Hand-thrown in small batches"}\n```',
};

// Calls made to the real Stripe API (captured by the fetch stub below).
const stripeCalls = [];
const llmCalls = [];
const modalCalls = [];
const modalStatuses = new Map();
let modalDispatchStatus = 202;

const sandbox = {
  fetch: async (url, opts) => {
    if (String(url).startsWith('https://modal.invalid')) {
      const target = new URL(String(url));
      modalCalls.push({ url: String(url), method: opts && opts.method || 'GET', headers: opts && opts.headers, body: opts && opts.body });
      if (target.pathname === '/v1/runs' && opts && opts.method === 'POST') {
        const envelope = JSON.parse(opts.body);
        if (modalDispatchStatus !== 202) {
          return { ok: false, status: modalDispatchStatus, json: async () => ({ detail: 'dispatch_failed' }) };
        }
        modalStatuses.set(envelope.run_id, { run_id: envelope.run_id, status: 'running' });
        return { ok: true, status: 202, json: async () => ({ run_id: envelope.run_id, status: 'accepted', platform: { paid_traffic_ready: false } }) };
      }
      const runId = target.pathname.split('/').at(-1);
      const status = modalStatuses.get(runId);
      return status
        ? { ok: true, status: 200, json: async () => status }
        : { ok: false, status: 404, json: async () => ({ detail: 'run_not_found' }) };
    }
    if (String(url).includes('/.well-known/jwks.json')) {
      return { ok: true, status: 200, json: async () => ({ keys: [clerkJwk] }) };
    }
    if (String(url).includes('api.stripe.com')) {
      stripeCalls.push({ url: String(url), body: String(opts.body), headers: opts.headers });
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 'cs_test_123', url: 'https://checkout.stripe.com/c/pay/test_123' }),
      };
    }
    const body = JSON.parse(opts.body);
    llmCalls.push(body);
    const user = body.messages.find((m) => m.role === 'user').content;
    let route = '/api/ugc-script-studio';
    if (user.includes('Ads export')) route = '/api/meta-ads-analyser';
    if (user.includes('Plan the shot list')) route = '/api/product-photo-generator';
    return {
      ok: true,
      status: 200,
      json: async () => ({ choices: [{ message: { content: canned[route] } }] }),
    };
  },
  URL,
  URLSearchParams,
  Response,
  Headers,
  JSON,
  Date,
  String,
  Number,
  Array,
  Object,
  TextEncoder,
  TextDecoder,
  atob,
  btoa,
  crypto: webcrypto,
  console,
};
vm.createContext(sandbox);
vm.runInContext(`${cjs}\n;globalThis.__workerExport = __workerExport;`, sandbox, { filename: 'worker.js' });
const worker = sandbox.__workerExport;

const env = { LLM_API_KEY: 'test-key', LLM_BASE_URL: 'https://llm.invalid/v1', LLM_MODEL: 'test-model' };
// Encodes example.clerk.accounts.dev$; API-key tests do not need a JWKS fetch.
const realEnv = { ...env, CLERK_PUBLISHABLE_KEY: clerkPublishableKey };

let pass = 0;
let fail = 0;
function check(name, cond) {
  if (cond) { pass += 1; console.log(`PASS  ${name}`); }
  else { fail += 1; console.log(`FAIL  ${name}`); }
}

const dashboardSource = fs.readFileSync(path.join(here, '..', 'dashboard.html'), 'utf8');
check('dashboard: server account loads /api/me with a Clerk session bearer', dashboardSource.includes('window.Clerk.session.getToken()') && dashboardSource.includes("fetch(API_BASE + '/api/me', { headers: { Authorization: 'Bearer ' + token"));
check('dashboard: cloud-run network errors never fall back to a mock after POST', (dashboardSource.match(/startMockVideoRun\(form, product\);/g) || []).length === 1 && dashboardSource.includes('The submission outcome is unknown') && dashboardSource.includes('Reconcile run'));
check('dashboard: terminal 5xx run states are handled before indefinite retry', dashboardSource.includes("terminalStatus === 'failed' || terminalStatus === 'refunded'") && dashboardSource.includes("status === 'failed' || status === 'refunded'"));
check('dashboard: server top-ups post to /api/topup with authenticated headers', dashboardSource.includes("fetch((API_BASE || '') + '/api/topup'") && dashboardSource.includes("authenticatedRunHeaders('').then(function (headers)"));
check('dashboard: hosted video form exposes the sample-only provider gate', dashboardSource.includes('Hosted staging currently accepts only sample-demello-10s'));

const mkReq = (method, pathname, body, extraHeaders = {}) => ({
  method,
  url: `https://demo.cognition.cv${pathname}`,
  headers: new Headers({
    'CF-Connecting-IP': '203.0.113.9',
    'Content-Type': 'application/json',
    ...extraHeaders,
  }),
  json: async () => body,
  text: async () => JSON.stringify(body),
});

// OPTIONS → 200 + CORS
const opt = await worker.fetch(mkReq('OPTIONS', '/api/ugc-script-studio'), env);
check('router: OPTIONS returns 200 + CORS', opt.status === 200 && opt.headers.get('Access-Control-Allow-Origin') === '*');

// GET → 405
const get = await worker.fetch(mkReq('GET', '/api/ugc-script-studio'), env);
check('router: GET returns 405', get.status === 405);

// Unknown route → 404
const nf = await worker.fetch(mkReq('POST', '/api/nope', {}), env);
const nfBody = await nf.json();
check('router: unknown route returns 404 + routes list', nf.status === 404 && Array.isArray(nfBody.routes) && nfBody.routes.length === 8);

// Generic /api/run route
const run = await (await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'listing-copy-engine',
  system_prompt: 'MALICIOUS CLIENT PROMPT',
  max_tokens: 999999,
  fields: { description: 'ceramic mug', marketplace: 'etsy' },
}), env)).json();
check('run: catalog route ignores client prompt/token controls', run.ok === true && run.slug === 'listing-copy-engine' && run.output.hook === 'stop scrolling' && llmCalls.at(-1).max_tokens === 600 && !llmCalls.at(-1).messages[0].content.includes('MALICIOUS'));
const badRun = await worker.fetch(mkReq('POST', '/api/run', { slug: '', system_prompt: '' }), env);
check('run: missing slug returns 400', badRun.status === 400);

// Three successful dispatches (KV-less env → caps skipped)
const ugc = await (await worker.fetch(mkReq('POST', '/api/ugc-script-studio', { product: 'silk pillowcase', voice: 'raw', length: 30 }), env)).json();
check('ugc: dispatch returns ok + script', ugc.ok === true && ugc.script.hook === 'stop scrolling' && Array.isArray(ugc.script.shots));

const meta = await (await worker.fetch(mkReq('POST', '/api/meta-ads-analyser', { ads_export: 'campaign,spend\nprospecting-v1,412.00', goal: 'roas' }), env)).json();
check('meta: dispatch returns ok + analysis', meta.ok === true && meta.analysis.verdict === 'retargeting wins' && meta.analysis.winners.length === 1);

const photo = await (await worker.fetch(mkReq('POST', '/api/product-photo-generator', { product_description: 'ceramic mug', photo_url: '', style: 'lifestyle' }), env)).json();
check('photo: dispatch returns ok + plan', photo.ok === true && photo.plan.shot_plan.length === 1 && photo.plan.listing_copy !== '');

// Validation paths
const bad = await worker.fetch(mkReq('POST', '/api/ugc-script-studio', {}), env);
check('router: missing product returns 400', bad.status === 400);
const badMeta = await worker.fetch(mkReq('POST', '/api/meta-ads-analyser', { ads_export: 'x', goal: 'nope' }), env);
check('router: bad meta goal returns 400', badMeta.status === 400);
const badStyle = await worker.fetch(mkReq('POST', '/api/product-photo-generator', { product_description: 'x', style: 'neon' }), env);
check('router: bad photo style returns 400', badStyle.status === 400);

// ── /api/checkout (Stripe Checkout session) ───────────────────────────────

const stripeEnv = { ...realEnv, STRIPE_SECRET_KEY: 'sk_test_fake_secret' };
const user111Token = await clerkToken('user_111');
const user111Headers = { Authorization: `Bearer ${user111Token}`, Origin: 'https://omo.best' };

const co = await worker.fetch(mkReq('POST', '/api/checkout', { slug: 'ugc-script-studio', priceUsd: 25, email: 'buyer@example.com' }), env);
check('checkout: no secret key returns 501', co.status === 501);
const coBody = await co.json();
check('checkout: 501 body says not configured', coBody.error === 'stripe not configured');

const badCheckout = await worker.fetch(mkReq('POST', '/api/checkout', { slug: '', priceUsd: 5 }), stripeEnv);
check('checkout: missing slug returns 400', badCheckout.status === 400);

const cs = await (await worker.fetch(mkReq('POST', '/api/checkout', { slug: 'ugc-script-studio', priceUsd: 25, email: 'buyer@example.com' }), stripeEnv)).json();
check('checkout: returns Stripe Checkout url', cs.url === 'https://checkout.stripe.com/c/pay/test_123');

const sc = stripeCalls[stripeCalls.length - 1];
const scParams = new URLSearchParams(sc.body);
check('checkout: posts form-encoded to Stripe sessions API', sc.url === 'https://api.stripe.com/v1/checkout/sessions');
check('checkout: unit_amount is server catalog price (client price ignored)', scParams.get('line_items[0][price_data][unit_amount]') === '3900');
check('checkout: currency + mode + quantity set', scParams.get('line_items[0][price_data][currency]') === 'usd' && scParams.get('mode') === 'payment' && scParams.get('line_items[0][quantity]') === '1');
check('checkout: success_url carries the slug', (scParams.get('success_url') || '').includes('purchased=ugc-script-studio'));
check('checkout: cancel_url set', (scParams.get('cancel_url') || '').includes('purchased=cancelled'));
check('checkout: buyer email forwarded', scParams.get('customer_email') === 'buyer@example.com');
check('checkout: bearer auth uses the secret (never logged)', (sc.headers.Authorization || '') === 'Bearer sk_test_fake_secret');
await worker.fetch(mkReq('POST', '/api/checkout', { slug: 'japanese-style-story-video', priceUsd: 99 }), stripeEnv);
const demelloCheckoutParams = new URLSearchParams(stripeCalls.at(-1).body);
check('checkout: Japanese Style Story Video own price is server-pinned at $29', demelloCheckoutParams.get('line_items[0][price_data][unit_amount]') === '2900');

// Cap enforcement via fake KV
let kvStore = {};
const kvEnv = {
  ...env,
  BENCH_KV: {
    get: async (k) => kvStore[k] ?? null,
    put: async (k, v) => { kvStore[k] = v; },
  },
  DEMO_DAILY_CAP_UGC: '1',
};
const r1 = await worker.fetch(mkReq('POST', '/api/ugc-script-studio', { product: 'pillowcase' }), kvEnv);
const r2 = await worker.fetch(mkReq('POST', '/api/ugc-script-studio', { product: 'pillowcase' }), kvEnv);
check('caps: first call allowed, second returns 429', r1.status === 200 && r2.status === 429);

// ── /api/me (dashboard: balance + api key + usage, mock store) ────────────

const me1 = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_111', {}), env)).json();
check('me: creates a user with the $5 signup grant', me1.ok === true && me1.balance === '5.00' && me1.balance_usd === 5 && me1.balance_cents === 500);
check('me: currency is usd + mock flag set without D1', me1.currency === 'usd' && me1.mock === true);
check('me: api key is a deterministic omo_ key', /^omo_[0-9a-f]{32}$/.test(me1.api_key));
check('me: usage list starts empty', Array.isArray(me1.runs) && me1.runs.length === 0);

const me2 = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_111', {}), env)).json();
check('me: repeat visit neither double-grants nor rotates the key', me2.balance_usd === 5 && me2.api_key === me1.api_key);

const meBad = await worker.fetch(mkReq('GET', '/api/me?user_id=user_attacker', {}, { Origin: 'https://evil.example' }), realEnv);
check('auth: real /api/me rejects missing token and evil CORS origin', meBad.status === 401 && !meBad.headers.get('Access-Control-Allow-Origin'));

// ── /api/run with user_id → debits the balance ────────────────────────────

const runPaid = await (await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'listing-copy-engine',
  system_prompt: 'You write marketplace listing copy. Output JSON with title, bullets, description.',
  fields: { description: 'ceramic mug' },
  user_id: 'user_111',
}), env)).json();
check('run: paid run succeeds and reports cost + new balance', runPaid.ok === true && runPaid.cost_usd === 0.1 && runPaid.balance === 4.9);

const me3 = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_111', {}), env)).json();
check('run: balance debited after run ($4.90)', me3.balance_usd === 4.9);
check('run: usage list records the run', me3.runs.length === 1 && me3.runs[0].slug === 'listing-copy-engine' && me3.runs[0].cost_usd === 0.1);

// ── /api/run → 402 insufficient balance ───────────────────────────────────

const lowEnv = { ...env, SIGNUP_GRANT_USD: '0.05' };
const lowMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_low', {}), lowEnv)).json();
check('run: low-balance user starts at $0.05', lowMe.balance_usd === 0.05);

const poor = await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'listing-copy-engine',
  system_prompt: 'You write listing copy.',
  fields: { description: 'mug' },
  user_id: 'user_low',
}), lowEnv);
const poorBody = await poor.json();
check('run: insufficient balance returns 402', poor.status === 402 && poorBody.error === 'insufficient_balance');
check('run: 402 carries balance, friendly top-up guidance, and suggestions', poorBody.balance === 0.05 && poorBody.cost_usd === 0.1 && poorBody.shortfall_usd === 0.05 && /top up/i.test(poorBody.message) && JSON.stringify(poorBody.suggested_amounts_usd) === JSON.stringify([20, 50, 100, 200]));

const lowMe2 = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_low', {}), lowEnv)).json();
check('run: 402 leaves the balance untouched (still $0.05)', lowMe2.balance_usd === 0.05 && lowMe2.runs.length === 0);

// Real /api/run accepts the owning omo_ key and charges exactly once when a
// request is replayed with the same Idempotency-Key.
const idemMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_idem', {}), env)).json();
const callsBeforeIdem = llmCalls.length;
const idemHeaders = { Authorization: `Bearer ${idemMe.api_key}`, 'Idempotency-Key': 'router-idem-0001' };
const idemBody = {
  slug: 'listing-copy-engine', fields: { description: 'idempotent mug' }, user_id: 'user_attacker',
  system_prompt: 'client prompt must be ignored', max_tokens: 999999,
};
const idem1 = await (await worker.fetch(mkReq('POST', '/api/run', idemBody, idemHeaders), realEnv)).json();
const idem2 = await (await worker.fetch(mkReq('POST', '/api/run', idemBody, idemHeaders), realEnv)).json();
const idemAfter = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_idem', {}), env)).json();
check('run: idempotency replay returns prior run and charges owner once', idem1.ok === true && idem2.idempotent_replay === true && idem2.run_id === idem1.run_id && idemAfter.balance_usd === 4.9 && llmCalls.length === callsBeforeIdem + 1);

// ── Japanese Style Story Video → private Modal + async progress ───────────

const demelloEnv = {
  ...realEnv,
  DEMELLO_MODAL_URL: 'https://modal.invalid',
  DEMELLO_MODAL_BEARER: 'private-modal-test-secret',
  DEMELLO_PROGRESS_WEBHOOK_SECRET: 'progress-webhook-test-secret',
};
const demelloMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_demello', {}), env)).json();
const demelloHeaders = { Authorization: `Bearer ${demelloMe.api_key}`, 'Idempotency-Key': 'demello-router-0001' };
const demelloInput = {
  slug: 'japanese-style-story-video',
  fields: {
    audio_ref: 'sample-demello-10s',
    style_hint: 'sumi-e',
    duration_bounds: { min_seconds: 5, max_seconds: 10 },
  },
};
const modalCallsBefore = modalCalls.length;
const demelloStartResponse = await worker.fetch(mkReq('POST', '/api/run', demelloInput, demelloHeaders), demelloEnv);
const demelloStart = await demelloStartResponse.json();
check('demello: dispatch returns progress + explicit quoted-but-zero-bill contract', demelloStartResponse.status === 202 && /^run_/.test(demelloStart.run_id) && demelloStart.status === 'running' && demelloStart.phase === 'running' && demelloStart.progress_pct >= 1 && demelloStart.status_url === `/api/run/${demelloStart.run_id}` && demelloStart.quoted_cost_usd === 0.1 && demelloStart.billed_amount_usd === 0 && demelloStart.billing_mode === 'nonpaid_milestone' && demelloStart.paid_traffic_ready === false);
const modalSubmit = modalCalls.at(-1);
const modalEnvelope = JSON.parse(modalSubmit.body);
const primaryModalKey = modalSubmit.headers['Idempotency-Key'];
check('demello: dispatch uses private bearer + final pinned canonical envelope', modalSubmit.headers.Authorization === 'Bearer private-modal-test-secret' && modalEnvelope.run_id === demelloStart.run_id && modalEnvelope.release_hash === 'sha256:245304c8f98839bf6ac570c3c09224fe839041dbc793f3fb7f7afb3eb475259e' && /^[0-9a-f]{64}$/.test(modalEnvelope.request_hash) && modalEnvelope.input.style === 'sumi-e-awake-v3' && modalEnvelope.max_cost_usd === 0.003);
check('demello: downstream idempotency key is deterministic and opaque', primaryModalKey === await expectedModalIdempotencyKey('user_demello', 'demello-router-0001') && /^omo-[0-9a-f]{64}$/.test(primaryModalKey) && primaryModalKey !== 'demello-router-0001' && !primaryModalKey.includes('user_demello'));

const demelloReplayResponse = await worker.fetch(mkReq('POST', '/api/run', demelloInput, demelloHeaders), demelloEnv);
const demelloReplay = await demelloReplayResponse.json();
check('demello: idempotent retry neither dispatches nor debits twice', demelloReplayResponse.status === 202 && demelloReplay.idempotent_replay === true && demelloReplay.run_id === demelloStart.run_id && modalCalls.length === modalCallsBefore + 1);
check('demello: same-owner retry retains the same derived Modal scope key', primaryModalKey === await expectedModalIdempotencyKey('user_demello', 'demello-router-0001'));

const scopeAMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_scope_a', {}), env)).json();
const scopeBMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_scope_b', {}), env)).json();
const sharedCallerKey = 'demello-shared-scope-001';
const scopeCallsBefore = modalCalls.length;
const scopeAStart = await (await worker.fetch(mkReq('POST', '/api/run', demelloInput, {
  Authorization: `Bearer ${scopeAMe.api_key}`, 'Idempotency-Key': sharedCallerKey,
}), demelloEnv)).json();
const scopeBStart = await (await worker.fetch(mkReq('POST', '/api/run', demelloInput, {
  Authorization: `Bearer ${scopeBMe.api_key}`, 'Idempotency-Key': sharedCallerKey,
}), demelloEnv)).json();
const scopeACall = modalCalls[scopeCallsBefore];
const scopeBCall = modalCalls[scopeCallsBefore + 1];
const scopeAKey = scopeACall && scopeACall.headers['Idempotency-Key'];
const scopeBKey = scopeBCall && scopeBCall.headers['Idempotency-Key'];
check('demello: two owners may reuse a caller key without a global Modal collision', scopeAStart.run_id !== scopeBStart.run_id && scopeAKey !== scopeBKey && scopeAKey === await expectedModalIdempotencyKey('user_scope_a', sharedCallerKey) && scopeBKey === await expectedModalIdempotencyKey('user_scope_b', sharedCallerKey) && !scopeAKey.includes('user_scope_a') && !scopeBKey.includes('user_scope_b'));
const scopeAReplay = await (await worker.fetch(mkReq('POST', '/api/run', demelloInput, {
  Authorization: `Bearer ${scopeAMe.api_key}`, 'Idempotency-Key': sharedCallerKey,
}), demelloEnv)).json();
check('demello: scoped owner retry replays without a second Modal dispatch', scopeAReplay.run_id === scopeAStart.run_id && scopeAReplay.idempotent_replay === true && modalCalls.length === scopeCallsBefore + 2 && scopeAKey === await expectedModalIdempotencyKey('user_scope_a', sharedCallerKey));

const demelloPoll1Response = await worker.fetch(mkReq('GET', `/api/run/${demelloStart.run_id}`, {}, { Authorization: `Bearer ${demelloMe.api_key}` }), demelloEnv);
const demelloPoll1 = await demelloPoll1Response.json();
check('demello: GET status returns explicit derived progress while Modal only says running', demelloPoll1Response.status === 202 && demelloPoll1.status === 'running' && demelloPoll1.progress_pct >= demelloStart.progress_pct && demelloPoll1.progress_source === 'derived');

modalStatuses.set(demelloStart.run_id, { run_id: demelloStart.run_id, status: 'running', phase: 'semantic', progress_pct: 64 });
const demelloModalProgress = await (await worker.fetch(mkReq('GET', `/api/run/${demelloStart.run_id}`, {}, { Authorization: `Bearer ${demelloMe.api_key}` }), demelloEnv)).json();
check('demello: Modal semantic checkpoint maps to observed generating progress', demelloModalProgress.phase === 'generating' && demelloModalProgress.progress_pct === 64 && demelloModalProgress.progress_source === 'modal');
modalStatuses.set(demelloStart.run_id, { run_id: demelloStart.run_id, status: 'running', phase: 'validating', progress_pct: 94 });
const demelloQaProgress = await (await worker.fetch(mkReq('GET', `/api/run/${demelloStart.run_id}`, {}, { Authorization: `Bearer ${demelloMe.api_key}` }), demelloEnv)).json();
check('demello: Modal validating checkpoint maps to public assembling phase', demelloQaProgress.phase === 'assembling' && demelloQaProgress.progress_pct === 94 && demelloQaProgress.progress_source === 'modal');

modalStatuses.set(demelloStart.run_id, {
  run_id: demelloStart.run_id,
  status: 'completed',
  video_url: await modalArtifactUrl(demelloStart.run_id, 'video.mp4'),
  contact_sheet_url: await modalArtifactUrl(demelloStart.run_id, 'contact-sheet.jpg'),
  media: { width: 1080, height: 1920, video_codec: 'h264', audio_codec: 'aac' },
  platform: { paid_traffic_ready: false },
});
const demelloDoneResponse = await worker.fetch(mkReq('GET', `/api/run/${demelloStart.run_id}`, {}, { Authorization: `Bearer ${demelloMe.api_key}` }), demelloEnv);
const demelloDone = await demelloDoneResponse.json();
check('demello: completed Modal poll settles and exposes zero-billed video delivery', demelloDoneResponse.status === 200 && demelloDone.status === 'delivered' && demelloDone.phase === 'delivered' && demelloDone.progress_pct === 100 && /video\.mp4\?/.test(demelloDone.video_url) && demelloDone.settlement.charged_usd === 0 && demelloDone.quoted_cost_usd === 0.1 && demelloDone.billed_amount_usd === 0);
const demelloAfter = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_demello', {}), env)).json();
const demelloUsage = demelloAfter.runs.filter((entry) => entry.slug === 'japanese-style-story-video');
check('demello: nonpaid milestone records usage without charging credits', demelloAfter.balance_usd === 5 && demelloUsage.length === 1 && demelloUsage[0].cost_usd === 0);
const lateFailure = await worker.fetch(mkReq('POST', `/api/run/${demelloStart.run_id}/progress`, {
  run_id: demelloStart.run_id, status: 'failed', error_code: 'LATE_CHECKPOINT',
}, { Authorization: 'Bearer progress-webhook-test-secret' }), demelloEnv);
const lateFailureBody = await lateFailure.json();
const demelloAfterLate = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_demello', {}), env)).json();
check('demello: delivered success is immutable against a late failed webhook', lateFailure.status === 200 && lateFailureBody.status === 'delivered' && demelloAfterLate.balance_usd === 5);

const progressMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_progress', {}), env)).json();
const progressHeaders = { Authorization: `Bearer ${progressMe.api_key}`, 'Idempotency-Key': 'demello-router-progress-001' };
const progressStart = await (await worker.fetch(mkReq('POST', '/api/run', demelloInput, progressHeaders), demelloEnv)).json();
const badProgressAuth = await worker.fetch(mkReq('POST', `/api/run/${progressStart.run_id}/progress`, { phase: 'generating', progress_pct: 70 }, { Authorization: 'Bearer wrong' }), demelloEnv);
check('demello: progress webhook rejects the wrong bearer', badProgressAuth.status === 401);
const checkpointResponse = await worker.fetch(mkReq('POST', `/api/run/${progressStart.run_id}/progress`, { run_id: progressStart.run_id, status: 'running', phase: 'assembling', progress_pct: 95 }, { Authorization: 'Bearer progress-webhook-test-secret' }), demelloEnv);
const checkpoint = await checkpointResponse.json();
check('demello: authenticated checkpoint records real phase + percent', checkpointResponse.status === 202 && checkpoint.phase === 'assembling' && checkpoint.progress_pct === 95 && checkpoint.progress_source === 'webhook');
modalStatuses.set(progressStart.run_id, { run_id: progressStart.run_id, status: 'running', phase: 'transcribing', progress_pct: 20 });
const checkpointPoll = await (await worker.fetch(mkReq('GET', `/api/run/${progressStart.run_id}`, {}, { Authorization: `Bearer ${progressMe.api_key}` }), demelloEnv)).json();
check('demello: lower Modal poll cannot relabel a winning atomic checkpoint', checkpointPoll.phase === 'assembling' && checkpointPoll.progress_pct === 95 && checkpointPoll.progress_source === 'webhook');

const invalidMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_demello_invalid', {}), env)).json();
const invalidBefore = modalCalls.length;
const invalidDemello = await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'japanese-style-story-video', fields: { audio_url: 'http://unsafe.example/audio.mp3' },
}, { Authorization: `Bearer ${invalidMe.api_key}`, 'Idempotency-Key': 'demello-invalid-0001' }), demelloEnv);
check('demello: invalid typed input is rejected before reservation or dispatch', invalidDemello.status === 400 && modalCalls.length === invalidBefore);

const gatedHttps = await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'japanese-style-story-video', fields: { audio_url: 'https://audio.example/short.mp3' },
}, { Authorization: `Bearer ${invalidMe.api_key}`, 'Idempotency-Key': 'demello-provider-gate-001' }), demelloEnv);
const gatedHttpsBody = await gatedHttps.json();
check('demello: arbitrary HTTPS audio is gated before reservation or Modal spend', gatedHttps.status === 400 && gatedHttpsBody.error === 'demello_provider_lane_not_enabled' && modalCalls.length === invalidBefore);

const topicMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_demello_topic', {}), env)).json();
const topicRun = await (await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'japanese-style-story-video', fields: { audio: 'A quiet story about waking up', duration: '10 seconds' },
}, { Authorization: `Bearer ${topicMe.api_key}`, 'Idempotency-Key': 'demello-topic-fallback-001' }), demelloEnv)).json();
const topicEnvelope = JSON.parse(modalCalls.at(-1).body);
check('demello: topic fallback is explicit and only runs the bundled sample audio', topicRun.status === 'running' && /not synthesized/i.test(topicRun.input_notice) && topicEnvelope.input.audio_ref === 'sample-demello-10s' && !topicEnvelope.input.topic);

const failedMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_demello_fail', {}), env)).json();
modalDispatchStatus = 503;
const failedDispatch = await worker.fetch(mkReq('POST', '/api/run', demelloInput, {
  Authorization: `Bearer ${failedMe.api_key}`, 'Idempotency-Key': 'demello-failed-dispatch-001',
}), demelloEnv);
modalDispatchStatus = 202;
const failedBody = await failedDispatch.json();
const failedAfter = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_demello_fail', {}), env)).json();
check('demello: explicit Modal dispatch failure refunds exactly once', failedDispatch.status === 502 && failedBody.status === 'failed' && failedBody.state === 'refunded' && failedAfter.balance_usd === 5);
const lateCompletion = await worker.fetch(mkReq('POST', `/api/run/${failedBody.run_id}/progress`, {
  run_id: failedBody.run_id, status: 'completed', video_url: 'https://modal.invalid/late', contact_sheet_url: 'https://modal.invalid/late-sheet',
}, { Authorization: 'Bearer progress-webhook-test-secret' }), demelloEnv);
const lateCompletionBody = await lateCompletion.json();
check('demello: refunded failure is authoritative against a late completion race', lateCompletion.status === 502 && lateCompletionBody.status === 'failed' && lateCompletionBody.state === 'refunded');

const artifactMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_demello_artifact', {}), env)).json();
const artifactRun = await (await worker.fetch(mkReq('POST', '/api/run', demelloInput, {
  Authorization: `Bearer ${artifactMe.api_key}`, 'Idempotency-Key': 'demello-bad-artifact-001',
}), demelloEnv)).json();
modalStatuses.set(artifactRun.run_id, {
  run_id: artifactRun.run_id, status: 'completed',
  video_url: `https://modal.invalid/v1/artifacts/${artifactRun.run_id}/video.mp4?expires=9999999999&signature=test&signature=duplicate`,
  contact_sheet_url: await modalArtifactUrl(artifactRun.run_id, 'contact-sheet.jpg'),
});
const badArtifactResponse = await worker.fetch(mkReq('GET', `/api/run/${artifactRun.run_id}`, {}, { Authorization: `Bearer ${artifactMe.api_key}` }), demelloEnv);
const artifactAfter = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_demello_artifact', {}), env)).json();
check('demello: malformed/overlong artifact signatures fail closed before settlement', badArtifactResponse.status === 502 && artifactAfter.balance_usd === 5);

const wrongOwnerMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_wrong_owner', {}), env)).json();
const wrongOwner = await worker.fetch(mkReq('GET', `/api/run/${demelloStart.run_id}`, {}, { Authorization: `Bearer ${wrongOwnerMe.api_key}` }), demelloEnv);
check('demello: run polling is owner-scoped', wrongOwner.status === 404);

// ── /api/topup (Stripe Checkout for credits) ──────────────────────────────

const tp501 = await worker.fetch(mkReq('POST', '/api/topup', { user_id: 'user_111', amount_usd: 20 }), env);
check('topup: no secret key returns 501', tp501.status === 501);

const badTopup = await worker.fetch(mkReq('POST', '/api/topup', { user_id: 'user_111', amount_usd: 20 }), stripeEnv);
check('topup: real mode requires a Clerk token', badTopup.status === 401);
const badTopup2 = await worker.fetch(mkReq('POST', '/api/topup', { user_id: 'user_111', amount_usd: 4 }, user111Headers), stripeEnv);
const badTopupType = await worker.fetch(mkReq('POST', '/api/topup', { user_id: 'user_111', amount_usd: '7' }, user111Headers), stripeEnv);
const badTopupMax = await worker.fetch(mkReq('POST', '/api/topup', { user_id: 'user_111', amount_usd: 1000.01 }, user111Headers), stripeEnv);
check('topup: rejects below-min, string, and over-max amounts', badTopup2.status === 400 && badTopupType.status === 400 && badTopupMax.status === 400);

const tp = await (await worker.fetch(mkReq('POST', '/api/topup', { user_id: 'user_attacker', amount_usd: 7 }, user111Headers), stripeEnv)).json();
check('topup: returns Stripe Checkout url', tp.url === 'https://checkout.stripe.com/c/pay/test_123');

const tpc = stripeCalls[stripeCalls.length - 1];
const tpcParams = new URLSearchParams(tpc.body);
check('topup: custom $7 becomes a 700-cent unit_amount', tpcParams.get('line_items[0][price_data][unit_amount]') === '700');
check('topup: success_url goes to dashboard', (tpcParams.get('success_url') || '').includes('dashboard.html?topup=success'));
check('topup: verified user overrides body user in reference + metadata', tpcParams.get('client_reference_id') === 'user_111' && tpcParams.get('metadata[user_id]') === 'user_111');

// ── /api/clerk-webhook (user.created → $5 grant) ──────────────────────────

const wh1 = await (await worker.fetch(mkReq('POST', '/api/clerk-webhook', { type: 'user.created', data: { id: 'user_clerk1', email_addresses: [{ email_address: 'a@b.co' }] } }), env)).json();
check('webhook: user.created grants $5', wh1.ok === true && wh1.granted === true && wh1.balance === '5.00' && wh1.balance_cents === 500);

const wh2 = await (await worker.fetch(mkReq('POST', '/api/clerk-webhook', { type: 'user.created', data: { id: 'user_clerk1' } }), env)).json();
check('webhook: second user.created does NOT double-grant', wh2.ok === true && wh2.granted === false && wh2.balance === '5.00');

const wh3 = await (await worker.fetch(mkReq('POST', '/api/clerk-webhook', { type: 'user.updated', data: { id: 'user_clerk1' } }), env)).json();
check('webhook: non user.created events are ignored', wh3.ok === true && wh3.ignored === true);

const whBad = await worker.fetch(Object.assign(mkReq('POST', '/api/clerk-webhook', {}), {
  text: async () => 'not-json{{{',
}), env);
check('webhook: invalid json returns 400', whBad.status === 400);

// Without CLERK_WEBHOOK_SECRET demo grants, while real mode fails closed.
const whNoSig = await worker.fetch(mkReq('POST', '/api/clerk-webhook', { type: 'user.created', data: { id: 'user_clerk2' } }), env);
const whRealNoSecret = await worker.fetch(mkReq('POST', '/api/clerk-webhook', { type: 'user.created', data: { id: 'user_clerk3' } }), realEnv);
check('webhook: unsigned demo works; real mode without secret fails closed', whNoSig.status === 200 && whRealNoSecret.status === 503);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
