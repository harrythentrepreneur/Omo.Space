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
  const payload = encode({ sub: userId, iss: `https://${clerkFrontendApi}`, azp: 'https://omo.space', iat: now, nbf: now - 1, exp: now + 60 });
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

async function signedStripeRequest(event, secret) {
  const raw = JSON.stringify(event);
  const timestamp = Math.floor(Date.now() / 1000);
  const key = await webcrypto.subtle.importKey(
    'raw', new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
  );
  const mac = await webcrypto.subtle.sign(
    'HMAC', key, new TextEncoder().encode(`${timestamp}.${raw}`),
  );
  const signature = Buffer.from(mac).toString('hex');
  return Object.assign(mkReq('POST', '/api/topup', event, {
    'Stripe-Signature': `t=${timestamp},v1=${signature}`,
  }), { text: async () => raw });
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
const prelude = stripModule('balance.mjs') + '\n'
  + stripModule('cost-model.mjs') + '\n'
  + stripModule('hosted-skills.generated.mjs') + '\n';
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
const wovenCalls = [];
const wovenStatuses = new Map();
const facebookCalls = [];
const facebookStatuses = new Map();
const facebookCases = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'containers', 'facebook-ads-copywriter', 'tests', 'cases.json'), 'utf8'));
let workerNativeMode = 'valid';
const neonSqlCalls = [];
let neonPoolShouldThrow = false;
let neonInfoSchemaTableExists = false;
let neonInfoSchemaColumns = [];
let neonApprovalRow = null;
let neonInternalDetailRow = null;

class MockPool {
  constructor(options) {
    this.options = options;
  }

  async connect() {
    const poolOptions = this.options;
    return {
      async query(query) {
        const entry = typeof query === 'string'
          ? { text: query, values: null, name: null, connectionString: poolOptions.connectionString }
          : { text: query.text, values: query.values || [], name: query.name, connectionString: poolOptions.connectionString };
        neonSqlCalls.push(entry);
        if (neonPoolShouldThrow && (entry.text.startsWith('ALTER TABLE') || entry.text.includes('information_schema'))) {
          throw new Error(`leaked dsn ${poolOptions.connectionString}`);
        }
        if (entry.text.includes('information_schema.tables')) {
          return { rows: [{ table_exists: neonInfoSchemaTableExists }], rowCount: 1 };
        }
        if (entry.text.includes('information_schema.columns')) {
          return { rows: neonInfoSchemaColumns.map((column_name) => ({ column_name })), rowCount: neonInfoSchemaColumns.length };
        }
        if (entry.name === 'omo-submission-approve-v1') {
          return neonApprovalRow ? { rows: [neonApprovalRow], rowCount: 1 } : { rows: [], rowCount: 0 };
        }
        if (entry.name === 'omo-internal-submission-detail-v1') {
          return neonInternalDetailRow ? { rows: [neonInternalDetailRow], rowCount: 1 } : { rows: [], rowCount: 0 };
        }
        return { rows: [], rowCount: 0 };
      },
      release() {
        neonSqlCalls.push({ text: 'RELEASE', values: null, name: null, connectionString: poolOptions.connectionString });
      },
    };
  }

  async end() {
    neonSqlCalls.push({ text: 'POOL_END', values: null, name: null, connectionString: this.options.connectionString });
  }
}

function llmResponse(status, envelope) {
  const text = JSON.stringify(envelope);
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => text,
    json: async () => envelope,
  };
}

const sandbox = {
  fetch: async (url, opts) => {
    if (String(url).startsWith('https://woven.modal.invalid')) {
      const target = new URL(String(url));
      wovenCalls.push({ url: String(url), method: opts && opts.method || 'GET', headers: opts && opts.headers, body: opts && opts.body });
      if (target.pathname === '/v1/runs' && opts && opts.method === 'POST') {
        const callId = 'fc-WOVENROUTER0001';
        wovenStatuses.set(callId, { status: 202, body: { call_id: callId, status: 'running' } });
        return { ok: true, status: 202, json: async () => ({ run_id: 'modal-submit-id', call_id: callId, status: 'accepted', result_url: `/v1/runs/${callId}` }) };
      }
      const callId = target.pathname.split('/').at(-1);
      const value = wovenStatuses.get(callId);
      return value
        ? { ok: value.status >= 200 && value.status < 300, status: value.status, json: async () => value.body }
        : { ok: false, status: 404, json: async () => ({ detail: 'run_not_found' }) };
    }
    if (String(url).startsWith('https://facebook.modal.invalid')) {
      const target = new URL(String(url));
      facebookCalls.push({ url: String(url), method: opts && opts.method || 'GET', headers: opts && opts.headers, body: opts && opts.body });
      if (target.pathname === '/v1/runs' && opts && opts.method === 'POST') {
        const callId = 'fc-FACEBOOKROUTER01';
        facebookStatuses.set(callId, { status: 202, body: { call_id: callId, status: 'running' } });
        return { ok: true, status: 202, json: async () => ({ run_id: 'modal-facebook-submit', call_id: callId, status: 'accepted', result_url: `/v1/runs/${callId}` }) };
      }
      const callId = target.pathname.split('/').at(-1);
      const value = facebookStatuses.get(callId);
      return value
        ? { ok: value.status >= 200 && value.status < 300, status: value.status, json: async () => value.body }
        : { ok: false, status: 404, json: async () => ({ detail: 'run_not_found' }) };
    }
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
      stripeCalls.push({ url: String(url), method: opts.method, body: String(opts.body), headers: opts.headers });
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 'cs_test_123', url: 'https://checkout.stripe.com/c/pay/test_123' }),
      };
    }
    const body = JSON.parse(opts.body);
    llmCalls.push(body);
    const system = body.messages.find((m) => m.role === 'system').content;
    if (system.includes('senior Facebook ads copywriter')) {
      if (workerNativeMode === 'provider_error') {
        return { ok: false, status: 503, text: async () => 'provider down', json: async () => ({ error: { message: 'provider down' } }) };
      }
      if (workerNativeMode === 'invalid_json') {
        return llmResponse(200, { choices: [{ message: { content: 'not json today' } }] });
      }
      if (workerNativeMode === 'invalid_schema') {
        return llmResponse(200, { choices: [{ message: { content: '{"status":"completed"}' } }] });
      }
      return llmResponse(200, { choices: [{ message: { content: JSON.stringify(facebookCases.happy_path.output) } }] });
    }
    const user = body.messages.find((m) => m.role === 'user').content;
    let route = '/api/ugc-script-studio';
    if (user.includes('Ads export')) route = '/api/meta-ads-analyser';
    if (user.includes('Plan the shot list')) route = '/api/product-photo-generator';
    return llmResponse(200, { choices: [{ message: { content: canned[route] } }] });
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
  Pool: MockPool,
  neon: (connectionString) => ({
    query: async (text, values = []) => {
      const entry = {
        text,
        values,
        name: text.includes('WITH updated AS') && text.includes("failure_code = 'slug_collision'")
          ? 'omo-submission-approve-v1'
          : text.includes('WITH updated AS') && text.includes('failure_code IN')
            ? 'omo-submission-retry-v1'
            : text.includes('SELECT id,slug,source_sha256,selected_runtime') && text.includes('WHERE id = $1')
              ? 'omo-internal-submission-detail-v1'
              : null,
        connectionString,
      };
      neonSqlCalls.push(entry);
      if (entry.name === 'omo-submission-approve-v1' || entry.name === 'omo-submission-retry-v1') {
        return neonApprovalRow ? { rows: [neonApprovalRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-submission-detail-v1') {
        return neonInternalDetailRow ? { rows: [neonInternalDetailRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      return { rows: [], rowCount: 0 };
    },
  }),
};
vm.createContext(sandbox);
vm.runInContext(`${cjs}\n;globalThis.__workerExport = __workerExport;globalThis.__workerTest = { mockSubmissions, constantTimeEquals, SUBMISSIONS_SCHEMA_MIGRATIONS, REQUIRED_SUBMISSIONS_COLUMNS, reviewedSourceApprovalAllowlist };`, sandbox, { filename: 'worker.js' });
const worker = sandbox.__workerExport;
const workerTest = sandbox.__workerTest;

const env = { LLM_API_KEY: 'test-key', LLM_BASE_URL: 'https://llm.invalid/v1', LLM_MODEL: 'test-model' };
// Encodes example.clerk.accounts.dev$; API-key tests do not need a JWKS fetch.
const realEnv = { ...env, CLERK_PUBLISHABLE_KEY: clerkPublishableKey };

let pass = 0;
let fail = 0;
function check(name, cond) {
  if (cond) { pass += 1; console.log(`PASS  ${name}`); }
  else { fail += 1; console.log(`FAIL  ${name}`); }
}

check('Neon: Worker never caches request-bound Pool I/O in module scope',
  !workerSrc.includes('let neonPool') &&
  workerSrc.includes("neon(url, { fullResults: true })") &&
  (workerSrc.match(/await client\.release\(\)/g) || []).length === 7);

const dashboardSource = fs.readFileSync(path.join(here, '..', 'dashboard.html'), 'utf8');
const billingSource = fs.readFileSync(path.join(here, '..', 'billing.html'), 'utf8');
const creditsSource = fs.readFileSync(path.join(here, '..', 'credits.js'), 'utf8');
const indexSource = fs.readFileSync(path.join(here, '..', 'index.html'), 'utf8');
const runPageSource = fs.readFileSync(path.join(here, '..', 'run.html'), 'utf8');
const sellSource = fs.readFileSync(path.join(here, '..', 'sell.html'), 'utf8');
const hostSource = fs.readFileSync(path.join(here, '..', 'host.html'), 'utf8');
const uploadSource = fs.readFileSync(path.join(here, '..', 'upload.js'), 'utf8');
const catalogSandbox = { window: {} };
vm.createContext(catalogSandbox);
vm.runInContext(fs.readFileSync(path.join(here, '..', 'catalog.js'), 'utf8'), catalogSandbox, { filename: 'catalog.js' });
const wovenListing = catalogSandbox.window.OMO_CATALOG.find((listing) => listing.slug === 'woven-relationship-book-maker');
const wovenRunManifest = JSON.parse(fs.readFileSync(path.join(here, '..', 'run-manifests', 'woven-relationship-book-maker.json'), 'utf8'));
const wovenContainerInput = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'containers', 'woven-storybook-pipeline', 'schemas', 'input.json'), 'utf8'));
const wovenContainerOutput = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'containers', 'woven-storybook-pipeline', 'schemas', 'output.json'), 'utf8'));
const facebookListing = catalogSandbox.window.OMO_CATALOG.find((listing) => listing.slug === 'facebook-ads-copywriter');
const facebookRunManifest = JSON.parse(fs.readFileSync(path.join(here, '..', 'run-manifests', 'facebook-ads-copywriter.json'), 'utf8'));
const facebookContainerInput = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'containers', 'facebook-ads-copywriter', 'schemas', 'input.json'), 'utf8'));
const facebookContainerOutput = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'containers', 'facebook-ads-copywriter', 'schemas', 'output.json'), 'utf8'));
const canonical = (value) => Array.isArray(value)
  ? value.map(canonical)
  : value && typeof value === 'object'
    ? Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]))
    : value;
