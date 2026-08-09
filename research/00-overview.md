# Agent Marketplace — Master Landscape Synthesis

**Date:** 2026-08-08 | **Status:** as complete as found (not internet-wide)
**Sources:** 158 deduplicated URLs across 3 research lanes (see per-lane source CSVs)
**Lane files:** 01-marketplaces.md (+csv) · 02-hosting-infra.md (+csv) · 03-monetization-gaps.md (+csv)

---

## 1. The competitive map (49 marketplace/store products, 6 categories)

### 1a. Prompt marketplaces
| Platform | Model | Creator economics | Status |
|---|---|---|---|
| PromptBase | Prompts + portable SKILL.md skills | 0% via own link, 20% marketplace; Stripe/USDC | ACTIVE — closest direct competitor |
| PromptsIdeas | One-time USD + free | commission UNVERIFIED | ACTIVE |
| PromptHero | Discovery/subscription, not peer sales | none | ACTIVE (not a marketplace) |
| FlowGPT | Prompt apps/characters, bounties | UNVERIFIED | ACTIVE, shifted to character RP |
| AIPRM | Template library + SaaS | no per-prompt royalty | ACTIVE (library, not cash market) |
| ChatX | Former prompt market | — | PIVOTED (marketplace 404) |
| PromptDen | — | — | LIKELY DORMANT — don't plan around it |

### 1b. Assistant / app stores
- **OpenAI GPT Store** — huge distribution; monetization opaque/invite-dependent; no public rate verified.
- **Poe** — per-message pricing by creators; $10 min Stripe payout, 23 countries; usage-based economy, no fixed commission published.
- **Gemini Gems/Extensions** — sharing, not cash marketplace.
- **Microsoft Copilot Agent Store** — enterprise procurement: free/trial/subscription/usage/contract offers; take-rate not public.

### 1c. Skill & agent marketplaces
- **Hugging Face hub/agents** — massive, mostly free/open.
- **Replicate** — model hosting + pay-per-use, not skill sales.
- **LangChain Hub** — prompt/tool sharing, free.
- **CrewAI Marketplace** — curated enterprise rollout, not open retail.
- **Anthropic Agent Skills** — open SKILL.md spec; ecosystem emerging (agentskills.io).

### 1d. MCP registries (heavily duplicated, mostly free directories)
Smithery (4,106 servers; now part of Arcade.dev), mcp.so, Glama, PulseMCP, MCP Market, Cloudflare MCP, MCP Registry (modelcontextprotocol.io — no commerce layer).

### 1e. Automation/workflow template marketplaces
- **n8n** — 11,190 templates; affiliates 30% of net Cloud subs for 12 months; no per-template royalty verified.
- **Dify Marketplace** — broadest runtime ecosystem (plugins/tools/models/agents); mostly free.
- **Relevance AI** — cloneable hosted agents; monetizes execution plans/credits.
- Zapier/Make — partner/affiliate programs (Make: 35% referral for 12 mo), not workflow royalties.
- **Flowise — SUNSETTING** (official homepage). Coze global vs China are distinct/region-locked.

### 1f. Dedicated agent-store startups
- **AgentHub.dev → absorbed/pivoted into Gumloop** (redirect).
- **Salesforce AgentExchange** — 15k+ partner community, enterprise.
- **AWS Marketplace AI Agents & Tools** — PAYG/contracts/private offers; Bedrock AgentCore deployable. Strongest infra+procurement competitor.
- Skyfire — payments for agents (adjacent, not a store).

---

## 2. Monetization benchmarks (verified)

| Platform | Verified economics |
|---|---|
| PromptBase | **80/20 creator/platform** (marketplace sales); **0%** when creator brings buyer |
| GPT Store | 2024 US-builder engagement payments announced; **no public rate verified by 2026-08** |
| Poe | Per-message earnings + subscription acquisition; Stripe from $10, 23 countries; no universal % |
| n8n | Affiliate: 30% net Cloud subs, 12 mo, €100 threshold; no template royalty |
| Make | 35% referral commission, 12 mo (subscription acquisition) |
| MCP Registry | No checkout/commission/payout layer at all |

**Takeaway:** 80/20 is the clearest per-item benchmark. There is NO verified 50/50 standard. The market's monetization is thin — most "marketplaces" are free directories monetized via subscriptions/credits, not per-item sales.

---

## 3. Dead / pivoted / constrained (do not plan around)

