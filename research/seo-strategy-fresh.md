# Fresh SEO strategy audit: static pages vs hosted listings

Audit date: 2026-08-14. Scope: the repository at this revision, the accumulated Omo research, and current Google Search Central guidance.

## Verdict

The founder is right about the strategic unit: a genuinely useful hosted listing should be Omo's long-term SEO atom. A workflow is a productized outcome with a name, inputs, outputs, price, examples, limitations, and—once available—run evidence. That is closer to a Fiverr Gig, PromptBase listing, or OpenRouter model page than to a generic blog article.

But “index only the current hosted listings” is premature. Today the hosted listing is a client-rendered app shell at `workflow.html?slug=...`, with no canonical tag or JSON-LD in the source, and the catalog is currently filtered to four visible slugs. It is not yet the clean, durable object the founder is imagining. The current static pages are the stronger search documents today, although they overlap with the dynamic shell and should not remain as two competing indexable representations.

**Recommendation: choose (c), a deliberate hybrid transition.** Keep static pages only for the 12 mapped money/workflow intents while they carry the best proof and metadata; make clean, server-rendered or prerendered `/workflows/<slug>/` pages the future canonical listing surface; migrate each static page into that canonical page when its hosted listing has equivalent proof. Do not keep both versions indexable indefinitely. Do not generate pages for every input variation.

## 1. What the code actually emits

### `site/workflow.html?slug=<slug>`

The current file has:

- a generic source `<title>Workflow details | Omo</title>`;
- a generic description, `See what is inside this Omo workflow...`;
- `<meta name="robots" content="index,follow">`;
- **no `rel="canonical"` tag**;
- **no JSON-LD script**;
- no listing-specific facts in the initial HTML head or body that are present only after rendering.

After `catalog.js` loads, client-side JavaScript reads `URLSearchParams(...).get('slug')`, finds the object in `OMO_VISIBLE_CATALOG`, changes `document.title`, changes the description, and fills the visible title, promise, intro, price, steps, media, FAQ-like material, and links. The catalog itself is a large JavaScript data file; the page is not server-rendered per listing.

Google does execute JavaScript and can index rendered content, so this is not automatically invisible. However, Google documents the extra crawl/render/index phases and says server-side or pre-rendering is still a good idea because it is faster and not all bots run JavaScript. More importantly for this implementation, the initial generic page is not a strong listing document, and non-Google crawlers or previews may see only the shell.

The page also uses `OMO_VISIBLE_CATALOG`, not all 220 catalog objects. The current visibility allowlist contains four slugs: `japanese-style-story-video`, `woven-relationship-book-maker`, `customer-feedback-theme-finder`, and `facebook-ads-copywriter`. That is a product visibility control, not an indexable catalog architecture.

### `site/run.html?slug=<slug>`

This is explicitly `<meta name="robots" content="noindex,follow">`, has a generic title/description, no canonical tag, and no JSON-LD. It is an authenticated/action surface that fetches a run manifest and builds the form in JavaScript. Keeping it out of the index is correct. It should be linked from the listing but should never be the SEO page.

### The static pages

The repository snapshot contains **40** `site/workflow-*.html` files (not 43 at this revision). Each sampled page has:

- a unique initial title and meta description;
- a self-referential canonical such as `https://omo.space/workflow-decodable-sentence-creator.html`;
- `index,follow`;
- server-delivered visible facts, inputs, outputs, examples, limitations, and FAQ/structured data;
- Product/Offer JSON-LD and, generally, FAQ JSON-LD.

These pages are materially richer in initial HTML than `workflow.html?slug=...`. They are not empty SEO doorway pages: they contain inspectable contract fixtures and explicit caveats. But they are not interchangeable with proven hosted output; several accurately say that a fixture is not a live customer run or that a workflow is still in review.

## 2. Duplicate-content finding

Yes, there is a real overlap risk, though it is not exact byte-for-byte duplication today. For a matching slug, the static page and the dynamic page both present the same productized object: name, promise/description, inputs, outputs, price/status, examples or media, limitations, and an “Open the workflow” path. The static page is proof-oriented and richer; the dynamic page is the purchase/run interface. Their primary intent is close enough that Google may cluster them as duplicates or near-duplicates.

