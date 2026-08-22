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
import { DatabaseSync } from 'node:sqlite';
import { fileURLToPath } from 'node:url';

globalThis.crypto ??= webcrypto;
const { signPilotToken } = await import('./pilot-magic.mjs');

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
  + stripModule('pilot-magic.mjs') + '\n'
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
const builderDispatchCalls = [];
const supportCalls = [];
const modalStatuses = new Map();
let modalDispatchStatus = 202;
const wovenCalls = [];
const wovenStatuses = new Map();
const japaneseCalls = [];
const japaneseStatuses = new Map();
const issue141Calls = [];
const issue141Statuses = new Map();
const facebookCalls = [];
const facebookStatuses = new Map();
const facebookCases = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'containers', 'facebook-ads-copywriter', 'tests', 'cases.json'), 'utf8'));
const japaneseCases = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'containers', 'japanese-style-story-video', 'tests', 'cases.json'), 'utf8'));
let workerNativeMode = 'valid';
let workerNativeProviderGate = null;
let releaseWorkerNativeProvider = null;
const neonSqlCalls = [];
let neonPoolShouldThrow = false;
let neonQueryFailureFragment = '';
let neonInfoSchemaTableExists = false;
let neonInfoSchemaColumns = [];
let neonApprovalRow = null;
let neonInternalClaimRow = null;
let neonInternalDetailRow = null;
let neonResumeMergedRow = null;
let neonFinalizationClaimRow = null;
let neonFinalizationDetailRow = null;
let neonFinalizationStatusRow = null;
let neonCompletedFinalizationRow = null;
let neonFailedFinalizationRow = null;
let neonFailedResumeRow = null;
let neonRecoveryRow = null;
let neonFinalizationRegistryRows = [];
let neonFinalizationEffectRow = null;

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
        if (neonQueryFailureFragment && entry.text.includes(neonQueryFailureFragment)) {
          throw new Error('SENTINEL_DATABASE_DETAIL');
        }
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
        if (entry.name && entry.name.startsWith('omo-internal-submission-claim-')) {
          return neonInternalClaimRow ? { rows: [neonInternalClaimRow], rowCount: 1 } : { rows: [], rowCount: 0 };
        }
        if (entry.name === 'omo-internal-submission-detail-v1') {
          return neonInternalDetailRow ? { rows: [neonInternalDetailRow], rowCount: 1 } : { rows: [], rowCount: 0 };
        }
        if (entry.name === 'omo-internal-resume-merged-release-v1') {
          return neonResumeMergedRow ? { rows: [neonResumeMergedRow], rowCount: 1 } : { rows: [], rowCount: 0 };
        }
        if (entry.name === 'omo-internal-finalization-resume-completed-v1') {
          return neonCompletedFinalizationRow ? { rows: [neonCompletedFinalizationRow], rowCount: 1 } : { rows: [], rowCount: 0 };
        }
        if (entry.name === 'omo-internal-finalization-failed-v1') {
          return neonFailedFinalizationRow ? { rows: [neonFailedFinalizationRow], rowCount: 1 } : { rows: [], rowCount: 0 };
        }
        if (entry.name === 'omo-internal-finalization-resume-failed-v1') {
          const allowed = Array.isArray(entry.values[1]) &&
            entry.values[1].includes(neonFailedResumeRow && neonFailedResumeRow.finalization_failure_code);
          return neonFailedResumeRow && allowed ? { rows: [neonFailedResumeRow], rowCount: 1 } : { rows: [], rowCount: 0 };
        }
        if (entry.name === 'omo-internal-finalization-recover-rolled-back-v1') {
          return neonRecoveryRow ? { rows: [neonRecoveryRow], rowCount: 1 } : { rows: [], rowCount: 0 };
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
    if (String(url) === 'https://builder.modal.run') {
      builderDispatchCalls.push({ url: String(url), opts, payload: JSON.parse(opts.body) });
      return { ok: true, status: 202, json: async () => ({ status: 'accepted' }) };
    }
    if (String(url) === 'https://support-broker.invalid/v1/chat') {
      const payload = JSON.parse(opts.body);
      supportCalls.push({ url: String(url), opts, payload });
      return new Response(JSON.stringify({
        ok: true, profile: 'omo-support', mode: 'support', session_id: payload.session_id, message: 'Support reply',
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
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
    if (String(url).startsWith('https://japanese.modal.invalid')) {
      const target = new URL(String(url));
      japaneseCalls.push({ url: String(url), method: opts && opts.method || 'GET', headers: opts && opts.headers, body: opts && opts.body });
      if (target.pathname === '/v1/runs' && opts && opts.method === 'POST') {
        const callId = 'fc-JAPANESEROUTER001';
        const runId = 'run-0123456789abcdef0123456789abcdef';
        const accessToken = 'japanese_owner_token_0123456789abcdefghi';
        const resultUrl = `/v1/runs/${runId}?call_id=${callId}&access_token=${accessToken}`;
        japaneseStatuses.set(callId, { status: 202, body: { run_id: runId, status: 'processing' } });
        return { ok: true, status: 202, json: async () => ({ run_id: runId, call_id: callId, status: 'accepted', result_url: resultUrl }) };
      }
      const callId = target.searchParams.get('call_id');
      const value = japaneseStatuses.get(callId);
      return value
        ? { ok: value.status >= 200 && value.status < 300, status: value.status, json: async () => value.body }
        : { ok: false, status: 404, json: async () => ({ detail: 'run_not_found' }) };
    }
    if (String(url).startsWith('https://issue141-canary.modal.invalid')) {
      const target = new URL(String(url));
      issue141Calls.push({ url: String(url), method: opts && opts.method || 'GET', headers: opts && opts.headers });
      const callId = target.searchParams.get('call_id');
      const value = issue141Statuses.get(callId);
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
      if (workerNativeMode === 'late_success_after_refund' && workerNativeProviderGate) {
        await workerNativeProviderGate;
      }
      const modelOutput = { ...facebookCases.happy_path.output };
      delete modelOutput.run_id;
      delete modelOutput.status;
      delete modelOutput.workflow_version;
      delete modelOutput.usage;
      return llmResponse(200, {
        choices: [{ message: { content: JSON.stringify(modelOutput) } }],
        usage: { prompt_tokens: 820, completion_tokens: 640 },
      });
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
          : text.includes('UPDATE submissions') && text.includes('failure_code IN') && text.includes("status = 'queued'")
            ? 'omo-submission-retry-v2'
            : text.includes("SELECT id,slug,source_sha256,selected_runtime") && text.includes('WHERE id = $1')
              ? 'omo-internal-submission-detail-v1'
              : text.includes('WITH candidate AS') && text.includes('build_claimed_at')
                ? 'omo-internal-submission-claim-v1'
              : text.includes('WITH candidate AS') && text.includes('finalization_id') && text.includes("finalization_status = 'claimed'")
                ? 'omo-internal-finalization-claim-v1'
              : text.includes("status IN ('ready_for_publish', 'deployed')") && text.includes("finalization_status = 'completed'") && text.includes('SELECT')
                ? 'omo-internal-finalization-resume-completed-v1'
              : text.includes("finalization_status = 'failed'") && text.includes('finalization_modal_receipt IS NOT NULL') && text.includes('SELECT')
                ? 'omo-internal-finalization-failed-v1'
              : text.includes('finalization_recovery_receipt = $1')
                ? 'omo-internal-finalization-recover-rolled-back-v1'
              : text.includes("SET status = 'ready_for_deploy'") && text.includes('finalization_id = NULL') && text.includes("finalization_status = 'failed'")
                ? 'omo-internal-finalization-resume-failed-v1'
              : text.includes('SELECT DISTINCT published_slug')
                ? 'omo-internal-finalization-registry-slugs-v1'
              : text.includes('SET finalization_modal_receipt =')
                ? 'omo-internal-finalization-effect-modal_deploy-v1'
              : text.includes('SET finalization_worker_receipt =')
                ? 'omo-internal-finalization-effect-worker_deploy-v1'
              : text.includes('WHERE finalization_id = $1') && text.includes('finalization_status')
                ? 'omo-internal-finalization-detail-v1'
              : text.includes('SET finalization_status = $1')
                ? 'omo-internal-finalization-status-v1'
              : text.includes("SET status = 'ready_for_publish', release_phase = 'promoted'") && text.includes("finalization_status = 'completed'")
                ? 'omo-internal-finalization-promote-v1'
              : text.includes("SET status = 'ready_for_deploy'") && text.includes("release_phase = 'merged_verified'")
                ? 'omo-internal-resume-merged-release-v1'
                : null,
        connectionString,
      };
      neonSqlCalls.push(entry);
      if (entry.name === 'omo-submission-approve-v1' || entry.name === 'omo-submission-retry-v2') {
        return neonApprovalRow ? { rows: [neonApprovalRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-submission-detail-v1') {
        return neonInternalDetailRow ? { rows: [neonInternalDetailRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-submission-claim-v1') {
        return neonInternalClaimRow ? { rows: [neonInternalClaimRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-finalization-claim-v1') {
        return neonFinalizationClaimRow ? { rows: [neonFinalizationClaimRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-finalization-resume-completed-v1') {
        return neonCompletedFinalizationRow ? { rows: [neonCompletedFinalizationRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-finalization-failed-v1') {
        return neonFailedFinalizationRow ? { rows: [neonFailedFinalizationRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-finalization-resume-failed-v1') {
        const allowed = Array.isArray(entry.values[1]) &&
          entry.values[1].includes(neonFailedResumeRow && neonFailedResumeRow.finalization_failure_code);
        return neonFailedResumeRow && allowed ? { rows: [neonFailedResumeRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-finalization-recover-rolled-back-v1') {
        return neonRecoveryRow ? { rows: [neonRecoveryRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-finalization-registry-slugs-v1') {
        return { rows: neonFinalizationRegistryRows, rowCount: neonFinalizationRegistryRows.length };
      }
      if (entry.name === 'omo-internal-finalization-effect-modal_deploy-v1' || entry.name === 'omo-internal-finalization-effect-worker_deploy-v1') {
        return neonFinalizationEffectRow ? { rows: [neonFinalizationEffectRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-finalization-detail-v1') {
        return neonFinalizationDetailRow ? { rows: [neonFinalizationDetailRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-finalization-status-v1' || entry.name === 'omo-internal-finalization-promote-v1') {
        return neonFinalizationStatusRow ? { rows: [neonFinalizationStatusRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      if (entry.name === 'omo-internal-resume-merged-release-v1') {
        return neonResumeMergedRow ? { rows: [neonResumeMergedRow], rowCount: 1 } : { rows: [], rowCount: 0 };
      }
      return { rows: [], rowCount: 0 };
    },
  }),
};
vm.createContext(sandbox);
vm.runInContext(`${cjs}\n;globalThis.__workerExport = __workerExport;globalThis.__workerTest = { mockSubmissions, mockRunRequests, constantTimeEquals, claimRunRequest, getRunRequestById, putRunProgress, getRunProgress, refreshHostedModalRun, HOSTED_MODAL_SKILLS, SUBMISSIONS_SCHEMA_MIGRATIONS, REQUIRED_SUBMISSIONS_COLUMNS, reviewedSourceApprovalAllowlist, internalClaimSubmission, internalClaimRow, internalClaimFinalization, internalResumeCompletedFinalization, completedFinalizationRow, internalInspectFailedFinalization, failedFinalizationRow, internalResumeFailedFinalization, internalRecoverRolledBackFinalization, internalSetFinalizationStatus, internalPromoteFinalization, internalRequiredRegistrySlugs, safeDeploymentReceipt, finalizationGenerationAllowsEffect, internalRecordFinalizationEffect, authenticateAccount, mockApiKeys, ensureProductionCanaryIdentity, userIdForApiKey, internalResumeMergedRelease };`, sandbox, { filename: 'worker.js' });
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
  (workerSrc.match(/await client\.release\(\)/g) || []).length === 13);

const dashboardSource = fs.readFileSync(path.join(here, '..', 'dashboard.html'), 'utf8');
const billingSource = fs.readFileSync(path.join(here, '..', 'billing.html'), 'utf8');
const creditsSource = fs.readFileSync(path.join(here, '..', 'credits.js'), 'utf8');
const indexSource = fs.readFileSync(path.join(here, '..', 'index.html'), 'utf8');
const runPageSource = fs.readFileSync(path.join(here, '..', 'run.html'), 'utf8');
const pilotClaimPageSource = fs.readFileSync(path.join(here, '..', 'pilot-claim.html'), 'utf8');
const pilotClaimClientSource = fs.readFileSync(path.join(here, '..', 'pilot-claim.js'), 'utf8');
const signupModalSource = fs.readFileSync(path.join(here, '..', 'signup-modal.js'), 'utf8');
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
check('pilot landing: preserves the signed bearer through Clerk auth, then redeems with the session token',
  pilotClaimPageSource.includes('pilot-claim.js') &&
  pilotClaimClientSource.includes("window.Clerk.session.getToken()") &&
  pilotClaimClientSource.includes("method: 'POST'") &&
  pilotClaimClientSource.includes("Authorization: 'Bearer '") &&
  signupModalSource.includes("return '/pilot-claim.html?token=' + encodeURIComponent(pilotToken)"));
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
check('run page: textarea array inputs accept one item per line and examples preserve lines', runPageSource.includes("component: 'ArrayTextField'") && runPageSource.includes("value = multilineArrayValue(control.value)") && runPageSource.includes("values[key].join('\\n')"));
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
check('creator upload: reviewed failed submissions expose the generalized gated-build retry',
  uploadSource.includes('Retry gated build') &&
  uploadSource.includes('Reviewed gated build needs another attempt') &&
  uploadSource.includes("submission.status === 'failed'") &&
  uploadSource.includes("isRetryableReviewedBuildFailure(submission)") &&
  uploadSource.includes("var retryableFailureCodes = ['build_or_deploy_failed', 'canary_or_internal_failed']") &&
  uploadSource.includes("retryableFailureCodes.includes(submission.failure_code) && !submission.selected_runtime") &&
  !uploadSource.includes("submission.approval_reason === 'exact_source_slug_collision'") &&
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

const issue141CanaryKey = 'issue141-canary-' + 'a'.repeat(32);
const issue141CanaryEnv = {
  ...env,
  ENVIRONMENT: 'staging',
  ISSUE141_CANARY_API_KEY: issue141CanaryKey,
  LABEL_NORMALIZER_CANARY_MODAL_URL: 'https://issue141-canary.modal.invalid',
  HOSTED_MODAL_PROXY_TOKEN_ID: 'issue141-modal-id',
  HOSTED_MODAL_PROXY_TOKEN_SECRET: 'issue141-modal-secret',
};
const issue141Headers = { 'X-API-Key': issue141CanaryKey, 'Idempotency-Key': 'issue141-staging-auth-test' };
const issue141Accepted = await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'label-normalizer-canary', input: { labels: [] },
}, issue141Headers), issue141CanaryEnv);
check('issue141 staging canary: exact slug accepts secret-backed identity before schema validation', issue141Accepted.status === 422);
const issue141WrongSlug = await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'japanese-style-story-video', input: {},
}, { ...issue141Headers, 'Idempotency-Key': 'issue141-wrong-slug' }), issue141CanaryEnv);
check('issue141 staging canary: key cannot authenticate another workflow', issue141WrongSlug.status === 401);
const issue141Production = await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'label-normalizer-canary', input: { labels: [] },
}, { ...issue141Headers, 'Idempotency-Key': 'issue141-production' }), { ...issue141CanaryEnv, ENVIRONMENT: 'production' });
check('issue141 staging canary: key cannot authenticate production', issue141Production.status === 401);
workerTest.mockRunRequests.set('issue141-staging-poll', {
  run_id: 'run_issue141stagingauth', user_id: 'user_issue141_canary', slug: 'label-normalizer-canary',
  state: 'refunded', cost_cents: 10, http_status: 502, response_json: JSON.stringify({ error: 'test_terminal' }),
});
const issue141Poll = await worker.fetch(mkReq('GET', '/api/run/run_issue141stagingauth', {}, {
  'X-API-Key': issue141CanaryKey,
}), issue141CanaryEnv);
check('issue141 staging canary: poll binds identity only after exact-slug row lookup', issue141Poll.status === 502);
workerTest.mockRunRequests.delete('issue141-staging-poll');

function sqliteD1Binding(db) {
  return {
    prepare(sql) {
      return {
        bind(...values) {
          return {
            first: async () => db.prepare(sql).get(...values) || null,
            run: async () => {
              const result = db.prepare(sql).run(...values);
              return { meta: { changes: Number(result.changes) } };
            },
            all: async () => ({ results: db.prepare(sql).all(...values) }),
          };
        },
      };
    },
  };
}

const issue141DurableDb = new DatabaseSync(':memory:');
issue141DurableDb.exec(fs.readFileSync(path.join(here, 'staging-d1-schema.sql'), 'utf8'));
const issue141WriterEnv = { BALANCE_DB: sqliteD1Binding(issue141DurableDb) };
const issue141ReaderEnv = {
  BALANCE_DB: sqliteD1Binding(issue141DurableDb),
  LABEL_NORMALIZER_CANARY_MODAL_URL: 'https://issue141-canary.modal.invalid',
  HOSTED_MODAL_PROXY_TOKEN_ID: 'issue141-modal-id',
  HOSTED_MODAL_PROXY_TOKEN_SECRET: 'issue141-modal-secret',
};
const durableClaim = await workerTest.claimRunRequest(
  issue141WriterEnv, 'user_issue141_canary', 'issue141-cross-isolate', 'a'.repeat(64),
  'label-normalizer-canary', 10, 'run_issue141crossisolate'
);
const issue141ProviderRunId = 'run-0123456789abcdef0123456789abcdef';
const issue141CallId = 'fc-issue141test';
const issue141AccessToken = 'a'.repeat(32);
const issue141ResultUrl = `/v1/runs/${issue141ProviderRunId}?call_id=${issue141CallId}&access_token=${issue141AccessToken}`;
await workerTest.putRunProgress(issue141WriterEnv, {
  run_id: 'run_issue141crossisolate', user_id: 'user_issue141_canary', phase: 'running',
  progress_pct: 35, progress_source: 'modal', modal_status: 'accepted',
  modal_status_url: `https://issue141-canary.modal.invalid${issue141ResultUrl}`,
  result_json: JSON.stringify({
    call_id: issue141CallId, run_id: issue141ProviderRunId, result_url: issue141ResultUrl,
  }),
});
const issue141Output = JSON.parse(fs.readFileSync(
  path.join(here, '..', '..', 'containers', 'label-normalizer-canary', 'tests', 'cases.json'), 'utf8'
)).happy_path.output;
issue141Statuses.set(issue141CallId, { status: 200, body: issue141Output });
const durableRow = await workerTest.getRunRequestById(issue141ReaderEnv, 'run_issue141crossisolate');
const durableResult = await workerTest.refreshHostedModalRun(
  issue141ReaderEnv, workerTest.HOSTED_MODAL_SKILLS.get('label-normalizer-canary'), durableRow
);
const durableTerminal = await workerTest.getRunRequestById(issue141ReaderEnv, 'run_issue141crossisolate');
const durableProgress = await workerTest.getRunProgress(issue141ReaderEnv, 'run_issue141crossisolate');
const durableReplay = await workerTest.refreshHostedModalRun(
  issue141ReaderEnv, workerTest.HOSTED_MODAL_SKILLS.get('label-normalizer-canary'), durableTerminal
);
check('issue141 staging D1: independent binding recovers, polls, settles, and replays exact Modal run',
  durableClaim.created === true && durableResult.status === 200 && durableResult.body.output.input_count === 3 &&
  durableTerminal?.state === 'succeeded' && durableProgress?.phase === 'delivered' &&
  issue141Calls.length === 1 && issue141Calls[0].url.endsWith(issue141ResultUrl) &&
  issue141Calls[0].headers['X-Omo-Owner-Id'] === 'user_issue141_canary' &&
  durableReplay.status === 200 && durableReplay.body.run_id === 'run_issue141crossisolate');
issue141DurableDb.close();

// OPTIONS → 200 + CORS
const opt = await worker.fetch(mkReq('OPTIONS', '/api/ugc-script-studio'), env);
check('router: OPTIONS returns 200 + CORS', opt.status === 200 && opt.headers.get('Access-Control-Allow-Origin') === '*');

// GET → 405
const get = await worker.fetch(mkReq('GET', '/api/ugc-script-studio'), env);
check('router: GET returns 405', get.status === 405);

// Unknown route → 404
const nf = await worker.fetch(mkReq('POST', '/api/nope', {}), env);
const nfBody = await nf.json();
check('router: unknown route returns 404 + routes list', nf.status === 404 && Array.isArray(nfBody.routes) && nfBody.routes.length === 13 && nfBody.routes.includes('/api/support/chat') && nfBody.routes.includes('/api/pilot/claim'));

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
const supportEnv = {
  ...realEnv,
  OMO_SUPPORT_BROKER_URL: 'https://support-broker.invalid/v1/chat',
  OMO_SUPPORT_SHARED_SECRET: 'support-shared-secret-for-tests',

};
const supportMissingAuth = await worker.fetch(mkReq('POST', '/api/support/chat', {
  session_id: 'support_guest_abcdefgh', message: 'help', context: 'Page: /support; title: Support',
}), supportEnv);
const guestSupportCall = supportCalls[0];
check('support: guests receive a server-derived identity and page/problem context',
  supportMissingAuth.status === 200
  && /^user_guest_[0-9a-f]{24}$/.test(guestSupportCall.payload.user_id)
  && guestSupportCall.payload.message.includes('PAGE CONTEXT (untrusted): Page: /support; title: Support')
  && guestSupportCall.payload.message.includes('USER PROBLEM:\nhelp'));
const supportResponse = await worker.fetch(mkReq('POST', '/api/support/chat', {
  session_id: 'support_abcdefgh', message: 'My upload is stuck', maintainer: false, profile: 'omo-dev',
}, creatorHeaders), supportEnv);
const supportBody = await supportResponse.json();
const supportCall = supportCalls[1];
check('support: browser privilege fields are dropped and response is pinned to diagnosis-only omo-support',
  supportResponse.status === 200 && supportBody.profile === 'omo-support' && supportBody.mode === 'support'
  && supportCall.payload.maintainer === undefined && supportCall.payload.user_id === 'user_creator'
  && supportCall.payload.profile === undefined);
check('support: Worker signs timestamp, nonce, and body without exposing its secret',
  /^[0-9]+$/.test(supportCall.opts.headers['X-Omo-Timestamp'])
  && /^[0-9a-f]{32}$/.test(supportCall.opts.headers['X-Omo-Nonce'])
  && /^[0-9a-f]{64}$/.test(supportCall.opts.headers['X-Omo-Signature'])
  && !supportCall.opts.body.includes('support-shared-secret-for-tests'));
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
  retryBody.submission.status === 'queued' &&
  retryBody.submission.failure_code === null &&
  retryBody.submission.approved_by === 'user_creator' &&
  retryBody.submission.approval_reason === 'exact_source_slug_collision' &&
  retryBody.submission.selected_runtime === 'worker-native' &&
  !retryText.includes('server keeps retry content private') &&
  !retryText.includes('retry-anyway') &&
  !retryText.includes('ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'));

const retryReplayResponse = await worker.fetch(mkReq('POST', `/api/submissions/${retryRecord.id}/retry`, {}, creatorHeaders), realEnv);
check('submission retry: replay rejects because only failed rows are retryable', retryReplayResponse.status === 409);

const retryCanaryRecord = {
  ...retryRecord,
  id: 'sub_retrycanary000000000000000001',
  status: 'failed',
  failure_code: 'build_or_deploy_failed',
  selected_runtime: null,
  runtime_policy: null,
  updated_at: '2026-08-14T00:04:00.000Z',
};
workerTest.mockSubmissions.set(`user_creator\u0000${retryCanaryRecord.id}`, retryCanaryRecord);
const retryCanaryResponse = await worker.fetch(mkReq('POST', `/api/submissions/${retryCanaryRecord.id}/retry`, {}, creatorHeaders), realEnv);
const retryCanaryBody = await retryCanaryResponse.json();
check('submission retry: owner can requeue a pre-runtime build failure through the same review gates',
  retryCanaryResponse.status === 200 &&
  retryCanaryBody.ok === true &&
  retryCanaryBody.retried === true &&
  retryCanaryBody.submission.id === retryCanaryRecord.id &&
  retryCanaryBody.submission.status === 'queued' &&
  retryCanaryBody.submission.failure_code === null &&
  retryCanaryBody.submission.approved_by === 'user_creator' &&
  retryCanaryBody.submission.approval_reason === 'exact_source_slug_collision' &&
  retryCanaryBody.submission.selected_runtime === null);

const retryReviewedNewRecord = {
  ...retryRecord,
  id: 'sub_retryreviewednew00000000000001',
  slug: 'brand-new-reviewed-workflow',
  sourceSha256: 'a'.repeat(64),
  source_sha256: 'a'.repeat(64),
  status: 'failed',
  failure_code: 'canary_or_internal_failed',
  approved_at: null,
  approved_by: null,
  approval_reason: null,
  release_phase: 'canary_failed',
  release_issue_url: 'https://example.invalid/issue/1',
  release_pr_url: 'https://example.invalid/pr/1',
  canary_evidence: '{"failed":true}',
  build_evidence: '{"old":true}',
};
workerTest.mockSubmissions.set(`user_creator\u0000${retryReviewedNewRecord.id}`, retryReviewedNewRecord);
const retryReviewedNewResponse = await worker.fetch(mkReq('POST', `/api/submissions/${retryReviewedNewRecord.id}/retry`, {}, creatorHeaders), realEnv);
const retryReviewedNewBody = await retryReviewedNewResponse.json();
check('submission retry: reviewed new submission is requeued without publishing or changing identity/runtime',
  retryReviewedNewResponse.status === 200 &&
  retryReviewedNewBody.submission.status === 'queued' &&
  retryReviewedNewBody.submission.failure_code === null &&
  retryReviewedNewBody.submission.selected_runtime === 'worker-native' &&
  retryReviewedNewBody.submission.source_sha256 === 'a'.repeat(64) &&
  retryReviewedNewRecord.release_phase === null &&
  retryReviewedNewRecord.release_issue_url === null &&
  retryReviewedNewRecord.canary_evidence === null &&
  retryReviewedNewRecord.build_evidence === null &&
  !retryReviewedNewBody.submission.published_slug);

const retryFailClosedRecords = [
  ['sub_retryhash00000000000000000001', 'failed', 'build_or_deploy_failed', 'g'.repeat(64), 'worker-native', 'reviewed_policy'],
  ['sub_retrystatus000000000000000001', 'needs_review', 'build_or_deploy_failed', reviewedWovenSourceSha, 'worker-native', 'reviewed_policy'],
  ['sub_retrycode00000000000000000001', 'failed', 'generated_source_hash_mismatch', reviewedWovenSourceSha, 'worker-native', 'reviewed_policy'],
  ['sub_retryruntime00000000000000001', 'failed', 'build_or_deploy_failed', reviewedWovenSourceSha, 'client-invented', 'reviewed_policy'],
  ['sub_retryunreviewed00000000000001', 'failed', 'build_or_deploy_failed', reviewedWovenSourceSha, 'worker-native', null],
];
for (const [id, status, failureCode, sourceSha256, selectedRuntime, runtimePolicy] of retryFailClosedRecords) {
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
    selected_runtime: selectedRuntime,
    runtime_policy: runtimePolicy,
    status,
    failure_code: failureCode,
    created_at: '2026-08-14T00:00:00.000Z',
    updated_at: '2026-08-14T00:02:00.000Z',
  });
}
const retryMismatch = await worker.fetch(mkReq('POST', '/api/submissions/sub_retryhash00000000000000000001/retry', {}, creatorHeaders), realEnv);
const retryWrongStatus = await worker.fetch(mkReq('POST', '/api/submissions/sub_retrystatus000000000000000001/retry', {}, creatorHeaders), realEnv);
const retryWrongCode = await worker.fetch(mkReq('POST', '/api/submissions/sub_retrycode00000000000000000001/retry', {}, creatorHeaders), realEnv);
const retryWrongRuntime = await worker.fetch(mkReq('POST', '/api/submissions/sub_retryruntime00000000000000001/retry', {}, creatorHeaders), realEnv);
const retryUnreviewed = await worker.fetch(mkReq('POST', '/api/submissions/sub_retryunreviewed00000000000001/retry', {}, creatorHeaders), realEnv);
check('submission retry: invalid identity, state, failure, runtime, and unreviewed rows fail closed',
  retryMismatch.status === 409 &&
  retryWrongStatus.status === 409 &&
  retryWrongCode.status === 409 &&
  retryWrongRuntime.status === 409 &&
  retryUnreviewed.status === 409);

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
              const [, id, userId] = values;
              const row = d1RetryRows.get(id);
              const retryableCode = row && (row.failure_code === 'build_or_deploy_failed' || row.failure_code === 'canary_or_internal_failed');
              const preRuntimeCanary = row && retryableCode && !row.selected_runtime && !row.runtime_policy;
              const reviewedRuntimeFailure = row &&
                (row.selected_runtime === 'worker-native' || row.selected_runtime === 'modal-hosted') && row.runtime_policy;
              const allowed = row && row.user_id === userId &&
                /^[a-f0-9]{64}$/.test(row.source_sha256) &&
                row.status === 'failed' &&
                retryableCode &&
                (preRuntimeCanary || reviewedRuntimeFailure);
              if (!allowed) return { meta: { changes: 0 } };
              row.status = 'queued';
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
check('submission retry: D1 permits only reviewed rows with the two gated failure codes',
  retryD1CanaryResponse.status === 200 &&
  retryD1CanaryBody.submission.status === 'queued' &&
  retryD1CanaryBody.submission.failure_code === null &&
  retryD1WrongCode.status === 409 &&
  retryD1UpdateCalls.length >= 2 &&
  retryD1UpdateCalls.every((call) => call.text.includes("failure_code IN ('build_or_deploy_failed', 'canary_or_internal_failed')")) &&
  retryD1UpdateCalls.every((call) => call.text.includes("selected_runtime IN ('worker-native', 'modal-hosted')")) &&
  retryD1UpdateCalls.every((call) => !call.text.includes('generated_source_hash_mismatch')) &&
  JSON.stringify(d1RetryCalls).includes('ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff') === false);

neonSqlCalls.length = 0;
neonApprovalRow = {
  ...retryRecord,
  user_id: 'user_creator',
  source_sha256: reviewedWovenSourceSha,
  status: 'queued',
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
const retryNeonCall = neonSqlCalls.find((call) => call.name === 'omo-submission-retry-v2');
neonApprovalRow = null;
check('submission retry: Neon uses one atomic guarded UPDATE and ignores client hash/runtime/decision',
  retryNeonResponse.status === 200 &&
  retryNeonBody.submission.status === 'queued' &&
  retryNeonCall &&
  retryNeonCall.text.includes('UPDATE submissions') &&
  retryNeonCall.text.includes("status = 'failed'") &&
  retryNeonCall.text.includes("failure_code IN ('build_or_deploy_failed', 'canary_or_internal_failed')") &&
  !retryNeonCall.text.includes('generated_source_hash_mismatch') &&
  retryNeonCall.text.includes("source_sha256 ~ '^[a-f0-9]{64}$'") &&
  retryNeonCall.text.includes("selected_runtime IN ('worker-native', 'modal-hosted')") &&
  retryNeonCall.text.includes("SET status = 'queued'") &&
  retryNeonCall.values[0] === retryRecord.id &&
  retryNeonCall.values[1] === 'user_creator' &&
  retryNeonCall.values.length === 2 &&
  JSON.stringify(neonSqlCalls).includes('retry-anyway') === false &&
  JSON.stringify(neonSqlCalls).includes('ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff') === false);

// Private build-worker bridge: bearer-only, no CORS, bounded strict payloads.
const buildEnv = {
  ...realEnv,
  BUILD_WORKER_TOKEN: 'bridge-token-for-tests',
  RELEASE_FINALIZER_TOKEN: 'finalizer-token-for-tests',
};
const internalHeaders = { Authorization: 'Bearer bridge-token-for-tests', Origin: 'https://omo.space' };
const finalizerHeaders = { Authorization: 'Bearer finalizer-token-for-tests', Origin: 'https://omo.space' };
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

const finalizerSchemaBuilder = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/schema', {}, internalHeaders), migrationEnv,
);
const finalizerSchemaReadback = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/schema', {}, finalizerHeaders), migrationEnv,
);
const finalizerSchemaBody = await finalizerSchemaReadback.json();
check('internal finalization schema: finalizer-only readback is closed to required columns',
  finalizerSchemaBuilder.status === 401 &&
  finalizerSchemaReadback.status === 200 &&
  JSON.stringify(finalizerSchemaBody) === JSON.stringify({
    ok: true, table_exists: true, present: requiredSubmissionColumns, missing: [],
  }));

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

neonSqlCalls.length = 0;
neonPoolShouldThrow = false;
const receiptMigrationBuilder = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/receipt-schema/migrate', {}, internalHeaders), migrationEnv,
);
const receiptMigrationNonempty = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/receipt-schema/migrate', { sql: 'ALTER TABLE attacker' }, finalizerHeaders), migrationEnv,
);
const receiptMigrationFinalizer = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/receipt-schema/migrate', {}, finalizerHeaders), migrationEnv,
);
const receiptMigrationBody = await receiptMigrationFinalizer.json();
const receiptMigrationCalls = neonSqlCalls.map(({ text, values, name }) => ({ text, values, name }));
neonSqlCalls.length = 0;
const receiptMigrationReplay = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/receipt-schema/migrate', {}, finalizerHeaders), migrationEnv,
);
const receiptMigrationReplayBody = await receiptMigrationReplay.json();
const receiptMigrationReplayCalls = neonSqlCalls.map(({ text }) => text);
neonSqlCalls.length = 0;
neonInfoSchemaTableExists = true;
neonInfoSchemaColumns = ['finalization_modal_receipt', 'finalization_worker_receipt', 'finalization_recovery_receipt', 'attacker_column'];
const receiptSchema = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/receipt-schema', {}, finalizerHeaders), migrationEnv,
);
const receiptSchemaBody = await receiptSchema.json();
check('internal finalization receipt migration: finalizer-only exact additive SQL and closed readback',
  receiptMigrationBuilder.status === 401 &&
  receiptMigrationNonempty.status === 400 &&
  receiptMigrationFinalizer.status === 200 &&
  JSON.stringify(receiptMigrationBody.applied) === JSON.stringify([
    'finalization_modal_receipt', 'finalization_worker_receipt', 'finalization_recovery_receipt',
  ]) &&
  JSON.stringify(receiptMigrationCalls.map((call) => call.text)) === JSON.stringify([
    'BEGIN',
    'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_modal_receipt TEXT',
    'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_worker_receipt TEXT',
    'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_recovery_receipt TEXT',
    'COMMIT', 'RELEASE', 'POOL_END',
  ]) &&
  receiptMigrationCalls.slice(1, 4).every((call) =>
    Array.isArray(call.values) && call.values.length === 0 &&
    /^omo-finalization-receipt-migrate-[a-z_]+-v1$/.test(call.name || '')
  ) &&
  receiptMigrationReplay.status === 200 &&
  JSON.stringify(receiptMigrationReplayBody.applied) === JSON.stringify(receiptMigrationBody.applied) &&
  JSON.stringify(receiptMigrationReplayCalls) === JSON.stringify(receiptMigrationCalls.map((call) => call.text)) &&
  receiptSchema.status === 200 &&
  JSON.stringify(receiptSchemaBody) === JSON.stringify({
    ok: true, table_exists: true,
    present: ['finalization_modal_receipt', 'finalization_worker_receipt', 'finalization_recovery_receipt'], missing: [],
  }) &&
  !JSON.stringify(receiptSchemaBody).includes('attacker_column'));

neonSqlCalls.length = 0;
const finalizationSchemaBuilder = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/schema/migrate', {}, internalHeaders), migrationEnv,
);
const finalizationSchemaMigration = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/schema/migrate', {}, finalizerHeaders), migrationEnv,
);
const finalizationSchemaMigrationBody = await finalizationSchemaMigration.json();
const expectedFinalizationColumns = [
  'promotion_evidence', 'finalization_id', 'finalization_status', 'finalization_target_sha',
  'finalization_source_sha256', 'finalization_head_sha', 'finalization_merge_sha',
  'finalization_artifact_hash', 'finalization_claimed_at', 'finalization_lease_expires_at',
  'finalization_attempts', 'finalization_failure_code', 'finalization_modal_receipt',
  'finalization_worker_receipt', 'finalization_recovery_receipt', 'automation_updated_at',
];
const expectedFinalizationSql = [
  'BEGIN',
  ...workerTest.SUBMISSIONS_SCHEMA_MIGRATIONS
    .filter(([name]) => expectedFinalizationColumns.includes(name))
    .map(([, sql]) => sql),
  'COMMIT', 'RELEASE', 'POOL_END',
];
check('internal finalization schema migration: finalizer-only complete fixed additive columns',
  finalizationSchemaBuilder.status === 401 &&
  finalizationSchemaMigration.status === 200 &&
  JSON.stringify(finalizationSchemaMigrationBody.applied) === JSON.stringify(expectedFinalizationColumns) &&
  JSON.stringify(neonSqlCalls.map((call) => call.text)) === JSON.stringify(expectedFinalizationSql) &&
  neonSqlCalls.slice(1, 1 + expectedFinalizationColumns.length).every((call) =>
    Array.isArray(call.values) && call.values.length === 0 &&
    /^omo-finalization-schema-migrate-[a-z0-9_]+-v1$/.test(call.name || '') &&
    call.text.includes('ADD COLUMN IF NOT EXISTS')
  ));

neonQueryFailureFragment = '';
const resumeProbeBuilder = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/resume-probe', {}, internalHeaders), migrationEnv,
);
const resumeProbePassed = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/resume-probe', {}, finalizerHeaders), migrationEnv,
);
const resumeProbePassedBody = await resumeProbePassed.json();
neonQueryFailureFragment = 'ORDER BY CASE';
const resumeProbeOrdering = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/resume-probe', {}, finalizerHeaders), migrationEnv,
);
const resumeProbeOrderingBody = await resumeProbeOrdering.json();
neonQueryFailureFragment = '';
check('internal finalization resume probe: finalizer-only safe staged readback exposes no DB detail',
  resumeProbeBuilder.status === 401 &&
  resumeProbePassed.status === 200 &&
  JSON.stringify(resumeProbePassedBody) === JSON.stringify({ ok: true, stage: 'passed' }) &&
  resumeProbeOrdering.status === 200 &&
  JSON.stringify(resumeProbeOrderingBody) === JSON.stringify({ ok: true, stage: 'ordering' }) &&
  !JSON.stringify(resumeProbeOrderingBody).includes('SENTINEL'));

for (const record of workerTest.mockSubmissions.values()) {
  if (record.id === submitAuto.id) {
    record.status = 'queued';
    record.failure_code = 'old_failure_must_clear';
    record.build_claimed_at = null;
    record.build_attempts = 2;
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
  internalReplay.status === 204 &&
  Array.from(workerTest.mockSubmissions.values()).some((record) =>
    record.id === submitAuto.id && record.status === 'processing' &&
    record.failure_code === null && record.build_attempts === 3 &&
    !Number.isNaN(Date.parse(record.build_claimed_at))));
const internalBadClaimId = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', { id: 'sub_bad' }, internalHeaders), buildEnv);
check('internal claim: unsafe specific ids are rejected before SQL', internalBadClaimId.status === 400);

const staleMockId = 'sub_staleclaimmock01';
const staleMockLease = new Date(Date.now() - (2 * 60 * 60 + 1) * 1000).toISOString();
workerTest.mockSubmissions.set('stale-mock-claim', {
  id: staleMockId,
  user_id: 'user_private_must_not_leak',
  name: 'Stale Claim Workflow',
  slug: 'stale-claim-workflow',
  content: '---\nname: stale-claim-workflow\ndescription: safe stale claim fixture\n---\n',
  source_sha256: '9'.repeat(64),
  requested_runtime: 'auto',
  status: 'processing',
  failure_code: 'old_failure_must_clear',
  build_claimed_at: staleMockLease,
  build_attempts: 4,
  build_evidence: JSON.stringify({ checks: ['old_check'], source_sha256: '9'.repeat(64), secret: 'must-not-leak' }),
  created_at: '2026-08-01T00:00:00.000Z',
  updated_at: staleMockLease,
});
const staleMockClaim = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', { id: staleMockId }, internalHeaders), buildEnv);
const staleMockClaimBody = staleMockClaim.status === 200 ? await staleMockClaim.json() : {};
const staleMockReplay = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', { id: staleMockId }, internalHeaders), buildEnv);
const staleMockRecord = workerTest.mockSubmissions.get('stale-mock-claim');
check('internal claim lease mock: stale processing is reclaimed once without trusting prior evidence',
  staleMockClaim.status === 200 && staleMockClaimBody.submission.prior_status === 'processing' &&
  !('build_evidence' in staleMockClaimBody.submission) &&
  !JSON.stringify(staleMockClaimBody).includes('must-not-leak') &&
  !('user_id' in staleMockClaimBody.submission) && staleMockReplay.status === 204 &&
  staleMockRecord.status === 'processing' && staleMockRecord.failure_code === null &&
  staleMockRecord.build_attempts === 5 && staleMockRecord.build_evidence === null &&
  Date.parse(staleMockRecord.build_claimed_at) > Date.parse(staleMockLease));

const freshMockId = 'sub_freshclaimmock01';
workerTest.mockSubmissions.set('fresh-mock-claim', {
  ...staleMockRecord,
  id: freshMockId,
  build_claimed_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
});
const freshMockClaim = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', { id: freshMockId }, internalHeaders), buildEnv);
check('internal claim lease mock: a fresh processing row cannot be reclaimed', freshMockClaim.status === 204);

neonSqlCalls.length = 0;
neonInternalClaimRow = {
  id: 'sub_staleclaimneon01',
  name: 'Neon Stale Claim',
  slug: 'neon-stale-claim',
  content: '---\nname: neon-stale-claim\ndescription: safe neon claim fixture\n---\n',
  source_sha256: '8'.repeat(64),
  requested_runtime: 'auto',
  prior_status: 'processing',
  build_evidence: '{"secret":"must-not-leak"}',
};
const staleNeonClaim = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', { id: 'sub_staleclaimneon01' }, internalHeaders), migrationEnv);
const staleNeonClaimBody = await staleNeonClaim.json();
const staleNeonCall = neonSqlCalls.find((call) => call.name && call.name.startsWith('omo-internal-submission-claim-'));
neonInternalClaimRow = null;
check('internal claim lease Neon: one locked guarded update applies the bounded lease and returns only processor fields',
  staleNeonClaim.status === 200 && staleNeonClaimBody.submission.prior_status === 'processing' &&
  !JSON.stringify(staleNeonClaimBody).includes('must-not-leak') && staleNeonCall &&
  staleNeonCall.text.includes('FOR UPDATE SKIP LOCKED') &&
  staleNeonCall.text.includes("status = 'processing'") &&
  staleNeonCall.text.includes('build_claimed_at') &&
  staleNeonCall.text.includes('build_attempts') &&
  staleNeonCall.text.includes('build_evidence') &&
  staleNeonCall.text.includes('source_sha256') &&
  staleNeonCall.values.includes(7200) &&
  !staleNeonCall.text.split('RETURNING', 2).at(-1).includes('user_id'));

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
const internalReadyForDeploy = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/deployment`, {
  status: 'ready_for_deploy',
  published_slug: 'auto-workflow',
  workflow_version: 'auto-workflow@1.0.0',
  build_evidence: {
    checks: ['compile', 'contract'],
    source_sha256: internalClaimBody.submission.source_sha256,
    generated_at: '2026-08-13T00:00:00Z',
  },
}, internalHeaders), buildEnv);
const builderPublishStatus = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/status`, {
  status: 'ready_for_publish',
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
const mergedInternalRelease = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/release`, {
  release_phase: 'merged_verified',
  issue_url: 'https://github.com/omo-space/marketplace/issues/31',
  pr_url: 'https://github.com/omo-space/marketplace/pull/42',
  pr_number: 42,
  branch: 'omo-release/' + internalClaimBody.submission.id + '-auto-workflow',
  head_sha: 'a'.repeat(40),
  merge_sha: 'c'.repeat(40),
  source_sha256: internalClaimBody.submission.source_sha256,
  artifact_hash: 'b'.repeat(64),
}, internalHeaders), buildEnv);
const deployedRecord = Array.from(workerTest.mockSubmissions.values()).find((record) => record.id === internalClaimBody.submission.id);
deployedRecord.finalization_id = 'fin_' + 'f'.repeat(32);
deployedRecord.finalization_status = 'verifying_public';
deployedRecord.finalization_target_sha = '9'.repeat(40);
deployedRecord.finalization_source_sha256 = internalClaimBody.submission.source_sha256;
deployedRecord.finalization_head_sha = 'a'.repeat(40);
deployedRecord.finalization_merge_sha = 'c'.repeat(40);
deployedRecord.finalization_artifact_hash = 'b'.repeat(64);
deployedRecord.finalization_lease_expires_at = '2099-08-20T12:00:00Z';
deployedRecord.finalization_attempts = 1;
const promotedInternalRelease = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/release`, {
  release_phase: 'promoted',
  issue_url: 'https://github.com/omo-space/marketplace/issues/31',
  pr_url: 'https://github.com/omo-space/marketplace/pull/42',
  pr_number: 42,
  branch: 'omo-release/' + internalClaimBody.submission.id + '-auto-workflow',
  head_sha: 'a'.repeat(40),
  merge_sha: 'c'.repeat(40),
  source_sha256: internalClaimBody.submission.source_sha256,
  artifact_hash: 'b'.repeat(64),
  release_gates: {
    status: 'live', checked_at: '2026-08-20T00:00:00Z',
    R1: { status: 'passed' }, R2: { status: 'passed' },
    R3: { status: 'passed' }, R4: { status: 'published' },
  },
}, internalHeaders), buildEnv);
const atomicInternalPromotion = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${deployedRecord.finalization_id}/promote`, {
  target_sha: '9'.repeat(40),
  release_gates: {
    status: 'live',
    checked_at: '2026-08-20T00:00:00Z',
    R1: { status: 'passed' },
    R2: { status: 'passed' },
    R3: { status: 'passed' },
    R4: { status: 'published' },
    secret: 'must-not-store',
  },
}, finalizerHeaders), buildEnv);
const promotedInternalDeployed = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/deployed`, {
  deployed_by: 'trusted_finalizer',
  deployment_url: 'https://omo.space/workflow.html?slug=auto-workflow',
}, finalizerHeaders), buildEnv);
const deployedReleaseDowngrade = await worker.fetch(mkReq('POST', `/api/internal/submissions/${internalClaimBody.submission.id}/release`, {
  release_phase: 'pr_open',
  issue_url: 'https://github.com/omo-space/marketplace/issues/31',
  pr_url: 'https://github.com/omo-space/marketplace/pull/42',
  pr_number: 42,
  branch: 'omo-release/' + internalClaimBody.submission.id + '-auto-workflow',
  head_sha: 'a'.repeat(40),
  source_sha256: internalClaimBody.submission.source_sha256,
  artifact_hash: 'b'.repeat(64),
}, internalHeaders), buildEnv);
check('internal deployment: builder cannot bypass atomic finalization and promoted R1-R4 evidence is required',
  internalDeployment.status === 409 &&
  internalReadyForDeploy.status === 200 &&
  builderPublishStatus.status === 409 &&
  internalRelease.status === 200 &&
  badInternalRelease.status === 400 &&
  internalDeployed.status === 401 &&
  mergedInternalRelease.status === 200 &&
  promotedInternalRelease.status === 409 &&
  atomicInternalPromotion.status === 200 &&
  promotedInternalDeployed.status === 200 &&
  deployedReleaseDowngrade.status === 409 &&
  deployedRecord.status === 'deployed' &&
  deployedRecord.published_slug === 'auto-workflow' &&
  deployedRecord.release_phase === 'promoted' &&
  deployedRecord.release_merge_sha === 'c'.repeat(40) &&
  JSON.parse(deployedRecord.promotion_evidence).status === 'live' &&
  !deployedRecord.promotion_evidence.includes('must-not-store') &&
  deployedRecord.release_branch === 'omo-release/' + internalClaimBody.submission.id + '-auto-workflow' &&
  deployedRecord.release_pr_number === 42 &&
  !String(deployedRecord.build_evidence).includes('must-not-store') &&
  !JSON.stringify(deployedRecord).includes('attacker-branch'));