check('account client: dashboard uses the shared Clerk-authenticated /api/me balance', dashboardSource.includes('<script src="credits.js"></script>') && dashboardSource.includes('window.OmoCredits.getBalance') && creditsSource.includes("fetch(apiBase() + '/api/me'") && creditsSource.includes("Authorization: 'Bearer ' + token"));
check('dashboard: cloud-run network errors never fall back to a mock after POST', (dashboardSource.match(/startMockVideoRun\(form, product\);/g) || []).length === 1 && dashboardSource.includes('The submission outcome is unknown') && dashboardSource.includes('Reconcile run'));
check('dashboard: terminal 5xx run states are handled before indefinite retry', dashboardSource.includes("terminalStatus === 'failed' || terminalStatus === 'refunded'") && dashboardSource.includes("status === 'failed' || status === 'refunded'"));
check('billing: server top-ups post to /api/topup with Clerk bearer + persistent idempotency', billingSource.includes("fetch(apiBase() + '/api/topup'") && billingSource.includes("Authorization: 'Bearer ' + token") && billingSource.includes("'Idempotency-Key': topupKey") && billingSource.includes('omo_topup_attempt_v1'));
check('billing: verified account snapshot is user-scoped and excludes the API key', creditsSource.includes('omo_verified_account_v1:') && creditsSource.includes('readVerifiedSnapshot') && creditsSource.includes('writeVerifiedSnapshot') && !creditsSource.includes('apiKey: account.apiKey'));
check('billing: cached account renders immediately before background validation', billingSource.includes('window.OmoCredits.getCachedBalance') && billingSource.includes("window.OmoCredits.getBalance({ force: true, preserve: true })"));
check('billing: stale cache is labelled and never used for top-up authorization', billingSource.includes('Last verified') && billingSource.includes("account.mode === 'server'") && billingSource.includes('getSessionToken().then'));
check('dashboard: hosted video form exposes the sample-only provider gate', dashboardSource.includes('Hosted staging currently accepts only sample-demello-10s'));
check('run manifest: Woven browser schemas stay aligned with generated container input/output', JSON.stringify(canonical(wovenRunManifest.input_schema)) === JSON.stringify(canonical(wovenContainerInput)) && JSON.stringify(canonical(wovenRunManifest.output_schema)) === JSON.stringify(canonical(wovenContainerOutput)));
check('catalog: Woven listing and hosted manifest publish the same $0.40 run price', wovenListing.runPrice === 0.4 && wovenRunManifest.price_usd === 0.4 && wovenListing.runManifest === 'run-manifests/woven-relationship-book-maker.json');
check('run manifest: Facebook Ads browser schemas stay aligned with its generated container', JSON.stringify(canonical(facebookRunManifest.input_schema)) === JSON.stringify(canonical(facebookContainerInput)) && JSON.stringify(canonical(facebookRunManifest.output_schema)) === JSON.stringify(canonical(facebookContainerOutput)));
check('catalog: Facebook Ads listing and hosted manifest publish the modeled $0.10 price', facebookListing.runPrice === 0.1 && facebookRunManifest.price_usd === 0.1 && facebookListing.runManifest === 'run-manifests/facebook-ads-copywriter.json');
check('catalog cards: per-run prices render to two decimal places', indexSource.includes("Number(p.runPrice || p.priceRun || 0).toFixed(2)"));
check('run page: compiled manifests drive typed form rendering and async polling', runPageSource.includes('listing.runManifest') && runPageSource.includes('resolveField') && runPageSource.includes('renderField') && runPageSource.includes('pollRun'));
check('run page: empty API base dispatches through the deployed same-origin Worker rewrite', runPageSource.includes("function workerBase() { return API_BASE || window.location.origin; }"));
check('creator upload: seller CTA reaches a real file-reading authenticated queue with honest local-only rollout receipts', sellSource.includes('href="host.html#upload"') && hostSource.includes('id="upload-form"') && uploadSource.includes('await selectedFile.text()') && uploadSource.includes("fetch(apiBase() + '/api/submit'") && uploadSource.includes("Authorization: 'Bearer ' + token") && uploadSource.includes('if (isFilePreview())') && uploadSource.includes("error.code === 'queue_unavailable'") && uploadSource.includes('not the Markdown') && !uploadSource.includes('startProgress'));
check('creator upload: browser persists only server submission ids and restores from owner APIs',
  uploadSource.includes("fetchJsonWithAuth('/api/submissions?limit=20')") &&
  uploadSource.includes("fetchJsonWithAuth('/api/submissions/' + encodeURIComponent") &&
  uploadSource.includes('writeSubmissionIds') &&
  uploadSource.includes('readSubmissionIds') &&
  !uploadSource.includes('localStorage.setItem(STORAGE_KEY, JSON.stringify(submissions)'));
check('creator upload: reload waits for Clerk auth readiness and never renders auth startup as an empty queue',
  uploadSource.includes('ClerkAuth.ensureLoaded') &&
  uploadSource.includes('ClerkAuth.onAuthChange') &&
  uploadSource.includes("setSubmissionMessage('Loading your submissions…')") &&
  uploadSource.includes("setSubmissionMessage('Sign in to see your submissions.')") &&
  !uploadSource.includes('restoreSubmissionsAfterReload(attempt)'));
check('creator upload: reload restores the latest browser submission progress from server state',
  uploadSource.includes('var savedIds = readSubmissionIds();') &&
  uploadSource.includes('var focusId = savedIds.length ? savedIds[savedIds.length - 1] : null;') &&
  uploadSource.includes('return refreshSubmissions(focusId);') &&
  !uploadSource.includes('localStorage.setItem(STORAGE_KEY, JSON.stringify(submissions)'));
check('creator upload: lifecycle UI is honest and opens workflow only after deployment',
  uploadSource.includes('runtimeDecisionText') &&
  uploadSource.includes('Open workflow') &&
  uploadSource.includes("submission.status === 'deployed' && submission.published_slug") &&
  uploadSource.includes('Queued for review') &&
  uploadSource.includes('Build gates running') &&
  !uploadSource.includes('automated research'));
check('creator upload: exact-match slug collision approval is visible, confirmed, disabled while pending, refreshed, and error-rendered',
  uploadSource.includes('Approve exact-match update') &&
  uploadSource.includes('approval sends it back through build/test/deploy gates and does not instantly publish') &&
  uploadSource.includes("submission.status === 'needs_review'") &&
  uploadSource.includes("submission.failure_code === 'slug_collision'") &&
  uploadSource.includes("fetch(apiBase() + '/api/submissions/' + encodeURIComponent(submission.id) + '/approve'") &&
  uploadSource.includes("Authorization: 'Bearer ' + token") &&
  uploadSource.includes('button.disabled = true') &&
  uploadSource.includes('aria-live') &&
  uploadSource.includes('refreshSubmissions(submission.id)') &&
  uploadSource.includes('fetchSubmissionDetail(submission.id)'));
check('creator upload: failed approved exact-match release retry is visible, confirmed, disabled while pending, refreshed, and error-rendered',
  uploadSource.includes('Retry gated build') &&
  uploadSource.includes('Gated release failed after owner approval') &&
  uploadSource.includes("submission.status === 'failed'") &&
  uploadSource.includes("isRetryableExactMatchReleaseFailure(submission)") &&
  uploadSource.includes("submission.failure_code === 'build_or_deploy_failed'") &&
  uploadSource.includes("submission.failure_code === 'canary_or_internal_failed'") &&
  uploadSource.includes("submission.approval_reason === 'exact_source_slug_collision'") &&
  uploadSource.includes("fetch(apiBase() + '/api/submissions/' + encodeURIComponent(submission.id) + '/retry'") &&
  uploadSource.includes("Authorization: 'Bearer ' + token") &&
  uploadSource.includes('button.disabled = true') &&
  uploadSource.includes('aria-live') &&
  uploadSource.includes('refreshSubmissions(submission.id)') &&
  uploadSource.includes('fetchSubmissionDetail(submission.id)'));
check('creator upload: Git-backed release progress renders issue/PR/merge links without client repo controls',
  uploadSource.includes('renderReleaseLinks(submission)') &&
  uploadSource.includes('submission.release.issue_url') &&
  uploadSource.includes('submission.release.pr_url') &&
  uploadSource.includes('submission.release.merge_sha') &&
  !uploadSource.includes('client_branch') &&
  !uploadSource.includes('client_repo'));

let browserCheckoutCall = null;
const stripeClientSandbox = {
  window: { location: { href: '' } },
  fetch: async (url, opts) => {
    browserCheckoutCall = { url, opts };
    return { status: 200, json: async () => ({ url: 'https://checkout.stripe.com/c/pay/browser_test' }) };
  },
};
vm.createContext(stripeClientSandbox);
vm.runInContext(fs.readFileSync(path.join(here, '..', 'stripe.js'), 'utf8'), stripeClientSandbox, { filename: 'stripe.js' });
await stripeClientSandbox.window.StripePay.checkout('ugc-script-studio', { priceOwn: 39 }, null, {});
check('checkout client: placeholder key still posts idempotently + redirects', browserCheckoutCall && browserCheckoutCall.url === '/api/checkout' && JSON.parse(browserCheckoutCall.opts.body).slug === 'ugc-script-studio' && /^checkout-[A-Za-z0-9-]{8,}$/.test(browserCheckoutCall.opts.headers['Idempotency-Key']) && stripeClientSandbox.window.location.href === 'https://checkout.stripe.com/c/pay/browser_test');

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
check('router: unknown route returns 404 + routes list', nf.status === 404 && Array.isArray(nfBody.routes) && nfBody.routes.length === 11);

// Public waitlist signup: normalized insert, validation, and duplicate replay.
const waitlistAddedResponse = await worker.fetch(mkReq('POST', '/api/waitlist', {
  email: '  Launch.Test@Example.com  ', source: 'creators',
}), env);
const waitlistAdded = await waitlistAddedResponse.json();
check('waitlist: valid email is normalized and inserted', waitlistAddedResponse.status === 200 && waitlistAdded.ok === true && waitlistAdded.status === 'added');

const waitlistInvalid = await worker.fetch(mkReq('POST', '/api/waitlist', {
  email: 'not-an-email', source: 'creators',
}), env);
check('waitlist: invalid email returns 400', waitlistInvalid.status === 400);

const waitlistDuplicateResponse = await worker.fetch(mkReq('POST', '/api/waitlist', {
  email: 'launch.test@example.com', source: 'sell',
}), env);
const waitlistDuplicate = await waitlistDuplicateResponse.json();
check('waitlist: duplicate email returns already without error', waitlistDuplicateResponse.status === 200 && waitlistDuplicate.ok === true && waitlistDuplicate.status === 'already');

// Authenticated creator submission: bounded Markdown, canonical metadata, and
// owner/content idempotency. It queues data but never executes the upload.
const submissionContent = '---\nname: sample-workflow\ndescription: A safe sample creator workflow.\n---\n\n## Workflow\n\n1. **Read:** Read the brief.\n';
const submitMissingAuth = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Sample workflow', content: submissionContent,
}), realEnv);
check('submit: real mode requires a Clerk session', submitMissingAuth.status === 401);

const creatorToken = await clerkToken('user_creator');
const creatorHeaders = { Authorization: `Bearer ${creatorToken}`, Origin: 'https://omo.space' };
const submitAddedResponse = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Sample workflow', content: submissionContent, visibility: 'public', runtime_preference: 'worker-native',
}, creatorHeaders), realEnv);
const submitAdded = await submitAddedResponse.json();
check('submit: valid Markdown queues with server-derived slug and stored runtime preference', submitAddedResponse.status === 202 && submitAdded.ok === true && /^sub_[0-9a-f]{32}$/.test(submitAdded.id) && submitAdded.slug === 'sample-workflow' && submitAdded.status === 'queued' && submitAdded.duplicate === false && submitAdded.runtime_preference === 'worker-native' && submitAdded.compatibility === 'pending_review' && submitAdded.changed === true && !('selected_runtime' in submitAdded) && !('requested_runtime' in submitAdded));

const submitDuplicate = await (await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Sample workflow', content: submissionContent, runtime_preference: 'worker-native',
}, creatorHeaders), realEnv)).json();
check('submit: same owner and content replay returns the same queue record and preserves original runtime preference', submitDuplicate.id === submitAdded.id && submitDuplicate.status === 'queued' && submitDuplicate.duplicate === true && submitDuplicate.runtime_preference === 'worker-native' && submitDuplicate.changed === false);

const submitDuplicateConflict = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Sample workflow', content: submissionContent, runtime_preference: 'modal-hosted',
}, creatorHeaders), realEnv);
check('submit: same owner and content with different runtime preference conflicts', submitDuplicateConflict.status === 409);

const autoSubmissionContent = '---\nname: auto-workflow\ndescription: Another safe sample creator workflow.\n---\n\n## Workflow\n\n1. **Read:** Read the brief.\n';
const submitAutoResponse = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Auto workflow', content: autoSubmissionContent, requested_runtime: 'auto', selected_runtime: 'worker-native', compatibility: { worker: true },
}, creatorHeaders), realEnv);
const submitAuto = await submitAutoResponse.json();
check('submit: accepts tested requested_runtime alias and ignores client-selected placement fields', submitAutoResponse.status === 202 && submitAuto.runtime_preference === 'auto' && submitAuto.compatibility === 'pending_review' && !('selected_runtime' in submitAuto) && !('requested_runtime' in submitAuto));

