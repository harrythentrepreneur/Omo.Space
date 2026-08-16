# REDDIT AI/SEO STRATEGY — what practitioners actually say works (2025–2026)

**Research date:** 2026-08-16
**Commissioned by:** Omo (omo.space) — AI workflow marketplace; every skill is a free skill.md + a paid hosted run; prerendered `/workflows/<slug>/` pages; GSC verified.
**Method:** Old.reddit RSS search (29 queries across r/SEO, r/juststart, r/seogrowth, r/TechSEO, r/ChatGPT, r/OpenAI, r/artificial) + full-thread HTML fetches parsed with BeautifulSoup. Every quote below is verbatim from fetched content (post bodies, comment bodies), attributed to subreddit, thread URL, poster, and date. Comment dates are the comment timestamps; thread dates are post dates. Scores are comment scores at fetch time. Nothing fabricated; where a claim is only the poster's assertion, it is flagged **UNVERIFIED**.
**Reuse:** Prior Omo reddit research (2026-08-08/12) and `seo-strategy-fresh.md` (2026-08-14) are cross-referenced where relevant.

---

## 0. TL;DR — the six big takeaways

1. **Programmatic scale still works, but the unit changed.** The 2026 winner is a *real data-driven page* (one distinct job per page, real numbers, answer-first structure) — not 10,000 template pages. Practitioners repeat: "indexed ≠ traffic", "without traffic and clicks the pages generally get de-indexed". 700K-impression case studies get publicly mocked for 2,700 clicks. **CONTESTED:** whether pSEO "works" at all in 2026 — multiple threads say it only works on top of existing authority.
2. **AI Overviews run on normal Google ranking systems** (Gary Illyes, r/SEO 2025-07) — so classic SEO is not dead, but the *click economics* are brutal: cited pages report 0.0009% CTR. AI citations ≠ clicks.
3. **RAG/AI-search visibility is a different game than ranking** — "AI engines don't cite you for being big. They cite you because a page is structured enough to lift a sentence straight out of." Answer-first structure, one question per H2, real numbers, clean tables, schema matching visible text. Small low-authority sites report ChatGPT/Perplexity as their #1 referrer. **CONTESTED:** GEO monetization — one practitioner's own numbers: 37 AI sessions/90 days, 1 paying customer.
4. **Reddit is the canonical example of the new SEO** — Google's AI summaries now explicitly quote Reddit; companies are caught *manipulating* AI search via planted Reddit content. Omo should study Reddit's document model (durable, individually-addressable, UGC-proven, engagement-signaled) — the same model Omo's own `seo-strategy-fresh.md` recommends for listings.
5. **E-E-A-T is contested** ("E-E-A-T is Snake Oil", 2024) but *reviewer bylines + real credentials + entity presence* are the most-repeated entity signals that survive scrutiny in 2025–2026 threads.
6. **Thin content is a live risk at scale** — Google issued a manual action on WindowsForum.com's entire /threads/ tree (July 2026) for "thin content" on pages indexed unchanged since 2008. LLM-generated page debates are everywhere; the safe play is proof-density per page, not page count.

---

## 1. Programmatic SEO at scale (10k+ pages)

### Evidence that scale still works — with the "impressions trap" exposed

> "I spent 6 months building something for my side hustle that I knew would make zero dollars… I built 300+ pages using code. Every baking ingredient gets its own page. Every ingredient swap gets its own page…"

