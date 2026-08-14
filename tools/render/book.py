#!/usr/bin/env python3
"""Deterministic keepsake-book PDF rendering for generated Omo workflows.

The renderer is intentionally provider-free and storage-agnostic. Generated
workflow runtimes pass reviewed story output in, then persist the returned PDF
through their authorized artifact plane.
"""

from __future__ import annotations

import io
import re
from collections.abc import Mapping, Sequence
from typing import Any

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


BOOK_SCHEMA_VERSION = "omo.book-pdf/v1"
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN_X = 66
BODY_TOP = PAGE_HEIGHT - 104
BODY_BOTTOM = 66
BODY_FONT = "Times-Roman"
BODY_FONT_BOLD = "Times-Bold"
DISPLAY_FONT = "Helvetica-Bold"
MUTED = colors.HexColor("#66756E")
INK = colors.HexColor("#17352C")
PAPER = colors.HexColor("#FBFAF7")
DEFAULT_COVER_COLORS = {
    "warm": "#B45F4A",
    "playful": "#D87843",
    "poetic": "#536B78",
}


class BookRenderError(ValueError):
    """The generated book contract cannot be rendered safely."""


def _text(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BookRenderError(f"{field} must be a non-empty string")
    result = value.strip()
    if len(result) > maximum:
        raise BookRenderError(f"{field} exceeds {maximum} characters")
    return result


def _pdf_text(value: str) -> str:
    """Normalize unsupported glyphs without letting ReportLab emit tofu boxes."""
    normalized = value.replace("\u2011", "-").replace("\u00a0", " ")
    return normalized.encode("cp1252", "replace").decode("cp1252")


def _plain_markdown(value: str) -> str:
    value = re.sub(r"!\[[^]]*\]\([^)]*\)", "", value)
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"(?<!\\)[*_`~]", "", value)
    return _pdf_text(re.sub(r"\s+", " ", value).strip())


