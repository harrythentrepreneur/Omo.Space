// Bench — UGC Script Studio demo harness (local run, no Cloudflare needed)
// Exercises the exact same flow as worker.js against the real LLM endpoint.
//
// Usage:
//   node packages/ugc-script-studio/demo.mjs "https://example.com/silk-pillowcase" raw 30
//
// Reads LLM credentials from ~/.hermes/.env (OPENCODE_GO_API_KEY) without printing them.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const envPath = path.join(os.homedir(), '.hermes', '.env');
let apiKey = process.env.OPENCODE_GO_API_KEY;
let baseUrl = process.env.OPENCODE_GO_BASE_URL || 'https://opencode.ai/zen/go/v1';
let model = 'deepseek-v4-flash';

if (!apiKey && fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const m = line.match(/^(OPENCODE_GO_API_KEY|OPENCODE_GO_BASE_URL|LLM_MODEL)="?([^"\s]+)"?\s*$/);
    if (m && m[1] === 'OPENCODE_GO_API_KEY') apiKey = m[2];
    if (m && m[1] === 'OPENCODE_GO_BASE_URL') baseUrl = m[2];
    if (m && m[1] === 'LLM_MODEL') model = m[2];
  }
}

if (!apiKey) {
  console.error('No OPENCODE_GO_API_KEY found in env or ~/.hermes/.env');
  process.exit(2);
}

const product = process.argv[2] || 'A silk pillowcase that prevents sleep creases, $60, hypoallergenic, 30-day trial';
const voice = process.argv[3] || 'raw';
const length = Number(process.argv[4] || 30);

const system = `You are UGC Script Studio, a specialist ad-script writer for ecommerce brands.
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
- Output ONLY the JSON object, no markdown fences, no commentary, no extra text.`;

const started = Date.now();
const res = await fetch(`${baseUrl}/chat/completions`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
  body: JSON.stringify({
    model,
    max_tokens: 4000,
    temperature: 0.8,
    messages: [
      { role: 'system', content: system },
      { role: 'user', content: `Product: ${product}\n\nBrand voice: ${voice}\nLength: ${length} seconds\n\nWrite the UGC ad script now.` },
    ],
  }),
});

if (!res.ok) {
  console.error(`LLM error ${res.status}: ${(await res.text()).slice(0, 300)}`);
  process.exit(1);
}

const data = await res.json();
const raw = data.choices?.[0]?.message?.content || '';
const elapsed = ((Date.now() - started) / 1000).toFixed(1);

// Normalize: accept the canonical shape AND the model's nested variant.
function normalize(rawText) {
  let cleaned = rawText.replace(/^```(?:json)?/m, '').replace(/```$/m, '').trim();
  // find first { and last }
  const start = cleaned.indexOf('{');
  const end = cleaned.lastIndexOf('}');
  if (start >= 0 && end > start) cleaned = cleaned.slice(start, end + 1);
  let obj;
  try {
    obj = JSON.parse(cleaned);
  } catch {
    return { raw: rawText };
  }
  // nested variant: shots = [{shot, camera_notes, captions}]
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
  // if captions came through as nested under each shot and obj.captions missing
  if (!Array.isArray(obj.captions)) obj.captions = [];
  return obj;
}

const parsed = normalize(raw);

console.log(`\n=== UGC SCRIPT STUDIO DEMO (${model}, ${elapsed}s) ===`);
console.log(`Product: ${product}\nVoice: ${voice} | Length: ${length}s\n`);
console.log(JSON.stringify(parsed, null, 2));
console.log('\n=== validation ===');
const shotsArr = Array.isArray(parsed.shots) ? parsed.shots : [];
const capsArr = Array.isArray(parsed.captions) ? parsed.captions : [];
console.log(`hook: ${parsed.hook ? 'ok' : 'MISSING'}`);
console.log(`shots: ${shotsArr.length} (strings: ${shotsArr.every(s => typeof s === 'string')})`);
console.log(`captions: ${capsArr.length} (strings: ${capsArr.every(s => typeof s === 'string')})`);
console.log(`cta: ${parsed.cta ? 'ok' : 'MISSING'}`);
const ok = parsed.hook && shotsArr.length >= 1 && shotsArr.every(s => typeof s === 'string') && capsArr.length === shotsArr.length && capsArr.every(s => typeof s === 'string') && parsed.cta;
console.log(ok ? 'DEMO RESULT: PASS' : 'DEMO RESULT: FAIL');
process.exit(ok ? 0 : 1);
