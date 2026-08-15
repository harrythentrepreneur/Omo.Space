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
const workflowPath = path.join(siteDir, 'workflow.html');
const workflowsDir = path.join(siteDir, 'workflows');
const origin = 'https://omo.space';
const coreUrls = ['/', '/about', '/blog', '/sell', '/terms', '/privacy', '/support'];
const workflowSource = await fs.readFile(workflowPath, 'utf8');
const workflowStyleMatch = workflowSource.match(/<style>([\s\S]*?)<\/style>/);
const workflowBehaviorStart = workflowSource.indexOf("    (function () {\n      'use strict';");
const workflowBehaviorEnd = workflowSource.lastIndexOf('  </script>');
if (!workflowStyleMatch || workflowBehaviorStart === -1 || workflowBehaviorEnd === -1) {
  throw new Error('Could not extract the frozen listing CSS and behavior from site/workflow.html');
}
const workflowCss = workflowStyleMatch[1].trimEnd();
const workflowBehavior = workflowSource.slice(workflowBehaviorStart, workflowBehaviorEnd).trim();

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

function isComingSoon(listing) {
  return listing.status === 'coming-soon' || listing.active === false || listing.chargeable === false;
}

function faqEntries(listing) {
  const source = listing.faqs || listing.faq || [];
  if (!Array.isArray(source)) return [];
  return source.map((entry) => ({
    question: entry && (entry.question || entry.q),
    answer: entry && (entry.answer || entry.a)
  })).filter((entry) => entry.question && entry.answer);
}

