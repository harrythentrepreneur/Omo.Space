import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const site = path.join(root, 'site');
const mapped = new Set([
  'phonics-list-generator', 'decodable-sentence-creator', 'digraph-spotter',
  'phonics-reading-error-coach', 'phoneme-counter', 'syllable-splitter-and-counter',
  'grapheme-to-phoneme-converter', 'phonics-rule-explainer', 'story-idea-generator',
  'phonics-worksheet-generator', 'phonics-story-edit-studio', 'illustrated-decodable-story-maker',
]);
const blockedProjection = {
  'phonics-worksheet-generator': '$2.50',
  'phonics-story-edit-studio': '$1.00',
  'illustrated-decodable-story-maker': '$1.62',
};

const decode = (value = '') => value
  .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&apos;/g, "'")
  .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)));
const text = (value = '') => decode(value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim());
const esc = (value = '') => String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const slugFromFile = (file) => file.slice('workflow-'.length, -'.html'.length);

function section(html, heading) {
  const re = new RegExp(`<section>\\s*<h2>${heading}<\\/h2>([\\s\\S]*?)<\\/section>`);
  return html.match(re)?.[1] || '';
}

function parsePre(value) {
  const decoded = decode(value.trim());
  try { return JSON.parse(decoded); } catch { return decoded; }
}

function renderValue(value, depth = 0) {
  if (value === null) return '<span>Not recorded</span>';
  if (Array.isArray(value)) {
    if (!value.length) return '<span>None</span>';
    return `<ul>${value.map((item) => `<li>${renderValue(item, depth + 1)}</li>`).join('')}</ul>`;
  }
  if (typeof value === 'object') {
    return `<dl>${Object.entries(value).map(([key, item]) => `<dt><strong>${esc(key.replaceAll('_', ' '))}</strong></dt><dd>${renderValue(item, depth + 1)}</dd>`).join('')}</dl>`;
  }
  return `<span>${esc(value)}</span>`;
}

function manifestFor(slug) {
  const direct = path.join(root, 'containers', slug, 'manifest.json');
  if (fs.existsSync(direct)) return JSON.parse(fs.readFileSync(direct, 'utf8'));
  if (slug === 'woven-relationship-book-maker') {
    return JSON.parse(fs.readFileSync(path.join(root, 'containers/woven-storybook-pipeline/manifest.json'), 'utf8'));
  }
  return null;
}

function inputRows(html, manifest, exampleInput) {
  const provided = section(html, 'What you provide');
  const existing = [...provided.matchAll(/<li>([\s\S]*?)<\/li>/g)].map((m) => text(m[1]));
  const properties = manifest?.input_schema?.properties || {};
  const required = new Set(manifest?.input_schema?.required || []);
  const names = Object.keys(properties).length ? Object.keys(properties) : existing.map((item) => item.split(/:| — /)[0].trim());
  if (!names.length) return '<p>No form fields are published for this editorial comparison page.</p>';
  const obj = exampleInput && typeof exampleInput === 'object' && !Array.isArray(exampleInput) ? exampleInput : {};
  return `<ul>${names.map((name, index) => {
    const schema = properties[name] || {};
    const source = existing.find((item) => item.startsWith(`${name}:`) || item.startsWith(`${name} —`)) || existing[index] || name;
    const description = source.includes(':') ? source.slice(source.indexOf(':') + 1).trim() : source;
    const type = schema.type || (schema.enum ? 'choice' : 'not specified in the published catalog');
    const constraints = [schema.minimum != null ? `minimum ${schema.minimum}` : '', schema.maximum != null ? `maximum ${schema.maximum}` : '', schema.minItems != null ? `${schema.minItems}–${schema.maxItems ?? 'several'} items` : '', schema.enum ? `choices: ${schema.enum.join(', ')}` : '', required.has(name) ? 'required' : ''].filter(Boolean).join('; ');
    const sample = Object.hasOwn(obj, name) ? JSON.stringify(obj[name]) : (index === 0 && typeof exampleInput === 'string' ? exampleInput : 'See the example above');
    return `<li><strong>${esc(name)}</strong> — Type: ${esc(type)}${constraints ? ` (${esc(constraints)})` : ''}. <strong>Example:</strong> ${esc(sample)}. <strong>What you give it:</strong> ${esc(description || 'the value requested by the workflow')}.</li>`;
  }).join('')}</ul>`;
}

