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
//   POST /api/support/chat             → guest-or-authenticated, profile-pinned Omo Support Hermes
//   GET/POST /api/me                   → {balance, api_key, currency, runs} for the dashboard
//   POST /api/topup                    → Stripe Checkout + signed top-up fulfillment
//   POST /api/clerk-webhook            → Clerk webhook: user.created → $5 signup grant
//   GET/POST /api/pilot/claim          → verify/redeem a signed pilot free-book grant
//   POST /api/internal/submissions/schema → build-worker schema introspection
//   POST /api/internal/submissions/migrate → temporary build-worker schema migration
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
//   PILOT_MAGIC_LINK_SECRET — HMAC secret for pilot claim tokens (SECRET,
//                       at least 32 bytes; never exposed to the browser).
//   PILOT_GRANT_CENTS — expected signed pilot grant; defaults to 99 cents.
//   PILOT_BOOK_BUILDER_PATH — same-origin path returned after a successful
//                       claim; required for redemption and must be reviewed.
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
import { Pool, neon } from '@neondatabase/serverless';
import { grantSignupCredits, debitForRun, apiKeyFor, topupAmounts, MIN_TOPUP_USD } from './balance.mjs';
import { PilotTokenError, verifyPilotToken } from './pilot-magic.mjs';
import { runPrice, llmWorkflow, LLM_RATES } from './cost-model.mjs';
import { handleMcpRequest } from './mcp-server.mjs';
import { HOSTED_WORKER_SKILL_ROWS, HOSTED_MODAL_SKILL_ROWS, HOSTED_SERVER_CATALOG_ROWS } from './hosted-skills.generated.mjs';
import { PureDataRuntimeError, executePureDataProgram, pureDataProgramDigest, validatePureDataProgram } from './pure-data-runtime.mjs';

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
const PRODUCTION_CANARY_RUN_SLUGS = new Set([
  'label-normalizer-canary',
  'release-tag-sorter-canary',
  'incident-route-classifier-canary',
]);
const PRODUCTION_CANARY_SUBMISSION_SLUGS = new Set([
  'v02-release-label-sorter',
  'v02-support-urgency-classifier',
]);
const DEMELLO_STYLE = 'sumi-e-awake-v3';
const DEMELLO_DEFAULT_ENDPOINT = 'https://harrythentrepreneur--omo-demello-awake-245304c8f988-api.modal.run';
const DEMELLO_DEFAULT_RELEASE_HASH = 'sha256:245304c8f98839bf6ac570c3c09224fe839041dbc793f3fb7f7afb3eb475259e';
const DEMELLO_QUOTED_RUN_CENTS = 10;
const DEMELLO_PAID_TRAFFIC_READY = false;
const DEMELLO_PHASES = ['reserved', 'running', 'transcribing', 'directing', 'generating', 'assembling', 'delivered', 'failed'];
const DEMELLO_PHASE_RANK = new Map(DEMELLO_PHASES.map((phase, index) => [phase, index]));
const HOSTED_WORKER_SKILLS = new Map(HOSTED_WORKER_SKILL_ROWS);
const HOSTED_MODAL_SKILLS = new Map(HOSTED_MODAL_SKILL_ROWS);
assertHostedRegistryDisjoint();
const REQUESTED_RUNTIMES = new Set(['auto', 'worker-native', 'modal-hosted']);
const SUBMISSION_RUNTIME_MUTABLE_STATES = new Set(['queued', 'needs_review']);
const HOSTED_WORKER_LLM_SPEC_VERSION = 'omo.worker-single-llm/v1';
const HOSTED_WORKER_LLM_EXECUTION_KIND = 'single_llm';
const HOSTED_WORKER_LLM_OPERATION = 'chat.completions.strict_json';
const HOSTED_WORKER_PURE_DATA_SPEC_VERSION = 'omo.worker-pure-data/v1';
const HOSTED_WORKER_PURE_DATA_EXECUTION_KIND = 'pure_data';
const HOSTED_WORKER_PURE_DATA_OPERATION = 'pure_data.execute';
const HOSTED_WORKER_PROVIDERS = new Set(['opencode-go', 'gemini']);
const HOSTED_WORKER_PROVIDER_DESCRIPTORS = new Map([
  ['opencode-go', {
    api_key_env: 'LLM_API_KEY',
    base_url_env: 'LLM_BASE_URL',
    default_base_url: 'https://opencode.ai/zen/go/v1',
    origin: 'https://opencode.ai',
    path: '/zen/go/v1',
  }],
  ['gemini', {
    api_key_env: 'GEMINI_API_KEY',
    base_url_env: 'GEMINI_BASE_URL',
    default_base_url: 'https://generativelanguage.googleapis.com/v1beta/openai',
    origin: 'https://generativelanguage.googleapis.com',
    path: '/v1beta/openai',
  }],
]);
const HOSTED_WORKER_MAX_RESPONSE_BYTES = 256 * 1024;

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

function assertHostedRegistryDisjoint() {
  const overlaps = HOSTED_WORKER_SKILL_ROWS
    .map((row) => row[0])
    .filter((slug) => HOSTED_MODAL_SKILLS.has(slug));
  if (overlaps.length) throw new Error(`hosted registries overlap: ${overlaps.join(', ')}`);
}

const MAX_TOPUP_USD_DEFAULT = 1000;
const MAX_SUBMISSION_BYTES = 200 * 1024;
const MAX_INTERNAL_BODY_BYTES = 16 * 1024;
const MAX_INTERNAL_MIGRATION_BODY_BYTES = 256;
const SUBMISSION_CLAIM_LEASE_SECONDS = 2 * 60 * 60;
const FINALIZATION_LEASE_SECONDS = 60 * 60;
const USER_ID_RE = /^user_[A-Za-z0-9_-]{1,80}$/;
const SUBMISSION_ID_RE = /^sub_[A-Za-z0-9_-]{8,100}$/;
const SAFE_FAILURE_RE = /^[a-z][a-z0-9_]{2,63}$/;
const SAFE_WORKFLOW_VERSION_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*@[0-9A-Za-z][0-9A-Za-z._:-]{0,79}$/;
const SAFE_GIT_SHA_RE = /^[0-9a-f]{40}$/;
const SAFE_SHA256_RE = /^[0-9a-f]{64}$/;
const SAFE_GITHUB_URL_RE = /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/(?:issues|pull)\/[1-9][0-9]{0,9}$/;
const SAFE_RELEASE_BRANCH_RE = /^omo-release\/sub_[A-Za-z0-9_-]{8,100}-[a-z0-9]+(?:-[a-z0-9]+)*$/;
const RELEASE_PHASES = new Set(['compiled', 'pr_open', 'ci_passed', 'merged_verified', 'promoted', 'failed']);
const FINALIZATION_FAILURE_CODES = new Set([
  'credential_preflight_failed',
  'modal_preflight_failed',
  'worker_preflight_failed',
  'public_preflight_failed',
  'modal_deploy_failed',
  'modal_canary_failed',
  'worker_deploy_failed',
  'worker_smoke_failed',
  'public_verification_failed',
  'superseded_main',
  'internal_finalizer_failed',
  'release_head_not_ancestor',
]);
const AUTO_RECOVERY_NO_EFFECT_CODES = new Set([
  'modal_preflight_failed', 'worker_preflight_failed', 'public_preflight_failed',
  'internal_finalizer_failed',
]);
const EXPECTED_MODAL_WORKSPACE = 'omo-space';
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

async function expireStripeCheckoutSession(secretKey, sessionId) {
  if (!secretKey || !/^cs_(?:test|live)_[A-Za-z0-9_]+$/.test(String(sessionId || ''))) return false;
  try {
    const response = await fetch(`https://api.stripe.com/v1/checkout/sessions/${encodeURIComponent(sessionId)}/expire`, {
      method: 'POST',
      headers: stripeCheckoutHeaders(secretKey),
    });
    return response.ok;
  } catch {
    return false;
  }
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
  '/api/support/chat': { handler: handleSupportChat }, // Guest or Clerk identity; server derives the user ID
  '/api/submissions': { handler: handleSubmissions, methods: ['GET'] }, // Owner creator lifecycle list
  '/api/me': { handler: handleMe, methods: ['GET', 'POST'] }, // dashboard: balance + api key + usage
  '/api/topup': { handler: handleTopup }, // Stripe Checkout: {user_id, amount_usd}
  '/api/clerk-webhook': { handler: handleClerkWebhook }, // user.created → $5 grant
  '/api/pilot/claim': { handler: handlePilotClaim, methods: ['GET', 'POST'] }, // signed 99-cent pilot grant
};

async function handleSupportChat(request, env) {
  const authorization = String(request.headers.get('authorization') || '').trim();
  let userId;
  if (authorization) {
    const auth = await authenticateAccount(request, env, false);
    if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, cors(request, env));
    userId = auth.userId;
  } else {
    const ip = String(request.headers.get('cf-connecting-ip') || 'unknown');
    const userAgent = String(request.headers.get('user-agent') || '').slice(0, 256);
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(ip + '\0' + userAgent));
    userId = 'user_guest_' + Array.from(new Uint8Array(digest)).slice(0, 12)
      .map((byte) => byte.toString(16).padStart(2, '0')).join('');
  }
  const brokerUrl = String(env.OMO_SUPPORT_BROKER_URL || '').trim();
  const sharedSecret = String(env.OMO_SUPPORT_SHARED_SECRET || '').trim();
  if (!/^https:\/\//.test(brokerUrl) || !sharedSecret) {
    return json({ ok: false, error: 'support_not_configured' }, 503, cors(request, env));
  }
  let body;
  try { body = await request.json(); } catch { body = {}; }
  const sessionId = String(body.session_id || '').trim();
  const message = String(body.message || '').trim();
  const context = String(body.context || '').trim().slice(0, 1200);
  if (!/^[A-Za-z0-9_-]{8,100}$/.test(sessionId) || !message || message.length > 8000) {
    return json({ ok: false, error: 'invalid_support_message' }, 400, cors(request, env));
  }
  const contextualMessage = context ? `PAGE CONTEXT (untrusted): ${context}\n\nUSER PROBLEM:\n${message}` : message;
  const payload = JSON.stringify({ user_id: userId, session_id: sessionId, message: contextualMessage });
  const timestamp = String(Math.floor(Date.now() / 1000));
  const nonce = crypto.randomUUID().replace(/-/g, '');
  const signature = bytesToHex(await hmacSha256(
    new TextEncoder().encode(sharedSecret),
    `${timestamp}\n${nonce}\n${payload}`,
  ));
  let response;
  try {
    response = await fetch(brokerUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Omo-Timestamp': timestamp,
        'X-Omo-Nonce': nonce,
        'X-Omo-Signature': signature,
      },
      body: payload,
    });
  } catch {
    return json({ ok: false, error: 'support_unavailable' }, 502, cors(request, env));
  }
  const declaredLength = Number(response.headers.get('Content-Length') || 0);
  if (declaredLength > 16384) {
    return json({ ok: false, error: 'invalid_support_response' }, 502, cors(request, env));
  }
  let rawResponse = '';
  let result;
  try {
    rawResponse = await response.text();
    if (new TextEncoder().encode(rawResponse).length > 16384) throw new Error('oversized');
    result = JSON.parse(rawResponse);
  } catch { result = {}; }
  if (!response.ok) {
    return json({ ok: false, error: 'support_unavailable' }, response.status === 429 ? 429 : 502, cors(request, env));
  }
  if (result.profile !== 'omo-support' || result.mode !== 'support' || result.session_id !== sessionId
      || typeof result.message !== 'string' || result.message.length > 12000) {
    return json({ ok: false, error: 'invalid_support_response' }, 502, cors(request, env));
  }
  return json({ ok: true, message: result.message, session_id: sessionId, profile: 'omo-support', mode: 'support' }, 200, cors(request, env));
}

