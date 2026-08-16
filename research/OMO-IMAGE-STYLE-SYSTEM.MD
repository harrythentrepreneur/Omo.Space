# Omo Image Style System — the signature look (master style)

> The one composition system every Omo social image follows. Synthesized from
> the brand DNA (`research/BRAND-DNA.MD`), the 9-style library in the
> `omo-social-media-post` skill, and the site chrome (`site/nav.js`,
> `site/workflow-facts.css`, `site/covers/*`). This is the **default
> recommendation before theme selection**: pick a use-case variant here, then
> choose a theme from the skill's style library to color the prompt.
>
> **One-line brand (the truth test):** *"Buy the result, not another
> subscription."* Every image must look like it was made at a kitchen table,
> not in a corporation.

---

## 0. The signature in one paragraph

Every Omo image is a **cream canvas** (`#F8F7F5`, roughly half the pixels),
enclosed in a **pine frame** (a `#17352C` outline, 9px at 1600px scale,
rounded, inset from the edge), carrying **two to three pastel fields** (mint,
sky, butter, peach, lilac — never more) and exactly **one orange accent**
(`#FF6B3D`, ≤5% of colored area: one price, one number, one strike, one CTA).
Copy runs **Fraunces** for display and **DM Sans** for everything else; the
only thing allowed to lean is the **peach bean** at **−7°**. Art is **flat
vector** — solid fills, thick round-capped pine outlines, one hero object,
abstract faces (`•ᴗ•` or dot eyes). At least a quarter of the canvas stays
open. One message per image, exact numbers with units, no hype.

---

## 1. The canvas

| Property | Value (master 1600×900) | Scaling rule |
|---|---|---|
| Canvas fill | Cream `#F8F7F5` (cute register may warm to `#F7F3E8`) | dominant: ≥40–50% of pixels |
| Margin | 48px from canvas edge (3%) | proportional on other presets |
| Frame | Pine `#17352C`, 9px stroke, radius 28, inset 24px | stroke scales with width |
| Content zone | Inside frame, 48px padding | never smaller than 40px |
| Grid | 12 columns, 32px gutters, content zone width | align every tile to the grid |
| Open cream | 25–50% of canvas stays empty field | the more open, the calmer |

Presets (scaled from this master): X landscape 1600×900, IG/FB square
1080×1080, FB portrait 1080×1350. Everything below is given at 1600×900 and
scales linearly.

## 2. The frame (pine outline, 9px)

- A single rounded-rect outline in pine, **9px**, radius **28px**, inset
  **24px** from the canvas edge. The frame is the "packaging": it tells the
  feed this is an Omo card before the viewer reads a word.
- Content never touches the frame; keep ≥48px inside it.
- Optional frame badge: the peach bean (≤140px) may sit on the frame's
  top-left corner, peeking over the stroke, tilted −7°.
- Do not double-frame (no inner outlines around the whole canvas), do not add
  a shadow behind the frame, do not use white as the frame color.

## 3. Field composition

- **2–3 pastel fields** max per composition, chosen from: Mint `#BDEFD4`,
  Sky `#CFE8F7`, Butter `#FFE7A3`, Peach `#FFB89D`, Lilac `#DCCEF7`,
  Mint-deep `#78CCA1` (data series only). Fields are rounded tiles (radius
  18–28) or organic blobs; they sit behind objects, never behind text.
- **One orange accent, max 5%** of colored area. One price chip, one headline
  number, one strike-through, one CTA, one check. If orange appears twice it
  is competing with itself — cut the second one.
- **White cards** (`#FFFFFF`, ~8%) for text panels on cream; pale tints
  (`#F6F0E7`, `#F2F6F1`, `#FFF0E8`) for hover-warm fields.
- **Fields never carry text.** Text sits on cream, white, or pine — nothing
  else (contrast rule from the DNA).
- Hairlines and rules: `#D9E2DC`, 2–3px, round caps.
- Shadows, when needed: pine-tinted only, `rgba(23,53,44,.16)`, soft and
  large; never black, never hard.
- Ratio discipline (of colored area): cream ~50%, pine ~20%, mint ~12%,
  orange ≤5%, peach ≤5%, white ~8%, rule lines only.

## 4. Typography roles

| Role | Face / weight | Size @1600 | Use |
|---|---|---|---|
| Eyebrow / kicker | DM Sans 700, uppercase, +0.12em tracking | 20–24px | category, platform, date; muted ink `#5F6F68` |
| Headline | Fraunces 600, optical size ~96 | 64–96px, leading 1.02–1.08, −0.015em | the one message |
| Big number | Fraunces 800 | up to 140px | the one metric / price figure |
| Body | DM Sans 400/500 | 26–30px, leading 1.35 | supporting line, subtext `#4D5B56` |
| Label / chip | DM Sans 700 | 22–26px | facts, tags, CTA text |
| Data | DM Sans 400/500, **tabular numerals** | 22–28px | sourced figures, axis labels, sources — digits must not jitter |

