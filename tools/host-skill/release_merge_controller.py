#!/usr/bin/env python3
"""Merge only server-derived Omo release PRs after protected, separate review.

The event is only a candidate hint. Repository, base, branch pattern, author,
reviewers, required checks, and exact head are fetched again from GitHub.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Sequence

REPOSITORY = "harrythentrepreneur/Omo.Space"
BASE = "main"
REQUIRED_CHECKS = ("contracts",)
TRUSTED_RELEASE_AUTHORS = frozenset({"harrythentrepreneur"})
TRUSTED_REVIEW_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BRANCH_RE = re.compile(
    r"^omo-release/sub_[A-Za-z0-9_-]{8,100}-[a-z0-9]+(?:-[a-z0-9]+)*$"
)
MAX_EVENT_BYTES = 1024 * 1024
MAX_CANDIDATES = 100


class MergeControllerError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _run(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command, shell=False, check=False, capture_output=True, text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise MergeControllerError("github_command_failed") from None
    if result.returncode != 0 or len(result.stdout.encode("utf-8")) > MAX_EVENT_BYTES:
        raise MergeControllerError("github_command_failed")
    return result.stdout


def _json_command(command: list[str], runner: Callable[[list[str]], str]) -> Any:
    try:
        value = json.loads(runner(command))
    except MergeControllerError:
        raise
    except Exception:
        raise MergeControllerError("github_response_invalid") from None
    return value


def _read_event(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= MAX_EVENT_BYTES:
            raise OSError
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise MergeControllerError("invalid_event") from None
    if not isinstance(value, dict) or (value.get("repository") or {}).get("full_name") != REPOSITORY:
        raise MergeControllerError("invalid_event")
    return value


def candidate_pr_numbers(
    event_path: Path, *, runner: Callable[[list[str]], str] = _run,
) -> list[int]:
    event = _read_event(event_path)
    pull = event.get("pull_request")
    review = event.get("review")
    if event.get("action") == "submitted" and isinstance(pull, dict) and isinstance(review, dict):
        if str(review.get("state") or "").lower() != "approved":
            return []
        number = pull.get("number")
        if type(number) is not int or not 1 <= number <= 2_147_483_647:
            raise MergeControllerError("invalid_event")
        return [number]
    workflow_run = event.get("workflow_run")
    if event.get("action") == "completed" and isinstance(workflow_run, dict):
        if (
            workflow_run.get("name") != "generated-workflow-contracts"
            or workflow_run.get("event") != "pull_request"
            or workflow_run.get("conclusion") != "success"
        ):
            return []
        pulls = workflow_run.get("pull_requests")
        if not isinstance(pulls, list) or len(pulls) != 1 or type(pulls[0].get("number")) is not int:
            raise MergeControllerError("invalid_event")
        return [pulls[0]["number"]]
    if event.get("schedule") == "*/5 * * * *":
        rows = _json_command([
            "gh", "pr", "list", "--repo", REPOSITORY, "--base", BASE,
            "--state", "open", "--limit", str(MAX_CANDIDATES),
            "--json", "number,headRefName",
        ], runner)
        if not isinstance(rows, list) or len(rows) > MAX_CANDIDATES:
            raise MergeControllerError("github_response_invalid")
        numbers = []
        for row in rows:
            if not isinstance(row, dict):
                raise MergeControllerError("github_response_invalid")
            number, branch = row.get("number"), row.get("headRefName")
            if type(number) is int and BRANCH_RE.fullmatch(str(branch or "")):
                numbers.append(number)
        return sorted(set(numbers))
    return []


def _validate_protection(value: Any) -> None:
    if not isinstance(value, dict):
        raise MergeControllerError("branch_protection_inadequate")
    checks = value.get("required_status_checks")
    reviews = value.get("required_pull_request_reviews")
    contexts = checks.get("contexts") if isinstance(checks, dict) else None
    count = reviews.get("required_approving_review_count") if isinstance(reviews, dict) else None
    if (
        not isinstance(checks, dict) or checks.get("strict") is not True
        or not isinstance(contexts, list) or not set(REQUIRED_CHECKS).issubset(set(contexts))
        or not isinstance(reviews, dict) or type(count) is not int or count < 1
        or reviews.get("dismiss_stale_reviews") is not True
    ):
        raise MergeControllerError("branch_protection_inadequate")


def _pr_view(number: int, runner: Callable[[list[str]], str]) -> dict[str, Any]:
    value = _json_command([
        "gh", "pr", "view", str(number), "--repo", REPOSITORY,
        "--json",
        "number,state,isDraft,baseRefName,headRefName,headRefOid,headRepository,author,reviewDecision,mergeStateStatus,statusCheckRollup,mergeCommit",
    ], runner)
    if not isinstance(value, dict):
        raise MergeControllerError("github_response_invalid")
    return value


def _validate_pr(pr: dict[str, Any], number: int) -> tuple[str, str]:
    author = pr.get("author")
    head_repo = pr.get("headRepository")
    head_sha = str(pr.get("headRefOid") or "").lower()
    author_login = str(author.get("login") if isinstance(author, dict) else "")
    repo_name = str(head_repo.get("nameWithOwner") if isinstance(head_repo, dict) else "")
    if (
        pr.get("number") != number or pr.get("state") != "OPEN" or pr.get("isDraft") is not False
        or pr.get("baseRefName") != BASE or not BRANCH_RE.fullmatch(str(pr.get("headRefName") or ""))
        or not SHA_RE.fullmatch(head_sha) or repo_name != REPOSITORY
        or author_login not in TRUSTED_RELEASE_AUTHORS
    ):
        raise MergeControllerError("release_pr_identity_invalid")
    if pr.get("reviewDecision") != "APPROVED":
        raise MergeControllerError("separate_review_required")
    if pr.get("mergeStateStatus") != "CLEAN":
        raise MergeControllerError("release_pr_not_mergeable")
    successful = {
        str(check.get("name") or check.get("context") or "")
        for check in pr.get("statusCheckRollup", [])
        if isinstance(check, dict) and str(check.get("conclusion") or "").upper() == "SUCCESS"
    }
    if not set(REQUIRED_CHECKS).issubset(successful):
        raise MergeControllerError("required_checks_not_successful")
    return head_sha, author_login


def _validate_separate_review(
    reviews: Any, *, head_sha: str, author_login: str,
) -> None:
    if not isinstance(reviews, list) or len(reviews) > 1000:
        raise MergeControllerError("github_response_invalid")
    latest: dict[str, dict[str, Any]] = {}
    for review in reviews:
        user = review.get("user") if isinstance(review, dict) else None
        login = str(user.get("login") if isinstance(user, dict) else "")
        if login:
            previous = latest.get(login)
            if previous is None or int(review.get("id") or 0) > int(previous.get("id") or 0):
                latest[login] = review
    separate = [
        review for login, review in latest.items()
        if login != author_login
        and isinstance(review.get("user"), dict)
        and review["user"].get("type") == "User"
        and review.get("author_association") in TRUSTED_REVIEW_ASSOCIATIONS
    ]
    if not separate:
        raise MergeControllerError("separate_review_required")
    if not any(
        review.get("state") == "APPROVED"
        and str(review.get("commit_id") or "").lower() == head_sha
        for review in separate
    ):
        raise MergeControllerError("exact_head_review_required")


def merge_release_pr(
    number: int, *, runner: Callable[[list[str]], str] = _run,
) -> dict[str, Any]:
    if type(number) is not int or not 1 <= number <= 2_147_483_647:
        raise MergeControllerError("release_pr_identity_invalid")
    protection = _json_command([
        "gh", "api", f"repos/{REPOSITORY}/branches/{BASE}/protection",
    ], runner)
    _validate_protection(protection)
    pr = _pr_view(number, runner)
    head_sha, author_login = _validate_pr(pr, number)
    reviews = _json_command([
        "gh", "api", f"repos/{REPOSITORY}/pulls/{number}/reviews",
    ], runner)
    _validate_separate_review(reviews, head_sha=head_sha, author_login=author_login)
    runner([
        "gh", "pr", "merge", str(number), "--repo", REPOSITORY,
        "--merge", "--match-head-commit", head_sha,
    ])
    merged = _pr_view(number, runner)
    commit = merged.get("mergeCommit")
    merge_sha = str(commit.get("oid") if isinstance(commit, dict) else "").lower()
    if (
        merged.get("state") != "MERGED"
        or str(merged.get("headRefOid") or "").lower() != head_sha
        or not SHA_RE.fullmatch(merge_sha)
    ):
        raise MergeControllerError("merge_receipt_invalid")
    return {"status": "merged", "pr_number": number, "head_sha": head_sha, "merge_sha": merge_sha}


def run(event_path: Path, *, runner: Callable[[list[str]], str] = _run) -> dict[str, Any]:
    results = []
    for number in candidate_pr_numbers(event_path, runner=runner):
        try:
            results.append(merge_release_pr(number, runner=runner))
        except MergeControllerError as error:
            if error.code in {
                "separate_review_required", "exact_head_review_required",
                "required_checks_not_successful", "release_pr_not_mergeable",
            }:
                results.append({"status": "waiting", "pr_number": number, "reason": error.code})
            else:
                raise
    return {"status": "complete", "results": results}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run(Path(args.event)), separators=(",", ":"), sort_keys=True))
        return 0
    except MergeControllerError as error:
        print(json.dumps({"error": error.code}, separators=(",", ":"), sort_keys=True))
        return 1
    except Exception:
        print('{"error":"merge_controller_failed"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
