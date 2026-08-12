// Omo — demo API worker (single Cloudflare Worker)
// The "it actually runs" proof for the storefront. One worker, several endpoints:
//
//   POST /api/ugc-script-studio        → UGC ad script from a product link
//   POST /api/meta-ads-analyser        → Meta Ads read/judge/advise (winners, losers, next move)
//   POST /api/product-photo-generator  → listing image shot plan + copy
//   POST /api/run                      → catalog helper runner {slug, fields}; real mode
//                                         authenticates, requires idempotency, and debits credits
//   POST /api/checkout                 → guest Stripe Checkout {slug, email?}
//   POST /api/waitlist                 → public waitlist signup {email, source?}
//   POST /api/submit                   → authenticated creator Markdown intake
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
//   DEMELLO_MODAL_BEARER — private Modal API bearer (SECRET, required for the
//                       japanese-style-story-video runner).
//   DEMELLO_MODAL_URL / DEMELLO_RELEASE_HASH — optional pinned release
//                       overrides; defaults match the deployed 245304c8f988 app.
//   DEMELLO_MAX_COST_USD — provider/compute ceiling, default 0.003.
//   DEMELLO_EXPECTED_RUN_SECONDS — derived-progress horizon, default 90.
//   DEMELLO_RUN_TIMEOUT_SECONDS — terminal refund timeout, default 1300.
//   DEMELLO_PROGRESS_WEBHOOK_SECRET — optional independent checkpoint bearer.
//   HOSTED_MODAL_PROXY_TOKEN_ID / HOSTED_MODAL_PROXY_TOKEN_SECRET — shared
//     Modal workspace Proxy Token pair for generated hosted-skill endpoints.
//     The legacy WOVEN_* names remain a temporary backwards-compatible fallback.
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
import { handleMcpRequest } from './mcp-server.mjs';
import { HOSTED_MODAL_SKILL_ROWS, HOSTED_SERVER_CATALOG_ROWS } from './hosted-skills.generated.mjs';

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

const DEMELLO_SLUG = 'japanese-style-story-video';
const DEMELLO_STYLE = 'sumi-e-awake-v3';
const DEMELLO_DEFAULT_ENDPOINT = 'https://harrythentrepreneur--omo-demello-awake-245304c8f988-api.modal.run';
const DEMELLO_DEFAULT_RELEASE_HASH = 'sha256:245304c8f98839bf6ac570c3c09224fe839041dbc793f3fb7f7afb3eb475259e';
const DEMELLO_QUOTED_RUN_CENTS = 10;
const DEMELLO_PAID_TRAFFIC_READY = false;
const DEMELLO_PHASES = ['reserved', 'running', 'transcribing', 'directing', 'generating', 'assembling', 'delivered', 'failed'];
const DEMELLO_PHASE_RANK = new Map(DEMELLO_PHASES.map((phase, index) => [phase, index]));
const HOSTED_MODAL_SKILLS = new Map(HOSTED_MODAL_SKILL_ROWS);

// Server-owned catalog. The Instagram tuples mirror site/ig-workflows.js and
// site/ig-more.js, but intentionally include only runtime-safe fields. Client
// system_prompt, model, max_tokens, workflow, and price values are ignored in
// real mode. Checkout also resolves its one-time price from this same map.
const CATALOG_ROWS = [
  ['ugc-script-studio', 'UGC Script Studio', 39, 0.10, 'deepseek-v4-flash', 4000, UGC_SYSTEM_PROMPT],
  ['meta-ads-analyser', 'Meta Ads Analyser', 49, 0.10, 'deepseek-v4-flash', 5000, META_SYSTEM_PROMPT],
  ['product-photo-generator', 'Product Photo Generator', 29, 0.10, 'deepseek-v4-flash', 4000, PHOTO_SYSTEM_PROMPT],
  ['listing-copy-engine', 'Listing Copy Engine', 19, 0.10, 'deepseek-v4-flash', 600, LISTING_COPY_SYSTEM_PROMPT],
  [DEMELLO_SLUG, 'Japanese Style Story Video', 29, 0.10, 'deepseek-v4-flash', 500, 'Turn supplied audio into a vertical sumi-e drawing animation. This listing is executed by its pinned Modal release, not by this prompt.'],
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
  ...HOSTED_SERVER_CATALOG_ROWS,
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
const MAX_SUBMISSION_BYTES = 200 * 1024;
const USER_ID_RE = /^user_[A-Za-z0-9_-]{1,80}$/;
const IDEMPOTENCY_KEY_RE = /^[A-Za-z0-9._:-]{8,128}$/;
const STRIPE_CHECKOUT_API_VERSION = '2025-09-30.clover';
const OMO_CHECKOUT_LOGO_URL = 'https://omo.space/logo-sweet-pastel.svg';
const OMO_CHECKOUT_ICON_URL = 'https://omo.space/favicon-512.png';

// Checkout Session branding is request-scoped in Clover. Supplying every
// visual field prevents this shared Stripe account's PhonicsMaker defaults
// from leaking into Omo's hosted Checkout page; the Account is never mutated.
function applyOmoCheckoutBranding(params) {
  params.set('locale', 'auto');
  params.set('submit_type', 'pay');
  params.set('branding_settings[display_name]', 'Omo');
  params.set('branding_settings[background_color]', '#F8F7F5');
  params.set('branding_settings[button_color]', '#17352C');
  params.set('branding_settings[border_style]', 'rounded');
  params.set('branding_settings[font_family]', 'nunito');
  params.set('branding_settings[logo][type]', 'url');
  params.set('branding_settings[logo][url]', OMO_CHECKOUT_LOGO_URL);
  params.set('branding_settings[icon][type]', 'url');
  params.set('branding_settings[icon][url]', OMO_CHECKOUT_ICON_URL);
}

function stripeCheckoutHeaders(secretKey) {
  return {
    'Content-Type': 'application/x-www-form-urlencoded',
    Authorization: `Bearer ${secretKey}`,
    'Stripe-Version': STRIPE_CHECKOUT_API_VERSION,
  };
}

function purchaseCancelUrl(request, slug) {
  const workflowUrl = `https://omo.space/workflow.html?slug=${encodeURIComponent(slug)}`;
  try {
    const referer = new URL(String(request.headers.get('referer') || ''));
    if (referer.origin !== 'https://omo.space') return workflowUrl;
    if (referer.pathname === '/dashboard.html') return 'https://omo.space/dashboard.html';
    if (referer.pathname === '/' || referer.pathname === '/index.html') return 'https://omo.space/';
  } catch {}
  return workflowUrl;
}

// ── Router ─────────────────────────────────────────────────────────────────
// Each route maps to { handler } (POST-only by default) or { handler, methods }
// for routes that accept other verbs (/api/me takes GET for the dashboard).

const ROUTES = {
  '/api/ugc-script-studio': { handler: handleUgc },
  '/api/meta-ads-analyser': { handler: handleMeta },
  '/api/product-photo-generator': { handler: handlePhoto },
  '/api/run': { handler: handleGenericRun }, // any catalog skill: {slug, system_prompt, fields:{...}, user_id?}
  '/api/checkout': { handler: handleCheckout }, // Guest Stripe Checkout: {slug, email?}; client price is ignored
  '/api/waitlist': { handler: handleWaitlist }, // Public waitlist signup: {email, source?}
  '/api/submit': { handler: handleSubmission }, // Creator queue: {name, content, visibility:'public'}
  '/api/me': { handler: handleMe, methods: ['GET', 'POST'] }, // dashboard: balance + api key + usage
  '/api/topup': { handler: handleTopup }, // Stripe Checkout: {user_id, amount_usd}
  '/api/clerk-webhook': { handler: handleClerkWebhook }, // user.created → $5 grant
};

function dynamicRoute(pathname) {
  const progress = /^\/api\/run\/(run_[A-Za-z0-9_-]{4,91})\/progress$/.exec(pathname);
  if (progress) return { handler: handleRunProgressWebhook, methods: ['POST'], params: { runId: progress[1] } };
  const status = /^\/api\/run\/(run_[A-Za-z0-9_-]{4,91})$/.exec(pathname);
  if (status) return { handler: handleRunStatus, methods: ['GET'], params: { runId: status[1] } };
  return null;
}

async function handleWorkerFetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: cors(request, env) });
    }

    const url = new URL(request.url);
    if (url.pathname === '/mcp') {
      // Keep MCP a client of the exact REST contract without a same-zone
      // network loop. An explicit OMO_API service binding still wins when the
      // MCP module is deployed separately.
      const mcpEnv = {
        ...env,
        OMO_API: env.OMO_API || { fetch: (nestedRequest) => handleWorkerFetch(nestedRequest, env) },
      };
      return handleMcpRequest(request, mcpEnv);
    }
    const route = ROUTES[url.pathname] || dynamicRoute(url.pathname);
    if (!route) {
      return json({ error: `Unknown route: ${url.pathname}`, routes: Object.keys(ROUTES) }, 404, cors(request, env));
    }
    const methods = route.methods || ['POST'];
    if (!methods.includes(request.method)) {
      return json({ error: 'Method not allowed', methods }, 405, cors(request, env));
    }
    try {
      return applyCors(await route.handler(request, env, url, route.params || {}), request, env);
    } catch (e) {
      const body = { error: 'internal_error' };
      if (env.DEBUG_ERRORS === 'true') body.detail = String(e && e.message || e).slice(0, 200);
      return json(body, 500, cors(request, env));
    }
}

export default { fetch: handleWorkerFetch };

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
  const isDemello = slug === DEMELLO_SLUG;
  const hosted = HOSTED_MODAL_SKILLS.get(slug) || null;
  const isHosted = Boolean(hosted);
  // Hosted workflows can spend Modal/provider budget and are never anonymous,
  // including in otherwise zero-config local mode.
  const real = isRealMode(env) || isDemello || isHosted;
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

  let demelloInput = null;
  let demelloInputNotice = '';
  if (isDemello) {
    const configError = demelloConfigError(env);
    if (configError) return json({ error: configError }, 503, cors());
    const normalized = normalizeDemelloInput(fields);
    if (normalized.error) return json({ error: normalized.error, detail: normalized.detail }, 400, cors());
    demelloInput = normalized.input;
    demelloInputNotice = normalized.input_notice || '';
  }
  let hostedInput = null;
  if (isHosted) {
    const configError = hostedModalConfigError(env, hosted);
    if (configError) return json({ error: configError }, 503, cors());
    const candidate = body.input && typeof body.input === 'object' && !Array.isArray(body.input)
      ? body.input : fields;
    const errors = validateSchemaValue(candidate, hosted.input_schema);
    if (errors.length) return json({ error: 'invalid_hosted_input', details: errors.slice(0, 8) }, 422, cors());
    hostedInput = candidate;
  }

  const systemPrompt = listing ? listing.systemPrompt : String(body.system_prompt || '').trim();
  const maxTokens = listing
    ? listing.maxTokens
    : boundedInt(body.max_tokens, 1, 8000, Number(env.DEMO_MAX_TOKENS_RUN || 4000));
  const model = listing ? listing.model : (env.LLM_MODEL || 'deepseek-v4-flash');
  if (!systemPrompt) return json({ error: 'Send slug and system_prompt.' }, 400, cors());

  // Flatten fields into the user prompt, rejecting oversized payloads. The
  // de Mello branch validates and hashes a typed server-owned input instead.
  let userPrompt = '';
  if (!isDemello && !isHosted) {
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
  }

  // Real calls must have a durable, account-scoped idempotency key. A row is
  // claimed before debit, so concurrent retries cannot both spend credits.
  let idempotencyKey = '';
  let requestHash = '';
  let runRequest = null;
  const runCostCents = isDemello && !DEMELLO_PAID_TRAFFIC_READY
    ? 0
    : (isHosted ? Number(hosted.run_price_cents) : (listing ? listing.runPriceCents : 0));
  if (real) {
    idempotencyKey = String(request.headers.get('idempotency-key') || body.idempotency_key || '').trim();
    if (!IDEMPOTENCY_KEY_RE.test(idempotencyKey)) {
      return json({ error: 'invalid_idempotency_key' }, 400, cors());
    }
    requestHash = await sha256Hex(stableStringify(isDemello
      ? { slug, input: demelloInput, input_notice: demelloInputNotice }
      : { slug, input: isHosted ? hostedInput : fields }));
    await getUserRecord(env, userId);
    await reconcileStaleReservations(env, userId);
    runRequest = await claimRunRequest(
      env, userId, idempotencyKey, requestHash, slug,
      runCostCents, makeId('run')
    );
    if (!runRequest.created) return replayRunResponse(env, runRequest.row, requestHash);
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
      ? runCostCents
      : Math.round(runPrice(llmWorkflow(systemPrompt, maxTokens, model)) * 100);
    costUsd = reservedCents / 100;
    if (!runId) runId = makeId('run');
    const reservation = reservedCents === 0
      ? { ok: true, balance_cents: billing.balance_cents }
      : await reserveRunCredits(env, userId, reservedCents, runId);
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
        topup_url: '/billing.html?topup=needed',
        run_id: runId,
        state: 'refunded',
      };
      if (runRequest) await finishRunRequest(env, runId, 'refunded', response, 402);
      return json(response, 402, cors());
    }
    balanceAfterDebit = reservation.balance_cents;
    if (runRequest && (isDemello || isHosted)) {
      await putRunProgress(env, {
        run_id: runId, user_id: userId, phase: 'reserved', progress_pct: 1,
        progress_source: 'derived', modal_status: 'reserved',
        modal_status_url: isHosted ? hostedModalEndpoint(env, hosted) : demelloModalStatusUrl(env, runId),
        input_notice: demelloInputNotice,
      });
    }
    if (runRequest) await setRunRunning(env, runId);
  }

  if (isDemello) {
    return dispatchDemelloRun(env, {
      runRequest, runId, userId, idempotencyKey, demelloInput,
      demelloInputNotice, reservedCents, costUsd, balanceAfterDebit, authMethod,
    });
  }
  if (isHosted) {
    return dispatchHostedModalRun(env, hosted, {
      runRequest, runId, userId, hostedInput, costUsd, balanceAfterDebit, authMethod,
    });
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
      const response = { error: llm.error, run_id: runId || undefined, state: runRequest ? 'refunded' : undefined };
      const ownsRefund = runRequest ? await finishRunRequest(env, runId, 'refunded', response, 502) : true;
      if (billing && ownsRefund) await refundRunCredits(env, userId, reservedCents, runId);
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
        result.topup_url = '/billing.html?topup=needed';
      }
      if (runRequest) await finishRunRequest(env, runId, 'succeeded', result, 200);
      settled = true;
      if (!runRequest) await addRun(env, userId, slug, reservedCents, runId);
      return json(result, 200, cors());
    }
    return json({ ok: true, slug, output: parsed || { raw: llm.content }, raw: llm.content }, 200, cors());
  } catch (e) {
    const response = { error: 'run_failed', run_id: runId || undefined, state: runRequest ? 'refunded' : undefined };
    if (!settled) {
      const ownsRefund = runRequest ? await finishRunRequest(env, runId, 'refunded', response, 500) : true;
      if (billing && ownsRefund) await refundRunCredits(env, userId, reservedCents, runId);
    }
    return json(response, 500, cors());
  }
}

