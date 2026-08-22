#!/usr/bin/env python3
"""Pure production-only deployment command and receipt contracts for Issue #141.

This module cannot execute subprocesses, read credentials, call providers, or
select arbitrary targets. A separately reviewed controller executes CommandCall
objects and feeds bounded JSON readbacks into these reducers.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

MODAL_ENVIRONMENT = "main"
MODAL_ALLOWED_SLUG = "label-normalizer-canary"
MODAL_TARGET = "cognition-label-normalizer-canary"
CLOUDFLARE_TARGET = "cognition-demos"
CLOUDFLARE_BUILDER_CRON = "*/1 * * * *"
PUBLIC_ORIGIN = "https://omo.space"
SAFE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SAFE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MODAL_ENV_KEYS = ("HOME", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "NO_COLOR", "PATH", "PYTHONUNBUFFERED")
CLOUDFLARE_ENV_KEYS = ("CI", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "HOME", "NO_COLOR", "PATH")


class AdapterError(RuntimeError):
    """Typed production-adapter failure with no provider payload."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CommandCall:
    argv: tuple[str, ...]
    cwd: Path
    allowed_env: tuple[str, ...]
    timeout_seconds: int
    shell: Literal[False] = False

    def __post_init__(self) -> None:
        if not self.argv or not self.cwd.is_absolute() or not 1 <= self.timeout_seconds <= 300 or self.shell is not False:
            raise AdapterError("invalid_production_command")
        if self.argv[:3] == (sys.executable, "-m", "modal"):
            valid = self.allowed_env == MODAL_ENV_KEYS and _valid_modal_argv(self.argv)
        elif self.argv[:3] == ("npx", "--no-install", "wrangler"):
            valid = self.allowed_env == CLOUDFLARE_ENV_KEYS and _valid_cloudflare_argv(self.argv)
        else:
            valid = False
        if not valid:
            raise AdapterError("invalid_production_command")


@dataclass(frozen=True)
class DeploymentReceipt:
    provider: Literal["modal", "cloudflare"]
    target: str
    environment: str
    target_sha: str
    artifact_hash: str
    version_id: str
    previous_version_id: str | None
    reused: bool
    rollback_token: str | None
    status: Literal["passed"] = "passed"

    def __post_init__(self) -> None:
        if (
            self.provider not in {"modal", "cloudflare"}
            or not SAFE_SHA_RE.fullmatch(self.target_sha)
            or not SAFE_HASH_RE.fullmatch(self.artifact_hash)
            or not SAFE_VERSION_RE.fullmatch(self.version_id)
            or (self.previous_version_id is not None and not SAFE_VERSION_RE.fullmatch(self.previous_version_id))
            or self.rollback_token != self.previous_version_id
            or type(self.reused) is not bool
            or (self.reused is False and self.previous_version_id is None)
            or (self.reused is True and self.previous_version_id is not None)
            or self.status != "passed"
            or (self.provider == "modal" and (self.target != MODAL_TARGET or self.environment != MODAL_ENVIRONMENT))
            or (self.provider == "cloudflare" and (self.target != CLOUDFLARE_TARGET or self.environment != "production"))
        ):
            raise AdapterError("invalid_production_receipt")


def _valid_modal_argv(argv: tuple[str, ...]) -> bool:
    tail = argv[3:]
    if tail == ("environment", "list", "--json"):
        return True
    if tail == ("app", "history", MODAL_TARGET, "--env", MODAL_ENVIRONMENT, "--json"):
        return True
    if len(tail) == 8 and tail[:1] == ("deploy",):
        path = Path(tail[1])
        return (
            path.is_absolute()
            and path.parts[-2:] == (MODAL_ALLOWED_SLUG, "modal_app.py")
            and tail[2:7] == ("--env", MODAL_ENVIRONMENT, "--name", MODAL_TARGET, "--tag")
            and bool(SAFE_SHA_RE.fullmatch(tail[7]))
        )
    if len(tail) == 6 and tail[:3] == ("app", "rollback", MODAL_TARGET):
        return bool(SAFE_VERSION_RE.fullmatch(tail[3])) and tail[4:] == ("--env", MODAL_ENVIRONMENT)
    return False


