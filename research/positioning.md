# Omo positioning

**Canonical business-positioning document**

**Founder refinement:** 2026-08-10

**Last updated:** 2026-08-11

Use this document to align the product, investor story, storefront, creator pitch, pricing, and technical roadmap. If another document conflicts with this one, this one wins.

## The position in one sentence

**Omo is the marketplace of proven AI automations: give a workflow its inputs and get the promised output with one API call, paying only when you use it—or download the files and run it locally, with no lock-in.**

Short version: **One key. Proven workflows. Pay per use.**

## The thesis: people want the result, not more software

“Software is dead” is the rallying cry, not a literal claim. Software still runs everything. What is dying is the idea that every useful AI outcome needs another dashboard, another $20–$50 monthly subscription, and a 30-minute setup.

Most buyers do not want to learn a prompt stack, connect five tools, manage API keys, or keep a fragile automation working. They want the input and output shown in the demo:

- product details in → finished UGC video out;
- phonics topic in → printable book out;
- story in → illustrated animation out;
- conversation export in → useful analysis out.

The interface is not the product. **The completed job is the product.** Omo turns proven ways of completing those jobs into small, callable services.

Our economic belief is simple: as AI changes work and puts pressure on household and small-business budgets, infrequent AI tasks should not carry permanent monthly rent. A teacher who needs one book should buy one book. A shop that needs three videos should buy three videos. Pay-per-use pricing matches cost to value and is easier to trust.

## What Omo is—and is not

Omo is a **marketplace of proven automations**. Each listing combines the models, prompts, tools, and workflow logic required to turn a clear input into a clear output.

Omo is not:

- a prompt dump;
- an uncurated directory of “AI agents”;
- a course that teaches buyers to assemble the result themselves;
- a thin model reseller;
- a closed SaaS wrapper that traps the buyer's work.

“Proven” is a product requirement. A workflow should not be promoted as proven until it has:

1. a plain input → output contract;
2. a real example or safe demo;
3. a known run price before the buyer starts;
4. repeatable quality checks;
5. measured cost, latency, and failure behavior;
6. a versioned source package that can be downloaded.

This curation is the trust layer. The marketplace should start narrow and useful, not broad and noisy.

## The anchor story: buy the video, not the lesson

Harry's mentor in Spain is willing to pay **$4 for a finished AI-UGC video**. An agent can run the full workflow for about **$3**, leaving **$1 of contribution margin** on a first-party workflow.

By contrast, a course reportedly has **26,400 members paying $9 per month** to learn how to prompt tools such as Higgsfield, HeyGen, and Google Omni by hand. The important signal is not the course revenue. It is the promise that attracted those members. They want the advertised video, not a new technical hobby.

Omo packages that promise as a service:

> Give us the product. Get the video. One call. $4.

That is the core conversion: **course knowledge → proven workflow → callable output**.

## The infrastructure analogy

