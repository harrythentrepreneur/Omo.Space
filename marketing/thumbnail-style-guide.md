# Omo Marketplace Thumbnail Style Guide

## 1. Visual style description

### Core look

A polished, high-energy elementary teacher-resource cover: part Teachers Pay Teachers product preview, part classroom printable flat-lay. The image should communicate “ready-to-use learning activity” immediately, not “AI software.” The finish is clean, commercial, cheerful, and deliberately simple enough to remain readable at marketplace-thumbnail size.

### Color palette

Use a mostly white base with hard, saturated accents and near-black outlines. Approximate reference colors:

- Paper white: `#FFFFFF`
- Soft warm white/background: `#FAFAF7`
- Near-black outlines and type: `#111111`
- Hot pink/magenta: `#F7088A` to `#FF0A91`
- Bright cyan/turquoise: `#08C9E8` to `#00BFD8`
- School-bus yellow: `#FFD21A`
- Tangerine/orange: `#FF7A24`
- Volcano red-orange: `#F33A0A`
- Lime/chartreuse: `#8BCB00`
- Warm kraft tan: `#B89263`
- Neutral smoke gray: `#A6A19F`
- Occasional pale pink grounding strip: `#F7A6C5`

Keep roughly 65–75% of the frame white or grayscale. Use three to five accent colors in large, discrete blocks; do not blend them. Color should appear in borders, backing sheets, classroom objects, a mascot, or simple header-like bands. Avoid muted palettes, beige lifestyle styling, metallic colors, and cinematic color grading.

### Illustration and image treatment

- Primary imagery is a collage of printable worksheet sheets, shown front-on or at a shallow overhead angle and overlapped like a product bundle.
- Worksheet art is black-and-white elementary clip art: simple rounded shapes, friendly faces, uncomplicated objects, and generous areas intended for coloring or marking.
- Linework is smooth, dark, and assertive: approximately 3–5 px on worksheet illustrations at the reference resolution, and 6–10 px on a foreground mascot or hero object. Use rounded caps and slightly imperfect hand-drawn contours.
- Flat vector/cartoon rendering is the dominant mode. Reference 2 permits a lightly photographed or photoreal flat-lay treatment for real school supplies, but the papers remain graphic and high-contrast.
- Surfaces are matte and nearly texture-free. Paper may have only the faintest natural texture. No glossy 3D render, painterly brushwork, watercolor, grain overlay, or detailed environmental scene.
- Shadows are restrained: a small soft gray drop shadow or narrow contact shadow under overlapping sheets and supplies, just enough to separate layers. No dramatic cast shadows.
- Lighting, when objects are photographic, is bright, diffuse, even studio/daylight from above with no strong directionality.

### Typography and title treatment

The references use typography as oversized packaging, although Omo should add listing copy in the UI rather than baking it into generated artwork.

- Display vibe: bold, condensed or hand-drawn classroom sans serif, similar in feel to Anton/Impact/Bebas-style capitals or a chunky teacher-display font.
- Weight and case: uppercase, extra-bold, tightly set, with minimal tracking.
- Reference 1 treatment: huge orange-red uppercase letters with a thick black outline and a subtle soft gray shadow; the headline occupies nearly the entire upper third.
- Reference 2 treatment: stacked headline bands—white uppercase on hot pink; then very large multicolor uppercase characters with black outlines; then a thin black uppercase subhead; and a heavy black bottom nameplate with white uppercase type.
- Label/badge language: bright rectangular strips, colored worksheet backings, and strong black framing. Avoid glossy pills, glassmorphism, beveled badges, or SaaS-style gradients.
- Generated thumbnail artwork must contain **no typography at all**: no words, letters, numbers, logos, watermarks, faux writing, or legible worksheet copy. Reserve visually quiet white space for UI-applied listing copy.

### Layout and composition

- Use a dense, edge-to-edge product-cover composition with very little empty outer margin and a clean white field.
- Reserve roughly the upper 25–35% as simple white breathing room for later UI title placement. It may be framed by a solid hot-pink or cyan accent band, but the band itself remains blank.
- Fill the middle and lower 60–70% with three to five overlapping portrait worksheet pages, slightly rotated (about 2–7 degrees) and staggered so the bundle is instantly legible.
- Make one worksheet the central hero at the largest scale; flank it with partially cropped sheets behind it.
- Add one or two recognizable classroom props—child-safe scissors, crayons, a chunky die, pencil, glue/dauber, or colored notebook edges—cropped by the frame rather than floating in isolation.
- A friendly, oversized mascot may anchor the lower-left corner and overlap the papers, but it is optional. If used, keep it flat, goofy, and black-outlined with very large eyes.
- Use thin bright-color backing mats behind individual sheets (cyan, lime, yellow, orange, or magenta) to separate layers.
- Crop confidently at the edges. The references favor abundance and immediacy over precious centered symmetry.
- Do not show browser windows, app dashboards, buttons, device mockups, cursors, or any other UI chrome.
- Master artwork should be portrait, ideally `4:5`; protect the central content so it can also survive a square marketplace crop.

