"""Image generation and visual QA for the de Mello Awake pipeline.

The module deliberately keeps provider I/O behind a tiny injectable adapter.
Tests can pass a fake ``request`` callable and never need credentials or
network access.  Accepted images are normalized into a request-scoped output
directory; rejected images are never promoted to the next edit parent.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import math
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageOps


GPT_IMAGE_MODEL = "gpt-image-2-2026-04-21"
STYLE_LOCK_V3 = (
    "Minimal Japanese sumi-e: thin black ink on pure white, sparse flat line, "
    "no shading/fill/texture, vertical 9:16, no text/watermark/color."
)
STYLE_DETAIL_V3 = (
    "Faint dry-brush Japanese sumi-e ink line art. Use thin irregular black "
    "brush strokes on an exact pure-white field with at least 85% negative "
    "space. Symbolic suggestion over detailed depiction; calm, elegant, and "
    "readable at phone size. FORBID gray wash, gradients, shading, color, red, "
    "seals, text, letters, numbers, logos, watermarks, extra figures, new "
    "scenery, vector/clip-art contours, anatomy detail, and camera change."
)


class ImageGenerationError(RuntimeError):
    """The image provider failed or returned an invalid response."""


class VisualValidationError(ValueError):
    """A decoded image failed the binding black-on-white visual gates."""


@dataclass(frozen=True)
class VisualReport:
    width: int
    height: int
    portrait: bool
    near_white_ratio: float
    exact_white_ratio: float
    chroma_ratio: float
    dark_mask_ratio: float
    sha256: str
    passed: bool
    failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class GeneratedFrame:
    frame_id: str
    second: float
    path: str
    parent_frame_id: str | None
    provider: str
    prompt_sha256: str
    image_sha256: str
    attempts: int
    visual: Mapping[str, Any]


@dataclass(frozen=True)
class GenerationResult:
    provider: str
    frames: tuple[GeneratedFrame, ...]
    usage: Mapping[str, Any]
    retries: int
    fallback_reason: str | None = None


@dataclass
class UsageLedger:
    """Provider usage priced from the GPT Image 2 token meter."""

    image_requests: int = 0
    image_generations: int = 0
    image_edits: int = 0
    provider_usage: list[Mapping[str, Any]] = field(default_factory=list)
    explicit_cost_usd: float = 0.0
    cost_complete: bool = True

    def add(self, *, edit: bool, usage: Mapping[str, Any] | None) -> None:
        self.image_requests += 1
        if edit:
            self.image_edits += 1
        else:
            self.image_generations += 1
        record = dict(usage or {})
        self.provider_usage.append(record)
        raw_cost = record.get("cost_usd")
        if not isinstance(raw_cost, (int, float)):
            try:
                input_tokens = float(record.get("input_tokens", 0) or 0)
                output_tokens = float(record.get("output_tokens", 0) or 0)
                details = record.get("input_tokens_details")
                if not isinstance(details, Mapping):
                    details = record.get("input_token_details")
                details = details if isinstance(details, Mapping) else {}
                image_input = float(details.get("image_tokens", input_tokens) or 0)
                text_input = float(details.get("text_tokens", 0) or 0)
                if input_tokens or output_tokens or image_input or text_input:
                    raw_cost = (
                        image_input * 8.0
                        + text_input * 5.0
                        + output_tokens * 30.0
                    ) / 1_000_000
                    record["cost_usd"] = round(raw_cost, 8)
            except (TypeError, ValueError):
                raw_cost = None
        if isinstance(raw_cost, (int, float)) and math.isfinite(float(raw_cost)):
            self.explicit_cost_usd += float(raw_cost)
        else:
            self.cost_complete = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_requests": self.image_requests,
            "image_generations": self.image_generations,
            "image_edits": self.image_edits,
            "provider_usage": self.provider_usage,
            "measured_cost_usd": (
                round(self.explicit_cost_usd, 8) if self.cost_complete else None
            ),
            "cost_complete": self.cost_complete,
        }


ProviderRequest = Callable[..., Mapping[str, Any]]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _decode_image(value: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(value)) as source:
            source.load()
            return source.convert("RGB")
    except Exception as exc:  # Pillow exposes several decoder-specific errors.
        raise VisualValidationError(f"image decode failed: {exc}") from exc


def validate_image_bytes(
    value: bytes,
    *,
    min_white_ratio: float = 0.85,
    max_chroma_ratio: float = 0.01,
    min_dark_ratio: float = 0.0001,
    max_dark_ratio: float = 0.15,
    expected_size: tuple[int, int] | None = None,
) -> VisualReport:
    """Validate decode, geometry, white field, chroma, and sparse dark ink."""
    image = _decode_image(value)
    pixels = np.asarray(image, dtype=np.uint8)
    minimum = pixels.min(axis=2)
    maximum = pixels.max(axis=2)
    near_white = (minimum >= 245)
    exact_white = (minimum == 255) & (maximum == 255)
    chroma = (maximum.astype(np.int16) - minimum.astype(np.int16)) > 12
    dark = maximum < 220
    failures: list[str] = []
    portrait = image.height > image.width
    if not portrait:
        failures.append("image is not portrait")
    if expected_size is not None and image.size != expected_size:
        failures.append(f"dimensions {image.size} != {expected_size}")
    near_white_ratio = float(near_white.mean())
    chroma_ratio = float(chroma.mean())
    dark_ratio = float(dark.mean())
    if near_white_ratio < min_white_ratio:
        failures.append(
            f"near-white ratio {near_white_ratio:.4f} < {min_white_ratio:.4f}"
        )
    if chroma_ratio > max_chroma_ratio:
        failures.append(f"chroma ratio {chroma_ratio:.4f} > {max_chroma_ratio:.4f}")
    if dark_ratio < min_dark_ratio:
        failures.append(f"dark-mask ratio {dark_ratio:.6f} < {min_dark_ratio:.6f}")
    if dark_ratio > max_dark_ratio:
        failures.append(f"dark-mask ratio {dark_ratio:.4f} > {max_dark_ratio:.4f}")
    return VisualReport(
        width=image.width,
        height=image.height,
        portrait=portrait,
        near_white_ratio=near_white_ratio,
        exact_white_ratio=float(exact_white.mean()),
        chroma_ratio=chroma_ratio,
        dark_mask_ratio=dark_ratio,
        sha256=_sha256_bytes(value),
        passed=not failures,
        failures=tuple(failures),
    )


def normalize_sumi_e_bytes(value: bytes) -> bytes:
    """Return deterministic flat-ink PNG bytes without gray wash or color."""
    image = _decode_image(value)
    rgb = np.asarray(image, dtype=np.float32)
    luma = np.rint(
        0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    )
    neutral = np.where(luma >= 245, 255, 26).astype(np.uint8)
    output = Image.fromarray(np.repeat(neutral[..., None], 3, axis=2), "RGB")
    buffer = io.BytesIO()
    output.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def validate_image_path(path: Path, **kwargs: Any) -> VisualReport:
    return validate_image_bytes(path.read_bytes(), **kwargs)


def build_frame_prompt(spec: Mapping[str, Any], *, first: bool) -> str:
    """Compile the canonical V3 one-delta prompt for a generated anchor."""
    frame_id = str(spec.get("frame_id") or spec.get("fid") or "G000")
    second = float(spec.get("second", spec.get("sec", 0.0)))
    role = str(spec.get("role", "change"))
    meaning = str(spec.get("meaning") or spec.get("spoken_meaning") or "awareness")
    delta = str(spec.get("delta") or "extend the existing ink line slightly")
    protected = spec.get("protected") or ["main figure", "through-line", "white field"]
    anchors = ", ".join(map(str, protected))
    mode = "TEXT-TO-IMAGE identity frame." if first else (
        "IMAGE-TO-IMAGE from the accepted parent. Continue this exact drawing."
    )
    return (
        f"{mode} {frame_id} @{second:.3f}s {role}. Meaning: {meaning}. "
        f"Change only: {delta}. Keep {anchors} at the same normalized position, "
        "scale, crop, and line identity; protected-anchor drift <=1%. Protect "
        f"the empty margins. {STYLE_LOCK_V3} {STYLE_DETAIL_V3}"
    )


class OpenAIImageAdapter:
    """Small GPT Image 2 generation/edit client with an injectable transport."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        request: ProviderRequest | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 180.0,
        model: str | None = None,
        size: str = "1024x1536",
        quality: str = "medium",
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.request = request
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.model = model or os.environ.get("OPENAI_IMAGE_MODEL") or GPT_IMAGE_MODEL
        self.size = size
        self.quality = quality

    def _http_request(self, *, edit: bool, prompt: str, parent: bytes | None) -> Mapping[str, Any]:
        if not self.api_key:
            raise ImageGenerationError("OPENAI_API_KEY is not configured")
        try:
            import httpx
        except ImportError as exc:
            raise ImageGenerationError("httpx is required for OpenAI image requests") from exc
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if edit:
            response = httpx.post(
                f"{self.base_url}/images/edits",
                headers=headers,
                data={
                    "model": self.model,
                    "prompt": prompt,
                    "size": self.size,
                    "quality": self.quality,
                },
                files={"image": ("accepted-parent.png", parent, "image/png")},
                timeout=self.timeout_seconds,
            )
        else:
            response = httpx.post(
                f"{self.base_url}/images/generations",
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "size": self.size,
                    "quality": self.quality,
                    "n": 1,
                },
                timeout=self.timeout_seconds,
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise ImageGenerationError("OpenAI image response is not an object")
        return payload

    def generate(self, prompt: str, *, parent: bytes | None = None) -> tuple[bytes, Mapping[str, Any]]:
        edit = parent is not None
        try:
            if self.request is not None:
                payload = self.request(
                    edit=edit,
                    prompt=prompt,
                    parent=parent,
                    model=self.model,
                    size=self.size,
                    quality=self.quality,
                )
            else:
                payload = self._http_request(edit=edit, prompt=prompt, parent=parent)
        except ImageGenerationError:
            raise
        except Exception as exc:
            raise ImageGenerationError(f"image request failed: {type(exc).__name__}: {exc}") from exc
        data = payload.get("data")
        if not isinstance(data, Sequence) or not data or not isinstance(data[0], Mapping):
            raise ImageGenerationError("image response has no data[0] object")
        encoded = data[0].get("b64_json")
        if not isinstance(encoded, str) or not encoded:
            raise ImageGenerationError("image response has no base64 payload")
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ImageGenerationError("image response contains invalid base64") from exc
        if not decoded:
            raise ImageGenerationError("image response decoded to zero bytes")
        usage = payload.get("usage")
        return decoded, dict(usage) if isinstance(usage, Mapping) else {}


