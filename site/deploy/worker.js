// Omo — demo API worker (single Cloudflare Worker)
// The "it actually runs" proof for the storefront. One worker, several endpoints:
//
//   POST /api/ugc-script-studio        → UGC ad script from a product link
//   POST /api/meta-ads-analyser        → Meta Ads read/judge/advise (winners, losers, next move)
//   POST /api/product-photo-generator  → listing image shot plan + copy
//   POST /api/run                      → generic helper runner {slug, system_prompt, fields};
//                                         with body.user_id it DEBITS the user's credits
//                                         (cost-model run price) and 402s when short
//   POST /api/checkout                 → Stripe Checkout session {slug, priceUsd, email?}
//   GET/POST /api/me?user_id=…         → {balance, api_key, currency, runs} for the dashboard
//   POST /api/topup                    → Stripe Checkout + signed top-up fulfillment
//   POST /api/clerk-webhook            → Clerk webhook: user.created → $10 signup grant
//
// Env vars (set in Cloudflare dashboard / wrangler secret):
//   LLM_API_KEY  — key for the OpenAI-compatible endpoint below (SECRET)
//   LLM_BASE_URL — default https://opencode.ai/zen/go/v1
//   LLM_MODEL    — default deepseek-v4-flash
//   STRIPE_SECRET_KEY — Stripe secret key (sk_test_…/sk_live_…); without it
//                       /api/checkout and /api/topup return 501 and the
//                       storefront simulates. Never logged or echoed.
//   CLERK_WEBHOOK_SECRET — Svix signing secret from the Clerk dashboard; when
//                       set, /api/clerk-webhook verifies the signature.
//   STRIPE_WEBHOOK_SECRET — signing secret for checkout.session.completed
//                       deliveries sent to /api/topup.
//   BALANCE_KEY_SECRET — optional extra entropy for deterministic API keys;
//                       falls back to LLM_API_KEY, then a dev constant.
//   SIGNUP_GRANT_USD  — optional override of the $10 signup grant (tests).
//
// Bindings:
//   BALANCE_DB (D1) — users + runs tables (schema.sql). Without it the worker
//                       runs in MOCK mode: an in-memory Map grants $10 + a
//                       deterministic 'omo_' key per user, so tests and local
//                       dev work with zero infra.
//   BENCH_KV — optional per-IP daily demo caps (skipped without it).
//
// Demo caps (per route, per IP per day; mirror each SKILL.md demo_caps):
//   UGC:   DEMO_MAX_TOKENS_UGC=4000, DEMO_MAX_INPUT_UGC=2000, DEMO_DAILY_CAP_UGC=5
//   META:  DEMO_MAX_TOKENS_META=5000, DEMO_MAX_INPUT_META=20000, DEMO_DAILY_CAP_META=3
//   PHOTO: DEMO_MAX_TOKENS_PHOTO=4000, DEMO_MAX_INPUT_PHOTO=2000, DEMO_DAILY_CAP_PHOTO=5
// Signed-in /api/run calls (body.user_id) are PAID runs — no free-demo cap.

// Pure credit math lives in ./balance.mjs (bundled at deploy time); the cost
// model in ./cost-model.mjs sets the per-run price (5x markup, $0.10 floor).
import { grantSignupCredits, debitForRun, apiKeyFor, topupAmounts } from './balance.mjs';
import { runPrice, llmWorkflow } from './cost-model.mjs';

// ── System prompts (hardened: exact JSON shape, flat string arrays, no fences) ──

const UGC_SYSTEM_PROMPT = `You are UGC Script Studio, a specialist ad-script writer for ecommerce brands.
Turn a product description into a ready-to-film UGC ad script.
Return EXACTLY this JSON shape, with parallel arrays (shot i pairs with caption i):

{
  "hook": "first 2 seconds, stops the scroll",
  "shots": ["shot 1 description with camera notes", "shot 2", "shot 3"],
  "captions": ["caption for shot 1", "caption for shot 2", "caption for shot 3"],
  "cta": "one call to action"
}

HARD RULES:
- shots must be a flat array of STRINGS (one per shot, with camera notes like CU, B-roll, direct-to-camera).
- captions must be a flat array of STRINGS, same length as shots.
- hook and cta are plain strings.
- Never nest objects inside shots or captions.
Rules:
- Write in the requested brand voice: raw (honest, imperfect, first-person), honest, hype (energetic, big), luxury (quiet, premium), or funny.
- Length: 15/30/60 seconds. 15s = 1-2 shots, 30s = 3-5 shots, 60s = up to 8 shots.
- The script must feel like a real person filmed it, not an ad agency.
- Never invent claims about the product; only use what the description supports.
- Output ONLY the JSON object, no markdown fences, no commentary.`;

