#!/usr/bin/env python3
"""Merge only trusted Omo release PRs after exact-head separate review."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
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
MAX_DIRTY_RELEASE_FILES = 1000
MAX_DIRTY_RELEASE_BYTES = 64 * 1024 * 1024
SHARED_GENERATED_PATHS = {
    "site/catalog.js",
    "site/deploy/hosted-skills.generated.mjs",
}
CONTRACT_RECHECK_LABEL = "omo-release-recheck"


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


def _git_bytes(
    repo: Path,
    args: list[str],
    *,
    error: str = "release_candidate_integrity_invalid",
    env: dict[str, str] | None = None,
) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            shell=False,
            check=False,
            capture_output=True,
            timeout=120,
            env={**os.environ, **(env or {})},
        )
    except (OSError, subprocess.TimeoutExpired):
        raise MergeControllerError(error) from None
    if result.returncode != 0 or len(result.stdout) > MAX_RESPONSE_BYTES * 64:
        raise MergeControllerError(error)
    return result.stdout


def _git(
    repo: Path,
    *args: str,
    error: str = "release_candidate_integrity_invalid",
    env: dict[str, str] | None = None,
) -> str:
    try:
        return _git_bytes(repo, list(args), error=error, env=env).decode("utf-8").strip()
    except UnicodeDecodeError:
        raise MergeControllerError(error) from None


def _remote_head(repo: Path, ref: str) -> str:
    raw = _git(
        repo, "ls-remote", "--exit-code", "origin", ref,
        error="release_regeneration_failed",
    )
    fields = raw.split()
    if len(fields) != 2 or fields[1] != ref or not SHA_RE.fullmatch(fields[0]):
        raise MergeControllerError("release_regeneration_failed")
    return fields[0]


def _push_dirty_head(
    repo: Path, *, branch: str, old_head: str, new_head: str, main_sha: str,
) -> None:
    try:
        _git(
            repo,
            "push", "origin", f"{new_head}:refs/heads/{branch}",
            f"--force-with-lease=refs/heads/{branch}:{old_head}",
            error="release_push_failed",
        )
    except MergeControllerError as error:
        if error.code != "release_push_failed":
            raise
        if _remote_head(repo, f"refs/heads/{branch}") != old_head:
            raise MergeControllerError("release_branch_moved") from None
        if _remote_head(repo, f"refs/heads/{BASE}") != main_sha:
            raise MergeControllerError("release_main_moved") from None
        raise


def _safe_release_path(path: str, slug: str) -> bool:
    pure = PurePosixPath(path)
    if (
        not path
        or pure.is_absolute()
        or "\\" in path
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
        or any(part in {"", ".", "..", ".git"} for part in pure.parts)
    ):
        return False
    container_prefix = f"containers/{slug}/"
    return path.startswith(container_prefix) or path in {
        f"packages/skill-to-modal/profiles/{slug}.json",
        f"packages/skill-to-modal/profile-authoring-specs/{slug}.json",
        f"site/run-manifests/{slug}.json",
    }


def _raw_diff_records(repo: Path, old: str, new: str) -> list[tuple[str, str, str, str]]:
    raw = _git_bytes(repo, ["diff", "--raw", "-z", "--no-abbrev", old, new])
    fields = raw.split(b"\0")
    records: list[tuple[str, str, str, str]] = []
    index = 0
    try:
        while index < len(fields) and fields[index]:
            header = fields[index].decode("ascii")
            index += 1
            path = fields[index].decode("utf-8")
            index += 1
            header_fields = header.split()
            if len(header_fields) != 5 or not header_fields[0].startswith(":"):
                raise ValueError
            old_mode = header_fields[0][1:]
            new_mode = header_fields[1]
            status = header_fields[4]
            if status.startswith(("R", "C")):
                index += 1
            records.append((status, old_mode, new_mode, path))
    except (IndexError, UnicodeDecodeError, ValueError):
        raise MergeControllerError("release_candidate_integrity_invalid") from None
    return records


def _candidate_blob_manifest(repo: Path, base: str, head: str, slug: str) -> dict[str, tuple[str, bytes]]:
    """Return fixed slug-owned regular blobs after validating the candidate delta."""
    merge_base = _git(repo, "merge-base", base, head)
    if not SHA_RE.fullmatch(merge_base):
        raise MergeControllerError("release_candidate_integrity_invalid")
    changed: set[str] = set()
    for status, old_mode, new_mode, path in _raw_diff_records(repo, merge_base, head):
        if (
            status not in {"A", "M"}
            or (status == "M" and old_mode != new_mode)
            or new_mode != "100644"
            or not (_safe_release_path(path, slug) or path in SHARED_GENERATED_PATHS)
        ):
            raise MergeControllerError("release_candidate_integrity_invalid")
        changed.add(path)
    if not SHARED_GENERATED_PATHS.issubset(changed):
        raise MergeControllerError("release_candidate_integrity_invalid")
    if not any(_safe_release_path(path, slug) for path in changed):
        raise MergeControllerError("release_candidate_integrity_invalid")

    fixed_paths = [
        f"containers/{slug}",
        f"packages/skill-to-modal/profiles/{slug}.json",
        f"packages/skill-to-modal/profile-authoring-specs/{slug}.json",
        f"site/run-manifests/{slug}.json",
    ]
    listing = _git_bytes(repo, ["ls-tree", "-r", "-z", head, "--", *fixed_paths])
    manifest: dict[str, tuple[str, bytes]] = {}
    total_bytes = 0
    try:
        for record in listing.split(b"\0"):
            if not record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            mode, kind, blob_sha = metadata.decode("ascii").split()
            path = raw_path.decode("utf-8")
            if mode != "100644" or kind != "blob" or not SHA_RE.fullmatch(blob_sha) or not _safe_release_path(path, slug):
                raise ValueError
            content = _git_bytes(repo, ["cat-file", "blob", blob_sha])
            total_bytes += len(content)
            if path in manifest or len(manifest) >= MAX_DIRTY_RELEASE_FILES or total_bytes > MAX_DIRTY_RELEASE_BYTES:
                raise ValueError
            manifest[path] = (blob_sha, content)
    except (UnicodeDecodeError, ValueError):
        raise MergeControllerError("release_candidate_integrity_invalid") from None

    required = {
        f"containers/{slug}/manifest.json",
        f"containers/{slug}/hosted-profile.json",
        f"packages/skill-to-modal/profiles/{slug}.json",
        f"packages/skill-to-modal/profile-authoring-specs/{slug}.json",
        f"site/run-manifests/{slug}.json",
    }
    if not required.issubset(manifest):
        raise MergeControllerError("release_candidate_integrity_invalid")
    return manifest


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
        "number,state,isDraft,baseRefName,headRefName,headRefOid,headRepository,author,reviewDecision,mergeStateStatus,mergeCommit,labels",
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


def _worktree_status_paths(worktree: Path) -> set[str]:
    fields = _git_bytes(worktree, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]).split(b"\0")
    paths: set[str] = set()
    index = 0
    try:
        while index < len(fields) and fields[index]:
            record = fields[index]
            index += 1
            if len(record) < 4 or record[2:3] != b" ":
                raise ValueError
            status = record[:2].decode("ascii")
            path = record[3:].decode("utf-8")
            if "R" in status or "C" in status:
                index += 1
            paths.add(path)
    except (IndexError, UnicodeDecodeError, ValueError):
        raise MergeControllerError("release_regeneration_failed") from None
    return paths


def _validated_label_names(value: Any) -> set[str]:
    if not isinstance(value, list) or len(value) > 100:
        raise MergeControllerError("github_response_invalid")
    names: set[str] = set()
    for item in value:
        name = item.get("name") if isinstance(item, dict) else None
        if not isinstance(name, str) or not 1 <= len(name) <= 100:
            raise MergeControllerError("github_response_invalid")
        names.add(name)
    return names


def _trigger_contracts_recheck(
    number: int, pr: dict[str, Any], head_sha: str,
    runner: Callable[[list[str]], str],
) -> None:
    labels = _validated_label_names(pr.get("labels"))
    endpoint = f"repos/{REPOSITORY}/issues/{number}/labels"
    if CONTRACT_RECHECK_LABEL in labels:
        remaining = _json_command([
            "gh", "api", "--method", "DELETE",
            f"{endpoint}/{CONTRACT_RECHECK_LABEL}",
        ], runner)
        if CONTRACT_RECHECK_LABEL in _validated_label_names(remaining):
            raise MergeControllerError("contracts_recheck_failed")
    applied = _json_command([
        "gh", "api", "--method", "POST", endpoint,
        "-f", f"labels[]={CONTRACT_RECHECK_LABEL}",
    ], runner)
    if CONTRACT_RECHECK_LABEL not in _validated_label_names(applied):
        raise MergeControllerError("contracts_recheck_failed")
    refreshed = _pr_view(number, runner)
    refreshed_head, _author, _state = _validate_pr(refreshed, number)
    if refreshed_head != head_sha or refreshed.get("headRefName") != pr.get("headRefName"):
        raise MergeControllerError("release_branch_moved")
    if CONTRACT_RECHECK_LABEL not in _validated_label_names(refreshed.get("labels")):
        raise MergeControllerError("contracts_recheck_failed")


def _run_trusted_registration(worktree: Path) -> None:
    script = (
        "import importlib.util, pathlib, sys\n"
        "root = pathlib.Path(sys.argv[1]).resolve(strict=True)\n"
        "path = root / 'tools/host-skill/host.py'\n"
        "spec = importlib.util.spec_from_file_location('trusted_release_host', path)\n"
        "assert spec is not None and spec.loader is not None\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "drift = module.refresh_cumulative_registration(root, check=False)\n"
        "assert drift == []\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", script, str(worktree)],
            shell=False,
            check=False,
            capture_output=True,
            timeout=120,
            cwd=worktree,
            env={**os.environ, "PYTHONPATH": ""},
        )
    except (OSError, subprocess.TimeoutExpired):
        raise MergeControllerError("release_regeneration_failed") from None
    if result.returncode != 0 or len(result.stdout) + len(result.stderr) > MAX_RESPONSE_BYTES:
        raise MergeControllerError("release_regeneration_failed")


def _regenerate_dirty_release(
    number: int,
    pr: dict[str, Any],
    old_head: str,
    gh_runner: Callable[[list[str]], str],
    repo_root: Path,
) -> str:
    branch = str(pr.get("headRefName") or "")
    branch_match = BRANCH_RE.fullmatch(branch)
    if branch_match is None:
        raise MergeControllerError("release_pr_identity_invalid")
    slug = branch_match.group("slug")
    repo = repo_root.resolve(strict=True)
    main_ref = "refs/reconcile-release/main"
    candidate_ref = "refs/reconcile-release/candidate"
    _git(
        repo,
        "fetch", "--no-tags", "origin",
        f"+refs/heads/{BASE}:{main_ref}",
        f"+refs/heads/{branch}:{candidate_ref}",
        error="release_regeneration_failed",
    )
    main_sha = _git(repo, "rev-parse", "--verify", main_ref)
    fetched_head = _git(repo, "rev-parse", "--verify", candidate_ref)
    if not SHA_RE.fullmatch(main_sha) or fetched_head != old_head:
        raise MergeControllerError("release_branch_moved")
    manifest = _candidate_blob_manifest(repo, main_sha, old_head, slug)
    allowed_paths = set(manifest) | SHARED_GENERATED_PATHS

    reconciliation_head = ""
    new_head = ""
    with tempfile.TemporaryDirectory(prefix="omo-release-reconcile-") as temporary:
        worktree = Path(temporary) / "tree"
        _git(repo, "worktree", "add", "--detach", str(worktree), main_sha, error="release_regeneration_failed")
        try:
            container = worktree / "containers" / slug
            if container.is_symlink():
                container.unlink()
            elif container.exists():
                if not container.is_dir():
                    raise MergeControllerError("release_regeneration_failed")
                shutil.rmtree(container)
            for path, (_blob_sha, content) in manifest.items():
                target = worktree / path
                target.parent.mkdir(parents=True, exist_ok=True)
                resolved_parent = target.parent.resolve()
                if worktree != resolved_parent and worktree not in resolved_parent.parents:
                    raise MergeControllerError("release_regeneration_failed")
                if target.exists() or target.is_symlink():
                    if not target.is_file() or target.is_symlink():
                        raise MergeControllerError("release_regeneration_failed")
                    target.unlink()
                target.write_bytes(content)
                target.chmod(0o644)

            _run_trusted_registration(worktree)
            for path, (blob_sha, _content) in manifest.items():
                if _git(worktree, "hash-object", "--", path) != blob_sha:
                    raise MergeControllerError("release_regeneration_failed")
            status_paths = _worktree_status_paths(worktree)
            if not status_paths or not status_paths.issubset(allowed_paths):
                raise MergeControllerError("release_regeneration_failed")
            _git(worktree, "add", "--all", "--", *sorted(allowed_paths), error="release_regeneration_failed")
            tree_sha = _git(worktree, "write-tree", error="release_regeneration_failed")
            identity = {
                "GIT_AUTHOR_NAME": "Omo Trusted Release Controller",
                "GIT_AUTHOR_EMAIL": "actions@users.noreply.github.com",
                "GIT_COMMITTER_NAME": "Omo Trusted Release Controller",
                "GIT_COMMITTER_EMAIL": "actions@users.noreply.github.com",
            }
            reconciliation_head = _git(
                worktree,
                "commit-tree", tree_sha,
                "-p", main_sha,
                "-p", old_head,
                "-m", f"Regenerate generated release {slug} on current main",
                error="release_regeneration_failed",
                env=identity,
            )
            new_head = _git(
                worktree,
                "commit-tree", tree_sha,
                "-p", reconciliation_head,
                "-m", f"Seal regenerated release {slug}",
                error="release_regeneration_failed",
                env=identity,
            )
        finally:
            _git(repo, "worktree", "remove", "--force", str(worktree), error="release_regeneration_failed")

    if not SHA_RE.fullmatch(reconciliation_head) or not SHA_RE.fullmatch(new_head):
        raise MergeControllerError("release_regeneration_failed")
    if _git(repo, "show", "-s", "--format=%P", new_head).split() != [reconciliation_head]:
        raise MergeControllerError("release_regeneration_failed")
    if _git(repo, "show", "-s", "--format=%P", reconciliation_head).split() != [main_sha, old_head]:
        raise MergeControllerError("release_regeneration_failed")
    if _git(repo, "rev-parse", f"{new_head}^{{tree}}") != _git(
        repo, "rev-parse", f"{reconciliation_head}^{{tree}}"
    ):
        raise MergeControllerError("release_regeneration_failed")
    for ancestor in (main_sha, old_head):
        _git(repo, "merge-base", "--is-ancestor", ancestor, new_head, error="release_regeneration_failed")
    result_records = _raw_diff_records(repo, main_sha, new_head)
    result_paths: set[str] = set()
    for status, old_mode, new_mode, path in result_records:
        if (
            status not in {"A", "M"}
            or (status == "M" and old_mode != new_mode)
            or new_mode != "100644"
            or path not in allowed_paths
        ):
            raise MergeControllerError("release_regeneration_failed")
        result_paths.add(path)
    if not result_paths or not result_paths.issubset(allowed_paths):
        raise MergeControllerError("release_regeneration_failed")

    _git(
        repo, "fetch", "--no-tags", "origin", f"+refs/heads/{BASE}:{main_ref}",
        error="release_regeneration_failed",
    )
    if _git(repo, "rev-parse", "--verify", main_ref) != main_sha:
        raise MergeControllerError("release_main_moved")
    _push_dirty_head(
        repo, branch=branch, old_head=old_head, new_head=new_head, main_sha=main_sha,
    )
    _git(
        repo,
        "fetch", "--no-tags", "origin",
        f"+refs/heads/{branch}:{candidate_ref}",
        f"+refs/heads/{BASE}:{main_ref}",
        error="release_regeneration_failed",
    )
    if _git(repo, "rev-parse", "--verify", candidate_ref) != new_head:
        raise MergeControllerError("release_branch_moved")
    if _git(repo, "rev-parse", "--verify", main_ref) != main_sha:
        raise MergeControllerError("release_main_moved")

    for attempt in range(10):
        updated = _pr_view(number, gh_runner)
        updated_head, _author, _state = _validate_pr(updated, number)
        if updated.get("headRefName") != branch:
            raise MergeControllerError("release_branch_moved")
        if updated_head == new_head:
            _validate_latest_release_for_slug(updated, gh_runner)
            _trigger_contracts_recheck(number, updated, new_head, gh_runner)
            return new_head
        if updated_head != old_head:
            raise MergeControllerError("release_branch_moved")
        if attempt < 9:
            time.sleep(1)
    raise MergeControllerError("release_branch_moved")


def merge_release_pr(
    number: int,
    *,
    runner: Callable[[list[str]], str] = _run,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    if type(number) is not int or not 1 <= number <= 2_147_483_647:
        raise MergeControllerError("release_pr_identity_invalid")
    pr = _pr_view(number, runner)
    head_sha, author_login, merge_state = _validate_pr(pr, number)
    _validate_latest_release_for_slug(pr, runner)
    if merge_state == "UNKNOWN":
        for _attempt in range(10):
            time.sleep(1)
            current = _pr_view(number, runner)
            current_head, current_author, current_state = _validate_pr(current, number)
            if current_head != head_sha or current_author != author_login:
                raise MergeControllerError("exact_head_review_required")
            _validate_latest_release_for_slug(current, runner)
            if current_state != "UNKNOWN":
                pr = current
                merge_state = current_state
                break
        else:
            raise MergeControllerError("release_pr_not_mergeable")
    if merge_state in {"BEHIND", "DIRTY"}:
        current = _pr_view(number, runner)
        current_head, current_author, current_state = _validate_pr(current, number)
        if current_head != head_sha or current_author != author_login:
            raise MergeControllerError("exact_head_review_required")
        _validate_latest_release_for_slug(current, runner)
        if current_state != merge_state:
            raise MergeControllerError("release_pr_not_mergeable")
        regenerated_head = _regenerate_dirty_release(
            number,
            current,
            head_sha,
            runner,
            repo_root or Path(__file__).resolve().parents[2],
        )
        return {
            "status": "regenerated", "pr_number": number,
            "previous_head_sha": head_sha, "head_sha": regenerated_head,
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
                "release_branch_moved",
                "release_main_moved",
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
