# Unit economics for thin-margin hosted demo agents

**Research date / target date:** 2026-08-08  
**Scope:** selective, evidence-backed public list prices and explicit estimates for a marketplace-hosted demo runtime. This is **not an internet-wide completeness claim**. USD unless stated. Taxes, card fees, refunds, support, observability, egress, storage, paid search/tool calls, and model-provider negotiated discounts are excluded unless explicitly included.

## Evidence and calculation rules

- **OFFICIAL pricing page / OFFICIAL docs:** first-party page retrieved directly. **REVIEW:** first-party URL was blocked and its text was inspected through a text mirror. **UNVERIFIED:** a current numeric value could not be extracted; no number is invented.
- **ESTIMATE:** workload or performance assumption, not a vendor promise. **DERIVED:** arithmetic from sourced prices and stated estimates.
- Model inference formula: `session LLM cost = input_tokens / 1,000,000 × input_rate + output_tokens / 1,000,000 × output_rate`.
- “Input” includes the instructions, conversation history, tool schemas/results, retrieved text, and browser state that actually reach the model. “Output” includes billable generated/reasoning tokens under each provider’s rules. Search, image, audio, grounding, and separately priced tools are excluded.
- Public list prices are volatile. DeepSeek explicitly warns of a near-term price increase; recheck at launch and pin a dated rate card.

---

## 1. LLM inference cost per demo session

### 1.1 Verified rate card: cheap-but-capable text tiers

