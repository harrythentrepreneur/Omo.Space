 # Omo Brand DNA — A Reading of the Brand from Its Own Files

> Source of truth: this document is extracted **from the product's own artifacts**,
> not from a wish list. Every claim below was read from a real file in this repo
> (paths listed per section). Where the brand has drifted between surfaces, the
> drift is called out. Plain words, no hype — this is the working reference for
> anyone making Omo visuals.

**One-line brand:** *"Buy the result, not another subscription."* Omo is a
marketplace where you buy a **workflow** (a runnable result) instead of renting
software. Everything visual follows from that: warmth instead of slickness,
honesty instead of hype, craft instead of chrome.

---

## 1. The Logo — `site/logo-sweet-pastel.svg`

The mark is two parts on a 128×40 canvas: a **peach bean with a face** beside a
lowercase **"omo" wordmark**. Official description embedded in the file:

> "A peach organic bean with the text face •ᴗ• beside the lowercase omo wordmark."

### The bean (the mascot)

| Property | Value (from file) |
|---|---|
| Shape | Organic blob, `d="M20.28 0A18.72 15.3 ..."` — explicitly derived from the concept's **39×34 CSS border-radius blob** (i.e. a super-ellipse, not a circle) |
| Fill | `#FFB89D` (peach) |
| Inset shadow | `#F47F78` at 20% opacity, offset (−3, −4) — a soft internal highlight, **not** a hard drop shadow |
| Rotation | `rotate(-7)` — the bean tilts, never sits perfectly straight |
| Face | The text `•ᴗ•` — two dots and a smile, rendered in the same deep pine as the wordmark, `font-weight: 800`, tight `letter-spacing: -1.2` |

### The wordmark

- **"omo" lowercase**, single path, filled `#17352C` — the logo's one and only
  non-peach color.
- Outlined from **Baloo 2 ExtraBold** (per file metadata): a rounded, chunky,
  friendly display face. The o's are near-circles with an organic inner
  counter; the m's arches are rounded.
- The wordmark is used **at rest, straight** — the playfulness lives in the
  bean, the trust lives in the word.

### What the logo says

- **One accent color + one dark color.** The entire mark is peach on pine.
  No gradients, no outlines, no 3D. Maximal simplicity.
- **The tilt is the personality.** A −7° lean is "handmade, almost but not
  quite symmetric." Combined with the face, the mark is cute without being
  childish, friendly without being slapstick.
- **The face IS the brand.** `•ᴗ•` is the single most reusable brand element:
  it appears in the logo, and the style system reuses it as a micro-cue in
  icons and characters.
- **Weight = warmth.** The bean is filled and solid; the wordmark is heavy
  (ExtraBold). Omo never draws itself in thin, delicate lines.

---

## 2. The Chrome Typography — `site/nav.js`, `site/workflow-facts.css`, `site/menu-workflows.css`

The site chrome is where the *product* talks, and it uses two faces with total
discipline:

| Role | Face | Evidence |
|---|---|---|
| Display / product identity | **Fraunces** 600, `Georgia, serif` fallback, `letter-spacing: -.015em` | `workflow-facts.css` sets `--display: "Fraunces", Georgia, serif` for `h1,h2,h3` with `font-weight: 600`; `nav.js` uses `font: 600 15px/1.12 "Fraunces", Georgia, serif` for the current-workflow identity in the nav |
| Body / UI / labels | **DM Sans**, `Inter, system-ui` fallback | `workflow-facts.css` `--body`; nav links at `font-size: 13.5px; font-weight: 650` (a semi-bold, friendly-but-legible weight) |

Supporting observations from the chrome CSS (all real values):

- **Pine is the "ink."** `var(--pine,#17352C)` is used for nearly all text.
- **Muted text** is a warm gray-green: `#4D5B56`, `#6F7E77`, `#777A77` — never
  cold gray, never black.
- **Pills everywhere.** Buttons, the balance chip, and the menu toggle are
  `border-radius: 999px`; cards and rows use 8–15px radii; popovers 15px.
- **Tabular numerals** for money/balances (`font-variant-numeric: tabular-nums`)
  — numbers must not jitter.
- **Warm hover states:** `#F6F0E7` (warm cream) on hover; the "sell" icon gets
  a peach-tinted field `#FFF0E8` with a deep orange glyph `#C65B3A`.
- **Soft shadows:** `0 20px 48px rgba(23,53,44,.16)` — shadows are *pine-tinted*,
  never neutral black.
- **Header field** is pale mint-tinted cream `#F2F6F1` with a `#D9E2DC` rule.
- **Focus rings** are `rgba(255,107,61,.3)` — orange is the "attention" color
  even in the a11y layer.

**Takeaway:** the chrome is quiet UI that lets the serif do one job (name a
thing with character) and the sans do the rest (be legible, be kind).

---

## 3. The Covers' Visual Language — `site/covers/` (225 files)

