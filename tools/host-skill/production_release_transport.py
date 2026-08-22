#!/usr/bin/env python3
"""Deny-by-default subprocess transport for production release commands."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from production_release_adapters import AdapterError, CommandCall

MAX_OUTPUT_BYTES = 1024 * 1024
SAFE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class TransportError(RuntimeError):
    """Typed production transport failure that never includes provider output."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _command_mode(call: CommandCall) -> str:
    try:
        CommandCall(call.argv, call.cwd, call.allowed_env, call.timeout_seconds, call.shell)
    except (AdapterError, AttributeError, TypeError, ValueError):
        raise TransportError("invalid_production_command") from None
    argv = call.argv
    if argv[:3] == ("npx", "--no-install", "wrangler"):
        tail = argv[3:]
        if tail[:1] in {("versions",), ("deployments",)} or (tail[:1] == ("deploy",) and "--dry-run" in tail):
            return "read"
        if tail[:1] in {("deploy",), ("rollback",)} or tail[:2] == ("triggers", "deploy"):
            return "write"
        raise TransportError("invalid_production_command")
    tail = argv[3:]
    if tail == ("environment", "list", "--json") or tail[:2] == ("app", "history"):
        return "read"
    if tail[:1] == ("deploy",) or tail[:2] == ("app", "rollback"):
        return "write"
    raise TransportError("invalid_production_command")


class ProductionCommandTransport:
    """Execute only production CommandCall objects with provider-isolated environments."""

    def __init__(
        self,
        *,
        executor: Callable[..., Any] = subprocess.run,
        checkout_verifier: Callable[[str, str], bool] | None = None,
        source_env: Mapping[str, str] | None = None,
        trusted_checkout: str,
        trusted_sha: str,
        allow_mutation: bool = False,
    ) -> None:
        self._executor = executor
        self._checkout_verifier = checkout_verifier or self._verify_git_checkout
        self._source_env = dict(source_env or {})
        self._trusted_checkout = str(Path(trusted_checkout).resolve())
        self._trusted_sha = str(trusted_sha or "").strip().lower()
        if not SAFE_SHA_RE.fullmatch(self._trusted_sha):
            raise TransportError("invalid_production_checkout")
        self._allow_mutation = allow_mutation

    def _verify_git_checkout(self, checkout: str, target_sha: str) -> bool:
        env = {"PATH": self._source_env.get("PATH", "/usr/bin:/bin"), "NO_COLOR": "1"}
        try:
            head = subprocess.run(
                ["git", "-C", checkout, "rev-parse", "HEAD"], env=env, shell=False,
                timeout=30, capture_output=True, check=False,
            )
            clean = subprocess.run(
                ["git", "-C", checkout, "status", "--porcelain", "--untracked-files=all"],
                env=env, shell=False, timeout=30, capture_output=True, check=False,
            )
        except (OSError, subprocess.TimeoutExpired, ValueError):
            return False
        return (
            head.returncode == 0 and clean.returncode == 0
            and head.stdout.decode("ascii", "ignore").strip().lower() == target_sha
            and clean.stdout == b""
        )

    def _verify_call_checkout(self, call: CommandCall) -> None:
        trusted = Path(self._trusted_checkout)
        cwd = call.cwd.resolve()
        if cwd not in {trusted, trusted / "site" / "deploy"}:
            raise TransportError("invalid_production_checkout")
        if not self._checkout_verifier(self._trusted_checkout, self._trusted_sha):
            raise TransportError("invalid_production_checkout")

    def _environment(self, call: CommandCall, private_home: str) -> dict[str, str]:
        env = {
            key: self._source_env[key]
            for key in call.allowed_env
            if key != "HOME" and key in self._source_env and self._source_env[key]
        }
        env["HOME"] = private_home
        if "NO_COLOR" in call.allowed_env:
            env["NO_COLOR"] = "1"
        if "PYTHONUNBUFFERED" in call.allowed_env:
            env["PYTHONUNBUFFERED"] = "1"
        if "CI" in call.allowed_env:
            env["CI"] = "1"
        return dict(sorted(env.items()))

    def _execute(self, call: CommandCall) -> str:
        if not isinstance(call, CommandCall):
            raise TransportError("invalid_production_command")
        self._verify_call_checkout(call)
        mode = _command_mode(call)
        if mode == "write" and not self._allow_mutation:
            raise TransportError("production_mutation_not_enabled")
        with tempfile.TemporaryDirectory(prefix="omo-production-provider-") as private_home, \
             tempfile.TemporaryFile(mode="w+b") as stdout_file, \
             tempfile.TemporaryFile(mode="w+b") as stderr_file:
            os.chmod(private_home, 0o700)
            try:
                result = self._executor(
                    list(call.argv), cwd=call.cwd, env=self._environment(call, private_home), shell=False,
                    timeout=call.timeout_seconds, stdout=stdout_file, stderr=stderr_file, check=False,
                )
            except subprocess.TimeoutExpired:
                raise TransportError("production_command_timeout") from None
            except (OSError, ValueError, TypeError):
                raise TransportError("production_command_failed") from None
            stdout_file.flush()
            stderr_file.flush()
            stdout_size = stdout_file.seek(0, 2)
            stderr_size = stderr_file.seek(0, 2)
            if stdout_size > MAX_OUTPUT_BYTES or stderr_size > MAX_OUTPUT_BYTES:
                raise TransportError("production_output_too_large")
            if result.returncode != 0:
                raise TransportError("production_command_failed")
            stdout_file.seek(0)
            try:
                return stdout_file.read(MAX_OUTPUT_BYTES + 1).decode("utf-8")
            except UnicodeDecodeError:
                raise TransportError("production_output_invalid") from None

    def run(self, call: CommandCall) -> None:
        self._execute(call)

    def run_json(self, call: CommandCall) -> Any:
        stdout = self._execute(call)
        try:
            return json.loads(stdout)
        except (json.JSONDecodeError, TypeError, ValueError):
            raise TransportError("production_json_invalid") from None