// ── Generated hosted skills / schema-driven Modal runs ────────────────────

function validateSchemaValue(value, schema, path = '$') {
  const errors = [];
  if (!schema || typeof schema !== 'object') return errors;
  if (Object.prototype.hasOwnProperty.call(schema, 'const') && value !== schema.const) {
    return [`${path} must equal the fixed value.`];
  }
  if (Array.isArray(schema.enum) && !schema.enum.some((item) => item === value)) {
    return [`${path} must be one of the allowed values.`];
  }
  const type = schema.type;
  if (type === 'object') {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return [`${path} must be an object.`];
    const properties = schema.properties || {};
    for (const required of schema.required || []) {
      if (!Object.prototype.hasOwnProperty.call(value, required)) errors.push(`${path}.${required} is required.`);
    }
    if (schema.additionalProperties === false) {
      for (const key of Object.keys(value)) if (!Object.prototype.hasOwnProperty.call(properties, key)) errors.push(`${path}.${key} is not allowed.`);
    }
    for (const [key, child] of Object.entries(properties)) {
      if (Object.prototype.hasOwnProperty.call(value, key)) errors.push(...validateSchemaValue(value[key], child, `${path}.${key}`));
    }
  } else if (type === 'array') {
    if (!Array.isArray(value)) return [`${path} must be an array.`];
    if (schema.minItems != null && value.length < schema.minItems) errors.push(`${path} needs at least ${schema.minItems} items.`);
    if (schema.maxItems != null && value.length > schema.maxItems) errors.push(`${path} allows at most ${schema.maxItems} items.`);
    value.forEach((item, index) => errors.push(...validateSchemaValue(item, schema.items || {}, `${path}[${index}]`)));
  } else if (type === 'string') {
    if (typeof value !== 'string') return [`${path} must be a string.`];
    if (schema.minLength != null && value.length < schema.minLength) errors.push(`${path} is too short.`);
    if (schema.maxLength != null && value.length > schema.maxLength) errors.push(`${path} is too long.`);
    if (schema.pattern && !(new RegExp(schema.pattern)).test(value)) errors.push(`${path} has an invalid format.`);
  } else if (type === 'integer' || type === 'number') {
    if (typeof value !== 'number' || !Number.isFinite(value) || (type === 'integer' && !Number.isInteger(value))) return [`${path} must be a ${type}.`];
    if (schema.minimum != null && value < schema.minimum) errors.push(`${path} is below the minimum.`);
    if (schema.maximum != null && value > schema.maximum) errors.push(`${path} is above the maximum.`);
  } else if (type === 'boolean' && typeof value !== 'boolean') {
    errors.push(`${path} must be true or false.`);
  }
  return errors;
}

function hostedModalEndpoint(env, hosted) {
  return String(env[hosted.endpoint_env] || hosted.default_endpoint).replace(/\/+$/, '');
}

function hostedModalCredentials(env, hosted) {
  return {
    id: String(env[hosted.proxy_token_id_env] || env.WOVEN_MODAL_PROXY_TOKEN_ID || '').trim(),
    secret: String(env[hosted.proxy_token_secret_env] || env.WOVEN_MODAL_PROXY_TOKEN_SECRET || '').trim(),
  };
}

function hostedModalConfigError(env, hosted) {
  const credentials = hostedModalCredentials(env, hosted);
  if (!credentials.id || !credentials.secret) return 'hosted_modal_auth_not_configured';
  try {
    const endpoint = new URL(hostedModalEndpoint(env, hosted));
    if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password) return 'hosted_modal_url_invalid';
  } catch { return 'hosted_modal_url_invalid'; }
  return '';
}

function hostedModalHeaders(env, hosted) {
  const credentials = hostedModalCredentials(env, hosted);
  return { 'Modal-Key': credentials.id, 'Modal-Secret': credentials.secret, Accept: 'application/json' };
}

function hostedModalPublicRunning(row, hosted, extra = {}) {
  return {
    ok: true, slug: hosted.slug, run_id: row.run_id, status: 'running', state: row.state,
    phase: 'running', progress_pct: 35, status_url: `/api/run/${encodeURIComponent(row.run_id)}`,
    quoted_cost_usd: Number(hosted.run_price_cents) / 100,
    billed_amount_usd: Number(row.cost_cents) / 100,
    ...extra,
  };
}

async function dispatchHostedModalRun(env, hosted, context) {
  const { runRequest, runId, userId, hostedInput, costUsd, balanceAfterDebit, authMethod } = context;
  let response;
  try {
    response = await fetch(`${hostedModalEndpoint(env, hosted)}/v1/runs`, {
      method: 'POST',
      headers: { ...hostedModalHeaders(env, hosted), 'Content-Type': 'application/json' },
      body: JSON.stringify(hostedInput),
    });
  } catch {
    return failHostedModalRun(env, hosted, runRequest.row, 'hosted_modal_dispatch_unavailable', 502);
  }
  let upstream = {};
  try { upstream = await response.json(); } catch { upstream = {}; }
  if (response.status !== 202 || !/^fc-[A-Za-z0-9_-]+$/.test(String(upstream.call_id || '')) || !/^\/v1\/runs\/fc-[A-Za-z0-9_-]+$/.test(String(upstream.result_url || ''))) {
    return failHostedModalRun(env, hosted, runRequest.row, `hosted_modal_dispatch_${response.status}`, 502);
  }
  const remote = { call_id: upstream.call_id, result_url: upstream.result_url };
  await putRunProgress(env, {
    run_id: runId, user_id: userId, phase: 'running', progress_pct: 35,
    progress_source: 'modal', modal_status: 'accepted',
    modal_status_url: hostedModalEndpoint(env, hosted) + upstream.result_url,
    result_json: JSON.stringify(remote),
  });
  return json(hostedModalPublicRunning(runRequest.row, hosted, {
    auth: authMethod, cost_usd: costUsd, balance: +(balanceAfterDebit / 100).toFixed(2),
  }), 202, cors());
}

async function refreshHostedModalRun(env, hosted, row) {
  if (row.state === 'succeeded' || row.state === 'refunded') {
    let terminal = {};
    try { terminal = JSON.parse(row.response_json || '{}'); } catch { terminal = {}; }
    return { status: row.state === 'succeeded' ? 200 : Number(row.http_status) || 502, body: terminal };
  }
  const progress = await getRunProgress(env, row.run_id);
  let remote = {};
  try { remote = JSON.parse(progress && progress.result_json || '{}'); } catch { remote = {}; }
  if (!/^\/v1\/runs\/fc-[A-Za-z0-9_-]+$/.test(String(remote.result_url || ''))) {
    return failHostedModalRun(env, hosted, row, 'hosted_modal_poll_contract_missing', 502, true);
  }
  let response;
  try {
    response = await fetch(hostedModalEndpoint(env, hosted) + remote.result_url, { headers: hostedModalHeaders(env, hosted) });
  } catch {
    await touchRunRequest(env, row.run_id);
    return { status: 202, body: hostedModalPublicRunning(row, hosted, { poll_warning: 'hosted_modal_status_unavailable' }) };
  }
  let upstream = {};
  try { upstream = await response.json(); } catch { upstream = {}; }
  if (response.status === 202) {
    await touchRunRequest(env, row.run_id);
    return { status: 202, body: hostedModalPublicRunning(row, hosted) };
  }
  const outputErrors = response.status === 200 ? validateSchemaValue(upstream, hosted.output_schema) : ['upstream failed'];
  if (response.status !== 200 || outputErrors.length) {
    return failHostedModalRun(env, hosted, row, response.status === 200 ? 'hosted_modal_invalid_output' : `hosted_modal_poll_${response.status}`, 502, true);
  }
  const result = {
    ok: true, slug: hosted.slug, run_id: row.run_id, status: 'completed', state: 'succeeded',
    phase: 'delivered', progress_pct: 100, status_url: `/api/run/${encodeURIComponent(row.run_id)}`,
    quoted_cost_usd: Number(hosted.run_price_cents) / 100,
    billed_amount_usd: Number(row.cost_cents) / 100,
    output: upstream,
  };
  await finishRunRequest(env, row.run_id, 'succeeded', result, 200);
  await putRunProgress(env, {
    run_id: row.run_id, user_id: row.user_id, phase: 'delivered', progress_pct: 100,
    progress_source: 'modal', modal_status: 'completed',
    modal_status_url: hostedModalEndpoint(env, hosted) + remote.result_url,
    result_json: JSON.stringify(upstream),
  });
  return { status: 200, body: result };
}

async function failHostedModalRun(env, hosted, row, reason, httpStatus = 502, returnObject = false) {
  const current = await getRunRequestById(env, row.run_id);
  if (current && current.state === 'succeeded') {
    let terminal = {};
    try { terminal = JSON.parse(current.response_json || '{}'); } catch { terminal = {}; }
    const result = { status: 200, body: terminal };
    return returnObject ? result : json(result.body, result.status, cors());
  }
  if (current) row = current;
  const response = {
    ok: false, error: 'run_failed', reason, slug: hosted.slug, run_id: row.run_id,
    status: 'failed', state: 'refunded', phase: 'failed', progress_pct: 0,
    quoted_cost_usd: Number(hosted.run_price_cents) / 100, billed_amount_usd: 0,
    status_url: `/api/run/${encodeURIComponent(row.run_id)}`,
  };
  const ownsRefund = await finishRunRequest(env, row.run_id, 'refunded', response, httpStatus);
  if (ownsRefund && await runDebitExists(env, row.run_id)) await refundRunCredits(env, row.user_id, Number(row.cost_cents), row.run_id);
  const terminal = { status: httpStatus, body: response };
  return returnObject ? terminal : json(terminal.body, terminal.status, cors());
}

// ── Async de Mello / Modal run ────────────────────────────────────────────

function demelloEndpoint(env) {
  return String(env.DEMELLO_MODAL_URL || DEMELLO_DEFAULT_ENDPOINT).replace(/\/+$/, '');
}

function demelloReleaseHash(env) {
  return String(env.DEMELLO_RELEASE_HASH || DEMELLO_DEFAULT_RELEASE_HASH).trim();
}

function demelloModalStatusUrl(env, runId) {
  return `${demelloEndpoint(env)}/v1/runs/${encodeURIComponent(runId)}`;
}

async function demelloModalIdempotencyKey(userId, callerKey) {
  // Modal's idempotency namespace is global, while Omo's durable key is scoped
  // by account. Hash the scope into an opaque downstream key: deterministic
  // for retries, collision-isolated across owners, and free of tenant IDs.
  const digest = await sha256Hex(`omo-demello-modal-idempotency-v1\u0000${userId}\u0000${callerKey}`);
  return `omo-${digest}`;
}

function demelloConfigError(env) {
  if (!String(env.DEMELLO_MODAL_BEARER || '').trim()) return 'demello_modal_auth_not_configured';
  try {
    const endpoint = new URL(demelloEndpoint(env));
    if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password) return 'demello_modal_url_invalid';
  } catch { return 'demello_modal_url_invalid'; }
  if (!/^sha256:[0-9a-f]{64}$/.test(demelloReleaseHash(env))) return 'demello_release_hash_invalid';
  return '';
}

