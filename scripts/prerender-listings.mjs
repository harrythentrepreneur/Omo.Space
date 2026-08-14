#!/usr/bin/env node

// Regenerate prerendered listing pages and the live-only sitemap with:
//   node scripts/prerender-listings.mjs

import fs from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(scriptDir, '..');
const siteDir = path.join(rootDir, 'site');
const catalogPath = path.join(siteDir, 'catalog.js');
const workflowsDir = path.join(siteDir, 'workflows');
const origin = 'https://omo.space';
const coreUrls = ['/', '/about', '/blog', '/sell', '/terms', '/privacy', '/support'];

function html(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function jsonLd(value) {
  return JSON.stringify(value, null, 2).replace(/</g, '\\u003c');
}

function money(value, decimals = false) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return null;
  return '$' + (decimals ? amount.toFixed(2) : amount.toFixed(2).replace(/\.00$/, ''));
}

function isComingSoon(listing) {
  return listing.status === 'coming-soon' || listing.active === false || listing.chargeable === false;
}

function list(items, emptyLabel) {
  const values = Array.isArray(items) ? items.filter(Boolean) : [];
  return values.length
    ? values.map((item) => `          <li>${html(item)}</li>`).join('\n')
    : `          <li>${html(emptyLabel)}</li>`;
}

function faqEntries(listing) {
  const source = listing.faqs || listing.faq || [];
  if (!Array.isArray(source)) return [];
  return source.map((entry) => ({
    question: entry && (entry.question || entry.q),
    answer: entry && (entry.answer || entry.a)
  })).filter((entry) => entry.question && entry.answer);
}

function structuredData(listing, canonical, comingSoon) {
  const data = {
    '@context': 'https://schema.org',
    '@type': comingSoon ? 'Service' : 'Product',
    name: listing.name,
    description: listing.desc || listing.promise,
    url: canonical,
    image: listing.cover ? new URL(listing.cover, origin + '/').href : undefined,
    brand: { '@type': 'Brand', name: 'Omo' },
    category: listing.category || listing.marketCategory || 'AI workflow',
    additionalProperty: [
      { '@type': 'PropertyValue', name: 'Input', value: (listing.inputs || []).join('; ') },
      { '@type': 'PropertyValue', name: 'Output', value: (listing.outputs || []).join('; ') },
      { '@type': 'PropertyValue', name: 'Availability status', value: comingSoon ? 'Coming soon' : 'Available' }
    ]
  };
  if (!comingSoon && Number.isFinite(Number(listing.priceOwn))) {
    data.offers = {
      '@type': 'Offer',
      price: Number(listing.priceOwn).toFixed(2),
      priceCurrency: 'USD',
      availability: 'https://schema.org/InStock',
      url: canonical
    };
  }
  return data;
}

