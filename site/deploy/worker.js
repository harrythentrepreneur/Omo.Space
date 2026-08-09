// Cognition — demo API worker (single Cloudflare Worker)
// The "it actually runs" proof for the storefront. One worker, several endpoints:
//
//   POST /api/ugc-script-studio        → UGC ad script from a product link
//   POST /api/meta-ads-analyser        → Meta Ads read/judge/advise (winners, losers, next move)
//   POST /api/product-photo-generator  → listing image shot plan + copy
//   POST /api/checkout                 → Stripe Checkout session {slug, priceUsd, email?}
//
// Env vars (set in Cloudflare dashboard / wrangler secret):
//   LLM_API_KEY  — key for the OpenAI-compatible endpoint below (SECRET)
//   LLM_BASE_URL — default https://opencode.ai/zen/go/v1
//   LLM_MODEL    — default deepseek-v4-flash
//   STRIPE_SECRET_KEY — Stripe secret key (sk_test_…/sk_live_…); without it
//                       /api/checkout returns 501 and the storefront simulates
//                       purchases. Never logged or echoed.
//
// Demo caps (per route, per IP per day; mirror each SKILL.md demo_caps):
//   UGC:   DEMO_MAX_TOKENS_UGC=4000, DEMO_MAX_INPUT_UGC=2000, DEMO_DAILY_CAP_UGC=5
//   META:  DEMO_MAX_TOKENS_META=5000, DEMO_MAX_INPUT_META=20000, DEMO_DAILY_CAP_META=3
//   PHOTO: DEMO_MAX_TOKENS_PHOTO=4000, DEMO_MAX_INPUT_PHOTO=2000, DEMO_DAILY_CAP_PHOTO=5
// Without a BENCH_KV binding, caps are skipped (worker still works, just uncapped).

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

const ROUTES = {
  '/api/ugc-script-studio': handleUgc,
  '/api/meta-ads-analyser': handleMeta,
  '/api/product-photo-generator': handlePhoto,
  '/api/run': handleGenericRun, // any catalog skill: {slug, system_prompt, fields:{...}}
  '/api/checkout': handleCheckout, // Stripe Checkout session: {slug, priceUsd, email?}
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: cors() });
    }
    if (request.method !== 'POST') {
      return json({ error: 'POST only' }, 405, cors());
    }

    const url = new URL(request.url);
    const handler = ROUTES[url.pathname];
    if (!handler) {
      return json({ error: `Unknown route: ${url.pathname}`, routes: Object.keys(ROUTES) }, 404, cors());
    }
    return handler(request, env);
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
// Body: { slug, system_prompt, fields: { key: value, ... }, max_tokens? }
// The storefront sends the skill's prompt + the buyer's input values; the
// worker runs it through the LLM and returns the raw + parsed output. This is
// what lets every catalog skill (100+) be tested in-browser with zero per-skill code.

async function handleGenericRun(request, env) {
  const ip = request.headers.get('CF-Connecting-IP') || 'local';
  const cap = await capCheck(env, 'run', ip, env.DEMO_DAILY_CAP_RUN || 20);
  if (!cap.allowed) {
    return json({ error: 'Free demo limit reached for today. Buy the license to keep going.' }, 429, cors());
  }

  let body;
  try { body = await request.json(); } catch { body = {}; }
  const slug = String(body.slug || '').trim();
  const systemPrompt = String(body.system_prompt || '').trim();
  const fields = body.fields && typeof body.fields === 'object' ? body.fields : {};
  const maxTokens = Number(body.max_tokens || env.DEMO_MAX_TOKENS_RUN || 4000);

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

  try {
    const llm = await callLLM(env, systemPrompt, userPrompt, maxTokens);
    if (llm.error) return json({ error: llm.error }, 502, cors());
    const parsed = stripJson(llm.content);
    await capBump(env, cap.key, cap.used);
    return json({ ok: true, slug, output: parsed || { raw: llm.content }, raw: llm.content }, 200, cors());
  } catch (e) {
    return json({ error: String(e.message || e) }, 500, cors());
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
  if (!slug || !isFinite(priceUsd) || priceUsd < 0) {
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
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };
}

function json(obj, status, headers) {
  return new Response(JSON.stringify(obj), { status, headers });
}