const submitBadRuntime = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Sample workflow', content: submissionContent, runtime_preference: 'edge-magic',
}, creatorHeaders), realEnv);
check('submit: invalid runtime preference is rejected', submitBadRuntime.status === 400);

const submitConflictingRuntimeAliases = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Sample workflow', content: submissionContent, runtime_preference: 'worker-native', requested_runtime: 'modal-hosted',
}, creatorHeaders), realEnv);
check('submit: conflicting runtime preference aliases are rejected', submitConflictingRuntimeAliases.status === 400);

const changedRuntimeResponse = await worker.fetch(mkReq('PATCH', `/api/submissions/${submitAdded.id}/runtime`, {
  runtime_preference: 'modal-hosted', selected_runtime: 'worker-native', compatibility: { unsafe: false },
}, creatorHeaders), realEnv);
const changedRuntime = await changedRuntimeResponse.json();
check('submit runtime: owner can change queued runtime preference only', changedRuntimeResponse.status === 200 && changedRuntime.ok === true && changedRuntime.id === submitAdded.id && changedRuntime.runtime_preference === 'modal-hosted' && changedRuntime.compatibility === 'pending_review' && changedRuntime.changed === true && !('selected_runtime' in changedRuntime) && !('requested_runtime' in changedRuntime));

const changedRuntimeReplay = await (await worker.fetch(mkReq('PATCH', `/api/submissions/${submitAdded.id}/runtime`, {
  runtime_preference: 'modal-hosted',
}, creatorHeaders), realEnv)).json();
check('submit runtime: repeated owner change is idempotent', changedRuntimeReplay.id === submitAdded.id && changedRuntimeReplay.runtime_preference === 'modal-hosted' && changedRuntimeReplay.changed === false);

const otherCreatorHeaders = { Authorization: `Bearer ${await clerkToken('user_other_creator')}`, Origin: 'https://omo.space' };
const nonOwnerRuntime = await worker.fetch(mkReq('PATCH', `/api/submissions/${submitAdded.id}/runtime`, {
  requested_runtime: 'auto',
}, otherCreatorHeaders), realEnv);
const missingRuntime = await worker.fetch(mkReq('PATCH', '/api/submissions/sub_00000000000000000000000000000000/runtime', {
  requested_runtime: 'auto',
}, creatorHeaders), realEnv);
const invalidRuntimePatch = await worker.fetch(mkReq('PATCH', `/api/submissions/${submitAdded.id}/runtime`, {
  requested_runtime: 'edge-magic',
}, creatorHeaders), realEnv);
check('submit runtime: non-owner, missing, and invalid changes fail closed', nonOwnerRuntime.status === 404 && missingRuntime.status === 404 && invalidRuntimePatch.status === 400);

for (const record of workerTest.mockSubmissions.values()) {
  if (record.id === submitAdded.id) record.status = 'processing';
}
const immutableRuntime = await worker.fetch(mkReq('PATCH', `/api/submissions/${submitAdded.id}/runtime`, {
  requested_runtime: 'auto',
}, creatorHeaders), realEnv);
check('submit runtime: processing and later states are immutable', immutableRuntime.status === 409);

const submitMismatch = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Different workflow', content: submissionContent,
}, creatorHeaders), realEnv);
const submitPrivate = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Sample workflow', content: submissionContent, visibility: 'private',
}, creatorHeaders), realEnv);
check('submit: name mismatch and unsupported private hosting fail closed', submitMismatch.status === 400 && submitPrivate.status === 400);

const boundaryPrefix = '---\nname: boundary-workflow\ndescription: Boundary-sized creator workflow.\n---\n\n## Workflow\n\n1. **Read:** Read.\n';
const boundaryContent = boundaryPrefix + 'x'.repeat(200 * 1024 - Buffer.byteLength(boundaryPrefix));
const submitBoundary = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Boundary workflow', content: boundaryContent,
}, creatorHeaders), realEnv);
const submitOversize = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Boundary workflow', content: boundaryContent + 'x',
}, creatorHeaders), realEnv);
check('submit: 200 KiB is accepted and the next byte is rejected', submitBoundary.status === 202 && submitOversize.status === 400);

for (const record of workerTest.mockSubmissions.values()) {
  if (record.id === submitAdded.id) {
    Object.assign(record, {
      status: 'deployed',
      selected_runtime: 'worker-native',
      runtime_policy: 'reviewed_profile_selected_worker',
      runtime_compatibility: JSON.stringify({
        recommended: 'worker-native',
        requested: 'modal-hosted',
        compatible: true,
        provider_config: { api_key_env: 'LLM_API_KEY', base_url: 'https://secret.invalid' },
        internal_error: 'stack trace should not leave the server',
      }),
      workflow_version: 'sample-workflow@1.0.0',
      published_slug: 'sample-workflow',
      build_evidence: JSON.stringify({
        checks: ['compile', 'router'],
        source_sha256: record.sourceSha256,
        secret: 'sk_test_secret',
        provider_config: { token: 'hidden' },
        log: 'internal failure text hidden',
      }),
      release_phase: 'promoted',
      release_issue_url: 'https://github.com/omo-space/marketplace/issues/31',
      release_pr_url: 'https://github.com/omo-space/marketplace/pull/42',
      release_pr_number: 42,
      release_branch: 'omo-release/sub_sample000000000000000001-sample-workflow',
      release_head_sha: 'a'.repeat(40),
      release_merge_sha: 'b'.repeat(40),
      release_artifact_hash: 'c'.repeat(64),
      modal_app: 'cognition-sample-workflow',
      modal_url: 'https://omo-space--cognition-sample-workflow-api.modal.run',
      canary_evidence: JSON.stringify({
        checked_at: '2026-08-14T00:09:00.000Z',
        status: 'passed',
        secret: 'must-not-leak',
      }),
      created_at: '2026-08-13T00:10:00.000Z',
      updated_at: '2026-08-13T00:10:00.000Z',
      deployed_at: '2026-08-13T00:10:00.000Z',
    });
  }
  if (record.id === submitAuto.id) {
    Object.assign(record, {
      created_at: '2026-08-13T00:20:00.000Z',
      updated_at: '2026-08-13T00:20:00.000Z',
      status: 'ready_for_deploy',
      selected_runtime: 'modal-hosted',
      runtime_policy: 'reviewed_profile_selected_modal',
      runtime_compatibility: '{"recommended":"modal-hosted","requested":"auto","compatible":true}',
      workflow_version: 'auto-workflow@1.0.0',
      build_evidence: '{"checks":["compile"],"duration_ms":1234}',
    });
  } else if (record.userId === 'user_creator') {
    Object.assign(record, {
      created_at: '2026-08-13T00:00:00.000Z',
      updated_at: '2026-08-13T00:00:00.000Z',
    });
  }
}

const submissionsListResponse = await worker.fetch(mkReq('GET', '/api/submissions?limit=1', {}, creatorHeaders), realEnv);
const submissionsList = await submissionsListResponse.json();
check('submissions list: authenticated owner receives newest-first bounded safe summaries',
  submissionsListResponse.status === 200 &&
  submissionsList.ok === true &&
  submissionsList.limit === 1 &&
  submissionsList.submissions.length === 1 &&
  submissionsList.submissions[0].id === submitAuto.id &&
  submissionsList.submissions[0].workflow_version === 'auto-workflow@1.0.0' &&
  submissionsList.submissions[0].selected_runtime === 'modal-hosted' &&
  submissionsList.submissions[0].compatibility.compatible === true &&
  submissionsList.submissions[0].build_evidence.checks.includes('compile') &&
  !('content' in submissionsList.submissions[0]));

const submissionDetailResponse = await worker.fetch(mkReq('GET', `/api/submissions/${submitAdded.id}`, {}, creatorHeaders), realEnv);
const submissionDetail = await submissionDetailResponse.json();
const detailText = JSON.stringify(submissionDetail);
check('submissions detail: owner response includes lifecycle fields and redacts unsafe internals',
  submissionDetailResponse.status === 200 &&
  submissionDetail.ok === true &&
  submissionDetail.submission.id === submitAdded.id &&
  submissionDetail.submission.published_slug === 'sample-workflow' &&
  /^[0-9a-f]{64}$/.test(submissionDetail.submission.source_sha256) &&
  submissionDetail.submission.workflow_version === 'sample-workflow@1.0.0' &&
  submissionDetail.submission.status === 'deployed' &&
  submissionDetail.submission.release.phase === 'promoted' &&
  submissionDetail.submission.release.issue_url === 'https://github.com/omo-space/marketplace/issues/31' &&
  submissionDetail.submission.release.pr_url === 'https://github.com/omo-space/marketplace/pull/42' &&
  submissionDetail.submission.release.pr_number === 42 &&
  submissionDetail.submission.release.branch === 'omo-release/sub_sample000000000000000001-sample-workflow' &&
  submissionDetail.submission.release.head_sha === 'a'.repeat(40) &&
  submissionDetail.submission.release.merge_sha === 'b'.repeat(40) &&
  submissionDetail.submission.release.artifact_hash === 'c'.repeat(64) &&
  submissionDetail.submission.release.modal_app === 'cognition-sample-workflow' &&
  submissionDetail.submission.release.modal_url === 'https://omo-space--cognition-sample-workflow-api.modal.run' &&
  submissionDetail.submission.release.canary.checked_at === '2026-08-14T00:09:00.000Z' &&
  submissionDetail.submission.release.canary.status === 'passed' &&
  submissionDetail.submission.deployed_at === '2026-08-13T00:10:00.000Z' &&
  submissionDetail.submission.compatibility.requested === 'modal-hosted' &&
  submissionDetail.submission.compatibility.recommended === 'worker-native' &&
  submissionDetail.submission.build_evidence.checks.includes('compile') &&
  !detailText.includes('SKILL.md') &&
  !detailText.includes('provider_config') &&
  !detailText.includes('secret') &&
  !detailText.includes('must-not-leak') &&
  !detailText.includes('stack trace') &&
  !detailText.includes('internal failure'));

const nonOwnerDetail = await worker.fetch(mkReq('GET', `/api/submissions/${submitAdded.id}`, {}, otherCreatorHeaders), realEnv);
const missingDetail = await worker.fetch(mkReq('GET', '/api/submissions/sub_00000000000000000000000000000000', {}, creatorHeaders), realEnv);
const missingListAuth = await worker.fetch(mkReq('GET', '/api/submissions', {}, {}), realEnv);
check('submissions API: missing auth, non-owner, and missing details fail closed', missingListAuth.status === 401 && nonOwnerDetail.status === 404 && missingDetail.status === 404);

const reviewedWovenSourceSha = '6297f14dfc8d4815efc041316e5c19df7faf4cb31dae3f73a0badc09101b90bf';
const approvalAllowlist = workerTest.reviewedSourceApprovalAllowlist();
check('approval allowlist: derives exact reviewed source hashes from generated hosted registry metadata',
  approvalAllowlist.get(reviewedWovenSourceSha) === 'woven-relationship-book-maker' &&
  !approvalAllowlist.has('f'.repeat(64)));

