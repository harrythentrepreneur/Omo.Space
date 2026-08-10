// Omo — demo API worker (single Cloudflare Worker)
// The "it actually runs" proof for the storefront. One worker, several endpoints:
//
//   POST /api/ugc-script-studio        → UGC ad script from a product link
//   POST /api/meta-ads-analyser        → Meta Ads read/judge/advise (winners, losers, next move)
//   POST /api/product-photo-generator  → listing image shot plan + copy
//   POST /api/run                      → catalog helper runner {slug, fields}; real mode
//                                         authenticates, requires idempotency, and debits credits
//   POST /api/checkout                 → Stripe Checkout session {slug, email?}
//   GET/POST /api/me                   → {balance, api_key, currency, runs} for the dashboard
//   POST /api/topup                    → Stripe Checkout + signed top-up fulfillment
//   POST /api/clerk-webhook            → Clerk webhook: user.created → $5 signup grant
//
// Env vars (set in Cloudflare dashboard / wrangler secret):
//   LLM_API_KEY  — key for the OpenAI-compatible endpoint below (SECRET)
//   LLM_BASE_URL — default https://opencode.ai/zen/go/v1
//   LLM_MODEL    — default deepseek-v4-flash
//   STRIPE_SECRET_KEY — Stripe secret key (sk_test_…/sk_live_…); without it
//                       /api/checkout and /api/topup return 501 and the
//                       storefront simulates. Never logged or echoed.
//   CLERK_PUBLISHABLE_KEY — Clerk pk_test_/pk_live_ key; its encoded Frontend
//                       API host is used to fetch and cache Clerk JWKS.
//   CLERK_WEBHOOK_SECRET — Svix signing secret from the Clerk dashboard.
//   STRIPE_WEBHOOK_SECRET — signing secret for checkout.session.completed
//                       deliveries sent to /api/topup.
//   BALANCE_KEY_SECRET — optional extra entropy for deterministic API keys;
//                       falls back to LLM_API_KEY, then a dev constant.
//   SIGNUP_GRANT_USD  — optional override of the $5 signup grant (tests).
//   NEON_DATABASE_URL — pooled Neon Postgres connection string (recommended).
//
// Bindings:
//   BALANCE_DB (D1) — optional fallback after Neon. Without either database the
//                       worker runs in MOCK mode: an in-memory Map grants $5 + a
//                       deterministic 'omo_' key per user, so tests and local
//                       dev work with zero infra.
//   BENCH_KV — optional per-IP daily demo caps (skipped without it).
//
// Demo caps (per route, per IP per day; mirror each SKILL.md demo_caps):
//   UGC:   DEMO_MAX_TOKENS_UGC=4000, DEMO_MAX_INPUT_UGC=2000, DEMO_DAILY_CAP_UGC=5
//   META:  DEMO_MAX_TOKENS_META=5000, DEMO_MAX_INPUT_META=20000, DEMO_DAILY_CAP_META=3
//   PHOTO: DEMO_MAX_TOKENS_PHOTO=4000, DEMO_MAX_INPUT_PHOTO=2000, DEMO_DAILY_CAP_PHOTO=5
// Real mode starts when Clerk or a durable database is configured. It requires
// Clerk JWT auth for account routes (or an omo_ API key for /api/run). With
// neither configured, mock mode preserves the localStorage-backed demo flow.

// Pure credit math lives in ./balance.mjs (bundled at deploy time); the cost
// model in ./cost-model.mjs sets the per-run price (5x markup, $0.10 floor).
import { Pool } from '@neondatabase/serverless';
import { grantSignupCredits, debitForRun, apiKeyFor, topupAmounts, MIN_TOPUP_USD } from './balance.mjs';
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

const LISTING_COPY_SYSTEM_PROMPT = `You write marketplace listing copy from buyer-supplied product facts.
Return EXACTLY this JSON shape: {"title":"SEO-aware title","bullets":["benefit 1","benefit 2","benefit 3"],"description":"2-3 sentence description"}.
HARD RULES: bullets is a flat array of STRINGS; never invent claims; output ONLY the JSON object.`;

