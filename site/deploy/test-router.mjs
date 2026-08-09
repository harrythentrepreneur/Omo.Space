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
const src = fs.readFileSync(path.join(here, 'worker.js'), 'utf8');
const cjs = src.replace('export default', 'const __workerExport =');

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
check('router: unknown route returns 404 + routes list', nf.status === 404 && Array.isArray(nfBody.routes) && nfBody.routes.length === 5);

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

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
