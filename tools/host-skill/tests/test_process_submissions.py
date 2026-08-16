"""Tests for reviewed submission deployment routing."""

from __future__ import annotations

import importlib.util
import json
import io
import os
import subprocess
import sys
import stat
from pathlib import Path
from urllib.error import HTTPError

import pytest


ROOT = Path(__file__).resolve().parents[3]
PROCESS_PATH = ROOT / "tools" / "host-skill" / "process-submissions.py"
PROFILE_PATH = ROOT / "packages" / "skill-to-modal" / "profiles" / "facebook-ads-copywriter.json"
SKILL_PATH = ROOT / "packages" / "facebook-ads-copywriter" / "SKILL.md"


def load_process_submissions():
    sys.path.insert(0, str(PROCESS_PATH.parent))
    spec = importlib.util.spec_from_file_location("process_submissions_test", PROCESS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_profile(tmp_path: Path, runtime_preference: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["runtime_preference"] = runtime_preference
    if runtime_preference == "modal-hosted":
        profile["marketplace"]["deployment"]["default_endpoint"] = "https://omo-space--cognition-facebook-ads-copywriter-api.modal.run"
    profile_path = tmp_path / f"profile-{runtime_preference}.json"
    profile_path.write_text(json.dumps(profile, sort_keys=True), encoding="utf-8")
    return profile_path


def test_modal_canary_missing_proxy_pair_is_typed_before_network(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    profile_path = write_profile(tmp_path, "modal-hosted")
    for name in (
        "HOSTED_MODAL_PROXY_TOKEN_ID",
        "HOSTED_MODAL_PROXY_TOKEN_SECRET",
        "WOVEN_MODAL_PROXY_TOKEN_ID",
        "WOVEN_MODAL_PROXY_TOKEN_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        process.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network called")),
    )
    try:
        process.direct_modal_canary("facebook-ads-copywriter", profile_path)
    except process.HostedPathBlocker as blocker:
        assert blocker.code == "hosted_modal_auth_not_configured"
        assert "HOSTED_MODAL_PROXY_TOKEN_ID" in blocker.remediation
        assert "HOSTED_MODAL_PROXY_TOKEN_SECRET" in blocker.remediation
    else:
        raise AssertionError("missing proxy pair was not typed")


def test_modal_canary_preflight_401_is_typed_and_never_submits(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    profile_path = write_profile(tmp_path, "modal-hosted")
    monkeypatch.setenv("HOSTED_MODAL_PROXY_TOKEN_ID", "SECRET_ID_SENTINEL")
    monkeypatch.setenv("HOSTED_MODAL_PROXY_TOKEN_SECRET", "SECRET_VALUE_SENTINEL")
    calls = []

    def unauthorized(request, timeout):
        calls.append((request.full_url, request.get_method(), timeout))
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO(b"SECRET_BODY_SENTINEL"))

    monkeypatch.setattr(process.urllib.request, "urlopen", unauthorized)
    try:
        process.direct_modal_canary("facebook-ads-copywriter", profile_path)
    except process.HostedPathBlocker as blocker:
        assert blocker.code == "hosted_modal_auth_invalid"
        assert "SECRET_ID_SENTINEL" not in str(blocker)
        assert "SECRET_VALUE_SENTINEL" not in blocker.remediation
        assert "SECRET_BODY_SENTINEL" not in blocker.remediation
    else:
        raise AssertionError("invalid proxy pair was not typed")
    assert calls == [
        (
            "https://omo-space--cognition-facebook-ads-copywriter-api.modal.run/openapi.json",
            "GET",
            30,
        )
    ]


def test_modal_canary_preflight_then_submit_and_poll(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    profile_path = write_profile(tmp_path, "modal-hosted")
    profile = json.loads(profile_path.read_text())
    monkeypatch.setenv("HOSTED_MODAL_PROXY_TOKEN_ID", "id-test")
    monkeypatch.setenv("HOSTED_MODAL_PROXY_TOKEN_SECRET", "secret-test")
    calls = []
    responses = [
        (200, b""),
        (202, json.dumps({"result_url": "/v1/runs/fc-test"}).encode()),
        (200, json.dumps(profile["happy_path"]["output"]).encode()),
    ]

    class Response:
        def __init__(self, status, body):
            self.status = status
            self.body = body
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, traceback):
            return False
        def read(self, _limit=-1):
            return self.body

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, request.get_method(), dict(request.header_items())))
        status, body = responses[len(calls) - 1]
        return Response(status, body)

    monkeypatch.setattr(process.urllib.request, "urlopen", fake_urlopen)
    process.direct_modal_canary("facebook-ads-copywriter", profile_path)
    assert [call[1] for call in calls] == ["GET", "POST", "GET"]
    assert calls[0][0].endswith("/openapi.json")
    assert calls[1][0].endswith("/v1/runs")
    assert calls[2][0].endswith("/v1/runs/fc-test")
    assert all(call[2]["Modal-key"] == "id-test" for call in calls)
    assert all(call[2]["Modal-secret"] == "secret-test" for call in calls)


def test_prepare_release_registers_worker_without_modal_or_wrangler(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[list[str]] = []
    canaries: list[tuple[str, Path]] = []

    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append(list(command)))
    monkeypatch.setattr(process, "direct_modal_canary", lambda slug, profile_path, timeout_seconds=240: canaries.append((slug, profile_path)))

    profile_path = write_profile(tmp_path, "worker-native")
    process.prepare_reviewed_release(SKILL_PATH, "facebook-ads-copywriter", profile_path, "worker-native")

    flattened = [" ".join(command) for command in commands]
    assert not any("modal deploy" in command for command in flattened)
    assert not any("wrangler deploy" in command for command in flattened)
    assert canaries == []
    register_commands = [command for command in commands if "--register" in command]
    assert len(register_commands) == 2
    assert all(str(profile_path) in command for command in register_commands)
    assert all("-m modal" not in " ".join(command) for command in commands)


def test_prepare_release_for_modal_does_not_deploy_or_canary_before_merge(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[list[str]] = []
    canaries: list[tuple[str, Path]] = []

    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append(list(command)))
    monkeypatch.setattr(process, "direct_modal_canary", lambda slug, profile_path, timeout_seconds=240: canaries.append((slug, profile_path)))

    profile_path = write_profile(tmp_path, "modal-hosted")
    process.prepare_reviewed_release(SKILL_PATH, "facebook-ads-copywriter", profile_path, "modal-hosted")

    flattened = [" ".join(command) for command in commands]
    assert not any("modal deploy" in command for command in flattened)
    assert canaries == []
    register_commands = [command for command in commands if "--register" in command]
    assert len(register_commands) == 2
    assert all(str(profile_path) in command for command in register_commands)


def test_deploy_merged_release_fails_closed_without_verified_origin_main_merge(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[list[str]] = []
    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append(list(command)))
    profile_path = write_profile(tmp_path, "modal-hosted")
    release = {
        "submission_id": "sub_verifieddeploy000000000001",
        "slug": "facebook-ads-copywriter",
        "selected_runtime": "modal-hosted",
        "source_sha256": "a" * 64,
        "artifact_hash": "b" * 64,
        "head_sha": "c" * 40,
        "merge_sha": "d" * 40,
        "verified_merge_sha": "e" * 40,
        "release_phase": "merged_verified",
    }

    class Adapter:
        def verify_merged_release(self, release_metadata):
            return {**release_metadata, "release_phase": "merge_mismatch"}

    try:
        process.deploy_merged_release(SKILL_PATH, "facebook-ads-copywriter", profile_path, release, Adapter())
    except RuntimeError as error:
        assert "verified_merge_required" in str(error)
    else:
        raise AssertionError("deploy must fail closed without a verified merge")
    assert commands == []


def test_deploy_merged_release_fails_closed_when_verified_artifact_hash_differs(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[list[str]] = []
    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append(list(command)))
    profile_path = write_profile(tmp_path, "worker-native")
    release = {
        "submission_id": "sub_verifieddeploy000000000003",
        "slug": "facebook-ads-copywriter",
        "selected_runtime": "worker-native",
        "source_sha256": "a" * 64,
        "artifact_hash": "b" * 64,
        "head_sha": "c" * 40,
        "merge_sha": "d" * 40,
        "verified_merge_sha": "d" * 40,
        "release_phase": "merged_verified",
    }

    class Adapter:
        def verify_merged_release(self, release_metadata):
            return {**release_metadata, "artifact_hash": "e" * 64}

    try:
        process.deploy_merged_release(SKILL_PATH, "facebook-ads-copywriter", profile_path, release, Adapter())
    except RuntimeError as error:
        assert "verified_merge_required" in str(error)
    else:
        raise AssertionError("deploy must fail closed on artifact mismatch")
    assert commands == []