function normalizeDemelloInput(fields) {
  const allowed = new Set([
    'audio_ref', 'audio_url', 'audio', 'topic', 'style', 'style_hint',
    'duration_bounds', 'min_seconds', 'max_seconds', 'duration_seconds', 'duration',
  ]);
  const unknown = Object.keys(fields).filter((key) => !allowed.has(key));
  if (unknown.length) {
    return { error: 'invalid_demello_input', detail: `Unsupported field: ${unknown[0]}` };
  }

  let rawAudioUrl = String(fields.audio_url || '').trim();
  let audioRef = String(fields.audio_ref || '').trim();
  const looseAudio = String(fields.audio || '').trim();
  const topic = String(fields.topic || '').trim();
  let inputNotice = '';
  if (!rawAudioUrl && !audioRef && looseAudio) {
    if (looseAudio === 'sample-demello-10s') audioRef = looseAudio;
    else if (/^https:\/\//i.test(looseAudio)) rawAudioUrl = looseAudio;
    else {
      audioRef = 'sample-demello-10s';
      inputNotice = 'Topic text was not synthesized into audio; this milestone run uses the bundled sample-demello-10s audio.';
    }
  }
  if (!rawAudioUrl && !audioRef && topic) {
    audioRef = 'sample-demello-10s';
    inputNotice = 'Topic text was not synthesized into audio; this milestone run uses the bundled sample-demello-10s audio.';
  }
  if (!!rawAudioUrl === !!audioRef) {
    return { error: 'invalid_demello_input', detail: 'Send exactly one of audio_url (HTTPS) or audio_ref.' };
  }
  if (audioRef && audioRef !== 'sample-demello-10s') {
    return { error: 'invalid_demello_input', detail: 'The only bundled audio_ref is sample-demello-10s.' };
  }
  if (rawAudioUrl) {
    return {
      error: 'demello_provider_lane_not_enabled',
      detail: 'Hosted milestone runs accept only audio_ref=sample-demello-10s. Arbitrary audio is gated until provider benchmarks and pre-spend controls pass.',
    };
  }

  const styleHint = String(fields.style || fields.style_hint || DEMELLO_STYLE).trim().toLowerCase();
  if (![DEMELLO_STYLE, 'sumi-e', 'japanese ink', 'japanese-style'].includes(styleHint)) {
    return { error: 'invalid_demello_input', detail: `This release is pinned to ${DEMELLO_STYLE}.` };
  }
  const bounds = fields.duration_bounds && typeof fields.duration_bounds === 'object' && !Array.isArray(fields.duration_bounds)
    ? fields.duration_bounds : {};
  const durationMatches = String(fields.duration == null ? '' : fields.duration).match(/\d+(?:\.\d+)?/g) || [];
  const duration = Number(fields.duration_seconds ?? (durationMatches.length ? durationMatches[durationMatches.length - 1] : NaN));
  const durationMin = durationMatches.length > 1 ? Number(durationMatches[0]) : Math.min(5, duration);
  const minSeconds = Number(bounds.min_seconds ?? fields.min_seconds ?? (Number.isFinite(duration) ? durationMin : 5));
  const maxSeconds = Number(bounds.max_seconds ?? fields.max_seconds ?? (Number.isFinite(duration) ? duration : 10));
  if (!Number.isFinite(minSeconds) || !Number.isFinite(maxSeconds) || minSeconds < 5 || maxSeconds > 20 || minSeconds > maxSeconds) {
    return { error: 'invalid_demello_input', detail: 'Duration bounds must satisfy 5 <= min_seconds <= max_seconds <= 20.' };
  }
  const input = {
    ...(audioRef ? { audio_ref: audioRef } : { audio_url: rawAudioUrl }),
    style: DEMELLO_STYLE,
    duration_bounds: { min_seconds: minSeconds, max_seconds: maxSeconds },
  };
  if (topic && !inputNotice) {
    inputNotice = 'The topic hint is not consumed by this pinned release; direction follows the supplied audio.';
  }
  return { input, input_notice: inputNotice };
}

function demelloPublicRunning(row, progress, extra = {}) {
  const phase = progress && progress.phase || 'running';
  const pct = Math.max(1, Math.min(99, Number(progress && progress.progress_pct) || 2));
  return {
    ok: true,
    slug: DEMELLO_SLUG,
    run_id: row.run_id,
    status: 'running',
    state: row.state,
    phase,
    progress_pct: pct,
    progress_source: progress && progress.progress_source || 'derived',
    status_url: `/api/run/${encodeURIComponent(row.run_id)}`,
    quoted_cost_usd: DEMELLO_QUOTED_RUN_CENTS / 100,
    billed_amount_usd: Number(row.cost_cents) / 100,
    billing_mode: DEMELLO_PAID_TRAFFIC_READY ? 'credits' : 'nonpaid_milestone',
    paid_traffic_ready: DEMELLO_PAID_TRAFFIC_READY,
    ...(progress && progress.input_notice ? { input_notice: progress.input_notice } : {}),
    ...extra,
  };
}

async function dispatchDemelloRun(env, context) {
  const {
    runRequest, runId, userId, idempotencyKey, demelloInput,
    demelloInputNotice, reservedCents, costUsd, balanceAfterDebit, authMethod,
  } = context;
  const requestHash = await sha256Hex(stableStringify(demelloInput));
  const modalIdempotencyKey = await demelloModalIdempotencyKey(userId, idempotencyKey);
  const envelope = {
    run_id: runId,
    release_hash: demelloReleaseHash(env),
    request_hash: requestHash,
    input: demelloInput,
    max_cost_usd: boundedNumber(env.DEMELLO_MAX_COST_USD, 0.0001, 100, 0.003),
  };
  await putRunProgress(env, {
    run_id: runId, user_id: userId, phase: 'running', progress_pct: 3,
    progress_source: 'derived', modal_status: 'dispatching',
    modal_status_url: demelloModalStatusUrl(env, runId),
    input_notice: demelloInputNotice,
  });

  let response;
  try {
    response = await fetch(`${demelloEndpoint(env)}/v1/runs`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${String(env.DEMELLO_MODAL_BEARER).trim()}`,
        'Content-Type': 'application/json',
        'Idempotency-Key': modalIdempotencyKey,
      },
      body: JSON.stringify(envelope),
    });
  } catch {
    // The request may have reached Modal. Keep the reservation and let the
    // deterministic status URL/reconciler resolve this unknown outcome.
    const progress = await getRunProgress(env, runId);
    return json(demelloPublicRunning(runRequest.row, progress, {
      auth: authMethod,
      cost_usd: costUsd,
      balance: +(balanceAfterDebit / 100).toFixed(2),
      dispatch_uncertain: true,
      ...(demelloInputNotice ? { input_notice: demelloInputNotice } : {}),
    }), 202, cors());
  }

  let upstream = {};
  try { upstream = await response.json(); } catch { upstream = {}; }
  if (!response.ok || String(upstream.run_id || '') !== runId) {
    const detail = response.ok ? 'modal_run_id_mismatch' : `modal_dispatch_${response.status}`;
    return failDemelloRun(env, runRequest.row, detail, response.ok ? 502 : 502);
  }

  await putRunProgress(env, {
    run_id: runId, user_id: userId, phase: 'running', progress_pct: 4,
    progress_source: 'derived', modal_status: String(upstream.status || 'accepted'),
    modal_status_url: demelloModalStatusUrl(env, runId),
    input_notice: demelloInputNotice,
  });
  const progress = await getRunProgress(env, runId);
  return json(demelloPublicRunning(runRequest.row, progress, {
    auth: authMethod,
    cost_usd: costUsd,
    balance: +(balanceAfterDebit / 100).toFixed(2),
    idempotent_replay: !!upstream.idempotent_replay,
    platform: upstream.platform,
    ...(demelloInputNotice ? { input_notice: demelloInputNotice } : {}),
  }), 202, cors());
}

async function handleRunStatus(request, env, _url, params) {
  const auth = await authenticateAccount(request, env, true);
  if (!auth.ok) return json({ error: auth.error }, auth.status, cors());
  const row = await getRunRequestById(env, params.runId);
  if (!row || row.user_id !== auth.userId) return json({ error: 'run_not_found' }, 404, cors());
  if (row.slug === DEMELLO_SLUG) {
    const result = await refreshDemelloRun(env, row);
    return json(result.body, result.status, cors());
  }
  const hosted = HOSTED_MODAL_SKILLS.get(row.slug);
  if (hosted) {
    const result = await refreshHostedModalRun(env, hosted, row);
    return json(result.body, result.status, cors());
  }
  if (row.state === 'succeeded' || row.state === 'refunded') {
    let body = {};
    try { body = JSON.parse(row.response_json || '{}'); } catch { body = {}; }
    return json({ ...body, run_id: row.run_id, state: row.state }, Number(row.http_status) || 200, cors());
  }
  return json({ ok: true, run_id: row.run_id, slug: row.slug, status: 'running', state: row.state }, 202, cors());
}

function derivedDemelloProgress(row, existing, env) {
  // Once a signed checkpoint or Modal-native checkpoint exists, elapsed time
  // never replaces it or relabels it as observed telemetry.
  if (existing && (existing.progress_source === 'webhook' || existing.progress_source === 'modal')) {
    return {
      phase: existing.phase,
      progress_pct: Number(existing.progress_pct) || 1,
      progress_source: existing.progress_source,
    };
  }
  const expected = boundedInt(env.DEMELLO_EXPECTED_RUN_SECONDS, 30, 1200, 90);
  const elapsed = Math.max(0, (Date.now() - Date.parse(row.created_at)) / 1000);
  const ratio = elapsed / expected;
  let phase = 'running';
  let pct = 4 + Math.floor(Math.min(ratio / 0.12, 1) * 12);
  if (ratio >= 0.12) { phase = 'transcribing'; pct = 16 + Math.floor(Math.min((ratio - 0.12) / 0.16, 1) * 14); }
  if (ratio >= 0.28) { phase = 'directing'; pct = 30 + Math.floor(Math.min((ratio - 0.28) / 0.14, 1) * 12); }
  if (ratio >= 0.42) { phase = 'generating'; pct = 42 + Math.floor(Math.min((ratio - 0.42) / 0.40, 1) * 40); }
  if (ratio >= 0.82) { phase = 'assembling'; pct = 82 + Math.floor(Math.min((ratio - 0.82) / 0.18, 1) * 13); }
  pct = Math.max(Number(existing && existing.progress_pct) || 0, Math.min(95, pct));
  return { phase, progress_pct: pct, progress_source: 'derived' };
}

function normalizeModalProgress(upstream) {
  if (!upstream || typeof upstream !== 'object') return null;
  const rawPhase = String(upstream.phase || upstream.progress && upstream.progress.phase || '').trim().toLowerCase();
  const pct = Number(upstream.progress_pct ?? (upstream.progress && upstream.progress.progress_pct));
  const phaseMap = {
    accepted: 'running', queued: 'running', reserved: 'reserved', running: 'running', starting: 'running',
    acquire: 'running', acquiring: 'running', preparing: 'running',
    transcribe: 'transcribing', transcription: 'transcribing', transcribing: 'transcribing',
    direct: 'directing', director: 'directing', directing: 'directing',
    generate: 'generating', generation: 'generating', generating: 'generating', semantic: 'generating',
    assemble: 'assembling', assembly: 'assembling', assembling: 'assembling',
    qa: 'assembling', validating: 'assembling', contract: 'assembling', finalizing: 'assembling',
  };
  const phase = phaseMap[rawPhase];
  if (!phase || !Number.isFinite(pct) || pct < 1 || pct > 99) return null;
  return { phase, progress_pct: Math.floor(pct), progress_source: 'modal' };
}

async function refreshDemelloRun(env, row) {
  let progress = await getRunProgress(env, row.run_id);
  let upstream = null;
  let pollWarning = '';
  if (!demelloConfigError(env)) {
    try {
      const response = await fetch(demelloModalStatusUrl(env, row.run_id), {
        headers: { Authorization: `Bearer ${String(env.DEMELLO_MODAL_BEARER).trim()}`, Accept: 'application/json' },
      });
      if (response.ok) upstream = await response.json();
      else pollWarning = `modal_status_${response.status}`;
    } catch { pollWarning = 'modal_status_unavailable'; }
  } else {
    pollWarning = 'modal_status_not_configured';
  }

  if (upstream && upstream.status === 'completed') {
    const delivered = await settleDemelloSuccess(env, row, upstream, 'modal');
    if (delivered) return delivered;
    if (row.state !== 'succeeded') return failDemelloRun(env, row, 'invalid_modal_artifact', 502, true);
  }
  if (upstream && upstream.status === 'failed' && row.state !== 'succeeded') {
    const code = String(upstream.error && upstream.error.code || 'modal_run_failed').slice(0, 80);
    return failDemelloRun(env, row, code, 502, true);
  }

  const modalProgress = normalizeModalProgress(upstream);
  if (modalProgress && row.state !== 'succeeded' && row.state !== 'refunded') {
    await putRunProgress(env, {
      run_id: row.run_id, user_id: row.user_id, ...modalProgress,
      modal_status: String(upstream.status || 'running'),
      modal_status_url: demelloModalStatusUrl(env, row.run_id),
    });
    await touchRunRequest(env, row.run_id);
    progress = await getRunProgress(env, row.run_id);
  }

  // A terminal response remains readable even if Modal is temporarily down;
  // successful status polls normally refresh its five-minute signed URL.
  if (row.state === 'succeeded' || row.state === 'refunded') {
    let terminal = {};
    try { terminal = JSON.parse(row.response_json || '{}'); } catch { terminal = {}; }
    return { status: row.state === 'succeeded' ? 200 : Number(row.http_status) || 502, body: terminal };
  }

  const timeoutSeconds = boundedInt(env.DEMELLO_RUN_TIMEOUT_SECONDS, 60, 3600, 1300);
  if (Date.now() - Date.parse(row.created_at) > timeoutSeconds * 1000) {
    return failDemelloRun(env, row, 'modal_run_timeout', 504, true);
  }
  if (!modalProgress) {
    const derived = derivedDemelloProgress(row, progress, env);
    await putRunProgress(env, {
      run_id: row.run_id, user_id: row.user_id, ...derived,
      modal_status: String(upstream && upstream.status || progress && progress.modal_status || 'running'),
      modal_status_url: demelloModalStatusUrl(env, row.run_id),
    });
    await touchRunRequest(env, row.run_id);
    progress = await getRunProgress(env, row.run_id);
  }
  return { status: 202, body: demelloPublicRunning(row, progress, pollWarning ? { poll_warning: pollWarning } : {}) };
}

async function verifiedDemelloArtifactUrl(env, runId, value, objectName) {
  try {
    const candidate = new URL(String(value || ''));
    const endpoint = new URL(demelloEndpoint(env));
    const expectedPath = `/v1/artifacts/${runId}/${objectName}`;
    const keys = Array.from(candidate.searchParams.keys());
    const expiresValues = candidate.searchParams.getAll('expires');
    const signatureValues = candidate.searchParams.getAll('signature');
    if (candidate.protocol !== 'https:' || candidate.username || candidate.password ||
        candidate.origin !== endpoint.origin || candidate.pathname !== expectedPath ||
        keys.length !== 2 || expiresValues.length !== 1 || signatureValues.length !== 1 ||
        !keys.includes('expires') || !keys.includes('signature')) return '';
    const expiresRaw = expiresValues[0];
    const signature = signatureValues[0];
    if (!/^\d{10}$/.test(expiresRaw) || !/^[0-9a-f]{64}$/.test(signature)) return '';
    const expires = Number(expiresRaw);
    const now = Math.floor(Date.now() / 1000);
    const minTtl = boundedInt(env.DEMELLO_ARTIFACT_MIN_TTL_SECONDS, 0, 120, 15);
    const maxTtl = boundedInt(env.DEMELLO_ARTIFACT_MAX_TTL_SECONDS, 60, 900, 900);
    if (!Number.isSafeInteger(expires) || expires < now + minTtl || expires > now + maxTtl) return '';
    const message = `GET\n${runId}\n${objectName}\n${expires}`;
    const mac = await hmacSha256(new TextEncoder().encode(String(env.DEMELLO_MODAL_BEARER || '')), message);
    if (!timingSafeEqual(signature, bytesToHex(mac))) return '';
    return candidate.toString();
  } catch { return ''; }
}

async function settleDemelloSuccess(env, row, upstream, source) {
  const current = await getRunRequestById(env, row.run_id);
  if (!current) return null;
  if (current.state === 'refunded') return terminalRunResult(current);
  row = current;
  const videoUrl = await verifiedDemelloArtifactUrl(env, row.run_id, upstream.video_url, 'video.mp4');
  if (!videoUrl) return null;
  const contactSheetUrl = upstream.contact_sheet_url
    ? await verifiedDemelloArtifactUrl(env, row.run_id, upstream.contact_sheet_url, 'contact-sheet.jpg') : '';
  if (!contactSheetUrl) return null;
  const storedProgress = await getRunProgress(env, row.run_id);
  const response = {
    ok: true,
    slug: DEMELLO_SLUG,
    run_id: row.run_id,
    status: 'delivered',
    upstream_status: 'completed',
    state: 'succeeded',
    phase: 'delivered',
    progress_pct: 100,
    progress_source: source,
    status_url: `/api/run/${encodeURIComponent(row.run_id)}`,
    video_url: videoUrl,
    ...(contactSheetUrl ? { contact_sheet_url: contactSheetUrl } : {}),
    output: { video_url: videoUrl, ...(contactSheetUrl ? { contact_sheet_url: contactSheetUrl } : {}) },
    quoted_cost_usd: DEMELLO_QUOTED_RUN_CENTS / 100,
    cost_usd: Number(row.cost_cents) / 100,
    billed_amount_usd: Number(row.cost_cents) / 100,
    billing_mode: DEMELLO_PAID_TRAFFIC_READY ? 'credits' : 'nonpaid_milestone',
    paid_traffic_ready: DEMELLO_PAID_TRAFFIC_READY,
    settlement: { status: 'settled', charged_usd: Number(row.cost_cents) / 100 },
    result: upstream,
    ...(storedProgress && storedProgress.input_notice ? { input_notice: storedProgress.input_notice } : {}),
  };
  const firstSettlement = await finishRunRequest(env, row.run_id, 'succeeded', response, 200);
  let authoritative = await getRunRequestById(env, row.run_id);
  if (!firstSettlement) {
    if (!authoritative || authoritative.state !== 'succeeded') return authoritative ? terminalRunResult(authoritative) : null;
    await replaceSuccessfulRunResponse(env, row.run_id, response);
    authoritative = await getRunRequestById(env, row.run_id);
  }
  await putRunProgress(env, {
    run_id: row.run_id, user_id: row.user_id, phase: 'delivered', progress_pct: 100,
    progress_source: source, modal_status: 'completed', modal_status_url: demelloModalStatusUrl(env, row.run_id),
    video_url: videoUrl, contact_sheet_url: contactSheetUrl, result_json: JSON.stringify(upstream),
  });
  return authoritative && authoritative.state === 'succeeded'
    ? { status: 200, body: response }
    : (authoritative ? terminalRunResult(authoritative) : null);
}

function terminalRunResult(row) {
  let body = {};
  try { body = JSON.parse(row.response_json || '{}'); } catch { body = {}; }
  return {
    status: row.state === 'succeeded' ? 200 : Number(row.http_status) || 502,
    body: { ...body, run_id: row.run_id, state: row.state },
  };
}

async function failDemelloRun(env, row, reason, httpStatus = 502, returnObject = false) {
  const current = await getRunRequestById(env, row.run_id);
  if (current && current.state === 'succeeded') {
    const terminal = terminalRunResult(current);
    return returnObject ? terminal : json(terminal.body, terminal.status, cors());
  }
  if (current) row = current;
  const existingProgress = await getRunProgress(env, row.run_id);
  const progressSource = existingProgress && existingProgress.progress_source || 'derived';
  const response = {
    ok: false, error: 'run_failed', reason, slug: DEMELLO_SLUG,
    run_id: row.run_id, status: 'failed', state: 'refunded', phase: 'failed',
    progress_pct: Number(existingProgress && existingProgress.progress_pct) || 0,
    progress_source: progressSource, status_url: `/api/run/${encodeURIComponent(row.run_id)}`,
    quoted_cost_usd: DEMELLO_QUOTED_RUN_CENTS / 100,
    billed_amount_usd: 0,
    billing_mode: DEMELLO_PAID_TRAFFIC_READY ? 'credits' : 'nonpaid_milestone',
    paid_traffic_ready: DEMELLO_PAID_TRAFFIC_READY,
    ...(existingProgress && existingProgress.input_notice ? { input_notice: existingProgress.input_notice } : {}),
  };
  const ownsRefund = await finishRunRequest(env, row.run_id, 'refunded', response, httpStatus);
  if (ownsRefund && await runDebitExists(env, row.run_id)) {
    await refundRunCredits(env, row.user_id, Number(row.cost_cents), row.run_id);
  }
  if (ownsRefund) {
    await putRunProgress(env, {
      run_id: row.run_id, user_id: row.user_id, phase: 'failed',
      progress_pct: response.progress_pct, progress_source: progressSource, modal_status: 'failed',
      modal_status_url: demelloModalStatusUrl(env, row.run_id), result_json: JSON.stringify({ error: reason }),
      input_notice: existingProgress && existingProgress.input_notice || '',
    });
  }
  const authoritative = await getRunRequestById(env, row.run_id);
  const terminal = authoritative ? terminalRunResult(authoritative) : { status: httpStatus, body: response };
  return returnObject ? terminal : json(terminal.body, terminal.status, cors());
}

async function handleRunProgressWebhook(request, env, _url, params) {
  const secret = String(env.DEMELLO_PROGRESS_WEBHOOK_SECRET || '').trim();
  if (!secret) return json({ error: 'progress_webhook_not_configured' }, 503, cors());
  const bearer = /^Bearer\s+(.+)$/i.exec(String(request.headers.get('authorization') || '').trim());
  if (!bearer || !timingSafeEqual(bearer[1], secret)) return json({ error: 'invalid_progress_webhook_auth' }, 401, cors());
  let body;
  try { body = await request.json(); } catch { body = {}; }
  const row = await getRunRequestById(env, params.runId);
  if (!row || row.slug !== DEMELLO_SLUG) return json({ error: 'run_not_found' }, 404, cors());
  if (body.run_id && body.run_id !== row.run_id) return json({ error: 'run_id_mismatch' }, 400, cors());
  if (row.state === 'succeeded' || row.state === 'refunded') {
    let terminal = {};
    try { terminal = JSON.parse(row.response_json || '{}'); } catch { terminal = {}; }
    return json(terminal, row.state === 'succeeded' ? 200 : Number(row.http_status) || 409, cors());
  }
  const status = String(body.status || 'running').trim().toLowerCase();
  if (status === 'completed' || status === 'delivered') {
    const delivered = await settleDemelloSuccess(env, row, body, 'webhook');
    return delivered ? json(delivered.body, delivered.status, cors()) : json({ error: 'invalid_artifact_url' }, 400, cors());
  }
  if (status === 'failed') return failDemelloRun(env, row, String(body.error_code || 'modal_run_failed').slice(0, 80));
  const phase = String(body.phase || '').trim().toLowerCase();
  const pct = Number(body.progress_pct);
  if (!DEMELLO_PHASE_RANK.has(phase) || ['delivered', 'failed'].includes(phase) || !Number.isFinite(pct) || pct < 1 || pct > 99) {
    return json({ error: 'invalid_progress_payload' }, 400, cors());
  }
  await putRunProgress(env, {
    run_id: row.run_id, user_id: row.user_id, phase, progress_pct: Math.floor(pct),
    progress_source: 'webhook', modal_status: 'running', modal_status_url: demelloModalStatusUrl(env, row.run_id),
  });
  await touchRunRequest(env, row.run_id);
  const progress = await getRunProgress(env, row.run_id);
  return json(demelloPublicRunning(row, progress), 202, cors());
}

// ── Route: Stripe Checkout session ────────────────────────────────────────
// Body: { slug, email? } → creates a Stripe Checkout Session and returns
// { url }. This route intentionally allows signed-out buyers; Stripe collects
// an email when one is not supplied. Slug, product name, and price are always
// resolved from SERVER_CATALOG. A valid optional Idempotency-Key is scoped and
// forwarded to Stripe so caller retries reuse the same Checkout Session.

async function handleCheckout(request, env) {
  let body;
  try { body = await request.json(); } catch { body = {}; }
  const slug = String(body.slug || '').trim();
  const listing = SERVER_CATALOG.get(slug);
  if (!slug) return json({ error: 'Send slug.' }, 400, cors());
  if (!listing) return json({ error: 'unknown_catalog_slug' }, 404, cors());

  const secretKey = String(env.STRIPE_SECRET_KEY || '').trim();
  if (!secretKey) {
    return json({ error: 'stripe not configured' }, 501, cors());
  }

  const suppliedEmail = String(body.email || '').trim();
  const email = normalizeBuyerEmail(suppliedEmail);
  if (suppliedEmail && !email) return json({ error: 'invalid email' }, 400, cors());
  const callerIdempotencyKey = String(request.headers.get('idempotency-key') || '').trim();
  if (callerIdempotencyKey && !IDEMPOTENCY_KEY_RE.test(callerIdempotencyKey)) {
    return json({ error: 'Invalid Idempotency-Key (8-128 URL-safe characters).' }, 400, cors());
  }
  let userId = '';
  if (isRealMode(env) && request.headers.get('authorization')) {
    const auth = await authenticateAccount(request, env, false);
    if (auth.ok) userId = auth.userId;
  }
  const params = new URLSearchParams();
  params.set('mode', 'payment');
  applyOmoCheckoutBranding(params);
  params.set('success_url', `https://omo.space/?purchased=${encodeURIComponent(slug)}&session_id={CHECKOUT_SESSION_ID}`);
  params.set('cancel_url', purchaseCancelUrl(request, slug));
  params.set('custom_text[submit][message]', `Purchasing the ${listing.name} workflow`);
  // Stripe renders after_submit below the pay button before payment, so keep
  // this conditional instead of implying that an unpaid order is fulfilled.
  params.set('custom_text[after_submit][message]', 'Enjoy your workflow — after payment, find it in your Omo dashboard');
  params.set('line_items[0][quantity]', '1');
  params.set('line_items[0][price_data][currency]', 'usd');
  params.set('line_items[0][price_data][product_data][name]', listing.name);
  params.set('line_items[0][price_data][product_data][description]', `${listing.name} workflow and prompts from Omo.`);
  params.set('line_items[0][price_data][unit_amount]', String(listing.licensePriceCents));
  params.set('metadata[type]', 'catalog_license');
  params.set('metadata[flow]', 'purchase');
  params.set('metadata[slug]', slug);
  params.set('metadata[workflow]', listing.name);
  params.set('metadata[amount_cents]', String(listing.licensePriceCents));
  params.set('metadata[currency]', 'usd');
  if (userId) params.set('metadata[user_id]', userId);
  if (email) params.set('customer_email', email);

  try {
    const stripeHeaders = stripeCheckoutHeaders(secretKey);
    if (callerIdempotencyKey) {
      stripeHeaders['Idempotency-Key'] = `omo-checkout-${await sha256Hex(`catalog-license\u0000${slug}\u0000${callerIdempotencyKey}`)}`;
    }
    const res = await fetch('https://api.stripe.com/v1/checkout/sessions', {
      method: 'POST',
      headers: stripeHeaders,
      body: params.toString(),
    });
    if (!res.ok) {
      return json({ error: `stripe error ${res.status}` }, 502, cors());
    }
    const data = await res.json();
    let checkoutUrl;
    try { checkoutUrl = new URL(data && data.url); } catch { checkoutUrl = null; }
    if (!data || !data.id || !checkoutUrl || checkoutUrl.origin !== 'https://checkout.stripe.com') {
      return json({ error: 'stripe returned an invalid checkout session' }, 502, cors());
    }
    await recordPendingPurchase(env, data.id, listing, email);
    return json({ url: checkoutUrl.toString() }, 200, cors());
  } catch (e) {
    return json({ error: 'stripe unavailable' }, 502, cors());
  }
}

// ── Route: public waitlist ──────────────────────────────────────────────
// Body: { email, source? }. Email is normalized before the unique insert, so
// casing and surrounding whitespace cannot create duplicate rows.

async function handleWaitlist(request, env) {
  let body;
  try { body = await request.json(); } catch { body = {}; }

  const email = normalizeWaitlistEmail(body.email);
  if (!email) {
    return json({ ok: false, error: 'invalid_email', message: 'That email looks a little off — try it once more.' }, 400, cors());
  }

  const rawSource = String(body.source || '').trim().toLowerCase();
  if (rawSource && !/^[a-z0-9][a-z0-9._:-]{0,63}$/.test(rawSource)) {
    return json({ ok: false, error: 'invalid_source', message: 'Source must be 1–64 letters, numbers, dots, dashes, underscores, or colons.' }, 400, cors());
  }

  const added = await insertWaitlistEntry(env, email, rawSource || null);
  if (!added) {
    return json({ ok: true, status: 'already', message: 'Already on the list!' }, 200, cors());
  }
  return json({ ok: true, status: 'added', message: "You're on the list — we'll email you when it opens 🎉" }, 200, cors());
}

// ── Route: creator workflow intake ──────────────────────────────────────
// The Worker stores Markdown as untrusted data. It does not compile or execute
// it. The agent-side processor owns the reviewed profile and deployment gates.

function submissionSlug(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function parseSubmissionMarkdown(content) {
  if (typeof content !== 'string' || !content.trim()) {
    return { error: 'content_required', message: 'Paste or upload workflow Markdown.' };
  }
  if (content.includes('\0')) {
    return { error: 'invalid_content', message: 'Workflow Markdown cannot contain NUL bytes.' };
  }
  const sizeBytes = new TextEncoder().encode(content).length;
  if (sizeBytes > MAX_SUBMISSION_BYTES) {
    return { error: 'content_too_large', message: `Workflow Markdown must be ${MAX_SUBMISSION_BYTES} bytes or smaller.` };
  }
  const lines = content.split(/\r?\n/);
  if (!lines.length || lines[0].trim() !== '---') {
    return { error: 'invalid_frontmatter', message: 'Markdown must begin with YAML frontmatter.' };
  }
  const end = lines.slice(1).findIndex((line) => line.trim() === '---');
  if (end < 0) {
    return { error: 'invalid_frontmatter', message: 'Markdown frontmatter is not closed.' };
  }
  const values = {};
  lines.slice(1, end + 1).forEach((line) => {
    const match = /^([A-Za-z][A-Za-z0-9_-]*):\s*(.*?)\s*$/.exec(line);
    if (!match || !match[2] || match[2] === '|' || match[2] === '>') return;
    values[match[1]] = match[2].replace(/^(?:"([\s\S]*)"|'([\s\S]*)')$/, (_all, double, single) => double ?? single);
  });
  const name = String(values.name || '').trim();
  const description = String(values.description || '').trim();
  if (!name || !description) {
    return { error: 'invalid_frontmatter', message: 'Frontmatter requires one-line name and description values.' };
  }
  if (name.length > 120) return { error: 'name_too_long', message: 'Frontmatter names allow 120 characters.' };
  if (description.length > 500) return { error: 'description_too_long', message: 'Frontmatter descriptions allow 500 characters.' };
  const slug = submissionSlug(name);
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || slug.length > 100) {
    return { error: 'invalid_name', message: 'The frontmatter name does not produce a valid workflow slug.' };
  }
  return { name, description, slug, content, sizeBytes };
}

async function handleSubmission(request, env) {
  let body;
  try { body = await request.json(); } catch { body = {}; }

  let userId = '';
  if (isRealMode(env)) {
    const auth = await authenticateAccount(request, env, false);
    if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, cors());
    userId = auth.userId;
  } else {
    userId = String(body.user_id || '').trim();
  }
  if (!validUserId(userId)) {
    return json({ ok: false, error: 'authentication_required', message: 'Sign in before submitting a workflow.' }, 401, cors());
  }
  if (body.visibility && body.visibility !== 'public') {
    return json({ ok: false, error: 'unsupported_visibility', message: 'Private workflow hosting is not available yet.' }, 400, cors());
  }

  const parsed = parseSubmissionMarkdown(body.content);
  if (parsed.error) return json({ ok: false, ...parsed }, 400, cors());
  const suppliedName = String(body.name || '').trim();
  if (!suppliedName) {
    return json({ ok: false, error: 'name_required', message: 'Give the workflow a name.' }, 400, cors());
  }
  if (suppliedName.length > 120) {
    return json({ ok: false, error: 'name_too_long', message: 'Workflow names allow 120 characters.' }, 400, cors());
  }
  if (submissionSlug(suppliedName) !== parsed.slug) {
    return json({ ok: false, error: 'name_mismatch', message: 'Workflow name must match the name in Markdown frontmatter.' }, 400, cors());
  }

  const sourceSha256 = await sha256Hex(parsed.content);
  const id = `sub_${(await sha256Hex(`${userId}\u0000${sourceSha256}`)).slice(0, 32)}`;
  const stored = await insertSubmission(env, {
    id, userId, name: parsed.name, slug: parsed.slug, content: parsed.content, sourceSha256,
  });
  return json({
    ok: true,
    id: stored.id,
    slug: parsed.slug,
    status: stored.status,
    duplicate: stored.duplicate,
    message: stored.duplicate ? 'This workflow is already in your queue.' : 'Queued for Omo review and hosting.',
  }, 202, cors());
}

// ── Route: dashboard /api/me ──────────────────────────────────────────────
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

  const firstRead = await getUserRecord(env, userId);
  await reconcileStaleReservations(env, userId);
  const record = (await getUserRecord(env, userId)).record;
  const runs = await listRuns(env, userId, 50);
  return json({
    ok: true,
    balance: (record.balance_cents / 100).toFixed(2),
    balance_usd: +(record.balance_cents / 100).toFixed(2),
    balance_cents: record.balance_cents,
    currency: 'usd',
    signup_granted: firstRead.created,
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
    return handleStripeWebhook(request, env);
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

  const callerIdempotencyKey = String(request.headers.get('idempotency-key') || '').trim();
  if (real && !IDEMPOTENCY_KEY_RE.test(callerIdempotencyKey)) {
    return json({ error: 'Invalid Idempotency-Key (8-128 URL-safe characters).' }, 400, cors());
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
  applyOmoCheckoutBranding(params);
  // Credits are fulfilled synchronously from checkout.session.completed.
  // Restrict Checkout to cards so delayed payment methods cannot create a
  // completed-but-not-yet-paid fulfillment gap.
  params.set('payment_method_types[0]', 'card');
  params.set('success_url', 'https://omo.space/billing.html?topup=success&session_id={CHECKOUT_SESSION_ID}');
  params.set('cancel_url', 'https://omo.space/billing.html?topup=cancelled');
  params.set('custom_text[submit][message]', 'Topping up Omo credits');
  // after_submit is below the pay button, not a post-payment success screen.
  params.set('custom_text[after_submit][message]', 'Thank you — your Omo credits are on the way after payment');
  params.set('client_reference_id', userId);
  params.set('metadata[user_id]', userId);
  params.set('metadata[type]', 'credits_topup');
  params.set('metadata[flow]', 'topup');
  params.set('metadata[amount_cents]', String(cents));
  params.set('metadata[currency]', 'usd');
  params.set('line_items[0][quantity]', '1');
  params.set('line_items[0][price_data][currency]', 'usd');
  params.set('line_items[0][price_data][product_data][name]', 'Omo credits');
  params.set('line_items[0][price_data][product_data][description]', `Adds $${(cents / 100).toFixed(2)} to your Omo balance.`);
  params.set('line_items[0][price_data][unit_amount]', String(cents));

  try {
    const stripeHeaders = stripeCheckoutHeaders(secretKey);
    if (callerIdempotencyKey) {
      stripeHeaders['Idempotency-Key'] = `omo-topup-${await sha256Hex(`credits-topup\u0000${userId}\u0000${cents}\u0000${callerIdempotencyKey}`)}`;
    }
    const res = await fetch('https://api.stripe.com/v1/checkout/sessions', {
      method: 'POST',
      headers: stripeHeaders,
      body: params.toString(),
    });
    if (!res.ok) {
      return json({ error: `stripe error ${res.status}` }, 502, cors());
    }
    const data = await res.json();
    let checkoutUrl;
    try { checkoutUrl = new URL(data && data.url); } catch { checkoutUrl = null; }
    if (!data || !data.id || !checkoutUrl || checkoutUrl.origin !== 'https://checkout.stripe.com') {
      return json({ error: 'stripe returned an invalid checkout session' }, 502, cors());
    }
    if (real) await recordPendingTopup(env, data.id, userId, cents, 'usd');
    return json({ url: checkoutUrl.toString(), session_id: data.id }, 200, cors());
  } catch (e) {
    return json({ error: 'stripe unavailable' }, 502, cors());
  }
}

// Stripe sends checkout.session.completed to this shared endpoint. Signed
// credit top-ups are applied exactly once; signed catalog-license purchases
// are recorded exactly once for later download/ownership fulfillment.
async function handleStripeWebhook(request, env) {
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
  const amountCents = Number(session && session.amount_total);
  const currency = String((session && session.currency) || '').toLowerCase();
  if (!session || session.payment_status !== 'paid' || !session.id || currency !== 'usd' ||
      !Number.isSafeInteger(amountCents) || amountCents <= 0) {
    return json({ ok: true, ignored: true }, 200, cors());
  }

  if (!event.id) return json({ error: 'missing event id' }, 400, cors());

  if (metadata && metadata.type === 'catalog_license') {
    return handleStripePurchaseCompleted(env, event.id, session, metadata, amountCents, currency);
  }
  if (!metadata || metadata.type !== 'credits_topup') {
    return json({ ok: true, ignored: true }, 200, cors());
  }

  let userId = '';
  if (isRealMode(env)) {
    const pending = await getPendingTopup(env, session.id);
    if (!pending || !['pending', 'applied'].includes(pending.state) || pending.amount_cents !== amountCents ||
        pending.currency !== 'usd' || !validUserId(pending.user_id)) {
      return json({ ok: true, ignored: true }, 200, cors());
    }
    userId = pending.user_id;
  } else {
    userId = String((metadata && metadata.user_id) || session.client_reference_id || '').trim();
    if (!validUserId(userId) || !metadata || metadata.type !== 'credits_topup' ||
        Number(metadata.amount_cents) !== amountCents || String(metadata.currency || 'usd') !== 'usd') {
      return json({ ok: true, ignored: true }, 200, cors());
    }
  }

  await getUserRecord(env, userId);
  const applied = await creditTopup(env, event.id, session.id, userId, amountCents);
  if (isRealMode(env)) await markPendingTopupApplied(env, session.id);
  const { record } = await getUserRecord(env, userId);
  return json({
    ok: true,
    applied,
    user_id: userId,
    balance: (record.balance_cents / 100).toFixed(2),
    balance_cents: record.balance_cents,
  }, 200, cors());
}

async function handleStripePurchaseCompleted(env, eventId, session, metadata, amountCents, currency) {
  const slug = String(metadata.slug || '').trim();
  const listing = SERVER_CATALOG.get(slug);
  const metadataAmountCents = Number(metadata.amount_cents);
  const metadataCurrency = String(metadata.currency || '').toLowerCase();
  if (!listing || metadataAmountCents !== listing.licensePriceCents || metadataCurrency !== 'usd' ||
      amountCents !== listing.licensePriceCents || currency !== 'usd') {
    return json({ ok: true, ignored: true }, 200, cors());
  }

  const pending = await getPendingPurchase(env, session.id);
  if (!pending || pending.slug !== slug || Number(pending.amount_cents) !== listing.licensePriceCents ||
      String(pending.currency || '').toLowerCase() !== 'usd') {
    return json({ ok: true, ignored: true }, 200, cors());
  }

  const buyerEmail = normalizeBuyerEmail(
    (session.customer_details && session.customer_details.email) || session.customer_email || pending.buyer_email || ''
  );
  const applied = await completePurchase(env, eventId, session.id, listing, buyerEmail);
  // Deliberately omit buyer email and all secrets from production logs.
  console.info('stripe catalog purchase completed', {
    stripe_event_id: String(eventId).slice(0, 128),
    session_id: String(session.id).slice(0, 128),
    slug,
    applied,
  });
  return json({ ok: true, applied, type: 'catalog_license', slug }, 200, cors());
}

// ── Route: Clerk webhook ───────────────────────────────────────────────────
// Clerk dashboard → Webhooks → Endpoint URL https://<worker>/api/clerk-webhook,
// event: user.created. On that event we grant the $5 signup credits (INSERT
// OR IGNORE — an existing row keeps its balance, so no double grants, and a
// lazy /api/me provision doesn't get reset by the webhook).
// Svix verification is mandatory in real mode. Mock/local mode keeps the
// unsigned grant path used by the zero-key demo and offline router tests.

async function handleClerkWebhook(request, env) {
  let raw;
  try { raw = await request.text(); } catch { raw = ''; }
  let body;
  try { body = JSON.parse(raw); } catch {
    return json({ error: 'invalid json' }, 400, cors());
  }

  const secret = env.CLERK_WEBHOOK_SECRET;
  if (isRealMode(env) && !secret) {
    return json({ error: 'clerk webhook not configured' }, 503, cors());
  }
  if (secret && !(await verifySvix(request.headers, raw, secret))) {
    return json({ error: 'invalid signature' }, 401, cors());
  }

  if (body.type !== 'user.created' || !body.data || !body.data.id) {
    return json({ ok: true, ignored: true }, 200, cors());
  }

  const userId = String(body.data.id);
  if (!validUserId(userId)) return json({ error: 'invalid user id' }, 400, cors());
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
const mockApiKeys = new Map();
const mockRunRequests = new Map();
const mockRunProgress = new Map();
const mockPendingTopups = new Map();
const mockPurchases = new Map();
const mockPurchaseEvents = new Set();
const mockWaitlist = new Map();
const mockSubmissions = new Map();
const clerkJwksCache = new Map();

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

function isRealMode(env) {
  if (databaseKind(env) !== 'mock') return true;
  if (!env) return false;
  return /^pk_(?:test|live)_/.test(String(env.CLERK_PUBLISHABLE_KEY || '')) ||
    !!(env.STRIPE_SECRET_KEY || env.CLERK_WEBHOOK_SECRET || env.STRIPE_WEBHOOK_SECRET || env.BALANCE_KEY_SECRET);
}

function validUserId(value) {
  return USER_ID_RE.test(String(value || '').trim());
}

function normalizeBuyerEmail(value) {
  const email = String(value || '').trim().toLowerCase();
  if (!email || email.length > 254 || /\s/.test(email)) return '';
  const at = email.indexOf('@');
  return at > 0 && at === email.lastIndexOf('@') && at < email.length - 1 ? email : '';
}

function normalizeWaitlistEmail(value) {
  const email = String(value || '').trim().toLowerCase();
  if (!email || email.length > 254) return '';
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : '';
}

function boundedInt(value, min, max, fallback) {
  const number = Number(value);
  return Number.isInteger(number) && number >= min && number <= max ? number : fallback;
}

function boundedNumber(value, min, max, fallback) {
  const number = Number(value);
  return Number.isFinite(number) && number >= min && number <= max ? number : fallback;
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

async function insertWaitlistEntry(env, email, source) {
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-waitlist-insert-v1',
      'INSERT INTO waitlist (email, source) VALUES ($1, $2) ON CONFLICT (email) DO NOTHING RETURNING id',
      [email, source]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB
      .prepare('INSERT OR IGNORE INTO waitlist (email, source, created_at) VALUES (?, ?, ?)')
      .bind(email, source, new Date().toISOString())
      .run();
    return Number(result && result.meta && result.meta.changes) === 1;
  }
  if (mockWaitlist.has(email)) return false;
  mockWaitlist.set(email, { email, source, created_at: new Date().toISOString() });
  return true;
}

async function insertSubmission(env, submission) {
  const now = new Date().toISOString();
  const values = [
    submission.id, submission.userId, submission.name, submission.slug,
    submission.content, submission.sourceSha256, 'queued', now, now,
  ];
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-submission-insert-v1',
      'INSERT INTO submissions (id,user_id,name,slug,content,source_sha256,status,created_at,updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (user_id,source_sha256) DO NOTHING RETURNING id,status',
      values
    ));
    if (result.rowCount === 1) return { ...result.rows[0], duplicate: false };
    const existing = await getNeonPool(env).query(prepared(
      'omo-submission-existing-v1',
      'SELECT id,status FROM submissions WHERE user_id = $1 AND source_sha256 = $2',
      [submission.userId, submission.sourceSha256]
    ));
    if (!existing.rows[0]) throw new Error('submission insert conflict could not be resolved');
    return { ...existing.rows[0], duplicate: true };
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB
      .prepare('INSERT OR IGNORE INTO submissions (id,user_id,name,slug,content,source_sha256,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)')
      .bind(...values).run();
    const existing = await env.BALANCE_DB
      .prepare('SELECT id,status FROM submissions WHERE user_id = ? AND source_sha256 = ?')
      .bind(submission.userId, submission.sourceSha256).first();
    if (!existing) throw new Error('submission insert conflict could not be resolved');
    return { ...existing, duplicate: Number(result && result.meta && result.meta.changes) !== 1 };
  }
  const key = `${submission.userId}\u0000${submission.sourceSha256}`;
  if (mockSubmissions.has(key)) return { ...mockSubmissions.get(key), duplicate: true };
  const record = { ...submission, status: 'queued', created_at: now, updated_at: now };
  mockSubmissions.set(key, record);
  return { id: record.id, status: record.status, duplicate: false };
}

function balanceSecret(env) {
  return env.BALANCE_KEY_SECRET || env.LLM_API_KEY || 'omo-dev-secret';
}

function signupGrantCents(env) {
  const override = Number(env.SIGNUP_GRANT_USD);
  const amountUsd = isFinite(override) && override > 0 ? override : grantSignupCredits().amountUsd;
  return Math.round(amountUsd * 100);
}

async function authenticateAccount(request, env, allowApiKey) {
  const authorization = String(request.headers.get('authorization') || '').trim();
  const bearer = /^Bearer\s+(.+)$/i.exec(authorization);
  const explicitApiKey = String(request.headers.get('x-api-key') || '').trim();
  const credential = explicitApiKey || (bearer && bearer[1]) || '';

  if (allowApiKey && credential.startsWith('omo_')) {
    const userId = await userIdForApiKey(env, credential);
    return userId
      ? { ok: true, userId, method: 'api_key' }
      : { ok: false, status: 401, error: 'invalid_api_key' };
  }
  if (!bearer || !bearer[1]) return { ok: false, status: 401, error: 'authentication_required' };
  if (!env.CLERK_PUBLISHABLE_KEY) return { ok: false, status: 503, error: 'clerk_not_configured' };

  try {
    const claims = await verifyClerkSessionToken(bearer[1], env);
    return { ok: true, userId: claims.sub, method: 'clerk' };
  } catch (e) {
    return { ok: false, status: 401, error: 'invalid_session_token' };
  }
}

async function userIdForApiKey(env, apiKey) {
  if (!/^omo_[0-9a-f]{32}$/.test(apiKey)) return '';
  const keyHash = await sha256Hex(apiKey);
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-api-key-owner-v1', 'SELECT user_id FROM api_keys WHERE key_hash = $1', [keyHash]
    ));
    if (result.rows[0] && validUserId(result.rows[0].user_id)) return result.rows[0].user_id;
    const legacy = await getNeonPool(env).query(prepared(
      'omo-api-key-legacy-owner-v1', 'SELECT user_id FROM users WHERE api_key = $1', [apiKey]
    ));
    if (legacy.rows[0] && validUserId(legacy.rows[0].user_id)) {
      await ensureApiKeyRecord(env, legacy.rows[0].user_id, apiKey);
      return legacy.rows[0].user_id;
    }
    return '';
  }
  if (databaseKind(env) === 'd1') {
    const row = await env.BALANCE_DB.prepare('SELECT user_id FROM api_keys WHERE key_hash = ?').bind(keyHash).first();
    if (row && validUserId(row.user_id)) return row.user_id;
    const legacy = await env.BALANCE_DB.prepare('SELECT user_id FROM users WHERE api_key = ?').bind(apiKey).first();
    if (legacy && validUserId(legacy.user_id)) {
      await ensureApiKeyRecord(env, legacy.user_id, apiKey);
      return legacy.user_id;
    }
    return '';
  }
  return mockApiKeys.get(keyHash) || '';
}

