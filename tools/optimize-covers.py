#!/usr/bin/env python3
"""Optimize marketplace cover thumbnails (the "smart thumbnail" step).

What it does, idempotently:
  1. Converts every site/covers/*.png to lossy WebP (q82, best compression).
     Flat-vector covers shrink ~10-20x; the baked titles stay crisp at card size.
  2. Removes the source .png (git keeps it in history if it was committed).
  3. Rewrites .png -> .webp cover references in site/catalog.js and
     site/run-design-2.html (leaves .jpg/.svg covers alone).
  4. Deletes orphan covers (webp twins whose stem is referenced nowhere).
  5. Verifies every referenced covers/* file actually exists on disk.

Usage:
  python3 tools/optimize-covers.py            # convert + verify
  python3 tools/optimize-covers.py --dry-run  # report only, change nothing

Run this after any batch of `thumb-<slug>-v5.png` files is generated, before
committing, so the repo never carries multi-MB PNGs again.
"""
import argparse, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERS = os.path.join(ROOT, "site", "covers")
REF_FILES = ["site/catalog.js", "site/run-design-2.html"]


def referenced_names():
    """Basenames (with extension) referenced in covers/ paths."""
    names = set()
    for rel in REF_FILES:
        s = open(os.path.join(ROOT, rel)).read()
        for m in re.findall(r'covers/([^"\s<>]+)', s):
            names.add(m.split("/")[-1])
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quality", type=int, default=82)
    args = ap.parse_args()

    pngs = sorted(f for f in os.listdir(COVERS) if f.endswith(".png"))
    png_refs = {n[:-4] for n in referenced_names() if n.endswith(".png")}

    if args.dry_run:
        kept = sum(1 for f in pngs if f[:-4] in png_refs)
        print(f"[dry-run] {len(pngs)} png(s): {kept} kept, "
              f"{len(pngs) - kept} orphan(s) dropped")
        return

    from PIL import Image  # local import; only needed when converting

    kept = removed_orphan = 0
    for f in pngs:
        stem = f[:-4]
        png = os.path.join(COVERS, f)
        webp = os.path.join(COVERS, stem + ".webp")
        im = Image.open(png)
        im = im.convert("RGBA") if im.mode in ("RGBA", "P", "LA") else im.convert("RGB")
        im.save(webp, "WEBP", quality=args.quality, method=6)
        os.remove(png)
        if stem in png_refs:
            kept += 1
        else:
            os.remove(webp)  # orphan
            removed_orphan += 1

    for rel in REF_FILES:
        p = os.path.join(ROOT, rel)
        s = open(p).read()
        n = s.count('.png"')
        if n:
            open(p, "w").write(s.replace('.png"', '.webp"'))
            print(f"  {rel}: {n} refs -> .webp")

    total = sum(os.path.getsize(os.path.join(COVERS, f))
                for f in os.listdir(COVERS) if f.endswith(".webp"))
    missing = [n for n in referenced_names()
               if not os.path.exists(os.path.join(COVERS, n))]
    print(f"{len(pngs)} png -> webp | kept {kept} | orphan removed {removed_orphan}")
    print(f"covers dir now {total/1048576:.1f} MB")
    print(f"MISSING refs: {missing if missing else 'none'}")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
