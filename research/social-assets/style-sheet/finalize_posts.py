#!/usr/bin/env python3
"""Finalize the 3 signature posts (issue #84): render into
research/social-assets/posts/<slug>/ with working/ provenance files."""
import os
from omo_style import PINE, CREAM, ORANGE, MINT, PEACH
from render_variants import render_tagline, render_book_card, render_oss_launch

ROOT = "/Users/yifan/marketplace/research/social-assets/posts"

POSTS = [
    ("tagline-buy-the-result", render_tagline, {
        "audience": "Creator-economy buyers tired of monthly software bills.",
        "takeaway": "On Omo you pay for the finished result, not for software you rent.",
        "layout": "master style — launch variant (masthead: eyebrow, 3-line Fraunces headline, one orange strike on the anti-lock-in word, CTA pill)",
        "headline": "Buy the result, / not another / subscription. (subscription. struck through in orange — the single accent)",
        "on_image": "OMO · THE RESULT MARKETPLACE / Buy the result, / not another / subscription. / Workflows, not rentals. / omo.space",
        "source": "Tagline from site/index.html ('…not another subscription.'); 'Buy the result, not another subscription.' is the brand one-liner in research/BRAND-DNA.MD.",
    }),
    ("decodable-book-card", render_book_card, {
        "audience": "Teachers and parents shopping phonics printables.",
        "takeaway": "One decodable phonics book, $0.99, keep the PDF — no subscription.",
        "layout": "master style — product variant (hero object = storybook with 9px pine outlines, butter cat with dot eyes, price chip = the one orange accent, fact chips, CTA)",
        "headline": "Decodable Book Maker — one book at a time.",
        "on_image": "DECODABLE BOOK MAKER / $0.99 (orange price chip) / 4-page phonics PDF / Keep it forever / No subscription / Make your book",
        "source": "$0.99/run: marketing/oss-strategy.md ('decodable-book-maker: $0.99/run') + marketing/pilot-email.md ('one book for $0.99… keep it. No subscription.'); '4-page phonics PDF' per issue #84 brief.",
    }),
    ("open-source-library", render_oss_launch, {
        "audience": "Developers evaluating Omo's openness before paying per run.",
        "takeaway": "The Omo skill library is open source: MIT, free to download, pay per run.",
        "layout": "master style — launch variant (masthead + hero repo panel, '15' in orange = the single accent)",
        "headline": "The library is open. / Everything free / to download.",
        "on_image": "OMO · OPEN SOURCE / The library is open. / Everything free / to download. / 15 free skills · MIT · pay per run / github.com/omo-space/skills / $ git clone omo-space/skills / MIT · 15 free skills · free to download / omo.space/skills",
        "source": "research/oss-publish-spec.md (implemented 2026-08-16, first publish = 15 free skills, commit 104a2b3, MIT, github.com/omo-space/skills) + marketing/oss-strategy.md ($0.99 book run, $0.10 typical education run, pay-per-run model).",
    }),
]

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)

for slug, renderer, meta in POSTS:
    d = os.path.join(ROOT, slug)
    os.makedirs(os.path.join(d, "working"), exist_ok=True)
    renderer().save(os.path.join(d, "image.png"))
    write(os.path.join(d, "working", "structured-content.md"),
          f"# Structured content — {slug}\n\n"
          f"- **Audience:** {meta['audience']}\n"
          f"- **Viewer takeaway:** {meta['takeaway']}\n"
          f"- **Platform:** X landscape (16:9, 1600x900, text inside central 84%).\n"
          f"- **Layout:** {meta['layout']}\n"
          f"- **Master style:** research/OMO-IMAGE-STYLE-SYSTEM.MD (canvas #F8F7F5, "
          f"pine 9px frame, 2-3 pastel fields, one orange accent ≤5%, Fraunces/DM Sans, "
          f"-7° bean, flat vector, 25-50% open cream).\n"
          f"- **Headline:** {meta['headline']}\n"
          f"- **On-image wording:** {meta['on_image']}\n"
          f"- **Sources:** {meta['source']}\n"
          f"- **Generator:** programmatic PIL render (real brand fonts, exact hexes) — "
          f"research/social-assets/style-sheet/render_variants.py\n")
    write(os.path.join(d, "working", "prompt.md"),
          f"# Prompt (kept for provenance) — {slug}\n\n"
          f"This post was rendered programmatically for exact brand control "
          f"(exact hexes, real Fraunces/DM Sans, exact copy) via "
          f"research/social-assets/style-sheet/render_variants.py + omo_style.py.\n\n"
          f"Composition spec: {meta['layout']} per research/OMO-IMAGE-STYLE-SYSTEM.MD. "
          f"On-image wording: {meta['on_image']}.\n")
    print("wrote", os.path.join(d, "image.png"))
