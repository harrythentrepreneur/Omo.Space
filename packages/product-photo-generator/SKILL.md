---
name: product-photo-generator
description: "Turn a product photo into a ready-to-use ecommerce listing image set — clean background, lifestyle shot, and a hero crop — without a studio."
version: 1.0.0
author: Cognition
license: proprietary
metadata:
  bench:
    id: product-photo-generator
    category: make-content
    niche: ecom-photography
    price_license: 29
    price_run: 10
    price_maintain: 9
    demo_caps:
      free_sessions_per_day: 5
      max_tokens_per_session: 4000
      max_steps_per_session: 1
    input_schema:
      product_description: string
      photo_url: string
      style: enum [clean, lifestyle, hero]
    output_schema:
      shot_plan: array[string]
      background_suggestion: string
      caption: string
      listing_copy: string
    runtime:
      model: deepseek-v4-flash
      adapter: bench-cloudflare-workers
    creator:
      handle: "@shotforjoe"
      name: "Joe Martell"
      split: 85
---

# Product Photo Generator

Turn one product photo into a full listing image plan: clean-background shot,
lifestyle scene, and a hero crop — with the caption and listing copy to match.
Built for Shopify sellers who can't afford a studio.

## When to use

- You have a single product photo and need a full listing set
- You're testing a new product and want listing images before ordering samples
- You need caption + copy that converts, not just images

## How it works (the flow the demo runs)

1. **Input** — product description + photo URL + style (clean / lifestyle / hero)
2. **Analyze** — what the product is, its key features, who buys it
3. **Plan** — 3-5 shots: angles, backgrounds, props, and which crop to lead with
4. **Deliver** — shot plan, background suggestion, caption, and listing copy

## Example

Input:
- product_description: "Handmade ceramic coffee mug, 12oz, matte sage glaze"
- style: lifestyle

Output (abridged):
- shot_plan: ["Hero: mug on walnut table, morning light, steam rising",
  "CU: sage glaze texture, hand in frame", "Lifestyle: laptop + mug + notebook,
  cozy corner", "Packaging shot: box with thank-you card"]
- background_suggestion: "Warm neutral (linen or oak) — keeps the sage green the star"
- caption: "your 7am ritual, upgraded ☕"
- listing_copy: "Hand-thrown in small batches…"

## Versioning

- v1.0.0 — initial release (2026-08-08)
- License: one-time purchase, perpetual, non-transferable
- Updates: buyers get new versions automatically

## Support

- Creator: @shotforjoe on Instagram
- Cognition support: support@cognition.cv