const approvalRecord = {
  id: 'sub_approvable000000000000000001',
  userId: 'user_creator',
  user_id: 'user_creator',
  name: 'Woven Storybook Pipeline',
  slug: 'woven-storybook-pipeline',
  content: 'server keeps content private',
  sourceSha256: reviewedWovenSourceSha,
  source_sha256: reviewedWovenSourceSha,
  requested_runtime: 'auto',
  status: 'needs_review',
  failure_code: 'slug_collision',
  created_at: '2026-08-14T00:00:00.000Z',
  updated_at: '2026-08-14T00:00:00.000Z',
};
workerTest.mockSubmissions.set(`user_creator\u0000${reviewedWovenSourceSha}`, approvalRecord);
const approveMissingAuth = await worker.fetch(mkReq('POST', `/api/submissions/${approvalRecord.id}/approve`, {
  source_sha256: 'f'.repeat(64), slug: 'attacker-slug', decision: 'approve',
}, { Origin: 'https://omo.space' }), realEnv);
const approveWrongOrigin = await worker.fetch(mkReq('OPTIONS', `/api/submissions/${approvalRecord.id}/approve`, {}, {
  Origin: 'https://evil.example',
}), realEnv);
const approveNonOwner = await worker.fetch(mkReq('POST', `/api/submissions/${approvalRecord.id}/approve`, {}, otherCreatorHeaders), realEnv);
const approveResponse = await worker.fetch(mkReq('POST', `/api/submissions/${approvalRecord.id}/approve`, {
  source_sha256: 'f'.repeat(64), slug: 'attacker-slug', decision: 'approve',
}, creatorHeaders), realEnv);
const approveBody = await approveResponse.json();
const approvalText = JSON.stringify(approveBody);
check('submission approval: Clerk owner can approve only server-reviewed exact hash and receives a safe summary',
  approveMissingAuth.status === 401 &&
  approveWrongOrigin.headers.get('Access-Control-Allow-Origin') === null &&
  approveNonOwner.status === 404 &&
  approveResponse.status === 200 &&
  approveBody.ok === true &&
  approveBody.approved === true &&
  approveBody.submission.id === approvalRecord.id &&
  approveBody.submission.status === 'ready_for_deploy' &&
  approveBody.submission.failure_code === null &&
  approveBody.submission.approval_reason === 'exact_source_slug_collision' &&
  approveBody.submission.approved_by === 'user_creator' &&
  !approvalText.includes('server keeps content private') &&
  !approvalText.includes('attacker-slug') &&
  !approvalText.includes('decision'));

const approveReplay = await (await worker.fetch(mkReq('POST', `/api/submissions/${approvalRecord.id}/approve`, {}, creatorHeaders), realEnv)).json();
check('submission approval: idempotent owner replay returns current approved state',
  approveReplay.ok === true &&
  approveReplay.approved === true &&
  approveReplay.submission.id === approvalRecord.id &&
  approveReplay.submission.status === 'ready_for_deploy' &&
  approveReplay.submission.failure_code === null);

const failClosedRecords = [
  ['sub_mismatch00000000000000000001', 'needs_review', 'slug_collision', 'f'.repeat(64)],
  ['sub_wrongreason00000000000000001', 'needs_review', 'reviewed_profile_required', reviewedWovenSourceSha],
  ['sub_wrongstatus00000000000000001', 'failed', 'slug_collision', reviewedWovenSourceSha],
];
for (const [id, status, failureCode, sourceSha256] of failClosedRecords) {
  workerTest.mockSubmissions.set(`user_creator\u0000${id}`, {
    id,
    userId: 'user_creator',
    user_id: 'user_creator',
    name: 'Blocked approval',
    slug: 'woven-storybook-pipeline',
    content: 'private',
    sourceSha256,
    source_sha256: sourceSha256,
    requested_runtime: 'auto',
    status,
    failure_code: failureCode,
    created_at: '2026-08-14T00:00:00.000Z',
    updated_at: '2026-08-14T00:00:00.000Z',
  });
}
const approveMismatch = await worker.fetch(mkReq('POST', '/api/submissions/sub_mismatch00000000000000000001/approve', {}, creatorHeaders), realEnv);
const approveWrongReason = await worker.fetch(mkReq('POST', '/api/submissions/sub_wrongreason00000000000000001/approve', {}, creatorHeaders), realEnv);
const approveWrongStatus = await worker.fetch(mkReq('POST', '/api/submissions/sub_wrongstatus00000000000000001/approve', {}, creatorHeaders), realEnv);
check('submission approval: mismatched hash, other failure reasons, and other statuses fail closed',
  approveMismatch.status === 409 &&
  approveWrongReason.status === 409 &&
  approveWrongStatus.status === 409);

neonSqlCalls.length = 0;
neonApprovalRow = {
  ...approvalRecord,
  user_id: 'user_creator',
  source_sha256: reviewedWovenSourceSha,
  status: 'ready_for_deploy',
  failure_code: null,
  approved_at: '2026-08-14T00:01:00.000Z',
  approved_by: 'user_creator',
  approval_reason: 'exact_source_slug_collision',
  updated_at: '2026-08-14T00:01:00.000Z',
};
const approveNeonResponse = await worker.fetch(mkReq('POST', `/api/submissions/${approvalRecord.id}/approve`, {
  source_sha256: 'f'.repeat(64), slug: 'attacker-slug',
}, creatorHeaders), { ...realEnv, NEON_DATABASE_URL: 'postgres://approval-user:secret@db.invalid/omo' });
const approveNeonBody = await approveNeonResponse.json();
const approveNeonCall = neonSqlCalls.find((call) => call.name === 'omo-submission-approve-v1');
neonApprovalRow = null;
check('submission approval: Neon uses one atomic guarded UPDATE and ignores client hash/slug/decision',
  approveNeonResponse.status === 200 &&
  approveNeonBody.submission.status === 'ready_for_deploy' &&
  approveNeonCall &&
  approveNeonCall.text.includes('UPDATE submissions') &&
  approveNeonCall.text.includes("status = 'needs_review'") &&
  approveNeonCall.text.includes("failure_code = 'slug_collision'") &&
  approveNeonCall.text.includes('source_sha256 = ANY($3::text[])') &&
  approveNeonCall.text.includes("SET status = 'ready_for_deploy'") &&
  approveNeonCall.values[0] === approvalRecord.id &&
  approveNeonCall.values[1] === 'user_creator' &&
  Array.isArray(approveNeonCall.values[2]) &&
  approveNeonCall.values[2].includes(reviewedWovenSourceSha) &&
  JSON.stringify(neonSqlCalls).includes('attacker-slug') === false &&
  JSON.stringify(neonSqlCalls).includes('ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff') === false);

const retryRecord = {
  id: 'sub_retryapproved0000000000000001',
  userId: 'user_creator',
  user_id: 'user_creator',
  name: 'Woven Storybook Pipeline',
  slug: 'woven-storybook-pipeline',
  content: 'server keeps retry content private',
  sourceSha256: reviewedWovenSourceSha,
  source_sha256: reviewedWovenSourceSha,
  requested_runtime: 'auto',
  selected_runtime: 'worker-native',
  runtime_policy: 'bounded_single_llm_is_worker_compatible',
  status: 'failed',
  failure_code: 'build_or_deploy_failed',
  approved_at: '2026-08-14T00:01:00.000Z',
  approved_by: 'user_creator',
  approval_reason: 'exact_source_slug_collision',
  created_at: '2026-08-14T00:00:00.000Z',
  updated_at: '2026-08-14T00:02:00.000Z',
};
workerTest.mockSubmissions.set(`user_creator\u0000${retryRecord.id}`, retryRecord);
const retryMissingAuth = await worker.fetch(mkReq('POST', `/api/submissions/${retryRecord.id}/retry`, {
  source_sha256: 'f'.repeat(64), selected_runtime: 'worker-native', decision: 'retry-anyway',
}, { Origin: 'https://omo.space' }), realEnv);
const retryNonOwner = await worker.fetch(mkReq('POST', `/api/submissions/${retryRecord.id}/retry`, {}, otherCreatorHeaders), realEnv);
const retryResponse = await worker.fetch(mkReq('POST', `/api/submissions/${retryRecord.id}/retry`, {
  source_sha256: 'f'.repeat(64), selected_runtime: 'worker-native', decision: 'retry-anyway',
}, creatorHeaders), realEnv);
const retryBody = await retryResponse.json();
const retryText = JSON.stringify(retryBody);
check('submission retry: Clerk owner can retry only a failed approved exact-match build failure and receives safe ready state',
  retryMissingAuth.status === 401 &&
  retryNonOwner.status === 404 &&
  retryResponse.status === 200 &&
  retryBody.ok === true &&
  retryBody.retried === true &&
  retryBody.submission.id === retryRecord.id &&
  retryBody.submission.status === 'ready_for_deploy' &&
  retryBody.submission.failure_code === null &&
  retryBody.submission.approved_by === 'user_creator' &&
  retryBody.submission.approval_reason === 'exact_source_slug_collision' &&
  retryBody.submission.selected_runtime === 'worker-native' &&
  !retryText.includes('server keeps retry content private') &&
  !retryText.includes('retry-anyway') &&
  !retryText.includes('ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'));

const retryReplay = await (await worker.fetch(mkReq('POST', `/api/submissions/${retryRecord.id}/retry`, {}, creatorHeaders), realEnv)).json();
check('submission retry: idempotent owner replay returns current ready_for_deploy state',
  retryReplay.ok === true &&
  retryReplay.retried === true &&
  retryReplay.submission.id === retryRecord.id &&
  retryReplay.submission.status === 'ready_for_deploy' &&
  retryReplay.submission.failure_code === null);

const retryCanaryRecord = {
  ...retryRecord,
  id: 'sub_retrycanary000000000000000001',
  status: 'failed',
  failure_code: 'canary_or_internal_failed',
  updated_at: '2026-08-14T00:04:00.000Z',
};
workerTest.mockSubmissions.set(`user_creator\u0000${retryCanaryRecord.id}`, retryCanaryRecord);
const retryCanaryResponse = await worker.fetch(mkReq('POST', `/api/submissions/${retryCanaryRecord.id}/retry`, {}, creatorHeaders), realEnv);
const retryCanaryBody = await retryCanaryResponse.json();
check('submission retry: owner can retry approved exact-match canary/internal failure with the same gates',
  retryCanaryResponse.status === 200 &&
  retryCanaryBody.ok === true &&
  retryCanaryBody.retried === true &&
  retryCanaryBody.submission.id === retryCanaryRecord.id &&
  retryCanaryBody.submission.status === 'ready_for_deploy' &&
  retryCanaryBody.submission.failure_code === null &&
  retryCanaryBody.submission.approved_by === 'user_creator' &&
  retryCanaryBody.submission.approval_reason === 'exact_source_slug_collision');

const retryFailClosedRecords = [
  ['sub_retryhash00000000000000000001', 'failed', 'build_or_deploy_failed', '2026-08-14T00:01:00.000Z', 'user_creator', 'exact_source_slug_collision', 'f'.repeat(64)],
  ['sub_retrystatus000000000000000001', 'needs_review', 'build_or_deploy_failed', '2026-08-14T00:01:00.000Z', 'user_creator', 'exact_source_slug_collision', reviewedWovenSourceSha],
  ['sub_retrycode00000000000000000001', 'failed', 'generated_source_hash_mismatch', '2026-08-14T00:01:00.000Z', 'user_creator', 'exact_source_slug_collision', reviewedWovenSourceSha],
  ['sub_retryapprover0000000000000001', 'failed', 'build_or_deploy_failed', '2026-08-14T00:01:00.000Z', 'user_other_creator', 'exact_source_slug_collision', reviewedWovenSourceSha],
  ['sub_retryreason000000000000000001', 'failed', 'build_or_deploy_failed', '2026-08-14T00:01:00.000Z', 'user_creator', 'manual_approval', reviewedWovenSourceSha],
  ['sub_retryapprovedat000000000001', 'failed', 'build_or_deploy_failed', null, 'user_creator', 'exact_source_slug_collision', reviewedWovenSourceSha],
];
for (const [id, status, failureCode, approvedAt, approvedBy, approvalReason, sourceSha256] of retryFailClosedRecords) {
  workerTest.mockSubmissions.set(`user_creator\u0000${id}`, {
    id,
    userId: 'user_creator',
    user_id: 'user_creator',
    name: 'Blocked retry',
    slug: 'woven-storybook-pipeline',
    content: 'private',
    sourceSha256,
    source_sha256: sourceSha256,
    requested_runtime: 'auto',
    status,
    failure_code: failureCode,
    approved_at: approvedAt,
    approved_by: approvedBy,
    approval_reason: approvalReason,
    created_at: '2026-08-14T00:00:00.000Z',
    updated_at: '2026-08-14T00:02:00.000Z',
  });
}
const retryMismatch = await worker.fetch(mkReq('POST', '/api/submissions/sub_retryhash00000000000000000001/retry', {}, creatorHeaders), realEnv);
const retryWrongStatus = await worker.fetch(mkReq('POST', '/api/submissions/sub_retrystatus000000000000000001/retry', {}, creatorHeaders), realEnv);
const retryWrongCode = await worker.fetch(mkReq('POST', '/api/submissions/sub_retrycode00000000000000000001/retry', {}, creatorHeaders), realEnv);
const retryWrongApprover = await worker.fetch(mkReq('POST', '/api/submissions/sub_retryapprover0000000000000001/retry', {}, creatorHeaders), realEnv);
const retryWrongReason = await worker.fetch(mkReq('POST', '/api/submissions/sub_retryreason000000000000000001/retry', {}, creatorHeaders), realEnv);
const retryMissingApprovedAt = await worker.fetch(mkReq('POST', '/api/submissions/sub_retryapprovedat000000000001/retry', {}, creatorHeaders), realEnv);
check('submission retry: arbitrary failed records cannot bypass exact-match approval gates',
  retryMismatch.status === 409 &&
  retryWrongStatus.status === 409 &&
  retryWrongCode.status === 409 &&
  retryWrongApprover.status === 409 &&
  retryWrongReason.status === 409 &&
  retryMissingApprovedAt.status === 409);

