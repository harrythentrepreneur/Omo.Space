#!/usr/bin/env python3
"""Deterministic, local PDF/artifact compositor for Omo education workflows.

The renderer consumes a reviewed post-generation manifest. It performs no LLM
calls, billing, deployment, network access, or authorization decisions. A host
must authorize the owner before constructing ``ArtifactStore`` and must pass
only local, owner-authorized image paths into a manifest.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


SCHEMA_VERSION = "omo.education-artifact-manifest/v1"
SUPPORTED_SLUGS = {
    "phonics-worksheet-generator",
    "illustrated-decodable-story-maker",
    "phonics-story-edit-studio",
}
SAFE_STEM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,99}$")
OWNER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 54
TEXT_COLOR = colors.HexColor("#172033")
ACCENT = colors.HexColor("#2F6B5F")
PALE = colors.HexColor("#EAF4F0")


class ManifestError(ValueError):
    """The structured render manifest is invalid."""


class ArtifactAccessError(ValueError):
    """An artifact descriptor is outside the authorized owner's namespace."""


@dataclass(frozen=True)
class ArtifactDescriptor:
    kind: str
    role: str
    object_key: str
    filename: str
    content_type: str
    bytes: int
    sha256: str
    page_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class RenderResult:
    workflow_slug: str
    artifacts: tuple[ArtifactDescriptor, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_slug": self.workflow_slug,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "warnings": list(self.warnings),
        }


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_stem(value: Any) -> str:
    stem = str(value or "").strip()
    if not SAFE_STEM_RE.fullmatch(stem):
        raise ManifestError("filename_stem must contain only letters, numbers, spaces, _ or -")
    return re.sub(r"[ _]+", "-", stem).lower()


def _required_text(value: Any, field: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{field} must be a non-empty string")
    text = value.strip()
    if len(text) > maximum:
        raise ManifestError(f"{field} exceeds {maximum} characters")
    return text


def _required_list(value: Any, field: str, *, minimum: int = 1, maximum: int = 50) -> list[Any]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ManifestError(f"{field} must contain {minimum}-{maximum} items")
    return value


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"schema_version must be {SCHEMA_VERSION!r}")
    slug = manifest.get("workflow_slug")
    if slug not in SUPPORTED_SLUGS:
        raise ManifestError(f"workflow_slug must be one of {sorted(SUPPORTED_SLUGS)}")
    _required_text(manifest.get("document_id"), "document_id", 120)
    _required_text(manifest.get("title"), "title", 160)
    _safe_stem(manifest.get("filename_stem"))
    pages = _required_list(manifest.get("pages"), "pages", maximum=24)
    page_numbers: list[int] = []
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, Mapping):
            raise ManifestError(f"pages[{index - 1}] must be an object")
        number = page.get("page_number")
        if not isinstance(number, int) or number < 1:
            raise ManifestError(f"pages[{index - 1}].page_number must be a positive integer")
        page_numbers.append(number)
        _required_text(page.get("heading", f"Page {number}"), f"pages[{index - 1}].heading", 200)
        body = page.get("body", [])
        if not isinstance(body, list) or len(body) > 30 or any(not isinstance(item, str) for item in body):
            raise ManifestError(f"pages[{index - 1}].body must be an array of strings")
        items = page.get("items", [])
        if not isinstance(items, list) or len(items) > 50:
            raise ManifestError(f"pages[{index - 1}].items must be an array with at most 50 items")
        for item_index, item in enumerate(items):
            if not isinstance(item, Mapping):
                raise ManifestError(f"pages[{index - 1}].items[{item_index}] must be an object")
            _required_text(item.get("id"), f"pages[{index - 1}].items[{item_index}].id", 80)
            _required_text(item.get("prompt"), f"pages[{index - 1}].items[{item_index}].prompt", 1000)
        image_path = page.get("image_path")
        if image_path is not None and (not isinstance(image_path, str) or not image_path.strip()):
            raise ManifestError(f"pages[{index - 1}].image_path must be a non-empty local path")
    if page_numbers != sorted(set(page_numbers)):
        raise ManifestError("page_number values must be unique and increasing")
    if slug == "phonics-worksheet-generator":
        if len(pages) > 12:
            raise ManifestError("worksheet manifests support at most 12 worksheet pages")
        if manifest.get("include_answer_key") not in {True, False}:
            raise ManifestError("worksheet include_answer_key must be boolean")
    else:
        phonemes = manifest.get("phonemes", [])
        if not isinstance(phonemes, list) or len(phonemes) > 12 or any(not isinstance(item, str) for item in phonemes):
            raise ManifestError("story phonemes must be an array of at most 12 strings")