const finalizationCandidateId = 'sub_finalizationlease0001';
workerTest.mockSubmissions.set(finalizationCandidateId, {
  id: finalizationCandidateId,
  name: 'Lease Workflow',
  slug: 'lease-workflow',
  content: '# Lease Workflow\n',
  source_sha256: 'e'.repeat(64),
  requested_runtime: 'auto',
  created_at: '2026-08-20T00:00:00Z',
  selected_runtime: 'worker-native',
  workflow_version: 'lease-workflow@1.0.0',
  published_slug: 'lease-workflow',
  build_evidence: JSON.stringify({ checks: ['compile'], source_sha256: 'e'.repeat(64) }),
  status: 'ready_for_deploy',
  release_phase: 'merged_verified',
  release_head_sha: 'f'.repeat(40),
  release_merge_sha: '1'.repeat(40),
  release_artifact_hash: '2'.repeat(64),
  release_issue_url: 'https://github.com/omo-space/marketplace/issues/51',
  release_pr_url: 'https://github.com/omo-space/marketplace/pull/52',
  release_pr_number: 52,
  release_branch: 'omo-release/' + finalizationCandidateId + '-lease-workflow',
  finalization_id: null,
  finalization_status: null,
  finalization_lease_expires_at: null,
  finalization_attempts: 0,
});
const completedFinalizationId = 'sub_completedfinalization01';
const completedFinalizationRecord = {
  id: completedFinalizationId,
  slug: 'completed-workflow',
  source_sha256: '6'.repeat(64),
  selected_runtime: 'worker-native',
  status: 'ready_for_publish',
  release_phase: 'promoted',
  release_head_sha: '7'.repeat(40),
  release_merge_sha: '8'.repeat(40),
  release_artifact_hash: '9'.repeat(64),
  promotion_evidence: JSON.stringify({
    status: 'live', checked_at: '2026-08-21T00:00:00Z',
    R1: { status: 'passed' }, R2: { status: 'passed' },
    R3: { status: 'passed' }, R4: { status: 'excluded_premium' },
  }),
  finalization_id: 'fin_' + '6'.repeat(32),
  finalization_status: 'completed',
  finalization_target_sha: '3'.repeat(40),
  finalization_source_sha256: '6'.repeat(64),
  finalization_head_sha: '7'.repeat(40),
  finalization_merge_sha: '8'.repeat(40),
  finalization_artifact_hash: '9'.repeat(64),
  finalization_lease_expires_at: '2099-08-21T00:00:00Z',
  finalization_attempts: 1,
};
workerTest.mockSubmissions.set(completedFinalizationId, completedFinalizationRecord);
const builderResumeCompleted = await worker.fetch(mkReq('POST', '/api/internal/finalizations/resume-completed', {
  target_sha: '3'.repeat(40),
}, internalHeaders), buildEnv);
const resumeCompleted = await worker.fetch(mkReq('POST', '/api/internal/finalizations/resume-completed', {
  target_sha: '3'.repeat(40),
}, finalizerHeaders), buildEnv);
const resumeCompletedBody = await resumeCompleted.json();
completedFinalizationRecord.status = 'deployed';
const deployedResumeCompleted = await worker.fetch(mkReq('POST', '/api/internal/finalizations/resume-completed', {
  target_sha: '3'.repeat(40),
}, finalizerHeaders), buildEnv);
const deployedResumeCompletedBody = await deployedResumeCompleted.json();
completedFinalizationRecord.status = 'ready_for_publish';
check('internal completed finalization resume: finalizer-only receipt prefers publish-ready and confirms exact-target deployed rows',
  builderResumeCompleted.status === 401 &&
  resumeCompleted.status === 200 &&
  resumeCompletedBody.finalization.id === completedFinalizationRecord.finalization_id &&
  resumeCompletedBody.finalization.status === 'completed' &&
  resumeCompletedBody.finalization.target_sha === '3'.repeat(40) &&
  !('content' in resumeCompletedBody.finalization) &&
  deployedResumeCompleted.status === 200 &&
  deployedResumeCompletedBody.finalization.submission_status === 'deployed');