const d1RetryCalls = [];
const d1RetryRows = new Map([
  ['sub_retryd1canary0000000000000001', {
    ...retryCanaryRecord,
    id: 'sub_retryd1canary0000000000000001',
    status: 'failed',
    failure_code: 'canary_or_internal_failed',
  }],
  ['sub_retryd1wrongcode000000000001', {
    ...retryCanaryRecord,
    id: 'sub_retryd1wrongcode000000000001',
    status: 'failed',
    failure_code: 'generated_source_hash_mismatch',
  }],
]);
const d1Env = {
  ...realEnv,
  BALANCE_DB: {
    prepare(text) {
      const call = { text, values: [] };
      d1RetryCalls.push(call);
      return {
        bind(...values) {
          call.values = values;
          return {
            async run() {
              const [, id, userId, sourceSha256, approvedBy, approvalReason] = values;
              const row = d1RetryRows.get(id);
              const retryableCode = row && (row.failure_code === 'build_or_deploy_failed' || row.failure_code === 'canary_or_internal_failed');
              const allowed = row && row.user_id === userId &&
                row.source_sha256 === sourceSha256 &&
                row.status === 'failed' &&
                retryableCode &&
                row.approved_by === approvedBy &&
                row.approval_reason === approvalReason &&
                row.approved_at;
              if (!allowed) return { meta: { changes: 0 } };
              row.status = 'ready_for_deploy';
              row.failure_code = null;
              row.updated_at = values[0];
              return { meta: { changes: 1 } };
            },
            async first() {
              const [id, userId] = values;
              const row = d1RetryRows.get(id);
              return row && row.user_id === userId ? row : null;
            },
          };
        },
      };
    },
  },
};
const retryD1CanaryResponse = await worker.fetch(mkReq('POST', '/api/submissions/sub_retryd1canary0000000000000001/retry', {
  source_sha256: 'f'.repeat(64), selected_runtime: 'worker-native',
}, creatorHeaders), d1Env);
const retryD1CanaryBody = await retryD1CanaryResponse.json();
const retryD1WrongCode = await worker.fetch(mkReq('POST', '/api/submissions/sub_retryd1wrongcode000000000001/retry', {}, creatorHeaders), d1Env);
const retryD1UpdateCalls = d1RetryCalls.filter((call) => call.text.includes('UPDATE submissions'));
check('submission retry: D1 permits only the two approved exact-match release failure codes',
  retryD1CanaryResponse.status === 200 &&
  retryD1CanaryBody.submission.status === 'ready_for_deploy' &&
  retryD1CanaryBody.submission.failure_code === null &&
  retryD1WrongCode.status === 409 &&
  retryD1UpdateCalls.length >= 2 &&
  retryD1UpdateCalls.every((call) => call.text.includes("failure_code IN ('build_or_deploy_failed', 'canary_or_internal_failed')")) &&
  retryD1UpdateCalls.every((call) => !call.text.includes('generated_source_hash_mismatch')) &&
  JSON.stringify(d1RetryCalls).includes('worker-native') === false &&
  JSON.stringify(d1RetryCalls).includes('ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff') === false);

neonSqlCalls.length = 0;
neonApprovalRow = {
  ...retryRecord,
  user_id: 'user_creator',
  source_sha256: reviewedWovenSourceSha,
  status: 'ready_for_deploy',
  failure_code: null,
  approved_at: '2026-08-14T00:01:00.000Z',
  approved_by: 'user_creator',
  approval_reason: 'exact_source_slug_collision',
  updated_at: '2026-08-14T00:03:00.000Z',
};
const retryNeonResponse = await worker.fetch(mkReq('POST', `/api/submissions/${retryRecord.id}/retry`, {
  source_sha256: 'f'.repeat(64), selected_runtime: 'worker-native', decision: 'retry-anyway',
}, creatorHeaders), { ...realEnv, NEON_DATABASE_URL: 'postgres://approval-user:secret@db.invalid/omo' });
const retryNeonBody = await retryNeonResponse.json();
const retryNeonCall = neonSqlCalls.find((call) => call.name === 'omo-submission-retry-v1');
neonApprovalRow = null;
check('submission retry: Neon uses one atomic guarded UPDATE and ignores client hash/runtime/decision',
  retryNeonResponse.status === 200 &&
  retryNeonBody.submission.status === 'ready_for_deploy' &&
  retryNeonCall &&
  retryNeonCall.text.includes('UPDATE submissions') &&
  retryNeonCall.text.includes("status = 'failed'") &&
  retryNeonCall.text.includes("failure_code IN ('build_or_deploy_failed', 'canary_or_internal_failed')") &&
  !retryNeonCall.text.includes('generated_source_hash_mismatch') &&
  retryNeonCall.text.includes('source_sha256 = ANY($3::text[])') &&
  retryNeonCall.text.includes('approved_by = $2') &&
  retryNeonCall.text.includes("approval_reason = 'exact_source_slug_collision'") &&
  retryNeonCall.text.includes("SET status = 'ready_for_deploy'") &&
  retryNeonCall.values[0] === retryRecord.id &&
  retryNeonCall.values[1] === 'user_creator' &&
  Array.isArray(retryNeonCall.values[2]) &&
  retryNeonCall.values[2].includes(reviewedWovenSourceSha) &&
  JSON.stringify(neonSqlCalls).includes('retry-anyway') === false &&
  JSON.stringify(neonSqlCalls).includes('worker-native') === false &&
  JSON.stringify(neonSqlCalls).includes('ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff') === false);

// Private build-worker bridge: bearer-only, no CORS, bounded strict payloads.
const buildEnv = { ...realEnv, BUILD_WORKER_TOKEN: 'bridge-token-for-tests' };
const internalHeaders = { Authorization: 'Bearer bridge-token-for-tests', Origin: 'https://omo.space' };
check('internal auth: constant-time helper is length-stable and exact',
  workerTest.constantTimeEquals('bridge-token-for-tests', 'bridge-token-for-tests') === true &&
  workerTest.constantTimeEquals('bridge-token-for-tests', 'bridge-token-for-testx') === false &&
  workerTest.constantTimeEquals('bridge-token-for-tests', 'x') === false);
const internalNoConfig = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', {}, {}), realEnv);
const internalBadAuth = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', {}, {
  Authorization: 'Bearer wrong-token',
  Origin: 'https://omo.space',
}), buildEnv);
const internalOptions = await worker.fetch(mkReq('OPTIONS', '/api/internal/submissions/claim', {}, {
  Authorization: 'Bearer bridge-token-for-tests',
  Origin: 'https://omo.space',
}), buildEnv);
const internalUnknown = await worker.fetch(mkReq('GET', '/api/internal/not-a-route', {}, {
  Authorization: 'Bearer bridge-token-for-tests',
  Origin: 'https://omo.space',
}), buildEnv);
check('internal auth: missing config is 503, bad token is 401, and internal routes expose no CORS',
  internalNoConfig.status === 503 &&
  internalBadAuth.status === 401 &&
  internalBadAuth.headers.get('Access-Control-Allow-Origin') === null &&
  internalOptions.headers.get('Access-Control-Allow-Origin') === null &&
  internalUnknown.status === 404 &&
  internalUnknown.headers.get('Access-Control-Allow-Origin') === null);

const migrationEnv = { ...buildEnv, NEON_DATABASE_URL: 'postgres://user:secret@db.invalid/omo' };
const requiredSubmissionColumns = workerTest.REQUIRED_SUBMISSIONS_COLUMNS;
const migrationNoConfig = await worker.fetch(mkReq('POST', '/api/internal/submissions/migrate', {}, internalHeaders), buildEnv);
const migrationBadAuth = await worker.fetch(mkReq('POST', '/api/internal/submissions/migrate', {}, {
  Authorization: 'Bearer wrong-token',
  Origin: 'https://omo.space',
}), migrationEnv);
const migrationNonempty = await worker.fetch(mkReq('POST', '/api/internal/submissions/migrate', { sql: 'ALTER TABLE anything' }, internalHeaders), migrationEnv);
const migrationEmptyBody = await worker.fetch(Object.assign(mkReq('POST', '/api/internal/submissions/migrate', {}, internalHeaders), {
  text: async () => '',
}), migrationEnv);
const migrationOversize = await worker.fetch(Object.assign(mkReq('POST', '/api/internal/submissions/migrate', {}, internalHeaders), {
  text: async () => JSON.stringify({}).padEnd(300, ' '),
}), migrationEnv);
check('internal migration auth/body: requires build token, Neon config, literal {}, and exposes no CORS',
  migrationNoConfig.status === 500 &&
  (await migrationNoConfig.clone().json()).error === 'internal_error' &&
  migrationBadAuth.status === 401 &&
  migrationBadAuth.headers.get('Access-Control-Allow-Origin') === null &&
  migrationNonempty.status === 400 &&
  migrationEmptyBody.status === 400 &&
  migrationOversize.status === 413);

neonSqlCalls.length = 0;
neonInfoSchemaTableExists = false;
neonInfoSchemaColumns = [];
const schemaAbsent = await worker.fetch(mkReq('POST', '/api/internal/submissions/schema', {}, internalHeaders), migrationEnv);
const schemaAbsentBody = await schemaAbsent.json();
const schemaAbsentCalls = neonSqlCalls.map(({ text, values, name }) => ({ text, values, name }));
check('internal schema: absent table returns only table_exists plus allowlisted missing names',
  schemaAbsent.status === 200 &&
  schemaAbsent.headers.get('Access-Control-Allow-Origin') === null &&
  schemaAbsentBody.ok === true &&
  schemaAbsentBody.table_exists === false &&
  Array.isArray(schemaAbsentBody.present) &&
  schemaAbsentBody.present.length === 0 &&
  JSON.stringify(schemaAbsentBody.missing) === JSON.stringify(requiredSubmissionColumns) &&
  Object.keys(schemaAbsentBody).sort().join(',') === 'missing,ok,present,table_exists' &&
  schemaAbsentCalls.length === 4 &&
  schemaAbsentCalls[0].text.includes('information_schema.tables') &&
  schemaAbsentCalls[1].text.includes('information_schema.columns') &&
  schemaAbsentCalls[1].values.length === 1 &&
  JSON.stringify(schemaAbsentCalls[1].values[0]) === JSON.stringify(requiredSubmissionColumns) &&
  !JSON.stringify(schemaAbsentBody).includes('TEXT') &&
  !JSON.stringify(schemaAbsentBody).includes('postgres://'));

neonSqlCalls.length = 0;
neonInfoSchemaTableExists = true;
neonInfoSchemaColumns = ['id', 'user_id', 'name', 'slug', 'content', 'source_sha256', 'status', 'created_at', 'updated_at', 'attacker_column'];
const schemaPartial = await worker.fetch(mkReq('POST', '/api/internal/submissions/schema', {}, internalHeaders), migrationEnv);
const schemaPartialBody = await schemaPartial.json();
check('internal schema: partial old table reports only allowlisted present and missing names',
  schemaPartial.status === 200 &&
  schemaPartialBody.table_exists === true &&
  JSON.stringify(schemaPartialBody.present) === JSON.stringify(['id', 'user_id', 'name', 'slug', 'content', 'source_sha256', 'status', 'created_at', 'updated_at']) &&
  schemaPartialBody.missing.includes('requested_runtime') &&
  schemaPartialBody.missing.includes('deployment_metadata') &&
  !schemaPartialBody.present.includes('attacker_column'));

