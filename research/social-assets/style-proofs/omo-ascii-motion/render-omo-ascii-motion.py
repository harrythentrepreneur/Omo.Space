#!/usr/bin/env python3
"""OMO ASCII Motion — proof clip for the omo-social-media-post skill.

Generative ASCII animation in the Omo palette (deep pine canvas, cream/mint
characters, one orange accent) using the ascii-video pipeline:
scene_fn() -> tonemap() -> FeedbackBuffer -> ffmpeg.

Story (6.5s, 640x360 @ 24fps):
  act 1  seed pulse  : expanding rings, mint -> cream by radius
  act 2  the bean    : the Omo bean (super-ellipse SDF) breathes at center,
                       orange/peach result-dots orbit it, quiet mint fbm
  act 3  the result  : end card — 'omo.space' + 'BUY THE RESULT' stamped
                       in cream with a single orange underline pulse

All local: numpy + Pillow + ffmpeg. No API keys.
"""
import os
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

VW, VH, FPS, DUR = 640, 360, 24, 6.5
N_FRAMES = int(FPS * DUR)
OUTDIR = "/Users/yifan/marketplace/research/social-assets/style-proofs/omo-ascii-motion"
os.makedirs(OUTDIR, exist_ok=True)

FONT_PATH = "/System/Library/Fonts/Menlo.ttc"

# --- Omo brand palette (exact hexes from the style system) ---
PINE      = (23, 53, 44)      # #17352C  — ink
DEEP_PINE = (20, 43, 35)      # #142B23  — noir canvas
CREAM     = (248, 247, 245)   # #F8F7F5  — light
MINT      = (189, 239, 212)   # #BDEFD4  — field
MINT_DEEP = (120, 204, 161)   # #78CCA1  — terminal green
ORANGE    = (255, 107, 61)    # #FF6B3D  — the one accent
PEACH     = (255, 184, 157)   # #FFB89D  — warm highlight
MUTED     = (95, 111, 104)    # #5F6F68  — muted ink

# value ramp for main content: deep mint -> mint -> cream
RAMP = [MINT_DEEP, MINT_DEEP, MINT, MINT, CREAM]
# particle colors: orange and peach
PART_COLORS = [ORANGE, PEACH]

# character palettes (block family — brand-appropriate, no neon, no matrix)
PAL_BLOCKS = " \u2591\u2592\u2593\u2588"
PAL_DENSE  = " .:;+=xX$#@\u2588"
PAL_DOTS   = " \u00b7\u2218\u2022\u25cf\u2605"

all_chars = set()
for p in (PAL_BLOCKS, PAL_DENSE, PAL_DOTS):
    all_chars.update(p)
all_chars.update("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .-:!?/|#$@*+='")
all_chars.discard(" ")


class GridLayer:
    """Monospace character grid with pre-rasterized bitmaps (ascii-video skill)."""
    def __init__(self, font_size, vw=VW, vh=VH):
        self.vw, self.vh = vw, vh
        self.font = ImageFont.truetype(FONT_PATH, font_size)
        asc, desc = self.font.getmetrics()
        bbox = self.font.getbbox("M")
        self.cw = bbox[2] - bbox[0]
        self.ch = asc + desc  # CRITICAL: getmetrics, not textbbox (macOS PIL)
        self.cols = vw // self.cw
        self.rows = vh // self.ch
        self.ox = (vw - self.cols * self.cw) // 2
        self.oy = (vh - self.rows * self.ch) // 2
        cx, cy = self.cols / 2.0, self.rows / 2.0
        asp = self.cw / self.ch
        self.rr = np.arange(self.rows, dtype=np.float32)[:, None]
        self.cc = np.arange(self.cols, dtype=np.float32)[None, :]
        self.dx = self.cc - cx
        self.dy = (self.rr - cy) * asp
        self.dist = np.sqrt(self.dx ** 2 + self.dy ** 2)
        self.angle = np.arctan2(self.dy, self.dx)
        self.dx_n = (self.cc - cx) / max(self.cols, 1)
        self.dy_n = (self.rr - cy) / max(self.rows, 1) * asp
        self.dist_n = np.sqrt(self.dx_n ** 2 + self.dy_n ** 2)
        self.bm = {}
        for c in all_chars:
            img = Image.new("L", (self.cw, self.ch), 0)
            ImageDraw.Draw(img).text((0, 0), c, fill=255, font=self.font)
            self.bm[c] = np.array(img, dtype=np.float32) / 255.0

    def render(self, chars, colors, canvas=None):
        if canvas is None:
            canvas = np.zeros((self.vh, self.vw, 3), dtype=np.uint8)
        for row in range(self.rows):
            y = self.oy + row * self.ch
            if y + self.ch > self.vh:
                break
            for col in range(self.cols):
                c = chars[row, col]
                if c == " ":
                    continue
                x = self.ox + col * self.cw
                if x + self.cw > self.vw:
                    break
                a = self.bm[c]
                canvas[y:y + self.ch, x:x + self.cw] = np.maximum(
                    canvas[y:y + self.ch, x:x + self.cw],
                    (a[:, :, None] * colors[row, col]).astype(np.uint8))
        return canvas