function renderListing(listing) {
  const canonical = `${origin}/workflows/${listing.slug}/`;
  const comingSoon = isComingSoon(listing);
  const status = comingSoon ? (listing.statusLabel || listing.priceLabel || 'Coming soon') : 'Available now';
  const ownPrice = money(listing.priceOwn);
  const runPrice = money(listing.runPrice != null ? listing.runPrice : listing.priceRun, true);
  const description = `${listing.promise || listing.desc || listing.name}${comingSoon ? ' This helper is coming soon and cannot run or charge yet.' : ''}`;
  const faqs = faqEntries(listing);
  const schemas = [structuredData(listing, canonical, comingSoon)];
  if (faqs.length) {
    schemas.push({
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: faqs.map((entry) => ({
        '@type': 'Question',
        name: entry.question,
        acceptedAnswer: { '@type': 'Answer', text: entry.answer }
      }))
    });
  }
  const cover = listing.cover
    ? `<img src="/${html(listing.cover).replace(/^\/+/, '')}" alt="${html(listing.name)} workflow cover">`
    : `<span class="cover-emoji" aria-hidden="true">${html(listing.emoji || '✦')}</span>`;
  const buyDoor = comingSoon
    ? '<button class="door door-primary" type="button" disabled>Download Skill.md — Coming soon</button>'
    : `<a class="door door-primary" href="/signup.html?open=${encodeURIComponent(listing.slug)}&amp;destination=buy">Download Skill.md${ownPrice ? ` — ${ownPrice}` : ''}</a>`;
  const runDoor = comingSoon
    ? '<button class="door door-secondary" type="button" disabled>Run it for me — Coming soon</button>'
    : `<a class="door door-secondary" href="/run.html?slug=${encodeURIComponent(listing.slug)}">Run it for me${runPrice ? ` — ${runPrice}/run` : ''}</a>`;
  const faqSection = faqs.length ? `
      <section class="section" aria-labelledby="faq-title">
        <h2 id="faq-title">Frequently asked questions</h2>
${faqs.map((entry) => `        <details><summary>${html(entry.question)}</summary><p>${html(entry.answer)}</p></details>`).join('\n')}
      </section>` : '';

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="${html(description)}">
  <meta name="robots" content="index,follow">
  <link rel="canonical" href="${canonical}">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/nav-footer.css">
  <link rel="stylesheet" href="/mobile-polish.css">
  <title>${html(listing.name)} | Omo</title>
${schemas.map((schema) => `  <script type="application/ld+json">\n${jsonLd(schema)}\n  </script>`).join('\n')}
  <style>
    :root{--canvas:#f8f7f5;--surface:#fff;--pine:#17352c;--orange:#ff6b3d;--mint:#bdefd4;--moss:#66756e;--rule:#dce3de;--display:Fraunces,Georgia,serif;--body:"DM Sans",Inter,system-ui,sans-serif}
    *{box-sizing:border-box}body{margin:0;background:var(--canvas);color:var(--pine);font:16px/1.65 var(--body)}a{color:inherit}.shell{width:min(1160px,calc(100% - 48px));margin:auto}.site-header{border-bottom:1px solid var(--rule);background:var(--canvas)}.nav-row{min-height:64px;display:flex;align-items:center;justify-content:space-between}.wordmark-logo{width:auto;height:32px}.page{padding:40px 0 80px}.layout{display:grid;grid-template-columns:minmax(0,2.3fr) minmax(280px,1fr);gap:32px;align-items:start}.story,.offer-card{border:1px solid var(--rule);border-radius:14px 14px 5px 14px;background:var(--surface)}.story{overflow:hidden}.hero{padding:36px}.eyebrow{margin:0 0 10px;color:var(--moss);font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.08em}h1,h2{font-family:var(--display);line-height:1.15}h1{margin:0 0 14px;font-size:clamp(36px,5vw,52px)}.promise{margin:0;color:#365349;font-size:20px}.cover{aspect-ratio:16/9;background:var(--mint);overflow:hidden}.cover img{width:100%;height:100%;object-fit:cover}.cover-emoji{height:100%;display:grid;place-items:center;font-size:72px}.copy{padding:12px 36px 38px}.intro{font-size:18px}.section{padding:24px 0;border-top:1px solid var(--rule)}.section h2{margin:0 0 14px;font-size:27px}.section ul{margin:0;padding-left:22px}.section li+li{margin-top:8px}details{padding:10px 0;border-top:1px solid var(--rule)}summary{font-weight:700}.sidebar{position:sticky;top:20px}.offer-card{padding:24px}.status{display:inline-block;margin-bottom:14px;padding:5px 9px;border-radius:999px;background:var(--mint);font-size:12px;font-weight:700}.price{margin:0 0 18px;color:var(--moss)}.doors{display:grid;gap:12px}.door{min-height:52px;display:flex;align-items:center;justify-content:center;padding:10px 14px;border:1px solid var(--pine);border-radius:9px;font:700 14px/1.3 var(--body);text-align:center;text-decoration:none}.door-primary{border-color:var(--orange);background:var(--orange)}.door-secondary{background:var(--surface)}button.door{width:100%;color:var(--moss);cursor:not-allowed;opacity:.72}.honesty{margin:16px 0 0;color:var(--moss);font-size:13px}.omo-footer{border-top:1px solid var(--rule)}.footer-row{min-height:92px;display:flex;align-items:center;justify-content:space-between;gap:24px}.footer-row p{margin:0}.omo-footer-links{display:flex;flex-wrap:wrap;gap:16px}.skip-link{position:absolute;left:-9999px}.skip-link:focus{left:8px;top:8px;background:#fff;padding:8px;z-index:10}@media(max-width:720px){.shell{width:calc(100% - 28px)}.layout{grid-template-columns:1fr}.sidebar{position:static}.hero,.copy{padding-left:22px;padding-right:22px}.footer-row{align-items:flex-start;flex-direction:column;padding:24px 0}}
  </style>
  <script defer src="/signup-modal.js"></script>
  <script defer src="/nav.js"></script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header omo-site-header">
    <div class="shell nav-row omo-nav-row">
      <div class="omo-nav-brand">
        <a class="wordmark" href="/" aria-label="Omo home"><img class="wordmark-logo" src="/logo-sweet-pastel.svg" alt="Omo"></a>
        <div class="omo-nav-menu"><button class="omo-nav-menu-toggle" type="button" aria-label="Menu" aria-expanded="false" aria-controls="omo-nav-menu"><span aria-hidden="true">▾</span></button><nav class="omo-nav-popover" id="omo-nav-menu" aria-label="Main menu" hidden><a href="/">Discover</a><a href="/sell">Sell Workflow</a></nav></div>
      </div>
      <a class="omo-nav-login" data-omo-login href="/signup.html">Log in</a>
    </div>
  </header>
  <main class="page" id="main">
    <div class="shell layout">
      <article class="story">
        <header class="hero"><p class="eyebrow">Omo workflow</p><h1>${html(listing.name)}</h1><p class="promise">${html(listing.promise || '')}</p></header>
        <div class="cover">${cover}</div>
        <div class="copy">
          <p class="intro">${html(listing.desc || listing.promise || '')}</p>
          <section class="section" aria-labelledby="inputs-title"><h2 id="inputs-title">What you’ll bring</h2><ul>
${list(listing.inputs, 'No input details published yet.')}
        </ul></section>
          <section class="section" aria-labelledby="outputs-title"><h2 id="outputs-title">What you’ll get</h2><ul>
${list(listing.outputs, 'No output details published yet.')}
        </ul></section>${faqSection}
        </div>
      </article>
      <aside class="sidebar" aria-label="Workflow offer"><div class="offer-card"><span class="status">${html(status)}</span><h2>${html(listing.name)}</h2><p class="price">${comingSoon ? 'Not available for purchase or cloud runs yet.' : `Download${ownPrice ? ` ${ownPrice}` : ''}${runPrice ? ` · Cloud run ${runPrice}` : ''}`}</p><div class="doors">${buyDoor}${runDoor}</div><p class="honesty">${comingSoon ? 'This listing is a preview. It cannot run or charge yet.' : 'Choose the workflow file for your own setup, or let Omo handle a hosted run.'}</p></div></aside>
    </div>
  </main>
  <footer class="omo-footer"><div class="shell footer-row"><p>Omo — useful AI helpers, ready to run.</p><nav class="omo-footer-links" aria-label="Footer"><a href="/about">About</a><a href="/sell">Sell yours</a><a href="/terms">Terms</a><a href="/privacy">Privacy</a><a href="/support">Support</a></nav></div></footer>
</body>
</html>
`;
}

async function readCatalog() {
  const source = await fs.readFile(catalogPath, 'utf8');
  const context = { window: {} };
  vm.createContext(context);
  vm.runInContext(source, context, { filename: catalogPath });
  const catalog = context.window.OMO_CATALOG;
  const visibleSlugs = context.window.OMO_VISIBLE_SLUGS;
  if (!Array.isArray(catalog) || !catalog.length) throw new Error('site/catalog.js did not expose a non-empty window.OMO_CATALOG array');
  if (!Array.isArray(visibleSlugs)) throw new Error('site/catalog.js did not expose window.OMO_VISIBLE_SLUGS');
  const slugs = new Set();
  for (const listing of catalog) {
    if (!listing || !/^[a-z0-9][a-z0-9-]*$/.test(listing.slug || '')) throw new Error(`Invalid catalog slug: ${listing && listing.slug}`);
    if (slugs.has(listing.slug)) throw new Error(`Duplicate catalog slug: ${listing.slug}`);
    slugs.add(listing.slug);
  }
  const visibleSet = new Set();
  for (const slug of visibleSlugs) {
    if (!/^[a-z0-9][a-z0-9-]*$/.test(slug || '')) throw new Error(`Invalid visible catalog slug: ${slug}`);
    if (visibleSet.has(slug)) throw new Error(`Duplicate visible catalog slug: ${slug}`);
    if (!slugs.has(slug)) throw new Error(`Visible slug is missing from catalog: ${slug}`);
    visibleSet.add(slug);
  }
  return { catalog, visibleSlugs };
}

async function writeSitemap(catalog, visibleSlugs) {
  const urls = [...coreUrls, ...visibleSlugs.map((slug) => `/workflows/${slug}/`)];
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map((pathname) => `  <url><loc>${origin}${pathname}</loc></url>`).join('\n')}\n</urlset>\n`;
  await fs.writeFile(path.join(siteDir, 'sitemap.xml'), xml);
  return urls.length;
}

const { catalog, visibleSlugs } = await readCatalog();
await fs.mkdir(workflowsDir, { recursive: true });
await Promise.all(catalog.map(async (listing) => {
  const outputDir = path.join(workflowsDir, listing.slug);
  await fs.mkdir(outputDir, { recursive: true });
  await fs.writeFile(path.join(outputDir, 'index.html'), renderListing(listing));
}));
const sitemapCount = await writeSitemap(catalog, visibleSlugs);
console.log(`Prerendered ${catalog.length} listing pages; sitemap contains ${sitemapCount} URLs.`);
