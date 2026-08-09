---
name: meta-ads-api-analyser
description: "Paste a Meta Ads account ID or export. Get a plain-language breakdown of what's working, what's burning money, and what to change next."
version: 1.0.0
author: Bench
license: proprietary
metadata:
  bench:
    id: meta-ads-api-analyser
    category: get-leads
    niche: ecom-media-buying
    price_license: 49
    price_run: 20
    price_maintain: 15
    demo_caps:
      free_sessions_per_day: 3
      max_tokens_per_session: 5000
      max_steps_per_session: 1
    input_schema:
      ads_export: file_or_text
      goal: enum [roas, cpa, ctr, scale]
    output_schema:
      verdict: string
      winners: array[string]
      losers: array[string]
      quick_wins: array[string]
      next_move: string
    runtime:
      model: deepseek-v4-flash
      adapter: bench-cloudflare-workers
    creator:
      handle: "@adswhisperer"
      name: "Dana Okafor"
      split: 85
---

# Meta Ads API Analyser

Paste your Meta Ads numbers. Get a plain-language read: which ads are printing
money, which are burning it, and the single highest-leverage change for next
week. Built for media buyers and ecom owners who don't have time to stare at
spreadsheets.

## When to use

- Weekly ad account review — before you touch the dashboard
- Deciding what to kill vs scale (ROAS / CPA / CTR reads)
- Explaining account performance to a client or boss in plain words

## How it works (the flow the demo runs)

1. **Input** — ad set / campaign export (CSV paste or file) + your goal
   (ROAS, CPA, CTR, or scale)
2. **Read** — normalize spend, impressions, clicks, purchases, revenue per row
3. **Judge** — flag winners (above goal, enough data), losers (spending without
   returning), and "undecided" (too little data to trust)
4. **Advise** — the next move: scale X, kill Y, test Z, or wait for data
5. **Deliver** — verdict, winners, losers, quick wins, next move — in plain words

## Example

Input (goal: ROAS 2.5):
```
campaign,spend,impressions,clicks,purchases,revenue
prospecting-v1,412.00,82000,3100,38,1876.00
retarget-v2,198.00,14000,980,52,2210.00
brand-test,150.00,61000,220,2,87.00
```

Output (abridged):
- verdict: "Retargeting is carrying the account; prospecting is borderline."
- winners: ["retarget-v2 — ROAS 11.2, keep scaling +20%/week"]
- losers: ["brand-test — ROAS 0.6 after $150; kill or change creative entirely"]
- quick_wins: ["Move 20% of prospecting budget into retarget-v2", "Pause brand-test, reuse its best creative in prospecting"]
- next_move: "Shift spend toward retarget-v2 this week, re-test prospecting with new angles."

## Versioning

- v1.0.0 — initial release (2026-08-08)
- License: one-time purchase, perpetual, non-transferable
- Updates: buyers get new versions automatically

## Support

- Creator: @adswhisperer on Instagram
- Bench support: support@dmmedone.com
