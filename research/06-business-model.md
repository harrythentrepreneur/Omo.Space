# Business-model design: paid agent configs with hosted demo agents

**Research date:** 2026-08-08  
**Concept:** creators publish portable agent configuration packages (prompts, `SKILL.md` skills, workflows); the marketplace runs capped live demos and optionally hosts production use; buyers may license the package, keep it hosted, or both.  
**Evidence labels:** `OFFICIAL` first-party product/docs; `LEGAL` operative terms/policies/law; `NEWS` reputable reporting; `REVIEW` independent analysis; `UNVERIFIED` no current public number was verified. `MODELED` and `RECOMMENDATION` are this report's analysis, not observed market facts.

> **Scope and caveat.** This is a dated, targeted review, not an internet-wide completeness claim and not legal advice. “No public share/rate found” means none appeared in the cited public materials reviewed on 2026-08-08; private, invited, regional, or negotiated arrangements may exist. Provider terms change and should be re-reviewed by counsel immediately before launch.

## Executive decision

Use a **hybrid, transparent waterfall**, not an engagement pool:

1. **Portable license:** creator receives **85%** of marketplace-discovered license and maintenance revenue; **95%** when the creator supplies the buyer. Taxes, refunds, and chargebacks are excluded before the split; processing is disclosed separately or borne from the marketplace share.
2. **Hosted runs:** charge all-in variable cost plus a target **25% markup on cost** (20% gross margin on hosted revenue), then give the creator **20% of positive net hosting contribution margin**. No payout accrues on a loss and no later creator clawback is created.
3. **Optional future value fee:** after telemetry is trustworthy, let verified creators add a clearly disclosed per-success/per-session fee. Do not launch with arbitrary per-message creator pricing: it complicates comparison, refunds, and cost predictability.
4. **Buyer offer:** three-message capped demo → one-time portable license ($19–$99 typical proposed band) → optional $10/$25 prepaid hosting credits; separately sell update/support subscriptions and team/private-catalog control-plane plans.

