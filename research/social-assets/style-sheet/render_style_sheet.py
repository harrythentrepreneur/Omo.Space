#!/usr/bin/env python3
"""Style sheet reference images (issue #84).

Panel A 1600x1200: the system — palette with hexes + ratios, type specimens,
the -7 deg bean, grid anatomy, ratio bar.
Panel B 1600x1200: the 4 use-case variant mini-previews + do/don't side by side.
"""
import os
from PIL import Image
from omo_style import (Canvas, CREAM, PINE, MINT, ORANGE, PEACH, WHITE, RULE,
                       MUTED, MUTED2, SKY, BUTTER, MINTDEEP)
import render_variants as V

OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- panel A
def panel_a():
    c = Canvas(1600, 1200)
    c.frame()
    # header
    c.text((72, 58), "OMO IMAGE STYLE SYSTEM \u00b7 REFERENCE A \u2014 THE SYSTEM",
           c.font("dm", 20, 700), MUTED, tracking=0.12)
    c.text((72, 92), "The signature look.", c.font("fraunces", 60, 600), PINE)
    c.text((76, 178), "cream canvas \u00b7 pine frame \u00b7 pastel fields \u00b7 "
                      "one orange \u00b7 Fraunces + DM Sans \u00b7 the \u22127\u00b0 bean",
           c.font("dm", 23, 400), MUTED2)

    # ---- left column: palette ----
    c.text((72, 236), "PALETTE \u00b7 RATIOS OF COLORED AREA",
           c.font("dm", 18, 700), MUTED, tracking=0.1)
    swatches = [
        (CREAM, "#F8F7F5", "canvas \u2014 breathing room", "~50%"),
        (PINE,  "#17352C", "ink \u2014 text, outlines", "~20%"),
        (MINT,  "#BDEFD4", "friendliness field", "~12%"),
        (ORANGE,"#FF6B3D", "the one accent", "\u22645%"),
        (PEACH, "#FFB89D", "warmth \u00b7 the bean", "~5%"),
        (WHITE, "#FFFFFF", "cards on cream", "~8%"),
        (RULE,  "#D9E2DC", "hairlines", "lines only"),
        (MUTED, "#5F6F68", "secondary text", "text only"),
    ]
    y = 282
    for fill, hexv, name, ratio in swatches:
        c.rrect([72, y, 144, y + 40], radius=10, fill=fill,
                outline=PINE if fill in (CREAM, WHITE, RULE) else None, width=3)
        c.text((166, y + 2), f"{hexv}  {name}", c.font("dm", 20, 500), PINE)
        c.text((700, y + 4), ratio, c.font("dm", 18, 500), MUTED, anchor="ra")
        y += 52
    # ratio bar
    segs = [(CREAM, 50), (PINE, 20), (MINT, 12), (ORANGE, 5), (PEACH, 5),
            (WHITE, 8)]
    x0, y0, total_w = 72, 716, 632
    for fill, pct in segs:
        w = total_w * pct / 100.0
        c.rrect([x0, y0, x0 + w, y0 + 30], radius=15, fill=fill,
                outline=PINE if fill == WHITE else None, width=3)
        x0 += w
    c.text((72, 758), "cream leads \u00b7 orange is the rarest \u2014 one accent per post",
           c.font("dm", 17, 500), MUTED)
    # bean demo
    c.text((72, 806), "THE \u22127\u00b0 BEAN \u2014 THE ONLY LEAN IN THE ROOM",
           c.font("dm", 18, 700), MUTED, tracking=0.1)
    c.bean(212, 972, 152, fill=PEACH)
    c.text((330, 906), "everything else sits level: 0\u00b0",
           c.font("dm", 19, 500), MUTED2)
    # level ruler with ticks
    for i in range(13):
        x = 330 + i * 31
        c.line((x, 972), (x + 14, 972), RULE, 3)
    c.text((330, 1018), "rotate(-7) about its own center \u00b7 peach #FFB89D \u00b7 \u2022\u1d17\u2022 in pine",
           c.font("dm", 17, 400), MUTED)

    # ---- right column: type ----
    c.text((740, 236), "TYPE ROLES", c.font("dm", 18, 700), MUTED, tracking=0.1)
    c.text((740, 272), "Fraunces 600 \u2014 headlines, pull phrases",
           c.font("dm", 17, 400), MUTED)
    c.text((740, 300), "Buy the result,", c.font("fraunces", 52, 600), PINE)
    c.text((740, 372), "Fraunces 800 \u2014 the one big number / price",
           c.font("dm", 17, 400), MUTED)
    c.text((740, 400), "$0.99", c.font("fraunces", 58, 800), PINE)
    c.text((900, 428), "orange is reserved for the one accent",
           c.font("dm", 17, 400), MUTED)
    c.text((740, 470), "DM Sans 400/500 \u2014 body copy",
           c.font("dm", 17, 400), MUTED)
    c.text((740, 498), "Pay once for the finished result. Keep it forever.",
           c.font("dm", 24, 500), MUTED2)
    c.text((740, 568), "DM Sans 700 \u2014 labels, tracked +0.12em",
           c.font("dm", 17, 400), MUTED)
    c.text((740, 596), "GET THE WORKFLOW \u00b7 TRY IT",
           c.font("dm", 24, 700), PINE, tracking=0.12)
    c.text((740, 666), "tabular numerals \u2014 data figures, no jitter",
           c.font("dm", 17, 400), MUTED)
    c.text((740, 694), "0123456789 \u00b7 $0.10 \u00b7 $0.99 \u00b7 15",
           c.font("dm", 30, 500), MUTED2)
    # grid anatomy
    c.text((740, 762), "GRID ANATOMY \u00b7 1600\u00d7900 MASTER",
           c.font("dm", 18, 700), MUTED, tracking=0.1)
    gx0, gy0, gx1, gy1 = 740, 800, 1380, 1160
    c.rrect([gx0, gy0, gx1, gy1], radius=18, fill=WHITE, outline=PINE, width=5)
    pad = 24
    inner_w = (gx1 - gx0) - 2 * pad
    colw = inner_w / 12.0
    for i in range(13):
        x = gx0 + pad + i * colw
        c.line((x, gy0 + pad), (x, gy1 - pad), RULE, 1.5)
    c.line((gx0 + pad, gy0 + pad + (gy1 - gy0 - 2 * pad) * 0.42),
           (gx1 - pad, gy0 + pad + (gy1 - gy0 - 2 * pad) * 0.42), RULE, 1.5)
    # sample placement: 2 pastel fields + 1 orange dot
    c.rrect([gx0 + pad + 3 * colw, gy0 + pad + (gy1 - gy0 - 2 * pad) * 0.5,
             gx0 + pad + 5 * colw, gy1 - pad], radius=12, fill=MINT)
    c.rrect([gx0 + pad + 7 * colw, gy0 + pad + (gy1 - gy0 - 2 * pad) * 0.5,
             gx0 + pad + 9 * colw, gy1 - pad], radius=12, fill=BUTTER)
    c.ellipse([gx0 + pad + 10.4 * colw - 9, gy0 + pad + (gy1 - gy0 - 2 * pad) * 0.5 - 9,
               gx0 + pad + 10.4 * colw + 9, gy0 + pad + (gy1 - gy0 - 2 * pad) * 0.5 + 9],
              fill=ORANGE)
    c.text((gx0 + 8, gy0 + 8), "48px margin", c.font("dm", 13, 700), MUTED)
    c.text((740, 1172), "cream canvas \u00b7 48px margin \u00b7 12-column grid \u00b7 "
                        "9px pine frame \u00b7 2\u20133 pastel fields \u00b7 one orange \u22645%",
           c.font("dm", 16, 500), MUTED)

    c.text((72, 1156), "Full spec: research/OMO-IMAGE-STYLE-SYSTEM.MD \u00b7 "
                       "fonts: Fraunces + DM Sans (Google Fonts, OFL)",
           c.font("dm", 16, 400), MUTED)
    return c