const META_SYSTEM_PROMPT = `You are the Meta Ads Analyser, a media-buying analyst for ecommerce brands.
Read the ad export, judge each row against the buyer's goal, and advise the next move.
Return EXACTLY this JSON shape:

{
  "verdict": "one plain-language sentence: what's working, what's burning money",
  "winners": ["campaign name — why it wins, with the numbers"],
  "losers": ["campaign name — why it loses, with the numbers"],
  "quick_wins": ["cheap high-leverage change, with the expected effect"],
  "next_move": "the single highest-leverage action for next week"
}

HARD RULES:
- winners, losers, quick_wins must be flat arrays of STRINGS.
- verdict and next_move are plain strings.
- Never nest objects inside the arrays.
Flow (follow in order):
1. READ — normalize spend, impressions, clicks, purchases, revenue per row. Compute ROAS = revenue/spend, CPA = spend/purchases, CTR = clicks/impressions.
2. JUDGE — flag winners (above goal with enough data), losers (spending without returning), and "undecided" (too little data to trust — say so in the verdict, don't force it into a bucket).
3. ADVISE — next move: scale X, kill Y, test Z, or wait for data.
Rules:
- Judge against the requested goal: roas, cpa, ctr, or scale.
- Never invent numbers; only use what the export supports.
- Plain words, no jargon dumps.
- Output ONLY the JSON object, no markdown fences, no commentary.`;

const PHOTO_SYSTEM_PROMPT = `You are the Product Photo Generator, an ecommerce photography director.
Turn a product description (and optional photo URL) into a ready-to-use listing image plan.
Return EXACTLY this JSON shape:

{
  "shot_plan": ["shot 1: angle, background, props, camera note", "shot 2", "shot 3"],
  "background_suggestion": "one background that makes the product the star",
  "caption": "short social caption that converts",
  "listing_copy": "2-3 sentence product listing description"
}

HARD RULES:
- shot_plan must be a flat array of 3-5 STRINGS.
- background_suggestion, caption, and listing_copy are plain strings.
- Never nest objects inside shot_plan.
Flow (follow in order):
1. ANALYZE — what the product is, its key features, who buys it.
2. PLAN — 3-5 shots: angles, backgrounds, props, and which crop to lead with.
3. DELIVER — shot plan, background suggestion, caption, listing copy.
Rules:
- Match the requested style: clean (white/seamless studio), lifestyle (in-context scene), or hero (dramatic lead crop).
- Never invent product features; only use what the description supports.
- Output ONLY the JSON object, no markdown fences, no commentary.`;

// ── Router ─────────────────────────────────────────────────────────────────
// Each route maps to { handler } (POST-only by default) or { handler, methods }
// for routes that accept other verbs (/api/me takes GET for the dashboard).

const ROUTES = {
  '/api/ugc-script-studio': { handler: handleUgc },
  '/api/meta-ads-analyser': { handler: handleMeta },
  '/api/product-photo-generator': { handler: handlePhoto },
  '/api/run': { handler: handleGenericRun }, // any catalog skill: {slug, system_prompt, fields:{...}, user_id?}
  '/api/checkout': { handler: handleCheckout }, // Stripe Checkout session: {slug, priceUsd, email?}
  '/api/me': { handler: handleMe, methods: ['GET', 'POST'] }, // dashboard: balance + api key + usage
  '/api/topup': { handler: handleTopup }, // Stripe Checkout: {user_id, amount_usd}
  '/api/clerk-webhook': { handler: handleClerkWebhook }, // user.created → $10 grant
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: cors() });
    }

    const url = new URL(request.url);
    const route = ROUTES[url.pathname];
    if (!route) {
      return json({ error: `Unknown route: ${url.pathname}`, routes: Object.keys(ROUTES) }, 404, cors());
    }
    const methods = route.methods || ['POST'];
    if (!methods.includes(request.method)) {
      return json({ error: 'Method not allowed', methods }, 405, cors());
    }
    try {
      return await route.handler(request, env, url);
    } catch (e) {
      return json({ error: 'internal_error' }, 500, cors());
    }
  },
};

// ── Route: UGC Script Studio ───────────────────────────────────────────────

async function handleUgc(request, env) {
  const ip = request.headers.get('CF-Connecting-IP') || 'local';
  const cap = await capCheck(env, 'ugc', ip, env.DEMO_DAILY_CAP_UGC || 5);
  if (!cap.allowed) {
    return json({ error: 'Free demo limit reached for today. Buy the license to keep going.' }, 429, cors());
  }

  let body;
  try { body = await request.json(); } catch { body = {}; }
  const product = String(body.product || body.product_url || '').trim();
  const voice = String(body.voice || 'raw').trim();
  const length = Number(body.length || 30);

  if (!product) return json({ error: 'Send a product link or description.' }, 400, cors());
  if (product.length > Number(env.DEMO_MAX_INPUT_UGC || 2000)) {
    return json({ error: 'Product description too long for the free demo.' }, 400, cors());
  }
  if (![15, 30, 60].includes(length)) {
    return json({ error: 'Length must be 15, 30, or 60 seconds.' }, 400, cors());
  }

  try {
    const llm = await callLLM(env, UGC_SYSTEM_PROMPT,
      `Product: ${product}\n\nBrand voice: ${voice}\nLength: ${length} seconds\n\nWrite the UGC ad script now.`,
      Number(env.DEMO_MAX_TOKENS_UGC || 4000));
    if (llm.error) return json({ error: llm.error }, 502, cors());

    const parsed = parseScript(llm.content);
    await capBump(env, cap.key, cap.used);
    return json({ ok: true, script: parsed, raw: llm.content }, 200, cors());
  } catch (e) {
    return json({ error: String(e.message || e) }, 500, cors());
  }
}