def val2char(v, mask, pal):
    n = len(pal)
    idx = np.clip((v * n).astype(int), 0, n - 1)
    out = np.full(v.shape, " ", dtype="U1")
    for i, ch in enumerate(pal):
        out[mask & (idx == i)] = ch
    return out


def ramp_color(val, mask, ramp=RAMP):
    """Map value in [0,1] to a discrete brand ramp color."""
    n = len(ramp)
    idx = np.clip((val * n).astype(int), 0, n - 1)
    co = np.zeros((*val.shape, 3), dtype=np.uint8)
    for i, rgb in enumerate(ramp):
        m = mask & (idx == i)
        co[m] = rgb
    return co


def blend_canvas(base, top, opacity=0.6):
    af = base.astype(np.float32)
    bf = top.astype(np.float32)
    return np.clip(af * (1 - opacity) + bf * opacity, 0, 255).astype(np.uint8)


def tonemap(canvas, gamma=0.8):
    """Hue-preserving adaptive tonemap: compute one luma-based gain per
    pixel and scale all channels by it, so brand hexes (orange #FF6B3D,
    cream #F8F7F5) keep their exact hue. (Per-channel percentile stretching
    shifts orange toward peach — unacceptable for brand color fidelity.)"""
    f = canvas.astype(np.float32)
    lum = f @ np.array([0.299, 0.587, 0.114])          # luma
    sub = lum[::4, ::4]
    lo = np.percentile(sub, 1)
    hi = np.percentile(sub, 99.5)
    if hi - lo < 10:
        hi = lo + 10
    target = np.clip((lum - lo) / (hi - lo), 0, 1) ** gamma * 255.0
    gain = np.where(lum > 2.0, target / np.maximum(lum, 1e-6), 0.0)
    out = f * gain[:, :, None]
    return np.clip(out, 0, 255).astype(np.uint8)


class FeedbackBuffer:
    """Screen-blended trails (ascii-video skill). Screen never saturates a
    static bright pixel to white, so brand hues survive feedback."""
    def __init__(self):
        self.buf = None

    def apply(self, canvas, decay=0.82, opacity=0.5):
        cur = canvas.astype(np.float32)
        if self.buf is None:
            self.buf = cur
            return canvas
        self.buf *= decay
        out = 255.0 - (255.0 - cur) * (255.0 - self.buf) / 255.0   # screen
        self.buf = out
        return blend_canvas(canvas, np.clip(out, 0, 255).astype(np.uint8), opacity)


# --- grids ---
grid_sm = GridLayer(10)   # dense detail
grid_md = GridLayer(14)   # main
grid_lg = GridLayer(22)   # end-card text

