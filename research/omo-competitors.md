# Omo's most similar competitors

**Research cut:** 2026-08-14  
**Question:** Which products are closest to Omo's specific model: a marketplace of proven AI workflows, hosted behind a stable call boundary, bought per result without a required subscription, with creator economics and a download door?  
**Method:** Existing Omo research was reviewed first. Fresh checks then prioritized official pricing, documentation, marketplace, creator, and publishing pages. Prices are public list prices observed on 2026-08-14. **UNVERIFIED** means an official reachable source did not expose the requested fact. Derived arithmetic is labeled **DERIVED**, not presented as a vendor quote.

## Executive answer

The three closest competitors are:

1. **Relevance AI** — the closest overall business-model analog. It already has a real paid third-party agent marketplace, creator-set one-time prices, Stripe payouts with currently 0% Relevance take rate, hosted agent execution, and editable cloned agents. Its decisive differences from Omo are subscription/action billing for execution, project-level lock-in, no general file-download door, and a builder program that is currently closed to new applicants.
2. **Gumloop** — the closest hosted-workflow product analog. Community creators publish outcome-oriented agents and workflows that run on Gumloop, and execution is metered in credits. But templates are free acquisition assets, creator economics are subscription affiliate commissions rather than per-listing or per-run royalties, and the minimum paid plan is subscription-first.
3. **Poe** — the closest usage-based creator-economy analog. Millions of user-created bots run on Poe; eligible creators set a per-message USD earning amount, users spend points, and Poe pays via Stripe. But the product boundary is normally a message/conversation rather than a tested finished workflow result, and bots are not downloadable portable artifacts.

The strongest overlooked structural analog is **SingularityNET**: third-party AI services expose typed inputs/outputs, charge per call, and run through a marketplace. It ranks below the top three because it is chiefly an AI-service/API and web3 infrastructure market, not a polished workflow-result storefront, and providers—not the marketplace—operate the service endpoints.

The plain competitive risk is **Relevance AI**. It could add per-run checkout and a portable export format faster than any other candidate because it already has paid listings, creator Stripe accounts, hosted agents, an execution meter, reviews/clones, and a marketplace. Nothing technical prevents it; what slows it is strategic conflict with its subscription/action revenue, project licensing, enterprise positioning, and closed creator program.

## 1. Existing-map review

### What the August 8 map got right

- True creator commerce and hosted execution are usually separated. PromptBase sells files but does not host their execution; Gumloop and most automation galleries host runs but distribute templates free; Poe pays for usage but does not transfer a portable bot artifact.
- Gumloop and Relevance AI are the nearest hosted “clone and run” experiences, while Poe has the clearest usage-based bot creator economy.
- n8n is the workflow-supply heavyweight and strongest portability benchmark; Zapier and Make templates mainly acquire subscribers rather than pay workflow authors.
- The market gap is the **complete loop**: try the exact workflow live, buy a bounded result, keep running it through one API, download the tested artifact, and pay its creator transparently.

### Materially stale or incomplete points

