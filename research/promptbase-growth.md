# PromptBase: how the prompt marketplace grew, and what it teaches Omo

Research date: 2026-08-14. Claims below distinguish first-party evidence, independent reporting, and **UNVERIFIED** claims. PromptBase changes quickly; current counts and prices are snapshots, not durable facts.

## Origin

PromptBase was founded by Ben Stokes, a British developer, as a solo/side project around the first wave of commercial generative-image tools. The date needs a careful answer: The Washington Post reported in February 2023 that 25,000 accounts had bought or sold prompts “since 2021,” while PromptBase’s own September 2024 post says it launched “2 years ago.” A later profile reports a June 2022 launch and ties it to the DALL-E 2 moment. The safest formulation is: **the product existed by 2021, with the recognizable marketplace launch likely in 2022; exact incorporation/launch date is not independently established in the primary sources reviewed.**

The founding insight was that users of DALL-E/Midjourney/early image models would pay to skip experimentation: a good prompt encoded hard-won model knowledge, style decisions, and iterations. Stokes described prompt writers as “multidisciplinary super-creators” and argued that crafting the right words was difficult; the product was a reusable template, not merely a one-line sentence. PromptBase’s current purchase guide confirms that the item is a flexible template with variables, examples, a creator guide, media, a commercial-use license, support, updates, and credits.

The early supply/demand seeding story is only partly documented. Stokes had an existing Tiny Projects/indie-builder audience, and the product arrived as DALL-E 2 and Midjourney interest was exploding. Independent reporting says the service was effectively bootstrapped and founder-led. **UNVERIFIED:** a precise “first 10 sellers,” first buyer, Reddit launch post, or Product Hunt launch tactic. The evidence supports “founder seeded a timely marketplace into an existing maker/AI-art audience,” not a precise launch playbook.

## Marketplace mechanics

### What is sold

PromptBase sells reusable prompts/templates for image, text, and video models; it also offers bundles, free prompts, creator services/jobs, and an App Builder/App Store in which creators can publish small AI applications. The current site advertises 310k+ quality-tested prompts and exposes model/category pages, profiles, trending/featured/best/new listings, apps, and a separate Agent Skills section.

The “skill files” claim is real, but the format is broader than a verified PromptBase-specific `SKILL.md` standard. PromptBase now has an Agent Skills category and a public `/agent-skills` directory with Claude Skill and ChatGPT Skill listings. Its homepage links to Agensi as a partner for “Agent Skills” and “skill.md files.” Current listings describe installable Claude/ChatGPT skills, but PromptBase’s public purchase/help pages reviewed here do not establish a universal required ZIP layout, exact `SKILL.md` schema, or whether every listing is a literal downloadable file bundle. Treat the marketplace’s skill category as verified; treat the exact file/packaging contract as **UNVERIFIED** until confirmed from seller upload documentation.

### Pricing and revenue share

Sellers set individual listing prices. Current first-party pages show ordinary prompts/skills commonly priced from roughly $2.99 to $14.99, with examples at $3.99, $4.99, $6.99, $8.99, $9.99, $11.99, and $14.99. **UNVERIFIED:** the often-repeated $1.99 minimum price rule. The Washington Post observed a $1.99 prompt in 2023, but that is evidence of a price, not a platform floor; PromptBase’s current public documentation does not substantiate a $1.99 minimum.

For ordinary marketplace sales, PromptBase takes 20% and the seller receives 80%. The seller balance is pending for 72 hours, then becomes available. Stripe payouts require an account at least 30 days old and generally a $30 available balance; sellers can use weekly or monthly schedules, while Zoneless supports daily USDC payouts with no minimum. An early Stripe payout costs $3.99 and takes seven days. Since June 2025, seller-referred sales can be 0% platform fee (subject to the referral rules; the marketplace fee remains 20%). Thus “80/20” is correct for marketplace-originated prompt sales, not every channel or every PromptBase product.

PromptBase also introduced an optional Select subscription in February 2026: buyers pay $14/month annual-plan equivalent or $19/month monthly for 10 downloads/month, while creators receive $1 per Select download. This means the current platform is no longer purely per-item, even though individual listings remain available at seller-set prices.

### Approval, quality, reviews, and refunds

Listings are curated. PromptBase says every prompt is tested before going live; its guidelines describe checks for use case, consistency, output quality, bad test generations, excessive simplicity, duplication/similarity, model-rule violations, and more. New submissions require structured example prompts/examples, and free listings go through the same review process. Reviews and ratings are public and affect discovery.

The refund promise is unusually concrete: PromptBase’s purchase guide says a buyer gets a 100% refund if the prompt does not work as advertised, with the request requiring the listing name, issue, and example outputs. The support page says requests must be made within 24 hours and are processed in 1–3 business days; the purchase guide says within 24 hours, “within 24 hours” processing. The slight timing inconsistency should be treated as a documentation mismatch, but the core rule is clear: refund for failure to work as advertised, not a no-questions-asked change-of-mind policy.

### Discovery and SEO

