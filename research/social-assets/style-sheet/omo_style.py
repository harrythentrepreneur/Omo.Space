#!/usr/bin/env python3
"""Omo master style render library (issue #84).

Faithful programmatic implementation of research/OMO-IMAGE-STYLE-SYSTEM.MD:
cream canvas, pine 9px frame, 2-3 pastel fields, one orange accent, Fraunces
display + DM Sans body, the -7 deg bean tilt, flat vector only.

All coordinates are LOGICAL (1600x900 / 1600x1200 space); everything is
rendered at 2x and downscaled for crisp flat edges.
"""
import math, os
from PIL import Image, ImageDraw, ImageFont

# ---------------- palette (brand DNA tokens) ----------------
CREAM    = (248, 247, 245)   # #F8F7F5 canvas ~50%
CREAM_W  = (247, 243, 232)   # #F7F3E8 cute register
PINE     = (23, 53, 44)      # #17352C ink ~20%
MINT     = (189, 239, 212)   # #BDEFD4 fields ~12%
ORANGE   = (255, 107, 61)    # #FF6B3D accent <=5%
PEACH    = (255, 184, 157)   # #FFB89D warmth ~5%
WHITE    = (255, 255, 255)   # cards ~8%
RULE     = (217, 226, 220)   # #D9E2DC hairlines
MUTED    = (95, 111, 104)    # #5F6F68 secondary text
MUTED2   = (77, 91, 86)      # #4D5B56 body text
SKY      = (207, 232, 247)   # #CFE8F7
BUTTER   = (255, 231, 163)   # #FFE7A3
LILAC    = (220, 206, 247)   # #DCCEF7
MINTDEEP = (120, 204, 161)   # #78CCA1 data series
PALEMINT = (234, 247, 240)   # #F2F6F1
PALEPEACH= (255, 240, 232)   # #FFF0E8
WARMCRM  = (246, 240, 231)   # #F6F0E7

FDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fonts"))
MENLO = "/System/Library/Fonts/Menlo.ttc"

# ---------------- logo bean path (site/logo-sweet-pastel.svg) ----------------
# M20.28 0 A18.72 15.3 0 0 1 39 15.3 A17.16 18.7 0 0 1 21.84 34 A21.84 14.96
# 0 0 1 0 19.04 A20.28 19.04 0 0 1 20.28 0 Z   (39 wide x 34 tall, y-down)
BEAN_ARCS = [
    (20.28, 0.0,   18.72, 15.3,  39.0, 15.3),
    (39.0,  15.3,  17.16, 18.7,  21.84, 34.0),
    (21.84, 34.0,  21.84, 14.96, 0.0,  19.04),
    (0.0,   19.04, 20.28, 19.04, 20.28, 0.0),
]

def _arc_pts(x1, y1, rx, ry, x2, y2, n=40):
    """SVG arc rx ry 0 0 1 (sweep=1, large=0, phi=0) -> point list."""
    pts = []
    x1p, y1p = (x1 - x2) / 2.0, (y1 - y2) / 2.0
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1:
        s = math.sqrt(lam); rx *= s; ry *= s
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    rad = 0.0 if den == 0 else math.sqrt(max(0.0, num / den))
    cxp = rad * rx * y1p / ry
    cyp = -rad * ry * x1p / rx
    cx, cy = cxp + (x1 + x2) / 2.0, cyp + (y1 + y2) / 2.0
    def ang(u, v): return math.atan2(v, u)
    t1 = ang((x1p - cxp) / rx, (y1p - cyp) / ry)
    t2 = ang((-x1p - cxp) / rx, (-y1p - cyp) / ry)
    dt = (t2 - t1) % (2 * math.pi)
    for i in range(n + 1):
        t = t1 + dt * i / n
        pts.append((cx + rx * math.cos(t), cy + ry * math.sin(t)))
    return pts