def _valid_cloudflare_argv(argv: tuple[str, ...]) -> bool:
    tail = argv[3:]
    common = ("--name", CLOUDFLARE_TARGET)
    if tail[:1] in (("versions",), ("deployments",)):
        return len(tail) == 5 and tail[1] == "list" and tail[2:] == (*common, "--json")
    if tail[:1] == ("deploy",):
        rest = tail[1:]
        if rest[:2] != common:
            return False
        if len(rest) == 5 and rest[2] == "--dry-run" and rest[3] == "--outdir":
            return Path(rest[4]).is_absolute()
        return (
            len(rest) == 5
            and rest[2:4] == ("--strict", "--message")
            and rest[4].startswith("issue141:")
            and bool(SAFE_SHA_RE.fullmatch(rest[4][9:]))
        )
    if tail[:1] == ("rollback",) and len(tail) == 7:
        return (
            bool(SAFE_VERSION_RE.fullmatch(tail[1]))
            and tail[2:4] == common
            and tail[4] == "--message"
            and tail[5].startswith("production rollback ")
            and bool(SAFE_SHA_RE.fullmatch(tail[5][20:]))
            and tail[6] == "--yes"
        )
    return False


def receipt_json(receipt: DeploymentReceipt) -> str:
    return json.dumps(asdict(receipt), separators=(",", ":"), sort_keys=True)


def _root(checkout: Path) -> Path:
    root = checkout.resolve()
    if not root.is_dir():
        raise AdapterError("invalid_production_checkout")
    return root


def _sha(value: str) -> str:
    sha = str(value or "").strip().lower()
    if not SAFE_SHA_RE.fullmatch(sha):
        raise AdapterError("invalid_target_sha")
    return sha


def _hash(value: str) -> str:
    artifact = str(value or "").strip().lower()
    if not SAFE_HASH_RE.fullmatch(artifact):
        raise AdapterError("production_readback_failed")
    return artifact


def _version(value: str) -> str:
    version = str(value or "").strip()
    if not SAFE_VERSION_RE.fullmatch(version):
        raise AdapterError("invalid_rollback_version")
    return version


def _modal_app(checkout: Path, slug: str) -> tuple[Path, Path]:
    root = _root(checkout)
    if str(slug or "").strip() != MODAL_ALLOWED_SLUG:
        raise AdapterError("invalid_production_target")
    raw_path = root / "containers" / MODAL_ALLOWED_SLUG / "modal_app.py"
    path = raw_path.resolve()
    if path != raw_path or path.parent.parent != root / "containers" or not path.is_file():
        raise AdapterError("production_artifact_missing")
    return root, path


def _worker_root(checkout: Path) -> Path:
    root = _root(checkout)
    raw_worker = root / "site" / "deploy"
    worker = raw_worker.resolve()
    if worker != raw_worker or not worker.is_dir():
        raise AdapterError("production_artifact_missing")
    for current, directories, files in os.walk(worker, followlinks=False):
        directories[:] = [name for name in directories if name not in {"node_modules", ".wrangler"}]
        paths = [Path(current) / name for name in (*directories, *files)]
        if any(path.is_symlink() for path in paths):
            raise AdapterError("production_artifact_missing")
    if not (worker / "worker.js").is_file() or not (worker / "wrangler.toml").is_file():
        raise AdapterError("production_artifact_missing")
    return worker


def modal_preflight_call(checkout: Path, slug: str) -> CommandCall:
    root, _ = _modal_app(checkout, slug)
    return CommandCall((sys.executable, "-m", "modal", "environment", "list", "--json"), root, MODAL_ENV_KEYS, 30)


