// Omo Marketplace MCP server — dependency-light, Workers-compatible JSON-RPC.
//
// Mount `handleMcpRequest(request, env)` at /mcp in worker.js. The server uses
// the same pure credit and cost helpers as the REST worker, reads the public
// storefront catalogue when an Assets binding/origin is available, and keeps a
// compact server-owned snapshot for cold/offline operation.

import { Pool } from '@neondatabase/serverless';
import {
  MIN_TOPUP_USD,
  apiKeyFor,
  debitForRun,
  grantSignupCredits,
  topupAmounts,
} from './balance.mjs';
import { llmWorkflow, runPrice as calculateRunPrice } from './cost-model.mjs';

const SERVER_NAME = 'omo-marketplace';
const SERVER_VERSION = '1.0.0';
const LATEST_PROTOCOL = '2025-06-18';
const SUPPORTED_PROTOCOLS = new Set([LATEST_PROTOCOL, '2025-03-26']);
const TOPUP_URL = 'https://omo.space/dashboard.html?topup=needed';
const MAX_INPUT_CHARS = 12_000;
const DEMELLO_SLUG = 'japanese-style-story-video';
const fetchedCatalogues = new Map();

// Newer live helpers share this intentionally simple interface.
const STANDARD_INPUTS = [
  'brief: product or topic',
  'style: creative direction hint',
  'length: video length',
];
const STANDARD_OUTPUTS = [
  'output — key results from the run',
  'summary — plain-language recap',
];
const GENERIC_SYSTEM = 'You are a specialist AI workflow operator. Use only the supplied facts. Return EXACTLY this JSON shape: {"output":["key result 1","key result 2","key result 3"],"summary":"one plain sentence of what was produced"}. HARD RULES: output is a flat array of STRINGS, never invent facts, output ONLY the JSON object.';

// The source of truth remains site/catalog.js. This
// snapshot mirrors the runtime-safe fields so MCP still works if static asset
// fetching is unavailable (including the zero-network self-test).
const FALLBACK_ROWS = [
  [DEMELLO_SLUG, 'Japanese Style Story Video', 'content', 'Turn spoken audio into a vertical Japanese sumi-e drawing animation.', 29, 0.10, 'Transcribe audio, direct the story, generate ink-wash frames, assemble a 1080×1920 MP4, and deliver the video.', ['audio_ref: sample-demello-10s (required by the hosted milestone)', 'style_hint: sumi-e', 'duration_seconds: 5–20'], ['video_url — delivered vertical MP4', 'contact_sheet_url — generated frame contact sheet'], GENERIC_SYSTEM, 500, [['api', 'modal_demello_run', 1]]],
  ['arcads-node-ugc-builder', 'Arcads Node UGC Builder', 'content', 'Turn a product brief into a batch of consistent UGC-style videos without a shoot.', 49, 1.40, 'Turn a product brief into scene images, connect the start and end frames in Arcads, and render a complete UGC-style video.', ['brief: product + hook + audience', 'scenes: how many scene frames', 'style: product style hint'], ['scene_prompts — per-frame generation prompts', 'video — rendered UGC-style ad'], 'You turn a product brief into scene prompts for UGC video generation. Return EXACTLY this JSON shape: {"scene_prompts":["prompt 1","prompt 2","prompt 3"],"hook":"first 2 seconds","cta":"one call to action"} HARD RULES: scene_prompts is a flat array of STRINGS, never invent claims, output ONLY the JSON object.', 400, [['api', 'replicate_run', 3], ['api', 'modal_gpu_30s', 2]]],
  ['product-link-to-meta-ugc-ad', 'Product Link → Meta UGC Ad', 'leads', 'Paste a product URL and get a ready-to-test UGC ad for Meta.', 49, 0.60, 'Paste the product link, generate a UGC video prompt, make the video, and prepare it for a Meta ad.', ['product_url: the product page link', 'claim: the main selling point'], ['ad_prompt — the UGC video generation prompt', 'video — avatar-rendered UGC ad', 'script — what the ad says'], 'You summarize an ecommerce product page for ad creation. Return EXACTLY this JSON shape: {"product":"what it is","claims":["supported claims only"],"audience":"who buys it"}. Never invent claims. Output JSON only.', 300, [['llm', 'prompt', 1], ['api', 'heygen_avatar_render', 1], ['api', 'heygen_voiceover', 1]]],
  ['one-photo-ecom-creative-factory', 'One-Photo Creative Factory', 'save', 'Make a full set of ecommerce photos, marketing creatives, and product videos from one source photo.', 39, 1.10, 'Create the full asset pack from one product photo: image variants, marketing creatives, and short product videos.', ['photo_desc: describe your product photo', 'usages: PDP, paid social, organic'], ['variants — angle/background/usage matrix', 'creatives — marketing-ready images'], 'You turn a product photo description into a creative variant matrix. Return JSON with variants as a flat array of angle, background, and usage objects. Output JSON only.', 400, [['api', 'openai_image', 4], ['api', 'replicate_run', 1]]],
  ['shopify-pics-to-description-bulk', 'Shopify Pics → Descriptions (Bulk)', 'ops', 'Generate SEO titles, descriptions, and meta tags for 1 or 100+ Shopify products from images.', 49, 0.30, 'Upload product images to get SEO descriptions, titles, and meta tags, then update one listing or a whole catalogue.', ['image_descs: describe your product images', 'store: Shopify store name'], ['copy — title, description, meta title, meta description per product', 'bulk_plan — update plan for 1 or 100+ products'], 'You generate SEO product listings from image descriptions. Return JSON with title, description, meta_title, and meta_description as strings. Never invent claims. Output JSON only.', 500, [['api', 'e2b_sandbox', 1]]],
  ['gpt-image-seedance-product-ad', 'Cinematic Product Ad (GPT Image + Seedance)', 'content', 'Turn a product concept into a polished cinematic ad with AI product shots and motion.', 49, 1.10, 'Create bold product shots, then animate them into cinematic motion and smooth transitions.', ['product: what the ad sells', 'mood: cinematic style hint'], ['shotlist — per-shot angle/props/motion notes', 'video — animated cinematic ad cut'], 'You plan cinematic product ad shots. Return JSON with shotlist and transitions as flat string arrays and style as a string. Output JSON only.', 400, [['api', 'openai_image', 3], ['api', 'modal_gpu_30s', 2]]],
  ['consistent-character-ugc', 'Consistent Character UGC System', 'content', 'Keep one AI character consistent across products and make realistic UGC ads in three steps.', 49, 0.90, 'Create a consistent UGC character, integrate the product, refine the frames, and animate them into a video ad.', ['character: character description (look, voice, vibe)', 'product: what the ad sells', 'mood: ad mood hint'], ['character_sheet — name, look, voice, brand-fit', 'frames — product-integrated scene frames', 'video — animated AI UGC ad'], 'You build a character sheet and product talking points for AI UGC ads. Return JSON only and never invent claims.', 400, [['api', 'openai_image', 3], ['api', 'replicate_run', 1]]],
  ['realistic-ugc-character-4step', 'Realistic AI UGC Character (4-Step)', 'content', 'Make realistic talking-character UGC for products in four repeatable steps.', 49, 0.90, 'Make realistic AI UGC videos with a talking character without filming a new host each time.', ['product: what the character talks about', 'character: character description', 'tone: casual · hype · informative'], ['script — talking-character script', 'frames — consistent character frames', 'video — talking-character UGC video'], 'You write natural talking-character UGC scripts. Return JSON with hook, lines, and cta. Never invent claims. Output JSON only.', 400, [['api', 'openai_image', 3], ['api', 'replicate_run', 1]]],
  ['prompt-to-ugc-ad-maxfusion-seedance-2-0', 'Prompt-to-UGC Ad (Maxfusion + Seedance 2.0)', 'content', 'Turn one text prompt into a realistic UGC video ad in under five minutes.', 29, 0.60, 'Turn one text prompt into a realistic UGC video ad using Maxfusion and Seedance 2.0.'],
  ['cinematic-ai-ugc-scene-builder', 'Cinematic AI UGC Scene Builder', 'content', 'Build cinematic UGC scenes with AI — no cameras, actors, or sets.', 29, 0.60, 'Turn a product or promo script into polished cinematic UGC scenes.'],
  ['ai-ugc-ad-prompt-guide', 'AI UGC Ad Prompt + Guide', 'content', 'Get a ready-to-use prompt and guide for making UGC-style ads with AI.', 29, 0.60, 'Turn a product brief into an ad concept, script, and production prompt.'],
  ['product-image-cinematic-ad-seedance-2-0', 'Product Image → Cinematic Ad (Seedance 2.0)', 'content', 'Turn one product image and a short prompt into a 15-second cinematic ad.', 49, 1.00, 'Make a video ad from a product shot without cameras or a production setup.'],
  ['claude-seo-skill-replaces-2k-mo-agency', 'Claude SEO Skill (replaces $2K/mo agency)', 'ops', 'Run a practical SEO workflow in Claude in about three minutes.', 29, 0.10, 'Review a site, find gaps, and turn them into practical SEO improvements.'],
  ['shopify-agentic-storefronts-ai-seo-playbook', 'Shopify Agentic Storefronts + AI SEO Playbook', 'ops', 'Make your Shopify products easier for AI assistants to discover and recommend.', 29, 0.30, 'Prepare a Shopify store for discovery and recommendation in AI chat.'],
  ['shopify-ai-stack-rebuy-klaviyo-ai-tidio', 'Shopify AI Stack (Rebuy + Klaviyo AI + Tidio)', 'ops', 'Plan a three-tool AI stack for Shopify: upsells, email, and abandoned-cart recovery.', 49, 1.05, 'Plan a Shopify automation stack with Rebuy, Klaviyo AI, and Tidio.'],
  ['shopify-agentic-plan-sellers-setup', 'Shopify Agentic Plan Sellers Setup', 'ops', 'Set up Shopify\'s Agentic Plan so buyers can shop inside AI chat.', 29, 0.30, 'Set up products for discovery and checkout inside AI chat.'],
  ['ai-brand-commercial-production-seedance-2-0-k', 'AI Brand Commercial Production (Seedance 2.0 + Kling 3)', 'content', 'Plan a full AI-made brand commercial from concept to final cut.', 29, 0.60, 'Create a storyboard, cinematic shots, and motion plan for an AI-made brand campaign.'],
  ['ai-ugc-tutorial-german-comment-to-get', 'AI UGC Tutorial (German, comment-to-get)', 'content', 'Get a German-language guide to making AI UGC videos.', 29, 0.10, 'Create a practical AI UGC starting guide for German-speaking marketers.'],
  ['ai-ugc-creator-guide-fully-ai-generated-ads', 'AI UGC Creator Guide (fully AI-generated ads)', 'content', 'Plan AI-generated UGC ads with more volume, variety, and speed.', 29, 0.60, 'Turn a product brief into a repeatable AI ad-production plan.'],
  ['batch-content-repurposing-system-transcripts-', 'Batch Content Repurposing System (transcripts → captions)', 'ops', 'Turn batches of recorded videos into transcripts, captions, and scheduled posts.', 39, 0.75, 'Turn a batch of recorded videos into platform-specific captions and a scheduling plan.'],
  ['kling-ai-higgsfield-viral-video-workflow', 'Kling AI + Higgsfield Viral Video Workflow', 'content', 'Turn a simple concept into scroll-stopping cinematic video clips.', 29, 0.60, 'Create short-form video ideas and production prompts for ecommerce ads.'],
  ['ai-readable-product-page-optimization', 'AI-Readable Product Page Optimization', 'ops', 'Structure product pages so AI assistants can understand and recommend them.', 39, 0.90, 'Sharpen product information and identify missing details that block AI discovery.'],
];

