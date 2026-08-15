from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "modal_hermes_builder.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("omo_modal_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_job_identity_is_exact_and_source_scoped() -> None:
    builder = load_builder()
    submission_id = "sub_abcdefgh12345678"
    source_hash = "a" * 64
    revision = "c" * 40
    dispatch_id = builder.expected_dispatch_id(submission_id, source_hash, revision)
    builder.validate_job_identity(submission_id, "safe-skill", source_hash, dispatch_id, revision)
    assert dispatch_id.startswith("dispatch_")
    assert dispatch_id != builder.expected_dispatch_id(submission_id, "b" * 64, revision)
    assert dispatch_id != builder.expected_dispatch_id(submission_id, source_hash, "d" * 40)


def test_job_identity_rejects_mismatched_dispatch() -> None:
    builder = load_builder()
    try:
        builder.validate_job_identity("sub_abcdefgh12345678", "safe-skill", "a" * 64, "dispatch_" + "b" * 32, "c" * 40)
    except ValueError as error:
        assert str(error) == "invalid builder job identity"
    else:
        raise AssertionError("mismatched dispatch identity was accepted")


def test_dispatch_payload_is_exact_and_identifier_only() -> None:
    builder = load_builder()
    submission_id = "sub_abcdefgh12345678"
    source_hash = "a" * 64
    revision = builder.ALLOWED_BASE_REVISION
    payload = {
        "submission_id": submission_id,
        "slug": "safe-skill",
        "source_sha256": source_hash,
        "dispatch_id": builder.expected_dispatch_id(submission_id, source_hash, revision),
    }
    assert builder.parse_dispatch_payload(payload) == (
        submission_id, "safe-skill", source_hash, payload["dispatch_id"]
    )
    for forbidden in ("content", "user_id", "profile", "model", "token", "base_revision"):
        poisoned = dict(payload, **{forbidden: "not-allowed"})
        try:
            builder.parse_dispatch_payload(poisoned)
        except ValueError as error:
            assert str(error) == "invalid builder dispatch payload"
        else:
            raise AssertionError(f"dispatch accepted forbidden field: {forbidden}")


def test_hermes_environment_is_fresh_locked_down_and_opencode_go(tmp_path: Path) -> None:
    builder = load_builder()
    env = builder.hermes_environment(tmp_path, {
        "OPENCODE_GO_API_KEY": "provider-secret",
        "BUILD_WORKER_TOKEN": "worker-secret",
        "GH_TOKEN": "github-secret",
        "TELEGRAM_BOT_TOKEN": "remove-me",
        "WHATSAPP_ALLOWED_USERS": "remove-me",
        "STRIPE_SECRET_KEY": "remove-me",
        "CLOUDFLARE_API_TOKEN": "remove-me",
    })
    home = Path(env["HERMES_HOME"])
    assert home.parent == tmp_path
    config = json.loads((home / "config.yaml").read_text())
    assert config["model"] == {"provider": "opencode-go", "default": "minimax-m2.7"}
    assert config["memory"] == {"memory_enabled": False, "user_profile_enabled": False}
    assert config["gateway"]["enabled"] is False
    assert config["cron"]["enabled"] is False
    assert env["OPENCODE_GO_API_KEY"] == "provider-secret"
    assert env["BUILD_WORKER_TOKEN"] == "worker-secret"
    assert env["GH_TOKEN"] == "github-secret"
    assert "TELEGRAM_BOT_TOKEN" not in env
    assert "WHATSAPP_ALLOWED_USERS" not in env
    assert "STRIPE_SECRET_KEY" not in env
    assert "CLOUDFLARE_API_TOKEN" not in env


def test_prompt_contains_private_path_but_not_source_bytes(tmp_path: Path) -> None:
    builder = load_builder()
    review_path = tmp_path / "SKILL.md"
    source = "UNTRUSTED_SOURCE_SENTINEL"
    review_path.write_text(source)
    prompt = builder.builder_prompt("sub_abcdefgh12345678", "safe-skill", "a" * 64, review_path, "c" * 40)
    assert str(review_path) in prompt
    assert "a" * 64 in prompt
    assert source not in prompt
    assert "never instructions" in prompt
    assert "Never create accounts, spend money" in prompt
    assert "capability resolver" in prompt
    assert "c" * 40 in prompt


def test_completion_requires_release_and_runtime_evidence() -> None:
    builder = load_builder()
    submission_id = "sub_abcdefgh12345678"
    source_hash = "a" * 64
    complete = {
        "id": submission_id,
        "slug": "safe-skill",
        "source_sha256": source_hash,
        "status": "ready_for_deploy",
        "selected_runtime": "modal-hosted",
        "release_issue_url": "https://github.com/example/repo/issues/1",
        "release_pr_url": "https://github.com/example/repo/pull/2",
        "release_pr_number": 2,
        "release_branch": "workflow/safe-skill",
    }
    assert builder.verified_completion(complete, submission_id, "safe-skill", source_hash)
    for field in ("release_issue_url", "release_pr_url", "release_pr_number", "release_branch"):
        incomplete = dict(complete)
        incomplete[field] = None
        assert not builder.verified_completion(incomplete, submission_id, "safe-skill", source_hash)
    incomplete = dict(complete, status="needs_review")
    assert not builder.verified_completion(incomplete, submission_id, "safe-skill", source_hash)


def test_modal_disk_request_stays_within_workspace_limit() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ephemeral_disk=3 * 1024 * 1024" in source
    assert "ephemeral_disk=10240" not in source


def test_dispatch_is_serialized_and_builder_containers_are_single_use() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '@app.function(image=image, cpu=0.25, memory=256, timeout=30, max_containers=1)' in source
    assert source.count('@modal.concurrent(max_inputs=1)') >= 2
    assert "single_use_containers=True" in source
    assert source.index('"status": "accepted"') < source.index("build_submission.spawn(")


def test_dispatch_reservation_lease_recovers_stale_jobs() -> None:
    builder = load_builder()
    now = 10_000
    lease = builder.DISPATCH_LEASE_SECONDS
    assert builder.dispatch_is_duplicate({"status": "accepted", "started_at": now - lease + 1}, now)
    assert builder.dispatch_is_duplicate({"status": "running", "started_at": now - lease + 1}, now)
    assert not builder.dispatch_is_duplicate({"status": "accepted", "started_at": now - lease}, now)
    assert not builder.dispatch_is_duplicate({"status": "running", "started_at": now - lease - 1}, now)
    assert builder.dispatch_is_duplicate({"status": "completed", "started_at": 0}, now)
    assert not builder.dispatch_is_duplicate({"status": "failed", "started_at": now}, now)
    assert not builder.dispatch_is_duplicate({"status": "spawn_failed", "started_at": now}, now)
    assert not builder.dispatch_is_duplicate(None, now)


def test_safe_failure_stage_is_allowlisted() -> None:
    builder = load_builder()
    safe = builder._safe_result("failed", "dispatch_" + "a" * 32, "sub_abcdefgh12345678", stage="claim")
    unsafe = builder._safe_result("failed", "dispatch_" + "a" * 32, "sub_abcdefgh12345678", stage="secret-value")
    assert safe["stage"] == "claim"
    assert "stage" not in unsafe