- **Flowise** — SUNSETTING (official)
- **AgentHub.dev** — pivoted into Gumloop
- **ChatX marketplace** — 404, pivoted
- **PromptDen** — unreachable/dormant
- **CrewAI Marketplace** — curated enterprise only
- **Coze China** — region/account constrained, distinct from global

---

## 4. Legal/IP reality (source-backed)

1. Prompts may be copyrightable if sufficiently creative, but do NOT establish authorship of generated output (US Copyright Office Part-2 report).
2. License SKILL.md, code, assets, datasets separately (MIT/Apache/proprietary). Anthropic's own repo mixes Apache + source-available.
3. MCP project license ≠ license for each server; per-server and per-API rights review needed.
4. OpenAI/Anthropic assign output rights to users, but outputs can be non-unique/non-copyrightable; hosted commerce must use commercial APIs (consumer-account automation prohibited).
5. PromptBase ToS: creator retains IP, buyer gets perpetual nonexclusive use. GPT Store sharing: OpenAI gets broad irrevocable royalty-free license, can remove anytime.

---

## 5. Top 5 gaps (ranked by opportunity)

1. **One-click deploy + managed hosting + creator share of hosting revenue** — almost nobody bundles commerce with execution.
2. **Cross-framework packaging** (SKILL.md ↔ MCP ↔ n8n ↔ GPTs with tested adapters; honest native-vs-converted labels).
3. **Trust layer**: security scanning, dependency pinning, signed/versioned artifacts, verified runs, rollback.
4. **Enterprise**: private catalogs, governance, audit, procurement.
5. **Discovery/SEO + verified-run reputation + maintainer community**.

---

## 6. Recommended default stack (from hosting lane)

- **Vercel** — marketplace UI, checkout, catalog, control-plane API (free Hobby; Pro $20/mo)
- **Railway** — default seller deployment target (containers, volumes, cron, secrets; Hobby $5 min usage) — Render/Cloud Run as secondary adapters
- **Cloudflare Workers + Durable Objects** — remote MCP servers + edge OAuth ($5/mo min + usage)
- **n8n** — portable automation format (workflow JSON) + Cloud SKU (Pro €50/mo, 10k executions)
- **Specialists:** GPU → Modal (H100 ~$3.95/hr) · browser → Browserbase (free tier 1 hr/mo; $20/$99) · sandbox → E2B (free + $100 credit; Pro $150/mo) or Daytona

---

## 7. Positioning recommendation (from monetization lane)

