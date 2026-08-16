#!/usr/bin/env python3
"""Omo vector-motion pipeline (issue #117).

Renders brand-style flat-vector motion clips per
research/OMO-IMAGE-STYLE-SYSTEM.MD (cream canvas, pine 9px frame, pastel
fields, bean mascot with dot eyes at -7 deg, Fraunces + DM Sans, ONE orange
accent <=5%) and encodes MP4 (H.264) + GIF via ffmpeg.

Design:
  - Every frame is drawn on an RGBA Frame at `scale` supersample, then
    LANCZOS-downscaled to target size before piping raw RGB24 to ffmpeg
    (same crisp-flat-edge trick as the style-sheet renders).
  - Elements that move/rotate/fade are pre-rendered onto transparent layers
    and placed with place() (scale / rotate / alpha) — the motion engine.
  - Motion primitives are pure functions of time t (easing, spring/pop,
    fade, drift, draw-on progress, wrapped periodic oscillators), so output
    is fully deterministic: same args -> identical frames.
  - loop=True clips wrap time with period P=(N-1)/fps; scene functions must
    return to the t=0 pose at t=P. Last frame == first frame, pixel-exact.

Usage:
  python3 vector_motion.py <clip> [--fps N] [--scale N] [--no-gif]
  python3 vector_motion.py --list
  python3 vector_motion.py --frames <clip>   # probe frames->PNG montage
Clips: mascot-wave comparison-drawon book-maker-pop tagline-loop phonics-bounce

Library:
  from vector_motion import SceneRegistry, Frame, place, easing, render_clip,
  encode_mp4, encode_gif, verify_mp4, palette_census
"""
import math, os, random, subprocess, sys, tempfile, json

from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------
# style tokens + primitives (reuse the canonical style-sheet library)
# --------------------------------------------------------------------------
_SHEET = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "style-sheet"))
if _SHEET not in sys.path:
    sys.path.insert(0, _SHEET)
import omo_style as _os  # palette, bean_pts, blob_pts, star_pts, rotate_pts, FDIR

CREAM, PINE, MINT, ORANGE, PEACH = (_os.CREAM, _os.PINE, _os.MINT,
                                    _os.ORANGE, _os.PEACH)
WHITE, SKY, BUTTER, LILAC = (_os.WHITE, _os.SKY, _os.BUTTER, _os.LILAC)
MUTED, MUTED2, RULE, MINTDEEP = (_os.MUTED, _os.MUTED2, _os.RULE, _os.MINTDEEP)
CREAM_W = _os.CREAM_W
PALEMINT, PALEPEACH = _os.PALEMINT, _os.PALEPEACH
FDIR = _os.FDIR

random.seed(2026)  # deterministic

# --------------------------------------------------------------------------
# easing + motion primitives (pure functions of t in [0,1] or seconds)
# --------------------------------------------------------------------------
def clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

def ease_out_cubic(t):
    t = clamp01(t); return 1 - (1 - t) ** 3

def ease_in_cubic(t):
    t = clamp01(t); return t ** 3

def ease_out_back(t, s=1.70158):
    """Spring overshoot: 0 at 0, ~1.1 mid-way, exactly 1 at t>=1."""
    t = clamp01(t)
    if t >= 1.0:
        return 1.0
    u = t - 1
    return 1 + (s + 1) * u ** 3 + s * u ** 2

def smoothstep(t):
    t = clamp01(t); return t * t * (3 - 2 * t)

def seg(t, t0, t1):
    """Ramp 0->1 between t0 and t1 (0 outside), for piecewise timelines."""
    if t <= t0: return 0.0
    if t >= t1: return 1.0
    return (t - t0) / (t1 - t0)

def spring_in(t, t0, dur):
    """Pop-in scale: 0 before t0, spring overshoot, exactly 1 after."""
    p = seg_ease(t, t0, t0 + dur, ease_out_back)
    return p

def seg_ease(t, t0, t1, ease=ease_out_cubic):
    return ease(seg(t, t0, t1))

def fade_alpha(t, t0, t1, out=False):
    if not out:
        return seg_ease(t, t0, t1)
    return 1 - seg_ease(t, t0, t1, ease_in_cubic)

def pulse(t, t0, dur, amp=1.0, cycles=1.0):
    """Rise+fall bump: exact 0 at t0 and t0+dur (sin-squared)."""
    p = seg(t, t0, t0 + dur)
    return amp * math.sin(math.pi * p * cycles) ** 2

def drawon_progress(t, t0, t1, ease=ease_out_cubic):
    return ease(seg(t, t0, t1))

def wrap(t, P):
    """Periodic time for loop-clean clips."""
    return t % P if P > 0 else t

def osc_loop(tw, P, cycles, amp):
    """Integer-cycle oscillator: value == start exactly at t=0 and t=P."""
    return amp * math.sin(2 * math.pi * cycles * tw / P)

# --------------------------------------------------------------------------
# fonts
# --------------------------------------------------------------------------
_FONTS = {}
def font(name, px):
    key = (name, px)
    f = _FONTS.get(key)
    if f is None:
        f = ImageFont.truetype(os.path.join(FDIR, name), px)
        _FONTS[key] = f
    return f

def F(size): return "fraunces_600" if False else None  # placeholder, unused