def test_deploy_merged_release_runs_deploy_only_after_verified_merge(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[list[str]] = []
    canaries: list[tuple[str, Path]] = []
    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append(list(command)))
    monkeypatch.setattr(process, "direct_modal_canary", lambda slug, profile_path, timeout_seconds=240: canaries.append((slug, profile_path)))
    monkeypatch.setattr(
        process,
        "smoke_live_worker_registry",
        lambda slugs: {"status": "passed", "slugs": {slugs[0]: {"status": 401, "error": "authentication_required"}}},
    )
    oss_publishes: list[tuple[str, Path]] = []
    monkeypatch.setattr(
        process,
        "publish_oss_release",
        lambda slug, source_root, environ=None: oss_publishes.append((slug, source_root))
        or {"status": "published", "slug": slug, "version": "0.1.0", "source_sha256": "f" * 64},
    )
    profile_path = write_profile(tmp_path, "modal-hosted")
    release = {
        "submission_id": "sub_verifieddeploy000000000002",
        "slug": "facebook-ads-copywriter",
        "selected_runtime": "modal-hosted",
        "source_sha256": "a" * 64,
        "artifact_hash": "b" * 64,
        "head_sha": "c" * 40,
        "merge_sha": "d" * 40,
        "verified_merge_sha": "d" * 40,
        "release_phase": "merged_verified",
    }

    class Adapter:
        def verify_merged_release(self, release_metadata):
            return release_metadata

    result = process.deploy_merged_release(SKILL_PATH, "facebook-ads-copywriter", profile_path, release, Adapter())

    flattened = [" ".join(command) for command in commands]
    assert result["release_phase"] == "promoted"
    assert result["release_gates"]["status"] == "live"
    assert result["release_gates"]["R1"]["slug_counts"] == {"facebook-ads-copywriter": 1}
    assert result["release_gates"]["R3"]["slugs"]["facebook-ads-copywriter"]["status"] == 401
    assert result["release_gates"]["R4"]["status"] == "published"
    assert oss_publishes == [("facebook-ads-copywriter", process.ROOT)]
    assert any("modal deploy" in command for command in flattened)
    assert "npm ci" in flattened
    assert any("wrangler@4.123.0 deploy" in command for command in flattened)
    assert flattened.index("npm ci") < next(index for index, command in enumerate(flattened) if "wrangler@4.123.0 deploy" in command)
    assert canaries == [("facebook-ads-copywriter", profile_path)]


