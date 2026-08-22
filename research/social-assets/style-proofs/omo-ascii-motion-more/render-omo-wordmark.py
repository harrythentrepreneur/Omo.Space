#!/usr/bin/env python3
"""WORDMARK-OMO — a 5.5s brand logo reveal (640x360 @ 24fps).

Concept: a meta-logo. The wordmark "OMO" is built from a swarm of tiny
O/M letters that fly in from all corners and lock into the big letterforms,
then the mark breathes, rings shockwave off it, an orange underline draws
itself, and the tagline 'omo.space' fades in below. Deep-pine canvas, cream
letterforms with mint edges, one pulsing orange accent — the first proof
clip's exact palette rules (hue-preserving LUMA tonemap, screen feedback).

Acts:
  assemble (0-1.6s)  cells scatter-converge with ease-out, fade in
  pulse    (1.6-3.2s) mark breathes, shockwave rings, underline draws
  resolve  (3.2-5.5s) crisp hold, orange underline pulses, motes drift,
                      'omo.space' fades in below
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from omo_common import (VW, VH, FPS, FONT_PATH, DEEP_PINE, CREAM, MINT,
                        MINT_DEEP, ORANGE, PAL_BLOCKS,
                        GridLayer, val2char, ramp_color, tonemap,
                        FeedbackBuffer, encode_mp4, ease_out_cubic,
                        smoothstep)

DUR = 5.5
N = int(FPS * DUR)
OUT = os.path.dirname(os.path.abspath(__file__))

g_sm = GridLayer(10)   # letter cells (6x12 px)
g_md = GridLayer(14)   # rings / motes

# ---- pixel wordmark masks -------------------------------------------------
F_BIG = ImageFont.truetype(FONT_PATH, 210)
ADV = int(round(0.6 * 210))            # Menlo monospace advance per glyph
W_W = 3 * ADV
X0 = (VW - W_W) // 2


def _glyph_geometry():
    test = Image.new("L", (VW, VH), 0)
    d = ImageDraw.Draw(test)
    for i, ch in enumerate("OMO"):
        d.text((X0 + i * ADV, 10), ch, fill=255, font=F_BIG)
    rows = np.argwhere(np.array(test, dtype=np.float32).max(axis=1) > 0.02)
    return int(rows.min()), int(rows.max())


_TMIN, _TMAX = _glyph_geometry()
GH = _TMAX - _TMIN
Y0 = int(VH * 0.28) - _TMIN + 10       # ink top lands at 0.28*VH

_full = Image.new("L", (VW, VH), 0)
_d = ImageDraw.Draw(_full)
for _i, _ch in enumerate("OMO"):
    _d.text((X0 + _i * ADV, Y0), _ch, fill=255, font=F_BIG)
MASK = np.array(_full, dtype=np.float32) / 255.0
ROWS_ON = np.argwhere(MASK.max(axis=1) > 0.02)
WM_TOP = int(ROWS_ON.min())
WM_BOT = int(ROWS_ON.max())


def cell_cov(px, py):
    s, n = 0.0, 0
    for dy in (-4, 0, 4):
        for dx in (-3, 0, 3):
            yy, xx = py + dy, px + dx
            if 0 <= yy < VH and 0 <= xx < VW:
                s += MASK[int(yy), int(xx)]
                n += 1
    return s / max(n, 1)


# ---- precompute in-letter cells with scatter offsets ----------------------
rng = np.random.RandomState(7)
SCAT = {}
for r in range(g_sm.rows):
    for c in range(g_sm.cols):
        hx = g_sm.ox + c * g_sm.cw + g_sm.cw / 2
        hy = g_sm.oy + r * g_sm.ch + g_sm.ch / 2
        cov = cell_cov(hx, hy)
        if cov < 0.10:
            continue
        region = max(0, min(2, (int(hx) - X0) // ADV))
        ang = rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(70, 300)
        kind = "interior" if cov >= 0.5 else ("edge" if cov >= 0.26 else "faint")
        SCAT[(r, c)] = dict(hx=hx, hy=hy, dx=math.cos(ang) * dist,
                            dy=math.sin(ang) * dist, region=region, kind=kind)
print(f"wordmark cells: {len(SCAT)}")


def blit_letter(canvas, px, py, ch_char, color, alpha):
    """Alpha-blit one glyph bitmap centered at (px, py)."""
    x = int(px - g_sm.cw / 2)
    y = int(py - g_sm.ch / 2)
    if x < 0 or y < 0 or x + g_sm.cw > VW or y + g_sm.ch > VH:
        return
    a = g_sm.bm[ch_char] * alpha
    m = a > 0.05
    if not m.any():
        return
    reg = canvas[y:y + g_sm.ch, x:x + g_sm.cw].astype(np.float32)
    col = np.array(color, dtype=np.float32)
    reg[m] = reg[m] * (1 - a[m])[:, None] + col * a[m][:, None]
    canvas[y:y + g_sm.ch, x:x + g_sm.cw] = np.clip(reg, 0, 255).astype(np.uint8)


def bg_pine(t):
    rr = np.arange(VH, dtype=np.float32)[:, None]
    cc = np.arange(VW, dtype=np.float32)[None, :]
    tex = (np.sin(cc * 0.02 + t * 0.3) * np.sin(rr * 0.025 - t * 0.2) * 0.5 + 0.5) * 0.11 \
        + (np.sin(np.hypot((cc - VW / 2) / 300.0, (rr - VH / 2) / 170.0) * 3 - t * 0.4) * 0.5 + 0.5) * 0.05
    b = np.empty((VH, VW, 3), dtype=np.float32)
    b[..., 0] = DEEP_PINE[0] + tex * 80
    b[..., 1] = DEEP_PINE[1] + tex * 105
    b[..., 2] = DEEP_PINE[2] + tex * 90
    return np.clip(b, 0, 255).astype(np.uint8)


def rings_layer(t):
    canvas = np.zeros((VH, VW, 3), dtype=np.uint8)
    for k in range(3):
        t0 = 0.55 + k * 1.3
        age = t - t0
        if 0.0 <= age < 1.1:
            prog = age / 1.1
            rad = 40 + prog * 260
            val = np.clip(1 - np.abs(g_md.dist - rad) / 16, 0, 1) * (1 - prog) * 0.9
            mask = val > 0.05
            ch = val2char(val, mask, PAL_BLOCKS)
            co = ramp_color(val, mask, [MINT_DEEP, MINT_DEEP, MINT])
            canvas = np.maximum(canvas, g_md.render(ch, co))
    return canvas


def wordmark(t):
    canvas = np.zeros((VH, VW, 3), dtype=np.uint8)
    p = ease_out_cubic(min(1.0, t / 1.6))          # assemble progress
    if t < 1.6:
        fade = 0.30 + 0.70 * p                     # fade in while assembling
    elif t < 3.2:
        fade = 0.86 + 0.14 * math.sin(t * 4.2)     # breathe
    else:
        fade = 0.99 + 0.01 * math.sin(t * 2.4)     # calm hold
    for (r, c), s in SCAT.items():
        px = s["hx"] + s["dx"] * (1 - p)
        py = s["hy"] + s["dy"] * (1 - p)
        if s["kind"] == "interior":
            ch_c, col = "OMO"[s["region"]], CREAM
        elif s["kind"] == "edge":
            ch_c, col = "\u2593", MINT
        else:
            ch_c, col = "\u2591", MINT_DEEP
        blit_letter(canvas, px, py, ch_c, col, fade)
    # one pulsing orange accent cell per letter
    for reg in range(3):
        cells = [key for key, s in SCAT.items()
                 if s["region"] == reg and s["kind"] == "interior"]
        if cells:
            key = cells[(reg * 7) % len(cells)]
            s = SCAT[key]
            a = 0.55 + 0.45 * math.sin(t * 5 + reg * 2.1)
            blit_letter(canvas, s["hx"], s["hy"], "OMO"[reg], ORANGE,
                        max(0.25, a))
    return canvas


def draw_pil(canvas, t):
    img = Image.fromarray(canvas)
    d = ImageDraw.Draw(img)
    if t >= 1.6:
        if t < 3.2:
            uw = int(320 * ease_out_cubic((t - 1.6) / 0.9))
        else:
            uw = int(320 * (0.82 + 0.18 * math.sin(t * 3.0)))
        uy = WM_BOT + 24
        d.rounded_rectangle([(VW - uw) // 2, uy, (VW + uw) // 2, uy + 10],
                            radius=5, fill=ORANGE)
    if t >= 3.3:
        ta = smoothstep(min(1.0, (t - 3.3) / 0.7))
        f26 = ImageFont.truetype(FONT_PATH, 26)
        txt = "omo.space"
        bb = d.textbbox((0, 0), txt, font=f26)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        ty = min(WM_BOT + 50, VH - th - 6)
        col = tuple(int(c * ta) for c in MINT)
        d.text(((VW - tw) // 2, ty), txt, font=f26, fill=col)
    return np.array(img)


def motes(t, canvas):
    if t < 3.2:
        return canvas
    ch_arr = np.full((g_md.rows, g_md.cols), " ", dtype="U1")
    co_arr = np.zeros((g_md.rows, g_md.cols, 3), dtype=np.uint8)
    for i in range(70):
        spd = 9 + (i % 5) * 4
        y = (VH * 0.6 - ((t - 3.2) * spd + (i * 137) % VH)) % VH
        x = (i * 211) % VW + math.sin(t * 0.7 + i * 1.7) * 12
        r = int((y - g_md.oy) / g_md.ch)
        c = int((x - g_md.ox) / g_md.cw)
        if 0 <= r < g_md.rows and 0 <= c < g_md.cols:
            ch_arr[r, c] = "\u00b7" if i % 3 else "\u2022"
            co_arr[r, c] = MINT if i % 4 else ORANGE
    return g_md.render(ch_arr, co_arr, canvas)


def scene(fi):
    t = fi / FPS
    canvas = bg_pine(t)
    canvas = np.maximum(canvas, rings_layer(t))
    canvas = np.maximum(canvas, wordmark(t))
    canvas = draw_pil(canvas, t)
    canvas = motes(t, canvas)
    return canvas


def gen_frames():
    fb = FeedbackBuffer()
    fb_active = True
    for fi in range(N):
        t = fi / FPS
        canvas = scene(fi)
        canvas = tonemap(canvas, gamma=0.82)
        if t >= 3.2:                        # crisp hold: no trails
            if fb_active:
                fb = FeedbackBuffer()
                fb_active = False
        else:
            canvas = fb.apply(canvas, decay=0.80, opacity=0.45)
        yield canvas


if __name__ == "__main__":
    encode_mp4(gen_frames(), os.path.join(OUT, "wordmark-omo.mp4"), N)
    print("wordmark-omo.mp4 done")