// ── Route: Meta Ads Analyser ───────────────────────────────────────────────

const META_GOALS = ['roas', 'cpa', 'ctr', 'scale'];

async function handleMeta(request, env) {
  const ip = request.headers.get('CF-Connecting-IP') || 'local';
  const cap = await capCheck(env, 'meta', ip, env.DEMO_DAILY_CAP_META || 3);
  if (!cap.allowed) {
    return json({ error: 'Free demo limit reached for today. Buy the license to keep going.' }, 429, cors());
  }

  let body;
  try { body = await request.json(); } catch { body = {}; }
  const adsExport = String(body.ads_export || '').trim();
  const goal = String(body.goal || 'roas').trim().toLowerCase();

  if (!adsExport) return json({ error: 'Send an ads_export (CSV paste or text).' }, 400, cors());
  if (adsExport.length > Number(env.DEMO_MAX_INPUT_META || 20000)) {
    return json({ error: 'Ads export too long for the free demo.' }, 400, cors());
  }
  if (!META_GOALS.includes(goal)) {
    return json({ error: `Goal must be one of: ${META_GOALS.join(', ')}.` }, 400, cors());
  }

  try {
    const llm = await callLLM(env, META_SYSTEM_PROMPT,
      `Goal: ${goal}\n\nAds export:\n${adsExport}\n\nRead, judge, and advise now.`,
      Number(env.DEMO_MAX_TOKENS_META || 5000));
    if (llm.error) return json({ error: llm.error }, 502, cors());

    const parsed = parseAds(llm.content);
    await capBump(env, cap.key, cap.used);
    return json({ ok: true, analysis: parsed, raw: llm.content }, 200, cors());
  } catch (e) {
    return json({ error: String(e.message || e) }, 500, cors());
  }
}

// ── Route: Product Photo Generator ─────────────────────────────────────────

const PHOTO_STYLES = ['clean', 'lifestyle', 'hero'];

async function handlePhoto(request, env) {
  const ip = request.headers.get('CF-Connecting-IP') || 'local';
  const cap = await capCheck(env, 'photo', ip, env.DEMO_DAILY_CAP_PHOTO || 5);
  if (!cap.allowed) {
    return json({ error: 'Free demo limit reached for today. Buy the license to keep going.' }, 429, cors());
  }

  let body;
  try { body = await request.json(); } catch { body = {}; }
  const productDescription = String(body.product_description || '').trim();
  const photoUrl = String(body.photo_url || '').trim();
  const style = String(body.style || 'lifestyle').trim().toLowerCase();

  if (!productDescription) return json({ error: 'Send a product_description.' }, 400, cors());
  if (productDescription.length > Number(env.DEMO_MAX_INPUT_PHOTO || 2000)) {
    return json({ error: 'Product description too long for the free demo.' }, 400, cors());
  }
  if (!PHOTO_STYLES.includes(style)) {
    return json({ error: `Style must be one of: ${PHOTO_STYLES.join(', ')}.` }, 400, cors());
  }

  try {
    const llm = await callLLM(env, PHOTO_SYSTEM_PROMPT,
      `Product description: ${productDescription}\nPhoto URL: ${photoUrl || '(none)'}\nStyle: ${style}\n\nPlan the shot list now.`,
      Number(env.DEMO_MAX_TOKENS_PHOTO || 4000));
    if (llm.error) return json({ error: llm.error }, 502, cors());

    const parsed = parsePhoto(llm.content);
    await capBump(env, cap.key, cap.used);
    return json({ ok: true, plan: parsed, raw: llm.content }, 200, cors());
  } catch (e) {
    return json({ error: String(e.message || e) }, 500, cors());
  }
}

// ── Route: Generic skill runner (catalog skills) ───────────────────────────
// Body: { slug, system_prompt, fields: { key: value, ... }, max_tokens?, user_id? }
// The storefront sends the skill's prompt + the buyer's input values; the
// worker runs it through the LLM and returns the raw + parsed output. This is
// what lets every catalog skill (100+) be tested in-browser with zero per-skill code.
//
// CREDITS: when body.user_id is present this becomes a PAID run — the balance
// is checked BEFORE the LLM call (402 {error:'insufficient_balance'} when the
// user is short) and debited at the cost-model run price (5x markup, $0.10
// floor) AFTER a successful run. Anonymous runs stay on the free demo caps.