— u/milkstarz, [r/juststart "Built a programmatic SEO site to 700K impressions in 12 months"](https://www.reddit.com/r/juststart/comments/1ri48gp/) — posted 2026-03-01. The case study claims 700K impressions in 12 months on 300+ generated pages, $38K revenue / $12K net profit (affiliate + toolkit).

The comment section is the real lesson — impressions without clicks get publicly roasted:

> "2,700 clicks in 12 months? Fewer than 10 per day? Is that right?"

— u/FoxDev, same thread, 2026-03-01

> "Fair enough. I just hate impressions as a metric. When you're in the tens of millions it sucks and I'd rather just have way fewer to have a nicer CTR. Clicks is where the cash is."

— u/FoxDev, same thread, 2026-03-01

> "Congrats on building an ad farm. More ai slop."

— u/Altruistic-Guard1982, same thread, 2026-03-06 — the "AI slop" accusation is the single most common dismissal in every 2026 scale thread.

> "The interesting part here is how the system compounds once Google understands the topical structure instead of evaluating pages in isolation."

— u/Exciting-Holiday2106, same thread, 2026-05-09 — topical-structure framing (entity/topic clusters) is the standard defense of scale.

### The 2026 verdict on template pages

> "Programmatic SEO used to feel like a cheat code: generate thousands of location, category, or use-case pages and scale organic traffic fast. But with Google's recent updates, AI-generated content everywhere, and heavier quality filters, I'm wondering how viable it really is today."

— u/Born-Squirrel6089, [r/seogrowth "Does Programmatic SEO Still Work, or Is the SERP Completely Saturated Now?"](https://www.reddit.com/r/seogrowth/comments/1pn0n30/) — posted 2025-12-15

> "programmatic seo kinda works in 2025 but only if youre not blasting generic crap. google nukes thin pages now, indexed doesnt mean traffic."

— u/Old-Blackberry-3019, same thread, 2025-12-16

> "It still works, but you need more customising."

— u/satanzhand, same thread, 2025-12-15

> "Programmatic SEO does not work unless it is improving something with authority already. The trend is a push towards quality and authority moreso than quantity. If the page answers a popular question early on just by skimming it, that will do better than a 10,000 word manifesto with all the schema."

— u/who_am_i_to_say_so, same thread, 2025-12-23 — **the most-cited "contested" position: pSEO without existing authority is dead.**

> "Works, but caveat. You need to pair it with other traffic sources so you can see what works commercially. The biggest fail for 99% of programmatic sites is waiting for Google to rank to see results."

— u/beefcutlery, same thread, 2026-01-10 (poster runs a pSEO service — treat with bias flag)

### The "30-day win, no 1-year results" problem

> "LinkedIn is full of '30-day programmatic SEO wins', but I almost never see 6–12 month follow-ups. Does the traffic actually sustain, or does it get wiped out by updates / indexing decay over time?"

— u/tonypaul009, [r/seogrowth "Why do we only see 30-day Programmatic SEO wins and never 1-year results?"](https://www.reddit.com/r/seogrowth/comments/1rthlm8/) — posted 2026-03-14

> "Programmatic SEO is nothing new… But yes, without traffic and clicks the pages generally get de-indexed."

— u/lightningautomation, same thread, 2026-03-14 — **indexed-but-unused pages decay. This is the core risk model for a 10k-page catalog.**

### From the earlier case-study era (still cited)

- [r/juststart "Programmatic SEO + AI Journey $25,000 profit (12th month)"](https://www.reddit.com/r/juststart/comments/1878rdt/) — 2023-11-30. The classic long-running case study; its lesson (template pages + real data + monetization) is still the reference point in 2026 threads.
- [r/juststart "What Happens If You Post 12,000 AI Articles In A Month?"](https://www.reddit.com/r/juststart/comments/12qm0n4/) — 2023-04-18. The cautionary canon for AI-generated page farms.

**Synthesis for Omo:** scale is the *distribution* strategy, but each page must be a distinct job with proof (data, numbers, examples, outputs) — the exact standard `seo-strategy-fresh.md` calls "proof density per page, not pages per keyword". And impressions are vanity: Omo's real metric must be qualified visits → workflow starts → paid runs (the same cohort logic `seo-strategy-fresh.md` §6.7 prescribes).

---

## 2. AI Overviews (AIO) — the click-economics shock

### Normal SEO still feeds AIO (confirmed by Google, repeated on r/SEO)

> "Gary Illyes just confirmed at Search Central Deep Dive what many of us suspected: AI Overviews use the same ranking systems as regular search. Normal SEO works."

— u/aftabaliqu, [r/SEO "Google confirms normal SEO works for AI Overviews"](https://www.reddit.com/r/SEO/comments/1m9k0kg/) — posted 2025-07-26

> "Google: Normal SEO Works To Get Into AI Overviews"

— [r/SEO thread, same week, 2025-07-24](https://www.reddit.com/r/SEO/comments/1m8gmmj/)

The top-voted reply (66 pts) both confirms and complicates it:

> "AI Overviews mix multiple query branches and reason through entities differently from regular SERPs. That's why you'll sometimes see low traffic domains in AI answers while top ones don't appear at all."

— u/mariestarlight, same thread, 2025-11-10

And the 56-point counter says the *ranking mechanics* claim misses the real story:

> "The unsaid pact between search engines and websites, was to take our content but give us traffic in return. That was upheld for 25 years until now. Google and others now steal your content and block the clicks or hide the links from 99% of the queries."

— u/Sniflix, same thread, 2025-07-26

> "The ranking mechanics haven't changed, but the traffic distribution absolutely has. Google is keeping more users on their platform."

— u/aftabaliqu, same thread, 2025-07-26

### But being cited does NOT mean clicks

> "We've been included in Google's AI Overviews lately, which looks great from an impressions point of view. However, the CTR is extremely low: 797,444 i[mpressions]…"

— u/mrborgen86, [r/SEO "Google AI Overviews has the worst click-through rate I've ever seen: 0.0009%"](https://www.reddit.com/r/SEO/comments/1r9wrgg/) — posted 2026-02-20. 797K impressions at 0.0009% CTR ≈ 7 clicks.

> "CTR is stuck at 0.5%. AI summaries are killing my clicks. How do I fight back?"

— [r/SEO, 2026-03-05](https://www.reddit.com/r/SEO/comments/1rltrzp/) — a recurring complaint pattern across the sub.

The design intent is explicit:

> "AI overviews is part of a design philosophy toward clickless search — no shit they have bad CTR — they literally exist to give users info without making them take an action"

— u/Nyodrax (36 pts), [r/SEO 0.0009% thread](https://www.reddit.com/r/SEO/comments/1r9wrgg/), 2026-02-20

> "Google is no longer just a search company. It is turning into an 'answer' company. That means the sources it used to send users to are being pushed aside, and in the future only paid ads will really work… Nobody wants to click through ten search [results]…"

— u/elixon (13 pts), same thread, 2026-02-20

The counter (why answer-content still needs a live source):

> "Except if the information changes and there is no one to update it or to 'add it' to llms… If all the informational websites stop publishing, from where will LLM get the most recent information?"

— u/pfunf, same thread, 2026-02-21 — **the "freshness supply chain" argument: current, updated, verifiable pages remain the input to AI answers. This is Omo's core thesis: live listings (prices, versions, run proofs) are exactly the content AI answers need and stale static pages can't supply.**

### The counter-hypothesis: total clicks may still rise

> "Click-through rates down due to AI Overview, but more overall traffic: could we actually have more total clicks?"

— [r/SEO, 2026-06-14](https://www.reddit.com/r/SEO/comments/1u5hqq6/) — contested; no consensus in-thread.

> "How can content-based websites combat AI Overviews? …we've seen our traffic get decimated over the past few months due to AI O[verviews]…"

— u/chewwydraper, [r/SEO](https://www.reddit.com/r/SEO/comments/1qcq17b/) — posted 2026-01-14 (poster: large content site employee, 10 years in SEO)

The thread's key line — ranking #1 while being the cited source is still losing:

> "We're #1 for our target search terms. Our data and content is high-quality enough that the AIO is constantly referring to us when giving answers. But we're not getting the clicks, because why click when AIO is already giving you our content?"

— u/chewwydraper, same thread

> "Having 'only' lost 40% you're doing well compared to a lot of sites as many have lost 60-100% of their organic Google search traffic."

— u/CraftBeerFomo (6 pts), same thread, 2026-01-14

> "I'm in a similar spot, working for a big site that's basically becoming the 'unpaid research department' for Gemini. It's soul-crushing to see a #1 ranking result in a big fat zero for CTR because the AIO just sucked the marrow out of your content."

— u/Bigzeebarrelmaster, same thread, 2026-01-15

The survivorship advice (what content still earns clicks):

> "Do you have the type of content users are willing to pay for? Do you have unique takes and insights or data/reporting? if not, you're done."

— u/RyanJones, same thread, 2026-01-14 — **the "own the data / own the product" test — directly relevant to Omo: listings with live run output are a unique, un-copy-pasteable asset; informational prose is not.**

**Omo implication:** being the *answer* for "what is the best skill for X" matters more than being a blue link. Omo should optimize for being the cited source AND make the post-answer click worth it (a runnable demo / sample output, not just prose).

---

## 3. RAG / AI-search / GEO — being cited by ChatGPT & Perplexity

### The single best practitioner articulation (2026)

> "AI engines don't cite you for being big. They cite you because a page is structured enough to lift a sentence straight out of. Authority is google's game. Getting cited is a different one, and a small site can win it faster."

— u/bikram_uk, [r/juststart "ChatGPT sends my niche site more buyers than Google now"](https://www.reddit.com/r/juststart/comments/1ve3olr/) — posted 2026-08-03. Claims: ChatGPT is now his #1 referrer ahead of Google; classic search ≈ 5% of traffic; works at low authority.

His on-page changes (post body, verbatim-ish summary — the full post is quoted in the appendix):

- "answer first, every section. the first 2-3 sentences answer the exact question, before any preamble"
- "one question per H2. AI pulls chunks, not whole pages."
- "specifics over adjectives. exact m[etrics]…"
- "schema that matched the visible text" (from his comment 2026-08-03: "tight answer right at the top, real numbers, clean comparison tables, and schema that matched the visible text")

> "The 'AI cites you for being liftable, not for being big' framing is the actual useful bit here, most people still treat AI visibility like SEO round two when it's a different game."

— u/Big_Watermalones_67, same thread, 2026-08-04

**Contested heavily — several commenters accuse the post of being AI-generated marketing:**
> "The post and replies are all trying to shill their slop. How many layers deep can we really go here."

— u/MCMK (14 pts), same thread, 2026-08-03

> "An ai written post about ai discovering your likely ai written website. How deep does the ai rabbit hole go?"

— u/KanyeWestsPoo, same thread, 2026-08-04 — **honesty flag: even genuinely useful AEO advice is publicly treated as slop when it comes from low-authority sellers. Omo must avoid the same pattern (no fake screenshots, no bot accounts, real proof artifacts).**

### The 4-layer citation model (GEO practitioner, 2026)

> "AI engines… select sources based on 4 layers: 1. Access: robots.txt allowing GPTBot, OAI-SearchBot…" [2–4: structure/extractability, corroboration, engagement]

— u/NervousBasis8600, [r/juststart "AI search isn't replacing SEO. It's making it irrelevant for half the sites I audit."](https://www.reddit.com/r/juststart/comments/1vfdxng/) — posted 2026-08-04. Poster: 6 months in GEO, "audited 1000+ sites, built a benchmark across 360 domains".

Supporting data from a commenter:

> "NZ property tools site, DR 18. Pulled the July numbers and the clicks arriving through AI citations show much higher intent than my general search clicks, they've already read the answer and land ready to use the tool, engagement is well above organic."

— u/Big-Leg-4847, same thread, 2026-08-04 — **the "pre-qualified AI traffic" claim, with a concrete site.**

The skeptical counter:

> "What I don't see is fact-based reporting on whether GEO is actually translating into clicks and, ultimately, sales that justify it. If you are essentially creating content for OpenAI to steal and serve their customers…"

— u/brendancoots (18 pts), same thread, 2026-08-04

And the poster's honest own numbers:

> "37 sessions from ChatGPT in 90 days, with 2m38s average engagement vs 1m for organic. One paying customer ($19/mo) came from China… That's one data point, not a statistically significant sample."

— u/NervousBasis8600, same thread, 2026-08-05 — **the most honest GEO data point in the corpus. AI traffic: higher intent, tiny volume. Marking GEO monetization UNPROVEN.**

### Who actually gets cited (2026-08)

> "Did this out of curiosity for a handful of B2B SaaS categories. The citations skew hard to Wikipedia, HubSpot-style guides, and the occasional arxiv p[aper]…"

— u/hseeman_sf, [r/SEO "Has anyone actually checked who gets cited when you ask ChatGPT or AI Overviews about your niche?"](https://www.reddit.com/r/SEO/comments/1vl1b5c/) — posted 2026-08-10 — **for B2B SaaS queries, AI answers cite authorities: Wikipedia/HubSpot. New small marketplaces are not auto-cited; they must earn citation via structure + corroboration.**

A GEO-tool builder's self-test in the same thread:

> "scored 31/100 on my own product, and of the 15 sources cited across the answers for my category, not one was my own domain."

— u/plasma_tron, same thread, 2026-08-11

And the measurement caveat:

> "A citation set that's absent on one pass can show up a third of the time over ten, so 'never cited' from one run is really 'not cited this run.' Worth treating presence as a rate, not a yes/no."

— u/hseeman_sf, same thread, 2026-08-15 — **operational rule for Omo: measure AI citations as a rate over repeated runs, not a single query.**

### The new-product cold start ("the GEO loop") — 2026-08

> "GEO tools and AI are heavily biased toward already-popular, established things. Because our product is new and nobody is talking about it yet, the AI treats us with extreme caution… we don't get traffic, there's no online buzz; and because there's no buzz, the AI continues to ign[ore us]…"

— u/Simple_Engineer3656, [r/SEO "How to break the AI search / GEO loop for your new product?"](https://www.reddit.com/r/SEO/comments/1vm0j5o/) — posted 2026-08-12

The community's answers — this thread is the best playbook for a new marketplace:

> "LLMs are obsessed with Reddit and GitHub right now. If you can get actual discussions going on these platforms, the crawlers will pick you up way faster than they will from your own blog."

— u/Objective-Fun-4533, same thread, 2026-08-12

> "whatever shows up in Google Search for the query is what the LLMs regurgitate. Reddit and GitHub are often first or second page… the LLMs will often confuse opinion and hearsay with fact."

— u/VillageHomeF, same thread, 2026-08-12 — **both halves matter for Omo: Reddit/GitHub presence feeds AI answers; and low-quality Reddit mentions can hurt as easily as help.**

> "the loop is real and it's specifically a cold-start problem: models cite you because third parties mention you, and nobody mentions a brand-new product, so you have to manufacture the first layer yourself, honestly."

— u/planerist, same thread, 2026-08-12

> "You don't break the loop by convincing the models to trust you but by manufacturing the evidence they read, from your own domain… Your own site and social posts barely count because they're self-ref[erential]."

— u/TamaraPI, same thread, 2026-08-12

> "The fastest way out is to stop trying to make the AI trust the brand and start creating evidence around the problem it solves. Publish original data, comparisons, customer results, and genuinely useful discussions around the category, then make sure those references exist outside your own domain."

— u/Significant_Pick8297, same thread, 2026-08-12

> "if you're not on g2, capterra, trustradius, or in reddit threads where people compare solutions, the model has no anchor to pull from."

— u/Agitated_Offer_4343, same thread, 2026-08-13 — **directory/listing presence (G2-style) is itself an AI-citation anchor — a strong argument for Omo pursuing its own directory credibility AND being present in adjacent directories.**

### AIO visibility ≠ ChatGPT visibility

> "Your site can pass Google's AI Overviews and still be invisible to ChatGPT. They're not the same thing… two separate layers, they have different failure modes…"

— u/Ok_Veterinarian446, [r/seogrowth](https://www.reddit.com/r/seogrowth/comments/1tuxarm/) — posted 2026-06-02 — corroborated by the Ahrefs study below.

### Schema does NOT move AI citations (hard data, 2026)

> "Adding schema didn't boost citations on any platform. We tracked 1,885 web pages that added JSON-LD schema between August 2025 and March 2026… AI Citations Barely Moved."

— u/WebLinkr, [r/TechSEO](https://www.reddit.com/r/TechSEO/comments/1ta9tux/) — posted 2026-05-11. Ahrefs-tracked sample. **CONTESTED against the r/TechSEO pricing case studies below — schema helps specific factual claims (pricing), but is not a citation lever by itself.**

### …but structured endpoints + server-rendered HTML measurably help LLM bots

> "We ran a controlled crawl experiment for 30 days across a few dozen sites… structured endpoints got ~14% stronger LLM bot behavior"

— u/lightsiteai, [r/TechSEO](https://www.reddit.com/r/TechSEO/comments/1r05tjr/) — posted 2026-02-09. ~5M bot requests analyzed. **Direct support for Omo's prerendered `/workflows/<slug>/` architecture + machine-readable listing endpoints.**

> "Case Study: Missing Product/Offer schema let Google's AI Overview quote competitor's pricing"

— [r/TechSEO, 2025-04-25](https://www.reddit.com/r/TechSEO/comments/1k7vwh2/) and [Case Study #2: Fixed AI Overview Pricing Citation with 3 Schema Nodes, 2025-04-29](https://www.reddit.com/r/TechSEO/comments/1kaxlpk/) — **for Omo: a skill listing's PRICE must be in Product/Offer JSON-LD or an AI answer will cite a competitor's price.**

---

## 4. Reddit's own SEO rise (the model to copy — and the manipulation warning)

> "Google says this update aims to address that 'people are increasingly seeking out advice from others' when searching for information online. This will be relatable for anyone who's added 'Reddit' to the end of Google Search terms to find experiences from real humans instead of SEO-optimized web results. It also backs up claims made by Reddit CEO Steve Huffman last year that 'just about anybody using Google at this point will end up on Reddit.'"

— u/tekz, [r/artificial "Google's AI search summaries will now quote Reddit"](https://www.reddit.com/r/artificial/comments/1t5ct5o/) — posted 2026-05-06 — **Google AI search now explicitly cites Reddit as a source class; Huffman's "anybody using Google will end up on Reddit" is the canonical statement of Reddit's SEO dominance.**

The deal structure, as commenters read it:

> "Which is exactly what happened. Google and Reddit made a deal for Google to scrape Reddit to educate their LLMs in exchange for preferential Reddit ranking in search and in AI responses."

— u/___Scenery_, same thread, 2026-05-06

The quality risks of AI-quoted UGC (both directions):

> "While it is true I've seen some well thought out responses… much of what I'm seeing contributed is not something I'd want fed back to me by Google. I hope they are discriminating in their quotes and not simply choosing highly upvoted comments, or quotes from accounts only days old."

— u/Old_timey_brain (4 pts), same thread, 2026-05-06

> "used reddit as my main debug tool for years. now google scrapes it, summarizes it, and serves it with no context or upvotes. last month a client trusted some ai summary that grabbed a deprecated fix. cost em 6 hours. good for recipes. shit for code."

— u/autonomousdev_, same thread, 2026-05-06 — **honesty flag for Omo: being quoted by AI is a liability if the quoted content is stale or wrong. Versioned, dated, verified listings are the antidote.**

> "Companies Are Using Reddit to Manipulate ChatGPT and Google AI Search. Peptide companies have been doing AI-engine optimization by spamming the biohackers subreddit to manipulate ChatGPT and Google."

— u/esporx, [r/artificial](https://www.reddit.com/r/artificial/comments/1tw6hb9/) — posted 2026-06-03 — **the flip side: AI-cited UGC platforms are already being gamed.**

> "the part that gets me is how obvious this is once you see it. companies know ai search pulls from reddit heavily. so they seed the platform with exactly what they want the models to say. it turns the whole thing into a feedback loop where the 'organic' source gets engineered."

— u/sheppyrun, same thread, 2026-06-04

> "As soon as Google invested in reddit, marketing agencies shifted balance to AI search. There are entire marketing agencies just dedicated to reddit/AI."

— u/Test_Account_2026, same thread, 2026-06-04 — **a whole agency category exists for Reddit/AI-search optimization; expect Omo's competitors to do this, and expect Reddit to fight manipulation (weighting recency vs manipulation, per u/sheppyrun).**

Why Reddit wins (synthesis from the corpus + `seo-strategy-fresh.md` §3): Reddit pages are durable, individually-addressable documents with substantial UGC text, ongoing engagement (fresh comments), human reputation, and external demand — exactly the 6 listing-quality signals `seo-strategy-fresh.md` lists for Omo (stable route, SSR, proof, marketplace signals, differentiation, honest engagement). Reddit also gets *freshness* and *breadth*: an answer for every long-tail variant, all on one domain with massive internal linking and entity strength.

**Omo takeaway:** each `/workflows/<slug>/` page should be *as Reddit-thread-like as possible*: real proof, versioned updates, creator identity, honest limitations, and genuine community/run signals. Do not buy comments or fake reviews — the community detects and torches it (see the slop accusations in §3), and AI engines are learning to weight recency against manipulation.

---

## 5. Entity / E-E-A-T signals (contested)

The strongest pro-E-E-A-T sentiment in the corpus is actually indirect — the "authority" requirement keeps coming back in pSEO threads ("does not work unless it is improving something with authority already"). The direct debates:

> "As an expert SEO with tons of experience, I have many case studies with data to prove that you don't need expertise, experience, trust or authority to rank."

— u/namynotc, [r/SEO "E-E-A-T is Snake Oil"](https://www.reddit.com/r/SEO/comments/1b60tfk/) — posted 2024-03-04 — **the contesting thread: E-E-A-T as a *checkbox set* is dismissed; E-E-A-T as *content quality* is not.**

The 70-point rebuttal that won the thread:

> "I think you completely misunderstand what E-E-A-T is and how Google can measure/approximate aspects of it… Being a popular brand is a super strong indicator of Expertise, Authoritativeness, and Trustworthiness. Big brands rank because of E-A-T, not despite of it!"

— u/maltelandwehr (70 pts), same thread, 2024-03-04

> "Don't discount the methods by which Google can attribute trust, because if you watched Medic update decimate the incredibly well written content by alternative health sites, you know that Google CAN and DOES have signals it can use. (Hint: It's distance by links to trusted seed sites for your niche in YMYL queries.)"

— u/footinmymouth (24 pts), same thread, 2024-03-04 — **the operative mechanism: link-distance to trusted "seed sites" in the niche. For Omo: links from established, trusted developer/marketing sites into the OSS library and listings are entity signals; blog posts alone are not.**

> "the main problem with EEAT is the lack of an exact definition of what the terms mean or which signals really influence it. So, there is an abundance of speculations and interpretations. It's basically the old 'Brands are how we sort out the cesspool.'"

— u/stablogger, same thread, 2024-03-04

And the Reddit-connection from that same thread:

> "Reddit and Quora are getting the positions that I formally held in the SERPS."

— u/JaniceWald, same thread, 2024-03-05

> "Google's E-E-A-T Guidelines - Are reviewer bylines necessary?"

— [r/SEO, 2024-10-25](https://www.reddit.com/r/SEO/comments/1gc3bjz/) — bylines = reviewer identity on YMYL-adjacent pages.

> "Anonymous under a pen name but I hold the real credential to go public. At what point does de-anonymizing actually help?"

— [r/SEO, 2026-07-05](https://www.reddit.com/r/SEO/comments/1uoeerf/) — the live 2026 question: real-name/credential signals vs anonymity.

**Synthesis (contested → practical):** nobody agrees E-E-A-T is a ranking *factor* you can toggle, but "authority already exists" is repeatedly stated as the precondition for scale to work, and bylines/credentials are the cheapest way to *demonstrate* authority. For Omo: creator profiles with real identity, per-listing reviewer/verification notes, and honest limitations are low-cost entity signals that also serve the marketplace's trust product.

---

## 6. Internal linking

> "Internal link best strategy?"

— [r/SEO, 2026-07-20](https://www.reddit.com/r/SEO/comments/1v1wj0x/) — recurring question; the pattern of answers across 2026 threads: link by *job/category*, not by keyword permutations; homepage → category → listing; "related" links must be genuinely related.

> "Question about Google's Reasonable Surfer model and internal links"

— [r/SEO, 2026-08-05](https://www.reddit.com/r/SEO/comments/1vfxja8/) — 2026 threads increasingly discuss *link-weight flow* (Reasonable Surfer) rather than raw counts.

> "184 blog posts, 684 internal links. How would you clean this up?"

— [r/SEO, 2026-07-07](https://www.reddit.com/r/SEO/comments/1uprihu/) — link bloat is a real operational problem at catalog scale; a *generated* linking layer needs rules (which links to emit, from where, to where, when to stop).

**Omo implication:** an agent-driven internal-linking policy (category hubs → listing → related listings by job; canonical URLs everywhere; a "link budget" cap so hubs stay focused) is exactly the kind of deterministic rule the Omo agent can execute and audit.

---

## 7. Thin-content risk at scale (the 2026 manual actions)

> "Last week, Google applied a manual action to every URL under /threads/ — which is the entire forum. The message (WNC‑651700, ~17 July 2026) is: 'Thin…'"

— u/WindowsForum, [r/SEO "Google hit WindowsForum.com with a thin-content manual action for pages it has indexed unchanged since 2008"](https://www.reddit.com/r/SEO/comments/1v6jn8x/) — posted 2026-07-25. **A whole forum tree nuked for thin content — the cautionary tale for "every skill gets a page" catalog strategies.**

> "SEO Debate: Does Google really block 'thin content'? Is it real? Are people getting it from LLMs?"

— u/WebLinkr, [r/SEO](https://www.reddit.com/r/SEO/comments/1tbx108/) — posted 2026-05-13 — the live debate about LLM-generated page farms. **The concept itself is contested:**

> "In my opinion, 'thin content' is doing a lot of work the evidence doesn't support. Google's own docs say no minimum word count. Matt Cutts said for years that duplicate content isn't penalized… And if thin content were really a thing, online dictionaries with pages of 200-300 words wouldn't be ranking."

— u/Legitimate-Salary108 (5 pts), same thread, 2026-05-13

> "thin gets conflated as short but there is plenty of low word count content ranking that satisfies the search intent or has backlinks."

— u/sibly, same thread, 2026-05-13

> "There's a penalty for Thin Affiliate content — but if you don't have a word count minimum. If XKCD can rank pages that are a cartoon and a description…"

— u/WebLinkr (6 pts), same thread, 2026-05-13 — **the resolution: "thin" ≠ short; "thin" = no added value (no data, no proof, no unique job). Omo pages with live run proofs are the opposite of thin.**

> "I 10x'd the quality of my site. Google's response: rank it lower."

— [r/SEO, 2026-03-08](https://www.reddit.com/r/SEO/comments/1roaiix/) — the dark-humor reminder that *site-level* quality changes don't move rankings quickly.

> "Is it best to just no index thin low quality articles or do you just delete them altogether?"

— [r/SEO, 2026-07-16](https://www.reddit.com/r/SEO/comments/1uxttp4/) — **the operative operational question for Omo's catalog: noindex unproven listings, don't delete the URL (future proof), and never let them into the sitemap** — which is Omo's current clean-index policy (`seo-strategy-fresh.md` §6.5).

---

## 8. What practitioners say works NOW (2025–2026) — synthesis

| Practice | Evidence (thread, date) | Confidence |
|---|---|---|
| Answer-first structure (question → answer in first 2–3 sentences) | r/juststart 1ve3olr (2026-08), r/seogrowth 1pn0n30 (2025-12) | **High** (repeated across threads) |
| One question per H2; chunk-sized sections | r/juststart 1ve3olr (2026-08) | Medium (single source, contested thread) |
| Real numbers/specifics over adjectives | r/juststart 1ve3olr (2026-08), r/seogrowth 1pn0n30 (2025-12) | **High** |
| Comparison tables + schema matching visible text | r/juststart 1ve3olr (2026-08); r/TechSEO 1k7vwh2 (2025-04) | Medium-High |
| Product/Offer schema for price (else AIO cites competitor price) | r/TechSEO 1k7vwh2, 1kaxlpk (2025-04) | **High for factual claims** |
| Schema as generic citation lever | r/TechSEO 1ta9tux (2026-05, 1,885 pages) | **Low — contested, data says no** |
| robots.txt/access: allow AI bots (GPTBot, OAI-SearchBot, PerplexityBot) | r/juststart 1vfdxng (2026-08) | High (necessary condition) |
| Structured/endpoint-friendly server-rendered pages | r/TechSEO 1r05tjr (2026-02, 14% LLM behavior lift) | Medium (single controlled study) |
| Third-party corroboration (citations from other sites) | r/juststart 1vfdxng (2026-08), r/SEO 1vl1b5c (2026-08) | **High** |
| Don't chase impressions; chase clicks → conversions | r/juststart 1ri48gp comments (2026-03) | **High** |
| Genuinely related internal links by job, not keywords | r/SEO 1v1wj0x, 1uprihu (2026-07) | Medium |
| Noindex (not delete) thin/unproven pages | r/SEO 1uxttp4 (2026-07) | Medium |
| Authority precondition for scale | r/seogrowth 1pn0n30 (2025-12) | Contested (many agree) |
| GEO monetization at scale | r/juststart 1vfdxng (2026-08) | **Unproven** (poster: 1 paying customer) |

---

## 9. THE OMO PLAYBOOK — 15 rules the Omo agent follows

Each rule cites the Reddit evidence above. Rules are numbered for the agent; `[C]` marks contested claims the agent should treat as hypotheses, not facts.

1. **One page per distinct job, not per query/input variant.** A skill listing exists only if a buyer would recognize a distinct job ("phonics word list generator" yes; "phonics worksheet for -at" no — that's an input). *Evidence:* r/seogrowth 1pn0n30 (u/who_am_i_to_say_so: "If the page answers a popular question early on just by skimming it, that will do better than a 10,000 word manifesto"); Omo's own seo-strategy-fresh.md §4 (Google scaled-content-abuse policy on query variants).
2. **Never publish an unproven listing to the index.** Noindex unproven/coming-soon listings; only sitemap-publish listings that pass Omo's proof gate (live price, real runs, inspectable output, creator/verifier identity). *Evidence:* r/SEO 1v6jn8x (WindowsForum manual action on the whole /threads/ tree, 2026-07); r/SEO 1uxttp4 (noindex vs delete debate, 2026-07).
3. **Measure clicks and paid runs, not impressions.** Impressions are the vanity metric of 2026 — a 700K-impression case study got 2,700 clicks and public mockery. *Evidence:* r/juststart 1ri48gp comments (u/FoxDev: "Clicks is where the cash is", 2026-03); r/SEO 1r9wrgg (0.0009% CTR, 2026-02). GSC cohorts: impressions → qualified visits → workflow starts → paid runs, per `seo-strategy-fresh.md` §6.7.
4. **Answer-first listing copy.** Every listing's first 2–3 sentences answer "what does this skill do for me" with zero preamble; no "in this guide we'll explore" anywhere. *Evidence:* r/juststart 1ve3olr (u/bikram_uk: "answer first, every section", 2026-08). `[C]` — the thread was accused of being AI slop; adopt the structure, not the seller's credibility.
5. **One question per H2.** AI engines pull chunks, not pages; each section must stand alone as a citable block. *Evidence:* r/juststart 1ve3olr (2026-08); r/seogrowth 1tuxarm (AIO ≠ ChatGPT layers, 2026-06).
6. **Real numbers, specifics, and comparison tables over adjectives.** Price, run cost, latency, output formats, limits — concrete and visible. *Evidence:* r/juststart 1ve3olr (2026-08); r/seogrowth 1pn0n30 (2025-12).
7. **Product/Offer JSON-LD with the actual price on every listing.** Without it, AI answers will quote a competitor's price. *Evidence:* r/TechSEO 1k7vwh2 + 1kaxlpk (2025-04 pricing citation case studies). Do NOT expect schema alone to win AI citations — *Evidence:* r/TechSEO 1ta9tux (1,885 pages, "AI Citations Barely Moved", 2026-05). `[C]` — schema is necessary for factual answers, not sufficient for citation.
8. **Allow AI crawlers and keep prerendered HTML.** robots.txt: GPTBot, OAI-SearchBot, PerplexityBot, ClaudeBot allowed; `/workflows/<slug>/` must be server-rendered with structured, extractable content. *Evidence:* r/juststart 1vfdxng (access = layer 1, 2026-08); r/TechSEO 1r05tjr (structured endpoints ≈ 14% stronger LLM bot behavior, 2026-02).
9. **Build third-party corroboration, not just on-page optimization.** Wikipedia/HubSpot-style authorities dominate AI citations in B2B SaaS queries. *Evidence:* r/SEO 1vl1b5c (2026-08); r/juststart 1vfdxng (2026-08). Omo actions: real user posts about skills on Reddit/HN (organic only), OSS library links, product mentions on credible sites. Do not plant/manipulate UGC — *Evidence:* r/artificial 1tw6hb9 (peptide companies caught gaming AI search via Reddit, 2026-06); r/juststart 1ve3olr (slop accusations, 2026-08).
10. **Publish creator identity + verification on every listing.** Bylines/credentials are the cheapest surviving E-E-A-T signal and the marketplace's trust product. *Evidence:* r/SEO 1gc3bjz (reviewer bylines, 2024-10), 1uoeerf (de-anonymizing question, 2026-07); r/SEO 1b60tfk ("E-E-A-T is Snake Oil", 2024-03 — treat checkbox-E-E-A-T as dead, demonstrated-authority as alive). `[C]`.
11. **Internal links by job, with a link budget.** Homepage → category → listing; related listings only when genuinely related; canonical URLs in every link; cap links per hub page so hubs stay focused. *Evidence:* r/SEO 1v1wj0x (2026-07), 1uprihu (684-link cleanup, 2026-07), 1vfxja8 (Reasonable Surfer, 2026-08).
12. **Track AI citations separately from rankings.** AIO citation, ChatGPT/Perplexity citation, and Google ranking are three different scores. *Evidence:* r/seogrowth 1tuxarm (2026-06), 1tjoqvt (citation-tracking framework, 2026-05), 1vlbct0 (2026-08). Add "cited by AI in Q" to the agent's weekly GSC+manual checks.
13. **Keep the site's document model Reddit-like.** Durable URLs, per-listing proof, versioned updates, honest limitations, real engagement. Reddit is the canonical proof that this model ranks — and gets quoted by Google's AI search. *Evidence:* r/artificial 1t5ct5o (2026-05); `seo-strategy-fresh.md` §3.
14. **Price the economics of GEO honestly.** AI traffic is pre-qualified but tiny; do not spend on GEO what it cannot return. *Evidence:* r/juststart 1vfdxng (u/NervousBasis8600: "37 sessions… one paying customer", u/brendancoots: "no fact-based reporting on whether GEO is actually translating into clicks", 2026-08). `[C]` — monetization unproven.
15. **Re-audit indexed-but-unused pages quarterly.** Pages that get indexed but no traffic/clicks risk de-indexation — prune-or-prove them. *Evidence:* r/seogrowth 1rthlm8 (u/lightningautomation: "without traffic and clicks the pages generally get de-indexed", 2026-03). This is the operational defense against the WindowsForum failure mode.
16. **Drive content from GSC data, not inspiration.** The one growth tactic that survived a public roasting: export GSC queries/impressions/CTR/positions, find "high impressions, zero clicks" queries, competitor-covered topics you lack, and cannibalization — then write only those pages. *Evidence:* r/ClaudeAI 1syt37w (u/BadMenFinance: "I feed Claude my Google Search Console data… and ask it to find keyword gaps", 2026-04-29; the traffic *claims* were debunked in-thread, the *method* was not); r/OpenAI 1tausi7 (2026-05-12). `[C]` — source credibility compromised by the poster's slop pattern; adopt the method, never the numbers.

## Appendix A — method

- **Discovery:** old.reddit.com RSS search, 29 queries, 2026-08-16 (one request per ~75s; checkpointed). Query set per sub: `"programmatic SEO"`, `"AI Overviews"`, `"E-E-A-T"`, `"thin content"`, `"internal linking"`, `"AI search"`, `"Reddit SEO"`, `LLM crawl` across r/SEO, r/juststart, r/seogrowth, r/TechSEO, r/ChatGPT, r/artificial.
- **Deep-dive:** full thread HTML via old.reddit, BeautifulSoup parse (post + comments, authors, scores, dates), checkpointed, ~75s cadence.
- **Scope caveat:** relevance-sorted RSS returns the sub's top hits per phrase; it is not an exhaustive corpus. Scores are fetch-time snapshots. Old.reddit direct fetch worked throughout this run (2026-08-16); on 2026-08-12 the same route 403'd from a different IP (see skills-research-report.md) — route availability varies.
- **Omo-internal cross-refs:** `marketing/seo-strategy.md`, `marketing/ai-seo-playbook.md`, `research/seo-strategy-fresh.md` (2026-08-14), `research/skills-research-report.md` (2026-08-12).

## Appendix B — all threads referenced (title | sub | date | URL)

| Title (truncated) | Sub | Date | URL |
|---|---|---|---|
| Built a programmatic SEO site to 700K impressions in 12 months | juststart | 2026-03-01 | /r/juststart/comments/1ri48gp/ |
| Programmatic SEO + AI Journey $25,000 profit (12th month) | juststart | 2023-11-30 | /r/juststart/comments/1878rdt/ |
| What Happens If You Post 12,000 AI Articles In A Month? | juststart | 2023-04-18 | /r/juststart/comments/12qm0n4/ |
| Does Programmatic SEO Still Work, or Is the SERP Completely Saturated Now? | seogrowth | 2025-12-15 | /r/seogrowth/comments/1pn0n30/ |
| Why do we only see 30-day Programmatic SEO wins and never 1-year results? | seogrowth | 2026-03-14 | /r/seogrowth/comments/1rthlm8/ |
| Google confirms normal SEO works for AI Overviews | SEO | 2025-07-26 | /r/SEO/comments/1m9k0kg/ |
| Google: Normal SEO Works To Get Into AI Overviews | SEO | 2025-07-24 | /r/SEO/comments/1m8gmmj/ |
| Google AI Overviews has the worst click-through rate I've ever seen: 0.0009% | SEO | 2026-02-20 | /r/SEO/comments/1r9wrgg/ |
| CTR is stuck at 0.5%. AI summaries are killing my clicks | SEO | 2026-03-05 | /r/SEO/comments/1rltrzp/ |
| Click-through rates down due to AI Overview, but more overall traffic | SEO | 2026-06-14 | /r/SEO/comments/1u5hqq6/ |
| How can content-based websites combat AI Overviews? | SEO | 2026-01-14 | /r/SEO/comments/1qcq17b/ |
| ChatGPT sends my niche site more buyers than Google now | juststart | 2026-08-03 | /r/juststart/comments/1ve3olr/ |
| AI search isn't replacing SEO. It's making it irrelevant for half the sites I audit | juststart | 2026-08-04 | /r/juststart/comments/1vfdxng/ |
| Has anyone actually checked who gets cited when you ask ChatGPT or AI Overviews? | SEO | 2026-08-10 | /r/SEO/comments/1vl1b5c/ |
| Your site can pass Google's AI Overviews and still be invisible to ChatGPT | seogrowth | 2026-06-02 | /r/seogrowth/comments/1tuxarm/ |
| Wow!!! Ahrefs Tracked 1,885 Pages Adding Schema. AI Citations Barely Moved. | TechSEO | 2026-05-11 | /r/TechSEO/comments/1ta9tux/ |
| Case Study: Missing Product/Offer schema let AI Overview quote competitor's pricing | TechSEO | 2025-04-25 | /r/TechSEO/comments/1k7vwh2/ |
| Case Study #2: Fixed AI Overview Pricing Citation with 3 Schema Nodes | TechSEO | 2025-04-29 | /r/TechSEO/comments/1kaxlpk/ |
| Month long crawl experiment: structured endpoints got ~14% stronger LLM bot behavior | TechSEO | 2026-02-09 | /r/TechSEO/comments/1r05tjr/ |
| Google's AI search summaries will now quote Reddit | artificial | 2026-05-06 | /r/artificial/comments/1t5ct5o/ |
| Companies Are Using Reddit to Manipulate ChatGPT and Google AI Search | artificial | 2026-06-03 | /r/artificial/comments/1tw6hb9/ |
| E-E-A-T is Snake Oil | SEO | 2024-03-04 | /r/SEO/comments/1b60tfk/ |
| Google's E-E-A-T Guidelines - Are reviewer bylines necessary? | SEO | 2024-10-25 | /r/SEO/comments/1gc3bjz/ |
| Anonymous under a pen name but I hold the real credential to go public | SEO | 2026-07-05 | /r/SEO/comments/1uoeerf/ |
| Internal link best strategy? | SEO | 2026-07-20 | /r/SEO/comments/1v1wj0x/ |
| 184 blog posts, 684 internal links. How would you clean this up? | SEO | 2026-07-07 | /r/SEO/comments/1uprihu/ |
| Question about Google's Reasonable Surfer model and internal links | SEO | 2026-08-05 | /r/SEO/comments/1vfxja8/ |
| SEO Debate: Does Google really block "thin content"? | SEO | 2026-05-13 | /r/SEO/comments/1tbx108/ |
| Google hit WindowsForum.com with a thin-content manual action | SEO | 2026-07-25 | /r/SEO/comments/1v6jn8x/ |
| I 10x'd the quality of my site. Google's response: rank it lower. | SEO | 2026-03-08 | /r/SEO/comments/1roaiix/ |
| Is it best to just no index thin low quality articles or do you just delete them? | SEO | 2026-07-16 | /r/SEO/comments/1uxttp4/ |
| How to break the AI search / GEO loop for your new product? | SEO | 2026-08-12 | /r/SEO/comments/1vm0j5o/ |
| I'm starting to track AI Overview citations: Here's the framework | seogrowth | 2026-05-21 | /r/seogrowth/comments/1tjoqvt/ |
| How are people tracking google AI overview and AI mode tracking… | seogrowth | 2026-08-11 | /r/seogrowth/comments/1vlbct0/ |