function dynamicRoute(pathname) {
  const internalSchema = /^\/api\/internal\/submissions\/schema$/.exec(pathname);
  if (internalSchema) return { handler: handleInternalSubmissionSchema, methods: ['POST'], internal: true };
  const internalMigration = /^\/api\/internal\/submissions\/migrate$/.exec(pathname);
  if (internalMigration) return { handler: handleInternalSubmissionMigration, methods: ['POST'], internal: true };
  const internalClaim = /^\/api\/internal\/submissions\/claim$/.exec(pathname);
  if (internalClaim) return { handler: handleInternalSubmissionClaim, methods: ['POST'], internal: true };
  const internalFinalizationClaim = /^\/api\/internal\/finalizations\/claim$/.exec(pathname);
  if (internalFinalizationClaim) return { handler: handleInternalFinalizationClaim, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationEligibility = /^\/api\/internal\/finalizations\/eligibility$/.exec(pathname);
  if (internalFinalizationEligibility) return { handler: handleInternalFinalizationEligibility, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationResumeCompleted = /^\/api\/internal\/finalizations\/resume-completed$/.exec(pathname);
  if (internalFinalizationResumeCompleted) return { handler: handleInternalFinalizationResumeCompleted, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationFailed = /^\/api\/internal\/finalizations\/failed$/.exec(pathname);
  if (internalFinalizationFailed) return { handler: handleInternalFinalizationFailed, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationResumeFailed = /^\/api\/internal\/finalizations\/resume-failed$/.exec(pathname);
  if (internalFinalizationResumeFailed) return { handler: handleInternalFinalizationResumeFailed, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationRecoveryPlan = /^\/api\/internal\/finalizations\/recovery-plan$/.exec(pathname);
  if (internalFinalizationRecoveryPlan) return { handler: handleInternalFinalizationRecoveryPlan, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationRecoverRolledBack = /^\/api\/internal\/finalizations\/recover-rolled-back$/.exec(pathname);
  if (internalFinalizationRecoverRolledBack) return { handler: handleInternalFinalizationRecoverRolledBack, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationRecoveryCandidate = /^\/api\/internal\/finalizations\/recovery-candidate$/.exec(pathname);
  if (internalFinalizationRecoveryCandidate) return { handler: handleInternalFinalizationRecoveryCandidate, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationResumeProbe = /^\/api\/internal\/finalizations\/resume-probe$/.exec(pathname);
  if (internalFinalizationResumeProbe) return { handler: handleInternalFinalizationResumeProbe, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationRegistrySlugs = /^\/api\/internal\/finalizations\/registry-slugs$/.exec(pathname);
  if (internalFinalizationRegistrySlugs) return { handler: handleInternalFinalizationRegistrySlugs, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationSchema = /^\/api\/internal\/finalizations\/schema$/.exec(pathname);
  if (internalFinalizationSchema) return { handler: handleInternalSubmissionSchema, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationSchemaMigration = /^\/api\/internal\/finalizations\/schema\/migrate$/.exec(pathname);
  if (internalFinalizationSchemaMigration) return { handler: handleInternalFinalizationSchemaMigration, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationReceiptSchema = /^\/api\/internal\/finalizations\/receipt-schema$/.exec(pathname);
  if (internalFinalizationReceiptSchema) return { handler: handleInternalFinalizationReceiptSchema, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationReceiptMigration = /^\/api\/internal\/finalizations\/receipt-schema\/migrate$/.exec(pathname);
  if (internalFinalizationReceiptMigration) return { handler: handleInternalFinalizationReceiptMigration, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationCanaryIdentity = /^\/api\/internal\/finalizations\/canary-identity$/.exec(pathname);
  if (internalFinalizationCanaryIdentity) return { handler: handleInternalFinalizationCanaryIdentity, methods: ['POST'], internal: true, finalizer: true };
  const internalFinalizationEffect = /^\/api\/internal\/finalizations\/(fin_[a-f0-9]{32})\/effects$/.exec(pathname);
  if (internalFinalizationEffect) return { handler: handleInternalFinalizationEffect, methods: ['POST'], params: { finalizationId: internalFinalizationEffect[1] }, internal: true, finalizer: true };
  const internalFinalizationStatus = /^\/api\/internal\/finalizations\/(fin_[a-f0-9]{32})\/status$/.exec(pathname);
  if (internalFinalizationStatus) return { handler: handleInternalFinalizationStatus, methods: ['POST'], params: { finalizationId: internalFinalizationStatus[1] }, internal: true, finalizer: true };
  const internalFinalizationPromote = /^\/api\/internal\/finalizations\/(fin_[a-f0-9]{32})\/promote$/.exec(pathname);
  if (internalFinalizationPromote) return { handler: handleInternalFinalizationPromote, methods: ['POST'], params: { finalizationId: internalFinalizationPromote[1] }, internal: true, finalizer: true };
  const internalFinalizationDetail = /^\/api\/internal\/finalizations\/(fin_[a-f0-9]{32})\/detail$/.exec(pathname);
  if (internalFinalizationDetail) return { handler: handleInternalFinalizationDetail, methods: ['POST'], params: { finalizationId: internalFinalizationDetail[1] }, internal: true, finalizer: true };
  const internalDetail = /^\/api\/internal\/submissions\/(sub_[A-Za-z0-9_-]{8,100})\/detail$/.exec(pathname);
  if (internalDetail) return { handler: handleInternalSubmissionDetail, methods: ['POST'], params: { submissionId: internalDetail[1] }, internal: true };
  const internalStatus = /^\/api\/internal\/submissions\/(sub_[A-Za-z0-9_-]{8,100})\/status$/.exec(pathname);
  if (internalStatus) return { handler: handleInternalSubmissionStatus, methods: ['POST'], params: { submissionId: internalStatus[1] }, internal: true };
  const internalResumeMergedRelease = /^\/api\/internal\/submissions\/(sub_[A-Za-z0-9_-]{8,100})\/resume-merged-release$/.exec(pathname);
  if (internalResumeMergedRelease) return { handler: handleInternalSubmissionResumeMergedRelease, methods: ['POST'], params: { submissionId: internalResumeMergedRelease[1] }, internal: true };
  const internalRuntime = /^\/api\/internal\/submissions\/(sub_[A-Za-z0-9_-]{8,100})\/runtime$/.exec(pathname);
  if (internalRuntime) return { handler: handleInternalSubmissionRuntime, methods: ['POST'], params: { submissionId: internalRuntime[1] }, internal: true };
  const internalDeployment = /^\/api\/internal\/submissions\/(sub_[A-Za-z0-9_-]{8,100})\/deployment$/.exec(pathname);
  if (internalDeployment) return { handler: handleInternalSubmissionDeployment, methods: ['POST'], params: { submissionId: internalDeployment[1] }, internal: true };
  const internalRelease = /^\/api\/internal\/submissions\/(sub_[A-Za-z0-9_-]{8,100})\/release$/.exec(pathname);
  if (internalRelease) return { handler: handleInternalSubmissionRelease, methods: ['POST'], params: { submissionId: internalRelease[1] }, internal: true };
  const internalDeployed = /^\/api\/internal\/submissions\/(sub_[A-Za-z0-9_-]{8,100})\/deployed$/.exec(pathname);
  if (internalDeployed) return { handler: handleInternalSubmissionDeployed, methods: ['POST'], params: { submissionId: internalDeployed[1] }, internal: true, finalizer: true };
  const submissionDetail = /^\/api\/submissions\/(sub_[A-Za-z0-9_-]{8,100})$/.exec(pathname);
  if (submissionDetail) return { handler: handleSubmissionDetail, methods: ['GET'], params: { submissionId: submissionDetail[1] } };
  const submissionApproval = /^\/api\/submissions\/(sub_[A-Za-z0-9_-]{8,100})\/approve$/.exec(pathname);
  if (submissionApproval) return { handler: handleSubmissionApproval, methods: ['POST'], params: { submissionId: submissionApproval[1] } };
  const submissionRetry = /^\/api\/submissions\/(sub_[A-Za-z0-9_-]{8,100})\/retry$/.exec(pathname);
  if (submissionRetry) return { handler: handleSubmissionRetry, methods: ['POST'], params: { submissionId: submissionRetry[1] } };
  const submissionRuntime = /^\/api\/submissions\/(sub_[A-Za-z0-9_-]{8,100})\/runtime$/.exec(pathname);
  if (submissionRuntime) return { handler: handleSubmissionRuntime, methods: ['PATCH'], params: { submissionId: submissionRuntime[1] } };
  const progress = /^\/api\/run\/(run_[A-Za-z0-9_-]{4,91})\/progress$/.exec(pathname);
  if (progress) return { handler: handleRunProgressWebhook, methods: ['POST'], params: { runId: progress[1] } };
  const status = /^\/api\/run\/(run_[A-Za-z0-9_-]{4,91})$/.exec(pathname);
  if (status) return { handler: handleRunStatus, methods: ['GET'], params: { runId: status[1] } };
  return null;
}

async function handleWorkerFetch(request, env) {
    const url = new URL(request.url);
    const route = ROUTES[url.pathname] || dynamicRoute(url.pathname);
    const isInternalPath = url.pathname.startsWith('/api/internal/');
    if (route && route.internal) {
      if (request.method === 'OPTIONS') return internalJson({ error: 'method_not_allowed' }, 405);
      const auth = route.finalizer
        ? authorizeReleaseFinalizer(request, env)
        : authorizeBuildWorker(request, env);
      if (!auth.ok) return internalJson({ error: auth.error }, auth.status);
      const methods = route.methods || ['POST'];
      if (!methods.includes(request.method)) return internalJson({ error: 'method_not_allowed' }, 405);
      try {
        return await route.handler(request, env, url, route.params || {});
      } catch {
        return internalJson({ error: 'internal_error' }, 500);
      }
    }
    if (isInternalPath) {
      const auth = authorizeBuildWorker(request, env);
      if (!auth.ok) return internalJson({ error: auth.error }, auth.status);
      return internalJson({ error: 'not_found' }, 404);
    }
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: cors(request, env) });
    }

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

export default { fetch: handleWorkerFetch, scheduled: handleBuilderSchedule };

async function handleBuilderSchedule(controller, env, ctx) {
  const phase = builderSchedulePhase(controller);
  const task = dispatchNextBuilderSubmission(env, phase).catch((error) => {
    console.error('builder_schedule_failed', String(error && error.message || error).slice(0, 120));
    throw error;
  });
  if (ctx && typeof ctx.waitUntil === 'function') ctx.waitUntil(task);
  else await task;
}

function builderSchedulePhase(controller) {
  const scheduledTime = Number(controller && controller.scheduledTime);
  if (!Number.isFinite(scheduledTime) || scheduledTime < 0) return 'build';
  return Math.floor(scheduledTime / 60_000) % 2 === 0 ? 'build' : 'verify_merged';
}

async function dispatchNextBuilderSubmission(env, phase = 'build') {
  if (!['build', 'verify_merged'].includes(phase)) throw new Error('invalid_builder_phase');
  const modalUrl = String(env.OMO_BUILDER_MODAL_URL || '').trim();
  const modalKey = String(env.OMO_BUILDER_MODAL_KEY || '').trim();
  const modalSecret = String(env.OMO_BUILDER_MODAL_SECRET || '').trim();
  const baseRevision = String(env.OMO_BUILDER_BASE_REVISION || '').trim();
  if (!/^https:\/\/[a-z0-9-]+(?:--[a-z0-9-]+)*\.modal\.run\/?$/.test(modalUrl) ||
      !modalKey || !modalSecret || !/^[0-9a-f]{40}$/.test(baseRevision)) {
    throw new Error('builder_dispatch_not_configured');
  }
  const candidate = await internalPeekBuilderSubmission(env, phase);
  if (!candidate) return { status: 'idle', phase };
  if ((phase === 'verify_merged') !== (candidate.status === 'ready_for_deploy')) {
    throw new Error('builder_phase_candidate_mismatch');
  }
  const dispatchHash = await sha256Hex(`omo-modal-builder-v3\0${phase}\0${candidate.id}\0${candidate.source_sha256}\0${baseRevision}`);
  const payload = {
    submission_id: candidate.id,
    slug: candidate.slug,
    source_sha256: candidate.source_sha256,
    dispatch_id: 'dispatch_' + dispatchHash.slice(0, 32),
    phase,
  };
  const response = await fetch(modalUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Modal-Key': modalKey,
      'Modal-Secret': modalSecret,
    },
    body: JSON.stringify(payload),
  });
  if (response.status !== 202 && response.status !== 200) {
    throw new Error(`builder_dispatch_rejected_${response.status}`);
  }
  return { status: 'dispatched', id: candidate.id, dispatch_id: payload.dispatch_id };
}

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

function validFinalizationLease(value, now = Date.now()) {
  const text = String(value || '');
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(text)
    && Number.isFinite(Date.parse(text)) && Date.parse(text) > now;
}

async function activeGeneratedCanaryClaim(request, env, slug) {
  const hosted = HOSTED_WORKER_SKILLS.get(slug);
  const executionKind = String(hosted && hosted.executor && hosted.executor.execution_kind || '');
  const runPriceCents = Number(hosted && hosted.run_price_cents);
  if (!hosted || !['pure_data', 'single_llm'].includes(executionKind)
      || !Number.isInteger(runPriceCents) || runPriceCents < 1 || runPriceCents > 10) {
    return false;
  }
  const targetSha = String(request.headers.get('x-omo-finalization-target-sha') || '').trim();
  const artifactHash = String(request.headers.get('x-omo-finalization-artifact-hash') || '').trim();
  const finalizationId = String(request.headers.get('x-omo-finalization-id') || '').trim();
  if (!/^[0-9a-f]{40}$/.test(targetSha) || !/^[0-9a-f]{64}$/.test(artifactHash)
      || !/^fin_[0-9a-f]{32}$/.test(finalizationId)) return false;

  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-production-canary-active-claim-v1',
      `SELECT 1 AS ok FROM submissions
       WHERE published_slug = $1 AND selected_runtime = 'worker-native'
         AND status = 'ready_for_deploy' AND release_phase = 'merged_verified'
         AND release_artifact_hash = $2 AND finalization_artifact_hash = $2
         AND finalization_target_sha = $3 AND finalization_status = 'verifying_public'
         AND finalization_id = $4
         AND CASE WHEN finalization_lease_expires_at ~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9][.][0-9]{3}Z$'
           THEN finalization_lease_expires_at > to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
           ELSE FALSE END
       LIMIT 1`,
      [slug, artifactHash, targetSha, finalizationId]
    ));
    return Boolean(result.rows && result.rows[0] && Number(result.rows[0].ok) === 1);
  }
  if (databaseKind(env) === 'd1') {
    const row = await env.BALANCE_DB.prepare(
      `SELECT 1 AS ok FROM submissions
       WHERE published_slug = ? AND selected_runtime = 'worker-native'
         AND status = 'ready_for_deploy' AND release_phase = 'merged_verified'
         AND release_artifact_hash = ? AND finalization_artifact_hash = ?
         AND finalization_target_sha = ? AND finalization_status = 'verifying_public'
         AND finalization_id = ?
         AND finalization_lease_expires_at GLOB '????-??-??T??:??:??.???Z'
         AND julianday(finalization_lease_expires_at) IS NOT NULL
         AND finalization_lease_expires_at > ?
       LIMIT 1`
    ).bind(slug, artifactHash, artifactHash, targetSha, finalizationId, new Date().toISOString()).first();
    return Boolean(row && Number(row.ok) === 1);
  }
  const now = Date.now();
  return [...mockSubmissions.values()].some((row) =>
    row && row.published_slug === slug && row.selected_runtime === 'worker-native'
    && row.status === 'ready_for_deploy' && row.release_phase === 'merged_verified'
    && row.release_artifact_hash === artifactHash && row.finalization_artifact_hash === artifactHash
    && row.finalization_target_sha === targetSha && row.finalization_status === 'verifying_public'
    && row.finalization_id === finalizationId
    && validFinalizationLease(row.finalization_lease_expires_at, now)
  );
}

async function productionCanaryRunAllowed(request, env, slug) {
  return PRODUCTION_CANARY_RUN_SLUGS.has(slug)
    || await activeGeneratedCanaryClaim(request, env, slug);
}

async function handleGenericRun(request, env) {
  let body;
  try { body = await request.json(); } catch { body = {}; }
  const slug = String(body.slug || '').trim();
  const fields = body.fields && typeof body.fields === 'object' && !Array.isArray(body.fields) ? body.fields : {};
  const hostedWorker = HOSTED_WORKER_SKILLS.get(slug) || null;
  const registeredHostedModal = HOSTED_MODAL_SKILLS.get(slug) || null;
  // A generated hosted registration supersedes the legacy nonpaid de Mello
  // bridge. The explicit flag exists only for bounded rollback/legacy tests.
  const isDemello = slug === DEMELLO_SLUG
    && (!registeredHostedModal || String(env.DEMELLO_LEGACY_EXECUTOR || '') === '1');
  const hostedModal = isDemello ? null : registeredHostedModal;
  const hosted = hostedWorker || hostedModal;
  const isHostedWorker = Boolean(hostedWorker);
  const isHostedModal = Boolean(hostedModal);
  const isHosted = Boolean(hosted);
  // Hosted workflows can spend Modal/provider budget and are never anonymous,
  // including in otherwise zero-config local mode.
  const real = isRealMode(env) || isDemello || isHosted;
  const listing = isHosted ? null : SERVER_CATALOG.get(slug);
  if (!slug) return json({ error: 'Send slug.' }, 400, cors());
  if (real && !isHosted && !listing) return json({ error: 'unknown_catalog_slug' }, 404, cors());

  let userId = '';
  let authMethod = 'demo';
  if (real) {
    const productionCanaryRun = await productionCanaryRunAllowed(request, env, slug);
    const auth = await authenticateAccount(request, env, true, productionCanaryRun);
    if (!auth.ok) return json({ error: auth.error }, auth.status, cors());
    userId = auth.userId;
    authMethod = auth.method;
    if (userId === 'user_prod_label_normalizer_canary_v1' && !productionCanaryRun) {
      return json({ error: 'production_canary_scope_violation' }, 403, cors());
    }
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
    if (isHostedModal) {
      const configError = hostedModalConfigError(env, hosted);
      if (configError) return json({ error: configError }, 503, cors());
    } else {
      const configError = await hostedWorkerConfigError(env, hosted);
      if (configError) return json({ error: configError }, 503, cors());
    }
    const candidate = body.input && typeof body.input === 'object' && !Array.isArray(body.input)
      ? body.input : fields;
    const errors = validateSchemaValue(candidate, hosted.input_schema);
    if (errors.length) return json({ error: 'invalid_hosted_input', details: errors.slice(0, 8) }, 422, cors());
    if (
      isHostedWorker
      && new TextEncoder().encode(stableStringify(candidate)).length > hosted.executor.max_input_bytes
    ) {
      return json({ error: 'hosted_worker_input_limit_exceeded' }, 422, cors());
    }
    hostedInput = candidate;
  }

  const systemPrompt = listing ? listing.systemPrompt : String(body.system_prompt || '').trim();
  const maxTokens = listing
    ? listing.maxTokens
    : boundedInt(body.max_tokens, 1, 8000, Number(env.DEMO_MAX_TOKENS_RUN || 4000));
  const model = listing ? listing.model : (env.LLM_MODEL || 'deepseek-v4-flash');
  if (!isHosted && !systemPrompt) return json({ error: 'Send slug and system_prompt.' }, 400, cors());

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
    reservedCents = isHosted
      ? runCostCents
      : (listing ? runCostCents : Math.round(runPrice(llmWorkflow(systemPrompt, maxTokens, model)) * 100));
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
    if (runRequest && (isDemello || isHostedModal)) {
      await putRunProgress(env, {
        run_id: runId, user_id: userId, phase: 'reserved', progress_pct: 1,
        progress_source: 'derived', modal_status: 'reserved',
        modal_status_url: isHostedModal ? hostedModalEndpoint(env, hosted) : demelloModalStatusUrl(env, runId),
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
  if (isHostedModal) {
    return dispatchHostedModalRun(env, hosted, {
      runRequest, runId, userId, hostedInput, costUsd, balanceAfterDebit, authMethod,
    });
  }
  if (isHostedWorker) {
    return dispatchHostedWorkerRun(env, hosted, {
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
    const stringLength = Array.from(value).length;
    if (schema.minLength != null && stringLength < schema.minLength) errors.push(`${path} is too short.`);
    if (schema.maxLength != null && stringLength > schema.maxLength) errors.push(`${path} is too long.`);
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

function hostedWorkerPrompt(executor, input) {
  if (typeof executor?.workflow_instructions === 'string' && executor.workflow_instructions.trim()) {
    return stableStringify({
      workflow_instructions: executor.workflow_instructions,
      input,
    });
  }
  return `Input JSON:\n${JSON.stringify(input)}\n\nRun the reviewed workflow using only this JSON input. Return only the complete JSON object required by the output schema.`;
}

function hostedWorkerUsage(executor, rawUsage) {
  const usage = rawUsage && typeof rawUsage === 'object' && !Array.isArray(rawUsage) ? rawUsage : {};
  const promptCandidate = Number(usage.prompt_tokens ?? usage.input_tokens ?? 0);
  const completionCandidate = Number(usage.completion_tokens ?? usage.output_tokens ?? 0);
  const promptTokens = Number.isInteger(promptCandidate) && promptCandidate >= 0 ? promptCandidate : 0;
  const completionTokens = Number.isInteger(completionCandidate) && completionCandidate >= 0 ? completionCandidate : 0;
  const rate = LLM_RATES[executor.model] || null;
  const estimatedCostUsd = rate
    ? (promptTokens / 1e6) * Number(rate.input) + (completionTokens / 1e6) * Number(rate.output)
    : 0;
  return {
    provider: executor.provider,
    model: executor.model,
    llm_calls: 1,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    estimated_cost_usd: Number.isFinite(estimatedCostUsd) && estimatedCostUsd >= 0
      ? +estimatedCostUsd.toFixed(12)
      : 0,
  };
}

function hostedWorkerPublicOutput(hosted, runId, modelOutput, rawUsage) {
  return {
    ...modelOutput,
    run_id: runId,
    status: 'completed',
    workflow_version: `${hosted.container_slug}@${hosted.executor.workflow_version}`,
    usage: hostedWorkerUsage(hosted.executor, rawUsage),
  };
}

async function dispatchHostedWorkerRun(env, hosted, context) {
  if (hosted.executor.execution_kind === HOSTED_WORKER_PURE_DATA_EXECUTION_KIND) {
    return dispatchHostedPureDataRun(env, hosted, context);
  }
  const {
    runRequest, runId, userId, hostedInput, costUsd, balanceAfterDebit, authMethod,
  } = context;
  const llm = await callHostedWorkerProvider(
    env,
    hosted.executor,
    hostedWorkerPrompt(hosted.executor, hostedInput),
  );
  if (llm.error) {
    return failHostedWorkerRun(env, hosted, runRequest.row, 'worker_native_provider_error', 502);
  }
  const parsed = parseStrictJsonObject(llm.content);
  if (!parsed.ok) {
    return failHostedWorkerRun(env, hosted, runRequest.row, 'worker_native_invalid_json', 502);
  }
  const modelOutputErrors = validateSchemaValue(parsed.value, hosted.model_output_schema);
  if (modelOutputErrors.length) {
    return failHostedWorkerRun(env, hosted, runRequest.row, 'worker_native_invalid_output', 502);
  }
  const publicOutput = hostedWorkerPublicOutput(hosted, runId, parsed.value, llm.usage);
  const outputErrors = validateSchemaValue(publicOutput, hosted.output_schema);
  if (outputErrors.length) {
    return failHostedWorkerRun(env, hosted, runRequest.row, 'worker_native_invalid_output', 502);
  }
  const result = {
    ok: true, slug: hosted.slug, run_id: runId, status: 'completed', state: 'succeeded',
    phase: 'delivered', progress_pct: 100, status_url: `/api/run/${encodeURIComponent(runId)}`,
    quoted_cost_usd: Number(hosted.run_price_cents) / 100,
    billed_amount_usd: Number(runRequest.row.cost_cents) / 100,
    cost_usd: costUsd, balance: +(balanceAfterDebit / 100).toFixed(2),
    auth: authMethod, output: publicOutput,
  };
  const ownsSuccess = await finishRunRequest(env, runId, 'succeeded', result, 200);
  if (!ownsSuccess) {
    const terminal = await getRunRequestById(env, runId);
    if (terminal) {
      const authoritative = terminalRunResult(terminal);
      return json(authoritative.body, authoritative.status, cors());
    }
    return json({ ok: false, error: 'run_terminal_state_unknown', run_id: runId }, 409, cors());
  }
  return json(result, 200, cors());
}

function hostedPureDataUsage() {
  return {
    provider: 'worker-pure-data',
    model: 'omo.pure-data/v1',
    llm_calls: 0,
    prompt_tokens: 0,
    completion_tokens: 0,
    estimated_cost_usd: 0,
  };
}

async function dispatchHostedPureDataRun(env, hosted, context) {
  const { runRequest, runId, hostedInput, costUsd, balanceAfterDebit, authMethod } = context;
  let modelOutput;
  try {
    modelOutput = executePureDataProgram(hosted.executor.program, hostedInput);
  } catch (error) {
    const isRuntimeViolation = error instanceof PureDataRuntimeError;
    const code = isRuntimeViolation
      ? String(error.code || 'INVALID_VALUE').toLowerCase()
      : 'internal_error';
    return failHostedWorkerRun(
      env, hosted, runRequest.row, `worker_native_pure_data_${code}`, isRuntimeViolation ? 422 : 500,
    );
  }
  const modelOutputErrors = validateSchemaValue(modelOutput, hosted.model_output_schema);
  if (modelOutputErrors.length) {
    return failHostedWorkerRun(env, hosted, runRequest.row, 'worker_native_invalid_output', 502);
  }
  const publicOutput = {
    ...modelOutput,
    run_id: runId,
    status: 'completed',
    workflow_version: `${hosted.container_slug}@${hosted.executor.workflow_version}`,
    usage: hostedPureDataUsage(),
  };
  const outputErrors = validateSchemaValue(publicOutput, hosted.output_schema);
  if (outputErrors.length) {
    return failHostedWorkerRun(env, hosted, runRequest.row, 'worker_native_invalid_output', 502);
  }
  const result = {
    ok: true, slug: hosted.slug, run_id: runId, status: 'completed', state: 'succeeded',
    phase: 'delivered', progress_pct: 100, status_url: `/api/run/${encodeURIComponent(runId)}`,
    quoted_cost_usd: Number(hosted.run_price_cents) / 100,
    billed_amount_usd: Number(runRequest.row.cost_cents) / 100,
    cost_usd: costUsd, balance: +(balanceAfterDebit / 100).toFixed(2),
    auth: authMethod, output: publicOutput,
  };
  const ownsSuccess = await finishRunRequest(env, runId, 'succeeded', result, 200);
  if (!ownsSuccess) {
    const terminal = await getRunRequestById(env, runId);
    if (terminal) {
      const authoritative = terminalRunResult(terminal);
      return json(authoritative.body, authoritative.status, cors());
    }
    return json({ ok: false, error: 'run_terminal_state_unknown', run_id: runId }, 409, cors());
  }
  return json(result, 200, cors());
}

async function hostedWorkerConfigError(env, hosted) {
  const executor = hosted && hosted.executor;
  if (!executor || typeof executor !== 'object') return 'hosted_worker_executor_missing';
  if (!hosted.model_output_schema || typeof hosted.model_output_schema !== 'object' || Array.isArray(hosted.model_output_schema)) return 'hosted_worker_model_output_schema_missing';
  if (!String(executor.workflow_version || '').trim()) return 'hosted_worker_workflow_version_missing';

  if (executor.execution_kind === HOSTED_WORKER_PURE_DATA_EXECUTION_KIND) {
    if (executor.spec_version !== HOSTED_WORKER_PURE_DATA_SPEC_VERSION) return 'hosted_worker_executor_spec_unsupported';
    if (executor.operation !== HOSTED_WORKER_PURE_DATA_OPERATION) return 'hosted_worker_operation_unsupported';
    if (!executor.program || typeof executor.program !== 'object' || Array.isArray(executor.program)) return 'hosted_worker_pure_data_program_missing';
    if (!/^sha256:[0-9a-f]{64}$/.test(String(executor.program_digest || ''))) return 'hosted_worker_pure_data_digest_invalid';
    try {
      validatePureDataProgram(executor.program);
    } catch {
      return 'hosted_worker_pure_data_program_invalid';
    }
    if (await pureDataProgramDigest(executor.program) !== executor.program_digest) return 'hosted_worker_pure_data_digest_mismatch';
    return '';
  }

  if (executor.execution_kind !== HOSTED_WORKER_LLM_EXECUTION_KIND) return 'hosted_worker_execution_kind_unsupported';
  if (executor.spec_version !== HOSTED_WORKER_LLM_SPEC_VERSION) return 'hosted_worker_executor_spec_unsupported';
  if (executor.operation !== HOSTED_WORKER_LLM_OPERATION) return 'hosted_worker_operation_unsupported';
  if (!HOSTED_WORKER_PROVIDERS.has(executor.provider)) return 'hosted_worker_provider_unsupported';
  const provider = HOSTED_WORKER_PROVIDER_DESCRIPTORS.get(executor.provider);
  if (!provider) return 'hosted_worker_provider_unsupported';
  if (!String(executor.model || '').trim()) return 'hosted_worker_model_missing';
  if (!String(executor.system_prompt || '').trim()) return 'hosted_worker_system_prompt_missing';
  if (!Number.isInteger(executor.max_output_tokens) || executor.max_output_tokens < 1 || executor.max_output_tokens > 8000) return 'hosted_worker_max_output_tokens_unbounded';
  if (!Number.isInteger(executor.max_input_bytes) || executor.max_input_bytes < 1 || executor.max_input_bytes > 65536) return 'hosted_worker_max_input_bytes_unbounded';
  if (!Number.isFinite(Number(executor.temperature)) || Number(executor.temperature) < 0 || Number(executor.temperature) > 1) return 'hosted_worker_temperature_unbounded';
  if (!Number.isInteger(executor.timeout_seconds) || executor.timeout_seconds < 1 || executor.timeout_seconds > 120) return 'hosted_worker_timeout_unbounded';
  if (!String(env[provider.api_key_env] || '').trim()) return 'hosted_worker_provider_key_missing';
  const baseUrl = hostedWorkerProviderBaseUrl(env, provider);
  if (baseUrl.error) return baseUrl.error;
  return '';
}

async function callHostedWorkerProvider(env, executor, userPrompt) {
  const provider = HOSTED_WORKER_PROVIDER_DESCRIPTORS.get(executor.provider);
  const baseUrl = hostedWorkerProviderBaseUrl(env, provider);
  if (!provider || baseUrl.error) return { error: 'provider_config_invalid' };
  const apiKey = String(env[provider.api_key_env] || '');
  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
  const timeout = controller ? setTimeout(() => controller.abort(), Number(executor.timeout_seconds) * 1000) : null;
  try {
    const response = await fetch(`${baseUrl.value}/chat/completions`, {
      method: 'POST',
      signal: controller ? controller.signal : undefined,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
        'User-Agent': 'Omo-Hosted-Worker/1.0',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        model: executor.model,
        max_tokens: executor.max_output_tokens,
        temperature: Number(executor.temperature),
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: executor.system_prompt },
          { role: 'user', content: userPrompt },
        ],
      }),
    });
    if (!response.ok) return { error: 'provider_http_status' };
    const textResult = await readResponseTextBounded(response, HOSTED_WORKER_MAX_RESPONSE_BYTES);
    if (textResult.error) return { error: textResult.error };
    let data;
    try { data = JSON.parse(textResult.text); } catch { return { error: 'provider_invalid_envelope' }; }
    const content = data && data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content;
    if (typeof content !== 'string' || !content.trim()) return { error: 'provider_empty_content' };
    const usage = data && data.usage && typeof data.usage === 'object' && !Array.isArray(data.usage) ? data.usage : {};
    return { content, usage };
  } catch {
    return { error: 'provider_fetch_failed' };
  } finally {
    if (timeout) clearTimeout(timeout);
  }
}

function hostedWorkerProviderBaseUrl(env, provider) {
  if (!provider) return { error: 'hosted_worker_provider_unsupported' };
  const raw = String(env[provider.base_url_env] || provider.default_base_url || '').trim();
  if (!raw) return { error: 'hosted_worker_provider_base_url_invalid' };
  let parsed;
  try { parsed = new URL(raw); } catch { return { error: 'hosted_worker_provider_base_url_invalid' }; }
  const hasNonDefaultPort = Boolean(parsed.port) && !((parsed.protocol === 'https:' && parsed.port === '443') || (parsed.protocol === 'http:' && parsed.port === '80'));
  if (
    parsed.protocol !== 'https:' ||
    parsed.origin !== provider.origin ||
    parsed.pathname.replace(/\/+$/, '') !== provider.path ||
    parsed.username ||
    parsed.password ||
    parsed.search ||
    parsed.hash ||
    hasNonDefaultPort
  ) {
    return { error: 'hosted_worker_provider_base_url_invalid' };
  }
  return { value: `${provider.origin}${provider.path}` };
}

async function readResponseTextBounded(response, maxBytes) {
  if (response.body && typeof response.body.getReader === 'function') {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let bytes = 0;
    let text = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > maxBytes) {
        try { await reader.cancel(); } catch {}
        return { error: 'provider_response_too_large' };
      }
      text += decoder.decode(value, { stream: true });
    }
    text += decoder.decode();
    return { text };
  }
  const text = await response.text();
  if (new TextEncoder().encode(text).length > maxBytes) return { error: 'provider_response_too_large' };
  return { text };
}

function parseStrictJsonObject(raw) {
  const text = String(raw || '').trim();
  if (!text || text[0] !== '{' || text[text.length - 1] !== '}') return { ok: false };
  try {
    const value = JSON.parse(text);
    if (!value || typeof value !== 'object' || Array.isArray(value)) return { ok: false };
    return { ok: true, value };
  } catch {
    return { ok: false };
  }
}

async function failHostedWorkerRun(env, hosted, row, reason, httpStatus = 502) {
  const current = await getRunRequestById(env, row.run_id);
  if (current && current.state === 'succeeded') {
    const terminal = terminalRunResult(current);
    return json(terminal.body, terminal.status, cors());
  }
  if (current) row = current;
  const response = {
    ok: false, error: 'run_failed', reason, slug: hosted.slug, run_id: row.run_id,
    status: 'failed', state: 'refunded', phase: 'failed', progress_pct: 0,
    quoted_cost_usd: Number(hosted.run_price_cents) / 100, billed_amount_usd: 0,
    status_url: `/api/run/${encodeURIComponent(row.run_id)}`,
  };
  const ownsRefund = await finishRunRequest(env, row.run_id, 'refunded', response, httpStatus);
  if (ownsRefund && await runDebitExists(env, row.run_id)) {
    await refundRunCredits(env, row.user_id, Number(row.cost_cents), row.run_id);
  }
  const terminal = await getRunRequestById(env, row.run_id);
  if (terminal) {
    const result = terminalRunResult(terminal);
    return json(result.body, result.status, cors());
  }
  return json(response, httpStatus, cors());
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

function hostedModalHeaders(env, hosted, ownerId = '') {
  const credentials = hostedModalCredentials(env, hosted);
  const headers = { 'Modal-Key': credentials.id, 'Modal-Secret': credentials.secret, Accept: 'application/json' };
  if (hosted.protocol === 'owner-scoped-async-v1' && ownerId) headers['X-Omo-Owner-Id'] = String(ownerId);
  return headers;
}

function hostedModalRemote(hosted, upstream) {
  const callId = String(upstream && upstream.call_id || '');
  const resultUrl = String(upstream && upstream.result_url || '');
  if (!/^fc-[A-Za-z0-9_-]+$/.test(callId)) return null;
  if (hosted.protocol === 'owner-scoped-async-v1') {
    const matched = /^\/v1\/runs\/(run-[0-9a-f]{32})\?call_id=(fc-[A-Za-z0-9_-]+)&access_token=([A-Za-z0-9_-]{32,200})$/.exec(resultUrl);
    if (!matched || matched[2] !== callId || String(upstream.run_id || '') !== matched[1]) return null;
    return { call_id: callId, run_id: matched[1], result_url: resultUrl };
  }
  if (!/^\/v1\/runs\/fc-[A-Za-z0-9_-]+$/.test(resultUrl)) return null;
  return { call_id: callId, result_url: resultUrl };
}

function hostedModalStoredRemote(hosted, value) {
  if (!value || typeof value !== 'object') return null;
  return hostedModalRemote(hosted, {
    call_id: value.call_id,
    run_id: value.run_id,
    result_url: value.result_url,
  });
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
      headers: { ...hostedModalHeaders(env, hosted, userId), 'Content-Type': 'application/json' },
      body: JSON.stringify(hostedInput),
    });
  } catch {
    return failHostedModalRun(env, hosted, runRequest.row, 'hosted_modal_dispatch_unavailable', 502);
  }
  let upstream = {};
  try { upstream = await response.json(); } catch { upstream = {}; }
  const remote = hostedModalRemote(hosted, upstream);
  if (response.status !== 202 || !remote) {
    return failHostedModalRun(env, hosted, runRequest.row, `hosted_modal_dispatch_${response.status}`, 502);
  }
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
  remote = hostedModalStoredRemote(hosted, remote);
  if (!remote) {
    return failHostedModalRun(env, hosted, row, 'hosted_modal_poll_contract_missing', 502, true);
  }
  let response;
  try {
    response = await fetch(hostedModalEndpoint(env, hosted) + remote.result_url, { headers: hostedModalHeaders(env, hosted, row.user_id) });
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
  if (
    response.status === 200 && hosted.protocol === 'owner-scoped-async-v1'
    && Object.prototype.hasOwnProperty.call(upstream, 'run_id')
    && upstream.run_id !== remote.run_id
  ) {
    outputErrors.push('owner-scoped upstream run identity mismatch');
  }
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
  const row = await getRunRequestById(env, params.runId);
  const productionCanaryRun = Boolean(row)
    && await productionCanaryRunAllowed(request, env, row.slug);
  const auth = await authenticateAccount(
    request, env, true, productionCanaryRun
  );
  if (!auth.ok) return json({ error: auth.error }, auth.status, cors());
  if (!row || row.user_id !== auth.userId) return json({ error: 'run_not_found' }, 404, cors());
  if (auth.userId === 'user_prod_label_normalizer_canary_v1' && !productionCanaryRun) {
    return json({ error: 'run_not_found' }, 404, cors());
  }
  const hosted = row.slug === DEMELLO_SLUG && String(env.DEMELLO_LEGACY_EXECUTOR || '') === '1'
    ? null : HOSTED_MODAL_SKILLS.get(row.slug);
  if (hosted) {
    const result = await refreshHostedModalRun(env, hosted, row);
    return json(result.body, result.status, cors());
  }
  if (row.slug === DEMELLO_SLUG) {
    const result = await refreshDemelloRun(env, row);
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

  let checkoutStage = 'stripe_request';
  let stripeSessionId = '';
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
    stripeSessionId = data.id;
    checkoutStage = 'purchase_record';
    await recordPendingPurchase(env, data.id, listing, email);
    return json({ url: checkoutUrl.toString() }, 200, cors());
  } catch (e) {
    const sessionExpired = checkoutStage === 'purchase_record'
      ? await expireStripeCheckoutSession(secretKey, stripeSessionId)
      : false;
    console.error('checkout session failed', {
      stage: checkoutStage,
      code: String(e && e.code || '').slice(0, 80),
      message: String(e && e.message || 'unknown error').slice(0, 240),
      session_expired: sessionExpired,
    });
    if (checkoutStage === 'purchase_record') {
      return json({ error: 'purchase recording unavailable', session_expired: sessionExpired }, 503, cors());
    }
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
    let auth = await authenticateAccount(request, env, false);
    if (!auth.ok) {
      const apiKey = String(request.headers.get('x-api-key') || '').trim();
      const apiKeyOwner = /^omo_[0-9a-f]{32}$/.test(apiKey) ? await userIdForHashedApiKey(env, apiKey) : '';
      if (apiKeyOwner === 'user_prod_label_normalizer_canary_v1') {
        auth = { ok: true, userId: apiKeyOwner, method: 'production_canary' };
      }
    }
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
  const runtimePreference = readRuntimePreference(body, 'auto');
  if (runtimePreference.error) {
    return json({ ok: false, error: runtimePreference.error, message: runtimePreference.message }, 400, cors());
  }
  const requestedRuntime = runtimePreference.value;
  if (!requestedRuntime) {
    return json({ ok: false, error: 'invalid_runtime_preference', message: 'runtime_preference must be auto, worker-native, or modal-hosted.' }, 400, cors());
  }

  const parsed = parseSubmissionMarkdown(body.content);
  if (parsed.error) return json({ ok: false, ...parsed }, 400, cors());
  if (userId === 'user_prod_label_normalizer_canary_v1' && !PRODUCTION_CANARY_SUBMISSION_SLUGS.has(parsed.slug)) {
    return json({ error: 'production_canary_scope_violation' }, 403, cors());
  }
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
    requestedRuntime,
  });
  if (stored.preference_conflict) {
    return json({
      ok: false,
      error: 'runtime_preference_conflict',
      id: stored.id,
      status: stored.status,
      runtime_preference: stored.requested_runtime,
      compatibility: 'pending_review',
      message: 'This workflow source is already queued with a different runtime preference.',
    }, 409, cors());
  }
  return json({
    ok: true,
    id: stored.id,
    slug: parsed.slug,
    status: stored.status,
    runtime_preference: stored.requested_runtime || requestedRuntime,
    compatibility: 'pending_review',
    changed: !stored.duplicate,
    duplicate: stored.duplicate,
    message: stored.duplicate ? 'This workflow is already in your queue.' : 'Queued for Omo review and hosting.',
  }, 202, cors());
}

async function handleSubmissionRuntime(request, env, _url, params) {
  const auth = await authenticateAccount(request, env, false);
  if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, cors());
  let body;
  try { body = await request.json(); } catch { body = {}; }
  const runtimePreference = readRuntimePreference(body, '');
  if (runtimePreference.error) {
    return json({ ok: false, error: runtimePreference.error, message: runtimePreference.message }, 400, cors());
  }
  const requestedRuntime = runtimePreference.value;
  if (!requestedRuntime) {
    return json({ ok: false, error: 'invalid_runtime_preference', message: 'runtime_preference must be auto, worker-native, or modal-hosted.' }, 400, cors());
  }
  const result = await updateSubmissionRuntime(env, auth.userId, params.submissionId, requestedRuntime);
  if (result.status === 'not_found') return json({ ok: false, error: 'submission_not_found' }, 404, cors());
  if (result.status === 'immutable') {
    return json({ ok: false, error: 'submission_runtime_immutable', id: params.submissionId, status: result.row.status }, 409, cors());
  }
  return json({
    ok: true,
    id: result.row.id,
    status: result.row.status,
    runtime_preference: result.row.requested_runtime,
    compatibility: 'pending_review',
    changed: result.changed,
  }, 200, cors());
}

async function handleSubmissions(request, env, url) {
  const auth = await authenticateAccount(request, env, false);
  if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, cors());
  const limit = boundedInt(url.searchParams && url.searchParams.get('limit'), 1, 50, 20);
  const rawCursor = String(url.searchParams && url.searchParams.get('cursor') || '').trim();
  const cursor = parseSubmissionCursor(rawCursor);
  if (rawCursor && !cursor) return json({ ok: false, error: 'invalid_submission_cursor' }, 400, cors());
  const rows = await listSubmissions(env, auth.userId, limit + 1, cursor);
  const hasMore = rows.length > limit;
  const pageRows = rows.slice(0, limit);
  return json({
    ok: true,
    limit,
    has_more: hasMore,
    next_cursor: hasMore ? submissionCursor(pageRows[pageRows.length - 1]) : null,
    submissions: pageRows.map(publicSubmission),
  }, 200, cors());
}

async function handleSubmissionDetail(request, env, _url, params) {
  const auth = await authenticateAccount(request, env, false);
  if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, cors());
  const row = await getSubmissionForOwner(env, auth.userId, params.submissionId);
  if (!row) return json({ ok: false, error: 'submission_not_found' }, 404, cors());
  return json({ ok: true, submission: publicSubmission(row) }, 200, cors());
}

async function handleSubmissionApproval(request, env, _url, params) {
  const auth = await authenticateAccount(request, env, false);
  if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, cors(request, env));
  const approved = await approveExactMatchSlugCollision(env, auth.userId, params.submissionId);
  if (approved.status === 'not_found') return json({ ok: false, error: 'submission_not_found' }, 404, cors(request, env));
  if (approved.status === 'not_approvable') {
    return json({ ok: false, error: 'submission_not_approvable' }, 409, cors(request, env));
  }
  return json({
    ok: true,
    approved: true,
    submission: publicSubmission(approved.row),
  }, 200, cors(request, env));
}

async function handleSubmissionRetry(request, env, _url, params) {
  let auth = await authenticateAccount(request, env, false);
  if (!auth.ok) {
    const apiKey = String(request.headers.get('x-api-key') || '').trim();
    const apiKeyOwner = /^omo_[0-9a-f]{32}$/.test(apiKey) ? await userIdForHashedApiKey(env, apiKey) : '';
    if (apiKeyOwner === 'user_prod_label_normalizer_canary_v1') {
      auth = { ok: true, userId: apiKeyOwner, method: 'production_canary' };
    }
  }
  if (!auth.ok) return json({ ok: false, error: auth.error }, auth.status, cors(request, env));
  let retried = { status: 'not_found' };
  if (auth.method === 'production_canary') {
    for (const requiredSlug of PRODUCTION_CANARY_SUBMISSION_SLUGS) {
      retried = await retryReviewedGatedBuildFailure(env, auth.userId, params.submissionId, requiredSlug);
      if (retried.status !== 'not_found') break;
    }
  } else {
    retried = await retryReviewedGatedBuildFailure(env, auth.userId, params.submissionId);
  }
  if (retried.status === 'not_found') return json({ ok: false, error: 'submission_not_found' }, 404, cors(request, env));
  if (retried.status === 'not_retryable') {
    return json({ ok: false, error: 'submission_not_retryable' }, 409, cors(request, env));
  }
  return json({
    ok: true,
    retried: true,
    submission: publicSubmission(retried.row),
  }, 200, cors(request, env));
}

function parseSubmissionCursor(value) {
  const text = String(value || '').trim();
  if (!text) return null;
  if (text.length > 180 || text.split('~').length !== 2) return null;
  const [createdAt, id] = text.split('~');
  if (!safeTimestamp(createdAt) || Number.isNaN(new Date(createdAt).getTime()) || !safeSubmissionId(id)) return null;
  return { created_at: createdAt, id };
}

function submissionCursor(row) {
  const createdAt = safeTimestamp(row && row.created_at);
  const id = safeSubmissionId(row && row.id);
  return createdAt && id ? `${createdAt}~${id}` : null;
}

function publicSubmission(row) {
  const selectedRuntime = safeRuntime(row.selected_runtime);
  const status = safeSubmissionStatus(row.status);
  return {
    id: String(row.id || ''),
    name: String(row.name || ''),
    slug: String(row.slug || ''),
    visibility: 'public',
    status,
    requested_runtime: normalizeRequestedRuntime(row.requested_runtime || 'auto') || 'auto',
    selected_runtime: selectedRuntime,
    runtime_policy: safeRuntimePolicy(row.runtime_policy),
    compatibility: safeCompatibility(row.runtime_compatibility),
    source_sha256: safeSha256(row.source_sha256 || row.sourceSha256),
    failure_code: safePublicFailureCode(row.failure_code || row.failureCode),
    workflow_version: safeText(row.workflow_version, 160),
    published_slug: safeSlug(row.published_slug),
    created_at: safeTimestamp(row.created_at),
    updated_at: safeTimestamp(row.updated_at),
    deployed_at: safeTimestamp(row.deployed_at),
    approved_at: safeTimestamp(row.approved_at),
    approved_by: safeUserId(row.approved_by),
    approval_reason: safeApprovalReason(row.approval_reason),
    build_evidence: safeBuildEvidence(row.build_evidence),
    release: safeReleaseSummary(row),
  };
}

function safeText(value, maxLength) {
  const text = String(value || '').trim();
  return text ? text.slice(0, maxLength) : null;
}

function safeTimestamp(value) {
  const text = String(value || '').trim();
  return text && text.length <= 64 ? text : null;
}

function safeSha256(value) {
  const text = String(value || '').trim().toLowerCase();
  return SAFE_SHA256_RE.test(text) ? text : null;
}

function safeSlug(value) {
  const text = String(value || '').trim();
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(text) && text.length <= 100 ? text : null;
}

function safeRuntime(value) {
  const text = String(value || '').trim();
  return text === 'worker-native' || text === 'modal-hosted' ? text : null;
}

function safeSubmissionStatus(value) {
  const text = String(value || '').trim();
  return ['queued', 'processing', 'needs_review', 'ready_for_deploy', 'ready_for_publish', 'deployed', 'failed'].includes(text)
    ? text
    : 'queued';
}

function safePublicFailureCode(value) {
  const code = String(value || '').trim().toLowerCase();
  return SAFE_FAILURE_RE.test(code) ? code : null;
}

function safeUserId(value) {
  const text = String(value || '').trim();
  return USER_ID_RE.test(text) ? text : null;
}

function safeApprovalReason(value) {
  const text = String(value || '').trim();
  return text === 'exact_source_slug_collision' ? text : null;
}

function safeRuntimePolicy(value) {
  const text = String(value || '').trim();
  return /^[a-z][a-z0-9_:-]{2,127}$/.test(text) ? text : null;
}

function parseJsonObject(value) {
  if (value && typeof value === 'object' && !Array.isArray(value)) return value;
  if (typeof value !== 'string' || !value.trim()) return {};
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function safeCompatibility(value) {
  const parsed = parseJsonObject(value);
  return {
    recommended: safeRuntime(parsed.recommended),
    requested: normalizeRequestedRuntime(parsed.requested || '') || null,
    compatible: typeof parsed.compatible === 'boolean' ? parsed.compatible : null,
  };
}

function safeBuildEvidence(value) {
  const parsed = parseJsonObject(value);
  const checks = Array.isArray(parsed.checks)
    ? parsed.checks.map((item) => String(item || '').trim()).filter((item) => /^[a-z][a-z0-9_:-]{1,63}$/.test(item)).slice(0, 20)
    : [];
  const evidence = { checks };
  if (Number.isSafeInteger(Number(parsed.duration_ms)) && Number(parsed.duration_ms) >= 0) {
    evidence.duration_ms = Number(parsed.duration_ms);
  }
  if (safeSha256(parsed.source_sha256)) evidence.source_sha256 = safeSha256(parsed.source_sha256);
  if (safeText(parsed.generated_at, 64)) evidence.generated_at = safeText(parsed.generated_at, 64);
  return evidence;
}

function safeGithubUrl(value, kind) {
  const text = String(value || '').trim();
  if (!SAFE_GITHUB_URL_RE.test(text)) return null;
  return text.includes(`/${kind}/`) ? text : null;
}

function safeGitSha(value) {
  const text = String(value || '').trim().toLowerCase();
  return SAFE_GIT_SHA_RE.test(text) ? text : null;
}

function safeReleaseBranch(value) {
  const text = String(value || '').trim();
  return SAFE_RELEASE_BRANCH_RE.test(text) ? text : null;
}

function safeModalEndpoint(value) {
  const text = String(value || '').trim().replace(/\/+$/, '');
  try {
    const url = new URL(text);
    if (url.protocol !== 'https:' || url.username || url.password || url.pathname !== '/' ||
        url.search || url.hash || !url.hostname.endsWith('.modal.run') ||
        !url.hostname.startsWith(`${EXPECTED_MODAL_WORKSPACE}--`)) {
      return null;
    }
    return text;
  } catch {
    return null;
  }
}

function safeCanaryEvidence(value) {
  const parsed = parseJsonObject(value);
  const status = String(parsed.status || '').trim();
  const checkedAt = safeTimestamp(parsed.checked_at || parsed.timestamp);
  const canary = {};
  if (status === 'passed' || status === 'failed') canary.status = status;
  if (checkedAt) canary.checked_at = checkedAt;
  return Object.keys(canary).length ? canary : null;
}

function safePromotionEvidence(value) {
  const parsed = parseJsonObject(value);
  const checkedAt = safeTimestamp(parsed.checked_at);
  if (String(parsed.status || '').trim() !== 'live' || !checkedAt) return null;
  const evidence = { status: 'live', checked_at: checkedAt };
  for (const name of ['R1', 'R2', 'R3', 'R4']) {
    const gate = parseJsonObject(parsed[name]);
    const status = String(gate.status || '').trim();
    const allowed = name === 'R4' ? ['published', 'excluded_premium'] : ['passed'];
    if (!allowed.includes(status)) return null;
    evidence[name] = { status };
  }
  return evidence;
}

function safeReleaseSummary(row) {
  const phase = String(row.release_phase || '').trim();
  if (!RELEASE_PHASES.has(phase)) return null;
  const summary = { phase };
  const issueUrl = safeGithubUrl(row.release_issue_url, 'issues');
  const prUrl = safeGithubUrl(row.release_pr_url, 'pull');
  const branch = safeReleaseBranch(row.release_branch);
  const headSha = safeGitSha(row.release_head_sha);
  const mergeSha = safeGitSha(row.release_merge_sha);
  const artifactHash = safeSha256(row.release_artifact_hash);
  const modalApp = safeSlug(row.modal_app);
  const modalUrl = safeModalEndpoint(row.modal_url);
  const canary = safeCanaryEvidence(row.canary_evidence);
  const promotionEvidence = safePromotionEvidence(row.promotion_evidence);
  if (issueUrl) summary.issue_url = issueUrl;
  if (prUrl) summary.pr_url = prUrl;
  if (Number.isSafeInteger(Number(row.release_pr_number)) && Number(row.release_pr_number) > 0) {
    summary.pr_number = Number(row.release_pr_number);
  }
  if (branch) summary.branch = branch;
  if (headSha) summary.head_sha = headSha;
  if (mergeSha) summary.merge_sha = mergeSha;
  if (artifactHash) summary.artifact_hash = artifactHash;
  if (modalApp) summary.modal_app = modalApp;
  if (modalUrl) summary.modal_url = modalUrl;
  if (canary) summary.canary = canary;
  if (promotionEvidence) summary.promotion_evidence = promotionEvidence;
  return summary;
}

// ── Private build-worker bridge ─────────────────────────────────────────
// These endpoints are intentionally bearer-only and same-zone/private. They
// never set CORS headers and never return owner ids or source except on claim.

const REQUIRED_SUBMISSIONS_COLUMNS = [
  'id',
  'user_id',
  'name',
  'slug',
  'content',
  'source_sha256',
  'requested_runtime',
  'selected_runtime',
  'runtime_policy',
  'runtime_compatibility',
  'workflow_version',
  'published_slug',
  'build_evidence',
  'build_claimed_at',
  'build_attempts',
  'deployment_metadata',
  'release_phase',
  'release_issue_url',
  'release_pr_url',
  'release_pr_number',
  'release_branch',
  'release_head_sha',
  'release_merge_sha',
  'release_artifact_hash',
  'modal_app',
  'modal_url',
  'canary_evidence',
  'promotion_evidence',
  'finalization_id',
  'finalization_status',
  'finalization_target_sha',
  'finalization_source_sha256',
  'finalization_head_sha',
  'finalization_merge_sha',
  'finalization_artifact_hash',
  'finalization_claimed_at',
  'finalization_lease_expires_at',
  'finalization_attempts',
  'finalization_failure_code',
  'finalization_modal_receipt',
  'finalization_worker_receipt',
  'finalization_recovery_receipt',
  'automation_updated_at',
  'status',
  'failure_code',
  'created_at',
  'updated_at',
  'approved_at',
  'approved_by',
  'approval_reason',
  'deployed_at',
];

const CREATE_SUBMISSIONS_TABLE_SQL = `CREATE TABLE IF NOT EXISTS submissions (
  id            TEXT PRIMARY KEY,
  user_id       TEXT NOT NULL,
  name          TEXT NOT NULL,
  slug          TEXT NOT NULL,
  content       TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  requested_runtime TEXT NOT NULL DEFAULT 'auto' CHECK (requested_runtime IN ('auto', 'worker-native', 'modal-hosted')),
  selected_runtime  TEXT CHECK (selected_runtime IN ('worker-native', 'modal-hosted')),
  runtime_policy    TEXT,
  runtime_compatibility TEXT,
  workflow_version  TEXT,
  published_slug    TEXT,
  build_evidence    TEXT,
  build_claimed_at  TEXT,
  build_attempts    INTEGER NOT NULL DEFAULT 0,
  deployment_metadata TEXT,
  release_phase   TEXT,
  release_issue_url TEXT,
  release_pr_url  TEXT,
  release_pr_number INTEGER,
  release_branch  TEXT,
  release_head_sha TEXT,
  release_merge_sha TEXT,
  release_artifact_hash TEXT,
  modal_app       TEXT,
  modal_url       TEXT,
  canary_evidence TEXT,
  promotion_evidence TEXT,
  finalization_id TEXT,
  finalization_status TEXT,
  finalization_target_sha TEXT,
  finalization_source_sha256 TEXT,
  finalization_head_sha TEXT,
  finalization_merge_sha TEXT,
  finalization_artifact_hash TEXT,
  finalization_claimed_at TEXT,
  finalization_lease_expires_at TEXT,
  finalization_attempts INTEGER NOT NULL DEFAULT 0,
  finalization_failure_code TEXT,
  finalization_modal_receipt TEXT,
  finalization_worker_receipt TEXT,
  finalization_recovery_receipt TEXT,
  automation_updated_at TEXT,
  status        TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'needs_review', 'ready_for_deploy', 'ready_for_publish', 'deployed', 'failed')),
  failure_code  TEXT,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL,
  approved_at   TEXT,
  approved_by   TEXT,
  approval_reason TEXT,
  deployed_at   TEXT,
  UNIQUE (user_id, source_sha256)
)`;

const SUBMISSIONS_SCHEMA_MIGRATIONS = [
  ['create_table', CREATE_SUBMISSIONS_TABLE_SQL],
  ['id', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS id TEXT'],
  ['user_id', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS user_id TEXT'],
  ['name', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS name TEXT'],
  ['slug', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS slug TEXT'],
  ['content', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS content TEXT'],
  ['source_sha256', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS source_sha256 TEXT'],
  ['requested_runtime', "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS requested_runtime TEXT NOT NULL DEFAULT 'auto' CHECK (requested_runtime IN ('auto', 'worker-native', 'modal-hosted'))"],
  ['selected_runtime', "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS selected_runtime TEXT CHECK (selected_runtime IN ('worker-native', 'modal-hosted'))"],
  ['runtime_policy', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS runtime_policy TEXT'],
  ['runtime_compatibility', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS runtime_compatibility TEXT'],
  ['workflow_version', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS workflow_version TEXT'],
  ['published_slug', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS published_slug TEXT'],
  ['build_evidence', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS build_evidence TEXT'],
  ['build_claimed_at', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS build_claimed_at TEXT'],
  ['build_attempts', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS build_attempts INTEGER NOT NULL DEFAULT 0'],
  ['deployment_metadata', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS deployment_metadata TEXT'],
  ['release_phase', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_phase TEXT'],
  ['release_issue_url', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_issue_url TEXT'],
  ['release_pr_url', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_pr_url TEXT'],
  ['release_pr_number', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_pr_number INTEGER'],
  ['release_branch', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_branch TEXT'],
  ['release_head_sha', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_head_sha TEXT'],
  ['release_merge_sha', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_merge_sha TEXT'],
  ['release_artifact_hash', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS release_artifact_hash TEXT'],
  ['modal_app', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS modal_app TEXT'],
  ['modal_url', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS modal_url TEXT'],
  ['canary_evidence', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS canary_evidence TEXT'],
  ['promotion_evidence', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS promotion_evidence TEXT'],
  ['finalization_id', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_id TEXT'],
  ['finalization_status', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_status TEXT'],
  ['finalization_target_sha', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_target_sha TEXT'],
  ['finalization_source_sha256', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_source_sha256 TEXT'],
  ['finalization_head_sha', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_head_sha TEXT'],
  ['finalization_merge_sha', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_merge_sha TEXT'],
  ['finalization_artifact_hash', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_artifact_hash TEXT'],
  ['finalization_claimed_at', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_claimed_at TEXT'],
  ['finalization_lease_expires_at', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_lease_expires_at TEXT'],
  ['finalization_attempts', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_attempts INTEGER NOT NULL DEFAULT 0'],
  ['finalization_failure_code', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_failure_code TEXT'],
  ['finalization_modal_receipt', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_modal_receipt TEXT'],
  ['finalization_worker_receipt', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_worker_receipt TEXT'],
  ['finalization_recovery_receipt', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS finalization_recovery_receipt TEXT'],
  ['automation_updated_at', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS automation_updated_at TEXT'],
  ['status', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS status TEXT'],
  ['failure_code', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS failure_code TEXT'],
  ['created_at', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS created_at TEXT'],
  ['updated_at', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS updated_at TEXT'],
  ['approved_at', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS approved_at TEXT'],
  ['approved_by', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS approved_by TEXT'],
  ['approval_reason', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS approval_reason TEXT'],
  ['deployed_at', 'ALTER TABLE submissions ADD COLUMN IF NOT EXISTS deployed_at TEXT'],
  ['idx_submissions_status_created', 'CREATE INDEX IF NOT EXISTS idx_submissions_status_created\n  ON submissions (status, created_at)'],
  ['idx_submissions_user_created', 'CREATE INDEX IF NOT EXISTS idx_submissions_user_created\n  ON submissions (user_id, created_at DESC)'],
];

const FINALIZATION_RECEIPT_COLUMNS = [
  'finalization_modal_receipt',
  'finalization_worker_receipt',
  'finalization_recovery_receipt',
];
const FINALIZATION_RECEIPT_MIGRATIONS = SUBMISSIONS_SCHEMA_MIGRATIONS.filter(([name]) =>
  FINALIZATION_RECEIPT_COLUMNS.includes(name)
);
const FINALIZATION_SCHEMA_COLUMNS = [
  'promotion_evidence', 'finalization_id', 'finalization_status', 'finalization_target_sha',
  'finalization_source_sha256', 'finalization_head_sha', 'finalization_merge_sha',
  'finalization_artifact_hash', 'finalization_claimed_at', 'finalization_lease_expires_at',
  'finalization_attempts', 'finalization_failure_code', 'finalization_modal_receipt',
  'finalization_worker_receipt', 'finalization_recovery_receipt', 'automation_updated_at',
];
const FINALIZATION_SCHEMA_MIGRATIONS = SUBMISSIONS_SCHEMA_MIGRATIONS.filter(([name]) =>
  FINALIZATION_SCHEMA_COLUMNS.includes(name)
);

const SUBMISSIONS_TABLE_EXISTS_SQL = `
SELECT EXISTS (
  SELECT 1
  FROM information_schema.tables
  WHERE table_schema = 'public' AND table_name = 'submissions'
) AS table_exists`;

const SUBMISSIONS_COLUMNS_SQL = `
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'submissions'
  AND column_name = ANY($1::text[])
ORDER BY array_position($1::text[], column_name)`;

function internalJson(obj, status) {
  return new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json' } });
}

function constantTimeEquals(expected, supplied) {
  const a = String(expected || '');
  const b = String(supplied || '');
  const max = Math.max(a.length, b.length);
  let diff = a.length ^ b.length;
  for (let i = 0; i < max; i += 1) {
    diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }
  return diff === 0;
}

function authorizeBuildWorker(request, env) {
  const token = String(env && env.BUILD_WORKER_TOKEN || '').trim();
  if (!token) return { ok: false, status: 503, error: 'build_worker_not_configured' };
  const authorization = String(request.headers.get('authorization') || '');
  const match = /^Bearer\s+(.+)$/i.exec(authorization);
  const supplied = match ? match[1] : '';
  return constantTimeEquals(token, supplied)
    ? { ok: true }
    : { ok: false, status: 401, error: 'unauthorized' };
}

function authorizeReleaseFinalizer(request, env) {
  const token = String(env && env.RELEASE_FINALIZER_TOKEN || '').trim();
  const builderToken = String(env && env.BUILD_WORKER_TOKEN || '').trim();
  if (!token || !builderToken) {
    return { ok: false, status: 503, error: 'release_finalizer_not_configured' };
  }
  if (constantTimeEquals(token, builderToken)) {
    return { ok: false, status: 503, error: 'release_finalizer_not_distinct' };
  }
  const authorization = String(request.headers.get('authorization') || '');
  const match = /^Bearer\s+(.+)$/i.exec(authorization);
  const supplied = match ? match[1] : '';
  return constantTimeEquals(token, supplied)
    ? { ok: true }
    : { ok: false, status: 401, error: 'unauthorized' };
}

async function readInternalJson(request) {
  let raw = '';
  try { raw = await request.text(); } catch { raw = ''; }
  if (new TextEncoder().encode(raw).length > MAX_INTERNAL_BODY_BYTES) {
    return { error: 'body_too_large', status: 413 };
  }
  if (!raw.trim()) return { body: {} };
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return { error: 'invalid_json', status: 400 };
    }
    return { body: parsed };
  } catch {
    return { error: 'invalid_json', status: 400 };
  }
}

async function readStrictEmptyInternalJson(request, maxBytes) {
  let raw = '';
  try { raw = await request.text(); } catch { raw = ''; }
  if (new TextEncoder().encode(raw).length > maxBytes) {
    return { error: 'body_too_large', status: 413 };
  }
  if (!raw.trim()) return { error: 'invalid_json', status: 400 };
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed) || Object.keys(parsed).length !== 0) {
      return { error: 'invalid_json', status: 400 };
    }
    return { body: parsed };
  } catch {
    return { error: 'invalid_json', status: 400 };
  }
}

function safeSubmissionId(value) {
  const text = String(value || '').trim();
  return SUBMISSION_ID_RE.test(text) ? text : '';
}

function safeFailureCode(value) {
  const code = String(value || 'internal_error').trim().toLowerCase();
  return SAFE_FAILURE_RE.test(code) ? code : 'internal_error';
}

function validSubmissionClaimSource(row) {
  const content = String(row && row.content || '');
  return safeSubmissionId(row && row.id) &&
    safeSlug(row && row.slug) &&
    safeSha256(row && (row.source_sha256 || row.sourceSha256)) &&
    content.length > 0 &&
    new TextEncoder().encode(content).length <= MAX_SUBMISSION_BYTES;
}

function staleSubmissionClaim(row, now = Date.now()) {
  if (!row || !row.build_claimed_at) return false;
  const claimedAt = Date.parse(String(row.build_claimed_at));
  return Number.isFinite(claimedAt) && now - claimedAt > SUBMISSION_CLAIM_LEASE_SECONDS * 1000;
}

function internalClaimRow(row) {
  if (!row) return null;
  const sourceSha256 = safeSha256(row.source_sha256 || row.sourceSha256);
  const requestedRuntime = normalizeRequestedRuntime(row.requested_runtime || row.requestedRuntime || 'auto') || 'auto';
  const priorStatus = safeSubmissionStatus(row.prior_status || row.priorStatus);
  const content = String(row.content || '');
  if (!safeSubmissionId(row.id) || !safeSlug(row.slug) || !sourceSha256 || !content ||
      new TextEncoder().encode(content).length > MAX_SUBMISSION_BYTES ||
      !['queued', 'needs_review', 'ready_for_deploy', 'processing'].includes(priorStatus)) {
    return null;
  }
  return {
    id: String(row.id),
    name: String(row.name || '').slice(0, 120),
    slug: String(row.slug),
    content,
    source_sha256: sourceSha256,
    requested_runtime: requestedRuntime,
    prior_status: priorStatus,
  };
}

function internalDetailRow(row) {
  if (!row) return null;
  const sourceSha256 = safeSha256(row.source_sha256 || row.sourceSha256);
  const rawSelectedRuntime = String(row.selected_runtime || row.selectedRuntime || '').trim();
  const selectedRuntime = safeRuntime(rawSelectedRuntime);
  const slug = safeSlug(row.slug);
  const status = safeSubmissionStatus(row.status);
  if (!safeSubmissionId(row.id) || !slug || !sourceSha256 || !status || (rawSelectedRuntime && !selectedRuntime)) return null;
  const detail = {
    id: String(row.id),
    slug,
    status,
    source_sha256: sourceSha256,
  };
  if (selectedRuntime) detail.selected_runtime = selectedRuntime;
  const workflowVersion = safeText(row.workflow_version, 160);
  const publishedSlug = safeSlug(row.published_slug);
  const buildEvidence = safeBuildEvidence(row.build_evidence);
  if (workflowVersion && SAFE_WORKFLOW_VERSION_RE.test(workflowVersion)) detail.workflow_version = workflowVersion;
  if (publishedSlug) detail.published_slug = publishedSlug;
  if (buildEvidence.checks.length) detail.build_evidence = buildEvidence;
  const release = safeReleaseSummary(row);
  if (release) {
    detail.release_phase = release.phase;
    if (release.issue_url) detail.release_issue_url = release.issue_url;
    if (release.pr_url) detail.release_pr_url = release.pr_url;
    if (release.pr_number) detail.release_pr_number = release.pr_number;
    if (release.branch) detail.release_branch = release.branch;
    if (release.head_sha) detail.release_head_sha = release.head_sha;
    if (release.merge_sha) detail.release_merge_sha = release.merge_sha;
    if (release.artifact_hash) detail.release_artifact_hash = release.artifact_hash;
    if (release.modal_app) detail.modal_app = release.modal_app;
    if (release.modal_url) detail.modal_url = release.modal_url;
    if (release.canary) detail.canary_evidence = release.canary;
    if (release.promotion_evidence) detail.promotion_evidence = release.promotion_evidence;
  }
  return detail;
}

function validateRuntimeDecision(body) {
  const effective = safeRuntime(body.effective || body.selected_runtime);
  const reason = safeRuntimePolicy(body.reason || body.runtime_policy);
  const recommended = safeRuntime(body.recommended);
  const requested = normalizeRequestedRuntime(body.requested || '') || null;
  if (!effective || !reason) return null;
  return {
    effective,
    reason,
    recommended,
    requested,
    compatible: typeof body.compatible === 'boolean' ? body.compatible : null,
  };
}

function validateDeploymentBody(body) {
  const status = String(body.status || '').trim();
  const publishedSlug = safeSlug(body.published_slug);
  const workflowVersion = String(body.workflow_version || '').trim();
  const evidence = safeBuildEvidence(body.build_evidence);
  if (status !== 'ready_for_deploy' ||
      !publishedSlug || !SAFE_WORKFLOW_VERSION_RE.test(workflowVersion) ||
      !evidence.checks.length) {
    return null;
  }
  return { status, publishedSlug, workflowVersion, evidence };
}

function validateReleaseBody(body) {
  const phase = String(body.release_phase || body.phase || '').trim();
  const sourceSha256 = safeSha256(body.source_sha256);
  const artifactHash = safeSha256(body.artifact_hash);
  const issueUrl = safeGithubUrl(body.issue_url, 'issues');
  const prUrl = safeGithubUrl(body.pr_url, 'pull');
  const branch = safeReleaseBranch(body.branch);
  const headSha = safeGitSha(body.head_sha);
  if (!RELEASE_PHASES.has(phase) || !sourceSha256 || !artifactHash || !issueUrl || !prUrl || !branch || !headSha) {
    return null;
  }
  const release = {
    phase,
    sourceSha256,
    artifactHash,
    issueUrl,
    prUrl,
    branch,
    headSha,
    prNumber: Number(body.pr_number),
    mergeSha: safeGitSha(body.merge_sha),
    modalApp: safeSlug(body.modal_app),
    modalUrl: safeModalEndpoint(body.modal_url),
    canary: safeCanaryEvidence(body.canary || body.canary_evidence),
    promotionEvidence: safePromotionEvidence(body.release_gates || body.promotion_evidence),
  };
  if (!Number.isSafeInteger(release.prNumber) || release.prNumber < 1) return null;
  if ((phase === 'merged_verified' || phase === 'promoted') && !release.mergeSha) return null;
  if (phase === 'promoted' && !release.promotionEvidence) return null;
  if (body.modal_url && !release.modalUrl) return null;
  return release;
}

async function handleInternalSubmissionClaim(request, env) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const requestedId = parsed.body.id == null ? '' : safeSubmissionId(parsed.body.id);
  if (parsed.body.id != null && !requestedId) return internalJson({ error: 'invalid_submission_id' }, 400);
  const row = await internalClaimSubmission(env, {
    id: requestedId || null,
    includeReview: Boolean(parsed.body.include_review),
    includeReady: Boolean(parsed.body.include_ready),
  });
  if (!row) return new Response(null, { status: 204, headers: { 'Content-Type': 'application/json' } });
  const submission = internalClaimRow(row);
  if (!submission) return internalJson({ error: 'invalid_claim_row' }, 500);
  return internalJson({ ok: true, submission }, 200);
}

async function handleInternalFinalizationClaim(request, env) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  if (Object.keys(parsed.body).sort().join(',') !== 'target_sha,targets') {
    return internalJson({ error: 'invalid_finalization_claim' }, 400);
  }
  const targetSha = safeGitSha(parsed.body.target_sha);
  const targets = safeFinalizationTargets(parsed.body.targets);
  if (!targetSha || !targets) return internalJson({ error: 'invalid_finalization_claim' }, 400);
  const finalization = await internalClaimFinalization(env, targetSha, targets);
  if (!finalization) return new Response(null, { status: 204, headers: { 'Content-Type': 'application/json' } });
  return internalJson({ ok: true, finalization }, 200);
}

async function handleInternalFinalizationEligibility(request, env) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  if (Object.keys(parsed.body).sort().join(',') !== 'target_sha,targets') {
    return internalJson({ error: 'invalid_finalization_eligibility' }, 400);
  }
  const targetSha = safeGitSha(parsed.body.target_sha);
  const targets = safeFinalizationTargets(parsed.body.targets);
  if (!targetSha || !targets) return internalJson({ error: 'invalid_finalization_eligibility' }, 400);
  return internalJson({ ok: true, eligibility: await internalFinalizationEligibility(env, targetSha, targets) }, 200);
}

function safeFinalizationTargets(value) {
  if (!Array.isArray(value) || value.length < 1 || value.length > 20) return null;
  const targets = [];
  const seen = new Set();
  for (const item of value) {
    if (!item || typeof item !== 'object' || Array.isArray(item)
        || Object.keys(item).sort().join(',') !== 'slug,source_sha256') return null;
    const slug = safeSlug(item.slug);
    const sourceSha256 = safeSha256(item.source_sha256);
    if (!slug || !sourceSha256 || seen.has(slug)) return null;
    seen.add(slug);
    targets.push({ slug, source_sha256: sourceSha256 });
  }
  return targets.sort((a, b) => a.slug.localeCompare(b.slug));
}

async function handleInternalFinalizationResumeCompleted(request, env) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  if (Object.keys(parsed.body).sort().join(',') !== 'target_sha') {
    return internalJson({ error: 'invalid_completed_finalization_resume' }, 400);
  }
  const targetSha = safeGitSha(parsed.body.target_sha);
  if (!targetSha) return internalJson({ error: 'invalid_target_sha' }, 400);
  const finalization = completedFinalizationRow(await internalResumeCompletedFinalization(env, targetSha));
  if (!finalization) return new Response(null, { status: 204, headers: { 'Content-Type': 'application/json' } });
  return internalJson({ ok: true, finalization }, 200);
}

async function handleInternalFinalizationFailed(request, env) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  if (Object.keys(parsed.body).sort().join(',') !== 'target_sha') {
    return internalJson({ error: 'invalid_failed_finalization_inspection' }, 400);
  }
  const targetSha = safeGitSha(parsed.body.target_sha);
  if (!targetSha) return internalJson({ error: 'invalid_target_sha' }, 400);
  const finalization = failedFinalizationRow(await internalInspectFailedFinalization(env, targetSha));
  if (!finalization) return new Response(null, { status: 204, headers: { 'Content-Type': 'application/json' } });
  return internalJson({ ok: true, finalization }, 200);
}

async function handleInternalFinalizationResumeFailed(request, env) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  if (Object.keys(parsed.body).sort().join(',') !== 'finalization_id,target_sha') {
    return internalJson({ error: 'invalid_failed_finalization_resume' }, 400);
  }
  const targetSha = safeGitSha(parsed.body.target_sha);
  const finalizationId = /^fin_[0-9a-f]{32}$/.test(String(parsed.body.finalization_id || ''))
    ? String(parsed.body.finalization_id) : null;
  if (!targetSha || !finalizationId) return internalJson({ error: 'invalid_recovery_generation' }, 400);
  const requeued = await internalResumeFailedFinalization(env, targetSha, finalizationId);
  return requeued
    ? internalJson({ ok: true, status: 'ready_for_deploy' }, 200)
    : internalJson({ error: 'invalid_transition' }, 409);
}

async function readRecoveryTarget(request, error) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return { response: internalJson({ error: parsed.error }, parsed.status) };
  if (Object.keys(parsed.body).sort().join(',') !== 'finalization_id,target_sha') {
    return { response: internalJson({ error }, 400) };
  }
  const targetSha = safeGitSha(parsed.body.target_sha);
  const finalizationId = /^fin_[0-9a-f]{32}$/.test(String(parsed.body.finalization_id || ''))
    ? String(parsed.body.finalization_id) : null;
  return targetSha && finalizationId
    ? { targetSha, finalizationId }
    : { response: internalJson({ error: 'invalid_recovery_generation' }, 400) };
}

async function handleInternalFinalizationRecoveryPlan(request, env) {
  const parsed = await readRecoveryTarget(request, 'invalid_recovery_plan');
  if (parsed.response) return parsed.response;
  const candidate = recoveryCandidate(await internalInspectFailedFinalization(
    env, parsed.targetSha, parsed.finalizationId
  ));
  return candidate
    ? internalJson({ ok: true, recovery: recoveryPlan(candidate) }, 200)
    : new Response(null, { status: 204, headers: { 'Content-Type': 'application/json' } });
}

async function handleInternalFinalizationRecoverRolledBack(request, env) {
  const parsed = await readRecoveryTarget(request, 'invalid_rollback_recovery');
  if (parsed.response) return parsed.response;
  const recovered = await internalRecoverRolledBackFinalization(
    env, parsed.targetSha, parsed.finalizationId
  );
  return recovered
    ? internalJson({ ok: true, status: 'ready_for_deploy' }, 200)
    : internalJson({ error: 'invalid_transition' }, 409);
}

async function handleInternalFinalizationRecoveryCandidate(request, env) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const recovery = await internalAutomaticRecoveryCandidate(env);
  return recovery
    ? internalJson({ ok: true, recovery }, 200)
    : new Response(null, { status: 204, headers: { 'Content-Type': 'application/json' } });
}

async function handleInternalFinalizationResumeProbe(request, env) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const stage = await inspectFinalizationResumeQuery(env);
  return internalJson({ ok: true, stage }, 200);
}

async function handleInternalFinalizationRegistrySlugs(request, env) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const slugs = await internalRequiredRegistrySlugs(env);
  return internalJson({ ok: true, slugs }, 200);
}

async function handleInternalFinalizationReceiptMigration(request, env) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const applied = await applyFinalizationReceiptMigration(env);
  return internalJson({ ok: true, applied }, 200);
}

async function handleInternalFinalizationSchemaMigration(request, env) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const applied = await applyFinalizationSchemaMigration(env);
  return internalJson({ ok: true, applied }, 200);
}

async function handleInternalFinalizationReceiptSchema(request, env) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const schema = await inspectFinalizationReceiptSchema(env);
  return internalJson({ ok: true, ...schema }, 200);
}

async function handleInternalFinalizationCanaryIdentity(request, env) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const apiKey = String(env.PRODUCTION_CANARY_API_KEY || '').trim();
  if (String(env.ENVIRONMENT || '') !== 'production' || !/^omo_[0-9a-f]{32}$/.test(apiKey)) {
    return internalJson({ error: 'production_canary_not_configured' }, 503);
  }
  const provisioned = await ensureProductionCanaryIdentity(env, apiKey);
  return internalJson({
    ok: true, user_id: 'user_prod_label_normalizer_canary_v1', created: provisioned.created,
  }, 200);
}

async function handleInternalFinalizationEffect(request, env, _url, params) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  if (Object.keys(parsed.body).sort().join(',') !== 'operation,receipt,target_sha') {
    return internalJson({ error: 'invalid_finalization_effect' }, 400);
  }
  const operation = String(parsed.body.operation || '').trim();
  const targetSha = safeGitSha(parsed.body.target_sha);
  const receipt = safeDeploymentReceipt(parsed.body.receipt, operation, targetSha);
  if (!targetSha || !receipt) return internalJson({ error: 'invalid_finalization_effect' }, 400);
  const result = await internalRecordFinalizationEffect(env, params.finalizationId, operation, targetSha, receipt);
  if (result === 'conflict') return internalJson({ error: 'effect_conflict' }, 409);
  if (result !== 'recorded' && result !== 'replayed') return internalJson({ error: 'invalid_transition' }, 409);
  return internalJson({ ok: true, finalization_id: params.finalizationId, operation, replayed: result === 'replayed' }, 200);
}

async function handleInternalFinalizationStatus(request, env, _url, params) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const status = String(parsed.body.status || '').trim();
  const expectedKeys = status === 'failed' ? 'failure_code,status,target_sha' : 'status,target_sha';
  if (Object.keys(parsed.body).sort().join(',') !== expectedKeys) {
    return internalJson({ error: 'invalid_finalization_status' }, 400);
  }
  const targetSha = safeGitSha(parsed.body.target_sha);
  const requestedFailure = status === 'failed' ? String(parsed.body.failure_code || '').trim() : '';
  const failureCode = FINALIZATION_FAILURE_CODES.has(requestedFailure) ? requestedFailure : null;
  if (!targetSha || !['deploying_modal', 'deploying_worker', 'verifying_public', 'failed'].includes(status) ||
      (status === 'failed' && !failureCode)) {
    return internalJson({ error: 'invalid_finalization_status' }, 400);
  }
  const updated = await internalSetFinalizationStatus(env, params.finalizationId, targetSha, status, failureCode);
  return updated
    ? internalJson({ ok: true, finalization_id: params.finalizationId, status }, 200)
    : internalJson({ error: 'invalid_transition' }, 409);
}

async function handleInternalFinalizationPromote(request, env, _url, params) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  if (Object.keys(parsed.body).sort().join(',') !== 'release_gates,target_sha') {
    return internalJson({ error: 'invalid_finalization_promotion' }, 400);
  }
  const targetSha = safeGitSha(parsed.body.target_sha);
  const promotionEvidence = safePromotionEvidence(parsed.body.release_gates);
  if (!targetSha || !promotionEvidence) {
    return internalJson({ error: 'invalid_finalization_promotion' }, 400);
  }
  const updated = await internalPromoteFinalization(
    env, params.finalizationId, targetSha, promotionEvidence
  );
  return updated
    ? internalJson({ ok: true, finalization_id: params.finalizationId, status: 'completed' }, 200)
    : internalJson({ error: 'invalid_transition' }, 409);
}

async function handleInternalFinalizationDetail(request, env, _url, params) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const finalization = finalizationDetailRow(await internalGetFinalization(env, params.finalizationId));
  return finalization
    ? internalJson({ ok: true, finalization }, 200)
    : internalJson({ error: 'not_found' }, 404);
}

async function handleInternalSubmissionDetail(request, env, _url, params) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const row = await internalGetSubmissionDetail(env, params.submissionId);
  if (!row) return internalJson({ error: 'not_found' }, 404);
  const submission = internalDetailRow(row);
  if (!submission) return internalJson({ error: 'invalid_detail_row' }, 500);
  return internalJson({ ok: true, submission }, 200);
}

async function handleInternalSubmissionStatus(request, env, _url, params) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const status = String(parsed.body.status || '').trim();
  if (status === 'ready_for_publish') {
    return internalJson({ error: 'trusted_finalizer_required' }, 409);
  }
  if (!['needs_review', 'ready_for_deploy', 'failed'].includes(status)) {
    return internalJson({ error: 'invalid_status' }, 400);
  }
  const updated = await internalSetSubmissionStatus(env, params.submissionId, status, parsed.body.failure_code);
  return updated ? internalJson({ ok: true, id: params.submissionId, status }, 200)
    : internalJson({ error: 'invalid_transition' }, 409);
}

async function handleInternalSubmissionResumeMergedRelease(request, env, _url, params) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  if (Object.keys(parsed.body).sort().join(',') !== 'merge_sha') {
    return internalJson({ error: 'invalid_resume_payload' }, 400);
  }
  const mergeSha = safeGitSha(parsed.body.merge_sha);
  if (!mergeSha) return internalJson({ error: 'invalid_merge_sha' }, 400);
  const updated = await internalResumeMergedRelease(env, params.submissionId, mergeSha);
  return updated
    ? internalJson({ ok: true, id: params.submissionId, status: 'ready_for_deploy' }, 200)
    : internalJson({ error: 'invalid_transition' }, 409);
}

async function handleInternalSubmissionRuntime(request, env, _url, params) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const decision = validateRuntimeDecision(parsed.body);
  if (!decision) return internalJson({ error: 'invalid_runtime_decision' }, 400);
  const updated = await internalSetRuntimeDecision(env, params.submissionId, decision);
  return updated ? internalJson({ ok: true, id: params.submissionId }, 200)
    : internalJson({ error: 'invalid_transition' }, 409);
}

async function handleInternalSubmissionDeployment(request, env, _url, params) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  if (String(parsed.body.status || '').trim() === 'ready_for_publish') {
    return internalJson({ error: 'trusted_finalizer_required' }, 409);
  }
  const deployment = validateDeploymentBody(parsed.body);
  if (!deployment) return internalJson({ error: 'invalid_deployment' }, 400);
  const updated = await internalSetDeployment(env, params.submissionId, deployment);
  return updated ? internalJson({ ok: true, id: params.submissionId, status: deployment.status }, 200)
    : internalJson({ error: 'invalid_transition' }, 409);
}

async function handleInternalSubmissionRelease(request, env, _url, params) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const release = validateReleaseBody(parsed.body);
  if (!release) return internalJson({ error: 'invalid_release' }, 400);
  if (release.phase === 'promoted') {
    return internalJson({ error: 'trusted_finalizer_required' }, 409);
  }
  const updated = await internalSetRelease(env, params.submissionId, release);
  return updated ? internalJson({ ok: true, id: params.submissionId, release_phase: release.phase }, 200)
    : internalJson({ error: 'invalid_transition' }, 409);
}

async function handleInternalSubmissionDeployed(request, env, _url, params) {
  const parsed = await readInternalJson(request);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const metadata = {
    deployed_by: safeRuntimePolicy(parsed.body.deployed_by || 'build_worker'),
    deployment_url: safeText(parsed.body.deployment_url, 240),
  };
  const updated = await internalMarkDeployed(env, params.submissionId, metadata);
  return updated ? internalJson({ ok: true, id: params.submissionId, status: 'deployed' }, 200)
    : internalJson({ error: 'invalid_transition' }, 409);
}

async function handleInternalSubmissionSchema(request, env) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const schema = await inspectSubmissionsSchema(env);
  return internalJson({ ok: true, ...schema }, 200);
}

async function handleInternalSubmissionMigration(request, env) {
  const parsed = await readStrictEmptyInternalJson(request, MAX_INTERNAL_MIGRATION_BODY_BYTES);
  if (parsed.error) return internalJson({ error: parsed.error }, parsed.status);
  const applied = await applySubmissionsSchemaMigration(env);
  return internalJson({ ok: true, applied }, 200);
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
    let auth = await authenticateAccount(request, env, false);
    if (!auth.ok && request.method === 'GET') {
      const apiKey = String(request.headers.get('x-api-key') || '').trim();
      const apiKeyOwner = /^omo_[0-9a-f]{32}$/.test(apiKey) ? await userIdForHashedApiKey(env, apiKey) : '';
      if (apiKeyOwner === 'user_prod_label_normalizer_canary_v1') {
        auth = { ok: true, userId: apiKeyOwner, method: 'production_canary_balance' };
      }
    }
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

  let topupStage = 'stripe_request';
  let stripeSessionId = '';
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
    stripeSessionId = data.id;
    if (real) {
      topupStage = 'topup_record';
      await recordPendingTopup(env, data.id, userId, cents, 'usd');
    }
    return json({ url: checkoutUrl.toString(), session_id: data.id }, 200, cors());
  } catch (e) {
    const sessionExpired = topupStage === 'topup_record'
      ? await expireStripeCheckoutSession(secretKey, stripeSessionId)
      : false;
    console.error('top-up session failed', {
      stage: topupStage,
      code: String(e && e.code || '').slice(0, 80),
      message: String(e && e.message || 'unknown error').slice(0, 240),
      session_expired: sessionExpired,
    });
    if (topupStage === 'topup_record') {
      return json({ error: 'top-up recording unavailable', session_expired: sessionExpired }, 503, cors());
    }
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
  const pendingPilot = await pendingPilotClaimForClerkUser(env, body.data);
  if (pendingPilot) {
    const pilotResult = await applyPilotGrant(env, {
      eventId: pendingPilot.event_id,
      userId,
      grantCents: Number(pendingPilot.grant_cents),
      cohort: pendingPilot.cohort,
    });
    const record = (await getUserRecord(env, userId)).record;
    return json({
      ok: true,
      granted: pilotResult.applied,
      pilot_granted: pilotResult.applied,
      user_id: userId,
      balance: (record.balance_cents / 100).toFixed(2),
      balance_cents: record.balance_cents,
    }, 200, cors());
  }
  const { record, created } = await getUserRecord(env, userId);
  return json({
    ok: true,
    granted: created,
    user_id: userId,
    balance: (record.balance_cents / 100).toFixed(2),
    balance_cents: record.balance_cents,
  }, 200, cors());
}

// ── Route: pilot free-book claim ──────────────────────────────────────────
// GET verifies a bearer link without consuming it. POST requires a verified
// Clerk session and atomically credits the token exactly once. The ledger ID
// contains only a SHA-256 token digest, never the recipient email or bearer.

async function handlePilotClaim(request, env, url) {
  const token = String((url.searchParams && url.searchParams.get('token')) || '').trim();
  if (!env.PILOT_MAGIC_LINK_SECRET || String(env.PILOT_MAGIC_LINK_SECRET).length < 32) {
    return pilotClaimError('pilot_secret_not_configured', 503, 'This free-book link is not available yet.');
  }

  let payload;
  try {
    payload = await verifyPilotToken(token, env.PILOT_MAGIC_LINK_SECRET);
  } catch (error) {
    if (error instanceof PilotTokenError && error.code === 'pilot_token_expired') {
      return pilotClaimError(error.code, 410, 'This free-book link has expired. Ask for a fresh link.');
    }
    return pilotClaimError('pilot_token_invalid', 400, 'This free-book link is not valid.');
  }

  const expectedGrant = boundedInt(env.PILOT_GRANT_CENTS, 1, 10000, 99);
  if (payload.grant_cents !== expectedGrant) {
    return pilotClaimError('pilot_grant_mismatch', 400, 'This free-book link has the wrong grant amount.');
  }
  const eventId = await pilotGrantEventId(token);
  if (await pilotGrantAlreadyApplied(env, eventId)) {
    return pilotClaimError('pilot_token_reused', 409, 'This free-book link has already been claimed.');
  }
  await registerPilotClaim(env, eventId, payload);

  if (request.method === 'GET') {
    return json({
      ok: true,
      status: 'ready_to_claim',
      grant_cents: payload.grant_cents,
      cohort: payload.cohort,
      requires_authentication: true,
      message: 'Your free book is ready. Sign in or create your account to add it to your balance.',
    }, 200, cors(request, env));
  }

  const auth = await authenticateAccount(request, env, false);
  if (!auth.ok) {
    return pilotClaimError(auth.error, auth.status, 'Sign in or create your account to claim your free book.');
  }
  const continueUrl = pilotBookBuilderPath(env);
  if (!continueUrl) {
    return pilotClaimError('pilot_builder_not_configured', 503, 'The free-book builder is not available yet.');
  }
  const result = await applyPilotGrant(env, {
    eventId,
    userId: auth.userId,
    grantCents: payload.grant_cents,
    cohort: payload.cohort,
  });
  if (!result.applied) {
    return pilotClaimError('pilot_token_reused', 409, 'This free-book link has already been claimed.');
  }
  return json({
    ok: true,
    status: 'claimed',
    grant_cents: payload.grant_cents,
    balance_cents: result.balance_cents,
    cohort: payload.cohort,
    continue_url: continueUrl,
    message: 'Your free book is now in your balance.',
  }, 200, cors(request, env));
}

function pilotClaimError(error, status, message) {
  return json({ ok: false, error, message }, status, cors());
}

function pilotBookBuilderPath(env) {
  const configured = String(env.PILOT_BOOK_BUILDER_PATH || '').trim();
  if (/^\/run\.html\?slug=[a-z0-9][a-z0-9-]{0,100}$/.test(configured)) return configured;
  return '';
}

async function pilotGrantEventId(token) {
  return `signup:pilot-${await sha256Hex(token)}`;
}

async function pilotGrantAlreadyApplied(env, eventId) {
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-pilot-ledger-exists-v1',
      'SELECT event_id FROM credits_ledger WHERE event_id = $1',
      [eventId],
    ));
    return result.rowCount > 0;
  }
  if (databaseKind(env) === 'd1') {
    return !!(await env.BALANCE_DB.prepare('SELECT event_id FROM credits_ledger WHERE event_id = ?').bind(eventId).first());
  }
  return mockLedger.has(eventId);
}

async function registerPilotClaim(env, eventId, payload) {
  const now = new Date().toISOString();
  const emailHash = await pilotEmailHash(payload.email, env.PILOT_MAGIC_LINK_SECRET);
  const values = [eventId, emailHash, payload.cohort, payload.grant_cents, payload.exp, 'pending', now, now];
  if (databaseKind(env) === 'neon') {
    await getNeonPool(env).query(prepared(
      'omo-pilot-claim-register-v1',
      'INSERT INTO pilot_claims (event_id, email_hash, cohort, grant_cents, expires_at, state, created_at, updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT (event_id) DO NOTHING',
      values,
    ));
    return;
  }
  if (databaseKind(env) === 'd1') {
    await env.BALANCE_DB.prepare('INSERT OR IGNORE INTO pilot_claims (event_id, email_hash, cohort, grant_cents, expires_at, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)').bind(...values).run();
    return;
  }
  if (!mockPilotClaims.has(eventId)) {
    mockPilotClaims.set(eventId, {
      event_id: eventId, email_hash: emailHash, cohort: payload.cohort,
      grant_cents: payload.grant_cents, expires_at: payload.exp,
      state: 'pending', user_id: null, created_at: now, updated_at: now,
    });
  }
}

async function pendingPilotClaimForClerkUser(env, clerkUser) {
  const addresses = Array.isArray(clerkUser && clerkUser.email_addresses) ? clerkUser.email_addresses : [];
  const now = Math.floor(Date.now() / 1000);
  for (const entry of addresses) {
    const email = normalizeBuyerEmail(entry && entry.email_address);
    if (!email) continue;
    const emailHash = await pilotEmailHash(email, env.PILOT_MAGIC_LINK_SECRET);
    let row = null;
    if (databaseKind(env) === 'neon') {
      const result = await getNeonPool(env).query(prepared(
        'omo-pilot-claim-by-email-v1',
        "SELECT event_id, cohort, grant_cents FROM pilot_claims WHERE email_hash = $1 AND state = 'pending' AND expires_at > $2 ORDER BY expires_at ASC LIMIT 1",
        [emailHash, now],
      ));
      row = result.rows[0] || null;
    } else if (databaseKind(env) === 'd1') {
      row = await env.BALANCE_DB.prepare("SELECT event_id, cohort, grant_cents FROM pilot_claims WHERE email_hash = ? AND state = 'pending' AND expires_at > ? ORDER BY expires_at ASC LIMIT 1").bind(emailHash, now).first();
    } else {
      row = Array.from(mockPilotClaims.values())
        .filter((claim) => claim.email_hash === emailHash && claim.state === 'pending' && claim.expires_at > now)
        .sort((left, right) => left.expires_at - right.expires_at)[0] || null;
    }
    if (row) return row;
  }
  return null;
}

async function pilotEmailHash(email, secret) {
  const digest = await hmacSha256(
    new TextEncoder().encode(String(secret)),
    `omo-pilot-email-v1\u0000${email}`,
  );
  return bytesToHex(digest);
}

async function applyPilotGrant(env, claim) {
  const now = new Date().toISOString();
  const apiKey = apiKeyFor(claim.userId, balanceSecret(env));
  const apiKeyHash = await sha256Hex(apiKey);
  const referenceId = `pilot:${claim.cohort}`;

  if (databaseKind(env) === 'neon') {
    const client = await getNeonPool(env).connect();
    try {
      await client.query('BEGIN');
      await client.query(prepared(
        'omo-pilot-user-create-v1',
        'INSERT INTO users (user_id, balance_cents, api_key, created_at) VALUES ($1, 0, $2, $3) ON CONFLICT (user_id) DO NOTHING',
        [claim.userId, apiKeyHash, now],
      ));
      const inserted = await client.query(prepared(
        'omo-pilot-ledger-claim-v1',
        'INSERT INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES ($1, $2, $3, $4, 0, $5, $6) ON CONFLICT (event_id) DO NOTHING RETURNING event_id',
        [claim.eventId, claim.userId, 'pilot_grant', claim.grantCents, referenceId, now],
      ));
      if (!inserted.rowCount) {
        await client.query('COMMIT');
        return { applied: false };
      }
      const updated = await client.query(prepared(
        'omo-pilot-user-credit-v1',
        'UPDATE users SET balance_cents = balance_cents + $1 WHERE user_id = $2 RETURNING balance_cents',
        [claim.grantCents, claim.userId],
      ));
      await client.query(prepared(
        'omo-pilot-ledger-balance-v1',
        'UPDATE credits_ledger SET balance_cents = $1 WHERE event_id = $2',
        [updated.rows[0].balance_cents, claim.eventId],
      ));
      await client.query(prepared(
        'omo-pilot-claim-applied-v1',
        "UPDATE pilot_claims SET state = 'applied', user_id = $1, updated_at = $2 WHERE event_id = $3 AND state = 'pending'",
        [claim.userId, now, claim.eventId],
      ));
      await client.query(prepared(
        'omo-api-key-upsert-v1',
        'INSERT INTO api_keys (key_hash, user_id, created_at) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET key_hash = EXCLUDED.key_hash',
        [apiKeyHash, claim.userId, now],
      ));
      await client.query('COMMIT');
      return { applied: true, balance_cents: updated.rows[0].balance_cents };
    } catch (error) {
      try { await client.query('ROLLBACK'); } catch (rollbackError) {}
      throw error;
    } finally {
      await client.release();
    }
  }

  if (databaseKind(env) === 'd1') {
    const results = await env.BALANCE_DB.batch([
      env.BALANCE_DB.prepare('INSERT OR IGNORE INTO users (user_id, balance_cents, api_key, created_at) VALUES (?, 0, ?, ?)').bind(claim.userId, apiKeyHash, now),
      env.BALANCE_DB.prepare('INSERT OR IGNORE INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES (?, ?, ?, ?, -1, ?, ?)').bind(claim.eventId, claim.userId, 'pilot_grant', claim.grantCents, referenceId, now),
      env.BALANCE_DB.prepare('UPDATE users SET balance_cents = balance_cents + ? WHERE user_id = ? AND EXISTS (SELECT 1 FROM credits_ledger WHERE event_id = ? AND balance_cents = -1)').bind(claim.grantCents, claim.userId, claim.eventId),
      env.BALANCE_DB.prepare('UPDATE credits_ledger SET balance_cents = (SELECT balance_cents FROM users WHERE user_id = ?) WHERE event_id = ? AND balance_cents = -1').bind(claim.userId, claim.eventId),
      env.BALANCE_DB.prepare("UPDATE pilot_claims SET state = 'applied', user_id = ?, updated_at = ? WHERE event_id = ? AND state = 'pending'").bind(claim.userId, now, claim.eventId),
      env.BALANCE_DB.prepare('INSERT INTO api_keys (key_hash, user_id, created_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET key_hash = excluded.key_hash').bind(apiKeyHash, claim.userId, now),
    ]);
    const applied = !!(results[1] && results[1].meta && results[1].meta.changes);
    if (!applied) return { applied: false };
    const record = await env.BALANCE_DB.prepare('SELECT balance_cents FROM users WHERE user_id = ?').bind(claim.userId).first();
    return { applied: true, balance_cents: record.balance_cents };
  }

  if (mockLedger.has(claim.eventId)) return { applied: false };
  let record = mockUsers.get(claim.userId);
  if (!record) {
    record = { balance_cents: 0, api_key: apiKey, created_at: now };
    mockUsers.set(claim.userId, record);
  }
  record.balance_cents += claim.grantCents;
  mockApiKeys.set(apiKeyHash, claim.userId);
  mockLedgerEntry(claim.eventId, claim.userId, 'pilot_grant', claim.grantCents, record.balance_cents, referenceId, now);
  const registered = mockPilotClaims.get(claim.eventId);
  if (registered) {
    registered.state = 'applied';
    registered.user_id = claim.userId;
    registered.updated_at = now;
  }
  return { applied: true, balance_cents: record.balance_cents };
}

// ── Balance store (Neon → D1 → in-memory mock) ─────────────────────────────
// Neon uses request-local HTTP queries and request-local transactional pools.
// Cloudflare I/O objects cannot cross request contexts, so never cache a Pool.
// D1 remains supported for existing deployments. With neither configured,
// tests and local demos use an in-memory $5 account and the same transitions.

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
const mockPilotClaims = new Map();
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
  const sql = neon(url, { fullResults: true });
  return {
    query(query) {
      if (typeof query === 'string') return sql.query(query);
      return sql.query(query.text, query.values || []);
    },
    async connect() {
      const pool = new Pool({
        connectionString: url,
        max: 1,
        connectionTimeoutMillis: 5000,
        allowExitOnIdle: true,
      });
      const client = await pool.connect();
      let released = false;
      return {
        query: client.query.bind(client),
        async release() {
          if (released) return;
          released = true;
          client.release();
          await pool.end();
        },
      };
    },
  };
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
  const requestedRuntime = normalizeRequestedRuntime(submission.requestedRuntime || 'auto');
  const values = [
    submission.id, submission.userId, submission.name, submission.slug,
    submission.content, submission.sourceSha256, requestedRuntime, 'queued', now, now,
  ];
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-submission-insert-v2',
      'INSERT INTO submissions (id,user_id,name,slug,content,source_sha256,requested_runtime,status,created_at,updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) ON CONFLICT (user_id,source_sha256) DO NOTHING RETURNING id,status,requested_runtime',
      values
    ));
    if (result.rowCount === 1) return { ...result.rows[0], duplicate: false, preference_conflict: false };
    const existing = await getNeonPool(env).query(prepared(
      'omo-submission-existing-v2',
      'SELECT id,status,requested_runtime FROM submissions WHERE user_id = $1 AND source_sha256 = $2',
      [submission.userId, submission.sourceSha256]
    ));
    if (!existing.rows[0]) throw new Error('submission insert conflict could not be resolved');
    return {
      ...existing.rows[0],
      duplicate: true,
      preference_conflict: existing.rows[0].requested_runtime !== requestedRuntime,
    };
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB
      .prepare('INSERT OR IGNORE INTO submissions (id,user_id,name,slug,content,source_sha256,requested_runtime,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)')
      .bind(...values).run();
    const existing = await env.BALANCE_DB
      .prepare('SELECT id,status,requested_runtime FROM submissions WHERE user_id = ? AND source_sha256 = ?')
      .bind(submission.userId, submission.sourceSha256).first();
    if (!existing) throw new Error('submission insert conflict could not be resolved');
    const duplicate = Number(result && result.meta && result.meta.changes) !== 1;
    return {
      ...existing,
      duplicate,
      preference_conflict: duplicate && existing.requested_runtime !== requestedRuntime,
    };
  }
  const key = `${submission.userId}\u0000${submission.sourceSha256}`;
  if (mockSubmissions.has(key)) {
    const existing = mockSubmissions.get(key);
    return {
      ...existing,
      duplicate: true,
      preference_conflict: existing.requested_runtime !== requestedRuntime,
    };
  }
  const record = { ...submission, requested_runtime: requestedRuntime, status: 'queued', created_at: now, updated_at: now };
  mockSubmissions.set(key, record);
  return { id: record.id, status: record.status, requested_runtime: record.requested_runtime, duplicate: false, preference_conflict: false };
}

async function internalClaimSubmission(env, options) {
  if (databaseKind(env) === 'neon') {
    const claimStates = ['queued'];
    if (options.includeReview) claimStates.push('needs_review');
    if (options.includeReady) claimStates.push('ready_for_deploy');
    const statePlaceholders = claimStates.map((_, index) => `$${index + 1}`).join(', ');
    const params = [...claimStates, SUBMISSION_CLAIM_LEASE_SECONDS];
    const leaseParam = params.length;
    const whereId = options.id ? `AND id = $${params.length + 1}` : '';
    if (options.id) params.push(options.id);
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-submission-claim-v1',
      `WITH candidate AS (
         SELECT id, status AS prior_status FROM submissions
         WHERE (
           status IN (${statePlaceholders})
           OR (
             status = 'processing'
             AND build_claimed_at IS NOT NULL
             AND build_claimed_at ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
             AND build_claimed_at::timestamptz < CURRENT_TIMESTAMP - ($${leaseParam} * INTERVAL '1 second')
           )
         )
         AND slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'
         AND source_sha256 ~ '^[0-9a-f]{64}$'
         AND content IS NOT NULL
         AND octet_length(content) BETWEEN 1 AND ${MAX_SUBMISSION_BYTES}
         AND finalization_id IS NULL
         ${whereId}
         ORDER BY created_at ASC
         FOR UPDATE SKIP LOCKED
         LIMIT 1
       )
       UPDATE submissions AS submission
       SET status = 'processing',
           failure_code = NULL,
           build_claimed_at = CURRENT_TIMESTAMP,
           build_attempts = COALESCE(build_attempts, 0) + 1,
           build_evidence = CASE WHEN candidate.prior_status = 'ready_for_deploy'
             THEN submission.build_evidence ELSE NULL END,
           updated_at = CURRENT_TIMESTAMP
       FROM candidate
       WHERE submission.id = candidate.id
       RETURNING submission.id, submission.name, submission.slug, submission.content, submission.source_sha256, submission.requested_runtime, candidate.prior_status`,
      params
    ));
    return result.rows[0] || null;
  }
  if (databaseKind(env) === 'd1') {
    const claimStates = ['queued'];
    if (options.includeReview) claimStates.push('needs_review');
    if (options.includeReady) claimStates.push('ready_for_deploy');
    const placeholders = claimStates.map(() => '?').join(', ');
    const params = [...claimStates, SUBMISSION_CLAIM_LEASE_SECONDS];
    const whereId = options.id ? 'AND id = ?' : '';
    if (options.id) params.push(options.id);
    const row = await env.BALANCE_DB
      .prepare(`SELECT id,name,slug,content,source_sha256,requested_runtime,status AS prior_status,build_claimed_at FROM submissions
        WHERE (
          status IN (${placeholders})
          OR (status = 'processing' AND build_claimed_at IS NOT NULL
            AND datetime(build_claimed_at) < datetime('now', '-' || ? || ' seconds'))
        )
        AND length(CAST(content AS BLOB)) BETWEEN 1 AND ${MAX_SUBMISSION_BYTES}
        AND finalization_id IS NULL
        ${whereId}
        ORDER BY created_at ASC LIMIT 1`)
      .bind(...params).first();
    if (!row) return null;
    const updated = await env.BALANCE_DB
      .prepare("UPDATE submissions SET status = 'processing', failure_code = NULL, build_claimed_at = ?, build_attempts = COALESCE(build_attempts, 0) + 1, build_evidence = CASE WHEN ? = 'ready_for_deploy' THEN build_evidence ELSE NULL END, updated_at = ? WHERE id = ? AND status = ? AND finalization_id IS NULL AND (status IN (" + placeholders + ") OR (status = 'processing' AND build_claimed_at = ? AND datetime(build_claimed_at) < datetime('now', '-' || ? || ' seconds')))" )
      .bind(new Date().toISOString(), row.prior_status, new Date().toISOString(), row.id, row.prior_status, ...claimStates, row.build_claimed_at || '', SUBMISSION_CLAIM_LEASE_SECONDS).run();
    return updated.meta && updated.meta.changes ? row : null;
  }
  const claimStates = new Set(['queued']);
  if (options.includeReview) claimStates.add('needs_review');
  if (options.includeReady) claimStates.add('ready_for_deploy');
  const rows = Array.from(mockSubmissions.values())
    .filter((record) => !record.finalization_id &&
      (claimStates.has(record.status) || (record.status === 'processing' && staleSubmissionClaim(record))) &&
      (!options.id || record.id === options.id))
    .sort((a, b) => String(a.created_at || '').localeCompare(String(b.created_at || '')) || String(a.id || '').localeCompare(String(b.id || '')));
  const record = rows[0];
  if (!record || !validSubmissionClaimSource(record)) return null;
  const priorStatus = record.status;
  record.status = 'processing';
  record.failure_code = null;
  record.build_claimed_at = new Date().toISOString();
  record.build_attempts = Number(record.build_attempts || 0) + 1;
  if (priorStatus !== 'ready_for_deploy') record.build_evidence = null;
  record.updated_at = new Date().toISOString();
  return {
    id: record.id,
    name: record.name,
    slug: record.slug,
    content: record.content,
    source_sha256: record.source_sha256 || record.sourceSha256,
    requested_runtime: record.requested_runtime || record.requestedRuntime,
    prior_status: priorStatus,
  };
}

async function internalPeekBuilderSubmission(env, phase = 'build') {
  if (!['build', 'verify_merged'].includes(phase)) throw new Error('invalid_builder_phase');
  const buildLane = phase === 'build';
  if (databaseKind(env) === 'neon') {
    const result = buildLane
      ? await getNeonPool(env).query(prepared(
        'omo-internal-builder-peek-build-v1',
        `SELECT id,slug,source_sha256,status
         FROM submissions
         WHERE status IN ($1, $2)
         ORDER BY CASE WHEN status = 'needs_review' THEN 0 ELSE 1 END, created_at ASC
         LIMIT 1`,
        ['needs_review', 'queued']
      ))
      : await getNeonPool(env).query(prepared(
        'omo-internal-builder-peek-verify-v1',
        `SELECT id,slug,source_sha256,status
         FROM submissions
         WHERE status = 'ready_for_deploy' AND release_phase IN ('pr_open', 'ci_passed')
           AND release_pr_url IS NOT NULL AND release_head_sha IS NOT NULL
           AND release_artifact_hash IS NOT NULL
         ORDER BY updated_at ASC
         LIMIT 1`,
        []
      ));
    return safeBuilderPeekRow(result.rows[0]);
  }
  if (databaseKind(env) === 'd1') {
    const row = buildLane
      ? await env.BALANCE_DB
        .prepare(`SELECT id,slug,source_sha256,status FROM submissions
                  WHERE status IN (?, ?)
                  ORDER BY CASE WHEN status = 'needs_review' THEN 0 ELSE 1 END, created_at ASC LIMIT 1`)
        .bind('needs_review', 'queued').first()
      : await env.BALANCE_DB
        .prepare(`SELECT id,slug,source_sha256,status FROM submissions
                  WHERE status = 'ready_for_deploy' AND release_phase IN ('pr_open', 'ci_passed')
                    AND release_pr_url IS NOT NULL AND release_head_sha IS NOT NULL
                    AND release_artifact_hash IS NOT NULL
                  ORDER BY updated_at ASC LIMIT 1`)
        .first();
    return safeBuilderPeekRow(row);
  }
  const rows = Array.from(mockSubmissions.values());
  const row = buildLane
    ? rows
      .filter((record) => ['needs_review', 'queued'].includes(record.status))
      .sort((a, b) => ({ needs_review: 0, queued: 1 }[a.status] - { needs_review: 0, queued: 1 }[b.status]) ||
        String(a.created_at || '').localeCompare(String(b.created_at || '')))[0]
    : rows
      .filter((record) => record.status === 'ready_for_deploy' &&
        ['pr_open', 'ci_passed'].includes(record.release_phase) &&
        record.release_pr_url && record.release_head_sha && record.release_artifact_hash)
      .sort((a, b) => String(a.updated_at || '').localeCompare(String(b.updated_at || '')))[0];
  return safeBuilderPeekRow(row);
}

function safeBuilderPeekRow(row) {
  if (!row) return null;
  const id = safeSubmissionId(row.id);
  const slug = safeSlug(row.slug);
  const sourceSha256 = safeSha256(row.source_sha256 || row.sourceSha256);
  const status = safeSubmissionStatus(row.status);
  if (!id || !slug || !sourceSha256 || !['queued', 'needs_review', 'ready_for_deploy'].includes(status)) return null;
  return { id, slug, source_sha256: sourceSha256, status };
}

function finalizationClaimRow(row) {
  if (!row) return null;
  const id = String(row.finalization_id || '');
  const submissionId = safeSubmissionId(row.id);
  const slug = safeSlug(row.slug);
  const runtime = safeRuntime(row.selected_runtime);
  const targetSha = safeGitSha(row.finalization_target_sha);
  const mergeSha = safeGitSha(row.finalization_merge_sha);
  const headSha = safeGitSha(row.finalization_head_sha);
  const sourceSha256 = safeSha256(row.finalization_source_sha256);
  const artifactHash = safeSha256(row.finalization_artifact_hash);
  const leaseExpiresAt = safeTimestamp(row.finalization_lease_expires_at);
  const attempts = Number(row.finalization_attempts);
  if (!/^fin_[a-f0-9]{32}$/.test(id) || !submissionId || !slug || !runtime || !targetSha ||
      !mergeSha || !headSha || !sourceSha256 || !artifactHash || !leaseExpiresAt ||
      !Number.isSafeInteger(attempts) || attempts < 1) return null;
  return {
    id,
    submission_id: submissionId,
    slug,
    runtime,
    status: 'claimed',
    target_sha: targetSha,
    merge_sha: mergeSha,
    head_sha: headSha,
    source_sha256: sourceSha256,
    artifact_hash: artifactHash,
    lease_expires_at: leaseExpiresAt,
    attempts,
  };
}

const FINALIZATION_EFFECT_COLUMNS = {
  modal_deploy: 'finalization_modal_receipt',
  worker_deploy: 'finalization_worker_receipt',
};
const SAFE_RECEIPT_TEXT_RE = /^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,159}$/;

function safeReceiptText(value, nullable = false) {
  if (value == null && nullable) return null;
  const text = String(value || '').trim();
  return SAFE_RECEIPT_TEXT_RE.test(text) ? text : null;
}

function safeDeploymentReceipt(value, operation, targetSha) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || !FINALIZATION_EFFECT_COLUMNS[operation]) return null;
  const expectedKeys = [
    'artifact_hash', 'environment', 'previous_version_id', 'provider', 'reused',
    'rollback_token', 'status', 'target', 'target_sha', 'version_id',
  ];
  if (Object.keys(value).sort().join(',') !== expectedKeys.join(',')) return null;
  const provider = safeReceiptText(value.provider);
  const target = safeReceiptText(value.target);
  const environment = safeReceiptText(value.environment);
  const receiptTargetSha = safeGitSha(value.target_sha);
  const artifactHash = safeSha256(value.artifact_hash);
  const versionId = safeReceiptText(value.version_id);
  const previousVersionId = safeReceiptText(value.previous_version_id, true);
  const rollbackToken = safeReceiptText(value.rollback_token, true);
  const status = safeReceiptText(value.status);
  if (!provider || !target || !environment || !receiptTargetSha || receiptTargetSha !== targetSha ||
      !artifactHash || !versionId || (value.previous_version_id != null && !previousVersionId) ||
      (value.rollback_token != null && !rollbackToken) || !status || typeof value.reused !== 'boolean') return null;
  if ((operation === 'modal_deploy' && provider !== 'modal') ||
      (operation === 'worker_deploy' && provider !== 'cloudflare') ||
      status !== 'passed' || rollbackToken !== previousVersionId ||
      (value.reused === false && previousVersionId === null) ||
      (value.reused === true && (previousVersionId !== null || rollbackToken !== null))) return null;
  return {
    provider, target, environment, target_sha: receiptTargetSha, artifact_hash: artifactHash,
    version_id: versionId, previous_version_id: previousVersionId, reused: value.reused,
    rollback_token: rollbackToken, status,
  };
}

function canonicalDeploymentReceipt(receipt) {
  return JSON.stringify(receipt);
}

function finalizationGenerationAllowsEffect(row, operation, targetSha, receipt, now = Date.now()) {
  if (!row || row.finalization_target_sha !== targetSha || receipt.target_sha !== targetSha ||
      safeSha256(row.finalization_artifact_hash) !== receipt.artifact_hash) return false;
  if (safeSha256(row.source_sha256 || row.sourceSha256) !== safeSha256(row.finalization_source_sha256) ||
      safeGitSha(row.release_head_sha) !== safeGitSha(row.finalization_head_sha) ||
      safeGitSha(row.release_merge_sha) !== safeGitSha(row.finalization_merge_sha) ||
      safeSha256(row.release_artifact_hash) !== safeSha256(row.finalization_artifact_hash)) return false;
  const status = String(row.finalization_status || '');
  const slug = safeSlug(row.slug);
  if ((operation === 'modal_deploy' && (!slug || receipt.target !== `cognition-${slug}` || receipt.environment !== 'main')) ||
      (operation === 'worker_deploy' && (receipt.target !== 'cognition-demos' || receipt.environment !== 'production'))) return false;
  const canonical = canonicalDeploymentReceipt(receipt);
  const lateWorkerReconciliation = operation === 'worker_deploy' && status === 'failed' &&
    String(row.finalization_failure_code || '') === 'internal_finalizer_failed' &&
    row.finalization_modal_receipt != null &&
    (row.finalization_worker_receipt == null || String(row.finalization_worker_receipt) === canonical) &&
    receipt.reused === true && receipt.previous_version_id === null && receipt.rollback_token === null;
  if (lateWorkerReconciliation) return true;
  const expiry = Date.parse(String(row.finalization_lease_expires_at || ''));
  if (!Number.isFinite(expiry) || expiry <= now || ['completed', 'failed'].includes(status)) return false;
  return operation === 'modal_deploy'
    ? status === 'deploying_modal' && safeRuntime(row.selected_runtime) === 'modal-hosted'
    : status === 'deploying_worker';
}

async function internalRequiredRegistrySlugs(env) {
  const statuses = ['ready_for_deploy', 'ready_for_publish', 'deployed'];
  let rows;
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-finalization-registry-slugs-v1',
      `SELECT DISTINCT published_slug FROM submissions
       WHERE status = ANY($1::text[]) AND published_slug IS NOT NULL
         AND source_sha256 IS NOT NULL AND release_head_sha IS NOT NULL
         AND release_merge_sha IS NOT NULL AND release_artifact_hash IS NOT NULL`,
      [statuses]
    ));
    rows = result.rows;
  } else if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare(
      `SELECT DISTINCT published_slug FROM submissions
       WHERE status IN (?, ?, ?) AND published_slug IS NOT NULL
         AND source_sha256 IS NOT NULL AND release_head_sha IS NOT NULL
         AND release_merge_sha IS NOT NULL AND release_artifact_hash IS NOT NULL`
    ).bind(...statuses).all();
    rows = result.results || [];
  } else {
    rows = Array.from(mockSubmissions.values())
      .filter((row) => statuses.includes(row.status) && safeSha256(row.source_sha256 || row.sourceSha256) &&
        safeGitSha(row.release_head_sha) && safeGitSha(row.release_merge_sha) && safeSha256(row.release_artifact_hash))
      .map((row) => ({ published_slug: row.published_slug }));
  }
  return Array.from(new Set(rows.map((row) => safeSlug(row.published_slug)).filter(Boolean))).sort();
}

async function internalRecordFinalizationEffect(env, finalizationId, operation, targetSha, receipt) {
  const column = FINALIZATION_EFFECT_COLUMNS[operation];
  if (!column) return 'invalid';
  const expectedStatus = operation === 'modal_deploy' ? 'deploying_modal' : 'deploying_worker';
  const runtimeGuard = operation === 'modal_deploy' ? " AND selected_runtime = 'modal-hosted'" : '';
  const row = await internalGetFinalization(env, finalizationId);
  if (!finalizationGenerationAllowsEffect(row, operation, targetSha, receipt)) return 'invalid';
  const canonical = canonicalDeploymentReceipt(receipt);
  const existing = row[column] == null ? null : String(row[column]);
  if (existing != null) return existing === canonical ? 'replayed' : 'conflict';
  const lateWorkerReconciliation = operation === 'worker_deploy' &&
    String(row.finalization_status || '') === 'failed' &&
    String(row.finalization_failure_code || '') === 'internal_finalizer_failed';
  if (lateWorkerReconciliation && databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-finalization-effect-worker-reconcile-v1',
      `UPDATE submissions SET finalization_worker_receipt = $1, automation_updated_at = CURRENT_TIMESTAMP
       WHERE finalization_id = $2 AND finalization_target_sha = $3
         AND finalization_status = 'failed' AND finalization_failure_code = 'internal_finalizer_failed'
         AND finalization_modal_receipt IS NOT NULL AND finalization_worker_receipt IS NULL
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash
       RETURNING id`,
      [canonical, finalizationId, targetSha]
    ));
    return result.rowCount === 1 ? 'recorded' : 'invalid';
  }
  if (lateWorkerReconciliation && databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare(
      `UPDATE submissions SET finalization_worker_receipt = ?, automation_updated_at = ?
       WHERE finalization_id = ? AND finalization_target_sha = ?
         AND finalization_status = 'failed' AND finalization_failure_code = 'internal_finalizer_failed'
         AND finalization_modal_receipt IS NOT NULL AND finalization_worker_receipt IS NULL
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash`
    ).bind(canonical, new Date().toISOString(), finalizationId, targetSha).run();
    return result.meta && result.meta.changes ? 'recorded' : 'invalid';
  }
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      `omo-internal-finalization-effect-${operation}-v1`,
      `UPDATE submissions SET ${column} = $1, automation_updated_at = CURRENT_TIMESTAMP
       WHERE finalization_id = $2 AND finalization_target_sha = $3 AND ${column} IS NULL
         AND finalization_status = $4${runtimeGuard}
         AND finalization_lease_expires_at::timestamptz > CURRENT_TIMESTAMP
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash
       RETURNING id`,
      [canonical, finalizationId, targetSha, expectedStatus]
    ));
    if (result.rowCount === 1) return 'recorded';
    const latest = await internalGetFinalization(env, finalizationId);
    return latest && finalizationGenerationAllowsEffect(latest, operation, targetSha, receipt) &&
      String(latest[column] || '') === canonical ? 'replayed' : 'invalid';
  }
  if (databaseKind(env) === 'd1') {
    const now = new Date().toISOString();
    const result = await env.BALANCE_DB.prepare(
      `UPDATE submissions SET ${column} = ?, automation_updated_at = ?
       WHERE finalization_id = ? AND finalization_target_sha = ? AND ${column} IS NULL
         AND finalization_status = ?${runtimeGuard}
         AND finalization_lease_expires_at > ?
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash`
    ).bind(canonical, now, finalizationId, targetSha, expectedStatus, now).run();
    if (result.meta && result.meta.changes) return 'recorded';
    const latest = await internalGetFinalization(env, finalizationId);
    return latest && finalizationGenerationAllowsEffect(latest, operation, targetSha, receipt) &&
      String(latest[column] || '') === canonical ? 'replayed' : 'invalid';
  }
  row[column] = canonical;
  row.automation_updated_at = new Date().toISOString();
  return 'recorded';
}