async function handleGenericRun(request, env) {
  let body;
  try { body = await request.json(); } catch { body = {}; }
  const slug = String(body.slug || '').trim();
  const systemPrompt = String(body.system_prompt || '').trim();
  const fields = body.fields && typeof body.fields === 'object' ? body.fields : {};
  const maxTokens = Number(body.max_tokens || env.DEMO_MAX_TOKENS_RUN || 4000);
  const userId = String(body.user_id || '').trim();

  if (!slug || !systemPrompt) {
    return json({ error: 'Send slug and system_prompt.' }, 400, cors());
  }
  // Flatten fields into the user prompt, rejecting oversized payloads.
  let userPrompt = '';
  for (const [k, v] of Object.entries(fields)) {
    const s = String(v == null ? '' : v).trim();
    if (s.length > Number(env.DEMO_MAX_INPUT_RUN || 3000)) {
      return json({ error: `"${k}" is too long for the free demo.` }, 400, cors());
    }
    userPrompt += `${k}: ${s}\n`;
  }
  if (!userPrompt.trim()) {
    return json({ error: 'Send at least one field value.' }, 400, cors());
  }
  userPrompt += '\nRun the skill now and return your output.';

  // Paid path: check + reserve the run price before spending LLM budget.
  let billing = null;
  let reservedCents = 0;
  let balanceAfterDebit = 0;
  let costUsd = 0;
  if (userId) {
    billing = (await getUserRecord(env, userId)).record;
    costUsd = runPrice(llmWorkflow(systemPrompt, maxTokens));
    reservedCents = Math.round(costUsd * 100);
    const reservation = await reserveRunCredits(env, userId, reservedCents);
    if (!reservation.ok) {
      const check = debitForRun(reservation.balance_cents / 100, costUsd);
      return json({
        error: 'insufficient_balance',
        balance: check.balance,
        cost_usd: check.costUsd,
        shortfall_usd: check.shortfallUsd,
        topup_url: '/dashboard.html',
      }, 402, cors());
    }
    balanceAfterDebit = reservation.balance_cents;
  }

  // Anonymous runs stay capped per IP; paid runs skip the free-demo cap.
  const ip = request.headers.get('CF-Connecting-IP') || 'local';
  const cap = userId ? { allowed: true } : await capCheck(env, 'run', ip, env.DEMO_DAILY_CAP_RUN || 20);
  if (!cap.allowed) {
    return json({ error: 'Free demo limit reached for today. Buy the license to keep going.' }, 429, cors());
  }

  try {
    const llm = await callLLM(env, systemPrompt, userPrompt, maxTokens);
    if (llm.error) {
      if (billing) await refundRunCredits(env, userId, reservedCents);
      return json({ error: llm.error }, 502, cors());
    }
    const parsed = stripJson(llm.content);
    await capBump(env, cap.key, cap.used);
    if (billing) {
      await addRun(env, userId, slug, reservedCents);
      return json({
        ok: true, slug, output: parsed || { raw: llm.content }, raw: llm.content,
        cost_usd: costUsd, balance: +(balanceAfterDebit / 100).toFixed(2),
      }, 200, cors());
    }
    return json({ ok: true, slug, output: parsed || { raw: llm.content }, raw: llm.content }, 200, cors());
  } catch (e) {
    if (billing) await refundRunCredits(env, userId, reservedCents);
    return json({ error: 'run_failed' }, 500, cors());
  }
}

// ── Route: Stripe Checkout session ────────────────────────────────────────
// Body: { slug, priceUsd, email?, mode? } → creates a Stripe Checkout Session
// and returns { url } when the worker has STRIPE_SECRET_KEY set; 501 when not
// configured. The secret key is read from env and NEVER logged or echoed.

async function handleCheckout(request, env) {
  let body;
  try { body = await request.json(); } catch { body = {}; }
  const slug = String(body.slug || '').trim();
  const priceUsd = Number(body.priceUsd);
  if (!slug || !isFinite(priceUsd) || priceUsd <= 0) {
    return json({ error: 'Send slug and priceUsd.' }, 400, cors());
  }

  const secretKey = env.STRIPE_SECRET_KEY;
  if (!secretKey) {
    return json({ error: 'stripe not configured' }, 501, cors());
  }

  const email = String(body.email || '').trim();
  const params = new URLSearchParams();
  params.set('mode', 'payment');
  params.set('success_url', `https://cognition.cv/?purchased=${encodeURIComponent(slug)}`);
  params.set('cancel_url', 'https://cognition.cv/?purchased=cancelled');
  params.set('line_items[0][quantity]', '1');
  params.set('line_items[0][price_data][currency]', 'usd');
  params.set('line_items[0][price_data][product_data][name]', slug);
  params.set('line_items[0][price_data][unit_amount]', String(Math.round(priceUsd * 100)));
  if (email) params.set('customer_email', email);

  try {
    const res = await fetch('https://api.stripe.com/v1/checkout/sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        Authorization: `Bearer ${secretKey}`,
      },
      body: params.toString(),
    });
    if (!res.ok) {
      return json({ error: `stripe error ${res.status}` }, 502, cors());
    }
    const data = await res.json();
    if (!data || !data.url) {
      return json({ error: 'stripe returned no checkout url' }, 502, cors());
    }
    return json({ url: data.url }, 200, cors());
  } catch (e) {
    return json({ error: 'stripe unavailable' }, 502, cors());
  }
}

