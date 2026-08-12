# Omo listing honesty audit

Audited 2026-08-13 against the repository, not storefront copy. The storefront
has **24 listings total**: 7 in `site/ig-workflows.js` and 17 in
`site/ig-more.js` (the latter does not contain 24).

Definitions used below:

- **Server-priced checkout:** the slug and price exist in `SERVER_CATALOG`, so
  `/api/checkout` can create a Stripe Checkout Session. This is not the same as
  fulfillment: the current webhook records a purchase but no ownership or file
  delivery endpoint exists.
- **Runnable:** the listing has a reviewed hosted container, a registered Modal
  endpoint, a run manifest, and a catalog route that dispatches to it. A generic
  Worker LLM approximation does not qualify as the marketed workflow.
- **Download:** a matching workflow `SKILL.md` exists in the repository. This
  does not mean a buyer can receive it after payment; that delivery path is
  currently absent.

**Buyable now: 0/24.** All 24 have server-priced checkout configuration, but
production is fail-closed because `public.purchases` is absent; even after that
migration, no paid download-delivery path exists. The table's Checkout column
therefore reports configuration coverage, not honest end-to-end buyability.

| Listing (slug) | Checkout config | Runnable | `SKILL.md` | Honest treatment now |
|---|---:|---:|---:|---|
| Arcads Node UGC Builder (`arcads-node-ugc-builder`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Product Link -> Meta UGC Ad (`product-link-to-meta-ugc-ad`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| One-Photo Creative Factory (`one-photo-ecom-creative-factory`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Shopify Pics -> Descriptions (Bulk) (`shopify-pics-to-description-bulk`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Cinematic Product Ad (`gpt-image-seedance-product-ad`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Consistent Character UGC System (`consistent-character-ugc`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Realistic AI UGC Character (`realistic-ugc-character-4step`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Prompt-to-UGC Ad (`prompt-to-ugc-ad-maxfusion-seedance-2-0`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Cinematic AI UGC Scene Builder (`cinematic-ai-ugc-scene-builder`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| AI UGC Ad Prompt + Guide (`ai-ugc-ad-prompt-guide`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Product Image -> Cinematic Ad (`product-image-cinematic-ad-seedance-2-0`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Claude SEO Skill (`claude-seo-skill-replaces-2k-mo-agency`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Shopify Agentic Storefronts + AI SEO (`shopify-agentic-storefronts-ai-seo-playbook`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Shopify AI Stack (`shopify-ai-stack-rebuy-klaviyo-ai-tidio`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Shopify Agentic Plan Sellers Setup (`shopify-agentic-plan-sellers-setup`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| AI Brand Commercial Production (`ai-brand-commercial-production-seedance-2-0-k`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| AI UGC Tutorial, German (`ai-ugc-tutorial-german-comment-to-get`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| AI UGC Creator Guide (`ai-ugc-creator-guide-fully-ai-generated-ads`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Batch Content Repurposing (`batch-content-repurposing-system-transcripts-`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Kling AI + Higgsfield Viral Video (`kling-ai-higgsfield-viral-video-workflow`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| AI-Readable Product Page Optimization (`ai-readable-product-page-optimization`) | Yes | No | No | Hide until an artifact exists; then label Run coming soon |
| Japanese Style Story Video (`japanese-style-story-video`) | Yes | No* | Yes | Keep only as a clearly limited prototype; hide Buy until delivery exists |
| Woven Relationship Book Maker (`woven-relationship-book-maker`) | Yes | Yes | Yes | Keep Run; hide Buy until verified download delivery exists |
| Facebook Ads Copywriter (`facebook-ads-copywriter`) | Yes | Yes | Yes | Keep Run; hide Buy until verified download delivery exists |

\* Japanese Style Story Video has a container and a deliberately pinned sample
milestone, but the current hosting runbook says it remains fail-closed on
provider, artifact, and cost gates. It is not a generally runnable version of
the listing's arbitrary-audio promise.

## Recommendation

Do not treat successful Checkout Session creation as proof that a product can
be delivered. Keep the two proven hosted run listings, describe the Japanese
prototype's sample-only limit, and hide the remaining 21 listings until a real
artifact exists. Across all 24, hide or disable **Buy** until a signed purchase
can be exchanged for the promised `SKILL.md`; merely recording a `purchases`
row is not fulfillment.
