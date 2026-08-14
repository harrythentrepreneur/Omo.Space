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
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageOps


GPT_IMAGE_MODEL = "gpt-image-2-2026-04-21"
CODEX_IMAGE_PROVIDER = "chatgpt-codex-image-generation"
CODEX_RESPONSES_MODEL = "gpt-5.6-terra"
CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
CODEX_REFRESH_URL = "https://auth.openai.com/oauth/token"
# Public OAuth client identifier used by the open-source Codex CLI. This is an
# identifier, not a credential; access and refresh tokens remain Modal Secrets.
CODEX_OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
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


def _codex_sse_image_result(lines: Sequence[str] | Any) -> str:
    """Extract one final image payload from Codex Responses SSE lines."""
    result: str | None = None
    failed = False
    for line in lines:
        if not isinstance(line, str) or not line.startswith("data: "):
            continue
        try:
            event = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        if event_type == "response.output_item.done":
            item = event.get("item")
            if isinstance(item, Mapping) and item.get("type") == "image_generation_call":
                candidate = item.get("result")
                if isinstance(candidate, str) and candidate:
                    result = candidate
        elif event_type == "response.image_generation_call.completed":
            candidate = event.get("result")
            if isinstance(candidate, str) and candidate:
                result = candidate
        elif event_type == "response.failed":
            failed = True
        elif event_type == "response.completed":
            break
    if failed:
        raise ImageGenerationError("Codex image response reported failure")
    if not result:
        raise ImageGenerationError("Codex image response contained no final image")
    return result


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