def test_deploy_merged_release_uses_verified_checkout_when_adapter_provides_one(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[tuple[list[str], Path]] = []
    canaries: list[tuple[str, Path]] = []
    release_root = tmp_path / "verified"
    clean_profile = write_profile(release_root / "profiles", "worker-native")
    expected_profile = release_root / "packages" / "skill-to-modal" / "profiles" / "facebook-ads-copywriter.json"
    expected_profile.parent.mkdir(parents=True, exist_ok=True)
    expected_profile.write_text(clean_profile.read_text(encoding="utf-8"), encoding="utf-8")
    (release_root / "containers" / "facebook-ads-copywriter").mkdir(parents=True)
    (release_root / "containers" / "facebook-ads-copywriter" / "modal_app.py").write_text("# clean\n", encoding="utf-8")
    (release_root / "site" / "deploy").mkdir(parents=True)
    (release_root / "site" / "deploy" / "hosted-skills.generated.mjs").write_text(
        'export const HOSTED_WORKER_SKILL_ROWS = [\n  [\n    "facebook-ads-copywriter",\n    {}\n  ]\n];\n'
        'export const HOSTED_SERVER_CATALOG_ROWS = [];\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append((list(command), cwd)))
    monkeypatch.setattr(process, "direct_modal_canary", lambda slug, profile_path, timeout_seconds=240: canaries.append((slug, profile_path)))
    monkeypatch.setattr(
        process,
        "smoke_live_worker_registry",
        lambda slugs: {"status": "passed", "slugs": {slugs[0]: {"status": 401, "error": "authentication_required"}}},
    )
    oss_publishes: list[tuple[str, Path]] = []
    monkeypatch.setattr(
        process,
        "publish_oss_release",
        lambda slug, source_root, environ=None: oss_publishes.append((slug, source_root))
        or {"status": "published", "slug": slug, "version": "0.1.0", "source_sha256": "f" * 64},
    )
    dirty_profile = write_profile(tmp_path, "worker-native")
    release = {
        "selected_runtime": "worker-native",
        "source_sha256": "a" * 64,
        "artifact_hash": "b" * 64,
        "head_sha": "c" * 40,
        "merge_sha": "d" * 40,
        "verified_merge_sha": "d" * 40,
        "release_phase": "merged_verified",
    }

    class Adapter:
        def verify_merged_release(self, release_metadata):
            return release_metadata
        def checkout_verified_release(self, release_metadata):
            return release_root

    result = process.deploy_merged_release(SKILL_PATH, "facebook-ads-copywriter", dirty_profile, release, Adapter())

    assert result["release_phase"] == "promoted"
    assert result["release_gates"]["R4"]["status"] == "published"
    assert oss_publishes == [("facebook-ads-copywriter", release_root)]
    assert commands == [
        (["npm", "ci"], release_root / "site" / "deploy"),
        (["npx", "wrangler@4.123.0", "deploy"], release_root / "site" / "deploy"),
    ]
    assert canaries == []


def test_prepare_release_registry_gate_requires_exactly_one_hosted_runtime_row(tmp_path: Path) -> None:
    process = load_process_submissions()
    worker_root = tmp_path / "deploy"
    worker_root.mkdir()
    registry = worker_root / process.WORKER_REGISTRY_FILENAME
    registry.write_text(
        'export const HOSTED_WORKER_SKILL_ROWS = [\n'
        '  [\n    "released-one",\n    {}\n  ],\n'
        '  [\n    "released-one",\n    {}\n  ]\n'
        '];\nexport const HOSTED_MODAL_SKILL_ROWS = [];\n'
        'export const HOSTED_SERVER_CATALOG_ROWS = [];\n',
        encoding="utf-8",
    )

    try:
        process.verify_generated_worker_registry(["released-one", "released-two"], worker_root)
    except process.WorkerReleaseBlocker as blocker:
        assert blocker.code == "hosted_worker_registry_missing_slug"
        assert blocker.gate == "R1"
        assert set(blocker.slugs) == {"released-one", "released-two"}
    else:
        raise AssertionError("R1 must reject missing or duplicate hosted runtime rows")


def test_prepare_release_worker_deploy_error_fails_closed_before_live_smoke(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[list[str]] = []
    profile_path = write_profile(tmp_path, "worker-native")
    release = {
        "selected_runtime": "worker-native",
        "source_sha256": "a" * 64,
        "artifact_hash": "b" * 64,
        "head_sha": "c" * 40,
        "merge_sha": "d" * 40,
        "verified_merge_sha": "d" * 40,
        "release_phase": "merged_verified",
    }

    class Adapter:
        def verify_merged_release(self, release_metadata):
            return release_metadata

    def fake_run_checked(command, cwd=process.ROOT):
        commands.append(list(command))
        if list(command) == list(process.WORKER_DEPLOY_COMMAND):
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(process, "run_checked", fake_run_checked)
    monkeypatch.setattr(
        process,
        "smoke_live_worker_registry",
        lambda _slugs: (_ for _ in ()).throw(AssertionError("R3 ran after failed R2")),
    )

    try:
        process.deploy_merged_release(SKILL_PATH, "facebook-ads-copywriter", profile_path, release, Adapter())
    except process.WorkerReleaseBlocker as blocker:
        assert blocker.code == "hosted_worker_deploy_failed"
        assert blocker.gate == "R2"
    else:
        raise AssertionError("Wrangler failure must return a typed, fail-closed R2 blocker")
    assert commands[-1] == ["npx", "wrangler@4.123.0", "deploy"]


def test_prepare_release_live_smoke_unknown_slug_is_typed_blocker(monkeypatch) -> None:
    process = load_process_submissions()

    def unresolved(request, timeout):
        assert json.loads(request.data) == {"fields": {}, "slug": "new-tool"}
        assert timeout == process.HTTP_TIMEOUT_SECONDS
        raise HTTPError(
            request.full_url,
            404,
            "Not Found",
            {},
            io.BytesIO(b'{"error":"unknown_catalog_slug"}'),
        )

    monkeypatch.setattr(process.urllib.request, "urlopen", unresolved)
    try:
        process.smoke_live_worker_registry(["new-tool"])
    except process.WorkerReleaseBlocker as blocker:
        assert blocker.code == "hosted_worker_registry_unresolved"
        assert blocker.gate == "R3"
        assert blocker.slugs == ("new-tool",)
    else:
        raise AssertionError("unknown_catalog_slug must block the release")


def test_prepare_release_live_smoke_accepts_auth_4xx_as_resolution_evidence(monkeypatch) -> None:
    process = load_process_submissions()

    def auth_required(request, timeout):
        raise HTTPError(
            request.full_url,
            401,
            "Unauthorized",
            {},
            io.BytesIO(b'{"error":"authentication_required"}'),
        )

    monkeypatch.setattr(process.urllib.request, "urlopen", auth_required)
    evidence = process.smoke_live_worker_registry(["new-tool"])

    assert evidence["status"] == "passed"
    assert evidence["slugs"] == {
        "new-tool": {"status": 401, "error": "authentication_required"}
    }


class FakeRepository:
    def __init__(self) -> None:
        self.statuses: list[tuple[str, str, str | None]] = []
        self.runtime_decisions: list[tuple[str, dict]] = []
        self.deployments: list[tuple[str, str, str, dict]] = []

    def set_status(self, submission_id: str, status: str, failure_code: str | None = None) -> None:
        self.statuses.append((submission_id, status, failure_code))

    def set_runtime_decision(self, submission_id: str, decision: dict) -> None:
        self.runtime_decisions.append((submission_id, decision))

    def set_deployment_metadata(
        self, submission_id: str, status: str, published_slug: str, workflow_version: str, build_evidence: dict
    ) -> None:
        self.deployments.append((submission_id, status, published_slug, workflow_version, build_evidence))

    def set_release_metadata(self, submission_id: str, release_metadata: dict) -> None:
        self.release_metadata = (submission_id, release_metadata)


def _unknown_review_row(process, source: str) -> dict:
    validated = process.validate_submission("Sample Creator Workflow", source)
    return {
        "id": "sub_reviewartifact000000000001",
        "name": "Sample Creator Workflow",
        "content": source,
        "source_sha256": validated.source_sha256,
        "slug": validated.slug,
        "requested_runtime": "auto",
        "prior_status": "queued",
    }


def test_process_row_persists_exact_private_review_source(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    source = (ROOT / "tools" / "host-skill" / "tests" / "fixtures" / "sample-workflow.md").read_text(encoding="utf-8")
    review_root = tmp_path / "review"
    review_root.mkdir(mode=0o700)
    monkeypatch.setenv("OMO_BUILD_REVIEW_ROOT", str(review_root))
    repo = FakeRepository()

    result = process.process_row(_unknown_review_row(process, source), repo, deploy=False)

    review_path = Path(result["review_path"])
    assert result == {
        "id": "sub_reviewartifact000000000001",
        "slug": "sample-creator-workflow",
        "source_sha256": process.sha256_bytes(source.encode("utf-8")),
        "status": "needs_review",
        "failure_code": "reviewed_profile_required",
        "review_path": str(review_path),
    }
    assert review_path.is_absolute()
    assert review_path.read_bytes() == source.encode("utf-8")
    assert stat.S_IMODE(review_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(review_path.stat().st_mode) == 0o600


def test_process_row_review_persistence_fails_closed_for_unsafe_root(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    source = (ROOT / "tools" / "host-skill" / "tests" / "fixtures" / "sample-workflow.md").read_text(encoding="utf-8")
    relative = "relative-review"
    monkeypatch.setenv("OMO_BUILD_REVIEW_ROOT", relative)

    try:
        process.process_row(_unknown_review_row(process, source), FakeRepository(), deploy=False)
    except RuntimeError as error:
        assert str(error) == "unsafe_review_root"
    else:
        raise AssertionError("relative review roots must fail closed")
    assert not (tmp_path / relative).exists()


def test_process_row_never_persists_for_other_review_gates_or_hash_errors(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    source = (ROOT / "tools" / "host-skill" / "tests" / "fixtures" / "sample-workflow.md").read_text(encoding="utf-8")
    review_root = tmp_path / "review"
    review_root.mkdir(mode=0o700)
    monkeypatch.setenv("OMO_BUILD_REVIEW_ROOT", str(review_root))

    collision_row = _unknown_review_row(process, source)
    monkeypatch.setattr(process, "evaluate_review_gate", lambda validated, allow_matching_container=False: ("needs_review", "slug_collision"))
    collision = process.process_row(collision_row, FakeRepository(), deploy=False)
    assert collision["failure_code"] == "slug_collision"
    assert list(review_root.iterdir()) == []

    bad_hash = _unknown_review_row(process, source)
    bad_hash["source_sha256"] = "0" * 64
    mismatch = process.process_row(bad_hash, FakeRepository(), deploy=False)
    assert mismatch["failure_code"] == "source_identity_mismatch"
    assert list(review_root.iterdir()) == []


def test_process_row_keeps_existing_review_result_when_review_root_unset(monkeypatch) -> None:
    process = load_process_submissions()
    source = (ROOT / "tools" / "host-skill" / "tests" / "fixtures" / "sample-workflow.md").read_text(encoding="utf-8")
    monkeypatch.delenv("OMO_BUILD_REVIEW_ROOT", raising=False)

    result = process.process_row(_unknown_review_row(process, source), FakeRepository(), deploy=False)

    assert result == {
        "id": "sub_reviewartifact000000000001",
        "slug": "sample-creator-workflow",
        "status": "needs_review",
        "failure_code": "reviewed_profile_required",
    }


def test_process_row_fails_closed_when_generated_source_hash_differs(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    source = SKILL_PATH.read_text(encoding="utf-8")
    validated = process.validate_submission("Facebook Ads Copywriter", source)
    repo = FakeRepository()
    monkeypatch.setattr(process, "evaluate_review_gate", lambda validated, allow_matching_container=False: ("ready_for_build", None))
    monkeypatch.setattr(process, "reviewed_profile_artifact", lambda slug, requested_runtime, temp_dir, source_sha256=None: (write_profile(tmp_path, "worker-native"), {"effective": "worker-native"}))
    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: None)
    monkeypatch.setattr(process, "generated_runtime_metadata", lambda slug, profile_path, expected_source_sha256: (_ for _ in ()).throw(RuntimeError("generated_source_hash_mismatch")))

    result = process.process_row({
        "id": "sub_sourcehashmismatch",
        "name": "Facebook Ads Copywriter",
        "content": source,
        "source_sha256": validated.source_sha256,
        "slug": validated.slug,
        "requested_runtime": "worker-native",
    }, repo, deploy=False)

    assert result == {
        "id": "sub_sourcehashmismatch",
        "slug": "facebook-ads-copywriter",
        "status": "failed",
        "failure_code": "generated_source_hash_mismatch",
    }
    assert repo.statuses[-1] == ("sub_sourcehashmismatch", "failed", "generated_source_hash_mismatch")


def test_process_row_preserves_secret_free_stage_for_compile_failure(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    source = SKILL_PATH.read_text(encoding="utf-8")
    validated = process.validate_submission("Facebook Ads Copywriter", source)
    repo = FakeRepository()
    monkeypatch.setattr(process, "evaluate_review_gate", lambda validated, allow_matching_container=False: ("ready_for_build", None))
    monkeypatch.setattr(
        process,
        "reviewed_profile_artifact",
        lambda slug, requested_runtime, temp_dir, source_sha256=None: (
            write_profile(tmp_path, "worker-native"),
            {"effective": "worker-native"},
        ),
    )

    def fail_compile(command, cwd=process.ROOT):
        raise subprocess.CalledProcessError(17, command)

    monkeypatch.setattr(process, "run_checked", fail_compile)

    result = process.process_row({
        "id": "sub_compilefailure000000000001",
        "name": "Facebook Ads Copywriter",
        "content": source,
        "source_sha256": validated.source_sha256,
        "slug": validated.slug,
        "requested_runtime": "worker-native",
    }, repo, deploy=False)

    assert result == {
        "id": "sub_compilefailure000000000001",
        "slug": "facebook-ads-copywriter",
        "status": "failed",
        "failure_code": "build_or_deploy_failed",
        "failure_stage": "trusted_compile",
    }
    assert repo.statuses[-1] == (
        "sub_compilefailure000000000001",
        "failed",
        "build_or_deploy_failed",
    )
    assert "17" not in result
    assert "SKILL.md" not in result


def test_github_release_adapter_preserves_safe_stage_for_command_failure() -> None:
    process = load_process_submissions()

    def fail(command, cwd=None, text=True):
        raise subprocess.CalledProcessError(23, command, stderr="token=should-not-escape")

    adapter = process.GitHubReleaseAdapter(command_runner=fail)

    with pytest.raises(process.StagedCalledProcessError) as caught:
        adapter._issue_for_submission("sub_stagefailure000000000001", "facebook-ads-copywriter")

    assert caught.value.stage == "release_issue_lookup"
    assert caught.value.output is None
    assert caught.value.stderr is None
    assert caught.value.__cause__ is None
    assert "should-not-escape" not in str(caught.value)


def test_github_release_adapter_uses_generic_stage_for_unknown_command() -> None:
    process = load_process_submissions()

    def fail(command, cwd=None, text=True):
        raise subprocess.CalledProcessError(23, command)

    adapter = process.GitHubReleaseAdapter(command_runner=fail)

    with pytest.raises(process.StagedCalledProcessError) as caught:
        adapter._run(["git", "commit", "-m", "release"])

    assert caught.value.stage == "release_command"


def test_process_row_with_deploy_prepares_git_release_without_production_side_effects(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    source = SKILL_PATH.read_text(encoding="utf-8")
    validated = process.validate_submission("Facebook Ads Copywriter", source)
    repo = FakeRepository()
    commands: list[list[str]] = []
    monkeypatch.setattr(process, "evaluate_review_gate", lambda validated, allow_matching_container=False: ("ready_for_build", None))
    monkeypatch.setattr(process, "reviewed_profile_artifact", lambda slug, requested_runtime, temp_dir, source_sha256=None: (write_profile(tmp_path, "worker-native"), {"effective": "worker-native"}))
    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append(list(command)))
    monkeypatch.setattr(process, "generated_runtime_metadata", lambda slug, profile_path, expected_source_sha256: {
        "decision": {"effective": "worker-native", "requested": "worker-native", "recommended": "worker-native", "compatible": True, "reason": "creator_selected_worker"},
        "published_slug": "facebook-ads-copywriter",
        "workflow_version": "facebook-ads-copywriter@1.0.0",
        "build_evidence": {"checks": ["compile"], "source_sha256": expected_source_sha256},
    })

    class Adapter:
        def prepare_release(self, release_request):
            assert release_request["submission_id"] == "sub_gitrelease00000000000001"
            assert release_request["branch"] == "omo-release/sub_gitrelease00000000000001-facebook-ads-copywriter"
            assert release_request["slug"] == "facebook-ads-copywriter"
            assert release_request["source_sha256"] == validated.source_sha256
            assert "client_branch" not in release_request
            return {
                "release_phase": "pr_open",
                "issue_url": "https://github.com/owner/repo/issues/31",
                "pr_url": "https://github.com/owner/repo/pull/42",
                "pr_number": 42,
                "branch": release_request["branch"],
                "head_sha": "a" * 40,
                "source_sha256": release_request["source_sha256"],
                "artifact_hash": release_request["artifact_hash"],
            }

    result = process.process_row({
        "id": "sub_gitrelease00000000000001",
        "name": "Facebook Ads Copywriter",
        "content": source,
        "source_sha256": validated.source_sha256,
        "slug": validated.slug,
        "requested_runtime": "worker-native",
    }, repo, deploy=True, release_adapter=Adapter())

    flattened = [" ".join(command) for command in commands]
    assert result["status"] == "ready_for_merge"
    assert repo.release_metadata[0] == "sub_gitrelease00000000000001"
    assert repo.release_metadata[1]["release_phase"] == "pr_open"
    assert not any("modal deploy" in command or "wrangler deploy" in command for command in flattened)


def test_github_release_adapter_uses_fixed_repo_branch_and_allowlisted_adds(tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[tuple[tuple[str, ...], Path | None]] = []

    def runner(command: list[str], cwd: Path | None = None, text: bool = True) -> str | bytes:
        commands.append((tuple(command), cwd))
        if command[:4] == ["gh", "issue", "list", "--repo"]:
            return "[]"
        if command[:4] == ["gh", "issue", "create", "--repo"]:
            return "https://github.com/harrythentrepreneur/Omo.Space/issues/31\n"
        if command[:4] == ["gh", "pr", "list", "--repo"]:
            return "[]"
        if command[:4] == ["gh", "pr", "create", "--repo"]:
            return "https://github.com/harrythentrepreneur/Omo.Space/pull/42\n"
        if command[:4] == ["gh", "pr", "view", "--repo"]:
            return json.dumps({"number": 42, "url": "https://github.com/harrythentrepreneur/Omo.Space/pull/42", "headRefOid": "a" * 40})
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return "a" * 40 + "\n"
        return ""

    adapter = process.GitHubReleaseAdapter(command_runner=runner, scratch_root=tmp_path)
    request = {
        "submission_id": "sub_adapter000000000000000001",
        "slug": "facebook-ads-copywriter",
        "published_slug": "facebook-ads-copywriter",
        "workflow_version": "facebook-ads-copywriter@1.0.0",
        "selected_runtime": "worker-native",
        "source_sha256": "b" * 64,
        "artifact_hash": "c" * 64,
        "branch": "evil/client-branch",
    }

    result = adapter.prepare_release(request)

    assert result["release_phase"] == "pr_open"
    assert result["branch"] == "omo-release/sub_adapter000000000000000001-facebook-ads-copywriter"
    assert result["issue_url"] == "https://github.com/harrythentrepreneur/Omo.Space/issues/31"
    assert result["pr_url"] == "https://github.com/harrythentrepreneur/Omo.Space/pull/42"
    flattened = [" ".join(command) for command, _cwd in commands]
    assert all("harrythentrepreneur/Omo.Space" in command or command.startswith("git ") for command in flattened)
    assert any(command.startswith("git worktree add --detach") and command.endswith("origin/main") for command in flattened)
    assert any(command == "git switch -C omo-release/sub_adapter000000000000000001-facebook-ads-copywriter" for command in flattened)
    assert any(command == "git push -u origin omo-release/sub_adapter000000000000000001-facebook-ads-copywriter" for command in flattened)
    add_commands = [command for command in flattened if command.startswith("git add ")]
    assert add_commands
    assert not any(command == "git add ." for command in add_commands)
    assert not any("/tmp/" in command and "SKILL.md" in command for command in flattened)


def test_release_allowlist_includes_reviewed_marketplace_slug_manifest(tmp_path: Path) -> None:
    process = load_process_submissions()
    slug = "education-workflow"
    container = tmp_path / "containers" / slug
    container.mkdir(parents=True)
    (container / "hosted-profile.json").write_text(
        json.dumps({"runtime": {"slug": "education-workflow-pro"}}),
        encoding="utf-8",
    )
    run_manifests = tmp_path / "site" / "run-manifests"
    run_manifests.mkdir(parents=True)
    aliased = run_manifests / "education-workflow-pro.json"
    aliased.write_text("{}", encoding="utf-8")

    assert "site/run-manifests/education-workflow-pro.json" in process.release_allowlisted_paths(
        slug, root=tmp_path
    )


def test_github_release_adapter_reuses_existing_issue_and_pr(tmp_path: Path) -> None:
    process = load_process_submissions()
    create_commands: list[list[str]] = []

    def runner(command: list[str], cwd: Path | None = None, text: bool = True) -> str | bytes:
        if command[:4] in (["gh", "issue", "create", "--repo"], ["gh", "pr", "create", "--repo"]):
            create_commands.append(command)
        if command[:4] == ["gh", "issue", "list", "--repo"]:
            return json.dumps([{"number": 31, "url": "https://github.com/harrythentrepreneur/Omo.Space/issues/31"}])
        if command[:4] == ["gh", "pr", "list", "--repo"]:
            return json.dumps([{"number": 42, "url": "https://github.com/harrythentrepreneur/Omo.Space/pull/42", "headRefOid": "a" * 40}])
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return "a" * 40 + "\n"
        return ""

    adapter = process.GitHubReleaseAdapter(command_runner=runner, scratch_root=tmp_path)
    result = adapter.prepare_release({
        "submission_id": "sub_reuse0000000000000000001",
        "slug": "facebook-ads-copywriter",
        "published_slug": "facebook-ads-copywriter",
        "workflow_version": "facebook-ads-copywriter@1.0.0",
        "selected_runtime": "worker-native",
        "source_sha256": "b" * 64,
        "artifact_hash": "c" * 64,
    })

    assert create_commands == []
    assert result["issue_url"].endswith("/issues/31")
    assert result["pr_number"] == 42


def test_verify_merged_release_reads_hashes_from_merge_tree_not_current_tree() -> None:
    process = load_process_submissions()
    calls: list[list[str]] = []

    def runner(command: list[str], cwd: Path | None = None, text: bool = True) -> str | bytes:
        calls.append(command)
        if command[:4] == ["gh", "pr", "view", "--repo"]:
            return json.dumps({
                "state": "MERGED",
                "baseRefName": "main",
                "headRefOid": "a" * 40,
                "mergeCommit": {"oid": "d" * 40},
                "statusCheckRollup": [{"name": "contracts", "conclusion": "SUCCESS"}],
            })
        if command[:2] == ["git", "ls-tree"]:
            return "containers/facebook-ads-copywriter/manifest.json\0"
        if command[:2] == ["git", "show"]:
            spec = command[2]
            if spec.endswith(":containers/facebook-ads-copywriter/source/SKILL.md"):
                return b"reviewed source"
            if spec.endswith(":containers/facebook-ads-copywriter/manifest.json"):
                return b'{"slug":"facebook-ads-copywriter"}'
        return ""

    expected_source = process.sha256_bytes(b"reviewed source")
    expected_artifact = process.hash_release_artifact_entries({
        "containers/facebook-ads-copywriter/manifest.json": b'{"slug":"facebook-ads-copywriter"}',
    })
    adapter = process.GitHubReleaseAdapter(command_runner=runner)
    release = {
        "release_phase": "pr_open",
        "branch": "omo-release/sub_verifytree000000000001-facebook-ads-copywriter",
        "pr_number": 42,
        "head_sha": "a" * 40,
        "source_sha256": expected_source,
        "artifact_hash": expected_artifact,
    }

    verified = adapter.verify_merged_release(release)

    assert verified["release_phase"] == "merged_verified"
    assert verified["verified_merge_sha"] == "d" * 40
    assert ["git", "fetch", "origin", "main"] in calls
    assert ["git", "merge-base", "--is-ancestor", "d" * 40, "origin/main"] in calls


def test_verify_merged_release_fails_when_required_check_is_not_success() -> None:
    process = load_process_submissions()

    def runner(command: list[str], cwd: Path | None = None, text: bool = True) -> str | bytes:
        if command[:4] == ["gh", "pr", "view", "--repo"]:
            return json.dumps({
                "state": "OPEN",
                "baseRefName": "main",
                "headRefOid": "a" * 40,
                "mergeCommit": None,
                "statusCheckRollup": [{"name": "contracts", "conclusion": "FAILURE"}],
            })
        return ""

    adapter = process.GitHubReleaseAdapter(command_runner=runner)
    try:
        adapter.merge_after_required_checks({
            "release_phase": "pr_open",
            "branch": "omo-release/sub_checkfail00000000001-facebook-ads-copywriter",
            "pr_number": 42,
            "head_sha": "a" * 40,
            "source_sha256": "b" * 64,
            "artifact_hash": "c" * 64,
        })
    except RuntimeError as error:
        assert "required_checks_not_successful" in str(error)
    else:
        raise AssertionError("merge must fail closed when required checks fail")


def test_reviewed_profile_auto_inherits_exact_match_runtime_from_hosted_metadata(tmp_path: Path) -> None:
    process = load_process_submissions()
    woven_source_sha = "6297f14dfc8d4815efc041316e5c19df7faf4cb31dae3f73a0badc09101b90bf"

    profile_path, decision = process.reviewed_profile_artifact(
        "woven-storybook-pipeline",
        "auto",
        tmp_path,
        source_sha256=woven_source_sha,
    )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    assert profile["runtime_preference"] == "modal-hosted"
    assert decision["requested"] == "modal-hosted"
    assert decision["effective"] == "modal-hosted"
    assert decision["recommended"] == "modal-hosted"
    assert decision["reason"] == "worker_executor_contract_not_satisfied"


def test_runtime_preference_helper_is_data_only_and_changes_only_auto() -> None:
    process = load_process_submissions()
    source_sha = "1" * 64
    runtime_by_source = {source_sha: "modal-hosted"}

    assert process.runtime_preference_for_reviewed_source("auto", source_sha, runtime_by_source) == "modal-hosted"
    assert process.runtime_preference_for_reviewed_source("worker-native", source_sha, runtime_by_source) == "worker-native"
    assert process.runtime_preference_for_reviewed_source("modal-hosted", source_sha, runtime_by_source) == "modal-hosted"
    assert process.runtime_preference_for_reviewed_source("auto", "2" * 64, runtime_by_source) == "auto"
    assert process.runtime_preference_for_reviewed_source(None, source_sha, runtime_by_source) is None


def test_reviewed_profile_rejects_worker_override_for_modal_only_capabilities(tmp_path: Path) -> None:
    process = load_process_submissions()
    woven_source_sha = "6297f14dfc8d4815efc041316e5c19df7faf4cb31dae3f73a0badc09101b90bf"

    with pytest.raises(ValueError, match="workflow requires Modal"):
        process.reviewed_profile_artifact(
            "woven-storybook-pipeline",
            "worker-native",
            tmp_path,
            source_sha256=woven_source_sha,
        )


def test_process_row_retries_exact_match_with_inherited_modal_runtime(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    source = (process.ROOT / "containers" / "woven-storybook-pipeline" / "source" / "SKILL.md").read_text(encoding="utf-8")
    validated = process.validate_submission("Woven Storybook Pipeline", source)
    repo = FakeRepository()
    profile_decisions: list[dict] = []

    monkeypatch.setattr(process, "evaluate_review_gate", lambda validated, allow_matching_container=False: ("ready_for_build", None))
    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: None)
    monkeypatch.setattr(process, "generated_runtime_metadata", lambda slug, profile_path, expected_source_sha256: {
        "decision": {"effective": "modal-hosted", "requested": "modal-hosted", "recommended": "worker-native", "compatible": True, "reason": "creator_selected_modal"},
        "published_slug": "woven-relationship-book-maker",
        "workflow_version": "woven-storybook-pipeline@0.2.0",
        "build_evidence": {"checks": ["compile"], "source_sha256": expected_source_sha256},
    })

    original_reviewed_profile_artifact = process.reviewed_profile_artifact
    def recording_reviewed_profile_artifact(slug, requested_runtime, temp_dir, source_sha256=None):
        profile_path, decision = original_reviewed_profile_artifact(slug, requested_runtime, temp_dir, source_sha256=source_sha256)
        profile_decisions.append(decision)
        return profile_path, decision
    monkeypatch.setattr(process, "reviewed_profile_artifact", recording_reviewed_profile_artifact)

    result = process.process_row({
        "id": "sub_08b017bc6b22fca3112dead68f19f4a2",
        "name": "Woven Storybook Pipeline",
        "content": source,
        "source_sha256": validated.source_sha256,
        "slug": validated.slug,
        "requested_runtime": "auto",
        "prior_status": "ready_for_deploy",
    }, repo, deploy=False)

    assert result["status"] == "ready_for_deploy"
    assert profile_decisions[0]["effective"] == "modal-hosted"
    assert repo.runtime_decisions[-1][1]["effective"] == "modal-hosted"
    assert repo.deployments[-1][2] == "woven-relationship-book-maker"


def test_process_row_allows_matching_container_for_review_and_ready_resumes(monkeypatch) -> None:
    process = load_process_submissions()
    source = (ROOT / "tools" / "host-skill" / "tests" / "fixtures" / "sample-workflow.md").read_text(encoding="utf-8")
    validated = process.validate_submission("sample-creator-workflow", source)
    seen: list[bool] = []

    def gate(_validated, allow_matching_container=False):
        seen.append(allow_matching_container)
        return "needs_review", "slug_collision"

    monkeypatch.setattr(process, "evaluate_review_gate", gate)
    for prior_status in ("needs_review", "ready_for_deploy"):
        process.process_row({
            "id": f"sub_resume{prior_status.replace('_', '')}00000001",
            "name": validated.name,
            "content": source,
            "source_sha256": validated.source_sha256,
            "slug": validated.slug,
            "requested_runtime": "auto",
            "prior_status": prior_status,
        }, FakeRepository(), deploy=False)

    assert seen == [True, True]


def test_deployed_gate_requires_publish_slug_version_and_evidence() -> None:
    process = load_process_submissions()

    class Cursor:
        rowcount = 0
        def execute(self, query, params):
            assert "published_slug IS NOT NULL" in query
            assert "workflow_version IS NOT NULL" in query
            assert "build_evidence IS NOT NULL" in query
            self.rowcount = 0

    class Connection:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def cursor(self): return CursorContext()

    class CursorContext:
        def __enter__(self): return Cursor()
        def __exit__(self, exc_type, exc, tb): return False

    repo = object.__new__(process.SubmissionRepository)
    repo.connection = Connection()

    try:
        repo.mark_deployed("sub_readywithoutmetadata")
    except RuntimeError as error:
        assert "ready_for_publish" in str(error)
    else:
        raise AssertionError("mark_deployed should fail without deployment metadata")


def test_repository_factory_prefers_private_worker_bridge(monkeypatch) -> None:
    process = load_process_submissions()
    monkeypatch.setenv("BUILD_WORKER_BASE_URL", "https://omo.space")
    monkeypatch.setenv("BUILD_WORKER_TOKEN", "token-value")
    monkeypatch.delenv("NEON_DATABASE_URL", raising=False)

    repo = process.repository_from_env(os.environ)

    assert isinstance(repo, process.HttpSubmissionRepository)
    assert "token-value" not in repr(repo)


def test_repository_factory_keeps_neon_fallback(monkeypatch) -> None:
    process = load_process_submissions()
    monkeypatch.delenv("BUILD_WORKER_BASE_URL", raising=False)
    monkeypatch.delenv("BUILD_WORKER_TOKEN", raising=False)
    monkeypatch.setenv("NEON_DATABASE_URL", "postgres://example")

    captured: dict[str, str] = {}
    class FakeNeon(process.SubmissionRepository):
        def __init__(self, database_url: str):
            captured["database_url"] = database_url

    monkeypatch.setattr(process, "SubmissionRepository", FakeNeon)
    repo = process.repository_from_env(os.environ)

    assert isinstance(repo, FakeNeon)
    assert captured == {"database_url": "postgres://example"}


def test_http_repository_rejects_unapproved_non_https_origin() -> None:
    process = load_process_submissions()
    try:
        process.HttpSubmissionRepository("http://omo.space", "token")
    except ValueError as error:
        assert "HTTPS" in str(error)
    else:
        raise AssertionError("HTTP base URL should be rejected")

    try:
        process.HttpSubmissionRepository("https://evil.example", "token")
    except ValueError as error:
        assert "not allowlisted" in str(error)
    else:
        raise AssertionError("unapproved origin should be rejected")


def test_http_repository_claim_posts_bearer_and_validates_schema(monkeypatch) -> None:
    process = load_process_submissions()
    calls: list[dict] = []

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self):
            return json.dumps({
                "ok": True,
                "submission": {
                    "id": "sub_12345678",
                    "name": "sample-workflow",
                    "slug": "sample-workflow",
                    "content": "---\nname: sample-workflow\ndescription: x\n---\n",
                    "source_sha256": "a" * 64,
                    "requested_runtime": "auto",
                    "prior_status": "queued",
                },
            }).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append({
            "url": request.full_url,
            "method": request.get_method(),
            "headers": dict(request.header_items()),
            "body": request.data.decode("utf-8"),
            "timeout": timeout,
        })
        return Response()

    monkeypatch.setattr(process.urllib.request, "urlopen", fake_urlopen)
    repo = process.HttpSubmissionRepository("https://omo.space", "secret-token")

    row = repo.claim("sub_12345678")

    assert row["id"] == "sub_12345678"
    assert calls[0]["url"] == "https://omo.space/api/internal/submissions/claim"
    assert calls[0]["method"] == "POST"
    assert calls[0]["headers"]["Authorization"] == "Bearer secret-token"
    assert calls[0]["headers"]["User-agent"] == "OmoBuildWorker/1.0"
    assert calls[0]["headers"]["Accept"] == "application/json"
    assert json.loads(calls[0]["body"]) == {"id": "sub_12345678"}
    assert calls[0]["timeout"] == process.HTTP_TIMEOUT_SECONDS


def test_http_repository_response_schema_rejects_markdown_and_bad_ids(monkeypatch) -> None:
    process = load_process_submissions()

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self):
            return json.dumps({
                "ok": True,
                "submission": {
                    "id": "bad",
                    "name": "sample-workflow",
                    "slug": "sample-workflow",
                    "content": "secret markdown",
                    "source_sha256": "a" * 64,
                    "requested_runtime": "auto",
                    "prior_status": "queued",
                },
            }).encode("utf-8")

    monkeypatch.setattr(process.urllib.request, "urlopen", lambda request, timeout: Response())
    repo = process.HttpSubmissionRepository("https://omo.space", "secret-token")

    try:
        repo.claim()
    except RuntimeError as error:
        assert "invalid internal claim response" in str(error)
        assert "secret markdown" not in str(error)
    else:
        raise AssertionError("bad claim schema should fail closed")


def test_http_repository_maps_204_claim_to_idle(monkeypatch) -> None:
    process = load_process_submissions()

    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 204, "No Content", {}, None)

    monkeypatch.setattr(process.urllib.request, "urlopen", fake_urlopen)
    repo = process.HttpSubmissionRepository("https://omo.space", "secret-token")

    assert repo.claim() is None


def test_http_repository_get_posts_bearer_and_normalizes_safe_detail(monkeypatch) -> None:
    process = load_process_submissions()
    calls: list[dict] = []

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self):
            return json.dumps({
                "ok": True,
                "submission": {
                    "id": "sub_12345678",
                    "slug": "sample-workflow",
                    "status": "ready_for_publish",
                    "source_sha256": "a" * 64,
                    "selected_runtime": "worker-native",
                    "workflow_version": "sample-workflow@1.0.0",
                    "published_slug": "sample-workflow",
                    "build_evidence": {"checks": ["compile"], "secret": "must-not-leak"},
                    "release_phase": "merged_verified",
                    "release_issue_url": "https://github.com/omo-space/marketplace/issues/37",
                    "release_pr_url": "https://github.com/omo-space/marketplace/pull/38",
                    "release_pr_number": 38,
                    "release_branch": "omo-release/sub_12345678-sample-workflow",
                    "release_head_sha": "b" * 40,
                    "release_merge_sha": "c" * 40,
                    "release_artifact_hash": "d" * 64,
                    "modal_app": "sample-workflow",
                    "modal_url": "https://omo-space--sample-workflow-api.modal.run",
                    "canary_evidence": {"status": "passed", "checked_at": "2026-08-14T00:00:00Z"},
                },
            }).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append({
            "url": request.full_url,
            "method": request.get_method(),
            "headers": dict(request.header_items()),
            "body": request.data.decode("utf-8"),
            "timeout": timeout,
        })
        return Response()

    monkeypatch.setattr(process.urllib.request, "urlopen", fake_urlopen)
    repo = process.HttpSubmissionRepository("https://omo.space", "secret-token")

    row = repo.get("sub_12345678")

    assert row["id"] == "sub_12345678"
    assert row["slug"] == "sample-workflow"
    assert row["selected_runtime"] == "worker-native"
    assert row["release_phase"] == "merged_verified"
    assert row["canary_evidence"] == {"status": "passed", "checked_at": "2026-08-14T00:00:00Z"}
    assert row["build_evidence"] == {"checks": ["compile"]}
    assert "content" not in row
    assert "user_id" not in row
    assert "must-not-leak" not in json.dumps(row)
    assert calls[0]["url"] == "https://omo.space/api/internal/submissions/sub_12345678/detail"
    assert calls[0]["method"] == "POST"
    assert calls[0]["headers"]["Authorization"] == "Bearer secret-token"
    assert json.loads(calls[0]["body"]) == {}
    assert calls[0]["timeout"] == process.HTTP_TIMEOUT_SECONDS


def test_http_repository_get_maps_404_to_none_and_rejects_leaky_detail(monkeypatch) -> None:
    process = load_process_submissions()

    def not_found(request, timeout):
        raise HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(process.urllib.request, "urlopen", not_found)
    repo = process.HttpSubmissionRepository("https://omo.space", "secret-token")
    assert repo.get("sub_12345678") is None

    class LeakyResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self):
            return json.dumps({
                "ok": True,
                "submission": {
                    "id": "sub_12345678",
                    "slug": "bad",
                    "source_sha256": "a" * 64,
                    "selected_runtime": "worker-native",
                    "release_phase": "compiled",
                    "content": "secret markdown",
                },
            }).encode("utf-8")

    monkeypatch.setattr(process.urllib.request, "urlopen", lambda request, timeout: LeakyResponse())
    try:
        repo.get("sub_12345678")
    except RuntimeError as error:
        assert "invalid internal detail response" in str(error)
        assert "secret markdown" not in str(error)
    else:
        raise AssertionError("leaky detail schema should fail closed")


def test_http_repository_resume_merged_release_posts_only_exact_merge_sha(monkeypatch) -> None:
    process = load_process_submissions()
    calls: list[dict] = []

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self):
            return json.dumps({
                "ok": True,
                "id": "sub_12345678",
                "status": "ready_for_deploy",
            }).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append({
            "url": request.full_url,
            "method": request.get_method(),
            "headers": dict(request.header_items()),
            "body": request.data.decode("utf-8"),
            "timeout": timeout,
        })
        return Response()

    monkeypatch.setattr(process.urllib.request, "urlopen", fake_urlopen)
    repo = process.HttpSubmissionRepository("https://omo.space", "secret-token")
    merge_sha = "c" * 40

    repo.resume_merged_release("sub_12345678", merge_sha)

    assert calls[0]["url"] == "https://omo.space/api/internal/submissions/sub_12345678/resume-merged-release"
    assert calls[0]["method"] == "POST"
    assert calls[0]["headers"]["Authorization"] == "Bearer secret-token"
    assert json.loads(calls[0]["body"]) == {"merge_sha": merge_sha}
    assert calls[0]["timeout"] == process.HTTP_TIMEOUT_SECONDS

    try:
        repo.resume_merged_release("sub_12345678", "bad")
    except ValueError as error:
        assert "merge SHA" in str(error)
    else:
        raise AssertionError("invalid merge SHA should fail before the request")


def test_http_repository_resume_merged_release_rejects_invalid_success_envelope(monkeypatch) -> None:
    process = load_process_submissions()

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self):
            return json.dumps({
                "ok": True,
                "id": "sub_other0000",
                "status": "ready_for_deploy",
            }).encode("utf-8")

    monkeypatch.setattr(process.urllib.request, "urlopen", lambda request, timeout: Response())
    repo = process.HttpSubmissionRepository("https://omo.space", "secret-token")

    with pytest.raises(RuntimeError, match="recovery was rejected"):
        repo.resume_merged_release("sub_12345678", "c" * 40)


def test_main_resume_merged_release_derives_sha_from_authoritative_detail(monkeypatch) -> None:
    process = load_process_submissions()
    submission_id = "sub_12345678"
    merge_sha = "c" * 40
    calls: list[tuple[str, str]] = []
    outputs: list[dict] = []

    class Repository:
        def get(self, requested_id):
            assert requested_id == submission_id
            return {
                "id": submission_id,
                "status": "failed",
                "release_phase": "merged_verified",
                "release_merge_sha": merge_sha,
            }
        def resume_merged_release(self, requested_id, requested_sha):
            calls.append((requested_id, requested_sha))
        def close(self):
            return None

    class Args:
        dry_run = None
        deploy = False
        prepare_release = False
        id = None
        export_review = None
        review_dir = None
        mark_deployed = None
        merge_verified_release = None
        resume_merged_release = submission_id
        deploy_merged_release = None

    monkeypatch.setattr(process, "parse_args", lambda: Args())
    monkeypatch.setattr(process, "repository_from_env", lambda _environ: Repository())
    monkeypatch.setattr(process, "output", outputs.append)

    assert process.main() == 0
    assert calls == [(submission_id, merge_sha)]
    assert outputs == [{"id": submission_id, "status": "ready_for_deploy", "release_phase": "merged_verified"}]


@pytest.mark.parametrize("row", [
    {"status": "ready_for_deploy", "release_phase": "merged_verified", "release_merge_sha": "c" * 40},
    {"status": "failed", "release_phase": "pr_open", "release_merge_sha": "c" * 40},
    {"status": "failed", "release_phase": "merged_verified", "release_merge_sha": "bad"},
])
def test_main_resume_merged_release_rejects_invalid_authoritative_state(monkeypatch, row) -> None:
    process = load_process_submissions()
    submission_id = "sub_12345678"
    calls: list[tuple[str, str]] = []

    class Repository:
        def get(self, requested_id):
            assert requested_id == submission_id
            return {"id": submission_id, **row}
        def resume_merged_release(self, requested_id, requested_sha):
            calls.append((requested_id, requested_sha))
        def close(self):
            return None

    class Args:
        dry_run = None
        deploy = False
        prepare_release = False
        id = None
        export_review = None
        review_dir = None
        mark_deployed = None
        merge_verified_release = None
        resume_merged_release = submission_id
        deploy_merged_release = None

    monkeypatch.setattr(process, "parse_args", lambda: Args())
    monkeypatch.setattr(process, "repository_from_env", lambda _environ: Repository())

    with pytest.raises(RuntimeError, match="not a failed merge-verified release"):
        process.main()
    assert calls == []


def test_claim_sql_is_atomic_and_returns_only_processor_fields() -> None:
    process = load_process_submissions()

    class Cursor:
        def execute(self, query, params):
            assert "FOR UPDATE SKIP LOCKED" in query
            assert "UPDATE submissions AS submission" in query
            assert "RETURNING submission.id, submission.name, submission.slug, submission.content, submission.source_sha256, submission.requested_runtime, candidate.prior_status" in " ".join(query.split())
            assert "user_id" not in query.split("RETURNING", 1)[1]
            assert params == ["queued"]
        def fetchone(self):
            return None

    class Connection:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def cursor(self, cursor_factory=None): return CursorContext()

    class CursorContext:
        def __enter__(self): return Cursor()
        def __exit__(self, exc_type, exc, tb): return False

    repo = object.__new__(process.SubmissionRepository)
    repo.connection = Connection()
    repo._extras = object()

    assert repo.claim() is None


# --- R4 open-source publish gate -------------------------------------------


def make_oss_source_root(tmp_path: Path, slug: str = "oss-test-skill", version: str = "1.2.3", price: float = 0.1) -> Path:
    source_root = tmp_path / "source-root"
    container = source_root / "containers" / slug
    (container / "source").mkdir(parents=True)
    (container / "source" / "SKILL.md").write_text(
        "---\n"
        f"name: {slug}\n"
        "description: An OSS test skill.\n"
        "---\n"
        "\n"
        f"# {slug.replace('-', ' ').title()}\n"
        "\n"
        "A short description of what this does.\n"
        "\n"
        "## Inputs\n"
        "\n"
        "- `word`: one English word, 1-80 characters.\n"
        "- `dialect`: `en-US` or `en-GB`.\n"
        "\n"
        "## Workflow\n"
        "\n"
        "1. **Validate:** Reject bad input before a provider call.\n"
        "\n"
        "## Output contract\n"
        "\n"
        "- Return one JSON object with `run_id` and `usage`.\n",
        encoding="utf-8",
    )
    (container / "manifest.json").write_text(
        json.dumps({"name": "OSS Test Skill", "version": version, "description": "An OSS test skill."}),
        encoding="utf-8",
    )
    (container / "pricing-report.json").write_text(json.dumps({"display_price_usd": price}), encoding="utf-8")
    return source_root


def make_oss_remote(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "oss-remote.git"
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(remote)], check=True, capture_output=True)
    seed = tmp_path / "oss-seed"
    seed.mkdir()
    (seed / "LICENSE").write_text("MIT License\n\nCopyright (c) 2026 Omo\n", encoding="utf-8")
    (seed / "README.md").write_text("# Omo Skills\n\nFree skill.md files.\n", encoding="utf-8")
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=seed, check=True, capture_output=True)
    subprocess.run(["git", "-C", str(seed), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(seed), "-c", "user.name=Seed", "-c", "user.email=seed@example.com", "commit", "-m", "seed"],
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "-C", str(seed), "remote", "add", "origin", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(seed), "push", "-u", "origin", "main"], check=True, capture_output=True)
    checkout = tmp_path / "oss-checkout"
    subprocess.run(["git", "clone", str(remote), str(checkout)], check=True, capture_output=True)
    return remote, checkout


