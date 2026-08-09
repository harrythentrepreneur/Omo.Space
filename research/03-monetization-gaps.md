# Monetization models, legal/IP landscape, and market gaps for AI prompts, agent skills, and automations

**Research date:** 2026-08-08  
**Scope:** Selling prompts, instruction-based agent skills, executable skills/MCP servers, and automations, with emphasis on a new marketplace that bundles managed hosting.  
**Evidence labels:** `OFFICIAL` = first-party platform/project material; `NEWS` = reputable reporting; `LEGAL` = law/government text or operative legal terms; `DIRECTORY` = catalog/company database; `REVIEW` = independent review; `UNVERIFIED` = not verified to the requested standard.

> **Limitations.** This is a dated, targeted source review, not an internet-wide census. Commercial terms, beta programs, and marketplace policies can change quickly. “No public rate verified” means the cited official materials reviewed on 2026-08-08 did not disclose one; it does not prove that no private, invited, regional, or negotiated program exists. Recommendations are analysis, not legal advice.

## Executive takeaways

1. **There is no single standard creator split.** The cleanest verified per-item benchmark is PromptBase: creator keeps 80% on marketplace-discovered sales and 100% of the item price when the seller brings the buyer through a unique link (payment-processing, tax, refund, or adjustment effects may still apply). ([OFFICIAL](https://promptbase.com/sell), [OFFICIAL](https://promptbase.com/blog/zero-fees))
2. **The strongest recurring creator economics are affiliate or usage based, not store-item royalties.** n8n pays 30% of net Cloud subscription revenue for 12 months; Make advertises 35% for 12 months; Poe lets creators set per-message earnings and also pays for subscriber acquisition, but publishes no universal percentage split. ([OFFICIAL](https://n8n.io/affiliates/), [OFFICIAL](https://www.make.com/en/affiliate), [OFFICIAL](https://poe.com/pages/demos/creator-monetization))
3. **OpenAI still does not provide a public GPT-builder split or payout formula in the official sources reviewed.** Its January 2024 launch post promised a US engagement-based program and said details would follow; the June 2026 GPT service terms govern content and distribution but do not state a compensation rate. Treat any “GPT Store 80/20” or similar number as `UNVERIFIED`. ([OFFICIAL](https://openai.com/index/introducing-the-gpt-store/), [LEGAL](https://openai.com/policies/service-terms/))
4. **Prompts are not categorically uncopyrightable, but prompt authorship and output authorship are different questions.** A sufficiently creative prompt may itself be protected; under the Copyright Office’s January 2025 analysis, prompts alone generally do not give enough control over current generative systems to make the user author of the resulting output. ([LEGAL](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf))
5. **The largest opportunity is not another download catalog.** It is a trusted cross-framework package plus one-click managed runtime: import an open `SKILL.md` skill, adapt it to supported clients, provision its dependencies/secrets, run it safely, meter it, update it, and share hosting margin with the creator. This opportunity is supported by the new Agent Skills portability standard, the official MCP Registry’s deliberately unopinionated catalog role, and Vercel’s validation of unified installation/billing/provisioning. ([OFFICIAL](https://agentskills.io/home), [OFFICIAL](https://modelcontextprotocol.io/registry/about), [OFFICIAL](https://vercel.com/blog/ai-agents-and-services-on-the-vercel-marketplace))

---

## 1. Monetization models: what platforms actually do

### 1.1 Verified creator economics

| Platform / program | What the buyer pays / platform model | Verified creator payout | Effective creator split | Evidence and caveat |
|---|---|---:|---:|---|
| **PromptBase marketplace** | Per-item prompts and, by 2026, agent skills (`SKILL.md` files) | Platform fee is **20%** on marketplace sales | **80/20** creator/platform before other adjustments | Seller page explicitly says “20% via marketplace.” ([OFFICIAL](https://promptbase.com/sell)) |
| **PromptBase seller-referred sale** | Same per-item sale, reached through seller’s unique link | **0% platform fee** | **100/0** on the item price, subject to payment/tax/refund mechanics | Launched/updated 2025-10-30; PromptBase says the normal fee is 20%. ([OFFICIAL](https://promptbase.com/blog/zero-fees)) |
| **OpenAI GPT Store** | ChatGPT subscription/discovery ecosystem; users do not normally buy a GPT as a separately priced item | Official launch promised US builders payment based on engagement; **no public percentage, unit rate, or generally available formula verified** | **UNVERIFIED** | January 2024 post said a program would launch in Q1 and details would follow. Current GPT terms contain no public rate. ([OFFICIAL](https://openai.com/index/introducing-the-gpt-store/), [LEGAL](https://openai.com/policies/service-terms/)) |
| **Poe creator monetization** | Poe subscriptions/points; bot creators may set per-message pricing; subscriber-acquisition payouts also exist | Creator can set a flat or code-determined payout per call/message; Stripe payout after **$10**, available in **23 countries** on the official program page | No universal split published; **usage-based / acquisition-based**, not a fixed store royalty | Poe says it intends to cover inference and other significant per-message costs, including custom arrangements. ([OFFICIAL](https://poe.com/pages/demos/creator-monetization), [OFFICIAL](https://creator.poe.com/docs/resources/how-we-cover-your-costs)) |
| **n8n templates + affiliate** | Templates are browsed/imported; official docs describe the creator program/marketplace as ongoing and subject to change | No verified per-template sale royalty; creators can attach acquisition to **30% of net n8n Cloud subscription revenue for 12 months** | **30% referral / 70% vendor** on qualifying net Cloud revenue for one year | Monthly PayPal payout at balances of at least **€100**. ([OFFICIAL](https://docs.n8n.io/workflows/templates/), [OFFICIAL](https://n8n.io/affiliates/)) |
| **Make affiliate** | Referral to Make’s subscription product, often via shared automation scenarios/content | **35% commission for 12 months** | **35/65** of qualifying referred subscription revenue during year one | Official affiliate page; not a template-sale royalty. ([OFFICIAL](https://www.make.com/en/affiliate)) |
| **Zapier partner programs** | Integration, solution/consulting, and creator partnerships drive Zapier adoption | Current official partner page offers incentives/benefits and sponsored content for selected large creators, but **no standardized public commission rate verified** | **UNVERIFIED / negotiated** | Joining is free; integration benefits are mainly distribution, support, co-marketing, and tier benefits rather than a published template royalty. ([OFFICIAL](https://zapier.com/l/partners), [OFFICIAL](https://zapier.com/developer-platform/partner-program)) |
| **Official MCP Registry** | Open discovery catalog/API for public MCP servers; downstream marketplaces can enrich it | **No checkout, commission, or creator-payout mechanism verified** | **None at registry layer** | Registry is an open upstream source; downstream aggregators are expected to provide curation, ratings, and marketplace experiences. ([OFFICIAL](https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/), [OFFICIAL](https://modelcontextprotocol.io/registry/about)) |
| **Vercel Marketplace agents/services** | Native integrations with unified authentication, provisioning, billing, observability, and installation | Provider-specific economics; **no universal creator split disclosed in the launch materials reviewed** | **UNVERIFIED / provider-specific** | Important competitive proof that bundled infrastructure and billing are valuable, but not evidence of a standard marketplace royalty. ([OFFICIAL](https://vercel.com/blog/ai-agents-and-services-on-the-vercel-marketplace), [OFFICIAL](https://vercel.com/changelog/introducing-ai-agents-and-services-on-the-vercel-marketplace)) |

### 1.2 What “typical split” can safely mean

- For a **true per-item prompt/skill sale**, **80/20 is the strongest verified category benchmark in this review**, because PromptBase states it directly. PromptBase’s 0% seller-referred fee also shows that platforms may waive the marketplace take when they did not supply demand. ([OFFICIAL](https://promptbase.com/sell), [OFFICIAL](https://promptbase.com/blog/zero-fees))
- **30–35% is a verified one-year recurring referral share** in the automation category (n8n 30%; Make 35%), but it is an affiliate acquisition payment, not ownership of or royalties on the workflow itself. ([OFFICIAL](https://n8n.io/affiliates/), [OFFICIAL](https://www.make.com/en/affiliate))
- A **50/50 “typical creator split” is not supported by the sources reviewed**. Poe’s usage payouts are creator-configurable and OpenAI’s GPT engagement economics are undisclosed, so forcing them into a percentage split would be misleading. ([OFFICIAL](https://creator.poe.com/docs/resources/creator-monetization), [OFFICIAL](https://openai.com/index/introducing-the-gpt-store/))

### 1.3 Model taxonomy and fit for a new marketplace

| Model | Existing proof | Strength | Weakness | Recommended use |
|---|---|---|---|---|
| **Per-item purchase** | PromptBase’s 80/20 and 100/0 referral routes ([OFFICIAL](https://promptbase.com/sell)) | Simple and creator-legible | Low price ceiling; easy copying; no recurring maintenance revenue | Small prompts, static skills, starter bundles |
| **Subscription library** | ChatGPT/Poe bundle access around GPTs/bots ([OFFICIAL](https://openai.com/index/introducing-the-gpt-store/), [OFFICIAL](https://poe.com/pages/demos/creator-monetization)) | Predictable buyer spend; good discovery | Opaque allocation pool can alienate creators | Curated skill packs, team plans, support/update entitlement |
| **Credits / per-message** | Poe’s message pricing and points economics ([OFFICIAL](https://creator.poe.com/docs/resources/how-we-cover-your-costs)) | Aligns revenue to usage and inference cost | Metering complexity; creators need cost visibility | Hosted agents, expensive tools/search/browser/model calls |
| **Usage-based infrastructure** | Vercel’s unified billing/provisioning and Poe’s inference-cost coverage ([OFFICIAL](https://vercel.com/blog/ai-agents-and-services-on-the-vercel-marketplace), [OFFICIAL](https://creator.poe.com/docs/resources/how-we-cover-your-costs)) | Best fit for bundled hosting; recurring gross profit | Requires observability, budget controls, abuse/fraud handling | Primary model for managed skills and automations |
| **Affiliate / acquisition bounty** | n8n 30% and Make 35% for 12 months ([OFFICIAL](https://n8n.io/affiliates/), [OFFICIAL](https://www.make.com/en/affiliate)) | Pays creators for demand generation | Rewards marketing more than technical quality | Seller-referral bonus and ecosystem partner channel |
| **Enterprise license / procurement** | Anthropic organization-wide skills and Vercel unified platform installation/billing ([OFFICIAL](https://claude.com/blog/skills), [OFFICIAL](https://vercel.com/changelog/introducing-ai-agents-and-services-on-the-vercel-marketplace)) | Higher ACV, private distribution, governance | Longer sales/support/compliance cycle | Private catalogs, seats + usage, support/SLA add-ons |

### 1.4 Proposed economics (recommendation, not an observed market fact)

A cost-conscious entrant should publish a transparent waterfall rather than an opaque engagement pool:

1. **Asset sale:** target **85/15** marketplace-discovered and **95/5 or 100/0 platform fee** when the creator supplies the buyer; pass through card fees/tax/refunds explicitly. This deliberately beats PromptBase’s verified 80/20 benchmark while preserving a discovery fee. Evidence basis: PromptBase’s differentiated 20%/0% routes. ([OFFICIAL](https://promptbase.com/blog/zero-fees))
2. **Managed run:** charge metered model/tool/compute cost plus a visible platform margin; share a defined portion of **net hosting contribution margin** with the creator. Do not describe gross usage revenue as creator earnings before inference and third-party tool costs. Evidence basis: Poe separates creator payout from inference-cost coverage. ([OFFICIAL](https://creator.poe.com/docs/resources/how-we-cover-your-costs))
3. **Maintenance subscription:** let creators sell update/support entitlements or team subscriptions in addition to a one-time license. This ties recurring revenue to versioning work rather than only downloads; the market gap is supported by n8n’s still-evolving template marketplace and Agent Skills’ version-controlled folder model. ([OFFICIAL](https://docs.n8n.io/workflows/templates/), [OFFICIAL](https://agentskills.io/home))
4. **Enterprise:** invoice seats/base platform + metered runs + optional SLA; support private catalogs and creator-specific commercial licenses. Evidence basis: Anthropic organization-wide skill management and Vercel’s unified enterprise-oriented install/billing model. ([OFFICIAL](https://claude.com/blog/skills), [OFFICIAL](https://vercel.com/blog/ai-agents-and-services-on-the-vercel-marketplace))

---

## 2. Legal and IP landscape

### 2.1 Are prompts copyrightable?

**Nuanced answer: sometimes the text of a prompt, but not necessarily the generated output.**

- The U.S. Copyright Office states that a prompt **itself may be copyrightable if sufficiently creative/original**. A terse instruction, method, idea, formula, or functional command may fail originality or fall on the idea/method side of copyright; a long, expressive prompt can contain protectable human-authored expression. ([LEGAL](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf))
- Separately, the Office concludes that, with current generally available technology, **prompts alone do not provide sufficient human control to make the user the author of the AI output**. Repeated prompt revision and selecting one result generally do not change that control analysis. ([LEGAL](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf))
- Copyright can protect human-authored elements perceptible in the final work, creative selection/coordination/arrangement, or sufficiently creative human modifications, while excluding purely AI-generated elements. The analysis is case-specific. ([LEGAL](https://www.copyright.gov/newsnet/2025/1060.html), [LEGAL](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf))

**Marketplace implication:** do not market every prompt as a copyright “asset.” Use contract licenses, confidentiality before purchase, anti-redistribution terms, access controls, reputation, updates, support, and hosted execution as the practical protection/value layer. The contract can restrict a buyer even when copyright coverage is thin, subject to applicable law and enforceability.

### 2.2 Can skills and automations be licensed?

Yes. A skill bundle can contain several legally distinct layers: human-authored instructions/documentation, source code/scripts, configuration, templates/assets, data, trademarks, and third-party dependencies. Each layer can carry an open-source license, a proprietary commercial license, or no granted license; absence of a license is not the same as open source.

- **MIT** is a permissive software license allowing use, copying, modification, distribution, sublicensing, and sale while requiring preservation of the copyright/license notice. ([LEGAL](https://opensource.org/license/mit))
- **Apache-2.0** is permissive and adds an express patent license plus notice/attribution conditions; it is often a better default for executable agent infrastructure with patent concerns. ([LEGAL](https://www.apache.org/licenses/LICENSE-2.0))
- Anthropic’s public skills repository illustrates mixed licensing: many skills are Apache-2.0, while its document-generation skills are described as source-available rather than open source. A marketplace must read the license at the file/package level rather than assume one repository-wide grant. ([OFFICIAL](https://github.com/anthropics/skills))
- A proprietary skill can grant nonexclusive use by buyer, per-seat/per-organization rights, hosted-use-only access, or resale/redistribution restrictions. PromptBase’s contract model, for example, says creators retain IP and buyers receive a nonexclusive, worldwide, perpetual use license but may not directly resell/redistribute/transfer the prompt without consent. ([LEGAL](https://promptbase.com/tandcs))

**Recommended listing fields:** SPDX identifier; separate code/content/data licenses; commercial-use, seat, client-work, redistribution, modification, hosted-use, and sublicensing flags; dependency bill of materials; model/provider requirements; trademark permissions; and a seller warranty that they have authority to license every bundled component.

### 2.3 MCP server licensing

- **MCP is an interoperability protocol, not a license for each server.** A server implementation remains governed by its own repository/package/content licenses and by the terms of APIs or data sources it connects to. The official registry stores self-reported distribution metadata and deliberately relies on downstream aggregators for added curation; it does not convert a listed server into open source or commercially reusable code. ([OFFICIAL](https://modelcontextprotocol.io/registry/about))
- The MCP project itself is in a transition from MIT to Apache-2.0: new code/spec contributions are Apache-2.0, documentation other than specifications is CC-BY-4.0, and older contributions without relicensing consent remain MIT. This project license does **not** automatically apply to third-party MCP servers. ([LEGAL](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/LICENSE))
- Registry namespace verification and moderation reduce impersonation/spam, but the registry documentation says it does not itself scan actual server code and expects the broader ecosystem to contribute security analysis. ([OFFICIAL](https://modelcontextprotocol.io/registry/about))

**Marketplace implication:** require a server-level license, source/provenance URL, declared tool permissions, network destinations, secret scopes, dependency lockfile/SBOM, vulnerability scan, sandbox result, and signed/versioned release. “Listed in the official MCP Registry” should not be displayed as “security approved.”

### 2.4 Closed-model terms and selling prompts/skills/outputs

#### OpenAI

- OpenAI’s January 2026 individual Terms say the user retains ownership rights in Input and owns Output as between the parties, with OpenAI assigning any rights it may have. The same terms warn that outputs may not be unique and that users are responsible for having rights in Inputs and for lawful use. ([LEGAL](https://openai.com/policies/terms-of-use/))
- The Terms prohibit representing AI output as human-generated when it is not, programmatic extraction except as allowed, bypassing protections, and using Output to develop models that compete with OpenAI. These restrictions matter more to a hosted automation service than to a static prompt listing. ([LEGAL](https://openai.com/policies/terms-of-use/))
- OpenAI’s June 2026 Service Terms treat a builder’s GPT instructions/name/description as the builder’s Content, but public sharing grants OpenAI a nonexclusive, worldwide, **irrevocable, royalty-free** license to use, modify, distribute, and promote the GPT. Users also receive rights to use GPT Content to the extent it appears in output; OpenAI may remove a GPT at any time. ([LEGAL](https://openai.com/policies/service-terms/))
- A product-specific exception illustrates why output ownership is not enough: ChatGPT Voice Output is designated non-commercial and may not be repackaged as a standalone recording. Code output may also be subject to third-party licenses. ([LEGAL](https://openai.com/policies/service-terms/))

#### Anthropic

- Anthropic’s commercial terms say customers retain Inputs and own Outputs as between the parties; Anthropic assigns any rights it may have and says it may not train models on commercial Customer Content. Customers remain responsible for compliant inputs/use. ([LEGAL](https://www.anthropic.com/legal/commercial-terms))
- Anthropic’s consumer terms similarly assign its rights in Outputs, but prohibit automated/non-human access except through an Anthropic API key or where explicitly permitted; evaluation-only access may be non-commercial. A hosted marketplace should use commercial API terms, not automate a consumer Claude account. ([LEGAL](https://www.anthropic.com/legal/consumer-terms))
- Anthropic’s Usage Policy applies to users including pass-through access and expressly covers consumer-facing chatbots/products and MCP servers. A marketplace must screen listings and runtime behavior for universal/high-risk restrictions rather than assume that “the seller owns the output” permits every use. ([LEGAL](https://www.anthropic.com/legal/aup))

**Bottom line:** neither provider’s ownership assignment is a guarantee that an output is copyrightable, unique, non-infringing, accurate, or allowed for every product-specific use. Selling a prompt or skill is not generally forbidden by the cited terms, but hosted execution must use the correct account/API terms, preserve provider-required disclosures/restrictions, and avoid prohibited content and automation methods.

### 2.5 What sellers retain on PromptBase and GPT Store

| Platform | Seller/builder rights | License granted / buyer rights | Platform control |
|---|---|---|---|
| **PromptBase** | Terms state prompts are IP of their respective creators | Buyer receives nonexclusive, worldwide, perpetual use; no direct resale/redistribution/transfer without creator consent | PromptBase collects as seller’s limited payment agent and can deduct fees, refunds, chargebacks, and adjustments. ([LEGAL](https://promptbase.com/tandcs)) |
| **OpenAI GPTs/GPT Store** | GPT Content is builder Content; underlying general Terms retain Input rights | Public sharing gives OpenAI an irrevocable, royalty-free worldwide operational/distribution/promotion license; users gain rights where GPT Content appears in output | OpenAI can reject/remove a GPT at any time; current official terms state no creator revenue percentage. ([LEGAL](https://openai.com/policies/service-terms/)) |

### 2.6 Top legal implementation requirements

1. **Separate ownership from licensing and from output copyrightability.** Record who authored instructions/code, which parts were AI-generated, and exactly what rights are granted. ([LEGAL](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf))
2. **Use component-level licenses and dependency provenance.** A `SKILL.md`, scripts, assets, datasets, model output, and MCP server may require different grants/notices. ([OFFICIAL](https://github.com/anthropics/skills), [LEGAL](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/LICENSE))
3. **Use commercial API access for hosted runs and flow down provider restrictions.** Do not automate consumer accounts where prohibited; enforce OpenAI/Anthropic usage policies at listing and runtime. ([LEGAL](https://openai.com/policies/terms-of-use/), [LEGAL](https://www.anthropic.com/legal/consumer-terms), [LEGAL](https://www.anthropic.com/legal/aup))
4. **Draft explicit marketplace licenses and platform grants.** Define seats, client work, hosted-only use, modifications, redistribution, output use, update rights, termination, refunds, and takedowns. PromptBase and OpenAI show materially different grants. ([LEGAL](https://promptbase.com/tandcs), [LEGAL](https://openai.com/policies/service-terms/))
5. **Design IP/safety operations, not only terms.** Seller identity, DMCA/takedown/counter-notice, repeat-infringer process, trademark/impersonation reports, malicious-code response, audit logs, escrow/rollback, and dispute evidence are necessary because official registries themselves do not certify server code. ([OFFICIAL](https://modelcontextprotocol.io/registry/about))

---

## 3. Market gaps and opportunity ranking

### Rank 1 — One-click deployment plus managed hosting and creator participation in usage revenue (**very high opportunity**)

**Observed gap.** PromptBase mainly monetizes transferable items; n8n/Make reward subscription referrals; Poe supports usage payouts inside its own bot environment. None of those cited programs provides a framework-neutral storefront where a skill purchase automatically provisions runtime, dependencies, secrets, scheduler/webhooks, logs, budgets, updates, and creator hosting revenue. ([OFFICIAL](https://promptbase.com/sell), [OFFICIAL](https://n8n.io/affiliates/), [OFFICIAL](https://creator.poe.com/docs/resources/how-we-cover-your-costs))

**Competitive signal.** Vercel launched AI agents/services with native installation, authentication, provisioning, unified billing, and observability in October 2025, validating demand for reduced integration friction. It is a competitor/adjacent platform, but its launch focuses on Vercel project integrations rather than a portable long-tail `SKILL.md`/automation creator economy. ([OFFICIAL](https://vercel.com/blog/ai-agents-and-services-on-the-vercel-marketplace))

**Product wedge.** “Buy → configure required secrets → deploy → test → run” with local/self-hosted and managed-cloud targets; transparent per-run costs; caps and approvals; creator share of net hosting margin; and an inexpensive open-source runtime option.

### Rank 2 — Cross-framework packaging and verified adapters (**high opportunity, partially de-risked by a standard**)

**What improved.** Anthropic introduced Agent Skills in October 2025 and published the format as an open standard for cross-platform portability in December 2025. The standard defines a folder containing `SKILL.md` with YAML metadata/instructions plus optional scripts, references, and assets; it also documents `.agents/skills/` as a cross-client discovery convention. ([OFFICIAL](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), [OFFICIAL](https://agentskills.io/specification), [OFFICIAL](https://agentskills.io/integrate-skills))

**Hermes fit.** Hermes skills use the same core `SKILL.md` + YAML frontmatter + optional resources/scripts model and support publishing/installing through its skills registry. This is strong structural compatibility, but no official Hermes↔Claude conversion guarantee or compatibility certification was found in the cited docs; extra metadata, command availability, tool names, environment variables, security policy, and filesystem conventions can still differ. ([OFFICIAL](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills/), [OFFICIAL](https://agentskills.io/specification))

**What remains fragmented.** GPTs use OpenAI-hosted GPT Content/Actions/configuration rather than the open folder standard; MCP servers expose tools/resources through a protocol and are complementary to instruction skills, not equivalent packages; n8n/Make/Zapier workflows each use platform-specific graph/integration formats. ([LEGAL](https://openai.com/policies/service-terms/), [OFFICIAL](https://modelcontextprotocol.io/registry/about), [OFFICIAL](https://docs.n8n.io/workflows/templates/))

**Product wedge.** Store one canonical manifest and generate/test adapters: Agent Skills/Hermes package, Claude paths, GPT build instructions/Actions schema where permitted, MCP wrapper, n8n import, and Docker/OCI deployment. Display “portable source” separately from “verified on version X.”

### Rank 3 — Trust, security, reproducibility, versioning, and updates (**high opportunity and enterprise prerequisite**)

**Observed gap.** The official MCP Registry is intentionally unopinionated, relies on self-reported metadata, does not scan actual server code, and expects downstream marketplaces to add ratings/curation. Agent Skills can execute code and official Anthropic guidance warns users to stick to trusted sources. ([OFFICIAL](https://modelcontextprotocol.io/registry/about), [OFFICIAL](https://claude.com/blog/skills))

OpenAI applies automated/human review and user reporting to GPTs, while PromptBase gives a narrow “works as described” refund policy; neither cited model constitutes reproducible testing across model/framework versions. ([OFFICIAL](https://openai.com/index/introducing-the-gpt-store/), [LEGAL](https://promptbase.com/tandcs))

**Product wedge.** Verified identity/domain, signed artifacts, immutable versions, changelogs, semantic compatibility ranges, dependency lockfiles/SBOM, static and malware scans, sandboxed permission tests, red-team results, model/version CI, usage-derived reliability, rollback, security advisories, and reviews restricted to verified purchasers/runs. Show last-tested date and environment, not only stars.

### Rank 4 — Enterprise procurement, governance, and private catalogs (**high-value medium/high opportunity**)

**Observed demand.** Anthropic added organization-wide skill management and partner-built skills; Vercel offers unified authentication/provisioning/billing; the MCP Registry explicitly anticipates private enterprise subregistries. ([OFFICIAL](https://claude.com/blog/skills), [OFFICIAL](https://vercel.com/changelog/introducing-ai-agents-and-services-on-the-vercel-marketplace), [OFFICIAL](https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/))

**Product wedge.** SSO/SAML/SCIM, role/approval policies, private/allowlisted catalogs, vendor onboarding and tax forms, purchase orders/invoices, DPAs/data-region controls, audit logs, secret isolation, per-team budgets, model allowlists, security questionnaires, indemnity/support/SLA tiers, and self-hosted control plane. Let enterprises buy one approved package while preserving creator licensing and update revenue.

### Rank 5 — Discovery, SEO, reputation, lifecycle, and community (**medium/high opportunity**)

**Observed gap/signals.** GPT Store discovery is trending/category/featured-list driven, and OpenAI’s launch said more than three million GPTs already existed; PromptBase’s 0%-fee seller link explicitly rewards creators for supplying their own traffic. These facts indicate that supply is abundant and demand/discovery is scarce. ([OFFICIAL](https://openai.com/index/introducing-the-gpt-store/), [OFFICIAL](https://promptbase.com/blog/zero-fees))

The official MCP Registry expects downstream marketplaces to supply ratings and curation, while Agent Skills now has an open standard and community/client ecosystem but not a universal commercial reputation graph. ([OFFICIAL](https://modelcontextprotocol.io/registry/about), [OFFICIAL](https://agentskills.io/home))

**Product wedge.** Indexable public pages, use-case landing pages, dependency/framework/model filters, side-by-side cost/reliability comparisons, curated collections, verified-run reviews, maintainer response metrics, favorites/follows, Q&A, bounties, templates/forks, public roadmaps, update feeds, and portable creator reputation. Reward useful maintenance and runtime success, not raw listing volume.

### Opportunity matrix

| Gap | User pain | Defensibility | Revenue fit | Priority |
|---|---:|---:|---:|---:|
| Deploy + managed hosting + creator usage share | Very high | High (runtime, billing, telemetry) | Very high | **1** |
| Cross-framework package/adapters | High | Medium/high (test matrix, conversion IP) | High | **2** |
| Trust/security/version/update system | Very high for executable artifacts | High (data + process + brand) | High | **3** |
| Enterprise procurement/private governance | High for teams | High | Very high, slower cycle | **4** |
| Discovery/reputation/community/SEO | High | Medium, rises with network effects | Medium/high | **5** |

---

## 4. Recent moves, 2024–2026

| Date | Move | Why it matters | Evidence |
|---|---|---|---|
| **2024-01-10** | OpenAI launched the GPT Store after users had created more than **3 million** GPTs; it promised an engagement-based US builder revenue program but did not publish the formula | Massive supply/distribution proof, but weak public creator-economic transparency | [OFFICIAL](https://openai.com/index/introducing-the-gpt-store/) |
| **2024-05-05** | AgentHub rebranded to **Gumloop** after pivoting away from its original idea: a central place to publish, host, and share autonomous-agent creations | A useful “shutdown/pivot” signal: the generic agent marketplace concept gave way to narrower, controllable workflow automation after user feedback | [OFFICIAL](https://www.gumloop.com/blog/agenthub-to-gumloop) |
| **2024-08-21** | Skyfire launched payment rails for AI agents and announced an **$8.5M seed round** | Infrastructure funding signal: autonomous payments, identity, limits, and controls are required for agent commerce | [NEWS](https://techcrunch.com/2024/08/21/skyfire-lets-ai-agents-spend-your-money/) |
| **2025-01-10** | Gumloop (formerly AgentHub) closed a **$17M Series A**, bringing total capital reported by TechCrunch to $20M | Investment shifted toward reliable, drag-and-drop AI automation with hosting/integrations rather than a pure listing marketplace | [NEWS](https://techcrunch.com/2025/01/10/gumloop-founded-in-a-bedroom-in-vancouver-lets-users-automate-tasks-with-drag-and-drop-modules/) |
| **2025-09-08** | Official MCP Registry launched in preview as an open catalog/API and upstream source for downstream subregistries/marketplaces | Standardized discovery lowers catalog-ingestion cost but leaves curation, security, ratings, private registries, and commerce to others | [OFFICIAL](https://blog.modelcontextprotocol.io/posts/2025-09-08-mcp-registry-preview/) |
| **2025-10-16** | Anthropic launched Agent Skills across Claude products/API | Made file/folder procedural capability a first-class product category | [OFFICIAL](https://claude.com/blog/skills) |
| **2025-10-23** | Vercel added AI Agents & Services to its Marketplace with unified install/auth/provisioning/billing/observability | Direct validation—and competition—for hosting-bundled agent distribution | [OFFICIAL](https://vercel.com/blog/ai-agents-and-services-on-the-vercel-marketplace) |
| **2025-10-30** | PromptBase introduced 0% platform fees on sales where the seller brings the buyer; normal marketplace fee remained 20% | Creator-friendly acquisition pricing and a useful benchmark for demand attribution | [OFFICIAL](https://promptbase.com/blog/zero-fees) |
| **2025-12-18** | Anthropic published Agent Skills as an open cross-platform standard and added organization-wide management / partner directory | Reduces format fragmentation among compatible clients, while opening a distribution layer above any one model vendor | [OFFICIAL](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), [OFFICIAL](https://agentskills.io/home) |
| **2026-03-12** | Gumloop raised a **$50M Series B** led by Benchmark to expand its enterprise agent/automation platform | Strong funding evidence for model-agnostic, controllable, hosted enterprise automation; also a well-funded adjacent competitor | [NEWS](https://techcrunch.com/2026/03/12/gumloop-lands-50m-from-benchmark-to-turn-every-employee-into-an-ai-agent-builder/) |
| **By 2026-08-08** | PromptBase’s seller page explicitly supports selling prompts **or agent skills (`SKILL.md`)** | Incumbent prompt marketplaces are moving up-stack into reusable agent capabilities | [OFFICIAL](https://promptbase.com/sell) |
| **By 2026-08-08** | OpenAI’s GPT service terms were updated 2026-06-12 but still disclosed no universal GPT-builder revenue split; the only verified launch statement remains engagement-based | GPT Store should not be used as a transparent payout benchmark | [LEGAL](https://openai.com/policies/service-terms/), [OFFICIAL](https://openai.com/index/introducing-the-gpt-store/) |

### Requested names that could not be verified cleanly

- **PromptBase funding:** a company profile exists in commercial directories, but no amount/round was verified from a PromptBase announcement or reputable news source in this review. Funding claims should be treated as **UNVERIFIED** rather than inferring that the company is bootstrapped or funded. ([DIRECTORY](https://www.crunchbase.com/organization/promptbase))
- **Shutdowns beyond the AgentHub→Gumloop pivot (`UNVERIFIED`):** no other notable 2024–2026 shutdown specific to a major prompt/skill/automation marketplace was verified to the primary/reputable-news standard in this targeted review. This is **not** a claim that none occurred internet-wide.

---

## 5. Positioning recommendation

Position the product as **the trusted deployment and commerce layer for portable agent capabilities**, not as another prompt gallery. Start with the open Agent Skills/`SKILL.md` ecosystem—where Hermes is structurally close—then add tested adapters for MCP and selected automation frameworks, while clearly labeling native versus converted compatibility. Offer a generous, transparent asset-sale split and make the durable business model metered managed hosting, update/support subscriptions, and enterprise private catalogs; share a defined portion of net hosting margin with creators. Make security, versioned reproducibility, cost visibility, self-hosting, and verified-run reputation the brand promise, because official registries deliberately leave those layers open and Vercel has already validated the value of unified deployment and billing. ([OFFICIAL](https://agentskills.io/home), [OFFICIAL](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills/), [OFFICIAL](https://modelcontextprotocol.io/registry/about), [OFFICIAL](https://vercel.com/blog/ai-agents-and-services-on-the-vercel-marketplace))
