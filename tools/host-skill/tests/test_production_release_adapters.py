"""Production-only Modal and Cloudflare release adapter contracts."""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools" / "host-skill" / "production_release_adapters.py"
SHA = "a" * 40
ARTIFACT = "b" * 64
SLUG = "label-normalizer-canary"


def load_module():
    spec = importlib.util.spec_from_file_location("production_release_adapters", MODULE_PATH)
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
    (worker.parent / "wrangler.toml").write_text("name = 'cognition-demos'\n", encoding="utf-8")
    return tmp_path.resolve()


def test_receipt_is_closed_production_bound_and_finalizer_compatible():
    mod = load_module()
    receipt = mod.DeploymentReceipt(
        "modal", "cognition-label-normalizer-canary", "main", SHA, ARTIFACT,
        "v3", "v2", False, "v2",
    )
    payload = json.loads(mod.receipt_json(receipt))
    assert payload == {
        "artifact_hash": ARTIFACT,
        "environment": "main",
        "previous_version_id": "v2",
        "provider": "modal",
        "reused": False,
        "rollback_token": "v2",
        "status": "passed",
        "target": "cognition-label-normalizer-canary",
        "target_sha": SHA,
        "version_id": "v3",
    }
    with pytest.raises(mod.AdapterError):
        replace(receipt, environment="omo-release-staging")
    with pytest.raises(mod.AdapterError):
        replace(receipt, target="other-app")
    with pytest.raises(mod.AdapterError):
        replace(receipt, reused="false")


def test_modal_commands_are_exact_main_target_and_sha(tmp_path):
    mod = load_module()
    root = checkout(tmp_path)
    assert mod.modal_preflight_call(root, SLUG).argv == (
        sys.executable, "-m", "modal", "environment", "list", "--json",
    )
    assert mod.modal_history_call(root, SLUG).argv == (
        sys.executable, "-m", "modal", "app", "history", "cognition-label-normalizer-canary",
        "--env", "main", "--json",
    )
    deploy = mod.modal_deploy_call(root, SLUG, SHA)
    assert deploy.argv == (
        sys.executable, "-m", "modal", "deploy", str(root / "containers" / SLUG / "modal_app.py"),
        "--env", "main", "--name", "cognition-label-normalizer-canary", "--tag", SHA,
    )
    assert mod.modal_rollback_call(root, SLUG, "v2").argv == (
        sys.executable, "-m", "modal", "app", "rollback", "cognition-label-normalizer-canary",
        "v2", "--env", "main",
    )
    assert deploy.allowed_env == mod.MODAL_ENV_KEYS
    assert "CLOUDFLARE_API_TOKEN" not in deploy.allowed_env


def test_cloudflare_commands_are_exact_production_target_without_env_alias(tmp_path):
    mod = load_module()
    root = checkout(tmp_path)
    outdir = tmp_path / "private"
    outdir.mkdir(mode=0o700)
    assert mod.cloudflare_preflight_call(root, outdir).argv == (
        "npx", "--no-install", "wrangler", "deploy", "--name", "cognition-demos",
        "--dry-run", "--outdir", str(outdir.resolve()),
    )
    assert mod.cloudflare_versions_call(root).argv == (
        "npx", "--no-install", "wrangler", "versions", "list", "--name", "cognition-demos", "--json",
    )
    assert mod.cloudflare_deployments_call(root).argv == (
        "npx", "--no-install", "wrangler", "deployments", "list", "--name", "cognition-demos", "--json",
    )
    deploy = mod.cloudflare_deploy_call(root, SHA)
    assert deploy.argv == (
        "npx", "--no-install", "wrangler", "deploy", "--name", "cognition-demos",
        "--strict", "--message", f"issue141:{SHA}",
    )
    assert mod.cloudflare_rollback_call(root, "cf-old", SHA).argv == (
        "npx", "--no-install", "wrangler", "rollback", "cf-old", "--name", "cognition-demos",
        "--message", f"production rollback {SHA}", "--yes",
    )
    assert deploy.allowed_env == mod.CLOUDFLARE_ENV_KEYS
    assert "MODAL_TOKEN_SECRET" not in deploy.allowed_env
    assert "--env" not in deploy.argv