# --------------------------------------------------------------------------
# Frame + layer compositing
# --------------------------------------------------------------------------
class Frame:
    """Supersampled RGBA canvas with omo-style primitives (coords * scale)."""
    def __init__(self, W, H, scale=2, fill=CREAM):
        self.W, self.H, self.scale = W, H, scale
        self.img = Image.new("RGBA", (W * scale, H * scale), fill + (255,))
        self.d = ImageDraw.Draw(self.img)
        self.F = 0.0  # current time, optional

    def S(self, v):
        return v * self.scale

    def rrect(self, box, radius, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(
            [self.S(box[0]), self.S(box[1]), self.S(box[2]), self.S(box[3])],
            radius=self.S(radius), fill=fill, outline=outline,
            width=max(1, int(round(width * self.scale))))

    def poly(self, pts, fill, outline=None, width=1):
        self.d.polygon([(self.S(x), self.S(y)) for (x, y) in pts],
                       fill=fill, outline=outline,
                       width=max(1, int(round(width * self.scale))))

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse([self.S(box[0]), self.S(box[1]),
                        self.S(box[2]), self.S(box[3])],
                       fill=fill, outline=outline,
                       width=max(1, int(round(width * self.scale))))

    def line(self, p0, p1, fill, width):
        self.d.line([self.S(p0[0]), self.S(p0[1]),
                     self.S(p1[0]), self.S(p1[1])],
                    fill=fill, width=max(1, int(round(width * self.scale))),
                    joint="curve")

    def polyline(self, pts, fill, width):
        self.d.line([(self.S(x), self.S(y)) for (x, y) in pts],
                    fill=fill, width=max(1, int(round(width * self.scale))),
                    joint="curve")

    def text(self, xy, s, f, fill, tracking=0.0, anchor="la"):
        x, y = self.S(xy[0]), self.S(xy[1])
        if tracking:
            step = tracking * (f.size / self.scale)
            for ch in s:
                self.d.text((x, y), ch, font=f, fill=fill, anchor=anchor)
                x += f.getlength(ch) + self.S(step)
        else:
            self.d.text((x, y), s, font=f, fill=fill, anchor=anchor)

    def centered(self, cx, cy, s, f, fill, tracking=0.0):
        """Vertically+horizontally centered text (center anchor semantics)."""
        w = f.getlength(s)
        a, dsc = f.getmetrics()
        top = cy - (a - dsc) / 2.0 / self.scale
        self.text((cx - w / 2.0 / self.scale, top - a / self.scale),
                  s, f, fill, tracking, "la")

    def paste(self, layer_img, cx, cy, alpha=1.0):
        """Composite a transparent RGBA layer centered on (cx, cy)."""
        L = layer_img
        if alpha < 1.0:
            L = L.copy()
            L.putalpha(L.getchannel("A").point(lambda v: int(v * alpha)))
        w, h = L.size
        self.img.alpha_composite(L, (int(round(cx * self.scale)) - w // 2,
                                     int(round(cy * self.scale)) - h // 2))

    def crop(self, box):
        return self.img.crop([self.S(box[0]), self.S(box[1]),
                              self.S(box[2]), self.S(box[3])])

    def to_rgb(self):
        out = self.img.convert("RGB")
        if self.scale != 1:
            out = out.resize((self.W, self.H), Image.LANCZOS)
        return out

def layer(w, h, scale=2):
    """New transparent RGBA layer, logical w x h, supersampled by scale."""
    return Image.new("RGBA", (int(round(w * scale)), int(round(h * scale))),
                     (0, 0, 0, 0))

def place(layer_img, scale=1.0, rot=0.0, alpha=1.0):
    """Return a transformed copy of an RGBA layer (no canvas attach)."""
    img = layer_img
    if scale != 1.0:
        w, h = img.size
        img = img.resize((max(1, int(round(w * scale))),
                          max(1, int(round(h * scale)))), Image.LANCZOS)
    if rot:
        img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1.0:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * alpha)))
    return img

# --------------------------------------------------------------------------
# draw helpers (all take a PIL ImageDraw on an RGBA layer, logical coords)
# --------------------------------------------------------------------------
def _d_scale(d, scale):
    return scale

def _pts_scaled(pts, scale):
    return [(x * scale, y * scale) for (x, y) in pts]

def rrect_pts(x0, y0, x1, y1, r, step=10):
    """Polyline around a rounded rectangle (for draw-on strokes)."""
    pts = []
    n = max(2, int(step))
    for i in range(n + 1):  # top edge (left->right)
        th = math.pi + math.pi * i / n
        pts.append((x1 - r + r * math.cos(th), y0 + r - r * math.sin(th)))
    for i in range(n + 1):  # right edge
        th = -math.pi / 2 + math.pi * i / n
        pts.append((x1 - r + r * math.cos(th), y1 - r - r * math.sin(th)))
    for i in range(n + 1):  # bottom edge
        th = 0 + math.pi * i / n
        pts.append((x0 + r + r * math.cos(th), y1 - r - r * math.sin(th)))
    for i in range(n + 1):  # left edge
        th = math.pi / 2 + math.pi * i / n
        pts.append((x0 + r + r * math.cos(th), y0 + r - r * math.sin(th)))
    return pts

def _cum_len(pts):
    cum, tot = [0.0], 0.0
    for i in range(len(pts) - 1):
        dx, dy = pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]
        tot += math.hypot(dx, dy)
        cum.append(tot)
    return cum, tot

def draw_on(d, pts, p, fill, width, scale=2):
    """Draw the first p (0..1) of a polyline, growing end = current tip."""
    if p <= 0:
        return
    sp = _pts_scaled(pts, scale)
    cum, tot = _cum_len(sp)
    target = p * tot
    # full segments
    drawn = 0.0
    for i in range(1, len(sp)):
        if cum[i] <= target:
            d.line([sp[i - 1], sp[i]], fill=fill,
                   width=max(1, int(round(width * scale))), joint="curve")
            drawn = cum[i]
        else:
            break
    # partial final segment
    idx = 0
    for i in range(1, len(sp)):
        if cum[i] > target:
            idx = i; break
    if idx > 0 and cum[idx] > drawn:
        frac = (target - cum[idx - 1]) / max(1e-9, cum[idx] - cum[idx - 1])
        x = sp[idx - 1][0] + (sp[idx][0] - sp[idx - 1][0]) * frac
        y = sp[idx - 1][1] + (sp[idx][1] - sp[idx - 1][1]) * frac
        d.line([sp[idx - 1], (x, y)], fill=fill,
               width=max(1, int(round(width * scale))), joint="curve")