The dynamic URL currently has no canonical pointing to the static page, and the static page canonicals point only to themselves. The dynamic URL is also not in the XML sitemap, while the static URLs are. That creates mixed signals rather than a defined duplicate policy. Google says it clusters substantially similar pages, chooses one representative URL, and uses canonical tags, redirects, internal links, and sitemaps as signals; canonicalization is not a guaranteed command. It also recommends linking consistently to the canonical URL.

The practical result is signal dilution and measurement ambiguity: external/internal links, impressions, and conversions can attach to two URLs; Google may choose the richer static page today, or the dynamic page after rendering, without Omo controlling the result.

## 3. Is the founder's Reddit/Skool model valid?

The analogy is directionally right but technically incomplete.

Reddit threads and Skool pages can rank because they are durable, individually addressable documents with substantial user-generated text, ongoing engagement, links, reputation, and often strong external demand. A JavaScript catalog detail page with a query parameter gets none of those signals automatically. A clean URL and a title are prerequisites, not proof of rank.

For hosted listings to become the indexable object, Omo needs:

1. A stable clean route, for example `/workflows/decodable-sentence-creator/`, with a 200 response and one listing per URL.
2. SSR or build-time prerendering of the title, description, H1, price/status, inputs, outputs, proof example, limitations, creator, and relevant structured data.
3. A self-canonical clean URL, consistent links from the homepage/catalog/category pages, and no indexable query-string duplicate.
4. A generated sitemap containing only canonical, actually publishable listings.
5. Real listing differentiation: a tested output, named reviewer where appropriate, version/date, failure/limitation data, and a clear hosted CTA. The proof must live on the listing, not only in a separate static page.
6. Marketplace signals over time: successful runs, legitimate reviews, creator identity, repeat use, links/mentions, and useful related-listing/category navigation. Do not manufacture ratings, reviews, or engagement.

Until those exist, “1000 hosted listings” means 1000 thin app-shell URLs, not 1000 Reddit-like documents.

## 4. Natural long-tail: opportunity and trap

The opportunity is real. Slugs such as “decodable sentence creator” or “phonics word list generator” are close to outcome-shaped queries. A large catalog can cover more legitimate jobs than a small hand-authored page set, and the PromptBase/Fiverr/OpenRouter evidence supports per-object discovery when each object has a real commercial/useful identity.

The trap is treating every catalog object or input value as an SEO page. “Phonics worksheet for -at,” “phonics worksheet for -an,” and similar substitutions are not separate jobs; they are parameters of one workflow. Google’s current guidance says focusing on every possible query variation to manipulate rankings can violate its scaled-content-abuse policy, and its spam policy defines the abuse as many pages made primarily for rankings rather than users. Omo's own playbook correctly says proof density per page—not pages per keyword—is the operating rule.

The safe test for a hosted listing is: would a buyer recognize a distinct job, and does the page contain distinct evidence, not merely a changed slug, keyword, or input? If not, keep the variant as an input on the parent listing.

## 5. Options

### (a) Keep the current static pages

Best short-term crawlability and proof control. They already have stable canonicals, initial HTML, schema, examples, and FAQs. The costs are 40 pages to maintain, stale facts when catalog/runtime data changes, and continued collision with the dynamic app URL. This is acceptable as a temporary bridge, not a final architecture.

### (b) Index only hosted listings

Best long-term catalog model: one object, one URL, one proof surface, scalable supply. It becomes a good choice only after clean routing, SSR/prerendering, canonical discipline, internal links, sitemap generation, and listing-level proof exist. Switching now would trade away the strongest current metadata and make the index depend on client-side rendering. It also risks publishing thin coming-soon or unproven listings.

### (c) Hybrid: top-N static proof pages plus hosted listings

Best current choice. It preserves the 12 mapped money/workflow intents and their proof standard while building the hosted listing architecture for everything else. It has a migration burden and requires a strict canonical rule, but it lets Omo learn from Search Console and paid-run data without making 40 pages or 1000 catalog records compete.