[Runware's January 2026 announcement](https://runware.ai/blog/runware-raises-50m-series-a-to-power-all-intelligent-applications) says it raised a **$50M Series A** around a “one API for all AI” model-inference layer. It reports more than 10 billion generations and 200,000 developers, and describes hundreds of model classes behind one consistent schema and endpoint.

[OpenRouter's official quickstart](https://openrouter.ai/docs/quickstart) makes the same access pattern easy to understand: hundreds of models through one API endpoint, with routing and provider complexity handled behind the call.

Omo applies that pattern one layer higher:

| Layer | What the buyer calls | What the platform hides |
| --- | --- | --- |
| Runware | A model | Inference hardware, deployment, scaling |
| OpenRouter | A model from many providers | Provider accounts, routing, fallbacks |
| **Omo** | **A proven outcome workflow** | **Models, prompts, tool accounts, workflow steps, hosting, billing** |

Runware is models-as-API. OpenRouter is model choice through one API. **Omo is models plus workflows through one API.** The unit sold is not a token or model invocation; it is the finished job.

## Two doors: API or local

Every paid workflow has two operating doors. Free demos and lead magnets may help discovery, but they are not a third execution model.

| Door | Buyer experience | Omo handles | Buyer gets |
| --- | --- | --- | --- |
| **API** | Send inputs with one key and pay per use | Hosting, provider accounts, API keys, orchestration, billing, updates | The finished output |
| **Download** | Take the workflow package and run it locally | A portable, versioned package and documentation | The workflow files, prompts, and control |

The local door is non-negotiable. Buyers can inspect, adapt, and keep the workflow. The API wins on convenience because many workflows are too heavy or fiddly for most people to run themselves—just as open models can be downloaded, yet most teams still pay an inference provider to run them.

**Convenience creates retention. Lock-in does not.**

## The marketplace model

Creators—including Omo—list workflows that already produce useful results. Buyers discover them by job, see the input and output, know the price, and either call the API or download the files.

Omo handles:

- workflow hosting and isolation;
- model and third-party service accounts;
- API keys and provider changes;
- checkout, credits, metering, and payouts;
- versioning, logs, and basic quality checks;
- the storefront, examples, and discovery.

Creators provide the workflow, domain knowledge, examples, and improvements. They get paid when their work is bought or used. The creator promise stays simple: **we host it, bill for it, and deal with the infrastructure; you keep 85% of the creator margin.** For hosted runs, direct run costs come out first; the positive margin is then split 85% to the creator and 15% to Omo. First-party Omo workflows retain their full contribution margin.

The marketplace does not need to wait until Omo has built a large first-party catalog. We can host other people's proven workflows first, bring their buyers onto one key, and learn which jobs repeat. Teachers, operators, and vibecoders expand the catalog instead of Omo trying to build every vertical itself.

## Pricing philosophy

The default is **no subscription**. Buyers pay for a result when they need it, usually cents to a few dollars.

Pricing rules:

1. Price the outcome, not the token count or workflow complexity.
2. Show the full price before the run starts.
3. Charge only when a valid run starts; failed validation costs nothing.
4. Include direct model, media, compute, and provider costs in the run economics.
5. Leave enough contribution margin to pay the creator and Omo.
6. Let buyers top up credits and set spending limits without taking on a monthly commitment.
7. Keep download pricing available for buyers who prefer ownership and local control.

The target is a Vercel-like value layer over underlying infrastructure such as AWS: customers happily pay more than raw compute because deployment, orchestration, reliability, and simplicity are handled for them.

## The education wedge: PhonicsMaker becomes Omo Education

PhonicsMaker is the first distribution advantage, not a separate legacy product. It has **4,500 subscribers** and a real teacher audience, but the classic SaaS economics have weakened: acquisition spend compresses profit, and the founder estimates sale value has fallen from roughly **$400,000 three years ago to $40,000 today**.

The pivot is from “subscribe to PhonicsMaker” to **“make the teaching resource you need and pay for that one result.”**

Initial Omo Education menu:

| Outcome | Buyer price | Expected direct cost | Role |
| --- | ---: | ---: | --- |
| Phonics book | $0.30–$1.00 each | $0.05–$0.10 | Launch anchor |
| Phonics song | About $0.50 | To validate | Repeat classroom use |
| Worksheet | About $0.20 | To validate | High-frequency utility |

At the stated book range, gross contribution before creator share is roughly **67% to 95%**, depending on price and run cost. More important, a teacher can spend $1 at the moment of need instead of deciding whether another subscription deserves a place in the household or school budget.

Education then becomes a category, not a closed product roadmap. Teachers and vibecoders can publish new book formats, games, songs, worksheets, and classroom tools and get paid per use. Omo curates quality, runs them, and handles the money.

## Anchor use cases

The first catalog should demonstrate range without losing the clear input → output promise:

| Workflow | Clear output | Starting economic anchor |
| --- | --- | ---: |
| AI-UGC video | Product inputs → finished ad video | $3–$4 per video |
| Phonics book maker | Topic and level → printable book | $0.30–$1 per book |
| Japanese-style story animation | Story → animated short in the Anthony DeMello drawing style | About $0.30 per call |
| WhatsApp analysis | Chat export → useful relationship or conversation analysis | $1 per analysis; about $0.30 profit |
| PadelBuddy | Player inputs → hosted padel utility | Open-source package plus hosted listing |
| Minecraft education bot | Learning goal + play time → guided in-game session | $0.50/hour on about $0.40 cost |

These are pricing and product anchors, not promises to ship all six at once. Each still has to pass the “proven” gate before promotion.

## Go to market

### 1. Start with demand we already own

Email the **4,500 PhonicsMaker subscribers** with one plain message:

> PhonicsMaker is now priced per book. No subscription. Make a book when you need one and pay only for that book.

Give every existing subscriber enough starter credit to make the first book. The goal is to measure completed outputs, second use, and teacher referrals—not clicks to a pricing page.

### 2. Supply proven workflows before building everything

Recruit people who already show useful automations on Instagram, TikTok, GitHub, courses, and niche communities. Offer to host their workflow, handle the billing and provider accounts, and pay them per use. A creator with a real audience brings both supply and the first buyers.

### 3. Expand from one trusted category

Use education to prove the payment loop and repeat usage. Then add high-intent jobs such as UGC video, ecommerce creative, analysis, and small-business operations. New categories earn their place through repeat use and healthy unit economics.

### 4. Make the API the shared account

Every new workflow makes the same Omo key more useful. Buyers should not create a fresh account, paste a new provider key, or learn a new dashboard for each outcome.

## Technical direction

This is the intended architecture, not a claim that every part is already shipped.

- **Go backend:** use Go for the control plane and execution services. It fits the performance, small-binary, deployment, and open-source goals.
- **Provider-neutral model layer:** support Groq as an option alongside other model and media providers. Workflows choose capabilities, not hard-coded vendor lock-in.
- **Declarative workflow files:** represent each workflow as a versioned XML file with its inputs, outputs, steps, provider needs, pricing metadata, and tests.
- **Visual workflow editor:** the editor reads and writes the same XML. Non-technical creators can compose visually; technical creators can edit the file directly.
- **Git as the history:** keep workflow versions, reviews, rollbacks, and contributor changes in GitHub.
- **Portable package:** ship the XML, `skill.md`, prompts, schemas, tests, and supporting files together so the hosted and local versions describe the same job.
- **Hosted execution:** Omo resolves providers, injects secrets, runs the workflow in isolation, meters direct cost, and returns the output through one API.

The creator loop is therefore:

> Build or import → test against examples → publish → run by API or download → improve through versioned changes.

## Defensibility

The moat is not access to a model. Models and raw compute will keep getting cheaper.

Omo compounds four things:

1. **Proven workflow supply:** versioned recipes that reliably finish valuable jobs.
2. **Outcome data:** real knowledge of which workflows complete, repeat, fail, and earn.
3. **Shared distribution:** one buyer account and one API key become useful across categories.
4. **Creator economics:** makers improve the workflows because successful runs keep paying them.

The downloadable local version builds trust and helps distribution. The hosted version wins most usage because it is faster than managing the stack. Each side strengthens the other.

## Message hierarchy

Use these ideas consistently in public copy:

- **Category:** The marketplace of proven AI automations.
- **Buyer promise:** Give it the inputs. Get the result. Pay per use.
- **API promise:** One key for every proven workflow.
- **Trust promise:** Download and run locally whenever you want. Never locked in.
- **Creator promise:** We host, bill, and deal with everything. You get paid when your workflow is used.
- **Price promise:** No subscriptions. Usually cents to a few dollars per run.

Prefer “helper,” “workflow,” “job,” “result,” and “run” in customer copy. Use “agent,” “orchestration,” “inference,” and “declarative specification” only when speaking to technical buyers or investors.

## Non-negotiables

- Lead with the result, not the underlying models.
- Do not make buyers complete a setup tutorial before receiving value.
- Do not hide the per-use price.
- Do not require a subscription for ordinary access.
- Do not list untested workflows as proven.
- Do not trap a buyer in Omo; keep the local download real and usable.
- Do not build every category ourselves when a credible creator already has the workflow.
- Do not confuse a large catalog with a useful marketplace.

## What we must prove next

The first launch should answer five questions:

1. How many of the 4,500 PhonicsMaker subscribers make a first per-use book?
2. How many return to make a second output within 30 days?
3. Which price points preserve conversion and contribution margin?
4. Can third-party creators deliver workflows that pass Omo's proof gate?
5. Does the download option increase trust without materially reducing hosted usage?

Track activation, completed runs, repeat runs, contribution margin per run, creator payout, refund/failure rate, and time to useful output. Monthly recurring revenue is no longer the primary truth; **successful paid runs and repeat use are.**

## Evidence note

The Runware and OpenRouter descriptions above were checked against their primary pages on 2026-08-11. The customer stories, PhonicsMaker figures, use-case prices, cost estimates, and valuation history came from the founder/co-founder conversation on 2026-08-10. Confirm the underlying records before quoting those internal figures in published investor materials.