neonSqlCalls.length = 0;
neonInfoSchemaTableExists = true;
neonInfoSchemaColumns = [...requiredSubmissionColumns];
const schemaComplete = await worker.fetch(mkReq('POST', '/api/internal/submissions/schema', {}, internalHeaders), migrationEnv);
const schemaCompleteBody = await schemaComplete.json();
check('internal schema: complete table returns all required names as present and no missing names',
  schemaComplete.status === 200 &&
  JSON.stringify(schemaCompleteBody.present) === JSON.stringify(requiredSubmissionColumns) &&
  schemaCompleteBody.missing.length === 0);

neonSqlCalls.length = 0;
neonInfoSchemaTableExists = true;
neonInfoSchemaColumns = [];
const schemaNonempty = await worker.fetch(mkReq('POST', '/api/internal/submissions/schema', { column: 'content' }, internalHeaders), migrationEnv);
const schemaOversize = await worker.fetch(Object.assign(mkReq('POST', '/api/internal/submissions/schema', {}, internalHeaders), {
  text: async () => JSON.stringify({}).padEnd(300, ' '),
}), migrationEnv);
check('internal schema auth/body: rejects nonempty and oversized bodies before SQL',
  schemaNonempty.status === 400 &&
  schemaOversize.status === 413 &&
  neonSqlCalls.length === 0);

neonSqlCalls.length = 0;
neonPoolShouldThrow = true;
const schemaFailure = await worker.fetch(mkReq('POST', '/api/internal/submissions/schema', {}, internalHeaders), migrationEnv);
const schemaFailureText = await schemaFailure.text();
neonPoolShouldThrow = false;
check('internal schema: database errors are generic and never include DSN or exception text',
  schemaFailure.status === 500 &&
  schemaFailureText === '{"error":"internal_error"}' &&
  !schemaFailureText.includes('postgres://') &&
  !schemaFailureText.includes('secret'));

neonSqlCalls.length = 0;
neonPoolShouldThrow = false;
const migrationOne = await worker.fetch(mkReq('POST', '/api/internal/submissions/migrate', {}, internalHeaders), migrationEnv);
const migrationOneBody = await migrationOne.json();
const migrationFirstCalls = neonSqlCalls.map(({ text, values, name }) => ({ text, values, name }));
neonSqlCalls.length = 0;
const migrationTwo = await worker.fetch(mkReq('POST', '/api/internal/submissions/migrate', {}, internalHeaders), migrationEnv);
const migrationTwoBody = await migrationTwo.json();
const expectedMigrationNames = workerTest.SUBMISSIONS_SCHEMA_MIGRATIONS.map(([name]) => name);
const expectedMigrationSql = [
  'BEGIN',
  ...workerTest.SUBMISSIONS_SCHEMA_MIGRATIONS.map(([, sql]) => sql),
  'COMMIT',
  'RELEASE',
  'POOL_END',
];
check('internal migration: fixed allowlisted SQL runs in one transaction with no request parameters',
  migrationOne.status === 200 &&
  migrationOne.headers.get('Access-Control-Allow-Origin') === null &&
  migrationOneBody.ok === true &&
  JSON.stringify(migrationOneBody.applied) === JSON.stringify(expectedMigrationNames) &&
  JSON.stringify(migrationFirstCalls.map((call) => call.text)) === JSON.stringify(expectedMigrationSql) &&
  migrationFirstCalls[1].text.startsWith('CREATE TABLE IF NOT EXISTS submissions') &&
  migrationFirstCalls.slice(2, 2 + requiredSubmissionColumns.length).every((call) => Array.isArray(call.values) && call.values.length === 0 && /^omo-submissions-migrate-[a-z0-9_]+-v1$/.test(call.name || '') && call.text.includes('ADD COLUMN IF NOT EXISTS')) &&
  migrationFirstCalls.some((call) => call.text === 'CREATE INDEX IF NOT EXISTS idx_submissions_status_created\n  ON submissions (status, created_at)') &&
  migrationFirstCalls.some((call) => call.text === 'CREATE INDEX IF NOT EXISTS idx_submissions_user_created\n  ON submissions (user_id, created_at DESC)') &&
  migrationOneBody.applied.includes('create_table') &&
  migrationOneBody.applied.includes('idx_submissions_status_created') &&
  requiredSubmissionColumns.every((name) => migrationOneBody.applied.includes(name)) &&
  !JSON.stringify(migrationFirstCalls).includes('ALTER TABLE anything'));
check('internal migration: idempotent replay returns the same allowlisted names and SQL sequence',
  migrationTwo.status === 200 &&
  JSON.stringify(migrationTwoBody.applied) === JSON.stringify(expectedMigrationNames) &&
  JSON.stringify(neonSqlCalls.map((call) => call.text)) === JSON.stringify(expectedMigrationSql));

neonSqlCalls.length = 0;
neonPoolShouldThrow = true;
const migrationFailure = await worker.fetch(mkReq('POST', '/api/internal/submissions/migrate', {}, internalHeaders), migrationEnv);
const migrationFailureText = await migrationFailure.text();
neonPoolShouldThrow = false;
check('internal migration: database errors are generic and never include DSN or exception text',
  migrationFailure.status === 500 &&
  migrationFailureText === '{"error":"internal_error"}' &&
  !migrationFailureText.includes('postgres://') &&
  !migrationFailureText.includes('secret') &&
  neonSqlCalls.some((call) => call.text === 'ROLLBACK'));

for (const record of workerTest.mockSubmissions.values()) {
  if (record.id === submitAuto.id) {
    record.status = 'queued';
    record.published_slug = null;
    record.workflow_version = null;
    record.build_evidence = null;
  }
}
const internalClaim = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', { id: submitAuto.id }, internalHeaders), buildEnv);
const internalClaimBody = await internalClaim.json();
const internalReplay = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', { id: submitAuto.id }, internalHeaders), buildEnv);
check('internal claim: atomically returns one safe processing row and cannot replay a processing id',
  internalClaim.status === 200 &&
  internalClaimBody.ok === true &&
  internalClaimBody.submission.id === submitAuto.id &&
  internalClaimBody.submission.prior_status === 'queued' &&
  internalClaimBody.submission.content === autoSubmissionContent &&
  !('user_id' in internalClaimBody.submission) &&
  internalReplay.status === 204);
const internalBadClaimId = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', { id: 'sub_bad' }, internalHeaders), buildEnv);
check('internal claim: unsafe specific ids are rejected before SQL', internalBadClaimId.status === 400);

const internalRuntime = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/runtime`, {
  effective: 'worker-native',
  reason: 'reviewed_profile_selected_worker',
  recommended: 'worker-native',
  requested: 'auto',
  compatible: true,
  token: 'must-not-store',
}, internalHeaders), buildEnv);
const internalBadRuntime = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/runtime`, {
  effective: 'edge-magic',
  reason: 'bad',
}, internalHeaders), buildEnv);
check('internal runtime: strict allowlisted decision fields update processing rows only', internalRuntime.status === 200 && internalBadRuntime.status === 400);

const internalDeployment = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/deployment`, {
  status: 'ready_for_publish',
  published_slug: 'auto-workflow',
  workflow_version: 'auto-workflow@1.0.0',
  build_evidence: {
    checks: ['compile', 'contract'],
    source_sha256: internalClaimBody.submission.source_sha256,
    generated_at: '2026-08-13T00:00:00Z',
    secret: 'must-not-store',
  },
}, internalHeaders), buildEnv);
const internalRelease = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/release`, {
  release_phase: 'pr_open',
  issue_url: 'https://github.com/omo-space/marketplace/issues/31',
  pr_url: 'https://github.com/omo-space/marketplace/pull/42',
  pr_number: 42,
  branch: 'omo-release/' + internalClaimBody.submission.id + '-auto-workflow',
  head_sha: 'a'.repeat(40),
  source_sha256: internalClaimBody.submission.source_sha256,
  artifact_hash: 'b'.repeat(64),
  client_branch: 'attacker-branch',
  secret: 'must-not-store',
}, internalHeaders), buildEnv);
const badInternalRelease = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/release`, {
  release_phase: 'merged_verified',
  issue_url: 'https://github.com/omo-space/marketplace/issues/31',
  pr_url: 'https://github.com/omo-space/marketplace/pull/42',
  pr_number: 42,
  branch: 'main',
  head_sha: 'a'.repeat(40),
  source_sha256: internalClaimBody.submission.source_sha256,
  artifact_hash: 'b'.repeat(64),
}, internalHeaders), buildEnv);
const internalDeployed = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/deployed`, {
  deployed_by: 'build-worker',
  deployment_url: 'https://omo.space/workflow.html?slug=auto-workflow',
}, internalHeaders), buildEnv);
const deployedRecord = Array.from(workerTest.mockSubmissions.values()).find((record) => record.id === internalClaimBody.submission.id);
check('internal deployment: metadata is allowlisted and deployed is gated from ready_for_publish',
  internalDeployment.status === 200 &&
  internalRelease.status === 200 &&
  badInternalRelease.status === 400 &&
  internalDeployed.status === 200 &&
  deployedRecord.status === 'deployed' &&
  deployedRecord.published_slug === 'auto-workflow' &&
  deployedRecord.release_phase === 'pr_open' &&
  deployedRecord.release_branch === 'omo-release/' + internalClaimBody.submission.id + '-auto-workflow' &&
  deployedRecord.release_pr_number === 42 &&
  !String(deployedRecord.build_evidence).includes('must-not-store') &&
  !JSON.stringify(deployedRecord).includes('attacker-branch'));