The “top 12” is a cap and a queue, not a promise to index all 12 immediately: the playbook requires live price, five real runs, inspectable output, limitations, and educator review before publication. Current blocked worksheet/story/edit pages should remain unpublished or noindex until those gates pass.

## 6. Concrete action plan

1. **Choose the canonical now.** Make `/workflows/<slug>/` the target canonical for mature hosted listings. Until that route exists, keep the relevant static page canonical and add a canonical to the dynamic shell only after the dynamic URL is redirected or explicitly treated as a non-indexable app route. Do not point two live pages at each other.

2. **Build SSR/prerendered listing pages.** Generate initial HTML from the same catalog source, including unique title/description, H1, promise, inputs/outputs, exact price or honest status, proof, limitations, creator/version/date, Product/Offer only when truthful, and links to the `noindex` run surface. Hydrate the existing interaction layer afterward.

3. **Eliminate query-string discovery as the public detail URL.** Update every internal listing link and CTA from `workflow.html?slug=X` to `/workflows/X/`. 301/308 old dynamic URLs to the clean URL once the clean page is equivalent. Preserve `run.html?slug=X` as an action URL with `noindex,follow`.

4. **Migrate the static pages by evidence, not by calendar.** For each of the 12 mapped intents, move its proof sections into the clean listing only when the hosted workflow has the same or better facts. Redirect the old `workflow-<slug>.html` to the clean page. For pages that are only fixtures, blocked, or materially editorial/comparison content, keep them separate or `noindex`; never canonicalize a weak page to a page that does not contain its claims.

5. **Regenerate the sitemap from canonical publishable records.** Include only the clean URLs that are intended for search and meet the publishability gate. Exclude query-string detail URLs, run URLs, coming-soon records, and duplicate static URLs. Add `lastmod` only when the page's substantive proof changes.

6. **Create crawlable internal linking.** Link homepage → categories → listings; add a small set of genuinely related listings based on job/category, not keyword permutations; link open-source recipe, proof artifact, and creator/profile pages where they exist. Use the canonical clean URL in every link.

7. **Measure the migration in GSC.** Inspect rendered HTML and structured data for representative clean URLs; monitor indexed/canonical-selected status, impressions, qualified visits, workflow starts, paid runs, and repeat runs separately. Compare the old static and new clean URL cohorts. Do not treat “discovered” or “indexed” as product-market validation.

## 7. Stop doing

- Stop adding static pages merely to cover keyword permutations or catalog inputs.
- Stop allowing the query-string detail shell to be an indexable competing surface without a canonical/redirect policy.
- Stop putting proof only in static pages while the hosted listing is thin; the canonical page must contain the evidence.
- Stop putting coming-soon, projected-price, fixture-only, or unverified-review listings into the index as if they were live products.
- Stop using generic catalog scale, slugs, JSON-LD, or JavaScript rendering as substitutes for useful content and real user signals.
- Stop expanding page count when qualified visits do not produce paid and repeat runs; fix the listing, proof, price, checkout, or reliability loop first.

## Sources

- [Google: JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics) — Google can render JS, but describes the crawl/render/index pipeline and recommends SSR/prerendering for speed and crawler coverage.
- [Google: canonicalization](https://developers.google.com/search/docs/crawling-indexing/canonicalization) — duplicate clustering, representative URLs, and signal consolidation.
- [Google: specifying canonicals](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls) — redirects are stronger than `rel=canonical`, sitemap inclusion is weaker, and internal links should use the canonical URL.
- [Google: sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap) — submit the URLs intended for search and prefer canonical URLs when duplicate content exists.
- [Google: spam policies](https://developers.google.com/search/docs/essentials/spam-policies) and [AI features guidance](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide) — scaled content made primarily to manipulate rankings, including excessive query variants, is not a safe growth strategy.
- Omo internal evidence: [SEO strategy](../marketing/seo-strategy.md), [AI SEO playbook](../marketing/ai-seo-playbook.md), [OpenRouter growth](openrouter-growth.md), [PromptBase growth](promptbase-growth.md), [Fiverr growth](fiverr-growth.md), and [competitor map](omo-competitors.md).