def oss_env(remote: Path, checkout: Path) -> dict[str, str]:
    return {"OMO_OSS_REPO_DIR": str(checkout), "OMO_OSS_REPO_URL": str(remote)}


def test_oss_publish_publishes_artifacts_and_pushes(tmp_path: Path) -> None:
    process = load_process_submissions()
    source_root = make_oss_source_root(tmp_path)
    remote, checkout = make_oss_remote(tmp_path)

    result = process.publish_oss_release("oss-test-skill", source_root, oss_env(remote, checkout))

    assert result["status"] == "published"
    assert result["slug"] == "oss-test-skill"
    assert result["version"] == "1.2.3"
    assert result["commit"]
    target = checkout / "skills" / "oss-test-skill"
    assert (target / "SKILL.md").exists()
    published = (target / "SKILL.md").read_text(encoding="utf-8")
    assert published.startswith("---\n")
    assert "Omo open source" in published  # policy header inserted after frontmatter
    assert "`word`: one English word" in published
    assert (target / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")
    assert "omo.space" in (target / "README.md").read_text(encoding="utf-8")
    assert "**$0.10 per run**" in (target / "README.md").read_text(encoding="utf-8")
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["slug"] == "oss-test-skill"
    assert manifest["version"] == "1.2.3"
    assert manifest["license"] == "MIT"
    assert manifest["policy"] == process.OSS_POLICY_URL
    assert manifest["hosted_run_price_usd"] == 0.1
    assert manifest["inputs"] == ["`word`: one English word, 1-80 characters.", "`dialect`: `en-US` or `en-GB`."]
    assert manifest["outputs"] == ["Return one JSON object with `run_id` and `usage`."]
    assert manifest["source_sha256"] == process.sha256_bytes(published.encode("utf-8"))
    assert manifest["publish_mechanism"] == process.OSS_PUBLISH_MECHANISM
    head = subprocess.run(
        ["git", "-C", str(checkout), "log", "-1", "--format=%s"], check=True, capture_output=True, text=True
    )
    assert head.stdout.strip() == "release(oss-test-skill): v1.2.3 oss publish"
    remote_head = subprocess.run(
        ["git", "--git-dir", str(remote), "log", "-1", "--format=%H"], check=True, capture_output=True, text=True
    )
    assert remote_head.stdout.strip() == result["commit"]  # push landed


def test_oss_publish_excluded_premium_never_publishes(tmp_path: Path) -> None:
    process = load_process_submissions()
    source_root = make_oss_source_root(tmp_path, slug="illustrated-decodable-story-maker")
    remote, checkout = make_oss_remote(tmp_path)

    result = process.publish_oss_release("illustrated-decodable-story-maker", source_root, oss_env(remote, checkout))

    assert result == {"status": "excluded_premium", "slug": "illustrated-decodable-story-maker"}
    assert not (checkout / "skills" / "illustrated-decodable-story-maker").exists()
    log = subprocess.run(["git", "-C", str(checkout), "rev-list", "--count", "HEAD"], check=True, capture_output=True, text=True)
    assert log.stdout.strip() == "1"  # seed only; the flagship was never committed


def test_oss_publish_release_gate_excludes_premium_without_publishing(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[list[str]] = []
    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append(list(command)))
    monkeypatch.setattr(
        process,
        "verify_generated_worker_registry",
        lambda slugs, worker_root=process.WORKER_ROOT: {"status": "passed", "slug_counts": {slugs[0]: 1}},
    )
    monkeypatch.setattr(process, "deploy_worker_registry", lambda worker_root=process.WORKER_ROOT: {"status": "deployed"})
    monkeypatch.setattr(
        process,
        "smoke_live_worker_registry",
        lambda slugs, base_url=process.LIVE_WORKER_BASE_URL, timeout_seconds=process.HTTP_TIMEOUT_SECONDS: {
            "status": "passed",
            "slugs": {slugs[0]: {"status": 401, "error": "authentication_required"}},
        },
    )
    monkeypatch.setattr(
        process,
        "publish_oss_release",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("premium must never reach the publish function")),
    )
    profile_path = write_profile(tmp_path, "worker-native")
    release = {
        "submission_id": "sub_verifieddeploy000000000009",
        "slug": "illustrated-decodable-story-maker",
        "selected_runtime": "worker-native",
        "source_sha256": "a" * 64,
        "artifact_hash": "b" * 64,
        "head_sha": "c" * 40,
        "merge_sha": "d" * 40,
        "verified_merge_sha": "d" * 40,
        "release_phase": "merged_verified",
    }

    class Adapter:
        def verify_merged_release(self, release_metadata):
            return release_metadata

    result = process.deploy_merged_release(
        SKILL_PATH, "illustrated-decodable-story-maker", profile_path, release, Adapter()
    )

    assert result["release_gates"]["R4"] == {"status": "excluded_premium", "slug": "illustrated-decodable-story-maker"}


