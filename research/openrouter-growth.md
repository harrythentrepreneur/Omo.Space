# How OpenRouter grew — and what transfers to Omo

Research date: 2026-08-14. Primary sources are preferred below. `UNVERIFIED` means the reviewed public record did not support a confident claim; it does not mean the claim is false.

## Launch & origin

### What was founded, when, and by whom

OpenRouter says it was **started in early 2023**. Its 2025 financing announcement says it was founded in 2023 by **Alex Atallah and Louis Vichy**; CapitalG's 2026 announcement describes **Chris Clark, Alex Atallah, and Louis Vichy** as founders. The safest formulation is therefore: *founded in 2023 by Atallah and Vichy, with Clark described as a founder in later company/investor material*. The brief's suggested founder, **Steven Heidel, is not listed as an OpenRouter founder in any company, investor, launch, or financing source reviewed**. [OpenRouter About](https://openrouter.ai/about), [2025 financing release](https://www.globenewswire.com/news-release/2025/06/25/3105125/0/en/openrouter-raises-40-million-to-scale-up-multi-model-inference-for-enterprise.html), [CapitalG Series B post](https://www.capitalg.com/insights/Leading-OpenRouters-Series-B)

OpenRouter did not appear out of nowhere as a 100-model marketplace. The precursor was **Window**, a browser extension/JavaScript API that let a user choose the model and keep control of credentials. Atallah's launch thread on **2023-04-05** opened: **“Excited to launch an experiment today — introducing Window, a way to use your own AI models on the web.”** The next post named the category enemy: **“Current approaches all involve some kind of vendor lock-in.”** The thread said beta builds and community experiments would live in Discord. [Atallah's Window launch thread](https://x.com/alexatallah/status/1643356106670981122)

Window reached Hacker News on **2023-04-07** under the literal pitch **“Window: Use your own AI models on the web.”** It received only 6 points and no comments. That is useful negative evidence: the first public launch itself was not a breakout HN event. [HN item](https://news.ycombinator.com/item?id=35481760), [HN Algolia record](https://hn.algolia.com/api/v1/items/35481760)

The clearest early public launch-style post for OpenRouter itself is a **Show HN on 2023-11-25**, “Ranking LLMs by Usage over Time.” It explicitly said the team had been building OpenRouter since Window's April launch. The actual pitch was already a marketplace plus data product:

> “The API supports — 50+ different models … Consolidated payments for all models … Upstream latency/throughput tracking … Multiple providers per model, for redundancy.”

It also said OpenRouter supported **11 model hosts**, including its own open-sourced vLLM-based host, and would use opted-in prompt data to show which models worked best for different tasks. The sign-off was “Alex and Louis.” [Show HN](https://news.ycombinator.com/item?id=38415092), [HN Algolia record with full post text](https://hn.algolia.com/api/v1/items/38415092)

### What can and cannot be called “the launch”

- **Twitter/X:** verified for the Window precursor on 2023-04-05. I did not locate a comparable, date-stamped 2023 OpenRouter-specific launch thread. **UNVERIFIED**.
- **Hacker News:** verified Window submission on 2023-04-07 and a direct OpenRouter Show HN on 2023-11-25. Neither was viral: 6 and 3 points respectively. [Window HN](https://news.ycombinator.com/item?id=35481760), [OpenRouter Show HN](https://news.ycombinator.com/item?id=38415092)
- **Product Hunt:** no verified 2023 core-product launch was found. The current OpenRouter Product Hunt page is for **Model Fusion**, launched in 2026, not the original gateway. Treat “OpenRouter launched on Product Hunt in 2023” as **UNVERIFIED**. [Product Hunt page](https://www.producthunt.com/products/openrouter)

### The category insight

At launch, the problem was not merely “one bill for many models.” It was that model choice was becoming unstable along four axes at once: model quality, provider availability, latency, and price. Window first tested whether users wanted model control without application-level lock-in. OpenRouter then centralized access, payment, observability, and failover while publishing usage data.

That resonated specifically with developers because the replacement cost was unusually low:

1. **Existing code kept working.** OpenRouter exposes `/api/v1/chat/completions` and documents the OpenAI SDK pointed at a different `baseURL` as a “drop-in replacement.” [Quickstart](https://openrouter.ai/docs/quickstart), [OpenAI SDK guide](https://openrouter.ai/docs/community/open-ai-sdk)
2. **One integration removed repeated operational work.** The current quickstart promises hundreds of models through one endpoint, automatic fallbacks, and cost-effective routing. The 2023 Show HN already bundled 50+ models, 11 hosts, payments, and provider telemetry. [Quickstart](https://openrouter.ai/docs/quickstart), [2023 Show HN](https://news.ycombinator.com/item?id=38415092)
3. **The product made tradeoffs inspectable.** OpenRouter exposes model pricing, context, provider performance, and popularity; its router can sort by price, throughput, or latency. This turns “which model/provider?” into a runtime choice instead of a rewrite. [Models documentation](https://openrouter.ai/docs/guides/overview/models), [Provider routing](https://openrouter.ai/docs/features/provider-routing)
4. **It preserved optionality.** The early Window thread explicitly attacked vendor lock-in; OpenRouter now describes itself as eliminating lock-in while improving price and uptime. [Window thread](https://x.com/alexatallah/status/1643356106670981122), [OpenRouter About](https://openrouter.ai/about)

The often-repeated “100+ models” description is historically imprecise. The direct November 2023 launch evidence says **50+**; the platform later passed 400 and currently advertises 500+. [2023 Show HN](https://news.ycombinator.com/item?id=38415092), [OpenRouter About](https://openrouter.ai/about)

## Growth mechanics ranked

This ranking is about causal importance, not visibility today. OpenRouter does not publish a channel-attribution report, so rankings 2–6 combine dated product evidence, usage milestones, and explicit partner statements. Where causality cannot be proved, it is labeled as inference.

### 1. Near-zero migration plus a genuinely useful aggregation layer

This was the core growth engine. OpenAI compatibility reduced adoption friction to changing a base URL and model slug, while unified billing, standardized accounting, provider fallback, and price/latency routing created value after integration. Menlo says developers came for access and then used OpenRouter to compare price/performance/latency and run evaluations. [OpenAI SDK guide](https://openrouter.ai/docs/community/open-ai-sdk), [Provider routing](https://openrouter.ai/docs/features/provider-routing), [Menlo investment post](https://menlovc.com/perspective/investing-in-openrouter-the-one-api-for-all-ai/)

The mechanism compounds: every new model/provider improves selection and redundancy; every request improves public usage/performance data; that data attracts developers and gives model makers a launch/feedback channel. CapitalG calls OpenRouter's leaderboards an industry standard and says model and app developers track their positions. [CapitalG Series B post](https://www.capitalg.com/insights/Leading-OpenRouters-Series-B)

### 2. Supply breadth first, followed by demand and data

The November 2023 post launched with 50+ models and 11 hosts already integrated, rather than waiting for a large audience. That is strong evidence for **supply-first breadth**. OpenRouter's current provider onboarding is explicitly a marketplace: providers apply to “sell inference,” publish model/capability/pricing/capacity data, and are routed traffic based on uptime and performance. [2023 Show HN](https://news.ycombinator.com/item?id=38415092), [Provider integration guide](https://openrouter.ai/docs/use-cases/for-providers)

Partnerships later became distribution events. OpenRouter and OpenAI collaborated on the stealth launch of GPT-4.1 as Quasar Alpha; OpenAI said OpenRouter's developer community supplied valuable real-world feedback. The 2025 release also described 50+ providers, and the platform currently lists 80+. [2025 financing release](https://www.globenewswire.com/news-release/2025/06/25/3105125/0/en/openrouter-raises-40-million-to-scale-up-multi-model-inference-for-enterprise.html), [OpenRouter About](https://openrouter.ai/about)

**Inference:** integrating desired models early did not merely “let demand follow”; it created news, useful comparisons, and partner feedback loops that recursively improved supply.

### 3. Transparent rankings, pricing, and usage data

The first direct Show HN was a rankings/data launch, not a generic API announcement. It visualized model usage and token flows and promised task-level insights. Today each model page exposes price and provider performance, while the Models API can sort by price, throughput, latency, popularity, or recency. [2023 Show HN](https://news.ycombinator.com/item?id=38415092), [Models documentation](https://openrouter.ai/docs/guides/overview/models), [Rankings](https://openrouter.ai/rankings)

This did three jobs simultaneously: helped buyers choose, gave providers a competitive scoreboard, and generated linkable industry data. Menlo explicitly says developers come to see which models the rest of the industry uses; CapitalG says model/app developers watch their rankings. [Menlo investment post](https://menlovc.com/perspective/investing-in-openrouter-the-one-api-for-all-ai/), [CapitalG Series B post](https://www.capitalg.com/insights/Leading-OpenRouters-Series-B)

### 4. Developer community as support and product/partner feedback

The Discord was part of the product from the precursor stage: Atallah directed Window users there for beta installation and to explore each other's creations. OpenRouter now presents Discord as instant community support, and requests for missing models/providers are directed to Discord. [Window launch thread](https://x.com/alexatallah/status/1643356106670981122), [Support page](https://openrouter.ai/support), [Models documentation](https://openrouter.ai/docs/guides/overview/models)

On 2026-08-14, Discord's public invite API reported approximately **50,863 members and 6,906 online**. This is a live approximate count, not an audited user metric. [Discord invite](https://discord.com/invite/openrouter), [Discord invite API](https://discord.com/api/v10/invites/openrouter?with_counts=true&with_expiration=true)

The community was also a partner asset: OpenAI's quoted statement says OpenRouter's “diverse and active developer community” provided feedback on GPT-4.1 performance in practice. [2025 financing release](https://www.globenewswire.com/news-release/2025/06/25/3105125/0/en/openrouter-raises-40-million-to-scale-up-multi-model-inference-for-enterprise.html)

Status communication is adjacent but distinct. OpenRouter operates a public component-level status page for the API, Data API, homepage, and auth, with incident history and subscriptions. This reduces perceived intermediary risk. [Status page](https://status.openrouter.ai/)

### 5. Free access and low minimum commitment—not a proven universal signup-credit giveaway

Current official pricing offers **25+ free models**, community support, and 50 requests/day without a purchase. The FAQ says users who have purchased at least $10 in credits receive a 1,000-request/day limit for free models; otherwise it is 50/day. Paid usage has no minimum ongoing spend and is funded with prepaid credits; current terms set a $5 minimum top-up and allow auto-recharge. [Pricing](https://openrouter.ai/pricing), [FAQ](https://openrouter.ai/docs/faq), [API limits](https://openrouter.ai/docs/api_reference/limits), [Terms §4](https://openrouter.ai/terms)

I found **no official public evidence of a standing, universal cash-equivalent signup grant**, either today or at the 2023 launch. The terms only say OpenRouter *may* issue promotional/trial credits at its discretion. The growth mechanism that can be verified is free-model usage plus a small prepaid-credit commitment—not “everyone got $X free.” Any precise historical signup-credit amount is **UNVERIFIED**. [Terms §4.3](https://openrouter.ai/terms)

### 6. Ecosystem integrations and app attribution

OpenRouter works with existing SDKs and frameworks, and optional app headers put applications on OpenRouter leaderboards. That gives tool builders a distribution incentive while making the gateway easy to embed. Menlo cited native VS Code/Cline use as part of the 2024–25 hypergrowth story. [Quickstart](https://openrouter.ai/docs/quickstart), [Framework integrations](https://openrouter.ai/docs/community/frameworks), [Menlo investment post](https://menlovc.com/perspective/investing-in-openrouter-the-one-api-for-all-ai/)

### 7. SEO and indexable model inventory—useful, but not the original engine

OpenRouter has hundreds of indexable model pages containing pricing, benchmarks, context, and provider data. In a non-personalized Google spot-check on 2026-08-14, OpenRouter appeared among the first organic results for exact-intent queries such as “DeepSeek R1 API pricing,” “Kimi K2 API pricing providers,” and “Claude Sonnet API pricing providers.” [DeepSeek query](https://www.google.com/search?q=DeepSeek+R1+API+pricing&pws=0), [Kimi query](https://www.google.com/search?q=Kimi+K2+API+pricing+providers&pws=0), [Claude query](https://www.google.com/search?q=Claude+Sonnet+API+pricing+providers&pws=0)

However, the same spot-check did **not** surface OpenRouter on page one for broad “best LLM models leaderboard” or generic “Claude vs GPT API price,” “DeepSeek vs Claude,” and “Gemini vs Claude” queries. OpenRouter's strength is structured **model/provider pages and live rankings**, not a large verified library of editorial “X vs Y” pages. Search results vary by date and geography, so treat this as directional rather than audited traffic attribution. [Leaderboard query](https://www.google.com/search?q=best+LLM+models+leaderboard&pws=0), [Claude-vs-GPT query](https://www.google.com/search?q=Claude+vs+GPT+API+price&pws=0)

### 8. Launch virality and later press/funding

The early HN posts were not viral. The financing and partner story arrived after product-market pull: the 2025 announcement reported 10x annualized inference-spend growth from $10M in October 2024 to $100M+ in May 2025, and Menlo described token volume rising from roughly 10T/year to 100T/year before the Series A announcement. Funding news increased credibility and enterprise reach, but the chronology argues against it being the initial acquisition engine. [2025 financing release](https://www.globenewswire.com/news-release/2025/06/25/3105125/0/en/openrouter-raises-40-million-to-scale-up-multi-model-inference-for-enterprise.html), [Menlo investment post](https://menlovc.com/perspective/investing-in-openrouter-the-one-api-for-all-ai/)

### 9. Affiliate/referral program and paid ads

No official referral or affiliate program, payout rate, cookie window, or eligibility terms were found in OpenRouter's pricing, FAQ, terms, or indexed official pages. Third-party affiliate directories make conflicting claims and one explicitly labels terms unpublished. Therefore: **an official OpenRouter affiliate/referral program and its terms are UNVERIFIED**. Omo should not cite OpenRouter as proof of this mechanic. [Pricing](https://openrouter.ai/pricing), [FAQ](https://openrouter.ai/docs/faq), [Terms](https://openrouter.ai/terms)

Likewise, no primary evidence or channel attribution showing paid advertising as a material growth driver was found. **Paid-ad importance is UNVERIFIED and ranked last**, not asserted to be zero.

## Funding & scale

### Financing

- **Seed + Series A, announced 2025-06-25:** $40M combined, led by Andreessen Horowitz and Menlo Ventures, with Sequoia and angels participating. OpenRouter did not publicly separate the seed and Series A amounts in its release. Menlo describes the announced financing as a $40M Series A and says it had invested earlier through the Menlo/Anthropic Anthology Fund. [Company financing release](https://www.globenewswire.com/news-release/2025/06/25/3105125/0/en/openrouter-raises-40-million-to-scale-up-multi-model-inference-for-enterprise.html), [Menlo investment post](https://menlovc.com/perspective/investing-in-openrouter-the-one-api-for-all-ai/)
- **2025 valuation:** not disclosed by OpenRouter in the reviewed announcement. TechCrunch, citing PitchBook, later reported approximately **$547M post-money**; contemporaneous press often rounded this to roughly $500M. Treat it as reported, not company-confirmed. [TechCrunch](https://techcrunch.com/2026/05/26/openrouter-more-than-doubles-valuation-to-1-3b-in-a-year/)
- **Series B, announced 2026-05-28:** $113M led by CapitalG, with NVentures and several enterprise-software strategic investors plus existing a16z and Menlo. [OpenRouter announcement](https://openrouter.ai/blog/announcements/series-b/)
- **2026 valuation:** OpenRouter did not disclose it; TechCrunch reported approximately **$1.3B post-money**, citing the New York Times. Menlo also states $1.3B. [TechCrunch](https://techcrunch.com/2026/05/26/openrouter-more-than-doubles-valuation-to-1-3b-in-a-year/), [Menlo](https://menlovc.com/perspective/openrouter-now-processes-more-than-a-quadrillion-tokens-a-year/)

### Public scale markers

- At the 2025 financing announcement: **1M+ developers had used the API**, billions of requests, trillions of tokens/week, 400+ models, and 50+ providers. [Company financing release](https://www.globenewswire.com/news-release/2025/06/25/3105125/0/en/openrouter-raises-40-million-to-scale-up-multi-model-inference-for-enterprise.html)
- Menlo's roughly contemporaneous post says **2.5M+ developers** and 100T+ tokens/year. That conflicts with the company's “more than one million” language, likely because of date or metric definitions; neither source reconciles it. Do not collapse them into one precise user count. [Menlo investment post](https://menlovc.com/perspective/investing-in-openrouter-the-one-api-for-all-ai/)
- At Series B: OpenRouter said **8M+ developers**, 400+ models, and weekly volume rising from 5T to 25T tokens in six months. [OpenRouter Series B](https://openrouter.ai/blog/announcements/series-b/)
- Current About page on 2026-08-14: **10M+ global users, 200T+ monthly tokens, 80+ providers, 500+ models**. These are company-reported counters, not independently audited. [OpenRouter About](https://openrouter.ai/about)
- A public **tokens/day** figure was not found in the reviewed company sources; they disclose weekly, monthly, and annualized numbers. It would be easy to divide those values, but that would create an estimate the brief explicitly asked us not to fabricate.

The scale numbers establish that OpenRouter became very large; they do not prove which acquisition channel caused growth. The more defensible signal is the sequence: useful abstraction and supply breadth in 2023, 10x usage/inference-spend growth by 2024–25, then major financing and enterprise expansion.

## Transferable to Omo

### Where the analogy is real

- **Pay per use:** both replace another subscription with metered consumption. OpenRouter uses prepaid credits and per-token debits; Omo's top-up wallet and per-run debit are the workflow equivalent. [OpenRouter Terms §4](https://openrouter.ai/terms), [OpenRouter Pricing](https://openrouter.ai/pricing)
- **Aggregation:** one account/API hides many suppliers and normalizes billing, discovery, and fulfillment.
- **No lock-in:** buyers can switch the underlying option without rebuilding their surrounding workflow. OpenRouter proved the positioning resonates when the category changes quickly. [Window launch thread](https://x.com/alexatallah/status/1643356106670981122)
- **Marketplace flywheel:** more useful supply attracts more demand; usage data then tells suppliers and buyers what performs.
- **API-first:** a stable call boundary makes catalog expansion valuable without forcing reintegration.

### Where the analogy breaks

1. **OpenRouter's unit is relatively commodity-like inference; Omo's unit is a differentiated outcome.** OpenRouter can compare interchangeable hosts of the same model on price, latency, and uptime. Two Omo workflows with similar labels may have radically different prompts, inputs, tools, quality controls, and artifacts. Blind routing and lowest-price selection would damage trust.
2. **OpenRouter's first buyer is a developer; Omo's current wedge is a teacher/creator.** Developers understand API keys, tokens, fallbacks, and model IDs. Teachers buy “a decodable worksheet” or “a finished story video,” not infrastructure optionality. Omo's API should exist, but the early conversion surface needs outcome previews, plain-language inputs, and proof—not developer jargon.
3. **The moats differ.** OpenRouter's moat is aggregation, provider liquidity, routing data, uptime, and purchasing leverage. Omo's moat must be workflow quality, reproducible result evidence, trusted creator supply, and the `SKILL.md → hosted result` pipeline. Catalog count alone is not defensibility.
4. **Supply onboarding is harder for Omo.** A model provider can publish machine-readable price/capability/capacity fields. A workflow creator needs review criteria, representative outputs, failure boundaries, rights/safety checks, and ongoing quality monitoring.
5. **Usage leaderboards can mislead for outcomes.** “Most tokens” is useful market signal. “Most workflow runs” may reward cheap novelty rather than learner outcomes or artifact quality. Omo should rank verified usefulness, repeat purchase, completion, and refund/complaint rates—not raw volume alone.

### Seven tactics Omo should copy

1. **Make the first successful result free or nearly free, with a hard cap.** Copy the low-friction principle, not a mythical OpenRouter signup grant. Give a new teacher enough promotional wallet balance for one bounded, representative workflow; require an account, cap abuse, show the normal per-run price before execution, and expire promo credit clearly. Success metric: first-run completion → wallet top-up → second paid run. OpenRouter evidence: free models plus 50/day limits, with higher limits after $10 purchased. [Pricing](https://openrouter.ai/pricing), [API limits](https://openrouter.ai/docs/api_reference/limits)
2. **Create a drop-in “one call, one result” contract.** For developers, expose one stable Omo endpoint and a uniform result envelope across workflows. For teachers, make the UI equivalent just as simple: choose outcome, supply minimal inputs, preview price, receive artifact. The transferable insight is integration continuity, not OpenAI-shaped payloads. [OpenRouter Quickstart](https://openrouter.ai/docs/quickstart)
3. **Launch with a narrow shelf of excellent, visibly different outcomes.** OpenRouter had meaningful breadth at launch; Omo should not imitate the number. Start with 3–5 educator-reviewed workflows whose outputs are demonstrably better than generic prompting, then expand only when each addition creates a new buyer reason. Publish status as “reviewed,” “beta,” or “coming soon.”
4. **Use a Discord-first feedback loop, but keep support where teachers already are.** OpenRouter used Discord for beta distribution, peer creations, missing-model requests, support, and lab feedback. Omo can use a small creator/early-adopter Discord for rapid iteration while offering email/in-product support to teachers who will not join Discord. Create channels per workflow and log failure examples into review queues. [Window launch thread](https://x.com/alexatallah/status/1643356106670981122), [Support](https://openrouter.ai/support)
5. **Turn every workflow into an indexable evidence page.** Adapt OpenRouter's model pages into pages such as “Decodable sentence generator: examples, reading level, price, inputs, turnaround, limitations” and comparison pages such as “Omo decodable worksheet vs Diffit for one-off use.” Do not publish generic SEO prose; include real outputs, review rubric, price, and a runnable CTA. OpenRouter's model pages rank for exact pricing intent, while broad editorial comparisons are not its demonstrated strength. [Models documentation](https://openrouter.ai/docs/guides/overview/models)
6. **Build a creator affiliate/referral program only after attribution and payouts are reliable.** This is a sensible Omo-specific tactic, **not a copied verified OpenRouter mechanic**. Give creators a durable link/code, disclose payout basis and clawbacks, reward paid repeat use rather than free signups, and provide a simple earnings dashboard. Never claim OpenRouter validates the terms; its program is unverified.
7. **Publish trust infrastructure early.** Add a component-level status page, workflow-specific incident/history notes, explicit refund behavior, and visible fail-closed states. An intermediary must prove it will not charge for broken fulfillment. OpenRouter's public status and routing/fallback transparency directly reduce gateway risk. [Status page](https://status.openrouter.ai/), [Provider routing](https://openrouter.ai/docs/features/provider-routing)

For launch, use the honest message **“buy the result, not another subscription”** on Product Hunt and in a carefully targeted HN Show post only when the API and proof pages work. OpenRouter's own early HN results show that launch-platform presence is not a growth strategy by itself. Lead with a working artifact, price, and reproducible comparison—not the marketplace abstraction.

### Three tactics Omo should not copy

1. **Do not enter a commodity price war.** Omo should price against the value of a finished, reviewed result and the avoided subscription/time—not route to the cheapest creator/workflow. Quality variance is the product risk.
2. **Do not make the early experience developer-only.** Preserve the API, but optimize initial discovery and purchase for teachers/creators. “One API” is infrastructure; “one finished decodable worksheet for $X” is the sale.
3. **Do not use VC subsidy as the growth model.** Free usage should be a capped proof mechanism with measured payback, not an uncapped burn loop. OpenRouter's financing followed large organic/product usage; it should not be read as permission to buy Omo's demand.

## Sources

### Primary / first-party

- [Alex Atallah, Window launch thread, 2023-04-05](https://x.com/alexatallah/status/1643356106670981122)
- [Hacker News: Window submission, 2023-04-07](https://news.ycombinator.com/item?id=35481760)
- [HN Algolia API: Window record](https://hn.algolia.com/api/v1/items/35481760)
- [Hacker News: OpenRouter rankings Show HN, 2023-11-25](https://news.ycombinator.com/item?id=38415092)
- [HN Algolia API: full OpenRouter Show HN text](https://hn.algolia.com/api/v1/items/38415092)
- [OpenRouter About](https://openrouter.ai/about)
- [OpenRouter Quickstart](https://openrouter.ai/docs/quickstart)
- [OpenAI SDK compatibility](https://openrouter.ai/docs/community/open-ai-sdk)
- [OpenRouter Models documentation](https://openrouter.ai/docs/guides/overview/models)
- [OpenRouter provider routing](https://openrouter.ai/docs/features/provider-routing)
- [OpenRouter provider integration](https://openrouter.ai/docs/use-cases/for-providers)
- [OpenRouter Pricing](https://openrouter.ai/pricing)
- [OpenRouter FAQ](https://openrouter.ai/docs/faq)
- [OpenRouter API limits](https://openrouter.ai/docs/api_reference/limits)
- [OpenRouter Terms](https://openrouter.ai/terms)
- [OpenRouter Support](https://openrouter.ai/support)
- [OpenRouter Rankings](https://openrouter.ai/rankings)
- [OpenRouter Status](https://status.openrouter.ai/)
- [Discord invite API with approximate live counts](https://discord.com/api/v10/invites/openrouter?with_counts=true&with_expiration=true)
- [OpenRouter 2025 Seed + Series A announcement](https://www.globenewswire.com/news-release/2025/06/25/3105125/0/en/openrouter-raises-40-million-to-scale-up-multi-model-inference-for-enterprise.html)
- [OpenRouter 2026 Series B announcement](https://openrouter.ai/blog/announcements/series-b/)
- [Product Hunt: current OpenRouter Model Fusion listing](https://www.producthunt.com/products/openrouter)

### Investors / reputable secondary reporting

- [Menlo: Investing in OpenRouter](https://menlovc.com/perspective/investing-in-openrouter-the-one-api-for-all-ai/)
- [Menlo: OpenRouter processes more than a quadrillion tokens/year](https://menlovc.com/perspective/openrouter-now-processes-more-than-a-quadrillion-tokens-a-year/)
- [CapitalG: Leading OpenRouter's Series B](https://www.capitalg.com/insights/Leading-OpenRouters-Series-B)
- [TechCrunch: $113M Series B and reported $1.3B valuation](https://techcrunch.com/2026/05/26/openrouter-more-than-doubles-valuation-to-1-3b-in-a-year/)

### Explicitly unresolved

- A date-stamped 2023 OpenRouter-specific X launch post: **UNVERIFIED**. The Window precursor thread is verified.
- A 2023 core-product Product Hunt launch: **UNVERIFIED**. The current listing is a 2026 Model Fusion launch.
- A universal OpenRouter signup-credit amount at launch or today: **UNVERIFIED**. Free models and discretionary promo credits are verified.
- An official affiliate/referral program and its terms: **UNVERIFIED**.
- Paid advertising as a meaningful growth channel: **UNVERIFIED**.
- Exact day-level token volume: **not public in the reviewed sources**; only weekly, monthly, and annualized figures were found.
