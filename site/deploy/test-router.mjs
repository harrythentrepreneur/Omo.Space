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
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));

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

const sandbox = {
  fetch: async (url, opts) => {
    if (String(url).includes('api.stripe.com')) {
      stripeCalls.push({ url: String(url), body: String(opts.body), headers: opts.headers });
      return {
        ok: true,
        status: 200,
        json: async () => ({ url: 'https://checkout.stripe.com/c/pay/test_123' }),
      };
    }
    const body = JSON.parse(opts.body);
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
  JSON,
  Date,
  String,
  Number,
  Array,
  Object,
  console,
};
vm.createContext(sandbox);
vm.runInContext(`${cjs}\n;globalThis.__workerExport = __workerExport;`, sandbox, { filename: 'worker.js' });
const worker = sandbox.__workerExport;

const env = { LLM_API_KEY: 'test-key', LLM_BASE_URL: 'https://llm.invalid/v1', LLM_MODEL: 'test-model' };

let pass = 0;
let fail = 0;
function check(name, cond) {
  if (cond) { pass += 1; console.log(`PASS  ${name}`); }
  else { fail += 1; console.log(`FAIL  ${name}`); }
}

const mkReq = (method, pathname, body) => ({
  method,
  url: `https://demo.cognition.cv${pathname}`,
  headers: new Map([['CF-Connecting-IP', '203.0.113.9'], ['Content-Type', 'application/json']]),
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
  system_prompt: 'You write marketplace listing copy. Output JSON with title, bullets, description.',
  fields: { description: 'ceramic mug', marketplace: 'etsy' },
}), env)).json();
check('run: generic route returns ok + output', run.ok === true && run.slug === 'listing-copy-engine' && run.output.hook === 'stop scrolling');
const badRun = await worker.fetch(mkReq('POST', '/api/run', { slug: '', system_prompt: '' }), env);
check('run: missing slug/prompt returns 400', badRun.status === 400);

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

const stripeEnv = { ...env, STRIPE_SECRET_KEY: 'sk_test_fake_secret' };

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
check('checkout: unit_amount is priceUsd * 100', scParams.get('line_items[0][price_data][unit_amount]') === '2500');
check('checkout: currency + mode + quantity set', scParams.get('line_items[0][price_data][currency]') === 'usd' && scParams.get('mode') === 'payment' && scParams.get('line_items[0][quantity]') === '1');
check('checkout: success_url carries the slug', (scParams.get('success_url') || '').includes('purchased=ugc-script-studio'));
check('checkout: cancel_url set', (scParams.get('cancel_url') || '').includes('purchased=cancelled'));
check('checkout: buyer email forwarded', scParams.get('customer_email') === 'buyer@example.com');
check('checkout: bearer auth uses the secret (never logged)', (sc.headers.Authorization || '') === 'Bearer sk_test_fake_secret');

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
check('me: creates a user with the $10 signup grant', me1.ok === true && me1.balance === '10.00' && me1.balance_usd === 10 && me1.balance_cents === 1000);
check('me: currency is usd + mock flag set without D1', me1.currency === 'usd' && me1.mock === true);
check('me: api key is a deterministic omo_ key', /^omo_[0-9a-f]{32}$/.test(me1.api_key));
check('me: usage list starts empty', Array.isArray(me1.runs) && me1.runs.length === 0);

const me2 = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_111', {}), env)).json();
check('me: repeat visit does NOT double-grant (still $10)', me2.balance_usd === 10);
check('me: api key is stable across visits', me2.api_key === me1.api_key);

const meBad = await worker.fetch(mkReq('GET', '/api/me', {}), env);
check('me: missing user_id returns 400', meBad.status === 400);

// ── /api/run with user_id → debits the balance ────────────────────────────

