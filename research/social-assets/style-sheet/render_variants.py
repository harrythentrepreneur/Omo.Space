#!/usr/bin/env python3
"""The five signature compositions of the Omo master style (issue #84).

Each renderer builds a 1600x900 Canvas per research/OMO-IMAGE-STYLE-SYSTEM.MD:
  - render_tagline     launch variant   (tagline card)
  - render_book_card   product variant  (decodable-book-maker)
  - render_oss_launch  launch variant   (open-source library banner)
  - render_education   education variant (3-step example)
  - render_metrics     metrics variant   (one true number example)
"""
import os
from omo_style import (Canvas, CREAM, PINE, MINT, ORANGE, PEACH, WHITE, RULE,
                       MUTED, MUTED2, SKY, BUTTER, PALEMINT, MINTDEEP)

W, H = 1600, 900

# ---------------------------------------------------------------- launch
def render_tagline():
    c = Canvas(W, H)
    c.frame()
    # eyebrow
    c.text((112, 92), "OMO \u00b7 THE RESULT MARKETPLACE",
           c.font("dm", 22, 700), MUTED, tracking=0.12)
    # mint field + bean (top-right)
    c.blob(1290, 205, 300, 168, MINT, seed=3)
    c.bean(1360, 195, 165, fill=PEACH)
    # headline, Fraunces 600, strike-through = the one orange accent
    hf = c.font("fraunces", 86, 600)
    c.text((112, 252), "Buy the result,", hf, PINE)
    c.text((112, 348), "not another", hf, PINE)
    c.struck(112 + c.measure(hf, "subscription.") / 2.0, 452, "subscription.",
             hf, PINE, strike=ORANGE, sw=9, pad=16)
    # supporting line
    c.text((116, 610), "Workflows, not rentals.",
           c.font("dm", 30, 500), MUTED2)
    # CTA pill
    c.pill(236, 778, 320, 76, PINE, "omo.space", c.font("dm", 30, 700),
           tfill=CREAM, tracking=0.05)
    return c

# ---------------------------------------------------------------- product
def render_book_card():
    c = Canvas(W, H)
    c.frame()
    # eyebrow
    c.text((112, 84), "DECODABLE BOOK MAKER",
           c.font("dm", 22, 700), MUTED, tracking=0.12)
    # --- hero: open storybook (9px pine outlines, white pages) ---
    bx0, by0, bx1, by1 = 330, 250, 870, 640
    c.rrect([bx0, by0, bx1, by1], radius=22, fill=WHITE, outline=PINE, width=9)
    # center fold
    c.line((600, by0 + 18), (600, by1 - 18), RULE, 4)
    # page print dashes (left page)
    for i, (px, pw) in enumerate([(360, 150), (366, 140), (362, 158), (368, 130)]):
        c.line((px, 300 + i * 44), (px + pw, 300 + i * 44), RULE, 6)
    # butter cat with dot eyes, sitting on the left page
    cat_cx, cat_cy = 448, 470
    c.poly([(cat_cx - 34, cat_cy - 26), (cat_cx - 20, cat_cy - 58),
            (cat_cx - 4, cat_cy - 34), (cat_cx + 18, cat_cy - 58),
            (cat_cx + 34, cat_cy - 26), (cat_cx + 34, cat_cy + 6),
            (cat_cx - 34, cat_cy + 6)], BUTTER, PINE, 6)          # head+ears
    c.poly([(cat_cx - 30, cat_cy + 4), (cat_cx + 30, cat_cy + 4),
            (cat_cx + 22, cat_cy + 62), (cat_cx - 22, cat_cy + 62)],
           BUTTER, PINE, 6)                                        # body
    for sgn in (-1, 1):                                            # dot eyes
        c.ellipse([cat_cx + sgn * 14 - 4.5, cat_cy - 16 - 4.5,
                   cat_cx + sgn * 14 + 4.5, cat_cy - 16 + 4.5], fill=PINE)
    c.ellipse([cat_cx - 4, cat_cy + 4, cat_cx + 4, cat_cy + 12], fill=PINE)  # nose
    # right page: mint map with dotted path + pine check
    c.rrect([636, 300, 834, 540], radius=18, fill=MINT)
    for i in range(7):
        x0 = 668 + i * 26
        c.ellipse([x0, 430 - i * 18 - 5, x0 + 10, 430 - i * 18 + 5], fill=PINE)
    c.check(700, 560, 728, 588, 790, 520, PINE, 10)
    # --- the one orange accent: the price chip ---
    c.pill(1010, 236, 250, 84, ORANGE, "$0.99", c.font("fraunces", 52, 800),
           tfill=CREAM, tracking=0.0)
    # --- fact chips (exact claims only) ---
    facts = ["4-page phonics PDF", "Keep it forever", "No subscription"]
    fw = [c.measure(c.font("dm", 24, 700), t) + 64 for t in facts]
    gap = 28
    total = sum(fw) + gap * 2
    x = 600 - total / 2.0
    for t, tw in zip(facts, fw):
        c.pill(x + tw / 2.0, 706, tw, 62, WHITE, t, c.font("dm", 24, 700),
               tfill=PINE, tracking=0.01, outline=PINE, owidth=3)
        x += tw + gap
    # --- CTA ---
    c.pill(600, 800, 330, 66, PINE, "Make your book", c.font("dm", 26, 700),
           tfill=CREAM, tracking=0.03)
    # --- bean badge on the frame corner ---
    c.bean(1472, 108, 108, fill=PEACH)
    return c