# --- act 1: expanding rings (seed pulse) ---
def act_rings(t):
    g = grid_md
    val = np.zeros((g.rows, g.cols), dtype=np.float32)
    n = 5
    base = 3 + t * 2.2                       # rings expand outward
    for i in range(n):
        rad = (base + i * 4.0)
        rd = np.abs(g.dist - rad)
        th = 1.6
        ring = np.clip(1 - rd / th, 0, 1)
        fade = np.clip(1 - (base - 3) / 12, 0.25, 1)   # older rings dim
        val = np.maximum(val, ring * fade)
    val = np.clip(val * 1.2, 0, 1)
    mask = val > 0.04
    ch = val2char(val, mask, PAL_BLOCKS)
    co = ramp_color(val, mask)
    return grid_md.render(ch, co)

# --- act 2: the bean (super-ellipse SDF, breathing) + orbiting result dots ---
def act_bean(t):
    g = grid_sm
    # quiet mint background texture (layered sines — never flat black)
    bg = (np.sin(g.cc * 0.06 + t * 0.35) * np.sin(g.rr * 0.05 - t * 0.25) * 0.5 + 0.5) * 0.30 + \
         (np.sin(g.dist_n * 6 - t * 0.5) * 0.5 + 0.5) * 0.12
    # bean edge glow (wider band) + soft interior
    sb = np.abs(np.abs(g.dx_n / 0.20) ** 2.6 + np.abs(g.dy_n / 0.145) ** 2.6) ** (1 / 2.6)
    edge = np.clip(1.55 - sb * 3.1, 0, 1) * np.clip(1.15 - sb * 2.5, 0, 1)
    interior = np.clip(1.9 - sb * 3.1, 0, 1) * 0.95
    val = np.clip(np.maximum(edge, interior) + bg, 0, 1)
    mask = val > 0.04
    ch = val2char(val, mask, PAL_BLOCKS)
    co = ramp_color(val, mask)
    canvas = grid_sm.render(ch, co)
    # orbiting result dots (orange + peach) — the one orange accent
    g2 = grid_md
    dots_ch = np.full((g2.rows, g2.cols), " ", dtype="U1")
    dots_co = np.zeros((g2.rows, g2.cols, 3), dtype=np.uint8)
    n_dots = 7
    for i in range(n_dots):
        ang = t * 1.3 + i * 2 * np.pi / n_dots
        rx, ry = 0.30, 0.19
        c = int(g2.cols / 2 + np.cos(ang) * rx * g2.cols)
        r = int(g2.rows / 2 + np.sin(ang) * ry * g2.rows)
        if 0 <= r < g2.rows and 0 <= c < g2.cols:
            dots_ch[r, c] = "\u25cf"
            dots_co[r, c] = PART_COLORS[i % 2]
    canvas = g2.render(dots_ch, dots_co, canvas)
    return canvas