Covers are the marketplace's "packaging." Two families exist:

### Family A — flat-vector product covers (SVGs, readable directly)

`meta-ads-analyser.svg` — a near-perfect token map of the brand:

```
#17352C  ×8   pine  — every outline, every dark glyph
#FF6B3D  ×4   orange — the one accent, used on key objects
#BDEFD4  ×4   mint   — the friendly field color
#FFFFFF  ×3   white  — clean panels
#6F7E77  ×2   muted gray-green — secondary labels
#F2F6F1  ×1   pale mint-tinted cream — canvas
#D9E2DC  ×1   quiet rule
```

`decodable-book-maker.svg` (a PhonicsMaker-adjacent cover) shows the *cute*
register of the same system: cream canvas `#F7F3E8`, a storybook with **9px
pine outlines**, a butter-yellow cat `#F9C74F` with **two dot eyes**, a mint
map `#9EE6C5`, blue `#4C6FFF` and coral `#FF6B5E` as bright-but-pastel
accents, rounded tiles (`rx=18`), and a **checkmark badge**. Faces are
abstract (dot eyes), objects are chunky and friendly.

### Family B — photographic/3D-generated covers (JPG/WebP, ~215 files)

The majority of covers are AI-generated JPGs/WebPs (thumbnail cards for
workflows). These are *looser* — some are 3D-ish renders or photos — which is
a known drift in the system: the SVG covers are the canonical brand voice,
the JPG covers are the fast-and-varied voice. The style system built in
`omo-social-media-post` exists partly to pull social output back to the
canonical flat-vector voice.

### Covers' shared grammar

1. **Canvas = cream** (`#F8F7F5` / `#F2F6F1` / `#F7F3E8` family).
2. **One hero object** (book, badge, cat, chart, character) — never a collage.
3. **Thick rounded pine outlines** for the hero (7–9px at 1200px scale).
4. **2–3 pastel fields** (mint, butter, sky, peach) + **one orange accent**.
5. **Flat. No gradients, no photos, no texture** (family A).
6. **A tiny check, star, or heart** as the "result" cue.

---

## 4. The Mood

Four words, in priority order:

- **Cute** — the bean, the face, the tilt, the rounded everything. Cute is
  the *entry point*: it disarms, invites a click, feels safe.
- **Friendly** — warm cream fields, rounded corners, human-scale copy, "we
  made this for you" posture. Friendly is the *behavior*: nothing in the brand
  threatens, shames, or scolds.
- **Open** — lowercase wordmark, open-source posture, honest numbers, no
  lock-in messaging ("not another subscription" is literally an anti-lock-in
  promise). Open is the *structure*: things are legible, nameable, inspectable.
- **Honest** — pine-on-cream contrast, muted labels, exact figures, no hype
  words, no urgency clichés. Honest is the *floor*: the brand would rather be
  plain than be caught exaggerating.

The mood is **kitchen-table optimism**: results feel human, not corporate.
Warm, but never saccharine; simple, but never cheap.

---

## 5. Brand Tokens

### 5.1 Palette — exact hexes, roles, and usage ratios

| Token | Hex | Role | Usage ratio (of colored area) |
|---|---|---|---|
| Cream | `#F8F7F5` | Canvas — breathing room | ~50% of canvas |
| Pine | `#17352C` | Ink — text, outlines, dark fields | ~20% (most-used after cream) |
| Mint | `#BDEFD4` | Friendliness field — cards, fills, success | ~12% |
| Orange | `#FF6B3D` | Attention — one CTA, one number, one accent | ~5% (max) |
| Peach | `#FFB89D` | Warmth accent (logo bean, highlights) | ~5% |
| White | `#FFFFFF` | Clean panels/cards on cream | ~8% (cards) |
| Quiet rule | `#D9E2DC` | Hairlines, gridlines, separators | lines only |
| Muted ink | `#5F6F68` / `#4D5B56` | Secondary labels, captions, sources | text only |

Extended pastel accents (max 4 in any one composition): Sky `#CFE8F7`,
Butter `#FFE7A3`, Lilac `#DCCEF7`, Mint-deep `#78CCA1` (data series), warm
cream hover `#F6F0E7`, pale mint field `#F2F6F1`, pale peach field `#FFF0E8`.

**Rules that bind the palette:**
- Orange is *always* the rarest color. One CTA, one headline number, one
  underline. If orange appears twice, it's competing with itself.
- Pine is the only dark. Never pure black, never gray. (Exception: noir-sweet
  style darkens pine for the night register — see style library.)
- Text is pine on cream, pine on mint, or cream on pine — nothing else.
- Pastels never carry text; text always sits on cream/white/pine.

### 5.2 Typography roles