def modal_history_call(checkout: Path, slug: str) -> CommandCall:
    root, _ = _modal_app(checkout, slug)
    return CommandCall((sys.executable, "-m", "modal", "app", "history", MODAL_TARGET, "--env", MODAL_ENVIRONMENT, "--json"), root, MODAL_ENV_KEYS, 60)


def modal_deploy_call(checkout: Path, slug: str, target_sha: str) -> CommandCall:
    root, path = _modal_app(checkout, slug)
    sha = _sha(target_sha)
    return CommandCall((sys.executable, "-m", "modal", "deploy", str(path), "--env", MODAL_ENVIRONMENT, "--name", MODAL_TARGET, "--tag", sha), root, MODAL_ENV_KEYS, 300)


def modal_rollback_call(checkout: Path, slug: str, version_id: str) -> CommandCall:
    root, _ = _modal_app(checkout, slug)
    version = _version(version_id)
    return CommandCall((sys.executable, "-m", "modal", "app", "rollback", MODAL_TARGET, version, "--env", MODAL_ENVIRONMENT), root, MODAL_ENV_KEYS, 180)


def cloudflare_preflight_call(checkout: Path, outdir: Path) -> CommandCall:
    root = _worker_root(checkout)
    private = outdir.resolve()
    if not private.is_dir() or stat.S_IMODE(private.stat().st_mode) != 0o700:
        raise AdapterError("invalid_dry_run_directory")
    return CommandCall(("npx", "--no-install", "wrangler", "deploy", "--name", CLOUDFLARE_TARGET, "--dry-run", "--outdir", str(private)), root, CLOUDFLARE_ENV_KEYS, 180)


def cloudflare_versions_call(checkout: Path) -> CommandCall:
    root = _worker_root(checkout)
    return CommandCall(("npx", "--no-install", "wrangler", "versions", "list", "--name", CLOUDFLARE_TARGET, "--json"), root, CLOUDFLARE_ENV_KEYS, 60)


def cloudflare_deployments_call(checkout: Path) -> CommandCall:
    root = _worker_root(checkout)
    return CommandCall(("npx", "--no-install", "wrangler", "deployments", "list", "--name", CLOUDFLARE_TARGET, "--json"), root, CLOUDFLARE_ENV_KEYS, 60)


def cloudflare_deploy_call(checkout: Path, target_sha: str) -> CommandCall:
    root = _worker_root(checkout)
    sha = _sha(target_sha)
    return CommandCall(("npx", "--no-install", "wrangler", "deploy", "--name", CLOUDFLARE_TARGET, "--strict", "--message", f"issue141:{sha}"), root, CLOUDFLARE_ENV_KEYS, 300)


def cloudflare_rollback_call(checkout: Path, version_id: str, target_sha: str) -> CommandCall:
    root = _worker_root(checkout)
    version, sha = _version(version_id), _sha(target_sha)
    return CommandCall(("npx", "--no-install", "wrangler", "rollback", version, "--name", CLOUDFLARE_TARGET, "--message", f"production rollback {sha}", "--yes"), root, CLOUDFLARE_ENV_KEYS, 180)


def cloudflare_bundle_sha256(outdir: Path) -> str:
    root = outdir.resolve()
    artifact = root / "worker.js"
    if not root.is_dir() or artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size > 10 * 1024 * 1024:
        raise AdapterError("production_artifact_invalid")
    return hashlib.sha256(artifact.read_bytes()).hexdigest()


def _list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise AdapterError("production_readback_failed")
    return value


def modal_history_snapshot(value: Any) -> list[tuple[str, str | None]]:
    normalized: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for row in _list(value):
        if "Version" not in row or "Tag" not in row:
            raise AdapterError("production_readback_failed")
        version, tag = row["Version"], row["Tag"]
        if type(version) is not str or not SAFE_VERSION_RE.fullmatch(version) or version in seen:
            raise AdapterError("production_readback_failed")
        if tag is not None and (type(tag) is not str or not SAFE_SHA_RE.fullmatch(tag.lower())):
            raise AdapterError("production_readback_failed")
        seen.add(version)
        normalized.append((version, tag.lower() if isinstance(tag, str) else None))
    return normalized