async function ensureApiKeyRecord(env, userId, apiKey) {
  const keyHash = await sha256Hex(apiKey);
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    await getNeonPool(env).query(prepared(
      'omo-api-key-upsert-v1',
      'INSERT INTO api_keys (key_hash, user_id, created_at) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET key_hash = EXCLUDED.key_hash',
      [keyHash, userId, now]
    ));
  } else if (databaseKind(env) === 'd1') {
    await env.BALANCE_DB.prepare('INSERT INTO api_keys (key_hash, user_id, created_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET key_hash = excluded.key_hash').bind(keyHash, userId, now).run();
  } else {
    mockApiKeys.set(keyHash, userId);
  }
}

function clerkFrontendApi(publishableKey) {
  const match = /^pk_(?:test|live)_(.+)$/.exec(String(publishableKey || '').trim());
  if (!match) throw new Error('invalid Clerk publishable key');
  const decoded = new TextDecoder().decode(base64UrlBytes(match[1])).replace(/\$$/, '');
  if (!/^[A-Za-z0-9.-]{3,253}$/.test(decoded) || decoded.startsWith('.') || decoded.endsWith('.')) {
    throw new Error('invalid Clerk Frontend API');
  }
  return decoded.toLowerCase();
}

async function getClerkJwks(env, forceRefresh) {
  const frontendApi = clerkFrontendApi(env.CLERK_PUBLISHABLE_KEY);
  const cached = clerkJwksCache.get(frontendApi);
  if (!forceRefresh && cached && cached.expiresAt > Date.now()) return cached.keys;
  const response = await fetch(`https://${frontendApi}/.well-known/jwks.json`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error('Clerk JWKS unavailable');
  const body = await response.json();
  const keys = Array.isArray(body.keys) ? body.keys.filter((key) => key && key.kty === 'RSA') : [];
  if (!keys.length) throw new Error('Clerk JWKS empty');
  clerkJwksCache.set(frontendApi, { keys, expiresAt: Date.now() + 10 * 60 * 1000 });
  return keys;
}

async function verifyClerkSessionToken(token, env) {
  if (typeof token !== 'string' || token.length < 32 || token.length > 8192) throw new Error('invalid JWT');
  const parts = token.split('.');
  if (parts.length !== 3) throw new Error('invalid JWT');
  const header = JSON.parse(new TextDecoder().decode(base64UrlBytes(parts[0])));
  const claims = JSON.parse(new TextDecoder().decode(base64UrlBytes(parts[1])));
  if (!header || header.alg !== 'RS256' || typeof header.kid !== 'string') throw new Error('invalid JWT header');

  let keys = await getClerkJwks(env, false);
  let jwk = keys.find((key) => key.kid === header.kid && (!key.alg || key.alg === 'RS256'));
  if (!jwk) {
    keys = await getClerkJwks(env, true);
    jwk = keys.find((key) => key.kid === header.kid && (!key.alg || key.alg === 'RS256'));
  }
  if (!jwk) throw new Error('unknown JWT key');
  const publicKey = await crypto.subtle.importKey(
    'jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']
  );
  const verified = await crypto.subtle.verify(
    'RSASSA-PKCS1-v1_5', publicKey, base64UrlBytes(parts[2]),
    new TextEncoder().encode(`${parts[0]}.${parts[1]}`)
  );
  if (!verified) throw new Error('invalid JWT signature');

  const now = Math.floor(Date.now() / 1000);
  const skew = boundedInt(env.CLERK_CLOCK_SKEW_SECONDS, 0, 30, 5);
  const issuer = `https://${clerkFrontendApi(env.CLERK_PUBLISHABLE_KEY)}`;
  if (!Number.isFinite(claims.exp) || now - skew >= claims.exp) throw new Error('expired JWT');
  if (Number.isFinite(claims.nbf) && now + skew < claims.nbf) throw new Error('early JWT');
  if (Number.isFinite(claims.iat) && now + skew < claims.iat) throw new Error('future JWT');
  if (String(claims.iss || '').replace(/\/$/, '') !== issuer) throw new Error('invalid JWT issuer');
  if (!validUserId(claims.sub)) throw new Error('invalid JWT subject');
  if (claims.azp && !isAllowedStorefrontOrigin(String(claims.azp))) throw new Error('invalid authorized party');
  return claims;
}

