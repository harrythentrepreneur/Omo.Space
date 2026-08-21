#!/usr/bin/env python3
"""Pure staging-only deployment command and receipt contracts.

This module cannot execute subprocesses, access credentials, call providers, or
select production. A separately reviewed controller must execute CommandCall
objects and feed bounded JSON readbacks into the receipt reducers.
"""
from __future__ import annotations

import json
import hashlib
import re
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

MODAL_ENVIRONMENT = "omo-release-staging"
MODAL_ALLOWED_SLUG = "label-normalizer-canary"
MODAL_TARGET = "cognition-staging-label-normalizer-canary"
CLOUDFLARE_TARGET = "cognition-demos-staging"
SAFE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SAFE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MODAL_ENV_KEYS = ("HOME", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "NO_COLOR", "PATH", "PYTHONUNBUFFERED")
CLOUDFLARE_ENV_KEYS = ("CI", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "HOME", "NO_COLOR", "PATH")


class AdapterError(RuntimeError):
    """Typed staging-adapter failure with no provider payload."""

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
        if not self.argv or not self.cwd.is_absolute() or not 1 <= self.timeout_seconds <= 300:
            raise AdapterError("invalid_staging_command")
        if self.shell is not False:
            raise AdapterError("invalid_staging_command")
        modal_prefix = (sys.executable, "-m", "modal")
        worker_prefix = ("npx", "--no-install", "wrangler")
        if self.argv[:3] == modal_prefix:
            if self.allowed_env != MODAL_ENV_KEYS or not _valid_modal_argv(self.argv):
                raise AdapterError("invalid_staging_command")
        elif self.argv[:3] == worker_prefix:
            if self.allowed_env != CLOUDFLARE_ENV_KEYS or not _valid_cloudflare_argv(self.argv):
                raise AdapterError("invalid_staging_command")
        else:
            raise AdapterError("invalid_staging_command")


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
            or
            self.environment not in {MODAL_ENVIRONMENT, "staging"}
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
            or (self.provider == "cloudflare" and (self.target != CLOUDFLARE_TARGET or self.environment != "staging"))
        ):
            raise AdapterError("invalid_staging_receipt")


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
            and tail[2:8] == ("--env", MODAL_ENVIRONMENT, "--name", MODAL_TARGET, "--tag", tail[7])
            and bool(SAFE_SHA_RE.fullmatch(tail[7]))
        )
    if len(tail) == 6 and tail[:3] == ("app", "rollback", MODAL_TARGET):
        return bool(SAFE_VERSION_RE.fullmatch(tail[3])) and tail[4:] == ("--env", MODAL_ENVIRONMENT)
    return False


def _valid_cloudflare_argv(argv: tuple[str, ...]) -> bool:
    tail = argv[3:]
    common = ("--env", "staging", "--name", CLOUDFLARE_TARGET)
    if tail[:1] in (("versions",), ("deployments",)):
        return len(tail) == 7 and tail[1] == "list" and tail[2:] == (*common, "--json")
    if tail[:1] == ("deploy",):
        rest = tail[1:]
        if rest[:4] != common:
            return False
        if len(rest) == 7 and rest[4] == "--dry-run" and rest[5] == "--outdir":
            return Path(rest[6]).is_absolute()
        return (
            len(rest) == 7
            and rest[4:6] == ("--strict", "--message")
            and rest[6].startswith("issue141:")
            and bool(SAFE_SHA_RE.fullmatch(rest[6][9:]))
        )
    if tail[:1] == ("rollback",) and len(tail) == 9:
        return (
            bool(SAFE_VERSION_RE.fullmatch(tail[1]))
            and tail[2:6] == common
            and tail[6] == "--message"
            and tail[7].startswith("staging rollback ")
            and bool(SAFE_SHA_RE.fullmatch(tail[7][17:]))
            and tail[8:] == ("--yes",)
        )
    return False


def receipt_json(receipt: DeploymentReceipt) -> str:
    return json.dumps(asdict(receipt), separators=(",", ":"), sort_keys=True)


def cloudflare_bundle_sha256(outdir: Path) -> str:
    """Hash only Wrangler's authoritative compiled Worker bytes."""
    root = outdir.resolve()
    artifact = root / "worker.js"
    if (
        not root.is_dir()
        or artifact.is_symlink()
        or not artifact.is_file()
        or artifact.stat().st_size > 10 * 1024 * 1024
    ):
        raise AdapterError("staging_artifact_invalid")
    return hashlib.sha256(artifact.read_bytes()).hexdigest()


def _root(checkout: Path) -> Path:
    root = checkout.resolve()
    if not root.is_dir():
        raise AdapterError("invalid_staging_checkout")
    return root