def modal_receipt(before: Any, after: Any, slug: str, target_sha: str, artifact_hash: str) -> DeploymentReceipt:
    if str(slug or "").strip() != MODAL_ALLOWED_SLUG:
        raise AdapterError("invalid_production_target")
    sha, artifact = _sha(target_sha), _hash(artifact_hash)
    before_history, after_history = modal_history_snapshot(before), modal_history_snapshot(after)
    before_match = [version for version, tag in before_history if tag == sha]
    if before_match:
        if after_history != before_history:
            raise AdapterError("production_readback_failed")
        return DeploymentReceipt(
            "modal", MODAL_TARGET, MODAL_ENVIRONMENT, sha, artifact,
            before_match[0], None, True, None,
        )
    if (
        not before_history or len(after_history) != len(before_history) + 1
        or after_history[1:] != before_history or after_history[0][1] != sha
        or after_history[0][0] in {version for version, _ in before_history}
    ):
        raise AdapterError("production_readback_failed")
    version = after_history[0][0]
    previous = before_history[0][0]
    return DeploymentReceipt("modal", MODAL_TARGET, MODAL_ENVIRONMENT, sha, artifact, version, previous, False, previous)


def _active_version(deployments: list[dict[str, Any]]) -> str:
    if not deployments:
        raise AdapterError("production_readback_failed")
    versions = deployments[-1].get("versions")
    if not isinstance(versions, list) or len(versions) != 1 or not isinstance(versions[0], dict):
        raise AdapterError("production_readback_failed")
    version, percentage = str(versions[0].get("version_id") or ""), versions[0].get("percentage")
    if not SAFE_VERSION_RE.fullmatch(version) or percentage not in {100, 100.0}:
        raise AdapterError("production_readback_failed")
    return version


def cloudflare_receipt(versions_before: Any, versions_after: Any, deployments_before: Any, deployments_after: Any, target_sha: str, artifact_hash: str) -> DeploymentReceipt:
    sha, artifact = _sha(target_sha), _hash(artifact_hash)
    before_rows, after_rows = _list(versions_before), _list(versions_after)
    before_deployments, after_deployments = _list(deployments_before), _list(deployments_after)
    message = f"issue141:{sha}"
    matches = lambda rows: [row for row in rows if isinstance(row.get("annotations"), dict) and row["annotations"].get("workers/message") == message and SAFE_VERSION_RE.fullmatch(str(row.get("id") or ""))]
    before_match, after_match = matches(before_rows), matches(after_rows)
    active_before, active_after = _active_version(before_deployments), _active_version(after_deployments)
    if len(before_match) == 1:
        version = str(before_match[0]["id"])
        if len(after_match) != 1 or str(after_match[0]["id"]) != version or active_after != version:
            raise AdapterError("production_readback_failed")
        return DeploymentReceipt("cloudflare", CLOUDFLARE_TARGET, "production", sha, artifact, version, None, True, None)
    if before_match or len(after_match) != 1:
        raise AdapterError("production_readback_failed")
    version = str(after_match[0]["id"])
    before_ids = {str(row.get("id")) for row in before_rows if SAFE_VERSION_RE.fullmatch(str(row.get("id") or ""))}
    after_ids = {str(row.get("id")) for row in after_rows if SAFE_VERSION_RE.fullmatch(str(row.get("id") or ""))}
    if after_ids - before_ids != {version} or active_after != version or active_before == version:
        raise AdapterError("production_readback_failed")
    return DeploymentReceipt("cloudflare", CLOUDFLARE_TARGET, "production", sha, artifact, version, active_before, False, active_before)
