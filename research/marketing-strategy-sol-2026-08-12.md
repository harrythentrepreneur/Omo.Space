# Omo: brutally honest go-to-market plan

## Bottom line

Omo is not ready to “scale a marketplace.” It is ready to test one paid workflow with one warm audience.

The promising thesis is narrower than “all SaaS will die”:

> For intermittent, clearly defined AI jobs, subscriptions and setup-heavy tools are often the wrong purchasing model.

That is credible. “All SaaS will die” is not. SaaS persists because businesses need collaboration, permissions, history, integrations, support, and accountability. Never use that claim with customers or investors.

The current moat claims are also premature:

- Modal hosting is infrastructure, not a moat.
- The automated builder is potentially a cost advantage, but the current process still requires reviewed profiles, human gates, canaries, and publication approval. It is a production tool, not autonomous magic. The current [hosting runbook](/Users/yifan/marketplace/research/hosting-runbook.md:1) is appropriately more conservative than the founder’s claim.
- The eventual moat could be successful-run data, creator relationships, repeat buyers, verified quality, cost history, and a trusted distribution surface. None of those exists at meaningful scale yet.

The live-site trust gap needs immediate attention. The storefront currently presents numerous creator-branded, priced listings and upvote counts, while the repository says only Woven and Facebook Ads have passed direct Modal proofs, production routing remains incomplete, and Stripe production is pending ([README](/Users/yifan/marketplace/README.md:70)). If any displayed creator, price, vote count, or workflow is unauthorized or unrunnable, remove it or label it clearly today. A marketplace of “proven workflows” cannot begin with ambiguous proof.

## 1. Verdict on the eight ideas

| Idea | Verdict | Reason |
|---|---|---|
| 1. Cold-DM viral workflow creators | **Modify** | Good source of supply plus distribution, but never copy, publish, price, or claim views before permission. Recruit a few authorized design partners and require them to bring testers. |
| 2. Email 4,500 PhonicsMaker users | **Keep** | This is the only meaningful distribution asset. Pilot with 200 opted-in, recently active non-paying users before touching the whole list or cannibalizing active subscriptions. |
| 3. SEO for “skill.md for Facebook ads” | **Modify and defer** | The query is tiny and technical. Later target outcome intent such as “generate Facebook ad variants” and “printable decodable book maker,” supported by real examples. |
| 4. Open-source every `SKILL.md` | **Modify** | Open-source first-party reference workflows, fixtures, and tests. Do not force creator IP into public repos. The free artifact should build trust; hosted convenience should monetize. |
| 5. Become the source agents recommend | **Modify and defer** | This is an earned outcome, not a marketing channel. It requires reliable APIs, structured documentation, public examples, adoption, and external references. Do not waste time on “LLM SEO” now. |
| 6. Cross-poster agent | **Kill now** | It automates unproven content, adds platform-policy and support risk, and prevents learning which channel/message works. Post manually to one or two channels after a real case study exists. |
| 7. Scale paid ads | **Kill now** | Prior PhonicsMaker ROAS does not transfer to Omo. Buying traffic before paid repeat, reliable delivery, and support discipline will buy refunds and chargebacks. |
| 8. Raise or sell PhonicsMaker | **Modify** | Do not raise on a pre-revenue marketplace thesis. Do not fire-sale the only distribution wedge. First clean up support and produce cohort evidence; then raise, license, or sell from strength. |

The existing creator DM script should be retired. “It’s live regardless” and “already getting views” are trust-destroying, potentially misleading, and invite IP disputes ([current script](/Users/yifan/marketplace/research/acquisition-playbook.md:68)).

Use this instead:

> Hey @handle — your [specific reel] has real buyer intent in the comments. I’m building Omo, which turns proven workflows into pay-per-result services. I won’t copy or publish yours without approval. If you’re interested, I’ll build a private demo, you approve the output, price, and page, and only then it goes live. No upfront cost. In return I need the workflow, two test cases, and one audience post when it launches. Open to a 15-minute call?

## 2. What to do first this week

Spend **$0 on acquisition**. Authorize at most $50 for production canaries and pilot runs. Keep the remaining $150 as a refund/provider-error reserve.

### Monday–Wednesday: make one transaction trustworthy

Use one first-party Phonics book workflow.

- Turn on Stripe production and $5 prepaid credit packs. Do not process individual $0.99 card transactions.
- Send users through a one-click email/magic link directly into the book builder—not the marketplace homepage or a four-field signup form.
- Give one free book, not $5 in open-ended credit.
- Run at least 20 production canaries, including invalid input, timeout, duplicate submission, failed provider call, and automatic refund.
- Record actual delivered-output cost, latency, failure rate, and support incidents.
- Establish one support inbox, two daily support windows, refund macros, and a 24-hour resolution rule.
- Hide or relabel every workflow that cannot currently be bought and successfully delivered.