function base64UrlBytes(value) {
  const normalized = String(value || '').replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized + '='.repeat((4 - normalized.length % 4) % 4);
  return base64Bytes(padded);
}

async function sha256Hex(value) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(value)));
  return bytesToHex(new Uint8Array(digest));
}

function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
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
  const apiKeyHash = await sha256Hex(apiKey);
  const grantCents = signupGrantCents(env);

  if (databaseKind(env) === 'neon') {
    const client = await getNeonPool(env).connect();
    try {
      await client.query('BEGIN');
      const inserted = await client.query(prepared(
        'omo-user-create-v1',
        'INSERT INTO users (user_id, balance_cents, api_key, created_at) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO NOTHING RETURNING balance_cents, api_key, created_at',
        [userId, grantCents, apiKeyHash, now]
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
      await client.query(prepared(
        'omo-api-key-upsert-v1',
        'INSERT INTO api_keys (key_hash, user_id, created_at) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET key_hash = EXCLUDED.key_hash',
        [apiKeyHash, userId, now]
      ));
      await client.query('COMMIT');
      return { record: { ...selected.rows[0], api_key: apiKey }, created };
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
    if (existing) {
      await ensureApiKeyRecord(env, userId, apiKey);
      return { record: { ...existing, api_key: apiKey }, created: false };
    }
    const insert = await env.BALANCE_DB
      .prepare('INSERT OR IGNORE INTO users (user_id, balance_cents, api_key, created_at) VALUES (?, ?, ?, ?)')
      .bind(userId, grantCents, apiKeyHash, now).run();
    const created = !!(insert.meta && insert.meta.changes);
    if (created) {
      await insertD1Ledger(env, [`signup:${userId}`, userId, 'signup_grant', grantCents, grantCents, userId, now]);
    }
    const row = await env.BALANCE_DB
      .prepare('SELECT balance_cents, api_key, created_at FROM users WHERE user_id = ?')
      .bind(userId).first();
    await ensureApiKeyRecord(env, userId, apiKey);
    return { record: { ...(row || { balance_cents: grantCents, created_at: now }), api_key: apiKey }, created };
  }

  if (!mockUsers.has(userId)) {
    const record = { balance_cents: grantCents, api_key: apiKey, created_at: now };
    mockUsers.set(userId, record);
    mockApiKeys.set(apiKeyHash, userId);
    mockLedgerEntry(`signup:${userId}`, userId, 'signup_grant', grantCents, grantCents, userId, now);
    return { record, created: true };
  }
  mockApiKeys.set(apiKeyHash, userId);
  return { record: mockUsers.get(userId), created: false };
}

function mockRunRequestKey(userId, idempotencyKey) {
  return `${userId}\u0000${idempotencyKey}`;
}

async function claimRunRequest(env, userId, idempotencyKey, requestHash, slug, costCents, runId) {
  const now = new Date().toISOString();
  const values = [runId, userId, idempotencyKey, requestHash, slug, costCents, 'reserved', now, now];
  if (databaseKind(env) === 'neon') {
    const client = await getNeonPool(env).connect();
    try {
      await client.query('BEGIN');
      const inserted = await client.query(prepared(
        'omo-run-request-claim-v1',
        'INSERT INTO run_requests (run_id, user_id, idempotency_key, request_hash, slug, cost_cents, state, created_at, updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (user_id, idempotency_key) DO NOTHING RETURNING *',
        values
      ));
      const selected = inserted.rowCount ? inserted : await client.query(prepared(
        'omo-run-request-by-key-v1',
        'SELECT * FROM run_requests WHERE user_id = $1 AND idempotency_key = $2',
        [userId, idempotencyKey]
      ));
      await client.query('COMMIT');
      return { created: inserted.rowCount === 1, row: selected.rows[0] };
    } catch (e) {
      try { await client.query('ROLLBACK'); } catch (rollbackError) {}
      throw e;
    } finally { client.release(); }
  }
  if (databaseKind(env) === 'd1') {
    const inserted = await env.BALANCE_DB.prepare('INSERT OR IGNORE INTO run_requests (run_id, user_id, idempotency_key, request_hash, slug, cost_cents, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)').bind(...values).run();
    const row = await env.BALANCE_DB.prepare('SELECT * FROM run_requests WHERE user_id = ? AND idempotency_key = ?').bind(userId, idempotencyKey).first();
    return { created: !!(inserted.meta && inserted.meta.changes), row };
  }
  const key = mockRunRequestKey(userId, idempotencyKey);
  if (mockRunRequests.has(key)) return { created: false, row: mockRunRequests.get(key) };
  const row = {
    run_id: runId, user_id: userId, idempotency_key: idempotencyKey,
    request_hash: requestHash, slug, cost_cents: costCents, state: 'reserved',
    response_json: null, http_status: null, created_at: now, updated_at: now,
  };
  mockRunRequests.set(key, row);
  return { created: true, row };
}

async function replayRunResponse(env, row, requestHash) {
  if (!row || row.request_hash !== requestHash) {
    return json({ error: 'idempotency_key_conflict' }, 409, cors());
  }
  if (row.state === 'succeeded' || row.state === 'refunded') {
    let body = {};
    try { body = JSON.parse(row.response_json || '{}'); } catch { body = {}; }
    body.idempotent_replay = true;
    body.state = row.state;
    body.run_id = row.run_id;
    return json(body, Number(row.http_status) || (row.state === 'succeeded' ? 200 : 500), cors());
  }
  if (row.slug === DEMELLO_SLUG) {
    const progress = await getRunProgress(env, row.run_id);
    return json(demelloPublicRunning(row, progress, { idempotent_replay: true }), 202, cors());
  }
  const hosted = HOSTED_MODAL_SKILLS.get(row.slug);
  if (hosted) {
    return json(hostedModalPublicRunning(row, hosted, { idempotent_replay: true }), 202, cors());
  }
  return json({
    ok: true, idempotent_replay: true, run_id: row.run_id, state: row.state,
  }, 202, cors());
}

async function getRunRequestById(env, runId) {
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-run-request-by-id-v1', 'SELECT * FROM run_requests WHERE run_id = $1', [runId]
    ));
    return result.rows[0] || null;
  }
  if (databaseKind(env) === 'd1') {
    return env.BALANCE_DB.prepare('SELECT * FROM run_requests WHERE run_id = ?').bind(runId).first();
  }
  for (const row of mockRunRequests.values()) if (row.run_id === runId) return row;
  return null;
}