- Color: pine `#17352C` on cream/white; cream on pine; muted `#5F6F68` for
  secondary text. Orange type is reserved for the one accent element.
- Font-replacement rule (image models): if the renderer can't draw Fraunces,
  use a close high-contrast soft serif; if it can't draw DM Sans, a clean
  geometric sans. Preserve exact wording above face fidelity.
- Total on-image words: 12–20 for launch/product, fewer for metrics (the
  numbers do the talking). If a word isn't needed, cut it.

## 5. The −7° tilt rule

- **One lean per composition, and it belongs to the bean.** The mascot's
  `rotate(-7)` (about its own center) is the brand's entire supply of
  playfulness.
- Headlines, tiles, frames, buttons, icons: always axis-aligned. Nothing else
  rotates. A stray rotated card or diagonal headline reads as sloppy, not
  cute.
- If the bean is absent, the composition is perfectly level — that is
  correct and calm.

## 6. Flat-vector rules

- Solid fills, crisp edges: no gradients, no gloss, no 3D extrusion, no
  texture, no photos (the site's photographic JPG covers are the known
  exception; social output stays flat).
- Hero outlines: **9px pine, round caps**, for the one hero object; 3–5px
  for small accents.
- **One hero object per composition** (book, chart, terminal, badge, bean) —
  never a collage, never a pile.
- Faces are abstract: the `•ᴗ•` text-face or simple dot eyes. No detailed
  human faces.
- Max **4 accent colors** total (fields + accents) in any one image; the
  palette list in §3 is closed — no new colors.
- Pine is the only dark ink. Never pure black, never gray.

## 7. White-space discipline

- 25–50% of the canvas stays open cream (metrics register may run tighter,
  editorial looser).
- Margins ≥48px at 1600; text-to-field padding ≥24px; chips/pills separated
  by ≥16px gutters.
- One message per image: one headline, one supporting line, one CTA. If a
  second message sneaks in, the post is two posts.
- Whitespace is not empty — it is the "kitchen-table" breath that separates
  Omo from ad-soup.

## 8. The bean mascot (optional)

- Geometry: peach `#FFB89D` super-ellipse blob (the logo's 39×34 CSS
  border-radius shape — "organic bean", not a circle), tilted **−7°**.
- Face: `•ᴗ•` in pine, weight 800, tight tracking; optionally a tiny check,
  heart, or star instead.
- Size: ≤12% of canvas width (≈190px at 1600). One bean per image.
- Placement: on the frame corner, beside the headline, or holding the result
  object. The bean is a wink, not a character cast — never both bean and a
  dot-eyed animal in the same field.

## 9. Text-tone rules

- Short sentences. Short words. One claim per post.
- Numbers are exact, sourced, and carry units: `$0.99`, `15 free skills`,
  `4-page PDF`. Never rounded for effect, never invented.
- No hype words: no "revolutionary", "game-changing", "unlimited", "magic".
  Omo words: simple, honest, open, built, works, yours, keep it.
- Admitting a limit is on-brand ("This does X, not Y"). It is the trust part.
- CTAs are plain: `omo.space`, `Get the workflow`, `Try it`, `Make your
  book`. Never "ACT NOW", never countdowns.
- If it can't be sourced, it doesn't go on-image.

---

## 10. Use-case variants

### 10.1 Launch (announcements, positioning, taglines)

**Intent:** one big announcement the feed stops on.
**Composition:**
- Eyebrow top-left (category/date), Fraunces headline bottom-left block (2–3
  lines, 72–88px), hero object bottom-right or top-right, CTA pill
  bottom-left, bean optional on the frame corner.
- Fields: mint + peach; headline sits on cream (never on a field).
- Orange accent: the strike-through on the anti-lock-in word, or the CTA
  underline — one only.
- Grid: headline occupies columns 1–8, hero object columns 9–12.
- Words ≤ 14.
- Themes that pair: `omo-editorial-news`, `omo-sweet-pastel`,
  `omo-bold-orange` (price-led launches), `omo-noir-sweet` (night register).

### 10.2 Product card (a workflow's "packaging")