# ---------------------------------------------------------------- panel B
DO_LIST = [
    "Lead with cream ~50%, ink with pine, warm with mint, point with orange once.",
    "Frame every post with the 9px pine rounded outline.",
    "Keep 2\u20133 pastel fields max; text never sits on a pastel.",
    "Fraunces for display, DM Sans for everything else, tabular for figures.",
    "The \u22127\u00b0 tilt belongs to the bean alone \u2014 one lean per composition.",
    "Draw flat: solid fills, 9px round-capped pine outlines, one hero object.",
    "Leave 25\u201350% of the canvas open \u2014 white space is the brand.",
    "Print exact, sourced numbers with units on-image.",
    "Use the bean / \u2022\u1d17\u2022 / dot-eyes sparingly as the wink.",
    "End with one plain CTA: omo.space, Get the workflow, Try it.",
]
DONT_LIST = [
    "Use black, pure grays, or neon; never let orange outnumber mint.",
    "Use more than one orange accent \u2014 one price, one number, one strike.",
    "Put text on a pastel field or let text touch a field edge.",
    "Rotate anything except the bean \u2014 no tilted headlines or cards.",
    "Mix in gradients, gloss, 3D, photos, or textures (flat vector only).",
    "Add a second hero object, sticker piles, or confetti.",
    "Crowd the canvas \u2014 under 25% open cream is clutter.",
    "Print invented metrics, fake testimonials, or unsourced claims.",
    "Use hype words, countdowns, ACT NOW, or urgency clich\u00e9s.",
    "Redraw the logo wordmark \u2014 use the asset or plain omo.space text.",
]

