// Bench — UGC Script Studio demo worker (Cloudflare Workers compatible)
// The "it actually runs" proof: paste a product link, get a real UGC script.
//
// Env vars (set in Cloudflare dashboard / wrangler secret):
//   LLM_API_KEY  — key for the OpenAI-compatible endpoint below
//   LLM_BASE_URL — default https://opencode.ai/zen/go/v1
//   LLM_MODEL    — default deepseek-v4-flash
//
// Demo caps (mirror SKILL.md metadata.bench.demo_caps):
//   DEMO_MAX_TOKENS   — 4000
//   DEMO_MAX_INPUT    — 2000 chars of product text
//   DEMO_DAILY_CAP    — 5 free sessions/day (per IP via KV; no KV = in-memory)

const SYSTEM_PROMPT = `You are UGC Script Studio, a specialist ad-script writer for ecommerce brands.
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

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: cors(),
      });
    }
    if (request.method !== 'POST') {
      return json({ error: 'POST only' }, 405, cors());
    }

    // ── Demo caps ─────────────────────────────────────────────
    const ip = request.headers.get('CF-Connecting-IP') || 'local';
    const today = new Date().toISOString().slice(0, 10);
    const key = `demo:${ip}:${today}`;
    let used = 0;
    if (env.BENCH_KV) {
      used = Number((await env.BENCH_KV.get(key)) || 0);
      if (used >= Number(env.DEMO_DAILY_CAP || 5)) {
        return json({ error: 'Free demo limit reached for today. Buy the license to keep going.' }, 429, cors());
      }
    }

    let body;
    try { body = await request.json(); } catch { body = {}; }
    const product = String(body.product || body.product_url || '').trim();
    const voice = String(body.voice || 'raw').trim();
    const length = Number(body.length || 30);

    if (!product) return json({ error: 'Send a product link or description.' }, 400, cors());
    if (product.length > Number(env.DEMO_MAX_INPUT || 2000)) {
      return json({ error: 'Product description too long for the free demo.' }, 400, cors());
    }
    if (![15, 30, 60].includes(length)) {
      return json({ error: 'Length must be 15, 30, or 60 seconds.' }, 400, cors());
    }

    // ── Run the workflow ──────────────────────────────────────
    try {
      const llm = await fetch(`${env.LLM_BASE_URL || 'https://opencode.ai/zen/go/v1'}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${env.LLM_API_KEY}`,
        },
        body: JSON.stringify({
          model: env.LLM_MODEL || 'deepseek-v4-flash',
          max_tokens: Number(env.DEMO_MAX_TOKENS || 4000),
          temperature: 0.8,
          messages: [
            { role: 'system', content: SYSTEM_PROMPT },
            {
              role: 'user',
              content:
                `Product: ${product}\n\n` +
                `Brand voice: ${voice}\nLength: ${length} seconds\n\n` +
                `Write the UGC ad script now.`,
            },
          ],
        }),
      });

      if (!llm.ok) {
        const errText = await llm.text();
        return json({ error: `LLM error ${llm.status}: ${errText.slice(0, 200)}` }, 502, cors());
      }
      const data = await llm.json();
      const raw = data.choices?.[0]?.message?.content || '';
      const parsed = parseScript(raw);

      if (env.BENCH_KV) {
        await env.BENCH_KV.put(key, String(used + 1), { expirationTtl: 86400 });
      }

      return json({ ok: true, script: parsed, raw }, 200, cors());
    } catch (e) {
      return json({ error: String(e.message || e) }, 500, cors());
    }
  },
};

function parseScript(raw) {
  // Strip markdown fences if the model wrapped them anyway, then find the JSON object.
  let cleaned = raw.replace(/^```(?:json)?/m, '').replace(/```$/m, '').trim();
  const start = cleaned.indexOf('{');
  const end = cleaned.lastIndexOf('}');
  if (start >= 0 && end > start) cleaned = cleaned.slice(start, end + 1);
  let obj;
  try {
    obj = JSON.parse(cleaned);
  } catch {
    return { raw };
  }
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