async function touchRunRequest(env, runId) {
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    await getNeonPool(env).query(prepared(
      'omo-run-request-touch-v1', "UPDATE run_requests SET updated_at = $1 WHERE run_id = $2 AND state = 'running'", [now, runId]
    ));
  } else if (databaseKind(env) === 'd1') {
    await env.BALANCE_DB.prepare("UPDATE run_requests SET updated_at = ? WHERE run_id = ? AND state = 'running'").bind(now, runId).run();
  } else {
    const row = await getRunRequestById(env, runId);
    if (row && row.state === 'running') row.updated_at = now;
  }
}

async function replaceSuccessfulRunResponse(env, runId, response) {
  const now = new Date().toISOString();
  const responseJson = JSON.stringify(response);
  if (databaseKind(env) === 'neon') {
    await getNeonPool(env).query(prepared(
      'omo-run-request-refresh-result-v1',
      "UPDATE run_requests SET response_json = $1, http_status = 200, updated_at = $2 WHERE run_id = $3 AND state = 'succeeded'",
      [responseJson, now, runId]
    ));
  } else if (databaseKind(env) === 'd1') {
    await env.BALANCE_DB.prepare("UPDATE run_requests SET response_json = ?, http_status = 200, updated_at = ? WHERE run_id = ? AND state = 'succeeded'").bind(responseJson, now, runId).run();
  } else {
    const row = await getRunRequestById(env, runId);
    if (row && row.state === 'succeeded') {
      row.response_json = responseJson;
      row.http_status = 200;
      row.updated_at = now;
    }
  }
}