| Provider / model (current ID) | Input / 1M | Cached input / 1M | Output / 1M | Evidence / notes |
|---|---:|---:|---:|---|
| OpenAI **GPT-5 mini** | $0.25 | $0.025 | $2.00 | [Official model page](https://developers.openai.com/api/docs/models/gpt-5-mini). Function calling supported. |
| OpenAI **GPT-5.4 mini** | $0.75 | $0.075 | $4.50 | [Official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini). Regional processing is +10%; excluded here. |
| Anthropic **Claude Haiku 4.5** | $1.00 | $0.10 read; $1.25 write | $5.00 | [Official pricing](https://www.anthropic.com/pricing#api). US-only inference is 1.1×; excluded. |
| Google **Gemini 3.5 Flash-Lite** (standard) | $0.30 | $0.03 | $2.50 | [Official Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing). Output includes thinking tokens. The page also shows a free tier and cheaper batch/flex rates; standard paid rate used here. |
| Google **Gemini 3.6 Flash** (standard) | $1.50 | $0.15 | $7.50 | [Official Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing). Output includes thinking tokens. |
| DeepSeek **V4 Flash** (cache miss) | $0.14 | $0.0028 | $0.28 | [Official pricing](https://api-docs.deepseek.com/quick_start/pricing). Current successor to the requested V3/R1-class comparison; supports thinking/non-thinking and tool calls. |
| DeepSeek **V4 Pro** (cache miss) | $0.435 | $0.003625 | $0.87 | [Official pricing](https://api-docs.deepseek.com/quick_start/pricing). Page warns overall API pricing is expected to rise. |
| Self-hosted **Qwen/Llama 7–8B quantized on Modal L4** | **$0.222 DERIVED** | n/a | **$2.22 DERIVED** | Modal L4 is $0.000222/sec ([official](https://modal.com/pricing)). **ESTIMATE:** hot single-stream prefill 1,000 input tok/s and decode 100 output tok/s under llama.cpp/vLLM. Effective input = `$0.000222 × 1,000,000/1,000`; output = `$0.000222 × 1,000,000/100`. Excludes cold start, idle time, CPU/RAM, batching gains, and ops. These are planning assumptions, not benchmark claims. |

**Why current IDs differ from the examples in the brief.** “GPT-5.x mini,” “Haiku,” “Flash,” and “DeepSeek V3/R1” describe families, not stable price IDs. The table uses the canonical models exposed on official pages on 2026-08-08 rather than assigning a newer price to an older alias.

### 1.2 Session token scenarios (ESTIMATE)

| Scenario | Input tokens | Output tokens | Assumption |
|---|---:|---:|---|
| **Low — simple chat / QA** | 4,000 | 500 | system prompt + one or two turns + short answer; no paid tools |
| **Mid — tool-calling agent** | 8,000 | 1,500 | instructions, tool schemas, two to four tool/result turns, concise final answer |
| **High — browser agent** | 20,000 | 4,000 | multiple DOM/page excerpts, action loop and larger reasoning/final output; browser fee is separate |

These are not token guarantees. An implementation should meter actual uncached/cached input, output/reasoning, tool calls, retries, and model fallback per run.

### 1.3 Core 3 × 3 per-session model-cost table

Every cell is **DERIVED** using the formula above; it is **LLM only**.

| Scenario | Economy: DeepSeek V4 Flash ($0.14/$0.28) | Mainstream mini: GPT-5 mini ($0.25/$2.00) | Premium small: Haiku 4.5 ($1/$5) |
|---|---:|---:|---:|
| Low: 4k in / 0.5k out | **$0.00070** | **$0.00200** | **$0.00650** |
| Mid: 8k in / 1.5k out | **$0.00154** | **$0.00500** | **$0.01550** |
| High: 20k in / 4k out | **$0.00392** | **$0.01300** | **$0.04000** |

Example: GPT-5 mini mid = `8,000/1M × $0.25 + 1,500/1M × $2.00 = $0.002 + $0.003 = $0.005/session`.

### 1.4 Other budget comparisons

| Scenario | Gemini 3.5 Flash-Lite | Self-host L4 estimate |
|---|---:|---:|
| Low | **$0.00245 DERIVED** | **$0.001998 DERIVED** (9 GPU-sec) |
| Mid | **$0.00615 DERIVED** | **$0.005106 DERIVED** (23 GPU-sec) |
| High | **$0.01600 DERIVED** | **$0.013320 DERIVED** (60 GPU-sec) |

Self-host time formula is **DERIVED from ESTIMATE**: `GPU seconds = input/1,000 + output/100`; cost = `GPU seconds × $0.000222`. It is not automatically cheaper at low volume: idle/cold-start and operations can dominate, while continuous batching can improve economics at sustained demand.

---

## 2. Hosting cost per session

The figures below reuse the official prices captured in `02-hosting-infra.md`, with per-session assumptions made explicit. Included monthly allowances can make early marginal cash cost zero, but they are scarce subsidy capacity—not a durable $0 unit cost.

### 2.1 Stateless control plane / serverless orchestration

| Platform | Sourced rate | Per-session assumption and DERIVED cost |
|---|---|---|
| **Cloudflare Workers Paid** | 10M requests + 30M CPU-ms included/month; overage $0.30/M requests and $0.02/M CPU-ms; $5/month minimum ([official](https://developers.cloudflare.com/workers/platform/pricing/)) | **$0.00000130 marginal** after allowance: one request + 50 CPU-ms = `$0.30/1M + 50×$0.02/1M`. Fixed $5 not allocated. |
| **Vercel Functions, Portland** | $0.128/active CPU-hour, $0.0106/GB-hour memory, $0.60/M invocations; Hobby includes 1M invocations ([official docs](https://vercel.com/docs/functions/usage-and-pricing), updated 2026-06-16) | **$0.00005088**: 1 CPU-sec + 0.5 GB for 10 wall-sec + one invocation = `1/3600×.128 + .5×10/3600×.0106 + .60/1M`. Pro subscription/credit not allocated. |
| **Railway** | CPU $0.00000772/vCPU-sec, memory $0.00000386/GB-sec; Free becomes $1/month after trial, Hobby $5 minimum with credits ([official](https://railway.com/pricing)) | **$0.00011580**: 0.25 vCPU + 0.5 GB for 30 sec = `(.25×.00000772 + .5×.00000386)×30`. Minimum/idle allocation excluded. |

**Interpretation:** for an API-orchestrated demo, control-plane compute is normally sub-$0.0002/session; model, browser, sandbox, paid search, and idle minimums matter more.

### 2.2 Sandboxed code execution

**ESTIMATE:** one 5-minute sandbox, 2 vCPU + 2 GiB unless noted; storage/egress excluded.

| Sandbox | Sourced rate | DERIVED 5-minute cost |
|---|---|---:|
| **E2B** | 2 vCPU $0.000028/sec; RAM $0.0000045/GiB-sec; Hobby free + usage with one-time $100 credit; max 1-hour session ([official](https://e2b.dev/pricing)) | **$0.01110** = `(.000028 + 2×.0000045)×300` |
| **Daytona** | vCPU $0.000014/sec; RAM $0.0000045/GiB-sec; first 5 GiB storage free ([official](https://www.daytona.io/pricing)) | **$0.00690** = `(.000014 + 2×.0000045)×300` |
| **Modal Sandbox, minimal CPU example** | $0.0000131/core-sec and $0.00000222/GiB-sec; Sandboxes use Modal compute pricing ([pricing](https://modal.com/pricing), [docs](https://modal.com/docs/guide/sandboxes)) | **$0.000824** = `(.125 core×.0000131 + .5 GiB×.00000222)×300`; minimal resources, not equivalent to the 2-vCPU rows |

The correct product default is **no sandbox unless the listing declares code execution**. A five-minute E2B/Daytona session can cost more than a mid-tier LLM call.

### 2.3 Managed browser

**ESTIMATE:** one 10-minute browser session; proxy, CAPTCHA, model-gateway and search costs excluded.

| Browser | Sourced rate | DERIVED 10-minute cost |
|---|---|---:|
| **Browserbase Developer** | $20/month includes 100 browser-hours, then $0.12/browser-hour; Free has 1 browser-hour, 3 runs and 15 min/session ([official](https://www.browserbase.com/pricing)) | **$0.03333 allocated** = `$20/100h × 1/6h`; **$0.02000 marginal overage** = `$0.12×1/6` |
| **Cloudflare Browser Rendering / Browser Run** | Free 10 browser-min/day; Workers Paid includes 10 browser-hours/month, then $0.09/hour ([official](https://developers.cloudflare.com/browser-run/pricing/)) | **$0.01500 overage** = `$0.09×1/6`; within allowance marginal cash cost is $0 but allowance is finite |

A self-hosted Playwright browser avoids a managed-browser rate but shifts cost, isolation, patching, proxy/egress and abuse risk to the marketplace; it is not treated as free.

---

## 3. Subsidy precedents

| Platform | How demos/free use are subsidized | Evidence and implication |
|---|---|---|
| **Hugging Face Spaces** | CPU Basic is listed as **Free**; paid hardware is billed by the minute. The docs allow applications for free GPU upgrades/community GPU grants. PRO is $9/month and advertises 8× ZeroGPU quota and 20× included inference credits. | [Spaces hardware docs](https://huggingface.co/docs/hub/spaces-gpus), [HF pricing](https://huggingface.co/pricing). This is capped/queued/grant-based subsidy, not unlimited production GPU. Free hardware sleeps after inactivity. |
| **Poe** | Poe says its intent is to cover model inference and other significant per-message bot costs. Creators can set flat or code-determined earnings per message; Poe can make custom arrangements for non-catalog/self-hosted models. | [Cost coverage](https://creator.poe.com/docs/resources/how-we-cover-your-costs), [creator monetization](https://creator.poe.com/docs/resources/creator-monetization). Precedent: platform bundles inference subsidy and creator payout into a point/message economy rather than exposing raw API bills. |
| **Coze** | Coze distributes bots/templates and uses platform resource/credit plans, but the current official pricing/credit documentation was JavaScript-only and returned no dependable numeric allowance in retrieval. | [Official pricing route](https://www.coze.com/open/docs/guides/pricing), **UNVERIFIED numeric current credits**. Treat “Coze gives N credits” claims as stale until verified in-product; precedent is credit-gated execution, not a verified amount. |
| **Replit** | Starter is free with daily Agent credits, monthly cloud credits and one published project; Core is $20/month annually ($25 monthly) with $25 monthly credits. Starter docs say Agent credits reset daily up to a monthly cap and the one free published link goes down after 30 days. | [Official pricing](https://replit.com/pricing), [Starter docs](https://docs.replit.com/billing/plans/starter-plan). Precedent: daily + monthly caps and a time-limited free deployment, followed by paid credit packs/plans. |
| **OpenAI / ChatGPT Free** | Free users can use chat capabilities and GPTs, but GPT access pauses when the current free-tier model limit is reached; reset timing is shown in-product. Current Instant access is limited within a 5-hour window and can be dynamic; no fixed universal message count is published. | [Official FAQ](https://help.openai.com/en/articles/9275245-using-chatgpt-s-free-tier-faq), [model limits](https://help.openai.com/en/articles/11909943-gpt-5-in-chatgpt). Direct page was blocked in curl; content checked through text mirror, so **REVIEW** provenance. Precedent: dynamic quota/fallback, not guaranteed messages. |
| **Anthropic / Claude Free** | Free consumer plan is $0. Anthropic says every plan has rolling 5-hour usage limits; usage depends on conversation length/complexity and model/features, so there is no fixed message count. | [Official pricing/plan FAQ](https://www.anthropic.com/pricing). Precedent: context-sensitive rolling quota; paid plans increase capacity rather than promising infinite use. |

**Marketplace lesson:** subsidy is normally constrained by daily/rolling limits, credits, queue priority, sleeping demos, model fallback, or grants. No cited precedent supports unlimited anonymous premium-agent execution.

---

## 4. Break-even math at an 80/20 creator split

Assume creator gets `80% × buyer price`, platform gets `20% × buyer price`, and the **platform pays all run COGS `C`**. Ignore payment fees/tax/refunds here.

- Per-session price floor: **`P_min = C / 0.20 = 5C`**.
- Ten-session pack floor: **`Pack10_min = 10C / 0.20 = 50C`**.
- At buyer price `P`, the maximum run cost the 20% take can absorb is **`0.20P`**. Thus $0.01/session covers at most $0.002 COGS; $0.05 covers $0.01; $0.10 covers $0.02; $0.25 covers $0.05.
- This split is economically harsh for usage: the creator gets 80% even though the platform incurs 100% of inference/hosting. A safer waterfall is **pass-through COGS first, then split net contribution**, or separate the asset-sale royalty from hosted-usage margin.

### 4.1 Three concrete stacks

| Stack (all assumptions above) | LLM | Hosting add-ons | `C` / session | Required price `5C` | Required 10-pack `50C` |
|---|---:|---:|---:|---:|---:|
| **Economy chat:** DeepSeek low + Workers | $0.000700 | $0.0000013 | **$0.0007013** | **$0.00351** | **$0.03507** |
| **Balanced tool agent:** GPT-5 mini mid + Vercel + 5-min Daytona | $0.005000 | $0.0069509 | **$0.0119509** | **$0.05975** | **$0.59754** |
| **Browser agent:** GPT-5 mini high + Vercel + 10-min Cloudflare browser overage | $0.013000 | $0.0150509 | **$0.0280509** | **$0.14025** | **$1.40254** |

These floors produce **zero contribution before** payment processing, support, refunds, observability, storage and fraud. Microtransactions at fractions of a cent are impractical; meter internally and sell credit packs.

### 4.2 Usage-capped free demos

For **5 free sessions/day per active buyer**, marketplace subsidy is `5C/day`; at a 30-day active month it is `150C/month`.

| Stack | 5 free/day | 30-day maximum per active buyer |
|---|---:|---:|
| Economy chat | **$0.00351/day** | **$0.10520/month** |
| Balanced tool agent | **$0.05975/day** | **$1.79263/month** |
| Browser agent | **$0.14025/day** | **$4.20763/month** |

A million “free sessions” would therefore not have one universal cost: it is **$701** for the economy stack, **$11,951** for the tool stack, or **$28,051** for the browser stack, **DERIVED as `1,000,000 × C`**. This is why quotas must be capability- and model-aware.

---

## 5. Abuse and cost-runaway risks

| Risk | Economic failure mode | Required mitigations |
|---|---|---|
| **Prompt/config extraction** | A user repeatedly probes the live demo until proprietary instructions/workflows are reproduced, then avoids purchase. Prompt injection can reveal system behavior and sensitive data; no prompt is a perfect DRM boundary. | Never return raw config; strip system/tool traces; use output classifiers/canaries; limit turns and response length; watermark/version demo behavior; make paid value include files, updates, support and deployment—not only a secret prompt. See [OWASP prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/). |
| **Credential misuse / API-key reselling** | A leaked provider/tool key can be replayed outside the demo and create unbounded third-party charges. | Keep keys server-side; short-lived scoped tokens; per-listing service accounts; egress allowlists; rotate/revoke; never expose provider credentials to browser code; bind tool actions to authenticated user/session. |
| **Rate-limit bypass / Sybil accounts** | Attackers multiply the free allowance with accounts, IPs, devices or concurrent requests. | Require verified account before expensive tools; quotas by user + organization + payment instrument + risk signals; concurrency caps; velocity checks; CAPTCHA only where appropriate; no anonymous browser/code sessions. |
| **Infinite/retry loops** | Tool failures, recursive agents or attacker prompts consume tokens, browser minutes and sandbox seconds until budget exhaustion. | Hard limits on wall time, steps/tool calls, input/output tokens, retries and per-session dollars; cancellation propagation; idempotency keys; circuit breakers; kill sandboxes/browser at deadline. Cloudflare explicitly recommends per-invocation CPU limits against denial-of-wallet ([official pricing docs](https://developers.cloudflare.com/workers/platform/pricing/)). |
| **Expensive model/tool escalation** | Seller config selects premium models, search, CAPTCHA, proxies, images, code or browser without buyer-visible pricing. | Manifest-declared capability budget; demo-only model allowlist (mini/flash); deny premium fallback by default; price paid search/browser/sandbox separately; creator cannot override platform budget. |
| **Cache poisoning / giant context** | Attackers force unique huge prompts so caches miss or poison shared responses; long tool/browser output multiplies input cost. | Cache only deterministic public outputs with tenant-safe keys; canonicalize; cap retrieved/browser text; summarize state; prompt caching where safe; never cross-tenant cache secrets. |

**Operating controls:** prepaid credit packs, per-user/day and per-listing/month quotas, streaming-only responses with disconnect cancellation, hard spend alerts at 50/75/90/100%, automatic model downgrade, global daily loss cap, real-time cost ledger, and a provider-level billing ceiling where available. Streaming is a UX/control technique, not itself a discount: charge still follows consumed tokens unless cancellation stops generation.

---

## 6. Bottom line: what “thin margins” means

1. **LLM-only cheap-tier cost is genuinely sub-cent for many sessions.** In this model, DeepSeek V4 Flash is **$0.00070–$0.00392/session**; GPT-5 mini is **$0.002–$0.013**; Gemini Flash-Lite is **$0.00245–$0.016**. Haiku 4.5 reaches **$0.040** in the browser-token scenario. Thus **roughly $0.001–$0.02/session** is a defensible thin-margin COGS range for capped non-premium demos—not for every agent.
2. **Control-plane hosting is nearly noise; specialized execution is not.** Workers/Vercel/Railway orchestration is about **$0.000001–$0.000116/session** under the stated assumptions, while a five-minute Daytona sandbox is **$0.0069**, E2B **$0.0111**, and ten managed browser minutes about **$0.015–$0.033**.
3. **Cheapest viable default:** Cloudflare Workers, DeepSeek V4 Flash (or Gemini Flash-Lite/GPT-5 mini where quality/terms justify it), no browser/sandbox by default, 4k/500 token target, hard step/token/dollar caps, safe caching, streaming cancellation, authenticated quotas and prepaid credit packs. Planning COGS is about **$0.00070/session** for the DeepSeek example before fixed minimums and operations.
4. **Do not give 80% of gross usage revenue to creators while the marketplace pays all COGS.** At a 20% gross take, buyer price must be **5× run cost merely to break even**. Prefer pass-through model/tool cost plus a visible hosting markup, then share **net** margin; keep 80/20 for asset sales.
5. **Self-host only with sustained load or strategic need.** The conservative hot-L4 estimate is about **$0.002–$0.013/session**, before idle/cold-start/ops. Serverless APIs are simpler and can be cheaper at sparse demo traffic; batching and high utilization are required for open-model hosting to win reliably.

### Known limitations

- Prices are public list prices as retrieved on 2026-08-08 and may change by region, service tier, caching, batch/flex mode, data residency, negotiated contract or tax.
- The token scenarios and self-host throughput are estimates, not measurements of a production agent. Benchmark the actual prompt/tool topology and retain retry/fallback headroom before launch.
- Coze’s numeric current credits and several consumer free-tier limits are dynamic or not directly retrievable; they are marked REVIEW/UNVERIFIED instead of guessed.
- Payment fees, tax, refunds/chargebacks, moderation, support, observability, storage/egress, provider minimums and idle capacity are excluded, so break-even prices are lower bounds.