def panel_b():
    c = Canvas(1600, 1200)
    c.frame()
    c.text((72, 58), "OMO IMAGE STYLE SYSTEM \u00b7 REFERENCE B \u2014 USE CASES",
           c.font("dm", 20, 700), MUTED, tracking=0.12)
    c.text((72, 92), "Four jobs, one system.", c.font("fraunces", 60, 600), PINE)
    c.text((76, 170), "the same canvas, frame, palette, and type \u2014 composed per job",
           c.font("dm", 21, 400), MUTED2)

    # 2x2 variant mini-previews (real renders, scaled 0.4)
    cells = [((72, 192), "tagline", "LAUNCH \u00b7 the tagline card"),
             ((888, 192), "book", "PRODUCT \u00b7 the decodable book"),
             ((72, 576), "education", "EDUCATION \u00b7 3 steps"),
             ((888, 576), "metrics", "METRICS \u00b7 one true number")]
    for (cx, cy), name, caption in cells:
        cv = V.RENDERERS[name]()
        mini = cv.img.resize((640, 360), Image.LANCZOS)
        c.img.paste(mini, (cx * c.scale, cy * c.scale))
        c.text((cx + 320, cy + 370), caption, c.font("dm", 20, 700), PINE,
               tracking=0.06, anchor="mm")

    # do / don't side by side
    c.text((72, 974), "DO", c.font("dm", 26, 700), PINE, tracking=0.06)
    c.check(128, 990, 138, 1000, 158, 978, MINTDEEP, 7)
    c.text((816, 974), "DON\u2019T", c.font("dm", 26, 700), PINE, tracking=0.06)
    c.polyline([(936, 978), (956, 998)], ORANGE, 7)
    c.polyline([(956, 978), (936, 998)], ORANGE, 7)

    y = 1012
    for i, (do, dont) in enumerate(zip(DO_LIST, DONT_LIST)):
        c.check(88, y + 6, 96, y + 14, 112, y - 6, MINTDEEP, 6)
        c.text((124, y - 2), do, c.font("dm", 14, 500), MUTED2)
        c.text((832, y - 2), dont, c.font("dm", 14, 500), MUTED2)
        y += 15
    return c

if __name__ == "__main__":
    p1 = os.path.join(OUT, "style-sheet-system.png")
    p2 = os.path.join(OUT, "style-sheet-variants.png")
    panel_a().save(p1)
    panel_b().save(p2)
    print("wrote", p1)
    print("wrote", p2)