class ArtifactStore:
    """Content-addressed, owner-scoped local artifact storage.

    This is a testable storage adapter, not an authentication system. The host
    supplies an already-authenticated owner ID. Writes never replace content.
    """

    def __init__(self, root: Path, owner_id: str) -> None:
        if not OWNER_RE.fullmatch(owner_id):
            raise ArtifactAccessError("owner_id is not a safe artifact namespace")
        self.root = root.resolve()
        self.owner_id = owner_id
        self.owner_root = self.root / owner_id
        self.owner_root.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, object_key: str) -> Path:
        key_path = Path(object_key)
        if key_path.is_absolute() or ".." in key_path.parts:
            raise ArtifactAccessError("object_key must be a relative path without traversal")
        candidate = (self.root / key_path).resolve()
        try:
            candidate.relative_to(self.owner_root)
        except ValueError as exc:
            raise ArtifactAccessError("object_key does not belong to the authorized owner") from exc
        return candidate

    def write_immutable(
        self,
        *,
        run_id: str,
        role: str,
        filename: str,
        content_type: str,
        data: bytes,
        kind: str,
        page_count: int | None = None,
    ) -> ArtifactDescriptor:
        digest = sha256_bytes(data)
        safe_filename = Path(filename).name
        if safe_filename != filename or not safe_filename:
            raise ArtifactAccessError("filename must be a plain filename")
        run_component = re.sub(r"[^A-Za-z0-9_-]", "-", run_id)[:80]
        if not run_component:
            raise ArtifactAccessError("run_id must contain a safe character")
        object_key = f"{self.owner_id}/{run_component}/{digest}/{safe_filename}"
        destination = self._resolve_key(object_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != data:
                raise ArtifactAccessError("immutable artifact collision")
        else:
            with destination.open("xb") as stream:
                stream.write(data)
        return ArtifactDescriptor(
            kind=kind,
            role=role,
            object_key=object_key,
            filename=safe_filename,
            content_type=content_type,
            bytes=len(data),
            sha256=digest,
            page_count=page_count,
        )

    def read_owned(self, descriptor: Mapping[str, Any]) -> bytes:
        destination = self._resolve_key(_required_text(descriptor.get("object_key"), "object_key", 512))
        if not destination.is_file():
            raise ArtifactAccessError("artifact does not exist")
        data = destination.read_bytes()
        if len(data) != descriptor.get("bytes"):
            raise ArtifactAccessError("artifact byte count does not match descriptor")
        if sha256_bytes(data) != descriptor.get("sha256"):
            raise ArtifactAccessError("artifact checksum does not match descriptor")
        return data


def _wrap(text: str, font: str, size: float, width: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if stringWidth(candidate, font, size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _header(pdf: canvas.Canvas, title: str, label: str, page_number: int, total: int) -> float:
    pdf.setFillColor(ACCENT)
    pdf.roundRect(MARGIN, PAGE_HEIGHT - 112, PAGE_WIDTH - 2 * MARGIN, 58, 10, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(MARGIN + 18, PAGE_HEIGHT - 82, title[:58])
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(PAGE_WIDTH - MARGIN - 18, PAGE_HEIGHT - 82, label)
    pdf.setFillColor(colors.HexColor("#667085"))
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(PAGE_WIDTH - MARGIN, 28, f"Page {page_number} of {total}")
    return PAGE_HEIGHT - 138


def _draw_image(pdf: canvas.Canvas, path_text: str, *, y_top: float, height: float) -> float:
    path = Path(path_text).resolve()
    if not path.is_file():
        raise ManifestError(f"authorized local image does not exist: {path_text}")
    with PILImage.open(path) as image:
        image.verify()
    max_width = PAGE_WIDTH - 2 * MARGIN
    with PILImage.open(path) as image:
        ratio = min(max_width / image.width, height / image.height)
        width = image.width * ratio
        drawn_height = image.height * ratio
    x = (PAGE_WIDTH - width) / 2
    y = y_top - drawn_height
    pdf.drawImage(ImageReader(str(path)), x, y, width=width, height=drawn_height, preserveAspectRatio=True, mask="auto")
    return y - 18


def _draw_highlighted_line(
    pdf: canvas.Canvas, text: str, phonemes: Sequence[str], x: float, y: float, *, size: float = 11
) -> None:
    tokens = re.split(r"(\s+)", text)
    cursor = x
    patterns = [item.lower() for item in phonemes if item]
    for token in tokens:
        highlighted = bool(token.strip()) and any(pattern in token.lower() for pattern in patterns)
        pdf.setFillColor(colors.HexColor("#B42318") if highlighted else TEXT_COLOR)
        pdf.setFont("Helvetica-Bold" if highlighted else "Helvetica", size)
        pdf.drawString(cursor, y, token)
        cursor += stringWidth(token, "Helvetica-Bold" if highlighted else "Helvetica", size)


def _render_pdf(manifest: Mapping[str, Any], *, answer_key: bool = False) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter, invariant=1, pageCompression=1)
    pdf.setAuthor("Omo Space")
    pdf.setCreator("Omo deterministic education artifact renderer")
    pdf.setTitle(str(manifest["title"]) + (" - Answer Key" if answer_key else ""))
    pages = manifest["pages"]
    for index, page in enumerate(pages, start=1):
        label = "ANSWER KEY" if answer_key else str(manifest["workflow_slug"]).replace("-", " ").upper()
        y = _header(pdf, str(manifest["title"]), label, index, len(pages))
        heading = str(page.get("heading") or f"Page {page['page_number']}")
        pdf.setFillColor(TEXT_COLOR)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(MARGIN, y, heading[:72])
        y -= 28
        if page.get("image_path") and not answer_key:
            y = _draw_image(pdf, str(page["image_path"]), y_top=y, height=270)
        for paragraph in page.get("body", []):
            for line in _wrap(str(paragraph), "Helvetica", 11, PAGE_WIDTH - 2 * MARGIN):
                if y < 82:
                    raise ManifestError(f"page {page['page_number']} content exceeds safe page bounds")
                if manifest.get("highlight_text") and not answer_key:
                    _draw_highlighted_line(pdf, line, manifest.get("phonemes", []), MARGIN, y)
                else:
                    pdf.setFillColor(TEXT_COLOR)
                    pdf.setFont("Helvetica", 11)
                    pdf.drawString(MARGIN, y, line)
                y -= 15
            y -= 6
        for item_number, item in enumerate(page.get("items", []), start=1):
            content = str(item.get("answer", "Answer not supplied")) if answer_key else str(item["prompt"])
            prefix = f"{item_number}. "
            available = PAGE_WIDTH - 2 * MARGIN - stringWidth(prefix, "Helvetica-Bold", 11)
            lines = _wrap(content, "Helvetica", 11, available)
            required_height = 19 * len(lines) + (10 if answer_key else 29)
            if y - required_height < 62:
                raise ManifestError(f"page {page['page_number']} content exceeds safe page bounds")
            pdf.setFillColor(TEXT_COLOR)
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(MARGIN, y, prefix)
            text_x = MARGIN + stringWidth(prefix, "Helvetica-Bold", 11)
            for line_index, line in enumerate(lines):
                line_y = y - line_index * 19
                if manifest.get("highlight_text") and not answer_key:
                    _draw_highlighted_line(pdf, line, manifest.get("phonemes", []), text_x, line_y)
                else:
                    pdf.setFillColor(TEXT_COLOR)
                    pdf.setFont("Helvetica", 11)
                    pdf.drawString(text_x, line_y, line)
            y -= required_height
            if not answer_key:
                pdf.setStrokeColor(colors.HexColor("#C9D2DD"))
                pdf.line(MARGIN + 20, y + 15, PAGE_WIDTH - MARGIN, y + 15)
        if not page.get("body") and not page.get("items"):
            pdf.setFillColor(colors.HexColor("#667085"))
            pdf.setFont("Helvetica-Oblique", 11)
            pdf.drawString(MARGIN, y, "This page intentionally contains no instructional text.")
        pdf.showPage()
    pdf.save()
    value = buffer.getvalue()
    reader = PdfReader(io.BytesIO(value))
    if len(reader.pages) != len(pages):
        raise RuntimeError("rendered PDF page count does not match the manifest")
    return value


def _thumbnail(manifest: Mapping[str, Any]) -> bytes:
    first_image = next((page.get("image_path") for page in manifest["pages"] if page.get("image_path")), None)
    image = PILImage.new("RGB", (600, 800), "#EAF4F0")
    if first_image:
        with PILImage.open(Path(str(first_image)).resolve()) as source:
            source = source.convert("RGB")
            source.thumbnail((600, 500), PILImage.Resampling.LANCZOS)
            image.paste(source, ((600 - source.width) // 2, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 500, 600, 800), fill="#2F6B5F")
    font = ImageFont.load_default(size=34)
    small = ImageFont.load_default(size=20)
    lines = textwrap.wrap(str(manifest["title"]), width=24)[:4]
    y = 550
    for line in lines:
        draw.text((40, y), line, fill="white", font=font)
        y += 44
    draw.text((40, 748), "Omo Space classroom artifact", fill="#D7ECE5", font=small)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88, optimize=False, progressive=False)
    return buffer.getvalue()


def _artifact_from_file(
    path: Path,
    role: str,
    kind: str,
    content_type: str,
    page_count: int | None = None,
) -> ArtifactDescriptor:
    data = path.read_bytes()
    return ArtifactDescriptor(
        kind=kind,
        role=role,
        object_key=path.as_posix(),
        filename=path.name,
        content_type=content_type,
        bytes=len(data),
        sha256=sha256_bytes(data),
        page_count=page_count,
    )


def _write_artifact(
    *,
    output_dir: Path,
    store: ArtifactStore | None,
    run_id: str,
    role: str,
    filename: str,
    content_type: str,
    data: bytes,
    kind: str,
    page_count: int | None = None,
) -> ArtifactDescriptor:
    output_dir.mkdir(parents=True, exist_ok=True)
    local_path = output_dir / filename
    local_path.write_bytes(data)
    if store is not None:
        return store.write_immutable(
            run_id=run_id,
            role=role,
            filename=filename,
            content_type=content_type,
            data=data,
            kind=kind,
            page_count=page_count,
        )
    return _artifact_from_file(local_path, role, kind, content_type, page_count)


def render_manifest(
    manifest: Mapping[str, Any],
    output_dir: Path,
    *,
    store: ArtifactStore | None = None,
    run_id: str = "local-render",
) -> RenderResult:
    validate_manifest(manifest)
    slug = str(manifest["workflow_slug"])
    stem = _safe_stem(manifest["filename_stem"])
    pages = manifest["pages"]
    artifacts: list[ArtifactDescriptor] = []
    warnings: list[str] = []
    pdf_data = _render_pdf(manifest)
    pdf_role = {
        "phonics-worksheet-generator": "worksheet",
        "phonics-story-edit-studio": "revised_story",
        "illustrated-decodable-story-maker": "story",
    }[slug]
    artifacts.append(_write_artifact(
        output_dir=output_dir, store=store, run_id=run_id, role=pdf_role,
        filename=f"{stem}.pdf", content_type="application/pdf", data=pdf_data,
        kind="pdf", page_count=len(pages),
    ))
    if slug == "phonics-worksheet-generator" and manifest["include_answer_key"]:
        missing = [
            item["id"]
            for page in pages
            for item in page.get("items", [])
            if not str(item.get("answer", "")).strip()
        ]
        if missing:
            raise ManifestError(f"answer key requested but answers are missing for item IDs: {missing}")
        answer_data = _render_pdf(manifest, answer_key=True)
        artifacts.append(_write_artifact(
            output_dir=output_dir, store=store, run_id=run_id, role="answer_key",
            filename=f"{stem}-answer-key.pdf", content_type="application/pdf", data=answer_data,
            kind="pdf", page_count=len(pages),
        ))
    if slug != "phonics-worksheet-generator":
        source = copy.deepcopy(dict(manifest))
        source["renderer"] = {"name": "omo-education-artifact-renderer", "schema_version": SCHEMA_VERSION}
        source_data = canonical_json(source)
        artifacts.append(_write_artifact(
            output_dir=output_dir, store=store, run_id=run_id, role="editable_source",
            filename=f"{stem}.json", content_type="application/json", data=source_data, kind="json",
        ))
        thumb_data = _thumbnail(manifest)
        artifacts.append(_write_artifact(
            output_dir=output_dir, store=store, run_id=run_id, role="thumbnail",
            filename=f"{stem}.jpg", content_type="image/jpeg", data=thumb_data, kind="thumbnail",
        ))
        missing_images = [str(page["page_number"]) for page in pages if not page.get("image_path")]
        if missing_images:
            warnings.append(
                "text-only fallback: no authorized/generated image supplied for page(s) " + ", ".join(missing_images)
            )
    return RenderResult(slug, tuple(artifacts), tuple(warnings))


def apply_edit_operations(source: Mapping[str, Any], operations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Apply bounded edit-studio operations without mutating the source object."""
    result = copy.deepcopy(dict(source))
    pages = result.get("pages")
    if not isinstance(pages, list):
        raise ManifestError("editable source pages must be an array")
    for index, operation in enumerate(operations):
        name = operation.get("operation")
        if name == "change_story_title":
            result["title"] = _required_text(operation.get("new_title"), f"operations[{index}].new_title", 160)
            continue
        if name == "toggle_highlighting":
            enabled = operation.get("enabled")
            if not isinstance(enabled, bool):
                raise ManifestError(f"operations[{index}].enabled must be boolean")
            result["highlight_text"] = enabled
            continue
        if name == "set_highlight_color":
            color = _required_text(operation.get("color"), f"operations[{index}].color", 20)
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                raise ManifestError(f"operations[{index}].color must be a six-digit hex color")
            result["highlight_color"] = color
            continue
        if name == "regenerate_scene_image":
            raise ManifestError("regenerate_scene_image requires the separately reviewed image tier")
        if name not in {"change_scene_text", "set_text_style", "set_text_position"}:
            raise ManifestError(f"unsupported edit operation: {name!r}")
        page_number = operation.get("page_number")
        page = next((item for item in pages if item.get("page_number") == page_number), None)
        if page is None:
            raise ManifestError(f"operations[{index}] references unknown page_number")
        if name == "change_scene_text":
            page["body"] = [_required_text(operation.get("text"), f"operations[{index}].text", 4000)]
        elif name == "set_text_style":
            style = operation.get("style")
            if not isinstance(style, Mapping):
                raise ManifestError(f"operations[{index}].style must be an object")
            allowed = {"font_size", "font_name", "fill", "alignment", "line_spacing"}
            if set(style) - allowed:
                raise ManifestError(f"operations[{index}].style contains unknown fields")
            page["text_style"] = dict(style)
        elif name == "set_text_position":
            position = operation.get("position")
            if not isinstance(position, Mapping) or set(position) - {"x", "y", "width", "height"}:
                raise ManifestError(f"operations[{index}].position must contain only x/y/width/height")
            page["text_position"] = dict(position)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--owner-id")
    parser.add_argument("--run-id", default="local-render")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    store = None
    if args.artifact_root or args.owner_id:
        if not args.artifact_root or not args.owner_id:
            parser.error("--artifact-root and --owner-id must be supplied together")
        store = ArtifactStore(args.artifact_root, args.owner_id)
    result = render_manifest(manifest, args.output_dir, store=store, run_id=args.run_id)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