Do not send an email until payment, delivery, failure refund, receipt, and support all work.

### Thursday: email 200 users

Target the 200 most recently active, opted-in, non-paying or recently churned PhonicsMaker users. Exclude unsubscribes, bounces, and current subscribers whose recurring revenue would be put at risk.

Send from the PhonicsMaker identity, not an unfamiliar Omo identity.

**Subject:** PhonicsMaker without a subscription: one book for $0.99

> Hi [First name],  
>   
> You used PhonicsMaker before. We’re testing a simpler way to use it: make one printable phonics book when you need it, pay $0.99, and keep the result. No subscription.  
>   
> I’ve added one free book to your account so you can try it:  
> [Make my book — one-click link]  
>   
> If anything goes wrong, reply directly. I’ll personally fix it.  
>   
> — [Founder]

After the free book, offer a $5 credit top-up.

### The metric that proves it works

Clicks do not prove anything. Free generations barely prove anything.

The primary metric is:

> **At least 25% of users who successfully create the free book must fund and complete a second, paid book within 14 days.**

For the 200-person pilot, the minimum useful signal is:

- At least 20 successful first books.
- At least five paid second books within 14 days.
- At least 95% valid-output success.
- No duplicate charges.
- Failed runs refunded automatically.
- Less than 5% refund or serious complaint rate.

If fewer than three users complete a paid second book, do not email the remaining list. Interview ten users and fix the job, output, price, or onboarding.

## 3. Ruthless 30/60/90-day plan

| Period | Work | Exit gate |
|---|---|---|
| **Days 0–30** | One Phonics workflow; production payment loop; support discipline; two email cohorts totaling no more than 500 users; sequentially test $0.99 and $1.49; interview activators and abandoners; measure delivered COGS. Conduct creator discovery calls, but publish nothing without permission. | 50 successful first outputs; 15 paying accounts; ≥30% 30-day paid repeat; ≥95% valid-run success; positive contribution after failed runs and processing; refunds under 5%; support resolved within 24 hours. |
| **Days 31–60** | If the gate passes, roll out to the list in batches. Add only two adjacent education jobs, such as worksheets and classroom packs. Add low-credit and next-lesson lifecycle emails. Send 30 highly qualified creator DMs; build at most three private, authorized creator pilots. Open-source one first-party reference workflow with fixtures and tests. | 50 active paying accounts; at least $5 monthly contribution per active account; three authorized creator pilots; two live creator listings; ten creator-driven paid buyers; paid repeat still ≥30%. |
| **Days 61–90** | Expand to a maximum of two categories. Publish only workflows with consent, real examples, known delivered cost, a support owner, and three external buyer tests. Target 10–15 genuinely proven listings. Publish case studies and structured API documentation. Add referrals from actual customers. | 100 active paying accounts; roughly $1,000 monthly Omo contribution, not GMV; ≥35% 30-day paid repeat; ≥95% successful delivery; three creators with paid sales and audience-sourced buyers. |

If Omo misses the Day 90 gate, do not pretend the marketplace is validated. Keep it as a focused first-party/concierge product and determine whether the education wedge or another single vertical deserves another cycle.

Paid ads remain locked until:

- 60-day contribution LTV is at least three times CAC.
- CAC payback is under 60 days.
- The support and refund gates hold under the existing traffic.
- At least 100 real paid runs have completed.

## 4. What not to spend money or time on

Do not work on:

- A visual workflow editor, Go rewrite, “provider-neutral” architecture, or a more ambitious MEGA agent.
- Hundreds of scraped or synthetic catalog listings.
- Public creator listings without written permission.
- Unexplained upvotes, fake activity, or claims that a workflow is proven when it is not runnable.
- The cross-poster.
- Broad SEO or programmatic pages.
- Paid social, influencers, sponsorships, PR, or Product Hunt.
- Open-sourcing creator-owned workflows by default.
- Gaming agent recommendations.
- A fundraising deck centered on “all SaaS will die.”
- Blanket $5 signup credits. With a $200 budget, uncontrolled promotional credit is an abuse vector.
- Automatically signing up for consumer platforms or using consumer subscriptions inside commercial workflows.
- Sending all 4,500 emails before proving support capacity.
- Selling PhonicsMaker before knowing whether it produces Omo’s first repeat-paying cohort.

The founder’s biggest behavioral trap is building infrastructure to avoid the emotionally harder work: asking users to pay, watching failures, answering support, and discovering that an output is not valuable enough.