**Intent:** make one result object feel worth paying for once.
**Composition:**
- Hero object centered (the book, the chart, the video still), drawn with
  9px pine outlines on a white or pale-tint panel; eyebrow above; price chip
  top-right of the object; 2–3 fact chips in a row beneath; CTA pill bottom.
- Fields: mint + butter (education products) or mint + sky (utility);
  summer-fun register allowed for phonics/kids.
- Orange accent: **the price chip** (`$0.99`, Fraunces 800 cream-on-orange
  or orange text on white) — everything else stays pine.
- Fact chips carry exact claims only: `4-page phonics PDF`, `Keep it. No
  subscription.` — no invented specs.
- Words ≤ 16.
- Themes: `omo-sweet-pastel`, `omo-summer-fun`, `omo-mint-flat`.

### 10.3 Education (how-it-works, phonics, kids)

**Intent:** a parent or teacher gets it in 3 seconds.
**Composition:**
- 2–4 chunky numbered steps, each a rounded tile with one flat icon and one
  short label; big Fraunces headline on top; result cue (check/star) on the
  final tile; CTA pill bottom.
- Fields: sky + butter + peach (bright but pastel, never neon); white text
  panels for anything longer than a label.
- Orange accent: the final "result" check/star, or the price chip.
- Generous padding everywhere; labels in DM Sans 700 ≥24px; no tiny text.
- Words ≤ 20 — labels stay short.
- Themes: `omo-summer-fun`, `omo-sweet-pastel`.

### 10.4 Metrics (evidence, sourced numbers)

**Intent:** one true number, told like a friendly fact.
**Composition:**
- One big number leads (Fraunces 800, ≤140px, with unit) in the top-left
  content zone; 2–4 compact supporting cards (white on cream) carry the
  breakdown; a source line (`Source: …`) sits at the bottom in muted ink.
- Fields: mint-deep `#78CCA1` only for data series bars; mint + white for
  cards; charts are simple rounded bars, flat.
- Orange accent: the big number itself (or one key bar) — one only.
- Every figure carries units and a source; never a number without a source
  line.
- Words ≤ 14; the digits do the talking.
- Themes: `omo-data-clean`, `omo-terminal` (OSS evidence).

---

## 11. Do / Don't

**Do:**
1. Lead with cream (~50%), ink with pine, warm with mint, point with orange
   (once).
2. Frame every post with the 9px pine rounded outline.
3. Keep 2–3 pastel fields max, and keep text off pastels.
4. Set display copy in Fraunces and everything else in DM Sans (tabular
   numerals for figures).
5. Let the −7° tilt belong to the bean alone — one lean per composition.
6. Draw flat: solid fills, 9px round-capped pine outlines, one hero object.
7. Leave 25–50% of the canvas open.
8. Print exact, sourced numbers with units on-image.
9. Use the bean / `•ᴗ•` / dot-eyes sparingly as the wink.
10. End with one plain CTA (`omo.space`, "Get the workflow", "Try it").

**Don't:**
1. Use black, pure grays, or neon; never let orange outnumber mint.
2. Use more than one orange accent — one price, one number, one strike.
3. Put text on a pastel field or let text touch a field edge.
4. Rotate anything except the bean — no tilted headlines or cards.
5. Mix in gradients, gloss, 3D, photos, or textures (flat vector only).
6. Add a second hero object, sticker piles, or confetti.
7. Crowd the canvas — below 25% open cream is clutter.
8. Print invented metrics, fake testimonials, or unsourced claims.
9. Use hype words, countdowns, "ACT NOW", or urgency clichés.
10. Redraw the logo wordmark from scratch — use the asset or plain
    `omo.space` text.

---

## 12. Sources & artifacts

- Synthesized from: `research/BRAND-DNA.MD` (tokens, ratios, tilt, tone),
  the 9 style specs in the `omo-social-media-post` skill
  (`references/styles/*.md`), and the site chrome (`site/nav.js`,
  `site/workflow-facts.css`, `site/covers/meta-ads-analyser.svg`,
  `site/logo-sweet-pastel.svg`).
- Rendered style sheet (this system, visual):
  - `research/social-assets/style-sheet/style-sheet-system.png` (1600×1200 —
    palette, type, grid anatomy)
  - `research/social-assets/style-sheet/style-sheet-variants.png` (1600×1200 —
    the 4 variants + do/don't)
- Signature post proofs (1600×900 each):
  - `research/social-assets/posts/tagline-buy-the-result/image.png`
  - `research/social-assets/posts/decodable-book-card/image.png`
  - `research/social-assets/posts/open-source-library/image.png`
- Fonts used by the renders: `research/social-assets/fonts/` (Fraunces
  variable, DM Sans variable — Google Fonts, OFL).