function pageFacts(html) {
  const name = text(html.match(/<h1>([\s\S]*?)<\/h1>/)?.[1] || 'This workflow').split(':')[0];
  const description = decode(html.match(/<meta name="description" content="([^"]*)">/)?.[1] || '');
  const price = text(html.match(/<div class="fact"><strong>Price<\/strong><span>([\s\S]*?)<\/span><\/div>/)?.[1] || 'See the page for current pricing');
  const pre = [...html.matchAll(/<pre>([\s\S]*?)<\/pre>/g)].map((m) => parsePre(m[1]));
  return { name, description, price, exampleInput: pre[0], exampleOutput: pre[1] };
}

function runtimeLine(slug, html, manifest) {
  if (slug.startsWith('compare-')) return 'Editorial comparison page · no model runtime · status: indexable reference page.';
  if (blockedProjection[slug]) {
    if (slug === 'illustrated-decodable-story-maker') return `Multi-provider artifact runtime · not yet available — in review. The ${blockedProjection[slug]} figure is a projection, not an offer.`;
    return `Artifact runtime · not yet available — in review. The ${blockedProjection[slug]} figure is a projection, not an offer.`;
  }
  const provider = decode(html.match(/&quot;provider&quot;:\s*&quot;([^&]+)&quot;/)?.[1] || '');
  const model = decode(html.match(/&quot;model&quot;:\s*&quot;([^&]+)&quot;/)?.[1] || '');
  if (mapped.has(slug)) return `${model || 'deepseek-v4-flash'} via ${provider || 'the shared Omo LLM runner'} · in review — live soon. The listed $0.10 is the reviewed target price; a chargeable hosted run is not yet proven.`;
  if (manifest) {
    const readiness = manifest.readiness?.status === 'ready' ? 'hosted-run profile is reviewed; confirm current runner availability before purchase' : 'in review; hosted run is not currently available';
    return `${model && provider ? `${model} via ${provider}` : 'Provider/model are not named in the public manifest'} · ${readiness}.`;
  }
  return 'Provider/model are not published for this catalog workflow · hosted-run verification is not recorded on this static page; confirm current availability in the runner.';
}

function faqFor(slug, facts) {
  const isCompare = slug.startsWith('compare-');
  const isBlocked = Boolean(blockedProjection[slug]);
  const isMappedLiveSoon = mapped.has(slug) && !isBlocked;
  const phonics = /phonics|phoneme|grapheme|syllable|decodable|digraph/i.test(`${facts.name} ${facts.description}`);
  const first = isCompare
    ? { q: `Does this page claim ${facts.name} are equivalent products?`, a: 'No. It compares one bounded job and states where the broader product is a better fit.' }
    : isBlocked
      ? { q: `Can I buy ${facts.name} now?`, a: `No. It is not yet available and remains in review. ${blockedProjection[slug]} is a planning projection, not a sale price.` }
      : isMappedLiveSoon
        ? { q: `Is ${facts.name} really $0.10?`, a: 'The reviewed target is $0.10 per run, but the chargeable hosted workflow is still in review and is not yet proven live.' }
        : { q: `How much does ${facts.name} cost?`, a: `The price shown on this page is ${facts.price}. Confirm runner availability before purchase.` };
  const items = [
    first,
    { q: 'Do I need an account to inspect this page?', a: 'No. You can read the inputs, example, limitations, and price without an account. The runner may require sign-in before a run or purchase.' },
    { q: 'Is the example a verified customer run?', a: 'No. It is an example output from a contract fixture or catalog preview unless the page explicitly supplies a dated real-run test note.' },
    { q: 'What should I do if the output is wrong?', a: phonics ? 'Review it against the learner’s taught code, dialect, and classroom context. Do not treat it as an assessment or diagnosis.' : 'Review all facts, claims, media, and platform settings before using or publishing the result. Regenerate or edit anything unsupported.' },
    { q: phonics ? 'What grade is this for?' : 'Can I download the result?', a: phonics ? 'Use the grade or difficulty controls when the workflow provides them; otherwise a teacher must decide whether the output fits the learner.' : 'A download is available only when the completed workflow explicitly lists a file artifact. The page example itself is not a promised download.' },
  ];
  return items;
}