function fallbackCatalogue() {
  return FALLBACK_ROWS.map((row) => {
    const [slug, name, category, promise, priceOwn, runPrice, desc] = row;
    const inputs = row[7] || STANDARD_INPUTS;
    const outputs = row[8] || STANDARD_OUTPUTS;
    const system = row[9] || GENERIC_SYSTEM;
    const maxOutput = row[10] || 500;
    const extras = row[11] || [];
    const steps = [{ type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: maxOutput, system }];
    for (const [type, label, qty] of extras) {
      if (type === 'llm') steps.push({ type, role: label, model: 'deepseek-v4-flash', max_output: 500, system: GENERIC_SYSTEM });
      else steps.push({ type, api: label, qty });
    }
    return { slug, name, category, promise, priceOwn, runPrice, desc, inputs, outputs, workflow: { steps } };
  });
}

function withPinnedRuntimeHelpers(helpers) {
  const output = helpers.slice();
  if (!output.some((helper) => helper.slug === DEMELLO_SLUG)) {
    const pinned = fallbackCatalogue().find((helper) => helper.slug === DEMELLO_SLUG);
    if (pinned) output.push(pinned);
  }
  return output;
}

const TOOLS = [
  {
    name: 'omo_search_helpers',
    description: 'Search Omo\'s helper catalogue by need, task, category, or niche.',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'What you want help with.' },
        category_or_niche: { type: 'string', description: 'Optional category or niche, such as content, ops, Shopify, or UGC.' },
      },
      required: ['query'],
      additionalProperties: false,
    },
  },
  {
    name: 'omo_get_helper',
    description: 'Get full details, inputs, outputs, pricing, and workflow summary for one Omo helper.',
    inputSchema: {
      type: 'object',
      properties: { slug: { type: 'string', description: 'The exact helper slug.' } },
      required: ['slug'],
      additionalProperties: false,
    },
  },
  {
    name: 'omo_run_helper',
    description: 'Run an Omo helper. With an API key, the listed per-run price is debited from Omo credits; without one, a mock/demo result is returned when available.',
    inputSchema: {
      type: 'object',
      properties: {
        slug: { type: 'string', description: 'The exact helper slug.' },
        inputs: { type: 'object', description: 'Input names and values described by omo_get_helper.', additionalProperties: true },
        api_key: { type: 'string', description: 'Your secret omo_ API key from omo.space/api.html.' },
        idempotency_key: { type: 'string', description: 'Required for the hosted video workflow: an 8–128 character retry key. Reuse it only for the same inputs.' },
      },
      required: ['slug', 'inputs'],
      additionalProperties: false,
    },
  },
  {
    name: 'omo_get_run_progress',
    description: 'Get the current phase and monotonic progress percentage for an Omo run.',
    inputSchema: {
      type: 'object',
      properties: {
        run_id: { type: 'string', description: 'The run_id returned by omo_run_helper.' },
        api_key: { type: 'string', description: 'The owning omo_ API key.' },
      },
      required: ['run_id', 'api_key'],
      additionalProperties: false,
    },
  },
  {
    name: 'omo_get_run_result',
    description: 'Get a completed run result, including its video URL when delivery is ready.',
    inputSchema: {
      type: 'object',
      properties: {
        run_id: { type: 'string', description: 'The run_id returned by omo_run_helper.' },
        api_key: { type: 'string', description: 'The owning omo_ API key.' },
      },
      required: ['run_id', 'api_key'],
      additionalProperties: false,
    },
  },
  {
    name: 'omo_get_balance',
    description: 'Get the owning Omo account credit balance and recent run usage. Possession of its secret omo_ API key is required.',
    inputSchema: {
      type: 'object',
      properties: { api_key: { type: 'string', description: 'The owning secret omo_ API key.' } },
      required: ['api_key'],
      additionalProperties: false,
    },
  },
  {
    name: 'omo_topup_options',
    description: 'Show supported credit top-up amounts and the secure Stripe dashboard link. MCP never takes payments directly.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
];

class RpcFault extends Error {
  constructor(code, message, data) {
    super(message);
    this.code = code;
    this.data = data;
  }
}

