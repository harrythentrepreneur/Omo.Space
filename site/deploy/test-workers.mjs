// Cognition demo worker — parse-function unit tests (no network, no keys)
//
// Usage:  node test-workers.mjs
//
// Loads the merged worker.js in a vm sandbox (stubs out `export default` so the
// module-level normalizers can be pulled in), then exercises each one against
// fenced JSON, prose-wrapped JSON, nested-variant, mixed-type, and garbage
// inputs. Prints PASS/FAIL per case, exits 0 only if everything passed.

import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(path.join(here, 'worker.js'), 'utf8');
const cjs = src.replace('export default', 'const __workerExport =');

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(
  `${cjs}\n;globalThis.__exports = { parseScript, parseAds, parsePhoto };`,
  sandbox,
  { filename: 'worker.js' }
);
const { parseScript, parseAds, parsePhoto } = sandbox.__exports;

let pass = 0;
let fail = 0;
function check(name, cond) {
  if (cond) { pass += 1; console.log(`PASS  ${name}`); }
  else { fail += 1; console.log(`FAIL  ${name}`); }
}

// ── parseScript (UGC Script Studio) ──────────────────────────────────────

const fenced = '```json\n{"hook":"h","shots":["s1","s2"],"captions":["c1","c2"],"cta":"buy"}\n```';
const s1 = parseScript(fenced);
check('ugc: fenced canonical JSON parsed', s1.hook === 'h' && s1.shots.length === 2 && s1.cta === 'buy');
check('ugc: shots are flat strings', s1.shots.every((x) => typeof x === 'string'));
check('ugc: captions parallel to shots', s1.captions.length === s1.shots.length);

const nested = '{"hook":"h","shots":[{"shot":"cu on texture","camera_notes":"CU","captions":["c1"]},{"shot":"lifestyle","camera_notes":"WS","captions":["c2"]}],"cta":"buy"}';
const s2 = parseScript(nested);
check('ugc: nested-variant flattened to strings', s2.shots.length === 2 && s2.shots.every((x) => typeof x === 'string'));
check('ugc: nested captions promoted to parallel array', Array.isArray(s2.captions) && s2.captions.length === 2);
check('ugc: nested shot joined with camera notes', s2.shots[0] === 'cu on texture — CU');

const prose = 'Here you go: {"hook":"h","shots":["a"],"captions":["b"],"cta":"c"} hope it helps!';
const s3 = parseScript(prose);
check('ugc: prose-wrapped JSON extracted', s3.hook === 'h' && s3.shots[0] === 'a');

const s4 = parseScript('sorry, no structured output today, just words');
check('ugc: garbage returns { raw }', s4 && s4.raw && !s4.hook && s4.raw.includes('sorry'));

// ── parseAds (Meta Ads Analyser) ─────────────────────────────────────────

const adsRaw = '```json\n{"verdict":"retargeting carries the account","winners":["retarget-v2 — ROAS 11.2"],"losers":["brand-test — ROAS 0.6"],"quick_wins":["move 20% of prospecting budget"],"next_move":"scale retarget-v2"}\n```';
const a1 = parseAds(adsRaw);
check('ads: fenced JSON parsed', a1.verdict.includes('retargeting') && a1.winners.length === 1 && a1.next_move === 'scale retarget-v2');
check('ads: all four arrays are string arrays', [a1.winners, a1.losers, a1.quick_wins].every((arr) => Array.isArray(arr) && arr.every((x) => typeof x === 'string')));

const a2 = parseAds('{"verdict":"v","winners":["a",123,{"nested":"obj"}],"losers":[],"quick_wins":[],"next_move":"n"}');
check('ads: mixed-type winners coerced to strings', a2.winners.length === 3 && a2.winners.every((x) => typeof x === 'string'));

const a3 = parseAds('{"verdict":"v"}');
check('ads: missing arrays default to []', Array.isArray(a3.winners) && a3.winners.length === 0 && Array.isArray(a3.losers));

const a4 = parseAds('no json at all here');
check('ads: garbage returns { raw }', a4 && a4.raw && !a4.verdict);

// ── parsePhoto (Product Photo Generator) ──────────────────────────────────

const photoRaw = '```json\n{"shot_plan":["Hero: mug on walnut table, morning light","CU: sage glaze texture"],"background_suggestion":"warm neutral — linen or oak","caption":"your 7am ritual, upgraded","listing_copy":"Hand-thrown in small batches"}\n```';
const p1 = parsePhoto(photoRaw);
check('photo: fenced JSON parsed', p1.shot_plan.length === 2 && p1.background_suggestion.includes('neutral') && p1.caption !== '' && p1.listing_copy !== '');
check('photo: shot_plan is flat strings', p1.shot_plan.every((x) => typeof x === 'string'));

const p2 = parsePhoto('{"shot_plan":["a"]}');
check('photo: missing fields default to empty string', p2.background_suggestion === '' && p2.caption === '' && p2.listing_copy === '');

const p3 = parsePhoto('nope');
check('photo: garbage returns { raw }', p3 && p3.raw === 'nope');

// ── Summary ───────────────────────────────────────────────────────────────

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
