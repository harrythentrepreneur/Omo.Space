# font_config.py — Font and layout registry for book style customization

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from app.core.config.logger import logger

# ─── Static fonts directory ──────────────────────────────────────────
STATIC_FONTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "static" / "fonts"


@dataclass
class FontConfig:
    """Resolved font configuration for PDF generation."""
    ttf_path: str           # Path to the body font .ttf file
    heading_ttf_path: str   # Path to the heading/bold font .ttf file
    css_family: str         # CSS font-family value for HTML templates


@dataclass
class LayoutConfig:
    """Resolved layout configuration for PDF generation."""
    template: str           # Jinja2 template filename for scene pages
    text_in_image: bool     # Whether text should be baked into image via PIL


# ─── Font Registry ───────────────────────────────────────────────────
FONT_REGISTRY = {
    "comic_neue": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "ComicNeue-Regular.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "ComicNeue-Bold.ttf"),
        css_family="'Comic Neue', cursive",
    ),
    "lexie_readable": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "LexieReadable-Regular.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "LexieReadable-Regular.ttf"),
        css_family="'Lexie Readable', sans-serif",
    ),
    "open_dyslexic": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "OpenDyslexic-Regular.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "OpenDyslexic-Bold.ttf"),
        css_family="'OpenDyslexic', sans-serif",
    ),
    "andika": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "Andika-Regular.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "Andika-Bold.ttf"),
        css_family="'Andika', sans-serif",
    ),
    "lexend": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "Lexend-Regular.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "Lexend-Bold.ttf"),
        css_family="'Lexend', sans-serif",
    ),
    # ── New fonts ────────────────────────────────────────────────────
    "poppins": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "Poppins-Regular.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "Poppins-Bold.ttf"),
        css_family="'Poppins', sans-serif",
    ),
    "nunito": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "Nunito-Variable.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "Nunito-Variable.ttf"),
        css_family="'Nunito', sans-serif",
    ),
    "quicksand": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "Quicksand-Variable.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "Quicksand-Variable.ttf"),
        css_family="'Quicksand', sans-serif",
    ),
    "patrick_hand": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "PatrickHand-Regular.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "PatrickHand-Regular.ttf"),
        css_family="'Patrick Hand', cursive",
    ),
    "fredoka": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "Fredoka-Variable.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "Fredoka-Variable.ttf"),
        css_family="'Fredoka', sans-serif",
    ),
    "atkinson_hyperlegible": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "AtkinsonHyperlegible-Regular.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "AtkinsonHyperlegible-Bold.ttf"),
        css_family="'Atkinson Hyperlegible', sans-serif",
    ),
    "cabin": FontConfig(
        ttf_path=str(STATIC_FONTS_DIR / "Cabin-Variable.ttf"),
        heading_ttf_path=str(STATIC_FONTS_DIR / "Cabin-Variable.ttf"),
        css_family="'Cabin', sans-serif",
    ),
}

DEFAULT_FONT_ID = "lexie_readable"

# ─── Layout Registry ────────────────────────────────────────────────
LAYOUT_REGISTRY = {
    "classic": LayoutConfig(
        template="scene_template.html",
        text_in_image=True,
    ),
    "picture_top": LayoutConfig(
        template="scene_picture_top.html",
        text_in_image=False,
    ),
    "side_by_side": LayoutConfig(
        template="scene_side_by_side.html",
        text_in_image=False,
    ),
    "text_top": LayoutConfig(
        template="scene_text_top.html",
        text_in_image=False,
    ),
}

DEFAULT_LAYOUT_ID = "classic"


def resolve_font(font_id: Optional[str] = None) -> FontConfig:
    """Resolve a font ID to its configuration. Falls back to default."""
    if font_id and font_id in FONT_REGISTRY:
        return FONT_REGISTRY[font_id]
    if font_id:
        logger.warning(f"Unknown font ID '{font_id}', falling back to default '{DEFAULT_FONT_ID}'")
    return FONT_REGISTRY[DEFAULT_FONT_ID]


def resolve_layout(layout_id: Optional[str] = None) -> LayoutConfig:
    """Resolve a layout ID to its configuration. Falls back to default."""
    if layout_id and layout_id in LAYOUT_REGISTRY:
        return LAYOUT_REGISTRY[layout_id]
    if layout_id:
        logger.warning(f"Unknown layout ID '{layout_id}', falling back to default '{DEFAULT_LAYOUT_ID}'")
    return LAYOUT_REGISTRY[DEFAULT_LAYOUT_ID]