Position as **the trusted deployment + commerce layer for portable agent capabilities**, not another prompt gallery. Start with Agent Skills/Hermes-compatible packages, then add tested MCP and automation adapters with clear native-vs-converted labels. Transparent creator-favorable asset split (PromptBase's 80/20 is the benchmark to beat — e.g. 85/15 or 90/10 on self-sold), while making managed usage, maintenance subscriptions, and enterprise private catalogs the recurring business. Differentiate: self-hosting, signed/versioned artifacts, verified execution, budget controls, creator participation in net hosting margin.

---

# PART 2 — Deep-dive: hosted-demo + config-commerce model (2026-08-08, sol lanes)

## 8. The concept validated

The refined model — **creators publish config files; marketplace hosts a live demo agent at thin margins; buyers try it out of the box, then buy the config or keep it hosted; creators get paid** — maps to a THREE-LOOP loop no verified platform closes today:

1. **Try live** — hosted demo of the exact config (Poe, Dify, HF Spaces, Relevance AI all do variants)
2. **Buy/export config** — purchase of the tested, versioned config (PromptBase sells files; Dify exports; nobody ties it to the demo)
3. **Creator paid across sale + usage + hosting margin** — with a public formula (nobody verified has all three)

Closest per-loop leaders: **Poe** (hosted demo + usage payouts, no config commerce) · **Dify** (hosted demo + config copy, no payouts) · **Vercel Marketplace** (deploy + billing infra, no creator split) · **PromptBase** (config commerce 80/20, no demo hosting). The full loop is open.

## 9. Unit economics — thin margins made concrete (from 05-unit-economics.md)

LLM-only cost per session (DERIVED, verified rate cards 2026-08-08):

| Scenario (in/out tokens) | DeepSeek V4 Flash | GPT-5 mini | Claude Haiku 4.5 |
|---|---|---|---|
| Simple QA (4k/500) | $0.00070 | $0.00200 | $0.00650 |
| Tool agent (8k/1.5k) | $0.00154 | $0.00500 | $0.01550 |
| Browser agent (20k/4k) | $0.00392 | $0.01300 | $0.04000 |

Hosting per session: Workers $0.0000013 · Vercel $0.00005 · Railway $0.00012 · sandbox (Modal $0.0008 / Daytona $0.0069 / E2B $0.011) · managed browser (Browserbase ~$0.02 marginal).

**Break-even at 80/20: session floor = 5×COGS.** Economy chat: $0.0035/session (10-pack $0.035). Tool agent + Daytona: $0.060/session (10-pack $0.60). Browser agent: $0.14/session (10-pack $1.40).

**"Thin margin" = roughly $0.001–$0.02/session** for capped cheap-tier demos; browser workloads exceed that.

Free demo caps: 5 free sessions/day ≈ $0.105–$4.21/month per maximally active buyer depending on stack — viable ONLY with hard dollar/token/step/time caps.

Cheapest viable stack: **Cloudflare Workers + DeepSeek V4 Flash**, 4k/500 tokens, no browser/sandbox unless declared.

Key risks: prompt/config extraction, credential leaks + key resale, sybil quota bypass, infinite tool loops, undeclared premium escalation, giant-context attacks. Controls: hard limits, authenticated quotas, server-side scoped secrets, prepaid credits, streaming cancellation, spend alerts.

## 10. Recommended business model (from 06-business-model.md)

**Payout waterfall (transparent, creator-favorable, beats PromptBase):**
- **85/15** creator/platform on marketplace-discovered license sales (95/5 on creator-referred)
- **20% of positive net hosting margin** to the creator (hosted revenue − actual variable model/tool/compute costs) — no verified precedent anywhere; this is the differentiator
- Maintenance/update subscriptions: **85/15**
- Usage royalties: defer until telemetry is reliable; later add disclosed per-session/per-success fees

**Buyer pricing (5 tiers):**
1. **Explore — free:** 1 anonymous or 3 authenticated read-only messages, ≤$0.05 COGS/visitor cap
2. **Own — $19–$99:** perpetual license to versioned portable config; redistribution prohibited
3. **Run — $10/$25 prepaid credits:** all-in variable cost + 25% markup → 20% hosted gross margin before creator share
4. **Maintain — $5–$25/mo:** updates, compatibility testing, support (85/15)
5. **Team/Enterprise:** control-plane fee + seats + metered usage + private catalogs, SSO/SCIM, budgets, audit, model allowlists, DPA/SLA

**Legal findings for demo hosting (verified):**
1. Value-added applications are permitted by OpenAI/Anthropic/Google; raw API/account/key resale is prohibited. Keep keys server-side; sell specialized agent outcomes, not generic model access.
2. The marketplace is the API customer and stays responsible for provider policy, age/region limits, AI disclosure, high-risk review, moderation, agentic confirmations.
3. Never automate consumer subscriptions for hosting — commercial API agreements only (Anthropic consumer terms prohibit automated access except via API key).

**Final positioning:** "The trusted try-before-you-deploy marketplace for portable agent capabilities." Launch: read-only SKILL.md packages, capped demos, verified runs, signed versions, cost visibility, rollback, no consequential external actions. Portability, transparent economics, reproducible execution — not prompt secrecy — are the core value.

## 11. THE MOAT — backend execution (client articulation, 2026-08-08)

The client's own words define the durable advantage: "our magic and MOAT is the backend, how we can host all the models and set it up in docker containers for deployment so people can use it through API in their own container env... it's like gumtree, where people can list their services/skills and then sell them here, but we also can host the workflows and models for people to use and pay for and get paid for, so it's like a massive directory of input/output skills."

What this means concretely:
- **Every listing is a full product, skool-style:** cover image, description, INPUT → OUTPUT examples, a working demo, price. Click a card → a real detail view, not a README.
- **The moat is that Bench RUNS what it sells.** GitHub hands you a link and you're on your own; Bench hosts the workflow AND the model (Docker containers under the hood), serves it via API (one key) or on-platform, or hands you the files to run in your own container environment.
- **Personalised + remembered:** user settings/history persist across uses — via API or however the user likes.
- **Gumtree analogy:** a noticeboard where people list skills and sell them — except here the skill actually executes. "A massive directory of input/output skills."
- **Copy rule that follows:** explain the backend in 8-year-old-simple language where it must be said (container → "a clean little box on our servers"; API key → "a key that lets your app call it"; Docker mostly invisible; "it remembers you and your settings").
- **Why it wins:** this is the un-copied half of the loop. Prompt galleries sell files; Gumloop/Relevance host but don't pay creators per-sale; Poe pays usage but sells no configs. The combination — niche directory + hosted execution + transparent creator payouts + remembered personal state — is the full loop from section 8, now with the backend as the defensible infrastructure.