| Role | Face / weight | Use |
|---|---|---|
| Display | Fraunces 600 (visual dir: high-contrast soft serif) | Headlines, pull phrases, product/identity names; tight leading, slight negative tracking |
| Display-emphasis | Fraunces 700–800 | The one big number, the one shout |
| Body | DM Sans 400/500 | Paragraphs, descriptions |
| Label | DM Sans 700, uppercase, letterspaced | Eyebrows, kickers, tags, folios |
| Data | DM Sans 400/500, tabular numerals | Numbers, axis labels, sources — digits must not jitter |
| Terminal (new) | Monospace (Menlo/Monaco/DejaVu Sans Mono) | OSS/developer register: code, banners, ASCII art |

Font-replacement rule: if the rendering model can't draw Fraunces, use a
close **high-contrast soft serif**; if it can't draw DM Sans, use a clean
**geometric sans**. Preserve exact wording at all costs; the *feel* of the
face is secondary to the exactness of the copy.

### 5.3 Shape / vibe rules

- Rounded first, everywhere: pills for actions, 8–18px radii for cards,
  super-ellipse blobs for organic shapes.
- One tilt allowed: the bean's −7°. Nothing else leans.
- Outlines are **thick and round-capped** (pine), fills are **flat pastels**.
- One hero object per composition; faces are abstract (`•ᴗ•` cue, dot eyes).
- Soft pine-tinted shadows only (e.g. `rgba(23,53,44,.16)`), never hard or black.
- Whitespace is a feature: 25–50% open canvas depending on register.
- **Never**: neon, gradients, gloss, 3D extrusion, harsh drop shadows,
  corporate stock photography, urgency clichés (countdowns, sirens, fire emoji),
  clutter piles.

### 5.4 Tone rules (writing + on-image copy)

- Short sentences. Short words. One claim per post.
- Numbers must be exact, sourced, and carry units — never rounded for effect.
- No hype words: no "revolutionary," "game-changing," "unlimited," "magic."
  "Simple," "honest," "open," "built," "works" are Omo words.
- Admitting a limit is on-brand ("this does X, not Y"). It's the *trust* part.
- CTAs are plain: `omo.space`, "Get the workflow," "Try it," never "ACT NOW."
- If you can't source it, don't claim it on-image.

---

## 6. Personality Definition — "cute friendly opensource open style"

What the founder's shorthand *means*, made concrete:

| Trait | Concrete meaning in visuals & copy |
|---|---|
| **cute** | The bean + `•ᴗ•` face; chunky rounded shapes; warm pastel fields; playful but never babyish; one small joke or wink per piece is welcome |
| **friendly** | Kitchen-table warmth: cream canvas, rounded corners, human-scale type, "we made this for you" posture; nothing threatens, shames, or scolds |
| **opensource** | Terminal/ASCII register for OSS content (monospace, code blocks, `$` prompts, figlet banners, stone boxes); visible process ("here's how it works"), crediting, no lock-in language; community posture |
| **open** | Honest numbers with sources; transparent pricing ("$0.99, no subscription"); lowercase wordmark; whitespace that lets the viewer breathe; information wants to be legible |

### Do / Don't

**Do:**
- Lead with cream, ink with pine, warm with mint, point with orange (once).
- Use the bean, the `•ᴗ•` face, beans/hearts/stars/checks as micro-cues.
- Show the result as a tangible object (a book, a chart, a finished video).
- Print exact, sourced numbers with units.
- Use ASCII/terminal craft for developer & open-source content.
- Keep one hero object and one message per piece.
- Let the −7° tilt be the only lean in the room.

**Don't:**
- Use black, pure grays, or neon; never let orange outnumber mint.
- Render the logo's wordmark from scratch — reference the asset or use plain
  `omo.space` text.
- Show invented metrics, fake testimonials, or unsourced claims on-image.
- Depict real customer messages/private chat content or third-party logos.
- Use urgency clichés, countdown timers, "ACT NOW," or hype adjectives.
- Mix photorealism into the flat-vector system (family B covers are the known
  exception; social output should stay flat).
- Pile stickers/confetti/decoration — cute is one accent, not a collage.

---

## 7. Sources (all read directly)

| File | What it proved |
|---|---|
| `site/logo-sweet-pastel.svg` | Bean geometry/fill/shadow/rotation, face, wordmark, Baloo 2 ExtraBold provenance |
| `site/nav.js` | Chrome palette (pine/mint/cream/orange/muted), radii, shadows, hover states, tabular numerals, Fraunces in nav identity |
| `site/workflow-facts.css` | `--display: Fraunces` / `--body: DM Sans` canonical pair |
| `site/menu-workflows.css` | Letterspaced uppercase labels, 650/700 weights |
| `site/covers/meta-ads-analyser.svg` | Token-exact cover palette (pine 8×, orange 4×, mint 4×, white, muted) |
| `site/covers/decodable-book-maker.svg` | Cute register: cream canvas, 9px pine outlines, dot eyes, rounded tiles, check badge |
| `site/index.html` | "…not another subscription." tagline in the wild |
| `omo-social-media-post` skill (7 style files) | The existing style library this DNA formalizes |