def test_oss_publish_idempotent_release_is_noop_and_changes_republish(tmp_path: Path) -> None:
    process = load_process_submissions()
    source_root = make_oss_source_root(tmp_path)
    remote, checkout = make_oss_remote(tmp_path)

    first = process.publish_oss_release("oss-test-skill", source_root, oss_env(remote, checkout))
    assert first["status"] == "published"

    second = process.publish_oss_release("oss-test-skill", source_root, oss_env(remote, checkout))
    assert second["status"] == "up_to_date"
    assert second["source_sha256"] == first["source_sha256"]
    log1 = subprocess.run(["git", "-C", str(checkout), "rev-list", "--count", "HEAD"], check=True, capture_output=True, text=True)
    assert log1.stdout.strip() == "2"  # seed + publish; identical re-release adds no commit

    skill_path = source_root / "containers" / "oss-test-skill" / "source" / "SKILL.md"
    skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\n## Changelog\n\n- v1.3.0 tweak.\n", encoding="utf-8")
    third = process.publish_oss_release("oss-test-skill", source_root, oss_env(remote, checkout))
    assert third["status"] == "published"
    assert third["source_sha256"] != second["source_sha256"]
    assert "v1.3.0 tweak" in (checkout / "skills" / "oss-test-skill" / "SKILL.md").read_text(encoding="utf-8")
    log2 = subprocess.run(["git", "-C", str(checkout), "rev-list", "--count", "HEAD"], check=True, capture_output=True, text=True)
    assert log2.stdout.strip() == "3"  # one new commit for the changed release


