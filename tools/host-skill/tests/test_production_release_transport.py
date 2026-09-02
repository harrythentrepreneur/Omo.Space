"""Contracts for the credential-isolated production command transport."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ADAPTER_PATH = ROOT / "tools" / "host-skill" / "production_release_adapters.py"
TRANSPORT_PATH = ROOT / "tools" / "host-skill" / "production_release_transport.py"


def load_modules():
    adapter_spec = importlib.util.spec_from_file_location("production_release_adapters", ADAPTER_PATH)
    assert adapter_spec and adapter_spec.loader
    adapters = importlib.util.module_from_spec(adapter_spec)
    sys.modules[adapter_spec.name] = adapters
    adapter_spec.loader.exec_module(adapters)
    transport_spec = importlib.util.spec_from_file_location("production_release_transport", TRANSPORT_PATH)
    assert transport_spec and transport_spec.loader
    transport = importlib.util.module_from_spec(transport_spec)
    sys.modules[transport_spec.name] = transport
    transport_spec.loader.exec_module(transport)
    return adapters, transport


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


class Executor:
    def __init__(self, results):
        self.results, self.calls = list(results), []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        result = self.results.pop(0)
        kwargs["stdout"].write(result.stdout.encode())
        kwargs["stderr"].write(result.stderr.encode())
        return result


def checkout(tmp_path: Path) -> Path:
    app = tmp_path / "containers" / "label-normalizer-canary" / "modal_app.py"
    app.parent.mkdir(parents=True)
    app.write_text("# fixture", encoding="utf-8")
    worker = tmp_path / "site" / "deploy" / "worker.js"
    worker.parent.mkdir(parents=True)
    worker.write_text("export default {};", encoding="utf-8")
    (worker.parent / "wrangler.toml").write_text("name='cognition-demos'", encoding="utf-8")
    return tmp_path.resolve()


def make_transport(transport, root: Path, **kwargs):
    return transport.ProductionCommandTransport(
        trusted_checkout=str(root), trusted_sha="a" * 40,
        checkout_verifier=lambda checkout_path, target_sha: (
            checkout_path == str(root) and target_sha == "a" * 40
        ),
        **kwargs,
    )


def test_modal_environment_is_fresh_allowlisted_and_never_receives_cloudflare(tmp_path):
    adapters, transport = load_modules()
    executor = Executor([Result(stdout="[]")])
    source = {
        "PATH": "/safe/bin", "HOME": "/safe/home", "MODAL_TOKEN_ID": "id",
        "MODAL_TOKEN_SECRET": "secret", "CLOUDFLARE_API_TOKEN": "must-not-cross",
        "GITHUB_TOKEN": "must-not-cross", "HTTP_PROXY": "must-not-cross",
    }
    root = checkout(tmp_path)
    runner = make_transport(transport, root, executor=executor, source_env=source)
    assert runner.run_json(adapters.modal_preflight_call(root, adapters.MODAL_ALLOWED_SLUG)) == []
    args, kwargs = executor.calls[0]
    assert args[0][:3] == [sys.executable, "-m", "modal"]
    assert kwargs["shell"] is False
    assert kwargs["env"]["HOME"] != "/safe/home"
    assert "omo-production-provider-" in kwargs["env"]["HOME"]
    assert {key: value for key, value in kwargs["env"].items() if key != "HOME"} == {
        "MODAL_TOKEN_ID": "id", "MODAL_TOKEN_SECRET": "secret", "NO_COLOR": "1",
        "PATH": "/safe/bin", "PYTHONUNBUFFERED": "1",
    }


def test_first_modal_rollback_stop_and_list_cross_real_transport_boundary(tmp_path):
    adapters, transport = load_modules()
    root = checkout(tmp_path)
    executor = Executor([
        Result(stdout=""),
        Result(stdout='[{"Description":"cognition-label-normalizer-canary","State":"stopped","Tasks":"0"}]'),
    ])
    runner = make_transport(
        transport, root, executor=executor,
        source_env={"PATH": "/safe/bin", "MODAL_TOKEN_ID": "id", "MODAL_TOKEN_SECRET": "secret"},
        allow_mutation=True,
    )
    runner.run(adapters.modal_stop_call(root, adapters.MODAL_ALLOWED_SLUG))
    rows = runner.run_json(adapters.modal_apps_call(root, adapters.MODAL_ALLOWED_SLUG))
    assert adapters.modal_app_stopped(rows, adapters.MODAL_ALLOWED_SLUG) is True
    assert len(executor.calls) == 2


def test_cloudflare_environment_is_fresh_allowlisted_and_never_receives_modal(tmp_path):
    adapters, transport = load_modules()
    root = checkout(tmp_path)
    executor = Executor([Result(stdout="[]")])
    source = {
        "PATH": "/safe/bin", "HOME": "/safe/home", "CLOUDFLARE_ACCOUNT_ID": "account",
        "CLOUDFLARE_API_TOKEN": "token", "MODAL_TOKEN_ID": "must-not-cross",
        "MODAL_TOKEN_SECRET": "must-not-cross", "GITHUB_TOKEN": "must-not-cross",
    }
    runner = make_transport(transport, root, executor=executor, source_env=source)
    assert runner.run_json(adapters.cloudflare_versions_call(root)) == []
    child_env = executor.calls[0][1]["env"]
    assert child_env["HOME"] != "/safe/home" and "omo-production-provider-" in child_env["HOME"]
    assert {key: value for key, value in child_env.items() if key != "HOME"} == {
        "CI": "1", "CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_API_TOKEN": "token",
        "NO_COLOR": "1", "PATH": "/safe/bin",
    }


def test_mutations_require_explicit_gate_and_dry_run_remains_read_only(tmp_path):
    adapters, transport = load_modules()
    root = checkout(tmp_path)
    deploy = adapters.cloudflare_deploy_call(root, "a" * 40)
    denied_executor = Executor([Result()])
    denied = make_transport(transport, root, executor=denied_executor, source_env={"PATH": "/bin"})
    with pytest.raises(transport.TransportError) as caught:
        denied.run(deploy)
    assert caught.value.code == "production_mutation_not_enabled" and denied_executor.calls == []

    outdir = tmp_path / "private"
    outdir.mkdir(mode=0o700)
    read_executor = Executor([Result()])
    reader = make_transport(transport, root, executor=read_executor, source_env={"PATH": "/bin"})
    assert reader.run(adapters.cloudflare_preflight_call(root, outdir)) is None

    write_executor = Executor([Result()])
    writer = make_transport(transport, root,
        executor=write_executor, source_env={"PATH": "/bin"}, allow_mutation=True
    )
    assert writer.run(deploy) is None and len(write_executor.calls) == 1


def test_forged_secret_or_future_commands_fail_even_with_mutation_enabled(tmp_path):
    adapters, transport = load_modules()
    root = checkout(tmp_path)
    forged = object.__new__(adapters.CommandCall)
    object.__setattr__(forged, "argv", ("npx", "--no-install", "wrangler", "secret", "put", "TOKEN"))
    object.__setattr__(forged, "cwd", root)
    object.__setattr__(forged, "allowed_env", adapters.CLOUDFLARE_ENV_KEYS)
    object.__setattr__(forged, "timeout_seconds", 30)
    object.__setattr__(forged, "shell", False)
    executor = Executor([Result()])
    runner = make_transport(transport, root,
        executor=executor, source_env={"PATH": "/bin"}, allow_mutation=True
    )
    with pytest.raises(transport.TransportError) as caught:
        runner.run(forged)
    assert caught.value.code == "invalid_production_command" and executor.calls == []


def test_valid_command_from_untrusted_or_unverified_checkout_is_rejected_before_execution(tmp_path):
    adapters, transport = load_modules()
    trusted = checkout(tmp_path / "trusted")
    other = checkout(tmp_path / "other")
    executor = Executor([Result()])
    runner = make_transport(
        transport, trusted, executor=executor, source_env={"PATH": "/bin"}, allow_mutation=True
    )
    with pytest.raises(transport.TransportError) as caught:
        runner.run(adapters.cloudflare_deploy_call(other, "a" * 40))
    assert caught.value.code == "invalid_production_checkout" and executor.calls == []

    unverified = transport.ProductionCommandTransport(
        trusted_checkout=str(trusted), trusted_sha="a" * 40,
        checkout_verifier=lambda checkout_path, target_sha: False,
        executor=executor, source_env={"PATH": "/bin"}, allow_mutation=True,
    )
    with pytest.raises(transport.TransportError) as caught:
        unverified.run(adapters.cloudflare_deploy_call(trusted, "a" * 40))
    assert caught.value.code == "invalid_production_checkout" and executor.calls == []


def test_default_checkout_verifier_rejects_untracked_contamination(tmp_path):
    adapters, transport = load_modules()
    root = checkout(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    (root / "site" / "deploy" / "untracked-provider-input.js").write_text(
        "export default 'unsafe';", encoding="utf-8"
    )
    executor = Executor([Result(stdout="[]")])
    runner = transport.ProductionCommandTransport(
        trusted_checkout=str(root), trusted_sha=sha, executor=executor,
        source_env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    with pytest.raises(transport.TransportError) as caught:
        runner.run_json(adapters.cloudflare_versions_call(root))
    assert caught.value.code == "invalid_production_checkout" and executor.calls == []


@pytest.mark.parametrize(
    ("result", "code"),
    [
        (Result(returncode=1, stderr="SECRET provider payload"), "production_command_failed"),
        (Result(stdout="not json"), "production_json_invalid"),
        (Result(stdout="x" * (1024 * 1024 + 1)), "production_output_too_large"),
        (Result(stderr="x" * (1024 * 1024 + 1)), "production_output_too_large"),
    ],
)
def test_failures_are_typed_bounded_and_never_echo_provider_output(tmp_path, result, code):
    adapters, transport = load_modules()
    root = checkout(tmp_path)
    executor = Executor([result])
    runner = make_transport(transport, root, executor=executor, source_env={"PATH": "/bin"})
    with pytest.raises(transport.TransportError) as caught:
        runner.run_json(adapters.modal_preflight_call(root, adapters.MODAL_ALLOWED_SLUG))
    assert caught.value.code == code
    assert "SECRET" not in str(caught.value) and "provider" not in str(caught.value)


def test_timeout_is_sanitized(tmp_path):
    adapters, transport = load_modules()
    root = checkout(tmp_path)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output="SECRET")

    runner = make_transport(transport, root, executor=timeout, source_env={"PATH": "/bin"})
    with pytest.raises(transport.TransportError) as caught:
        runner.run(adapters.modal_preflight_call(root, adapters.MODAL_ALLOWED_SLUG))
    assert caught.value.code == "production_command_timeout" and "SECRET" not in str(caught.value)