function completedFinalizationRow(row) {
  if (!row) return null;
  const finalization = finalizationClaimRow(row);
  const submissionStatus = String(row.status || '');
  if (!finalization || !['ready_for_publish', 'deployed'].includes(submissionStatus) ||
      String(row.release_phase || '') !== 'promoted' ||
      String(row.finalization_status || '') !== 'completed' ||
      safeSha256(row.source_sha256 || row.sourceSha256) !== safeSha256(row.finalization_source_sha256) ||
      safeGitSha(row.release_head_sha) !== safeGitSha(row.finalization_head_sha) ||
      safeGitSha(row.release_merge_sha) !== safeGitSha(row.finalization_merge_sha) ||
      safeSha256(row.release_artifact_hash) !== safeSha256(row.finalization_artifact_hash) ||
      !safePromotionEvidence(row.promotion_evidence)) return null;
  return { ...finalization, status: 'completed', submission_status: submissionStatus };
}

function failedFinalizationRow(row) {
  if (!row) return null;
  const id = String(row.finalization_id || '');
  const submissionId = safeSubmissionId(row.id);
  const submissionStatus = String(row.status || '');
  const releasePhase = String(row.release_phase || '');
  const failureCode = String(row.finalization_failure_code || '').trim();
  const targetSha = safeGitSha(row.finalization_target_sha);
  const sourceSha256 = safeSha256(row.finalization_source_sha256);
  const headSha = safeGitSha(row.finalization_head_sha);
  const mergeSha = safeGitSha(row.finalization_merge_sha);
  const artifactHash = safeSha256(row.finalization_artifact_hash);
  const attempts = Number(row.finalization_attempts);
  if (!/^fin_[a-f0-9]{32}$/.test(id) || !submissionId ||
      String(row.finalization_status || '') !== 'failed' || !FINALIZATION_FAILURE_CODES.has(failureCode) ||
      !['ready_for_deploy', 'failed'].includes(submissionStatus) || releasePhase !== 'merged_verified' ||
      !targetSha || !sourceSha256 || !headSha || !mergeSha || !artifactHash ||
      safeSha256(row.source_sha256 || row.sourceSha256) !== sourceSha256 ||
      safeGitSha(row.release_head_sha) !== headSha || safeGitSha(row.release_merge_sha) !== mergeSha ||
      safeSha256(row.release_artifact_hash) !== artifactHash ||
      !Number.isSafeInteger(attempts) || attempts < 1) return null;
  return {
    id, status: 'failed', failure_code: failureCode, submission_id: submissionId,
    submission_status: submissionStatus, release_phase: releasePhase, target_sha: targetSha,
    source_sha256: sourceSha256, head_sha: headSha, merge_sha: mergeSha,
    artifact_hash: artifactHash, attempts,
    modal_receipt_present: row.modal_receipt_present === true || row.finalization_modal_receipt != null,
    worker_receipt_present: row.worker_receipt_present === true || row.finalization_worker_receipt != null,
  };
}

