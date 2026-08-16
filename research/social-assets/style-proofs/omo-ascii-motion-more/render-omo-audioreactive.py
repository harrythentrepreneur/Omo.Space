#!/usr/bin/env python3
"""AUDIO-REACTIVE "BUY THE RESULT" — a 7s brand visualizer (640x360 @ 24fps).

An ffmpeg-synthesized 120 BPM beat (55Hz kick + offbeat noise hats + 110Hz
bass swell, all aevalsrc — no samples needed) drives mirrored spectrum bars
in the brand ramp (deep mint -> mint -> cream) with orange tips on beats,
a live waveform on the mirror axis, and the tagline "BUY THE RESULT" /
"NOT ANOTHER SUBSCRIPTION" jumping on every beat. The audio track is
muxed into the MP4 (AAC). Pipeline: scene -> hue-preserving LUMA tonemap ->
screen-blend feedback -> ffmpeg.
"""
import math
import os
import subprocess

import numpy as np
from PIL import ImageFont

from omo_common import (VW, VH, FPS, FONT_PATH, CREAM, MINT, MINT_DEEP,
                        ORANGE, RAMP, PAL_BLOCKS, GridLayer, tonemap,
                        FeedbackBuffer, encode_mp4, load_audio_features)

DUR = 7.0
N = int(FPS * DUR)
OUT = os.path.dirname(os.path.abspath(__file__))
WAV = os.path.join(OUT, "omo-audioreactive.wav")

g_sm = GridLayer(10)   # bars / waveform (106 x 29)
g_md = GridLayer(14)   # subline (76 x 21)
g_lg = GridLayer(22)   # headline (48 x 13)


def gen_audio():
    if os.path.exists(WAV) and os.path.getsize(WAV) > 1000:
        return
    # Kick every 0.5s ((t*2-floor(t*2)) = sawtooth period 0.5), offbeat hats,
    # 110Hz bass swell. floor() instead of mod() — aevalsrc splits exprs on
    # commas, so mod(t,0.5) would break the expression list.
    cmd = ["ffmpeg", "-y",
           "-f", "lavfi",
           "-i", "aevalsrc=0.7*sin(2*PI*55*t)*exp(-14*(t*2-floor(t*2))):s=44100:d=7",
           "-f", "lavfi",
           "-i", "aevalsrc=0.16*(random(0)-0.5)*exp(-45*(t*2+0.5-floor(t*2+0.5))):s=44100:d=7",
           "-f", "lavfi",
           "-i", "aevalsrc=0.30*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*t*0.25)):s=44100:d=7",
           "-filter_complex",
           "[0:a][1:a][2:a]amix=inputs=3:normalize=0,"
           "alimiter=limit=0.95,afade=t=in:st=0:d=0.05,afade=t=out:st=6.9:d=0.1[a]",
           "-map", "[a]", "-ac", "1", WAV]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    print("audio generated:", WAV)


FEATS, SAMPLES, HOP = None, None, None


def load():
    global FEATS, SAMPLES, HOP
    FEATS, SAMPLES, HOP, _sr = load_audio_features(WAV, fps=FPS)
    print(f"audio analyzed: {len(FEATS['beat'])} frames, "
          f"{int(FEATS['beat'].sum())} beats detected")