// ── Route: dashboard /api/me ───────────────────────────────────────────────
// GET /api/me?user_id=…  (POST /api/me {user_id} also works) →
//   { ok, balance: "10.00", balance_usd, balance_cents, currency: "usd",
//     api_key: "omo_…", mock: true|false, runs: [{slug, cost_usd, created_at}] }
// The record is self-provisioned: the first time a user_id appears they get
// the $10 signup grant + a deterministic API key (no double grant on repeat
// visits). With no D1 binding this runs off the in-memory mock store.

async function handleMe(request, env, url) {
  let userId = (url.searchParams && url.searchParams.get('user_id')) || '';
  if (!userId && request.method === 'POST') {
    try {
      const body = await request.json();
      userId = String(body.user_id || '').trim();
    } catch (e) { /* fall through */ }
  }
  if (!userId) return json({ error: 'Send user_id.' }, 400, cors());

  const { record } = await getUserRecord(env, userId);
  const runs = await listRuns(env, userId, 50);
  return json({
    ok: true,
    balance: (record.balance_cents / 100).toFixed(2),
    balance_usd: +(record.balance_cents / 100).toFixed(2),
    balance_cents: record.balance_cents,
    currency: 'usd',
    api_key: record.api_key,
    mock: !env.BALANCE_DB,
    runs: runs.map((r) => ({
      slug: r.slug,
      cost_usd: +(r.cost_cents / 100).toFixed(2),
      created_at: r.created_at,
    })),
  }, 200, cors());
}

// ── Route: credit top-up ───────────────────────────────────────────────────
// Body: { user_id, amount_usd } → Stripe Checkout Session for a credits
// top-up; returns { url } when STRIPE_SECRET_KEY is set, else 501 (the
// dashboard then simulates the top-up in mock mode). Signed Stripe webhook
// deliveries to this endpoint apply paid credits exactly once.

async function handleTopup(request, env) {
  if (request.headers.get('stripe-signature')) {
    return handleStripeTopupWebhook(request, env);
  }

  let body;
  try { body = await request.json(); } catch { body = {}; }
  const userId = String(body.user_id || '').trim();
  const amountUsd = Number(body.amount_usd);
  if (!userId || !topupAmounts().includes(amountUsd)) {
    return json({ error: `Send user_id and amount_usd (${topupAmounts().join(', ')}).` }, 400, cors());
  }

  const secretKey = env.STRIPE_SECRET_KEY;
  if (!secretKey) {
    return json({ error: 'stripe not configured' }, 501, cors());
  }

  await getUserRecord(env, userId); // ensure the account exists for the credits

  const cents = Math.round(amountUsd * 100);
  const params = new URLSearchParams();
  params.set('mode', 'payment');
  params.set('success_url', 'https://omo.best/dashboard.html?topup=success');
  params.set('cancel_url', 'https://omo.best/dashboard.html?topup=cancelled');
  params.set('client_reference_id', userId);
  params.set('metadata[user_id]', userId);
  params.set('metadata[type]', 'credits_topup');
  params.set('metadata[amount_cents]', String(cents));
  params.set('line_items[0][quantity]', '1');
  params.set('line_items[0][price_data][currency]', 'usd');
  params.set('line_items[0][price_data][product_data][name]', 'Omo credits');
  params.set('line_items[0][price_data][unit_amount]', String(cents));

  try {
    const res = await fetch('https://api.stripe.com/v1/checkout/sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        Authorization: `Bearer ${secretKey}`,
      },
      body: params.toString(),
    });
    if (!res.ok) {
      return json({ error: `stripe error ${res.status}` }, 502, cors());
    }
    const data = await res.json();
    if (!data || !data.url) {
      return json({ error: 'stripe returned no checkout url' }, 502, cors());
    }
    return json({ url: data.url }, 200, cors());
  } catch (e) {
    return json({ error: 'stripe unavailable' }, 502, cors());
  }
}