# ---------------------------------------------------------------- oss launch
def render_oss_launch():
    c = Canvas(W, H)
    c.frame()
    c.text((112, 88), "OMO \u00b7 OPEN SOURCE",
           c.font("dm", 22, 700), MUTED, tracking=0.12)
    hf = c.font("fraunces", 78, 600)
    c.text((112, 224), "The library is open.", hf, PINE)
    c.text((112, 316), "Everything free", hf, PINE)
    c.text((112, 408), "to download.", hf, PINE)
    # stat row: the one orange accent = the "15"
    nf = c.font("fraunces", 58, 800)
    base = 470
    c.text((116, base), "15", nf, ORANGE)
    x = 116 + c.measure(nf, "15")
    sf = c.font("dm", 32, 500)
    c.text((x + 12, base + 20), "free skills \u00b7 MIT \u00b7 pay per run",
           sf, MUTED2)
    # --- hero panel: the repo, flat vector ---
    px0, py0, px1, py1 = 950, 190, 1506, 580
    c.rrect([px0, py0, px1, py1], radius=28, fill=WHITE, outline=PINE, width=6)
    c.text((986, 222), "github.com/omo-space/skills",
           c.font("dm", 24, 700), PINE)
    for i in range(3):
        dx = 986 + i * 78
        c.rrect([dx, 292, dx + 58, 378], radius=10, fill=MINT, outline=PINE,
                width=5)
        c.line((dx + 18, 322), (dx + 40, 322), PINE, 5)   # print line
        c.line((dx + 18, 342), (dx + 40, 342), PINE, 5)
    c.check(1150, 320, 1168, 342, 1204, 300, PINE, 9)      # checked doc
    c.text((986, 424), "$ git clone omo-space/skills",
           c.font("mono", 24), PINE)
    c.text((986, 470), "MIT \u00b7 15 free skills \u00b7 free to download",
           c.font("dm", 22, 500), MUTED)
    # bean peeking over the panel corner
    c.bean(958, 176, 118, fill=PEACH)
    # CTA
    c.pill(300, 796, 380, 66, PINE, "omo.space/skills", c.font("dm", 26, 700),
           tfill=CREAM, tracking=0.03)
    return c