### Mood and audience signal

The image should feel like a proven, practical classroom resource sold by an experienced kindergarten or early-elementary teacher: cheerful, approachable, organized, hands-on, low-prep, and immediately useful. It should signal literacy learning for ages roughly 4–8 without looking babyish. It should not feel corporate, futuristic, luxurious, editorial, or technically “AI.”

### Recurring motifs and exclusions

Recurring motifs are layered worksheet previews, bright backing paper, chunky black outlines, child-friendly clip art, school supplies, large white areas, simple faces, and saturated single-color bands. Gradients are absent. Lighting is flat and bright. Shadows are soft and secondary. Keep all content safe, friendly, and classroom-specific.

Avoid faux text, alphabet glyphs, readable labels, speech bubbles, logos, app UI, photoreal children, busy classroom backgrounds, pastel-only palettes, intricate textures, thin gray linework, glossy 3D objects, neon glow, lens effects, and moody lighting.

## 2. Reusable image-generation prompt

```text
Create a portrait 4:5 marketplace thumbnail for a phonics worksheet generator in the polished elementary teacher-resource cover style: bright white background, upper 30% kept clean and visually quiet for later UI copy, lower two-thirds filled with a dense overhead collage of four overlapping printable worksheet pages, one large central hero page and three slightly rotated sheets behind it, each backed by thin saturated mats in hot pink #F7088A, cyan #08C9E8, school-bus yellow #FFD21A, lime #8BCB00, and tangerine #FF7A24. Show only text-free phonics activity visuals: bold black-and-white coloring-page line art of a friendly mouth forming sounds, simple sound-wave marks, and picture cards depicting a cat, sun, fish, moon, and ball, plus empty circles, matching paths, and blank answer boxes; absolutely no words, letters, numbers, glyphs, labels, logos, watermarks, or faux writing anywhere. Add a child-safe pair of scissors and three bright crayons cropped at the side, with a small cheerful wide-eyed cartoon sound mascot anchoring the lower-left corner. Use smooth thick near-black outlines, rounded hand-drawn elementary clip-art shapes, mostly flat vector rendering, crisp white paper, minimal texture, tiny soft gray contact shadows between layers, bright diffuse overhead studio lighting, energetic edge-to-edge composition, polished commercial Teachers Pay Teachers product-preview feel, highly legible at thumbnail size, no gradients, no glossy 3D, no app interface, no people, no environmental classroom background. Keep all important imagery centered enough to survive a square crop.
```

## 3. Fixed versus flexible elements

### Fixed across both references

- White-dominant, high-contrast canvas.
- Saturated primary/secondary classroom accents, especially pink, cyan, yellow, orange, and lime.
- Heavy near-black outlines and simple elementary clip-art language.
- Several worksheet previews layered into a visibly abundant product bundle.
- Dense commercial cover composition with confident edge cropping.
- Clear hierarchy designed to read at small thumbnail size.
- Cheerful, practical early-elementary teacher-resource mood.
- Flat color, minimal texture, no gradients, and only light separation shadows.

### Flexible between the references

- **Hero device:** Reference 1 is mascot-led, with a large cartoon volcano occupying the lower-left; Reference 2 is product-led, with supplies and worksheets carrying the image. Either is valid, though the reusable prompt combines a small mascot with a product-led bundle.
- **Media mix:** Reference 1 is almost entirely flat digital illustration. Reference 2 mixes black-and-white digital printables with lightly photoreal school supplies and paper. Keep worksheet art flat; props may be flat or lightly photographic.
- **Palette concentration:** Reference 1 concentrates color in one orange-red headline and one tan/orange mascot. Reference 2 distributes rainbow accents across header treatment, page mats, and props.
- **Header structure:** Reference 1 uses one enormous two-line outlined title on white. Reference 2 uses multiple stacked bands, multicolor display type, a subtitle, and a black footer nameplate. For Omo, generated art remains text-free and the UI supplies this hierarchy.
- **Worksheet angle:** Reference 1 presents a looser fanned stack with perspective and more overlap. Reference 2 uses a more orderly shallow-overhead flat lay with rectangular page mats.
- **Framing:** Reference 2 has a thin rounded black outer border and stronger top/bottom bands. Reference 1 has no obvious enclosing border and lets the composition crop directly at the canvas edge. A subtle border is optional, but it should never resemble app chrome.
- **Aspect:** Both references are essentially square product covers. Omo's requested master is portrait 4:5, with a square-safe central composition for marketplace reuse.