async function getRunProgress(env, runId) {
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-run-progress-get-v1', 'SELECT * FROM run_progress WHERE run_id = $1', [runId]
    ));
    return result.rows[0] || null;
  }
  if (databaseKind(env) === 'd1') {
    return env.BALANCE_DB.prepare('SELECT * FROM run_progress WHERE run_id = ?').bind(runId).first();
  }
  return mockRunProgress.get(runId) || null;
}

async function putRunProgress(env, value) {
  const candidatePct = Math.max(0, Math.min(100, Math.floor(Number(value.progress_pct) || 0)));
  const candidateRank = DEMELLO_PHASE_RANK.get(value.phase) ?? -1;
  const sourceRank = { derived: 0, webhook: 1, modal: 2 }[value.progress_source] ?? 0;
  const terminal = value.phase === 'delivered' || value.phase === 'failed';
  const now = new Date().toISOString();
  const candidate = {
    run_id: value.run_id,
    user_id: value.user_id || '',
    phase: value.phase,
    progress_pct: value.phase === 'delivered' ? 100 : candidatePct,
    progress_source: value.progress_source || 'derived',
    modal_status: value.modal_status || 'running',
    modal_status_url: value.modal_status_url || '',
    video_url: value.video_url || null,
    contact_sheet_url: value.contact_sheet_url || null,
    result_json: value.result_json || null,
    input_notice: value.input_notice || null,
    started_at: now,
    updated_at: now,
    terminal_at: terminal ? now : null,
  };

  if (databaseKind(env) === 'mock') {
    const existing = mockRunProgress.get(candidate.run_id);
    if (existing && (existing.phase === 'delivered' || existing.phase === 'failed')) return existing;
    const existingRank = DEMELLO_PHASE_RANK.get(existing && existing.phase) ?? -1;
    const existingSourceRank = { derived: 0, webhook: 1, modal: 2 }[existing && existing.progress_source] ?? 0;
    const wins = !existing || candidate.progress_pct > Number(existing.progress_pct) ||
      (candidate.progress_pct === Number(existing.progress_pct) && (candidateRank > existingRank ||
        (candidateRank === existingRank && sourceRank > existingSourceRank)));
    const row = !existing ? candidate : {
      ...existing,
      ...(wins ? candidate : {}),
      user_id: existing.user_id,
      input_notice: existing.input_notice || candidate.input_notice,
      started_at: existing.started_at,
      updated_at: now,
      terminal_at: wins && terminal ? existing.terminal_at || now : existing.terminal_at,
    };
    mockRunProgress.set(row.run_id, row);
    return row;
  }

  const values = [
    candidate.run_id, candidate.user_id, candidate.phase, candidate.progress_pct, candidate.progress_source,
    candidate.modal_status, candidate.modal_status_url, candidate.video_url, candidate.contact_sheet_url,
    candidate.result_json, candidate.input_notice, candidate.started_at, candidate.updated_at, candidate.terminal_at,
  ];
  const pgPhaseExcluded = "CASE EXCLUDED.phase WHEN 'reserved' THEN 0 WHEN 'running' THEN 1 WHEN 'transcribing' THEN 2 WHEN 'directing' THEN 3 WHEN 'generating' THEN 4 WHEN 'assembling' THEN 5 WHEN 'delivered' THEN 6 WHEN 'failed' THEN 7 ELSE -1 END";
  const pgPhaseCurrent = "CASE run_progress.phase WHEN 'reserved' THEN 0 WHEN 'running' THEN 1 WHEN 'transcribing' THEN 2 WHEN 'directing' THEN 3 WHEN 'generating' THEN 4 WHEN 'assembling' THEN 5 WHEN 'delivered' THEN 6 WHEN 'failed' THEN 7 ELSE -1 END";
  const pgSourceExcluded = "CASE EXCLUDED.progress_source WHEN 'derived' THEN 0 WHEN 'webhook' THEN 1 WHEN 'modal' THEN 2 ELSE -1 END";
  const pgSourceCurrent = "CASE run_progress.progress_source WHEN 'derived' THEN 0 WHEN 'webhook' THEN 1 WHEN 'modal' THEN 2 ELSE -1 END";
  const pgWins = `(EXCLUDED.progress_pct > run_progress.progress_pct OR (EXCLUDED.progress_pct = run_progress.progress_pct AND (${pgPhaseExcluded} > ${pgPhaseCurrent} OR (${pgPhaseExcluded} = ${pgPhaseCurrent} AND ${pgSourceExcluded} > ${pgSourceCurrent}))))`;
  const sqliteWins = pgWins.replaceAll('EXCLUDED.', 'excluded.');
  if (databaseKind(env) === 'neon') {
    await getNeonPool(env).query(prepared(
      'omo-run-progress-upsert-v2',
      `INSERT INTO run_progress (run_id,user_id,phase,progress_pct,progress_source,modal_status,modal_status_url,video_url,contact_sheet_url,result_json,input_notice,started_at,updated_at,terminal_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14) ON CONFLICT (run_id) DO UPDATE SET phase=CASE WHEN ${pgWins} THEN EXCLUDED.phase ELSE run_progress.phase END,progress_pct=CASE WHEN ${pgWins} THEN EXCLUDED.progress_pct ELSE run_progress.progress_pct END,progress_source=CASE WHEN ${pgWins} THEN EXCLUDED.progress_source ELSE run_progress.progress_source END,modal_status=CASE WHEN ${pgWins} THEN EXCLUDED.modal_status ELSE run_progress.modal_status END,modal_status_url=CASE WHEN ${pgWins} THEN EXCLUDED.modal_status_url ELSE run_progress.modal_status_url END,video_url=CASE WHEN ${pgWins} THEN COALESCE(EXCLUDED.video_url,run_progress.video_url) ELSE run_progress.video_url END,contact_sheet_url=CASE WHEN ${pgWins} THEN COALESCE(EXCLUDED.contact_sheet_url,run_progress.contact_sheet_url) ELSE run_progress.contact_sheet_url END,result_json=CASE WHEN ${pgWins} THEN COALESCE(EXCLUDED.result_json,run_progress.result_json) ELSE run_progress.result_json END,input_notice=COALESCE(run_progress.input_notice,EXCLUDED.input_notice),updated_at=EXCLUDED.updated_at,terminal_at=CASE WHEN ${pgWins} THEN COALESCE(EXCLUDED.terminal_at,run_progress.terminal_at) ELSE run_progress.terminal_at END WHERE run_progress.phase NOT IN ('delivered','failed')`,
      values
    ));
  } else if (databaseKind(env) === 'd1') {
    await env.BALANCE_DB.prepare(`INSERT INTO run_progress (run_id,user_id,phase,progress_pct,progress_source,modal_status,modal_status_url,video_url,contact_sheet_url,result_json,input_notice,started_at,updated_at,terminal_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET phase=CASE WHEN ${sqliteWins} THEN excluded.phase ELSE run_progress.phase END,progress_pct=CASE WHEN ${sqliteWins} THEN excluded.progress_pct ELSE run_progress.progress_pct END,progress_source=CASE WHEN ${sqliteWins} THEN excluded.progress_source ELSE run_progress.progress_source END,modal_status=CASE WHEN ${sqliteWins} THEN excluded.modal_status ELSE run_progress.modal_status END,modal_status_url=CASE WHEN ${sqliteWins} THEN excluded.modal_status_url ELSE run_progress.modal_status_url END,video_url=CASE WHEN ${sqliteWins} THEN COALESCE(excluded.video_url,run_progress.video_url) ELSE run_progress.video_url END,contact_sheet_url=CASE WHEN ${sqliteWins} THEN COALESCE(excluded.contact_sheet_url,run_progress.contact_sheet_url) ELSE run_progress.contact_sheet_url END,result_json=CASE WHEN ${sqliteWins} THEN COALESCE(excluded.result_json,run_progress.result_json) ELSE run_progress.result_json END,input_notice=COALESCE(run_progress.input_notice,excluded.input_notice),updated_at=excluded.updated_at,terminal_at=CASE WHEN ${sqliteWins} THEN COALESCE(excluded.terminal_at,run_progress.terminal_at) ELSE run_progress.terminal_at END WHERE run_progress.phase NOT IN ('delivered','failed')`).bind(...values).run();
  }
  return getRunProgress(env, candidate.run_id);
}

async function setRunRunning(env, runId) {
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    await getNeonPool(env).query(prepared(
      'omo-run-request-running-v1',
      "UPDATE run_requests SET state = 'running', updated_at = $1 WHERE run_id = $2 AND state = 'reserved'",
      [now, runId]
    ));
  } else if (databaseKind(env) === 'd1') {
    await env.BALANCE_DB.prepare("UPDATE run_requests SET state = 'running', updated_at = ? WHERE run_id = ? AND state = 'reserved'").bind(now, runId).run();
  } else {
    for (const row of mockRunRequests.values()) {
      if (row.run_id === runId && row.state === 'reserved') {
        row.state = 'running';
        row.updated_at = now;
        break;
      }
    }
  }
}

async function finishRunRequest(env, runId, state, response, httpStatus) {
  const now = new Date().toISOString();
  const responseJson = JSON.stringify(response);
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-run-request-finish-v1',
      "UPDATE run_requests SET state = $1, response_json = $2, http_status = $3, updated_at = $4 WHERE run_id = $5 AND state IN ('reserved','running')",
      [state, responseJson, httpStatus, now, runId]
    ));
    return result.rowCount === 1;
  } else if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare("UPDATE run_requests SET state = ?, response_json = ?, http_status = ?, updated_at = ? WHERE run_id = ? AND state IN ('reserved','running')").bind(state, responseJson, httpStatus, now, runId).run();
    return !!(result.meta && result.meta.changes);
  } else {
    for (const row of mockRunRequests.values()) {
      if (row.run_id === runId && (row.state === 'reserved' || row.state === 'running')) {
        row.state = state;
        row.response_json = responseJson;
        row.http_status = httpStatus;
        row.updated_at = now;
        return true;
      }
    }
    return false;
  }
}

