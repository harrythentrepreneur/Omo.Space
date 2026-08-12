// Omo production API canary (network, but no writes, provider calls, or spend).
// Usage: node test-live.mjs
// Override only for an equivalent deployment: LIVE_BASE_URL=https://example/api node test-live.mjs

const base = String(process.env.LIVE_BASE_URL || 'https://omo.space/api').replace(/\/+$/, '');
let pass = 0;
let fail = 0;

async function check(name, path, init, expectedStatus, expectedBody) {
  try {
    const response = await fetch(`${base}${path}`, {
      redirect: 'error',
      signal: AbortSignal.timeout(15_000),
      ...init,
      headers: {
        Accept: 'application/json',
        Origin: 'https://omo.space',
        ...(init && init.body ? { 'Content-Type': 'application/json' } : {}),
        ...(init && init.headers ? init.headers : {}),
      },
    });
    const text = await response.text();
    let body = null;
    try { body = text ? JSON.parse(text) : null; } catch { body = null; }
    const expectedStatuses = Array.isArray(expectedStatus) ? expectedStatus : [expectedStatus];
    const statusOk = expectedStatuses.includes(response.status);
    const bodyOk = !expectedBody || expectedBody(body, response);
    if (statusOk && bodyOk) {
      pass += 1;
      console.log(`PASS  ${name}`);
      return;
    }
    fail += 1;
    const safeBody = text.slice(0, 180).replace(/\s+/g, ' ');
    console.log(`FAIL  ${name} (HTTP ${response.status}; ${safeBody || 'empty body'})`);
  } catch (error) {
    fail += 1;
    console.log(`FAIL  ${name} (${error && error.name ? error.name : 'request failed'})`);
  }
}

const post = (value) => ({ method: 'POST', body: JSON.stringify(value) });
const hasError = (value) => (body) => body && body.error === value;

await check('CORS preflight reaches Worker through Vercel or directly', '/me', { method: 'OPTIONS' }, [200, 204],
  (_body, response) => response.headers.get('access-control-allow-origin') === 'https://omo.space');
await check('unknown route is 404 JSON', '/live-canary-not-a-route', { method: 'GET' }, 404,
  (body) => body && (body.error === 'Not found' || String(body.error || '').startsWith('Unknown route:')));
await check('checkout rejects GET', '/checkout', { method: 'GET' }, 405, hasError('Method not allowed'));
await check('checkout validates missing slug without Stripe', '/checkout', post({}), 400, hasError('Send slug.'));
await check('checkout rejects unknown slug without Stripe', '/checkout', post({ slug: 'live-canary-not-a-listing' }), 404, hasError('unknown_catalog_slug'));
await check('balance requires auth', '/me', { method: 'GET' }, 401, hasError('authentication_required'));
await check('top-up requires auth before Stripe', '/topup', post({ amount_usd: 20 }), 401, hasError('authentication_required'));
await check('catalog run requires auth before provider', '/run', post({
  slug: 'woven-relationship-book-maker',
  input: {},
}), 401, hasError('authentication_required'));
await check('waitlist rejects invalid email without a write', '/waitlist', post({ email: 'not-an-email' }), 400,
  (body) => body && (body.error === 'invalid email' || body.error === 'invalid_email'));
await check('Clerk webhook rejects unsigned body', '/clerk-webhook', post({ type: 'user.created' }), 401,
  (body) => body && (body.error === 'invalid signature' || body.error === 'invalid webhook signature'));

console.log(`\n${pass} passed, ${fail} failed against ${base}`);
process.exit(fail ? 1 : 0);
