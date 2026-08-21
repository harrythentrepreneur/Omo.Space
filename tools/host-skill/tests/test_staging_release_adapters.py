"""Staging-only Modal and Cloudflare release adapter contracts."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools" / "host-skill" / "staging_release_adapters.py"
WRANGLER_PATH = ROOT / "site" / "deploy" / "wrangler.toml"
PACKAGE_PATH = ROOT / "site" / "deploy" / "package.json"
SHA = "a" * 40
ARTIFACT = "b" * 64
SLUG = "label-normalizer-canary"


def load_module():
    spec = importlib.util.spec_from_file_location("staging_release_adapters", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def checkout(tmp_path: Path) -> Path:
    app = tmp_path / "containers" / SLUG / "modal_app.py"
    app.parent.mkdir(parents=True)
    app.write_text("# deterministic fixture\n", encoding="utf-8")
    worker = tmp_path / "site" / "deploy" / "worker.js"
    worker.parent.mkdir(parents=True)
    worker.write_text("export default {};\n", encoding="utf-8")
    (worker.parent / "wrangler.toml").write_text(WRANGLER_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_receipt_is_immutable_bounded_and_generation_independent():
    mod = load_module()
    receipt = mod.DeploymentReceipt(
        provider="modal",
        target="cognition-staging-label-normalizer-canary",
        environment="omo-release-staging",
        target_sha=SHA,
        artifact_hash=ARTIFACT,
        version_id="v-123",
        previous_version_id="v-122",
        reused=False,
        rollback_token="v-122",
    )
    assert receipt.status == "passed"
    assert mod.receipt_json(receipt) == json.dumps(
        {
            "artifact_hash": ARTIFACT,
            "environment": "omo-release-staging",
            "previous_version_id": "v-122",
            "provider": "modal",
            "reused": False,
            "rollback_token": "v-122",
            "status": "passed",
            "target": "cognition-staging-label-normalizer-canary",
            "target_sha": SHA,
            "version_id": "v-123",
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    with pytest.raises(Exception):
        replace(receipt, environment="production").environment = "production"


@pytest.mark.parametrize(
    ("provider", "target", "environment"),
    [
        ("cloudflare", "cognition-demos", "staging"),
        ("cloudflare", "cognition-demos-staging", "production"),
        ("modal", "cognition-label-normalizer-canary", "omo-release-staging"),
        ("modal", "cognition-staging-label-normalizer-canary", "main"),
    ],
)
def test_receipts_reject_every_production_or_alternate_target(provider, target, environment):
    mod = load_module()
    with pytest.raises(mod.AdapterError) as caught:
        mod.DeploymentReceipt(
            provider=provider,
            target=target,
            environment=environment,
            target_sha=SHA,
        artifact_hash=ARTIFACT,
            version_id="v-123",
            previous_version_id="v-122",
            reused=False,
            rollback_token="v-122",
        )
    assert caught.value.code == "invalid_staging_receipt"


def test_receipt_rejects_non_boolean_reused_and_new_deployment_without_rollback():
    mod = load_module()
    base = dict(
        provider="cloudflare",
        target="cognition-demos-staging",
        environment="staging",
        target_sha=SHA,
        artifact_hash=ARTIFACT,
        version_id="cf-new",
        previous_version_id="cf-old",
        rollback_token="cf-old",
    )
    with pytest.raises(mod.AdapterError):
        mod.DeploymentReceipt(**base, reused="false")
    with pytest.raises(mod.AdapterError):
        mod.DeploymentReceipt(
            **{**base, "previous_version_id": None, "rollback_token": None},
            reused=False,
        )


def test_command_call_rejects_shell_production_and_mixed_credentials(tmp_path):
    mod = load_module()
    root = checkout(tmp_path)
    with pytest.raises(mod.AdapterError):
        mod.CommandCall(("/bin/sh", "-c", "true"), root, ("PATH",), 30)
    with pytest.raises(mod.AdapterError):
        mod.CommandCall(
            ("npx", "--no-install", "wrangler", "deploy", "--env", "production", "--name", "cognition-demos"),
            root / "site" / "deploy",
            mod.CLOUDFLARE_ENV_KEYS,
            30,
        )
    with pytest.raises(mod.AdapterError):
        mod.CommandCall(
            (sys.executable, "-m", "modal", "environment", "list", "--json"),
            root,
            tuple(sorted(set(mod.MODAL_ENV_KEYS + mod.CLOUDFLARE_ENV_KEYS))),
            30,
        )


def test_modal_commands_are_staging_only_exact_sha_and_explicit_rollback(tmp_path):
    mod = load_module()
    root = checkout(tmp_path)
    app_name = "cognition-staging-label-normalizer-canary"
    assert mod.modal_preflight_call(root, SLUG).argv == (
        sys.executable, "-m", "modal", "environment", "list", "--json",
    )
    assert mod.modal_environment_create_call(root).argv == (
        sys.executable, "-m", "modal", "environment", "create", "omo-release-staging",
    )
    assert mod.modal_history_call(root, SLUG).argv == (
        sys.executable, "-m", "modal", "app", "history", app_name,
        "--env", "omo-release-staging", "--json",
    )
    deploy = mod.modal_deploy_call(root, SLUG, SHA)
    assert deploy.argv == (
        sys.executable, "-m", "modal", "deploy", str(root / "containers" / SLUG / "modal_app.py"),
        "--env", "omo-release-staging", "--name", app_name, "--tag", SHA,
    )
    rollback = mod.modal_rollback_call(root, SLUG, "v-122")
    assert rollback.argv == (
        sys.executable, "-m", "modal", "app", "rollback", app_name, "v-122",
        "--env", "omo-release-staging",
    )
    for call in (deploy, rollback):
        assert call.shell is False
        assert call.timeout_seconds <= 300
        assert call.allowed_env == (
            "HOME", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "NO_COLOR", "PATH", "PYTHONUNBUFFERED",
        )
        assert "production" not in " ".join(call.argv)


def test_cloudflare_commands_are_staging_only_exact_sha_and_explicit_rollback(tmp_path):
    mod = load_module()
    root = checkout(tmp_path)
    outdir = tmp_path / "private-dry-run"
    outdir.mkdir(mode=0o700)
    preflight = mod.cloudflare_preflight_call(root, outdir)
    assert preflight.argv == (
        "npx", "--no-install", "wrangler", "deploy", "--env", "staging",
        "--name", "cognition-demos-staging", "--dry-run", "--outdir", str(outdir),
    )
    versions = mod.cloudflare_deployments_call(root)
    assert versions.argv == (
        "npx", "--no-install", "wrangler", "deployments", "list", "--env", "staging",
        "--name", "cognition-demos-staging", "--json",
    )
    deploy = mod.cloudflare_deploy_call(root, SHA)
    assert deploy.argv == (
        "npx", "--no-install", "wrangler", "deploy", "--env", "staging",
        "--name", "cognition-demos-staging", "--strict", "--message", f"issue141:{SHA}",
    )
    bootstrap = mod.cloudflare_bootstrap_deploy_call(root)
    assert bootstrap.argv == (
        "npx", "--no-install", "wrangler", "deploy", "--env", "staging",
        "--name", "cognition-demos-staging", "--message", f"issue141:{'0' * 40}",
    )
    rollback = mod.cloudflare_rollback_call(root, "cf-old", SHA)
    assert rollback.argv == (
        "npx", "--no-install", "wrangler", "rollback", "cf-old", "--env", "staging",
        "--name", "cognition-demos-staging", "--message", f"staging rollback {SHA}", "--yes",
    )
    for call in (preflight, versions, bootstrap, deploy, rollback):
        assert call.cwd == root / "site" / "deploy"
        assert call.shell is False
        assert call.timeout_seconds <= 300
        assert call.allowed_env == (
            "CI", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "HOME", "NO_COLOR", "PATH",
        )
        assert "production" not in " ".join(call.argv)


def test_cloudflare_non_strict_deploy_is_bootstrap_only(tmp_path):
    mod = load_module()
    root = checkout(tmp_path) / "site" / "deploy"
    with pytest.raises(mod.AdapterError):
        mod.CommandCall(
            (
                "npx", "--no-install", "wrangler", "deploy", "--env", "staging",
                "--name", "cognition-demos-staging", "--message", f"issue141:{SHA}",
            ),
            root,
            mod.CLOUDFLARE_ENV_KEYS,
            300,
        )


@pytest.mark.parametrize("slug", ["../prod", "Production", "label_normalizer", "a" * 101])
def test_modal_target_rejects_unsafe_or_production_like_slugs(tmp_path, slug):
    mod = load_module()
    with pytest.raises(mod.AdapterError) as caught:
        mod.modal_deploy_call(checkout(tmp_path), slug, SHA)
    assert caught.value.code == "invalid_staging_target"


def test_command_builders_reject_bad_sha_and_missing_rollback(tmp_path):
    mod = load_module()
    root = checkout(tmp_path)
    with pytest.raises(mod.AdapterError):
        mod.modal_deploy_call(root, SLUG, "b" * 39)
    with pytest.raises(mod.AdapterError):
        mod.cloudflare_deploy_call(root, "b" * 39)
    with pytest.raises(mod.AdapterError):
        mod.modal_rollback_call(root, SLUG, "")
    with pytest.raises(mod.AdapterError):
        mod.cloudflare_rollback_call(root, "", SHA)


def test_modal_readback_binds_target_sha_and_prior_version():
    mod = load_module()
    before = [
        {"Version": "v2", "Time deployed": "2026-08-20 00:00:00", "Tag": "b" * 40},
    ]
    after = [
        {"Version": "v3", "Time deployed": "2026-08-21 00:00:00", "Tag": SHA},
        *before,
    ]
    receipt = mod.modal_receipt(before, after, SLUG, SHA, ARTIFACT)
    assert receipt.version_id == "v3"
    assert receipt.previous_version_id == "v2"
    assert receipt.rollback_token == "v2"
    assert receipt.target_sha == SHA
    assert receipt.environment == "omo-release-staging"
    assert receipt.reused is False

    reused = mod.modal_receipt(after, after, SLUG, SHA, ARTIFACT)
    assert reused.version_id == "v3"
    assert reused.reused is True
    assert reused.previous_version_id is None


def test_cloudflare_readback_binds_message_sha_and_prior_version():
    mod = load_module()
    versions_before = [
        {"id": "cf-old", "annotations": {"workers/message": "issue141:" + "b" * 40}},
    ]
    versions_after = [
        *versions_before,
        {"id": "cf-new", "annotations": {"workers/message": f"issue141:{SHA}"}},
    ]
    deployments_before = [
        {"id": "dep-old", "versions": [{"version_id": "cf-old", "percentage": 100}]},
    ]
    deployments_after = [
        *deployments_before,
        {"id": "dep-new", "versions": [{"version_id": "cf-new", "percentage": 100}]},
    ]
    receipt = mod.cloudflare_receipt(
        versions_before, versions_after, deployments_before, deployments_after, SHA, ARTIFACT
    )
    assert receipt.target == "cognition-demos-staging"
    assert receipt.version_id == "cf-new"
    assert receipt.previous_version_id == "cf-old"
    assert receipt.rollback_token == "cf-old"
    assert receipt.reused is False


@pytest.mark.parametrize(
    ("provider", "payload"),
    [
        ("modal", [{"Version": "v1", "Tag": "b" * 40}]),
        ("cloudflare", [{"id": "cf1", "annotations": {"workers/message": "issue141:" + "b" * 40}}]),
    ],
)
def test_readback_fails_closed_on_wrong_sha_or_state(provider, payload):
    mod = load_module()
    with pytest.raises(mod.AdapterError) as caught:
        if provider == "modal":
            mod.modal_receipt(payload, payload, SLUG, SHA, ARTIFACT)
        else:
            deployments = [{"id": "dep1", "versions": [{"version_id": "cf1", "percentage": 100}]}]
            mod.cloudflare_receipt(payload, payload, deployments, deployments, SHA, ARTIFACT)
    assert caught.value.code == "staging_readback_failed"


def test_new_readback_requires_exactly_one_new_version_and_a_rollback_predecessor():
    mod = load_module()
    with pytest.raises(mod.AdapterError):
        mod.modal_receipt([], [{"Version": "v1", "Tag": SHA}], SLUG, SHA, ARTIFACT)
    before_versions = [{"id": "old", "annotations": {"workers/message": "old"}}]
    after_versions = before_versions + [
        {"id": "new1", "annotations": {"workers/message": f"issue141:{SHA}"}},
        {"id": "new2", "annotations": {"workers/message": f"issue141:{SHA}"}},
    ]
    before_deployments = [{"id": "d0", "versions": [{"version_id": "old", "percentage": 100}]}]
    after_deployments = before_deployments + [
        {"id": "d1", "versions": [{"version_id": "new2", "percentage": 100}]}
    ]
    with pytest.raises(mod.AdapterError):
        mod.cloudflare_receipt(
            before_versions, after_versions, before_deployments, after_deployments, SHA, ARTIFACT
        )


def test_wrangler_staging_environment_has_no_routes_crons_or_production_vars():
    config = tomllib.loads(WRANGLER_PATH.read_text(encoding="utf-8"))
    staging = config["env"]["staging"]
    staging_url = "https://omo-space-omo-release-staging--cognition-staging-label-n-11704d.modal.run"
    assert staging["name"] == "cognition-demos-staging"
    assert staging["workers_dev"] is True
    assert staging["routes"] == []
    assert staging["triggers"] == {"crons": []}
    assert staging["vars"] == {
        "ENVIRONMENT": "staging",
        "LABEL_NORMALIZER_CANARY_MODAL_URL": staging_url,
    }
    assert config["vars"].get("LABEL_NORMALIZER_CANARY_MODAL_URL") is None
    assert staging_url != "https://omo-space--cognition-label-normalizer-canary-api.modal.run"


def test_wrangler_is_exact_local_dev_dependency():
    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
    assert package["devDependencies"] == {"wrangler": "4.125.0"}


def test_wrangler_bundle_digest_uses_only_compiled_worker_bytes(tmp_path):
    mod = load_module()
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir(mode=0o700)
    second.mkdir(mode=0o700)
    worker = b"export default { fetch() { return new Response('ok') } }\n"
    (first / "worker.js").write_bytes(worker)
    (second / "worker.js").write_bytes(worker)
    (first / "README.md").write_text("generated at time one", encoding="utf-8")
    (second / "README.md").write_text("generated at time two", encoding="utf-8")
    (first / "worker.js.map").write_text('{"sourceRoot":"/tmp/one"}', encoding="utf-8")
    (second / "worker.js.map").write_text('{"sourceRoot":"/tmp/two"}', encoding="utf-8")
    expected = hashlib.sha256(worker).hexdigest()
    assert mod.cloudflare_bundle_sha256(first) == expected
    assert mod.cloudflare_bundle_sha256(second) == expected


@pytest.mark.parametrize("name", ["missing", "directory", "symlink"])
def test_wrangler_bundle_digest_fails_closed_on_unsafe_worker_artifact(tmp_path, name):
    mod = load_module()
    outdir = tmp_path / name
    outdir.mkdir(mode=0o700)
    if name == "directory":
        (outdir / "worker.js").mkdir()
    elif name == "symlink":
        target = tmp_path / "target.js"
        target.write_text("safe", encoding="utf-8")
        (outdir / "worker.js").symlink_to(target)
    with pytest.raises(mod.AdapterError) as caught:
        mod.cloudflare_bundle_sha256(outdir)
    assert caught.value.code == "staging_artifact_invalid"
