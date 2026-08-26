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
ACTIONS_APP_ID = 15368


def load_module():
    spec = importlib.util.spec_from_file_location("release_merge_controller", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def protection(**review_changes):
    reviews = {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": True,
        "require_last_push_approval": True,
    }
    reviews.update(review_changes)
    return {
        "required_status_checks": {
            "strict": True,
            "checks": [{"context": "contracts", "app_id": ACTIONS_APP_ID}],
        },
        "required_pull_request_reviews": reviews,
        "allow_force_pushes": {"enabled": False},
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
        "mergeCommit": None,
    }
    value.update(changes)
    return value


def review(review_id=7, state="APPROVED", commit_id=HEAD, login="kaviru2"):
    return {
        "id": review_id,
        "state": state,
        "commit_id": commit_id,
        "submitted_at": "2026-08-26T00:00:00Z",
        "user": {"login": login, "type": "User"},
    }


def check_runs(conclusion="success", app_id=ACTIONS_APP_ID, run_id=7):
    return {
        "total_count": 1,
        "check_runs": [{
            "id": run_id,
            "name": "contracts",
            "status": "completed",
            "conclusion": conclusion,
            "app": {"id": app_id},
            "head_sha": HEAD,
        }],
    }


def successful_runner(calls, *, reviews=None, pr_changes=None, protection_value=None, check_value=None):
    views = [open_pr(**(pr_changes or {})), open_pr(state="MERGED", mergeCommit={"oid": MERGE})]
    review_pages = reviews if reviews is not None else [[review()]]

    def runner(command):
        calls.append(command)
        joined = " ".join(command)
        if command[:2] == ["gh", "api"] and joined.endswith("/protection"):
            return json.dumps(protection_value or protection())
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps(views.pop(0))
        if command[:2] == ["gh", "api"] and "/reviews?per_page=100" in joined:
            return json.dumps(review_pages)
        if command[:2] == ["gh", "api"] and "/check-runs?per_page=100" in joined:
            return json.dumps(check_value or check_runs())
        if command[:3] == ["gh", "pr", "merge"]:
            return ""
        raise AssertionError(command)

    return runner


def test_merges_only_exact_head_after_kaviru2_review_and_actions_check() -> None:
    module = load_module()
    calls = []
    result = module.merge_release_pr(42, runner=successful_runner(calls))
    assert result == {"status": "merged", "pr_number": 42, "head_sha": HEAD, "merge_sha": MERGE}
    merge = next(command for command in calls if command[:3] == ["gh", "pr", "merge"])
    assert merge == [
        "gh", "pr", "merge", "42", "--repo", module.REPOSITORY,
        "--squash", "--match-head-commit", HEAD,
    ]
    assert not any("deploy" in " ".join(command).lower() for command in calls)


def test_latest_matching_contracts_check_must_be_successful_and_well_typed() -> None:
    module = load_module()
    older = check_runs(run_id=7)["check_runs"][0]
    newer = check_runs(conclusion="failure", run_id=8)["check_runs"][0]
    with pytest.raises(module.MergeControllerError, match="required_checks_not_successful"):
        module.merge_release_pr(
            42,
            runner=successful_runner(
                [], check_value={"total_count": 2, "check_runs": [older, newer]}
            ),
        )

    malformed = dict(newer)
    malformed["id"] = "bad"
    with pytest.raises(module.MergeControllerError, match="github_response_invalid"):
        module.merge_release_pr(
            42,
            runner=successful_runner(
                [], check_value={"total_count": 2, "check_runs": [older, malformed]}
            ),
        )

    float_app = check_runs()["check_runs"][0]
    float_app["app"] = {"id": float(ACTIONS_APP_ID)}
    with pytest.raises(module.MergeControllerError, match="github_response_invalid"):
        module.merge_release_pr(
            42,
            runner=successful_runner(
                [], check_value={"total_count": 1, "check_runs": [float_app]}
            ),
        )

    assert module.merge_release_pr(
        42,
        runner=successful_runner([], check_value=check_runs(run_id=3_000_000_000)),
    )["status"] == "merged"


@pytest.mark.parametrize(
    ("reviews", "pr_changes", "protection_value", "check_value", "blocker"),
    [
        ([[review(login="someone-else")]], None, None, None, "separate_review_required"),
        ([[review(commit_id="c" * 40)]], None, None, None, "exact_head_review_required"),
        ([[review(), review(8, state="DISMISSED")]], None, None, None, "separate_review_required"),
        ([[review(), review(8, state="CHANGES_REQUESTED")]], None, None, None, "separate_review_required"),
        (None, {"headRepository": {"nameWithOwner": "evil/fork"}}, None, None, "release_pr_identity_invalid"),
        (None, {"author": {"login": "kaviru2"}}, None, None, "release_pr_identity_invalid"),
        (None, None, protection(require_code_owner_reviews=False), None, "branch_protection_inadequate"),
        (None, None, protection(require_last_push_approval=False), None, "branch_protection_inadequate"),
        (
            None,
            None,
            {
                **protection(),
                "required_status_checks": {
                    "strict": True,
                    "checks": [{"context": "contracts", "app_id": 15368.0}],
                },
            },
            None,
            "branch_protection_inadequate",
        ),
        (None, None, None, check_runs(app_id=999), "required_checks_not_successful"),
        (None, None, None, check_runs(conclusion="failure"), "required_checks_not_successful"),
    ],
)
def test_controller_fails_closed_without_merge(reviews, pr_changes, protection_value, check_value, blocker) -> None:
    module = load_module()
    calls = []
    runner = successful_runner(
        calls,
        reviews=reviews,
        pr_changes=pr_changes,
        protection_value=protection_value,
        check_value=check_value,
    )
    with pytest.raises(module.MergeControllerError) as caught:
        module.merge_release_pr(42, runner=runner)
    assert caught.value.code == blocker
    assert not any(command[:3] == ["gh", "pr", "merge"] for command in calls)


def test_review_pagination_accepts_exact_review_after_first_30() -> None:
    module = load_module()
    calls = []
    page_one = [review(i + 1, login=f"reviewer-{i}") for i in range(30)]
    page_two = [review(100, login="kaviru2")]
    assert module.merge_release_pr(
        42, runner=successful_runner(calls, reviews=[page_one, page_two])
    )["status"] == "merged"
    review_call = next(command for command in calls if "/reviews?per_page=100" in " ".join(command))
    assert "--paginate" in review_call and "--slurp" in review_call


def test_scheduled_candidates_are_isolated_when_one_is_malformed(tmp_path: Path) -> None:
    module = load_module()
    event = tmp_path / "schedule.json"
    event.write_text(json.dumps({
        "schedule": "*/5 * * * *",
        "repository": {"full_name": module.REPOSITORY},
    }))
    valid_views = [open_pr(number=42), open_pr(number=42, state="MERGED", mergeCommit={"oid": MERGE})]

    def runner(command):
        joined = " ".join(command)
        if command[:3] == ["gh", "pr", "list"]:
            return json.dumps([
                {"number": 41, "headRefName": "omo-release/sub_12345678-one"},
                {"number": 42, "headRefName": "omo-release/sub_12345678-two"},
            ])
        if command[:4] == ["gh", "pr", "view", "41"]:
            return json.dumps(open_pr(number=41))
        if command[:2] == ["gh", "api"] and joined.endswith("/protection"):
            return json.dumps(protection())
        if command[:4] == ["gh", "pr", "view", "42"]:
            return json.dumps(valid_views.pop(0))
        if command[:2] == ["gh", "api"] and "/pulls/41/reviews?per_page=100" in joined:
            malformed = review(review_id=8)
            malformed["id"] = "malformed"
            return json.dumps([[review(), malformed]])
        if command[:2] == ["gh", "api"] and "/pulls/42/reviews?per_page=100" in joined:
            return json.dumps([[review()]])
        if command[:2] == ["gh", "api"] and "/check-runs?per_page=100" in joined:
            return json.dumps(check_runs())
        if command[:4] == ["gh", "pr", "merge", "42"]:
            return ""
        raise AssertionError(command)

    result = module.run(event, runner=runner)
    assert result["results"] == [
        {"status": "blocked", "pr_number": 41, "reason": "github_response_invalid"},
        {"status": "merged", "pr_number": 42, "head_sha": HEAD, "merge_sha": MERGE},
    ]


def test_merge_workflow_loads_controller_only_from_main() -> None:
    workflow = (ROOT / ".github/workflows/trusted-release-merge.yml").read_text()
    assert "pull_request_review:" in workflow
    assert "workflow_run:" in workflow
    assert "cron: '*/5 * * * *'" in workflow
    assert "contents: write" in workflow and "pull-requests: write" in workflow
    assert "ref: main" in workflow and "persist-credentials: false" in workflow
    assert "path: controller" in workflow
    assert "if [ ! -f controller/tools/host-skill/release_merge_controller.py ]; then" in workflow
    assert "exit 0" in workflow
    assert "python3 controller/tools/host-skill/release_merge_controller.py" in workflow
    assert "github.event.pull_request.head.sha" not in workflow