def generate_keyframes(
    specs: Sequence[Mapping[str, Any]],
    output_dir: Path,
    *,
    adapter: OpenAIImageAdapter,
    max_retries: int = 2,
    backoff_seconds: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
) -> GenerationResult:
    """Generate sequential accepted-parent anchors with bounded retries."""
    if not specs:
        raise ValueError("at least one keyframe spec is required")
    if not 0 <= max_retries <= 5:
        raise ValueError("max_retries must be in [0, 5]")
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = UsageLedger()
    frames: list[GeneratedFrame] = []
    accepted_parent: bytes | None = None
    accepted_parent_id: str | None = None
    retry_count = 0
    for index, spec in enumerate(specs):
        frame_id = str(spec.get("frame_id") or spec.get("fid") or f"G{index:03d}")
        prompt = build_frame_prompt(spec, first=index == 0)
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                raw, usage = adapter.generate(prompt, parent=accepted_parent)
                ledger.add(edit=accepted_parent is not None, usage=usage)
                raw_report = validate_image_bytes(raw)
                if not raw_report.passed:
                    raise VisualValidationError("; ".join(raw_report.failures))
                normalized = normalize_sumi_e_bytes(raw)
                normalized_report = validate_image_bytes(normalized)
                if not normalized_report.passed:
                    raise VisualValidationError("; ".join(normalized_report.failures))
                path = output_dir / f"{frame_id}.png"
                path.write_bytes(normalized)
                frame = GeneratedFrame(
                    frame_id=frame_id,
                    second=float(spec.get("second", spec.get("sec", index))),
                    path=str(path),
                    parent_frame_id=accepted_parent_id,
                    provider=adapter.model,
                    prompt_sha256=_sha256_bytes(prompt.encode("utf-8")),
                    image_sha256=normalized_report.sha256,
                    attempts=attempt + 1,
                    visual=asdict(normalized_report),
                )
                frames.append(frame)
                accepted_parent = normalized
                accepted_parent_id = frame_id
                break
            except (ImageGenerationError, VisualValidationError) as exc:
                last_error = exc
                if attempt >= max_retries:
                    break
                retry_count += 1
                if backoff_seconds > 0:
                    sleep(backoff_seconds * (2**attempt))
        else:  # pragma: no cover - loop always breaks or exhausts naturally.
            last_error = ImageGenerationError("unreachable retry state")
        if len(frames) != index + 1:
            raise ImageGenerationError(
                f"{frame_id} failed after {max_retries + 1} attempts: {last_error}"
            ) from last_error
    return GenerationResult(
        provider=adapter.model,
        frames=tuple(frames),
        usage=ledger.to_dict(),
        retries=retry_count,
    )