function requireObject(value, label = 'params') {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new RpcFault(-32602, `${label} must be an object.`);
  }
  return value;
}

function requireString(value, label) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new RpcFault(-32602, `${label} must be a non-empty string.`);
  }
  return value.trim();
}

function safeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function publicWorkflow(workflow) {
  const steps = workflow && Array.isArray(workflow.steps) ? workflow.steps : [];
  return {
    summary: steps.length
      ? steps.map((step, index) => step.type === 'api'
        ? `${index + 1}. ${step.api || 'external API'}${step.qty > 1 ? ` ×${step.qty}` : ''}`
        : `${index + 1}. AI ${step.role || 'generation'} step`).join(' → ')
      : 'One AI generation step.',
    steps: steps.map((step) => step.type === 'api'
      ? { type: 'api', api: step.api || 'external', qty: safeNumber(step.qty, 1) }
      : {
          type: 'llm',
          role: step.role || 'main',
          model: step.model || 'deepseek-v4-flash',
          max_output: safeNumber(step.max_output, 500),
        }),
  };
}

function normalizeHelper(helper) {
  if (!helper || typeof helper !== 'object' || !helper.slug || !helper.name ||
      helper.chargeable === false || helper.active === false || helper.status === 'coming-soon') return null;
  const workflow = helper.workflow && Array.isArray(helper.workflow.steps)
    ? helper.workflow
    : llmWorkflow(GENERIC_SYSTEM, 500);
  const computedPrice = calculateRunPrice(workflow);
  return {
    slug: String(helper.slug),
    name: String(helper.name),
    category: String(helper.category || 'general'),
    promise: String(helper.promise || helper.desc || ''),
    priceOwn: safeNumber(helper.priceOwn, 0),
    runPrice: safeNumber(helper.runPrice, computedPrice),
    desc: String(helper.desc || helper.promise || ''),
    inputs: Array.isArray(helper.inputs) ? helper.inputs.map(String) : STANDARD_INPUTS.slice(),
    outputs: Array.isArray(helper.outputs) ? helper.outputs.map(String) : STANDARD_OUTPUTS.slice(),
    workflow,
  };
}

// Small parser for the catalogue's data-only JavaScript literals. Dynamic
// eval is intentionally avoided because Workers disallow string codegen.
class LiteralReader {
  constructor(source, start) {
    this.source = source;
    this.index = start;
  }

  skip() {
    while (this.index < this.source.length) {
      if (/\s/.test(this.source[this.index])) { this.index += 1; continue; }
      if (this.source.startsWith('//', this.index)) {
        const end = this.source.indexOf('\n', this.index + 2);
        this.index = end < 0 ? this.source.length : end + 1;
        continue;
      }
      if (this.source.startsWith('/*', this.index)) {
        const end = this.source.indexOf('*/', this.index + 2);
        this.index = end < 0 ? this.source.length : end + 2;
        continue;
      }
      break;
    }
  }

  value() {
    this.skip();
    const char = this.source[this.index];
    if (char === '[') return this.array();
    if (char === '{') return this.object();
    if (char === '"' || char === "'") return this.string();
    if (char === '-' || /[0-9]/.test(char || '')) return this.number();
    const word = this.identifier();
    if (word === 'true') return true;
    if (word === 'false') return false;
    if (word === 'null') return null;
    if (word === 'undefined') return undefined;
    throw new Error(`Unsupported catalogue literal "${word}" at ${this.index}.`);
  }

  array() {
    const output = [];
    this.index += 1;
    while (this.index < this.source.length) {
      this.skip();
      if (this.source[this.index] === ']') { this.index += 1; return output; }
      output.push(this.value());
      this.skip();
      if (this.source[this.index] === ',') { this.index += 1; continue; }
      if (this.source[this.index] !== ']') throw new Error(`Expected , or ] at ${this.index}.`);
    }
    throw new Error('Unterminated catalogue array.');
  }

  object() {
    const output = {};
    this.index += 1;
    while (this.index < this.source.length) {
      this.skip();
      if (this.source[this.index] === '}') { this.index += 1; return output; }
      const key = this.source[this.index] === '"' || this.source[this.index] === "'"
        ? this.string()
        : this.identifier();
      this.skip();
      if (this.source[this.index] !== ':') throw new Error(`Expected : at ${this.index}.`);
      this.index += 1;
      output[key] = this.value();
      this.skip();
      if (this.source[this.index] === ',') { this.index += 1; continue; }
      if (this.source[this.index] !== '}') throw new Error(`Expected , or } at ${this.index}.`);
    }
    throw new Error('Unterminated catalogue object.');
  }

  string() {
    const quote = this.source[this.index++];
    let output = '';
    while (this.index < this.source.length) {
      const char = this.source[this.index++];
      if (char === quote) return output;
      if (char !== '\\') { output += char; continue; }
      const escaped = this.source[this.index++];
      const common = { n: '\n', r: '\r', t: '\t', b: '\b', f: '\f', v: '\v', '0': '\0' };
      if (Object.prototype.hasOwnProperty.call(common, escaped)) output += common[escaped];
      else if (escaped === 'x') {
        output += String.fromCharCode(parseInt(this.source.slice(this.index, this.index + 2), 16));
        this.index += 2;
      } else if (escaped === 'u') {
        if (this.source[this.index] === '{') {
          const end = this.source.indexOf('}', this.index + 1);
          output += String.fromCodePoint(parseInt(this.source.slice(this.index + 1, end), 16));
          this.index = end + 1;
        } else {
          output += String.fromCharCode(parseInt(this.source.slice(this.index, this.index + 4), 16));
          this.index += 4;
        }
      } else if (escaped !== '\n' && escaped !== '\r') output += escaped;
    }
    throw new Error('Unterminated catalogue string.');
  }

  number() {
    const match = this.source.slice(this.index).match(/^-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?/i);
    if (!match) throw new Error(`Invalid number at ${this.index}.`);
    this.index += match[0].length;
    return Number(match[0]);
  }

  identifier() {
    this.skip();
    const match = this.source.slice(this.index).match(/^[A-Za-z_$][\w$-]*/);
    if (!match) throw new Error(`Expected identifier at ${this.index}.`);
    this.index += match[0].length;
    return match[0];
  }
}

function parseCatalogueSource(source) {
  const text = String(source || '');
  const assignment = text.search(/window\.OMO_CATALOG\s*=/);
  const start = assignment < 0 ? -1 : text.indexOf('[', assignment);
  if (start < 0) throw new Error('Catalogue assignment was not found.');
  const value = new LiteralReader(text, start).value();
  if (!Array.isArray(value)) throw new Error('Catalogue value was not an array.');
  return value;
}

async function fetchCatalogueSource(url, env) {
  const request = new Request(url, { headers: { Accept: 'application/javascript, text/javascript;q=0.9' } });
  const response = env && env.ASSETS && typeof env.ASSETS.fetch === 'function'
    ? await env.ASSETS.fetch(request)
    : await fetch(request);
  if (!response.ok) throw new Error(`Catalogue fetch failed (${response.status}).`);
  return response.text();
}

async function loadCatalogue(request, env = {}) {
  if (Array.isArray(env.MCP_CATALOG)) {
    const supplied = env.MCP_CATALOG.map(normalizeHelper).filter(Boolean);
    return withPinnedRuntimeHelpers(supplied.length ? supplied : fallbackCatalogue());
  }

  if (Array.isArray(env.MCP_CATALOG_SOURCES)) {
    const supplied = env.MCP_CATALOG_SOURCES.flatMap(parseCatalogueSource).map(normalizeHelper).filter(Boolean);
    return withPinnedRuntimeHelpers(supplied.length ? supplied : fallbackCatalogue());
  }

  const origin = String(env.OMO_SITE_ORIGIN || new URL(request.url).origin).replace(/\/+$/, '');
  if (!fetchedCatalogues.has(origin)) {
    fetchedCatalogues.set(origin, (async () => {
      try {
        const source = await fetchCatalogueSource(`${origin}/catalog.js`, env);
        const helpers = parseCatalogueSource(source).map(normalizeHelper).filter(Boolean);
        return withPinnedRuntimeHelpers(helpers.length ? helpers : fallbackCatalogue());
      } catch {
        return withPinnedRuntimeHelpers(fallbackCatalogue());
      }
    })());
  }
  return fetchedCatalogues.get(origin);
}