PromptBase has built a large indexable surface: individual `/prompt/...` and `/skill/...` pages, creator profiles/storefronts, model/category pages, bundles, free pages, best/trending/new pages, and a sitemap/directory. Its changelog records 265 category pages plus a prompt directory in June 2023, search suggestions, model filters, freshness, ratings, sales, and rank changes. It also explicitly says sales have an order-of-magnitude more impact on search position than free-prompt downloads, while reviews, freshness, and profile rank influence exposure.

This is strong evidence for a per-listing discovery engine. **UNVERIFIED:** the specific claim that PromptBase systematically ranks for Google queries such as “best X prompt,” or that SEO—not internal marketplace browsing/social—is the dominant acquisition channel. The page architecture is SEO-compatible; public analytics proving search share are not available.

## Growth

The documented loop is:

1. Model waves create a new, urgent need (DALL-E/Midjourney, then GPT-4, Stable Diffusion, video models, and now agent skills).
2. Sellers submit tested, visual, reusable recipes; approval and examples create trust.
3. Each listing, profile, category, model page, bundle, review, and free sample becomes a discovery surface.
4. Sales/reviews improve ranking; free prompts generate downloads, reviews, profile traffic, and—when used in PromptBase apps—usage revenue.
5. Bundles, cart discounts, app generation, creator referrals, communities, and Select add repeat and cross-sell mechanics.

PromptBase’s own history shows deliberate product-led growth: free listings (up to 10% of a seller’s inventory) were added as a trust/acquisition tool; bundles reward inventory depth and sales milestones; the App Builder monetizes prompt use; referral links give sellers a reason to bring their own audience; and the current homepage foregrounds featured, trending, best, free, newest, model, and skill collections.

Reported scale:

- Current first-party homepage snapshot: **310k+ prompts**; Select page: **250k+ Select prompts**; Agent Skills page title: **4,400+ Agent Skills**.
- February 2023 Washington Post reporting: **25,000 accounts** had bought or sold prompts since 2021 and roughly **700 prompt engineers** were selling by commission.
- A June 2025 Guardian report, reproduced by secondary outlets, attributes to Stokes approximately **20,000 sellers**, thousands of monthly sales, and **seven figures paid to sellers since 2022**. The original Guardian page was not retrievable in this research pass, so treat these figures as reported-but-not-fully-verified.
- A 2026 Korean analysis claims 450k users, 20k sellers, and 270k prompts three years after launch. Because it is secondary and the counts conflict with the current first-party snapshot, mark these numbers **UNVERIFIED** rather than using them as facts.

No reliable public GMV, revenue, profit, or cohort-retention disclosure was found. Do not repeat “$X revenue” claims without a direct source.

## Skill-files angle

PromptBase added the Agent Skills category on **May 5, 2026**, according to its changelog. The current `/agent-skills` page says “4400+ Agent Skills” and segments them by runtime (Claude Skill, ChatGPT Skill, etc.). It displays the same marketplace grammar as prompts: seller pages, examples/ratings, free items, featured/trending/best sections, discounts, Select badges, and prices.

Observed current prices on the category page include free, $3.99, $4.99, $5.99, $6.99, $7.99, $8.99, $9.99, $11.99, and $14.99, including a discounted $14.99 item at $11.24. These are observed listing prices, not a platform price rule. **UNVERIFIED:** PromptBase’s treatment of LoRAs or embeddings as a first-class current category; the public marketplace and knowledge-base pages reviewed show prompts, apps, and skills, but no authoritative LoRA/embedding seller documentation.

The fit is strategically important for Omo. A skill file is a downloadable recipe with more durable structure than a one-shot prompt: trigger/description, workflow instructions, variables, examples, and optionally scripts/references/assets. PromptBase validates the economic proposition that buyers will pay for reusable AI procedures, but its current public evidence does not yet prove that buyers pay $29–$400 for skills. Most visible PromptBase skill prices are low-ticket, closer to impulse digital goods. Omo can use the same download door while pricing premium files against demonstrated teacher outcomes, proof runs, update commitments, and commercial value.

## Lessons for Omo

### What PromptBase validates

Yes: PromptBase is credible evidence that a subset of people will pay for AI “recipes,” especially when the recipe is adaptable, visually demonstrated, tested, searchable, and backed by a refund policy. It does not prove that any arbitrary prompt has value, that high prices work, or that a recipe remains valuable after the underlying model changes.

For Omo, the strongest analogy is not “sell text.” It is “sell compressed, proven know-how.” A teacher may pay for a SKILL.md because it saves repeated planning, editing, and quality-control time—and because Omo can show the hosted output. That supports testing $29–$400 download doors, but only as tiered, evidence-backed products: $29–$49 for a narrow reusable skill, $99–$199 for a richer classroom workflow, and $299–$400 only where the file includes substantial assets, update/support rights, and repeated proof of outcome. Those price bands are an Omo hypothesis, not PromptBase evidence.

### Copy these tactics