def test_arbitrary_staging_secret_and_shell_commands_fail_closed(tmp_path):
    mod = load_module()
    root = checkout(tmp_path)
    bad_calls = [
        (("/bin/sh", "-c", "true"), ("PATH",)),
        (("npx", "--no-install", "wrangler", "deploy", "--env", "staging", "--name", "cognition-demos-staging"), mod.CLOUDFLARE_ENV_KEYS),
        (("npx", "--no-install", "wrangler", "secret", "put", "TOKEN"), mod.CLOUDFLARE_ENV_KEYS),
    ]
    for argv, env in bad_calls:
        with pytest.raises(mod.AdapterError) as caught:
            mod.CommandCall(argv, root, env, 30)
        assert caught.value.code == "invalid_production_command"
    with pytest.raises(mod.AdapterError):
        mod.modal_deploy_call(root, "../unsafe", SHA)
    with pytest.raises(mod.AdapterError):
        mod.cloudflare_deploy_call(root, "c" * 39)


def test_modal_and_worker_sources_reject_symlink_escape(tmp_path):
    mod = load_module()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "modal_app.py").write_text("# outside", encoding="utf-8")
    (outside / "worker.js").write_text("export default {};", encoding="utf-8")

    modal_root = checkout(tmp_path / "modal-case")
    modal_path = modal_root / "containers" / SLUG / "modal_app.py"
    modal_path.unlink()
    modal_path.symlink_to(outside / "modal_app.py")
    with pytest.raises(mod.AdapterError):
        mod.modal_deploy_call(modal_root, SLUG, SHA)

    worker_root = checkout(tmp_path / "worker-case")
    worker_path = worker_root / "site" / "deploy" / "worker.js"
    worker_path.unlink()
    worker_path.symlink_to(outside / "worker.js")
    with pytest.raises(mod.AdapterError):
        mod.cloudflare_deploy_call(worker_root, SHA)

    directory_root = checkout(tmp_path / "directory-case")
    deploy_dir = directory_root / "site" / "deploy"
    for child in deploy_dir.iterdir():
        child.unlink()
    deploy_dir.rmdir()
    deploy_dir.symlink_to(outside, target_is_directory=True)
    with pytest.raises(mod.AdapterError):
        mod.cloudflare_versions_call(directory_root)


