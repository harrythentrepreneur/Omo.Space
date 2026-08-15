// Registry-first Tier-2 dispatch + billing contract test (no network, no keys).

import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { webcrypto } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const clerkFrontendApi = 'registry-test.clerk.accounts.dev';
const clerkPublishableKey = `pk_test_${Buffer.from(`${clerkFrontendApi}$`).toString('base64url')}`;
const clerkKeyPair = await webcrypto.subtle.generateKey(
  { name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' },
  true,
  ['sign', 'verify'],
);
const clerkJwk = {
  ...(await webcrypto.subtle.exportKey('jwk', clerkKeyPair.publicKey)),
  kid: 'registry-test-kid',
  alg: 'RS256',
  use: 'sig',
};

async function clerkToken(userId) {
  const now = Math.floor(Date.now() / 1000);
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString('base64url');
  const header = encode({ alg: 'RS256', typ: 'JWT', kid: clerkJwk.kid });
  const payload = encode({
    sub: userId,
    iss: `https://${clerkFrontendApi}`,
    azp: 'https://omo.space',
    iat: now,
    nbf: now - 1,
    exp: now + 300,
  });
  const input = `${header}.${payload}`;
  const signature = await webcrypto.subtle.sign(
    'RSASSA-PKCS1-v1_5', clerkKeyPair.privateKey, new TextEncoder().encode(input),
  );
  return `${input}.${Buffer.from(signature).toString('base64url')}`;
}

function stripModule(relativePath) {
  return fs.readFileSync(path.join(here, relativePath), 'utf8')
    .replace(/^import .*$/gm, '')
    .replace(/^export /gm, '');
}

const prelude = stripModule('balance.mjs') + '\n'
  + stripModule('cost-model.mjs') + '\n'
  + stripModule('hosted-skills.generated.mjs') + '\n';
const workerSource = fs.readFileSync(path.join(here, 'worker.js'), 'utf8').replace(/^import .*$/gm, '');
const bundled = prelude + workerSource.replace('export default', 'const __workerExport =');

const manifest = JSON.parse(fs.readFileSync(
  path.join(root, 'manifests', 'llm-tools', 'generated', 'phonics-list-generator@1.json'), 'utf8',
));
const profile = JSON.parse(fs.readFileSync(
  path.join(root, 'packages', 'skill-to-modal', 'profiles', 'phonics-list-generator.json'), 'utf8',
));
const input = profile.happy_path.input;
const domainOutput = Object.fromEntries(
  Object.entries(profile.happy_path.output)
    .filter(([key]) => !['run_id', 'status', 'workflow_version', 'usage'].includes(key)),
);

function registryRow(overrides = {}) {
  const payload = manifest.payload;
  return {
    tool_id: payload.tool_id,
    slug: payload.slug,
    tier: 2,
    name: 'Phonics List Generator',
    status: 'live',
    chargeable: true,
    active: true,
    version: payload.version,
    manifest,
    manifest_sha256: manifest.payload_sha256,
    price_cents: payload.pricing.price_cents,
    runtime_family: null,
    runner_release: 'stable',
    adapter_key: 'opencode-go',
    catalog_json: { name: 'Phonics List Generator', description: 'Test public projection.' },
    ...overrides,
  };
}

let runnerMode = 'success';
const runnerCalls = [];
const sandbox = {
  fetch: async (url, options = {}) => {
    if (String(url).includes('/.well-known/jwks.json')) {
      return { ok: true, status: 200, json: async () => ({ keys: [clerkJwk] }) };
    }
    if (String(url).startsWith('https://omo-space--omo-llm-runner-api.modal.run/')) {
      const request = JSON.parse(String(options.body || '{}'));
      runnerCalls.push({ url: String(url), options, request });
      let body;
      let status = 200;
      if (runnerMode === 'invalid') {
        body = { spec_version: 'omo.result/v1', run_id: request.run_id, status: 'completed' };
      } else if (runnerMode === 'failure') {
        status = 502;
        body = { status: 'failed', error: { code: 'LLM_UNAVAILABLE' } };
      } else {
        body = {
          spec_version: 'omo.result/v1',
          run_id: request.run_id,
          tool_id: request.tool_id,
          tool_version: request.tool_version,
          status: 'completed',
          data: domainOutput,
          artifacts: [],
          usage: {
            adapter: 'opencode-go@1',
            provider: 'opencode-go',
            model: 'deepseek-v4-flash',
            prompt_tokens: 100,
            completion_tokens: 50,
            provider_calls: 1,
            estimated_cost_usd: 0.000035,
          },
        };
      }
      return {
        ok: status >= 200 && status < 300,
        status,
        text: async () => JSON.stringify(body),
      };
    }
    throw new Error(`unexpected outbound request: ${url}`);
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
vm.runInContext(`${bundled}\n;globalThis.__workerExport = __workerExport;`, sandbox, { filename: 'worker.js' });
const worker = sandbox.__workerExport;

const baseEnv = {
  CLERK_PUBLISHABLE_KEY: clerkPublishableKey,
  OMO_LLM_RUNNER_URL: 'https://omo-space--omo-llm-runner-api.modal.run',
  HOSTED_MODAL_PROXY_TOKEN_ID: 'test-proxy-id',
  HOSTED_MODAL_PROXY_TOKEN_SECRET: 'test-proxy-secret',
};

async function request(method, pathname, userId, body, idempotencyKey = '') {
  const subject = userId.startsWith('user_')
    ? userId.replace(/[^A-Za-z0-9_-]/g, '_')
    : `user_${userId.replace(/[^A-Za-z0-9_-]/g, '_')}`;
  const headers = { Authorization: `Bearer ${await clerkToken(subject)}` };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
  return new Request(`https://omo.space${pathname}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function invoke(env, method, pathname, userId, body, idempotencyKey = '') {
  const response = await worker.fetch(await request(method, pathname, userId, body, idempotencyKey), env);
  return { response, body: await response.json() };
}

let passed = 0;
function check(name, condition) {
  if (!condition) throw new Error(`FAIL  ${name}`);
  passed += 1;
  console.log(`PASS  ${name}`);
}

const successEnv = { ...baseEnv, __TEST_REGISTRY_ROWS: [registryRow()] };
const publicResult = await invoke(successEnv, 'GET', '/api/run?slug=phonics-list-generator', 'registry-public');
check('registry GET returns the public projection without the signed prompt',
  publicResult.response.status === 200 && publicResult.body.slug === manifest.payload.slug &&
  publicResult.body.price_cents === 10 && !('manifest' in publicResult.body) &&
  !JSON.stringify(publicResult.body).includes(manifest.payload.prompt.system_template));

const success = await invoke(
  successEnv, 'POST', '/api/run', 'registry-success-user',
  { slug: manifest.payload.slug, input }, 'registry-success-key',
);
check('reviewed Tier-2 row executes through the shared runner and returns omo.result/v1',
  success.response.status === 200 && success.body.ok === true &&
  success.body.output.spec_version === 'omo.result/v1' && success.body.output.data.words.length === 8);
check('billing reads the registry price once and debits the $5 grant to $4.90',
  success.body.quoted_cost_usd === 0.1 && success.body.billed_amount_usd === 0.1 && success.body.balance === 4.9);
const forwarded = runnerCalls.at(-1);
check('handoff pins run, tool, version, hash, signature, manifest, and exact typed input',
  forwarded.request.spec_version === 'omo.runner-request/v1' &&
  forwarded.request.run_id === success.body.run_id &&
  forwarded.request.tool_id === manifest.payload.tool_id &&
  forwarded.request.tool_version === 1 &&
  forwarded.request.manifest_sha256 === manifest.payload_sha256 &&
  forwarded.request.execution_manifest.signature.value === manifest.signature.value &&
  JSON.stringify(forwarded.request.input) === JSON.stringify(input));
check('runner target and Proxy Token headers are environment-owned',
  forwarded.url === `${baseEnv.OMO_LLM_RUNNER_URL}/v1/runs` &&
  forwarded.options.headers['Modal-Key'] === 'test-proxy-id' &&
  forwarded.options.headers['Modal-Secret'] === 'test-proxy-secret');

const callsAfterSuccess = runnerCalls.length;
const replay = await invoke(
  successEnv, 'POST', '/api/run', 'registry-success-user',
  { slug: manifest.payload.slug, input }, 'registry-success-key',
);
check('identical idempotency replay returns the terminal run without a second provider effect',
  replay.response.status === 200 && replay.body.idempotent_replay === true &&
  replay.body.run_id === success.body.run_id && runnerCalls.length === callsAfterSuccess);
const conflict = await invoke(
  successEnv, 'POST', '/api/run', 'registry-success-user',
  { slug: manifest.payload.slug, input: { ...input, topic: 'city animals' } }, 'registry-success-key',
);
check('changed input with the same idempotency key conflicts before dispatch',
  conflict.response.status === 409 && conflict.body.error === 'idempotency_key_conflict' &&
  runnerCalls.length === callsAfterSuccess);

const status = await invoke(successEnv, 'GET', `/api/run/${success.body.run_id}`, 'registry-success-user');
check('run status replays the stored registry result without consulting a per-tool endpoint',
  status.response.status === 200 && status.body.run_id === success.body.run_id &&
  status.body.state === 'succeeded' && runnerCalls.length === callsAfterSuccess);

const invalidInput = await invoke(
  successEnv, 'POST', '/api/run', 'registry-invalid-input-user',
  { slug: manifest.payload.slug, input: { topic: 'missing required fields' } }, 'registry-invalid-input',
);
check('invalid input is rejected before reservation, debit, or runner dispatch',
  invalidInput.response.status === 422 && invalidInput.body.error === 'invalid_registry_input' &&
  runnerCalls.length === callsAfterSuccess);

const gateCases = [
  ['candidate row', registryRow({ active: false, chargeable: false, status: 'draft' }), 503, 'workflow_not_ready'],
  ['Tier 1 row', registryRow({ tier: 1 }), 503, 'tier_1_runner_not_ready'],
  ['Tier 3 row', registryRow({ tier: 3 }), 409, 'download_only'],
  ['Tier 4 row', registryRow({ tier: 4 }), 503, 'tier_4_adapter_not_ready'],
  ['price drift', registryRow({ price_cents: 11 }), 503, 'manifest_price_mismatch'],
  ['manifest hash drift', registryRow({ manifest_sha256: '0'.repeat(64) }), 503, 'manifest_identity_mismatch'],
];
for (const [label, row, expectedStatus, expectedError] of gateCases) {
  const before = runnerCalls.length;
  const result = await invoke(
    { ...baseEnv, __TEST_REGISTRY_ROWS: [row] }, 'POST', '/api/run', `gate-${label.replaceAll(' ', '-')}`,
    { slug: row.slug, input }, `gate-${label.replaceAll(' ', '-')}`,
  );
  check(`${label} fails closed before debit or runner dispatch`,
    result.response.status === expectedStatus && result.body.error === expectedError && runnerCalls.length === before);
}

const missing = await invoke(
  { ...baseEnv, __TEST_REGISTRY_ROWS: [] }, 'POST', '/api/run', 'registry-missing-user',
  { slug: 'not-in-registry', input: {} }, 'registry-missing',
);
check('an enforced registry lookup rejects an absent slug',
  missing.response.status === 404 && missing.body.error === 'unknown_catalog_slug');

runnerMode = 'invalid';
const failedEnv = { ...baseEnv, __TEST_REGISTRY_ROWS: [registryRow()] };
const failed = await invoke(
  failedEnv, 'POST', '/api/run', 'registry-refund-user',
  { slug: manifest.payload.slug, input }, 'registry-refund-key',
);
check('invalid runner output fails closed with a terminal refunded result',
  failed.response.status === 502 && failed.body.state === 'refunded' &&
  failed.body.reason === 'llm_runner_invalid_output');
const balance = await invoke(failedEnv, 'GET', '/api/me', 'registry-refund-user');
check('terminal runner failure refunds exactly to the original $5 balance',
  balance.response.status === 200 && balance.body.balance_cents === 500);
const callsAfterFailure = runnerCalls.length;
const failedReplay = await invoke(
  failedEnv, 'POST', '/api/run', 'registry-refund-user',
  { slug: manifest.payload.slug, input }, 'registry-refund-key',
);
check('refunded replay neither dispatches nor refunds twice',
  failedReplay.response.status === 502 && failedReplay.body.idempotent_replay === true &&
  runnerCalls.length === callsAfterFailure);

console.log(`\n${passed} passed, 0 failed`);