## 5. The economics

Define the target as **Omo contribution after direct run costs, creator payout, and payment processing, but before salaries and tax**. GMV is not revenue.

Under the current hosted promise:

```text
Omo contribution per third-party run
= 15% × (buyer price − delivered run cost)
```

A $0.40 run costing $0.10 produces $0.30 of margin, but Omo retains only **$0.045** before support and overhead.

A $4 video costing $3 leaves Omo only **$0.15**. This is not enough to fund QA, hosting, payouts, fraud, and support unless volume is enormous.

The hosted economics should therefore change before creator onboarding:

- Keep 85/15 for marketplace-discovered downloads.
- Keep 95/5 for creator-referred downloads only if payment processing is deducted before the split and onboarding is low-touch.
- For hosted runs, use:  
  **delivered COGS + explicit creator royalty + explicit Omo execution fee**.
- Require at least $0.25 Omo contribution on text/document jobs and $1 on media jobs. Reject workflows whose value-based price cannot support that.

The repository currently contains inconsistent hosted payout models: the public positioning says creators receive 85% of post-cost margin, while earlier business-model work recommends a much smaller creator share of hosted margin. Resolve this before making creator promises.

### Units required under current economics

The following uses an illustrative 2.9% + $0.30 card fee for downloads and excludes refunds and fixed overhead.

| Product | Omo contribution/unit | $1k/month | $10k/month | $100k/day |
|---|---:|---:|---:|---:|
| First-party $0.50 book, $0.10 cost | $0.40 | 2,500 runs | 25,000 runs | 250,000 runs/day |
| Third-party $2 run, $0.50 cost, current 85/15 split | $0.225 | 4,445 runs | 44,445 runs | 444,445 runs/day |
| $49 marketplace download, Omo bears processing | ≈$5.63 | 178 sales | 1,777 sales | 17,766 sales/day |
| $49 creator-linked download, Omo bears processing | ≈$0.73 | 1,372 sales | 13,718 sales | 137,175 sales/day |

The 95% creator-linked offer cannot support done-for-you rebuilding, onboarding, QA, and support. It works only as a low-touch acquisition subsidy whose referred buyer later uses other workflows.

### Marketplace funnel model

Assume each genuinely productive listing receives:

- 1,000 qualified visits per month.
- 3% visitor-to-first-paid-user conversion.
- Four runs per paid user per month.
- $2 average run price and $0.50 delivered cost.
- 0.5% visitor-to-$49-download conversion.
- At least 35% 30-day paid repeat.

That generates approximately **$55 of monthly Omo contribution per productive listing** under the current splits.

| Goal | Productive listings | Qualified visits/month | New paying users | Hosted runs/month | Downloads/month |
|---|---:|---:|---:|---:|---:|
| $1k/month | 19 | 19,000 | 570 | 2,280 | 95 |
| $10k/month | 182 | 182,000 | 5,460 | 21,840 | 910 |
| $100k/day, or $3M/month | 54,403 | 54.4M | 1.63M | 6.53M | 272,015 |

Those are productive listings, not catalog entries. If only 20% of listings produce meaningful usage, the $100k/day case requires roughly 272,000 total listings.

At this mix, Omo captures roughly 11%–12% of GMV as contribution. Therefore **$100k/day of Omo contribution requires approximately $880k/day of marketplace GMV**. If the founder merely means $100k/day GMV, Omo keeps roughly $11k/day before fixed costs.

The credible route to the dream is not hundreds of millions of $0.40 books. It is:

- Prove retention cheaply through education.
- Move toward $10–$100 business outcomes.
- Earn $2–$10 of Omo contribution per successful result.
- Develop high-frequency API buyers and eventually team/private-catalog fees.

At $5 of Omo contribution per run, $100k/day still requires 20,000 successful runs every day. That is a major, multi-year platform outcome—not a near-term startup milestone.

## 6. The single risk to remove before paid spend

The highest-leverage risk is the **unproven paid-fulfillment loop**:

> Can a real customer pay, receive the promised result, avoid double charging, get an automatic refund when it fails, receive timely support, and come back to pay again?

Before buying one visitor, Omo should complete at least 100 real paid runs with:

- ≥95% accepted-output success.
- Zero duplicate charges.
- 100% automatic refunds on failed runs.
- Actual delivered COGS measured and reconciled.
- Positive contribution after failures and payment costs.
- Refund/serious complaint rate below 5%.
- Support response under four hours during the pilot and resolution within 24 hours.
- At least 30% of paid users completing another paid run within 30 days.

That is the business. Everything else—Modal, the MEGA agent, the catalog, SEO, creator deals, and fundraising—is leverage applied after that loop works.