def _sha(value: str) -> str:
    sha = str(value or "").strip().lower()
    if not SAFE_SHA_RE.fullmatch(sha):
        raise AdapterError("invalid_target_sha")
    return sha


def _version(value: str) -> str:
    version = str(value or "").strip()
    if not SAFE_VERSION_RE.fullmatch(version):
        raise AdapterError("invalid_rollback_version")
    return version


def _modal_target(slug: str) -> str:
    value = str(slug or "").strip()
    if value != MODAL_ALLOWED_SLUG:
        raise AdapterError("invalid_staging_target")
    return MODAL_TARGET


def _modal_app(checkout: Path, slug: str) -> tuple[Path, str, Path]:
    root = _root(checkout)
    target = _modal_target(slug)
    path = (root / "containers" / slug / "modal_app.py").resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise AdapterError("invalid_staging_target") from error
    if not path.is_file():
        raise AdapterError("staging_artifact_missing")
    return root, target, path


def _worker_root(checkout: Path) -> Path:
    root = _root(checkout)
    worker_root = (root / "site" / "deploy").resolve()
    if not (worker_root / "worker.js").is_file() or not (worker_root / "wrangler.toml").is_file():
        raise AdapterError("staging_artifact_missing")
    return worker_root


def modal_preflight_call(checkout: Path, slug: str) -> CommandCall:
    root, _target, _path = _modal_app(checkout, slug)
    return CommandCall((sys.executable, "-m", "modal", "environment", "list", "--json"), root, MODAL_ENV_KEYS, 30)


def modal_history_call(checkout: Path, slug: str) -> CommandCall:
    root, target, _path = _modal_app(checkout, slug)
    return CommandCall(
        (sys.executable, "-m", "modal", "app", "history", target, "--env", MODAL_ENVIRONMENT, "--json"),
        root,
        MODAL_ENV_KEYS,
        60,
    )


def modal_deploy_call(checkout: Path, slug: str, target_sha: str) -> CommandCall:
    root, target, path = _modal_app(checkout, slug)
    sha = _sha(target_sha)
    return CommandCall(
        (sys.executable, "-m", "modal", "deploy", str(path), "--env", MODAL_ENVIRONMENT, "--name", target, "--tag", sha),
        root,
        MODAL_ENV_KEYS,
        300,
    )


def modal_rollback_call(checkout: Path, slug: str, version_id: str) -> CommandCall:
    root, target, _path = _modal_app(checkout, slug)
    version = _version(version_id)
    return CommandCall(
        (sys.executable, "-m", "modal", "app", "rollback", target, version, "--env", MODAL_ENVIRONMENT),
        root,
        MODAL_ENV_KEYS,
        180,
    )


def cloudflare_preflight_call(checkout: Path, outdir: Path) -> CommandCall:
    root = _worker_root(checkout)
    private_outdir = outdir.resolve()
    if not private_outdir.is_dir() or stat.S_IMODE(private_outdir.stat().st_mode) != 0o700:
        raise AdapterError("invalid_dry_run_directory")
    return CommandCall(
        (
            "npx", "--no-install", "wrangler", "deploy", "--env", "staging",
            "--name", CLOUDFLARE_TARGET, "--dry-run", "--outdir", str(private_outdir),
        ),
        root,
        CLOUDFLARE_ENV_KEYS,
        180,
    )


def cloudflare_deployments_call(checkout: Path) -> CommandCall:
    root = _worker_root(checkout)
    return CommandCall(
        (
            "npx", "--no-install", "wrangler", "deployments", "list", "--env", "staging",
            "--name", CLOUDFLARE_TARGET, "--json",
        ),
        root,
        CLOUDFLARE_ENV_KEYS,
        60,
    )


def cloudflare_versions_call(checkout: Path) -> CommandCall:
    root = _worker_root(checkout)
    return CommandCall(
        (
            "npx", "--no-install", "wrangler", "versions", "list", "--env", "staging",
            "--name", CLOUDFLARE_TARGET, "--json",
        ),
        root,
        CLOUDFLARE_ENV_KEYS,
        60,
    )


def cloudflare_deploy_call(checkout: Path, target_sha: str) -> CommandCall:
    root = _worker_root(checkout)
    sha = _sha(target_sha)
    return CommandCall(
        (
            "npx", "--no-install", "wrangler", "deploy", "--env", "staging",
            "--name", CLOUDFLARE_TARGET, "--strict", "--message", f"issue141:{sha}",
        ),
        root,
        CLOUDFLARE_ENV_KEYS,
        300,
    )


def cloudflare_rollback_call(checkout: Path, version_id: str, target_sha: str) -> CommandCall:
    root = _worker_root(checkout)
    version = _version(version_id)
    sha = _sha(target_sha)
    return CommandCall(
        (
            "npx", "--no-install", "wrangler", "rollback", version, "--env", "staging",
            "--name", CLOUDFLARE_TARGET, "--message", f"staging rollback {sha}", "--yes",
        ),
        root,
        CLOUDFLARE_ENV_KEYS,
        180,
    )