function canonicalStoredReceipt(raw, operation, targetSha) {
  if (typeof raw !== 'string' || !raw) return null;
  let value;
  try { value = JSON.parse(raw); } catch { return null; }
  const receipt = safeDeploymentReceipt(value, operation, targetSha);
  return receipt && canonicalDeploymentReceipt(receipt) === raw ? receipt : null;
}

function recoveryHistory(raw) {
  if (raw == null) return [];
  if (typeof raw !== 'string' || !raw || raw.length > 256 * 1024) return null;
  let value;
  try { value = JSON.parse(raw); } catch { return null; }
  const history = Array.isArray(value) ? value : [value];
  if (!history.length || history.length > 32 || history.some((item) =>
    !item || typeof item !== 'object' || Array.isArray(item) ||
    item.verified_by !== 'trusted_production_finalizer' ||
    !/^fin_[0-9a-f]{32}$/.test(String(item.finalization_id || '')) ||
    !/^[0-9a-f]{40}$/.test(String(item.target_sha || '')) ||
    !Number.isInteger(item.attempt) || item.attempt < 1 ||
    typeof item.recovered_at !== 'string')) return null;
  return history;
}

function recoveryCandidate(row) {
  if (!row) return null;
  const failed = failedFinalizationRow(row);
  const history = recoveryHistory(row.finalization_recovery_receipt);
  if (!failed || !['worker_smoke_failed', 'internal_finalizer_failed', 'public_verification_failed'].includes(failed.failure_code) ||
      safeRuntime(row.selected_runtime) !== 'modal-hosted' || history == null) return null;
  const slug = safeSlug(row.slug);
  const modalReceipt = canonicalStoredReceipt(row.finalization_modal_receipt, 'modal_deploy', failed.target_sha);
  const workerReceipt = canonicalStoredReceipt(row.finalization_worker_receipt, 'worker_deploy', failed.target_sha);
  if (!slug || !modalReceipt || !workerReceipt ||
      modalReceipt.target !== `cognition-${slug}` || modalReceipt.environment !== 'main' ||
      workerReceipt.target !== 'cognition-demos' || workerReceipt.environment !== 'production' ||
      modalReceipt.artifact_hash !== failed.artifact_hash || workerReceipt.artifact_hash !== failed.artifact_hash) return null;
  return { row, failed, modalReceipt, workerReceipt, history };
}

