"""Contracts for the credential-safe staging command transport."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ADAPTER_PATH = ROOT / "tools" / "host-skill" / "staging_release_adapters.py"
TRANSPORT_PATH = ROOT / "tools" / "host-skill" / "staging_release_transport.py"


def load_modules():
    adapter_spec = importlib.util.spec_from_file_location("staging_release_adapters", ADAPTER_PATH)
    assert adapter_spec is not None and adapter_spec.loader is not None
    adapters = importlib.util.module_from_spec(adapter_spec)
    sys.modules[adapter_spec.name] = adapters
    adapter_spec.loader.exec_module(adapters)
    transport_spec = importlib.util.spec_from_file_location("staging_release_transport", TRANSPORT_PATH)
    assert transport_spec is not None and transport_spec.loader is not None
    transport = importlib.util.module_from_spec(transport_spec)
    sys.modules[transport_spec.name] = transport
    transport_spec.loader.exec_module(transport)
    return adapters, transport


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class Executor:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        result = self.results.pop(0)
        kwargs["stdout"].write(result.stdout.encode("utf-8"))
        kwargs["stderr"].write(result.stderr.encode("utf-8"))
        return result


def modal_call(adapters, tmp_path, *, deploy=False):
    root = tmp_path.resolve()
    argv = (sys.executable, "-m", "modal", "environment", "list", "--json")
    if deploy:
        app = root / "containers" / "label-normalizer-canary" / "modal_app.py"
        app.parent.mkdir(parents=True)
        app.write_text("# fixture", encoding="utf-8")
        argv = (
            sys.executable, "-m", "modal", "deploy", str(app),
            "--env", "omo-release-staging", "--name", "cognition-staging-label-normalizer-canary",
            "--tag", "a" * 40,
        )
    return adapters.CommandCall(argv, root, adapters.MODAL_ENV_KEYS, 30)


def cloudflare_dry_run(adapters, tmp_path):
    root = (tmp_path / "site" / "deploy").resolve()
    root.mkdir(parents=True)
    outdir = (tmp_path / "private").resolve()
    outdir.mkdir(mode=0o700)
    argv = (
        "npx", "--no-install", "wrangler", "deploy", "--env", "staging",
        "--name", "cognition-demos-staging", "--dry-run", "--outdir", str(outdir),
    )
    return adapters.CommandCall(argv, root, adapters.CLOUDFLARE_ENV_KEYS, 120)


def test_transport_runs_without_shell_using_fresh_allowlisted_environment(tmp_path):
    adapters, transport = load_modules()
    executor = Executor([Result(stdout='[{"Name":"main"}]')])
    source = {
        "PATH": "/safe/bin",
        "HOME": "/safe/home",
        "MODAL_TOKEN_ID": "id",
        "MODAL_TOKEN_SECRET": "secret",
        "CLOUDFLARE_API_TOKEN": "must-not-cross",
        "GITHUB_TOKEN": "must-not-cross",
        "HTTP_PROXY": "must-not-cross",
    }
    runner = transport.StagingCommandTransport(executor=executor, source_env=source)
    result = runner.run_json(modal_call(adapters, tmp_path))
    assert result == [{"Name": "main"}]
    args, kwargs = executor.calls[0]
    assert args[0][0:3] == [sys.executable, "-m", "modal"]
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 30
    assert "capture_output" not in kwargs
    assert "text" not in kwargs
    assert kwargs["env"] == {
        "HOME": "/safe/home",
        "MODAL_TOKEN_ID": "id",
        "MODAL_TOKEN_SECRET": "secret",
        "NO_COLOR": "1",
        "PATH": "/safe/bin",
        "PYTHONUNBUFFERED": "1",
    }


def test_transport_does_not_require_token_env_when_cli_session_is_available(tmp_path):
    adapters, transport = load_modules()
    executor = Executor([Result(stdout="[]")])
    runner = transport.StagingCommandTransport(
        executor=executor,
        source_env={"PATH": "/safe/bin", "HOME": "/safe/home"},
    )
    assert runner.run_json(modal_call(adapters, tmp_path)) == []
    env = executor.calls[0][1]["env"]
    assert "MODAL_TOKEN_ID" not in env
    assert "MODAL_TOKEN_SECRET" not in env


def test_mutating_commands_are_denied_until_explicitly_enabled(tmp_path):
    adapters, transport = load_modules()
    executor = Executor([Result()])
    call = modal_call(adapters, tmp_path, deploy=True)
    runner = transport.StagingCommandTransport(executor=executor, source_env={"PATH": "/bin", "HOME": "/root"})
    with pytest.raises(transport.TransportError) as caught:
        runner.run(call)
    assert caught.value.code == "staging_mutation_not_enabled"
    assert executor.calls == []

    enabled = transport.StagingCommandTransport(
        executor=executor,
        source_env={"PATH": "/bin", "HOME": "/root"},
        allow_mutation=True,
    )
    assert enabled.run(call) is None
    assert len(executor.calls) == 1


def test_dry_run_is_not_treated_as_mutation(tmp_path):
    adapters, transport = load_modules()
    executor = Executor([Result()])
    runner = transport.StagingCommandTransport(executor=executor, source_env={"PATH": "/bin", "HOME": "/root"})
    assert runner.run(cloudflare_dry_run(adapters, tmp_path)) is None


def test_forged_or_future_command_is_denied_by_default_and_when_mutation_enabled(tmp_path):
    adapters, transport = load_modules()
    forged = object.__new__(adapters.CommandCall)
    object.__setattr__(forged, "argv", ("npx", "--no-install", "wrangler", "secret", "delete", "TOKEN"))
    object.__setattr__(forged, "cwd", tmp_path.resolve())
    object.__setattr__(forged, "allowed_env", adapters.CLOUDFLARE_ENV_KEYS)
    object.__setattr__(forged, "timeout_seconds", 30)
    object.__setattr__(forged, "shell", False)
    for allow_mutation in (False, True):
        executor = Executor([Result()])
        runner = transport.StagingCommandTransport(
            executor=executor,
            source_env={"PATH": "/bin", "HOME": "/root"},
            allow_mutation=allow_mutation,
        )
        with pytest.raises(transport.TransportError) as caught:
            runner.run(forged)
        assert caught.value.code == "invalid_staging_command"
        assert executor.calls == []


@pytest.mark.parametrize(
    ("result", "code"),
    [
        (Result(returncode=1, stderr="SECRET provider payload"), "staging_command_failed"),
        (Result(stdout="not json"), "staging_json_invalid"),
        (Result(stdout="x" * (1024 * 1024 + 1)), "staging_output_too_large"),
        (Result(stderr="x" * (1024 * 1024 + 1)), "staging_output_too_large"),
    ],
)
def test_failures_are_typed_bounded_and_never_expose_provider_output(tmp_path, result, code):
    adapters, transport = load_modules()
    executor = Executor([result])
    runner = transport.StagingCommandTransport(executor=executor, source_env={"PATH": "/bin", "HOME": "/root"})
    with pytest.raises(transport.TransportError) as caught:
        runner.run_json(modal_call(adapters, tmp_path))
    assert caught.value.code == code
    assert "SECRET" not in str(caught.value)
    assert "provider" not in str(caught.value)


def test_timeout_is_sanitized(tmp_path):
    adapters, transport = load_modules()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output="SECRET")

    runner = transport.StagingCommandTransport(executor=timeout, source_env={"PATH": "/bin", "HOME": "/root"})
    with pytest.raises(transport.TransportError) as caught:
        runner.run(modal_call(adapters, tmp_path))
    assert caught.value.code == "staging_command_timeout"
    assert "SECRET" not in str(caught.value)