class ProceduralSumiEGenerator:
    """Deterministic, disclosed fallback; it never impersonates model output."""

    provider_name = "procedural-fallback"

    def __init__(self, *, width: int = 1024, height: int = 1536) -> None:
        self.width = width
        self.height = height

    def render(self, spec: Mapping[str, Any], index: int, total: int) -> bytes:
        image = Image.new("RGB", (self.width, self.height), "white")
        draw = ImageDraw.Draw(image)
        scale = self.width / 1024.0
        phase = index / max(total - 1, 1)
        # After the taste lands, the predicament recedes as one continuous ink
        # wash while the sweetness mark remains fully black. At 90% of the clip
        # the established drawing has faded completely to a dot-only white field.
        recede = min(1.0, max(0.0, (phase - 0.62) / 0.28))
        scene_value = round(22 + (255 - 22) * recede)
        ink = (scene_value, scene_value, scene_value)
        final_ink = (22, 22, 22)
        thin = max(2, round(2 * scale))
        strong = max(4, round(7 * scale))

        def brush_line(
            points: Sequence[tuple[int, int]],
            width: int = strong,
            end_width: int | None = None,
        ) -> None:
            """Paint a tapered, slightly irregular dry-brush polyline."""
            if len(points) < 2:
                return
            target = max(1, end_width if end_width is not None else max(1, width // 2))
            for segment, (start, end) in enumerate(zip(points, points[1:])):
                ratio = segment / max(len(points) - 2, 1)
                segment_width = max(1, round(width + (target - width) * ratio))
                draw.line((start, end), fill=ink, width=segment_width)
                # A single-offset bristle gives the contour an organic edge but
                # preserves a flat monochrome field and deterministic geometry.
                if segment_width >= 4:
                    offset = -1 if (index + segment) % 2 else 1
                    draw.line(
                        ((start[0], start[1] + offset), (end[0], end[1] + offset)),
                        fill=ink,
                        width=max(1, segment_width // 3),
                    )

        def brush_arc(box: tuple[int, int, int, int], start: int, end: int, width: int) -> None:
            draw.arc(box, start, end, fill=ink, width=width)
            inset = max(1, width // 3)
            shifted = (box[0] + 1, box[1] - 1, box[2] - inset, box[3] + 1)
            draw.arc(shifted, start + 2, end - 1, fill=ink, width=max(1, width // 3))

        # Keep one continuous composition for all thirty frames. Motion happens
        # inside the drawing: berry rises, taste ripples, sweetness travels.
        y = int(self.height * 0.43)
        branch_left, branch_right = int(self.width * 0.12), int(self.width * 0.86)
        brush_line([(branch_left, y + 8), (int(self.width * 0.46), y), (branch_right, y - 13)], strong, thin)
        brush_line(
            [(int(self.width * 0.05), y - 155), (int(self.width * 0.13), y - 48), (branch_left + 45, y + 3)],
            strong + 2,
            thin,
        )

        # A readable tiger mask peers from the cliff: ears, brow, eyes, muzzle,
        # whiskers, and three unmistakable stripes in sparse brush language.
        tx, ty = int(self.width * 0.22), y - 215
        brush_arc((tx - 105, ty - 85, tx + 120, ty + 105), 188, 353, strong)
        brush_line([(tx - 80, ty - 46), (tx - 54, ty - 90), (tx - 24, ty - 53)], strong, thin)
        brush_line([(tx + 42, ty - 54), (tx + 73, ty - 94), (tx + 94, ty - 42)], strong, thin)
        brush_line([(tx - 58, ty + 4), (tx - 30, ty - 4)], thin, 1)
        brush_line([(tx + 25, ty - 4), (tx + 53, ty + 4)], thin, 1)
        draw.polygon([(tx - 8, ty + 20), (tx + 8, ty + 20), (tx, ty + 32)], fill=ink)
        brush_arc((tx - 38, ty + 10, tx + 40, ty + 72), 12, 168, thin)
        for stripe_x in (-45, 0, 45):
            brush_line([(tx + stripe_x, ty - 55), (tx + stripe_x // 2, ty - 20)], strong, 1)
        for whisker_y in (35, 48):
            brush_line([(tx - 12, ty + whisker_y), (tx - 100, ty + whisker_y + 12)], thin, 1)
            brush_line([(tx + 12, ty + whisker_y), (tx + 105, ty + whisker_y + 8)], thin, 1)

        # Exactly two large mice face inward and gnaw the branch.
        for mx, direction in ((int(self.width * 0.37), 1), (int(self.width * 0.66), -1)):
            draw.ellipse((mx - 30, y - 45, mx + 30, y + 7), outline=ink, width=strong)
            ear_x = mx + direction * 12
            draw.ellipse((ear_x - 12, y - 58, ear_x + 12, y - 34), outline=ink, width=thin)
            nose_x = mx + direction * 32
            draw.ellipse((nose_x - 4, y - 19, nose_x + 4, y - 11), fill=ink)
            brush_arc(
                (mx - 78, y - 30, mx + 78, y + 56),
                190 if direction > 0 else 350,
                342 if direction > 0 else 502,
                thin,
            )
            brush_line([(nose_x, y - 13), (nose_x + direction * 24, y - 4)], thin, 1)

        # One hanging person, with a filled brush robe instead of a stick body.
        fx, head_y = int(self.width * 0.51), y + 132
        draw.ellipse((fx - 30, head_y - 30, fx + 30, head_y + 30), outline=ink, width=strong)
        brush_line([(fx - 12, head_y + 28), (fx - 28, head_y + 165)], strong + 2, thin)
        brush_line([(fx + 12, head_y + 28), (fx + 30, head_y + 165)], strong, thin)
        brush_line([(fx - 18, head_y + 50), (fx - 76, y + 2), (fx - 53, y - 8)], strong, thin)
        brush_line([(fx - 28, head_y + 165), (fx - 78, head_y + 235), (fx - 48, head_y + 250)], strong, thin)
        brush_line([(fx + 30, head_y + 165), (fx + 82, head_y + 235), (fx + 50, head_y + 252)], strong, thin)

        berry_progress = min(1.0, phase / 0.46)
        berry_x = fx + int(112 - 68 * berry_progress)
        berry_y = head_y + int(63 - 58 * berry_progress)
        brush_line([(fx + 16, head_y + 62), (berry_x - 18, berry_y + 25)], strong, thin)
        berry = [
            (berry_x, berry_y + 27),
            (berry_x - 23, berry_y - 4),
            (berry_x - 12, berry_y - 22),
            (berry_x, berry_y - 11),
            (berry_x + 12, berry_y - 22),
            (berry_x + 23, berry_y - 4),
        ]
        brush_line(berry + [berry[0]], strong, thin)
        brush_line([(berry_x, berry_y - 14), (berry_x - 18, berry_y - 35)], thin, 1)
        brush_line([(berry_x, berry_y - 14), (berry_x + 22, berry_y - 34)], thin, 1)

        # One deliberately broken ripple expands and vanishes; it never becomes
        # a closed target/bubble and never survives into the dot-only ending.
        if 0.34 <= phase <= 0.68:
            pulse_phase = min(1.0, (phase - 0.34) / 0.34)
            pulse_radius = int(28 + 48 * math.sin(math.pi * pulse_phase))
            brush_arc(
                (berry_x - pulse_radius, berry_y - pulse_radius, berry_x + pulse_radius, berry_y + pulse_radius),
                205,
                430,
                thin,
            )

        # Sweetness is born at the mouth and rises into protected central white
        # space; it cannot be confused with either mouse on the branch.
        if phase >= 0.52:
            sweet = min(1.0, (phase - 0.52) / 0.36)
            dot_x = int(berry_x + (self.width * 0.54 - berry_x) * sweet)
            dot_y = int(berry_y + (self.height * 0.29 - berry_y) * sweet)
            radius = int(7 + 25 * sweet)
            if phase > 0.88:
                radius = max(20, int(32 - 10 * ((phase - 0.88) / 0.12)))
            draw.ellipse(
                (dot_x - radius, dot_y - radius, dot_x + radius, dot_y + radius),
                fill=final_ink,
            )

        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()


def generate_procedural_keyframes(
    specs: Sequence[Mapping[str, Any]],
    output_dir: Path,
    *,
    generator: ProceduralSumiEGenerator | None = None,
    fallback_reason: str | None = None,
) -> GenerationResult:
    if not specs:
        raise ValueError("at least one keyframe spec is required")
    generator = generator or ProceduralSumiEGenerator()
    output_dir.mkdir(parents=True, exist_ok=True)
    frames: list[GeneratedFrame] = []
    parent_id: str | None = None
    for index, spec in enumerate(specs):
        frame_id = str(spec.get("frame_id") or spec.get("fid") or f"G{index:03d}")
        raw = generator.render(spec, index, len(specs))
        report = validate_image_bytes(raw, expected_size=(generator.width, generator.height))
        if not report.passed:
            raise VisualValidationError("procedural fallback failed: " + "; ".join(report.failures))
        path = output_dir / f"{frame_id}.png"
        path.write_bytes(raw)
        prompt = build_frame_prompt(spec, first=index == 0)
        frames.append(
            GeneratedFrame(
                frame_id=frame_id,
                second=float(spec.get("second", spec.get("sec", index))),
                path=str(path),
                parent_frame_id=parent_id,
                provider=generator.provider_name,
                prompt_sha256=_sha256_bytes(prompt.encode("utf-8")),
                image_sha256=report.sha256,
                attempts=1,
                visual=asdict(report),
            )
        )
        parent_id = frame_id
    return GenerationResult(
        provider=generator.provider_name,
        frames=tuple(frames),
        usage={
            "image_requests": 0,
            "image_generations": 0,
            "image_edits": 0,
            "provider_usage": [],
            "measured_cost_usd": 0.0,
            "cost_complete": True,
        },
        retries=0,
        fallback_reason=fallback_reason,
    )


def generate_with_fallback(
    specs: Sequence[Mapping[str, Any]],
    output_dir: Path,
    *,
    adapter: OpenAIImageAdapter | None,
    allow_procedural_fallback: bool,
    max_retries: int = 2,
) -> GenerationResult:
    if adapter is not None:
        try:
            return generate_keyframes(
                specs,
                output_dir,
                adapter=adapter,
                max_retries=max_retries,
            )
        except (ImageGenerationError, VisualValidationError) as exc:
            if not allow_procedural_fallback:
                raise
            reason = f"{type(exc).__name__}: {exc}"
    elif allow_procedural_fallback:
        reason = "OpenAI image adapter unavailable"
    else:
        raise ImageGenerationError("OpenAI image adapter unavailable and fallback disabled")
    return generate_procedural_keyframes(specs, output_dir, fallback_reason=reason)


def _fit_delivery(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(image.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def expand_semantic_frames(
    generated: Sequence[GeneratedFrame | Mapping[str, Any]],
    schedule: Sequence[Mapping[str, Any]],
    duration_seconds: float,
    output_dir: Path,
    *,
    width: int = 1080,
    height: int = 1920,
) -> list[dict[str, Any]]:
    """Expand sparse accepted anchors into exactly three authored cells/second.

    Adjacent anchors are blended with a non-decreasing progress value.  The
    director's slot metadata remains attached to each cell, so the renderer and
    contact sheet can show the intended settle/change/land decision separately
    from paid image count.
    """
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if not generated:
        raise ValueError("at least one generated anchor is required")
    semantic_count = int(math.ceil(duration_seconds * 3.0 - 1e-9))
    output_dir.mkdir(parents=True, exist_ok=True)
    anchors: list[tuple[float, str, Image.Image]] = []
    for item in generated:
        if isinstance(item, GeneratedFrame):
            second, frame_id, path = item.second, item.frame_id, Path(item.path)
        else:
            second = float(item.get("second", item.get("sec", 0.0)))
            frame_id = str(item.get("frame_id", item.get("fid", "G000")))
            path = Path(str(item["path"]))
        anchors.append((second, frame_id, _fit_delivery(Image.open(path), (width, height))))
    anchors.sort(key=lambda value: value[0])
    if anchors[0][0] > 0.0:
        anchors.insert(0, (0.0, anchors[0][1], anchors[0][2].copy()))
    if anchors[-1][0] < duration_seconds:
        anchors.append((duration_seconds, anchors[-1][1], anchors[-1][2].copy()))

    results: list[dict[str, Any]] = []
    for index in range(semantic_count):
        timestamp = index / 3.0
        left = anchors[0]
        right = anchors[-1]
        for candidate in anchors[1:]:
            if candidate[0] >= timestamp:
                right = candidate
                break
            left = candidate
        span = max(right[0] - left[0], 1e-9)
        progress = min(1.0, max(0.0, (timestamp - left[0]) / span))
        image = Image.blend(left[2], right[2], progress)
        # Reassert exact white after interpolation and remove chromatic residue.
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        normalized = normalize_sumi_e_bytes(buffer.getvalue())
        path = output_dir / f"F{index:03d}.png"
        path.write_bytes(normalized)
        report = validate_image_bytes(normalized, expected_size=(width, height))
        if not report.passed:
            raise VisualValidationError(
                f"semantic F{index:03d} failed: " + "; ".join(report.failures)
            )
        sec = min(int(timestamp), max(len(schedule) - 1, 0))
        directed = dict(schedule[sec]) if schedule else {}
        micro = directed.get("micro") or []
        slot = index % 3
        micro_record = dict(micro[slot]) if len(micro) == 3 else {
            "role": ("settle", "change", "land")[slot],
            "delta": "monotonic ink interpolation",
            "amount": (0.25, 0.75, 1.0)[slot],
        }
        results.append(
            {
                "fid": f"F{index:03d}",
                "path": str(path),
                "t": round(timestamp, 6),
                "sec": sec,
                "slot": slot,
                "role": micro_record.get("role"),
                "verb": directed.get("verb", "settle"),
                "delta": micro_record.get("delta"),
                "amount": micro_record.get("amount"),
                "source_anchor": left[1],
                "target_anchor": right[1],
                "blend_progress": round(progress, 8),
                "sha256": report.sha256,
                "visual": asdict(report),
            }
        )
    return results


def generation_result_dict(result: GenerationResult) -> dict[str, Any]:
    return {
        "provider": result.provider,
        "frames": [asdict(frame) for frame in result.frames],
        "usage": dict(result.usage),
        "retries": result.retries,
        "fallback_reason": result.fallback_reason,
    }


__all__ = [
    "GPT_IMAGE_MODEL",
    "STYLE_LOCK_V3",
    "GeneratedFrame",
    "GenerationResult",
    "ImageGenerationError",
    "OpenAIImageAdapter",
    "ProceduralSumiEGenerator",
    "VisualReport",
    "VisualValidationError",
    "build_frame_prompt",
    "expand_semantic_frames",
    "generate_keyframes",
    "generate_procedural_keyframes",
    "generate_with_fallback",
    "generation_result_dict",
    "normalize_sumi_e_bytes",
    "validate_image_bytes",
    "validate_image_path",
]