function searchHelpers(catalogue, query, niche) {
  const words = `${query} ${niche || ''}`.toLowerCase().split(/\s+/).filter(Boolean);
  const nicheText = String(niche || '').toLowerCase().trim();
  return catalogue
    .map((helper) => {
      const haystack = [helper.name, helper.slug, helper.category, helper.promise, helper.desc, ...helper.inputs, ...helper.outputs].join(' ').toLowerCase();
      let score = words.reduce((total, word) => total + (haystack.includes(word) ? 2 : 0), 0);
      if (nicheText && helper.category.toLowerCase() === nicheText) score += 5;
      if (helper.name.toLowerCase().includes(String(query).toLowerCase())) score += 4;
      return { helper, score };
    })
    .filter((entry) => entry.score > 0)
    .sort((left, right) => right.score - left.score || left.helper.name.localeCompare(right.helper.name))
    .slice(0, 20)
    .map(({ helper }) => ({
      name: helper.name,
      slug: helper.slug,
      promise: helper.promise,
      priceOwn: helper.priceOwn,
      runPrice: helper.runPrice,
    }));
}

function getHelper(catalogue, slug) {
  return catalogue.find((helper) => helper.slug === slug) || null;
}

let neonPool = null;
let neonPoolUrl = '';
const mockUsers = new Map();
const mockRuns = new Map();
const mockLedger = new Map();

function databaseKind(env) {
  if (env && String(env.NEON_DATABASE_URL || '').trim()) return 'neon';
  if (env && env.BALANCE_DB) return 'd1';
  return 'mock';
}

function getNeonPool(env) {
  const url = String(env.NEON_DATABASE_URL || '').trim();
  if (!neonPool || neonPoolUrl !== url) {
    neonPool = new Pool({
      connectionString: url,
      max: 4,
      idleTimeoutMillis: 30_000,
      connectionTimeoutMillis: 5_000,
      allowExitOnIdle: true,
    });
    neonPoolUrl = url;
  }
  return neonPool;
}

function prepared(name, text, values) {
  return { name, text, values };
}

function signupGrantCents(env) {
  const override = Number(env && env.SIGNUP_GRANT_USD);
  const usd = Number.isFinite(override) && override > 0 ? override : grantSignupCredits().amountUsd;
  return Math.round(usd * 100);
}

function balanceSecret(env) {
  return (env && (env.BALANCE_KEY_SECRET || env.LLM_API_KEY)) || 'omo-dev-secret';
}

function isApiKey(identity) {
  return /^omo_[0-9a-f]{32}$/.test(identity);
}

async function sha256Hex(value) {
  const bytes = new TextEncoder().encode(String(value));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

async function insertD1Ledger(env, values) {
  try {
    await env.BALANCE_DB
      .prepare('INSERT OR IGNORE INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)')
      .bind(...values).run();
  } catch { /* legacy D1 schemas continue to work without the audit row */ }
}

async function getAccount(env, identity, createUser = true) {
  const kind = databaseKind(env);
  const keyLookup = isApiKey(identity);

  if (kind === 'neon') {
    const pool = getNeonPool(env);
    if (keyLookup) {
      const keyHash = await sha256Hex(identity);
      const result = await pool.query(prepared('omo-mcp-user-key-v2', 'SELECT u.user_id, u.balance_cents, u.created_at FROM api_keys k JOIN users u ON u.user_id = k.user_id WHERE k.key_hash = $1 LIMIT 1', [keyHash]));
      return result.rows[0] || null;
    }
    let selected = await pool.query(prepared('omo-mcp-user-id-v1', 'SELECT user_id, balance_cents, api_key, created_at FROM users WHERE user_id = $1', [identity]));
    if (selected.rows[0] || !createUser) return selected.rows[0] || null;
    const now = new Date().toISOString();
    const key = apiKeyFor(identity, balanceSecret(env));
    const grantCents = signupGrantCents(env);
    const inserted = await pool.query(prepared('omo-mcp-user-create-v1', 'INSERT INTO users (user_id, balance_cents, api_key, created_at) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO NOTHING RETURNING user_id', [identity, grantCents, key, now]));
    if (inserted.rows[0]) {
      await pool.query(prepared('omo-mcp-signup-ledger-v1', 'INSERT INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT (event_id) DO NOTHING', [`signup:${identity}`, identity, 'signup_grant', grantCents, grantCents, identity, now]));
    }
    selected = await pool.query(prepared('omo-mcp-user-id-v1', 'SELECT user_id, balance_cents, api_key, created_at FROM users WHERE user_id = $1', [identity]));
    return selected.rows[0] || null;
  }

  if (kind === 'd1') {
    if (keyLookup) {
      const keyHash = await sha256Hex(identity);
      return env.BALANCE_DB.prepare('SELECT u.user_id, u.balance_cents, u.created_at FROM api_keys k JOIN users u ON u.user_id = k.user_id WHERE k.key_hash = ? LIMIT 1').bind(keyHash).first();
    }
    let selected = await env.BALANCE_DB.prepare('SELECT user_id, balance_cents, api_key, created_at FROM users WHERE user_id = ?').bind(identity).first();
    if (selected || !createUser) return selected || null;
    const now = new Date().toISOString();
    const key = apiKeyFor(identity, balanceSecret(env));
    const grantCents = signupGrantCents(env);
    const inserted = await env.BALANCE_DB.prepare('INSERT OR IGNORE INTO users (user_id, balance_cents, api_key, created_at) VALUES (?, ?, ?, ?)').bind(identity, grantCents, key, now).run();
    if (inserted.meta && inserted.meta.changes) {
      await insertD1Ledger(env, [`signup:${identity}`, identity, 'signup_grant', grantCents, grantCents, identity, now]);
    }
    selected = await env.BALANCE_DB.prepare('SELECT user_id, balance_cents, api_key, created_at FROM users WHERE user_id = ?').bind(identity).first();
    return selected || null;
  }

  if (keyLookup) {
    for (const record of mockUsers.values()) if (record.api_key === identity) return record;
    return null;
  }
  if (!mockUsers.has(identity) && createUser) {
    mockUsers.set(identity, {
      user_id: identity,
      balance_cents: signupGrantCents(env),
      api_key: apiKeyFor(identity, balanceSecret(env)),
      created_at: new Date().toISOString(),
    });
    mockLedger.set(`signup:${identity}`, { user_id: identity, kind: 'signup_grant', amount_cents: signupGrantCents(env) });
  }
  return mockUsers.get(identity) || null;
}

async function reserveCredits(env, account, costCents, runId) {
  const kind = databaseKind(env);
  const check = debitForRun(safeNumber(account.balance_cents) / 100, costCents / 100);
  if (!check.ok) return { ok: false, balance_cents: safeNumber(account.balance_cents) };
  const now = new Date().toISOString();
  const ledgerId = `run:${runId}:debit`;
  if (kind === 'neon') {
    const client = await getNeonPool(env).connect();
    try {
      await client.query('BEGIN');
      const result = await client.query(prepared('omo-mcp-reserve-v1', 'UPDATE users SET balance_cents = balance_cents - $1 WHERE user_id = $2 AND balance_cents >= $1 RETURNING balance_cents', [costCents, account.user_id]));
      if (!result.rows[0]) {
        const current = await client.query(prepared('omo-mcp-balance-v1', 'SELECT balance_cents FROM users WHERE user_id = $1', [account.user_id]));
        await client.query('COMMIT');
        return { ok: false, balance_cents: current.rows[0] ? current.rows[0].balance_cents : 0 };
      }
      const balanceCents = result.rows[0].balance_cents;
      await client.query(prepared('omo-mcp-debit-ledger-v1', 'INSERT INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT (event_id) DO NOTHING', [ledgerId, account.user_id, 'run_debit', -costCents, balanceCents, runId, now]));
      await client.query('COMMIT');
      return { ok: true, balance_cents: balanceCents };
    } catch (error) {
      try { await client.query('ROLLBACK'); } catch { /* no-op */ }
      throw error;
    } finally {
      client.release();
    }
  }
  if (kind === 'd1') {
    const update = await env.BALANCE_DB.prepare('UPDATE users SET balance_cents = balance_cents - ? WHERE user_id = ? AND balance_cents >= ?').bind(costCents, account.user_id, costCents).run();
    const current = await getAccount(env, account.user_id, false);
    const ok = !!(update.meta && update.meta.changes);
    if (ok) await insertD1Ledger(env, [ledgerId, account.user_id, 'run_debit', -costCents, current.balance_cents, runId, now]);
    return { ok, balance_cents: current ? current.balance_cents : 0 };
  }
  const current = mockUsers.get(account.user_id);
  if (!current) return { ok: false, balance_cents: 0 };
  current.balance_cents = Math.round(check.balance * 100);
  mockLedger.set(ledgerId, { user_id: account.user_id, kind: 'run_debit', amount_cents: -costCents, balance_cents: current.balance_cents, reference_id: runId, created_at: now });
  return { ok: true, balance_cents: current.balance_cents };
}

async function refundCredits(env, userId, costCents, runId) {
  if (!costCents) return;
  const kind = databaseKind(env);
  const now = new Date().toISOString();
  const ledgerId = `run:${runId}:refund`;
  if (kind === 'neon') {
    const result = await getNeonPool(env).query(prepared('omo-mcp-refund-v1', 'UPDATE users SET balance_cents = balance_cents + $1 WHERE user_id = $2 RETURNING balance_cents', [costCents, userId]));
    if (result.rows[0]) await getNeonPool(env).query(prepared('omo-mcp-refund-ledger-v1', 'INSERT INTO credits_ledger (event_id, user_id, kind, amount_cents, balance_cents, reference_id, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT (event_id) DO NOTHING', [ledgerId, userId, 'run_refund', costCents, result.rows[0].balance_cents, runId, now]));
  } else if (kind === 'd1') {
    await env.BALANCE_DB.prepare('UPDATE users SET balance_cents = balance_cents + ? WHERE user_id = ?').bind(costCents, userId).run();
    const account = await getAccount(env, userId, false);
    if (account) await insertD1Ledger(env, [ledgerId, userId, 'run_refund', costCents, account.balance_cents, runId, now]);
  } else {
    const account = mockUsers.get(userId);
    if (account) {
      account.balance_cents += costCents;
      mockLedger.set(ledgerId, { user_id: userId, kind: 'run_refund', amount_cents: costCents, balance_cents: account.balance_cents, reference_id: runId, created_at: now });
    }
  }
}

async function recordRun(env, userId, slug, costCents, runId) {
  const now = new Date().toISOString();
  const kind = databaseKind(env);
  if (kind === 'neon') {
    await getNeonPool(env).query(prepared('omo-mcp-run-v1', 'INSERT INTO runs (user_id, slug, cost_cents, created_at) VALUES ($1, $2, $3, $4)', [userId, slug, costCents, now]));
  } else if (kind === 'd1') {
    await env.BALANCE_DB.prepare('INSERT INTO runs (user_id, slug, cost_cents, created_at) VALUES (?, ?, ?, ?)').bind(userId, slug, costCents, now).run();
  } else {
    const runs = mockRuns.get(userId) || [];
    runs.unshift({ run_id: runId, slug, cost_cents: costCents, created_at: now });
    mockRuns.set(userId, runs);
  }
}

async function recentRuns(env, userId, limit = 20) {
  const kind = databaseKind(env);
  if (kind === 'neon') {
    const result = await getNeonPool(env).query(prepared('omo-mcp-runs-v1', 'SELECT slug, cost_cents, created_at FROM runs WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2', [userId, limit]));
    return result.rows || [];
  }
  if (kind === 'd1') {
    const result = await env.BALANCE_DB.prepare('SELECT slug, cost_cents, created_at FROM runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?').bind(userId, limit).all();
    return result.results || [];
  }
  return (mockRuns.get(userId) || []).slice(0, limit);
}

function makeId(prefix) {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return `${prefix}_${crypto.randomUUID().replace(/-/g, '')}`;
    }
  } catch { /* use portable fallback */ }
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
}