const runPaid = await (await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'listing-copy-engine',
  system_prompt: 'You write marketplace listing copy. Output JSON with title, bullets, description.',
  fields: { description: 'ceramic mug' },
  user_id: 'user_111',
}), env)).json();
check('run: paid run succeeds and reports cost + new balance', runPaid.ok === true && runPaid.cost_usd === 0.1 && runPaid.balance === 9.9);

const me3 = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_111', {}), env)).json();
check('run: balance debited after run ($9.90)', me3.balance_usd === 9.9);
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
check('run: 402 carries balance + cost + shortfall', poorBody.balance === 0.05 && poorBody.cost_usd === 0.1 && poorBody.shortfall_usd === 0.05);

const lowMe2 = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_low', {}), lowEnv)).json();
check('run: 402 leaves the balance untouched (still $0.05)', lowMe2.balance_usd === 0.05 && lowMe2.runs.length === 0);

// ── /api/topup (Stripe Checkout for credits) ──────────────────────────────

const tp501 = await worker.fetch(mkReq('POST', '/api/topup', { user_id: 'user_111', amount_usd: 25 }), env);
check('topup: no secret key returns 501', tp501.status === 501);

const badTopup = await worker.fetch(mkReq('POST', '/api/topup', { user_id: '', amount_usd: 25 }), stripeEnv);
check('topup: missing user_id returns 400', badTopup.status === 400);
const badTopup2 = await worker.fetch(mkReq('POST', '/api/topup', { user_id: 'user_111', amount_usd: -5 }), stripeEnv);
check('topup: negative amount returns 400', badTopup2.status === 400);

const tp = await (await worker.fetch(mkReq('POST', '/api/topup', { user_id: 'user_111', amount_usd: 25 }), stripeEnv)).json();
check('topup: returns Stripe Checkout url', tp.url === 'https://checkout.stripe.com/c/pay/test_123');

const tpc = stripeCalls[stripeCalls.length - 1];
const tpcParams = new URLSearchParams(tpc.body);
check('topup: unit_amount is amount_usd * 100', tpcParams.get('line_items[0][price_data][unit_amount]') === '2500');
check('topup: success_url goes to dashboard', (tpcParams.get('success_url') || '').includes('dashboard.html?topup=success'));
check('topup: user carried as client_reference_id + metadata', tpcParams.get('client_reference_id') === 'user_111' && tpcParams.get('metadata[user_id]') === 'user_111');

// ── /api/clerk-webhook (user.created → $10 grant) ─────────────────────────

const wh1 = await (await worker.fetch(mkReq('POST', '/api/clerk-webhook', { type: 'user.created', data: { id: 'user_clerk1', email_addresses: [{ email_address: 'a@b.co' }] } }), env)).json();
check('webhook: user.created grants $10', wh1.ok === true && wh1.granted === true && wh1.balance === '10.00' && wh1.balance_cents === 1000);

const wh2 = await (await worker.fetch(mkReq('POST', '/api/clerk-webhook', { type: 'user.created', data: { id: 'user_clerk1' } }), env)).json();
check('webhook: second user.created does NOT double-grant', wh2.ok === true && wh2.granted === false && wh2.balance === '10.00');

const wh3 = await (await worker.fetch(mkReq('POST', '/api/clerk-webhook', { type: 'user.updated', data: { id: 'user_clerk1' } }), env)).json();
check('webhook: non user.created events are ignored', wh3.ok === true && wh3.ignored === true);

const whBad = await worker.fetch(Object.assign(mkReq('POST', '/api/clerk-webhook', {}), {
  text: async () => 'not-json{{{',
}), env);
check('webhook: invalid json returns 400', whBad.status === 400);

// Without CLERK_WEBHOOK_SECRET the signature check is skipped (mock mode).
const whNoSig = await worker.fetch(mkReq('POST', '/api/clerk-webhook', { type: 'user.created', data: { id: 'user_clerk2' } }), env);
check('webhook: no secret → signature skipped, grant works', whNoSig.status === 200);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
