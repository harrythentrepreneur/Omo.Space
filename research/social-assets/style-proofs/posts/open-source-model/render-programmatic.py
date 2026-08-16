#!/usr/bin/env python3
"""Render the omo-terminal x hub-spoke proof post at exactly 1600x900.
Faithful execution of references/styles/omo-terminal.md + the hub-spoke
layout: cream canvas, pine terminal chrome, real pyfiglet banner in a stone
box, six sourced spokes, one orange accent, CTA pill."""
import os
from pyfiglet import Figlet
from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 900
OUT = "/Users/yifan/marketplace/research/social-assets/style-proofs/posts/open-source-model"
os.makedirs(OUT, exist_ok=True)

CREAM, PINE, MINT, PALEMINT, ORANGE, PEACH, RULE, MUTED = (
    (248, 247, 245), (23, 53, 44), (189, 239, 212),
    (234, 247, 240), (255, 107, 61), (255, 184, 157), (217, 226, 220), (95, 111, 104),
)
FONT = "/System/Library/Fonts/Menlo.ttc"

img = Image.new("RGB", (W, H), CREAM)
d = ImageDraw.Draw(img)

def mono(size, bold=False):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)

# ---------- terminal chrome strip ----------
d.rounded_rectangle([48, 36, W - 48, 92], radius=12, fill=PINE)
tf = mono(24)
d.text((76, 50), "omo@space:~$", font=tf, fill=CREAM)
# the one orange accent: the command
cmd = " omo model --open"
d.text((76 + tf.getbbox("omo@space:~$")[2] + 8, 50), cmd, font=mono(24, True), fill=ORANGE)
for i, c in enumerate([ORANGE, PEACH, MINT]):
    d.ellipse([W - 150 + i * 38, 52, W - 130 + i * 38, 72], fill=c)

# ---------- stone-boxed figlet banner ----------
def stone_box(lines, pad=1):
    w = max(len(l) for l in lines)
    inner = " " * pad
    top = "+" + "-" * (w + 2 * pad) + "+"
    return [top] + ["|" + inner + l.ljust(w) + inner + "|" for l in lines] + [top]

banner = Figlet(font="slant", width=80).renderText("OPEN SOURCE").rstrip("\n").split("\n")
boxed = stone_box(banner)
bw = max(len(l) for l in boxed)
bf = mono(34, True)
ch = bf.getbbox("M")[2] - bf.getbbox("M")[0]
bh = bf.getmetrics()[0] + bf.getmetrics()[1]
banner_px_w = bw * ch
banner_px_h = len(boxed) * bh
bx, by = (W - banner_px_w) // 2, 116
for i, line in enumerate(boxed):
    d.text((bx, by + i * bh), line, font=bf, fill=PINE)

# ---------- hub-spoke ----------
hub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
hd = ImageDraw.Draw(hub)
hub_cx, hub_cy, hub_w, hub_h = W // 2, 560, 560, 250
hd.rounded_rectangle([hub_cx - hub_w // 2, hub_cy - hub_h // 2,
                      hub_cx + hub_w // 2, hub_cy + hub_h // 2],
                     radius=28, fill=PINE)
hf = mono(64, True)
t = "OPEN SOURCE"
tb = hf.getbbox(t)
hd.text((hub_cx - (tb[2] - tb[0]) // 2, hub_cy - 68), t, font=hf, fill=CREAM)
sf = mono(30)
sub = "omo.space/skills"
sb_ = sf.getbbox(sub)
hd.text((hub_cx - (sb_[2] - sb_[0]) // 2, hub_cy + 40), sub, font=sf, fill=MINT)
# bean face, small and honest: the •ᴗ• cue in mint
ff = mono(30)
hd.text((hub_cx - 30, hub_cy - 118), "\u2022\u1d17\u2022", font=ff, fill=PEACH)

# spokes: (label, angle_deg, pill_w)
spokes = [
    ("MIT", -90, 150),
    ("15 free skills", -30, 300),
    ("FREE to download", 30, 330),
    ("Pay per run", 90, 260),
    ("Readable", 150, 240),
    ("1 flagship paid", 210, 300),
]
for label, ang, pw in spokes:
    import math
    a = math.radians(ang)
    # spoke line from hub edge to pill inner edge
    r0 = 125 + hub_w // 2 * 0.0
    x0 = hub_cx + math.cos(a) * (hub_w // 2 + 10)
    y0 = hub_cy + math.sin(a) * (hub_h // 2 + 10)
    ph = 64
    rp = 250
    px = hub_cx + math.cos(a) * rp
    py = hub_cy + math.sin(a) * rp
    # clamp pill inside canvas
    px = min(max(px, 40 + pw // 2), W - 40 - pw // 2)
    py = min(max(py, 130), H - 130)
    # connect line hub->pill (from hub edge toward pill)
    d.line([x0, y0, px - math.cos(a) * (pw // 2 + 10), py - math.sin(a) * (ph // 2 + 10)],
           fill=RULE, width=4)
    # pill
    d.rounded_rectangle([px - pw // 2, py - ph // 2, px + pw // 2, py + ph // 2],
                        radius=22, fill=PALEMINT, outline=RULE, width=3)
    lf = mono(26, True)
    lb = lf.getbbox(label)
    d.text((px - (lb[2] - lb[0]) // 2, py - (lb[3] - lb[1]) // 2 - 8), label,
           font=lf, fill=PINE)

img.paste(hub, (0, 0), hub)

# ---------- CTA ----------
cta_w, cta_h = 300, 64
ctx, cty = W // 2, H - 92
d.rounded_rectangle([ctx - cta_w // 2, cty - cta_h // 2, ctx + cta_w // 2, cty + cta_h // 2],
                    radius=32, fill=PINE)
cf = mono(30, True)
ct = "omo.space"
cb = cf.getbbox(ct)
d.text((ctx - (cb[2] - cb[0]) // 2, cty - (cb[3] - cb[1]) // 2 - 9), ct, font=cf, fill=CREAM)

out = os.path.join(OUT, "image.png")
img.save(out)
print("wrote", out)