neonSqlCalls.length = 0;
neonCompletedFinalizationRow = { ...completedFinalizationRecord };
const neonCompletedResume = await workerTest.internalResumeCompletedFinalization(
  { NEON_DATABASE_URL: 'postgres://example' }, '3'.repeat(40)
);
const neonCompletedResumeCall = neonSqlCalls.find((call) => call.name === 'omo-internal-finalization-resume-completed-v1');
check('internal completed finalization resume: empty result is idle rather than an exception',
  workerTest.completedFinalizationRow(null) === null);
check('internal completed finalization resume Neon: exact target and immutable completed guards are parameterized',
  workerTest.completedFinalizationRow(neonCompletedResume).status === 'completed' &&
  neonCompletedResumeCall.values.length === 1 &&
  neonCompletedResumeCall.values[0] === '3'.repeat(40) &&
  neonCompletedResumeCall.text.includes("status IN ('ready_for_publish', 'deployed')") &&
  neonCompletedResumeCall.text.includes("release_phase = 'promoted'") &&
  neonCompletedResumeCall.text.includes("finalization_status = 'completed'") &&
  neonCompletedResumeCall.text.includes('source_sha256 = finalization_source_sha256') &&
  neonCompletedResumeCall.text.includes("CASE WHEN status = 'ready_for_publish' THEN 0 ELSE 1 END") &&
  neonSqlCalls.some((call) => call.text === 'RELEASE') &&
  neonSqlCalls.some((call) => call.text === 'POOL_END'));