1. **Relevance AI was understated.** The prior map said “no creator payout.” Current official documentation says verified Relevance Builders may set listing prices up to $1,000, connect Stripe, and currently keep **100% of the listing price minus Stripe processing fees**. Paid purchases can be cloned, edited, and refunded within seven days. The builder program is currently not accepting new applications. This changes Relevance from “free clone gallery” to the closest overall Omo analog. [Marketplace](https://relevanceai.com/docs/get-started/marketplace/introduction) · [builder payouts](https://relevanceai.com/docs/get-started/marketplace/relevance-builders/getting-paid) · [submissions](https://relevanceai.com/docs/get-started/marketplace/relevance-builders/submit-agents)
2. **Dify advanced materially in March 2026.** Its Creator Center and Template Marketplace now let creators publish workflows, users one-click adopt them, and users download templates; creators can attach PartnerStack affiliate links for recurring Dify subscription commission. This improves Dify's marketplace and portability score, although it still lacks per-template or per-run royalties. [Dify announcement](https://dify.ai/blog/dify-creator-center-template-marketplace-share-your-workflows) · [marketplace example with Download](https://marketplace.dify.ai/template/ariefjuharza/Dify%20x%20EdgeOne%20AI%20Course%20Support%20Assistant?creationType=templates&language=en-US&templateId=0601d7a3-a6a4-41ec-961d-5a35f62878b5&theme=light)
3. **n8n supply grew.** The official catalog showed **11,490 templates** on August 14 versus 11,190 in the August 8 map. Its current pricing also explicitly bills complete workflow executions, not steps: €20/month annually for 2,500 hosted executions and €50/month annually for 10,000. [templates](https://n8n.io/workflows/) · [pricing](https://n8n.io/pricing/)
4. **Gumloop pricing and portability advanced.** Its current public paid plan starts at **$37/month**, includes 20,000 credits, and lists an **8% orchestration fee**. Official docs price overage at **$0.007/credit**, a workflow base run at one credit, and standard/advanced/expert AI nodes at 2/20/30 credits. Community authors can now publish through an official review flow, and Pro/Enterprise users can sync portable Markdown skills with GitHub. This is meaningful no-lock-in progress, although Gumloop still does not sell templates or portable purchased workflows. [pricing](https://www.gumloop.com/pricing) · [credit documentation](https://docs.gumloop.com/core-concepts/credits) · [community publishing](https://www.gumloop.com/blog/announcing-community-templates) · [GitHub skill sync](https://www.gumloop.com/blog/sync-skills-between-github-and-gumloop)
5. **Agent.ai is now subscription-priced, not pay-per-run commerce.** Marketplace agents remain free; individual Premium agents cost $10/month and Pro costs $25/month. Its internal credits have no monetary value and typically one agent run costs one credit. [pricing announcement](https://blog.agent.ai/agent.ai-is-introducing-platform-based-pricing-heres-whats-staying-free) · [credit docs](https://docs.agent.ai/marketplace-credits)
6. **SmythOS's “marketplace” is still future tense on its own pricing page.** It has public/cloneable templates, hosted deployment, API endpoints, export/local deployment, and metered model usage, but says it plans to launch an agent marketplace in the future. Treat it as a platform/gallery, not a functioning two-sided cash marketplace. [pricing](https://smythos.com/pricing/) · [templates](https://smythos.com/docs/agent-templates/overview/)

The Education and category-expansion work remains strategically useful rather than directly competitive. It validates Omo's result-level wedge: teacher tools sell subscriptions for quizzes, leveled passages, worksheets, and lesson packs, while Omo can meter those exact bounded outputs. The strongest next horizontal analog is still e-commerce, where existing vendors already charge per product/image/result; this supports Omo's “buy the result” framing but those vertical SaaS products are substitutes, not marketplace peers.

## 2. Candidate matrix — all investigated

“Marketplace” below means actual third-party supply, not merely a first-party template gallery. “Hosted” means the buyer can execute on the vendor's service; it does not imply the vendor itself operates every underlying endpoint.

| Candidate | Current pricing / unit | Hosted runs? | Third-party supply? | Creator / affiliate economics | Primary buyer and public traction | Bottom line vs Omo |
|---|---|---|---|---|---|---|
| **Relevance AI** | Free: 200 Actions/mo + $2 one-time vendor credits. Pro: $19/mo annual or $29 monthly, 2,500 Actions/mo. Official top-up sources conflict: the live pricing page says $40/1,000 Actions, while docs say $80/1,000; both say $20/10,000 Vendor Credits. Paid listings are separate one-time purchases; a live SEO agent is $33.33. | Yes: chat, scheduled tasks, tools/workforces, webhooks/API-like integrations. | **Yes, paid and free**, but curated; 85 creators shown publicly. | Creator chooses price up to $1,000 and currently keeps 100% minus Stripe fees; affiliate program also exists. New builder applications currently closed. | GTM operators, agencies and teams. Public marketplace shows 85 creators; Viola shows 2,140 clones; top builders show 93/75/42 templates. | **Closest overall.** Has creator commerce + hosted use, but execution remains subscription/action-first and purchases are project-tied. |
| **Gumloop** | Pro starts $37/mo, 20k credits, 8% orchestration fee. Overage $0.007/credit; workflow base 1 credit; standard/advanced/expert AI nodes 2/20/30 credits. | Yes: workflows and agents; share/setup links; up to 5 concurrent workflow runs on Pro. | **Yes, free community templates**; 185+ examples. | Creator program pays 20% of a new customer's first-year subscription revenue; no template sale or per-run royalty found. | Business operators and automation teams. 185+ examples; public template pages show leading examples around 9k–11k views. Site banner says $50M Series B. | Closest hosted workflow UX; not true creator goods commerce and not pay-as-you-go without a plan. |
| **Poe** | Free for most usage; subscriptions start $4.99/mo. Add-on points start at $30/1M points (=$0.00003/point **DERIVED**). Each bot exposes a fixed or variable point cost. | Yes, including prompt bots, server bots and API access. | **Yes**; official page says “millions of user-created bots.” | Eligible creators set a USD price per message; each answered message earns that amount. Official example uses $3/1,000 messages; maximum is $10,000/1,000. Stripe payout threshold $10; 23 eligible countries. | Broad consumers and bot developers; millions of user-created bots, exact active/monetized count **UNVERIFIED**. | Best usage-payout loop and distribution; weak finished-result boundary and no artifact download. |
| **SingularityNET AI Marketplace** | Provider-set **price per call**, usually after free demo calls, paid in ASI/FET; live service-specific prices were not reliably exposed signed-out, so exact examples are **UNVERIFIED**. | Yes from the marketplace/SDK, but the provider hosts an SSL endpoint behind the SNET daemon. | **Yes**; developers publish services and charge per use. | Direct usage payment to service providers through marketplace payment channels; universal platform take rate **UNVERIFIED**. | AI developers/integrators; current service count and call volume **UNVERIFIED**. | Structurally close per-call API market; too infra/web3-centric and not a portable workflow-result store. |
| **n8n** | Hosted Starter €20/mo annual for 2,500 complete executions; Pro €50/mo annual for 10,000. Community Edition free/self-hosted. | Yes on Cloud; self-host option. Stable webhook/API/workflow boundary. | **Yes, free templates**; 11,490 current templates and verified creators. | 30% of referred n8n Cloud net revenue for 12 months; €100 payout threshold. No per-template or per-run royalty found. | Technical automation teams. 11,490 templates; official pricing page links a GitHub count of 200,550 and says community forum has 45,000 members. | Strongest supply/portability incumbent; builder-first, subscription-first, and templates are acquisition rather than paid results. |
| **Dify** | Sandbox free with 200 message credits. Professional $590/workspace/year with 5,000 message credits/mo; Team $1,590/year with 10,000/mo. Community self-hosted edition free. | Yes: preview, cloud publish, triggers and API access; self-hosted runtime. | **Yes, free creator templates/plugins** with one-click adoption and download. | Optional affiliate links earn recurring subscription commission; rate not exposed on the announcement page. No listing/per-run royalty found. | AI app developers and teams. Public total **UNVERIFIED**; one June 2026 course-support template showed 195 uses. | Best emerging download + hosted + creator-template combination, but commerce is affiliate/subscription based. |
| **PromptBase** | One-time creator-set prices for prompts and `SKILL.md` files; exact representative live skill prices were client-rendered and **UNVERIFIED**. | No production hosted run for the sold skill. | **Yes, paid** prompts and agent skills. | 80% creator / 20% marketplace; 100% creator on own-link sales. Stripe $30 scheduled threshold or daily USDC with no minimum. | Prompt/skill buyers and creators; exact current catalog/GMV **UNVERIFIED**. | Closest artifact-sale competitor and already speaks `SKILL.md`; lacks Omo's run/result layer. |
| **Replicate** | Pure pay-for-use. Examples: FLUX 1.1 Pro $0.04/image, FLUX dev $0.025/image, CPU-small $0.000025/sec, H100 $0.001525/sec. | **Yes**, demos and prediction APIs with a stable schema. | Community contributes thousands of public models; proprietary vendors also publish. This is model supply, not workflow supply. | No universal creator royalty for community models found; economics center on hosted inference/model providers. | Developers and media-generation buyers. Popular public models show 51.5M and 29.9M runs; current total models **UNVERIFIED**. | Strongest cents-per-result runtime analog, but sells model predictions rather than expert workflows and has no clear creator workflow royalty. |
| **OpenAI GPT Store** | GPT use is bundled into ChatGPT plan access; no per-GPT or per-run purchase. | Yes, inside ChatGPT. | **Yes**, public/community GPTs. | Usage-based earnings remain limited to a handful of builders; universal rate/open enrollment **UNVERIFIED**. | Global ChatGPT users. More than 3M GPTs had been created by Jan 2024; current store count **UNVERIFIED**. | Unmatched distribution/brand; weak pricing transparency, no portable artifact and no stable per-result call purchase. |
| **Zapier** | Free: 100 tasks/mo. Professional from $19.99/mo; pay-per-task overage on paid plans. Zapier Agents: free 400 activities/mo or $33.33/mo annual for 1,500. AI steps now cost 1x/3x/5x tasks by model tier. | Yes. | Third-party integrations; workflow templates are largely free recipes, not creator goods. | Partner programs, but no template-author royalty found. | SMB/enterprise automation. Existing official map claim: 9,000+ apps and 3M+ businesses. | Mature distribution/integrations; step billing and templates are far from a result marketplace. |
| **Make** | Free 1,000 credits/mo; Core $12/mo, Pro $21, Teams $38 at 10k credits. Most operations cost one credit; AI may be dynamic. | Yes. | Community/shared templates, but no paid workflow market verified. | Affiliate program (prior map: 35% referral for 12 months); no template/run royalty found. | Visual automation users; 3,000+ apps on current pricing page, prior official template result said 7,000+ templates. | Metered hosted workflows, but subscription/operations-first and not result commerce. |
| **Copy.ai** | Chat $29/mo monthly or $24/mo annual; workflow plan jumps to Growth $1,000/mo annual with 20k workflow credits; Expansion $2,000/45k; Scale $3,000/75k. Per-workflow credit cost varies and is visible only after a run. | Yes, including API and bulk runs on enterprise. | No true third-party marketplace verified; template library is product supply. | No creator payout found. | Enterprise GTM teams; official page claims 17M users at leading companies. | Finished GTM workflows but first-party, high-contract, subscription/enterprise platform. |
| **Lindy** | Plus $29.99/user/mo for 3k credits; Pro $99.99/15k; Max $199.99/35k. Jobs range 2–250, 250–1,000 or 1,000–2,500 credits. | Yes, persistent agents, scheduled routines, computer use and integrations. | Skills page is a first-party/curated examples catalog; open cash marketplace not verified. | Creator terms/payout for skill authors **UNVERIFIED**; partners link exists. | Teams wanting an AI teammate; official page says “thousands of teams,” exact number **UNVERIFIED**. | Strong outcome framing, but a subscription teammate with a skills gallery rather than result commerce. |
| **SmythOS** | Public $0 with $5 model credits/mo and 2.5x model cost; Builder $39/seat/mo with $20 credits and 100 fast API calls/day; higher tiers $399+. Built-in model usage billed separately; BYOM available. | Yes: Agent Cloud, API, MCP, chat; local/private options. | Public/community templates exist, but official page says an agent marketplace is planned for the future. | No current agent-sale or per-run creator payout verified. | Agent builders and enterprises. Traction counts **UNVERIFIED**. | Very strong deploy/export/no-lock-in ethos; presently a platform/gallery, not a true marketplace. |
| **Stack AI** | Free $0 with 500 runs/mo; Enterprise custom. | Yes, API and published interfaces; enterprise cloud/VPC/on-prem. | Template gallery appears first-party/curated; no third-party seller market verified. | No creator economics found. | Regulated/enterprise teams. Exact customer/run count **UNVERIFIED**. | Has bounded workflows and runs, but enterprise platform economics and no marketplace. |
| **Agent.ai** | Marketplace agents remain free. Premium agent subscriptions $10/agent/mo; Pro $25/mo. Internal credits cannot be bought/sold and typically one run costs one credit. | Yes. | Marketplace builders and agents, though current paid Premium supply appears platform-selected. | No per-run/listing creator payout verified. | Professionals exploring agents; exact current agent/user count **UNVERIFIED**. | Marketplace UX but subscription monetization, non-monetary credits and no portable artifact. |

## 3. Similarity ranking

### Scoring rubric

Each dimension is scored independently from 0 to 10:

- **A — pay per use / credits:** 10 is direct, optional per-run payment with no subscription; subscription-included credits score materially lower.
- **B — finished result:** 10 is a bounded buyer-facing outcome; infra, visual builders and generic chat score lower.
- **C — true marketplace:** 10 is open third-party supply with creator commerce; free community galleries or closed curation score lower.
- **D — hosted stable call:** 10 is vendor-hosted execution behind a repeatable input/output or API boundary.
- **E — no lock-in:** 10 is downloadable/exportable and runnable elsewhere; editable only inside the vendor is partial credit.

Scores measure **model similarity, not company quality, traction or threat**.

| Rank | Candidate | A | B | C | D | E | Total / 50 | Why it lands here |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | **Relevance AI** | 6 | 8 | 9 | 9 | 5 | **37** | Paid creator marketplace plus hosted outcome agents; execution needs platform credits/subscription and artifacts stay project-bound. |
| 2 | **Gumloop** | 6 | 8 | 6 | 9 | 6 | **35** | Very close outcome/workflow/runtime experience plus portable Markdown skills; free templates and affiliate-only creator economics prevent a higher marketplace score. |
| 3 | **Poe** | 9 | 5 | 10 | 9 | 1 | **34** | Strongest per-use creator payouts and huge third-party bot supply; mostly message/chat outcomes and hard platform lock-in. |
| 4 | **SingularityNET** | 10 | 3 | 9 | 7 | 4 | **33** | Direct per-call third-party service market with typed APIs; provider hosting, web3 payment and infrastructure framing reduce buyer-result fit. |
| 5 | **Dify** | 3 | 6 | 7 | 8 | 9 | **33** | New creator template market, cloud API and download/self-hosting; still subscription credits + affiliate monetization rather than commerce per result. |
| 6 | **n8n** | 4 | 5 | 7 | 8 | 9 | **33** | Massive third-party workflow supply and excellent portability; subscription executions and free templates, with a builder-first UX. |
| 7 | **PromptBase** | 2 | 6 | 10 | 1 | 10 | **29** | True paid `SKILL.md` market and perfect file portability; no hosted result execution and purchases are one-time assets. |
| 8 | **Replicate** | 10 | 3 | 3 | 10 | 2 | **28** | Prediction APIs match metering/runtime exactly, but the sold unit is a model rather than a proven end-to-end workflow; community model publishing is not creator workflow commerce. |

Outside the top eight: OpenAI GPT Store 27/50 (3/5/9/9/1); Agent.ai 27 (3/7/7/8/2); SmythOS 27 (4/6/3/7/7); Make 25 (4/4/5/8/4); Zapier 24 (4/4/4/9/3); Stack AI 21 (3/6/1/8/3); Lindy 20 (4/7/1/7/1); Copy.ai 18 (3/6/1/7/1).

## 4. Top three detailed profiles

### 1. Relevance AI — closest overall

#### Exact pricing and unit economics

- Free: $0, 200 Actions/month, $2 one-time Vendor Credits.
- Pro: **$19/month billed annually or $29 monthly**, 2,500 Actions/month and $20/month of Vendor Credits according to current pricing docs.
- Team: **$234/month annual or $349 monthly**, 7,000 Actions/month and $70/month Vendor Credits.
- Official sources conflict on Action top-ups: the live pricing page says **$40 per 1,000 Actions** (= $0.04/action **DERIVED**), while current documentation says **$80 per 1,000** (= $0.08/action **DERIVED**). The checkout amount is therefore **UNVERIFIED**. Both sources list **$20 per 10,000 Vendor Credits** (= $0.002/vendor credit **DERIVED**). Vendor Credits cover model/tool cost at wholesale with no markup; paid plans may bring their own LLM key.
- Marketplace assets are a separate one-time price chosen by the builder, up to $1,000. The docs suggest $5–$25 for simple automation, $25–$100 moderate, $100–$500 advanced and $500–$1,000 enterprise-grade. A current third-party SEO Content Agent is listed at **$33.33**.
- A buyer commonly pays twice: once for the listing, then for the Relevance plan/Actions/Vendor Credits needed to run it. That is asset + platform usage, not Omo's all-in one-run price.

Sources: [live pricing page](https://relevanceai.com/pricing-new) · [current pricing docs](https://relevanceai.com/docs/get-started/pricing) · [paid SEO listing](https://marketplace.relevanceai.com/listing/d9ea471f-dd81-477a-b7be-718160137b8e) · [creator pricing/payout](https://relevanceai.com/docs/get-started/marketplace/relevance-builders/getting-paid)

#### How supply is onboarded

- Only approved **Relevance Builders** can submit. Applications are currently closed.
- Builders create a profile, connect Stripe, submit an Agent or Tool, choose free/paid and set a price, then pass internal review.
- Review checks usability, instructions, prompts, OAuth/API-key handling, inputs and prohibited legacy sub-agents. Updates are re-reviewed.
- Buyers purchase/clone into a project, can edit prompts/tools/settings, and may re-clone across projects only if the builder permits it. Most paid listings restrict cross-project cloning.
- Current public evidence: **85 creators**; top public builders show 93, 75 and 42 templates. The free Viola image-to-video agent shows 2,140 clones; a paid $33.33 SEO agent shows only two clones, illustrating that discovery exists but paid-liquidity depth is not yet proven.

Sources: [become a builder](https://relevanceai.com/docs/get-started/marketplace/relevance-builders/become-a-relevance-builder) · [submission review](https://relevanceai.com/docs/get-started/marketplace/relevance-builders/submit-agents) · [builders directory](https://marketplace.relevanceai.com/builders) · [Viola listing](https://marketplace.relevanceai.com/agents/image-to-video-generator)

#### Moat

- It already joins the two hard halves most competitors separate: creator checkout and hosted agent execution.
- 2,000+ integrations, agent/tool/workforce primitives, editable clones, schedules, Chat, analytics and enterprise controls make marketplace assets immediately operational.
- Creator-friendly 0% listing take rate lowers supply friction, while Relevance monetizes downstream Actions and Vendor Credits.
- Project-bound licenses and internal review create an ecosystem moat, although also lock-in.

#### Honest weaknesses vs Omo

- **Subscription-first execution.** A buyer cannot simply pay $0.10 for one finished result without joining the Relevance credit system.
- **Price is split and cognitively heavy:** listing price + Actions + Vendor Credits + possible third-party API key.
- **No general download door.** Editing a clone in Relevance is not owning a portable `SKILL.md` package runnable elsewhere.
- **Closed creator intake** blocks an open long-tail supply flywheel.
- **General GTM-agent positioning** lacks Omo's simple input → finished file/result merchandising and PhonicsMaker's credible education wedge.
- Paid marketplace liquidity is early: public clone counts on paid examples are low, even if free agents can reach thousands.

### 2. Gumloop — closest hosted workflow product

#### Exact pricing and per-run costs

- Pro starts at **$37/month**, includes **20,000 credits/month**, unlimited agents/seats, five concurrent workflow runs and an **8% orchestration fee**.
- Credit overage is **$0.007/credit** and capped at 2× the plan allocation.
- Each workflow execution starts at **1 base credit**. Standard AI nodes cost 2 credits, advanced 20 and expert 30; custom/MCP nodes cost 3. Many logic and connector nodes are free.
- Official examples: a standard AI workflow is 3 credits; an advanced AI + custom-processing workflow is 24 credits. At overage price these are **$0.021** and **$0.168** respectively (**DERIVED**). The base plan's simple division is $37/20,000 = $0.00185 per included credit (**DERIVED**) before the listed orchestration fee, but this is not a vendor-promised marginal cash price.
- Templates are free. There is no buyer-facing creator-set per-run or one-time template price.

Sources: [pricing](https://www.gumloop.com/pricing) · [credit rates and examples](https://docs.gumloop.com/core-concepts/credits)

#### How supply is onboarded

- The public catalog says it contains **185+ community examples**, with named creators, profiles, views, tools, descriptions and setup steps.
- Authors publish through **Share → Create template**, then provide a title, setup steps and Markdown description. Gumloop reviews every submission for quality and real-world usefulness and says it responds within 2–3 business days.
- Gumloop explicitly says it does **not currently facilitate payment for templates**.
- The separate Creator program is application-reviewed, but its economics are affiliate-driven: 20% of first-year subscription revenue from a new referred customer. It does not state that authors earn for template use.
- Current public pages show established examples such as an Automated AI Approval Flow at 11.1k views, Automated Email Triage at 10.4k and Meeting Prep at 10.1k. Views are not runs, paid conversions or GMV.

Sources: [community templates](https://www.gumloop.com/templates) · [publishing and review flow](https://www.gumloop.com/blog/announcing-community-templates) · [creator program](https://www.gumloop.com/partners/apply-to-be-a-creator) · [example workflow](https://www.gumloop.com/templates/automated-ai-approval-flow-using-agents)

#### Moat

- Outcome-oriented templates already look like operational products, not abstract prompts: clear setup, tool list and result descriptions.
- Deep no-code execution, connector auth, agents, flows, triggers, MCP hosting, analytics and enterprise governance are expensive runtime capabilities to reproduce.
- Community template views and creator profiles provide working discovery/distribution.
- GitHub Skill Sync gives Pro/Enterprise teams a repository source of truth, version history and portable Markdown skills that Gumloop says can be used across agent platforms.
- The $50M Series B banner signals substantial financing, though valuation, revenue and customer count are **UNVERIFIED** from the checked primary pages.

#### Honest weaknesses vs Omo

- It is still a **$37/month minimum subscription**, not “buy one finished result for cents.”
- A template is free; the creator is paid for referring the platform subscription, not for the intrinsic value or successful use of that workflow.
- Buyers must configure integrations/credentials and often understand a flow or agent. Omo's intended boundary is a much simpler form/API → result.
- GitHub Skill Sync is genuine portable-skill infrastructure, but it is not a buyer download door for a purchased, complete Gumloop workflow and is limited to Pro/Enterprise plans.
- Credit costs are resource-oriented and can be variable for agents, weakening an exact result price.

### 3. Poe — closest usage-based creator economy

#### Exact pricing and per-message costs

- Poe is free for most usage; subscriptions start at **$4.99/month**.
- Subscribers can buy add-on points starting at **$30 per 1,000,000 points** (= $0.00003/point **DERIVED**).
- Each bot displays fixed or variable point pricing. User cost combines the creator-set earning amount with model/compute cost.
- Eligible creators set their own USD earnings per answered message. Poe's official example uses **$3 per 1,000 messages** for one period and **$0.50 per 1,000** for another (= $0.003 and $0.0005/message **DERIVED**). The formal maximum is **$10,000 per 1,000 messages** (= $10/message **DERIVED**) for unusually expensive or specialized server bots.
- Stripe payouts begin at **$10**; creator monetization is available in 23 listed countries.

Sources: [consumer points](https://help.poe.com/hc/en-us/articles/19945140063636-Poe-Purchases-FAQs) · [creator FAQ](https://help.poe.com/hc/en-us/articles/21921312368020-Poe-Creator-Monetization-FAQs) · [Poe overview](https://poe.com/about)

#### How supply is onboarded

- Creators build prompt bots or server/API bots, enroll through Poe's Creators page, accept earnings terms, and set per-message pricing if located in an eligible region.
- Server-bot developers can dynamically set earnings through Poe's Bot Monetization API; custom commercial arrangements may be requested.
- Discovery occurs inside Poe's consumer bot network. The official about page says **millions of user-created bots** are available. Current active bot, monetized bot, creator, MAU and GMV figures are **UNVERIFIED**.

Sources: [creator program](https://poe.com/pages/demos/creator-monetization) · [creator API overview](https://creator.poe.com/docs/resources/creator-monetization) · [official about page](https://poe.com/about)

#### Moat

- Large consumer distribution and a familiar chat surface minimize adoption friction.
- It aggregates leading text, image, video and audio models behind one points wallet and API.
- The creator can align earnings to every successful response rather than depend only on a one-time sale or affiliate conversion.
- Server bots allow creators to bring differentiated backends and cover their own compute in the per-message price.

#### Honest weaknesses vs Omo

- The paid unit is normally **a message**, not a tested completion contract such as “upload source → receive a validated worksheet PDF.” Long conversations make result cost unpredictable.
- Discovery mixes base models, entertainment bots and utilities; it does not consistently merchandise professional input/output workflows.
- No portable bot or `SKILL.md` download door exists.
- Users still enter Poe's subscription/points ecosystem, and the creator does not control the full buyer checkout presentation.
- The platform, not the creator, owns most distribution and relationship context; switching costs are high.

## 5. Honest comparison and named risk

### What the top three already do that Omo does not yet

| Capability | Relevance AI | Gumloop | Poe | Omo's current gap |
|---|---|---|---|---|
| Demonstrated marketplace activity | 85 public creators, hundreds of templates, paid checkout and clone counts | 185+ community examples with examples around 10k views | Millions of user-created bots | Omo has not yet demonstrated comparable two-sided liquidity, repeat paid-run volume or public creator earnings. |
| Mature creator onboarding | Stripe-connected paid listings, review, refunds, update review | Creator application, featured templates, affiliate dashboard | Enrollment, per-message price controls, analytics, Stripe payouts | Omo's 85/15 promise needs a proven submission → test → price → payout → dispute loop at scale. |
| Hosted runtime breadth | Agents, tools, workforces, schedules, Chat and 2,000+ integrations | Agents, flows, triggers, credentials, MCP, governance | Multi-model text/image/video/audio, prompt and server bots, API | Omo's container/API runtime is strategically differentiated but is not yet proven at their breadth, uptime, concurrency and support load. |
| Distribution and brand | Enterprise customer base and builder agencies | Funded automation brand and creator ecosystem | Quora/Poe consumer network and mass bot discovery | Omo must earn demand; a superior model without distribution does not create marketplace liquidity. |
| Usage telemetry | Actions, vendor cost, task history and analytics | Credit/run logs, deterministic workflow cost, agent usage analytics | Per-bot messages, engagement and earnings | Omo needs enough completed-run data to rank “proven” workflows honestly and detect low-quality or unsafe listings. |

These are not cosmetic deficits. Marketplace liquidity, runtime reliability, payouts/refunds and outcome telemetry compound. Omo should not claim a moat merely from having a catalog schema or container architecture before repeated paid runs validate it.

### What Omo's complete model does that none of the top three does

Individual ingredients exist elsewhere—PromptBase sells `SKILL.md`, Gumloop syncs portable Markdown skills through GitHub, Dify/n8n/SmythOS allow export or self-hosting, Replicate prices predictions in cents, and Relevance sells hosted agent assets. The defensible claim is the **combination**, not exclusive ownership of each ingredient:

1. **`SKILL.md` → hosted, tested, priced, deployable pipeline.** A creator submits a portable skill; Omo turns it into a verified hosted result endpoint with a declared input/output contract, price and downloadable source. None of Relevance, Gumloop or Poe offers that complete conversion pipeline.
2. **Two doors on one listing.** The same proven workflow can be called on Omo/through one API or downloaded to leave. Relevance clones inside Relevance, Gumloop uses Gumloop templates, and Poe bots stay on Poe.
3. **Direct cents-level result checkout without a subscription.** Omo intends $0.10–a few dollars for the finished artifact/run. The top three require platform subscriptions/credit pools or price conversational messages rather than guarantee one all-in result price.
4. **Creator economics tied to the workflow sale/run.** Omo's proposed 85/15 directly values the creator's listing. Relevance pays one-time listing sales but not execution royalties; Gumloop pays subscription referrals; Poe pays messages but transfers no artifact.
5. **PhonicsMaker as a narrow demand wedge.** Omo has specific teacher workflows, bounded outputs and an existing education audience. The top three are general horizontal platforms; none combines a phonics-specific catalog, tested pedagogical contracts and per-result teacher pricing. This wedge is an initial distribution advantage, not a permanent moat by itself.

The wording should therefore be: **“No competitor found combines portable `SKILL.md` ownership, verified hosted execution, one-call finished results, cents-level no-subscription pricing and creator revenue on the same listing.”** Do not say no competitor has downloads, credits, hosted agents or creator payments individually.

### The one risk to name plainly: Relevance AI

**Why it could copy fastest:** Relevance already has every hard commercial primitive except the final packaging choice: paid third-party listings, creator-set prices, Stripe Connect-style payouts, curation/review, refunds, editable clones, hosted execution, action/vendor-cost metering, integrations, marketplace ratings and usage counts. Adding a “Run once for $0.50” button, a normalized input/output schema and a YAML/Markdown export is incremental product work for it, not a new company.

**What would stop or slow it:**

- A direct per-result wallet could cannibalize or confuse its Pro/Team Actions business.
- Portable export weakens project-bound licensing and enterprise lock-in.
- Its current builder program is closed and curated; opening long-tail supply increases review, fraud, support and security burden.
- Its GTM/enterprise positioning rewards ongoing agents and workforces more than tiny transactional outputs.
- Omo can build category depth, evidence standards and creator identity around proven results before Relevance chooses to move downmarket.

**What would not stop it:** technology. Omo's protection must be execution speed and accumulated evidence: better creator terms, faster skill-to-endpoint publishing, outcome QA, signed/versioned downloadable packages, category-specific reputation, and a growing graph of inputs → verified results → repeat purchases. PhonicsMaker can seed that graph, but only paid repeat use makes it defensible.

## 6. Sources

Primary sources were used unless explicitly marked. Pages were freshly checked on 2026-08-14.

### Relevance AI

- [Pricing documentation](https://relevanceai.com/docs/get-started/pricing)
- [Live pricing page](https://relevanceai.com/pricing-new)
- [Marketplace overview and paid purchase rules](https://relevanceai.com/docs/get-started/marketplace/introduction)
- [Become a Relevance Builder](https://relevanceai.com/docs/get-started/marketplace/relevance-builders/become-a-relevance-builder)
- [Submit agents and review requirements](https://relevanceai.com/docs/get-started/marketplace/relevance-builders/submit-agents)
- [Creator prices, 0% take rate, payouts and refunds](https://relevanceai.com/docs/get-started/marketplace/relevance-builders/getting-paid)
- [Public builders directory](https://marketplace.relevanceai.com/builders)
- [Paid SEO Content Agent — $33.33](https://marketplace.relevanceai.com/listing/d9ea471f-dd81-477a-b7be-718160137b8e)
- [Viola image-to-video agent](https://marketplace.relevanceai.com/agents/image-to-video-generator)

### Gumloop

- [Pricing](https://www.gumloop.com/pricing)
- [Credits, node rates and overage](https://docs.gumloop.com/core-concepts/credits)
- [Community templates](https://www.gumloop.com/templates)
- [Community template publishing and review](https://www.gumloop.com/blog/announcing-community-templates)
- [GitHub Skill Sync and Markdown portability](https://www.gumloop.com/blog/sync-skills-between-github-and-gumloop)
- [Creator affiliate program](https://www.gumloop.com/partners/apply-to-be-a-creator)
- [Agent node and sharing](https://docs.gumloop.com/core-concepts/agent_node)
- [Automated AI Approval Flow example](https://www.gumloop.com/templates/automated-ai-approval-flow-using-agents)

### Poe and OpenAI GPT Store

- [Poe creator monetization](https://poe.com/pages/demos/creator-monetization)
- [Poe Creator Monetization FAQ, updated June 18, 2026](https://help.poe.com/hc/en-us/articles/21921312368020-Poe-Creator-Monetization-FAQs)
- [Poe points and purchases](https://help.poe.com/hc/en-us/articles/19945140063636-Poe-Purchases-FAQs)
- [Poe FAQ](https://help.poe.com/hc/en-us/articles/19944206309524-Poe-FAQs)
- [Poe about page](https://poe.com/about)
- [OpenAI GPT Store launch](https://openai.com/index/introducing-the-gpt-store/)
- [OpenAI GPT FAQ and monetization status](https://help.openai.com/en/articles/8554407-gpts-faq)

### Automation, workflow and agent platforms

- [n8n pricing](https://n8n.io/pricing/)
- [n8n 11,490-template catalog](https://n8n.io/workflows/)
- [n8n affiliate program](https://n8n.io/affiliates/)
- [Dify pricing](https://dify.ai/pricing)
- [Dify Creator Center and Template Marketplace announcement](https://dify.ai/blog/dify-creator-center-template-marketplace-share-your-workflows)
- [Dify downloadable template example](https://marketplace.dify.ai/template/ariefjuharza/Dify%20x%20EdgeOne%20AI%20Course%20Support%20Assistant?creationType=templates&language=en-US&templateId=0601d7a3-a6a4-41ec-961d-5a35f62878b5&theme=light)
- [Zapier pricing](https://zapier.com/pricing)
- [Zapier 2026 AI-step task rates](https://help.zapier.com/hc/en-us/articles/46425475442829-AI-by-Zapier-model-tier-pricing)
- [Make pricing](https://www.make.com/en/pricing)
- [Make credit rules](https://help.make.com/credits)
- [Copy.ai pricing and workflow credits](https://www.copy.ai/prices)
- [Lindy pricing and job credit ranges](https://www.lindy.ai/pricing)
- [Lindy skills](https://www.lindy.ai/skills)
- [SmythOS pricing](https://smythos.com/pricing/)
- [SmythOS template/deploy workflow](https://smythos.com/docs/agent-templates/overview/)
- [Stack AI pricing](https://www.stackai.com/pricing)
- [Stack AI templates](https://www.stackai.com/templates)
- [Agent.ai pricing announcement](https://blog.agent.ai/agent.ai-is-introducing-platform-based-pricing-heres-whats-staying-free)
- [Agent.ai credits](https://docs.agent.ai/marketplace-credits)

### Artifact, inference and per-call marketplaces

- [PromptBase sell page](https://promptbase.com/sell)
- [PromptBase payouts and 80/20 split](https://promptbase.com/knowledge-base/payouts)
- [Replicate pricing](https://replicate.com/pricing)
- [Replicate Explore and public run counts](https://replicate.com/explore)
- [SingularityNET marketplace overview](https://dev.singularitynet.io/docs/products/AIMarketplace/)
- [SingularityNET per-call service page](https://dev.singularitynet.io/docs/products/AIMarketplace/service-page/)
- [SingularityNET free demo calls](https://dev.singularitynet.io/docs/products/AIMarketplace/free-call/)
- [SingularityNET publisher portal](https://publisher.singularitynet.io/)

### Existing Omo research reviewed

- `research/00-overview.md` (2026-08-08)
- `research/01-marketplaces.md` and `research/01-marketplaces-sources.csv` (2026-08-08)
- `marketing/category-expansion.md` (2026-08-13)
- `marketing/edtech-kill-list.md` (2026-08-13)