class CodexSubscriptionImageAdapter:
    """ChatGPT-subscription image client through the Codex Responses route.

    ChatGPT OAuth access tokens do not have the public ``api.images`` scope.
    The Codex backend does, however, expose the Responses image-generation
    tool to an entitled account. The transport stays injectable so tests never
    require a subscription or network access.

    An optional refresh token follows the open-source Codex CLI JSON refresh
    request. Refreshed credentials are memory-only. A server deployment still
    needs a controlled secret-rotation owner because a scale-to-zero container
    cannot persist a rotated refresh token back into a Modal Secret.
    """

    model = CODEX_IMAGE_PROVIDER

    def __init__(
        self,
        *,
        access_token: str | None = None,
        account_id: str | None = None,
        refresh_token: str | None = None,
        request: ProviderRequest | None = None,
        base_url: str | None = None,
        refresh_url: str | None = None,
        responses_model: str | None = None,
        timeout_seconds: float = 180.0,
        size: str = "1024x1536",
        quality: str = "medium",
        allow_refresh: bool = True,
    ) -> None:
        self.access_token = access_token or os.environ.get("OPENAI_CODEX_ACCESS_TOKEN")
        self.account_id = account_id or os.environ.get("OPENAI_CODEX_ACCOUNT_ID")
        self.allow_refresh = allow_refresh
        self.refresh_token = (
            refresh_token or os.environ.get("OPENAI_CODEX_REFRESH_TOKEN")
            if allow_refresh
            else None
        )
        self.request = request
        self.base_url = (base_url or os.environ.get("OPENAI_CODEX_BASE_URL") or CODEX_BASE_URL).rstrip("/")
        self.refresh_url = refresh_url or os.environ.get("OPENAI_CODEX_REFRESH_URL") or CODEX_REFRESH_URL
        self.responses_model = (
            responses_model
            or os.environ.get("OPENAI_CODEX_RESPONSES_MODEL")
            or CODEX_RESPONSES_MODEL
        )
        self.timeout_seconds = timeout_seconds
        self.size = size
        self.quality = quality

    @staticmethod
    def _jwt_expiration(token: str | None) -> int | None:
        if not token or token.count(".") != 2:
            return None
        try:
            encoded = token.split(".", 2)[1]
            encoded += "=" * (-len(encoded) % 4)
            payload = json.loads(base64.urlsafe_b64decode(encoded))
            expiration = payload.get("exp")
            return int(expiration) if isinstance(expiration, (int, float)) else None
        except Exception:
            return None

    def _refresh_if_needed(self) -> str:
        expiration = self._jwt_expiration(self.access_token)
        if self.access_token and (expiration is None or expiration > int(time.time()) + 300):
            return self.access_token
        if not self.allow_refresh or not self.refresh_token:
            if self.access_token:
                return self.access_token
            raise ImageGenerationError("OPENAI_CODEX_ACCESS_TOKEN is not configured")
        try:
            import httpx

            response = httpx.post(
                self.refresh_url,
                headers={"Content-Type": "application/json"},
                json={
                    "client_id": CODEX_OAUTH_CLIENT_ID,
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                timeout=min(self.timeout_seconds, 30.0),
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise ImageGenerationError(
                f"Codex OAuth refresh failed: {type(exc).__name__}"
            ) from exc
        access_token = payload.get("access_token") if isinstance(payload, Mapping) else None
        if not isinstance(access_token, str) or not access_token:
            raise ImageGenerationError("Codex OAuth refresh returned no access token")
        rotated = payload.get("refresh_token")
        self.access_token = access_token
        if isinstance(rotated, str) and rotated:
            self.refresh_token = rotated
        return access_token

    def _http_request(self, *, prompt: str, parent: bytes | None) -> Mapping[str, Any]:
        if not self.account_id:
            raise ImageGenerationError("OPENAI_CODEX_ACCOUNT_ID is not configured")
        token = self._refresh_if_needed()
        try:
            import httpx
        except ImportError as exc:
            raise ImageGenerationError("httpx is required for Codex image requests") from exc

        content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
        if parent is not None:
            encoded_parent = base64.b64encode(parent).decode("ascii")
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{encoded_parent}",
                    "detail": "high",
                }
            )
        body = {
            "model": self.responses_model,
            "instructions": (
                "Use the image-generation tool exactly once. Return no prose. "
                "When an input image is present, edit it according to the prompt."
            ),
            "input": [{"role": "user", "content": content}],
            "tools": [
                {
                    "type": "image_generation",
                    "quality": self.quality,
                    "size": self.size,
                }
            ],
            "tool_choice": {"type": "image_generation"},
            "parallel_tool_calls": False,
            "store": False,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "ChatGPT-Account-Id": self.account_id,
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "OpenAI-Beta": "responses=experimental",
            "User-Agent": "omo-demello-awake/0.1.0",
            "originator": "codex_cli_rs",
            "session_id": str(uuid.uuid4()),
        }
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/responses",
                headers=headers,
                json=body,
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()
                result = _codex_sse_image_result(response.iter_lines())
        except Exception as exc:
            if isinstance(exc, ImageGenerationError):
                raise
            raise ImageGenerationError(
                f"Codex image request failed: {type(exc).__name__}"
            ) from exc
        return {"data": [{"b64_json": result}], "usage": {}}

    def generate(self, prompt: str, *, parent: bytes | None = None) -> tuple[bytes, Mapping[str, Any]]:
        try:
            if self.request is not None:
                payload = self.request(
                    edit=parent is not None,
                    prompt=prompt,
                    parent=parent,
                    model=self.responses_model,
                    size=self.size,
                    quality=self.quality,
                )
            else:
                payload = self._http_request(prompt=prompt, parent=parent)
        except ImageGenerationError:
            raise
        except Exception as exc:
            raise ImageGenerationError(
                f"Codex image request failed: {type(exc).__name__}: {exc}"
            ) from exc
        data = payload.get("data")
        if not isinstance(data, Sequence) or not data or not isinstance(data[0], Mapping):
            raise ImageGenerationError("Codex image response has no data[0] object")
        encoded = data[0].get("b64_json")
        if not isinstance(encoded, str) or not encoded:
            raise ImageGenerationError("Codex image response has no base64 payload")
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ImageGenerationError("Codex image response contains invalid base64") from exc
        if not decoded:
            raise ImageGenerationError("Codex image response decoded to zero bytes")
        # Subscription Responses does not currently return a billable USD cost
        # for the image tool. Leave usage empty so cost_complete remains false.
        return decoded, {}


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
    """Deterministic, disclosed fallback; it never impersonates model output.

    The fallback is authored as geometry at the semantic 3 fps cadence.  It is
    rendered on a supersampled delivery canvas and flattened back to two ink
    values, so brush edges are smooth without introducing gray wash.  Motion
    is a redraw of the geometry: in particular, the sweetness mark has exactly
    one position in every frame and is never represented by two cross-faded
    circles.
    """

    provider_name = "procedural-fallback"

    def __init__(
        self,
        *,
        width: int = 1080,
        height: int = 1920,
        supersample: int = 2,
    ) -> None:
        if width < 540 or height < 960:
            raise ValueError("procedural canvas must be at least 540x960")
        if supersample not in {1, 2, 3}:
            raise ValueError("supersample must be 1, 2, or 3")
        self.width = width
        self.height = height
        self.supersample = supersample

    def render(self, spec: Mapping[str, Any], index: int, total: int) -> bytes:
        if total < 1 or not 0 <= index < total:
            raise ValueError("procedural frame index is outside the sequence")
        ss = self.supersample
        canvas_width, canvas_height = self.width * ss, self.height * ss
        image = Image.new("RGB", (canvas_width, canvas_height), "white")
        draw = ImageDraw.Draw(image)
        phase = index / max(total - 1, 1)
        ink = (26, 26, 26)

        def point(value: tuple[float, float]) -> tuple[int, int]:
            return round(value[0] * canvas_width), round(value[1] * canvas_height)

        def quadratic(
            start: tuple[float, float],
            control: tuple[float, float],
            end: tuple[float, float],
            *,
            steps: int = 24,
        ) -> list[tuple[float, float]]:
            return [
                (
                    (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0],
                    (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1],
                )
                for t in (value / steps for value in range(steps + 1))
            ]

        def brush_line(
            points: Sequence[tuple[float, float]],
            width: float = 8.0,
            end_width: float | None = None,
        ) -> None:
            """Paint a smooth, tapered brush path with rounded ink bristles."""
            if len(points) < 2:
                return
            target = end_width if end_width is not None else max(1.0, width * 0.24)
            samples: list[tuple[float, float]] = [points[0]]
            for start, end in zip(points, points[1:]):
                distance = math.hypot(
                    (end[0] - start[0]) * self.width,
                    (end[1] - start[1]) * self.height,
                )
                count = max(2, min(36, math.ceil(distance / 8)))
                samples.extend(
                    (
                        start[0] + (end[0] - start[0]) * step / count,
                        start[1] + (end[1] - start[1]) * step / count,
                    )
                    for step in range(1, count + 1)
                )
            for segment, (start, end) in enumerate(zip(samples, samples[1:])):
                ratio = segment / max(len(samples) - 2, 1)
                segment_width = max(1, round((width + (target - width) * ratio) * ss))
                start_px, end_px = point(start), point(end)
                draw.line((start_px, end_px), fill=ink, width=segment_width)
                radius = max(1, segment_width // 2)
                draw.ellipse(
                    (
                        end_px[0] - radius,
                        end_px[1] - radius,
                        end_px[0] + radius,
                        end_px[1] + radius,
                    ),
                    fill=ink,
                )

        def brush_arc(
            box: tuple[float, float, float, float],
            start: float,
            end: float,
            width: float = 6.0,
            end_width: float = 1.5,
        ) -> None:
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            rx, ry = (box[2] - box[0]) / 2, (box[3] - box[1]) / 2
            steps = max(12, round(abs(end - start) / 6))
            brush_line(
                [
                    (
                        cx + rx * math.cos(math.radians(start + (end - start) * step / steps)),
                        cy + ry * math.sin(math.radians(start + (end - start) * step / steps)),
                    )
                    for step in range(steps + 1)
                ],
                width,
                end_width,
            )

        def ink_dot(center: tuple[float, float], radius_px: float) -> None:
            cx, cy = point(center)
            radius = round(radius_px * ss)
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=ink)

        def leaf(center: tuple[float, float], direction: float, size: float = 0.028) -> None:
            dx, dy = math.cos(direction) * size, math.sin(direction) * size * 0.58
            px, py = -dy * 0.45, dx * 0.45
            start = center
            end = (center[0] + dx, center[1] + dy)
            brush_line(quadratic(start, (center[0] + dx * 0.5 + px, center[1] + dy * 0.5 + py), end), 4.6, 1.2)
            brush_line(quadratic(end, (center[0] + dx * 0.5 - px, center[1] + dy * 0.5 - py), start), 3.0, 1.0)
            brush_line([start, end], 2.0, 0.8)

        def render_berry(center: tuple[float, float], radius: float = 0.019) -> None:
            cx, cy = center
            brush_arc((cx - radius, cy - radius, cx + radius, cy + radius), 20, 350, 6.0, 2.0)
            brush_line([(cx, cy - radius * 0.75), (cx - 0.006, cy - radius * 1.35)], 4.0, 1.0)
            leaf((cx - 0.004, cy - radius * 1.20), 3.72, radius * 1.25)
            leaf((cx - 0.003, cy - radius * 1.20), 5.68, radius * 1.12)

        def transformed(
            values: Sequence[tuple[float, float]],
            scale: float,
            shift_y: float,
        ) -> list[tuple[float, float]]:
            cx, cy = 0.54, 0.48
            return [
                (cx + (x - cx) * scale, cy + (y - cy) * scale + shift_y)
                for x, y in values
            ]

        def wide_scene(*, berry_progress: float | None, scale: float, shift_y: float) -> None:
            def scene(values: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
                return transformed(values, scale, shift_y)

            weight = max(3.5, 8.5 * scale)
            hairline = max(1.2, 3.2 * scale)

            # Crag and a full striped tiger silhouette, visually separate from
            # the branch. The animal faces the hanging figure across the gap.
            brush_line(scene([(0.055, 0.43), (0.11, 0.34), (0.17, 0.31), (0.235, 0.35), (0.285, 0.43)]), weight + 2, 1.5)
            brush_line(scene(quadratic((0.075, 0.43), (0.13, 0.50), (0.20, 0.56))), weight, 1.5)
            brush_line(scene(quadratic((0.12, 0.275), (0.20, 0.225), (0.292, 0.272))), weight, 2.0)
            brush_line(scene(quadratic((0.292, 0.272), (0.33, 0.245), (0.355, 0.278))), weight, 1.5)
            brush_line(scene([(0.355, 0.278), (0.382, 0.292), (0.349, 0.306), (0.292, 0.31), (0.205, 0.318), (0.125, 0.292)]), weight, 2.0)
            brush_line(scene([(0.314, 0.262), (0.326, 0.235), (0.341, 0.265)]), weight, 1.0)
            brush_line(scene([(0.23, 0.313), (0.226, 0.349)]), weight, 1.0)
            brush_line(scene([(0.30, 0.307), (0.304, 0.345)]), weight, 1.0)
            brush_line(scene(quadratic((0.13, 0.278), (0.052, 0.22), (0.085, 0.145))), weight, 1.0)
            brush_line(scene(quadratic((0.085, 0.145), (0.12, 0.13), (0.13, 0.165))), hairline, 1.0)
            for stripe in (0.18, 0.215, 0.25):
                brush_line(scene([(stripe, 0.252), (stripe + 0.014, 0.285)]), weight, 1.0)
            brush_line(scene([(0.343, 0.281), (0.354, 0.283)]), hairline, 1.0)
            ink_dot(scene([(0.348, 0.277)])[0], max(2.2, 3.2 * scale))
            for offset in (-0.006, 0.004):
                brush_line(scene([(0.358, 0.294 + offset), (0.402, 0.286 + offset)]), hairline, 0.8)

            # A cut branch crosses the composition. Two mouse silhouettes face
            # their separate gnaw points; ears, eyes, pointed noses, and tails
            # keep them distinct from decorative blobs.
            brush_line(scene([(0.285, 0.372), (0.51, 0.364), (0.705, 0.375), (0.91, 0.351)]), weight + 3, 2.0)
            brush_line(scene([(0.90, 0.351), (0.938, 0.326)]), 5.0 * scale, 1.0)
            for mx, direction in ((0.42, 1), (0.71, -1)):
                body = scene(quadratic((mx - 0.042 * direction, 0.352), (mx, 0.316), (mx + 0.039 * direction, 0.348)))
                belly = scene(quadratic((mx + 0.039 * direction, 0.348), (mx, 0.373), (mx - 0.042 * direction, 0.352)))
                brush_line(body, weight, 1.6)
                brush_line(belly, weight * 0.75, 1.2)
                ear = mx + 0.010 * direction
                brush_arc(tuple(scene([(ear - 0.014, 0.313), (ear + 0.014, 0.343)])[0] + scene([(ear - 0.014, 0.313), (ear + 0.014, 0.343)])[1]), 10, 345, hairline, 1.0)
                nose = scene([(mx + 0.043 * direction, 0.349)])[0]
                eye = scene([(mx + 0.020 * direction, 0.335)])[0]
                ink_dot(nose, max(2.0, 2.6 * scale))
                ink_dot(eye, max(1.5, 2.0 * scale))
                brush_line(scene(quadratic((mx - 0.04 * direction, 0.351), (mx - 0.09 * direction, 0.325), (mx - 0.105 * direction, 0.365))), hairline, 0.8)
                brush_line(scene([(mx + 0.041 * direction, 0.353), (mx + 0.061 * direction, 0.363)]), hairline, 0.8)

            # A robed figure hangs below the branch. Three curved fingers wrap
            # the branch; the other articulated hand lifts the leafed berry.
            head_center = scene([(0.605, 0.485)])[0]
            head_rx, head_ry = 0.027 * scale, 0.032 * scale
            brush_arc((head_center[0] - head_rx, head_center[1] - head_ry, head_center[0] + head_rx, head_center[1] + head_ry), 70, 420, weight, 1.5)
            brush_line(scene(quadratic((0.578, 0.515), (0.505, 0.455), (0.538, 0.374))), weight, 1.5)
            brush_line(scene([(0.518, 0.374), (0.558, 0.374)]), weight * 0.72, 1.2)
            for finger_x in (0.528, 0.539, 0.550):
                brush_arc(tuple(scene([(finger_x - 0.010, 0.356), (finger_x + 0.010, 0.384)])[0] + scene([(finger_x - 0.010, 0.356), (finger_x + 0.010, 0.384)])[1]), 175, 375, hairline, 0.8)
            brush_line(scene([(0.574, 0.516), (0.525, 0.675), (0.602, 0.702), (0.640, 0.522)]), weight + 1, 2.0)
            brush_line(scene([(0.548, 0.577), (0.616, 0.585)]), hairline, 1.0)
            brush_line(scene([(0.538, 0.674), (0.488, 0.775), (0.466, 0.786)]), weight, 1.0)
            brush_line(scene([(0.593, 0.695), (0.653, 0.774), (0.680, 0.779)]), weight, 1.0)

            if berry_progress is not None:
                eased = berry_progress * berry_progress * (3 - 2 * berry_progress)
                berry = (
                    0.755 + (0.652 - 0.755) * eased,
                    0.620 + (0.488 - 0.620) * eased,
                )
                hand = (berry[0] + 0.012, berry[1] + 0.026)
                brush_line(scene(quadratic((0.632, 0.535), (0.70, 0.57 - 0.08 * eased), hand)), weight, 1.5)
                for finger in (0.0, 0.008, 0.016):
                    brush_line(scene([(hand[0] + finger, hand[1]), (berry[0] + 0.010 + finger * 0.25, berry[1] + 0.010)]), hairline, 0.8)
                berry_scene = scene([berry])[0]
                render_berry(berry_scene, 0.019 * scale)
                # A short mouth stroke keeps berry-to-lips contact legible.
                brush_line(scene([(0.628, 0.486), (0.647, 0.488)]), hairline, 0.8)

        def closeup(close_progress: float) -> None:
            # Editorial side-profile insert: recognizable forehead, nose, open
            # lips, chin, eye, fingers, and a leafed berry at the lip line.
            brush_line(quadratic((0.275, 0.29), (0.47, 0.16), (0.61, 0.315)), 13.0, 2.0)
            brush_line(quadratic((0.61, 0.315), (0.64, 0.355), (0.60, 0.395)), 8.0, 1.5)
            brush_line([(0.60, 0.395), (0.635, 0.425), (0.595, 0.438)], 7.5, 1.5)
            brush_line(quadratic((0.595, 0.438), (0.64, 0.455), (0.595, 0.472)), 7.0, 1.2)
            brush_line(quadratic((0.595, 0.472), (0.56, 0.56), (0.43, 0.585)), 10.0, 1.5)
            brush_line(quadratic((0.43, 0.585), (0.30, 0.54), (0.275, 0.29)), 11.0, 2.0)
            brush_line(quadratic((0.47, 0.36), (0.525, 0.34), (0.56, 0.368)), 6.0, 1.0)
            ink_dot((0.535, 0.363), 3.2)
            brush_line([(0.60, 0.438), (0.626, 0.438)], 5.0, 1.0)
            berry_x = 0.705 + (0.635 - 0.705) * min(1.0, close_progress * 2.5)
            berry = (berry_x, 0.445)
            render_berry(berry, 0.025)
            for finger, y in enumerate((0.48, 0.50, 0.522)):
                brush_line(quadratic((0.86, 0.59 + finger * 0.015), (0.76, y + 0.02), (berry_x + 0.018, y)), 8.0 - finger, 1.3)
            brush_line(quadratic((0.82, 0.63), (0.74, 0.59), (berry_x + 0.025, 0.535)), 10.0, 1.5)
            if 0.16 <= close_progress <= 0.82:
                pulse = (close_progress - 0.16) / 0.66
                radius = 0.035 + 0.035 * math.sin(math.pi * pulse)
                # Exactly one deliberately broken taste ripple.
                brush_arc((0.615 - radius, 0.445 - radius, 0.615 + radius, 0.445 + radius), 215, 432, 5.5, 1.0)

        if phase < 0.29:
            wide_scene(berry_progress=min(1.0, phase / 0.25), scale=1.0, shift_y=0.0)
        elif phase < 0.51:
            closeup((phase - 0.29) / 0.22)
        else:
            recede = min(1.0, max(0.0, (phase - 0.53) / 0.29))
            if phase < 0.84:
                wide_scene(
                    berry_progress=None,
                    scale=1.0 - 0.42 * recede,
                    shift_y=-0.055 * recede,
                )

            # One mouth-born mark is redrawn at one continuous geometric
            # position per authored cell. It is the only ink in the last beat.
            sweet = min(1.0, max(0.0, (phase - 0.51) / 0.34))
            eased = sweet * sweet * (3 - 2 * sweet)
            dot_x = 0.650 + (0.52 - 0.650) * eased
            dot_y = 0.485 + (0.31 - 0.485) * eased
            radius = 9.0 + 30.0 * eased
            if phase > 0.90:
                radius -= 9.0 * ((phase - 0.90) / 0.10)
            ink_dot((dot_x, dot_y), radius)

        if ss > 1:
            image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return normalize_sumi_e_bytes(buffer.getvalue())


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

    A dense 3 fps authored chain is copied cell-for-cell. Sparse provider
    anchors retain the legacy difference interpolation here, but procedural
    frames never pass through a crossfade that could duplicate moved topology.
    The director's slot metadata remains attached to each cell.
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
    dense_authored = len(anchors) == semantic_count and all(
        abs(anchor[0] - index / 3.0) <= 1e-6
        for index, anchor in enumerate(anchors)
    )
    if anchors[0][0] > 0.0:
        anchors.insert(0, (0.0, anchors[0][1], anchors[0][2].copy()))
    if anchors[-1][0] < duration_seconds:
        anchors.append((duration_seconds, anchors[-1][1], anchors[-1][2].copy()))

    results: list[dict[str, Any]] = []
    for index in range(semantic_count):
        timestamp = index / 3.0
        if dense_authored:
            left = right = anchors[index]
            progress = 0.0
            image = left[2].copy()
        else:
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
                "transition_mode": "authored-redraw" if dense_authored else "anchor-blend",
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
    "CODEX_IMAGE_PROVIDER",
    "CodexSubscriptionImageAdapter",
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
