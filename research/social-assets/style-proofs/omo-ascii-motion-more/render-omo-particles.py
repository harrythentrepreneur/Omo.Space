#!/usr/bin/env python3
"""PARTICLES — a calm 5.5s brand-colored drift scene (640x360 @ 24fps).

The quiet inverse of the dark proof clips: a cream canvas (brand light),
a barely-there mint bean ghost breathing at center, and ~300 motes, bubbles
and sparks drifting upward with a gentle sway — pine, mint-deep, mint and
muted motes, rare orange/peach sparks that twinkle. Slow fade-in/out.
No tonemap needed (the scene is bright by design); exact brand hexes are
alpha-composited over cream so dark pine reads as ink on paper.
"""
import math
import os

import numpy as np

from omo_common import (VW, VH, FPS, PINE, MINT, MINT_DEEP, ORANGE, PEACH,
                        MUTED, CREAM, GridLayer, encode_mp4, smoothstep)

DUR = 5.5
N = int(FPS * DUR)
OUT = os.path.dirname(os.path.abspath(__file__))

g = GridLayer(14)   # 76 x 21 cells

# ---- particle state -------------------------------------------------------
NP = 300
rng = np.random.RandomState(11)
PX = rng.uniform(0, g.cols, NP).astype(np.float32)
PY = rng.uniform(0, g.rows, NP).astype(np.float32)
KIND = rng.choice(["mote", "mote", "mote", "spark", "bubble"], NP)
VY = np.where(KIND == "spark", rng.uniform(-0.42, -0.24, NP),
              np.where(KIND == "bubble", rng.uniform(-0.05, -0.02, NP),
                       rng.uniform(-0.16, -0.04, NP))).astype(np.float32)
PHASE = rng.uniform(0, 2 * np.pi, NP).astype(np.float32)

P_CHAR = np.empty(NP, dtype="U2")
P_COL = np.zeros((NP, 3), dtype=np.uint8)
for i in range(NP):
    if KIND[i] == "spark":
        P_CHAR[i] = g.safe_char("\u2736", "\u2022") if i % 2 else "\u2022"
        P_COL[i] = ORANGE if rng.rand() < 0.6 else PEACH
    elif KIND[i] == "bubble":
        P_CHAR[i] = g.safe_char("\u25cb", "\u2218")
        P_COL[i] = PINE
    else:
        r = rng.rand()
        if r < 0.40:
            P_CHAR[i] = "\u00b7"; P_COL[i] = PINE
        elif r < 0.65:
            P_CHAR[i] = "\u2218"; P_COL[i] = MINT_DEEP
        elif r < 0.80:
            P_CHAR[i] = "\u2022"; P_COL[i] = MUTED
        else:
            P_CHAR[i] = "\u2022"; P_COL[i] = MINT
print(f"particles: {NP}  (blank glyphs substituted: "
      f"{sorted(g.blank) if g.blank else 'none'})")


def bg_cream(t):
    rr = np.arange(VH, dtype=np.float32)[:, None]
    cc = np.arange(VW, dtype=np.float32)[None, :]
    base = np.full((VH, VW, 3), CREAM, dtype=np.float32)
    # faint mint texture
    v = np.sin(cc * 0.015 + t * 0.12) * np.sin(rr * 0.02 - t * 0.09) * 0.5 + 0.5
    tint = 0.05 * v
    base = base * (1 - tint[..., None]) \
        + np.array(MINT, dtype=np.float32) * tint[..., None]
    # ghost bean (brand super-ellipse), breathing
    dxn = (cc - VW / 2) / VW
    dyn = (rr - VH / 2) / VH * 0.5
    sb = np.abs(np.abs(dxn / 0.20) ** 2.6 + np.abs(dyn / 0.145) ** 2.6) ** (1 / 2.6)
    edge = np.clip(1.55 - sb * 3.1, 0, 1) * np.clip(1.15 - sb * 2.5, 0, 1)
    ghost = 0.08 * edge * (0.55 + 0.45 * math.sin(t * 1.1))
    base = base * (1 - ghost[..., None]) \
        + np.array(MINT, dtype=np.float32) * ghost[..., None]
    return np.clip(base, 0, 255).astype(np.uint8)


def blit(canvas, r, c, ch_c, color, alpha):
    """Alpha-composite one glyph over the canvas (overwrite, not max —
    dark pine ink must show on the bright cream field)."""
    y = g.oy + r * g.ch
    x = g.ox + c * g.cw
    if y + g.ch > VH or x + g.cw > VW:
        return
    a = g.bm[ch_c] * alpha
    m = a > 0.05
    if not m.any():
        return
    reg = canvas[y:y + g.ch, x:x + g.cw].astype(np.float32)
    col = np.array(color, dtype=np.float32)
    reg[m] = reg[m] * (1 - a[m])[:, None] + col * a[m][:, None]
    canvas[y:y + g.ch, x:x + g.cw] = np.clip(reg, 0, 255).astype(np.uint8)


def scene(fi):
    t = fi / FPS
    canvas = bg_cream(t)
    # drift: gentle sway + slow rise, respawn at bottom
    xq = PX + np.sin(t * 0.9 + PHASE) * 0.055
    yq = PY + VY
    up = yq < -1
    if up.any():
        yq[up] = g.rows + 1 + rng.uniform(0, 1, int(up.sum()))
        xq[up] = rng.uniform(0, g.cols, int(up.sum()))
    PX[:] = xq % g.cols
    PY[:] = yq
    for i in range(NP):
        r = int(PY[i])
        c = int(PX[i])
        if 0 <= r < g.rows and 0 <= c < g.cols:
            if KIND[i] == "spark":
                tw = 0.5 + 0.5 * math.sin(t * 5.0 + PHASE[i] * 6)
            else:
                tw = 0.62 + 0.38 * math.sin(t * 2.2 + PHASE[i] * 7)
            blit(canvas, r, c, P_CHAR[i], P_COL[i], max(0.15, tw))
    # global fade in/out toward cream
    fade = smoothstep(min(1.0, t / 0.8)) \
        * (1 - smoothstep(max(0.0, (t - 4.7) / 0.8)))
    if fade < 1.0:
        canvas = (canvas.astype(np.float32) * fade
                  + np.array(CREAM, dtype=np.float32) * (1 - fade))
    return np.clip(canvas, 0, 255).astype(np.uint8)


def gen_frames():
    for fi in range(N):
        yield scene(fi)


if __name__ == "__main__":
    encode_mp4(gen_frames(), os.path.join(OUT, "omo-particles.mp4"), N)
    print("omo-particles.mp4 done")
