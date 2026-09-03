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
SUBMISSION = "sub_" + "1" * 32


def load_module():
    spec = importlib.util.spec_from_file_location("release_merge_controller", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def open_pr(**changes):
    value = {
        "number": 42,
        "state": "OPEN",
        "isDraft": False,
        "baseRefName": "main",
        "headRefName": f"omo-release/{SUBMISSION}-safe-workflow",
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


def successful_runner(
    calls, *, reviews=None, pr_changes=None, check_value=None,
    merge_value=None,
):
    views = [open_pr(**(pr_changes or {})), open_pr(state="MERGED", mergeCommit={"oid": MERGE})]
    review_pages = reviews if reviews is not None else [[review()]]

    def runner(command):
        calls.append(command)
        joined = " ".join(command)
        if command[:2] == ["gh", "api"] and joined.endswith("/protection"):
            raise AssertionError("merge path must not require Administration: read")
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps(views.pop(0))
        if command[:3] == ["gh", "pr", "list"]:
            return json.dumps([open_pr()])
        if command[:2] == ["gh", "api"] and "/reviews?per_page=100" in joined:
            return json.dumps(review_pages)
        if command[:2] == ["gh", "api"] and "/check-runs?per_page=100" in joined:
            return json.dumps(check_value or check_runs())
        if command[:4] == ["gh", "api", "--method", "PUT"] and joined.endswith("/pulls/42/merge -f sha=" + HEAD + " -f merge_method=squash"):
            return json.dumps(merge_value if merge_value is not None else {
                "sha": MERGE, "merged": True, "message": "Pull Request successfully merged",
            })
        raise AssertionError(command)

    return runner


def test_merges_only_exact_head_after_kaviru2_review_and_actions_check() -> None:
    module = load_module()
    calls = []
    result = module.merge_release_pr(42, runner=successful_runner(calls))
    assert result == {"status": "merged", "pr_number": 42, "head_sha": HEAD, "merge_sha": MERGE}
    merge = next(command for command in calls if command[:4] == ["gh", "api", "--method", "PUT"])
    assert merge == [
        "gh", "api", "--method", "PUT",
        f"repos/{module.REPOSITORY}/pulls/42/merge",
        "-f", f"sha={HEAD}", "-f", "merge_method=squash",
    ]
    assert not any("/branches/main/protection" in " ".join(command) for command in calls)
    assert not any("deploy" in " ".join(command).lower() for command in calls)


def test_real_github_review_ids_above_signed_32_bit_are_valid() -> None:
    module = load_module()
    result = module.merge_release_pr(
        42,
        runner=successful_runner([], reviews=[[review(review_id=5_095_757_861)]]),
    )
    assert result["status"] == "merged"


def test_older_open_release_for_same_slug_is_never_merged() -> None:
    module = load_module()
    calls = []
    newer = open_pr(
        number=43,
        headRefName="omo-release/sub_" + "2" * 32 + "-safe-workflow",
        headRefOid="c" * 40,
    )
    base_runner = successful_runner(calls)

    def runner(command):
        if command[:3] == ["gh", "pr", "list"]:
            calls.append(command)
            return json.dumps([open_pr(), newer])
        return base_runner(command)

    with pytest.raises(module.MergeControllerError, match="superseded_release_pr"):
        module.merge_release_pr(42, runner=runner)
    assert not any(call[:4] == ["gh", "api", "--method", "PUT"] for call in calls)


def test_behind_latest_release_is_exact_head_updated_then_requeued() -> None:
    module = load_module()
    old_head = HEAD
    new_head = "c" * 40
    views = [
        open_pr(mergeStateStatus="BEHIND"),
        open_pr(headRefOid=new_head, reviewDecision="REVIEW_REQUIRED", mergeStateStatus="BLOCKED"),
    ]
    calls = []

    def runner(command):
        calls.append(command)
        joined = " ".join(command)
        if command[:3] == ["gh", "pr", "view"]:
            return json.dumps(views.pop(0))
        if command[:3] == ["gh", "pr", "list"]:
            return json.dumps([open_pr(mergeStateStatus="BEHIND")])
        if command[:4] == ["gh", "api", "--method", "PUT"] and "/update-branch" in joined:
            assert f"expected_head_sha={old_head}" in command
            return json.dumps({
                "message": "Updating pull request branch.",
                "url": "https://api.github.com/repos/harrythentrepreneur/Omo.Space/pulls/42",
            })
        raise AssertionError(command)

    assert module.merge_release_pr(42, runner=runner) == {
        "status": "updated",
        "pr_number": 42,
        "previous_head_sha": old_head,
        "head_sha": new_head,
    }
    assert not any("/pulls/42/merge" in " ".join(call) for call in calls)


@pytest.mark.parametrize(
    "receipt",
    [
        [],
        {"sha": MERGE, "merged": False, "message": "blocked"},
        {"sha": "bad", "merged": True, "message": "merged"},
        {"sha": MERGE, "merged": True, "message": ""},
    ],
)
def test_rest_merge_receipt_must_confirm_a_valid_merge(receipt) -> None:
    module = load_module()
    calls = []
    runner = successful_runner(calls, merge_value=receipt)
    with pytest.raises(module.MergeControllerError, match="merge_receipt_invalid"):
        module.merge_release_pr(42, runner=runner)
    assert len([call for call in calls if call[:4] == ["gh", "api", "--method", "PUT"]]) == 1


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
    ("reviews", "pr_changes", "check_value", "blocker"),
    [
        ([[review(login="someone-else")]], None, None, "separate_review_required"),
        ([[review(commit_id="c" * 40)]], None, None, "exact_head_review_required"),
        ([[review(), review(8, state="DISMISSED")]], None, None, "separate_review_required"),
        ([[review(), review(8, state="CHANGES_REQUESTED")]], None, None, "separate_review_required"),
        (None, {"headRepository": {"nameWithOwner": "evil/fork"}}, None, "release_pr_identity_invalid"),
        (None, {"author": {"login": "kaviru2"}}, None, "release_pr_identity_invalid"),
        (None, None, check_runs(app_id=999), "required_checks_not_successful"),
        (None, None, check_runs(conclusion="failure"), "required_checks_not_successful"),
    ],
)
def test_controller_fails_closed_without_merge(reviews, pr_changes, check_value, blocker) -> None:
    module = load_module()
    calls = []
    runner = successful_runner(
        calls,
        reviews=reviews,
        pr_changes=pr_changes,
        check_value=check_value,
    )
    with pytest.raises(module.MergeControllerError) as caught:
        module.merge_release_pr(42, runner=runner)
    assert caught.value.code == blocker
    assert not any(command[:4] == ["gh", "api", "--method", "PUT"] for command in calls)


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
            if "number,state,isDraft" in joined:
                return json.dumps([open_pr(number=42)])
            return json.dumps([
                {"number": 41, "headRefName": "omo-release/sub_" + "1" * 32 + "-one"},
                {"number": 42, "headRefName": "omo-release/sub_" + "2" * 32 + "-two"},
            ])
        if command[:4] == ["gh", "pr", "view", "41"]:
            return json.dumps(open_pr(number=41))
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
        if command[:4] == ["gh", "api", "--method", "PUT"] and "/pulls/42/merge" in joined:
            return json.dumps({"sha": MERGE, "merged": True, "message": "Pull Request successfully merged"})
        raise AssertionError(command)

    result = module.run(event, runner=runner)
    assert result["results"] == [
        {"status": "blocked", "pr_number": 41, "reason": "github_response_invalid"},
        {"status": "merged", "pr_number": 42, "head_sha": HEAD, "merge_sha": MERGE},
    ]


def test_cli_fails_the_workflow_when_any_candidate_is_blocked(tmp_path: Path, monkeypatch, capsys) -> None:
    module = load_module()
    event = tmp_path / "event.json"
    event.write_text("{}")
    monkeypatch.setattr(module, "run", lambda _path: {
        "status": "complete",
        "results": [{"status": "blocked", "pr_number": 42, "reason": "github_command_failed"}],
    })
    assert module.main(["--event", str(event)]) == 1
    assert '"status":"blocked"' in capsys.readouterr().out

    monkeypatch.setattr(module, "run", lambda _path: {
        "status": "complete",
        "results": [{"status": "waiting", "pr_number": 42, "reason": "separate_review_required"}],
    })
    assert module.main(["--event", str(event)]) == 0


def test_merge_workflow_loads_controller_only_from_main() -> None:
    workflow = (ROOT / ".github/workflows/trusted-release-merge.yml").read_text()
    assert "pull_request_review:" in workflow
    assert "workflow_run:" in workflow
    assert "cron: '*/5 * * * *'" in workflow
    assert "contents: write" in workflow and "pull-requests: write" in workflow
    assert "environment: Production" in workflow
    assert "GH_TOKEN: ${{ secrets.TRUSTED_RELEASE_REVIEW_TOKEN }}" in workflow
    assert "GH_TOKEN: ${{ github.token }}" not in workflow
    assert "ref: main" in workflow and "persist-credentials: false" in workflow
    assert "path: controller" in workflow
    assert "if [ ! -f controller/tools/host-skill/release_merge_controller.py ]; then" in workflow
    assert "exit 0" in workflow
    assert "python3 controller/tools/host-skill/release_merge_controller.py" in workflow
    assert "github.event.pull_request.head.sha" not in workflow