def scene(fi):
    t = fi / FPS
    f = {k: float(v[fi]) for k, v in FEATS.items()}

    # ---- background: deep pine + mint texture, energy-scaled ----
    rr = np.arange(VH, dtype=np.float32)[:, None]
    cc = np.arange(VW, dtype=np.float32)[None, :]
    tex = (np.sin(cc * 0.02 + t * 0.35) * np.sin(rr * 0.025 - t * 0.25) * 0.5 + 0.5) * 0.10
    en = 0.8 + 0.4 * f["rms"]
    b = np.empty((VH, VW, 3), dtype=np.float32)
    b[..., 0] = 20 + tex * 80 * en
    b[..., 1] = 43 + tex * 105 * en
    b[..., 2] = 35 + tex * 90 * en
    canvas = np.clip(b, 0, 255).astype(np.uint8)

    # ---- mirrored spectrum bars (brand ramp, orange tips on beats) ----
    g = g_sm
    ch = np.full((g.rows, g.cols), " ", dtype="U1")
    co = np.zeros((g.rows, g.cols, 3), dtype=np.uint8)
    n_bars = 44
    bar_w = 2
    total = n_bars * bar_w
    c0 = (g.cols - total) // 2
    center = g.rows // 2
    maxh = center - 4
    bvals = [f["sub"], f["bass"], f["lomid"], f["mid"], f["himid"], f["hi"]]
    for b_i in range(n_bars):
        frac = b_i / n_bars
        fi_ = frac * 5
        lo_i = int(fi_)
        hi_i = min(lo_i + 1, 5)
        bv = (bvals[lo_i] * (1 - fi_ % 1) + bvals[hi_i] * (fi_ % 1)) * 1.5 \
            + 0.10 * f["bdecay"]
        bv = min(1.0, bv)
        hgt = int(bv * maxh)
        if hgt < 1:
            continue
        bch = PAL_BLOCKS[1 + min(int(bv * 4), 3)]
        hot = bv > 0.72 or f["bdecay"] > 0.45
        for dy in range(hgt):
            ri = min(int((dy / max(hgt, 1)) * len(RAMP)), len(RAMP) - 1)
            col = RAMP[ri]
            if hot and dy == hgt - 1:
                col = ORANGE
            for dc in range(bar_w):
                colx = c0 + b_i * bar_w + dc
                ch[center - dy, colx] = bch
                co[center - dy, colx] = col
                ch[center + dy, colx] = bch
                co[center + dy, colx] = col
    canvas = g.render(ch, co, canvas)

    # ---- live waveform on the mirror axis (full width) ----
    chunk = SAMPLES[fi * HOP: fi * HOP + HOP]
    xq = np.linspace(0, len(chunk) - 1, g.cols)
    down = np.interp(xq, np.arange(len(chunk)), chunk)
    amp = 1.8 + 2.4 * f["rms"]
    for i in range(g.cols):
        row = int(np.clip(down[i] * amp, -2, 2))
        rw = center + row
        if 0 <= rw < g.rows:
            ch[rw, i] = "\u2022"
            co[rw, i] = ORANGE if abs(row) >= 2 else MINT
    canvas = g.render(ch, co, canvas)

    # ---- tagline: cream headline jumps on beats, mint subline ----
    gL = g_lg
    chL = np.full((gL.rows, gL.cols), " ", dtype="U1")
    coL = np.zeros((gL.rows, gL.cols, 3), dtype=np.uint8)
    line1 = "BUY THE RESULT"
    jump = -1 if f["bdecay"] > 0.5 else 0
    row1 = 1 + jump
    flash = 0.62 + 0.38 * f["bdecay"]
    c_start = (gL.cols - len(line1)) // 2
    for i, ch_ in enumerate(line1):
        if 0 <= row1 < gL.rows:
            chL[row1, c_start + i] = ch_
            coL[row1, c_start + i] = tuple(int(v * flash) for v in CREAM)
    canvas = gL.render(chL, coL, canvas)

    gM = g_md
    chM = np.full((gM.rows, gM.cols), " ", dtype="U1")
    coM = np.zeros((gM.rows, gM.cols, 3), dtype=np.uint8)
    line2 = "NOT ANOTHER SUBSCRIPTION"
    flash2 = 0.7 + 0.3 * f["bdecay"]
    c2 = (gM.cols - len(line2)) // 2
    for i, ch_ in enumerate(line2):
        chM[5, c2 + i] = ch_
        coM[5, c2 + i] = tuple(int(v * flash2) for v in MINT)
    canvas = gM.render(chM, coM, canvas)

    # ---- global beat lift ----
    if f["bdecay"] > 0.02:
        lift = int(10 * f["bdecay"])
        canvas = np.clip(canvas.astype(np.int16) + lift, 0, 255).astype(np.uint8)
    return canvas


def gen_frames():
    fb = FeedbackBuffer()
    for fi in range(N):
        canvas = scene(fi)
        canvas = tonemap(canvas, gamma=0.82)
        canvas = fb.apply(canvas, decay=0.82, opacity=0.40)
        yield canvas


if __name__ == "__main__":
    gen_audio()
    load()
    encode_mp4(gen_frames(), os.path.join(OUT, "omo-audioreactive.mp4"), N,
               audio=WAV)
    print("omo-audioreactive.mp4 done")