# ---------------------------------------------------------------- education
def render_education():
    c = Canvas(W, H)
    c.frame()
    c.text((112, 86), "HOW IT WORKS \u00b7 PHONICS",
           c.font("dm", 22, 700), MUTED, tracking=0.12)
    hf = c.font("fraunces", 66, 600)
    c.text((112, 200), "Make a decodable book", hf, PINE)
    c.text((112, 282), "in 3 steps", hf, PINE)
    # three tiles: sky / butter / peach fields, icons only, no text on fields
    tiles = [((112, 420, 492, 720), SKY, 1), ((612, 420, 992, 720), BUTTER, 2),
             ((1112, 420, 1492, 720), PEACH, 3)]
    for (x0, y0, x1, y1), fill, num in tiles:
        c.rrect([x0, y0, x1, y1], radius=28, fill=fill, outline=PINE, width=6)
        # number badge: white circle, pine figure
        c.ellipse([x0 + 30, y0 + 30, x0 + 98, y0 + 98], fill=WHITE,
                  outline=PINE, width=5)
        c.text((x0 + 64, y0 + 64), str(num), c.font("fraunces", 46, 800),
               PINE, anchor="mm")
    # icons
    cx0, cy0 = 302, 560   # (1) sound waves
    for i, rr in enumerate([58, 40, 22]):
        c.polyline([(cx0 - rr, cy0 - 8), (cx0 - rr, cy0 + 8),
                    (cx0 - rr + 22, cy0 + 8), (cx0 - rr + 22, cy0 - 8)],
                   PINE, 8)
    c.ellipse([cx0 + 62, cy0 - 46, cx0 + 150, cy0 + 46], fill=WHITE,
              outline=PINE, width=6)                      # ear
    cx1, cy1 = 802, 560   # (2) word blocks
    for i in range(3):
        c.rrect([cx1 - 66, cy1 - 88 + i * 62, cx1 + 66, cy1 - 26 + i * 62],
                radius=14, fill=WHITE, outline=PINE, width=6)
        c.line((cx1 - 36, cy1 - 57 + i * 62), (cx1 + 36, cy1 - 57 + i * 62),
               RULE, 7)
    cx2, cy2 = 1302, 560  # (3) open book + the orange result star
    c.rrect([cx2 - 78, cy2 - 58, cx2 + 78, cy2 + 58], radius=16, fill=WHITE,
            outline=PINE, width=7)
    c.line((cx2, cy2 - 44), (cx2, cy2 + 44), RULE, 4)
    c.check(cx2 - 34, cy2 - 6, cx2 - 6, cy2 + 22, cx2 + 40, cy2 - 34, PINE, 8)
    c.star(1330, 500, 26, ORANGE)                         # one orange accent
    # labels on cream below each tile
    labels = ["Pick a sound", "Build the words", "Read the book"]
    for (x0, y0, x1, y1), _fill, _num in tiles:
        lab = labels.pop(0)
        c.text((x0, y1 + 26), lab, c.font("dm", 30, 700), PINE)
    c.pill(300, 826, 300, 62, PINE, "omo.space", c.font("dm", 26, 700),
           tfill=CREAM, tracking=0.04)
    c.bean(1472, 96, 104, fill=PEACH)
    return c

# ---------------------------------------------------------------- metrics
def render_metrics():
    c = Canvas(W, H)
    c.frame()
    c.text((112, 88), "THE OPEN MODEL \u00b7 SOURCED NUMBERS",
           c.font("dm", 22, 700), MUTED, tracking=0.12)
    # the one big number, orange = the accent
    c.text((112, 240), "15", c.font("fraunces", 150, 800), ORANGE)
    c.text((118, 436), "free skills", c.font("dm", 32, 700), PINE)
    c.text((118, 484), "MIT \u00b7 free to download",
           c.font("dm", 26, 500), MUTED2)
    # supporting cards (white, pine outline), stacked right
    cards = [
        ("$0.10", "typical education run"),
        ("$0.99", "decodable book, one at a time"),
        ("$5.00", "loader guard \u00b7 analysis floor"),
    ]
    y = 240
    for big, sub in cards:
        c.rrect([720, y, 1490, y + 172], radius=24, fill=WHITE, outline=PINE,
                width=5)
        c.text((760, y + 34), big, c.font("fraunces", 64, 800), PINE)
        c.text((760, y + 116), sub, c.font("dm", 24, 500), MUTED2)
        y += 192
    # source line
    c.text((116, 806), "Source: github.com/omo-space/skills",
           c.font("dm", 20, 400), MUTED)
    c.pill(640, 806, 300, 60, PINE, "omo.space", c.font("dm", 26, 700),
           tfill=CREAM, tracking=0.04)
    return c


RENDERERS = {
    "tagline": render_tagline,
    "book": render_book_card,
    "oss": render_oss_launch,
    "education": render_education,
    "metrics": render_metrics,
}

if __name__ == "__main__":
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")
    os.makedirs(outdir, exist_ok=True)
    for name, fn in RENDERERS.items():
        p = os.path.join(outdir, f"example-{name}.png")
        fn().save(p)
        print("wrote", p)