function automaticRecoveryCandidateRow(row) {
  const failed = failedFinalizationRow(row);
  if (!failed) return null;
  const noEffectAttempt = failed.attempts === 1 ||
    (failed.attempts === 2 && failed.failure_code === 'internal_finalizer_failed');
  if (noEffectAttempt && !failed.modal_receipt_present && !failed.worker_receipt_present &&
      AUTO_RECOVERY_NO_EFFECT_CODES.has(failed.failure_code)) {
    return {
      target_sha: failed.target_sha, finalization_id: failed.id, mode: 'resume_no_effect',
    };
  }
  const receiptCandidate = recoveryCandidate(row);
  return receiptCandidate && receiptCandidate.history.length === 0
    ? { target_sha: failed.target_sha, finalization_id: failed.id, mode: 'verify_then_retry' }
    : null;
}

async function internalAutomaticRecoveryCandidate(env) {
  const columns = `id,slug,selected_runtime,status,release_phase,source_sha256,release_head_sha,release_merge_sha,
    release_artifact_hash,finalization_id,finalization_status,finalization_target_sha,
    finalization_source_sha256,finalization_head_sha,finalization_merge_sha,
    finalization_artifact_hash,finalization_attempts,finalization_failure_code,
    finalization_modal_receipt,finalization_worker_receipt,finalization_recovery_receipt,
    (finalization_modal_receipt IS NOT NULL) AS modal_receipt_present,
    (finalization_worker_receipt IS NOT NULL) AS worker_receipt_present`;
  const effectCodes = ['worker_smoke_failed', 'internal_finalizer_failed', 'public_verification_failed'];
  let rows;
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-finalization-recovery-candidate-v1',
      `SELECT ${columns} FROM submissions
       WHERE finalization_status = 'failed'
         AND status IN ('ready_for_deploy', 'failed') AND release_phase = 'merged_verified'
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash
         AND ((((finalization_attempts = 1 AND finalization_failure_code = ANY($1::text[]))
                 OR (finalization_attempts = 2 AND finalization_failure_code = 'internal_finalizer_failed'))
               AND finalization_modal_receipt IS NULL AND finalization_worker_receipt IS NULL)
           OR (selected_runtime = 'modal-hosted' AND finalization_failure_code = ANY($2::text[])
               AND finalization_modal_receipt IS NOT NULL AND finalization_worker_receipt IS NOT NULL))
       ORDER BY automation_updated_at ASC, id ASC LIMIT 32`,
      [Array.from(AUTO_RECOVERY_NO_EFFECT_CODES), effectCodes]
    ));
    rows = result.rows || [];
  } else if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare(
      `SELECT ${columns} FROM submissions
       WHERE finalization_status = 'failed'
         AND status IN ('ready_for_deploy', 'failed') AND release_phase = 'merged_verified'
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash
         AND ((((finalization_attempts = 1 AND finalization_failure_code IN (?, ?, ?, ?))
                 OR (finalization_attempts = 2 AND finalization_failure_code = 'internal_finalizer_failed'))
               AND finalization_modal_receipt IS NULL AND finalization_worker_receipt IS NULL)
           OR (selected_runtime = 'modal-hosted' AND finalization_failure_code IN (?, ?, ?)
               AND finalization_modal_receipt IS NOT NULL AND finalization_worker_receipt IS NOT NULL))
       ORDER BY automation_updated_at ASC, id ASC LIMIT 32`
    ).bind(...AUTO_RECOVERY_NO_EFFECT_CODES, ...effectCodes).all();
    rows = result.results || [];
  } else {
    rows = Array.from(mockSubmissions.values()).sort((left, right) =>
      String(left.automation_updated_at || '').localeCompare(String(right.automation_updated_at || '')) ||
      String(left.id || '').localeCompare(String(right.id || ''))
    );
  }
  return rows.map(automaticRecoveryCandidateRow).find(Boolean) || null;
}

function expectedRecoveryVersion(receipt, provider) {
  return provider === 'modal' || receipt.reused ? receipt.version_id : receipt.previous_version_id;
}

function recoveryPlan(candidate) {
  return {
    target_sha: candidate.failed.target_sha, finalization_id: candidate.failed.id,
    modal: { receipt: candidate.modalReceipt, expected_active_version_id: expectedRecoveryVersion(candidate.modalReceipt, 'modal') },
    cloudflare: { receipt: candidate.workerReceipt, expected_active_version_id: expectedRecoveryVersion(candidate.workerReceipt, 'cloudflare') },
  };
}

function recoverySnapshot(candidate, recoveredAt) {
  const failed = candidate.failed;
  return JSON.stringify({
    finalization_id: failed.id, attempt: failed.attempts, target_sha: failed.target_sha,
    source_sha256: failed.source_sha256, head_sha: failed.head_sha, merge_sha: failed.merge_sha,
    artifact_hash: failed.artifact_hash, failure_code: failed.failure_code,
    modal_receipt: candidate.modalReceipt, worker_receipt: candidate.workerReceipt,
    expected_provider_state: {
      modal: { version_id: expectedRecoveryVersion(candidate.modalReceipt, 'modal') },
      cloudflare: { version_id: expectedRecoveryVersion(candidate.workerReceipt, 'cloudflare') },
    },
    verified_by: 'trusted_production_finalizer', recovered_at: recoveredAt,
  });
}