def bean_pts(width):
    """Polygon for the logo bean, width px, 39x34 aspect, y-down."""
    s = width / 39.0
    pts = []
    x1, y1 = 20.28, 0.0
    for (ax1, ay1, rx, ry, x2, y2) in BEAN_ARCS:
        pts.extend(_arc_pts(ax1, ay1, rx, ry, x2, y2))
        x1, y1 = x2, y2
    return [(x * s, y * s) for (x, y) in pts]

def rotate_pts(pts, deg, cx, cy):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for (x, y) in pts:
        dx, dy = x - cx, y - cy
        out.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    return out

def blob_pts(cx, cy, rx, ry, seed=1, n=48):
    """Gentle organic field (super-ellipse-ish, no sharp corners)."""
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        r = 1.0 + 0.055 * math.sin(2 * th + seed) + 0.035 * math.sin(3 * th + 2 * seed)
        pts.append((cx + rx * r * math.cos(th), cy + ry * r * math.sin(th)))
    return pts

def star_pts(cx, cy, r, n=5, rot=-90.0):
    pts = []
    for i in range(2 * n):
        rr = r if i % 2 == 0 else r * 0.45
        a = math.radians(rot + i * 180.0 / n)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts

# ---------------- canvas ----------------
class Canvas:
    def __init__(self, W, H, scale=2, fill=CREAM):
        self.W, self.H, self.scale = W, H, scale
        self.img = Image.new("RGB", (W * scale, H * scale), fill)
        self.d = ImageDraw.Draw(self.img)
        self._fcache = {}

    def save(self, path):
        out = self.img if self.scale == 1 else self.img.resize(
            (self.W, self.H), Image.LANCZOS)
        out.save(path)
        return path

    # ---- fonts: logical sizes, cached, scaled internally ----
    def font(self, face, size, weight=None):
        key = (face, size, weight)
        f = self._fcache.get(key)
        if f is not None:
            return f
        px = size * self.scale
        if face == "fraunces":
            path = os.path.join(FDIR, f"Fraunces-{weight}.ttf")
        elif face == "dm":
            path = os.path.join(FDIR, f"DMSans-{weight}.ttf")
        else:  # mono
            path = MENLO
        if face == "mono":
            f = ImageFont.truetype(path, px, index=1 if weight == "bold" else 0)
        else:
            f = ImageFont.truetype(path, px)
        self._fcache[key] = f
        return f

    def measure(self, f, s, tracking=0.0):
        if tracking:
            return sum(f.getlength(c) for c in s) + tracking * (f.size / self.scale) * max(0, len(s) - 1)
        return f.getlength(s)

    # ---- primitives (logical coords) ----
    def _S(self, v):
        return v * self.scale

    def rrect(self, box, radius, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(
            [self._S(box[0]), self._S(box[1]), self._S(box[2]), self._S(box[3])],
            radius=self._S(radius), fill=fill, outline=outline,
            width=max(1, int(round(width * self.scale))))

    def line(self, p0, p1, fill, width):
        self.d.line([self._S(p0[0]), self._S(p0[1]), self._S(p1[0]), self._S(p1[1])],
                    fill=fill, width=max(1, int(round(width * self.scale))),
                    joint="curve")

    def polyline(self, pts, fill, width):
        self.d.line([(self._S(x), self._S(y)) for (x, y) in pts],
                    fill=fill, width=max(1, int(round(width * self.scale))),
                    joint="curve")

    def poly(self, pts, fill, outline=None, width=1):
        self.d.polygon([(self._S(x), self._S(y)) for (x, y) in pts],
                       fill=fill, outline=outline,
                       width=max(1, int(round(width * self.scale))))

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse([self._S(box[0]), self._S(box[1]), self._S(box[2]), self._S(box[3])],
                       fill=fill, outline=outline, width=max(1, int(round(width * self.scale))))

    def text(self, xy, s, f, fill, tracking=0.0, anchor="la"):
        x, y = self._S(xy[0]), self._S(xy[1])
        if tracking:
            step = tracking * (f.size / self.scale)
            for ch in s:
                self.d.text((x, y), ch, font=f, fill=fill, anchor=anchor)
                x += f.getlength(ch) + self._S(step)
        else:
            self.d.text((x, y), s, font=f, fill=fill, anchor=anchor)

    def centered(self, cx, y, s, f, fill, tracking=0.0, anchor="la"):
        """Anchor 'la' (left+ascender top): y is text top. Centers on cx."""
        w = self.measure(f, s, tracking)
        self.text((cx - w / 2.0, y), s, f, fill, tracking, anchor)

    # ---- brand pieces ----
    def frame(self, inset=24, stroke=9, radius=28, color=PINE):
        self.rrect([inset, inset, self.W - inset, self.H - inset],
                   radius=radius, outline=color, width=stroke)

    def pill(self, cx, cy, w, h, fill, text=None, font=None, tfill=PINE,
             tracking=0.02, outline=None, owidth=3):
        self.rrect([cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0],
                   radius=h / 2.0, fill=fill, outline=outline, width=owidth)
        if text and font:
            self.text((cx - self.measure(font, text, tracking) / 2.0, cy),
                      text, font, tfill, tracking, "lm")

    def _ascent(self, f):
        a, d = f.getmetrics()
        return a / self.scale

    def _descent(self, f):
        a, d = f.getmetrics()
        return d / self.scale

    def text_top_center(self, cx, top, s, f, fill, tracking=0.0):
        """Text vertically centered on the 'top' line using ascent/descent."""
        a, d = f.getmetrics()
        self.text((cx - self.measure(f, s, tracking) / 2.0, top - (a / self.scale)),
                  s, f, fill, tracking, "la")

    def bean(self, cx, cy, width, tilt=-7.0, fill=PEACH, face=True,
             dot=PINE, smile=PINE, outline=None, owidth=3):
        pts = bean_pts(width)
        x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts)
        y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)
        cx0, cy0 = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        pts = [(px - cx0 + cx, py - cy0 + cy) for (px, py) in pts]
        pts = rotate_pts(pts, tilt, cx, cy)
        self.poly(pts, fill, outline, owidth)
        if face:
            # dot eyes + smile, proportional to the logo face (pine)
            r = width * 0.075
            dx = width * 0.155
            dy = -width * 0.045
            for sgn in (-1, 1):
                self.ellipse([cx + sgn * dx - r, cy + dy - r,
                              cx + sgn * dx + r, cy + dy + r], fill=dot)
            # smile: arc of an ellipse, drawn as polyline
            sm_cx, sm_cy = cx, cy + width * 0.16
            sm_rx, sm_ry = width * 0.155, width * 0.10
            pts2 = []
            for i in range(17):
                t = math.radians(200 + 140 * i / 16.0)
                pts2.append((sm_cx + sm_rx * math.cos(t), sm_cy - sm_ry * math.sin(t)))
            self.polyline(pts2, smile, max(2, int(width * 0.035)))
        return (min(p[0] for p in pts), min(p[1] for p in pts),
                max(p[0] for p in pts), max(p[1] for p in pts))

    def blob(self, cx, cy, rx, ry, fill, seed=1):
        self.poly(blob_pts(cx, cy, rx, ry, seed), fill)

    def star(self, cx, cy, r, fill, n=5):
        self.poly(star_pts(cx, cy, r, n), fill)

    def check(self, x0, y0, x1, y1, x2, y2, fill, width):
        self.polyline([(x0, y0), (x1, y1), (x2, y2)], fill, width)

    def struck(self, cx, top, s, f, fill, strike=ORANGE, sw=8, pad=14):
        """Centered text with the one orange strike-through."""
        w = self.measure(f, s)
        a, d = f.getmetrics()
        self.text((cx - w / 2.0, top - a / self.scale), s, f, fill, 0.0, "la")
        mid = top + (d - a) / self.scale * 0.15
        self.line((cx - w / 2.0 - pad, mid), (cx + w / 2.0 + pad, mid), strike, sw)