// Stripe sends checkout.session.completed to this same endpoint. A signed,
// paid credits session is applied exactly once, then /api/me reflects it.
async function handleStripeTopupWebhook(request, env) {
  if (!env.STRIPE_WEBHOOK_SECRET) {
    return json({ error: 'stripe webhook not configured' }, 501, cors());
  }

  let raw;
  try { raw = await request.text(); } catch { raw = ''; }
  if (!(await verifyStripeSignature(request.headers, raw, env.STRIPE_WEBHOOK_SECRET))) {
    return json({ error: 'invalid signature' }, 401, cors());
  }

  let event;
  try { event = JSON.parse(raw); } catch {
    return json({ error: 'invalid json' }, 400, cors());
  }
  if (event.type !== 'checkout.session.completed') {
    return json({ ok: true, ignored: true }, 200, cors());
  }

  const session = event.data && event.data.object;
  const metadata = session && session.metadata;
  const userId = String((metadata && metadata.user_id) || (session && session.client_reference_id) || '').trim();
  const amountCents = Number(session && session.amount_total);
  if (!session || session.payment_status !== 'paid' || !session.id || !userId ||
      !metadata || metadata.type !== 'credits_topup' || Number(metadata.amount_cents) !== amountCents ||
      !Number.isInteger(amountCents) || amountCents <= 0) {
    return json({ ok: true, ignored: true }, 200, cors());
  }

  await getUserRecord(env, userId);
  const applied = await creditTopup(env, session.id, userId, amountCents);
  const { record } = await getUserRecord(env, userId);
  return json({
    ok: true,
    applied,
    user_id: userId,
    balance: (record.balance_cents / 100).toFixed(2),
    balance_cents: record.balance_cents,
  }, 200, cors());
}

// ── Route: Clerk webhook ───────────────────────────────────────────────────
// Clerk dashboard → Webhooks → Endpoint URL https://<worker>/api/clerk-webhook,
// event: user.created. On that event we grant the $10 signup credits (INSERT
// OR IGNORE — an existing row keeps its balance, so no double grants, and a
// lazy /api/me provision doesn't get reset by the webhook).
// When CLERK_WEBHOOK_SECRET is set the Svix signature is verified (svix-id /
// svix-timestamp / svix-signature headers, HMAC-SHA256). Without the secret
// (mock/local) validation is skipped.

async function handleClerkWebhook(request, env) {
  let raw;
  try { raw = await request.text(); } catch { raw = ''; }
  let body;
  try { body = JSON.parse(raw); } catch {
    return json({ error: 'invalid json' }, 400, cors());
  }

  const secret = env.CLERK_WEBHOOK_SECRET;
  if (secret && !(await verifySvix(request.headers, raw, secret))) {
    return json({ error: 'invalid signature' }, 401, cors());
  }

  if (body.type !== 'user.created' || !body.data || !body.data.id) {
    return json({ ok: true, ignored: true }, 200, cors());
  }

  const userId = String(body.data.id);
  const { record, created } = await getUserRecord(env, userId);
  return json({
    ok: true,
    granted: created,
    user_id: userId,
    balance: (record.balance_cents / 100).toFixed(2),
    balance_cents: record.balance_cents,
  }, 200, cors());
}

// ── Balance store (D1 when bound, in-memory mock otherwise) ────────────────
// MOCK MODE: with no BALANCE_DB binding every user gets $10 + a deterministic
// 'omo_' key from an in-memory Map, so tests and local dev run with zero
// infra. REAL MODE: D1 (schema.sql) — users (balance_cents, api_key) and runs.

const mockUsers = new Map(); // user_id → { balance_cents, api_key, created_at }
const mockRuns = new Map();  // user_id → [{slug, cost_cents, created_at}]
const mockTopups = new Set(); // Stripe Checkout session ids already credited

function balanceSecret(env) {
  return env.BALANCE_KEY_SECRET || env.LLM_API_KEY || 'omo-dev-secret';
}

function signupGrantCents(env) {
  const override = Number(env.SIGNUP_GRANT_USD);
  const amountUsd = isFinite(override) && override > 0 ? override : grantSignupCredits().amountUsd;
  return Math.round(amountUsd * 100);
}

// Fetch (and lazily provision) a user's balance record. Returns
// { record: {balance_cents, api_key, created_at}, created: boolean }.
async function getUserRecord(env, userId) {
  const now = new Date().toISOString();
  const apiKey = apiKeyFor(userId, balanceSecret(env));

  if (env.BALANCE_DB) {
    const existing = await env.BALANCE_DB
      .prepare('SELECT balance_cents, api_key, created_at FROM users WHERE user_id = ?')
      .bind(userId).first();
    if (existing) return { record: existing, created: false };
    const insert = await env.BALANCE_DB
      .prepare('INSERT OR IGNORE INTO users (user_id, balance_cents, api_key, created_at) VALUES (?, ?, ?, ?)')
      .bind(userId, signupGrantCents(env), apiKey, now).run();
    const row = await env.BALANCE_DB
      .prepare('SELECT balance_cents, api_key, created_at FROM users WHERE user_id = ?')
      .bind(userId).first();
    return {
      record: row || { balance_cents: signupGrantCents(env), api_key: apiKey, created_at: now },
      created: !!(insert.meta && insert.meta.changes),
    };
  }

  if (!mockUsers.has(userId)) {
    mockUsers.set(userId, { balance_cents: signupGrantCents(env), api_key: apiKey, created_at: now });
    return { record: mockUsers.get(userId), created: true };
  }
  return { record: mockUsers.get(userId), created: false };
}