async function internalInspectFailedFinalization(env, targetSha, finalizationId = null) {
  const columns = `id,slug,selected_runtime,status,release_phase,source_sha256,release_head_sha,release_merge_sha,
    release_artifact_hash,finalization_id,finalization_status,finalization_target_sha,
    finalization_source_sha256,finalization_head_sha,finalization_merge_sha,
    finalization_artifact_hash,finalization_attempts,finalization_failure_code,
    finalization_modal_receipt,finalization_worker_receipt,finalization_recovery_receipt,
    (finalization_modal_receipt IS NOT NULL) AS modal_receipt_present,
    (finalization_worker_receipt IS NOT NULL) AS worker_receipt_present`;
  const generationFilter = finalizationId ? ' AND finalization_id = $2' : '';
  const filters = `finalization_status = 'failed' AND finalization_target_sha = $1${generationFilter}
    AND status IN ('ready_for_deploy', 'failed') AND release_phase = 'merged_verified'
    AND source_sha256 = finalization_source_sha256
    AND release_head_sha = finalization_head_sha
    AND release_merge_sha = finalization_merge_sha
    AND release_artifact_hash = finalization_artifact_hash`;
  const values = finalizationId ? [targetSha, finalizationId] : [targetSha];
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      finalizationId
        ? 'omo-internal-finalization-failed-by-generation-v1'
        : 'omo-internal-finalization-failed-by-target-v1',
      `SELECT ${columns} FROM submissions WHERE ${filters}
       ORDER BY automation_updated_at DESC, id ASC LIMIT 1`,
      values
    ));
    return result.rows[0] || null;
  }
  if (databaseKind(env) === 'd1') {
    return await env.BALANCE_DB.prepare(
      `SELECT ${columns.replaceAll('$1', '?')} FROM submissions
       WHERE ${filters.replaceAll('$1', '?').replaceAll('$2', '?')}
       ORDER BY automation_updated_at DESC, id ASC LIMIT 1`
    ).bind(...values).first();
  }
  return Array.from(mockSubmissions.values())
    .filter((record) => record.finalization_status === 'failed' &&
      record.finalization_target_sha === targetSha && (!finalizationId || record.finalization_id === finalizationId) &&
      ['ready_for_deploy', 'failed'].includes(record.status) && record.release_phase === 'merged_verified')
    .sort((a, b) => String(b.automation_updated_at || '').localeCompare(String(a.automation_updated_at || '')) ||
      String(a.id || '').localeCompare(String(b.id || '')))[0] || null;
}

async function internalRecoverRolledBackFinalization(env, targetSha, finalizationId) {
  if (!/^fin_[0-9a-f]{32}$/.test(String(finalizationId || ''))) return false;
  const candidate = recoveryCandidate(await internalInspectFailedFinalization(env, targetSha, finalizationId));
  if (!candidate) return false;
  const { failed, row } = candidate;
  const recoveredAt = new Date().toISOString();
  const currentSnapshot = recoverySnapshot(candidate, recoveredAt);
  const snapshot = candidate.history.length
    ? JSON.stringify([...candidate.history, JSON.parse(currentSnapshot)])
    : currentSnapshot;
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-finalization-recover-rolled-back-v1',
      `UPDATE submissions SET status = 'ready_for_deploy', finalization_recovery_receipt = $1,
+         finalization_id = NULL, finalization_status = NULL, finalization_target_sha = NULL,
+         finalization_source_sha256 = NULL, finalization_head_sha = NULL, finalization_merge_sha = NULL,
+         finalization_artifact_hash = NULL, finalization_claimed_at = NULL,
+         finalization_lease_expires_at = NULL, finalization_failure_code = NULL,
+         finalization_modal_receipt = NULL, finalization_worker_receipt = NULL,
+         automation_updated_at = CURRENT_TIMESTAMP
+       WHERE id = $2 AND finalization_id = $3 AND finalization_target_sha = $4
+         AND finalization_status = 'failed' AND finalization_failure_code IN ('worker_smoke_failed', 'internal_finalizer_failed', 'public_verification_failed')
+         AND status IN ('ready_for_deploy', 'failed') AND release_phase = 'merged_verified'
+         AND selected_runtime = 'modal-hosted' AND finalization_recovery_receipt IS NOT DISTINCT FROM $11
+         AND source_sha256 = $5 AND finalization_source_sha256 = $5
+         AND release_head_sha = $6 AND finalization_head_sha = $6
+         AND release_merge_sha = $7 AND finalization_merge_sha = $7
+         AND release_artifact_hash = $8 AND finalization_artifact_hash = $8
+         AND finalization_modal_receipt = $9 AND finalization_worker_receipt = $10
+       RETURNING id`.replace(/^\+/gm, ''),
      [snapshot, failed.submission_id, finalizationId, targetSha, failed.source_sha256, failed.head_sha,
        failed.merge_sha, failed.artifact_hash, row.finalization_modal_receipt, row.finalization_worker_receipt,
        row.finalization_recovery_receipt]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare(
      `UPDATE submissions SET status = 'ready_for_deploy', finalization_recovery_receipt = ?,
+         finalization_id = NULL, finalization_status = NULL, finalization_target_sha = NULL,
+         finalization_source_sha256 = NULL, finalization_head_sha = NULL, finalization_merge_sha = NULL,
+         finalization_artifact_hash = NULL, finalization_claimed_at = NULL,
+         finalization_lease_expires_at = NULL, finalization_failure_code = NULL,
+         finalization_modal_receipt = NULL, finalization_worker_receipt = NULL, automation_updated_at = ?
+       WHERE id = ? AND finalization_id = ? AND finalization_target_sha = ?
+         AND finalization_status = 'failed' AND finalization_failure_code IN ('worker_smoke_failed', 'internal_finalizer_failed', 'public_verification_failed')
+         AND status IN ('ready_for_deploy', 'failed') AND release_phase = 'merged_verified'
+         AND selected_runtime = 'modal-hosted' AND finalization_recovery_receipt IS ?
+         AND source_sha256 = ? AND finalization_source_sha256 = ?
+         AND release_head_sha = ? AND finalization_head_sha = ?
+         AND release_merge_sha = ? AND finalization_merge_sha = ?
+         AND release_artifact_hash = ? AND finalization_artifact_hash = ?
+         AND finalization_modal_receipt = ? AND finalization_worker_receipt = ?`.replace(/^\+/gm, '')
    ).bind(snapshot, recoveredAt, failed.submission_id, finalizationId, targetSha,
      row.finalization_recovery_receipt,
      failed.source_sha256, failed.source_sha256, failed.head_sha, failed.head_sha,
      failed.merge_sha, failed.merge_sha, failed.artifact_hash, failed.artifact_hash,
      row.finalization_modal_receipt, row.finalization_worker_receipt).run();
    return Boolean(result.meta && result.meta.changes);
  }
  if (recoveryCandidate(row) == null) return false;
  row.status = 'ready_for_deploy';
  row.finalization_recovery_receipt = snapshot;
  for (const field of ['id', 'status', 'target_sha', 'source_sha256', 'head_sha', 'merge_sha',
    'artifact_hash', 'claimed_at', 'lease_expires_at', 'failure_code', 'modal_receipt', 'worker_receipt']) {
    row[`finalization_${field}`] = null;
  }
  row.automation_updated_at = recoveredAt;
  return true;
}

async function internalResumeFailedFinalization(env, targetSha, finalizationId) {
  if (!/^fin_[0-9a-f]{32}$/.test(String(finalizationId || ''))) return false;
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-finalization-resume-failed-v1',
      `WITH candidate AS (
         SELECT id, finalization_id
         FROM submissions
         WHERE finalization_target_sha = $1 AND finalization_id = $2
           AND finalization_status = 'failed'
           AND finalization_failure_code = ANY($3::text[])
           AND status IN ('ready_for_deploy', 'failed') AND release_phase = 'merged_verified'
           AND finalization_modal_receipt IS NULL AND finalization_worker_receipt IS NULL
           AND source_sha256 = finalization_source_sha256
           AND release_head_sha = finalization_head_sha
           AND release_merge_sha = finalization_merge_sha
           AND release_artifact_hash = finalization_artifact_hash
         ORDER BY automation_updated_at DESC, id ASC
         FOR UPDATE SKIP LOCKED
         LIMIT 1
       )
       UPDATE submissions AS submission
       SET status = 'ready_for_deploy', finalization_id = NULL, finalization_status = NULL,
           finalization_target_sha = NULL, finalization_source_sha256 = NULL,
           finalization_head_sha = NULL, finalization_merge_sha = NULL,
           finalization_artifact_hash = NULL, finalization_claimed_at = NULL,
           finalization_lease_expires_at = NULL, finalization_failure_code = NULL,
           finalization_modal_receipt = NULL, finalization_worker_receipt = NULL,
           automation_updated_at = CURRENT_TIMESTAMP
       FROM candidate
       WHERE submission.id = candidate.id
         AND submission.finalization_id = candidate.finalization_id
         AND submission.finalization_target_sha = $1
         AND submission.finalization_status = 'failed'
       RETURNING submission.id`,
      [targetSha, finalizationId, Array.from(FINALIZATION_FAILURE_CODES)]
    ));
    return result.rowCount === 1;
  }
  const row = await internalInspectFailedFinalization(env, targetSha, finalizationId);
  const failed = failedFinalizationRow(row);
  if (!failed || failed.modal_receipt_present || failed.worker_receipt_present) return false;
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare(
      `UPDATE submissions
       SET status = 'ready_for_deploy', finalization_id = NULL, finalization_status = NULL,
           finalization_target_sha = NULL, finalization_source_sha256 = NULL,
           finalization_head_sha = NULL, finalization_merge_sha = NULL,
           finalization_artifact_hash = NULL, finalization_claimed_at = NULL,
           finalization_lease_expires_at = NULL, finalization_failure_code = NULL,
           finalization_modal_receipt = NULL, finalization_worker_receipt = NULL,
           automation_updated_at = ?
       WHERE id = ? AND finalization_id = ? AND finalization_target_sha = ?
         AND finalization_status = 'failed' AND status IN ('ready_for_deploy', 'failed')
         AND release_phase = 'merged_verified'
         AND finalization_modal_receipt IS NULL AND finalization_worker_receipt IS NULL
         AND source_sha256 = ? AND finalization_source_sha256 = ?
         AND release_head_sha = ? AND finalization_head_sha = ?
         AND release_merge_sha = ? AND finalization_merge_sha = ?
         AND release_artifact_hash = ? AND finalization_artifact_hash = ?`
    ).bind(
      now, failed.submission_id, failed.id, targetSha,
      failed.source_sha256, failed.source_sha256, failed.head_sha, failed.head_sha,
      failed.merge_sha, failed.merge_sha, failed.artifact_hash, failed.artifact_hash,
    ).run();
    return Boolean(result.meta && result.meta.changes);
  }
  row.status = 'ready_for_deploy';
  row.finalization_id = null;
  row.finalization_status = null;
  row.finalization_target_sha = null;
  row.finalization_source_sha256 = null;
  row.finalization_head_sha = null;
  row.finalization_merge_sha = null;
  row.finalization_artifact_hash = null;
  row.finalization_claimed_at = null;
  row.finalization_lease_expires_at = null;
  row.finalization_failure_code = null;
  row.finalization_modal_receipt = null;
  row.finalization_worker_receipt = null;
  row.automation_updated_at = now;
  return true;
}

async function inspectFinalizationResumeQuery(env) {
  if (databaseKind(env) !== 'neon') return 'unsupported';
  let client;
  try {
    client = await getNeonPool(env).connect();
  } catch {
    return 'connection';
  }
  const columns = `id,slug,selected_runtime,status,release_phase,source_sha256,
    release_head_sha,release_merge_sha,release_artifact_hash,promotion_evidence,
    finalization_id,finalization_status,finalization_target_sha,
    finalization_source_sha256,finalization_head_sha,finalization_merge_sha,
    finalization_artifact_hash,finalization_lease_expires_at,finalization_attempts`;
  const targetSha = '0000000000000000000000000000000000000000';
  const filters = `status IN ('ready_for_publish', 'deployed') AND release_phase = 'promoted'
    AND finalization_status = 'completed' AND finalization_target_sha = $1
    AND source_sha256 = finalization_source_sha256
    AND release_head_sha = finalization_head_sha
    AND release_merge_sha = finalization_merge_sha
    AND release_artifact_hash = finalization_artifact_hash`;
  const probes = [
    ['table', prepared('omo-finalization-resume-probe-table-v1', 'SELECT id FROM submissions LIMIT 1', [])],
    ['columns', prepared('omo-finalization-resume-probe-columns-v1', `SELECT ${columns} FROM submissions LIMIT 1`, [])],
    ['filters', prepared('omo-finalization-resume-probe-filters-v1', `SELECT id FROM submissions WHERE ${filters} LIMIT 1`, [targetSha])],
    ['ordering', prepared('omo-finalization-resume-probe-ordering-v1',
      `SELECT ${columns} FROM submissions WHERE ${filters}
       ORDER BY CASE WHEN status = 'ready_for_publish' THEN 0 ELSE 1 END,
                automation_updated_at ASC, id ASC LIMIT 1`, [targetSha])],
  ];
  try {
    for (const [stage, query] of probes) {
      try { await client.query(query); } catch { return stage; }
    }
    return 'passed';
  } finally {
    await client.release();
  }
}

async function internalResumeCompletedFinalization(env, targetSha) {
  const columns = `id,slug,selected_runtime,status,release_phase,source_sha256,
    release_head_sha,release_merge_sha,release_artifact_hash,promotion_evidence,
    finalization_id,finalization_status,finalization_target_sha,
    finalization_source_sha256,finalization_head_sha,finalization_merge_sha,
    finalization_artifact_hash,finalization_lease_expires_at,finalization_attempts`;
  if (databaseKind(env) === 'neon') {
    const client = await getNeonPool(env).connect();
    try {
      const result = await client.query(prepared(
        'omo-internal-finalization-resume-completed-v1',
        `SELECT ${columns}
         FROM submissions
         WHERE status IN ('ready_for_publish', 'deployed') AND release_phase = 'promoted'
           AND finalization_status = 'completed' AND finalization_target_sha = $1
           AND source_sha256 = finalization_source_sha256
           AND release_head_sha = finalization_head_sha
           AND release_merge_sha = finalization_merge_sha
           AND release_artifact_hash = finalization_artifact_hash
         ORDER BY CASE WHEN status = 'ready_for_publish' THEN 0 ELSE 1 END,
                  automation_updated_at ASC, id ASC
         LIMIT 1`,
        [targetSha]
      ));
      return result.rows[0] || null;
    } finally {
      await client.release();
    }
  }
  if (databaseKind(env) === 'd1') {
    return await env.BALANCE_DB.prepare(
      `SELECT ${columns}
       FROM submissions
       WHERE status IN ('ready_for_publish', 'deployed') AND release_phase = 'promoted'
         AND finalization_status = 'completed' AND finalization_target_sha = ?
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash
       ORDER BY CASE WHEN status = 'ready_for_publish' THEN 0 ELSE 1 END,
                automation_updated_at ASC, id ASC
       LIMIT 1`
    ).bind(targetSha).first();
  }
  return Array.from(mockSubmissions.values())
    .filter((record) => ['ready_for_publish', 'deployed'].includes(record.status) &&
      record.release_phase === 'promoted' && record.finalization_status === 'completed' &&
      record.finalization_target_sha === targetSha)
    .sort((a, b) => Number(a.status === 'deployed') - Number(b.status === 'deployed') ||
      String(a.automation_updated_at || '').localeCompare(String(b.automation_updated_at || '')) ||
      String(a.id || '').localeCompare(String(b.id || '')))[0] || null;
}

async function internalFinalizationEligibility(env, targetSha, targets) {
  const columns = `id,published_slug,status,release_phase,selected_runtime,source_sha256,workflow_version,
    build_evidence,release_issue_url,release_pr_url,release_pr_number,release_branch,release_head_sha,
    release_merge_sha,release_artifact_hash,finalization_status,finalization_target_sha,
    finalization_lease_expires_at`;
  const canonicalOwner = 'user_prod_label_normalizer_canary_v1';
  const values = targets.flatMap((target) => [target.slug, target.source_sha256]);
  let rows;
  if (databaseKind(env) === 'neon') {
    const pairs = targets.map((_, index) => `($${index * 2 + 1}, $${index * 2 + 2})`).join(', ');
    const ownerParam = `$${values.length + 1}`;
    const result = await getNeonPool(env).query(prepared(
      `omo-internal-finalization-eligibility-v3-${targets.length}`,
      `SELECT ${columns} FROM submissions WHERE user_id = ${ownerParam} AND (published_slug, source_sha256) IN (${pairs}) ORDER BY published_slug ASC`,
      [...values, canonicalOwner]
    ));
    rows = result.rows || [];
  } else if (databaseKind(env) === 'd1') {
    const pairs = targets.map(() => '(published_slug = ? AND source_sha256 = ?)').join(' OR ');
    const result = await env.BALANCE_DB.prepare(
      `SELECT ${columns} FROM submissions WHERE user_id = ? AND (${pairs}) ORDER BY published_slug ASC`
    ).bind(canonicalOwner, ...values).all();
    rows = result.results || [];
  } else {
    const targetMap = new Map(targets.map((target) => [target.slug, target.source_sha256]));
    rows = Array.from(mockSubmissions.values())
      .filter((row) => row && row.user_id === canonicalOwner && targetMap.has(row.published_slug)
        && targetMap.get(row.published_slug) === row.source_sha256)
      .sort((a, b) => String(a.published_slug).localeCompare(String(b.published_slug)));
  }
  const now = Date.now();
  return rows.map((row) => finalizationEligibilityRow(row, targetSha, now));
}

function finalizationEligibilityRow(row, targetSha, now) {
  const activeStatuses = new Set(['claimed', 'deploying_modal', 'deploying_worker', 'verifying_public']);
  const rawFinalizationStatus = row.finalization_status == null ? null : String(row.finalization_status);
  const finalizationState = rawFinalizationStatus === null || activeStatuses.has(rawFinalizationStatus)
    || ['failed', 'completed', 'rolled_back'].includes(rawFinalizationStatus)
    ? rawFinalizationStatus : 'invalid';
  const leaseMs = Date.parse(String(row.finalization_lease_expires_at || ''));
  const leaseExpired = activeStatuses.has(rawFinalizationStatus) && Number.isFinite(leaseMs) && leaseMs < now;
  const finalizationAvailable = rawFinalizationStatus === null || leaseExpired;
  const present = (value) => value !== null && value !== undefined && String(value).trim() !== '';
  const result = {
    submission_id: safeSubmissionId(row.id),
    slug: safeSlug(row.published_slug),
    status: safeSubmissionStatus(row.status),
    release_phase: RELEASE_PHASES.has(String(row.release_phase || '')) ? String(row.release_phase) : null,
    selected_runtime: safeRuntime(row.selected_runtime),
    source_sha256_present: Boolean(safeSha256(row.source_sha256)),
    published_slug_present: Boolean(safeSlug(row.published_slug)),
    workflow_version_present: SAFE_WORKFLOW_VERSION_RE.test(String(row.workflow_version || '')),
    build_evidence_present: safeBuildEvidence(row.build_evidence).checks.length > 0,
    release_issue_url_present: Boolean(safeGithubUrl(row.release_issue_url, 'issues')),
    release_pr_url_present: Boolean(safeGithubUrl(row.release_pr_url, 'pull')),
    release_pr_number_present: Number.isSafeInteger(Number(row.release_pr_number)) && Number(row.release_pr_number) > 0,
    release_branch_present: Boolean(safeReleaseBranch(row.release_branch)),
    release_head_sha_present: Boolean(safeGitSha(row.release_head_sha)),
    release_merge_sha_present: Boolean(safeGitSha(row.release_merge_sha)),
    release_artifact_hash_present: Boolean(safeSha256(row.release_artifact_hash)),
    finalization_status: finalizationState,
    finalization_target_matches: present(row.finalization_target_sha) && row.finalization_target_sha === targetSha,
    finalization_lease_expired: leaseExpired,
    finalization_available: finalizationAvailable,
  };
  result.claimable = result.status === 'ready_for_deploy'
    && result.release_phase === 'merged_verified'
    && ['worker-native', 'modal-hosted'].includes(result.selected_runtime)
    && result.source_sha256_present && result.published_slug_present && result.workflow_version_present
    && result.build_evidence_present && result.release_issue_url_present && result.release_pr_url_present
    && result.release_pr_number_present && result.release_branch_present && result.release_head_sha_present
    && result.release_merge_sha_present && result.release_artifact_hash_present && result.finalization_available;
  return result;
}

async function internalClaimFinalization(env, targetSha, targets) {
  const now = new Date();
  const claimedAt = now.toISOString();
  const leaseExpiresAt = new Date(now.getTime() + FINALIZATION_LEASE_SECONDS * 1000).toISOString();
  const finalizationId = `fin_${crypto.randomUUID().replace(/-/g, '')}`;
  const canonicalOwner = 'user_prod_label_normalizer_canary_v1';
  const targetValues = targets.flatMap((target) => [target.slug, target.source_sha256]);
  if (databaseKind(env) === 'neon') {
    const targetPairs = targets.map((_, index) => `($${index * 2 + 5}, $${index * 2 + 6})`).join(', ');
    const result = await getNeonPool(env).query(prepared(
      `omo-internal-finalization-claim-v3-${targets.length}`,
      `WITH candidate AS (
         SELECT id FROM submissions
         WHERE user_id = $4
           AND status = 'ready_for_deploy'
           AND release_phase = 'merged_verified'
           AND (published_slug, source_sha256) IN (${targetPairs})
           AND selected_runtime IN ('worker-native', 'modal-hosted')
           AND source_sha256 IS NOT NULL
           AND published_slug IS NOT NULL
           AND workflow_version IS NOT NULL
           AND build_evidence IS NOT NULL
           AND release_issue_url IS NOT NULL
           AND release_pr_url IS NOT NULL
           AND release_pr_number IS NOT NULL
           AND release_branch IS NOT NULL
           AND release_head_sha IS NOT NULL
           AND release_merge_sha IS NOT NULL
           AND release_artifact_hash IS NOT NULL
           AND (finalization_status IS NULL OR
                (finalization_status IN ('claimed', 'deploying_modal', 'deploying_worker', 'verifying_public')
                 AND finalization_lease_expires_at::timestamptz < CURRENT_TIMESTAMP))
         ORDER BY updated_at ASC, id ASC
         FOR UPDATE SKIP LOCKED
         LIMIT 1
       )
       UPDATE submissions AS submission
       SET finalization_id = $1, finalization_status = 'claimed', finalization_target_sha = $2,
           finalization_source_sha256 = source_sha256, finalization_head_sha = release_head_sha,
           finalization_merge_sha = release_merge_sha, finalization_artifact_hash = release_artifact_hash,
           finalization_claimed_at = CURRENT_TIMESTAMP, finalization_lease_expires_at = $3,
           finalization_attempts = COALESCE(finalization_attempts, 0) + 1,
           finalization_failure_code = NULL, finalization_modal_receipt = NULL,
           finalization_worker_receipt = NULL, automation_updated_at = CURRENT_TIMESTAMP
       FROM candidate
       WHERE submission.id = candidate.id
       RETURNING submission.id,submission.slug,submission.selected_runtime,
                 submission.finalization_id,submission.finalization_target_sha,
                 submission.finalization_source_sha256,submission.finalization_head_sha,
                 submission.finalization_merge_sha,submission.finalization_artifact_hash,
                 submission.finalization_lease_expires_at,submission.finalization_attempts`,
      [finalizationId, targetSha, leaseExpiresAt, canonicalOwner, ...targetValues]
    ));
    return finalizationClaimRow(result.rows[0]);
  }
  if (databaseKind(env) === 'd1') {
    const targetPairs = targets.map(() => '(published_slug = ? AND source_sha256 = ?)').join(' OR ');
    const row = await env.BALANCE_DB.prepare(
      `SELECT id,slug,selected_runtime,source_sha256,published_slug,workflow_version,build_evidence,
              release_issue_url,release_pr_url,release_pr_number,release_branch,
              release_head_sha,release_merge_sha,release_artifact_hash,
              finalization_status,finalization_lease_expires_at,finalization_attempts
       FROM submissions
       WHERE user_id = ? AND status = 'ready_for_deploy' AND release_phase = 'merged_verified'
         AND (${targetPairs})
         AND selected_runtime IN ('worker-native', 'modal-hosted')
         AND source_sha256 IS NOT NULL AND published_slug IS NOT NULL
         AND workflow_version IS NOT NULL AND build_evidence IS NOT NULL
         AND release_issue_url IS NOT NULL AND release_pr_url IS NOT NULL
         AND release_pr_number IS NOT NULL AND release_branch IS NOT NULL
         AND release_head_sha IS NOT NULL AND release_merge_sha IS NOT NULL
         AND release_artifact_hash IS NOT NULL
         AND (finalization_status IS NULL OR
              (finalization_status IN ('claimed', 'deploying_modal', 'deploying_worker', 'verifying_public')
               AND finalization_lease_expires_at < ?))
       ORDER BY updated_at ASC, id ASC LIMIT 1`
    ).bind(canonicalOwner, ...targetValues, claimedAt).first();
    if (!row) return null;
    const updated = await env.BALANCE_DB.prepare(
      `UPDATE submissions
       SET finalization_id = ?, finalization_status = 'claimed', finalization_target_sha = ?,
           finalization_source_sha256 = ?, finalization_head_sha = ?,
           finalization_merge_sha = ?, finalization_artifact_hash = ?,
           finalization_claimed_at = ?, finalization_lease_expires_at = ?,
           finalization_attempts = COALESCE(finalization_attempts, 0) + 1,
           finalization_failure_code = NULL, finalization_modal_receipt = NULL,
           finalization_worker_receipt = NULL, automation_updated_at = ?
       WHERE id = ? AND user_id = ?
         AND status = 'ready_for_deploy' AND release_phase = 'merged_verified'
         AND source_sha256 IS NOT NULL AND published_slug IS NOT NULL
         AND workflow_version IS NOT NULL AND build_evidence IS NOT NULL
         AND release_issue_url IS NOT NULL AND release_pr_url IS NOT NULL
         AND release_pr_number IS NOT NULL AND release_branch IS NOT NULL
         AND selected_runtime = ? AND source_sha256 = ? AND published_slug = ?
         AND workflow_version = ? AND build_evidence = ?
         AND release_issue_url = ? AND release_pr_url = ? AND release_pr_number = ?
         AND release_branch = ? AND release_head_sha = ? AND release_merge_sha = ?
         AND release_artifact_hash = ?
         AND (finalization_status IS NULL OR
              (finalization_status IN ('claimed', 'deploying_modal', 'deploying_worker', 'verifying_public')
               AND finalization_lease_expires_at < ?))`
    ).bind(
      finalizationId, targetSha, row.source_sha256, row.release_head_sha,
      row.release_merge_sha, row.release_artifact_hash, claimedAt, leaseExpiresAt, claimedAt, row.id,
      canonicalOwner, row.selected_runtime, row.source_sha256, row.published_slug, row.workflow_version,
      row.build_evidence, row.release_issue_url, row.release_pr_url, row.release_pr_number,
      row.release_branch, row.release_head_sha, row.release_merge_sha,
      row.release_artifact_hash, claimedAt,
    ).run();
    if (!updated.meta || !updated.meta.changes) return null;
    return finalizationClaimRow({
      ...row,
      finalization_id: finalizationId,
      finalization_target_sha: targetSha,
      finalization_source_sha256: row.source_sha256,
      finalization_head_sha: row.release_head_sha,
      finalization_merge_sha: row.release_merge_sha,
      finalization_artifact_hash: row.release_artifact_hash,
      finalization_lease_expires_at: leaseExpiresAt,
      finalization_attempts: Number(row.finalization_attempts || 0) + 1,
    });
  }
  const targetMap = new Map(targets.map((target) => [target.slug, target.source_sha256]));
  for (const record of mockSubmissions.values()) {
    const expiry = Date.parse(String(record.finalization_lease_expires_at || ''));
    const claimable = record.finalization_status == null ||
      (['claimed', 'deploying_modal', 'deploying_worker', 'verifying_public'].includes(record.finalization_status) &&
       Number.isFinite(expiry) && expiry < now.getTime());
    if (record.user_id === canonicalOwner &&
        targetMap.get(record.published_slug) === record.source_sha256 &&
        record.status === 'ready_for_deploy' && record.release_phase === 'merged_verified' &&
        safeRuntime(record.selected_runtime) && safeGitSha(record.release_head_sha) &&
        safeGitSha(record.release_merge_sha) && safeSha256(record.release_artifact_hash) &&
        safeSha256(record.source_sha256) && safeSlug(record.published_slug) &&
        SAFE_WORKFLOW_VERSION_RE.test(String(record.workflow_version || '')) &&
        safeBuildEvidence(record.build_evidence).checks.length &&
        safeGithubUrl(record.release_issue_url, 'issues') && safeGithubUrl(record.release_pr_url, 'pull') &&
        Number.isSafeInteger(Number(record.release_pr_number)) && Number(record.release_pr_number) > 0 &&
        safeReleaseBranch(record.release_branch) && claimable) {
      record.finalization_id = finalizationId;
      record.finalization_status = 'claimed';
      record.finalization_target_sha = targetSha;
      record.finalization_source_sha256 = record.source_sha256;
      record.finalization_head_sha = record.release_head_sha;
      record.finalization_merge_sha = record.release_merge_sha;
      record.finalization_artifact_hash = record.release_artifact_hash;
      record.finalization_claimed_at = claimedAt;
      record.finalization_lease_expires_at = leaseExpiresAt;
      record.finalization_attempts = Number(record.finalization_attempts || 0) + 1;
      record.finalization_failure_code = null;
      record.finalization_modal_receipt = null;
      record.finalization_worker_receipt = null;
      record.automation_updated_at = claimedAt;
      return finalizationClaimRow(record);
    }
  }
  return null;
}

