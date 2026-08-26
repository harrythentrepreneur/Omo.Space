"""Contracts for the protected autonomous release-PR merge controller."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools/host-skill/release_merge_controller.py"
HEAD = "a" * 40
MERGE = "b" * 40


def load_module():
    spec = importlib.util.spec_from_file_location("release_merge_controller", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def protection():
    return {
        "required_status_checks": {"strict": True, "contexts": ["contracts"]},
        "required_pull_request_reviews": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
        },
    }


def open_pr(**changes):
    value = {
        "number": 42,
        "state": "OPEN",
        "isDraft": False,
        "baseRefName": "main",
        "headRefName": "omo-release/sub_12345678-safe-workflow",
        "headRefOid": HEAD,
        "headRepository": {"nameWithOwner": "harrythentrepreneur/Omo.Space"},
        "author": {"login": "harrythentrepreneur"},
        "reviewDecision": "APPROVED",
        "mergeStateStatus": "CLEAN",
        "statusCheckRollup": [{"name": "contracts", "conclusion": "SUCCESS", "status": "COMPLETED"}],
        "mergeCommit": None,
    }
    value.update(changes)
    return value


def approved_review(**changes):
    value = {
        "id": 7,
        "state": "APPROVED",
        "commit_id": HEAD,
        "submitted_at": "2026-08-26T00:00:00Z",
        "author_association": "MEMBER",
        "user": {"login": "separate-human", "type": "User"},
    }
    value.update(changes)
    return value


def test_merges_only_after_exact_head_separate_review_green_checks_and_protection() -> None:
    module = load_module()
    calls = []
    views = [open_pr(), open_pr(state="MERGED", mergeCommit={"oid": MERGE})]

    def runner(command):
        calls.append(command)
        if command[:2] == ["gh", "api"] and command[-1].endswith("/protection"):
            return json.dumps(protection())
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps(views.pop(0))
        if command[:2] == ["gh", "api"] and command[-1].endswith("/reviews"):
            return json.dumps([approved_review()])
        if command[:3] == ["gh", "pr", "merge"]:
            return ""
        raise AssertionError(command)

    assert module.merge_release_pr(42, runner=runner) == {
        "status": "merged", "pr_number": 42, "head_sha": HEAD, "merge_sha": MERGE,
    }
    merge = next(command for command in calls if command[:3] == ["gh", "pr", "merge"])
    assert merge == [
        "gh", "pr", "merge", "42", "--repo", module.REPOSITORY,
        "--merge", "--match-head-commit", HEAD,
    ]


@pytest.mark.parametrize(
    ("pr_changes", "review_changes", "protection_changes", "blocker"),
    [
        ({}, {"user": {"login": "harrythentrepreneur", "type": "User"}}, {}, "separate_review_required"),
        ({}, {"commit_id": "c" * 40}, {}, "exact_head_review_required"),
        ({"statusCheckRollup": [{"name": "contracts", "conclusion": "FAILURE"}]}, {}, {}, "required_checks_not_successful"),
        ({}, {}, {"required_status_checks": {"strict": False, "contexts": ["contracts"]}}, "branch_protection_inadequate"),
    ],
)
def test_review_merge_contract_fails_closed_without_mutation(
    pr_changes, review_changes, protection_changes, blocker,
) -> None:
    module = load_module()
    calls = []
    protected = protection()
    protected.update(protection_changes)

    def runner(command):
        calls.append(command)
        if command[:2] == ["gh", "api"] and command[-1].endswith("/protection"):
            return json.dumps(protected)
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps(open_pr(**pr_changes))
        if command[:2] == ["gh", "api"] and command[-1].endswith("/reviews"):
            return json.dumps([approved_review(**review_changes)])
        raise AssertionError("mutation must not occur")

    with pytest.raises(module.MergeControllerError) as caught:
        module.merge_release_pr(42, runner=runner)
    assert caught.value.code == blocker
    assert not any(command[:3] == ["gh", "pr", "merge"] for command in calls)


def test_event_candidates_are_server_derived_and_schedule_filters_release_branches(tmp_path: Path) -> None:
    module = load_module()
    review_event = tmp_path / "review.json"
    review_event.write_text(json.dumps({
        "action": "submitted",
        "repository": {"full_name": module.REPOSITORY},
        "review": {"state": "approved"},
        "pull_request": {"number": 42},
    }))
    assert module.candidate_pr_numbers(review_event, runner=lambda command: pytest.fail(str(command))) == [42]

    schedule_event = tmp_path / "schedule.json"
    schedule_event.write_text(json.dumps({"schedule": "*/5 * * * *", "repository": {"full_name": module.REPOSITORY}}))
    assert module.candidate_pr_numbers(schedule_event, runner=lambda command: json.dumps([
        {"number": 42, "headRefName": "omo-release/sub_12345678-safe-workflow"},
        {"number": 99, "headRefName": "attacker/branch"},
    ])) == [42]

    review_event.write_text(json.dumps({
        "action": "submitted", "repository": {"full_name": "evil/fork"},
        "review": {"state": "approved"}, "pull_request": {"number": 42},
    }))
    with pytest.raises(module.MergeControllerError, match="invalid_event"):
        module.candidate_pr_numbers(review_event, runner=lambda command: "")


def test_merge_workflow_loads_controller_only_from_main_and_has_bounded_triggers() -> None:
    workflow = (ROOT / ".github/workflows/trusted-release-merge.yml").read_text()
    assert "pull_request_review:" in workflow
    assert "workflow_run:" in workflow
    assert "cron: '*/5 * * * *'" in workflow
    assert "contents: write" in workflow and "pull-requests: write" in workflow
    assert "ref: main" in workflow and "persist-credentials: false" in workflow
    assert "path: controller" in workflow
    assert "python3 controller/tools/host-skill/release_merge_controller.py" in workflow
    assert "--event \"$GITHUB_EVENT_PATH\"" in workflow
    assert "ref: ${{ github.event.pull_request.head.sha }}" not in workflow