def test_modal_readback_binds_sha_and_rollback_predecessor():
    mod = load_module()
    before = [{"Version": "v2", "Tag": "c" * 40}]
    after = [{"Version": "v3", "Tag": SHA}, *before]
    receipt = mod.modal_receipt(before, after, SLUG, SHA, ARTIFACT)
    assert receipt.version_id == "v3" and receipt.previous_version_id == "v2"
    assert receipt.rollback_token == "v2" and receipt.status == "passed"
    reused = mod.modal_receipt(after, after, SLUG, SHA, ARTIFACT)
    assert reused.reused is True and reused.previous_version_id is None
    duplicated = [{"Version": "v5", "Tag": SHA}, {"Version": "v4", "Tag": SHA}, *before]
    recovered = mod.modal_receipt(duplicated, duplicated, SLUG, SHA, ARTIFACT)
    assert recovered.reused is True and recovered.version_id == "v5"
    with pytest.raises(mod.AdapterError):
        mod.modal_receipt([], [{"Version": "v1", "Tag": SHA}], SLUG, SHA, ARTIFACT)


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ([{"Version": "v5", "Tag": SHA}, {"Version": "bad version", "Tag": SHA}],
         [{"Version": "v5", "Tag": SHA}, {"Version": "bad version", "Tag": SHA}]),
        ([{"Version": 5, "Tag": SHA}], [{"Version": 5, "Tag": SHA}]),
        ([{"Version": "v2", "Tag": None}, {"Version": "v2", "Tag": None}],
         [{"Version": "v3", "Tag": SHA}, {"Version": "v2", "Tag": None}, {"Version": "v2", "Tag": None}]),
        ([{"Version": "v2", "Tag": "not-a-sha"}],
         [{"Version": "v3", "Tag": SHA}, {"Version": "v2", "Tag": "not-a-sha"}]),
        ([{"Version": "v2"}], [{"Version": "v3", "Tag": SHA}, {"Version": "v2"}]),
        ([{"Version": "v2", "Tag": None}, {"Version": "v1", "Tag": None}],
         [{"Version": "v3", "Tag": SHA}]),
        ([{"Version": "v2", "Tag": None}, {"Version": "v1", "Tag": None}],
         [{"Version": "v3", "Tag": SHA}, {"Version": "v1", "Tag": None}, {"Version": "v2", "Tag": None}]),
    ],
)
def test_modal_readback_rejects_malformed_or_changed_ordered_history(before, after):
    mod = load_module()
    with pytest.raises(mod.AdapterError, match="production_readback_failed"):
        mod.modal_receipt(before, after, SLUG, SHA, ARTIFACT)


def test_cloudflare_readback_binds_message_active_version_and_rollback():
    mod = load_module()
    versions_before = [{"id": "cf-old", "annotations": {"workers/message": "old"}}]
    versions_after = [*versions_before, {"id": "cf-new", "annotations": {"workers/message": f"issue141:{SHA}"}}]
    deployments_before = [{"id": "dep-old", "versions": [{"version_id": "cf-old", "percentage": 100}]}]
    deployments_after = [*deployments_before, {"id": "dep-new", "versions": [{"version_id": "cf-new", "percentage": 100}]}]
    receipt = mod.cloudflare_receipt(
        versions_before, versions_after, deployments_before, deployments_after, SHA, ARTIFACT
    )
    assert receipt.target == "cognition-demos" and receipt.environment == "production"
    assert receipt.version_id == "cf-new" and receipt.rollback_token == "cf-old"
    with pytest.raises(mod.AdapterError):
        mod.cloudflare_receipt(
            versions_before, versions_after, deployments_before,
            [{"id": "dep-new", "versions": [{"version_id": "cf-old", "percentage": 100}]}],
            SHA, ARTIFACT,
        )


def test_cloudflare_readback_adopts_active_exact_target_without_mutation():
    mod = load_module()
    rows = [
        {"id": "cf-old", "annotations": {"workers/message": "old"}},
        {"id": "cf-first", "annotations": {"workers/message": f"issue141:{SHA}"}},
        {"id": "cf-active", "annotations": {"workers/message": f"issue141:{SHA}"}},
    ]
    deployments = [
        {"id": "dep-old", "versions": [{"version_id": "cf-old", "percentage": 100}]},
        {"id": "dep-active", "versions": [{"version_id": "cf-active", "percentage": 100}]},
    ]
    receipt = mod.cloudflare_receipt(rows, rows, deployments, deployments, SHA, ARTIFACT)
    assert receipt.version_id == "cf-active"
    assert receipt.reused is True and receipt.previous_version_id is None


def test_bundle_hash_reads_only_bounded_authoritative_worker(tmp_path):
    mod = load_module()
    outdir = tmp_path / "out"
    outdir.mkdir()
    worker = outdir / "worker.js"
    worker.write_bytes(b"compiled-worker")
    assert mod.cloudflare_bundle_sha256(outdir) == __import__("hashlib").sha256(b"compiled-worker").hexdigest()
    worker.unlink()
    with pytest.raises(mod.AdapterError):
        mod.cloudflare_bundle_sha256(outdir)