def text_centered(d, cx, cy, s, f, fill, tracking=0.0, scale=2):
    w = f.getlength(s) / scale
    a, dsc = f.getmetrics()
    top = cy - (a - dsc) / 2.0 / scale
    if tracking:
        step = tracking * (f.size / scale)
        x = cx - w / 2.0
        for ch in s:
            d.text((x * scale, top * scale), ch, font=f, fill=fill, anchor="la")
            x += f.getlength(ch) / scale + step
    else:
        d.text(((cx - w / 2.0) * scale, top * scale), s, font=f,
               fill=fill, anchor="la")

def draw_bean_layer(w, scale=2, face=True, eye_open=1.0, fill=PEACH,
                    outline=None, owidth=4, tilt=-7.0, arm_angle=None,
                    arm_scale=1.0):
    """Bean on its own layer (center 0,0), optional waving arm at right."""
    pad = int(w * 0.55)
    L = layer(w + 2 * pad, w + 2 * pad, scale)
    d = ImageDraw.Draw(L)
    cx = (w / 2.0 + pad)
    cy = cx
    pts = _os.bean_pts(w)
    x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts)
    y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)
    cx0, cy0 = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    pts = [(px - cx0 + cx, py - cy0 + cy) for (px, py) in pts]
    pts = _os.rotate_pts(pts, tilt, cx, cy)
    d.polygon([(x * scale, y * scale) for (x, y) in pts], fill=fill,
              outline=outline, width=max(1, int(round(owidth * scale))))
    if face:
        r = w * 0.075
        dx = w * 0.155
        dy = -w * 0.045
        eh = r * 2 * eye_open  # blink: eyes squash to a line
        for sgn in (-1, 1):
            d.ellipse([(cx + sgn * dx - r) * scale, (cy + dy - eh / 2) * scale,
                       (cx + sgn * dx + r) * scale, (cy + dy + eh / 2) * scale],
                      fill=PINE)
        sm_cx, sm_cy = cx, cy + w * 0.16
        sm_rx, sm_ry = w * 0.155, w * 0.10
        pts2 = [(sm_cx + sm_rx * math.cos(t), sm_cy - sm_ry * math.sin(t))
                for i in range(17) for t in
                [math.radians(200 + 140 * i / 16.0)]]
        d.line([(x * scale, y * scale) for (x, y) in pts2], fill=PINE,
               width=max(2, int(w * 0.035 * scale)), joint="curve")
    if arm_angle is not None:
        # arm: peach rounded bar rotating around a pivot at the bean's right
        ax = cx + w * 0.30
        ay = cy + w * 0.02
        al, aw2 = w * 0.34, w * 0.085
        arm = layer(int(al * 1.6), int(aw2 * 3.2), scale)
        ad = ImageDraw.Draw(arm)
        arm_cx, arm_cy = arm.size[0] / 2.0, arm.size[1] / 2.0
        ad.rounded_rectangle(
            [(arm_cx - al * scale / 2, arm_cy - aw2 * scale / 2),
             (arm_cx + al * scale / 2, arm_cy + aw2 * scale / 2)],
            radius=aw2 * scale / 2, fill=fill)
        # hand dot at arm end
        hx, hy = arm_cx + al * scale / 2, arm_cy
        ad.ellipse([hx - aw2 * scale * 0.72, hy - aw2 * scale * 0.72,
                    hx + aw2 * scale * 0.72, hy + aw2 * scale * 0.72],
                   fill=fill)
        arm = arm.rotate(arm_angle, resample=Image.BICUBIC, expand=True)
        L.paste(arm, (int(ax * scale - arm.size[0] / 2),
                      int(ay * scale - arm.size[1] / 2)), arm)
    return L

# --------------------------------------------------------------------------
# reusable elements (each returns an RGBA layer, drawn centered at 0,0)
# --------------------------------------------------------------------------
def draw_book(w, scale=2, face=True):
    """Decodable storybook: butter cover, cream pages, cat face w/ dot eyes."""
    h = w * 0.78
    pad = int(w * 0.35)
    L = layer(w + 2 * pad, h + 2 * pad, scale)
    d = ImageDraw.Draw(L)
    cx = (w + 2 * pad) / 2.0
    cy = (h + 2 * pad) / 2.0
    x0, y0 = cx - w / 2.0, cy - h / 2.0
    # cream page block (a bit taller on the right: slightly open)
    d.rounded_rectangle([(x0 + w * 0.06) * scale, (y0 + h * 0.05) * scale,
                         (x0 + w * 0.97) * scale, (y0 + h * 0.95) * scale],
                        radius=w * 0.04 * scale, fill=WHITE,
                        outline=PINE, width=max(1, int(round(3 * scale))))
    d.line([(x0 + w * 0.90) * scale, (y0 + h * 0.05) * scale,
            (x0 + w * 0.90) * scale, (y0 + h * 0.95) * scale],
           fill=RULE, width=max(1, int(round(3 * scale))))
    # cover
    d.rounded_rectangle([(x0 - w * 0.06) * scale, (y0 + h * 0.04) * scale,
                         (x0 + w * 0.80) * scale, (y0 + h * 0.96) * scale],
                        radius=w * 0.045 * scale, fill=BUTTER,
                        outline=PINE, width=max(1, int(round(6 * scale))))
    # spine
    d.line([(x0 + w * 0.10) * scale, (y0 + h * 0.06) * scale,
            (x0 + w * 0.10) * scale, (y0 + h * 0.94) * scale],
           fill=PINE, width=max(1, int(round(3.5 * scale))))
    if face:
        # tiny butter cat: ears + dot eyes
        fx = x0 + w * 0.24
        fy = y0 + h * 0.55
        fr = w * 0.14
        d.ellipse([(fx - fr) * scale, (fy - fr) * scale,
                   (fx + fr) * scale, (fy + fr) * scale],
                  fill=CREAM, outline=PINE, width=3 * scale)
        er = fr * 0.14
        for sgn in (-1, 1):
            d.ellipse([(fx + sgn * fr * 0.45 - er) * scale,
                       (fy - er) * scale,
                       (fx + sgn * fr * 0.45 + er) * scale,
                       (fy + er) * scale], fill=PINE)
        d.arc([(fx - fr * 0.55) * scale, (fy - fr * 0.35) * scale,
               (fx + fr * 0.55) * scale, (fy + fr * 0.85) * scale],
              200, 340, fill=PINE, width=2 * scale)
        for sgn in (-1, 1):  # ears
            ex = fx + sgn * fr * 0.62
            ey = fy - fr * 0.95
            d.polygon([(ex * scale, (ey + fr * 0.7) * scale),
                       ((ex - sgn * fr * 0.42) * scale, ey * scale),
                       ((ex + sgn * fr * 0.10) * scale, ey * scale)],
                      fill=BUTTER, outline=PINE)
    return L

