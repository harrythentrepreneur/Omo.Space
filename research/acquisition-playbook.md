# Cognition — Customer Acquisition Playbook (v1, 2026-08-08)

Mission context (from the founder, verbatim): find workflows on Instagram reels /
TikTok that have gone viral, add them to the marketplace, then DM the creators:
"we hosted your skill + made you a sales page, you get paid per sale — want your
link?" Short shareable domain. The founder DMs when human help is needed.

---

## 1. The wedge: who we sell to FIRST

**Target creator profile:** IG/TikTok accounts posting AI-workflow demos with
"DM me for the workflow" / "link in bio" / GitHub link in comments. Typically
2k–200k followers, monetizing nothing, already producing content every day.

**Target buyer profile:** ecom brands / small businesses who comment "how do I
use this?" — they want the OUTPUT, not the setup.

**First 3 niches to fill (from founder's list):**
1. UGC ad scripts (Google Omni UGC style, HeyGen, Actor Maker) → sell to ecom brands
2. Meta Ads API analyser → sell to media buyers
3. Product-photo / listing generators → sell to Shopify sellers

Rule: pick niches where the buyer is a BUSINESS with money, not a hobbyist.

---

## 2. Finding viral workflows (the mining loop)

### Daily scan (30 min, repeatable)
1. **IG Reels:** search `AI workflow`, `AI automation`, `ChatGPT hack`, `make money AI`,
   `n8n`, `Claude`, `AI agent` — sorted by recent, note accounts with 1k+ likes
   whose caption/comment says "DM me".
2. **TikTok:** same queries + `workflow for sale`, `prompt pack`.
3. **YouTube Shorts:** same.
4. **Reddit:** r/ChatGPT, r/ClaudeAI, r/automation, r/nocode — "I built X, sharing
   the GitHub" posts with engagement.
5. **Pinterest/Threads:** lighter, check weekly.

### Qualification checklist (all must pass)
- [ ] The demo is visual & impressive in <30 seconds
- [ ] Output is a deliverable a business pays for (script, ad, image, report)
- [ ] Creator posts regularly (weekly minimum) — they'll keep selling
- [ ] No existing paywall / they currently give it away free (our pitch works)
- [ ] Workflow is replicable from a config (SKILL.md / prompt / n8n JSON)

### The listing pipeline
1. Save creator handle + reel link + what the workflow does (research/)
2. Rebuild the workflow as a Cognition package (SKILL.md + config + demo)
3. Create the sales page from `landing/sales/sales-template.html`
4. Draft the DM (section 4) → send → log in `research/outreach-log.csv`
5. If they say yes: point their link to our page, 95/5 creator-referred split

---

## 3. The demo hosting (what makes DMs work)

The DM only works if the link shows a REAL working thing. Per listing:
- Host the workflow on Cognition infra (Cloudflare Workers + DeepSeek V4 Flash =
  ~$0.0035/session — free tier: 5 capped sessions/day)
- Sales page shows: try-it box, INPUT→OUTPUT examples, price, the money line
- The "demo-with-cap" protects the creator's prompt (they can't be copied)

---

## 4. DM scripts (copy-paste)

### Cold DM — creator found via reel (TikTok/IG)
```
hey @{handle} — saw your {reel topic} reel, the {X} workflow is genuinely
useful 🔥

we put it on a store page so people can use it instantly (no "dm me", no
github setup) — and you'd get paid every time someone buys or runs it.

your page: {url}
you keep 85% of each sale. want me to switch the "dm me" in your bio to this
link instead?

no pressure either way — it's live regardless, happy to take it down.
```

### Follow-up (3-4 days later, if no reply)
```
hey! not sure you saw this — your {workflow} is live on {url} and it's already
getting views. you keep 85% of every sale, and I'll handle all the hosting +
payments. want the link for your bio?
```

### Reply to "how does this work?"
```
super simple:
1. I host your workflow — people try it free (capped so your prompt stays yours)
2. when someone buys: you keep 85% (95% if it's from YOUR link)
3. you can push updates anytime, everyone who bought gets the new version
4. if they run it on the platform, you get 20% of the profit after costs

no code, no payment setup, no hosting. your job is just making cool stuff.
```

### The ask (when they're in)
```
to go live I just need:
- the workflow files (or I rebuild it from your demo — same output)
- your name/handle + a cover image (I can make one)
- the price you want to charge

I'll have the page ready in a day. you keep 85% of every sale. deal? 👌
```

---

## 5. The numbers (unit economics for outreach volume)

| Metric | Value |
|---|---|
| DM → reply rate (expected, cold) | 10–25% |
| Reply → listed | 30–50% |
| Listed → first sale | 7–14 days |
| License price (niche business tool) | $29–$99 |
| Creator keeps (85%) | $25–$84 |
| Our cut per sale | 15% |
| Hosting cost per session (cheap stack) | ~$0.0035 |
| Demo free tier | 5 capped sessions/day |

**Path to $100k MRR (scenario):**
- 200 active listings × $49 avg license × 10 sales/mo each = $98k creator-side
  → Bench keeps 15% = ~$14.7k/mo + hosting margin + maintenance subs
- OR fewer, bigger: 40 listings × $99 × 25 sales/mo = $99k → ~$15k/mo to Cognition
- Realistic 90-day target: 25 listings, first $1k/mo. Then double every 6 weeks.

---

## 6. What the founder does vs what I do

| Task | Who |
|---|---|
| Mining reels/TikTok for workflows | ME (research) — founder watches + sends reels |
| Rebuilding workflow as Cognition package | ME |
| Sales page per creator | ME (template above) |
| Sending DMs | FOUNDER (their IG account = trust) — I draft every DM |
| Replying to DMs | FOUNDER, with my drafted replies |
| Domain purchase (~$10–12) | FOUNDER (their card) — I recommend + verify |
| Hosting infra setup | ME |
| Payments/Stripe account | FOUNDER (KYC needs a human) |
| Legal pages (terms/privacy) | ME, founder reviews |

---

## 7. First week action list

- [x] Domain: cognition.cv (user-owned, Cloudflare-ready) — deploy site/ to Cloudflare Pages
- [ ] Point it at landing/variations/landing-v6-workshop.html (storefront)
- [ ] Mine IG/TikTok for first 10 creator candidates → research/creators.csv
- [ ] Rebuild first 3 workflows (UGC script studio, Meta Ads analyser, product
      photo) as Cognition packages
- [ ] Create 3 sales pages from the template
- [ ] Founder sends first 5 DMs using scripts above
- [ ] Set up Stripe account (founder) for checkout + payouts
- [ ] Log every outreach in research/outreach-log.csv