function firstLlmStep(helper) {
  return helper.workflow.steps.find((step) => step.type === 'llm') || llmWorkflow(GENERIC_SYSTEM, 500).steps[0];
}

function buildUserPrompt(inputs) {
  let total = 0;
  const lines = [];
  for (const [key, value] of Object.entries(inputs)) {
    const text = typeof value === 'string' ? value.trim() : JSON.stringify(value);
    total += key.length + String(text || '').length;
    if (total > MAX_INPUT_CHARS) throw new RpcFault(-32602, `inputs are too long; keep the total under ${MAX_INPUT_CHARS} characters.`);
    lines.push(`${key}: ${text == null ? '' : text}`);
  }
  if (!lines.length) throw new RpcFault(-32602, 'inputs must contain at least one value.');
  return `${lines.join('\n')}\n\nRun the helper now and return its output.`;
}

function parseModelOutput(raw) {
  let cleaned = String(raw || '').replace(/^```(?:json)?/i, '').replace(/```$/i, '').trim();
  const start = cleaned.indexOf('{');
  const end = cleaned.lastIndexOf('}');
  if (start >= 0 && end > start) cleaned = cleaned.slice(start, end + 1);
  try { return JSON.parse(cleaned); } catch { return { raw: String(raw || '') }; }
}

async function runLlm(env, helper, inputs) {
  const step = firstLlmStep(helper);
  if (!env.LLM_API_KEY) {
    return {
      mock: true,
      summary: `Mock run completed for ${helper.name}. Add LLM_API_KEY for generated output.`,
      output: helper.outputs,
      received_inputs: inputs,
    };
  }
  const response = await fetch(`${String(env.LLM_BASE_URL || 'https://opencode.ai/zen/go/v1').replace(/\/+$/, '')}/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${env.LLM_API_KEY}` },
    body: JSON.stringify({
      model: env.LLM_MODEL || step.model || 'deepseek-v4-flash',
      max_tokens: safeNumber(step.max_output, 500),
      temperature: 0.8,
      messages: [
        { role: 'system', content: step.system || GENERIC_SYSTEM },
        { role: 'user', content: buildUserPrompt(inputs) },
      ],
    }),
  });
  if (!response.ok) throw new Error(`The generation service returned ${response.status}.`);
  const body = await response.json();
  return parseModelOutput(body && body.choices && body.choices[0] && body.choices[0].message && body.choices[0].message.content);
}

async function toolSearch(request, env, args) {
  const query = requireString(args.query, 'query');
  const niche = args.category_or_niche == null ? '' : requireString(args.category_or_niche, 'category_or_niche');
  const results = searchHelpers(await loadCatalogue(request, env), query, niche);
  return { query, category_or_niche: niche || null, count: results.length, helpers: results };
}

async function toolGetHelper(request, env, args) {
  const slug = requireString(args.slug, 'slug');
  const helper = getHelper(await loadCatalogue(request, env), slug);
  if (!helper) throw new RpcFault(-32000, `I couldn't find “${slug}”. Use omo_search_helpers to find the right helper slug.`);
  return {
    name: helper.name,
    slug: helper.slug,
    category: helper.category,
    promise: helper.promise,
    description: helper.desc,
    priceOwn: helper.priceOwn,
    runPrice: helper.runPrice,
    inputs: helper.inputs,
    outputs: helper.outputs,
    workflow: publicWorkflow(helper.workflow),
  };
}

