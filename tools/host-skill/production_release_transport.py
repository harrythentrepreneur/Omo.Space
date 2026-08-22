#!/usr/bin/env python3
"""Deny-by-default subprocess transport for production release commands."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from typing import Any

from production_release_adapters import AdapterError, CommandCall

MAX_OUTPUT_BYTES = 1024 * 1024


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
        if tail[:1] in {("deploy",), ("rollback",)}:
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
        source_env: Mapping[str, str] | None = None,
        allow_mutation: bool = False,
    ) -> None:
        self._executor = executor
        self._source_env = dict(source_env or {})
        self._allow_mutation = allow_mutation

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