1. Give every workflow a durable, indexable page targeting a concrete job (“decodable passage generator for Grade 1,” not “AI skill”), with examples, inputs, model/runtime, creator proof, price, and FAQ.
2. Keep seller-set pricing but add a minimum viable price floor or quality gate so creators do not race to zero; use free samples selectively as a lead and trust mechanism.
3. Operate a real approval queue: run the workflow, inspect outputs, check safety/IP/prompt injection, require examples, and reject thin or duplicative submissions.
4. Build category, model/runtime, best-seller, trending, newest, and “best for [teacher job]” pages; let reviews, successful runs, freshness, and repeat purchases feed ranking.
5. Make “bad output” refunds operational: require the input/output evidence, auto-refund failed hosted runs, and use failure data to demote or pause the listing.
6. Give creators a reason to distribute: referral links, named proof pages, bundles, and a transparent 80/20-style baseline, while preserving better economics for creator-sourced demand.

### Do not copy these tactics blindly

- Do not make the core product a commodity prompt/file detached from the result. PromptBase’s low-ticket recipe market is vulnerable to copying and model updates; Omo’s hosted execution and evidence should be the moat.
- Do not require buyers to run everything themselves. Teachers often buy to remove setup and troubleshooting; a download-only door should be an option, not the whole product.
- Do not let platform/model churn define the catalog. Build model-agnostic workflow contracts, versioned skills, migration notes, and hosted fallbacks so a model update does not erase the buyer’s investment.

The central Omo position: PromptBase shows that “someone else already figured out the recipe” can be a paid unit. Omo should sell the recipe and the finished classroom result together, then learn whether proof, reliability, and teacher-specific value move the unit from PromptBase-like $5–$15 impulse pricing toward $29–$400 professional pricing.

## Sources

- [PromptBase homepage](https://promptbase.com/) — current 310k+ prompt claim, marketplace surfaces, model/category navigation, and Agent Skills partner link.
- [PromptBase Agent Skills directory](https://promptbase.com/agent-skills) — current 4,400+ skill count, runtimes, visible prices, free/featured/trending/best sections.
- [PromptBase changelog](https://promptbase.com/changelog) — May 5, 2026 Agent Skills category launch; search/ranking, category-page, free-prompt, app, bundle, and payout history.
- [Prompt purchases guide](https://promptbase.com/knowledge-base/prompt-purchases) — purchase contents, testing, reviews, and 100% money-back guarantee.
- [PromptBase prompt guidelines](https://promptbase.com/prompt-guidelines) — review criteria, test generations, quality, duplication, and model-rule screening.
- [PromptBase payouts guide](https://promptbase.com/knowledge-base/payouts) — 20% fee, 80% pending balance, 72-hour hold, Stripe/Zoneless schedules and thresholds.
- [PromptBase support](https://promptbase.com/support) — refund window/process and revenue split summary.
- [List Free Prompts Update](https://promptbase.com/blog/free-prompts-update) — up to 10% free inventory, same review process, free prompts as trust/discovery, usage revenue, and search-weight explanation.
- [Prompt Submission Updates](https://promptbase.com/blog/prompt-submission-updates) — structured examples requirement and app conversion.
- [Prompt Bundles](https://promptbase.com/blog/bundles) and [Bundle Updates](https://promptbase.com/blog/bundle-updates) — sales-gated bundles, discounts, cart mechanics.
- [Sell With 0% Fees](https://promptbase.com/blog/zero-fees) — seller referral economics introduced in 2025.
- [PromptBase Select for Creators](https://promptbase.com/blog/promptbase-select-creators) and [PromptBase Select](https://promptbase.com/blog/promptbase-select) — optional subscription and creator $1/download economics.
- [The Washington Post, “Prompt engineers can make ChatGPT and Bing AI do what you want”](https://www.washingtonpost.com/technology/2023/02/25/prompt-engineers-techs-next-big-job/) — Ben Stokes, since-2021 account count, $1.99 observed listing, and roughly 700 commission sellers as of February 2023.
- [DeepLearning.AI, “Where to Buy DALL-E, Midjourney, and Stable Diffusion Inputs”](https://www.deeplearning.ai/the-batch/prompting-dall-e-for-fun-and-profit) — reported Stokes description of testing uploads through target-model runs and reverse-image checks; page was 403 in this pass, so use as a source lead and verify independently before relying on details.
- [Fast Company, “The wild world of PromptBase”](https://www.fastcompany.com/90825418/promptbase-generative-ai-prompt-marketplace) — independent early-market context.
- [Secondary 2026 Korean profile/analysis](https://itgit.co.kr/promptbase-solo-developer-ai-prompt-marketplace-analysis/) — June 2022 and later scale claims; included as a lead, with its 450k/20k/270k figures marked **UNVERIFIED**.
- [Secondary report reproducing the Guardian claim](https://www.suarasakti.com/will-ai-wipe-out-the-first-rung-of-the-career-ladder-20106.html) — 20k sellers, thousands of monthly sales, and seven-figure seller payouts attributed to Stokes; original article not retrieved here, so **reported/unverified**.