function workerApiUrl(request, env, path) {
  const base = String(env.OMO_API_BASE_URL || new URL(request.url).origin).replace(/\/+$/, '');
  return `${base}${path}`;
}

async function callWorkerApi(request, env, path, options) {
  const target = new Request(workerApiUrl(request, env, path), options);
  if (env.OMO_API && typeof env.OMO_API.fetch === 'function') return env.OMO_API.fetch(target);
  return fetch(target);
}

async function workerJson(response) {
  let body = {};
  try { body = await response.json(); } catch { body = {}; }
  if (!response.ok) {
    const reason = String(body.error || body.reason || `http_${response.status}`);
    throw new RpcFault(-32000, body.message || `Omo could not complete the request (${reason}).`, {
      reason,
      http_status: response.status,
      ...body,
    });
  }
  return body;
}

async function runDemelloViaWorker(request, env, helper, inputs, apiKey, idempotencyKey) {
  if (!apiKey || !isApiKey(apiKey)) {
    throw new RpcFault(-32602, 'This video workflow requires the owning omo_ API key so its run can be authorized and polled safely.');
  }
  if (!idempotencyKey) throw new RpcFault(-32602, 'idempotency_key is required for this hosted workflow. Reuse the same key when retrying the same inputs.');
  const key = idempotencyKey;
  if (!/^[A-Za-z0-9._:-]{8,128}$/.test(key)) throw new RpcFault(-32602, 'idempotency_key must be 8–128 letters, numbers, dots, underscores, colons, or hyphens.');
  const response = await callWorkerApi(request, env, '/api/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
      'Idempotency-Key': key,
    },
    body: JSON.stringify({ slug: helper.slug, fields: inputs }),
  });
  const body = await workerJson(response);
  return {
    ok: body.ok !== false,
    slug: helper.slug,
    run_id: body.run_id,
    status: body.status || 'running',
    phase: body.phase || 'running',
    progress_pct: safeNumber(body.progress_pct),
    progress_source: body.progress_source || 'derived',
    status_url: body.status_url || `/api/run/${body.run_id}`,
    listed_run_price_usd: safeNumber(helper.runPrice, 0.10),
    quoted_cost_usd: safeNumber(body.quoted_cost_usd, 0.10),
    billed_amount_usd: safeNumber(body.billed_amount_usd, 0),
    balance_usd: body.balance == null ? null : safeNumber(body.balance),
    billing_mode: body.billing_mode || 'nonpaid_milestone',
    paid_traffic_ready: body.paid_traffic_ready === true,
    input_notice: body.input_notice || null,
    mock: false,
    idempotent_replay: !!body.idempotent_replay,
  };
}

async function getWorkerRun(request, env, args) {
  const runId = requireString(args.run_id, 'run_id');
  const apiKey = requireString(args.api_key, 'api_key');
  if (!/^run_[A-Za-z0-9_-]{4,91}$/.test(runId)) throw new RpcFault(-32602, 'run_id is invalid.');
  if (!isApiKey(apiKey)) throw new RpcFault(-32602, 'api_key must be an Omo key beginning with omo_.');
  const response = await callWorkerApi(request, env, `/api/run/${encodeURIComponent(runId)}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${apiKey}`, Accept: 'application/json' },
  });
  return workerJson(response);
}

async function toolGetRunProgress(request, env, args) {
  const body = await getWorkerRun(request, env, args);
  return {
    ok: body.ok !== false,
    run_id: body.run_id,
    status: body.status,
    phase: body.phase,
    progress_pct: safeNumber(body.progress_pct),
    progress_source: body.progress_source || null,
    input_notice: body.input_notice || null,
    billing_mode: body.billing_mode || null,
    paid_traffic_ready: body.paid_traffic_ready === true,
    ready: body.status === 'delivered' || body.status === 'completed',
  };
}

async function toolGetRunResult(request, env, args) {
  const body = await getWorkerRun(request, env, args);
  const delivered = body.status === 'delivered' || body.status === 'completed';
  return {
    ok: body.ok !== false,
    ready: delivered,
    run_id: body.run_id,
    status: body.status,
    phase: body.phase,
    progress_pct: safeNumber(body.progress_pct),
    input_notice: body.input_notice || null,
    quoted_cost_usd: body.quoted_cost_usd == null ? null : safeNumber(body.quoted_cost_usd),
    billed_amount_usd: body.billed_amount_usd == null ? null : safeNumber(body.billed_amount_usd),
    billing_mode: body.billing_mode || null,
    paid_traffic_ready: body.paid_traffic_ready === true,
    video_url: delivered ? body.video_url || body.output && body.output.video_url || null : null,
    contact_sheet_url: delivered ? body.contact_sheet_url || body.output && body.output.contact_sheet_url || null : null,
  };
}

async function toolRunHelper(request, env, args) {
  const slug = requireString(args.slug, 'slug');
  const inputs = requireObject(args.inputs, 'inputs');
  buildUserPrompt(inputs); // validate before any credit reservation
  const helper = getHelper(await loadCatalogue(request, env), slug);
  if (!helper) throw new RpcFault(-32000, `I couldn't find “${slug}”. Search the catalogue and try the exact slug.`);

  const apiKey = args.api_key == null || args.api_key === '' ? '' : requireString(args.api_key, 'api_key');
  if (slug === DEMELLO_SLUG) {
    const idempotencyKey = args.idempotency_key == null || args.idempotency_key === ''
      ? '' : requireString(args.idempotency_key, 'idempotency_key');
    return runDemelloViaWorker(request, env, helper, inputs, apiKey, idempotencyKey);
  }
  const costUsd = safeNumber(helper.runPrice, calculateRunPrice(helper.workflow));
  const costCents = Math.round(costUsd * 100);
  let account = null;
  let reservation = null;
  const runId = makeId('run');

  if (apiKey) {
    if (!isApiKey(apiKey)) throw new RpcFault(-32602, 'api_key must be an Omo key beginning with omo_.');
    account = await getAccount(env, apiKey, false);
    if (!account) throw new RpcFault(-32000, 'That Omo API key was not found. Get your key at https://omo.space/api.html.');
    reservation = await reserveCredits(env, account, costCents, runId);
    if (!reservation.ok) {
      const check = debitForRun(safeNumber(reservation.balance_cents) / 100, costUsd);
      throw new RpcFault(-32000, `You need $${check.shortfallUsd.toFixed(2)} more Omo credit for this run. Top up securely at ${TOPUP_URL}.`, {
        reason: 'insufficient_credits',
        balance_usd: check.balance,
        cost_usd: check.costUsd,
        shortfall_usd: check.shortfallUsd,
        topup_url: TOPUP_URL,
      });
    }
  }

  try {
    const result = await runLlm(env, helper, inputs);
    if (account) await recordRun(env, account.user_id, slug, costCents, runId);
    return {
      ok: true,
      slug,
      run_id: runId,
      result,
      cost_debited_usd: account ? costUsd : 0,
      listed_run_price_usd: costUsd,
      balance_usd: account ? +(reservation.balance_cents / 100).toFixed(2) : null,
      billing_mode: account ? 'credits' : 'demo',
      mock: !env.LLM_API_KEY,
    };
  } catch (error) {
    if (account && reservation && reservation.ok) await refundCredits(env, account.user_id, costCents, runId);
    if (error instanceof RpcFault) throw error;
    throw new RpcFault(-32000, 'The helper could not finish, so any reserved credits were returned. Please try again.', { reason: 'run_failed' });
  }
}

async function toolGetBalance(_request, env, args) {
  const identity = requireString(args.api_key, 'api_key');
  if (!isApiKey(identity)) throw new RpcFault(-32602, 'Use the owning secret omo_ API key. Clerk user ids are not accepted by this public tool.');
  const account = await getAccount(env, identity, false);
  if (!account) throw new RpcFault(-32000, 'That Omo account was not found. Get your API key at https://omo.space/api.html.');
  const runs = await recentRuns(env, account.user_id, 20);
  return {
    ok: true,
    user_id: account.user_id,
    balance: (safeNumber(account.balance_cents) / 100).toFixed(2),
    balance_usd: +(safeNumber(account.balance_cents) / 100).toFixed(2),
    balance_cents: safeNumber(account.balance_cents),
    currency: 'usd',
    mock: databaseKind(env) === 'mock',
    runs: runs.map((run) => ({
      slug: run.slug,
      cost_usd: +(safeNumber(run.cost_cents) / 100).toFixed(2),
      created_at: run.created_at,
    })),
  };
}