def _list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise AdapterError("staging_readback_failed")
    return value


def modal_receipt(before: Any, after: Any, slug: str, target_sha: str, artifact_hash: str) -> DeploymentReceipt:
    target = _modal_target(slug)
    sha = _sha(target_sha)
    artifact = str(artifact_hash or "").lower()
    if not SAFE_HASH_RE.fullmatch(artifact):
        raise AdapterError("staging_readback_failed")
    before_rows = _list(before)
    after_rows = _list(after)

    def matches(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            row for row in rows
            if str(row.get("Tag") or "").lower() == sha
            and SAFE_VERSION_RE.fullmatch(str(row.get("Version") or ""))
        ]

    before_match = matches(before_rows)
    after_match = matches(after_rows)
    if len(before_match) == 1:
        version = str(before_match[0]["Version"])
        if len(after_match) != 1 or str(after_match[0]["Version"]) != version:
            raise AdapterError("staging_readback_failed")
        return DeploymentReceipt("modal", target, MODAL_ENVIRONMENT, sha, artifact, version, None, True, None)
    if before_match or len(after_match) != 1 or not before_rows:
        raise AdapterError("staging_readback_failed")
    version = str(after_match[0]["Version"])
    before_versions = {
        str(row.get("Version")) for row in before_rows
        if SAFE_VERSION_RE.fullmatch(str(row.get("Version") or ""))
    }
    after_versions = {
        str(row.get("Version")) for row in after_rows
        if SAFE_VERSION_RE.fullmatch(str(row.get("Version") or ""))
    }
    previous = str(before_rows[0].get("Version") or "")
    if (
        after_versions - before_versions != {version}
        or not SAFE_VERSION_RE.fullmatch(previous)
        or not after_rows
        or str(after_rows[0].get("Version") or "") != version
    ):
        raise AdapterError("staging_readback_failed")
    return DeploymentReceipt("modal", target, MODAL_ENVIRONMENT, sha, artifact, version, previous, False, previous)


def _active_version(deployments: list[dict[str, Any]]) -> str:
    if not deployments:
        raise AdapterError("staging_readback_failed")
    versions = deployments[-1].get("versions")
    if not isinstance(versions, list) or len(versions) != 1 or not isinstance(versions[0], dict):
        raise AdapterError("staging_readback_failed")
    version = str(versions[0].get("version_id") or "")
    percentage = versions[0].get("percentage")
    if not SAFE_VERSION_RE.fullmatch(version) or percentage not in {100, 100.0}:
        raise AdapterError("staging_readback_failed")
    return version


def cloudflare_receipt(
    versions_before: Any,
    versions_after: Any,
    deployments_before: Any,
    deployments_after: Any,
    target_sha: str,
    artifact_hash: str,
) -> DeploymentReceipt:
    sha = _sha(target_sha)
    artifact = str(artifact_hash or "").lower()
    if not SAFE_HASH_RE.fullmatch(artifact):
        raise AdapterError("staging_readback_failed")
    before_rows = _list(versions_before)
    after_rows = _list(versions_after)
    before_deployments = _list(deployments_before)
    after_deployments = _list(deployments_after)
    message = f"issue141:{sha}"

    def matches(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            row for row in rows
            if isinstance(row.get("annotations"), dict)
            and row["annotations"].get("workers/message") == message
            and SAFE_VERSION_RE.fullmatch(str(row.get("id") or ""))
        ]

    before_match = matches(before_rows)
    after_match = matches(after_rows)
    if len(before_match) == 1:
        version = str(before_match[0]["id"])
        if len(after_match) != 1 or str(after_match[0]["id"]) != version or _active_version(after_deployments) != version:
            raise AdapterError("staging_readback_failed")
        return DeploymentReceipt("cloudflare", CLOUDFLARE_TARGET, "staging", sha, artifact, version, None, True, None)
    if before_match or len(after_match) != 1:
        raise AdapterError("staging_readback_failed")
    version = str(after_match[0]["id"])
    before_ids = {
        str(row.get("id")) for row in before_rows
        if SAFE_VERSION_RE.fullmatch(str(row.get("id") or ""))
    }
    after_ids = {
        str(row.get("id")) for row in after_rows
        if SAFE_VERSION_RE.fullmatch(str(row.get("id") or ""))
    }
    previous = _active_version(before_deployments)
    if after_ids - before_ids != {version} or _active_version(after_deployments) != version:
        raise AdapterError("staging_readback_failed")
    return DeploymentReceipt(
        "cloudflare", CLOUDFLARE_TARGET, "staging", sha,
        artifact, version, previous, False, previous,
    )