def _cover_color(style: Mapping[str, Any]) -> colors.Color:
    raw = style.get("cover_color")
    if raw is None:
        raw = DEFAULT_COVER_COLORS.get(str(style.get("name") or "warm"), "#B45F4A")
    if not isinstance(raw, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", raw):
        raise BookRenderError("style.cover_color must be a six-digit hex color")
    return colors.HexColor(raw)


def _parse_sections(markdown: str, fallback_title: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    heading = fallback_title
    paragraphs: list[str] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            paragraph = _plain_markdown(" ".join(paragraph_lines))
            if paragraph:
                paragraphs.append(paragraph)
            paragraph_lines.clear()

    def flush_section() -> None:
        flush_paragraph()
        if paragraphs:
            sections.append((_plain_markdown(heading), list(paragraphs)))
            paragraphs.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        match = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if match:
            flush_section()
            heading = match.group(1)
            continue
        if re.match(r"^#\s+", line):
            flush_paragraph()
            continue
        if not line:
            flush_paragraph()
            continue
        paragraph_lines.append(line)
    flush_section()
    if not sections:
        raise BookRenderError("book Markdown must contain prose")
    return sections


def _wrapped_lines(text: str, font: str, size: float, width: float) -> list[list[str]]:
    words = text.split()
    if not words:
        return [[]]
    lines: list[list[str]] = []
    current = [words[0]]
    for word in words[1:]:
        candidate = " ".join([*current, word])
        if stringWidth(candidate, font, size) <= width:
            current.append(word)
        else:
            lines.append(current)
            current = [word]
    lines.append(current)
    return lines


def _draw_wrapped_centered(
    pdf: canvas.Canvas,
    text: str,
    *,
    y: float,
    font: str,
    size: float,
    width: float,
    leading: float,
) -> float:
    for words in _wrapped_lines(_pdf_text(text), font, size, width):
        line = " ".join(words)
        pdf.setFont(font, size)
        pdf.drawCentredString(PAGE_WIDTH / 2, y, line)
        y -= leading
    return y


def _draw_footer(pdf: canvas.Canvas, page_number: int, footer: str, accent: colors.Color) -> None:
    pdf.setStrokeColor(colors.Color(accent.red, accent.green, accent.blue, alpha=0.32))
    pdf.setLineWidth(0.6)
    pdf.line(MARGIN_X, 45, PAGE_WIDTH - MARGIN_X, 45)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(MARGIN_X, 29, _pdf_text(footer)[:72])
    pdf.drawRightString(PAGE_WIDTH - MARGIN_X, 29, str(page_number))


def _draw_justified_paragraph(
    pdf: canvas.Canvas,
    paragraph: str,
    *,
    y: float,
    width: float,
    size: float = 11.25,
    leading: float = 17.2,
) -> float:
    lines = _wrapped_lines(paragraph, BODY_FONT, size, width)
    for index, words in enumerate(lines):
        if not words:
            y -= leading
            continue
        pdf.setFillColor(colors.HexColor("#27352F"))
        pdf.setFont(BODY_FONT, size)
        if index == len(lines) - 1 or len(words) == 1:
            pdf.drawString(MARGIN_X, y, " ".join(words))
        else:
            word_width = sum(stringWidth(word, BODY_FONT, size) for word in words)
            gap = (width - word_width) / (len(words) - 1)
            x = MARGIN_X
            for word in words:
                pdf.drawString(x, y, word)
                x += stringWidth(word, BODY_FONT, size) + gap
        y -= leading
    return y - 8


def _new_body_page(
    pdf: canvas.Canvas,
    *,
    page_number: int,
    footer: str,
    accent: colors.Color,
    running_title: str | None = None,
) -> float:
    pdf.setFillColor(PAPER)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    if running_title:
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(MARGIN_X, PAGE_HEIGHT - 55, _pdf_text(running_title).upper()[:70])
    _draw_footer(pdf, page_number, footer, accent)
    return BODY_TOP


def validate_book_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != BOOK_SCHEMA_VERSION:
        raise BookRenderError(f"schema_version must be {BOOK_SCHEMA_VERSION!r}")
    _text(manifest.get("title"), "title", 160)
    _text(manifest.get("subtitle"), "subtitle", 240)
    _text(manifest.get("book"), "book", 50_000)
    page_plan = manifest.get("page_plan")
    if not isinstance(page_plan, Sequence) or isinstance(page_plan, (str, bytes)):
        raise BookRenderError("page_plan must be an array")
    if not 1 <= len(page_plan) <= 24:
        raise BookRenderError("page_plan must contain 1-24 items")
    for index, item in enumerate(page_plan):
        _text(item, f"page_plan[{index}]", 500)
    style = manifest.get("style", {})
    if not isinstance(style, Mapping):
        raise BookRenderError("style must be an object")
    _cover_color(style)
    footer = manifest.get("footer", "Omo Space | Keepsake Edition")
    _text(footer, "footer", 100)


def render_book_pdf(manifest: Mapping[str, Any]) -> bytes:
    """Render one real keepsake PDF with deterministic metadata and byte layout."""
    validate_book_manifest(manifest)
    title = _text(manifest["title"], "title", 160)
    subtitle = _text(manifest["subtitle"], "subtitle", 240)
    footer = _text(manifest.get("footer", "Omo Space | Keepsake Edition"), "footer", 100)
    accent = _cover_color(manifest.get("style", {}))
    sections = _parse_sections(_text(manifest["book"], "book", 50_000), title)
    page_plan = [_plain_markdown(str(item)) for item in manifest["page_plan"]]

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter, invariant=1, pageCompression=1)
    pdf.setAuthor("Omo Space")
    pdf.setCreator("Omo deterministic keepsake book renderer")
    pdf.setProducer("Omo Space")
    pdf.setTitle(_pdf_text(title))
    pdf.setSubject("A generated relationship keepsake")

    # Cover.
    pdf.setFillColor(accent)
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    pdf.setStrokeColor(colors.Color(1, 1, 1, alpha=0.42))
    pdf.setLineWidth(1.2)
    pdf.roundRect(36, 36, PAGE_WIDTH - 72, PAGE_HEIGHT - 72, 18, fill=0, stroke=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 92, "A WOVEN KEEPSAKE")
    y = _draw_wrapped_centered(
        pdf,
        title,
        y=PAGE_HEIGHT * 0.61,
        font=DISPLAY_FONT,
        size=31,
        width=PAGE_WIDTH - 150,
        leading=37,
    )
    pdf.setStrokeColor(colors.Color(1, 1, 1, alpha=0.7))
    pdf.setLineWidth(1)
    pdf.line(PAGE_WIDTH / 2 - 42, y - 4, PAGE_WIDTH / 2 + 42, y - 4)
    pdf.setFillColor(colors.Color(1, 1, 1, alpha=0.9))
    _draw_wrapped_centered(
        pdf,
        subtitle,
        y=y - 36,
        font="Times-Italic",
        size=14,
        width=PAGE_WIDTH - 180,
        leading=20,
    )
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(PAGE_WIDTH / 2, 68, "MADE WITH CARE BY OMO SPACE")
    pdf.showPage()

    body_page = 1

    # A designed keepsake map makes the supplied page plan useful without
    # confusing it with the finished prose.
    y = _new_body_page(pdf, page_number=body_page, footer=footer, accent=accent)
    pdf.setFillColor(accent)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(MARGIN_X, y, "THE KEEPSAKE MAP")
    y -= 34
    pdf.setFillColor(INK)
    pdf.setFont(DISPLAY_FONT, 25)
    pdf.drawString(MARGIN_X, y, "The moments held inside")
    y -= 34
    pdf.setFillColor(MUTED)
    pdf.setFont("Times-Italic", 11)
    pdf.drawString(MARGIN_X, y, "A small map of the memories woven into this book.")
    y -= 32
    for index, item in enumerate(page_plan, start=1):
        lines = _wrapped_lines(item, BODY_FONT, 10.5, PAGE_WIDTH - 2 * MARGIN_X - 36)
        required = max(30, 15 * len(lines) + 10)
        if y - required < BODY_BOTTOM:
            pdf.showPage()
            body_page += 1
            y = _new_body_page(
                pdf,
                page_number=body_page,
                footer=footer,
                accent=accent,
                running_title="The Keepsake Map",
            )
        pdf.setFillColor(accent)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(MARGIN_X, y, f"{index:02d}")
        pdf.setFillColor(colors.HexColor("#27352F"))
        for line in lines:
            pdf.setFont(BODY_FONT, 10.5)
            pdf.drawString(MARGIN_X + 36, y, " ".join(line))
            y -= 15
        y -= 10
    pdf.showPage()

    for chapter_number, (heading, paragraphs) in enumerate(sections, start=1):
        body_page += 1
        y = _new_body_page(pdf, page_number=body_page, footer=footer, accent=accent)
        pdf.setFillColor(accent)
        pdf.setFont("Helvetica", 8)
        pdf.drawString(MARGIN_X, y, f"CHAPTER {chapter_number:02d}")
        y -= 32
        pdf.setFillColor(INK)
        y = _draw_wrapped_centered(
            pdf,
            heading,
            y=y,
            font=DISPLAY_FONT,
            size=24,
            width=PAGE_WIDTH - 2 * MARGIN_X,
            leading=29,
        )
        y -= 3
        pdf.setStrokeColor(accent)
        pdf.setLineWidth(1.6)
        pdf.line(MARGIN_X, y, MARGIN_X + 58, y)
        y -= 32
        for paragraph in paragraphs:
            lines = _wrapped_lines(paragraph, BODY_FONT, 11.25, PAGE_WIDTH - 2 * MARGIN_X)
            required = len(lines) * 17.2 + 14
            if y - required < BODY_BOTTOM:
                pdf.showPage()
                body_page += 1
                y = _new_body_page(
                    pdf,
                    page_number=body_page,
                    footer=footer,
                    accent=accent,
                    running_title=heading,
                )
            y = _draw_justified_paragraph(
                pdf,
                paragraph,
                y=y,
                width=PAGE_WIDTH - 2 * MARGIN_X,
            )
        pdf.showPage()

    pdf.save()
    data = buffer.getvalue()
    reader = PdfReader(io.BytesIO(data))
    expected_minimum = 2 + len(sections)
    if len(reader.pages) < expected_minimum:
        raise RuntimeError("rendered keepsake PDF lost a required cover, map, or chapter page")
    return data


def pdf_page_count(data: bytes) -> int:
    """Return the verified page count for a rendered PDF byte string."""
    return len(PdfReader(io.BytesIO(data)).pages)