neonCompletedFinalizationRow = null;
const failedRecoveryTarget = '4'.repeat(40);
const failedRecoveryRecord = {
  id: 'sub_failedfinalization01', slug: 'failed-workflow', source_sha256: 'a'.repeat(64),
  selected_runtime: 'worker-native', status: 'failed', failure_code: 'build_or_deploy_failed',
  release_phase: 'merged_verified', published_slug: 'failed-workflow', workflow_version: 'failed-workflow@1.0.0',
  build_evidence: JSON.stringify({ checks: ['trusted_compile'], source_sha256: 'a'.repeat(64) }),
  release_issue_url: 'https://github.com/omo-space/marketplace/issues/71',
  release_pr_url: 'https://github.com/omo-space/marketplace/pull/72', release_pr_number: 72,
  release_branch: 'omo-release/sub_failedfinalization01-failed-workflow',
  release_head_sha: 'b'.repeat(40), release_merge_sha: 'c'.repeat(40), release_artifact_hash: 'd'.repeat(64),
  finalization_id: 'fin_' + '4'.repeat(32), finalization_status: 'failed',
  finalization_failure_code: 'release_head_not_ancestor', finalization_target_sha: failedRecoveryTarget,
  finalization_source_sha256: 'a'.repeat(64), finalization_head_sha: 'b'.repeat(40),
  finalization_merge_sha: 'c'.repeat(40), finalization_artifact_hash: 'd'.repeat(64),
  finalization_lease_expires_at: '2026-08-21T00:00:00Z', finalization_attempts: 1,
  finalization_modal_receipt: null, finalization_worker_receipt: null,
  updated_at: '2026-08-21T00:00:00Z', automation_updated_at: '2026-08-21T00:00:00Z',
};
workerTest.mockSubmissions.set(failedRecoveryRecord.id, failedRecoveryRecord);
const typedPreflightInspections = [];
for (const failureCode of ['modal_preflight_failed', 'worker_preflight_failed', 'public_preflight_failed']) {
  failedRecoveryRecord.finalization_failure_code = failureCode;
  const response = await worker.fetch(mkReq('POST', '/api/internal/finalizations/failed', {
    target_sha: failedRecoveryTarget,
  }, finalizerHeaders), buildEnv);
  const body = await response.json();
  typedPreflightInspections.push(response.status === 200 && body.finalization.failure_code === failureCode);
}
failedRecoveryRecord.finalization_failure_code = 'release_head_not_ancestor';
const builderFailedInspect = await worker.fetch(mkReq('POST', '/api/internal/finalizations/failed', {
  target_sha: failedRecoveryTarget,
}, internalHeaders), buildEnv);
const failedInspect = await worker.fetch(mkReq('POST', '/api/internal/finalizations/failed', {
  target_sha: failedRecoveryTarget,
}, finalizerHeaders), buildEnv);
const failedInspectBody = await failedInspect.json();
const failedInspectExtra = await worker.fetch(mkReq('POST', '/api/internal/finalizations/failed', {
  target_sha: failedRecoveryTarget, receipts: true,
}, finalizerHeaders), buildEnv);
const failedResume = await worker.fetch(mkReq('POST', '/api/internal/finalizations/resume-failed', {
  target_sha: failedRecoveryTarget,
}, finalizerHeaders), buildEnv);
const failedResumeBody = await failedResume.json();
const failedResumeReplay = await worker.fetch(mkReq('POST', '/api/internal/finalizations/resume-failed', {
  target_sha: failedRecoveryTarget,
}, finalizerHeaders), buildEnv);
check('failed finalization diagnosis/resume mock: finalizer-only exact safe envelope requeues once for a fresh standard claim',
  typedPreflightInspections.every(Boolean) && builderFailedInspect.status === 401 &&
  failedInspect.status === 200 && failedInspectExtra.status === 400 &&
  Object.keys(failedInspectBody.finalization).sort().join(',') === [
    'artifact_hash', 'attempts', 'failure_code', 'head_sha', 'id', 'merge_sha',
    'modal_receipt_present', 'release_phase', 'source_sha256', 'status', 'submission_id',
    'submission_status', 'target_sha', 'worker_receipt_present',
  ].sort().join(',') &&
  failedInspectBody.finalization.failure_code === 'release_head_not_ancestor' &&
  failedInspectBody.finalization.modal_receipt_present === false &&
  failedResume.status === 200 && failedResumeBody.status === 'ready_for_deploy' &&
  failedRecoveryRecord.status === 'ready_for_deploy' && failedRecoveryRecord.finalization_id === null &&
  failedRecoveryRecord.finalization_status === null && failedResumeReplay.status === 409);

const receiptBearingFailed = { ...failedRecoveryRecord,
  id: 'sub_receiptfailedfinal01', finalization_id: 'fin_' + '5'.repeat(32),
  finalization_status: 'failed', finalization_failure_code: 'worker_smoke_failed',
  finalization_target_sha: '5'.repeat(40), finalization_attempts: 3,
  finalization_source_sha256: 'a'.repeat(64), finalization_head_sha: 'b'.repeat(40),
  finalization_merge_sha: 'c'.repeat(40), finalization_artifact_hash: 'd'.repeat(64),
  finalization_lease_expires_at: '2026-08-21T00:00:00Z',
  finalization_worker_receipt: '{"recorded":true}', finalization_modal_receipt: null,
  status: 'ready_for_deploy',
};
workerTest.mockSubmissions.set(receiptBearingFailed.id, receiptBearingFailed);
const receiptFailedInspect = await worker.fetch(mkReq('POST', '/api/internal/finalizations/failed', {
  target_sha: '5'.repeat(40),
}, finalizerHeaders), buildEnv);
const receiptFailedInspectBody = await receiptFailedInspect.json();
const receiptFailedResume = await worker.fetch(mkReq('POST', '/api/internal/finalizations/resume-failed', {
  target_sha: '5'.repeat(40),
}, finalizerHeaders), buildEnv);
receiptBearingFailed.release_merge_sha = 'f'.repeat(40);
const malformedFailedResume = await worker.fetch(mkReq('POST', '/api/internal/finalizations/resume-failed', {
  target_sha: '5'.repeat(40),
}, finalizerHeaders), buildEnv);
check('failed finalization resume mock: receipt-bearing, malformed identity, wrong state, and replay fail closed',
  receiptFailedInspect.status === 200 && receiptFailedInspectBody.finalization.worker_receipt_present === true &&
  !JSON.stringify(receiptFailedInspectBody).includes('recorded') && receiptFailedResume.status === 409 &&
  malformedFailedResume.status === 409);

const rollbackTarget = '8'.repeat(40);
const rollbackArtifact = 'd'.repeat(64);
const rollbackModalReceipt = workerTest.safeDeploymentReceipt({
  provider: 'modal', target: 'cognition-recovery-workflow', environment: 'main',
  target_sha: rollbackTarget, artifact_hash: rollbackArtifact, version_id: 'modal-v7',
  previous_version_id: 'modal-v6', reused: false, rollback_token: 'modal-v6', status: 'passed',
}, 'modal_deploy', rollbackTarget);
const rollbackWorkerReceipt = workerTest.safeDeploymentReceipt({
  provider: 'cloudflare', target: 'cognition-demos', environment: 'production',
  target_sha: rollbackTarget, artifact_hash: rollbackArtifact, version_id: 'cf-v9',
  previous_version_id: 'cf-v8', reused: false, rollback_token: 'cf-v8', status: 'passed',
}, 'worker_deploy', rollbackTarget);
const priorRecoveryEvidence = {
  finalization_id: 'fin_' + '7'.repeat(32), attempt: 4, target_sha: '7'.repeat(40),
  verified_by: 'trusted_production_finalizer', recovered_at: '2026-08-21T00:00:00.000Z',
  modal_receipt: {}, worker_receipt: {}, expected_provider_state: {},
};
const rollbackRecord = {
  ...receiptBearingFailed,
  id: 'sub_rollbackrecover01', slug: 'recovery-workflow', selected_runtime: 'modal-hosted',
  status: 'failed', release_phase: 'merged_verified', finalization_id: 'fin_' + '8'.repeat(32),
  finalization_status: 'failed', finalization_failure_code: 'public_verification_failed',
  finalization_target_sha: rollbackTarget, finalization_attempts: 5,
  release_merge_sha: 'c'.repeat(40),
  release_artifact_hash: rollbackArtifact, finalization_artifact_hash: rollbackArtifact,
  finalization_recovery_receipt: JSON.stringify(priorRecoveryEvidence),
  finalization_modal_receipt: JSON.stringify(rollbackModalReceipt),
  finalization_worker_receipt: JSON.stringify(rollbackWorkerReceipt),
};
const lateWorkerReceipt = workerTest.safeDeploymentReceipt({
  provider: 'cloudflare', target: 'cognition-demos', environment: 'production',
  target_sha: rollbackTarget, artifact_hash: rollbackArtifact, version_id: 'cf-current',
  previous_version_id: null, reused: true, rollback_token: null, status: 'passed',
}, 'worker_deploy', rollbackTarget);
const lateEffectRecord = {
  ...rollbackRecord, id: 'sub_lateeffectreconcile01', finalization_id: 'fin_' + 'e'.repeat(32),
  finalization_failure_code: 'internal_finalizer_failed',
  finalization_modal_receipt: JSON.stringify(rollbackModalReceipt), finalization_worker_receipt: null,
};
workerTest.mockSubmissions.set(lateEffectRecord.id, lateEffectRecord);
check('failed finalization effect reconciliation: exact receipt passes generation guard',
  workerTest.finalizationGenerationAllowsEffect(
    lateEffectRecord, 'worker_deploy', rollbackTarget, lateWorkerReceipt
  ) === true);
const lateEffectRecorded = await workerTest.internalRecordFinalizationEffect(
  buildEnv, lateEffectRecord.finalization_id, 'worker_deploy', rollbackTarget, lateWorkerReceipt
);
const lateEffectReplay = await workerTest.internalRecordFinalizationEffect(
  buildEnv, lateEffectRecord.finalization_id, 'worker_deploy', rollbackTarget, lateWorkerReceipt
);
check('failed finalization effect reconciliation: exact reused Worker receipt records once',
  lateEffectRecorded === 'recorded');
check('failed finalization effect reconciliation: identical receipt replays',
  lateEffectReplay === 'replayed');
check('failed finalization effect reconciliation: canonical receipt persists',
  lateEffectRecord.finalization_worker_receipt != null &&
  JSON.parse(lateEffectRecord.finalization_worker_receipt).version_id === 'cf-current');
workerTest.mockSubmissions.delete(lateEffectRecord.id);
workerTest.mockSubmissions.set(rollbackRecord.id, rollbackRecord);
const recoveryPlanResponse = await worker.fetch(mkReq('POST', '/api/internal/finalizations/recovery-plan', {
  target_sha: rollbackTarget,
}, finalizerHeaders), buildEnv);
const recoveryPlanBody = await recoveryPlanResponse.json();
const recoveryExtra = await worker.fetch(mkReq('POST', '/api/internal/finalizations/recover-rolled-back', {
  target_sha: rollbackTarget, modal_version: 'attacker-controlled',
}, finalizerHeaders), buildEnv);
const recoveryResponse = await worker.fetch(mkReq('POST', '/api/internal/finalizations/recover-rolled-back', {
  target_sha: rollbackTarget,
}, finalizerHeaders), buildEnv);
const recoveryBody = await recoveryResponse.json();
const recoveryHistory = JSON.parse(rollbackRecord.finalization_recovery_receipt || 'null');
const recoverySnapshot = recoveryHistory[1];
const recoveryReplay = await worker.fetch(mkReq('POST', '/api/internal/finalizations/recover-rolled-back', {
  target_sha: rollbackTarget,
}, finalizerHeaders), buildEnv);
check('receipt-aware rollback recovery mock: exact target-only boundary preserves immutable evidence and rearms once',
  recoveryPlanResponse.status === 200 && recoveryPlanBody.recovery.target_sha === rollbackTarget &&
  recoveryPlanBody.recovery.modal.expected_active_version_id === 'modal-v7' &&
  recoveryPlanBody.recovery.cloudflare.expected_active_version_id === 'cf-v8' &&
  recoveryExtra.status === 400 && recoveryResponse.status === 200 &&
  recoveryBody.status === 'ready_for_deploy' && recoveryReplay.status === 409 &&
  rollbackRecord.status === 'ready_for_deploy' && rollbackRecord.finalization_id === null &&
  rollbackRecord.finalization_attempts === 5 && rollbackRecord.finalization_modal_receipt === null &&
  rollbackRecord.finalization_worker_receipt === null && Array.isArray(recoveryHistory) && recoveryHistory.length === 2 &&
  JSON.stringify(recoveryHistory[0]) === JSON.stringify(priorRecoveryEvidence) &&
  recoverySnapshot.finalization_id === 'fin_' + '8'.repeat(32) &&
  recoverySnapshot.attempt === 5 && recoverySnapshot.target_sha === rollbackTarget &&
  recoverySnapshot.failure_code === 'public_verification_failed' &&
  recoverySnapshot.modal_receipt.version_id === 'modal-v7' &&
  recoverySnapshot.worker_receipt.previous_version_id === 'cf-v8' &&
  recoverySnapshot.expected_provider_state.modal.version_id === 'modal-v7' &&
  recoverySnapshot.expected_provider_state.cloudflare.version_id === 'cf-v8' &&
  recoverySnapshot.verified_by === 'trusted_production_finalizer');
workerTest.mockSubmissions.delete(rollbackRecord.id);

neonSqlCalls.length = 0;
neonFailedFinalizationRow = { ...receiptBearingFailed, release_merge_sha: 'c'.repeat(40),
  modal_receipt_present: false, worker_receipt_present: true };
const neonFailedInspect = await workerTest.internalInspectFailedFinalization(
  { NEON_DATABASE_URL: 'postgres://example' }, '5'.repeat(40)
);
const neonFailedInspectCall = neonSqlCalls.find((call) => call.name === 'omo-internal-finalization-failed-v1');
neonFailedResumeRow = { ...failedRecoveryRecord, finalization_id: 'fin_' + '7'.repeat(32),
  finalization_failure_code: 'unknown_preflight_failure', finalization_target_sha: '7'.repeat(40),
  finalization_attempts: 4, finalization_lease_expires_at: '2099-08-21T00:00:00Z' };
const neonUnknownFailedResumed = await workerTest.internalResumeFailedFinalization(
  { NEON_DATABASE_URL: 'postgres://example' }, '7'.repeat(40)
);
neonFailedResumeRow = { ...failedRecoveryRecord, finalization_id: 'fin_' + '6'.repeat(32),
  finalization_failure_code: 'modal_preflight_failed',
  finalization_target_sha: '6'.repeat(40), finalization_attempts: 4,
  finalization_lease_expires_at: '2099-08-21T00:00:00Z' };
const neonFailedResumed = await workerTest.internalResumeFailedFinalization(
  { NEON_DATABASE_URL: 'postgres://example' }, '6'.repeat(40)
);
const neonFailedResumeCall = neonSqlCalls.find((call) =>
  call.name === 'omo-internal-finalization-resume-failed-v1' && call.values[0] === '6'.repeat(40)
);
check('failed finalization Neon SQL: exact target, allowlisted failure, complete immutable equality, and no-receipt requeue CAS',
  neonUnknownFailedResumed === false &&
  workerTest.failedFinalizationRow(neonFailedInspect).worker_receipt_present === true &&
  neonFailedInspectCall.values[0] === '5'.repeat(40) &&
  neonFailedInspectCall.text.includes('source_sha256 = finalization_source_sha256') &&
  neonFailedInspectCall.text.includes('release_artifact_hash = finalization_artifact_hash') &&
  neonFailedResumeCall.values.includes('6'.repeat(40)) &&
  Array.isArray(neonFailedResumeCall.values[1]) &&
  neonFailedResumeCall.values[1].includes('modal_preflight_failed') &&
  neonFailedResumeCall.values[1].includes('worker_preflight_failed') &&
  neonFailedResumeCall.values[1].includes('public_preflight_failed') &&
  !neonFailedResumeCall.values[1].includes('unknown_preflight_failure') &&
  neonFailedResumeCall.text.includes("finalization_failure_code = ANY($2::text[])") &&
  neonFailedResumeCall.text.includes("status IN ('ready_for_deploy', 'failed')") &&
  neonFailedResumeCall.text.includes('FOR UPDATE SKIP LOCKED') &&
  neonFailedResumeCall.text.includes('submission.id = candidate.id') &&
  neonFailedResumeCall.text.includes('submission.finalization_id = candidate.finalization_id') &&
  neonFailedResumeCall.text.includes('finalization_modal_receipt IS NULL') &&
  neonFailedResumeCall.text.includes('release_merge_sha = finalization_merge_sha') &&
  neonFailedResumed === true);
neonSqlCalls.length = 0;
neonFailedFinalizationRow = {
  ...rollbackRecord, status: 'failed', finalization_id: 'fin_' + '8'.repeat(32),
  finalization_status: 'failed', finalization_failure_code: 'worker_smoke_failed',
  finalization_target_sha: rollbackTarget, finalization_source_sha256: 'a'.repeat(64),
  finalization_head_sha: 'b'.repeat(40), finalization_merge_sha: 'c'.repeat(40),
  finalization_artifact_hash: rollbackArtifact, finalization_attempts: 5,
  finalization_modal_receipt: JSON.stringify(rollbackModalReceipt),
  finalization_worker_receipt: JSON.stringify(rollbackWorkerReceipt),
  finalization_recovery_receipt: JSON.stringify(priorRecoveryEvidence),
};
neonRecoveryRow = { id: rollbackRecord.id };
const neonRecovered = await workerTest.internalRecoverRolledBackFinalization(
  { NEON_DATABASE_URL: 'postgres://example' }, rollbackTarget
);
const neonRecoveryCall = neonSqlCalls.find((call) => call.name === 'omo-internal-finalization-recover-rolled-back-v1');
check('receipt-aware rollback recovery Neon: exact immutable CAS stores evidence once and clears active generation',
  neonRecovered === true && neonRecoveryCall.values.length === 11 &&
  neonRecoveryCall.values[3] === rollbackTarget &&
  JSON.parse(neonRecoveryCall.values[0])[1].verified_by === 'trusted_production_finalizer' &&
  neonRecoveryCall.values[8] === JSON.stringify(rollbackModalReceipt) &&
  neonRecoveryCall.values[9] === JSON.stringify(rollbackWorkerReceipt) &&
  neonRecoveryCall.values[10] === JSON.stringify(priorRecoveryEvidence) &&
  neonRecoveryCall.text.includes("finalization_failure_code IN ('worker_smoke_failed', 'internal_finalizer_failed', 'public_verification_failed')") &&
  neonRecoveryCall.text.includes("selected_runtime = 'modal-hosted'") &&
  neonRecoveryCall.text.includes('finalization_recovery_receipt IS NOT DISTINCT FROM $11') &&
  neonRecoveryCall.text.includes('finalization_modal_receipt = $9') &&
  neonRecoveryCall.text.includes('finalization_worker_receipt = $10'));