function titleCase(value) {
  return String(value || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatPrice(value) {
  const price = Number(value);
  if (!Number.isFinite(price)) return '$0';
  return '$' + (Math.round(price * 100) % 100 === 0
    ? price.toFixed(0)
    : price.toFixed(2).replace(/0$/, ''));
}

function formatRunPrice(value) {
  const price = Number(value);
  return '$' + (Number.isFinite(price) ? price : 0).toFixed(2);
}

function workflowStepLabel(step, index) {
  if (step && step.label) return step.label;
  if (step && step.type === 'llm') {
    return 'Shape the ' + titleCase(step.role || 'result').toLowerCase() +
      (step.model ? ' with ' + titleCase(step.model) : '');
  }
  if (step && step.type === 'api') {
    const apiLabels = {
      replicate_run: 'Generate the visual assets',
      modal_gpu_30s: 'Render the final media',
      heygen_avatar_render: 'Render the on-camera avatar',
      heygen_voiceover: 'Add the finished voiceover',
      openai_image: 'Create the supporting images',
      elevenlabs_tts: 'Generate the voice track',
      e2b_sandbox: 'Package the result in a clean workspace'
    };
    return apiLabels[step.api] || titleCase(step.api || 'service step');
  }
  if (step && step.role) return titleCase(step.role);
  return 'Complete workflow step ' + (index + 1);
}

function perfectFor(listing) {
  const results = [];
  const tags = listing.tags || [];
  for (let index = 0; index < tags.length && results.length < 3; index += 1) {
    const tag = titleCase(tags[index]);
    if (tag && !results.includes(tag)) results.push(tag);
  }
  const haystack = [listing.name, listing.promise, listing.desc].join(' ').toLowerCase();
  const inferred = [];
  if (/ugc|ad|creative|commercial/.test(haystack)) inferred.push('Ecommerce creative teams', 'Performance marketers');
  if (/shopify|product page|storefront/.test(haystack)) inferred.push('Shopify operators');
  if (/seo|discover|recommend/.test(haystack)) inferred.push('Growth and SEO teams');
  if (/video|reel|animation/.test(haystack)) inferred.push('Content creators');
  if (/relationship|book|story/.test(haystack)) inferred.push('Thoughtful gift makers');
  if (!inferred.length) inferred.push('Small teams', 'Solo operators');
  for (let index = 0; index < inferred.length && results.length < 5; index += 1) {
    if (!results.includes(inferred[index])) results.push(inferred[index]);
  }
  return results;
}

function imageSource(candidate) {
  if (typeof candidate === 'string') return candidate;
  if (!candidate || typeof candidate !== 'object') return '';
  if (/video|reel|embed/i.test(String(candidate.type || candidate.kind || ''))) return '';
  return candidate.url || candidate.src || candidate.image || candidate.imageUrl || candidate.path || '';
}

function mediaAssets(listing) {
  const assets = [];
  const imageUrls = new Set();
  const hasCreatorReel = Boolean(listing.embedHtml || listing.embed || listing.reelUrl);
  function addImage(candidate, label) {
    if (Array.isArray(candidate)) {
      candidate.forEach((item, index) => addImage(item, `${label} ${index + 1}`));
      return;
    }
    const source = imageSource(candidate);
    if (source) {
      if (!imageUrls.has(source)) {
        imageUrls.add(source);
        assets.push({ type: 'image', src: source, label });
      }
      return;
    }
    if (candidate && typeof candidate === 'object') {
      Object.keys(candidate).forEach((key) => addImage(candidate[key], titleCase(key)));
    }
  }
  if (hasCreatorReel) {
    const posterSource = imageSource(listing.cover);
    if (posterSource) imageUrls.add(posterSource);
    assets.push({ type: 'video', src: posterSource, label: 'Creator reel' });
  } else {
    addImage(listing.cover, 'Cover');
  }
  if (listing.icon && /[/.]/.test(String(listing.icon))) addImage(listing.icon, 'Artwork');
  ['media', 'gallery', 'images', 'frames', 'art', 'assets'].forEach((key) => {
    if (listing[key]) addImage(listing[key], titleCase(key));
  });
  if (!assets.length) assets.push({ type: 'image', src: '', label: 'Artwork' });
  return assets;
}

function imageMarkup(listing, source, alt = '') {
  return source
    ? `<img src="${html(assetHref(source))}" alt="${html(alt)}">`
    : `<span class="media-emoji" aria-hidden="true">${html(listing.emoji || '✦')}</span>`;
}

function assetHref(source) {
  const value = String(source || '');
  return /^[a-z][a-z0-9+.-]*:/i.test(value) || value.startsWith('//')
    ? value
    : '/' + value.replace(/^\/+/, '');
}

function mediaMarkup(listing) {
  const slides = mediaAssets(listing);
  const slideMarkup = slides.map((asset, index) => {
    const activeClass = index === 0 ? ' is-active' : '';
    const attributes = `id="media-slide-${index}" data-slide-index="${index}" role="group" aria-roledescription="slide" aria-label="${index + 1} of ${slides.length}: ${html(asset.label)}" aria-hidden="${index === 0 ? 'false' : 'true'}"`;
    if (asset.type === 'video') {
      return `<div class="media-slide${activeClass}" ${attributes}><button class="media-poster" type="button" data-play-index="${index}" aria-label="Play the creator reel">${imageMarkup(listing, asset.src)}<span class="play-button" aria-hidden="true">▶</span><span class="watch-label">Watch the creator’s reel</span></button></div>`;
    }
    return `<div class="media-slide${activeClass}" ${attributes}><div class="media-fallback">${imageMarkup(listing, asset.src, `${listing.name} ${asset.label.toLowerCase()}`)}</div></div>`;
  }).join('');
  const controls = slides.length > 1
    ? `<button class="media-nav media-prev" type="button" aria-label="Previous slide">‹</button><button class="media-nav media-next" type="button" aria-label="Next slide">›</button><div class="media-dots" aria-label="Choose a slide">${slides.map((asset, index) => `<button class="media-dot${index === 0 ? ' is-active' : ''}" type="button" data-dot-index="${index}" aria-label="Go to slide ${index + 1}" aria-current="${index === 0 ? 'true' : 'false'}"></button>`).join('')}</div>`
    : '';
  const thumbnails = slides.map((asset, index) => `<button class="media-thumbnail${index === 0 ? ' is-active' : ''}" type="button" data-thumbnail-index="${index}" role="tab" aria-controls="media-slide-${index}" aria-label="Show ${html(asset.label.toLowerCase())}" aria-selected="${index === 0 ? 'true' : 'false'}" aria-current="${index === 0 ? 'true' : 'false'}" tabindex="${index === 0 ? '0' : '-1'}">${imageMarkup(listing, asset.src)}${asset.type === 'video' ? '<span class="thumbnail-play" aria-hidden="true">▶</span>' : ''}</button>`).join('');
  return {
    slides: slideMarkup + controls + '<span class="sr-only" id="media-status" aria-live="polite">Slide 1 of ' + slides.length + '</span>',
    thumbnails,
    count: slides.length
  };
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
  const listingPath = `/workflows/${listing.slug}/`;
  const canonical = `${origin}${listingPath}`;
  const comingSoon = isComingSoon(listing);
  const ownPrice = formatPrice(listing.priceOwn);
  const runPrice = formatRunPrice(listing.runPrice != null ? listing.runPrice : listing.priceRun);
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
  const media = mediaMarkup(listing);
  const maker = listing.makerName || listing.maker || 'Independent maker';
  const infoParts = [`by ${maker}`, `${listing.upvotes || 0} upvotes`];
  if (listing.category) infoParts.push(titleCase(listing.category));
  if (listing.version) {
    const versionLabel = String(listing.version).split('·')[0].trim();
    infoParts.push(/^v/i.test(versionLabel) ? versionLabel : `v${versionLabel}`);
  }
  let workflowSteps = listing.workflow && Array.isArray(listing.workflow.steps)
    ? listing.workflow.steps
    : [];
  if (comingSoon) {
    workflowSteps = [{ label: 'Complete hosting, review, and safety checks before activation' }];
  } else if (!workflowSteps.length) {
    workflowSteps = [{ label: 'Follow the included process from your input to a finished result' }];
  }
  const insideItems = workflowSteps.map(workflowStepLabel);
  const inputItems = listing.inputs || ['Your brief and the details you want the workflow to use'];
  const outputItems = listing.outputs || ['A finished, ready-to-use result'];
  const perfectItems = perfectFor(listing);
  const renderItems = (items) => items.map((item) => `<li>${html(item)}</li>`).join('');
  const coverSource = listing.cover || listing.icon || '';
  const cover = imageMarkup(listing, coverSource, `${listing.name} cover`);
  const contextThumb = coverSource
    ? `<img src="${html(assetHref(coverSource))}" alt="">`
    : html(listing.emoji || '✦');
  const buyButtonLabel = comingSoon ? 'Coming soon' : `Download Skill.md — ${ownPrice}`;
  const runButtonLabel = comingSoon ? 'Coming soon' : `Run it for me — ${runPrice}/run`;
  const offerActions = `
                <div class="offer-actions"${comingSoon ? ' hidden' : ''}>
                  <div class="offer-choice offer-choice-buy">
                    <button class="button button-buy" id="buy-button" type="button" aria-label="${html(buyButtonLabel)}. Workflow + prompts. Run them on your computer.">${html(buyButtonLabel)}</button>
                    <button class="offer-info" id="buy-info" type="button" aria-label="About Download Skill.md: Workflow + prompts. Run them on your computer." aria-controls="buy-tooltip" aria-expanded="false"><span class="offer-info-mark" aria-hidden="true">i</span></button>
                    <span class="offer-tooltip" id="buy-tooltip" role="tooltip">Workflow + prompts. Run them on your computer.</span>
                  </div>
                  <div class="offer-choice offer-choice-run">
                    <button class="button button-run" id="run-button" type="button" aria-label="${html(runButtonLabel)}. Per run. Omo handles the setup and sends back the finished result.">${html(runButtonLabel)}</button>
                    <button class="offer-info" id="run-info" type="button" aria-label="About Run it for me: Per run. Omo handles the setup and sends back the finished result." aria-controls="run-tooltip" aria-expanded="false"><span class="offer-info-mark" aria-hidden="true">i</span></button>
                    <span class="offer-tooltip" id="run-tooltip" role="tooltip">Per run. Omo handles the setup and sends back the finished result.</span>
                  </div>
                </div>`;
  const closingCopy = comingSoon
    ? 'This helper is being prepared for hosting and review. It cannot run or charge yet.'
    : 'Buy it once if you want the workflow and prompts in your own hands. Choose a cloud run when you would rather skip the setup and let Omo handle the service keys.';

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <base href="/">
  <meta name="description" content="${html(description)}">
  <meta name="robots" content="index,follow">
  <link rel="canonical" href="${canonical}">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <meta name="theme-color" content="#F8F7F5">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&amp;family=Fraunces:opsz,wght@9..144,600&amp;display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/nav-footer.css">
  <link rel="stylesheet" href="/mobile-polish.css">
  <title>${html(listing.name)} | Omo</title>
${schemas.map((schema) => `  <script type="application/ld+json">\n${jsonLd(schema)}\n  </script>`).join('\n')}
  <style>${workflowCss}
  </style>
  <script defer src="/signup-modal.js"></script>
  <script defer src="/nav.js"></script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header omo-site-header">
    <div class="shell nav-row omo-nav-row">
      <div class="omo-nav-brand">
        <a class="omo-nav-workflow-identity" href="${listingPath}" aria-label="${html(listing.name)} workflow listing"><span class="omo-nav-context-thumb" aria-hidden="true">${contextThumb}</span><span class="omo-nav-context-name">${html(listing.name)}</span></a>
        <div class="omo-nav-menu"><button class="omo-nav-menu-toggle" type="button" aria-label="Menu" aria-expanded="false" aria-controls="omo-nav-menu" aria-haspopup="true"><span class="omo-nav-chevron" aria-hidden="true">▾</span></button><nav class="omo-nav-popover" id="omo-nav-menu" aria-label="Main menu" hidden><a href="/">Discover</a><a href="/sell">Sell Workflow</a></nav></div>
      </div>
      <a class="omo-nav-login" data-omo-login href="/signup.html">Log in</a>
    </div>
  </header>
  <main class="page" id="main">
    <div class="shell">
      <div class="layout" id="workflow-layout">
        <article class="story sig-cut" aria-labelledby="listing-title">
          <header class="story-header"><h1 class="listing-title" id="listing-title">${html(listing.name)}</h1><p class="listing-promise" id="listing-promise">${html(listing.promise || '')}</p></header>
          <div class="media-gallery">
            <div class="media-shell sig-cut" id="hero-media" role="region" aria-roledescription="carousel" aria-label="${html(listing.name)} media" tabindex="0">${media.slides}</div>
            <div class="media-thumbnails${media.count === 1 ? ' is-single' : ''}" id="media-thumbnails" role="tablist" aria-label="Choose a slide" style="--thumbnail-count:${media.count}">${media.thumbnails}</div>
            <p class="quiet-line" id="quiet-line">${infoParts.map((part) => `<span class="metadata-item">${html(part)}</span>`).join('')}</p>
          </div>
          <div class="story-copy">
            <p class="intro" id="listing-intro">${html(listing.desc || listing.promise || '')}</p>
            <section class="copy-section" aria-labelledby="inside-title"><h2 id="inside-title">What’s inside</h2><ol class="plain-list" id="steps-list">${renderItems(insideItems)}</ol></section>
            <section class="copy-section" aria-labelledby="inputs-title"><h2 id="inputs-title">What you’ll bring</h2><ul class="plain-list" id="inputs-list">${renderItems(inputItems)}</ul></section>
            <section class="copy-section" aria-labelledby="outputs-title"><h2 id="outputs-title">What you’ll get</h2><ul class="plain-list" id="outputs-list">${renderItems(outputItems)}</ul></section>
            <section class="copy-section" aria-labelledby="perfect-title"><h2 id="perfect-title">Perfect for</h2><ul class="plain-list" id="perfect-list">${renderItems(perfectItems)}</ul></section>
            <p class="closing-copy" id="closing-copy">${html(closingCopy)}</p>
          </div>
        </article>
        <aside class="sidebar" aria-label="Workflow offer">
          <div class="offer-card sig-cut">
            <div class="offer-cover" id="offer-cover">${cover}</div>
            <div class="offer-body">
              <h2 class="offer-title" id="offer-title">${html(listing.name)}</h2>
              <p class="offer-desc" id="offer-desc">${html(listing.promise || '')}</p>${offerActions}
            </div>
          </div>
          <div class="offer-powered"><span>Powered by</span><img class="offer-logo" src="/logo-sweet-pastel.svg" alt="" width="128" height="40"></div>
          <p class="offer-note" id="offer-note" role="status" aria-live="polite">${comingSoon ? 'Coming soon — this helper cannot run or charge yet.' : ''}</p>
        </aside>
      </div>
    </div>
  </main>
  <footer class="omo-footer">
    <div class="shell footer-row"><p>Omo — useful AI helpers, ready to run.</p><nav class="omo-footer-links" aria-label="Footer"><a href="/about">About</a><a href="/sell">Sell yours</a><a href="/creators">For creators</a><a href="/terms">Terms</a><a href="/privacy">Privacy</a><a href="/support">Support</a></nav></div>
  </footer>
  <script src="/catalog.js"></script>
  <script src="/key-config.js"></script>
  <script src="/clerk.js"></script>
  <script src="/stripe.js"></script>
  <script>
${workflowBehavior}
  </script>
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