def draw_result_card(w=220, h=120, scale=2, fill=WHITE):
    pad = 60
    L = layer(w + 2 * pad, h + 2 * pad, scale)
    d = ImageDraw.Draw(L)
    cx, cy = (w + 2 * pad) / 2.0, (h + 2 * pad) / 2.0
    x0, y0 = cx - w / 2.0, cy - h / 2.0
    d.rounded_rectangle([x0 * scale, y0 * scale, (x0 + w) * scale,
                         (y0 + h) * scale], radius=18 * scale, fill=fill,
                        outline=PINE, width=4 * scale)
    d.line([(x0 + 20) * scale, (y0 + 34) * scale,
            (x0 + w - 20) * scale, (y0 + 34) * scale],
           fill=RULE, width=3 * scale)
    return L

def draw_calendar(w=200, h=150, scale=2):
    pad = 60
    L = layer(w + 2 * pad, h + 2 * pad, scale)
    d = ImageDraw.Draw(L)
    cx, cy = (w + 2 * pad) / 2.0, (h + 2 * pad) / 2.0
    x0, y0 = cx - w / 2.0, cy - h / 2.0
    d.rounded_rectangle([x0 * scale, y0 * scale, (x0 + w) * scale,
                         (y0 + h) * scale], radius=16 * scale, fill=WHITE,
                        outline=PINE, width=4 * scale)
    d.rounded_rectangle([x0 * scale, y0 * scale, (x0 + w) * scale,
                         (y0 + 40) * scale], radius=16 * scale, fill=MINT)
    # binder rings
    for i in (-1, 0, 1):
        rx = cx + i * w * 0.22
        d.ellipse([(rx - 5) * scale, (y0 - 10) * scale,
                   (rx + 5) * scale, (y0 + 10) * scale],
                  outline=PINE, width=3 * scale)
    # three repeating $ chips
    for i in (-1, 0, 1):
        chx = cx + i * w * 0.24
        d.rounded_rectangle([(chx - 22) * scale, (y0 + 60) * scale,
                             (chx + 22) * scale, (y0 + 100) * scale],
                            radius=8 * scale, fill=PALEMINT,
                            outline=PINE, width=2 * scale)
        f = font("DMSans-700.ttf", 20 * scale)
        text_centered(d, chx, y0 + 80, "$", f, PINE, 0.0, scale)
    return L

def draw_check(w, scale=2, fill=ORANGE):
    pad = int(w * 0.9)
    L = layer(w + pad, w + pad, scale)
    d = ImageDraw.Draw(L)
    cx = (w + pad) / 2.0
    cy = cx
    pts = [(cx - w * 0.42, cy + w * 0.02), (cx - w * 0.10, cy + w * 0.40),
           (cx + w * 0.46, cy - w * 0.40)]
    d.line([(x * scale, y * scale) for (x, y) in pts], fill=fill,
           width=max(2, int(round(w * 0.13 * scale))), joint="curve")
    return L

def draw_sparkle(r, scale=2, fill=ORANGE):
    pad = int(r * 1.6)
    L = layer(2 * r + pad, 2 * r + pad, scale)
    d = ImageDraw.Draw(L)
    cx = r + pad / 2.0
    cy = cx
    pts = [(cx, cy - r), (cx + r * 0.22, cy - r * 0.22), (cx + r, cy),
           (cx + r * 0.22, cy + r * 0.22), (cx, cy + r),
           (cx - r * 0.22, cy + r * 0.22), (cx - r, cy),
           (cx - r * 0.22, cy - r * 0.22)]
    d.polygon([(x * scale, y * scale) for (x, y) in pts], fill=fill)
    return L

def draw_tile(w, h, fill, scale=2):
    pad = 40
    L = layer(w + 2 * pad, h + 2 * pad, scale)
    d = ImageDraw.Draw(L)
    cx, cy = (w + 2 * pad) / 2.0, (h + 2 * pad) / 2.0
    x0, y0 = cx - w / 2.0, cy - h / 2.0
    d.rounded_rectangle([x0 * scale, y0 * scale, (x0 + w) * scale,
                         (y0 + h) * scale], radius=22 * scale, fill=fill)
    return L

def price_pill(text, scale=2, fill=ORANGE):
    f = font("Fraunces-800.ttf", 64 * scale)
    w = f.getlength(text) / scale
    padx, h = 46, 92
    L = layer(int(w + 2 * padx), h + 60, scale)
    d = ImageDraw.Draw(L)
    cx = (w + 2 * padx) / 2.0
    cy = (h + 60) / 2.0
    d.rounded_rectangle([(cx - w / 2.0 - padx) * scale,
                         (cy - h / 2.0) * scale,
                         (cx + w / 2.0 + padx) * scale,
                         (cy + h / 2.0) * scale],
                        radius=(h / 2.0) * scale, fill=fill)
    text_centered(d, cx, cy, text, f, CREAM, 0.0, scale)
    return L