neonFailedFinalizationRow = null;
neonFailedResumeRow = null;
neonRecoveryRow = null;
workerTest.mockSubmissions.delete(failedRecoveryRecord.id);
const builderFinalizationClaim = await worker.fetch(mkReq('POST', '/api/internal/finalizations/claim', {
  target_sha: '3'.repeat(40),
}, internalHeaders), buildEnv);
const noConfigFinalizationClaim = await worker.fetch(mkReq('POST', '/api/internal/finalizations/claim', {
  target_sha: '3'.repeat(40),
}, finalizerHeaders), { ...realEnv, BUILD_WORKER_TOKEN: 'bridge-token-for-tests' });
const equalTokenFinalizationClaim = await worker.fetch(mkReq('POST', '/api/internal/finalizations/claim', {
  target_sha: '3'.repeat(40),
}, internalHeaders), {
  ...realEnv,
  BUILD_WORKER_TOKEN: 'bridge-token-for-tests',
  RELEASE_FINALIZER_TOKEN: 'bridge-token-for-tests',
});
const finalizationClaim = await worker.fetch(mkReq('POST', '/api/internal/finalizations/claim', {
  target_sha: '3'.repeat(40),
}, finalizerHeaders), buildEnv);
const finalizationClaimBody = await finalizationClaim.json();
const finalizationRecord = workerTest.mockSubmissions.get(finalizationCandidateId);
const builderReclaimAfterFinalization = await worker.fetch(mkReq('POST', '/api/internal/submissions/claim', {
  id: finalizationCandidateId,
  include_ready: true,
}, internalHeaders), buildEnv);
const builderFailureAfterFinalization = await worker.fetch(mkReq('POST', `/api/internal/submissions/${finalizationCandidateId}/status`, {
  status: 'failed',
  failure_code: 'build_or_deploy_failed',
}, internalHeaders), buildEnv);
const builderReleaseMutationAfterClaim = await worker.fetch(mkReq('POST', `/api/internal/submissions/${finalizationCandidateId}/release`, {
  release_phase: 'failed',
  issue_url: finalizationRecord.release_issue_url,
  pr_url: finalizationRecord.release_pr_url,
  pr_number: finalizationRecord.release_pr_number,
  branch: finalizationRecord.release_branch,
  head_sha: finalizationRecord.release_head_sha,
  merge_sha: finalizationRecord.release_merge_sha,
  source_sha256: finalizationRecord.source_sha256,
  artifact_hash: finalizationRecord.release_artifact_hash,
}, internalHeaders), buildEnv);
const duplicateFinalizationClaim = await worker.fetch(mkReq('POST', '/api/internal/finalizations/claim', {
  target_sha: '3'.repeat(40),
}, finalizerHeaders), buildEnv);
const wrongTargetFinalizationAdvance = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/status`, {
  target_sha: '4'.repeat(40),
  status: 'deploying_worker',
}, finalizerHeaders), buildEnv);
const driftedMergeSha = finalizationRecord.release_merge_sha;
finalizationRecord.release_merge_sha = 'd'.repeat(40);
const driftedFinalizationAdvance = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/status`, {
  target_sha: '3'.repeat(40),
  status: 'deploying_worker',
}, finalizerHeaders), buildEnv);
finalizationRecord.release_merge_sha = driftedMergeSha;
const finalizationAdvance = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/status`, {
  target_sha: '3'.repeat(40),
  status: 'deploying_worker',
}, finalizerHeaders), buildEnv);
const duplicateFinalizationAdvance = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/status`, {
  target_sha: '3'.repeat(40),
  status: 'deploying_worker',
}, finalizerHeaders), buildEnv);
const skippedFinalizationAdvance = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/status`, {
  target_sha: '3'.repeat(40),
  status: 'completed',
}, finalizerHeaders), buildEnv);
const builderRegistrySlugs = await worker.fetch(mkReq('POST', '/api/internal/finalizations/registry-slugs', {}, internalHeaders), buildEnv);
const registrySlugs = await worker.fetch(mkReq('POST', '/api/internal/finalizations/registry-slugs', {}, finalizerHeaders), buildEnv);
const registrySlugsBody = await registrySlugs.json();
const workerReceiptPayload = {
  provider: 'cloudflare', target: 'cognition-demos', environment: 'production',
  target_sha: '3'.repeat(40), artifact_hash: '2'.repeat(64),
  version_id: 'worker-version-1', previous_version_id: 'worker-version-0',
  reused: false, rollback_token: 'worker-version-0', status: 'passed',
};
const invalidReceiptContracts = [
  { ...workerReceiptPayload, previous_version_id: null, rollback_token: null, reused: false },
  { ...workerReceiptPayload, reused: true },
  { ...workerReceiptPayload, rollback_token: 'unrelated-token' },
].map((receipt) => workerTest.safeDeploymentReceipt(receipt, 'worker_deploy', '3'.repeat(40)));
const builderEffect = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/effects`, {
  operation: 'worker_deploy', target_sha: '3'.repeat(40), receipt: workerReceiptPayload,
}, internalHeaders), buildEnv);
const recordedEffect = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/effects`, {
  operation: 'worker_deploy', target_sha: '3'.repeat(40), receipt: workerReceiptPayload,
}, finalizerHeaders), buildEnv);
const recordedEffectBody = await recordedEffect.json();
const replayedEffect = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/effects`, {
  operation: 'worker_deploy', target_sha: '3'.repeat(40), receipt: workerReceiptPayload,
}, finalizerHeaders), buildEnv);
const replayedEffectBody = await replayedEffect.json();
const conflictingEffect = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/effects`, {
  operation: 'worker_deploy', target_sha: '3'.repeat(40), receipt: { ...workerReceiptPayload, version_id: 'worker-version-2' },
}, finalizerHeaders), buildEnv);
const unsafeEffect = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/effects`, {
  operation: 'worker_deploy', target_sha: '3'.repeat(40), receipt: { ...workerReceiptPayload, command: 'must-not-store' },
}, finalizerHeaders), buildEnv);
const wrongIdentityEffect = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${finalizationClaimBody.finalization.id}/effects`, {
  operation: 'worker_deploy', target_sha: '3'.repeat(40), receipt: { ...workerReceiptPayload, target: 'another-worker' },
}, finalizerHeaders), buildEnv);
check('internal finalization claim: separate finalizer authority gets one target-SHA-bound lease',
  builderFinalizationClaim.status === 401 &&
  noConfigFinalizationClaim.status === 503 &&
  equalTokenFinalizationClaim.status === 503 &&
  finalizationClaim.status === 200 &&
  finalizationClaimBody.finalization.submission_id === finalizationCandidateId &&
  finalizationClaimBody.finalization.target_sha === '3'.repeat(40) &&
  finalizationClaimBody.finalization.status === 'claimed' &&
  builderReclaimAfterFinalization.status === 204 &&
  builderFailureAfterFinalization.status === 409 &&
  finalizationRecord.status === 'ready_for_deploy' &&
  builderReleaseMutationAfterClaim.status === 409 &&
  finalizationRecord.release_phase === 'merged_verified' &&
  /^fin_[a-f0-9]{32}$/.test(finalizationClaimBody.finalization.id) &&
  duplicateFinalizationClaim.status === 204 &&
  finalizationRecord.finalization_attempts === 1 &&
  finalizationRecord.finalization_id === finalizationClaimBody.finalization.id);
check('internal finalization status: exact generation advances idempotently and skipped/wrong-target transitions fail',
  wrongTargetFinalizationAdvance.status === 409 &&
  driftedFinalizationAdvance.status === 409 &&
  finalizationAdvance.status === 200 &&
  duplicateFinalizationAdvance.status === 200 &&
  skippedFinalizationAdvance.status === 400 &&
  finalizationRecord.finalization_status === 'deploying_worker');
check('internal finalization effects: finalizer-only closed receipts persist once and conflicting replay fails closed',
  builderRegistrySlugs.status === 401 && registrySlugs.status === 200 &&
  registrySlugsBody.slugs.includes('lease-workflow') &&
  builderEffect.status === 401 && recordedEffect.status === 200 && recordedEffectBody.replayed === false &&
  replayedEffect.status === 200 && replayedEffectBody.replayed === true &&
  conflictingEffect.status === 409 && unsafeEffect.status === 400 && wrongIdentityEffect.status === 409 &&
  invalidReceiptContracts.every((receipt) => receipt === null) &&
  JSON.parse(finalizationRecord.finalization_worker_receipt).version_id === 'worker-version-1' &&
  !finalizationRecord.finalization_worker_receipt.includes('must-not-store'));

const modalEffectRecord = {
  id: 'sub_modaleffect0001', slug: 'label-normalizer-canary', source_sha256: 'a'.repeat(64),
  selected_runtime: 'modal-hosted', status: 'ready_for_deploy', release_phase: 'merged_verified',
  release_head_sha: 'b'.repeat(40), release_merge_sha: 'c'.repeat(40), release_artifact_hash: 'd'.repeat(64),
  finalization_id: 'fin_' + 'e'.repeat(32), finalization_status: 'deploying_modal',
  finalization_target_sha: 'f'.repeat(40), finalization_source_sha256: 'a'.repeat(64),
  finalization_head_sha: 'b'.repeat(40), finalization_merge_sha: 'c'.repeat(40),
  finalization_artifact_hash: 'd'.repeat(64), finalization_lease_expires_at: '2099-08-20T12:00:00Z',
  finalization_attempts: 1, finalization_modal_receipt: null,
};
workerTest.mockSubmissions.set(modalEffectRecord.id, modalEffectRecord);
const modalReceipt = workerTest.safeDeploymentReceipt({
  provider: 'modal', target: 'cognition-label-normalizer-canary', environment: 'main',
  target_sha: 'f'.repeat(40), artifact_hash: 'd'.repeat(64), version_id: 'modal-v2',
  previous_version_id: 'modal-v1', reused: false, rollback_token: 'modal-v1', status: 'passed',
}, 'modal_deploy', 'f'.repeat(40));
const modalEffectRecorded = await workerTest.internalRecordFinalizationEffect(
  buildEnv, modalEffectRecord.finalization_id, 'modal_deploy', modalEffectRecord.finalization_target_sha, modalReceipt
);
modalEffectRecord.finalization_status = 'completed';
const modalEffectAfterCompletion = await workerTest.internalRecordFinalizationEffect(
  buildEnv, modalEffectRecord.finalization_id, 'modal_deploy', modalEffectRecord.finalization_target_sha, modalReceipt
);
check('internal finalization Modal effect: exact main identity persists and completed generation is immutable',
  modalEffectRecorded === 'recorded' && modalEffectAfterCompletion === 'invalid' &&
  JSON.parse(modalEffectRecord.finalization_modal_receipt).target === 'cognition-label-normalizer-canary');

const productionCanaryKey = 'omo_' + '1'.repeat(32);
const productionCanaryEnv = {
  ...buildEnv,
  ENVIRONMENT: 'production',
  PRODUCTION_CANARY_API_KEY: productionCanaryKey,
  LABEL_NORMALIZER_CANARY_MODAL_URL: 'https://issue141-canary.modal.invalid',
  HOSTED_MODAL_PROXY_TOKEN_ID: 'production-modal-id',
  HOSTED_MODAL_PROXY_TOKEN_SECRET: 'production-modal-secret',
};
const builderCanaryProvision = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/canary-identity', {}, internalHeaders), productionCanaryEnv
);
const wrongEnvironmentCanaryProvision = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/canary-identity', {}, finalizerHeaders),
  { ...productionCanaryEnv, ENVIRONMENT: 'staging' }
);
const canaryProvision = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/canary-identity', {}, finalizerHeaders), productionCanaryEnv
);
const canaryProvisionBody = await canaryProvision.json();
const canaryProvisionReplay = await worker.fetch(
  mkReq('POST', '/api/internal/finalizations/canary-identity', {}, finalizerHeaders), productionCanaryEnv
);
const canaryProvisionReplayBody = await canaryProvisionReplay.json();
const savedApiKeys = new Map(workerTest.mockApiKeys);
workerTest.mockApiKeys.clear();
const directProductionCanaryAuth = await workerTest.authenticateAccount(
  mkReq('GET', '/api/run/run_scopecheck', null, { 'X-API-Key': productionCanaryKey }),
  productionCanaryEnv, true, true,
);
const unscopedProductionCanaryAuth = await workerTest.authenticateAccount(
  mkReq('GET', '/api/me', null, { 'X-API-Key': productionCanaryKey }),
  productionCanaryEnv, true, false,
);
workerTest.mockApiKeys.clear();
for (const [key, value] of savedApiKeys) workerTest.mockApiKeys.set(key, value);
const productionCanaryScopedReject = await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'facebook-ads-copywriter', fields: { product_name: 'Nope' },
}, { 'X-API-Key': productionCanaryKey, 'Idempotency-Key': 'production-canary-scope-reject' }), productionCanaryEnv);
const productionCanarySubmissionReject = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Sample workflow', content: submissionContent, visibility: 'public', runtime_preference: 'worker-native',
}, { 'X-API-Key': productionCanaryKey }), productionCanaryEnv);
const productionCanaryContent = '---\nname: label-normalizer-canary\ndescription: Deterministic production release canary.\n---\n\n## Workflow\n\n1. Normalize bounded labels.\n';
const productionCanarySubmissionAccept = await worker.fetch(mkReq('POST', '/api/submit', {
  name: 'Label normalizer canary', content: productionCanaryContent,
  visibility: 'public', runtime_preference: 'modal-hosted',
}, { 'X-API-Key': productionCanaryKey }), productionCanaryEnv);
const productionCanarySubmissionAcceptBody = await productionCanarySubmissionAccept.json();
for (const record of workerTest.mockSubmissions.values()) {
  if (record.id === productionCanarySubmissionAcceptBody.id) {
    record.status = 'failed';
    record.failure_code = 'build_or_deploy_failed';
    record.selected_runtime = null;
    record.runtime_policy = null;
  }
}
const productionCanaryRetry = await worker.fetch(mkReq(
  'POST', `/api/submissions/${productionCanarySubmissionAcceptBody.id}/retry`, {},
  { 'X-API-Key': productionCanaryKey },
), productionCanaryEnv);
const productionCanaryRetryBody = await productionCanaryRetry.json();
const productionCanaryForeignRetry = await worker.fetch(mkReq(
  'POST', `/api/submissions/${submitAdded.id}/retry`, {},
  { 'X-API-Key': productionCanaryKey },
), productionCanaryEnv);
const productionCanaryOwner = await workerTest.userIdForApiKey(productionCanaryEnv, productionCanaryKey);
const hashOnlyCanaryResolver = /async function userIdForHashedApiKey[\s\S]*?(?=async function ensureProductionCanaryIdentity)/.exec(workerSrc)?.[0] || '';
check('production canary auth: hashed submission fallback stays narrow and fixed secret is scope-gated',
  hashOnlyCanaryResolver.includes('omo-api-key-owner-v1') &&
  !hashOnlyCanaryResolver.includes('legacy') && !hashOnlyCanaryResolver.includes('users WHERE api_key') &&
  (workerSrc.match(/apiKeyOwner = .*userIdForHashedApiKey/g) || []).length === 2 &&
  directProductionCanaryAuth.ok === true &&
  directProductionCanaryAuth.userId === 'user_prod_label_normalizer_canary_v1' &&
  directProductionCanaryAuth.method === 'production_canary' &&
  unscopedProductionCanaryAuth.ok === false);
check('production canary identity: finalizer-only one-time finite principal uses normal API-key auth and exact slug scope',
  builderCanaryProvision.status === 401 && wrongEnvironmentCanaryProvision.status === 503 &&
  canaryProvision.status === 200 && canaryProvisionBody.created === true &&
  canaryProvisionBody.user_id === 'user_prod_label_normalizer_canary_v1' &&
  canaryProvisionReplay.status === 200 && canaryProvisionReplayBody.created === false &&
  productionCanaryScopedReject.status === 403 &&
  productionCanarySubmissionReject.status === 403 &&
  productionCanarySubmissionAccept.status === 202 &&
  productionCanarySubmissionAcceptBody.slug === 'label-normalizer-canary' &&
  productionCanaryRetry.status === 200 && productionCanaryRetryBody.retried === true &&
  productionCanaryRetryBody.submission.id === productionCanarySubmissionAcceptBody.id &&
  productionCanaryRetryBody.submission.status === 'queued' && productionCanaryForeignRetry.status === 404 &&
  productionCanaryOwner === 'user_prod_label_normalizer_canary_v1');

const firstFinalizationId = finalizationRecord.finalization_id;
const reclaimedGenerationIds = [];
const reclaimedReceiptsCleared = [];
let reclaimedFinalization;
let reclaimedFinalizationBody;
for (const expiredStatus of ['claimed', 'deploying_modal', 'deploying_worker', 'verifying_public']) {
  finalizationRecord.finalization_status = expiredStatus;
  finalizationRecord.finalization_modal_receipt = '{"stale":"modal"}';
  finalizationRecord.finalization_worker_receipt = '{"stale":"worker"}';
  finalizationRecord.finalization_lease_expires_at = '2020-01-01T00:00:00.000Z';
  reclaimedFinalization = await worker.fetch(mkReq('POST', '/api/internal/finalizations/claim', {
    target_sha: '5'.repeat(40),
  }, finalizerHeaders), buildEnv);
  reclaimedFinalizationBody = await reclaimedFinalization.json();
  reclaimedGenerationIds.push(reclaimedFinalizationBody.finalization.id);
  reclaimedReceiptsCleared.push(
    finalizationRecord.finalization_modal_receipt === null &&
    finalizationRecord.finalization_worker_receipt === null
  );
}
const finalizationDetail = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${reclaimedFinalizationBody.finalization.id}/detail`, {}, finalizerHeaders), buildEnv);
const finalizationDetailBody = await finalizationDetail.json();
const failedFinalization = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${reclaimedFinalizationBody.finalization.id}/status`, {
  target_sha: '5'.repeat(40),
  status: 'failed',
  failure_code: 'worker_deploy_failed',
}, finalizerHeaders), buildEnv);
const unsafeFailedFinalization = await worker.fetch(mkReq('POST', `/api/internal/finalizations/${reclaimedFinalizationBody.finalization.id}/status`, {
  target_sha: '5'.repeat(40),
  status: 'failed',
  failure_code: 'secret',
}, finalizerHeaders), buildEnv);
check('internal finalization claim: every expired active infrastructure phase is reclaimed as a new generation',
  reclaimedFinalization.status === 200 &&
  reclaimedGenerationIds.length === 4 &&
  new Set([firstFinalizationId, ...reclaimedGenerationIds]).size === 5 &&
  reclaimedReceiptsCleared.every(Boolean) &&
  reclaimedFinalizationBody.finalization.target_sha === '5'.repeat(40) &&
  reclaimedFinalizationBody.finalization.attempts === 5 &&
  finalizationRecord.finalization_attempts === 5);
check('internal finalization detail: safe generation state is readable without owner/source payloads',
  finalizationDetail.status === 200 &&
  finalizationDetailBody.finalization.id === reclaimedFinalizationBody.finalization.id &&
  finalizationDetailBody.finalization.submission_id === finalizationCandidateId &&
  finalizationDetailBody.finalization.status === 'claimed' &&
  !('user_id' in finalizationDetailBody.finalization) &&
  !('content' in finalizationDetailBody.finalization));
check('internal finalization failure: exact generation records one typed safe terminal code',
  failedFinalization.status === 200 &&
  unsafeFailedFinalization.status === 400 &&
  finalizationRecord.finalization_status === 'failed' &&
  finalizationRecord.finalization_failure_code === 'worker_deploy_failed');

neonSqlCalls.length = 0;
neonFinalizationClaimRow = {
  id: 'sub_neonfinalizer01',
  slug: 'neon-finalizer',
  selected_runtime: 'modal-hosted',
  source_sha256: '6'.repeat(64),
  release_head_sha: '7'.repeat(40),
  release_merge_sha: '8'.repeat(40),
  release_artifact_hash: '9'.repeat(64),
  finalization_id: 'fin_' + 'a'.repeat(32),
  finalization_target_sha: 'b'.repeat(40),
  finalization_source_sha256: '6'.repeat(64),
  finalization_head_sha: '7'.repeat(40),
  finalization_merge_sha: '8'.repeat(40),
  finalization_artifact_hash: '9'.repeat(64),
  finalization_lease_expires_at: '2099-08-20T12:00:00Z',
  finalization_attempts: 1,
};
const neonFinalization = await workerTest.internalClaimFinalization({ NEON_DATABASE_URL: 'postgres://example' }, 'b'.repeat(40));
const neonFinalizationCall = neonSqlCalls.find((call) => call.name === 'omo-internal-finalization-claim-v1');
check('internal finalization claim Neon: one locked atomic update returns only finalizer fields',
  neonFinalization.id === 'fin_' + 'a'.repeat(32) &&
  neonFinalizationCall.text.includes('FOR UPDATE SKIP LOCKED') &&
  neonFinalizationCall.text.includes("release_phase = 'merged_verified'") &&
  neonFinalizationCall.text.includes('release_pr_url IS NOT NULL') &&
  neonFinalizationCall.text.includes('build_evidence IS NOT NULL') &&
  neonFinalizationCall.text.includes('finalization_lease_expires_at::timestamptz < CURRENT_TIMESTAMP') &&
  !neonFinalizationCall.text.split('RETURNING', 2).at(-1).includes('user_id') &&
  !neonFinalizationCall.text.split('RETURNING', 2).at(-1).includes('content'));
neonFinalizationClaimRow = null;

neonSqlCalls.length = 0;
neonFinalizationRegistryRows = [
  { published_slug: 'zeta-workflow' }, { published_slug: 'alpha-workflow' },
  { published_slug: 'alpha-workflow' }, { published_slug: '../unsafe' },
];
const neonRegistrySlugs = await workerTest.internalRequiredRegistrySlugs({ NEON_DATABASE_URL: 'postgres://example' });
const neonRegistryCall = neonSqlCalls.find((call) => call.name === 'omo-internal-finalization-registry-slugs-v1');
neonFinalizationDetailRow = {
  id: 'sub_neonfinalizer01', slug: 'neon-finalizer', source_sha256: '6'.repeat(64),
  selected_runtime: 'worker-native', status: 'ready_for_deploy', release_phase: 'merged_verified',
  release_head_sha: '7'.repeat(40), release_merge_sha: '8'.repeat(40), release_artifact_hash: '9'.repeat(64),
  finalization_id: 'fin_' + 'a'.repeat(32), finalization_status: 'deploying_worker',
  finalization_target_sha: 'b'.repeat(40), finalization_source_sha256: '6'.repeat(64),
  finalization_head_sha: '7'.repeat(40), finalization_merge_sha: '8'.repeat(40),
  finalization_artifact_hash: '9'.repeat(64), finalization_lease_expires_at: '2099-08-20T12:00:00Z',
  finalization_attempts: 1, finalization_worker_receipt: null,
};
neonFinalizationEffectRow = { id: 'sub_neonfinalizer01' };
const neonWorkerReceipt = workerTest.safeDeploymentReceipt({
  provider: 'cloudflare', target: 'cognition-demos', environment: 'production',
  target_sha: 'b'.repeat(40), artifact_hash: '9'.repeat(64), version_id: 'worker-v1',
  previous_version_id: 'worker-v0', reused: false, rollback_token: 'worker-v0', status: 'passed',
}, 'worker_deploy', 'b'.repeat(40));
const neonEffectRecorded = await workerTest.internalRecordFinalizationEffect(
  { NEON_DATABASE_URL: 'postgres://example' }, 'fin_' + 'a'.repeat(32), 'worker_deploy', 'b'.repeat(40), neonWorkerReceipt
);
const neonEffectCall = neonSqlCalls.find((call) => call.name === 'omo-internal-finalization-effect-worker_deploy-v1');
check('internal finalization registry/effect Neon: queries are parameterized, bounded, and generation-guarded',
  JSON.stringify(neonRegistrySlugs) === JSON.stringify(['alpha-workflow', 'zeta-workflow']) &&
  neonRegistryCall.values.length === 1 && neonRegistryCall.text.includes('SELECT DISTINCT published_slug') &&
  neonEffectRecorded === 'recorded' && neonEffectCall.values.length === 4 &&
  neonEffectCall.values[3] === 'deploying_worker' &&
  neonEffectCall.text.includes('finalization_worker_receipt IS NULL') &&
  neonEffectCall.text.includes('finalization_status = $4') &&
  neonEffectCall.text.includes('finalization_lease_expires_at::timestamptz > CURRENT_TIMESTAMP') &&
  neonEffectCall.text.includes('release_artifact_hash = finalization_artifact_hash') &&
  !neonEffectCall.text.includes('command') && !neonEffectCall.text.includes('url'));
neonFinalizationRegistryRows = [];
neonFinalizationEffectRow = null;
neonFinalizationDetailRow = null;

neonSqlCalls.length = 0;
neonFinalizationDetailRow = {
  id: 'sub_neonfinalizer01',
  slug: 'neon-finalizer',
  source_sha256: '6'.repeat(64),
  selected_runtime: 'modal-hosted',
  status: 'ready_for_deploy',
  release_phase: 'merged_verified',
  release_head_sha: '7'.repeat(40),
  release_merge_sha: '8'.repeat(40),
  release_artifact_hash: '9'.repeat(64),
  promotion_evidence: JSON.stringify({
    status: 'live', checked_at: '2026-08-20T00:00:00Z',
    R1: { status: 'passed' }, R2: { status: 'passed' },
    R3: { status: 'passed' }, R4: { status: 'published' },
  }),
  finalization_id: 'fin_' + 'a'.repeat(32),
  finalization_status: 'verifying_public',
  finalization_target_sha: 'b'.repeat(40),
  finalization_source_sha256: '6'.repeat(64),
  finalization_head_sha: '7'.repeat(40),
  finalization_merge_sha: '8'.repeat(40),
  finalization_artifact_hash: '9'.repeat(64),
  finalization_lease_expires_at: '2099-08-20T12:00:00Z',
};
neonFinalizationStatusRow = { id: 'sub_neonfinalizer01' };
const neonFinalizationCompleted = await workerTest.internalPromoteFinalization(
  { NEON_DATABASE_URL: 'postgres://example' },
  'fin_' + 'a'.repeat(32),
  'b'.repeat(40),
  {
    status: 'live', checked_at: '2026-08-20T00:00:00Z',
    R1: { status: 'passed' }, R2: { status: 'passed' },
    R3: { status: 'passed' }, R4: { status: 'published' },
  }
);
const neonFinalizationStatusCall = neonSqlCalls.find((call) => call.name === 'omo-internal-finalization-promote-v1');
check('internal finalization completion Neon: promotion, publish readiness, and completion are one atomic update',
  neonFinalizationCompleted === true &&
  neonFinalizationStatusCall.text.includes("SET status = 'ready_for_publish', release_phase = 'promoted'") &&
  neonFinalizationStatusCall.text.includes("finalization_status = 'completed'") &&
  neonFinalizationStatusCall.text.includes("release_phase = 'merged_verified'") &&
  neonFinalizationStatusCall.text.includes('source_sha256 = finalization_source_sha256') &&
  neonFinalizationStatusCall.text.includes('finalization_lease_expires_at::timestamptz > CURRENT_TIMESTAMP'));
neonFinalizationDetailRow = null;
neonFinalizationStatusRow = null;

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
  internalDetailBody.submission.release_phase === 'promoted' &&
  internalDetailBody.submission.release_pr_number === 42 &&
  internalDetailBody.submission.release_branch === 'omo-release/' + internalClaimBody.submission.id + '-auto-workflow' &&
  internalDetailBody.submission.release_head_sha === 'a'.repeat(40) &&
  internalDetailBody.submission.release_merge_sha === 'c'.repeat(40) &&
  internalDetailBody.submission.release_artifact_hash === 'b'.repeat(64) &&
  internalDetailBody.submission.promotion_evidence.status === 'live' &&
  internalDetailBody.submission.promotion_evidence.R4.status === 'published' &&
  !JSON.stringify(internalDetailBody.submission).includes('must-not-store') &&
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
neonInternalDetailRow = {
  id: 'sub_neondetail01',
  slug: 'neon-workflow',
  source_sha256: 'e'.repeat(64),
  selected_runtime: null,
  status: 'failed',
};
const neonPreRuntimeDetail = await worker.fetch(mkReq('POST', '/api/internal/submissions/sub_neondetail01/detail', {}, internalHeaders), migrationEnv);
const neonPreRuntimeBody = await neonPreRuntimeDetail.json();
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
check('internal detail Neon: valid pre-runtime failure omits unset selected_runtime instead of returning 500',
  neonPreRuntimeDetail.status === 200 &&
  neonPreRuntimeBody.submission.status === 'failed' &&
  !('selected_runtime' in neonPreRuntimeBody.submission));

neonSqlCalls.length = 0;
neonInternalDetailRow = validMergedReleaseRecord('sub_neonresume01', { release_merge_sha: '2'.repeat(40) });
neonResumeMergedRow = { id: 'sub_neonresume01' };
const resumeMergeSha = '2'.repeat(40);
const resumeMerged = await worker.fetch(mkReq('POST', '/api/internal/submissions/sub_neonresume01/resume-merged-release', {
  merge_sha: resumeMergeSha,
}, internalHeaders), migrationEnv);
const resumeMergedBody = await resumeMerged.json();
const resumeMergedCall = neonSqlCalls.find((call) => call.name === 'omo-internal-resume-merged-release-v1');
neonInternalDetailRow = null;
neonResumeMergedRow = null;
const resumeMergedMismatch = await worker.fetch(mkReq('POST', '/api/internal/submissions/sub_neonresume01/resume-merged-release', {
  merge_sha: '3'.repeat(40),
}, internalHeaders), migrationEnv);
const resumeMergedExtra = await worker.fetch(mkReq('POST', '/api/internal/submissions/sub_neonresume01/resume-merged-release', {
  merge_sha: resumeMergeSha,
  status: 'ready_for_deploy',
}, internalHeaders), migrationEnv);
const resumeMergedBadAuth = await worker.fetch(mkReq('POST', '/api/internal/submissions/sub_neonresume01/resume-merged-release', {
  merge_sha: resumeMergeSha,
}, { Authorization: 'Bearer wrong-token' }), migrationEnv);
check('internal merged-release recovery: exact merge evidence resumes failed row and all other transitions fail closed',
  resumeMerged.status === 200 &&
  resumeMergedBody.ok === true &&
  resumeMergedBody.status === 'ready_for_deploy' &&
  resumeMergedMismatch.status === 409 &&
  resumeMergedExtra.status === 400 &&
  resumeMergedBadAuth.status === 401);

function validMergedReleaseRecord(id, overrides = {}) {
  const sourceSha256 = 'a'.repeat(64);
  return {
    id,
    slug: 'label-normalizer-canary',
    status: 'failed',
    failure_code: null,
    release_phase: 'merged_verified',
    release_issue_url: 'https://github.com/harrythentrepreneur/Omo.Space/issues/112',
    release_pr_url: 'https://github.com/harrythentrepreneur/Omo.Space/pull/111',
    release_pr_number: 111,
    release_branch: `omo-release/${id}-label-normalizer-canary`,
    release_head_sha: 'b'.repeat(40),
    release_merge_sha: 'c'.repeat(40),
    release_artifact_hash: 'd'.repeat(64),
    source_sha256: sourceSha256,
    selected_runtime: 'modal-hosted',
    published_slug: 'label-normalizer-canary',
    workflow_version: 'label-normalizer-canary@1.0.0',
    build_evidence: JSON.stringify({ checks: ['trusted_compile'], source_sha256: sourceSha256 }),
    ...overrides,
  };
}

function d1DatabaseForSubmissionClaim(records) {
  const db = new DatabaseSync(':memory:');
  db.exec(`CREATE TABLE submissions (
    id TEXT PRIMARY KEY, user_id TEXT, name TEXT, slug TEXT, content TEXT,
    source_sha256 TEXT, requested_runtime TEXT, status TEXT, failure_code TEXT,
    build_claimed_at TEXT, build_attempts INTEGER, build_evidence TEXT,
    finalization_id TEXT, created_at TEXT, updated_at TEXT
  )`);
  for (const record of records) {
    const keys = Object.keys(record);
    db.prepare(`INSERT INTO submissions (${keys.join(',')}) VALUES (${keys.map(() => '?').join(',')})`).run(...keys.map((key) => record[key]));
  }
  return {
    db,
    binding: {
      prepare(sql) {
        return {
          bind(...values) {
            return {
              first: async () => db.prepare(sql).get(...values) || null,
              all: async () => ({ results: db.prepare(sql).all(...values) }),
              run: async () => {
                const result = db.prepare(sql).run(...values);
                return { meta: { changes: Number(result.changes) } };
              },
            };
          },
        };
      },
    },
  };
}

const d1ClaimLease = new Date(Date.now() - (2 * 60 * 60 + 1) * 1000).toISOString();
const d1ClaimValidId = 'sub_d1staleclaim01';
const d1ClaimInvalidId = 'sub_d1badstale01';
const d1Claims = d1DatabaseForSubmissionClaim([
  {
    id: d1ClaimValidId, user_id: 'user_private', name: 'D1 Stale Claim', slug: 'd1-stale-claim',
    content: '---\nname: d1-stale-claim\ndescription: safe d1 claim fixture\n---\n', source_sha256: '7'.repeat(64),
    requested_runtime: 'auto', status: 'processing', failure_code: 'old_failure',
    build_claimed_at: d1ClaimLease, build_attempts: 6,
    build_evidence: JSON.stringify({ checks: ['old_check'], source_sha256: '7'.repeat(64) }),
    created_at: '2026-08-01T00:00:00.000Z', updated_at: d1ClaimLease,
  },
  {
    id: d1ClaimInvalidId, user_id: 'user_private', name: 'Bad D1 Stale Claim', slug: 'bad-d1-stale-claim',
    content: '', source_sha256: 'not-a-source-identity', requested_runtime: 'auto', status: 'processing',
    failure_code: 'must_stay', build_claimed_at: d1ClaimLease, build_attempts: 9,
    build_evidence: '{"secret":"must-stay"}', created_at: '2026-08-01T00:00:00.000Z', updated_at: d1ClaimLease,
  },
]);
const d1ConcurrentClaims = await Promise.all([
  workerTest.internalClaimSubmission({ BALANCE_DB: d1Claims.binding }, { id: d1ClaimValidId, includeReview: false, includeReady: false }),
  workerTest.internalClaimSubmission({ BALANCE_DB: d1Claims.binding }, { id: d1ClaimValidId, includeReview: false, includeReady: false }),
]);
const d1SuccessfulClaims = d1ConcurrentClaims.filter(Boolean);
const d1ClaimFinal = d1Claims.db.prepare('SELECT * FROM submissions WHERE id = ?').get(d1ClaimValidId);
const d1InvalidClaim = await workerTest.internalClaimSubmission(
  { BALANCE_DB: d1Claims.binding }, { id: d1ClaimInvalidId, includeReview: false, includeReady: false }
);
const d1InvalidFinal = d1Claims.db.prepare('SELECT * FROM submissions WHERE id = ?').get(d1ClaimInvalidId);
check('internal claim lease D1: stale compare-and-swap has one winner and malformed stale source is untouched',
  d1SuccessfulClaims.length === 1 && workerTest.internalClaimRow(d1SuccessfulClaims[0]).prior_status === 'processing' &&
  d1ClaimFinal.status === 'processing' && d1ClaimFinal.failure_code === null &&
  d1ClaimFinal.build_attempts === 7 && d1ClaimFinal.build_evidence === null &&
  Date.parse(d1ClaimFinal.build_claimed_at) > Date.parse(d1ClaimLease) &&
  d1InvalidClaim === null && d1InvalidFinal.failure_code === 'must_stay' &&
  d1InvalidFinal.build_attempts === 9 && d1InvalidFinal.build_claimed_at === d1ClaimLease);
d1Claims.db.close();

function d1DatabaseForFinalization(record) {
  const db = new DatabaseSync(':memory:');
  db.exec(`CREATE TABLE submissions (
    id TEXT PRIMARY KEY, slug TEXT, source_sha256 TEXT, selected_runtime TEXT,
    status TEXT, release_phase TEXT, published_slug TEXT, workflow_version TEXT,
    build_evidence TEXT, release_issue_url TEXT, release_pr_url TEXT,
    release_pr_number INTEGER, release_branch TEXT, release_head_sha TEXT,
    release_merge_sha TEXT, release_artifact_hash TEXT, promotion_evidence TEXT,
    finalization_id TEXT, finalization_status TEXT, finalization_target_sha TEXT,
    finalization_source_sha256 TEXT, finalization_head_sha TEXT,
    finalization_merge_sha TEXT, finalization_artifact_hash TEXT,
    finalization_claimed_at TEXT, finalization_lease_expires_at TEXT,
    finalization_attempts INTEGER NOT NULL DEFAULT 0,
    finalization_failure_code TEXT, finalization_modal_receipt TEXT,
    finalization_worker_receipt TEXT, finalization_recovery_receipt TEXT,
    automation_updated_at TEXT, updated_at TEXT
  )`);
  const keys = Object.keys(record);
  db.prepare(`INSERT INTO submissions (${keys.join(',')}) VALUES (${keys.map(() => '?').join(',')})`)
    .run(...keys.map((key) => record[key]));
  return {
    db,
    binding: {
      prepare(sql) {
        return {
          bind(...values) {
            return {
              first: async () => db.prepare(sql).get(...values) || null,
              all: async () => ({ results: db.prepare(sql).all(...values) }),
              run: async () => {
                const result = db.prepare(sql).run(...values);
                return { meta: { changes: Number(result.changes) } };
              },
            };
          },
        };
      },
    },
  };
}

const d1FinalizerId = 'sub_d1finalizer01';
const d1Finalizer = d1DatabaseForFinalization({
  id: d1FinalizerId,
  slug: 'd1-finalizer',
  source_sha256: 'a'.repeat(64),
  selected_runtime: 'worker-native',
  status: 'ready_for_deploy',
  release_phase: 'merged_verified',
  published_slug: 'd1-finalizer',
  workflow_version: 'd1-finalizer@1.0.0',
  build_evidence: JSON.stringify({ checks: ['trusted_compile'], source_sha256: 'a'.repeat(64) }),
  release_issue_url: 'https://github.com/omo-space/marketplace/issues/61',
  release_pr_url: 'https://github.com/omo-space/marketplace/pull/62',
  release_pr_number: 62,
  release_branch: 'omo-release/' + d1FinalizerId + '-d1-finalizer',
  release_head_sha: 'b'.repeat(40),
  release_merge_sha: 'c'.repeat(40),
  release_artifact_hash: 'd'.repeat(64),
  finalization_attempts: 0,
  updated_at: '2026-08-20T00:00:00.000Z',
});
const d1FinalizerEnv = { BALANCE_DB: d1Finalizer.binding };
const d1FinalizerTarget = 'e'.repeat(40);
const d1RegistrySlugs = await workerTest.internalRequiredRegistrySlugs(d1FinalizerEnv);
const d1FinalizerClaim = await workerTest.internalClaimFinalization(d1FinalizerEnv, d1FinalizerTarget);
const d1FinalizerDuplicate = await workerTest.internalClaimFinalization(d1FinalizerEnv, d1FinalizerTarget);
const d1FinalizerDeploying = await workerTest.internalSetFinalizationStatus(
  d1FinalizerEnv, d1FinalizerClaim.id, d1FinalizerTarget, 'deploying_worker'
);
const d1WorkerReceipt = workerTest.safeDeploymentReceipt({
  provider: 'cloudflare', target: 'cognition-demos', environment: 'production',
  target_sha: d1FinalizerTarget, artifact_hash: 'd'.repeat(64),
  version_id: 'worker-version-1', previous_version_id: 'worker-version-0',
  reused: false, rollback_token: 'worker-version-0', status: 'passed',
}, 'worker_deploy', d1FinalizerTarget);
const d1ConcurrentEffectResults = await Promise.all([
  workerTest.internalRecordFinalizationEffect(
    d1FinalizerEnv, d1FinalizerClaim.id, 'worker_deploy', d1FinalizerTarget, d1WorkerReceipt
  ),
  workerTest.internalRecordFinalizationEffect(
    d1FinalizerEnv, d1FinalizerClaim.id, 'worker_deploy', d1FinalizerTarget, d1WorkerReceipt
  ),
]);
const d1ConflictingReceipt = { ...d1WorkerReceipt, version_id: 'worker-version-2' };
const d1EffectConflict = await workerTest.internalRecordFinalizationEffect(
  d1FinalizerEnv, d1FinalizerClaim.id, 'worker_deploy', d1FinalizerTarget, d1ConflictingReceipt
);
const d1FinalizerVerifying = await workerTest.internalSetFinalizationStatus(
  d1FinalizerEnv, d1FinalizerClaim.id, d1FinalizerTarget, 'verifying_public'
);
const d1FinalizerCompleted = await workerTest.internalPromoteFinalization(
  d1FinalizerEnv,
  d1FinalizerClaim.id,
  d1FinalizerTarget,
  {
    status: 'live', checked_at: '2026-08-20T00:00:00Z',
    R1: { status: 'passed' }, R2: { status: 'passed' },
    R3: { status: 'passed' }, R4: { status: 'published' },
  }
);
const d1FinalizerRow = d1Finalizer.db.prepare('SELECT * FROM submissions WHERE id = ?').get(d1FinalizerId);
check('internal finalization D1: SQLite claim and immutable phase CAS complete one exact generation',
  d1FinalizerClaim && d1FinalizerClaim.submission_id === d1FinalizerId &&
  d1FinalizerDuplicate === null && d1FinalizerDeploying === true &&
  d1RegistrySlugs.length === 1 && d1RegistrySlugs[0] === 'd1-finalizer' &&
  d1ConcurrentEffectResults.slice().sort().join(',') === 'recorded,replayed' && d1EffectConflict === 'conflict' &&
  d1FinalizerVerifying === true && d1FinalizerCompleted === true &&
  d1FinalizerRow.finalization_status === 'completed' &&
  d1FinalizerRow.finalization_source_sha256 === 'a'.repeat(64) &&
  d1FinalizerRow.finalization_head_sha === 'b'.repeat(40) &&
  d1FinalizerRow.finalization_merge_sha === 'c'.repeat(40) &&
  d1FinalizerRow.finalization_artifact_hash === 'd'.repeat(64) &&
  d1FinalizerRow.finalization_attempts === 1 &&
  JSON.parse(d1FinalizerRow.finalization_worker_receipt).version_id === 'worker-version-1');
d1Finalizer.db.close();

const d1EffectRace = d1DatabaseForFinalization({
  id: 'sub_d1effectrace01', slug: 'd1-effect-race', source_sha256: '1'.repeat(64),
  selected_runtime: 'worker-native', status: 'ready_for_deploy', release_phase: 'merged_verified',
  release_head_sha: '2'.repeat(40), release_merge_sha: '3'.repeat(40), release_artifact_hash: '4'.repeat(64),
  finalization_id: 'fin_' + '5'.repeat(32), finalization_status: 'deploying_worker',
  finalization_target_sha: '6'.repeat(40), finalization_source_sha256: '1'.repeat(64),
  finalization_head_sha: '2'.repeat(40), finalization_merge_sha: '3'.repeat(40),
  finalization_artifact_hash: '4'.repeat(64), finalization_lease_expires_at: '2099-08-20T12:00:00Z',
  finalization_attempts: 1, finalization_worker_receipt: null, updated_at: '2026-08-20T00:00:00Z',
});
let d1CompletionInterleaved = false;
const d1RaceBinding = {
  prepare(sql) {
    const prepared = d1EffectRace.binding.prepare(sql);
    return {
      bind(...values) {
        const bound = prepared.bind(...values);
        return {
          first: async () => {
            const row = await bound.first();
            if (!d1CompletionInterleaved && sql.includes('FROM submissions WHERE finalization_id')) {
              d1EffectRace.db.prepare("UPDATE submissions SET finalization_status = 'completed' WHERE finalization_id = ?")
                .run('fin_' + '5'.repeat(32));
              d1CompletionInterleaved = true;
            }
            return row;
          },
          all: bound.all,
          run: bound.run,
        };
      },
    };
  },
};
const d1RaceReceipt = workerTest.safeDeploymentReceipt({
  provider: 'cloudflare', target: 'cognition-demos', environment: 'production',
  target_sha: '6'.repeat(40), artifact_hash: '4'.repeat(64), version_id: 'race-v2',
  previous_version_id: 'race-v1', reused: false, rollback_token: 'race-v1', status: 'passed',
}, 'worker_deploy', '6'.repeat(40));
const d1LateEffect = await workerTest.internalRecordFinalizationEffect(
  { BALANCE_DB: d1RaceBinding }, 'fin_' + '5'.repeat(32), 'worker_deploy', '6'.repeat(40), d1RaceReceipt
);
const d1RaceRow = d1EffectRace.db.prepare('SELECT finalization_status,finalization_worker_receipt FROM submissions WHERE id = ?')
  .get('sub_d1effectrace01');
check('internal finalization effect D1 race: completion wins and late receipt write is rejected atomically',
  d1CompletionInterleaved && d1LateEffect === 'invalid' &&
  d1RaceRow.finalization_status === 'completed' && d1RaceRow.finalization_worker_receipt === null);
d1EffectRace.db.close();

const d1Completed = d1DatabaseForFinalization({
  ...completedFinalizationRecord,
  automation_updated_at: '2026-08-21T00:00:00Z',
  updated_at: '2026-08-21T00:00:00Z',
});
const d1CompletedResume = await workerTest.internalResumeCompletedFinalization(
  { BALANCE_DB: d1Completed.binding }, '3'.repeat(40)
);
d1Completed.db.prepare("UPDATE submissions SET status = 'deployed' WHERE id = ?").run(completedFinalizationId);
const d1CompletedAfterDeploy = await workerTest.internalResumeCompletedFinalization(
  { BALANCE_DB: d1Completed.binding }, '3'.repeat(40)
);
check('internal completed finalization resume D1: real SQLite returns publish-ready and confirms deployed',
  workerTest.completedFinalizationRow(d1CompletedResume).status === 'completed' &&
  workerTest.completedFinalizationRow(d1CompletedAfterDeploy).submission_status === 'deployed');
d1Completed.db.close();

const d1FailedTarget = '7'.repeat(40);
const d1Failed = d1DatabaseForFinalization({
  id: 'sub_d1failedfinal01', slug: 'd1-failed-final', source_sha256: '8'.repeat(64),
  selected_runtime: 'worker-native', status: 'failed',
  release_phase: 'merged_verified', published_slug: 'd1-failed-final',
  workflow_version: 'd1-failed-final@1.0.0',
  build_evidence: JSON.stringify({ checks: ['trusted_compile'], source_sha256: '8'.repeat(64) }),
  release_issue_url: 'https://github.com/omo-space/marketplace/issues/81',
  release_pr_url: 'https://github.com/omo-space/marketplace/pull/82', release_pr_number: 82,
  release_branch: 'omo-release/sub_d1failedfinal01-d1-failed-final',
  release_head_sha: '9'.repeat(40), release_merge_sha: 'a'.repeat(40),
  release_artifact_hash: 'b'.repeat(64), finalization_id: 'fin_' + '7'.repeat(32),
  finalization_status: 'failed', finalization_failure_code: 'release_head_not_ancestor',
  finalization_target_sha: d1FailedTarget, finalization_source_sha256: '8'.repeat(64),
  finalization_head_sha: '9'.repeat(40), finalization_merge_sha: 'a'.repeat(40),
  finalization_artifact_hash: 'b'.repeat(64), finalization_attempts: 1,
  finalization_lease_expires_at: '2026-08-21T00:00:00Z', finalization_modal_receipt: null,
  finalization_worker_receipt: null, automation_updated_at: '2026-08-21T00:00:00Z',
  updated_at: '2026-08-21T00:00:00Z',
});
const d1FailedEnv = { BALANCE_DB: d1Failed.binding };
const d1FailedBefore = workerTest.failedFinalizationRow(
  await workerTest.internalInspectFailedFinalization(d1FailedEnv, d1FailedTarget)
);
const d1FailedRequeued = await workerTest.internalResumeFailedFinalization(d1FailedEnv, d1FailedTarget);
const d1FreshTarget = 'c'.repeat(40);
const d1FailedResumed = await workerTest.internalClaimFinalization(d1FailedEnv, d1FreshTarget);
const d1FailedReplay = await workerTest.internalResumeFailedFinalization(d1FailedEnv, d1FailedTarget);
const d1FailedAfter = d1Failed.db.prepare(
  'SELECT status,finalization_id,finalization_status,finalization_attempts,finalization_failure_code FROM submissions WHERE id = ?'
).get('sub_d1failedfinal01');

check('internal failed finalization resume D1: real SQLite requeues once, then standard claim binds fresh green target',
  d1FailedBefore.failure_code === 'release_head_not_ancestor' &&
  d1FailedBefore.modal_receipt_present === false && d1FailedBefore.worker_receipt_present === false &&
  d1FailedRequeued === true && d1FailedResumed && d1FailedResumed.target_sha === d1FreshTarget &&
  d1FailedResumed.id !== 'fin_' + '7'.repeat(32) && d1FailedResumed.attempts === 2 &&
  d1FailedReplay === false && d1FailedAfter.status === 'ready_for_deploy' &&
  d1FailedAfter.finalization_status === 'claimed' && d1FailedAfter.finalization_attempts === 2 &&
  d1FailedAfter.finalization_failure_code === null);
d1Failed.db.close();

const d1RecoveryRecord = {
  ...rollbackRecord, status: 'failed', finalization_id: 'fin_' + '8'.repeat(32),
  finalization_status: 'failed', finalization_failure_code: 'worker_smoke_failed',
  finalization_target_sha: rollbackTarget, finalization_source_sha256: 'a'.repeat(64),
  finalization_head_sha: 'b'.repeat(40), finalization_merge_sha: 'c'.repeat(40),
  finalization_artifact_hash: rollbackArtifact, finalization_attempts: 5,
  finalization_modal_receipt: JSON.stringify(rollbackModalReceipt),
  finalization_worker_receipt: JSON.stringify(rollbackWorkerReceipt),
  finalization_recovery_receipt: JSON.stringify(priorRecoveryEvidence),
};
delete d1RecoveryRecord.failure_code;
const d1Recovery = d1DatabaseForFinalization(d1RecoveryRecord);
const d1RecoveryEnv = { BALANCE_DB: d1Recovery.binding };
const d1Recovered = await workerTest.internalRecoverRolledBackFinalization(d1RecoveryEnv, rollbackTarget);
const d1RecoveryReplay = await workerTest.internalRecoverRolledBackFinalization(d1RecoveryEnv, rollbackTarget);
const d1RecoveryFreshTarget = 'e'.repeat(40);
const d1RecoveryClaim = await workerTest.internalClaimFinalization(d1RecoveryEnv, d1RecoveryFreshTarget);
const d1RecoveryAfter = d1Recovery.db.prepare(
  'SELECT status,finalization_id,finalization_target_sha,finalization_attempts,finalization_recovery_receipt FROM submissions WHERE id = ?'
).get(rollbackRecord.id);
const d1RecoveryHistory = JSON.parse(d1RecoveryAfter.finalization_recovery_receipt);
const d1RecoveryEvidence = d1RecoveryHistory[1];
check('receipt-aware rollback recovery D1: real SQLite CAS has one winner and ordinary next claim preserves evidence',
  d1Recovered === true && d1RecoveryReplay === false && d1RecoveryClaim &&
  d1RecoveryClaim.target_sha === d1RecoveryFreshTarget && d1RecoveryClaim.attempts === 6 &&
  d1RecoveryAfter.finalization_id !== 'fin_' + '8'.repeat(32) &&
  d1RecoveryAfter.finalization_target_sha === d1RecoveryFreshTarget &&
  d1RecoveryAfter.finalization_attempts === 6 && Array.isArray(d1RecoveryHistory) && d1RecoveryHistory.length === 2 &&
  JSON.stringify(d1RecoveryHistory[0]) === JSON.stringify(priorRecoveryEvidence) &&
  d1RecoveryEvidence.target_sha === rollbackTarget &&
  d1RecoveryEvidence.modal_receipt.version_id === 'modal-v7' &&
  d1RecoveryEvidence.worker_receipt.previous_version_id === 'cf-v8');
d1Recovery.db.close();

function d1DatabaseForMergedRelease(record) {
  const db = new DatabaseSync(':memory:');
  db.exec(`CREATE TABLE submissions (
    id TEXT PRIMARY KEY, slug TEXT, status TEXT, failure_code TEXT, release_phase TEXT,
    release_issue_url TEXT, release_pr_url TEXT, release_pr_number INTEGER,
    release_branch TEXT, release_head_sha TEXT, release_merge_sha TEXT,
    release_artifact_hash TEXT, source_sha256 TEXT, selected_runtime TEXT,
    published_slug TEXT, workflow_version TEXT, build_evidence TEXT, updated_at TEXT,
    modal_app TEXT, modal_url TEXT, canary_evidence TEXT, promotion_evidence TEXT
  )`);
  const keys = Object.keys(record);
  db.prepare(`INSERT INTO submissions (${keys.join(',')}) VALUES (${keys.map(() => '?').join(',')})`).run(...keys.map((key) => record[key]));
  return {
    db,
    binding: {
      prepare(sql) {
        return {
          bind(...values) {
            return {
              first: async () => db.prepare(sql).get(...values) || null,
              all: async () => ({ results: db.prepare(sql).all(...values) }),
              run: async () => {
                const result = db.prepare(sql).run(...values);
                return { meta: { changes: Number(result.changes) } };
              },
            };
          },
        };
      },
    },
  };
}

const malformedMergedEvidence = [
  { release_pr_number: 0 },
  { release_issue_url: 'https://evil.invalid/issues/112' },
  { release_pr_url: 'https://github.com/harrythentrepreneur/Omo.Space/issues/111' },
  { release_branch: 'main' },
  { release_head_sha: 'g'.repeat(40) },
  { release_artifact_hash: 'g'.repeat(64) },
  { source_sha256: 'g'.repeat(64) },
  { selected_runtime: 'shell-hosted' },
  { slug: 'different-valid-slug' },
  { published_slug: 'Bad Slug' },
  { workflow_version: 'not-a-version' },
  { build_evidence: null },
  { build_evidence: '{bad json' },
  { build_evidence: JSON.stringify({ checks: [], source_sha256: 'a'.repeat(64) }) },
  { build_evidence: JSON.stringify({ checks: ['trusted_compile'] }) },
  { build_evidence: JSON.stringify({ checks: ['trusted_compile'], source_sha256: 'e'.repeat(64) }) },
  { status: 'ready_for_deploy' },
  { release_phase: 'pr_open' },
];

const d1ValidId = 'sub_d1resumevalid01';
const d1Valid = d1DatabaseForMergedRelease(validMergedReleaseRecord(d1ValidId));
const d1First = await workerTest.internalResumeMergedRelease({ BALANCE_DB: d1Valid.binding }, d1ValidId, 'c'.repeat(40));
const d1Replay = await workerTest.internalResumeMergedRelease({ BALANCE_DB: d1Valid.binding }, d1ValidId, 'c'.repeat(40));
const d1Final = d1Valid.db.prepare('SELECT status, failure_code FROM submissions WHERE id = ?').get(d1ValidId);
const d1MalformedResults = [];
for (let index = 0; index < malformedMergedEvidence.length; index += 1) {
  const id = `sub_d1resumebad${String(index).padStart(2, '0')}`;
  const fixture = d1DatabaseForMergedRelease(validMergedReleaseRecord(id, malformedMergedEvidence[index]));
  d1MalformedResults.push(await workerTest.internalResumeMergedRelease({ BALANCE_DB: fixture.binding }, id, 'c'.repeat(40)));
  fixture.db.close();
}
check('internal merged-release recovery: D1 validates complete evidence atomically and rejects replay',
  d1First === true && d1Replay === false && d1Final.status === 'ready_for_deploy' &&
  d1Final.failure_code === null && d1MalformedResults.every((result) => result === false));
d1Valid.db.close();

const mockValidId = 'sub_mockresumevalid01';
workerTest.mockSubmissions.set(`resume\u0000${mockValidId}`, validMergedReleaseRecord(mockValidId));
const mockFirst = await workerTest.internalResumeMergedRelease({}, mockValidId, 'c'.repeat(40));
const mockReplay = await workerTest.internalResumeMergedRelease({}, mockValidId, 'c'.repeat(40));
const mockMalformedResults = [];
for (let index = 0; index < malformedMergedEvidence.length; index += 1) {
  const id = `sub_mockresumebad${String(index).padStart(2, '0')}`;
  workerTest.mockSubmissions.set(`resume\u0000${id}`, validMergedReleaseRecord(id, malformedMergedEvidence[index]));
  mockMalformedResults.push(await workerTest.internalResumeMergedRelease({}, id, 'c'.repeat(40)));
}
check('internal merged-release recovery: mock validates complete evidence and rejects replay',
  mockFirst === true && mockReplay === false && mockMalformedResults.every((result) => result === false));
check('internal merged-release recovery: Neon update is atomic and binds the validated evidence snapshot',
  resumeMergedCall &&
  resumeMergedCall.text.includes("SET status = 'ready_for_deploy'") &&
  resumeMergedCall.text.includes("status = 'failed'") &&
  resumeMergedCall.text.includes("release_phase = 'merged_verified'") &&
  resumeMergedCall.text.includes('release_merge_sha = $2') &&
  resumeMergedCall.text.includes('source_sha256 = $3') &&
  resumeMergedCall.text.includes('release_head_sha = $4') &&
  resumeMergedCall.text.includes('release_artifact_hash = $5') &&
  resumeMergedCall.text.includes('build_evidence = $13') &&
  resumeMergedCall.text.includes('slug = $14') &&
  resumeMergedCall.values[0] === 'sub_neonresume01' &&
  resumeMergedCall.values[1] === resumeMergeSha &&
  resumeMergedCall.values.length === 14);

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

// ── /api/pilot/claim (signed, expiring, authenticated, idempotent) ────────

const pilotSecret = 'fixture-only-pilot-secret-32-bytes-minimum';
const pilotEnv = {
  ...realEnv,
  PILOT_MAGIC_LINK_SECRET: pilotSecret,
  PILOT_BOOK_BUILDER_PATH: '/run.html?slug=fixture-phonics-book',
};
const pilotNow = Math.floor(Date.now() / 1000);
const pilotToken = await signPilotToken({
  email: 'pilot-teacher@example.com', cohort: 'pilot-200', grant_cents: 99, exp: pilotNow + 300,
}, pilotSecret);
const pilotPath = `/api/pilot/claim?token=${encodeURIComponent(pilotToken)}`;
const pilotReadyResponse = await worker.fetch(mkReq('GET', pilotPath, {}), pilotEnv);
const pilotReady = await pilotReadyResponse.json();
check('pilot claim: valid token verifies without consuming the grant',
  pilotReadyResponse.status === 200 && pilotReady.status === 'ready_to_claim' && pilotReady.grant_cents === 99);

const pilotMissingAuthResponse = await worker.fetch(mkReq('POST', pilotPath, {}), pilotEnv);
const pilotMissingAuth = await pilotMissingAuthResponse.json();
check('pilot claim: redemption requires a verified Clerk session',
  pilotMissingAuthResponse.status === 401 && pilotMissingAuth.error === 'authentication_required');

const pilotClerkToken = await clerkToken('user_pilot_claim');
const pilotHeaders = { Authorization: `Bearer ${pilotClerkToken}`, Origin: 'https://omo.space' };
const pilotClaimedResponse = await worker.fetch(mkReq('POST', pilotPath, {}, pilotHeaders), pilotEnv);
const pilotClaimed = await pilotClaimedResponse.json();
const pilotBalanceResponse = await worker.fetch(mkReq('GET', '/api/me', {}, pilotHeaders), pilotEnv);
const pilotBalance = await pilotBalanceResponse.json();
check('pilot claim: finalized email promise lands exactly 99 cents in a fresh balance',
  pilotClaimedResponse.status === 200 && pilotClaimed.status === 'claimed' &&
  pilotClaimed.grant_cents === 99 && pilotClaimed.balance_cents === 99 && pilotBalance.balance_cents === 99);

const pilotReplayResponse = await worker.fetch(mkReq('POST', pilotPath, {}, pilotHeaders), pilotEnv);
const pilotReplay = await pilotReplayResponse.json();
const pilotBalanceAfterReplay = await (await worker.fetch(mkReq('GET', '/api/me', {}, pilotHeaders), pilotEnv)).json();
check('pilot claim: token reuse is typed and never double-grants',
  pilotReplayResponse.status === 409 && pilotReplay.error === 'pilot_token_reused' && pilotBalanceAfterReplay.balance_cents === 99);

const pilotInvalidResponse = await worker.fetch(mkReq('POST', '/api/pilot/claim?token=v1.invalid.invalid', {}, pilotHeaders), pilotEnv);
const pilotInvalid = await pilotInvalidResponse.json();
check('pilot claim: invalid signature returns a typed error',
  pilotInvalidResponse.status === 400 && pilotInvalid.error === 'pilot_token_invalid');

const expiredPilotToken = await signPilotToken({
  email: 'expired-teacher@example.com', cohort: 'pilot-200', grant_cents: 99, exp: pilotNow - 1,
}, pilotSecret);
const pilotExpiredResponse = await worker.fetch(mkReq('POST', `/api/pilot/claim?token=${encodeURIComponent(expiredPilotToken)}`, {}, pilotHeaders), pilotEnv);
const pilotExpired = await pilotExpiredResponse.json();
check('pilot claim: expired token returns a typed error without a grant',
  pilotExpiredResponse.status === 410 && pilotExpired.error === 'pilot_token_expired' && pilotBalanceAfterReplay.balance_cents === 99);

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
  run_id: 'run-provider-woven', status: 'completed', workflow_version: 'woven-storybook-pipeline@0.3.0',
  title: 'Wrong Turns, Best Views', book: '# Wrong Turns, Best Views\n\nA long enough factual keepsake story that clears the minimum output length. '.repeat(4),
  page_plan: ['Cover with rainy bookshop', 'The beginning in the bookshop', 'Two cities and one corgi', 'Closing on the best view'],
  usage: { provider: 'opencode-go', model: 'deepseek-v4-flash', llm_calls: 1, prompt_tokens: 269, completion_tokens: 314, estimated_cost_usd: 0.00012558 },
  artifact: { kind: 'pdf', role: 'book', object_key: 'runs/run-provider-woven/woven-keepsake.pdf', filename: 'woven-keepsake.pdf', content_type: 'application/pdf', bytes: 2048, sha256: 'a'.repeat(64), page_count: 4 },
  artifact_url: 'https://woven.modal.invalid/v1/artifacts/run-provider-woven/woven-keepsake.pdf?token=test',
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
check('hosted registry: Facebook Ads executes Worker-native synchronously at the server-owned $0.10 quote', facebookStartResponse.status === 200 && facebookStart.status === 'completed' && facebookStart.output.ads.length === 3 && facebookStart.output.run_id === facebookStart.run_id && facebookStart.output.status === 'completed' && facebookStart.output.workflow_version === 'facebook-ads-copywriter@0.1.0' && facebookStart.output.usage.provider === 'opencode-go' && facebookStart.output.usage.prompt_tokens === 820 && facebookStart.output.usage.completion_tokens === 640 && facebookStart.cost_usd === 0.1 && facebookStart.balance === 4.9);
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

workerNativeMode = 'late_success_after_refund';
workerNativeProviderGate = new Promise((resolve) => { releaseWorkerNativeProvider = resolve; });
const facebookLateMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook_late', {}), env)).json();
const facebookLateHeaders = { 'X-API-Key': facebookLateMe.api_key, 'Idempotency-Key': 'facebook-router-late-success' };
const facebookLatePromise = worker.fetch(mkReq('POST', '/api/run', facebookInput, facebookLateHeaders), facebookEnv);
let facebookLateRow = null;
for (let attempt = 0; attempt < 500; attempt += 1) {
  facebookLateRow = Array.from(workerTest.mockRunRequests.values()).find((row) => row.idempotency_key === 'facebook-router-late-success') || null;
  if (facebookLateRow && facebookLateRow.state === 'running') break;
  await new Promise((resolve) => setTimeout(resolve, 1));
}
check('hosted registry: Worker-native race fixture reaches a running provider call', facebookLateRow && facebookLateRow.state === 'running');
if (!facebookLateRow) throw new Error('facebook late-success fixture did not create a run row');
facebookLateRow.updated_at = new Date(Date.now() - 61 * 1000).toISOString();
const facebookBeforeTimeout = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook_late', {}), { ...env, RUN_RESERVATION_TTL_SECONDS: '60' })).json();
check('hosted registry: Worker-native run is not stale before provider timeout plus safety buffer', facebookLateRow.state === 'running' && facebookBeforeTimeout.balance_usd === 4.9);
facebookLateRow.updated_at = new Date(Date.now() - 151 * 1000).toISOString();
const facebookAfterTimeout = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_facebook_late', {}), { ...env, RUN_RESERVATION_TTL_SECONDS: '60' })).json();
check('hosted registry: Worker-native run refunds after provider timeout plus safety buffer', facebookLateRow.state === 'refunded' && facebookAfterTimeout.balance_usd === 5);
releaseWorkerNativeProvider();
const facebookLateResponse = await facebookLatePromise;
const facebookLateBody = await facebookLateResponse.json();
check('hosted registry: late Worker-native success returns the authoritative refunded terminal result', facebookLateResponse.status === 409 && facebookLateBody.state === 'refunded' && facebookLateBody.error === 'stale_reservation_refunded' && !('output' in facebookLateBody));
workerNativeProviderGate = null;
releaseWorkerNativeProvider = null;
workerNativeMode = 'valid';

// ── Japanese generated executor → owner-scoped Modal async run ───────────

const japaneseHostedEnv = {
  ...realEnv,
  JAPANESE_STORY_VIDEO_MODAL_URL: 'https://japanese.modal.invalid',
  HOSTED_MODAL_PROXY_TOKEN_ID: 'wk-japanese-test-id',
  HOSTED_MODAL_PROXY_TOKEN_SECRET: 'ws-japanese-test-secret',
};
const japaneseMe = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_japanese_hosted', {}), env)).json();
const japaneseHeaders = { Authorization: `Bearer ${japaneseMe.api_key}`, 'Idempotency-Key': 'japanese-hosted-0001' };
const japaneseInput = { slug: 'japanese-style-story-video', input: japaneseCases.happy_path.input };
const japaneseStartResponse = await worker.fetch(mkReq('POST', '/api/run', japaneseInput, japaneseHeaders), japaneseHostedEnv);
const japaneseStart = await japaneseStartResponse.json();
check('japanese generated: exact sample input reserves $0.10 and dispatches asynchronously', japaneseStartResponse.status === 202 && japaneseStart.status === 'running' && japaneseStart.quoted_cost_usd === 0.1 && japaneseStart.billed_amount_usd === 0.1);
check('japanese generated: Worker sends proxy credentials plus stable owner scope header', japaneseCalls.length === 1 && japaneseCalls[0].headers['Modal-Key'] === 'wk-japanese-test-id' && japaneseCalls[0].headers['Modal-Secret'] === 'ws-japanese-test-secret' && japaneseCalls[0].headers['X-Omo-Owner-Id'] === 'user_japanese_hosted');
check('japanese generated: Worker dispatches only the compiler-validated public sample input', JSON.stringify(JSON.parse(japaneseCalls[0].body)) === JSON.stringify(japaneseCases.happy_path.input));
const japaneseBad = await worker.fetch(mkReq('POST', '/api/run', {
  slug: 'japanese-style-story-video',
  input: { audio: 'customer-upload-001', style: 'sumi-e', duration: 10 },
}, { ...japaneseHeaders, 'Idempotency-Key': 'japanese-hosted-bad1' }), japaneseHostedEnv);
check('japanese generated: arbitrary audio fails schema validation before reservation or Modal work', japaneseBad.status === 422 && japaneseCalls.length === 1);
const japaneseRunning = await worker.fetch(mkReq('GET', `/api/run/${japaneseStart.run_id}`, {}, { Authorization: `Bearer ${japaneseMe.api_key}` }), japaneseHostedEnv);
check('japanese generated: owner-scoped status poll forwards the same owner header', japaneseRunning.status === 202 && japaneseCalls.at(-1).headers['X-Omo-Owner-Id'] === 'user_japanese_hosted');
const japaneseCompleted = JSON.parse(JSON.stringify(japaneseCases.happy_path.output));
japaneseCompleted.run_id = 'run-0123456789abcdef0123456789abcdef';
japaneseStatuses.set('fc-JAPANESEROUTER001', { status: 200, body: japaneseCompleted });
const japaneseDoneResponse = await worker.fetch(mkReq('GET', `/api/run/${japaneseStart.run_id}`, {}, { Authorization: `Bearer ${japaneseMe.api_key}` }), japaneseHostedEnv);
const japaneseDone = await japaneseDoneResponse.json();
const japaneseAfter = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_japanese_hosted', {}), env)).json();
check('japanese generated: schema-valid five-artifact result settles the reserved $0.10 once', japaneseDoneResponse.status === 200 && japaneseDone.status === 'completed' && japaneseDone.output.artifacts.length === 5 && japaneseDone.output.media.video_codec === 'h264' && japaneseAfter.balance_usd === 4.9);
const japaneseReplay = await (await worker.fetch(mkReq('POST', '/api/run', japaneseInput, japaneseHeaders), japaneseHostedEnv)).json();
check('japanese generated: idempotent replay never dispatches or charges twice', japaneseReplay.idempotent_replay === true && japaneseReplay.run_id === japaneseStart.run_id && japaneseCalls.length === 3 && japaneseAfter.balance_usd === 4.9);

// ── Japanese Style Story Video → private Modal + async progress ───────────

const demelloEnv = {
  ...realEnv,
  DEMELLO_LEGACY_EXECUTOR: '1',
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

const pilotWebhookEnv = { ...env, PILOT_MAGIC_LINK_SECRET: pilotSecret };
const pilotWebhookToken = await signPilotToken({
  email: 'webhook-pilot@example.com', cohort: 'pilot-200', grant_cents: 99, exp: pilotNow + 300,
}, pilotSecret);
const pilotWebhookPath = `/api/pilot/claim?token=${encodeURIComponent(pilotWebhookToken)}`;
await worker.fetch(mkReq('GET', pilotWebhookPath, {}), pilotWebhookEnv);
const pilotWh = await (await worker.fetch(mkReq('POST', '/api/clerk-webhook', {
  type: 'user.created', data: { id: 'user_clerk_pilot', email_addresses: [{ email_address: 'webhook-pilot@example.com' }] },
}), pilotWebhookEnv)).json();
const pilotWhBalance = await (await worker.fetch(mkReq('GET', '/api/me?user_id=user_clerk_pilot', {}), pilotWebhookEnv)).json();
const pilotWhReplay = await worker.fetch(mkReq('GET', pilotWebhookPath, {}), pilotWebhookEnv);
check('webhook: pending pilot signup receives 99 cents instead of racing the legacy $5 grant',
  pilotWh.ok === true && pilotWh.pilot_granted === true && pilotWh.balance_cents === 99 &&
  pilotWhBalance.balance_cents === 99 && pilotWhReplay.status === 409);

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

// ── Cloudflare cron → protected Modal Hermes dispatch ─────────────────────
const builderEnv = {
  ...env,
  OMO_BUILDER_MODAL_URL: 'https://builder.modal.run',
  OMO_BUILDER_MODAL_KEY: 'modal-key-test',
  OMO_BUILDER_MODAL_SECRET: 'modal-secret-test',
  OMO_BUILDER_BASE_REVISION: 'c'.repeat(40),
};
workerTest.mockSubmissions.clear();
const beforeIdleDispatches = builderDispatchCalls.length;
let scheduledTask = null;
await worker.scheduled({}, builderEnv, { waitUntil(task) { scheduledTask = task; } });
if (scheduledTask) await scheduledTask;
check('builder cron: empty queue makes zero Modal calls', builderDispatchCalls.length === beforeIdleDispatches);

workerTest.mockSubmissions.set('user_builder:label-normalizer-canary', {
  id: 'sub_abcdefgh12345678',
  user_id: 'user_builder',
  name: 'Label Normalizer Canary',
  slug: 'label-normalizer-canary',
  content: 'PRIVATE_SOURCE_MUST_NOT_LEAVE_WORKER',
  source_sha256: 'a'.repeat(64),
  requested_runtime: 'auto',
  status: 'needs_review',
  created_at: new Date().toISOString(),
});
scheduledTask = null;
await worker.scheduled({}, builderEnv, { waitUntil(task) { scheduledTask = task; } });
if (scheduledTask) await scheduledTask;
const builderCall = builderDispatchCalls.at(-1);
check('builder cron: dispatches identifiers only with Modal proxy auth',
  builderCall.url === builderEnv.OMO_BUILDER_MODAL_URL &&
  builderCall.opts.method === 'POST' &&
  builderCall.opts.headers['Modal-Key'] === builderEnv.OMO_BUILDER_MODAL_KEY &&
  builderCall.opts.headers['Modal-Secret'] === builderEnv.OMO_BUILDER_MODAL_SECRET &&
  builderCall.payload.submission_id === 'sub_abcdefgh12345678' &&
  builderCall.payload.slug === 'label-normalizer-canary' &&
  builderCall.payload.source_sha256 === 'a'.repeat(64) &&
  /^dispatch_[0-9a-f]{32}$/.test(builderCall.payload.dispatch_id) &&
  !('base_revision' in builderCall.payload) &&
  !JSON.stringify(builderCall.payload).includes('PRIVATE_SOURCE_MUST_NOT_LEAVE_WORKER') &&
  !('content' in builderCall.payload) && !('user_id' in builderCall.payload));
check('builder cron: peek does not mutate authoritative queue state before Modal claims',
  workerTest.mockSubmissions.get('user_builder:label-normalizer-canary').status === 'needs_review');

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