async function internalGetFinalization(env, finalizationId) {
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-finalization-detail-v1',
      `SELECT id,slug,source_sha256,selected_runtime,status,release_phase,release_head_sha,
              release_merge_sha,release_artifact_hash,promotion_evidence,finalization_id,
              finalization_status,finalization_target_sha,finalization_source_sha256,
              finalization_head_sha,finalization_merge_sha,finalization_artifact_hash,
              finalization_claimed_at,
              finalization_lease_expires_at,finalization_attempts,finalization_failure_code,
              finalization_modal_receipt,finalization_worker_receipt,automation_updated_at
       FROM submissions WHERE finalization_id = $1 LIMIT 1`,
      [finalizationId]
    ));
    return result.rows[0] || null;
  }
  if (databaseKind(env) === 'd1') {
    return await env.BALANCE_DB.prepare(
      `SELECT id,slug,source_sha256,selected_runtime,status,release_phase,release_head_sha,
              release_merge_sha,release_artifact_hash,promotion_evidence,finalization_id,
              finalization_status,finalization_target_sha,finalization_source_sha256,
              finalization_head_sha,finalization_merge_sha,finalization_artifact_hash,
              finalization_claimed_at,
              finalization_lease_expires_at,finalization_attempts,finalization_failure_code,
              finalization_modal_receipt,finalization_worker_receipt,automation_updated_at
       FROM submissions WHERE finalization_id = ? LIMIT 1`
    ).bind(finalizationId).first();
  }
  for (const record of mockSubmissions.values()) {
    if (record.finalization_id === finalizationId) return record;
  }
  return null;
}

function finalizationDetailRow(row) {
  if (!row || !/^fin_[a-f0-9]{32}$/.test(String(row.finalization_id || ''))) return null;
  const submissionId = safeSubmissionId(row.id);
  const slug = safeSlug(row.slug);
  const runtime = safeRuntime(row.selected_runtime);
  const targetSha = safeGitSha(row.finalization_target_sha);
  const headSha = safeGitSha(row.finalization_head_sha);
  const mergeSha = safeGitSha(row.finalization_merge_sha);
  const sourceSha256 = safeSha256(row.finalization_source_sha256);
  const artifactHash = safeSha256(row.finalization_artifact_hash);
  const leaseExpiresAt = safeTimestamp(row.finalization_lease_expires_at);
  const status = String(row.finalization_status || '');
  const submissionStatus = String(row.status || '');
  const releasePhase = String(row.release_phase || '');
  const attempts = Number(row.finalization_attempts);
  if (!submissionId || !slug || !runtime || !targetSha || !headSha || !mergeSha || !sourceSha256 ||
      !artifactHash || !leaseExpiresAt ||
      !['claimed', 'deploying_modal', 'deploying_worker', 'verifying_public', 'completed', 'failed'].includes(status) ||
      !['ready_for_deploy', 'ready_for_publish', 'deployed', 'failed'].includes(submissionStatus) ||
      !['merged_verified', 'promoted'].includes(releasePhase) ||
      !Number.isSafeInteger(attempts) || attempts < 1) return null;
  const detail = {
    id: String(row.finalization_id), submission_id: submissionId, slug, runtime, status,
    target_sha: targetSha, head_sha: headSha, merge_sha: mergeSha,
    source_sha256: sourceSha256, artifact_hash: artifactHash,
    lease_expires_at: leaseExpiresAt, attempts,
    submission_status: submissionStatus, release_phase: releasePhase,
  };
  const failureCode = String(row.finalization_failure_code || '').trim();
  if (status === 'failed' && FINALIZATION_FAILURE_CODES.has(failureCode)) detail.failure_code = failureCode;
  return detail;
}

function allowedFinalizationTransition(row, targetSha, nextStatus, failureCode, now = Date.now()) {
  if (!row || row.finalization_target_sha !== targetSha) return false;
  const claimedSource = safeSha256(row.finalization_source_sha256);
  const claimedHead = safeGitSha(row.finalization_head_sha);
  const claimedMerge = safeGitSha(row.finalization_merge_sha);
  const claimedArtifact = safeSha256(row.finalization_artifact_hash);
  if (!claimedSource || !claimedHead || !claimedMerge || !claimedArtifact ||
      safeSha256(row.source_sha256 || row.sourceSha256) !== claimedSource ||
      safeGitSha(row.release_head_sha) !== claimedHead ||
      safeGitSha(row.release_merge_sha) !== claimedMerge ||
      safeSha256(row.release_artifact_hash) !== claimedArtifact) return false;
  const expiry = Date.parse(String(row.finalization_lease_expires_at || ''));
  if (!Number.isFinite(expiry) || expiry <= now) return false;
  const current = String(row.finalization_status || '');
  if (current === nextStatus) return nextStatus !== 'failed' || row.finalization_failure_code === failureCode;
  const runtime = safeRuntime(row.selected_runtime);
  if (nextStatus === 'deploying_modal') return current === 'claimed' && runtime === 'modal-hosted';
  if (nextStatus === 'deploying_worker') {
    return (current === 'claimed' && runtime === 'worker-native') ||
      (current === 'deploying_modal' && runtime === 'modal-hosted');
  }
  if (nextStatus === 'verifying_public') return current === 'deploying_worker';

  if (nextStatus === 'failed') {
    return ['claimed', 'deploying_modal', 'deploying_worker', 'verifying_public'].includes(current) && Boolean(failureCode);
  }
  return false;
}

async function internalSetFinalizationStatus(env, finalizationId, targetSha, nextStatus, failureCode = null) {
  const row = await internalGetFinalization(env, finalizationId);
  if (!allowedFinalizationTransition(row, targetSha, nextStatus, failureCode)) return false;
  if (row.finalization_status === nextStatus) return true;
  const currentStatus = row.finalization_status;
  const now = new Date().toISOString();

  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-finalization-status-v1',
      `UPDATE submissions
       SET finalization_status = $1, finalization_failure_code = $2, automation_updated_at = CURRENT_TIMESTAMP
       WHERE finalization_id = $3 AND finalization_target_sha = $4
         AND finalization_status = $5 AND finalization_lease_expires_at::timestamptz > CURRENT_TIMESTAMP
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash
       RETURNING id`,
      [nextStatus, failureCode, finalizationId, targetSha, currentStatus]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare(
      `UPDATE submissions SET finalization_status = ?, finalization_failure_code = ?, automation_updated_at = ?
       WHERE finalization_id = ? AND finalization_target_sha = ?
         AND finalization_status = ? AND finalization_lease_expires_at > ?
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash`
    ).bind(nextStatus, failureCode, now, finalizationId, targetSha, currentStatus, now).run();
    return Boolean(result.meta && result.meta.changes);
  }
  row.finalization_status = nextStatus;
  row.finalization_failure_code = failureCode;
  row.automation_updated_at = now;
  return true;
}

async function internalPromoteFinalization(env, finalizationId, targetSha, evidence) {
  const row = await internalGetFinalization(env, finalizationId);
  const sanitized = safePromotionEvidence(evidence);
  if (!row || !sanitized || row.finalization_target_sha !== targetSha ||
      row.finalization_status !== 'verifying_public' ||
      !['ready_for_deploy', 'ready_for_publish'].includes(row.status) ||
      row.release_phase !== 'merged_verified') return false;
  const expiry = Date.parse(String(row.finalization_lease_expires_at || ''));
  if (!Number.isFinite(expiry) || expiry <= Date.now()) return false;
  const claimedSource = safeSha256(row.finalization_source_sha256);
  const claimedHead = safeGitSha(row.finalization_head_sha);
  const claimedMerge = safeGitSha(row.finalization_merge_sha);
  const claimedArtifact = safeSha256(row.finalization_artifact_hash);
  if (!claimedSource || !claimedHead || !claimedMerge || !claimedArtifact ||
      safeSha256(row.source_sha256 || row.sourceSha256) !== claimedSource ||
      safeGitSha(row.release_head_sha) !== claimedHead ||
      safeGitSha(row.release_merge_sha) !== claimedMerge ||
      safeSha256(row.release_artifact_hash) !== claimedArtifact) return false;
  const promotionEvidence = JSON.stringify(sanitized);
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-finalization-promote-v1',
      `UPDATE submissions
       SET status = 'ready_for_publish', release_phase = 'promoted', promotion_evidence = $1,
           finalization_status = 'completed', finalization_failure_code = NULL,
           automation_updated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
       WHERE finalization_id = $2 AND finalization_target_sha = $3
         AND finalization_status = 'verifying_public'
         AND status IN ('ready_for_deploy', 'ready_for_publish')
         AND release_phase = 'merged_verified'
         AND finalization_lease_expires_at::timestamptz > CURRENT_TIMESTAMP
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash
       RETURNING id`,
      [promotionEvidence, finalizationId, targetSha]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare(
      `UPDATE submissions
       SET status = 'ready_for_publish', release_phase = 'promoted', promotion_evidence = ?,
           finalization_status = 'completed', finalization_failure_code = NULL,
           automation_updated_at = ?, updated_at = ?
       WHERE finalization_id = ? AND finalization_target_sha = ?
         AND finalization_status = 'verifying_public'
         AND status IN ('ready_for_deploy', 'ready_for_publish')
         AND release_phase = 'merged_verified' AND finalization_lease_expires_at > ?
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash`
    ).bind(promotionEvidence, now, now, finalizationId, targetSha, now).run();
    return Boolean(result.meta && result.meta.changes);
  }
  row.status = 'ready_for_publish';
  row.release_phase = 'promoted';
  row.promotion_evidence = promotionEvidence;
  row.finalization_status = 'completed';
  row.finalization_failure_code = null;
  row.automation_updated_at = now;
  row.updated_at = now;
  return true;
}

async function internalGetSubmissionDetail(env, submissionId) {
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-submission-detail-v1',
      `SELECT id,slug,source_sha256,selected_runtime,workflow_version,published_slug,build_evidence,
              status,release_phase,release_issue_url,release_pr_url,release_pr_number,
              release_branch,release_head_sha,release_merge_sha,release_artifact_hash,
              modal_app,modal_url,canary_evidence,promotion_evidence
       FROM submissions
       WHERE id = $1
       LIMIT 1`,
      [submissionId]
    ));
    return result.rows[0] || null;
  }
  if (databaseKind(env) === 'd1') {
    return await env.BALANCE_DB
      .prepare(`SELECT id,slug,source_sha256,selected_runtime,workflow_version,published_slug,build_evidence,
                       status,release_phase,release_issue_url,release_pr_url,release_pr_number,
                       release_branch,release_head_sha,release_merge_sha,release_artifact_hash,
                       modal_app,modal_url,canary_evidence,promotion_evidence
                FROM submissions
                WHERE id = ?
                LIMIT 1`)
      .bind(submissionId).first();
  }
  for (const record of mockSubmissions.values()) {
    if (record.id === submissionId) return record;
  }
  return null;
}

function allowedInternalPriorStates(status) {
  if (status === 'needs_review') return ['processing'];
  if (status === 'ready_for_deploy') return ['processing'];

  if (status === 'failed') return ['processing', 'needs_review', 'ready_for_deploy', 'ready_for_publish'];
  return [];
}

async function internalSetSubmissionStatus(env, submissionId, status, failureCode) {
  const states = allowedInternalPriorStates(status);
  if (!states.length) return false;
  const failure = status === 'failed' || status === 'needs_review' ? safeFailureCode(failureCode) : null;
  if (databaseKind(env) === 'neon') {
    const params = [status, failure, submissionId, ...states];
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-submission-status-v1',
      `UPDATE submissions
       SET status = $1, failure_code = $2, updated_at = CURRENT_TIMESTAMP
       WHERE id = $3 AND status IN (${states.map((_, index) => `$${index + 4}`).join(', ')})
         AND finalization_id IS NULL
       RETURNING id`,
      params
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB
      .prepare(`UPDATE submissions SET status = ?, failure_code = ?, updated_at = ? WHERE id = ? AND status IN (${states.map(() => '?').join(', ')}) AND finalization_id IS NULL`)
      .bind(status, failure, new Date().toISOString(), submissionId, ...states).run();
    return Boolean(result.meta && result.meta.changes);
  }
  for (const record of mockSubmissions.values()) {
    if (record.id === submissionId && states.includes(record.status) && !record.finalization_id) {
      record.status = status;
      record.failure_code = failure;
      record.updated_at = new Date().toISOString();
      return true;
    }
  }
  return false;
}

function mergedReleaseRecoverySnapshot(row, submissionId, mergeSha) {
  if (!row || row.id !== submissionId || row.status !== 'failed' || row.release_phase !== 'merged_verified') return null;
  const sourceSha256 = safeSha256(row.source_sha256);
  const headSha = safeGitSha(row.release_head_sha);
  const recordedMergeSha = safeGitSha(row.release_merge_sha);
  const artifactHash = safeSha256(row.release_artifact_hash);
  const issueUrl = safeGithubUrl(row.release_issue_url, 'issues');
  const prUrl = safeGithubUrl(row.release_pr_url, 'pull');
  const branch = safeReleaseBranch(row.release_branch);
  const runtime = safeRuntime(row.selected_runtime);
  const canonicalSlug = safeSlug(row.slug);
  const publishedSlug = safeSlug(row.published_slug);
  const workflowVersion = String(row.workflow_version || '').trim();
  const prNumber = Number(row.release_pr_number);
  const rawBuildEvidence = typeof row.build_evidence === 'string'
    ? row.build_evidence
    : row.build_evidence && typeof row.build_evidence === 'object' && !Array.isArray(row.build_evidence)
      ? JSON.stringify(row.build_evidence)
      : '';
  const buildEvidence = safeBuildEvidence(rawBuildEvidence);
  if (!sourceSha256 || !headSha || !recordedMergeSha || recordedMergeSha !== mergeSha || !artifactHash ||
      !issueUrl || !prUrl || !branch || !runtime || !canonicalSlug || canonicalSlug !== publishedSlug ||
      !Number.isSafeInteger(prNumber) || prNumber < 1 ||
      !prUrl.endsWith(`/pull/${prNumber}`) || branch !== `omo-release/${submissionId}-${publishedSlug}` ||
      !SAFE_WORKFLOW_VERSION_RE.test(workflowVersion) || !workflowVersion.startsWith(`${publishedSlug}@`) ||
      !buildEvidence.checks.length || buildEvidence.source_sha256 !== sourceSha256) {
    return null;
  }
  return {
    sourceSha256, headSha, recordedMergeSha, artifactHash, issueUrl, prUrl, prNumber,
    branch, runtime, canonicalSlug, publishedSlug, workflowVersion, rawBuildEvidence,
  };
}

async function internalResumeMergedRelease(env, submissionId, mergeSha) {
  const row = await internalGetSubmissionDetail(env, submissionId);
  const snapshot = mergedReleaseRecoverySnapshot(row, submissionId, mergeSha);
  if (!snapshot) return false;
  const values = [
    submissionId, snapshot.recordedMergeSha, snapshot.sourceSha256, snapshot.headSha,
    snapshot.artifactHash, snapshot.issueUrl, snapshot.prUrl, snapshot.prNumber,
    snapshot.branch, snapshot.runtime, snapshot.publishedSlug, snapshot.workflowVersion,
    snapshot.rawBuildEvidence, snapshot.canonicalSlug,
  ];
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-resume-merged-release-v1',
      `UPDATE submissions
       SET status = 'ready_for_deploy', failure_code = NULL, updated_at = CURRENT_TIMESTAMP
       WHERE id = $1 AND release_merge_sha = $2 AND source_sha256 = $3
         AND release_head_sha = $4 AND release_artifact_hash = $5
         AND release_issue_url = $6 AND release_pr_url = $7 AND release_pr_number = $8
         AND release_branch = $9 AND selected_runtime = $10 AND published_slug = $11
         AND workflow_version = $12 AND build_evidence = $13 AND slug = $14
         AND status = 'failed' AND release_phase = 'merged_verified'
       RETURNING id`,
      values
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare(
      `UPDATE submissions
       SET status = 'ready_for_deploy', failure_code = NULL, updated_at = ?
       WHERE id = ? AND release_merge_sha = ? AND source_sha256 = ?
         AND release_head_sha = ? AND release_artifact_hash = ?
         AND release_issue_url = ? AND release_pr_url = ? AND release_pr_number = ?
         AND release_branch = ? AND selected_runtime = ? AND published_slug = ?
         AND workflow_version = ? AND build_evidence = ? AND slug = ?
         AND status = 'failed' AND release_phase = 'merged_verified'`
    ).bind(new Date().toISOString(), ...values).run();
    return Boolean(result.meta && result.meta.changes);
  }
  row.status = 'ready_for_deploy';
  row.failure_code = null;
  row.updated_at = new Date().toISOString();
  return true;
}

async function internalSetRuntimeDecision(env, submissionId, decision) {
  const compatibility = JSON.stringify({
    recommended: decision.recommended,
    requested: decision.requested,
    compatible: decision.compatible,
  }, null, 0);
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-submission-runtime-v1',
      `UPDATE submissions
       SET selected_runtime = $1, runtime_policy = $2, runtime_compatibility = $3, updated_at = CURRENT_TIMESTAMP
       WHERE id = $4 AND status = 'processing'
       RETURNING id`,
      [decision.effective, decision.reason, compatibility, submissionId]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB
      .prepare("UPDATE submissions SET selected_runtime = ?, runtime_policy = ?, runtime_compatibility = ?, updated_at = ? WHERE id = ? AND status = 'processing'")
      .bind(decision.effective, decision.reason, compatibility, new Date().toISOString(), submissionId).run();
    return Boolean(result.meta && result.meta.changes);
  }
  for (const record of mockSubmissions.values()) {
    if (record.id === submissionId && record.status === 'processing') {
      record.selected_runtime = decision.effective;
      record.runtime_policy = decision.reason;
      record.runtime_compatibility = compatibility;
      record.updated_at = new Date().toISOString();
      return true;
    }
  }
  return false;
}

async function internalSetDeployment(env, submissionId, deployment) {
  const evidence = JSON.stringify(deployment.evidence, null, 0);
  const fromStates = ['processing'];
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-submission-deployment-v1',
      `UPDATE submissions
       SET status = $1, failure_code = NULL, published_slug = $2, workflow_version = $3, build_evidence = $4, updated_at = CURRENT_TIMESTAMP
       WHERE id = $5 AND status IN (${fromStates.map((_, index) => `$${index + 6}`).join(', ')})
       RETURNING id`,
      [deployment.status, deployment.publishedSlug, deployment.workflowVersion, evidence, submissionId, ...fromStates]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB
      .prepare(`UPDATE submissions SET status = ?, failure_code = NULL, published_slug = ?, workflow_version = ?, build_evidence = ?, updated_at = ? WHERE id = ? AND status IN (${fromStates.map(() => '?').join(', ')})`)
      .bind(deployment.status, deployment.publishedSlug, deployment.workflowVersion, evidence, new Date().toISOString(), submissionId, ...fromStates).run();
    return Boolean(result.meta && result.meta.changes);
  }
  for (const record of mockSubmissions.values()) {
    if (record.id === submissionId && fromStates.includes(record.status)) {
      record.status = deployment.status;
      record.failure_code = null;
      record.published_slug = deployment.publishedSlug;
      record.workflow_version = deployment.workflowVersion;
      record.build_evidence = evidence;
      record.updated_at = new Date().toISOString();
      return true;
    }
  }
  return false;
}

async function internalSetRelease(env, submissionId, release) {
  const now = new Date().toISOString();
  const canary = release.canary ? JSON.stringify(release.canary, null, 0) : null;
  const promotionEvidence = release.promotionEvidence ? JSON.stringify(release.promotionEvidence, null, 0) : null;
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-submission-release-v1',
      `UPDATE submissions
       SET release_phase = $1,
           release_issue_url = $2,
           release_pr_url = $3,
           release_pr_number = $4,
           release_branch = $5,
           release_head_sha = $6,
           release_merge_sha = $7,
           release_artifact_hash = $8,
           modal_app = $9,
           modal_url = $10,
           canary_evidence = $11,
           promotion_evidence = $12,
           updated_at = CURRENT_TIMESTAMP
       WHERE id = $13
         AND status IN ('ready_for_deploy', 'ready_for_publish')
         AND finalization_id IS NULL
       RETURNING id`,
      [
        release.phase, release.issueUrl, release.prUrl, release.prNumber, release.branch,
        release.headSha, release.mergeSha, release.artifactHash, release.modalApp,
        release.modalUrl, canary, promotionEvidence, submissionId,
      ]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB
      .prepare("UPDATE submissions SET release_phase = ?, release_issue_url = ?, release_pr_url = ?, release_pr_number = ?, release_branch = ?, release_head_sha = ?, release_merge_sha = ?, release_artifact_hash = ?, modal_app = ?, modal_url = ?, canary_evidence = ?, promotion_evidence = ?, updated_at = ? WHERE id = ? AND status IN ('ready_for_deploy', 'ready_for_publish') AND finalization_id IS NULL")
      .bind(
        release.phase, release.issueUrl, release.prUrl, release.prNumber, release.branch,
        release.headSha, release.mergeSha, release.artifactHash, release.modalApp,
        release.modalUrl, canary, promotionEvidence, now, submissionId,
      ).run();
    return Boolean(result.meta && result.meta.changes);
  }
  for (const record of mockSubmissions.values()) {
    if (record.id === submissionId && ['ready_for_deploy', 'ready_for_publish'].includes(record.status) &&
        !record.finalization_id) {
      record.release_phase = release.phase;
      record.release_issue_url = release.issueUrl;
      record.release_pr_url = release.prUrl;
      record.release_pr_number = release.prNumber;
      record.release_branch = release.branch;
      record.release_head_sha = release.headSha;
      record.release_merge_sha = release.mergeSha || null;
      record.release_artifact_hash = release.artifactHash;
      record.modal_app = release.modalApp || null;
      record.modal_url = release.modalUrl || null;
      record.canary_evidence = canary;
      record.promotion_evidence = promotionEvidence;
      record.updated_at = now;
      return true;
    }
  }
  return false;
}

async function internalMarkDeployed(env, submissionId, metadata) {
  const deployedAt = new Date().toISOString();
  const deploymentMeta = JSON.stringify(metadata, null, 0);
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-internal-submission-deployed-v1',
      `UPDATE submissions
       SET status = 'deployed', failure_code = NULL, deployment_metadata = $1, updated_at = CURRENT_TIMESTAMP, deployed_at = CURRENT_TIMESTAMP
       WHERE id = $2
         AND status = 'ready_for_publish'
         AND published_slug IS NOT NULL
         AND workflow_version IS NOT NULL
         AND build_evidence IS NOT NULL
         AND release_phase = 'promoted'
         AND finalization_status = 'completed'
         AND source_sha256 = finalization_source_sha256
         AND release_head_sha = finalization_head_sha
         AND release_merge_sha = finalization_merge_sha
         AND release_artifact_hash = finalization_artifact_hash
         AND promotion_evidence::jsonb ->> 'status' = 'live'
         AND promotion_evidence::jsonb -> 'R1' ->> 'status' = 'passed'
         AND promotion_evidence::jsonb -> 'R2' ->> 'status' = 'passed'
         AND promotion_evidence::jsonb -> 'R3' ->> 'status' = 'passed'
         AND promotion_evidence::jsonb -> 'R4' ->> 'status' IN ('published', 'excluded_premium')
       RETURNING id`,
      [deploymentMeta, submissionId]
    ));
    return result.rowCount === 1;
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB
      .prepare("UPDATE submissions SET status = 'deployed', failure_code = NULL, deployment_metadata = ?, updated_at = ?, deployed_at = ? WHERE id = ? AND status = 'ready_for_publish' AND published_slug IS NOT NULL AND workflow_version IS NOT NULL AND build_evidence IS NOT NULL AND release_phase = 'promoted' AND finalization_status = 'completed' AND source_sha256 = finalization_source_sha256 AND release_head_sha = finalization_head_sha AND release_merge_sha = finalization_merge_sha AND release_artifact_hash = finalization_artifact_hash AND json_extract(promotion_evidence, '$.status') = 'live' AND json_extract(promotion_evidence, '$.R1.status') = 'passed' AND json_extract(promotion_evidence, '$.R2.status') = 'passed' AND json_extract(promotion_evidence, '$.R3.status') = 'passed' AND json_extract(promotion_evidence, '$.R4.status') IN ('published', 'excluded_premium')")
      .bind(deploymentMeta, deployedAt, deployedAt, submissionId).run();
    return Boolean(result.meta && result.meta.changes);
  }
  for (const record of mockSubmissions.values()) {
    if (record.id === submissionId && record.status === 'ready_for_publish' &&
        record.published_slug && record.workflow_version && record.build_evidence &&
        record.release_phase === 'promoted' && record.finalization_status === 'completed' &&
        safeSha256(record.source_sha256 || record.sourceSha256) === safeSha256(record.finalization_source_sha256) &&
        safeGitSha(record.release_head_sha) === safeGitSha(record.finalization_head_sha) &&
        safeGitSha(record.release_merge_sha) === safeGitSha(record.finalization_merge_sha) &&
        safeSha256(record.release_artifact_hash) === safeSha256(record.finalization_artifact_hash) &&
        safePromotionEvidence(record.promotion_evidence)) {
      record.status = 'deployed';
      record.failure_code = null;
      record.deployment_metadata = deploymentMeta;
      record.updated_at = deployedAt;
      record.deployed_at = deployedAt;
      return true;
    }
  }
  return false;
}

async function applySubmissionsSchemaMigration(env) {
  if (databaseKind(env) !== 'neon') throw new Error('internal_error');
  const client = await getNeonPool(env).connect();
  try {
    await client.query('BEGIN');
    const applied = [];
    for (const [name, statement] of SUBMISSIONS_SCHEMA_MIGRATIONS) {
      await client.query(prepared(`omo-submissions-migrate-${name}-v1`, statement, []));
      applied.push(name);
    }
    await client.query('COMMIT');
    return applied;
  } catch (e) {
    try { await client.query('ROLLBACK'); } catch { /* no-op */ }
    throw new Error('internal_error');
  } finally {
    await client.release();
  }
}

async function applyFinalizationReceiptMigration(env) {
  if (databaseKind(env) !== 'neon') throw new Error('internal_error');
  const client = await getNeonPool(env).connect();
  try {
    await client.query('BEGIN');
    const applied = [];
    for (const [name, statement] of FINALIZATION_RECEIPT_MIGRATIONS) {
      await client.query(prepared(`omo-finalization-receipt-migrate-${name}-v1`, statement, []));
      applied.push(name);
    }
    await client.query('COMMIT');
    return applied;
  } catch {
    try { await client.query('ROLLBACK'); } catch { /* no-op */ }
    throw new Error('internal_error');
  } finally {
    await client.release();
  }
}

async function applyFinalizationSchemaMigration(env) {
  if (databaseKind(env) !== 'neon') throw new Error('internal_error');
  const client = await getNeonPool(env).connect();
  try {
    await client.query('BEGIN');
    const applied = [];
    for (const [name, statement] of FINALIZATION_SCHEMA_MIGRATIONS) {
      await client.query(prepared(`omo-finalization-schema-migrate-${name}-v1`, statement, []));
      applied.push(name);
    }
    await client.query('COMMIT');
    return applied;
  } catch {
    try { await client.query('ROLLBACK'); } catch { /* no-op */ }
    throw new Error('internal_error');
  } finally {
    await client.release();
  }
}

async function inspectFinalizationReceiptSchema(env) {
  if (databaseKind(env) !== 'neon') throw new Error('internal_error');
  const client = await getNeonPool(env).connect();
  try {
    const table = await client.query(prepared(
      'omo-finalization-receipt-schema-table-v1', SUBMISSIONS_TABLE_EXISTS_SQL, []
    ));
    const columns = await client.query(prepared(
      'omo-finalization-receipt-schema-columns-v1', SUBMISSIONS_COLUMNS_SQL,
      [FINALIZATION_RECEIPT_COLUMNS]
    ));
    const presentSet = new Set((columns.rows || [])
      .map((row) => String(row.column_name || ''))
      .filter((name) => FINALIZATION_RECEIPT_COLUMNS.includes(name)));
    return {
      table_exists: Boolean(table.rows && table.rows[0] && table.rows[0].table_exists),
      present: FINALIZATION_RECEIPT_COLUMNS.filter((name) => presentSet.has(name)),
      missing: FINALIZATION_RECEIPT_COLUMNS.filter((name) => !presentSet.has(name)),
    };
  } catch {
    throw new Error('internal_error');
  } finally {
    await client.release();
  }
}

async function inspectSubmissionsSchema(env) {
  if (databaseKind(env) !== 'neon') throw new Error('internal_error');
  const client = await getNeonPool(env).connect();
  try {
    const table = await client.query(prepared(
      'omo-submissions-schema-table-v1',
      SUBMISSIONS_TABLE_EXISTS_SQL,
      []
    ));
    const columns = await client.query(prepared(
      'omo-submissions-schema-columns-v1',
      SUBMISSIONS_COLUMNS_SQL,
      [REQUIRED_SUBMISSIONS_COLUMNS]
    ));
    const presentSet = new Set((columns.rows || [])
      .map((row) => String(row.column_name || ''))
      .filter((name) => REQUIRED_SUBMISSIONS_COLUMNS.includes(name)));
    const present = REQUIRED_SUBMISSIONS_COLUMNS.filter((name) => presentSet.has(name));
    const missing = REQUIRED_SUBMISSIONS_COLUMNS.filter((name) => !presentSet.has(name));
    return {
      table_exists: Boolean(table.rows && table.rows[0] && table.rows[0].table_exists),
      present,
      missing,
    };
  } catch {
    throw new Error('internal_error');
  } finally {
    await client.release();
  }
}

function normalizeRequestedRuntime(value) {
  const requested = String(value || 'auto').trim();
  return REQUESTED_RUNTIMES.has(requested) ? requested : '';
}