def chip_pill(text, scale=2, fill=WHITE, tfill=PINE, outline=None, size=30):
    f = font("DMSans-700.ttf", size * scale)
    w = f.getlength(text) / scale
    padx, h = 34, 64
    L = layer(int(w + 2 * padx), h + 40, scale)
    d = ImageDraw.Draw(L)
    cx = (w + 2 * padx) / 2.0
    cy = (h + 40) / 2.0
    d.rounded_rectangle([(cx - w / 2.0 - padx) * scale,
                         (cy - h / 2.0) * scale,
                         (cx + w / 2.0 + padx) * scale,
                         (cy + h / 2.0) * scale],
                        radius=(h / 2.0) * scale, fill=fill, outline=outline,
                        width=3 * scale if outline else 0)
    text_centered(d, cx, cy, text, f, tfill, 0.0, scale)
    return L

def text_line_layer(s, fname, size, scale=2, fill=PINE, tracking=0.0):
    f = font(fname, size * scale)
    w = f.getlength(s) / scale
    a, dsc = f.getmetrics()
    L = layer(int(w + 80), int((a + dsc) / scale + 80), scale)
    d = ImageDraw.Draw(L)
    cx = L.size[0] / 2.0 / scale
    cy = L.size[1] / 2.0 / scale
    if tracking:
        step = tracking * (f.size / scale)
        x = cx - w / 2.0
        for ch in s:
            d.text((x * scale, (cy - (a - dsc) / 2.0 / scale) * scale), ch,
                   font=f, fill=fill, anchor="lm")
            x += f.getlength(ch) / scale + step
    else:
        text_centered(d, cx, cy, s, f, fill, 0.0, scale)
    return L