async function reconcileStaleReservations(env, userId) {
  const ttlSeconds = boundedInt(env.RUN_RESERVATION_TTL_SECONDS, 60, 3600, 300);
  const cutoff = new Date(Date.now() - ttlSeconds * 1000).toISOString();
  const demelloTtlSeconds = boundedInt(env.DEMELLO_RUN_TIMEOUT_SECONDS, 60, 3600, 1300);
  const demelloCutoff = new Date(Date.now() - demelloTtlSeconds * 1000).toISOString();
  let rows = [];
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-run-request-stale-v1',
      "SELECT run_id, cost_cents, slug, updated_at FROM run_requests WHERE user_id = $1 AND state IN ('reserved','running') AND updated_at < $2 ORDER BY updated_at LIMIT 20",
      [userId, cutoff]
    ));
    rows = result.rows || [];
  } else if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare("SELECT run_id, cost_cents, slug, updated_at FROM run_requests WHERE user_id = ? AND state IN ('reserved','running') AND updated_at < ? ORDER BY updated_at LIMIT 20").bind(userId, cutoff).all();
    rows = result.results || [];
  } else {
    rows = Array.from(mockRunRequests.values()).filter((row) =>
      row.user_id === userId && (row.state === 'reserved' || row.state === 'running') && row.updated_at < cutoff
    ).slice(0, 20);
  }
  for (const row of rows) {
    const longRunningHosted = row.slug === DEMELLO_SLUG || HOSTED_MODAL_SKILLS.has(row.slug);
    if (longRunningHosted && row.updated_at >= demelloCutoff) continue;
    const response = { error: 'stale_reservation_refunded', run_id: row.run_id, state: 'refunded' };
    const claimed = await claimStaleRunRefund(env, row.run_id, longRunningHosted ? demelloCutoff : cutoff, response);
    if (claimed && await runDebitExists(env, row.run_id)) {
      await refundRunCredits(env, userId, Number(row.cost_cents), row.run_id);
    }
  }
  await reconcileMissingRefunds(env, userId);
}

async function reconcileMissingRefunds(env, userId) {
  let rows = [];
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-run-request-unreconciled-refunds-v1',
      "SELECT run_id, cost_cents FROM run_requests WHERE user_id = $1 AND state = 'refunded' ORDER BY updated_at DESC LIMIT 20",
      [userId]
    ));
    rows = result.rows || [];
  } else if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare("SELECT run_id, cost_cents FROM run_requests WHERE user_id = ? AND state = 'refunded' ORDER BY updated_at DESC LIMIT 20").bind(userId).all();
    rows = result.results || [];
  } else {
    rows = Array.from(mockRunRequests.values()).filter((row) =>
      row.user_id === userId && row.state === 'refunded'
    ).slice(-20);
  }
  for (const row of rows) {
    if (await runDebitExists(env, row.run_id) && !(await runRefundExists(env, row.run_id))) {
      await refundRunCredits(env, userId, Number(row.cost_cents), row.run_id);
    }
  }
}

async function claimStaleRunRefund(env, runId, cutoff, response) {
  const now = new Date().toISOString();
  const responseJson = JSON.stringify(response);
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-run-request-claim-stale-v1',
      "UPDATE run_requests SET state = 'refunded', response_json = $1, http_status = 409, updated_at = $2 WHERE run_id = $3 AND state IN ('reserved','running') AND updated_at < $4 RETURNING run_id",
      [responseJson, now, runId, cutoff]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare("UPDATE run_requests SET state = 'refunded', response_json = ?, http_status = 409, updated_at = ? WHERE run_id = ? AND state IN ('reserved','running') AND updated_at < ?").bind(responseJson, now, runId, cutoff).run();
    return !!(result.meta && result.meta.changes);
  }
  for (const row of mockRunRequests.values()) {
    if (row.run_id === runId && (row.state === 'reserved' || row.state === 'running') && row.updated_at < cutoff) {
      row.state = 'refunded';
      row.response_json = responseJson;
      row.http_status = 409;
      row.updated_at = now;
      return true;
    }
  }
  return false;
}

async function runDebitExists(env, runId) {
  const ledgerId = `run:${runId}:debit`;
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-run-debit-exists-v1', 'SELECT event_id FROM credits_ledger WHERE event_id = $1', [ledgerId]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    return !!(await env.BALANCE_DB.prepare('SELECT event_id FROM credits_ledger WHERE event_id = ?').bind(ledgerId).first());
  }
  return mockLedger.has(ledgerId);
}

async function runRefundExists(env, runId) {
  const ledgerId = `run:${runId}:refund`;
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-run-refund-exists-v1', 'SELECT event_id FROM credits_ledger WHERE event_id = $1', [ledgerId]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    return !!(await env.BALANCE_DB.prepare('SELECT event_id FROM credits_ledger WHERE event_id = ?').bind(ledgerId).first());
  }
  return mockLedger.has(ledgerId);
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
    // D1 batch() is transactional. balance_cents=-1 is a private claim marker:
    // only the batch that inserted it can satisfy the guarded credit update.
    await env.BALANCE_DB.batch([
      env.BALANCE_DB.prepare('INSERT OR IGNORE INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES (?, ?, ?, ?, -1, ?, ?)').bind(ledgerId, userId, 'run_refund', costCents, runId, now),
      env.BALANCE_DB.prepare('UPDATE users SET balance_cents = balance_cents + ? WHERE user_id = ? AND EXISTS (SELECT 1 FROM credits_ledger WHERE event_id = ? AND balance_cents = -1)').bind(costCents, userId, ledgerId),
      env.BALANCE_DB.prepare('UPDATE credits_ledger SET balance_cents = (SELECT balance_cents FROM users WHERE user_id = ?) WHERE event_id = ? AND balance_cents = -1').bind(userId, ledgerId),
    ]);
    return;
  }
  if (mockLedger.has(ledgerId)) return;
  const rec = mockUsers.get(userId);
  if (rec) {
    rec.balance_cents += costCents;
    mockLedgerEntry(ledgerId, userId, 'run_refund', costCents, rec.balance_cents, runId, now);
  }
}

async function recordPendingPurchase(env, sessionId, listing, buyerEmail) {
  const now = new Date().toISOString();
  const values = [
    sessionId, listing.slug, listing.name, listing.licensePriceCents,
    'usd', buyerEmail || '', 'pending', now, now,
  ];
  if (databaseKind(env) === 'neon') {
    await getNeonPool(env).query(prepared(
      'omo-purchase-create-v1',
      'INSERT INTO purchases (session_id, slug, listing_name, amount_cents, currency, buyer_email, state, created_at, updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (session_id) DO NOTHING',
      values
    ));
  } else if (databaseKind(env) === 'd1') {
    await env.BALANCE_DB.prepare('INSERT OR IGNORE INTO purchases (session_id, slug, listing_name, amount_cents, currency, buyer_email, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)').bind(...values).run();
  } else if (!mockPurchases.has(sessionId)) {
    mockPurchases.set(sessionId, {
      session_id: sessionId,
      stripe_event_id: null,
      slug: listing.slug,
      listing_name: listing.name,
      amount_cents: listing.licensePriceCents,
      currency: 'usd',
      buyer_email: buyerEmail || '',
      state: 'pending',
      created_at: now,
      updated_at: now,
      completed_at: null,
    });
  }
}

async function getPendingPurchase(env, sessionId) {
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-purchase-get-v1', 'SELECT * FROM purchases WHERE session_id = $1', [sessionId]
    ));
    return result.rows[0] || null;
  }
  if (databaseKind(env) === 'd1') {
    return env.BALANCE_DB.prepare('SELECT * FROM purchases WHERE session_id = ?').bind(sessionId).first();
  }
  return mockPurchases.get(sessionId) || null;
}

async function completePurchase(env, stripeEventId, sessionId, listing, buyerEmail) {
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-purchase-complete-v1',
      "UPDATE purchases SET stripe_event_id = $1, buyer_email = CASE WHEN $2 <> '' THEN $2 ELSE buyer_email END, state = 'completed', updated_at = $3, completed_at = $3 WHERE session_id = $4 AND slug = $5 AND amount_cents = $6 AND currency = 'usd' AND state = 'pending' AND NOT EXISTS (SELECT 1 FROM purchases claimed WHERE claimed.stripe_event_id = $1) RETURNING session_id",
      [stripeEventId, buyerEmail || '', now, sessionId, listing.slug, listing.licensePriceCents]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare("UPDATE purchases SET stripe_event_id = ?, buyer_email = CASE WHEN ? <> '' THEN ? ELSE buyer_email END, state = 'completed', updated_at = ?, completed_at = ? WHERE session_id = ? AND slug = ? AND amount_cents = ? AND currency = 'usd' AND state = 'pending' AND NOT EXISTS (SELECT 1 FROM purchases claimed WHERE claimed.stripe_event_id = ?)")
      .bind(stripeEventId, buyerEmail || '', buyerEmail || '', now, now, sessionId, listing.slug, listing.licensePriceCents, stripeEventId).run();
    return !!(result.meta && result.meta.changes);
  }
  const pending = mockPurchases.get(sessionId);
  if (!pending || pending.state !== 'pending' || mockPurchaseEvents.has(stripeEventId) ||
      pending.slug !== listing.slug || pending.amount_cents !== listing.licensePriceCents || pending.currency !== 'usd') {
    return false;
  }
  mockPurchaseEvents.add(stripeEventId);
  pending.stripe_event_id = stripeEventId;
  pending.buyer_email = buyerEmail || pending.buyer_email;
  pending.state = 'completed';
  pending.updated_at = now;
  pending.completed_at = now;
  return true;
}

async function recordPendingTopup(env, sessionId, userId, amountCents, currency) {
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    await getNeonPool(env).query(prepared(
      'omo-pending-topup-create-v1',
      'INSERT INTO topup_sessions (session_id, user_id, amount_cents, currency, state, created_at, updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT (session_id) DO NOTHING',
      [sessionId, userId, amountCents, currency, 'pending', now, now]
    ));
  } else if (databaseKind(env) === 'd1') {
    await env.BALANCE_DB.prepare('INSERT OR IGNORE INTO topup_sessions (session_id, user_id, amount_cents, currency, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)').bind(sessionId, userId, amountCents, currency, 'pending', now, now).run();
  } else {
    if (!mockPendingTopups.has(sessionId)) {
      mockPendingTopups.set(sessionId, {
        session_id: sessionId, user_id: userId, amount_cents: amountCents,
        currency, state: 'pending', created_at: now, updated_at: now,
      });
    }
  }
}

async function getPendingTopup(env, sessionId) {
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-pending-topup-get-v1', 'SELECT * FROM topup_sessions WHERE session_id = $1', [sessionId]
    ));
    return result.rows[0] || null;
  }
  if (databaseKind(env) === 'd1') {
    return env.BALANCE_DB.prepare('SELECT * FROM topup_sessions WHERE session_id = ?').bind(sessionId).first();
  }
  return mockPendingTopups.get(sessionId) || null;
}

async function markPendingTopupApplied(env, sessionId) {
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    await getNeonPool(env).query(prepared(
      'omo-pending-topup-apply-v1',
      "UPDATE topup_sessions SET state = 'applied', updated_at = $1 WHERE session_id = $2 AND state = 'pending'",
      [now, sessionId]
    ));
  } else if (databaseKind(env) === 'd1') {
    await env.BALANCE_DB.prepare("UPDATE topup_sessions SET state = 'applied', updated_at = ? WHERE session_id = ? AND state = 'pending'").bind(now, sessionId).run();
  } else {
    const pending = mockPendingTopups.get(sessionId);
    if (pending && pending.state === 'pending') {
      pending.state = 'applied';
      pending.updated_at = now;
    }
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
      'omo-runs-list-v2',
      "SELECT slug, cost_cents, created_at FROM (SELECT slug, cost_cents, created_at FROM run_requests WHERE user_id = $1 AND state = 'succeeded' UNION ALL SELECT slug, cost_cents, created_at FROM runs WHERE user_id = $1) AS history ORDER BY created_at DESC LIMIT $2",
      [userId, limit || 50]
    ));
    return result.rows || [];
  }
  if (databaseKind(env) === 'd1') {
    const res = await env.BALANCE_DB.prepare("SELECT slug, cost_cents, created_at FROM (SELECT slug, cost_cents, created_at FROM run_requests WHERE user_id = ? AND state = 'succeeded' UNION ALL SELECT slug, cost_cents, created_at FROM runs WHERE user_id = ?) AS history ORDER BY created_at DESC LIMIT ?").bind(userId, userId, limit || 50).all();
    return res.results || [];
  }
  const stateRuns = Array.from(mockRunRequests.values()).filter((row) =>
    row.user_id === userId && row.state === 'succeeded'
  ).map((row) => ({
    run_id: row.run_id, slug: row.slug, cost_cents: row.cost_cents, created_at: row.created_at,
  }));
  return [...stateRuns, ...(mockRuns.get(userId) || [])]
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
    .slice(0, limit || 50);
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

async function callLLM(env, systemPrompt, userPrompt, maxTokens, model) {
  const res = await fetch(`${env.LLM_BASE_URL || 'https://opencode.ai/zen/go/v1'}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${env.LLM_API_KEY}`,
    },
    body: JSON.stringify({
      model: model || env.LLM_MODEL || 'deepseek-v4-flash',
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

function isAllowedStorefrontOrigin(origin) {
  return origin === 'https://omo.space' ||
    origin === 'https://www.omo.space' ||
    origin === 'https://omo.best' ||
    /^http:\/\/localhost(?::\d{1,5})?$/.test(origin);
}

function cors(request, env) {
  const origin = request && request.headers ? String(request.headers.get('origin') || '') : '';
  const headers = {
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type, Idempotency-Key, X-API-Key',
    'Content-Type': 'application/json',
  };
  if (!isRealMode(env)) headers['Access-Control-Allow-Origin'] = '*';
  else if (isAllowedStorefrontOrigin(origin)) {
    headers['Access-Control-Allow-Origin'] = origin;
    headers.Vary = 'Origin';
  }
  return headers;
}

function applyCors(response, request, env) {
  const headers = cors(request, env);
  response.headers.delete('Access-Control-Allow-Origin');
  response.headers.delete('Vary');
  Object.entries(headers).forEach(([key, value]) => response.headers.set(key, value));
  return response;
}

function json(obj, status, headers) {
  return new Response(JSON.stringify(obj), { status, headers });
}