// Server-owned catalog. The Instagram tuples mirror site/ig-workflows.js and
// site/ig-more.js, but intentionally include only runtime-safe fields. Client
// system_prompt, model, max_tokens, workflow, and price values are ignored in
// real mode. Checkout also resolves its one-time price from this same map.
const CATALOG_ROWS = [
  ['ugc-script-studio', 'UGC Script Studio', 39, 0.10, 'deepseek-v4-flash', 4000, UGC_SYSTEM_PROMPT],
  ['meta-ads-analyser', 'Meta Ads Analyser', 49, 0.10, 'deepseek-v4-flash', 5000, META_SYSTEM_PROMPT],
  ['product-photo-generator', 'Product Photo Generator', 29, 0.10, 'deepseek-v4-flash', 4000, PHOTO_SYSTEM_PROMPT],
  ['listing-copy-engine', 'Listing Copy Engine', 19, 0.10, 'deepseek-v4-flash', 600, LISTING_COPY_SYSTEM_PROMPT],
  ['ugc-actor-maker', 'UGC Actor Maker', 49, 0.15, 'deepseek-v4-flash', 700, UGC_SYSTEM_PROMPT],
  ['ugc-heygen-editor', 'UGC HeyGen Editor', 39, 0.15, 'deepseek-v4-flash', 700, UGC_SYSTEM_PROMPT],
  ['tiktok-ad-script-writer', 'TikTok Ad Script Writer', 29, 0.10, 'deepseek-v4-flash', 700, UGC_SYSTEM_PROMPT],
  ['youtube-ads-video-editor', 'YouTube Ads Video Editor', 49, 0.15, 'deepseek-v4-flash', 700, UGC_SYSTEM_PROMPT],
  ['shopify-product-story', 'Shopify Product Story', 39, 0.10, 'deepseek-v4-flash', 700, LISTING_COPY_SYSTEM_PROMPT],
  ['email-flow-copilot', 'Email Flow Copilot', 49, 0.10, 'deepseek-v4-flash', 800, 'You write ecommerce lifecycle email sequences using only supplied product and offer facts. Return JSON with subject_lines, emails, and next_steps. Output JSON only.'],
  ['arcads-node-ugc-builder', 'Arcads Node UGC Builder', 49, 1.40, 'deepseek-v4-flash', 400, 'You turn a product brief into scene prompts for UGC video generation. Return EXACTLY this JSON shape: {"scene_prompts":["prompt 1","prompt 2","prompt 3"],"hook":"first 2 seconds","cta":"one call to action"} HARD RULES: scene_prompts is a flat array of STRINGS, never nest objects, never invent claims, output ONLY the JSON object.'],
  ['product-link-to-meta-ugc-ad', 'Product Link → Meta UGC Ad', 49, 0.60, 'deepseek-v4-flash', 300, 'You summarize an ecommerce product page for ad creation. Return EXACTLY this JSON shape: {"product":"what it is","claims":["supported claims only"],"audience":"who buys it"} HARD RULES: claims is a flat array of STRINGS, never nest objects, only use what the description supports, output ONLY the JSON object.'],
  ['one-photo-ecom-creative-factory', 'One-Photo Creative Factory', 39, 1.10, 'deepseek-v4-flash', 400, 'You turn a product photo description into a creative variant matrix. Return EXACTLY this JSON shape: {"variants":[{"angle":"shot angle","background":"background","usage":"PDP or paid social"}]} HARD RULES: variants is a flat array of objects with STRING fields only, never nest deeper, output ONLY the JSON object.'],
  ['shopify-pics-to-description-bulk', 'Shopify Pics → Descriptions (Bulk)', 49, 0.30, 'deepseek-v4-flash', 500, 'You generate SEO product listings from image descriptions. Return EXACTLY this JSON shape: {"title":"SEO-aware, under 150 chars","description":"2-3 sentences that sell","meta_title":"under 60 chars","meta_description":"under 160 chars"} HARD RULES: all fields are plain STRINGS, never nest objects, output ONLY the JSON object.'],
  ['gpt-image-seedance-product-ad', 'Cinematic Product Ad (GPT Image + Seedance)', 49, 1.10, 'deepseek-v4-flash', 400, 'You plan cinematic product ad shots. Return EXACTLY this JSON shape: {"shotlist":["shot 1: angle, props, motion note"],"style":"visual style","transitions":["transition notes"]} HARD RULES: shotlist and transitions are flat arrays of STRINGS, never nest objects, output ONLY the JSON object.'],
  ['consistent-character-ugc', 'Consistent Character UGC System', 49, 0.90, 'deepseek-v4-flash', 400, 'You build a character sheet and product talking points for AI UGC ads. Return JSON with character_sheet, talking_points as a flat string array, and cta. Never invent claims. Output JSON only.'],
  ['realistic-ugc-character-4step', 'Realistic AI UGC Character (4-Step)', 49, 0.90, 'deepseek-v4-flash', 400, 'You write talking-character UGC scripts. Return JSON with hook, lines as a flat array of 3-5 strings, and cta. Never invent claims. Output JSON only.'],
  ['prompt-to-ugc-ad-maxfusion-seedance-2-0', 'Prompt-to-UGC Ad (Maxfusion + Seedance 2.0)', 29, 0.60, 'deepseek-v4-flash', 500, 'You turn supplied product facts into a realistic UGC video-ad plan. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['cinematic-ai-ugc-scene-builder', 'Cinematic AI UGC Scene Builder', 29, 0.60, 'deepseek-v4-flash', 500, 'You turn a supplied product or promotion into a cinematic UGC scene plan. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['ai-ugc-ad-prompt-guide', 'AI UGC Ad Prompt + Guide', 29, 0.60, 'deepseek-v4-flash', 500, 'You create a ready-to-use AI UGC ad prompt and concise production guide from supplied facts. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['product-image-cinematic-ad-seedance-2-0', 'Product Image → Cinematic Ad (Seedance 2.0)', 49, 1.00, 'deepseek-v4-flash', 500, 'You turn a supplied product-image description into a 15-second cinematic ad plan. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['claude-seo-skill-replaces-2k-mo-agency', 'Claude SEO Skill', 29, 0.10, 'deepseek-v4-flash', 500, 'You produce a practical SEO audit and action plan from supplied site facts. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['shopify-agentic-storefronts-ai-seo-playbook', 'Shopify Agentic Storefronts + AI SEO Playbook', 29, 0.30, 'deepseek-v4-flash', 500, 'You produce a Shopify AI-discovery and product-page optimization playbook from supplied store facts. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['shopify-ai-stack-rebuy-klaviyo-ai-tidio', 'Shopify AI Stack', 49, 1.05, 'deepseek-v4-flash', 500, 'You design a Shopify automation plan for Rebuy, Klaviyo, and Tidio from supplied store facts. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['shopify-agentic-plan-sellers-setup', 'Shopify Agentic Plan Sellers Setup', 29, 0.30, 'deepseek-v4-flash', 500, 'You create a Shopify Agentic Plan seller setup from supplied merchant facts. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['ai-brand-commercial-production-seedance-2-0-k', 'AI Brand Commercial Production', 29, 0.60, 'deepseek-v4-flash', 500, 'You create an AI brand-commercial storyboard and production plan from supplied campaign facts. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['ai-ugc-tutorial-german-comment-to-get', 'AI UGC Tutorial (German)', 29, 0.10, 'deepseek-v4-flash', 500, 'You create a German-language AI UGC tutorial from supplied product facts. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['ai-ugc-creator-guide-fully-ai-generated-ads', 'AI UGC Creator Guide', 29, 0.60, 'deepseek-v4-flash', 500, 'You create an AI UGC creator guide and ad plan from supplied brand facts. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['batch-content-repurposing-system-transcripts-', 'Batch Content Repurposing System', 39, 0.75, 'deepseek-v4-flash', 500, 'You turn supplied transcripts into a batch content-repurposing plan and platform captions. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['kling-ai-higgsfield-viral-video-workflow', 'Kling AI + Higgsfield Viral Video Workflow', 29, 0.60, 'deepseek-v4-flash', 500, 'You create a cinematic short-video workflow from supplied campaign facts. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
  ['ai-readable-product-page-optimization', 'AI-Readable Product Page Optimization', 39, 0.90, 'deepseek-v4-flash', 500, 'You optimize supplied product-page facts for accurate AI discovery and recommendation. Return JSON with output as a flat array of strings and summary as one string. Never invent facts. Output JSON only.'],
];

const SERVER_CATALOG = new Map(CATALOG_ROWS.map((row) => {
  const [slug, name, licensePriceUsd, runPriceUsd, model, maxTokens, systemPrompt] = row;
  return [slug, {
    slug, name, licensePriceCents: Math.round(licensePriceUsd * 100),
    runPriceCents: Math.round(runPriceUsd * 100), model, maxTokens, systemPrompt,
    workflow: { steps: [{ type: 'llm', role: 'main', model, max_output: maxTokens, system: systemPrompt }] },
  }];
}));

const MAX_TOPUP_USD_DEFAULT = 1000;
const USER_ID_RE = /^user_[A-Za-z0-9_-]{1,80}$/;
const IDEMPOTENCY_KEY_RE = /^[A-Za-z0-9._:-]{8,128}$/;

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
  '/api/clerk-webhook': { handler: handleClerkWebhook }, // user.created → $5 grant
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors(request, env) });
    }

    const url = new URL(request.url);
    const route = ROUTES[url.pathname];
    if (!route) {
      return json({ error: `Unknown route: ${url.pathname}`, routes: Object.keys(ROUTES) }, 404, cors(request, env));
    }
    const methods = route.methods || ['POST'];
    if (!methods.includes(request.method)) {
      return json({ error: 'Method not allowed', methods }, 405, cors(request, env));
    }
    try {
      return applyCors(await route.handler(request, env, url), request, env);
    } catch (e) {
      return json({ error: 'internal_error' }, 500, cors(request, env));
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
// Real mode accepts {slug, fields, idempotency_key?}; prompt, model, token cap,
// workflow, and price come only from SERVER_CATALOG. Mock mode keeps the old
// client-prompt fallback so the zero-key storefront demo remains functional.

async function handleGenericRun(request, env) {
  let body;
  try { body = await request.json(); } catch { body = {}; }
  const slug = String(body.slug || '').trim();
  const fields = body.fields && typeof body.fields === 'object' && !Array.isArray(body.fields) ? body.fields : {};
  const real = isRealMode(env);
  const listing = SERVER_CATALOG.get(slug);
  if (!slug) return json({ error: 'Send slug.' }, 400, cors());
  if (real && !listing) return json({ error: 'unknown_catalog_slug' }, 404, cors());

  let userId = '';
  let authMethod = 'demo';
  if (real) {
    const auth = await authenticateAccount(request, env, true);
    if (!auth.ok) return json({ error: auth.error }, auth.status, cors());
    userId = auth.userId;
    authMethod = auth.method;
  } else {
    userId = validUserId(body.user_id) ? String(body.user_id).trim() : '';
  }

  const systemPrompt = listing ? listing.systemPrompt : String(body.system_prompt || '').trim();
  const maxTokens = listing
    ? listing.maxTokens
    : boundedInt(body.max_tokens, 1, 8000, Number(env.DEMO_MAX_TOKENS_RUN || 4000));
  const model = listing ? listing.model : (env.LLM_MODEL || 'deepseek-v4-flash');
  if (!systemPrompt) return json({ error: 'Send slug and system_prompt.' }, 400, cors());

  // Flatten fields into the user prompt, rejecting oversized payloads.
  let userPrompt = '';
  for (const [k, v] of Object.entries(fields)) {
    if (!/^[A-Za-z0-9 _.-]{1,80}$/.test(k)) return json({ error: 'Invalid field name.' }, 400, cors());
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

  // Real calls must have a durable, account-scoped idempotency key. A row is
  // claimed before debit, so concurrent retries cannot both spend credits.
  let idempotencyKey = '';
  let requestHash = '';
  let runRequest = null;
  if (real) {
    idempotencyKey = String(request.headers.get('idempotency-key') || body.idempotency_key || '').trim();
    if (!IDEMPOTENCY_KEY_RE.test(idempotencyKey)) {
      return json({ error: 'invalid_idempotency_key' }, 400, cors());
    }
    requestHash = await sha256Hex(stableStringify({ slug, fields }));
    await getUserRecord(env, userId);
    await reconcileStaleReservations(env, userId);
    runRequest = await claimRunRequest(
      env, userId, idempotencyKey, requestHash, slug,
      listing.runPriceCents, makeId('run')
    );
    if (!runRequest.created) return replayRunResponse(runRequest.row, requestHash);
  }

  // Paid path: reserve the catalog price before spending LLM budget.
  let billing = null;
  let reservedCents = 0;
  let balanceAfterDebit = 0;
  let costUsd = 0;
  let runId = runRequest ? runRequest.row.run_id : '';
  if (userId) {
    billing = (await getUserRecord(env, userId)).record;
    reservedCents = listing
      ? listing.runPriceCents
      : Math.round(runPrice(llmWorkflow(systemPrompt, maxTokens, model)) * 100);
    costUsd = reservedCents / 100;
    if (!runId) runId = makeId('run');
    const reservation = await reserveRunCredits(env, userId, reservedCents, runId);
    if (!reservation.ok) {
      const check = debitForRun(reservation.balance_cents / 100, costUsd);
      const response = {
        error: 'insufficient_balance',
        message: 'You need a little more Omo credit for this run. Top up from $5 and keep going.',
        balance: check.balance,
        cost_usd: check.costUsd,
        shortfall_usd: check.shortfallUsd,
        minimum_topup_usd: MIN_TOPUP_USD,
        suggested_amounts_usd: topupAmounts(),
        topup_url: '/dashboard.html?topup=needed',
        run_id: runId,
        state: 'refunded',
      };
      if (runRequest) await finishRunRequest(env, runId, 'refunded', response, 402);
      return json(response, 402, cors());
    }
    balanceAfterDebit = reservation.balance_cents;
    if (runRequest) await setRunRunning(env, runId);
  }

  // Anonymous runs stay capped per IP; paid runs skip the free-demo cap.
  const ip = request.headers.get('CF-Connecting-IP') || 'local';
  const cap = userId ? { allowed: true } : await capCheck(env, 'run', ip, env.DEMO_DAILY_CAP_RUN || 20);
  if (!cap.allowed) {
    return json({ error: 'Free demo limit reached for today. Buy the license to keep going.' }, 429, cors());
  }

  let settled = false;
  try {
    const llm = await callLLM(env, systemPrompt, userPrompt, maxTokens, model);
    if (llm.error) {
      if (billing) await refundRunCredits(env, userId, reservedCents, runId);
      const response = { error: llm.error, run_id: runId || undefined, state: runRequest ? 'refunded' : undefined };
      if (runRequest) await finishRunRequest(env, runId, 'refunded', response, 502);
      settled = true;
      return json(response, 502, cors());
    }
    const parsed = stripJson(llm.content);
    await capBump(env, cap.key, cap.used);
    if (billing) {
      const result = {
        ok: true, slug, output: parsed || { raw: llm.content }, raw: llm.content,
        run_id: runId, state: 'succeeded', auth: authMethod,
        cost_usd: costUsd, balance: +(balanceAfterDebit / 100).toFixed(2),
      };
      if (balanceAfterDebit === 0) {
        result.message = 'That used your remaining credits. Top up from $5 whenever you are ready to run another helper.';
        result.minimum_topup_usd = MIN_TOPUP_USD;
        result.suggested_amounts_usd = topupAmounts();
        result.topup_url = '/dashboard.html?topup=needed';
      }
      if (runRequest) await finishRunRequest(env, runId, 'succeeded', result, 200);
      settled = true;
      await addRun(env, userId, slug, reservedCents, runId);
      return json(result, 200, cors());
    }
    return json({ ok: true, slug, output: parsed || { raw: llm.content }, raw: llm.content }, 200, cors());
  } catch (e) {
    if (billing && !settled) await refundRunCredits(env, userId, reservedCents, runId);
    const response = { error: 'run_failed', run_id: runId || undefined, state: runRequest ? 'refunded' : undefined };
    if (runRequest && !settled) await finishRunRequest(env, runId, 'refunded', response, 500);
    return json(response, 500, cors());
  }
}

// ── Route: Stripe Checkout session ────────────────────────────────────────
// Body: { slug, email? } → creates a Stripe Checkout Session
// and returns { url } when the worker has STRIPE_SECRET_KEY set; 501 when not
// configured. Slug, product name, and price are server-catalog values.

async function handleCheckout(request, env) {
  let body;
  try { body = await request.json(); } catch { body = {}; }
  const slug = String(body.slug || '').trim();
  const listing = SERVER_CATALOG.get(slug);
  if (!slug) return json({ error: 'Send slug.' }, 400, cors());
  if (!listing) return json({ error: 'unknown_catalog_slug' }, 404, cors());

  const secretKey = env.STRIPE_SECRET_KEY;
  if (!secretKey) {
    return json({ error: 'stripe not configured' }, 501, cors());
  }

  const email = String(body.email || '').trim();
  if (email.length > 254) return json({ error: 'invalid email' }, 400, cors());
  const params = new URLSearchParams();
  params.set('mode', 'payment');
  params.set('success_url', `https://omo.best/?purchased=${encodeURIComponent(slug)}`);
  params.set('cancel_url', 'https://omo.best/?purchased=cancelled');
  params.set('line_items[0][quantity]', '1');
  params.set('line_items[0][price_data][currency]', 'usd');
  params.set('line_items[0][price_data][product_data][name]', listing.name);
  params.set('line_items[0][price_data][unit_amount]', String(listing.licensePriceCents));
  params.set('metadata[type]', 'catalog_license');
  params.set('metadata[slug]', slug);
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
// Real: GET/POST /api/me with a Clerk bearer token. Mock: the legacy
// ?user_id=… / {user_id} form remains available for the local demo. →
//   { ok, balance: "10.00", balance_usd, balance_cents, currency: "usd",
//     api_key: "omo_…", mock: true|false, runs: [{slug, cost_usd, created_at}] }
// The record is self-provisioned: the first time a user_id appears they get
// the $5 signup grant + a deterministic API key (no double grant on repeat
// visits). Neon is preferred, then D1, then the in-memory mock store.

async function handleMe(request, env, url) {
  let userId = '';
  if (isRealMode(env)) {
    const auth = await authenticateAccount(request, env, false);
    if (!auth.ok) return json({ error: auth.error }, auth.status, cors());
    userId = auth.userId;
  } else {
    userId = (url.searchParams && url.searchParams.get('user_id')) || '';
    if (!userId && request.method === 'POST') {
      try {
        const body = await request.json();
        userId = String(body.user_id || '').trim();
      } catch (e) { /* fall through */ }
    }
  }
  if (!userId) return json({ error: 'Send user_id.' }, 400, cors());
  if (!validUserId(userId)) return json({ error: 'invalid user_id' }, 400, cors());

  const { record } = await getUserRecord(env, userId);
  const runs = await listRuns(env, userId, 50);
  return json({
    ok: true,
    balance: (record.balance_cents / 100).toFixed(2),
    balance_usd: +(record.balance_cents / 100).toFixed(2),
    balance_cents: record.balance_cents,
    currency: 'usd',
    api_key: record.api_key,
    mock: databaseKind(env) === 'mock',
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
  const real = isRealMode(env);
  let userId = '';
  if (real) {
    const auth = await authenticateAccount(request, env, false);
    if (!auth.ok) return json({ error: auth.error }, auth.status, cors());
    userId = auth.userId;
  } else {
    userId = String(body.user_id || '').trim();
  }

  const minTopupUsd = boundedNumber(env.MIN_TOPUP_USD, 1, MAX_TOPUP_USD_DEFAULT, MIN_TOPUP_USD);
  const maxTopupUsd = boundedNumber(env.MAX_TOPUP_USD, minTopupUsd, 100000, MAX_TOPUP_USD_DEFAULT);
  const amountUsd = body.amount_usd;
  const amountInCents = typeof amountUsd === 'number' ? amountUsd * 100 : NaN;
  const cents = Number.isSafeInteger(amountInCents) ? amountInCents : 0;
  const validAmount = cents >= minTopupUsd * 100 && cents <= maxTopupUsd * 100;
  if (!validUserId(userId) || !validAmount) {
    return json({
      error: `Send a numeric amount_usd from $${minTopupUsd.toFixed(2)} to $${maxTopupUsd.toFixed(2)} (up to two decimals).`,
      minimum_topup_usd: minTopupUsd,
      maximum_topup_usd: maxTopupUsd,
      suggested_amounts_usd: topupAmounts(),
    }, 400, cors());
  }

  const secretKey = env.STRIPE_SECRET_KEY;
  if (!secretKey) {
    return json({ error: 'stripe not configured' }, 501, cors());
  }

  await getUserRecord(env, userId); // ensure the account exists for the credits

  const params = new URLSearchParams();
  params.set('mode', 'payment');
  params.set('success_url', 'https://omo.best/dashboard.html?topup=success');
  params.set('cancel_url', 'https://omo.best/dashboard.html?topup=cancelled');
  params.set('client_reference_id', userId);
  params.set('metadata[user_id]', userId);
  params.set('metadata[type]', 'credits_topup');
  params.set('metadata[amount_cents]', String(cents));
  params.set('metadata[currency]', 'usd');
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
    if (!data || !data.url || (real && !data.id)) {
      return json({ error: 'stripe returned no checkout url' }, 502, cors());
    }
    if (real) await recordPendingTopup(env, data.id, userId, cents, 'usd');
    return json({ url: data.url, session_id: data.id || undefined }, 200, cors());
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

  if (!event.id) return json({ error: 'missing event id' }, 400, cors());

  await getUserRecord(env, userId);
  const applied = await creditTopup(env, event.id, session.id, userId, amountCents);
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
// event: user.created. On that event we grant the $5 signup credits (INSERT
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

// ── Balance store (Neon → D1 → in-memory mock) ─────────────────────────────
// Neon uses a small, process-wide serverless pool and named prepared queries.
// D1 remains supported for existing deployments. With neither configured,
// tests and local demos use an in-memory $5 account and the same transitions.

let neonPool = null;
let neonPoolUrl = '';
const mockUsers = new Map();
const mockRuns = new Map();
const mockLedger = new Map();
const mockTopups = new Set();
const mockStripeEvents = new Set();

function neonDatabaseUrl(env) {
  if (env && env.NEON_DATABASE_URL) return String(env.NEON_DATABASE_URL).trim();
  try {
    if (typeof process !== 'undefined' && process.env && process.env.NEON_DATABASE_URL) {
      return String(process.env.NEON_DATABASE_URL).trim();
    }
  } catch (e) { /* edge runtimes may not expose process */ }
  return '';
}

function databaseKind(env) {
  if (neonDatabaseUrl(env)) return 'neon';
  if (env && env.BALANCE_DB) return 'd1';
  return 'mock';
}

function getNeonPool(env) {
  const url = neonDatabaseUrl(env);
  if (!url) return null;
  if (!neonPool || neonPoolUrl !== url) {
    neonPool = new Pool({
      connectionString: url,
      max: 4,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
      allowExitOnIdle: true,
    });
    neonPoolUrl = url;
  }
  return neonPool;
}

function prepared(name, text, values) {
  return { name, text, values: values || [] };
}

function balanceSecret(env) {
  return env.BALANCE_KEY_SECRET || env.LLM_API_KEY || 'omo-dev-secret';
}

function signupGrantCents(env) {
  const override = Number(env.SIGNUP_GRANT_USD);
  const amountUsd = isFinite(override) && override > 0 ? override : grantSignupCredits().amountUsd;
  return Math.round(amountUsd * 100);
}

function makeId(prefix) {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return `${prefix}_${crypto.randomUUID().replace(/-/g, '')}`;
    }
  } catch (e) { /* deterministic uniqueness is not required in mock tests */ }
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
}

function mockLedgerEntry(eventId, userId, kind, amountCents, balanceCents, referenceId, now) {
  if (mockLedger.has(eventId)) return false;
  mockLedger.set(eventId, {
    event_id: eventId, user_id: userId, kind, amount_cents: amountCents,
    balance_cents: balanceCents, reference_id: referenceId, created_at: now,
  });
  return true;
}

async function insertD1Ledger(env, values) {
  try {
    await env.BALANCE_DB
      .prepare('INSERT OR IGNORE INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)')
      .bind(...values).run();
  } catch (e) { /* legacy D1 schemas keep working until schema.sql is reapplied */ }
}

// Fetch (and lazily provision) a user's balance record. The unique user row
// and signup ledger event make the $5 grant safe under concurrent requests.
async function getUserRecord(env, userId) {
  const now = new Date().toISOString();
  const apiKey = apiKeyFor(userId, balanceSecret(env));
  const grantCents = signupGrantCents(env);

  if (databaseKind(env) === 'neon') {
    const client = await getNeonPool(env).connect();
    try {
      await client.query('BEGIN');
      const inserted = await client.query(prepared(
        'omo-user-create-v1',
        'INSERT INTO users (user_id, balance_cents, api_key, created_at) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO NOTHING RETURNING balance_cents, api_key, created_at',
        [userId, grantCents, apiKey, now]
      ));
      const created = inserted.rowCount === 1;
      if (created) {
        await client.query(prepared(
          'omo-ledger-insert-v1',
          'INSERT INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT (event_id) DO NOTHING',
          [`signup:${userId}`, userId, 'signup_grant', grantCents, grantCents, userId, now]
        ));
      }
      const selected = created ? inserted : await client.query(prepared(
        'omo-user-select-v1',
        'SELECT balance_cents, api_key, created_at FROM users WHERE user_id = $1',
        [userId]
      ));
      await client.query('COMMIT');
      return { record: selected.rows[0], created };
    } catch (e) {
      try { await client.query('ROLLBACK'); } catch (rollbackError) {}
      throw e;
    } finally {
      client.release();
    }
  }

  if (databaseKind(env) === 'd1') {
    const existing = await env.BALANCE_DB
      .prepare('SELECT balance_cents, api_key, created_at FROM users WHERE user_id = ?')
      .bind(userId).first();
    if (existing) return { record: existing, created: false };
    const insert = await env.BALANCE_DB
      .prepare('INSERT OR IGNORE INTO users (user_id, balance_cents, api_key, created_at) VALUES (?, ?, ?, ?)')
      .bind(userId, grantCents, apiKey, now).run();
    const created = !!(insert.meta && insert.meta.changes);
    if (created) {
      await insertD1Ledger(env, [`signup:${userId}`, userId, 'signup_grant', grantCents, grantCents, userId, now]);
    }
    const row = await env.BALANCE_DB
      .prepare('SELECT balance_cents, api_key, created_at FROM users WHERE user_id = ?')
      .bind(userId).first();
    return { record: row || { balance_cents: grantCents, api_key: apiKey, created_at: now }, created };
  }

  if (!mockUsers.has(userId)) {
    const record = { balance_cents: grantCents, api_key: apiKey, created_at: now };
    mockUsers.set(userId, record);
    mockLedgerEntry(`signup:${userId}`, userId, 'signup_grant', grantCents, grantCents, userId, now);
    return { record, created: true };
  }
  return { record: mockUsers.get(userId), created: false };
}

async function reserveRunCredits(env, userId, costCents, runId) {
  const ledgerId = `run:${runId}:debit`;
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    const client = await getNeonPool(env).connect();
    try {
      await client.query('BEGIN');
      const claim = await client.query(prepared(
        'omo-ledger-debit-claim-v1',
        'INSERT INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES ($1, $2, $3, $4, 0, $5, $6) ON CONFLICT (event_id) DO NOTHING RETURNING event_id',
        [ledgerId, userId, 'run_debit', -costCents, runId, now]
      ));
      if (!claim.rowCount) {
        const duplicate = await client.query(prepared(
          'omo-ledger-select-v1', 'SELECT balance_cents FROM credits_ledger WHERE event_id = $1', [ledgerId]
        ));
        await client.query('COMMIT');
        return { ok: true, balance_cents: duplicate.rows[0] ? duplicate.rows[0].balance_cents : 0 };
      }
      const updated = await client.query(prepared(
        'omo-user-reserve-v1',
        'UPDATE users SET balance_cents = balance_cents - $1 WHERE user_id = $2 AND balance_cents >= $1 RETURNING balance_cents',
        [costCents, userId]
      ));
      if (!updated.rowCount) {
        await client.query(prepared(
          'omo-ledger-delete-v1', 'DELETE FROM credits_ledger WHERE event_id = $1', [ledgerId]
        ));
        const current = await client.query(prepared(
          'omo-user-balance-v1', 'SELECT balance_cents FROM users WHERE user_id = $1', [userId]
        ));
        await client.query('COMMIT');
        return { ok: false, balance_cents: current.rows[0] ? current.rows[0].balance_cents : 0 };
      }
      const balanceCents = updated.rows[0].balance_cents;
      await client.query(prepared(
        'omo-ledger-balance-v1', 'UPDATE credits_ledger SET balance_cents = $1 WHERE event_id = $2',
        [balanceCents, ledgerId]
      ));
      await client.query('COMMIT');
      return { ok: true, balance_cents: balanceCents };
    } catch (e) {
      try { await client.query('ROLLBACK'); } catch (rollbackError) {}
      throw e;
    } finally { client.release(); }
  }
  if (databaseKind(env) === 'd1') {
    try {
      const duplicate = await env.BALANCE_DB.prepare('SELECT balance_cents FROM credits_ledger WHERE event_id = ?').bind(ledgerId).first();
      if (duplicate) return { ok: true, balance_cents: duplicate.balance_cents };
    } catch (e) { /* legacy D1 schema */ }
    const result = await env.BALANCE_DB
      .prepare('UPDATE users SET balance_cents = balance_cents - ? WHERE user_id = ? AND balance_cents >= ?')
      .bind(costCents, userId, costCents).run();
    const { record } = await getUserRecord(env, userId);
    const ok = !!(result.meta && result.meta.changes);
    if (ok) await insertD1Ledger(env, [ledgerId, userId, 'run_debit', -costCents, record.balance_cents, runId, now]);
    return { ok, balance_cents: record.balance_cents };
  }
  const rec = mockUsers.get(userId);
  if (mockLedger.has(ledgerId)) return { ok: true, balance_cents: rec ? rec.balance_cents : 0 };
  if (!rec || rec.balance_cents < costCents) return { ok: false, balance_cents: rec ? rec.balance_cents : 0 };
  rec.balance_cents -= costCents;
  mockLedgerEntry(ledgerId, userId, 'run_debit', -costCents, rec.balance_cents, runId, now);
  return { ok: true, balance_cents: rec.balance_cents };
}

async function refundRunCredits(env, userId, costCents, runId) {
  if (!costCents) return;
  const ledgerId = `run:${runId}:refund`;
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    const client = await getNeonPool(env).connect();
    try {
      await client.query('BEGIN');
      const inserted = await client.query(prepared(
        'omo-ledger-refund-claim-v1',
        'INSERT INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES ($1, $2, $3, $4, 0, $5, $6) ON CONFLICT (event_id) DO NOTHING RETURNING event_id',
        [ledgerId, userId, 'run_refund', costCents, runId, now]
      ));
      if (!inserted.rowCount) { await client.query('COMMIT'); return; }
      const updated = await client.query(prepared(
        'omo-user-refund-v1',
        'UPDATE users SET balance_cents = balance_cents + $1 WHERE user_id = $2 RETURNING balance_cents',
        [costCents, userId]
      ));
      await client.query(prepared(
        'omo-ledger-balance-v1', 'UPDATE credits_ledger SET balance_cents = $1 WHERE event_id = $2',
        [updated.rows[0].balance_cents, ledgerId]
      ));
      await client.query('COMMIT');
      return;
    } catch (e) {
      try { await client.query('ROLLBACK'); } catch (rollbackError) {}
      throw e;
    } finally { client.release(); }
  }
  if (databaseKind(env) === 'd1') {
    try {
      const duplicate = await env.BALANCE_DB.prepare('SELECT event_id FROM credits_ledger WHERE event_id = ?').bind(ledgerId).first();
      if (duplicate) return;
    } catch (e) { /* legacy D1 schema */ }
    await env.BALANCE_DB.prepare('UPDATE users SET balance_cents = balance_cents + ? WHERE user_id = ?').bind(costCents, userId).run();
    const { record } = await getUserRecord(env, userId);
    await insertD1Ledger(env, [ledgerId, userId, 'run_refund', costCents, record.balance_cents, runId, now]);
    return;
  }
  if (mockLedger.has(ledgerId)) return;
  const rec = mockUsers.get(userId);
  if (rec) {
    rec.balance_cents += costCents;
    mockLedgerEntry(ledgerId, userId, 'run_refund', costCents, rec.balance_cents, runId, now);
  }
}

async function creditTopup(env, stripeEventId, sessionId, userId, amountCents) {
  const now = new Date().toISOString();
  const ledgerId = `stripe:${stripeEventId}`;
  if (databaseKind(env) === 'neon') {
    const client = await getNeonPool(env).connect();
    try {
      await client.query('BEGIN');
      const event = await client.query(prepared(
        'omo-stripe-event-create-v1',
        'INSERT INTO stripe_events (event_id, session_id, user_id, amount_cents, applied, created_at) VALUES ($1, $2, $3, $4, 0, $5) ON CONFLICT (event_id) DO NOTHING RETURNING event_id',
        [stripeEventId, sessionId, userId, amountCents, now]
      ));
      if (!event.rowCount) { await client.query('COMMIT'); return false; }
      const topup = await client.query(prepared(
        'omo-stripe-topup-create-v1',
        'INSERT INTO stripe_topups (session_id, user_id, amount_cents, applied, created_at) VALUES ($1, $2, $3, 0, $4) ON CONFLICT (session_id) DO NOTHING RETURNING session_id',
        [sessionId, userId, amountCents, now]
      ));
      if (!topup.rowCount) {
        await client.query(prepared(
          'omo-stripe-event-applied-v1', 'UPDATE stripe_events SET applied = 1 WHERE event_id = $1', [stripeEventId]
        ));
        await client.query('COMMIT');
        return false;
      }
      const updated = await client.query(prepared(
        'omo-user-topup-v1',
        'UPDATE users SET balance_cents = balance_cents + $1 WHERE user_id = $2 RETURNING balance_cents',
        [amountCents, userId]
      ));
      const balanceCents = updated.rows[0].balance_cents;
      await client.query(prepared(
        'omo-ledger-insert-v1',
        'INSERT INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT (event_id) DO NOTHING',
        [ledgerId, userId, 'topup', amountCents, balanceCents, sessionId, now]
      ));
      await client.query(prepared(
        'omo-stripe-topup-applied-v1', 'UPDATE stripe_topups SET applied = 1 WHERE session_id = $1', [sessionId]
      ));
      await client.query(prepared(
        'omo-stripe-event-applied-v1', 'UPDATE stripe_events SET applied = 1 WHERE event_id = $1', [stripeEventId]
      ));
      await client.query('COMMIT');
      return true;
    } catch (e) {
      try { await client.query('ROLLBACK'); } catch (rollbackError) {}
      throw e;
    } finally { client.release(); }
  }
  if (databaseKind(env) === 'd1') {
    let tracksEvents = false;
    try {
      const event = await env.BALANCE_DB
        .prepare('INSERT OR IGNORE INTO stripe_events (event_id, session_id, user_id, amount_cents, applied, created_at) VALUES (?, ?, ?, ?, 0, ?)')
        .bind(stripeEventId, sessionId, userId, amountCents, now).run();
      const row = await env.BALANCE_DB.prepare('SELECT applied FROM stripe_events WHERE event_id = ?').bind(stripeEventId).first();
      tracksEvents = true;
      if ((!event.meta || !event.meta.changes) && row && row.applied) return false;
    } catch (e) { /* old D1 schemas remain idempotent by Checkout session id */ }
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
    const applied = !!(results[1] && results[1].meta && results[1].meta.changes);
    if (tracksEvents) {
      await env.BALANCE_DB.prepare('UPDATE stripe_events SET applied = 1 WHERE event_id = ?').bind(stripeEventId).run();
    }
    if (applied) {
      const { record } = await getUserRecord(env, userId);
      await insertD1Ledger(env, [ledgerId, userId, 'topup', amountCents, record.balance_cents, sessionId, now]);
    }
    return applied;
  }
  if (mockStripeEvents.has(stripeEventId) || mockTopups.has(sessionId)) return false;
  mockStripeEvents.add(stripeEventId);
  mockTopups.add(sessionId);
  const rec = mockUsers.get(userId);
  if (rec) {
    rec.balance_cents += amountCents;
    mockLedgerEntry(ledgerId, userId, 'topup', amountCents, rec.balance_cents, sessionId, now);
  }
  return true;
}

async function addRun(env, userId, slug, costCents, runId) {
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    await getNeonPool(env).query(prepared(
      'omo-run-insert-v1',
      'INSERT INTO runs (user_id, slug, cost_cents, created_at) VALUES ($1, $2, $3, $4)',
      [userId, slug, costCents, now]
    ));
    return;
  }
  if (databaseKind(env) === 'd1') {
    await env.BALANCE_DB.prepare('INSERT INTO runs (user_id, slug, cost_cents, created_at) VALUES (?, ?, ?, ?)').bind(userId, slug, costCents, now).run();
    return;
  }
  const list = mockRuns.get(userId) || [];
  list.unshift({ run_id: runId, slug, cost_cents: costCents, created_at: now });
  mockRuns.set(userId, list);
}

async function listRuns(env, userId, limit) {
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-runs-list-v1',
      'SELECT slug, cost_cents, created_at FROM runs WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2',
      [userId, limit || 50]
    ));
    return result.rows || [];
  }
  if (databaseKind(env) === 'd1') {
    const res = await env.BALANCE_DB.prepare('SELECT slug, cost_cents, created_at FROM runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?').bind(userId, limit || 50).all();
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