function readRuntimePreference(body, fallback) {
  const hasRuntimePreference = Object.prototype.hasOwnProperty.call(body || {}, 'runtime_preference');
  const hasRequestedRuntime = Object.prototype.hasOwnProperty.call(body || {}, 'requested_runtime');
  const canonical = hasRuntimePreference ? normalizeRequestedRuntime(body.runtime_preference) : '';
  const alias = hasRequestedRuntime ? normalizeRequestedRuntime(body.requested_runtime) : '';
  if ((hasRuntimePreference && !canonical) || (hasRequestedRuntime && !alias)) {
    return {
      value: '',
      error: 'invalid_runtime_preference',
      message: 'runtime_preference must be auto, worker-native, or modal-hosted.',
    };
  }
  if (hasRuntimePreference && hasRequestedRuntime && canonical !== alias) {
    return {
      value: '',
      error: 'conflicting_runtime_preference',
      message: 'Use runtime_preference; requested_runtime is only a backward-compatible alias.',
    };
  }
  return { value: canonical || alias || normalizeRequestedRuntime(fallback) };
}

async function updateSubmissionRuntime(env, userId, submissionId, requestedRuntime) {
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-submission-runtime-update-v1',
      `UPDATE submissions SET requested_runtime = $1, updated_at = $2
       WHERE id = $3 AND user_id = $4 AND status IN ('queued','needs_review') AND requested_runtime <> $1
       RETURNING id,status,requested_runtime`,
      [requestedRuntime, now, submissionId, userId]
    ));
    if (result.rowCount === 1) return { status: 'updated', row: result.rows[0], changed: true };
    const existing = await getNeonPool(env).query(prepared(
      'omo-submission-runtime-existing-v1',
      'SELECT id,status,requested_runtime FROM submissions WHERE id = $1 AND user_id = $2',
      [submissionId, userId]
    ));
    if (!existing.rows[0]) return { status: 'not_found' };
    if (!SUBMISSION_RUNTIME_MUTABLE_STATES.has(existing.rows[0].status)) return { status: 'immutable', row: existing.rows[0] };
    if (existing.rows[0].requested_runtime === requestedRuntime) return { status: 'updated', row: existing.rows[0], changed: false };
    return { status: 'immutable', row: existing.rows[0] };
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB
      .prepare("UPDATE submissions SET requested_runtime = ?, updated_at = ? WHERE id = ? AND user_id = ? AND status IN ('queued','needs_review') AND requested_runtime <> ?")
      .bind(requestedRuntime, now, submissionId, userId, requestedRuntime).run();
    if (result.meta && result.meta.changes) {
      const row = await env.BALANCE_DB.prepare('SELECT id,status,requested_runtime FROM submissions WHERE id = ? AND user_id = ?').bind(submissionId, userId).first();
      return { status: 'updated', row, changed: true };
    }
    const existing = await env.BALANCE_DB.prepare('SELECT id,status,requested_runtime FROM submissions WHERE id = ? AND user_id = ?').bind(submissionId, userId).first();
    if (!existing) return { status: 'not_found' };
    if (!SUBMISSION_RUNTIME_MUTABLE_STATES.has(existing.status)) return { status: 'immutable', row: existing };
    if (existing.requested_runtime === requestedRuntime) return { status: 'updated', row: existing, changed: false };
    return { status: 'immutable', row: existing };
  }
  for (const record of mockSubmissions.values()) {
    if (record.id === submissionId && record.userId === userId) {
      if (!SUBMISSION_RUNTIME_MUTABLE_STATES.has(record.status)) return { status: 'immutable', row: record };
      if (record.requested_runtime === requestedRuntime) return { status: 'updated', row: record, changed: false };
      record.requested_runtime = requestedRuntime;
      record.updated_at = now;
      return { status: 'updated', row: record, changed: true };
    }
  }
  return { status: 'not_found' };
}

function reviewedSourceApprovalAllowlist() {
  const rows = [...HOSTED_MODAL_SKILL_ROWS, ...HOSTED_WORKER_SKILL_ROWS];
  const allowlist = new Map();
  for (const [runtimeSlug, runtime] of rows) {
    const sourceSha256 = safeSha256(runtime && runtime.reviewed_source_sha256);
    const safeRuntimeSlug = safeSlug(runtimeSlug);
    if (sourceSha256 && safeRuntimeSlug) allowlist.set(sourceSha256, safeRuntimeSlug);
  }
  return allowlist;
}

const APPROVAL_REASON_EXACT_SOURCE_SLUG_COLLISION = 'exact_source_slug_collision';
const RETRYABLE_EXACT_MATCH_RELEASE_FAILURE_CODES = new Set([
  'build_or_deploy_failed',
  'canary_or_internal_failed',
  'profile_identity_mismatch',
]);

function approvalSafeRow(row) {
  return row && safeSubmissionId(row.id) ? row : null;
}

async function approveExactMatchSlugCollision(env, userId, submissionId) {
  const allowedSourceHashes = reviewedSourceApprovalAllowlist();
  if (!allowedSourceHashes.size) return { status: 'not_approvable' };
  const now = new Date().toISOString();
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-submission-approve-v1',
      `WITH updated AS (
         UPDATE submissions
         SET status = 'ready_for_deploy',
             failure_code = NULL,
             updated_at = CURRENT_TIMESTAMP,
             approved_at = CURRENT_TIMESTAMP,
             approved_by = $2,
             approval_reason = '${APPROVAL_REASON_EXACT_SOURCE_SLUG_COLLISION}'
         WHERE id = $1
           AND user_id = $2
           AND source_sha256 = ANY($3::text[])
           AND status = 'needs_review'
           AND failure_code = 'slug_collision'
         RETURNING id,name,slug,status,requested_runtime,selected_runtime,runtime_policy,runtime_compatibility,source_sha256,failure_code,workflow_version,published_slug,created_at,updated_at,approved_at,approved_by,approval_reason,deployed_at,build_evidence
       ),
       current AS (
         SELECT id,name,slug,status,requested_runtime,selected_runtime,runtime_policy,runtime_compatibility,source_sha256,failure_code,workflow_version,published_slug,created_at,updated_at,approved_at,approved_by,approval_reason,deployed_at,build_evidence
         FROM submissions
         WHERE id = $1
           AND user_id = $2
           AND source_sha256 = ANY($3::text[])
           AND status = 'ready_for_deploy'
           AND failure_code IS NULL
           AND approved_by = $2
           AND approval_reason = '${APPROVAL_REASON_EXACT_SOURCE_SLUG_COLLISION}'
           AND approved_at IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM updated)
       )
       SELECT * FROM updated
       UNION ALL
       SELECT * FROM current
       LIMIT 1`,
      [submissionId, userId, [...allowedSourceHashes.keys()]]
    ));
    const row = approvalSafeRow(result.rows[0]);
    if (row) return { status: 'approved', row };
    const existing = await getSubmissionApprovalState(env, userId, submissionId);
    if (!existing) return { status: 'not_found' };
    return { status: 'not_approvable' };
  }
  if (databaseKind(env) === 'd1') {
    for (const sourceSha256 of allowedSourceHashes.keys()) {
      const updated = await env.BALANCE_DB
        .prepare(`UPDATE submissions
          SET status = 'ready_for_deploy', failure_code = NULL, updated_at = ?, approved_at = ?, approved_by = ?, approval_reason = ?
          WHERE id = ? AND user_id = ? AND source_sha256 = ? AND status = 'needs_review' AND failure_code = 'slug_collision'`)
        .bind(now, now, userId, APPROVAL_REASON_EXACT_SOURCE_SLUG_COLLISION, submissionId, userId, sourceSha256).run();
      if (updated.meta && updated.meta.changes) {
        const row = await getSubmissionForOwner(env, userId, submissionId);
        return { status: 'approved', row };
      }
    }
    const existing = await getSubmissionApprovalState(env, userId, submissionId);
    if (!existing) return { status: 'not_found' };
    if (existing.status === 'ready_for_deploy' && !existing.failure_code &&
        safeSha256(existing.source_sha256) && allowedSourceHashes.has(safeSha256(existing.source_sha256)) &&
        existing.approved_by === userId &&
        existing.approval_reason === APPROVAL_REASON_EXACT_SOURCE_SLUG_COLLISION &&
        existing.approved_at) {
      return { status: 'approved', row: existing };
    }
    return { status: 'not_approvable' };
  }
  let foundOwnerRecord = false;
  for (const record of mockSubmissions.values()) {
    if (record.id !== submissionId || (record.userId !== userId && record.user_id !== userId)) continue;
    foundOwnerRecord = true;
    const sourceSha256 = safeSha256(record.source_sha256 || record.sourceSha256);
    if (record.status === 'ready_for_deploy' && !record.failure_code &&
        sourceSha256 && allowedSourceHashes.has(sourceSha256) &&
        record.approved_by === userId &&
        record.approval_reason === APPROVAL_REASON_EXACT_SOURCE_SLUG_COLLISION &&
        record.approved_at) {
      return { status: 'approved', row: record };
    }
    if (record.status === 'needs_review' && record.failure_code === 'slug_collision' &&
        sourceSha256 && allowedSourceHashes.has(sourceSha256)) {
      record.status = 'ready_for_deploy';
      record.failure_code = null;
      record.updated_at = now;
      record.approved_at = now;
      record.approved_by = userId;
      record.approval_reason = APPROVAL_REASON_EXACT_SOURCE_SLUG_COLLISION;
      return { status: 'approved', row: record };
    }
    return { status: 'not_approvable' };
  }
  return foundOwnerRecord ? { status: 'not_approvable' } : { status: 'not_found' };
}

function releaseVerificationResumeSnapshot(record, submissionId, exactSlug = '') {
  if (!record || record.id !== submissionId || record.status !== 'failed' ||
      record.failure_code !== 'canary_or_internal_failed' ||
      !['pr_open', 'ci_passed'].includes(record.release_phase) ||
      (exactSlug && record.slug !== exactSlug)) return null;
  const sourceSha256 = safeSha256(record.source_sha256 || record.sourceSha256);
  const runtime = safeRuntime(record.selected_runtime);
  const runtimePolicy = safeRuntimePolicy(record.runtime_policy);
  const workflowVersion = String(record.workflow_version || '').trim();
  const publishedSlug = safeSlug(record.published_slug);
  const buildEvidence = safeBuildEvidence(record.build_evidence);
  const issueUrl = safeGithubUrl(record.release_issue_url, 'issues');
  const prUrl = safeGithubUrl(record.release_pr_url, 'pull');
  const prNumber = Number(record.release_pr_number);
  const branch = safeReleaseBranch(record.release_branch);
  const headSha = safeGitSha(record.release_head_sha);
  const artifactHash = safeSha256(record.release_artifact_hash);
  const rawBuildEvidence = typeof record.build_evidence === 'string'
    ? record.build_evidence
    : JSON.stringify(record.build_evidence || null);
  if (!sourceSha256 || !runtime || !runtimePolicy ||
      !/^[a-z0-9]+(?:-[a-z0-9]+)*@[0-9A-Za-z][0-9A-Za-z._:-]{0,79}$/.test(workflowVersion) ||
      !publishedSlug || buildEvidence.checks.length === 0 || !issueUrl || !prUrl ||
      !Number.isSafeInteger(prNumber) || prNumber < 1 || !branch || !headSha || !artifactHash) return null;
  return {
    phase: record.release_phase, sourceSha256, runtime, runtimePolicy, workflowVersion,
    publishedSlug, rawBuildEvidence, issueUrl, prUrl, prNumber, branch, headSha, artifactHash,
    slug: record.slug,
  };
}

async function resumeReviewedReleaseVerificationFailure(env, userId, submissionId, exactSlug = '') {
  const record = await getSubmissionApprovalState(env, userId, submissionId, exactSlug);
  if (!record) return { status: 'not_found' };
  const releaseShapedFailure = record.status === 'failed' &&
    record.failure_code === 'canary_or_internal_failed' &&
    ['pr_open', 'ci_passed'].includes(record.release_phase);
  if (!releaseShapedFailure) return { status: 'not_release_verification' };
  const snapshot = releaseVerificationResumeSnapshot(record, submissionId, exactSlug);
  if (!snapshot) return { status: 'not_retryable' };
  const now = new Date().toISOString();
  const resumedColumns = `id,name,slug,status,requested_runtime,selected_runtime,runtime_policy,
    runtime_compatibility,source_sha256,failure_code,workflow_version,published_slug,created_at,updated_at,
    approved_at,approved_by,approval_reason,deployed_at,build_evidence,release_phase,release_issue_url,
    release_pr_url,release_pr_number,release_branch,release_head_sha,release_merge_sha,release_artifact_hash,
    modal_app,modal_url,canary_evidence,promotion_evidence`;
  const evidenceValues = [
    snapshot.phase, snapshot.sourceSha256, snapshot.runtime, snapshot.runtimePolicy,
    snapshot.workflowVersion, snapshot.publishedSlug, snapshot.rawBuildEvidence,
    snapshot.issueUrl, snapshot.prUrl, snapshot.prNumber, snapshot.branch,
    snapshot.headSha, snapshot.artifactHash, snapshot.slug,
  ];
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-submission-retry-release-verification-v2',
      `UPDATE submissions
       SET status = 'ready_for_deploy', failure_code = NULL, updated_at = CURRENT_TIMESTAMP
       WHERE id = $1 AND user_id = $2 AND status = 'failed'
         AND failure_code = 'canary_or_internal_failed' AND release_phase = $3
         AND source_sha256 = $4 AND selected_runtime = $5 AND runtime_policy = $6
         AND workflow_version = $7 AND published_slug = $8 AND build_evidence = $9
         AND release_issue_url = $10 AND release_pr_url = $11 AND release_pr_number = $12
         AND release_branch = $13 AND release_head_sha = $14 AND release_artifact_hash = $15
         AND slug = $16
       RETURNING ${resumedColumns}`,
      [submissionId, userId, ...evidenceValues]
    ));
    return result.rowCount === 1 && result.rows[0]
      ? { status: 'retried', row: result.rows[0] }
      : { status: 'not_retryable' };
  }
  if (databaseKind(env) === 'd1') {
    const result = await env.BALANCE_DB.prepare(`UPDATE submissions
      SET status = 'ready_for_deploy', failure_code = NULL, updated_at = ?
      WHERE id = ? AND user_id = ? AND status = 'failed'
        AND failure_code = 'canary_or_internal_failed' AND release_phase = ?
        AND source_sha256 = ? AND selected_runtime = ? AND runtime_policy = ?
        AND workflow_version = ? AND published_slug = ? AND build_evidence = ?
        AND release_issue_url = ? AND release_pr_url = ? AND release_pr_number = ?
        AND release_branch = ? AND release_head_sha = ? AND release_artifact_hash = ?
        AND slug = ?`)
      .bind(now, submissionId, userId, ...evidenceValues).run();
    return result.meta && result.meta.changes
      ? { status: 'retried', row: await getSubmissionForOwner(env, userId, submissionId) }
      : { status: 'not_retryable' };
  }
  record.status = 'ready_for_deploy';
  record.failure_code = null;
  record.updated_at = now;
  return { status: 'retried', row: record };
}

async function retryReviewedGatedBuildFailure(env, userId, submissionId, requiredSlug = '') {
  const retryableFailureCodes = [...RETRYABLE_EXACT_MATCH_RELEASE_FAILURE_CODES];
  const exactSlug = requiredSlug ? safeSlug(requiredSlug) : '';
  if (requiredSlug && !exactSlug) return { status: 'not_found' };
  const releaseVerificationRetry = await resumeReviewedReleaseVerificationFailure(
    env, userId, submissionId, exactSlug
  );
  if (releaseVerificationRetry.status === 'retried' ||
      releaseVerificationRetry.status === 'not_retryable' ||
      releaseVerificationRetry.status === 'not_found') return releaseVerificationRetry;
  const now = new Date().toISOString();
  const transientAssignments = `failure_code = NULL, workflow_version = NULL, published_slug = NULL,
    deployed_at = NULL, build_evidence = NULL, release_phase = NULL, release_issue_url = NULL,
    release_pr_url = NULL, release_pr_number = NULL, release_branch = NULL, release_head_sha = NULL,
    release_merge_sha = NULL, release_artifact_hash = NULL, modal_app = NULL, modal_url = NULL,
    canary_evidence = NULL`;
  const returnedColumns = 'id,name,slug,status,requested_runtime,selected_runtime,runtime_policy,runtime_compatibility,source_sha256,failure_code,workflow_version,published_slug,created_at,updated_at,approved_at,approved_by,approval_reason,deployed_at,build_evidence';
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-submission-retry-v3',
      `UPDATE submissions
       SET status = 'queued', ${transientAssignments}, updated_at = CURRENT_TIMESTAMP
       WHERE id = $1 AND user_id = $2 AND ($3 = '' OR slug = $3)
         AND status = 'failed'
         AND failure_code IN ('build_or_deploy_failed', 'canary_or_internal_failed', 'profile_identity_mismatch')
         AND source_sha256 ~ '^[a-f0-9]{64}$'
         AND (
           (failure_code IN ('build_or_deploy_failed', 'canary_or_internal_failed', 'profile_identity_mismatch') AND selected_runtime IS NULL
             AND (runtime_policy IS NULL OR runtime_policy = ''))
           OR
           (selected_runtime IN ('worker-native', 'modal-hosted')
             AND runtime_policy IS NOT NULL AND runtime_policy <> '')
         )
       RETURNING ${returnedColumns}`,
      [submissionId, userId, exactSlug]
    ));
    const row = approvalSafeRow(result.rows[0]);
    if (row) return { status: 'retried', row };
    const existing = await getSubmissionApprovalState(env, userId, submissionId, exactSlug);
    return existing ? { status: 'not_retryable' } : { status: 'not_found' };
  }
  if (databaseKind(env) === 'd1') {
    const updated = await env.BALANCE_DB.prepare(`UPDATE submissions
      SET status = 'queued', ${transientAssignments}, updated_at = ?
      WHERE id = ? AND user_id = ? AND (? = '' OR slug = ?) AND status = 'failed'
        AND failure_code IN ('build_or_deploy_failed', 'canary_or_internal_failed', 'profile_identity_mismatch')
        AND length(source_sha256) = 64 AND source_sha256 NOT GLOB '*[^a-f0-9]*'
        AND (
          (failure_code IN ('build_or_deploy_failed', 'canary_or_internal_failed', 'profile_identity_mismatch') AND selected_runtime IS NULL
            AND (runtime_policy IS NULL OR runtime_policy = ''))
          OR
          (selected_runtime IN ('worker-native', 'modal-hosted')
            AND runtime_policy IS NOT NULL AND runtime_policy <> '')
        )`)
      .bind(now, submissionId, userId, exactSlug, exactSlug).run();
    if (updated.meta && updated.meta.changes) {
      return { status: 'retried', row: await getSubmissionForOwner(env, userId, submissionId) };
    }
    const existing = await getSubmissionApprovalState(env, userId, submissionId, exactSlug);
    return existing ? { status: 'not_retryable' } : { status: 'not_found' };
  }
  for (const record of mockSubmissions.values()) {
    if (record.id !== submissionId || (record.userId !== userId && record.user_id !== userId)) continue;
    if (exactSlug && record.slug !== exactSlug) return { status: 'not_found' };
    const preRuntimeCanary = retryableFailureCodes.includes(record.failure_code) &&
      !record.selected_runtime && !record.runtime_policy;
    const reviewedRuntimeFailure = !!safeRuntime(record.selected_runtime) && !!safeRuntimePolicy(record.runtime_policy);
    if (record.status !== 'failed' || !retryableFailureCodes.includes(record.failure_code) ||
        !safeSha256(record.source_sha256 || record.sourceSha256) ||
        (!preRuntimeCanary && !reviewedRuntimeFailure)) return { status: 'not_retryable' };
    record.status = 'queued';
    for (const field of ['failure_code', 'workflow_version', 'published_slug', 'deployed_at', 'build_evidence',
      'release_phase', 'release_issue_url', 'release_pr_url', 'release_pr_number', 'release_branch',
      'release_head_sha', 'release_merge_sha', 'release_artifact_hash', 'modal_app', 'modal_url', 'canary_evidence']) {
      record[field] = null;
    }
    record.updated_at = now;
    return { status: 'retried', row: record };
  }
  return { status: 'not_found' };
}

async function getSubmissionApprovalState(env, userId, submissionId, requiredSlug = '') {
  const exactSlug = requiredSlug ? safeSlug(requiredSlug) : '';
  if (requiredSlug && !exactSlug) return null;
  const columns = 'id,name,slug,status,requested_runtime,selected_runtime,runtime_policy,runtime_compatibility,source_sha256,failure_code,workflow_version,published_slug,created_at,updated_at,approved_at,approved_by,approval_reason,deployed_at,build_evidence,release_phase,release_issue_url,release_pr_url,release_pr_number,release_branch,release_head_sha,release_merge_sha,release_artifact_hash,modal_app,modal_url,canary_evidence,promotion_evidence';
  if (databaseKind(env) === 'neon') {
    const result = exactSlug
      ? await getNeonPool(env).query(prepared(
        'omo-submission-approval-state-by-slug-v1',
        `SELECT ${columns} FROM submissions WHERE id = $1 AND user_id = $2 AND slug = $3`,
        [submissionId, userId, exactSlug]
      ))
      : await getNeonPool(env).query(prepared(
        'omo-submission-approval-state-v1',
        `SELECT ${columns} FROM submissions WHERE id = $1 AND user_id = $2`,
        [submissionId, userId]
      ));
    return result.rows[0] || null;
  }
  if (databaseKind(env) === 'd1') {
    return exactSlug
      ? env.BALANCE_DB.prepare(`SELECT ${columns} FROM submissions WHERE id = ? AND user_id = ? AND slug = ?`).bind(submissionId, userId, exactSlug).first()
      : env.BALANCE_DB.prepare(`SELECT ${columns} FROM submissions WHERE id = ? AND user_id = ?`).bind(submissionId, userId).first();
  }
  const row = await getSubmissionForOwner(env, userId, submissionId);
  return row && (!exactSlug || row.slug === exactSlug) ? row : null;
}

async function listSubmissions(env, userId, limit, cursor = null) {
  const columns = 'id,name,slug,status,requested_runtime,selected_runtime,runtime_policy,runtime_compatibility,source_sha256,failure_code,workflow_version,published_slug,created_at,updated_at,approved_at,approved_by,approval_reason,deployed_at,build_evidence,release_phase,release_issue_url,release_pr_url,release_pr_number,release_branch,release_head_sha,release_merge_sha,release_artifact_hash,modal_app,modal_url,canary_evidence,promotion_evidence';
  if (databaseKind(env) === 'neon') {
    const result = cursor
      ? await getNeonPool(env).query(prepared(
        'omo-submissions-list-cursor-v1',
        `SELECT ${columns} FROM submissions
         WHERE user_id = $1 AND (created_at < $2 OR (created_at = $2 AND id < $3))
         ORDER BY created_at DESC, id DESC LIMIT $4`,
        [userId, cursor.created_at, cursor.id, limit]
      ))
      : await getNeonPool(env).query(prepared(
        'omo-submissions-list-v1',
        `SELECT ${columns} FROM submissions WHERE user_id = $1 ORDER BY created_at DESC, id DESC LIMIT $2`,
        [userId, limit]
      ));
    return result.rows;
  }
  if (databaseKind(env) === 'd1') {
    const statement = cursor
      ? env.BALANCE_DB
        .prepare(`SELECT ${columns} FROM submissions
                  WHERE user_id = ? AND (created_at < ? OR (created_at = ? AND id < ?))
                  ORDER BY created_at DESC, id DESC LIMIT ?`)
        .bind(userId, cursor.created_at, cursor.created_at, cursor.id, limit)
      : env.BALANCE_DB
        .prepare(`SELECT ${columns} FROM submissions WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?`)
        .bind(userId, limit);
    const result = await statement.all();
    return (result && result.results) || [];
  }
  return Array.from(mockSubmissions.values())
    .filter((record) => record.userId === userId || record.user_id === userId)
    .filter((record) => !cursor || String(record.created_at || '') < cursor.created_at ||
      (String(record.created_at || '') === cursor.created_at && String(record.id || '') < cursor.id))
    .sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')) || String(b.id || '').localeCompare(String(a.id || '')))
    .slice(0, limit);
}

async function getSubmissionForOwner(env, userId, submissionId) {
  const columns = 'id,name,slug,status,requested_runtime,selected_runtime,runtime_policy,runtime_compatibility,source_sha256,failure_code,workflow_version,published_slug,created_at,updated_at,approved_at,approved_by,approval_reason,deployed_at,build_evidence,release_phase,release_issue_url,release_pr_url,release_pr_number,release_branch,release_head_sha,release_merge_sha,release_artifact_hash,modal_app,modal_url,canary_evidence,promotion_evidence';
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-submission-detail-v1',
      `SELECT ${columns} FROM submissions WHERE id = $1 AND user_id = $2`,
      [submissionId, userId]
    ));
    return result.rows[0] || null;
  }
  if (databaseKind(env) === 'd1') {
    return env.BALANCE_DB
      .prepare(`SELECT ${columns} FROM submissions WHERE id = ? AND user_id = ?`)
      .bind(submissionId, userId).first();
  }
  for (const record of mockSubmissions.values()) {
    if (record.id === submissionId && (record.userId === userId || record.user_id === userId)) return record;
  }
  return null;
}

function balanceSecret(env) {
  return env.BALANCE_KEY_SECRET || env.LLM_API_KEY || 'omo-dev-secret';
}

function signupGrantCents(env) {
  const override = Number(env.SIGNUP_GRANT_USD);
  const amountUsd = isFinite(override) && override > 0 ? override : grantSignupCredits().amountUsd;
  return Math.round(amountUsd * 100);
}

async function authenticateAccount(request, env, allowApiKey, allowStagingCanary = false) {
  const authorization = String(request.headers.get('authorization') || '').trim();
  const bearer = /^Bearer\s+(.+)$/i.exec(authorization);
  const explicitApiKey = String(request.headers.get('x-api-key') || '').trim();
  const credential = explicitApiKey || (bearer && bearer[1]) || '';

  const productionCanaryKey = String(env.PRODUCTION_CANARY_API_KEY || '').trim();
  if (
    allowApiKey && allowStagingCanary && String(env.ENVIRONMENT || '') === 'production'
    && /^omo_[0-9a-f]{32}$/.test(productionCanaryKey)
    && timingSafeEqual(credential, productionCanaryKey)
  ) {
    return { ok: true, userId: 'user_prod_label_normalizer_canary_v1', method: 'production_canary' };
  }

  const stagingCanaryKey = String(env.ISSUE141_CANARY_API_KEY || '').trim();
  if (
    allowApiKey && allowStagingCanary && String(env.ENVIRONMENT || '') === 'staging'
    && stagingCanaryKey && timingSafeEqual(credential, stagingCanaryKey)
  ) {
    return { ok: true, userId: 'user_issue141_canary', method: 'staging_canary' };
  }

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

async function userIdForHashedApiKey(env, apiKey) {
  if (!/^omo_[0-9a-f]{32}$/.test(apiKey)) return '';
  const keyHash = await sha256Hex(apiKey);
  if (databaseKind(env) === 'neon') {
    const result = await getNeonPool(env).query(prepared(
      'omo-api-key-owner-v1', 'SELECT user_id FROM api_keys WHERE key_hash = $1', [keyHash]
    ));
    return result.rows[0] && validUserId(result.rows[0].user_id) ? result.rows[0].user_id : '';
  }
  if (databaseKind(env) === 'd1') {
    const row = await env.BALANCE_DB.prepare('SELECT user_id FROM api_keys WHERE key_hash = ?').bind(keyHash).first();
    return row && validUserId(row.user_id) ? row.user_id : '';
  }
  return mockApiKeys.get(keyHash) || '';
}

async function ensureProductionCanaryIdentity(env, apiKey) {
  const userId = 'user_prod_label_normalizer_canary_v1';
  const account = await getUserRecord(env, userId);
  await ensureApiKeyRecord(env, userId, apiKey);
  return { created: account.created };
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
      await client.release();
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
    } finally { await client.release(); }
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
  const hosted = row.slug === DEMELLO_SLUG && String(env.DEMELLO_LEGACY_EXECUTOR || '') === '1'
    ? null : HOSTED_MODAL_SKILLS.get(row.slug);
  if (hosted) {
    return json(hostedModalPublicRunning(row, hosted, { idempotent_replay: true }), 202, cors());
  }
  if (row.slug === DEMELLO_SLUG) {
    const progress = await getRunProgress(env, row.run_id);
    return json(demelloPublicRunning(row, progress, { idempotent_replay: true }), 202, cors());
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
    let staleCutoff = cutoff;
    if (HOSTED_WORKER_SKILLS.has(row.slug)) {
      const hostedWorker = HOSTED_WORKER_SKILLS.get(row.slug);
      const providerTimeoutSeconds = boundedInt(
        hostedWorker && hostedWorker.executor && hostedWorker.executor.timeout_seconds,
        1,
        120,
        120
      );
      const workerTtlSeconds = Math.max(ttlSeconds, providerTimeoutSeconds + 30);
      staleCutoff = new Date(Date.now() - workerTtlSeconds * 1000).toISOString();
      if (row.updated_at >= staleCutoff) continue;
    } else if (row.slug === DEMELLO_SLUG || HOSTED_MODAL_SKILLS.has(row.slug)) {
      staleCutoff = demelloCutoff;
      if (row.updated_at >= staleCutoff) continue;
    }
    const response = { error: 'stale_reservation_refunded', run_id: row.run_id, state: 'refunded' };
    const claimed = await claimStaleRunRefund(env, row.run_id, staleCutoff, response);
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
    } finally { await client.release(); }
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
    } finally { await client.release(); }
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
    } finally { await client.release(); }
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