This beats PromptBase’s verified **80/20** marketplace split without forcing thin hosted margin to subsidize unlimited demos. PromptBase also charges 0% when its creator supplies the buyer, so a 95/5 direct route is not the category’s cheapest but funds fraud, licensing, updates, and verified-run infrastructure ([OFFICIAL](https://promptbase.com/sell)).

---

## 1. Creator payout structures

### 1.1 Precedent and design matrix

| Payout structure | Verified precedent / number | What it rewards | Main weakness | Recommended use here |
|---|---|---|---|---|
| **Asset-sale royalty** | PromptBase: creator keeps **80%** on marketplace sales; platform fee **0%** through the seller’s own link; it explicitly lists prompts and `SKILL.md` skills ([OFFICIAL](https://promptbase.com/sell)). | Artifact quality and marketplace conversion | One-time, copyable, and may not pay for free-demo acquisition | **85/15 marketplace; 95/5 creator-referred**. Keep demo COGS capped and separately budgeted. |
| **Per-message / per-session royalty** | Poe creators can set a fixed message price or dynamically authorize/capture costs in **thousandths of a US cent**, converted to user compute points; Poe says creators can earn for every call and that it intends to cover model and other significant per-message costs. No universal percentage is published ([OFFICIAL](https://creator.poe.com/docs/server-bots/poe-bot-monetization-api-documentation), [OFFICIAL](https://creator.poe.com/docs/resources/how-we-cover-your-costs)). Poe pays via Stripe at **$10**, in **23 countries**, and offers subscriber-acquisition earnings ([OFFICIAL](https://poe.com/pages/demos/creator-monetization)). | Usage and expensive tool/model calls | Hard for buyers to predict; gaming and micro-refund complexity | Later-stage option: a displayed per-completed-session or per-success fee, not hidden token markup. |
| **Per-API-call/provider payout** | RapidAPI allows pay-per-use, subscription, and per-call overages; its current public API Hub fee is **25%**, so a $100 provider plan pays $75 before PayPal payout fees ([OFFICIAL](https://docs.rapidapi.com/docs/monetizing-your-api-on-rapidapicom), [OFFICIAL](https://docs.rapidapi.com/docs/payouts-and-finance)). | Callable service ownership | A 25% platform fee is high for low-cost config artifacts; providers still bear backend COGS | Useful precedent for an explicit creator value fee or metered MCP/tool service, not the default config split. |
| **Coze message billing / creator program** | Coze’s current documentation index exposes “Enable user message billing,” but no public creator payout rate, take rate, threshold, or global eligibility schedule was verifiable from the reachable official page ([UNVERIFIED](https://www.coze.com/open/docs/guides/subscription)). | Potentially bot usage | Geography/account differences and opaque payout economics | Do not benchmark a number from Coze; require a published rate card in this marketplace. |
| **Share of net hosting margin** | In the public Replit, Gumloop, Hugging Face Spaces, Relevance AI, and Vercel materials reviewed, hosting/compute is monetized but **no standard program paying template/config creators a percentage of hosting contribution margin was found**. This is a scoped negative finding, not proof no private deal exists ([OFFICIAL](https://replit.com/pricing), [OFFICIAL](https://www.gumloop.com/pricing), [OFFICIAL](https://huggingface.co/docs/hub/spaces-overview), [OFFICIAL](https://marketplace.relevanceai.com/), [OFFICIAL](https://vercel.com/blog/ai-agents-and-services-on-the-vercel-marketplace)). | Durable runtime value and maintainership | “Net margin” can become opaque; loss-making runs create disputes | **Genuinely differentiating:** 20% of a contractually defined, auditable positive contribution margin. |
| **Direct membership / subscription share** | Patreon’s standard plan for creators publishing after 2025-08-04 charges **10%** plus processing; USD domestic card processing is listed as **2.9% + $0.30**. Legacy platform fees are 5%, 8%, or 11% depending on plan ([OFFICIAL](https://support.patreon.com/hc/en-us/articles/11111747095181-Creator-fees-overview)). | Ongoing updates, access, support, community | Churn if updates are weak; many small subscriptions fatigue buyers | **85/15** on creator-specific maintenance/support subscriptions; do not allocate an opaque global pool. |
| **Attributable platform subscription** | Poe pays when a bot leads to a subscription, but publishes no universal acquisition amount/percentage; its earnings terms also support per-message earnings and adjust payouts for refunds, chargebacks, taxes, or fraud ([LEGAL](https://poe.com/pages/earnings-tos)). n8n pays **30% of net Cloud subscription revenue for 12 months** and Make advertises **35% for 12 months**, but these are affiliate commissions, not workflow royalties ([OFFICIAL](https://n8n.io/affiliates/), [OFFICIAL](https://www.make.com/en/affiliate)). | Demand generation | Rewards marketing rather than runtime quality; attribution disputes | Optional 5–10% referral credit from the marketplace’s own SaaS share for 12 months; keep separate from creator royalties. |
| **Subscription with no verified creator share** | Character.AI sells c.ai+ and its terms grant Character.AI a broad royalty-free, transferable, sublicensable, perpetual license to exploit/commercialize submitted Characters and generated content. No creator revenue-share schedule was found in the official plus page or terms reviewed ([OFFICIAL](https://character.ai/plus), [LEGAL](https://character.ai/tos)). | Platform subscription economics | Creators supply engagement without a predictable economic claim | Counterexample: publish a contractual creator formula rather than relying on platform discretion. |
| **Hybrid** | PromptBase proves asset sales; Poe proves metered creator earnings; Patreon proves recurring creator subscriptions; hosted workflow platforms prove recurring execution demand. No cited incumbent combines all with a transparent hosting-margin share. | Artifact, usage, maintenance, and acquisition | More ledgers, taxes, fraud controls, and explanations | **Recommended:** 85/15 license + 85/15 maintenance + 20% of positive hosting margin; add creator-set value fees only after MVP. |

### 1.2 What 85/15 and 90/10 do to a $20 sale

**MODELED formula** (before fixed payroll/support):

`platform contribution per sale = price × platform share − payment fee − (demo COGS / paid conversion) − refund/fraud reserve`

The example uses a $20 license and Stripe’s current standard US domestic-card rate of **2.9% + $0.30**, or **$0.88** on $20 ([OFFICIAL](https://stripe.com/pricing)). Demo costs and conversion rates below are explicit scenarios, not claimed market averages.

| Scenario | Demo COGS / visitor | Visitor→sale | Demo COGS / sale | Refund/fraud reserve | 80/20 contribution | 85/15 contribution | 90/10 contribution |
|---|---:|---:|---:|---:|---:|---:|---:|
| Efficient | $0.03 | 10% | $0.30 | 2% ($0.40) | **$2.42** | **$1.42** | **$0.42** |
| Base | $0.05 | 5% | $1.00 | 3% ($0.60) | **$1.52** | **$0.52** | **−$0.48** |
| Costly | $0.20 | 3% | $6.67 | 3% ($0.60) | **−$4.15** | **−$5.15** | **−$6.15** |

**Implication.** At a plausible-but-unproven base scenario, 85/15 leaves only 2.6% of GMV before fixed costs and 90/10 loses money. Therefore a creator-friendly split is viable only if free demos have hard dollar caps, expensive tools are mocked/disabled, creators or a marketing budget fund excess demo COGS, or demo users preauthorize credits. Do not promise “free unlimited demos” and finance them from a 10–15% artifact take.

### 1.3 Recommended hosting-margin waterfall

Define in the creator agreement:

- `Hosted Revenue`: usage credits actually consumed, net of sales tax.
- `Variable COGS`: model tokens, tools/search/browser, sandbox/container/GPU, egress, and per-use payment/refund allocation.
- `Net Hosting Margin (NHM) = max(0, Hosted Revenue − Variable COGS)`.
- `Creator Hosting Payout = 20% × NHM`; marketplace retains 80% of NHM. No payout on a loss, no negative creator balance, and no cross-subsidization between creators.

**MODELED example:** a $10 credit pack with $8 of all-in consumed variable COGS produces $2 NHM; creator gets **$0.40** and marketplace **$1.60** before fixed costs. Pricing service at `COGS × 1.25` produces a 20% gross hosted margin. Publish each run’s revenue, COGS categories, creator share, and corrections; otherwise “net” is not trustworthy.

---

## 2. Buyer pricing structures

| Buyer structure | Expected conversion effect (directional) | Margin / operational implication | Recommendation |
|---|---|---|---|
| **Free demo with caps** | Widest top of funnel; removes install and secret setup before value is seen | Negative unit margin by design; attracts abuse and extraction. Conversion must be measured against demo COGS | One anonymous turn, three authenticated turns, **$0.05 target hard COGS cap per visitor**, no write-capable tools. Stop/ask for credits before cap, not after. |
| **Prepaid credit packs** | Lower commitment than a subscription; makes spend visible | Positive cash timing and budget control; breakage may help but should not be assumed. Payment fixed fees hurt tiny packs | $10 and $25 packs; meter dollars and show model/tool/sandbox line items. Target `COGS × 1.25`; auto-reload opt-in only. |
| **Per-session / per-message** | Strong cost transparency for sporadic users; repeated checkout causes friction | Aligns price to runtime, but “session” must be defined and long-context variance bounded | Meter internally per run/message but settle from credits. Show an estimated range and authorization cap before run. |
| **One-time config license** | Best for technical buyers who want control/self-hosting; checkout is a larger commitment than trying | High gross margin, low recurrence, piracy/refund disputes, and support ambiguity | $19–$99 proposed band by complexity; perpetual use for purchased version, no redistribution, clear seats/client-work rights. 85/15 split. |
| **License + optional hosted plan** | Lets users buy after proof and choose convenience; reduces fear of lock-in | Two revenue streams; hosted revenue can outlive the sale. Requires entitlement and version synchronization | **Primary offer.** Buy portable package, receive small starter credits, then top up or subscribe. “Export any time” is the trust promise. |
| **Open-core: self-host/community free, hosted paid** | Maximizes adoption and contribution; converts convenience/security buyers | Free package cannot fund creator directly; host must win on secrets, logs, updates, uptime, and governance | Use for community/open-source packages, not as the only path for proprietary creators. Offer one-click hosted deployment and paid verified builds. |
| **Maintenance/update subscription** | Converts buyers who need compatibility and support; weak if artifact rarely changes | High gross margin but creates response/compatibility obligations | Creator-defined $5–$25/month proposed band, or annual update entitlement; 85/15. List model/runtime compatibility and response SLA precisely. |
| **Seat/team subscription** | Easier recurring budget for teams than many card purchases | Control-plane margin can be strong; included credits can silently erase it | Proposed Team plan: base fee for shared secrets, logs, budgets, approvals, private installs; usage remains separately metered. |
| **Enterprise private catalog** | Lower self-serve conversion but higher ACV and retention when governance is required | Sales, security reviews, support, DPA/SLA, SSO and invoicing costs are material | Base platform fee + seats + metered usage + creator licenses; private/allowlisted catalog, SSO/SCIM, audit, model/data-region controls, invoice/PO. Quote rather than fake a public list price. |

### Recommended buyer ladder

1. **Explore — $0:** one anonymous / three authenticated read-only demo messages, capped at $0.05 COGS per visitor and a daily account cap.
2. **Own — $19–$99 per config:** portable versioned package, commercial-use scope shown on listing, verified-run report, no updates unless stated.
3. **Run — prepaid $10/$25:** all variable costs + 25% markup on cost; estimates and hard authorization caps; creator receives 20% of positive NHM.
4. **Maintain — creator-priced $5–$25/month:** updates/support/compatibility entitlement, 85/15 split.
5. **Team / Enterprise:** shared secret vault, budgets, approvals, private catalogs, audit, policy/model allowlists, DPA/SLA; base fee plus seats, usage, and creator licenses.

The pricing test should optimize **contribution after demo COGS**, not raw demo-to-signup conversion. Report conversion by listing, demo cost, successful-run rate, refund rate, and 30/90-day hosted retention.

---

## 3. Possibility space: novel versus combined

The three primitives are: **A** paid transferable config, **D** live try-now demo, **H** recurring hosted execution.

| Platform/category | A | D | H | What it proves / does not prove |
|---|:---:|:---:|:---:|---|
| PromptBase | ✓ | — | — | Paid prompts/skills and a clear split; no bundled managed production runtime in the reviewed offer ([OFFICIAL](https://promptbase.com/sell)). |
| Poe | — | ✓ | ✓ | Live bots, points/message pricing, subscription acquisition, inference-cost support; buyer does not acquire a portable config ([OFFICIAL](https://poe.com/pages/demos/creator-monetization)). |
| Relevance AI / Gumloop | — | ✓ | ✓ | Cloneable/free agents or templates plus paid hosted runs; no public per-template artifact royalty verified ([OFFICIAL](https://marketplace.relevanceai.com/), [OFFICIAL](https://www.gumloop.com/templates), [OFFICIAL](https://www.gumloop.com/pricing)). |
| Hugging Face Spaces | — | ✓ | ✓ | Public demos and paid hosting/compute; no general paid config transfer or creator share of host margin found ([OFFICIAL](https://huggingface.co/docs/hub/spaces-overview), [OFFICIAL](https://huggingface.co/pricing)). |
| Replicate | — | ✓ | ✓ | Model demos and pay-per-use inference, not a portable prompt/skill license market ([OFFICIAL](https://replicate.com/explore), [OFFICIAL](https://replicate.com/pricing)). |
| Vercel AI templates/marketplace | — | partial | ✓ | Free deployable source and unified install/auth/provisioning/billing; no universal config-sale or creator hosting-share formula published ([OFFICIAL](https://vercel.com/blog/ai-agents-and-services-on-the-vercel-marketplace)). |
| AWS Marketplace agents/tools | partial | varies | ✓ | Real PAYG/contracts/private offers and deployment, but not a simple portable long-tail config-file purchase with transparent creator margin sharing ([OFFICIAL](https://aws.amazon.com/marketplace/solutions/ai-agents-and-tools)). |

**Merely combined:** paid digital assets, free capped trials, usage credits, memberships, hosted workflow execution, and enterprise private procurement all have precedent.

**Genuinely differentiating in the reviewed set:** the **same versioned portable config SKU** can be (1) tried live, (2) purchased/exported, and (3) kept hosted, while its creator receives a published share of positive hosting contribution margin. Add cross-runtime verified runs, signed versions, cost telemetry, and rollback, and the defensible product is the trust/deployment ledger—not the checkout page. No exact A+D+H implementation with a public creator hosting-margin formula was verified in the cited catalog; this is a scoped finding, not an internet-wide claim.

---

## 4. Legal / ToS reality check for demo hosting

### 4.1 Provider-by-provider

| Provider | Serving public/end users | Raw resale / charging reality | Key launch obligations |
|---|---|---|---|
| **OpenAI API** | The 2026 Services Agreement expressly lets a customer integrate the API into Customer Applications and make those applications available to End Users ([LEGAL](https://openai.com/policies/business-terms/)). | Charging for a value-added agent application is contemplated by the customer-application model. But the customer may not resell/lease account access or buy, sell, or transfer API keys. A generic key/model passthrough is therefore the wrong product shape ([LEGAL](https://openai.com/policies/business-terms/)). | Marketplace is responsible for end-user activity, rights in inputs, evaluating output, supported territories, and usage-policy enforcement ([LEGAL](https://openai.com/policies/business-terms/), [LEGAL](https://openai.com/policies/usage-policies/)). |
| **Anthropic API** | Commercial Terms A.1 expressly permits using Services to power products/services made available to the customer’s own users ([LEGAL](https://www.anthropic.com/legal/commercial-terms)). | The same terms prohibit using the Services to build a competing product or **“resell the Services except as expressly approved by Anthropic.”** A specialized demo agent is stronger than raw resale, but a marketplace whose core offer is paid Claude access should obtain written approval before launch ([LEGAL](https://www.anthropic.com/legal/commercial-terms)). | Flow down the Usage Policy to users; disclose AI at the beginning of every consumer-facing chat; implement qualified human review and disclosures for specified high-risk uses; Anthropic’s policy explicitly applies to pass-through access and MCP servers ([LEGAL](https://www.anthropic.com/legal/aup)). |
| **Google Gemini API** | Gemini terms contemplate API Clients made available to users in available regions, but say the developer service is for professional/business purposes, not consumer use; an API Client may not be directed toward or likely accessed by under-18s. Paid Services are required for end-user apps in the EEA, Switzerland, and UK ([LEGAL](https://ai.google.dev/gemini-api/terms)). | Google’s general API terms prohibit sublicensing an API and prohibit an API Client that functions substantially the same as the API and is offered to third parties. A use-case-specific agent/workflow is safer than a generic Gemini proxy; no explicit creator-marketplace approval is supplied by the terms ([LEGAL](https://developers.google.com/terms)). | Require end-user compliance, privacy policy/security, region/age gates, paid project where required, and safety controls. For agentic services, Google says the developer is solely responsible for actions/tasks and must not automatically bypass human confirmations ([LEGAL](https://ai.google.dev/gemini-api/terms), [LEGAL](https://policies.google.com/terms/generative-ai/use-policy)). |

### 4.2 Three non-negotiable conclusions

1. **A paid end-user application is not the same as reselling raw API access.** OpenAI explicitly permits customer applications; Anthropic permits powered products but separately restricts resale; Google forbids sublicensing/substantially identical API clients. Sell the specialized agent outcome/config, keep keys server-side, add material orchestration/UI/safety, and seek written approval when the commercial substance could look like model-access resale.
2. **The marketplace is the API customer and cannot contract away provider responsibility.** It must enforce policies against creators and end users, handle supported regions/ages, disclose AI where required, supervise high-risk/agentic actions, and bear suspension risk. Creator indemnities allocate loss internally but do not bind providers or injured third parties.
3. **Use commercial APIs, never automated consumer subscriptions.** Anthropic’s consumer terms prohibit automated/non-human access except through an API key or explicit permission and forbid reselling consumer Services ([LEGAL](https://www.anthropic.com/legal/consumer-terms)). OpenAI’s API/business agreement, not a ChatGPT seat, governs public hosted demos ([LEGAL](https://openai.com/policies/business-terms/)). Consumer UI automation is not a cheap hosting backend.

### 4.3 MCP and component licensing

MCP is an interoperability protocol, not a commercial license for every server. The official Registry is an upstream metadata source and does not make each listed server open source, safe, or commercially reusable ([OFFICIAL](https://modelcontextprotocol.io/registry/about)). The MCP project’s own license transition (Apache-2.0 for new code/spec contributions, CC-BY-4.0 for most docs, legacy MIT where not relicensed) does not flow automatically to third-party servers ([LEGAL](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/LICENSE)).

Require per-component SPDX/license and provenance for `SKILL.md`, scripts, assets, datasets, models, MCP server, dependencies, and every upstream API/data source. Review whether a remote server’s API terms allow commercial passthrough or resale; registry presence is not permission. Require SBOM/lockfiles, permissions and network destinations, secret scopes, source URL, signed version, vulnerability/sandbox result, and seller warranty of licensing authority.

---

## 5. Risks and mitigations

| Risk | Why the marketplace owns material exposure | MVP mitigation / contract design |
|---|---|---|
| **Prompt/skill extraction** | A live demo exposes behavior and can be prompt-injected; static prompt copyright may be thin—the U.S. Copyright Office says a prompt may itself be protectable only when sufficiently original, while prompts alone generally do not make the user author of model output—and server-side storage cannot prevent behavioral cloning ([LEGAL](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf)). | Never promise secrecy. Keep config server-side; redact debug/traces; run extraction/jailbreak evals; rate-limit and cap context; use canary phrases/watermarks where appropriate; serve reduced demo capabilities; prohibit redistribution/scraping contractually; sell updates, support, reputation, and verified operation—not “unstealable text.” |
| **Chargebacks/refunds** | Digital delivery is immediate; demos and usage incur irreversible COGS; Poe and RapidAPI both explicitly adjust/withhold payouts around refunds, disputes, fraud, or final settlement ([LEGAL](https://poe.com/pages/earnings-tos), [OFFICIAL](https://docs.rapidapi.com/docs/payouts-and-finance)). | 30-day rolling seller reserve; payout only after settlement; device/account risk scoring; 3DS where useful; immutable delivery/run logs; clear “works as described” acceptance tests; refund artifact sales for material misdescription/nonfunction, not buyer preference; consumed usage nonrefundable except outage/error or law. |
| **Quality / model drift** | A prompt that worked on one model/date may fail later; stars do not prove reproducibility | Require test fixtures and declared expected outcome; sandbox run before publish; show model/runtime/version, date, latency, COGS and pass rate; re-test on model changes; signed immutable versions, changelog, compatibility range, rollback; “verified” expires. |
| **Harmful agent actions** | Provider contracts place end-user/content/policy duties on the marketplace API customer; Google expressly assigns agentic task/action responsibility to the developer, while Anthropic requires review/disclosure for high-risk uses ([LEGAL](https://ai.google.dev/gemini-api/terms), [LEGAL](https://www.anthropic.com/legal/commercial-terms), [LEGAL](https://www.anthropic.com/legal/aup)). | MVP is read-only, sandboxed, no payments/email posting/deletion/browser purchase, and no high-risk decisions. Later: least-privilege scopes, dry-run previews, allowlists, per-action confirmations that cannot be bypassed, spend/rate caps, audit/undo, emergency kill switch, incident response and appropriate insurance. Creator warranty/indemnity plus buyer terms; do not imply these eliminate statutory/tort exposure. |
| **Moderation and illegal content** | Every listing and user turn can breach model policies; broad public catalog increases impersonation, IP, fraud, minors, sexual, cyber, and high-risk harms | Identity and tax verification for paid creators; automated static/malware/policy scan plus human review for risky categories; runtime input/output moderation; AI disclosure; age/region gates; user reports and appeal; DMCA/trademark/impersonation process; repeat-infringer policy; quarantine/kill switch; preserve audit evidence with privacy limits. |
| **Cost abuse / margin inversion** | Long context, loops, retries, browser/search/tools and adversarial users can exceed the displayed price | Pre-run cost estimate and authorization; max tokens/tool calls/wall time; budget circuit breaker; per-user/IP/device caps; no negative creator balances; itemized COGS; prohibit unbounded recursion; seller-visible test bill. |
| **License/provenance failure** | A package can mix proprietary prompt text, OSS code, datasets, brand assets, and unlicensed MCP/API access | Component-level license manifest; seller authority warranty; automated dependency/license scan; manual review for trademarks/celebrity personas; takedown/counter-notice; suspend payouts during credible disputes; signed provenance attestations. |
| **Opaque “net” calculations** | Creators cannot audit a margin share if the marketplace can allocate arbitrary overhead | Define NHM narrowly to actual variable run costs; do not deduct general payroll/marketing; provide per-run ledger/export; state correction window; independent audit right above a revenue threshold; version payout formula prospectively, not retroactively. |

### Responsibility stack

- **Model provider:** responsible only within its contract; disclaims broad accuracy/warranty and can suspend service ([LEGAL](https://openai.com/policies/business-terms/), [LEGAL](https://www.anthropic.com/legal/commercial-terms)).
- **Marketplace:** provider customer, merchant/platform operator, demo publisher, meter, moderator, and the party controlling runtime safeguards; it has the greatest practical external exposure.
- **Creator:** warrants authority, accurate listing claims, declared dependencies/permissions, policy-compliant intended use, and safe tests; indemnifies marketplace for specified breaches to the extent enforceable.
- **Buyer/end user:** agrees to permitted use, verifies outputs, supplies lawful inputs/secrets, and confirms consequential actions.

Contracts allocate risk but do not erase duties to consumers, regulators, or injured third parties. Product controls are the primary mitigation.

---

## 6. Concrete recommendation

### 6.1 Payout mix

- **Marketplace-discovered license and maintenance:** **85% creator / 15% marketplace** on net sale receipts excluding tax, refunds, and chargebacks.
- **Creator-referred license and maintenance:** **95% / 5%**, with no marketplace-funded free-demo allowance beyond a minimal global cap.
- **Hosted demo/production usage:** pass through itemized all-in variable COGS; target 25% markup on cost; creator gets **20% of positive NHM**, marketplace 80%.
- **Payout operations:** monthly, after a 30-day rolling reserve; $25 threshold proposed; KYC/tax/unsupported-region controls; adjustments only for documented refunds, chargebacks, fraud, or metering errors.
- **Later:** verified creators may add a disclosed per-success/session value fee. Do not use an opaque engagement pool or promise a per-message rate before fraud and completion semantics are proven.

### 6.2 MVP scope (first 90–120 days)

1. **One artifact:** native `SKILL.md` package with instructions, optional scripts/references/assets, manifest, license, lockfile, declared tools/secrets, and immutable versions. Defer broad automatic GPT/n8n/MCP conversion.
2. **One safe runtime shape:** text/document transformation and retrieval in a network-restricted sandbox; no arbitrary MCP, browser, payments, posting, deletion, healthcare/legal/financial decisions, or minors.
3. **One commercial API path initially:** server-side business/API credentials, value-added agent UI, end-user terms and policy enforcement. Obtain provider counsel/approval before enabling Anthropic- or Google-backed paid public demos whose economics could resemble model resale.
4. **Core trust layer:** publish-time static/license/malware scan, creator identity, test fixture, verified run with model/version/date/cost, buyer review only after verified purchase/run, rollback, report/takedown/kill switch.
5. **Core commerce:** capped free demo, $19–$99 licenses, $10/$25 prepaid credits, 85/15 license split, transparent NHM ledger, monthly delayed payout. Add maintenance subscriptions only after version/update delivery works.

### 6.3 Go/no-go unit gates

- Free demo COGS target **≤$0.05 per visitor** and per-listing hard cap.
- Demonstrated paid conversion sufficient that demo COGS per sale stays below half the platform’s license take.
- Hosted run gross margin target **≥20% before creator NHM share**; suspend or reprice listings below target.
- Verified-run pass rate, refund/chargeback rate, policy incident rate, and 30/90-day hosted retention shown by listing and creator.
- No write-capable external action until confirmation, least-privilege, audit, and kill-switch controls pass red-team tests.

### 6.4 Positioning (3–5 sentences)

**The trusted try-before-you-deploy marketplace for portable agent capabilities.** Every listing is a versioned config package you can test live, buy and export, or keep running on managed infrastructure—without surrendering portability. Verified runs show exactly which model/runtime passed, what permissions it needs, and what it costs; signed versions, budgets, and rollback make the runtime trustworthy. Creators earn from licenses, maintenance, and a transparent share of positive hosting margin, so the marketplace rewards useful operation rather than listing volume.