function toolTopupOptions() {
  return {
    currency: 'usd',
    suggested_amounts_usd: topupAmounts(),
    minimum_topup_usd: MIN_TOPUP_USD,
    checkout_url: 'https://omo.space/dashboard.html',
    note: 'Top-ups happen securely via Stripe on the Omo dashboard. MCP takes no payments in v1.',
  };
}

async function callTool(request, env, params) {
  requireObject(params, 'tools/call params');
  const name = requireString(params.name, 'tool name');
  const args = params.arguments == null ? {} : requireObject(params.arguments, 'tool arguments');
  if (name === 'omo_search_helpers') return toolSearch(request, env, args);
  if (name === 'omo_get_helper') return toolGetHelper(request, env, args);
  if (name === 'omo_run_helper') return toolRunHelper(request, env, args);
  if (name === 'omo_get_run_progress') return toolGetRunProgress(request, env, args);
  if (name === 'omo_get_run_result') return toolGetRunResult(request, env, args);
  if (name === 'omo_get_balance') return toolGetBalance(request, env, args);
  if (name === 'omo_topup_options') return toolTopupOptions();
  throw new RpcFault(-32602, `Unknown tool “${name}”. Call tools/list for available Omo tools.`);
}

function toolResult(value) {
  return {
    content: [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    structuredContent: value,
    isError: false,
  };
}

function rpcError(id, error) {
  const fault = error instanceof RpcFault ? error : new RpcFault(-32000, 'Omo could not complete that request. Please try again.');
  const body = { jsonrpc: '2.0', id: id === undefined ? null : id, error: { code: fault.code, message: fault.message } };
  if (fault.data !== undefined) body.error.data = fault.data;
  return body;
}

function chooseProtocol(params) {
  const requested = params && typeof params.protocolVersion === 'string' ? params.protocolVersion : '';
  return SUPPORTED_PROTOCOLS.has(requested) ? requested : LATEST_PROTOCOL;
}

async function dispatchRpc(message, request, env) {
  if (!message || typeof message !== 'object' || Array.isArray(message) || message.jsonrpc !== '2.0' || typeof message.method !== 'string') {
    return rpcError(message && message.id, new RpcFault(-32600, 'Invalid JSON-RPC request.'));
  }
  const notification = !Object.prototype.hasOwnProperty.call(message, 'id');
  try {
    if (message.method === 'initialize') {
      if (notification) return null;
      const params = requireObject(message.params, 'initialize params');
      return {
        jsonrpc: '2.0',
        id: message.id,
        result: {
          protocolVersion: chooseProtocol(params),
          capabilities: { tools: { listChanged: false } },
          serverInfo: { name: SERVER_NAME, version: SERVER_VERSION },
          instructions: 'Search Omo helpers, inspect exact inputs, then run with an optional omo_ API key. Payments always happen on omo.space, never inside MCP.',
        },
      };
    }
    if (message.method === 'notifications/initialized') return null;
    if (message.method === 'ping') return notification ? null : { jsonrpc: '2.0', id: message.id, result: {} };
    if (message.method === 'tools/list') {
      return notification ? null : { jsonrpc: '2.0', id: message.id, result: { tools: TOOLS } };
    }
    if (message.method === 'tools/call') {
      return notification ? null : { jsonrpc: '2.0', id: message.id, result: toolResult(await callTool(request, env, message.params)) };
    }
    if (notification) return null;
    throw new RpcFault(-32601, `Method not found: ${message.method}`);
  } catch (error) {
    return notification ? null : rpcError(message.id, error);
  }
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Accept, MCP-Protocol-Version, Authorization',
    'Access-Control-Expose-Headers': 'MCP-Protocol-Version',
    'Cache-Control': 'no-store',
  };
}

function jsonResponse(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders(), ...extraHeaders, 'Content-Type': 'application/json; charset=utf-8' },
  });
}

/**
 * Handle a stateless MCP Streamable HTTP request. A Worker instance may be
 * replaced between calls, so no in-memory Mcp-Session-Id is issued or required.
 * @param {Request} request
 * @param {Record<string, any>} env Cloudflare Worker bindings and secrets.
 * @returns {Promise<Response>}
 */
export async function handleMcpRequest(request, env = {}) {
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: corsHeaders() });

  if (request.method === 'DELETE') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (request.method !== 'POST') {
    return jsonResponse({ error: 'MCP uses POST for JSON-RPC messages.' }, 405, { Allow: 'POST, DELETE, OPTIONS' });
  }
  let payload;
  try { payload = await request.json(); } catch {
    return jsonResponse(rpcError(null, new RpcFault(-32700, 'Parse error: send valid JSON.')), 400);
  }
  const messages = Array.isArray(payload) ? payload : [payload];
  if (!messages.length) return jsonResponse(rpcError(null, new RpcFault(-32600, 'An empty JSON-RPC batch is invalid.')), 400);

  const responses = [];
  for (const message of messages) {
    const response = await dispatchRpc(message, request, env);
    if (response) responses.push(response);
  }
  if (!responses.length) return new Response(null, { status: 202, headers: corsHeaders() });
  const headers = { 'MCP-Protocol-Version': LATEST_PROTOCOL };
  return jsonResponse(Array.isArray(payload) ? responses : responses[0], 200, headers);
}