function jsonLd(faq) {
  return JSON.stringify({
    '@context': 'https://schema.org', '@type': 'FAQPage',
    mainEntity: faq.map(({ q, a }) => ({ '@type': 'Question', name: q, acceptedAnswer: { '@type': 'Answer', text: a } })),
  }, null, 2).split('\n').map((line) => `    ${line}`).join('\n');
}

function visibleFaq(faq) {
  return faq.map(({ q, a }) => `      <h3>${esc(q)}</h3>\n      <p>${esc(a)}</p>`).join('\n');
}

function enhancement(slug, html) {
  const manifest = manifestFor(slug);
  const facts = pageFacts(html);
  const faq = faqFor(slug, facts);
  const comparison = slug.startsWith('compare-');
  const readable = comparison
    ? `<p><strong>Example input:</strong> A buyer deciding whether one bounded job or a broader subscription product fits their current task.</p>\n      <p><strong>Example output:</strong> The visible scope, price, and limitations comparison above. This is editorial guidance, not a model-generated or tested proof object.</p>`
    : `<p class="note">Example output — fixture or catalog preview, not tested proof. The complete source example remains above for later replacement by verified run evidence.</p>\n      <h3>Example input, in readable form</h3>\n      ${renderValue(facts.exampleInput ?? 'No example input is published.')}\n      <h3>Example output, in readable form</h3>\n      ${renderValue(facts.exampleOutput ?? 'No example output is published.')}`;
  const bylineStatus = blockedProjection[slug] ? 'in review; no independent educator approval recorded' : mapped.has(slug) ? 'contract reviewed; hosted run and named educator review pending' : comparison ? 'editorial facts reviewed; no independent product endorsement' : 'catalog facts reviewed; no independent performance review recorded';
  return {
    faqJson: `  <!-- SEO-X:FAQ-JSON-LD:START -->\n  <script type="application/ld+json">\n${jsonLd(faq)}\n  </script>\n  <!-- SEO-X:FAQ-JSON-LD:END -->\n`,
    body: `    <!-- SEO-X:PROMPTBASE:START -->\n    <section aria-labelledby="seo-x-examples">\n      <h2 id="seo-x-examples">Examples</h2>\n      ${readable}\n    </section>\n    <section aria-labelledby="seo-x-inputs">\n      <h2 id="seo-x-inputs">What you give it</h2>\n      ${comparison ? '<p>This editorial comparison takes no workflow input. Start with the concrete job, required output, and whether you need one run or a broader platform.</p>' : inputRows(html, manifest, facts.exampleInput)}\n    </section>\n    <section aria-labelledby="seo-x-runtime">\n      <h2 id="seo-x-runtime">Model and runtime</h2>\n      <p>${esc(runtimeLine(slug, html, manifest))}</p>\n    </section>\n    <section aria-labelledby="seo-x-creator">\n      <h2 id="seo-x-creator">Creator proof</h2>\n      <p><strong>Built by Omo&#39;s team</strong> · reviewed status: ${esc(bylineStatus)}.</p>\n    </section>\n    <section aria-labelledby="seo-x-faq">\n      <h2 id="seo-x-faq">Frequently asked questions</h2>\n${visibleFaq(faq)}\n    </section>\n    <!-- SEO-X:PROMPTBASE:END -->\n`,
  };
}

const files = fs.readdirSync(site).filter((name) => /^workflow-.*\.html$/.test(name)).sort();
console.log('*** Begin Patch');
for (const file of files) {
  const html = fs.readFileSync(path.join(site, file), 'utf8');
  if (html.includes('SEO-X:PROMPTBASE:START')) continue;
  const { faqJson, body } = enhancement(slugFromFile(file), html);
  console.log(`*** Update File: site/${file}`);
  console.log('@@');
  console.log('-  <link rel="preconnect" href="https://fonts.googleapis.com">');
  for (const line of faqJson.trimEnd().split('\n')) console.log(`+${line}`);
  console.log('+  <link rel="preconnect" href="https://fonts.googleapis.com">');
  console.log('@@');
  console.log('-    <section>');
  console.log('-      <h2>Next action</h2>');
  for (const line of body.trimEnd().split('\n')) console.log(`+${line}`);
  console.log('+    <section>');
  console.log('+      <h2>Next action</h2>');
}
console.log('*** End Patch');