# --------------------------------------------------------------------------
# ffmpeg encode
# --------------------------------------------------------------------------
def encode_mp4(frames_rgb_iter, out_path, W, H, fps=30, crf=18):
    """Pipe RGB24 frames into ffmpeg -> H.264 MP4 (deterministic content)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    log = tempfile.NamedTemporaryFile(suffix=".log", delete=False).name
    with open(log, "wb") as errf:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL, stderr=errf)
        for img in frames_rgb_iter:
            proc.stdin.write(img.tobytes())
        proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        with open(log) as fh:
            raise RuntimeError(f"ffmpeg failed ({rc}): {fh.read()}")
    os.unlink(log)
    return out_path

def encode_gif(mp4_path, out_path, fps=12, width_cap=640):
    """Two-pass palette GIF from the MP4, capped width, 12fps default."""
    log = tempfile.NamedTemporaryFile(suffix=".log", delete=False).name
    pal = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    try:
        sc = f"scale='min({width_cap},iw)':-2:flags=lanczos"
        gen = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", mp4_path,
             "-vf", f"fps={fps},{sc},palettegen=stats_mode=diff", pal],
            stdout=subprocess.DEVNULL, stderr=open(log, "wb"))
        use = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", mp4_path,
             "-i", pal, "-lavfi",
             f"fps={fps},{sc}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4",
             out_path],
            stdout=subprocess.DEVNULL, stderr=open(log, "ab"))
        if gen.returncode != 0 or use.returncode != 0:
            with open(log) as fh:
                raise RuntimeError(f"gif encode failed: {fh.read()}")
    finally:
        for f in (log, pal):
            try: os.unlink(f)
            except OSError: pass
    return out_path

def ffprobe(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", path])
    return json.loads(out)

def verify_mp4(path):
    info = ffprobe(path)
    vs = [s for s in info["streams"] if s["codec_type"] == "video"][0]
    return {
        "path": path,
        "duration": float(info["format"].get("duration", 0)),
        "width": vs["width"], "height": vs["height"],
        "fps": eval(vs.get("avg_frame_rate", "0/1")),
        "frames": vs.get("nb_frames"),
        "codec": vs["codec_name"],
    }

# --------------------------------------------------------------------------
# palette census (brand-color verification)
# --------------------------------------------------------------------------
BRAND = {
    "cream": CREAM, "pine": PINE, "mint": MINT, "orange": ORANGE,
    "peach": PEACH, "white": WHITE, "sky": SKY, "butter": BUTTER,
    "muted": MUTED, "muted2": MUTED2, "rule": RULE, "mintdeep": MINTDEEP,
    "cream_warm": CREAM_W,
}
def near(c1, c2, tol=14):
    return all(abs(a - b) <= tol for a, b in zip(c1, c2))

def palette_census(img, tol=6, sample_step=1):
    """Share of pixels per brand color (sampled). Returns dict."""
    px = img.convert("RGB")
    w, h = px.size
    counts = {k: 0 for k in BRAND}
    other = 0
    total = 0
    for y in range(0, h, sample_step):
        row = px.load()
        for x in range(0, w, sample_step):
            total += 1
            c = row[x, y]
            matched = False
            for k, bc in BRAND.items():
                if near(c, bc, tol):
                    counts[k] += 1; matched = True; break
            if not matched:
                other += 1
    shares = {k: v / total for k, v in counts.items()}
    shares["other"] = other / total
    return shares

def census_report(img, label=""):
    s = palette_census(img)
    colored = 1 - s["cream"] - s["cream_warm"]
    lines = [f"-- palette census {label}",
             f"  cream {s['cream']+s['cream_warm']:.1%}  pine {s['pine']:.1%}"
             f"  mint {s['mint']:.1%}  orange {s['orange']:.1%}"
             f"  peach {s['peach']:.1%}  white {s['white']:.1%}"
             f"  other {s['other']:.1%}"]
    lines.append(f"  orange/colored {s['orange']/max(colored,1e-6):.1%}"
                 f" (target <=5%)  cream-dominant {s['cream']+s['cream_warm'] >= 0.4}")
    return "\n".join(lines)

# --------------------------------------------------------------------------
# scene functions  —  signature: scene(frame, t, P, L)  (L = loop period)
# --------------------------------------------------------------------------
def scene_mascot_wave(fr, t, P, L):
    W, H = fr.W, fr.H
    S = fr.scale
    # mint field behind
    fr.poly(_os.blob_pts(W * 0.66, H * 0.52, W * 0.20, H * 0.26, 3), MINT)
    # orange accent: tiny sparkle above bean, gentle pulse (periodic)
    sp = draw_sparkle(17, S)
    sp_scale = 1 + 0.22 * osc_loop(t, P, 1, 1.0)
    fr.paste(place(sp, sp_scale), W * 0.74, H * 0.34)
    # bean bounce-in (periodic: invisible at t=0 and t=P -> clean loop)
    bounce = spring_in(t, 0.0, 0.45)
    bw = 150
    arm_angle = None if bounce < 0.02 else 22 + 26 * osc_loop(t, P, 2, 1.0)
    if bounce < 0.02:
        arm_angle = 22.0
    blink = 1.0
    for bt, bd in ((1.45, 0.16), (3.02, 0.16)):
        p = seg(t, bt, bt + bd)
        blink = min(blink, 1 - 0.94 * math.sin(math.pi * p) ** 2)
    bean = draw_bean_layer(bw, S, face=True, eye_open=blink, arm_angle=arm_angle)
    fr.paste(place(bean, bounce), W * 0.60, H * 0.55)
    # pine frame last (on top)
    fr.rrect([24, 24, W - 24, H - 24], 28, outline=PINE, width=9)
    return fr

def scene_comparison_drawon(fr, t, P, L):
    W, H = fr.W, fr.H
    S = fr.scale
    # pastel tints behind panels (muted mint left, soft peach right)
    fr.poly(_os.blob_pts(W * 0.26, H * 0.52, W * 0.20, H * 0.26, 5), PALEMINT)
    fr.poly(_os.blob_pts(W * 0.74, H * 0.52, W * 0.20, H * 0.26, 9), PALEPEACH)
    # eyebrow
    eb = text_line_layer("OMO · PAY PER USE", "DMSans-700.ttf", 22, S,
                         fill=MUTED, tracking=0.12)
    fr.paste(place(eb, alpha=fade_alpha(t, 0.05, 0.35)), W * 0.13, H * 0.13)
    # headline
    h1 = text_line_layer("Subscriptions vs Omo:", "Fraunces-600.ttf", 56, S)
    fr.paste(place(h1, alpha=fade_alpha(t, 0.12, 0.42)), W * 0.5, H * 0.20)
    h2 = text_line_layer("pay per use.", "Fraunces-800.ttf", 68, S)
    fr.paste(place(h2, alpha=fade_alpha(t, 0.20, 0.50)), W * 0.5, H * 0.30)
    # ---- two panels ----
    pwid, phgt, gap = 640, 330, 90
    lx, rx = W * 0.5 - pwid / 2 - gap / 2, W * 0.5 + gap / 2
    py = H * 0.60
    box_l = [lx - pwid / 2, py - phgt / 2, lx + pwid / 2, py + phgt / 2]
    box_r = [rx - pwid / 2, py - phgt / 2, rx + pwid / 2, py + phgt / 2]
    # left panel: fill fade, then pine outline draws on
    fr.rrect(box_l, 24, fill=WHITE + (int(255 * fade_alpha(t, 0.8, 1.15)),))
    dl = fr.d
    draw_on(dl, rrect_pts(*box_l, 24), drawon_progress(t, 1.15, 2.15), PINE, 6, S)
    cal = draw_calendar(210, 155, S)
    fr.paste(place(cal, alpha=fade_alpha(t, 1.5, 1.9),
                   scale=spring_in(t, 1.5, 0.5)), lx, py + 8)
    lab_l = text_line_layer("SUBSCRIPTIONS", "DMSans-700.ttf", 26, S, fill=MUTED,
                            tracking=0.10)
    fr.paste(place(lab_l, alpha=fade_alpha(t, 1.75, 2.05)), lx, py - phgt / 2 + 42)
    line_l = text_line_layer("billed every month", "DMSans-500.ttf", 30, S,
                             fill=MUTED2)
    fr.paste(place(line_l, alpha=fade_alpha(t, 1.95, 2.25)), lx, py + phgt / 2 - 52)
    # right panel
    fr.rrect(box_r, 24, fill=WHITE + (int(255 * fade_alpha(t, 2.5, 2.85)),))
    draw_on(dl, rrect_pts(*box_r, 24), drawon_progress(t, 2.85, 3.85), PINE, 6, S)
    card = draw_result_card(230, 150, S)
    fr.paste(place(card, alpha=fade_alpha(t, 3.0, 3.4)), rx, py - 18)
    lab_r = text_line_layer("OMO", "DMSans-700.ttf", 26, S, fill=PINE,
                            tracking=0.10)
    fr.paste(place(lab_r, alpha=fade_alpha(t, 3.25, 3.55)), rx, py - phgt / 2 + 42)
    val = text_line_layer("pay per run, keep it", "DMSans-500.ttf", 30, S,
                          fill=PINE)
    vp = 1 + 0.10 * pulse(t, 4.4, 0.45, 1.0, 1.0)
    vly = py + phgt / 2 - 52
    fr.paste(place(val, alpha=fade_alpha(t, 3.4, 3.7), scale=vp), rx, vly)
    # "pay per run" emphasis: pine underline draws on
    uw = val.size[0] / S * 0.86
    up = drawon_progress(t, 4.4, 4.85)
    if up > 0:
        x0 = rx - uw / 2
        fr.line((x0, vly + 26), (x0 + uw * up, vly + 26), PINE, 5)
    # orange check pops (the one accent)
    chk = draw_check(70, S)
    fr.paste(place(chk, spring_in(t, 4.45, 0.45)), rx + 92, py - 12)
    # center seam
    fr.rrect([W / 2 - 2, H * 0.42, W / 2 + 2, H * 0.78], 2,
             fill=RULE + (int(255 * fade_alpha(t, 2.2, 2.8)),))
    # CTA
    cta = chip_pill("omo.space", S, fill=WHITE, outline=PINE, size=28)
    fr.paste(place(cta, alpha=fade_alpha(t, 5.15, 5.45)), W * 0.5, H * 0.905)
    fr.rrect([40, 40, W - 40, H - 40], 28, outline=PINE, width=9)
    return fr

def scene_book_maker_pop(fr, t, P, L):
    W, H = fr.W, fr.H
    S = fr.scale
    fr.poly(_os.blob_pts(W * 0.47, H * 0.50, W * 0.30, H * 0.22, 2), PALEMINT)
    eb = text_line_layer("DECODABLE BOOK MAKER", "DMSans-700.ttf", 24, S,
                         fill=MUTED, tracking=0.12)
    fr.paste(place(eb, alpha=fade_alpha(t, 0.1, 0.45)), W * 0.13, H * 0.13)
    # hero book pops (spring)
    book = draw_book(300, S, face=True)
    bx, by = W * 0.42, H * 0.52
    fr.paste(place(book, spring_in(t, 0.45, 0.8)), bx, by)
    # $0.99 orange chip slides in from the right (the one accent)
    pr = price_pill("$0.99", S)
    p_from = W * 1.18
    sl = seg_ease(t, 1.35, 1.9, ease_out_back)
    px = p_from + (bx + 260 - p_from) * sl
    fr.paste(place(pr, alpha=fade_alpha(t, 1.35, 1.7)), px, by - H * 0.09)
    # fact chips
    c1 = chip_pill("4-page phonics PDF", S, fill=MINT, tfill=PINE, size=28)
    fr.paste(place(c1, spring_in(t, 2.1, 0.5)), bx - 130, by + 300)
    c2 = chip_pill("Keep it forever", S, fill=WHITE, tfill=PINE, outline=PINE,
                   size=28)
    fr.paste(place(c2, spring_in(t, 2.45, 0.5)), bx + 150, by + 300)
    ns = text_line_layer("No subscription", "DMSans-500.ttf", 26, S, fill=MUTED2)
    fr.paste(place(ns, alpha=fade_alpha(t, 2.8, 3.05)), bx, by + 360)
    # CTA
    cta = chip_pill("Make your book", S, fill=WHITE, tfill=PINE, outline=PINE,
                    size=30)
    fr.paste(place(cta, spring_in(t, 3.2, 0.5)), W * 0.5, H * 0.90)
    fr.rrect([40, 40, W - 40, H - 40], 28, outline=PINE, width=9)
    return fr

def scene_tagline_loop(fr, t, P, L):
    W, H = fr.W, fr.H
    S = fr.scale
    # words breathe: staggered fade-in + upward drift, reverse-fade near P
    lines = [("Buy the result,", "Fraunces-600.ttf", 104, 590),
             ("not another", "Fraunces-600.ttf", 104, 740),
             ("subscription.", "Fraunces-800.ttf", 118, 900)]
    for i, (s, fn, sz, y) in enumerate(lines):
        t_in = 0.0 + i * 0.13
        a = min(fade_alpha(t, t_in, t_in + 0.35),
                fade_alpha(t, 4.35, 4.97, out=True))
        dy = 24 * (1 - fade_alpha(t, t_in, t_in + 0.35)) - 24 * fade_alpha(
            t, 4.35, 4.97, out=True)
        lay = text_line_layer(s, fn, sz, S)
        fr.paste(place(lay, alpha=a), W * 0.5, y + dy)
    # orange strike on "subscription." — draws on, then off, loop-clean
    st = 0.5
    prog = drawon_progress(t, st, st + 0.55) * fade_alpha(t, 4.3, 4.93, out=True)
    if prog > 0.01:
        lang = font("Fraunces-800.ttf", 118 * S).getlength("subscription.") / S
        x0 = W / 2 - lang / 2
        y0 = 900 + 34
        fr.line((x0 - 8, y0), (x0 - 8 + (lang + 16) * prog, y0), ORANGE, 8)
    # bean nods (periodic, returns to rest at t=0 and t=P), one blink
    nod = 0.0
    if 2.9 <= t <= 4.3:
        nod = 8 * math.sin(2 * math.pi * 2 * (t - 2.9) / 1.4)
    blink = 1.0
    p = seg(t, 3.95, 4.11)
    blink = 1 - 0.94 * math.sin(math.pi * p) ** 2
    bean = draw_bean_layer(215, S, face=True, eye_open=blink, arm_angle=None)
    fr.paste(place(bean, rot=-7 + nod), W * 0.5, H * 0.74)
    # omo.space (static: present at t=0 and t=P)
    os_ = text_line_layer("omo.space", "DMSans-500.ttf", 34, S, fill=MUTED)
    fr.paste(os_, W * 0.5, H * 0.90)
    fr.rrect([52, 52, W - 52, H - 52], 40, outline=PINE, width=9)
    return fr

def scene_phonics_bounce(fr, t, P, L):
    W, H = fr.W, fr.H
    S = fr.scale
    eb = text_line_layer("PHONICSMAKER · EDUCATION", "DMSans-700.ttf", 26, S,
                         fill=MUTED, tracking=0.12)
    fr.paste(place(eb, alpha=fade_alpha(t, 0.1, 0.4)), W * 0.5, H * 0.12)
    h1 = text_line_layer("9 phonics tools.", "Fraunces-600.ttf", 78, S)
    fr.paste(place(h1, alpha=fade_alpha(t, 0.15, 0.5)), W * 0.5, H * 0.21)
    # 3x3 tile grid, bounce in sequence (diagonal wave)
    tw, th, gap = 250, 170, 28
    x0 = W / 2 - (3 * tw + 2 * gap) / 2
    y0 = H * 0.52 - th / 2
    fills = [MINT, BUTTER, SKY, PEACH, MINT, BUTTER, SKY, PEACH, MINT]
    named = {0: "Decodable sentences", 4: "Syllable splitter",
             8: "Phoneme counter"}
    for k in range(9):
        i, j = k % 3, k // 3
        cx, cy = x0 + i * (tw + gap) + tw / 2, y0 + j * (th + gap) + th / 2
        t0 = 0.5 + (i + j) * 0.14
        sc = spring_in(t, t0, 0.45)
        if sc <= 0.01:
            continue
        tile = draw_tile(tw, th, fills[k], S)
        ft = font("Fraunces-800.ttf", 60 * S)
        w0, h0 = tile.size
        d = ImageDraw.Draw(tile)
        text_centered(d, w0 / 2 / S, th * 0.30, str(k + 1), ft, PINE, 0.0, S)
        nm = named.get(k)
        if nm:
            nf = font("DMSans-700.ttf", 24 * S)
            text_centered(d, w0 / 2 / S, th * 0.72, nm, nf, PINE, 0.0, S)
        fr.paste(place(tile, sc), cx, cy)
    # headline 2: $0.10 per run. — $0.10 is the one orange accent
    h2a = text_line_layer("$0.10", "Fraunces-800.ttf", 88, S, fill=ORANGE)
    h2b = text_line_layer(" per run.", "Fraunces-600.ttf", 72, S)
    a2 = fade_alpha(t, 2.6, 3.0)
    wa = h2a.size[0] / S
    gap2 = 8
    xa = W / 2 - (wa + gap2 + h2b.size[0] / S) / 2
    fr.paste(place(h2a, alpha=a2), xa + wa / 2, H * 0.80)
    fr.paste(place(h2b, alpha=a2), xa + wa + gap2 + h2b.size[0] / S / 2,
             H * 0.80)
    cta = chip_pill("omo.space", S, fill=WHITE, outline=PINE, size=28)
    fr.paste(place(cta, alpha=fade_alpha(t, 3.3, 3.6)), W * 0.5, H * 0.915)
    fr.rrect([42, 42, W - 42, H - 42], 36, outline=PINE, width=9)
    return fr

# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------
CLIPS = {
    "mascot-wave": dict(scene=scene_mascot_wave, W=640, H=360, dur=4.0,
                        fps=30, loop=True, scale=2),
    "comparison-drawon": dict(scene=scene_comparison_drawon, W=1600, H=900,
                              dur=6.0, fps=30, loop=False, scale=2),
    "book-maker-pop": dict(scene=scene_book_maker_pop, W=1600, H=900,
                           dur=5.0, fps=30, loop=False, scale=2),
    "tagline-loop": dict(scene=scene_tagline_loop, W=1080, H=1920, dur=5.0,
                         fps=30, loop=True, scale=2),
    "phonics-bounce": dict(scene=scene_phonics_bounce, W=1254, H=1254,
                           dur=4.0, fps=30, loop=False, scale=2),
}

def render_clip(name, out_prefix=None, fps=None, scale=None, progress=True):
    cfg = dict(CLIPS[name])
    if fps: cfg["fps"] = fps
    if scale: cfg["scale"] = scale
    W, H, dur = cfg["W"], cfg["H"], cfg["dur"]
    S = cfg["scale"]
    N = int(round(dur * cfg["fps"]))
    P = (N - 1) / cfg["fps"] if cfg["loop"] else dur

    def frames():
        for k in range(N):
            t = k / cfg["fps"]
            if cfg["loop"]:
                t = wrap(t, P)
            fr = Frame(W, H, S, CREAM)
            fr.F = t
            cfg["scene"](fr, t, P, cfg["loop"])
            yield fr.to_rgb()
            if progress and (k % 15 == 0 or k == N - 1):
                sys.stderr.write(f"  frame {k+1}/{N} (t={t:.2f})\n")
    out_prefix = out_prefix or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), name)
    mp4 = encode_mp4(frames(), out_prefix + ".mp4", W, H, cfg["fps"])
    return mp4

def frame_at(name, k=0):
    """Render a single frame as an RGB image (for inspection)."""
    cfg = CLIPS[name]
    N = int(round(cfg["dur"] * cfg["fps"]))
    P = (N - 1) / cfg["fps"] if cfg["loop"] else cfg["dur"]
    t = wrap(k / cfg["fps"], P) if cfg["loop"] else k / cfg["fps"]
    fr = Frame(cfg["W"], cfg["H"], cfg["scale"], CREAM)
    fr.F = t
    cfg["scene"](fr, t, P, cfg["loop"])
    return fr.to_rgb()

def main(argv):
    if "--list" in argv:
        for k, v in CLIPS.items():
            print(f"{k:20s} {v['W']}x{v['H']} {v['dur']}s @{v['fps']}fps"
                  f" loop={v['loop']}")
        return 0
    name = argv[0]
    if name not in CLIPS:
        print(f"unknown clip {name!r}; use --list", file=sys.stderr)
        return 2
    if "--frames" in argv:
        import glob
        idx = [int(a) for a in argv if a.isdigit()]
        ks = idx or [0, 1, 2]
        imgs = [frame_at(name, k) for k in ks[:16]]
        mont = Image.new("RGB", (imgs[0].size[0], imgs[0].size[1] * len(imgs)))
        y = 0
        for im in imgs:
            mont.paste(im, (0, y)); y += im.size[1]
        out = f"/tmp/{name}-probe.png"
        mont.save(out)
        print("saved probe montage:", out)
        return 0
    fps = None; scale = None; no_gif = False
    for a in argv[1:]:
        if a.startswith("--fps="): fps = int(a.split("=")[1])
        elif a.startswith("--scale="): scale = int(a.split("=")[1])
        elif a == "--no-gif": no_gif = True
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    print(f"rendering {name} ...")
    mp4 = render_clip(name, out_prefix=base, fps=fps, scale=scale)
    print("encoded:", mp4)
    v = verify_mp4(mp4)
    print(f"ffprobe: {v['duration']:.3f}s {v['width']}x{v['height']} "
          f"{v['fps']:.3f}fps {v['codec']}")
    if not no_gif:
        gif = encode_gif(mp4, base + ".gif")
        print("encoded:", gif)
        gv = verify_mp4(gif)
        print(f"ffprobe: {gv['duration']:.3f}s {gv['width']}x{gv['height']} "
              f"{gv['fps']:.3f}fps")
    # palette census on a mid+late frame
    N = round(CLIPS[name]["dur"] * CLIPS[name]["fps"])
    for k in (int(0.5 * N), int(0.9 * N)):
        im = frame_at(name, k)
        print(census_report(im, f"{name} k={k}"))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))