async function runSelfTest() {
  const { readFile } = await import('node:fs/promises');
  const sources = [await readFile(new URL('../catalog.js', import.meta.url), 'utf8')];
  let demelloPolls = 0;
  const demelloRunId = 'run_mcpdemelloselftest0001';
  const env = {
    MCP_CATALOG_SOURCES: sources,
    SIGNUP_GRANT_USD: 5,
    OMO_API: {
      fetch: async (workerRequest) => {
        const url = new URL(workerRequest.url);
        if (workerRequest.method === 'POST' && url.pathname === '/api/run') {
          const body = await workerRequest.json();
          return jsonResponse({
            ok: true, slug: body.slug, run_id: demelloRunId, status: 'running',
            phase: 'running', progress_pct: 4, progress_source: 'derived',
            status_url: `/api/run/${demelloRunId}`, balance: 5,
            quoted_cost_usd: 0.10, billed_amount_usd: 0,
            billing_mode: 'nonpaid_milestone', paid_traffic_ready: false,
            input_notice: 'Hosted milestone sample input.',
          }, 202);
        }
        if (workerRequest.method === 'GET' && url.pathname === `/api/run/${demelloRunId}`) {
          demelloPolls += 1;
          if (demelloPolls === 1) {
            return jsonResponse({ ok: true, run_id: demelloRunId, status: 'running', phase: 'generating', progress_pct: 61, progress_source: 'webhook', input_notice: 'Hosted milestone sample input.' }, 202);
          }
          return jsonResponse({
            ok: true, run_id: demelloRunId, status: 'delivered', phase: 'delivered', progress_pct: 100,
            video_url: 'https://artifacts.example/video.mp4', contact_sheet_url: 'https://artifacts.example/contact-sheet.jpg',
            quoted_cost_usd: 0.10, billed_amount_usd: 0, billing_mode: 'nonpaid_milestone',
            paid_traffic_ready: false, input_notice: 'Hosted milestone sample input.',
          });
        }
        return jsonResponse({ error: 'not_found' }, 404);
      },
    },
  };
  let nextId = 1;
  let passed = 0;
  let failed = 0;

  function check(name, condition, detail = '') {
    if (condition) { passed += 1; console.log(`PASS ${name}`); }
    else { failed += 1; console.error(`FAIL ${name}${detail ? ` — ${detail}` : ''}`); }
  }

  async function send(method, params, options = {}) {
    const id = options.notification ? undefined : nextId++;
    const body = { jsonrpc: '2.0', method };
    if (id !== undefined) body.id = id;
    if (params !== undefined) body.params = params;
    const headers = { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream' };
    const response = await handleMcpRequest(new Request('https://omo.space/mcp', { method: 'POST', headers, body: JSON.stringify(body) }), env);
    const json = response.status === 202 ? null : await response.json();
    return { id, response, json };
  }

  const initialized = await send('initialize', { protocolVersion: LATEST_PROTOCOL, capabilities: {}, clientInfo: { name: 'omo-selftest', version: '1' } });
  check('initialize negotiates protocol and matches id', initialized.json && initialized.json.id === initialized.id && initialized.json.result.protocolVersion === LATEST_PROTOCOL);
  check('initialize is stateless and does not issue an instance-local session id', !initialized.response.headers.get('Mcp-Session-Id'));

  const notification = await send('notifications/initialized', {}, { notification: true });
  check('initialized notification is accepted', notification.response.status === 202);

  const listed = await send('tools/list', {});
  const toolNames = listed.json && listed.json.result.tools.map((tool) => tool.name);
  check('tools/list exposes all tools', Array.isArray(toolNames) && TOOLS.every((tool) => toolNames.includes(tool.name)));

  const search = await send('tools/call', { name: 'omo_search_helpers', arguments: { query: 'UGC video', category_or_niche: 'content' } });
  check('omo_search_helpers returns catalogue matches', search.json && search.json.result.structuredContent.count > 0);
  const slug = search.json.result.structuredContent.helpers[0].slug;

  const detail = await send('tools/call', { name: 'omo_get_helper', arguments: { slug } });
  check('omo_get_helper returns inputs and workflow', detail.json && detail.json.result.structuredContent.inputs.length && detail.json.result.structuredContent.workflow.steps.length);
  const demelloDetail = await send('tools/call', { name: 'omo_get_helper', arguments: { slug: DEMELLO_SLUG } });
  check('omo_get_helper pins video own/run prices at $29/$0.10', demelloDetail.json && demelloDetail.json.result.structuredContent.priceOwn === 29 && demelloDetail.json.result.structuredContent.runPrice === 0.10);

  const run = await send('tools/call', { name: 'omo_run_helper', arguments: { slug, inputs: { brief: 'Self-test product', style: 'clean', length: '15 seconds' } } });
  check('omo_run_helper returns a mock result without service keys', run.json && run.json.result.structuredContent.ok && run.json.result.structuredContent.mock === true);

  const demelloKey = `omo_${'a'.repeat(32)}`;
  const demelloRun = await send('tools/call', { name: 'omo_run_helper', arguments: {
    slug: DEMELLO_SLUG, inputs: { audio_ref: 'sample-demello-10s', duration_seconds: 10 },
    api_key: demelloKey, idempotency_key: 'mcp-demello-selftest-001',
  } });
  const demelloStarted = demelloRun.json && demelloRun.json.result.structuredContent;
  check('omo_run_helper returns async video run + zero-bill milestone metadata', demelloStarted && demelloStarted.run_id === demelloRunId && demelloStarted.progress_pct === 4 && demelloStarted.quoted_cost_usd === 0.10 && demelloStarted.billed_amount_usd === 0 && demelloStarted.input_notice);

  const demelloMissingIdempotency = await send('tools/call', { name: 'omo_run_helper', arguments: {
    slug: DEMELLO_SLUG, inputs: { audio_ref: 'sample-demello-10s', duration_seconds: 10 }, api_key: demelloKey,
  } });
  check('hosted video run requires caller-owned idempotency key', demelloMissingIdempotency.json && demelloMissingIdempotency.json.error.code === -32602);

  const demelloProgress = await send('tools/call', { name: 'omo_get_run_progress', arguments: { run_id: demelloRunId, api_key: demelloKey } });
  check('omo_get_run_progress returns phase + monotonic percent + notice', demelloProgress.json && demelloProgress.json.result.structuredContent.phase === 'generating' && demelloProgress.json.result.structuredContent.progress_pct === 61 && demelloProgress.json.result.structuredContent.input_notice);

  const demelloResult = await send('tools/call', { name: 'omo_get_run_result', arguments: { run_id: demelloRunId, api_key: demelloKey } });
  check('omo_get_run_result returns delivered video + zero-bill metadata', demelloResult.json && demelloResult.json.result.structuredContent.ready === true && /video\.mp4$/.test(demelloResult.json.result.structuredContent.video_url) && demelloResult.json.result.structuredContent.billed_amount_usd === 0 && demelloResult.json.result.structuredContent.input_notice);

  const provisioned = await getAccount(env, 'user_selftest', true);
  const selftestKey = provisioned.api_key;
  const balance = await send('tools/call', { name: 'omo_get_balance', arguments: { api_key: selftestKey } });
  check('omo_get_balance requires key possession and never returns a credential', balance.json && balance.json.result.structuredContent.balance_cents === 500 && !Object.prototype.hasOwnProperty.call(balance.json.result.structuredContent, 'api_key'));

  const arbitraryUserBalance = await send('tools/call', { name: 'omo_get_balance', arguments: { api_key: 'user_attacker' } });
  check('omo_get_balance rejects arbitrary Clerk ids without provisioning', arbitraryUserBalance.json && arbitraryUserBalance.json.error.code === -32602 && !mockUsers.has('user_attacker'));
  const paidRun = await send('tools/call', { name: 'omo_run_helper', arguments: { slug, inputs: { brief: 'Credit debit test', style: 'clean', length: '15 seconds' }, api_key: selftestKey } });
  const paidResult = paidRun.json && paidRun.json.result && paidRun.json.result.structuredContent;
  check('omo_run_helper debits keyed runs', paidResult && paidResult.cost_debited_usd > 0 && paidResult.balance_usd === +(5 - paidResult.cost_debited_usd).toFixed(2));

  const balanceAfter = await send('tools/call', { name: 'omo_get_balance', arguments: { api_key: selftestKey } });
  check('omo_get_balance reports debited credits and usage', balanceAfter.json && balanceAfter.json.result.structuredContent.balance_usd === paidResult.balance_usd && balanceAfter.json.result.structuredContent.runs.length === 1);

  const topup = await send('tools/call', { name: 'omo_topup_options', arguments: {} });
  check('omo_topup_options returns presets and minimum', topup.json && topup.json.result.structuredContent.minimum_topup_usd === 5 && topup.json.result.structuredContent.suggested_amounts_usd.join(',') === '20,50,100,200');

  mockUsers.get('user_selftest').balance_cents = 0;
  const insufficient = await send('tools/call', { name: 'omo_run_helper', arguments: { slug, inputs: { brief: 'Insufficient-credit test' }, api_key: selftestKey } });
  check('insufficient credits use -32000 with the top-up link', insufficient.json && insufficient.json.error.code === -32000 && insufficient.json.error.data.topup_url === TOPUP_URL);

  const missing = await send('tools/call', { name: 'omo_get_helper', arguments: { slug: 'not-a-real-helper' } });
  check('friendly tool errors use -32000 and match id', missing.json && missing.json.id === missing.id && missing.json.error.code === -32000);

  const unknown = await send('does/not/exist', {});
  check('unknown JSON-RPC methods use -32601', unknown.json && unknown.json.error.code === -32601);

  const total = passed + failed;
  if (failed) {
    console.error(`SELFTEST FAIL (${passed}/${total} passed)`);
    process.exitCode = 1;
  } else {
    console.log(`SELFTEST PASS (${passed}/${total})`);
  }
}

if (typeof process !== 'undefined' && process.argv && process.argv.includes('--selftest')) {
  runSelfTest().catch((error) => {
    console.error(`SELFTEST FAIL — ${error && error.stack ? error.stack : error}`);
    process.exitCode = 1;
  });
}