async function reserveRunCredits(env, userId, costCents) {
  if (env.BALANCE_DB) {
    const result = await env.BALANCE_DB
      .prepare('UPDATE users SET balance_cents = balance_cents - ? WHERE user_id = ? AND balance_cents >= ?')
      .bind(costCents, userId, costCents).run();
    const { record } = await getUserRecord(env, userId);
    return { ok: !!(result.meta && result.meta.changes), balance_cents: record.balance_cents };
  }
  const rec = mockUsers.get(userId);
  if (!rec || rec.balance_cents < costCents) {
    return { ok: false, balance_cents: rec ? rec.balance_cents : 0 };
  }
  rec.balance_cents -= costCents;
  return { ok: true, balance_cents: rec.balance_cents };
}

async function refundRunCredits(env, userId, costCents) {
  if (!costCents) return;
  if (env.BALANCE_DB) {
    await env.BALANCE_DB
      .prepare('UPDATE users SET balance_cents = balance_cents + ? WHERE user_id = ?')
      .bind(costCents, userId).run();
    return;
  }
  const rec = mockUsers.get(userId);
  if (rec) rec.balance_cents += costCents;
}

async function creditTopup(env, sessionId, userId, amountCents) {
  if (env.BALANCE_DB) {
    const now = new Date().toISOString();
    const results = await env.BALANCE_DB.batch([
      env.BALANCE_DB
        .prepare('INSERT OR IGNORE INTO stripe_topups (session_id, user_id, amount_cents, applied, created_at) VALUES (?, ?, ?, 0, ?)')
        .bind(sessionId, userId, amountCents, now),
      env.BALANCE_DB
        .prepare('UPDATE users SET balance_cents = balance_cents + ? WHERE user_id = ? AND EXISTS (SELECT 1 FROM stripe_topups WHERE session_id = ? AND user_id = ? AND amount_cents = ? AND applied = 0)')
        .bind(amountCents, userId, sessionId, userId, amountCents),
      env.BALANCE_DB
        .prepare('UPDATE stripe_topups SET applied = 1 WHERE session_id = ? AND user_id = ? AND amount_cents = ? AND applied = 0')
        .bind(sessionId, userId, amountCents),
    ]);
    return !!(results[1] && results[1].meta && results[1].meta.changes);
  }
  if (mockTopups.has(sessionId)) return false;
  mockTopups.add(sessionId);
  const rec = mockUsers.get(userId);
  if (rec) rec.balance_cents += amountCents;
  return true;
}

async function addRun(env, userId, slug, costCents) {
  const now = new Date().toISOString();
  if (env.BALANCE_DB) {
    await env.BALANCE_DB
      .prepare('INSERT INTO runs (user_id, slug, cost_cents, created_at) VALUES (?, ?, ?, ?)')
      .bind(userId, slug, costCents, now).run();
    return;
  }
  const list = mockRuns.get(userId) || [];
  list.unshift({ slug, cost_cents: costCents, created_at: now });
  mockRuns.set(userId, list);
}

async function listRuns(env, userId, limit) {
  if (env.BALANCE_DB) {
    const res = await env.BALANCE_DB
      .prepare('SELECT slug, cost_cents, created_at FROM runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?')
      .bind(userId, limit || 50).all();
    return res.results || [];
  }
  return (mockRuns.get(userId) || []).slice(0, limit || 50);
}

// ── Clerk (Svix) webhook signature verification ────────────────────────────
// Signature header: space-separated v1,<base64> entries over
// `${svix-id}.${svix-timestamp}.${rawBody}` with HMAC-SHA256.

async function verifySvix(headers, rawBody, secret) {
  try {
    const id = headers.get('svix-id');
    const ts = headers.get('svix-timestamp');
    const sig = headers.get('svix-signature');
    if (!id || !ts || !sig) return false;

    const nowSec = Math.floor(Date.now() / 1000);
    const tsNum = Number(ts);
    if (!isFinite(tsNum) || Math.abs(nowSec - tsNum) > 300) return false; // ±5 min

    const encodedSecret = String(secret).startsWith('whsec_') ? String(secret).slice(6) : String(secret);
    const keyBytes = base64Bytes(encodedSecret);
    const mac = await hmacSha256(keyBytes, `${id}.${ts}.${rawBody}`);
    const expected = bytesToBase64(mac);
    return sig.split(/\s+/).some((part) => {
      const comma = part.indexOf(',');
      return comma > 0 && part.slice(0, comma) === 'v1' && timingSafeEqual(part.slice(comma + 1), expected);
    });
  } catch (e) {
    return false;
  }
}

// Stripe signature: t=<unix>,v1=<hex> over `${t}.${rawBody}`.
async function verifyStripeSignature(headers, rawBody, secret) {
  try {
    const header = headers.get('stripe-signature');
    if (!header) return false;
    let timestamp = '';
    const signatures = [];
    header.split(',').forEach((part) => {
      const pair = part.split('=');
      if (pair[0] === 't') timestamp = pair.slice(1).join('=');
      if (pair[0] === 'v1') signatures.push(pair.slice(1).join('='));
    });
    const tsNum = Number(timestamp);
    if (!timestamp || !isFinite(tsNum) || Math.abs(Math.floor(Date.now() / 1000) - tsNum) > 300) return false;
    const mac = await hmacSha256(new TextEncoder().encode(secret), `${timestamp}.${rawBody}`);
    const expected = bytesToHex(mac);
    return signatures.some((signature) => timingSafeEqual(signature, expected));
  } catch (e) {
    return false;
  }
}

