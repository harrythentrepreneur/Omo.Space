# Try-before-you-buy / hosted-demo-agent + commerce precedents

**Research date:** 2026-08-08
**Scope:** Platforms that combine hosted agent demos (usable out of the box) with commerce (config sales, payouts, or usage billing). This is **as complete as found**, not a claim of internet-wide completeness.
**Note:** This lane hit its tool-call limit before writing files; findings were returned inline by the agent and transcribed here by the orchestrator. All URLs are as cited by the agent.

## Evidence and notation
- **OFFICIAL** — first-party product, docs, pricing, blog, or repository page.
- **UNVERIFIED** — fact not exposed on a reachable official page (often client-rendered); no number inferred.

---

## The 8 strongest precedents

### 1. Poe — closest overall
- Buyers interact with published bots directly inside Poe. Prompt bots and Python "Script Bots" are **hosted by Poe**; custom Server Bots remain creator-hosted.
- Creators set flat or code-determined **per-message payouts** and earn for attributable subscriptions.
- Stripe pays monthly, 30–45 days after month-end; balances below **$10** roll over; program page cites **23 countries**.
- Poe can cover inference and significant per-message costs for creators.
- **Missing:** buyers never purchase or export the bot configuration — no config commerce.
- [OFFICIAL docs](https://creator.poe.com/docs) · [monetization](https://poe.com/pages/demos/creator-monetization) · [cost coverage](https://creator.poe.com/docs/resources/how-we-cover-your-costs) · [earnings ToS](https://poe.com/pages/earnings-tos)

### 2. Dify Cloud — strongest demo-plus-clone architecture
- Every app automatically gets a hosted web app/API; links work immediately, including an "Anyone" mode explicitly intended for public demos.
- Creators can submit exported app configurations to the Marketplace, where users **copy them into their own workspaces**.
- **Missing:** verified paid template checkout or creator payout.
- [OFFICIAL publish docs](https://github.com/langgenius/dify-docs/blob/main/en/cloud/use-dify/publish/README.mdx) · [OFFICIAL marketplace publishing](https://github.com/langgenius/dify-docs/blob/main/en/cloud/use-dify/publish/publish-to-marketplace.mdx)

### 3. Relevance AI
- Marketplace agents are presented as **free, cloneable hosted agents** with usage/ratings; execution runs on Relevance's runtime and may consume platform/vendor credits.
- **Missing:** paid artifact sales and creator royalty.
- [OFFICIAL](https://marketplace.relevanceai.com/)

### 4. Gumloop (AgentHub successor)
- Hosts agent pages and workflow execution; community catalog has **185+** agent/workflow templates with named creators.
- Pro is **$37/month** (20,000 credits) with a 14-day trial.
- AgentHub's original "publish, host and share agents" thesis pivoted into controlled automation.
- **Missing:** per-template payments or creator revenue share.
- [OFFICIAL templates](https://www.gumloop.com/templates) · [pricing](https://www.gumloop.com/pricing) · [pivot post](https://www.gumloop.com/blog/agenthub-to-gumloop)

### 5. n8n
- **11,190** importable workflows; Cloud executes them with a no-card 14-day trial.
- Official docs still describe the creator marketplace as under development.
- Creators instead earn **30% of net referred Cloud subscriptions for 12 months**, monthly via PayPal from **€100** (affiliate, not artifact royalty).
- **Missing:** live listing-level demo and template royalty.
- [OFFICIAL workflows](https://n8n.io/workflows/) · [docs](https://docs.n8n.io/workflows/templates/) · [affiliates](https://n8n.io/affiliates/)

### 6. Hugging Face Spaces
- Best proof that hosted, out-of-box interactive demos drive artifact discovery. ZeroGPU Spaces are **free to users**; source is repository-backed and forkable.
- **Missing:** general buyer checkout or uploader usage royalty; creators normally fund compute.
- [OFFICIAL spaces overview](https://huggingface.co/docs/hub/spaces-overview) · [ZeroGPU](https://huggingface.co/docs/hub/spaces-zerogpu)

### 7. Vercel
- Community AI templates have one-click **Deploy Buttons**.
- The Vercel Marketplace now provides unified installation, authentication, provisioning, billing, and observability for commercial AI agents/services.
- **Missing:** a try-before-buy hosted instance tied to transferable config and a standard creator split.
- [OFFICIAL marketplace blog](https://vercel.com/blog/ai-agents-and-services-on-the-vercel-marketplace) · [Deploy Button docs](https://vercel.com/docs/deployments/deploy-button)

### 8. Skyfire / Stripe / x402 — enabling payment rails
- **Skyfire:** sellers publish APIs, websites, or MCP servers with **per-use, per-MB, or subscription** pricing and token settlement.
- **Stripe:** metered LLM/API billing and agentic commerce support.
- **x402:** gates each HTTP request with payment.
- These enable per-call/per-session charging but provide no demo catalog or artifact licensing.
- [Skyfire seller guide](https://docs.skyfire.xyz/docs/seller-guide.md) · [Stripe agents](https://docs.stripe.com/agents) · [x402](https://www.x402.org/)

---

## Other platforms checked

| Platform | Finding | Evidence |
|---|---|---|
| Character.AI | Hosted characters + creator analytics/discovery launched June 2026; **no creator cash monetization announced/verified** | [OFFICIAL](https://blog.character.ai/creator-bundle/) |
| Coze Global | Store, agent publishing, flow-trial routes, credits visible; demo→purchase flow and cash creator payouts **UNVERIFIED** (client-rendered docs) | — |
| Lindy | Hosted skills/templates + 7-day product trial; no open creator marketplace/payout | [OFFICIAL](https://www.lindy.ai/templates) |
| Replit | Hosted gallery/remixing; no closed loop | — |
| FlowGPT | Character chat/membership UI; no config commerce | — |
| GPT Store | Opaque engagement payouts; no exportable config purchase | — |
| Claude / AI Studio | Free interactive artifact sharing/remixing; no commerce | — |

---

## The three largest missing pieces in the market

1. **One SKU joining free demo usage to purchase/export of the exact tested config.**
2. **A transparent creator waterfall across asset sale, usage royalty, inference cost, and hosting margin.**
3. **Portable, versioned handoff with secrets, dependencies, licenses, verified runs, and post-purchase deployment.**

---

## Synthesis: who is closest?

Poe closes the **hosted demo + usage payout** loop but has no config commerce. Dify closes the **hosted demo + config export** loop but has no payouts. Vercel closes **deployment + billing infrastructure** but no creator split. **No platform verified in this review closes all three loops (try live → buy/export config → creator paid on sale + usage + hosting margin) with a public formula.** That full loop is the user's opportunity.