def test_oss_publish_clone_failure_fails_closed(tmp_path: Path) -> None:
    process = load_process_submissions()
    source_root = make_oss_source_root(tmp_path)
    env = {
        "OMO_OSS_REPO_DIR": str(tmp_path / "missing-checkout"),
        "OMO_OSS_REPO_URL": str(tmp_path / "missing-remote.git"),
    }
    try:
        process.publish_oss_release("oss-test-skill", source_root, env)
    except process.OssPublishBlocker as blocker:
        assert blocker.code == "oss_publish_clone_failed"
        assert blocker.gate == "R4"
        assert "omo-space/skills" in blocker.remediation
    else:
        raise AssertionError("clone failure must fail closed with a typed blocker")


def test_oss_publish_commit_failure_fails_closed(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    source_root = make_oss_source_root(tmp_path)
    remote, checkout = make_oss_remote(tmp_path)
    real_oss_git = process._oss_git

    def failing_commit(repo_dir, *args):
        if "commit" in args:
            return subprocess.CompletedProcess(["git", "commit"], 128, "fatal: identity missing", "")
        return real_oss_git(repo_dir, *args)

    monkeypatch.setattr(process, "_oss_git", failing_commit)
    try:
        process.publish_oss_release("oss-test-skill", source_root, oss_env(remote, checkout))
    except process.OssPublishBlocker as blocker:
        assert blocker.code == "oss_publish_commit_failed"
        assert blocker.gate == "R4"
    else:
        raise AssertionError("commit failure must fail closed with a typed blocker")


def test_oss_publish_push_failure_fails_closed(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    source_root = make_oss_source_root(tmp_path)
    remote, checkout = make_oss_remote(tmp_path)
    real_oss_git = process._oss_git

    def failing_push(repo_dir, *args):
        if "push" in args:
            return subprocess.CompletedProcess(["git", "push"], 128, "fatal: unable to access", "")
        return real_oss_git(repo_dir, *args)

    monkeypatch.setattr(process, "_oss_git", failing_push)
    try:
        process.publish_oss_release("oss-test-skill", source_root, oss_env(remote, checkout))
    except process.OssPublishBlocker as blocker:
        assert blocker.code == "oss_publish_push_failed"
        assert blocker.gate == "R4"
        assert "omo-space/skills" in blocker.remediation
    else:
        raise AssertionError("push failure must fail closed with a typed blocker")
    # the local commit exists (resumable) but the remote never advanced
    local = subprocess.run(["git", "-C", str(checkout), "log", "-1", "--format=%s"], check=True, capture_output=True, text=True)
    assert local.stdout.strip() == "release(oss-test-skill): v1.2.3 oss publish"
    remote_log = subprocess.run(["git", "--git-dir", str(remote), "rev-list", "--count", "HEAD"], check=True, capture_output=True, text=True)
    assert remote_log.stdout.strip() == "1"


def test_release_worktree_commit_uses_scoped_git_identity(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[list[str]] = []

    def runner(command, cwd=None, text=True):
        commands.append(list(command))
        if command[:2] == ["git", "rev-parse"]:
            return "a" * 40
        return ""

    monkeypatch.setattr(
        process,
        "copy_allowlisted_release_paths",
        lambda _slug, _destination: ["site/deploy/worker.js"],
    )
    adapter = process.GitHubReleaseAdapter(
        command_runner=runner,
        scratch_root=tmp_path / "release-scratch",
    )

    _worktree, head_sha = adapter._prepare_worktree(
        "omo-release/sub_test00000000000000000000000000000000-slug",
        "slug",
    )

    assert head_sha == "a" * 40
    commit_index = next(index for index, command in enumerate(commands) if command[:2] == ["git", "-c"])
    assert commands[commit_index] == [
        "git",
        "-c",
        "user.name=Omo Trusted Release",
        "-c",
        "user.email=omo-trusted-release@users.noreply.github.com",
        "commit",
        "-m",
        "Release slug",
    ]
