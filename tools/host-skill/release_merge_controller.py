#!/usr/bin/env python3
"""Merge only trusted Omo release PRs after exact-head separate review."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Sequence

REPOSITORY = "harrythentrepreneur/Omo.Space"
BASE = "main"
TRUSTED_RELEASE_AUTHOR = "harrythentrepreneur"
TRUSTED_REVIEWER = "kaviru2"
REQUIRED_CHECK = "contracts"
REQUIRED_CHECK_APP_ID = 15368
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BRANCH_RE = re.compile(
    r"^omo-release/(?P<submission_id>sub_[0-9a-f]{32})-"
    r"(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$"
)
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_CANDIDATES = 1000
MAX_RELEASE_HISTORY = 1000
MAX_REVIEWS = 1000
MAX_GITHUB_ID = 9_007_199_254_740_991


class MergeControllerError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _run(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise MergeControllerError("github_command_failed") from None
    if result.returncode != 0 or len(result.stdout.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise MergeControllerError("github_command_failed")
    return result.stdout


def _json_command(command: list[str], runner: Callable[[list[str]], str]) -> Any:
    try:
        raw = runner(command)
        if len(raw.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise MergeControllerError("github_response_invalid")
        return json.loads(raw)
    except MergeControllerError:
        raise
    except Exception:
        raise MergeControllerError("github_response_invalid") from None


def _read_event(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= MAX_RESPONSE_BYTES:
            raise OSError
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise MergeControllerError("invalid_event") from None
    repository = value.get("repository") if isinstance(value, dict) else None
    if not isinstance(repository, dict) or repository.get("full_name") != REPOSITORY:
        raise MergeControllerError("invalid_event")
    return value


def _open_candidate_pr_numbers(runner: Callable[[list[str]], str]) -> list[int]:
    rows = _json_command([
        "gh", "pr", "list", "--repo", REPOSITORY, "--base", BASE,
        "--state", "open", "--limit", str(MAX_CANDIDATES + 1),
        "--json", "number,headRefName",
    ], runner)
    if not isinstance(rows, list) or len(rows) > MAX_CANDIDATES:
        raise MergeControllerError("github_response_invalid")
    numbers: list[int] = []
    for row in rows:
        if not isinstance(row, dict):
            raise MergeControllerError("github_response_invalid")
        number = row.get("number")
        branch = str(row.get("headRefName") or "")
        if type(number) is int and BRANCH_RE.fullmatch(branch):
            numbers.append(number)
    return sorted(set(numbers))


def candidate_pr_numbers(event_path: Path, *, runner: Callable[[list[str]], str] = _run) -> list[int]:
    event = _read_event(event_path)
    workflow_run = event.get("workflow_run")
    if event.get("action") == "completed" and isinstance(workflow_run, dict):
        name = workflow_run.get("name")
        workflow_event = workflow_run.get("event")
        if workflow_run.get("conclusion") != "success":
            return []
        if name == "trusted-release-review":
            return _open_candidate_pr_numbers(runner)
        if name != "generated-workflow-contracts":
            return []
        if workflow_event == "push":
            return _open_candidate_pr_numbers(runner)
        if workflow_event != "pull_request":
            return []
        pulls = workflow_run.get("pull_requests")
        if (
            not isinstance(pulls, list)
            or len(pulls) != 1
            or not isinstance(pulls[0], dict)
            or type(pulls[0].get("number")) is not int
        ):
            raise MergeControllerError("invalid_event")
        return [pulls[0]["number"]]

    if event.get("schedule") == "*/5 * * * *":
        return _open_candidate_pr_numbers(runner)
    return []


def _pr_view(number: int, runner: Callable[[list[str]], str]) -> dict[str, Any]:
    value = _json_command([
        "gh", "pr", "view", str(number), "--repo", REPOSITORY,
        "--json",
        "number,state,isDraft,baseRefName,headRefName,headRefOid,headRepository,author,reviewDecision,mergeStateStatus,mergeCommit",
    ], runner)
    if not isinstance(value, dict):
        raise MergeControllerError("github_response_invalid")
    return value


def _validate_pr(pr: dict[str, Any], number: int) -> tuple[str, str, str]:
    author = pr.get("author")
    repository = pr.get("headRepository")
    author_login = str(author.get("login") if isinstance(author, dict) else "")
    repository_name = str(repository.get("nameWithOwner") if isinstance(repository, dict) else "")
    head_sha = str(pr.get("headRefOid") or "").lower()
    if (
        pr.get("number") != number
        or pr.get("state") != "OPEN"
        or pr.get("isDraft") is not False
        or pr.get("baseRefName") != BASE
        or not BRANCH_RE.fullmatch(str(pr.get("headRefName") or ""))
        or not SHA_RE.fullmatch(head_sha)
        or repository_name != REPOSITORY
        or author_login != TRUSTED_RELEASE_AUTHOR
        or author_login == TRUSTED_REVIEWER
    ):
        raise MergeControllerError("release_pr_identity_invalid")
    merge_state = str(pr.get("mergeStateStatus") or "")
    if merge_state not in {"BEHIND", "BLOCKED", "CLEAN", "DIRTY", "DRAFT", "HAS_HOOKS", "UNKNOWN", "UNSTABLE"}:
        raise MergeControllerError("github_response_invalid")
    return head_sha, author_login, merge_state


def _validate_latest_release_for_slug(pr: dict[str, Any], runner: Callable[[list[str]], str]) -> None:
    branch = str(pr.get("headRefName") or "")
    match = BRANCH_RE.fullmatch(branch)
    if match is None:
        raise MergeControllerError("release_pr_identity_invalid")
    slug = match.group("slug")
    rows = _json_command([
        "gh", "pr", "list", "--repo", REPOSITORY, "--base", BASE,
        "--state", "all", "--limit", str(MAX_RELEASE_HISTORY + 1),
        "--json", "number,state,isDraft,baseRefName,headRefName,headRefOid,headRepository,author",
    ], runner)
    if not isinstance(rows, list) or len(rows) > MAX_RELEASE_HISTORY:
        raise MergeControllerError("github_response_invalid")
    matching_numbers: list[int] = []
    for row in rows:
        if not isinstance(row, dict):
            raise MergeControllerError("github_response_invalid")
        row_match = BRANCH_RE.fullmatch(str(row.get("headRefName") or ""))
        if row_match is None or row_match.group("slug") != slug:
            continue
        author = row.get("author")
        repository = row.get("headRepository")
        if (
            not isinstance(author, dict)
            or author.get("login") != TRUSTED_RELEASE_AUTHOR
            or not isinstance(repository, dict)
            or repository.get("nameWithOwner") != REPOSITORY
        ):
            continue
        number = row.get("number")
        head_sha = str(row.get("headRefOid") or "").lower()
        if (
            type(number) is not int
            or not 1 <= number <= 2_147_483_647
            or row.get("state") not in {"OPEN", "CLOSED", "MERGED"}
            or row.get("isDraft") is not False
            or row.get("baseRefName") != BASE
            or not SHA_RE.fullmatch(head_sha)
        ):
            raise MergeControllerError("github_response_invalid")
        matching_numbers.append(number)
    current_number = pr.get("number")
    if current_number not in matching_numbers:
        raise MergeControllerError("github_response_invalid")
    if current_number != max(matching_numbers):
        raise MergeControllerError("superseded_release_pr")


def _review_pages(number: int, runner: Callable[[list[str]], str]) -> list[dict[str, Any]]:
    pages = _json_command([
        "gh", "api", "--paginate", "--slurp",
        f"repos/{REPOSITORY}/pulls/{number}/reviews?per_page=100",
    ], runner)
    if not isinstance(pages, list):
        raise MergeControllerError("github_response_invalid")
    reviews: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, list):
            raise MergeControllerError("github_response_invalid")
        for item in page:
            if not isinstance(item, dict):
                raise MergeControllerError("github_response_invalid")
            review_id = item.get("id")
            state = item.get("state")
            commit_id = item.get("commit_id")
            user = item.get("user")
            login = user.get("login") if isinstance(user, dict) else None
            user_type = user.get("type") if isinstance(user, dict) else None
            if (
                type(review_id) is not int
                or not 1 <= review_id <= MAX_GITHUB_ID
                or state not in {"APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED", "PENDING"}
                or not isinstance(login, str)
                or not 1 <= len(login) <= 100
                or user_type not in {"User", "Bot"}
                or (commit_id is not None and (not isinstance(commit_id, str) or not SHA_RE.fullmatch(commit_id.lower())))
            ):
                raise MergeControllerError("github_response_invalid")
            reviews.append(item)
            if len(reviews) > MAX_REVIEWS:
                raise MergeControllerError("github_response_invalid")
    return reviews


def _validate_separate_review(reviews: list[dict[str, Any]], *, head_sha: str, author_login: str) -> None:
    latest: dict[str, Any] | None = None
    for item in reviews:
        user = item.get("user")
        login = str(user.get("login") if isinstance(user, dict) else "")
        if login != TRUSTED_REVIEWER:
            continue
        if not isinstance(user, dict) or user.get("type") != "User" or login == author_login:
            continue
        if latest is None or int(item.get("id") or 0) > int(latest.get("id") or 0):
            latest = item
    if latest is None or latest.get("state") != "APPROVED":
        raise MergeControllerError("separate_review_required")
    if str(latest.get("commit_id") or "").lower() != head_sha:
        raise MergeControllerError("exact_head_review_required")


def _validate_required_check(head_sha: str, runner: Callable[[list[str]], str]) -> None:
    value = _json_command([
        "gh", "api", f"repos/{REPOSITORY}/commits/{head_sha}/check-runs?per_page=100&filter=latest",
    ], runner)
    runs = value.get("check_runs") if isinstance(value, dict) else None
    total_count = value.get("total_count") if isinstance(value, dict) else None
    if type(total_count) is not int or not isinstance(runs, list) or total_count != len(runs):
        raise MergeControllerError("github_response_invalid")
    matching: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, dict):
            raise MergeControllerError("github_response_invalid")
        app = run.get("app")
        app_id = app.get("id") if isinstance(app, dict) else None
        if app_id == REQUIRED_CHECK_APP_ID and type(app_id) is not int:
            raise MergeControllerError("github_response_invalid")
        if run.get("name") != REQUIRED_CHECK or type(app_id) is not int or app_id != REQUIRED_CHECK_APP_ID:
            continue
        run_id = run.get("id")
        status = run.get("status")
        conclusion = run.get("conclusion")
        run_head = run.get("head_sha")
        if (
            type(run_id) is not int
            or run_id < 1
            or status not in {"queued", "in_progress", "completed", "pending"}
            or (conclusion is not None and not isinstance(conclusion, str))
            or not isinstance(run_head, str)
            or not SHA_RE.fullmatch(run_head.lower())
        ):
            raise MergeControllerError("github_response_invalid")
        matching.append(run)
    if not matching:
        raise MergeControllerError("required_checks_not_successful")
    latest = max(matching, key=lambda run: run["id"])
    if (
        latest.get("status") != "completed"
        or latest.get("conclusion") != "success"
        or str(latest.get("head_sha") or "").lower() != head_sha
    ):
        raise MergeControllerError("required_checks_not_successful")


def _merge_exact_head(number: int, head_sha: str, runner: Callable[[list[str]], str]) -> str:
    """Use GitHub's compare-and-swap merge endpoint directly.

    The REST ``sha`` field makes the mutation conditional on the exact head we
    just validated.  This avoids gh's higher-level auto-merge/merge-queue
    negotiation while leaving branch protection enforcement to GitHub.
    """
    value = _json_command([
        "gh", "api", "--method", "PUT",
        f"repos/{REPOSITORY}/pulls/{number}/merge",
        "-f", f"sha={head_sha}", "-f", "merge_method=squash",
    ], runner)
    merge_sha = str(value.get("sha") if isinstance(value, dict) else "").lower()
    message = value.get("message") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("merged") is not True
        or not SHA_RE.fullmatch(merge_sha)
        or not isinstance(message, str)
        or not 1 <= len(message) <= 500
    ):
        raise MergeControllerError("merge_receipt_invalid")
    return merge_sha


def _update_branch_exact(
    number: int, pr: dict[str, Any], head_sha: str, runner: Callable[[list[str]], str],
) -> str:
    value = _json_command([
        "gh", "api", "--method", "PUT",
        f"repos/{REPOSITORY}/pulls/{number}/update-branch",
        "-f", f"expected_head_sha={head_sha}",
    ], runner)
    message = value.get("message") if isinstance(value, dict) else None
    url = value.get("url") if isinstance(value, dict) else None
    if (
        not isinstance(message, str)
        or not 1 <= len(message) <= 500
        or url != f"https://api.github.com/repos/{REPOSITORY}/pulls/{number}"
    ):
        raise MergeControllerError("update_branch_receipt_invalid")
    expected_branch = pr.get("headRefName")
    for attempt in range(10):
        updated = _pr_view(number, runner)
        updated_head, _author, _state = _validate_pr(updated, number)
        if updated.get("headRefName") != expected_branch:
            raise MergeControllerError("update_branch_receipt_invalid")
        if updated_head != head_sha:
            return updated_head
        if attempt < 9:
            time.sleep(1)
    raise MergeControllerError("update_branch_receipt_invalid")


def merge_release_pr(number: int, *, runner: Callable[[list[str]], str] = _run) -> dict[str, Any]:
    if type(number) is not int or not 1 <= number <= 2_147_483_647:
        raise MergeControllerError("release_pr_identity_invalid")
    pr = _pr_view(number, runner)
    head_sha, author_login, merge_state = _validate_pr(pr, number)
    _validate_latest_release_for_slug(pr, runner)
    if merge_state == "BEHIND":
        current = _pr_view(number, runner)
        current_head, _current_author, current_state = _validate_pr(current, number)
        if current_head != head_sha:
            raise MergeControllerError("exact_head_review_required")
        _validate_latest_release_for_slug(current, runner)
        if current_state != "BEHIND":
            raise MergeControllerError("release_pr_not_mergeable")
        updated_head = _update_branch_exact(number, current, head_sha, runner)
        return {
            "status": "updated", "pr_number": number,
            "previous_head_sha": head_sha, "head_sha": updated_head,
        }
    if pr.get("reviewDecision") != "APPROVED":
        raise MergeControllerError("separate_review_required")
    if merge_state != "CLEAN":
        raise MergeControllerError("release_pr_not_mergeable")
    _validate_separate_review(_review_pages(number, runner), head_sha=head_sha, author_login=author_login)
    _validate_required_check(head_sha, runner)
    current = _pr_view(number, runner)
    current_head, current_author, current_state = _validate_pr(current, number)
    if current_head != head_sha or current_author != author_login:
        raise MergeControllerError("exact_head_review_required")
    _validate_latest_release_for_slug(current, runner)
    if current.get("reviewDecision") != "APPROVED":
        raise MergeControllerError("separate_review_required")
    if current_state != "CLEAN":
        raise MergeControllerError("release_pr_not_mergeable")
    api_merge_sha = _merge_exact_head(number, head_sha, runner)
    merged = _pr_view(number, runner)
    commit = merged.get("mergeCommit")
    merge_sha = str(commit.get("oid") if isinstance(commit, dict) else "").lower()
    if (
        merged.get("state") != "MERGED"
        or str(merged.get("headRefOid") or "").lower() != head_sha
        or not SHA_RE.fullmatch(merge_sha)
        or merge_sha != api_merge_sha
    ):
        raise MergeControllerError("merge_receipt_invalid")
    return {"status": "merged", "pr_number": number, "head_sha": head_sha, "merge_sha": merge_sha}


def run(event_path: Path, *, runner: Callable[[list[str]], str] = _run) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for number in candidate_pr_numbers(event_path, runner=runner):
        try:
            results.append(merge_release_pr(number, runner=runner))
        except MergeControllerError as error:
            status = "waiting" if error.code in {
                "separate_review_required",
                "exact_head_review_required",
                "required_checks_not_successful",
                "release_pr_not_mergeable",
                "superseded_release_pr",
            } else "blocked"
            results.append({"status": status, "pr_number": number, "reason": error.code})
    return {"status": "complete", "results": results}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    args = parser.parse_args(argv)
    try:
        result = run(Path(args.event))
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
        return 1 if any(item.get("status") == "blocked" for item in result.get("results", [])) else 0
    except MergeControllerError as error:
        print(json.dumps({"error": error.code}, separators=(",", ":"), sort_keys=True))
        return 1
    except Exception:
        print('{"error":"merge_controller_failed"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
