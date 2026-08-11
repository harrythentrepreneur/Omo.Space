"""Private milestone Modal ingress and CPU runner for de Mello Awake.

This is deliberately not a public paid-traffic boundary. Modal Proxy Token and
Omo-owned R2 capabilities are not available for milestone 1, so the ASGI app
uses a server-held bearer key and a named Modal Volume with signed, expiring
downloads. The response metadata states those gaps explicitly.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import math
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from starlette.requests import Request

# Modal hydrates this module at /root/modal_app.py while the immutable bundle
# lives at /root/demello_awake. Make that explicit instead of depending on the
# caller's working directory or package name.
sys.path.insert(0, "/root/demello_awake")

try:
    import modal

    MODAL_SDK_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - used in SDK-free test hosts
    MODAL_SDK_AVAILABLE = False

    class _LocalImage:
        def apt_install(self, *_packages: str) -> "_LocalImage":
            return self

        def uv_pip_install(self, *_packages: str) -> "_LocalImage":
            return self

        def add_local_dir(self, *_paths: Any, **_kwargs: Any) -> "_LocalImage":
            return self

        def run_commands(self, *_commands: str) -> "_LocalImage":
            return self

        def env(self, *_args: Any, **_kwargs: Any) -> "_LocalImage":
            return self

    class _ImageFactory:
        @staticmethod
        def debian_slim(**_kwargs: Any) -> _LocalImage:
            return _LocalImage()

    class _Secret:
        @staticmethod
        def from_name(name: str) -> dict[str, str]:
            return {"name": name}

    class _Volume:
        @staticmethod
        def from_name(name: str, **_kwargs: Any) -> "_Volume":
            instance = _Volume()
            instance.name = name
            return instance

        def commit(self) -> None:
            return None

        def reload(self) -> None:
            return None

    class _Function:
        def __init__(self, function: Callable[..., Any]):
            self._function = function

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return self._function(*args, **kwargs)

        def spawn(self, *_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("Modal SDK is required to spawn a remote function")

    class _App:
        def __init__(self, name: str):
            self.name = name

        def function(self, **_kwargs: Any) -> Callable[[Callable[..., Any]], _Function]:
            return lambda function: _Function(function)

    class _ModalFallback:
        App = _App
        Image = _ImageFactory
        Secret = _Secret
        Volume = _Volume

        @staticmethod
        def asgi_app(**_kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            return lambda function: function

        @staticmethod
        def concurrent(**_kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            return lambda function: function

    modal = _ModalFallback()  # type: ignore[assignment]

try:
    from pricing import PricingError, guarded_price_evidence
except ModuleNotFoundError:  # imported as a package by some test runners
    from .pricing import PricingError, guarded_price_evidence  # type: ignore[no-redef]


LOCAL_ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = Path("/root/demello_awake")
ARTIFACT_ROOT = Path("/artifacts")
GO_RUNNER_BINARY = "/usr/local/bin/demello-runner"
PYTHON_ENTRYPOINT = str(IMAGE_ROOT / "workflow.py")
SECRET_NAME = "omo-demello-awake"
VOLUME_NAME = "omo-demello-awake-artifacts"
STYLE = "sumi-e-awake-v3"
MAX_JSON_BYTES = 128 * 1024
MAX_RESULT_BYTES = 1024 * 1024
RUN_TIMEOUT_SECONDS = 20 * 60
SIGNED_URL_TTL_SECONDS = 5 * 60
MAX_SIGNED_URL_TTL_SECONDS = 15 * 60

# Public progress is monotonic even though the workflow has more detailed
# internal phase names. Checkpoints are derived from files written by the real
# subprocess, never from a dashboard timer.
PHASE_PROGRESS: dict[str, tuple[str, int]] = {
    "acquire": ("preparing", 8),
    "transcribe": ("transcribing", 20),
    "direct": ("directing", 36),
    "generate": ("generating", 52),
    "semantic": ("generating", 70),
    "assemble": ("assembling", 82),
    "qa": ("validating", 94),
    "contract": ("finalizing", 98),
}

RELEASE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,96}$")
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
REQUEST_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _release_hash() -> str:
    value = os.environ.get("DEMELLO_RELEASE_HASH", "0" * 64).strip()
    if not RELEASE_HASH_RE.fullmatch(value):
        raise RuntimeError("DEMELLO_RELEASE_HASH must be a 64-character lowercase sha256")
    return value


RELEASE_HASH = _release_hash()
RELEASE_DIGEST = f"sha256:{RELEASE_HASH}"
APP_NAME = f"omo-demello-awake-{RELEASE_HASH[:12]}"

# Explicit milestone metadata: neither substitution is acceptable for public
# paid traffic. A future release must turn both booleans true and replace the
# bearer/Volume mechanisms rather than merely changing this label.
MILESTONE_SECURITY = {
    "modal_proxy_token": False,
    "omo_r2_artifacts": False,
    "private_bearer_auth": True,
    "artifact_backend": "modal-volume-milestone-only",
    "paid_traffic_ready": False,
}


DURATION_BOUNDS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["min_seconds", "max_seconds"],
    "properties": {
        "min_seconds": {"type": "number", "minimum": 5, "maximum": 20},
        "max_seconds": {"type": "number", "minimum": 5, "maximum": 20},
    },
}

INPUT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://omo.best/schemas/demello-awake/input.json",
    "type": "object",
    "additionalProperties": False,
    "required": ["style", "duration_bounds"],
    "properties": {
        "audio_ref": {
            "type": "string",
            "enum": ["sample-demello-10s"],
        },
        "audio_url": {
            "type": "string",
            "minLength": 9,
            "maxLength": 2048,
            "pattern": "^https://",
        },
        "style": {"const": STYLE},
        "duration_bounds": DURATION_BOUNDS_SCHEMA,
    },
    "oneOf": [
        {"required": ["audio_ref"]},
        {"required": ["audio_url"]},
    ],
}

PRIVATE_RUN_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://omo.best/schemas/demello-awake/private-run.json",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "run_id",
        "release_hash",
        "request_hash",
        "input",
        "max_cost_usd",
    ],
    "properties": {
        "run_id": {"type": "string", "pattern": RUN_ID_RE.pattern},
        "release_hash": {"const": RELEASE_DIGEST},
        "request_hash": {"type": "string", "pattern": REQUEST_HASH_RE.pattern},
        "input": INPUT_SCHEMA,
        "max_cost_usd": {
            "type": "number",
            "exclusiveMinimum": 0,
            "maximum": 100,
        },
    },
}

ARTIFACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["key", "sha256", "bytes"],
    "properties": {
        "key": {"type": "string", "minLength": 1, "maxLength": 240},
        "sha256": {"type": "string", "pattern": SHA256_RE.pattern},
        "bytes": {"type": "integer", "minimum": 1},
    },
}

USAGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["provider_costs_usd", "provider_costs_complete"],
    "properties": {
        "provider_costs_usd": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "transcription": {"type": "number", "minimum": 0},
                "director": {"type": "number", "minimum": 0},
                "image_generation": {"type": "number", "minimum": 0},
            },
        },
        "provider_costs_complete": {"type": "boolean"},
        "modal_cpu_core_seconds": {"type": "number", "minimum": 0},
        "modal_memory_gib_seconds": {"type": "number", "minimum": 0},
        "artifact_storage_usd": {"type": "number", "minimum": 0},
        "artifact_egress_usd": {"type": "number", "minimum": 0},
    },
}

PRICING_HISTORY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["static_estimate_usd"],
    "properties": {
        "static_estimate_usd": {"type": "number", "minimum": 0},
        "successful_delivered_usd": {
            "type": "array",
            "maxItems": 10000,
            "items": {"type": "number", "minimum": 0},
        },
        "delivered_7d_usd": {"type": "number", "minimum": 0},
        "delivered_30d_usd": {"type": "number", "minimum": 0},
    },
}

MEDIA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "duration_seconds",
        "video_codec",
        "audio_codec",
        "width",
        "height",
        "fps",
    ],
    "properties": {
        "duration_seconds": {"type": "number", "minimum": 5, "maximum": 20.25},
        "video_codec": {"const": "h264"},
        "audio_codec": {"const": "aac"},
        "width": {"const": 1080},
        "height": {"const": 1920},
        "fps": {"const": 30},
    },
}

PIPELINE_RESULT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://omo.best/schemas/demello-awake/pipeline-result.json",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "run_id",
        "status",
        "artifacts",
        "frames_used",
        "usage",
        "pricing_history",
        "media",
        "generation_provider",
    ],
    "properties": {
        "run_id": {"type": "string", "pattern": RUN_ID_RE.pattern},
        "status": {"const": "completed"},
        "artifacts": {
            "type": "object",
            "additionalProperties": False,
            "required": ["video", "contact_sheet"],
            "properties": {
                "video": ARTIFACT_SCHEMA,
                "contact_sheet": ARTIFACT_SCHEMA,
            },
        },
        "frames_used": {
            "type": "object",
            "additionalProperties": False,
            "required": ["generated", "semantic", "output"],
            "properties": {
                "generated": {"type": "integer", "minimum": 1},
                "semantic": {"type": "integer", "minimum": 15, "maximum": 61},
                "output": {"type": "integer", "minimum": 150, "maximum": 608},
            },
        },
        "usage": USAGE_SCHEMA,
        "pricing_history": PRICING_HISTORY_SCHEMA,
        "media": MEDIA_SCHEMA,
        "generation_provider": {
            "type": "string",
            "enum": ["openai", "openai-codex-subscription", "procedural-fallback"],
        },
    },
}


def validate_schema(instance: Any, schema: Mapping[str, Any]) -> None:
    from jsonschema import Draft202012Validator

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_request_hash(workflow_input: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(workflow_input)).hexdigest()


def _run_id() -> str:
    return "run_" + secrets.token_hex(16)


def validate_audio_url(
    value: str,
    resolver: Callable[..., Sequence[Any]] = socket.getaddrinfo,
) -> None:
    """Reject obvious and DNS-resolved SSRF targets before workflow spend."""

    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("audio_url must be an HTTPS URL without userinfo")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise ValueError("audio_url host is not allowed")
    try:
        addresses = resolver(hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("audio_url host could not be resolved") from exc
    if not addresses:
        raise ValueError("audio_url host could not be resolved")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("audio_url resolved to a non-public address")


def normalize_submission(
    body: Any,
    *,
    resolver: Callable[..., Sequence[Any]] = socket.getaddrinfo,
) -> dict[str, Any]:
    """Validate direct smoke input or the future server-owned private envelope."""

    if not isinstance(body, Mapping):
        raise ValueError("request body must be an object")
    if len(canonical_json(body)) > MAX_JSON_BYTES:
        raise ValueError("request body is too large")

    if "input" in body or "run_id" in body or "request_hash" in body:
        validate_schema(body, PRIVATE_RUN_SCHEMA)
        envelope = dict(body)
        workflow_input = dict(envelope["input"])
        expected_hash = canonical_request_hash(workflow_input)
        if not hmac.compare_digest(envelope["request_hash"], expected_hash):
            raise ValueError("request_hash does not match the canonical input")
    else:
        validate_schema(body, INPUT_SCHEMA)
        workflow_input = dict(body)
        envelope = {
            "run_id": _run_id(),
            "release_hash": RELEASE_DIGEST,
            "request_hash": canonical_request_hash(workflow_input),
            "input": workflow_input,
            # Direct input exists only for private smoke testing. This is an
            # execution ceiling, not a buyer quote or authorization to spend.
            "max_cost_usd": 5.0,
        }

    bounds = workflow_input["duration_bounds"]
    if float(bounds["min_seconds"]) > float(bounds["max_seconds"]):
        raise ValueError("duration_bounds min_seconds must not exceed max_seconds")
    if "audio_url" in workflow_input:
        validate_audio_url(str(workflow_input["audio_url"]), resolver=resolver)
    return envelope


def _safe_run_id(value: str) -> str:
    if not RUN_ID_RE.fullmatch(str(value or "")):
        raise ValueError("invalid run_id")
    return str(value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FileRunStore:
    """Small milestone state store on the named Volume.

    This is transport evidence, not durable buyer/business state. The future
    Worker must own idempotency, run state, settlement, and tenant access.
    """

    def __init__(self, root: Path, volume: Any | None = None):
        self.root = Path(root)
        self.volume = volume

    def _commit(self) -> None:
        commit = getattr(self.volume, "commit", None)
        if callable(commit):
            commit()

    def _reload(self) -> None:
        reload_volume = getattr(self.volume, "reload", None)
        if callable(reload_volume):
            reload_volume()

    def _write_json(self, path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = canonical_json(value)
        if len(encoded) > MAX_RESULT_BYTES:
            raise ValueError("state document is too large")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=str(path.parent)
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        self._commit()

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        self._reload()
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            return None
        if len(raw) > MAX_RESULT_BYTES:
            raise ValueError("state document is too large")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("state document is invalid")
        return value

    def status_path(self, run_id: str) -> Path:
        return self.root / "runs" / _safe_run_id(run_id) / "status.json"

    def get_status(self, run_id: str) -> dict[str, Any] | None:
        status = self._read_json(self.status_path(run_id))
        if not status or status.get("status") != "running":
            return status
        # This also makes local/offline status reads useful if a test or an
        # older executor writes only workflow.py's diagnostic checkpoint.
        marker = self._read_json(self.diagnostic_path(run_id))
        checkpoint = PHASE_PROGRESS.get(str((marker or {}).get("phase", "")))
        if checkpoint and checkpoint[1] >= int(status.get("progress_pct", 0) or 0):
            status["phase"], status["progress_pct"] = checkpoint
        return status

    def set_status(self, run_id: str, value: Mapping[str, Any]) -> None:
        self._write_json(self.status_path(run_id), value)

    def diagnostic_path(self, run_id: str) -> Path:
        return self.root / "runs" / _safe_run_id(run_id) / "diagnostic.json"

    def claim(
        self, idempotency_key: str, request_hash: str, envelope: Mapping[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        if not IDEMPOTENCY_KEY_RE.fullmatch(idempotency_key):
            raise ValueError("invalid idempotency key")
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        claim_path = self.root / "_control" / "idempotency" / f"{key_hash}.json"
        claim_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "run_id": envelope["run_id"],
            "request_hash": request_hash,
            "release_hash": RELEASE_DIGEST,
        }
        payload = canonical_json(record)
        try:
            descriptor = os.open(
                claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
        except FileExistsError:
            existing = self._read_json(claim_path)
            if not existing or not hmac.compare_digest(
                str(existing.get("request_hash", "")), request_hash
            ):
                raise KeyError("idempotency_key_conflict")
            return existing, False
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        accepted = {
            "run_id": envelope["run_id"],
            "status": "accepted",
            "phase": "queued",
            "progress_pct": 2,
            "release_hash": RELEASE_DIGEST,
            "request_hash": request_hash,
            "platform": MILESTONE_SECURITY,
        }
        self.set_status(str(envelope["run_id"]), accepted)
        self._commit()
        return record, True

    def artifact_path(self, run_id: str, object_name: str) -> Path:
        safe_id = _safe_run_id(run_id)
        if object_name not in {"video.mp4", "contact-sheet.jpg"}:
            raise ValueError("unknown artifact")
        root = self.root.resolve()
        candidate = (self.root / "runs" / safe_id / object_name).resolve()
        candidate.relative_to(root)
        if not candidate.is_file() or candidate.is_symlink():
            raise FileNotFoundError(object_name)
        return candidate


def _verify_pipeline_result(result: Mapping[str, Any], envelope: Mapping[str, Any], root: Path) -> None:
    validate_schema(result, PIPELINE_RESULT_SCHEMA)
    run_id = str(envelope["run_id"])
    if result["run_id"] != run_id:
        raise ValueError("pipeline run_id mismatch")
    bounds = envelope["input"]["duration_bounds"]
    duration = float(result["media"]["duration_seconds"])
    if duration + 0.25 < float(bounds["min_seconds"]) or duration - 0.25 > float(
        bounds["max_seconds"]
    ):
        raise ValueError("media duration violates the requested bounds")

    expected_semantic = int(math.ceil(duration * 3 - 1e-9))
    expected_output = round(duration * 30)
    frames = result["frames_used"]
    if frames["semantic"] != expected_semantic or frames["output"] != expected_output:
        raise ValueError("frame counts do not match the 3 fps / 30 fps contract")
    if frames["generated"] > frames["semantic"]:
        raise ValueError("generated frame count exceeds semantic cells")

    expected_keys = {
        "video": f"runs/{run_id}/video.mp4",
        "contact_sheet": f"runs/{run_id}/contact-sheet.jpg",
    }
    for name, key in expected_keys.items():
        evidence = result["artifacts"][name]
        if evidence["key"] != key:
            raise ValueError("artifact key violates the exact run path")
        path = (root / key).resolve()
        path.relative_to(root.resolve())
        if not path.is_file() or path.is_symlink():
            raise ValueError("artifact file is missing")
        if path.stat().st_size != evidence["bytes"]:
            raise ValueError("artifact byte evidence does not match")
        if not hmac.compare_digest(_sha256_file(path), evidence["sha256"]):
            raise ValueError("artifact checksum evidence does not match")


def run_go_adapter(
    envelope: Mapping[str, Any],
    *,
    artifact_root: Path,
    runner_command: Sequence[str] = (GO_RUNNER_BINARY,),
    python_entrypoint: str = PYTHON_ENTRYPOINT,
    timeout_seconds: int = RUN_TIMEOUT_SECONDS - 20,
    progress_callback: Callable[[str, int], None] | None = None,
) -> dict[str, Any]:
    """Invoke the Go boundary without placing secrets or payloads in argv/logs."""

    if not runner_command or any(not isinstance(item, str) or not item for item in runner_command):
        raise ValueError("runner command is invalid")
    run_id = _safe_run_id(str(envelope["run_id"]))
    run_artifacts = artifact_root / "runs" / run_id
    run_artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"demello-{run_id}-") as temporary:
        work = Path(temporary)
        request_path = work / "request.json"
        result_path = work / "result.json"
        internal_request = {
            **dict(envelope),
            "artifact_root": str(artifact_root),
            "run_artifact_dir": str(run_artifacts),
        }
        request_path.write_bytes(canonical_json(internal_request))
        request_path.chmod(0o600)
        command = [
            *runner_command,
            "-request",
            str(request_path),
            "-result",
            str(result_path),
            "-python",
            "/usr/local/bin/python3",
            "-workflow",
            python_entrypoint,
        ]
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        deadline = time.monotonic() + timeout_seconds
        last_internal_phase: str | None = None
        while True:
            return_code = process.poll()
            diagnostic = run_artifacts / "diagnostic.json"
            try:
                marker = json.loads(diagnostic.read_text(encoding="utf-8"))
                internal_phase = str(marker.get("phase", ""))
            except Exception:
                internal_phase = ""
            if internal_phase != last_internal_phase and internal_phase in PHASE_PROGRESS:
                last_internal_phase = internal_phase
                if progress_callback is not None:
                    phase, progress_pct = PHASE_PROGRESS[internal_phase]
                    try:
                        progress_callback(phase, progress_pct)
                    except Exception:
                        # Delivery should not leave a paid provider subprocess
                        # orphaned merely because a milestone checkpoint failed.
                        pass
            if return_code is not None:
                break
            if time.monotonic() >= deadline:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise TimeoutError("workflow runner timed out")
            time.sleep(0.2)
        if return_code != 0:
            raise RuntimeError("workflow runner failed")
        raw = result_path.read_bytes()
        if not raw or len(raw) > MAX_RESULT_BYTES:
            raise ValueError("workflow result size is invalid")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("workflow result must be an object")
        _verify_pipeline_result(result, envelope, artifact_root)
        return result


runtime_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ca-certificates", "ffmpeg", "golang-go")
    .uv_pip_install(
        "modal==1.5.0",
        "fastapi==0.109.0",
        "httpx==0.28.1",
        "jsonschema==4.26.0",
        "numpy==2.2.6",
        "pillow==11.3.0",
    )
    .add_local_dir(
        LOCAL_ROOT / "cmd" / "runner",
        "/tmp/demello-runner-src",
        copy=True,
    )
    .run_commands(
        "cd /tmp/demello-runner-src && "
        "CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' "
        "-o /usr/local/bin/demello-runner ."
    )
    .add_local_dir(LOCAL_ROOT, IMAGE_ROOT, copy=True)
    .env(
        {
            "DEMELLO_RELEASE_HASH": RELEASE_HASH,
            "DEMELLO_PROCEDURAL_FALLBACK_ENABLED": "1",
            "DEMELLO_PROVIDER_LANE_ENABLED": "0",
        }
    )
)

app = modal.App(APP_NAME)
runtime_secret = modal.Secret.from_name(SECRET_NAME)
artifact_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)


@app.function(
    image=runtime_image,
    secrets=[runtime_secret],
    volumes={str(ARTIFACT_ROOT): artifact_volume},
    cpu=1.0,
    memory=2048,
    timeout=RUN_TIMEOUT_SECONDS,
    min_containers=0,
    max_containers=4,
    scaledown_window=15,
)
def execute_run(envelope: dict[str, Any]) -> None:
    """Run one bounded Go-controlled CPU workflow and checkpoint redacted state."""

    run_id = _safe_run_id(str(envelope.get("run_id", "")))
    store = FileRunStore(ARTIFACT_ROOT, artifact_volume)
    store.set_status(
        run_id,
        {
            "run_id": run_id,
            "status": "running",
            "phase": "starting",
            "progress_pct": 5,
            "release_hash": RELEASE_DIGEST,
            "request_hash": envelope.get("request_hash"),
            "platform": MILESTONE_SECURITY,
        },
    )
    try:
        def checkpoint(phase: str, progress_pct: int) -> None:
            store.set_status(
                run_id,
                {
                    "run_id": run_id,
                    "status": "running",
                    "phase": phase,
                    "progress_pct": progress_pct,
                    "release_hash": RELEASE_DIGEST,
                    "request_hash": envelope.get("request_hash"),
                    "platform": MILESTONE_SECURITY,
                },
            )

        result = run_go_adapter(
            envelope,
            artifact_root=ARTIFACT_ROOT,
            progress_callback=checkpoint,
        )
        cost = guarded_price_evidence(result["usage"], result["pricing_history"])
        if cost["measured_usd"] > float(envelope["max_cost_usd"]):
            raise PricingError("measured cost exceeds the server execution ceiling")
        completed = {
            "run_id": run_id,
            "status": "completed",
            "phase": "delivered",
            "progress_pct": 100,
            "release_hash": RELEASE_DIGEST,
            "request_hash": envelope["request_hash"],
            "artifacts": result["artifacts"],
            "frames_used": result["frames_used"],
            "cost": cost,
            "media": result["media"],
            "generation_provider": result["generation_provider"],
            "platform": MILESTONE_SECURITY,
        }
        store.set_status(run_id, completed)
    except Exception:
        # Never persist provider bodies, subprocess stderr, paths, keys, or raw
        # exception messages. A fixed phase code is enough to refine a candidate.
        error_code = "RUN_FAILED"
        diagnostic = ARTIFACT_ROOT / "runs" / run_id / "diagnostic.json"
        try:
            marker = json.loads(diagnostic.read_text(encoding="utf-8"))
            phase = str(marker.get("phase", ""))
            if phase in {"acquire", "transcribe", "direct", "generate", "semantic", "assemble", "qa", "contract"}:
                error_code = f"RUN_FAILED_{phase.upper()}"
        except Exception:
            pass
        previous = store.get_status(run_id) or {}
        store.set_status(
            run_id,
            {
                "run_id": run_id,
                "status": "failed",
                "phase": "failed",
                "progress_pct": int(previous.get("progress_pct", 0) or 0),
                "release_hash": RELEASE_DIGEST,
                "error": {"code": error_code},
                "platform": MILESTONE_SECURITY,
            },
        )


def _bearer_key() -> str:
    return str(os.environ.get("API_SERVER_KEY", ""))


def _authorized(authorization: str, expected: str) -> bool:
    if not expected or not authorization.startswith("Bearer "):
        return False
    supplied = authorization[7:]
    return bool(supplied) and hmac.compare_digest(supplied, expected)


def _signature(secret_key: str, run_id: str, object_name: str, expires: int) -> str:
    message = f"GET\n{run_id}\n{object_name}\n{expires}".encode("utf-8")
    return hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _signed_artifact_url(
    base_url: str,
    secret_key: str,
    run_id: str,
    object_name: str,
    now: float,
) -> str:
    expires = int(now) + SIGNED_URL_TTL_SECONDS
    signature = _signature(secret_key, run_id, object_name, expires)
    return (
        f"{base_url.rstrip('/')}/v1/artifacts/{run_id}/{object_name}"
        f"?expires={expires}&signature={signature}"
    )


def _public_status(
    status: Mapping[str, Any], base_url: str, secret_key: str, now: float
) -> dict[str, Any]:
    public = {key: value for key, value in status.items() if key != "artifacts"}
    state = status.get("status")
    if state == "accepted":
        public.setdefault("phase", "queued")
        public.setdefault("progress_pct", 2)
    elif state == "running":
        public.setdefault("phase", "starting")
        public.setdefault("progress_pct", 5)
    elif state == "completed":
        public.setdefault("phase", "delivered")
        public.setdefault("progress_pct", 100)
        run_id = str(status["run_id"])
        public["video_url"] = _signed_artifact_url(
            base_url, secret_key, run_id, "video.mp4", now
        )
        public["contact_sheet_url"] = _signed_artifact_url(
            base_url, secret_key, run_id, "contact-sheet.jpg", now
        )
    return public


SpawnRunner = Callable[[dict[str, Any]], str]


def create_fastapi_app(
    *,
    spawn_runner: SpawnRunner | None = None,
    store: FileRunStore | None = None,
    auth_key_getter: Callable[[], str] = _bearer_key,
    clock: Callable[[], float] = time.time,
    resolver: Callable[..., Sequence[Any]] = socket.getaddrinfo,
) -> Any:
    """Build the private API with injectable offline test boundaries."""

    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, JSONResponse
    from jsonschema import ValidationError

    web = FastAPI(title="Omo de Mello Awake private milestone", version="0.1.0")
    run_store = store or FileRunStore(ARTIFACT_ROOT, artifact_volume)

    def spawn(envelope: dict[str, Any]) -> str:
        if spawn_runner is not None:
            return str(spawn_runner(envelope))
        call = execute_run.spawn(envelope)
        return str(call.object_id)

    def require_bearer(request: Request) -> str:
        expected = auth_key_getter()
        if not expected:
            raise HTTPException(status_code=503, detail="private_auth_not_configured")
        if not _authorized(str(request.headers.get("authorization") or ""), expected):
            raise HTTPException(status_code=401, detail="authentication_required")
        return expected

    async def submit(request: Request) -> JSONResponse:
        require_bearer(request)
        idempotency_key = str(request.headers.get("idempotency-key") or "").strip()
        if not IDEMPOTENCY_KEY_RE.fullmatch(idempotency_key):
            raise HTTPException(status_code=400, detail="invalid_idempotency_key")
        try:
            body = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid_json") from exc
        try:
            envelope = normalize_submission(body, resolver=resolver)
            record, created = run_store.claim(
                idempotency_key, envelope["request_hash"], envelope
            )
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail="invalid_run_input") from exc
        except KeyError as exc:
            raise HTTPException(status_code=409, detail="idempotency_key_conflict") from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="invalid_run_input") from exc

        run_id = str(record["run_id"])
        if created:
            try:
                spawn(envelope)
            except Exception as exc:
                run_store.set_status(
                    run_id,
                    {
                        "run_id": run_id,
                        "status": "failed",
                        "release_hash": RELEASE_DIGEST,
                        "error": {"code": "DISPATCH_FAILED"},
                        "platform": MILESTONE_SECURITY,
                    },
                )
                raise HTTPException(status_code=503, detail="dispatch_failed") from exc
        return JSONResponse(
            {
                "run_id": run_id,
                "status": "accepted",
                "phase": "queued",
                "progress_pct": 2,
                "status_url": f"/v1/runs/{run_id}",
                "idempotent_replay": not created,
                "platform": MILESTONE_SECURITY,
            },
            status_code=202,
        )

    web.add_api_route("/v1/runs", submit, methods=["POST"])
    web.add_api_route("/run", submit, methods=["POST"])

    @web.get("/v1/runs/{run_id}")
    async def get_status(run_id: str, request: Request) -> Any:
        secret_key = require_bearer(request)
        try:
            status = run_store.get_status(_safe_run_id(run_id))
        except (TypeError, ValueError):
            status = None
        if status is None:
            raise HTTPException(status_code=404, detail="run_not_found")
        return _public_status(status, str(request.base_url), secret_key, clock())

    @web.get("/v1/artifacts/{run_id}/{object_name}")
    async def get_artifact(
        run_id: str,
        object_name: str,
        expires: int,
        signature: str,
    ) -> Any:
        secret_key = auth_key_getter()
        now = int(clock())
        if not secret_key or expires < now or expires > now + MAX_SIGNED_URL_TTL_SECONDS:
            raise HTTPException(status_code=403, detail="invalid_artifact_signature")
        if object_name not in {"video.mp4", "contact-sheet.jpg"}:
            raise HTTPException(status_code=404, detail="artifact_not_found")
        expected = _signature(secret_key, run_id, object_name, expires)
        if not SHA256_RE.fullmatch(signature) or not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=403, detail="invalid_artifact_signature")
        try:
            status = run_store.get_status(_safe_run_id(run_id))
            if not status or status.get("status") != "completed":
                raise FileNotFoundError(object_name)
            path = run_store.artifact_path(run_id, object_name)
        except (FileNotFoundError, TypeError, ValueError):
            raise HTTPException(status_code=404, detail="artifact_not_found")
        media_type = "video/mp4" if object_name == "video.mp4" else "image/jpeg"
        return FileResponse(
            path,
            media_type=media_type,
            filename=object_name,
            headers={"Cache-Control": "private, no-store"},
        )

    return web


@app.function(
    image=runtime_image,
    secrets=[runtime_secret],
    volumes={str(ARTIFACT_ROOT): artifact_volume},
    cpu=0.25,
    memory=512,
    timeout=150,
    min_containers=0,
    max_containers=8,
    scaledown_window=15,
)
@modal.concurrent(max_inputs=20)
# Proxy Token is intentionally unavailable for milestone 1. Bearer auth is
# mandatory in every private/status request; signed artifact GETs are expiring.
@modal.asgi_app(requires_proxy_auth=False)
def api() -> Any:
    return create_fastapi_app()
