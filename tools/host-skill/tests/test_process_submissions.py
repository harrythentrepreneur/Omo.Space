"""Tests for reviewed submission deployment routing."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError


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
    assert any("modal deploy" in command for command in flattened)
    assert any("wrangler deploy" in command for command in flattened)
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

    monkeypatch.setattr(process, "run_checked", lambda command, cwd=process.ROOT: commands.append((list(command), cwd)))
    monkeypatch.setattr(process, "direct_modal_canary", lambda slug, profile_path, timeout_seconds=240: canaries.append((slug, profile_path)))
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
    assert commands == [(["npx", "wrangler", "deploy"], release_root / "site" / "deploy")]
    assert canaries == []


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
    assert decision["reason"] == "creator_selected_modal"


def test_runtime_preference_helper_is_data_only_and_changes_only_auto() -> None:
    process = load_process_submissions()
    source_sha = "1" * 64
    runtime_by_source = {source_sha: "modal-hosted"}

    assert process.runtime_preference_for_reviewed_source("auto", source_sha, runtime_by_source) == "modal-hosted"
    assert process.runtime_preference_for_reviewed_source("worker-native", source_sha, runtime_by_source) == "worker-native"
    assert process.runtime_preference_for_reviewed_source("modal-hosted", source_sha, runtime_by_source) == "modal-hosted"
    assert process.runtime_preference_for_reviewed_source("auto", "2" * 64, runtime_by_source) == "auto"
    assert process.runtime_preference_for_reviewed_source(None, source_sha, runtime_by_source) is None


def test_reviewed_profile_explicit_runtime_override_is_not_silently_changed(tmp_path: Path) -> None:
    process = load_process_submissions()
    woven_source_sha = "6297f14dfc8d4815efc041316e5c19df7faf4cb31dae3f73a0badc09101b90bf"

    profile_path, decision = process.reviewed_profile_artifact(
        "woven-storybook-pipeline",
        "worker-native",
        tmp_path,
        source_sha256=woven_source_sha,
    )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    assert profile["runtime_preference"] == "worker-native"
    assert decision["requested"] == "worker-native"
    assert decision["effective"] == "worker-native"
    assert decision["reason"] == "bounded_single_llm_is_worker_compatible"


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
