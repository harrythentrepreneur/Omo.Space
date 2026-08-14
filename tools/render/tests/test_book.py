from __future__ import annotations

import io

import pytest
from pypdf import PdfReader

from tools.render.book import (
    BOOK_SCHEMA_VERSION,
    BookRenderError,
    pdf_page_count,
    render_book_pdf,
)


def book_manifest() -> dict:
    return {
        "schema_version": BOOK_SCHEMA_VERSION,
        "title": "Wrong Turn, Best View",
        "subtitle": "A story of rain, two cities, and the home they made",
        "book": """# Wrong Turn, Best View

## The Bookshop in the Rain

It began with two hands reaching for the same travel book while rain traced the window. They talked until closing, discovering that an ordinary detour could become the start of everything.

## Two Cities and One Small Home

Seven years carried them through two cities and into a first tiny apartment. The rooms were modest, but the life inside them kept expanding after a sock-stealing corgi arrived.

## The View They Kept

Plans still went sideways. Each time, they returned to the phrase that had become their compass: wrong turn, best view. Their keepsake was the joy of finding the view together.
""",
        "page_plan": [
            "Cover - a rainy bookshop motif",
            "The shared travel book and conversation until closing",
            "Seven years across two cities and the first apartment",
            "The corgi, stolen socks, and their favorite phrase",
        ],
        "style": {"name": "warm", "cover_color": "#B45F4A"},
        "footer": "Woven | A relationship keepsake",
    }


def test_book_renderer_is_byte_deterministic_and_has_real_pages() -> None:
    first = render_book_pdf(book_manifest())
    second = render_book_pdf(book_manifest())
    assert first == second
    assert first.startswith(b"%PDF-")
    assert pdf_page_count(first) >= 5
    reader = PdfReader(io.BytesIO(first))
    assert reader.metadata.title == "Wrong Turn, Best View"
    assert "The Bookshop in the Rain" in (reader.pages[2].extract_text() or "")
    assert "Woven | A relationship keepsake" in (reader.pages[2].extract_text() or "")


def test_book_renderer_rejects_unreviewed_cover_color() -> None:
    manifest = book_manifest()
    manifest["style"]["cover_color"] = "red"
    with pytest.raises(BookRenderError, match="six-digit hex"):
        render_book_pdf(manifest)


def test_book_renderer_rejects_missing_story_prose() -> None:
    manifest = book_manifest()
    manifest["book"] = "# A title only"
    with pytest.raises(BookRenderError, match="must contain prose"):
        render_book_pdf(manifest)
