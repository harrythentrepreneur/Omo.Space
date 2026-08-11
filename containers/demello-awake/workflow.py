"""Request-scoped orchestration for the de Mello Awake media pipeline."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

try:  # Support both package imports and direct ``python workflow.py`` loading.
    from .image_gen import (
        GeneratedFrame,
        ImageGenerationError,
        OpenAIImageAdapter,
        expand_semantic_frames,
        generate_with_fallback,
        generation_result_dict,
        validate_image_path,
    )
    from .media import (
        MAX_AUDIO_BYTES,
        MediaError,
        acquire_audio,
        assemble_video,
        make_contact_sheet,
        normalize_audio,
        qa_video,
    )
except ImportError:  # pragma: no cover - exercised by container runner usage.
    from image_gen import (
        GeneratedFrame,
        ImageGenerationError,
        OpenAIImageAdapter,
        expand_semantic_frames,
        generate_with_fallback,
        generation_result_dict,
        validate_image_path,
    )
    from media import (
        MAX_AUDIO_BYTES,
        MediaError,
        acquire_audio,
        assemble_video,
        make_contact_sheet,
        normalize_audio,
        qa_video,
    )


STYLE_ID = "sumi-e-awake-v3"
TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe-2025-12-15"
DIRECTOR_MODEL = "deepseek-v4-flash"
VERBS = {
    "hold-breath", "settle", "descend", "rise", "expand", "contract",
    "drift-toward", "drift-away", "coil", "uncoil", "open", "close",
    "surge", "recede",
}
ROLE_PATTERNS = {
    "settle-change-land": ("settle", "change", "land"),
    "anticipate-act-recover": ("anticipate", "act", "recover"),
    "hold-breathe-hold": ("hold", "breathe", "hold"),
}
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


class WorkflowError(RuntimeError):
    """A fail-closed request or pipeline phase error."""


@dataclass(frozen=True)
class Transcript:
    text: str
    segments: tuple[Mapping[str, Any], ...]
    language: str
    duration_seconds: float
    model: str
    usage: Mapping[str, Any]


@dataclass
class PipelineConfig:
    artifact_root: Path
    work_root: Path = Path("/tmp/omo-demello-awake")
    audio_refs: Mapping[str, Path] = field(default_factory=dict)
    transcript_refs: Mapping[str, Path] = field(default_factory=dict)
    allow_procedural_fallback: bool = False
    max_image_retries: int = 2
    max_audio_bytes: int = MAX_AUDIO_BYTES
    anchor_interval_seconds: int = 4
    guarded_price_usd: float = 0.10
    static_estimate_usd: float = 0.25
    keep_work: bool = False
    artifact_url_builder: Callable[[str], str] | None = None


@dataclass
class PipelineDependencies:
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run
    downloader: Callable[..., Path] | None = None
    transcriber: Callable[[Path], Transcript | Mapping[str, Any]] | None = None
    director: Callable[[Transcript, float], Mapping[str, Any]] | None = None
    image_adapter: OpenAIImageAdapter | None = None
    clock: Callable[[], float] = time.perf_counter


def _strict_keys(value: Mapping[str, Any], allowed: set[str], context: str) -> None:
    extra = set(value) - allowed
    if extra:
        raise WorkflowError(f"{context} has unsupported fields: {', '.join(sorted(extra))}")


def validate_input(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the direct input or extract a future server-owned envelope."""
    if not isinstance(raw, Mapping):
        raise WorkflowError("workflow input must be an object")
    if "validated_input" in raw or "input" in raw:
        candidate = raw.get("validated_input", raw.get("input"))
        if not isinstance(candidate, Mapping):
            raise WorkflowError("envelope input must be an object")
        run_id = raw.get("run_id")
        max_cost = raw.get("max_cost_usd")
        payload = dict(candidate)
        if run_id is not None:
            payload["run_id"] = run_id
        if max_cost is not None:
            payload["max_cost_usd"] = max_cost
    else:
        payload = dict(raw)
    _strict_keys(
        payload,
        {"audio_url", "audio_ref", "style", "duration_bounds", "run_id", "max_cost_usd"},
        "input",
    )
    if bool(payload.get("audio_url")) == bool(payload.get("audio_ref")):
        raise WorkflowError("exactly one of audio_url or audio_ref is required")
    if payload.get("style") != STYLE_ID:
        raise WorkflowError(f"style must be {STYLE_ID!r}")
    bounds = payload.get("duration_bounds")
    if not isinstance(bounds, Mapping):
        raise WorkflowError("duration_bounds must be an object")
    _strict_keys(bounds, {"min_seconds", "max_seconds"}, "duration_bounds")
    try:
        minimum = float(bounds["min_seconds"])
        maximum = float(bounds["max_seconds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkflowError("duration bounds must be numbers") from exc
    if minimum < 5 or maximum > 20 or maximum < minimum:
        raise WorkflowError("duration bounds must satisfy 5 <= min <= max <= 20")
    run_id = payload.get("run_id")
    if run_id is not None and (not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id)):
        raise WorkflowError("run_id has an invalid format")
    max_cost = payload.get("max_cost_usd")
    if max_cost is not None:
        try:
            max_cost = float(max_cost)
        except (TypeError, ValueError) as exc:
            raise WorkflowError("max_cost_usd must be a number") from exc
        if not math.isfinite(max_cost) or max_cost <= 0:
            raise WorkflowError("max_cost_usd must be positive")
    payload["duration_bounds"] = {"min_seconds": minimum, "max_seconds": maximum}
    payload["max_cost_usd"] = max_cost
    return payload


def _provider_json(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if "choices" not in payload:
        return payload
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise WorkflowError("director response has no choices[0].message.content") from exc
    if not isinstance(content, str) or content.lstrip().startswith("```"):
        raise WorkflowError("director must return bare JSON without fences")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise WorkflowError("director returned invalid JSON") from exc
    if not isinstance(parsed, Mapping):
        raise WorkflowError("director JSON must be an object")
    return parsed


def _coerce_transcript(value: Transcript | Mapping[str, Any], duration: float) -> Transcript:
    if isinstance(value, Transcript):
        return value
    text = str(value.get("text", "")).strip()
    if not text:
        raise WorkflowError("transcription is empty")
    segments = value.get("segments") or []
    if not isinstance(segments, Sequence):
        raise WorkflowError("transcription segments must be an array")
    return Transcript(
        text=text,
        segments=tuple(dict(item) for item in segments if isinstance(item, Mapping)),
        language=str(value.get("language", "en")),
        duration_seconds=float(value.get("duration", value.get("duration_seconds", duration))),
        model=str(value.get("model", TRANSCRIPTION_MODEL)),
        usage=dict(value.get("usage") or {}),
    )


def transcribe_openai(
    audio: Path,
    *,
    api_key: str | None = None,
    request: Callable[..., Mapping[str, Any]] | None = None,
    model: str = TRANSCRIPTION_MODEL,
    timeout_seconds: float = 120.0,
) -> Transcript:
    """Transcribe one bounded clip through the OpenAI transcription endpoint."""
    key = api_key or os.environ.get("OPENAI_API_KEY")
    try:
        if request is not None:
            payload = request(audio=audio, model=model)
        else:
            if not key:
                raise WorkflowError("OPENAI_API_KEY is not configured")
            import httpx
            with audio.open("rb") as handle:
                response = httpx.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {key}"},
                    data={
                        "model": model,
                        "language": "en",
                        "response_format": "json",
                    },
                    files={"file": (audio.name, handle, "audio/mp4")},
                    timeout=timeout_seconds,
                )
            response.raise_for_status()
            payload = response.json()
    except WorkflowError:
        raise
    except Exception as exc:
        raise WorkflowError(f"transcription request failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise WorkflowError("transcription response is not an object")
    duration = float(payload.get("duration", 0.0) or 0.0)
    return _coerce_transcript(dict(payload) | {"model": model}, duration)


def director_schema() -> dict[str, Any]:
    micro = {
        "type": "object",
        "additionalProperties": False,
        "required": ["role", "delta", "amount"],
        "properties": {
            "role": {"type": "string"},
            "delta": {"type": "string", "minLength": 5, "maxLength": 240},
            "amount": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }
    second = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "sec", "spoken_meaning", "verb", "target", "pattern", "micro", "protected", "pivot"
        ],
        "properties": {
            "sec": {"type": "integer", "minimum": 0},
            "spoken_meaning": {"type": "string", "minLength": 1, "maxLength": 300},
            "verb": {"type": "string", "enum": sorted(VERBS)},
            "target": {"type": "string", "minLength": 1, "maxLength": 120},
            "pattern": {"type": "string", "enum": sorted(ROLE_PATTERNS)},
            "micro": {"type": "array", "minItems": 3, "maxItems": 3, "items": micro},
            "protected": {
                "type": "array", "minItems": 1, "maxItems": 6,
                "items": {"type": "string", "minLength": 1, "maxLength": 80},
            },
            "pivot": {"type": "boolean"},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["version", "seconds"],
        "properties": {
            "version": {"const": "demello-director-v3"},
            "seconds": {"type": "array", "items": second},
        },
    }


def validate_director_plan(plan: Mapping[str, Any], duration_seconds: float) -> dict[str, Any]:
    _strict_keys(plan, {"version", "seconds", "usage", "provider"}, "director plan")
    if plan.get("version") != "demello-director-v3":
        raise WorkflowError("director plan version mismatch")
    seconds = plan.get("seconds")
    expected = int(math.ceil(duration_seconds - 1e-9))
    if not isinstance(seconds, Sequence) or len(seconds) != expected:
        raise WorkflowError(f"director plan must contain exactly {expected} seconds")
    validated: list[dict[str, Any]] = []
    allowed = {"sec", "spoken_meaning", "verb", "target", "pattern", "micro", "protected", "pivot"}
    for index, raw in enumerate(seconds):
        if not isinstance(raw, Mapping):
            raise WorkflowError(f"director second {index} must be an object")
        _strict_keys(raw, allowed, f"director second {index}")
        if raw.get("sec") != index:
            raise WorkflowError(f"director second index mismatch at {index}")
        verb = raw.get("verb")
        pattern = raw.get("pattern")
        if verb not in VERBS or pattern not in ROLE_PATTERNS:
            raise WorkflowError(f"director second {index} has invalid verb/pattern")
        if not str(raw.get("spoken_meaning", "")).strip() or not str(raw.get("target", "")).strip():
            raise WorkflowError(f"director second {index} has empty semantic fields")
        protected = raw.get("protected")
        if not isinstance(protected, Sequence) or isinstance(protected, (str, bytes)) or not protected:
            raise WorkflowError(f"director second {index} has invalid protected anchors")
        micro = raw.get("micro")
        if not isinstance(micro, Sequence) or len(micro) != 3:
            raise WorkflowError(f"director second {index} must contain three micro deltas")
        expected_roles = ROLE_PATTERNS[str(pattern)]
        amounts: list[float] = []
        clean_micro: list[dict[str, Any]] = []
        for slot, item in enumerate(micro):
            if not isinstance(item, Mapping):
                raise WorkflowError(f"director micro {index}.{slot} must be an object")
            _strict_keys(item, {"role", "delta", "amount"}, f"director micro {index}.{slot}")
            if item.get("role") != expected_roles[slot] or len(str(item.get("delta", ""))) < 5:
                raise WorkflowError(f"director micro {index}.{slot} has invalid role/delta")
            amount = float(item.get("amount", -1))
            if not 0 < amount <= 1:
                raise WorkflowError(f"director micro {index}.{slot} amount is invalid")
            amounts.append(amount)
            clean_micro.append({"role": item["role"], "delta": str(item["delta"]), "amount": amount})
        if not amounts[0] < amounts[1] < amounts[2]:
            raise WorkflowError(f"director second {index} micro amounts are not monotonic")
        validated.append(
            {
                "sec": index,
                "spoken_meaning": str(raw["spoken_meaning"]).strip(),
                "verb": str(verb),
                "target": str(raw["target"]).strip(),
                "pattern": str(pattern),
                "micro": clean_micro,
                "protected": [str(value) for value in protected],
                "pivot": bool(raw.get("pivot")),
            }
        )
    return {
        "version": "demello-director-v3",
        "seconds": validated,
        "usage": dict(plan.get("usage") or {}),
        "provider": str(plan.get("provider", "unknown")),
    }


def direct_opencode(
    transcript: Transcript,
    duration_seconds: float,
    *,
    api_key: str | None = None,
    request: Callable[..., Mapping[str, Any]] | None = None,
    base_url: str | None = None,
    model: str = DIRECTOR_MODEL,
) -> dict[str, Any]:
    key = api_key or os.environ.get("OPENCODE_GO_API_KEY")
    endpoint = (
        base_url
        or os.environ.get("OPENCODE_GO_BASE_URL")
        or "https://opencode.ai/zen/go/v1"
    ).rstrip("/")
    prompt = (
        "Direct this Anthony de Mello audio as sparse black-on-white sumi-e. "
        "Return only strict JSON matching the supplied schema. Create exactly "
        f"{int(math.ceil(duration_seconds - 1e-9))} second records. Each second "
        "has one primary motion verb and exactly three same-direction cumulative "
        "micro deltas with amounts 0.25, 0.75, 1.0. Keep camera fixed; edits must "
        "follow the spoken meaning and protect figure identity, through-line, and white field.\n\n"
        f"Transcript: {transcript.text[:12000]}"
    )
    try:
        if request is not None:
            payload = request(
                model=model,
                prompt=prompt,
                schema=director_schema(),
                duration_seconds=duration_seconds,
            )
        else:
            if not key:
                raise WorkflowError("OPENCODE_GO_API_KEY is not configured")
            import httpx
            response = httpx.post(
                f"{endpoint}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": "You are a precise animation director. Output JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            payload = response.json()
    except WorkflowError:
        raise
    except Exception as exc:
        raise WorkflowError(f"director request failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise WorkflowError("director response is not an object")
    parsed = dict(_provider_json(payload))
    parsed.setdefault("provider", model)
    if isinstance(payload.get("usage"), Mapping):
        parsed["usage"] = dict(payload["usage"])
    return validate_director_plan(parsed, duration_seconds)


def _meaning_for_second(transcript: Transcript, sec: int) -> str:
    texts: list[str] = []
    for segment in transcript.segments:
        try:
            start, end = float(segment.get("start", 0)), float(segment.get("end", 0))
        except (TypeError, ValueError):
            continue
        if start < sec + 1 and end > sec:
            texts.append(str(segment.get("text", "")).strip())
    if texts:
        return " ".join(value for value in texts if value)[:280]
    words = transcript.text.split()
    total = max(1, int(math.ceil(transcript.duration_seconds)))
    start = math.floor(len(words) * sec / total)
    end = math.ceil(len(words) * (sec + 1) / total)
    return " ".join(words[start:end])[:280] or "the spoken thought continues"


def deterministic_director(transcript: Transcript, duration_seconds: float) -> dict[str, Any]:
    seconds: list[dict[str, Any]] = []
    for sec in range(int(math.ceil(duration_seconds - 1e-9))):
        meaning = _meaning_for_second(transcript, sec)
        lower = meaning.lower()
        if any(word in lower for word in ("wake", "open", "see", "taste", "sweet")):
            verb, target, pivot = "open", "awareness aperture and through-line", True
        elif any(word in lower for word in ("fall", "down", "sleep", "die", "death")):
            verb, target, pivot = "descend", "existing figure posture", "fall" in lower
        elif any(word in lower for word in ("rise", "lift", "up", "born")):
            verb, target, pivot = "rise", "existing figure and life-line", False
        elif any(word in lower for word in ("inside", "brain", "thought", "bound")):
            verb, target, pivot = "coil", "existing through-line tip", False
        elif any(word in lower for word in ("all", "world", "grow", "large")):
            verb, target, pivot = "expand", "existing through-line extent", False
        else:
            verb, target, pivot = "settle", "existing through-line endpoint", False
        pattern = "anticipate-act-recover" if pivot else "settle-change-land"
        roles = ROLE_PATTERNS[pattern]
        direction = "upward" if verb in {"rise", "open", "expand"} else "downward" if verb == "descend" else "forward"
        seconds.append(
            {
                "sec": sec,
                "spoken_meaning": meaning,
                "verb": verb,
                "target": target,
                "pattern": pattern,
                "micro": [
                    {"role": roles[0], "delta": f"move the {target} {direction} by 0.0025", "amount": 0.25},
                    {"role": roles[1], "delta": f"continue the same {direction} edit to 0.0075", "amount": 0.75},
                    {"role": roles[2], "delta": f"land the same {direction} edit at 0.0100", "amount": 1.0},
                ],
                "protected": ["main figure identity", "through-line continuity", "white margins"],
                "pivot": pivot,
            }
        )
    return validate_director_plan(
        {"version": "demello-director-v3", "seconds": seconds, "provider": "deterministic-fallback", "usage": {}},
        duration_seconds,
    )


def direct_with_fallback(
    transcript: Transcript,
    duration_seconds: float,
    *,
    director: Callable[[Transcript, float], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if director is not None:
        try:
            return validate_director_plan(director(transcript, duration_seconds), duration_seconds)
        except Exception as exc:
            fallback = deterministic_director(transcript, duration_seconds)
            fallback["fallback_reason"] = f"{type(exc).__name__}: {exc}"
            return fallback
    try:
        return direct_opencode(transcript, duration_seconds)
    except Exception as exc:
        fallback = deterministic_director(transcript, duration_seconds)
        fallback["fallback_reason"] = f"{type(exc).__name__}: {exc}"
        return fallback


def select_anchor_specs(plan: Mapping[str, Any], duration_seconds: float, interval: int = 4) -> list[dict[str, Any]]:
    if interval < 1:
        raise ValueError("anchor interval must be positive")
    times = [float(value) for value in range(0, int(duration_seconds), interval)]
    if not times or times[0] != 0.0:
        times.insert(0, 0.0)
    if abs(times[-1] - duration_seconds) > 1e-9:
        times.append(duration_seconds)
    seconds = plan["seconds"]
    specs: list[dict[str, Any]] = []
    for index, timestamp in enumerate(times):
        directed = seconds[min(int(timestamp), len(seconds) - 1)]
        specs.append(
            {
                "frame_id": f"G{index:03d}",
                "second": timestamp,
                "role": "act" if directed["pivot"] else "land",
                "meaning": directed["spoken_meaning"],
                "verb": directed["verb"],
                "delta": directed["micro"][-1]["delta"],
                "protected": directed["protected"],
                "pivot": directed["pivot"],
            }
        )
    return specs


def select_semantic_specs(plan: Mapping[str, Any], duration_seconds: float) -> list[dict[str, Any]]:
    """Compile one authored fallback drawing state for every 3 fps cell."""
    count = int(math.ceil(duration_seconds * 3 - 1e-9))
    seconds = plan["seconds"]
    specs: list[dict[str, Any]] = []
    for index in range(count):
        timestamp = index / 3.0
        directed = seconds[min(int(timestamp), len(seconds) - 1)]
        micro = directed["micro"][index % 3]
        specs.append(
            {
                "frame_id": f"G{index:03d}",
                "second": timestamp,
                "role": micro["role"],
                "meaning": directed["spoken_meaning"],
                "verb": directed["verb"],
                "delta": micro["delta"],
                "protected": directed["protected"],
                "pivot": directed["pivot"],
            }
        )
    return specs


def _phase(telemetry: dict[str, float], name: str, started: float, clock: Callable[[], float]) -> None:
    telemetry[name] = round(clock() - started, 6)


def _mark_phase(run_dir: Path, phase: str) -> None:
    allowed = {"acquire", "transcribe", "direct", "generate", "semantic", "assemble", "qa", "contract"}
    if phase not in allowed:
        raise WorkflowError("invalid internal phase marker")
    (run_dir / "diagnostic.json").write_text(
        json.dumps({"phase": phase}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _url(config: PipelineConfig, key: str, path: Path) -> str:
    if config.artifact_url_builder is not None:
        return config.artifact_url_builder(key)
    return path.resolve().as_uri()


def _explicit_usage_cost(usage: Mapping[str, Any]) -> float | None:
    value = usage.get("measured_cost_usd", usage.get("cost_usd"))
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _transcription_cost(usage: Mapping[str, Any]) -> float | None:
    explicit = _explicit_usage_cost(usage)
    if explicit is not None:
        return explicit
    try:
        input_tokens = float(usage.get("input_tokens", 0) or 0)
        output_tokens = float(usage.get("output_tokens", 0) or 0)
        details = usage.get("input_token_details")
        if not isinstance(details, Mapping):
            details = usage.get("input_tokens_details")
        details = details if isinstance(details, Mapping) else {}
        audio_tokens = float(details.get("audio_tokens", input_tokens) or 0)
    except (TypeError, ValueError):
        return None
    if not audio_tokens and not output_tokens:
        return None
    return (audio_tokens * 1.25 + output_tokens * 5.0) / 1_000_000


def run_pipeline(
    raw_request: Mapping[str, Any],
    config: PipelineConfig,
    dependencies: PipelineDependencies | None = None,
) -> dict[str, Any]:
    """Run one isolated request and atomically persist only a QA-passing result."""
    deps = dependencies or PipelineDependencies()
    request = validate_input(raw_request)
    if (
        request.get("max_cost_usd") is not None
        and config.static_estimate_usd > float(request["max_cost_usd"])
    ):
        raise WorkflowError("max_cost_usd is below this release's static delivered-cost estimate")
    run_id = str(request.get("run_id") or uuid.uuid4().hex)
    if not RUN_ID_RE.fullmatch(run_id):
        raise WorkflowError("run_id has an invalid format")
    runs_root = config.artifact_root / "runs"
    final_dir = runs_root / run_id
    if final_dir.exists() and (
        not final_dir.is_dir()
        or any((final_dir / name).exists() for name in ("video.mp4", "contact-sheet.jpg", "result.json"))
    ):
        raise WorkflowError("run artifact path already contains workflow outputs")
    runs_root.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)
    config.work_root.mkdir(parents=True, exist_ok=True)
    job_dir = config.work_root / f"{run_id}-{uuid.uuid4().hex}"
    stage_dir = runs_root / f".{run_id}.{uuid.uuid4().hex}.staging"
    job_dir.mkdir(parents=True)
    stage_dir.mkdir(parents=True)
    telemetry: dict[str, float] = {}
    pipeline_started = deps.clock()
    completed = False
    try:
        _mark_phase(final_dir, "acquire")
        started = deps.clock()
        acquired = job_dir / "source-audio.bin"
        acquire_kwargs: dict[str, Any] = {
            "audio_refs": config.audio_refs,
            "max_bytes": config.max_audio_bytes,
        }
        if deps.downloader is not None:
            acquire_kwargs["downloader"] = deps.downloader
        acquired, source_kind = acquire_audio(request, acquired, **acquire_kwargs)
        bounds = request["duration_bounds"]
        audio_info = normalize_audio(
            acquired,
            job_dir / "audio.m4a",
            min_seconds=bounds["min_seconds"],
            max_seconds=bounds["max_seconds"],
            runner=deps.command_runner,
        )
        _phase(telemetry, "acquire_audio_seconds", started, deps.clock)

        _mark_phase(final_dir, "transcribe")
        started = deps.clock()
        transcript_ref = config.transcript_refs.get(str(request.get("audio_ref", "")))
        if deps.transcriber is not None:
            transcript = _coerce_transcript(deps.transcriber(Path(audio_info.path)), audio_info.duration_seconds)
        elif transcript_ref is not None:
            bundled = json.loads(transcript_ref.read_text(encoding="utf-8"))
            if not isinstance(bundled, Mapping):
                raise WorkflowError("bundled transcript is invalid")
            transcript = _coerce_transcript(bundled, audio_info.duration_seconds)
        else:
            transcript = transcribe_openai(Path(audio_info.path))
        if transcript.duration_seconds <= 0:
            transcript = Transcript(
                text=transcript.text,
                segments=transcript.segments,
                language=transcript.language,
                duration_seconds=audio_info.duration_seconds,
                model=transcript.model,
                usage=transcript.usage,
            )
        _phase(telemetry, "transcribe_seconds", started, deps.clock)

        _mark_phase(final_dir, "direct")
        started = deps.clock()
        if transcript_ref is not None and deps.director is None:
            plan = deterministic_director(transcript, audio_info.duration_seconds)
        else:
            plan = direct_with_fallback(
                transcript,
                audio_info.duration_seconds,
                director=deps.director,
            )
        _phase(telemetry, "direct_seconds", started, deps.clock)

        _mark_phase(final_dir, "generate")
        started = deps.clock()
        if transcript_ref is not None:
            anchor_specs = select_semantic_specs(plan, audio_info.duration_seconds)
        else:
            anchor_specs = select_anchor_specs(
                plan,
                audio_info.duration_seconds,
                config.anchor_interval_seconds,
            )
        image_adapter = deps.image_adapter
        if image_adapter is None and transcript_ref is None and os.environ.get("OPENAI_API_KEY"):
            image_adapter = OpenAIImageAdapter()
        generation = generate_with_fallback(
            anchor_specs,
            job_dir / "generated",
            adapter=image_adapter,
            allow_procedural_fallback=config.allow_procedural_fallback,
            max_retries=config.max_image_retries,
        )
        _phase(telemetry, "generate_seconds", started, deps.clock)

        _mark_phase(final_dir, "semantic")
        started = deps.clock()
        semantic = expand_semantic_frames(
            generation.frames,
            plan["seconds"],
            audio_info.duration_seconds,
            job_dir / "semantic",
        )
        contact = make_contact_sheet(semantic, job_dir / "contact-sheet.jpg")
        _phase(telemetry, "semantic_expand_seconds", started, deps.clock)

        _mark_phase(final_dir, "assemble")
        started = deps.clock()
        assembly = assemble_video(
            semantic,
            Path(audio_info.path),
            job_dir / "video.mp4",
            job_dir / "render",
            duration_seconds=audio_info.duration_seconds,
            runner=deps.command_runner,
        )
        _phase(telemetry, "assemble_seconds", started, deps.clock)

        _mark_phase(final_dir, "qa")
        started = deps.clock()
        qa = qa_video(
            Path(assembly.video_path),
            expected_duration_seconds=assembly.duration_seconds,
            expected_frames=assembly.frame_count,
            qa_dir=job_dir / "qa",
            runner=deps.command_runner,
            visual_validator=lambda path: validate_image_path(path, expected_size=(1080, 1920)),
        )
        _phase(telemetry, "qa_seconds", started, deps.clock)

        _mark_phase(final_dir, "contract")
        video_key = f"runs/{run_id}/video.mp4"
        contact_key = f"runs/{run_id}/contact-sheet.jpg"
        shutil.copy2(assembly.video_path, stage_dir / "video.mp4")
        shutil.copy2(contact, stage_dir / "contact-sheet.jpg")
        image_usage = dict(generation.usage)
        image_cost = _explicit_usage_cost(image_usage)
        transcript_cost = _transcription_cost(dict(transcript.usage))
        director_cost = _explicit_usage_cost(dict(plan.get("usage") or {}))
        known_costs = [value for value in (image_cost, transcript_cost, director_cost) if value is not None]
        explicit_cost = sum(known_costs)
        cost_complete = bool(image_usage.get("cost_complete")) and image_cost is not None
        if request.get("max_cost_usd") is not None and explicit_cost > float(request["max_cost_usd"]):
            raise WorkflowError("measured provider cost exceeds max_cost_usd")
        result = {
            "run_id": run_id,
            "status": "completed",
            "video_url": _url(config, video_key, final_dir / "video.mp4"),
            "contact_sheet_url": _url(config, contact_key, final_dir / "contact-sheet.jpg"),
            "artifact_keys": {"video": video_key, "contact_sheet": contact_key},
            "generation_provider": generation.provider,
            "generation_fallback_reason": generation.fallback_reason,
            "frames_used": {
                "generated": len(generation.frames),
                "semantic": len(semantic),
                "output": assembly.frame_count,
            },
            "cost": {
                "measured_usd": round(explicit_cost, 8),
                "cost_complete": cost_complete,
                "guarded_price_usd": config.guarded_price_usd,
                "currency": "USD",
            },
            "media": {
                "duration_seconds": qa["duration_seconds"],
                "video_codec": qa["video_codec"],
                "audio_codec": qa["audio_codec"],
                "width": qa["width"],
                "height": qa["height"],
                "fps": qa["fps"],
                "bytes": qa["bytes"],
                "sha256": qa["sha256"],
            },
            "audio": asdict(audio_info) | {"acquisition": source_kind},
            "transcription": {
                "model": transcript.model,
                "language": transcript.language,
                "characters": len(transcript.text),
                "segments": len(transcript.segments),
                "usage": dict(transcript.usage),
            },
            "director": {
                "provider": plan.get("provider"),
                "fallback_reason": plan.get("fallback_reason"),
                "seconds": len(plan["seconds"]),
                "usage": dict(plan.get("usage") or {}),
            },
            "image_generation": generation_result_dict(generation),
            "assembly": asdict(assembly),
            "qa": qa,
            "telemetry": telemetry,
        }
        telemetry["total_seconds"] = round(deps.clock() - pipeline_started, 6)
        (stage_dir / "result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for staged in stage_dir.iterdir():
            os.replace(staged, final_dir / staged.name)
        stage_dir.rmdir()
        (final_dir / "diagnostic.json").unlink(missing_ok=True)
        completed = True
        return result
    except MediaError as exc:
        # Preserve only allow-listed QA check names. This is enough to diagnose
        # ffmpeg/runtime differences without persisting paths, provider bodies,
        # request data, or arbitrary exception text.
        prefix = "delivery QA failed: "
        message = str(exc)
        if message.startswith(prefix):
            allowed_checks = {
                "duration", "audio_duration", "frame_count", "resolution", "fps",
                "video_h264", "audio_aac", "faststart", "nonempty", "visual_samples",
            }
            check_text = message[len(prefix):].split(" | ", 1)[0]
            failed_checks = [
                name.strip()
                for name in check_text.split(",")
                if name.strip() in allowed_checks
            ]
            diagnostic: dict[str, Any] = {
                "phase": "qa", "failed_checks": sorted(set(failed_checks))
            }
            duration_match = re.search(
                r" \| audio_duration_seconds=([0-9]+(?:\.[0-9]+)?)"
                r" \| expected_duration_seconds=([0-9]+(?:\.[0-9]+)?)$",
                message,
            )
            if duration_match:
                diagnostic["audio_duration_seconds"] = float(duration_match.group(1))
                diagnostic["expected_duration_seconds"] = float(duration_match.group(2))
            (final_dir / "diagnostic.json").write_text(
                json.dumps(diagnostic, separators=(",", ":"))
                + "\n",
                encoding="utf-8",
            )
        raise
    except (ImageGenerationError, WorkflowError):
        raise
    except Exception as exc:
        raise WorkflowError(f"pipeline failed: {type(exc).__name__}: {exc}") from exc
    finally:
        if stage_dir.exists() and not completed:
            shutil.rmtree(stage_dir)
        if not config.keep_work and job_dir.exists():
            shutil.rmtree(job_dir)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_evidence(path: Path, key: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise WorkflowError(f"missing regular artifact: {key}")
    return {"key": key, "sha256": _sha256_file(path), "bytes": path.stat().st_size}


def _typed_runner_result(envelope: Mapping[str, Any], rich: Mapping[str, Any], config: PipelineConfig) -> dict[str, Any]:
    run_id = str(rich["run_id"])
    final_dir = config.artifact_root / "runs" / run_id
    video_key = f"runs/{run_id}/video.mp4"
    contact_key = f"runs/{run_id}/contact-sheet.jpg"
    image_usage = rich.get("image_generation", {}).get("usage", {})
    transcript_usage = rich.get("transcription", {}).get("usage", {})
    director_usage = rich.get("director", {}).get("usage", {})
    image_cost = _explicit_usage_cost(image_usage) if isinstance(image_usage, Mapping) else None
    transcript_cost = _transcription_cost(transcript_usage) if isinstance(transcript_usage, Mapping) else None
    director_cost = _explicit_usage_cost(director_usage) if isinstance(director_usage, Mapping) else None
    wall_seconds = float(rich.get("telemetry", {}).get("total_seconds", 0) or 0)
    provider = str(rich.get("generation_provider"))
    return {
        "run_id": run_id,
        "status": "completed",
        "artifacts": {
            "video": _artifact_evidence(final_dir / "video.mp4", video_key),
            "contact_sheet": _artifact_evidence(final_dir / "contact-sheet.jpg", contact_key),
        },
        "frames_used": dict(rich["frames_used"]),
        "usage": {
            "provider_costs_usd": {
                "transcription": round(float(transcript_cost or 0), 8),
                "director": round(float(director_cost or 0), 8),
                "image_generation": round(float(image_cost or 0), 8),
            },
            "modal_cpu_core_seconds": round(wall_seconds, 6),
            "modal_memory_gib_seconds": round(wall_seconds * 2.0, 6),
            "artifact_storage_usd": 0.0,
            "artifact_egress_usd": 0.0,
        },
        "pricing_history": {
            "static_estimate_usd": config.static_estimate_usd,
            "successful_delivered_usd": [],
            "delivered_7d_usd": 0.0,
            "delivered_30d_usd": 0.0,
        },
        "media": {
            key: rich["media"][key]
            for key in ("duration_seconds", "video_codec", "audio_codec", "width", "height", "fps")
        },
        "generation_provider": "procedural-fallback" if provider == "procedural-fallback" else "openai",
    }


def run_from_files(request_path: Path, result_path: Path) -> None:
    if not request_path.is_absolute() or not result_path.is_absolute():
        raise WorkflowError("runner paths must be absolute")
    if not request_path.is_file() or request_path.is_symlink() or result_path.exists():
        raise WorkflowError("runner paths are invalid")
    envelope = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(envelope, Mapping):
        raise WorkflowError("runner request must be an object")
    run_id = str(envelope.get("run_id", ""))
    if not RUN_ID_RE.fullmatch(run_id):
        raise WorkflowError("runner request has an invalid run_id")
    artifact_root = Path(str(envelope.get("artifact_root", "")))
    run_artifact_dir = Path(str(envelope.get("run_artifact_dir", "")))
    if not artifact_root.is_absolute() or run_artifact_dir != artifact_root / "runs" / run_id:
        raise WorkflowError("runner artifact scope is invalid")
    root = Path(__file__).resolve().parent
    workflow_input = envelope.get("validated_input", envelope.get("input", envelope))
    is_bundled_fixture = (
        isinstance(workflow_input, Mapping)
        and workflow_input.get("audio_ref") == "sample-demello-10s"
    )
    config = PipelineConfig(
        artifact_root=artifact_root,
        audio_refs={"sample-demello-10s": root / "assets" / "sample-demello-10s.m4a"},
        transcript_refs={
            "sample-demello-10s": root / "assets" / "sample-demello-10s.transcript.json"
        },
        anchor_interval_seconds=3,
        allow_procedural_fallback=os.environ.get("DEMELLO_PROCEDURAL_FALLBACK_ENABLED", "0") == "1",
        # The fixture is the measured no-provider reference lane. Arbitrary customer
        # audio retains the conservative provider-backed estimate until credentials
        # and delivered-cost history are available in the Worker ledger.
        static_estimate_usd=(
            0.003
            if is_bundled_fixture
            else float(os.environ.get("DEMELLO_STATIC_COST_USD", "0.25"))
        ),
    )
    rich = run_pipeline(envelope, config)
    typed = _typed_runner_result(envelope, rich, config)
    encoded = (json.dumps(typed, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    descriptor = os.open(result_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the de Mello Awake typed workflow")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        run_from_files(arguments.request, arguments.result)
    except Exception:
        return 1
    return 0


__all__ = [
    "DIRECTOR_MODEL",
    "PipelineConfig",
    "PipelineDependencies",
    "STYLE_ID",
    "TRANSCRIPTION_MODEL",
    "Transcript",
    "WorkflowError",
    "deterministic_director",
    "direct_opencode",
    "direct_with_fallback",
    "director_schema",
    "run_pipeline",
    "run_from_files",
    "select_anchor_specs",
    "select_semantic_specs",
    "transcribe_openai",
    "validate_director_plan",
    "validate_input",
]


if __name__ == "__main__":
    raise SystemExit(main())