const internalDetail = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/detail`, {}, internalHeaders), buildEnv);
const internalDetailBody = await internalDetail.json();
const internalDetailBadToken = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/detail`, {}, {
  Authorization: 'Bearer wrong-token',
  Origin: 'https://omo.space',
}), buildEnv);
const internalDetailUnsafe = await worker.fetch(mkReq('POST', '/api/internal/submissions/sub_bad/detail', {}, internalHeaders), buildEnv);
const internalDetailGet = await worker.fetch(mkReq('GET', `/api/internal/submissions/${internalClaimBody.submission.id}/detail`, {}, internalHeaders), buildEnv);
const internalDetailNonempty = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/detail`, { include_content: true }, internalHeaders), buildEnv);
const internalDetailMissing = await worker.fetch(mkReq('POST', '/api/internal/submissions/sub_zzzzzzzz/detail', {}, internalHeaders), buildEnv);
check('internal detail mock: bearer-only POST detail returns release/deploy fields without source or private owner data',
  internalDetail.status === 200 &&
  internalDetail.headers.get('Access-Control-Allow-Origin') === null &&
  internalDetailBody.ok === true &&
  internalDetailBody.submission.id === internalClaimBody.submission.id &&
  internalDetailBody.submission.slug === 'auto-workflow' &&
  internalDetailBody.submission.selected_runtime === 'worker-native' &&
  internalDetailBody.submission.workflow_version === 'auto-workflow@1.0.0' &&
  internalDetailBody.submission.published_slug === 'auto-workflow' &&
  internalDetailBody.submission.source_sha256 === internalClaimBody.submission.source_sha256 &&
  internalDetailBody.submission.release_phase === 'pr_open' &&
  internalDetailBody.submission.release_pr_number === 42 &&
  internalDetailBody.submission.release_branch === 'omo-release/' + internalClaimBody.submission.id + '-auto-workflow' &&
  internalDetailBody.submission.release_head_sha === 'a'.repeat(40) &&
  internalDetailBody.submission.release_artifact_hash === 'b'.repeat(64) &&
  !('content' in internalDetailBody.submission) &&
  !('user_id' in internalDetailBody.submission) &&
  !('approved_by' in internalDetailBody.submission) &&
  !JSON.stringify(internalDetailBody).includes('must-not-store') &&
  internalDetailBadToken.status === 401 &&
  internalDetailBadToken.headers.get('Access-Control-Allow-Origin') === null &&
  internalDetailUnsafe.status === 404 &&
  internalDetailGet.status === 405 &&
  internalDetailNonempty.status === 400 &&
  internalDetailMissing.status === 404);

neonSqlCalls.length = 0;
neonInternalDetailRow = {
  id: 'sub_neondetail01',
  user_id: 'user_must_not_leak',
  name: 'must not leak',
  slug: 'neon-workflow',
  content: 'secret markdown must not leak',
  source_sha256: 'e'.repeat(64),
  selected_runtime: 'modal-hosted',
  workflow_version: 'neon-workflow@1.0.0',
  published_slug: 'neon-workflow',
  build_evidence: JSON.stringify({ checks: ['compile'], secret: 'must-not-leak' }),
  status: 'ready_for_publish',
  release_phase: 'merged_verified',
  release_issue_url: 'https://github.com/omo-space/marketplace/issues/37',
  release_pr_url: 'https://github.com/omo-space/marketplace/pull/38',
  release_pr_number: 38,
  release_branch: 'omo-release/sub_neondetail01-neon-workflow',
  release_head_sha: '1'.repeat(40),
  release_merge_sha: '2'.repeat(40),
  release_artifact_hash: 'f'.repeat(64),
  modal_app: 'neon-workflow',
  modal_url: 'https://omo-space--neon-workflow-api.modal.run',
  canary_evidence: JSON.stringify({ status: 'passed', checked_at: '2026-08-14T00:00:00Z', secret: 'must-not-leak' }),
};
const neonDetail = await worker.fetch(mkReq('POST', '/api/internal/submissions/sub_neondetail01/detail', {}, internalHeaders), migrationEnv);
const neonDetailBody = await neonDetail.json();
const neonDetailCall = neonSqlCalls.find((call) => call.name === 'omo-internal-submission-detail-v1');
neonInternalDetailRow = null;
const neonDetailMissing = await worker.fetch(mkReq('POST', '/api/internal/submissions/sub_neondetail01/detail', {}, internalHeaders), migrationEnv);
check('internal detail Neon: parameterized narrow select excludes content/user/private data and maps missing to 404',
  neonDetail.status === 200 &&
  neonDetailBody.submission.id === 'sub_neondetail01' &&
  neonDetailBody.submission.slug === 'neon-workflow' &&
  neonDetailBody.submission.selected_runtime === 'modal-hosted' &&
  neonDetailBody.submission.release_merge_sha === '2'.repeat(40) &&
  neonDetailBody.submission.canary_evidence.status === 'passed' &&
  !JSON.stringify(neonDetailBody).includes('secret') &&
  !('content' in neonDetailBody.submission) &&
  !('user_id' in neonDetailBody.submission) &&
  neonDetailCall &&
  neonDetailCall.text.includes('SELECT id,slug,source_sha256,selected_runtime') &&
  !neonDetailCall.text.includes('content') &&
  !neonDetailCall.text.includes('user_id') &&
  neonDetailCall.values[0] === 'sub_neondetail01' &&
  neonDetailMissing.status === 404);

const internalBadStatus = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/status`, {
  status: 'queued',
}, internalHeaders), buildEnv);
const internalOversize = await worker.fetch(Object.assign(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/status`, {}, internalHeaders), {
  text: async () => 'x'.repeat(20 * 1024),
  json: async () => { throw new Error('should not parse oversize'); },
}), buildEnv);
check('internal status: invalid transitions and oversized bodies fail closed', internalBadStatus.status === 400 && internalOversize.status === 413);

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
const user111Headers = { Authorization: `Bearer ${user111Token}`, Origin: 'https://omo.space' };

const co = await worker.fetch(mkReq('POST', '/api/checkout', { slug: 'ugc-script-studio', priceUsd: 25, email: 'buyer@example.com' }), env);
check('checkout: no secret key returns 501', co.status === 501);
const coBody = await co.json();
check('checkout: 501 body says not configured', coBody.error === 'stripe not configured');

const badCheckout = await worker.fetch(mkReq('POST', '/api/checkout', { slug: '', priceUsd: 5 }), stripeEnv);
check('checkout: missing slug returns 400', badCheckout.status === 400);
const stripeCallsBeforeUnknown = stripeCalls.length;
const unknownCheckout = await worker.fetch(mkReq('POST', '/api/checkout', { slug: 'client-invented-listing', priceUsd: 1 }), stripeEnv);
check('checkout: unknown slug returns 404 without calling Stripe', unknownCheckout.status === 404 && stripeCalls.length === stripeCallsBeforeUnknown);

const csResponse = await worker.fetch(mkReq('POST', '/api/checkout', {
  slug: 'ugc-script-studio', priceUsd: 0.01, email: 'buyer@example.com',
}, {
  Origin: 'https://omo.space', Referer: 'https://omo.space/workflow.html?slug=ugc-script-studio',
  'Idempotency-Key': 'checkout-router-0001',
}), stripeEnv);
const cs = await csResponse.json();
check('checkout: guest buyer needs no auth and receives hosted Stripe URL', csResponse.status === 200 && cs.url === 'https://checkout.stripe.com/c/pay/test_123');
check('checkout: real-mode CORS allows the production storefront', csResponse.headers.get('Access-Control-Allow-Origin') === 'https://omo.space');

const sc = stripeCalls[stripeCalls.length - 1];
const scParams = new URLSearchParams(sc.body);
check('checkout: posts form-encoded to Stripe sessions API', sc.url === 'https://api.stripe.com/v1/checkout/sessions');
check('checkout: unit_amount is server catalog price (client price ignored)', scParams.get('line_items[0][price_data][unit_amount]') === '3900');
check('checkout: currency + mode + quantity + locale + submit type set', scParams.get('line_items[0][price_data][currency]') === 'usd' && scParams.get('mode') === 'payment' && scParams.get('line_items[0][quantity]') === '1' && scParams.get('locale') === 'auto' && scParams.get('submit_type') === 'pay');
check('checkout: product and scoped custom text name the server catalog workflow', scParams.get('line_items[0][price_data][product_data][name]') === 'UGC Script Studio' && scParams.get('line_items[0][price_data][product_data][description]') === 'UGC Script Studio workflow and prompts from Omo.' && scParams.get('custom_text[submit][message]') === 'Purchasing the UGC Script Studio workflow' && scParams.get('custom_text[after_submit][message]') === 'Enjoy your workflow — after payment, find it in your Omo dashboard');
check('checkout: success_url carries slug + Stripe session placeholder', scParams.get('success_url') === 'https://omo.space/?purchased=ugc-script-studio&session_id={CHECKOUT_SESSION_ID}');
check('checkout: cancel_url returns to the originating workflow listing', scParams.get('cancel_url') === 'https://omo.space/workflow.html?slug=ugc-script-studio');
check('checkout: buyer email forwarded', scParams.get('customer_email') === 'buyer@example.com');
check('checkout: ownership metadata pins workflow, flow, amount + currency', scParams.get('metadata[type]') === 'catalog_license' && scParams.get('metadata[flow]') === 'purchase' && scParams.get('metadata[slug]') === 'ugc-script-studio' && scParams.get('metadata[workflow]') === 'UGC Script Studio' && scParams.get('metadata[amount_cents]') === '3900' && scParams.get('metadata[currency]') === 'usd');
check('checkout: secret + Clover version and complete Omo branding are request-scoped', (sc.headers.Authorization || '') === 'Bearer sk_test_fake_secret' && sc.headers['Stripe-Version'] === '2025-09-30.clover' && scParams.get('branding_settings[display_name]') === 'Omo' && scParams.get('branding_settings[background_color]') === '#F8F7F5' && scParams.get('branding_settings[button_color]') === '#17352C' && scParams.get('branding_settings[border_style]') === 'rounded' && scParams.get('branding_settings[font_family]') === 'nunito' && scParams.get('branding_settings[logo][url]') === 'https://omo.space/logo-sweet-pastel.svg' && scParams.get('branding_settings[icon][url]') === 'https://omo.space/favicon-512.png');
check('checkout: caller idempotency is scoped before Stripe', /^omo-checkout-[0-9a-f]{64}$/.test(sc.headers['Idempotency-Key'] || '') && sc.headers['Idempotency-Key'] !== 'checkout-router-0001');

const persistenceFailureEnv = {
  ...stripeEnv,
  BALANCE_DB: { prepare() { throw Object.assign(new Error('missing purchases table'), { code: '42P01' }); } },
};
const failedPersistenceResponse = await worker.fetch(mkReq('POST', '/api/checkout', {
  slug: 'ugc-script-studio',
}, { 'Idempotency-Key': 'checkout-router-db-failure' }), persistenceFailureEnv);
const failedPersistence = await failedPersistenceResponse.json();
const expireCall = stripeCalls.at(-1);
check('checkout: persistence failure expires the unpaid Stripe session and fails closed',
  failedPersistenceResponse.status === 503 && failedPersistence.error === 'purchase recording unavailable' &&
  failedPersistence.session_expired === true &&
  expireCall.url === 'https://api.stripe.com/v1/checkout/sessions/cs_test_123/expire' && expireCall.method === 'POST');

const authedCheckout = await worker.fetch(mkReq('POST', '/api/checkout', {
  slug: 'listing-copy-engine', email: 'member@example.com',
}, user111Headers), stripeEnv);
const authedCheckoutParams = new URLSearchParams(stripeCalls.at(-1).body);
check('checkout: verified callers add user metadata without changing the guest-compatible contract', authedCheckout.status === 200 && authedCheckoutParams.get('metadata[user_id]') === 'user_111');

const stripeWebhookSecret = 'whsec_router_purchase_secret';
const purchaseEvent = {
  id: 'evt_catalog_purchase_123',
  type: 'checkout.session.completed',
  data: { object: {
    id: 'cs_test_123',
    payment_status: 'paid',
    amount_total: 3900,
    currency: 'usd',
    customer_details: { email: 'stripe-buyer@example.com' },
    metadata: { type: 'catalog_license', slug: 'ugc-script-studio', amount_cents: '3900', currency: 'usd' },
  } },
};
const purchaseWebhookEnv = { ...stripeEnv, STRIPE_WEBHOOK_SECRET: stripeWebhookSecret };
const purchaseWebhook = await worker.fetch(await signedStripeRequest(purchaseEvent, stripeWebhookSecret), purchaseWebhookEnv);
const purchaseWebhookBody = await purchaseWebhook.json();
check('checkout webhook: signed paid purchase is acknowledged + recorded', purchaseWebhook.status === 200 && purchaseWebhookBody.ok === true && purchaseWebhookBody.applied === true && purchaseWebhookBody.slug === 'ugc-script-studio');
const purchaseReplay = await worker.fetch(await signedStripeRequest(purchaseEvent, stripeWebhookSecret), purchaseWebhookEnv);
const purchaseReplayBody = await purchaseReplay.json();
check('checkout webhook: replay is acknowledged without duplicate ownership', purchaseReplay.status === 200 && purchaseReplayBody.ok === true && purchaseReplayBody.applied === false);

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

// ── Woven Relationship Book Maker → schema-driven Modal async run ─────────

const wovenEnv = {
  ...realEnv,
  WOVEN_MODAL_URL: 'https://woven.modal.invalid',
  WOVEN_MODAL_PROXY_TOKEN_ID: 'wk-test-id',
  WOVEN_MODAL_PROXY_TOKEN_SECRET: 'ws-test-secret',
};
const wovenMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_woven', {}), env)).json();
const wovenHeaders = { Authorization: `Bearer ${wovenMe.api_key}`, 'Idempotency-Key': 'woven-router-0001' };
const wovenInput = {
  slug: 'woven-relationship-book-maker',
  input: {
    how_you_met: 'We reached for the same travel book on a rainy afternoon.',
    favorite_moments: 'Seven years, two cities, our first apartment, and adopting a corgi.',
    inside_jokes: 'Wrong turn, best view.', style: 'warm', length: 'short',
  },
};
const wovenStartResponse = await worker.fetch(mkReq('POST', '/api/run', wovenInput, wovenHeaders), wovenEnv);
const wovenStart = await wovenStartResponse.json();
check('woven: schema-valid input dispatches asynchronously at the server-owned $0.40 quote', wovenStartResponse.status === 202 && wovenStart.status === 'running' && wovenStart.quoted_cost_usd === 0.4 && wovenStart.billed_amount_usd === 0.4);
check('woven: Worker sends exact typed input with scoped Modal Proxy Token headers', JSON.parse(wovenCalls[0].body).style === 'warm' && wovenCalls[0].headers['Modal-Key'] === 'wk-test-id' && wovenCalls[0].headers['Modal-Secret'] === 'ws-test-secret');
const badWoven = await worker.fetch(mkReq('POST', '/api/run', { slug: 'woven-relationship-book-maker', input: { ...wovenInput.input, style: 'invented' } }, { ...wovenHeaders, 'Idempotency-Key': 'woven-router-bad1' }), wovenEnv);
check('woven: schema-invalid input fails before debit or Modal spend', badWoven.status === 422 && wovenCalls.length === 1);
const wovenRunning = await worker.fetch(mkReq('GET', `/api/run/${wovenStart.run_id}`, {}, { Authorization: `Bearer ${wovenMe.api_key}` }), wovenEnv);
check('woven: Omo status poll proxies Modal running state', wovenRunning.status === 202);
wovenStatuses.set('fc-WOVENROUTER0001', { status: 200, body: {
  run_id: 'run-provider-woven', status: 'completed', workflow_version: 'woven-storybook-pipeline@0.2.0',
  title: 'Wrong Turns, Best Views', book: '# Wrong Turns, Best Views\n\nA long enough factual keepsake story that clears the minimum output length. '.repeat(4),
  page_plan: ['Cover with rainy bookshop', 'The beginning in the bookshop', 'Two cities and one corgi', 'Closing on the best view'],
  usage: { provider: 'opencode-go', model: 'deepseek-v4-flash', llm_calls: 1, prompt_tokens: 269, completion_tokens: 314, estimated_cost_usd: 0.00012558 },
} });
const wovenDoneResponse = await worker.fetch(mkReq('GET', `/api/run/${wovenStart.run_id}`, {}, { Authorization: `Bearer ${wovenMe.api_key}` }), wovenEnv);
const wovenDone = await wovenDoneResponse.json();
const wovenAfter = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_woven', {}), env)).json();
check('woven: completed Modal output settles once and preserves the schema-valid result', wovenDoneResponse.status === 200 && wovenDone.status === 'completed' && wovenDone.output.title === 'Wrong Turns, Best Views' && wovenAfter.balance_usd === 4.6);

// ── Facebook Ads Copywriter → generated hosted-Modal registry ─────────────

const facebookEnv = {
  ...realEnv,
  LLM_BASE_URL: 'https://opencode.ai/zen/go/v1',
  FACEBOOK_ADS_MODAL_URL: 'https://facebook.modal.invalid',
  HOSTED_MODAL_PROXY_TOKEN_ID: 'wk-hosted-test-id',
  HOSTED_MODAL_PROXY_TOKEN_SECRET: 'ws-hosted-test-secret',
};
const facebookMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook', {}), env)).json();
const facebookHeaders = { Authorization: `Bearer ${facebookMe.api_key}`, 'Idempotency-Key': 'facebook-router-0001' };
const facebookInput = { slug: 'facebook-ads-copywriter', input: facebookCases.happy_path.input };
const facebookProviderCallsBeforeEvil = llmCalls.length;
const facebookEvilMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook_evil', {}), env)).json();
const facebookEvilOriginFailure = await worker.fetch(mkReq('POST', '/api/run', facebookInput, {
  Authorization: `Bearer ${facebookEvilMe.api_key}`,
  'Idempotency-Key': 'facebook-router-evil-origin',
}), { ...facebookEnv, LLM_BASE_URL: 'https://attacker.invalid/zen/go/v1' });
const facebookEvilOriginBody = await facebookEvilOriginFailure.json();
check('hosted registry: evil Worker provider origin fails configuration before fetch or auth emission', facebookEvilOriginFailure.status === 503 && facebookEvilOriginBody.error === 'hosted_worker_provider_base_url_invalid' && facebookCalls.length === 0 && llmCalls.length === facebookProviderCallsBeforeEvil);
const facebookStartResponse = await worker.fetch(mkReq('POST', '/api/run', facebookInput, facebookHeaders), facebookEnv);
const facebookStart = await facebookStartResponse.json();
check('hosted registry: Facebook Ads executes Worker-native synchronously at the server-owned $0.10 quote', facebookStartResponse.status === 200 && facebookStart.status === 'completed' && facebookStart.output.ads.length === 3 && facebookStart.cost_usd === 0.1 && facebookStart.balance === 4.9);
check('hosted registry: Worker-native path calls the server-owned LLM provider directly without Modal', facebookCalls.length === 0 && llmCalls.at(-1).messages[0].content.includes('senior Facebook ads copywriter') && !llmCalls.at(-1).messages[1].content.includes('MALICIOUS'));
const badFacebook = await worker.fetch(mkReq('POST', '/api/run', { slug: 'facebook-ads-copywriter', input: { ...facebookInput.input, objective: 'awareness' } }, { ...facebookHeaders, 'Idempotency-Key': 'facebook-router-bad1' }), facebookEnv);
const facebookAfterBad = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook', {}), env)).json();
check('hosted registry: invalid Facebook Ads input fails before debit or provider spend', badFacebook.status === 422 && facebookCalls.length === 0 && facebookAfterBad.balance_usd === 4.9);
const facebookDoneResponse = await worker.fetch(mkReq('GET', `/api/run/${facebookStart.run_id}`, {}, { Authorization: `Bearer ${facebookMe.api_key}` }), facebookEnv);
const facebookDone = await facebookDoneResponse.json();
const facebookAfter = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook', {}), env)).json();
check('hosted registry: completed Worker-native output replays from durable state', facebookDoneResponse.status === 200 && facebookDone.status === 'completed' && facebookDone.output.ads.length === 3 && facebookAfter.balance_usd === 4.9);

const facebookReplay = await (await worker.fetch(mkReq('POST', '/api/run', facebookInput, facebookHeaders), facebookEnv)).json();
check('hosted registry: Worker-native idempotent replay returns prior run and never double-charges', facebookReplay.idempotent_replay === true && facebookReplay.run_id === facebookStart.run_id && llmCalls.filter((call) => call.messages[0].content.includes('senior Facebook ads copywriter')).length === 1 && facebookAfter.balance_usd === 4.9);

workerNativeMode = 'invalid_json';
const facebookJsonMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook_json', {}), env)).json();
const badJson = await worker.fetch(mkReq('POST', '/api/run', facebookInput, { Authorization: `Bearer ${facebookJsonMe.api_key}`, 'Idempotency-Key': 'facebook-router-json1' }), facebookEnv);
const badJsonBody = await badJson.json();
const facebookJsonAfter = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook_json', {}), env)).json();
check('hosted registry: invalid Worker-native provider JSON refunds exactly once', badJson.status === 502 && badJsonBody.reason === 'worker_native_invalid_json' && facebookJsonAfter.balance_usd === 5);

workerNativeMode = 'invalid_schema';
const facebookSchemaMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook_schema', {}), env)).json();
const badSchemaHeaders = { Authorization: `Bearer ${facebookSchemaMe.api_key}`, 'Idempotency-Key': 'facebook-router-schema1' };
const badSchema = await worker.fetch(mkReq('POST', '/api/run', facebookInput, badSchemaHeaders), facebookEnv);
const badSchemaBody = await badSchema.json();
const badSchemaReplay = await worker.fetch(mkReq('POST', '/api/run', facebookInput, badSchemaHeaders), facebookEnv);
const facebookSchemaAfter = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook_schema', {}), env)).json();
check('hosted registry: invalid Worker-native output schema refunds once and replays failure', badSchema.status === 502 && badSchemaBody.reason === 'worker_native_invalid_output' && badSchemaReplay.status === 502 && facebookSchemaAfter.balance_usd === 5);

workerNativeMode = 'provider_error';
const facebookProviderMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook_provider', {}), env)).json();
const providerFailure = await worker.fetch(mkReq('POST', '/api/run', facebookInput, { Authorization: `Bearer ${facebookProviderMe.api_key}`, 'Idempotency-Key': 'facebook-router-provider1' }), facebookEnv);
const providerFailureBody = await providerFailure.json();
const facebookProviderAfter = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook_provider', {}), env)).json();
check('hosted registry: Worker-native provider failure refunds exactly once', providerFailure.status === 502 && providerFailureBody.reason === 'worker_native_provider_error' && facebookProviderAfter.balance_usd === 5);
workerNativeMode = 'valid';

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

const topupHeaders = { ...user111Headers, 'Idempotency-Key': 'topup-router-0001' };
const tp = await (await worker.fetch(mkReq('POST', '/api/topup', { user_id: 'user_attacker', amount_usd: 7 }, topupHeaders), stripeEnv)).json();
check('topup: returns Stripe Checkout url', tp.url === 'https://checkout.stripe.com/c/pay/test_123');

const tpc = stripeCalls[stripeCalls.length - 1];
const tpcParams = new URLSearchParams(tpc.body);
check('topup: custom $7 Omo credits, cards only, locale, text, version + idempotency are pinned at Stripe', tpcParams.get('line_items[0][price_data][unit_amount]') === '700' && tpcParams.get('line_items[0][price_data][product_data][name]') === 'Omo credits' && tpcParams.get('line_items[0][price_data][product_data][description]') === 'Adds $7.00 to your Omo balance.' && tpcParams.get('payment_method_types[0]') === 'card' && tpcParams.get('locale') === 'auto' && tpcParams.get('submit_type') === 'pay' && tpcParams.get('custom_text[submit][message]') === 'Topping up Omo credits' && tpcParams.get('custom_text[after_submit][message]') === 'Thank you — your Omo credits are on the way after payment' && tpc.headers['Stripe-Version'] === '2025-09-30.clover' && /^omo-topup-[0-9a-f]{64}$/.test(tpc.headers['Idempotency-Key'] || ''));
check('topup: success and cancel URLs return directly to billing', tpcParams.get('success_url') === 'https://omo.space/billing.html?topup=success&session_id={CHECKOUT_SESSION_ID}' && tpcParams.get('cancel_url') === 'https://omo.space/billing.html?topup=cancelled');
check('topup: verified user overrides body user in reference + scoped metadata', tpcParams.get('client_reference_id') === 'user_111' && tpcParams.get('metadata[user_id]') === 'user_111' && tpcParams.get('metadata[type]') === 'credits_topup' && tpcParams.get('metadata[flow]') === 'topup');

const topupPersistenceFailureEnv = {
  ...stripeEnv,
  BALANCE_DB: {
    prepare(sql) {
      if (sql.includes('topup_sessions')) throw Object.assign(new Error('missing topup_sessions table'), { code: '42P01' });
      return {
        bind() {
          return {
            first: async () => sql.startsWith('SELECT balance_cents')
              ? { balance_cents: 500, api_key: 'hash', created_at: new Date().toISOString() }
              : null,
            run: async () => ({ meta: { changes: 1 } }),
          };
        },
      };
    },
  },
};
const failedTopupResponse = await worker.fetch(mkReq('POST', '/api/topup', {
  user_id: 'user_attacker', amount_usd: 7,
}, { ...topupHeaders, 'Idempotency-Key': 'topup-router-db-failure' }), topupPersistenceFailureEnv);
const failedTopup = await failedTopupResponse.json();
const topupExpireCall = stripeCalls.at(-1);
check('topup: persistence failure expires the unpaid Stripe session and fails closed',
  failedTopupResponse.status === 503 && failedTopup.error === 'top-up recording unavailable' &&
  failedTopup.session_expired === true &&
  topupExpireCall.url === 'https://api.stripe.com/v1/checkout/sessions/cs_test_123/expire' && topupExpireCall.method === 'POST');

const topupEvent = {
  id: 'evt_credit_topup_123',
  type: 'checkout.session.completed',
  data: { object: {
    id: 'cs_test_123', payment_status: 'paid', amount_total: 700, currency: 'usd', client_reference_id: 'user_111',
    metadata: { type: 'credits_topup', user_id: 'user_111', amount_cents: '700', currency: 'usd' },
  } },
};
const topupWebhook = await worker.fetch(await signedStripeRequest(topupEvent, stripeWebhookSecret), purchaseWebhookEnv);
const topupWebhookBody = await topupWebhook.json();
const topupReplay = await worker.fetch(await signedStripeRequest(topupEvent, stripeWebhookSecret), purchaseWebhookEnv);
const topupReplayBody = await topupReplay.json();
check('topup webhook: signed fulfillment applies once and event/session replay cannot double credit', topupWebhook.status === 200 && topupWebhookBody.ok === true && topupWebhookBody.applied === true && topupWebhookBody.user_id === 'user_111' && topupReplay.status === 200 && topupReplayBody.ok === true && topupReplayBody.applied === false && topupReplayBody.balance_cents === topupWebhookBody.balance_cents);

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
