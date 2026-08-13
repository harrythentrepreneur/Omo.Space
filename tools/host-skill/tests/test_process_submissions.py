"""Tests for reviewed submission deployment routing."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


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
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile["runtime_preference"] = runtime_preference
    profile_path = tmp_path / f"profile-{runtime_preference}.json"
    profile_path.write_text(json.dumps(profile, sort_keys=True), encoding="utf-8")
    return profile_path


def test_worker_reviewed_selection_registers_worker_without_modal(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[list[str]] = []
    canaries: list[tuple[str, Path]] = []

    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append(list(command)))
    monkeypatch.setattr(process, "direct_modal_canary", lambda slug, profile_path, timeout_seconds=240: canaries.append((slug, profile_path)))

    profile_path = write_profile(tmp_path, "worker-native")
    process.deploy_reviewed_submission(SKILL_PATH, "facebook-ads-copywriter", profile_path, "worker-native")

    flattened = [" ".join(command) for command in commands]
    assert not any("modal deploy" in command for command in flattened)
    assert canaries == []
    register_commands = [command for command in commands if "--register" in command]
    assert len(register_commands) == 2
    assert all(str(profile_path) in command for command in register_commands)
    assert all("-m modal" not in " ".join(command) for command in commands)


def test_modal_reviewed_selection_uses_modal_gates_and_modal_registration(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    commands: list[list[str]] = []
    canaries: list[tuple[str, Path]] = []

    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append(list(command)))
    monkeypatch.setattr(process, "direct_modal_canary", lambda slug, profile_path, timeout_seconds=240: canaries.append((slug, profile_path)))

    profile_path = write_profile(tmp_path, "modal-hosted")
    process.deploy_reviewed_submission(SKILL_PATH, "facebook-ads-copywriter", profile_path, "modal-hosted")

    flattened = [" ".join(command) for command in commands]
    assert any("modal deploy" in command for command in flattened)
    assert canaries == [("facebook-ads-copywriter", profile_path)]
    register_commands = [command for command in commands if "--register" in command]
    assert len(register_commands) == 2
    assert all(str(profile_path) in command for command in register_commands)


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


def test_process_row_fails_closed_when_generated_source_hash_differs(monkeypatch, tmp_path: Path) -> None:
    process = load_process_submissions()
    source = SKILL_PATH.read_text(encoding="utf-8")
    validated = process.validate_submission("Facebook Ads Copywriter", source)
    repo = FakeRepository()
    monkeypatch.setattr(process, "evaluate_review_gate", lambda validated, allow_matching_container=False: ("ready_for_build", None))
    monkeypatch.setattr(process, "reviewed_profile_artifact", lambda slug, requested_runtime, temp_dir: (write_profile(tmp_path, "worker-native"), {"effective": "worker-native"}))
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
