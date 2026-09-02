#!/usr/bin/env python3
"""Approve only reproducible exact-head compiler-generated release PRs.

This file is executed from protected ``main``.  The candidate checkout is
untrusted data: this controller never imports it or runs its tests/code.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

REPOSITORY = "harrythentrepreneur/Omo.Space"
BASE = "main"
TRUSTED_RELEASE_AUTHOR = "harrythentrepreneur"
TRUSTED_REVIEWER = "kaviru2"
REQUIRED_CHECK = "contracts"
REQUIRED_CHECK_APP_ID = 15368
ROOT = Path(__file__).resolve().parents[2]
COMPILER_PATH = ROOT / "packages/skill-to-modal/compiler.py"
HOST_PATH = ROOT / "tools/host-skill/host.py"
PROCESS_PATH = ROOT / "tools/host-skill/process-submissions.py"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BRANCH_RE = re.compile(
    r"^omo-release/sub_[A-Za-z0-9_-]{8,100}-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)$"
)
MAX_RESPONSE_BYTES = 1024 * 1024
MAX_CANDIDATES = 100
MAX_CHANGED_PATHS = 10_000
MAX_REVIEWS = 1_000


class ReviewControllerError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _run(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command, shell=False, check=False, capture_output=True, text=True, timeout=180
        )
    except (OSError, subprocess.TimeoutExpired):
        raise ReviewControllerError("command_failed") from None
    if result.returncode != 0 or len(result.stdout.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ReviewControllerError("command_failed")
    return result.stdout


def _json(command: list[str], runner: Callable[[list[str]], str]) -> Any:
    try:
        raw = runner(command)
        if len(raw.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise ValueError
        return json.loads(raw)
    except ReviewControllerError:
        raise
    except Exception:
        raise ReviewControllerError("github_response_invalid") from None


def _read_event(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= MAX_RESPONSE_BYTES:
            raise OSError
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ReviewControllerError("invalid_event") from None
    if not isinstance(value, dict):
        raise ReviewControllerError("invalid_event")
    repository = value.get("repository")
    if not isinstance(repository, dict) or repository.get("full_name") != REPOSITORY:
        raise ReviewControllerError("invalid_event")
    return value


def candidate_pr_numbers(
    event_path: Path, *, api_runner: Callable[[list[str]], str] = _run
) -> list[int]:
    """Return bounded PR-number hints; all metadata is re-fetched during review."""
    event = _read_event(event_path)
    workflow = event.get("workflow_run")
    if event.get("action") == "completed" and isinstance(workflow, dict):
        if (
            workflow.get("name") != "generated-workflow-contracts"
            or workflow.get("event") != "pull_request"
            or workflow.get("conclusion") != "success"
        ):
            raise ReviewControllerError("invalid_event")
        pulls = workflow.get("pull_requests")
        if (
            not isinstance(pulls, list) or len(pulls) != 1
            or not isinstance(pulls[0], dict) or type(pulls[0].get("number")) is not int
        ):
            raise ReviewControllerError("invalid_event")
        number = pulls[0]["number"]
        if not 1 <= number <= 2_147_483_647:
            raise ReviewControllerError("invalid_event")
        return [number]
    if event.get("schedule") == "*/15 * * * *":
        rows = _json([
            "gh", "pr", "list", "--repo", REPOSITORY, "--base", BASE,
            "--state", "open", "--limit", str(MAX_CANDIDATES),
            "--json", "number,headRefName",
        ], api_runner)
        if not isinstance(rows, list) or len(rows) > MAX_CANDIDATES:
            raise ReviewControllerError("github_response_invalid")
        numbers = []
        for row in rows:
            if not isinstance(row, dict):
                raise ReviewControllerError("github_response_invalid")
            number = row.get("number")
            if type(number) is int and 1 <= number <= 2_147_483_647 and BRANCH_RE.fullmatch(
                str(row.get("headRefName") or "")
            ):
                numbers.append(number)
        return sorted(set(numbers))
    raise ReviewControllerError("invalid_event")


def _pr_view(number: int, runner: Callable[[list[str]], str]) -> dict[str, Any]:
    value = _json([
        "gh", "pr", "view", str(number), "--repo", REPOSITORY, "--json",
        "number,state,isDraft,baseRefName,headRefName,headRefOid,headRepository,author,mergeStateStatus",
    ], runner)
    if not isinstance(value, dict):
        raise ReviewControllerError("github_response_invalid")
    return value


def validate_pr(pr: dict[str, Any], number: int, *, checked_out_head: str) -> tuple[str, str]:
    head = str(pr.get("headRefOid") or "").lower()
    branch = str(pr.get("headRefName") or "")
    match = BRANCH_RE.fullmatch(branch)
    author = pr.get("author")
    repository = pr.get("headRepository")
    if (
        type(number) is not int or pr.get("number") != number
        or pr.get("state") != "OPEN" or pr.get("isDraft") is not False
        or pr.get("baseRefName") != BASE or match is None
        or not SHA_RE.fullmatch(head)
        or not isinstance(author, dict) or author.get("login") != TRUSTED_RELEASE_AUTHOR
        or not isinstance(repository, dict) or repository.get("nameWithOwner") != REPOSITORY
    ):
        raise ReviewControllerError("release_pr_identity_invalid")
    if not isinstance(checked_out_head, str) or checked_out_head.lower() != head:
        raise ReviewControllerError("candidate_head_mismatch")
    # Before the required Code Owner approval GitHub reports BLOCKED even when
    # the head is conflict-free and all exact-head checks passed.
    if pr.get("mergeStateStatus") not in {"BLOCKED", "CLEAN"}:
        raise ReviewControllerError("release_pr_not_mergeable")
    return head, match.group("slug")


def validate_required_check(value: Any, head_sha: str) -> None:
    runs = value.get("check_runs") if isinstance(value, dict) else None
    total = value.get("total_count") if isinstance(value, dict) else None
    if type(total) is not int or not isinstance(runs, list) or total != len(runs):
        raise ReviewControllerError("github_response_invalid")
    matches = []
    for run in runs:
        if not isinstance(run, dict):
            raise ReviewControllerError("github_response_invalid")
        app = run.get("app")
        app_id = app.get("id") if isinstance(app, dict) else None
        if run.get("name") == REQUIRED_CHECK and app_id == REQUIRED_CHECK_APP_ID:
            if type(run.get("id")) is not int or type(app_id) is not int:
                raise ReviewControllerError("github_response_invalid")
            matches.append(run)
    if not matches:
        raise ReviewControllerError("required_checks_not_successful")
    latest = max(matches, key=lambda item: item["id"])
    if (
        latest.get("status") != "completed" or latest.get("conclusion") != "success"
        or str(latest.get("head_sha") or "").lower() != head_sha
    ):
        raise ReviewControllerError("required_checks_not_successful")


def _check_value(head_sha: str, runner: Callable[[list[str]], str]) -> Any:
    return _json([
        "gh", "api",
        f"repos/{REPOSITORY}/commits/{head_sha}/check-runs?per_page=100&filter=latest",
    ], runner)


def _safe_relative(path: str) -> bool:
    if not path or "\\" in path or path.startswith("/") or "\x00" in path:
        return False
    parts = path.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


def _required_paths(slug: str) -> set[str]:
    return {
        f"containers/{slug}/source/SKILL.md",
        f"containers/{slug}/manifest.json",
        f"packages/skill-to-modal/profiles/{slug}.json",
        f"packages/skill-to-modal/profile-authoring-specs/{slug}.json",
        f"site/run-manifests/{slug}.json",
        "site/catalog.js",
        "site/deploy/hosted-skills.generated.mjs",
    }


def _derive_candidate_slug(candidate: Path, branch: str) -> str:
    """Resolve the otherwise ambiguous submission-id/slug branch boundary."""
    profile_root = candidate / "packages/skill-to-modal/profiles"
    matches: list[str] = []
    try:
        profiles = list(profile_root.iterdir())
    except OSError:
        raise ReviewControllerError("required_release_files_missing") from None
    for profile in profiles:
        slug = profile.stem if profile.suffix == ".json" else ""
        if not SLUG_RE.fullmatch(slug):
            continue
        prefix = branch.removesuffix("-" + slug)
        submission = prefix.removeprefix("omo-release/")
        if (
            prefix != branch
            and re.fullmatch(r"sub_[A-Za-z0-9_-]{8,100}", submission)
            and all((candidate / path).is_file() for path in _required_paths(slug))
        ):
            matches.append(slug)
    if len(matches) != 1:
        raise ReviewControllerError("required_release_files_missing")
    return matches[0]


def _allowed_path(path: str, slug: str) -> bool:
    return (
        path.startswith(f"containers/{slug}/")
        or path in {
            f"packages/skill-to-modal/profiles/{slug}.json",
            f"packages/skill-to-modal/profile-authoring-specs/{slug}.json",
            f"site/run-manifests/{slug}.json",
            "site/catalog.js",
            "site/deploy/hosted-skills.generated.mjs",
        }
    )


def validate_changed_entries(entries: list[tuple[str, str, str, str]], slug: str) -> None:
    if not SLUG_RE.fullmatch(slug) or not 1 <= len(entries) <= MAX_CHANGED_PATHS:
        raise ReviewControllerError("candidate_paths_invalid")
    seen: set[str] = set()
    for path, change, old_mode, new_mode in entries:
        if not _safe_relative(path) or not _allowed_path(path, slug):
            raise ReviewControllerError("candidate_paths_invalid")
        if path in seen or change not in {"A", "M"}:
            raise ReviewControllerError("candidate_git_entry_unsafe")
        if new_mode != "100644" or old_mode not in {"000000", "100644"}:
            raise ReviewControllerError("candidate_git_entry_unsafe")
        seen.add(path)
    if not _required_paths(slug).issubset(seen):
        raise ReviewControllerError("required_release_files_missing")


def _parse_raw_diff(raw: str) -> list[tuple[str, str, str, str]]:
    fields = raw.split("\x00")
    if fields and fields[-1] == "":
        fields.pop()
    entries: list[tuple[str, str, str, str]] = []
    index = 0
    while index < len(fields):
        metadata = fields[index]
        index += 1
        pieces = metadata.split()
        if len(pieces) != 5 or not pieces[0].startswith(":") or index >= len(fields):
            raise ReviewControllerError("candidate_git_diff_invalid")
        old_mode = pieces[0][1:]
        new_mode = pieces[1]
        change = pieces[4]
        path = fields[index]
        index += 1
        if change.startswith(("R", "C")):
            if index >= len(fields):
                raise ReviewControllerError("candidate_git_diff_invalid")
            index += 1
        entries.append((path, change, old_mode, new_mode))
    return entries


def inspect_candidate(candidate: Path, slug: str, runner: Callable[[list[str]], str] = _run):
    candidate = candidate.resolve(strict=True)
    raw = runner([
        "git", "-C", str(candidate), "diff", "--raw", "--no-renames", "-z",
        f"origin/{BASE}...HEAD",
    ])
    entries = _parse_raw_diff(raw)
    # A separate rename-aware pass ensures renames/copies are rejected explicitly.
    rename_aware = _parse_raw_diff(runner([
        "git", "-C", str(candidate), "diff", "--raw", "-M", "-C", "-z",
        f"origin/{BASE}...HEAD",
    ]))
    if any(item[1].startswith(("R", "C")) for item in rename_aware):
        raise ReviewControllerError("candidate_git_entry_unsafe")
    validate_changed_entries(entries, slug)
    root = candidate.resolve(strict=True)
    for path, _change, _old_mode, _new_mode in entries:
        target = candidate / path
        try:
            mode = target.lstat().st_mode
            if target.is_symlink() or not stat.S_ISREG(mode) or mode & 0o111:
                raise OSError
            if not target.resolve(strict=True).is_relative_to(root):
                raise OSError
        except OSError:
            raise ReviewControllerError("candidate_git_entry_unsafe") from None
    return entries


def _load_protected(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ReviewControllerError("protected_validator_unavailable")
    module = importlib.util.module_from_spec(spec)
    try:
        sys.path.insert(0, str(path.parent))
        spec.loader.exec_module(module)
    except Exception:
        raise ReviewControllerError("protected_validator_unavailable") from None
    finally:
        if sys.path and sys.path[0] == str(path.parent):
            sys.path.pop(0)
    return module


def validate_generated_release(
    candidate: Path,
    slug: str,
    *,
    command_runner: Callable[[list[str]], str] = _run,
    host_module: Any | None = None,
    process_module: Any | None = None,
) -> str:
    """Run only protected-main validators over candidate bytes."""
    candidate = candidate.resolve(strict=True)
    skill = candidate / f"containers/{slug}/source/SKILL.md"
    profile = candidate / f"packages/skill-to-modal/profiles/{slug}.json"
    out = candidate / f"containers/{slug}"
    try:
        command_runner([
            sys.executable, str(COMPILER_PATH), str(skill), "--profile", str(profile),
            "--out", str(out), "--check",
        ])
    except Exception:
        raise ReviewControllerError("compiler_drift") from None
    host = host_module if host_module is not None else _load_protected(HOST_PATH, "omo_release_review_host")
    process = process_module if process_module is not None else _load_protected(
        PROCESS_PATH, "omo_release_review_process"
    )
    try:
        drift = host.refresh_cumulative_registration(candidate, check=True)
    except Exception:
        raise ReviewControllerError("cumulative_registry_invalid") from None
    if drift:
        raise ReviewControllerError("cumulative_registry_drift")
    try:
        artifact_hash = process.hash_release_artifacts(slug, root=candidate)
    except Exception:
        raise ReviewControllerError("release_artifacts_invalid") from None
    if not isinstance(artifact_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", artifact_hash):
        raise ReviewControllerError("release_artifacts_invalid")
    return artifact_hash


def _validate_actor(runner: Callable[[list[str]], str]) -> None:
    user = _json(["gh", "api", "user"], runner)
    if not isinstance(user, dict) or user.get("login") != TRUSTED_REVIEWER:
        raise ReviewControllerError("trusted_reviewer_identity_invalid")


def _validate_approval_readback(number: int, head_sha: str, runner: Callable[[list[str]], str]) -> None:
    pages = _json([
        "gh", "api", "--paginate", "--slurp",
        f"repos/{REPOSITORY}/pulls/{number}/reviews?per_page=100",
    ], runner)
    if not isinstance(pages, list):
        raise ReviewControllerError("approval_receipt_invalid")
    matching = []
    count = 0
    for page in pages:
        if not isinstance(page, list):
            raise ReviewControllerError("approval_receipt_invalid")
        for review in page:
            count += 1
            if count > MAX_REVIEWS or not isinstance(review, dict) or type(review.get("id")) is not int:
                raise ReviewControllerError("approval_receipt_invalid")
            user = review.get("user")
            if isinstance(user, dict) and user.get("login") == TRUSTED_REVIEWER:
                matching.append(review)
    if not matching:
        raise ReviewControllerError("approval_receipt_invalid")
    latest = max(matching, key=lambda item: item["id"])
    user = latest.get("user")
    if (
        latest.get("state") != "APPROVED"
        or str(latest.get("commit_id") or "").lower() != head_sha
        or not isinstance(user, dict) or user.get("login") != TRUSTED_REVIEWER
        or user.get("type") != "User"
    ):
        raise ReviewControllerError("approval_receipt_invalid")


def review_release_pr(
    number: int,
    *,
    candidate: Path,
    checked_out_head: str | None = None,
    api_runner: Callable[[list[str]], str] = _run,
    command_runner: Callable[[list[str]], str] = _run,
    host_module: Any | None = None,
    process_module: Any | None = None,
    inspector: Callable[..., Any] = inspect_candidate,
) -> dict[str, Any]:
    if type(number) is not int or not 1 <= number <= 2_147_483_647:
        raise ReviewControllerError("release_pr_identity_invalid")
    candidate = candidate.resolve(strict=True)
    if checked_out_head is None:
        checked_out_head = command_runner(["git", "-C", str(candidate), "rev-parse", "HEAD"]).strip().lower()
    if not SHA_RE.fullmatch(str(checked_out_head).lower()):
        raise ReviewControllerError("candidate_head_mismatch")
    initial_pr = _pr_view(number, api_runner)
    head_sha, _branch_slug = validate_pr(initial_pr, number, checked_out_head=checked_out_head)
    slug = _derive_candidate_slug(candidate, str(initial_pr.get("headRefName") or ""))
    validate_required_check(_check_value(head_sha, api_runner), head_sha)
    inspector(candidate, slug, command_runner)
    validate_generated_release(
        candidate, slug, command_runner=command_runner,
        host_module=host_module, process_module=process_module,
    )
    _validate_actor(api_runner)
    # The final decision uses fresh PR metadata and fresh latest check-runs.
    refreshed_pr = _pr_view(number, api_runner)
    refreshed_head, _refreshed_branch_slug = validate_pr(
        refreshed_pr, number, checked_out_head=head_sha
    )
    if (
        refreshed_head != head_sha
        or refreshed_pr.get("headRefName") != initial_pr.get("headRefName")
    ):
        raise ReviewControllerError("candidate_head_mismatch")
    validate_required_check(_check_value(head_sha, api_runner), head_sha)
    api_runner([
        "gh", "api", "--method", "POST", f"repos/{REPOSITORY}/pulls/{number}/reviews",
        "-f", f"commit_id={head_sha}",
        "-f", "event=APPROVE",
        "-f", f"body=Protected compiler-generated release validated at {head_sha}.",
    ])
    _validate_approval_readback(number, head_sha, api_runner)
    return {"status": "approved", "pr_number": number, "head_sha": head_sha, "slug": slug}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event")
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--pr", type=int)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--head")
    args = parser.parse_args(argv)
    try:
        if args.discover and args.event and not args.review:
            result = {"candidates": candidate_pr_numbers(Path(args.event))}
        elif args.review and args.pr and args.candidate and args.head and not args.discover:
            result = review_release_pr(
                args.pr, candidate=args.candidate, checked_out_head=args.head.lower()
            )
        else:
            raise ReviewControllerError("invalid_arguments")
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
        return 0
    except ReviewControllerError as error:
        print(json.dumps({"error": error.code}, separators=(",", ":"), sort_keys=True))
        return 1
    except Exception:
        print('{"error":"release_review_controller_failed"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