async function hmacSha256(keyBytes, message) {
  if (typeof crypto === 'undefined' || !crypto.subtle) throw new Error('crypto unavailable');
  const key = await crypto.subtle.importKey(
    'raw', keyBytes, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']
  );
  return new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message)));
}

function base64Bytes(value) {
  const binary = atob(value);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

function bytesToBase64(bytes) {
  let binary = '';
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary);
}

function bytesToHex(bytes) {
  return Array.from(bytes).map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

function timingSafeEqual(left, right) {
  if (left.length !== right.length) return false;
  let mismatch = 0;
  for (let i = 0; i < left.length; i++) mismatch |= left.charCodeAt(i) ^ right.charCodeAt(i);
  return mismatch === 0;
}

// ── Shared helpers ─────────────────────────────────────────────────────────

async function callLLM(env, systemPrompt, userPrompt, maxTokens) {
  const res = await fetch(`${env.LLM_BASE_URL || 'https://opencode.ai/zen/go/v1'}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${env.LLM_API_KEY}`,
    },
    body: JSON.stringify({
      model: env.LLM_MODEL || 'deepseek-v4-flash',
      max_tokens: maxTokens,
      temperature: 0.8,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    return { error: `LLM error ${res.status}: ${errText.slice(0, 200)}` };
  }
  const data = await res.json();
  return { content: data.choices?.[0]?.message?.content || '' };
}

async function capCheck(env, route, ip, dailyCap) {
  if (!env.BENCH_KV) return { key: null, used: 0, allowed: true };
  const today = new Date().toISOString().slice(0, 10);
  const key = `demo:${route}:${ip}:${today}`;
  const used = Number((await env.BENCH_KV.get(key)) || 0);
  return { key, used, allowed: used < Number(dailyCap || 0) };
}

async function capBump(env, key, used) {
  if (!env.BENCH_KV || !key) return;
  await env.BENCH_KV.put(key, String(used + 1), { expirationTtl: 86400 });
}

// ── Normalizers (all handle: fenced JSON, prose-wrapped JSON, garbage) ─────

function stripJson(raw) {
  // Strip markdown fences if the model wrapped them anyway, then find the JSON object.
  let cleaned = String(raw || '').replace(/^```(?:json)?/m, '').replace(/```$/m, '').trim();
  const start = cleaned.indexOf('{');
  const end = cleaned.lastIndexOf('}');
  if (start >= 0 && end > start) cleaned = cleaned.slice(start, end + 1);
  try {
    return JSON.parse(cleaned);
  } catch {
    return null;
  }
}

function parseScript(raw) {
  const obj = stripJson(raw);
  if (!obj) return { raw };
  // Nested variant: shots = [{shot, camera_notes, captions}] → flatten to parallel arrays.
  if (Array.isArray(obj.shots) && obj.shots.length && typeof obj.shots[0] === 'object') {
    const shots = [];
    const captions = [];
    for (const s of obj.shots) {
      shots.push([s.shot, s.camera_notes].filter(Boolean).join(' — '));
      if (s.captions) captions.push(s.captions);
    }
    if (!Array.isArray(obj.captions)) obj.captions = captions;
    obj.shots = shots;
  }
  if (!Array.isArray(obj.captions)) obj.captions = [];
  return obj;
}

function parseAds(raw) {
  const obj = stripJson(raw);
  if (!obj) return { raw };
  obj.verdict = typeof obj.verdict === 'string' ? obj.verdict : '';
  obj.winners = toStrArray(obj.winners);
  obj.losers = toStrArray(obj.losers);
  obj.quick_wins = toStrArray(obj.quick_wins);
  obj.next_move = typeof obj.next_move === 'string' ? obj.next_move : '';
  return obj;
}

function parsePhoto(raw) {
  const obj = stripJson(raw);
  if (!obj) return { raw };
  obj.shot_plan = toStrArray(obj.shot_plan);
  obj.background_suggestion = typeof obj.background_suggestion === 'string' ? obj.background_suggestion : '';
  obj.caption = typeof obj.caption === 'string' ? obj.caption : '';
  obj.listing_copy = typeof obj.listing_copy === 'string' ? obj.listing_copy : '';
  return obj;
}

function toStrArray(v) {
  if (!Array.isArray(v)) return [];
  // Coerce any non-string members (numbers, stray objects) to strings so the
  // storefront can always render a flat list.
  return v.map((x) => (typeof x === 'string' ? x : JSON.stringify(x)));
}

function cors() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };
}

function json(obj, status, headers) {
  return new Response(JSON.stringify(obj), { status, headers });
}
