"""Fixture-only Modal-compatible runtime for audio-symbolic-animation.

The executable lane is intentionally narrow: it accepts a reviewed fixture_id,
produces deterministic local media artifacts, and refuses production/provider
audio or image generation before any work is created.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import math
import shutil
import struct
import subprocess
import tempfile
import uuid
import wave
import zlib
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

try:
    import modal
except Exception:  # pragma: no cover - local contract tests do not need Modal.
    class _NoopImage:
        @classmethod
        def debian_slim(cls, **_kwargs: Any) -> "_NoopImage":
            return cls()

        def apt_install(self, *_packages: str) -> "_NoopImage":
            return self

        def uv_pip_install(self, *_packages: str) -> "_NoopImage":
            return self

        def add_local_dir(self, *_args: Any, **_kwargs: Any) -> "_NoopImage":
            return self

        def add_local_file(self, *_args: Any, **_kwargs: Any) -> "_NoopImage":
            return self

    class _NoopFunction:
        def __init__(self, fn):
            self.fn = fn

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return self.fn(*args, **kwargs)

        def spawn(self, *args: Any, **kwargs: Any) -> Any:
            class _Call:
                object_id = "fc-localfixture"
            self.fn(*args, **kwargs)
            return _Call()

    class _NoopApp:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def function(self, **_kwargs: Any):
            return lambda fn: _NoopFunction(fn)

    class _NoopModal:
        Image = _NoopImage
        App = _NoopApp

        @staticmethod
        def concurrent(**_kwargs: Any):
            return lambda fn: fn

        @staticmethod
        def asgi_app(**_kwargs: Any):
            return lambda fn: fn

    modal = _NoopModal()  # type: ignore[assignment]

from jsonschema import Draft202012Validator, ValidationError


APP_NAME = "cognition-audio-symbolic-animation"
WORKFLOW_VERSION = "audio-symbolic-animation@0.2.0-fixture"
EXECUTION_KIND = "media-sequential"
AVAILABILITY = "fixture_only"
LOCAL_ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = Path("/root/audio_symbolic_animation")
RUN_ID_RE = "run_"
FIXTURE_IDS = {"tone-thread-3s": 3}
STAGES = ["accepted", "transcribed", "briefed", "frames", "assembled", "validated", "complete"]


class InputRejected(ValueError):
    """Raised before any file work when input does not match the fixture lane."""


class WorkflowNotReady(RuntimeError):
    """Raised before spend when the reviewed production workflow cannot run live."""


class ProviderUnavailable(RuntimeError):
    """Raised before any file work when the production provider lane is requested."""


Executor = Callable[[dict[str, Any]], dict[str, Any]]


def _asset_root() -> Path:
    return LOCAL_ROOT if (LOCAL_ROOT / "schemas" / "input.json").is_file() else IMAGE_ROOT


@lru_cache(maxsize=None)
def load_json(relative_path: str) -> dict[str, Any]:
    return json.loads((_asset_root() / relative_path).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    schema = load_json(f"schemas/{name}")
    Draft202012Validator.check_schema(schema)
    return schema


def validate_instance(instance: Any, schema_name: str) -> None:
    Draft202012Validator(load_schema(schema_name)).validate(instance)


def readiness() -> dict[str, Any]:
    return load_json("manifest.json")["readiness"]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_canonical_json(value), encoding="utf-8")


def _write_fixture_wav(path: Path, seconds: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16_000
    samples = bytearray()
    for index in range(seconds * sample_rate):
        tone = int(2400 * math.sin(2 * math.pi * 220 * index / sample_rate))
        samples.extend(struct.pack("<h", tone))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(samples))


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def _transcript(duration: float) -> dict[str, Any]:
    words = ["hold", "one", "thread", "then", "open"]
    step = duration / len(words)
    return {
        "text": "hold one thread then open",
        "language": "en",
        "duration_seconds": duration,
        "model": "fixture-deterministic-wav",
        "words": [
            {"word": word, "start": round(index * step, 3), "end": round((index + 1) * step, 3)}
            for index, word in enumerate(words)
        ],
    }


def _brief(duration: float) -> dict[str, Any]:
    verbs = ["hold", "release", "open"]
    frame_count = int(math.ceil(duration))
    frames = []
    for index in range(frame_count):
        threads_remaining = max(0, frame_count - index - 1)
        frames.append(
            {
                "fid": f"F{index:03d}",
                "second": index,
                "verb": verbs[min(index, len(verbs) - 1)],
                "prompt": (
                    f"F{index:03d} @ {index}s CU CHANGE ONLY: thread count becomes "
                    f"{threads_remaining}; keep the same hand, same white field, black ink only."
                ),
                "mechanical_state": {
                    "anchor": "one open hand",
                    "threads_remaining": threads_remaining,
                    "monotonic": True,
                },
            }
        )
    return {
        "generation_fps": 1,
        "style": "sumi-e",
        "machine": "thread-release",
        "frames": frames,
    }


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def _draw_line(pixels: bytearray, width: int, height: int, start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int]) -> None:
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                x, y = x0 + ox, y0 + oy
                if 0 <= x < width and 0 <= y < height:
                    offset = (y * width + x) * 3
                    pixels[offset : offset + 3] = bytes(color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _write_png(path: Path, width: int, height: int, frame_index: int, total: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pixels = bytearray([255] * width * height * 3)
    black = (24, 24, 24)
    center_x = width // 2
    hand_y = int(height * 0.72)
    _draw_line(pixels, width, height, (center_x - 58, hand_y), (center_x + 58, hand_y), black)
    _draw_line(pixels, width, height, (center_x - 26, hand_y), (center_x - 62, hand_y + 58), black)
    _draw_line(pixels, width, height, (center_x + 26, hand_y), (center_x + 62, hand_y + 58), black)
    remaining = max(0, total - frame_index - 1)
    for thread in range(remaining):
        x = center_x - 44 + thread * 44
        _draw_line(pixels, width, height, (x, int(height * 0.24)), (x + 10, hand_y - 8), black)
    if remaining == 0:
        _draw_line(pixels, width, height, (center_x - 18, int(height * 0.34)), (center_x + 18, int(height * 0.30)), black)
    raw = b"".join(b"\x00" + pixels[row * width * 3 : (row + 1) * width * 3] for row in range(height))
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def _artifact(root: Path, path: Path, kind: str, content_type: str, ttl_seconds: int = 3600) -> dict[str, Any]:
    expires = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=ttl_seconds)
    relative = str(path.relative_to(root))
    return {
        "kind": kind,
        "object_key": relative,
        "sha256": _sha256_file(path),
        "bytes": path.stat().st_size,
        "content_type": content_type,
        "url": f"/v1/artifacts/{relative}",
        "ttl_seconds": ttl_seconds,
        "delete_after": expires.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def _run_ffmpeg(frames_pattern: Path, audio: Path, video: Path, duration: float) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for the fixture media contract")
    video.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            "1",
            "-i",
            str(frames_pattern),
            "-i",
            str(audio),
            "-t",
            f"{duration:.3f}",
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-movflags",
            "+faststart",
            str(video),
        ],
        check=True,
    )


def _probe_video(video: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required for the fixture media contract")
    raw = subprocess.check_output(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,codec_name,width,height",
            "-of",
            "json",
            str(video),
        ],
        text=True,
    )
    data = json.loads(raw)
    streams = {stream["codec_type"]: stream for stream in data["streams"]}
    return {
        "duration_seconds": float(data["format"]["duration"]),
        "width": int(streams["video"]["width"]),
        "height": int(streams["video"]["height"]),
        "fps": 30,
        "video_codec": streams["video"]["codec_name"],
        "audio_codec": streams["audio"]["codec_name"],
    }


def _normalize_input(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InputRejected("input must be an object")
    if "fixture_id" not in payload:
        if "audio_ref" in payload or "audio_artifact" in payload:
            raise ProviderUnavailable("production image provider is unavailable for this workflow")
        raise InputRejected("fixture_id is required")
    try:
        validate_instance(payload, "fixture-input.json")
    except ValidationError as exc:
        raise InputRejected(exc.message) from exc
    fixture_id = str(payload["fixture_id"])
    duration = int(payload["duration_seconds"])
    if FIXTURE_IDS.get(fixture_id) != duration:
        raise InputRejected("fixture_id and duration_seconds do not match a reviewed fixture")
    return {"fixture_id": fixture_id, "duration_seconds": duration, "style": "sumi-e"}


def _production_not_ready_error() -> WorkflowNotReady:
    state = readiness()
    return WorkflowNotReady("; ".join(reason["code"] for reason in state["blockers"]))


def execute_workflow(
    payload: dict[str, Any],
    *,
    executor: Executor | None = None,
    work_root: str | Path | None = None,
) -> dict[str, Any]:
    if executor is not None:
        validate_instance(payload, "input.json")
        result = executor(payload)
        validate_instance(result, "output.json")
        return result

    if isinstance(payload, dict) and "audio_artifact" in payload:
        validate_instance(payload, "input.json")
        raise _production_not_ready_error()

    normalized = _normalize_input(payload)
    root = Path(work_root) if work_root is not None else Path(tempfile.mkdtemp(prefix="audio-symbolic-fixture-"))
    root.mkdir(parents=True, exist_ok=True)
    run_id = "run_" + hashlib.sha256(_canonical_json(normalized).encode("utf-8")).hexdigest()[:24]
    duration = normalized["duration_seconds"]
    run_root = root
    audio = run_root / "input.wav"
    transcript_path = run_root / "transcript.json"
    brief_path = run_root / "mechanical-brief.json"
    frames_dir = run_root / "frames"
    video = run_root / "video.mp4"

    progress = [{"stage": "accepted", "pct": 5}]
    _write_fixture_wav(audio, duration)
    actual_duration = _wav_duration(audio)
    transcript = _transcript(actual_duration)
    _write_json(transcript_path, transcript)
    progress.append({"stage": "transcribed", "pct": 20})
    brief = _brief(actual_duration)
    _write_json(brief_path, brief)
    progress.append({"stage": "briefed", "pct": 35})
    for index, _frame in enumerate(brief["frames"]):
        _write_png(frames_dir / f"F{index:03d}.png", 270, 480, index, len(brief["frames"]))
    progress.append({"stage": "frames", "pct": 60, "completed": len(brief["frames"]), "total": len(brief["frames"])})
    _run_ffmpeg(frames_dir / "F%03d.png", audio, video, actual_duration)
    progress.append({"stage": "assembled", "pct": 85})
    media = _probe_video(video)
    if media["width"] != 1080 or media["height"] != 1920 or media["video_codec"] != "h264" or media["audio_codec"] != "aac":
        raise RuntimeError("ffprobe media contract failed")
    if abs(media["duration_seconds"] - actual_duration) > 0.2:
        raise RuntimeError("ffprobe duration contract failed")
    progress.append({"stage": "validated", "pct": 95})

    artifacts = [
        _artifact(run_root, video, "video", "video/mp4"),
        _artifact(run_root, transcript_path, "transcript", "application/json"),
        _artifact(run_root, brief_path, "mechanical_brief", "application/json"),
    ]
    frame_artifacts = [
        _artifact(run_root, frame, "frame", "image/png")
        for frame in sorted(frames_dir.glob("F*.png"))
    ]
    artifacts.extend(frame_artifacts)
    by_kind = {artifact["kind"]: artifact for artifact in artifacts if artifact["kind"] != "frame"}
    progress.append({"stage": "complete", "pct": 100})
    result = {
        "run_id": run_id,
        "status": "completed",
        "workflow_version": WORKFLOW_VERSION,
        "runtime": {
            "classification": EXECUTION_KIND,
            "availability": AVAILABILITY,
            "provider": "deterministic_fixture",
        },
        "progress": progress,
        "transcript": {"object_key": "transcript.json", "sha256": _sha256_file(transcript_path), **transcript},
        "mechanical_brief": {"object_key": "mechanical-brief.json", "sha256": _sha256_file(brief_path), **brief},
        "artifacts": artifacts,
        "artifacts_by_kind": by_kind,
        "media": media,
        "usage": {
            "generated_frames": len(frame_artifacts),
            "accepted_frames": len(frame_artifacts),
            "provider_cost_usd": 0,
        },
    }
    validate_instance(result, "output.json")
    _write_json(run_root / "result.json", result)
    return result


runtime_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")
    .uv_pip_install("modal==1.5.0", "fastapi==0.109.0", "jsonschema==4.26.0")
    .add_local_dir(LOCAL_ROOT / "schemas", IMAGE_ROOT / "schemas", copy=True)
    .add_local_file(LOCAL_ROOT / "manifest.json", str(IMAGE_ROOT / "manifest.json"), copy=True)
)

app = modal.App(APP_NAME)


@app.function(image=runtime_image, cpu=2.0, memory=1024, timeout=120, min_containers=0, max_containers=2)
def run_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    return execute_workflow(payload)


SpawnRunner = Callable[[dict[str, Any]], str]
LookupResult = Callable[[str], dict[str, Any]]


def create_fastapi_app(
    spawn_runner: SpawnRunner | None = None,
    lookup_result: LookupResult | None = None,
    *,
    ready_override: bool | None = None,
    work_root: str | Path | None = None,
    require_proxy_auth: bool = True,
) -> Any:
    from fastapi import Body, FastAPI, Header, HTTPException
    from fastapi.responses import JSONResponse

    web = FastAPI(title="audio-symbolic-animation fixture preview", version="0.2.0")
    root = Path(work_root) if work_root is not None else Path(tempfile.mkdtemp(prefix="audio-symbolic-api-"))
    runs: dict[str, dict[str, Any]] = {}
    idempotency: dict[str, str] = {}

    def default_spawn(payload: dict[str, Any]) -> str:
        return run_workflow.spawn(payload).object_id

    def default_lookup(call_id: str) -> dict[str, Any]:
        return modal.FunctionCall.from_id(call_id).get(timeout=0)

    spawn = spawn_runner or default_spawn
    lookup = lookup_result or default_lookup

    def auth_error(modal_key: str | None, modal_secret: str | None) -> JSONResponse | None:
        if not require_proxy_auth:
            return None
        if not modal_key or not modal_secret:
            return JSONResponse({"status": "failed", "error": {"code": "MODAL_PROXY_AUTH_REQUIRED"}}, status_code=401)
        return None

    @web.post("/v1/runs", status_code=202)
    async def submit(
        body: Any = Body(...),
    ) -> Any:
        try:
            validate_instance(body, "input.json")
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc

        state = readiness()
        can_submit = state["can_submit"] if ready_override is None else ready_override
        if not can_submit:
            return JSONResponse(
                {
                    "status": "not_ready",
                    "error": {
                        "code": "WORKFLOW_NOT_READY",
                        "blockers": state["blockers"],
                    },
                },
                status_code=503,
            )

        call_id = spawn(body)
        run_id = str(uuid.uuid4())
        return {
            "run_id": run_id,
            "call_id": call_id,
            "status": "accepted",
            "result_url": f"/v1/runs/{call_id}",
        }

    @web.get("/v1/runs/{call_id}")
    async def get_result(call_id: str) -> Any:
        try:
            result = lookup(call_id)
            validate_instance(result, "output.json")
            return result
        except TimeoutError:
            return JSONResponse({"call_id": call_id, "status": "running"}, status_code=202)
        except Exception:
            return JSONResponse({"call_id": call_id, "status": "failed", "error": {"code": "RUN_FAILED"}}, status_code=500)

    @web.post("/v1/fixture-runs", status_code=202)
    async def submit_fixture(
        body: Any = Body(...),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        modal_key: str | None = Header(default=None, alias="Modal-Key"),
        modal_secret: str | None = Header(default=None, alias="Modal-Secret"),
    ) -> Any:
        maybe_auth = auth_error(modal_key, modal_secret)
        if maybe_auth is not None:
            return maybe_auth
        if not idempotency_key or len(idempotency_key) < 8:
            return JSONResponse({"status": "failed", "error": {"code": "INVALID_IDEMPOTENCY_KEY"}}, status_code=400)
        try:
            if not isinstance(body, dict):
                raise InputRejected("input must be an object")
            _normalize_input(body)
        except ProviderUnavailable:
            return JSONResponse({"status": "failed", "error": {"code": "PROVIDER_UNAVAILABLE"}}, status_code=503)
        except Exception as exc:
            return JSONResponse({"status": "failed", "error": {"code": "INVALID_INPUT", "message": str(exc)}}, status_code=422)
        request_hash = hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()
        if idempotency_key in idempotency:
            run_id = idempotency[idempotency_key]
            row = runs[run_id]
            if row["request_hash"] != request_hash:
                return JSONResponse({"status": "failed", "error": {"code": "IDEMPOTENCY_CONFLICT"}}, status_code=409)
            return {
                "run_id": run_id,
                "status": row["status"],
                "result_url": f"/v1/runs/{run_id}",
                "idempotent_replay": True,
            }
        run_id = "run_" + uuid.uuid4().hex
        idempotency[idempotency_key] = run_id
        runs[run_id] = {
            "run_id": run_id,
            "request_hash": request_hash,
            "status": "running",
            "progress": [{"stage": "accepted", "pct": 5}],
            "result": None,
        }
        result = await asyncio.to_thread(execute_workflow, dict(body), work_root=root / run_id)
        result["run_id"] = run_id
        _write_json(root / run_id / "result.json", result)
        runs[run_id].update({"status": "completed", "progress": result["progress"], "result": result})
        return {"run_id": run_id, "status": "accepted", "result_url": f"/v1/fixture-runs/{run_id}", "idempotent_replay": False}

    @web.get("/v1/fixture-runs/{run_id}")
    async def get_fixture_result(run_id: str) -> Any:
        row = runs.get(run_id)
        if not row:
            return JSONResponse({"status": "missing", "error": {"code": "RUN_NOT_FOUND"}}, status_code=404)
        if row["status"] != "completed":
            return JSONResponse({"run_id": run_id, "status": "running", "progress": row["progress"]}, status_code=202)
        return row["result"]

    @web.delete("/v1/fixture-runs/{run_id}")
    async def delete_fixture_run(run_id: str) -> Any:
        if run_id not in runs:
            return JSONResponse({"status": "missing", "error": {"code": "RUN_NOT_FOUND"}}, status_code=404)
        runs.pop(run_id, None)
        shutil.rmtree(root / run_id, ignore_errors=True)
        return {"run_id": run_id, "status": "deleted"}

    return web


@app.function(image=runtime_image, min_containers=0, max_containers=20, scaledown_window=2)
@modal.concurrent(max_inputs=20)
@modal.asgi_app(requires_proxy_auth=True)
def api() -> Any:
    return create_fastapi_app(require_proxy_auth=True)
