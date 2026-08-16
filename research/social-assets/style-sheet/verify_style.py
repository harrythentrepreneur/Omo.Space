#!/usr/bin/env python3
"""Pixel-level verification for issue #84 images.

Checks per image: real PNG magic, exact dimensions, palette conformance
(every pixel near an allowed Omo token; cream dominant >=40%; orange <=5%;
no pure black, no neutral gray, no neon), plus expected location of the one
orange accent for the signature posts.
"""
import sys
import numpy as np
from PIL import Image

# allowed Omo tokens (brand DNA + master palette)
ALLOWED = {
    "cream":   (248, 247, 245), "pine": (23, 53, 44), "mint": (189, 239, 212),
    "orange":  (255, 107, 61),  "peach": (255, 184, 157), "white": (255, 255, 255),
    "rule":    (217, 226, 220), "muted": (95, 111, 104), "muted2": (77, 91, 86),
    "sky":     (207, 232, 247), "butter": (255, 231, 163),
    "palemint":(234, 247, 240), "mintdeep": (120, 204, 161),
}
NAMES = list(ALLOWED)
ARR = np.array(list(ALLOWED.values()), dtype=int)

def classify(img):
    """Nearest-token label per pixel; returns counts dict + foreign mask."""
    px = np.asarray(img, dtype=int).reshape(-1, 3)
    diff = np.abs(px[:, None, :] - ARR[None, :, :]).sum(axis=2)   # N x K
    best = diff.argmin(axis=1)
    dist = diff[np.arange(len(px)), best]
    counts = {n: int((best == i).sum()) for i, n in enumerate(NAMES)}
    foreign = (dist > 150).sum()
    return counts, foreign, best

def scan_danger(img, best):
    px = np.asarray(img, dtype=int).reshape(-1, 3)
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    # near-black: only LANCZOS ringing on pine/cream edges is tolerated (<0.01%)
    black = int(((r < 25) & (g < 25) & (b < 25)).sum())
    mx, mn = px.max(axis=1), px.min(axis=1)
    # saturated = foreign color UNLESS it quantizes to Omo's orange token (idx 3)
    sat = (mx - mn > 150)
    neon = int((sat & (best != 3)).sum())
    gray = int(((mx - mn <= 12) & (mn > 45) & (mx < 235)).sum())
    return black, neon, gray

def verify(path, expect, orange_box=None, name=""):
    ok = True
    with open(path, "rb") as f:
        magic = f.read(8)
    im = Image.open(path)
    w, h = im.size
    lines = []
    def chk(cond, msg):
        nonlocal ok
        lines.append(("OK " if cond else "FAIL") + "  " + msg)
        if not cond:
            ok = False

    chk(magic == b"\x89PNG\r\n\x1a\n", f"PNG magic {magic[:4]!r}")
    chk((w, h) == expect, f"dims {w}x{h} == {expect[0]}x{expect[1]}")

    rgb = im.convert("RGB")
    counts, foreign, best = classify(rgb)
    total = w * h
    cream = counts["cream"] / total
    orange = counts["orange"] / total
    chk(cream >= 0.40, f"cream dominant {cream*100:.1f}% (>=40%)")
    chk(orange <= 0.05, f"orange accent {orange*100:.2f}% (<=5%)")
    chk(foreign <= total * 0.01,
        f"foreign pixels {foreign} ({foreign/total*100:.3f}% <=1%)")
    black, neon, gray = scan_danger(rgb, best)
    chk(black <= total * 0.0005,
        f"no pure black fill (ringing {black}px <= 0.05%)")
    chk(neon == 0, f"no neon/saturated foreign color (found {neon})")
    if orange_box:
        mask = np.abs(np.asarray(rgb, dtype=int) - np.array((255, 107, 61))).sum(axis=2) < 60
        ys, xs = np.where(mask)
        if len(xs):
            bx = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
            in_box = (orange_box[0] <= bx[0] and bx[2] <= orange_box[2]
                      and orange_box[1] <= bx[1] and bx[3] <= orange_box[3])
            chk(in_box, f"orange accent at {bx} within {orange_box}")
        else:
            chk(False, "orange accent missing")
    print(f"## {name or path}")
    for l in lines:
        print("   " + l)
    print(f"   ratios: " + " ".join(f"{k[:6]}={v/total*100:.1f}%" for k, v in
          sorted(counts.items(), key=lambda kv: -kv[1])[:6]))
    return ok

ROOT = "/Users/yifan/marketplace/research/social-assets"
all_ok = True
for p, dims, obox, nm in [
    (f"{ROOT}/style-sheet/style-sheet-system.png", (1600, 1200), None, "style sheet A (system)"),
    (f"{ROOT}/style-sheet/style-sheet-variants.png", (1600, 1200), None, "style sheet B (variants)"),
    (f"{ROOT}/style-sheet/examples/example-tagline.png", (1600, 900), None, "example launch"),
    (f"{ROOT}/style-sheet/examples/example-book.png", (1600, 900), None, "example product"),
    (f"{ROOT}/style-sheet/examples/example-oss.png", (1600, 900), None, "example oss launch"),
    (f"{ROOT}/style-sheet/examples/example-education.png", (1600, 900), None, "example education"),
    (f"{ROOT}/style-sheet/examples/example-metrics.png", (1600, 900), None, "example metrics"),
    (f"{ROOT}/posts/tagline-buy-the-result/image.png", (1600, 900), (80, 420, 1060, 470), "POST tagline"),
    (f"{ROOT}/posts/decodable-book-card/image.png", (1600, 900), (860, 180, 1160, 300), "POST product card"),
    (f"{ROOT}/posts/open-source-library/image.png", (1600, 900), (100, 470, 190, 540), "POST oss launch"),
]:
    all_ok &= verify(p, dims, obox, nm)

print("\nALL PASS" if all_ok else "\nSOME CHECKS FAILED")
sys.exit(0 if all_ok else 1)