# --- act 3: the result end card ---
def act_result(t):
    g = grid_lg
    canvas = np.zeros((VH, VW, 3), dtype=np.uint8)
    # grid-aligned layout so every element lands on a sampled cell
    cy = g.oy + g.ch // 2                       # row-0 center y
    row = lambda r: cy + r * g.ch               # center y of grid row r
    top = int(row(1) - 14)
    bot = int(row(g.rows - 2) + 14)
    band = Image.new("RGB", (VW, VH), DEEP_PINE)
    d = ImageDraw.Draw(band)
    d.rounded_rectangle([70, top, VW - 70, bot], radius=18, fill=PINE)
    f1 = ImageFont.truetype(FONT_PATH, 34)
    f2 = ImageFont.truetype(FONT_PATH, 20)
    line1 = "omo.space"
    line2 = "BUY THE RESULT"
    b1 = d.textbbox((0, 0), line1, font=f1)
    b2 = d.textbbox((0, 0), line2, font=f2)
    h1 = b1[3] - b1[1]
    h2 = b2[3] - b2[1]
    d.text(((VW - (b1[2] - b1[0])) // 2, int(row(g.rows // 2 - 1)) - h1 // 2),
           line1, font=f1, fill=CREAM)
    d.text(((VW - (b2[2] - b2[0])) // 2, int(row(g.rows // 2 + 1)) - h2 // 2),
           line2, font=f2, fill=CREAM)
    # orange underline pulse, centered exactly on a sampled grid row
    ur = g.rows // 2 + 3 if g.rows // 2 + 3 < g.rows else g.rows - 1
    uc = int(row(ur))
    w = int(180 + 40 * np.sin(t * 6))
    d.rounded_rectangle([(VW - w) // 2, uc - 6, (VW + w) // 2, uc + 6], radius=4, fill=ORANGE)
    arr = np.array(band)                                   # (VH, VW, 3)

    ch = np.full((g.rows, g.cols), " ", dtype="U1")
    co = np.zeros((g.rows, g.cols, 3), dtype=np.uint8)
    def is_near(px, ref, tol=30):
        return abs(int(px[0]) - ref[0]) <= tol and abs(int(px[1]) - ref[1]) <= tol \
               and abs(int(px[2]) - ref[2]) <= tol
    def cell_kind(r, c):
        """3x3 mini-samples per cell; priority orange > cream > pine > deep pine."""
        y0 = g.oy + r * g.ch
        x0 = g.ox + c * g.cw
        for dy in (g.ch // 4, g.ch // 2, 3 * g.ch // 4):
            for dx in (g.cw // 4, g.cw // 2, 3 * g.cw // 4):
                px = arr[y0 + dy, x0 + dx]
                if is_near(px, ORANGE, 55):
                    return "orange"
        best = None
        for dy in (g.ch // 4, g.ch // 2, 3 * g.ch // 4):
            for dx in (g.cw // 4, g.cw // 2, 3 * g.cw // 4):
                px = arr[y0 + dy, x0 + dx]
                if is_near(px, CREAM, 45):
                    return "cream"
                if best is None and is_near(px, PINE, 60):
                    best = "pine"
        return best or "empty"
    for r in range(g.rows):
        for c in range(g.cols):
            kind = cell_kind(r, c)
            if kind == "orange":
                ch[r, c] = "\u2588"; co[r, c] = ORANGE
            elif kind == "cream":
                ch[r, c] = "\u2588"; co[r, c] = CREAM
            elif kind == "pine":
                ch[r, c] = "\u2593"; co[r, c] = PINE           # dark panel, textured
    canvas = g.render(ch, co, canvas)
    reveal = min(1.0, max(0.0, (t - 0.6) / 0.5))
    if reveal < 1:
        canvas = (canvas.astype(np.float32) * reveal).astype(np.uint8)
    return canvas


def scene(t):
    if t < 2.4:
        return act_rings(t)
    if t < 4.6:
        return act_bean(t)
    return act_result(t)


# --- render loop with feedback, pipe to ffmpeg ---
mp4_path = os.path.join(OUTDIR, "omo-ascii-motion.mp4")
err_log = os.path.join(OUTDIR, "ffmpeg-encode.log")
cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
       "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "pipe:0",
       "-c:v", "libx264", "-preset", "fast", "-crf", "20",
       "-pix_fmt", "yuv420p", mp4_path]
stderr_fh = open(err_log, "w")
pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL, stderr=stderr_fh)

fb = FeedbackBuffer()
means = []
fb_active = True
for fi in range(N_FRAMES):
    t = fi / FPS
    canvas = scene(t)
    canvas = tonemap(canvas, gamma=0.82)
    if t >= 4.6:
        if fb_active:                      # end card = crisp hold, no trails
            fb = FeedbackBuffer()
            fb_active = False
    else:
        canvas = fb.apply(canvas, decay=0.80, opacity=0.45)
    means.append(canvas.astype(float).mean())
    pipe.stdin.write(canvas.tobytes())
pipe.stdin.close()
pipe.wait()
stderr_fh.close()
print("mp4:", mp4_path, "frames:", N_FRAMES,
      "mean brightness min/max: %.1f/%.1f" % (min(means), max(means)))

# --- GIF (320x180 @ 15fps, palette-optimized) ---
gif_path = os.path.join(OUTDIR, "omo-ascii-motion.gif")
subprocess.run(["ffmpeg", "-y", "-i", mp4_path, "-vf",
                "fps=15,scale=320:180:flags=lanczos,split[s0][s1];"
                "[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3",
                gif_path], check=True, stdout=subprocess.DEVNULL,
               stderr=subprocess.DEVNULL)
print("gif:", gif_path)
