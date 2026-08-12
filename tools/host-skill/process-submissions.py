#!/usr/bin/env python3
"""Claim and process Omo's queued creator workflow submissions.

Default mode is deliberately non-deploying: it validates one claimed item and
runs the compile/test/price gate only when a trusted profile already exists.
`--deploy` additionally deploys Modal, runs a direct canary, registers the
listing, verifies the Worker suites, and deploys the Worker.  Publishing the
commit and the final Omo billing canary remain explicit agent actions; use
`--mark-deployed` only after those production checks succeed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

from submission_queue import (
    ROOT,
    SubmissionValidationError,
    evaluate_review_gate,
    safe_failure_code,
    validate_submission,
    validate_submission_id,
)


HOST_PATH = ROOT / "tools" / "host-skill" / "host.py"
WORKER_ROOT = ROOT / "site" / "deploy"
def output(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


class SubmissionRepository:
    """Small Postgres queue adapter; psycopg2 is loaded only for live runs."""

    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("NEON_DATABASE_URL is required")
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError as error:
            raise RuntimeError("Install psycopg2 to process the Neon queue") from error
        self._extras = psycopg2.extras
        self.connection = psycopg2.connect(database_url)

    def close(self) -> None:
        self.connection.close()

    def claim(
        self, submission_id: str | None = None, include_review: bool = False, include_ready: bool = False
    ) -> dict[str, Any] | None:
        claim_states = ("queued",)
        if include_review:
            claim_states += ("needs_review",)
        if include_ready:
            claim_states += ("ready_for_deploy",)
        state_placeholders = ", ".join(["%s"] * len(claim_states))
        where_id = "AND id = %s" if submission_id else ""
        params: list[Any] = list(claim_states)
        if submission_id:
            params.append(submission_id)
        query = f"""
            WITH candidate AS (
              SELECT id, status AS prior_status FROM submissions
              WHERE status IN ({state_placeholders}) {where_id}
              ORDER BY created_at ASC
              FOR UPDATE SKIP LOCKED
              LIMIT 1
            )
            UPDATE submissions AS submission
            SET status = 'processing', failure_code = NULL, updated_at = CURRENT_TIMESTAMP
            FROM candidate
            WHERE submission.id = candidate.id
            RETURNING submission.*, candidate.prior_status
        """
        with self.connection:
            with self.connection.cursor(cursor_factory=self._extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone()
        return dict(row) if row else None

    def set_status(self, submission_id: str, status: str, failure_code: str | None = None) -> None:
        deployed = ", deployed_at = CURRENT_TIMESTAMP" if status == "deployed" else ""
        with self.connection:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE submissions SET status = %s, failure_code = %s, updated_at = CURRENT_TIMESTAMP{deployed} WHERE id = %s",
                    (status, safe_failure_code(failure_code) if failure_code else None, submission_id),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("submission disappeared while its status was being updated")

    def get(self, submission_id: str) -> dict[str, Any] | None:
        with self.connection.cursor(cursor_factory=self._extras.RealDictCursor) as cursor:
            cursor.execute(
                "SELECT id,user_id,name,slug,content,source_sha256,status,created_at,updated_at FROM submissions WHERE id = %s",
                (submission_id,),
            )
            row = cursor.fetchone()
        return dict(row) if row else None

    def mark_deployed(self, submission_id: str) -> None:
        with self.connection:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE submissions SET status = 'deployed', failure_code = NULL, updated_at = CURRENT_TIMESTAMP, deployed_at = CURRENT_TIMESTAMP WHERE id = %s AND status = 'ready_for_publish'",
                    (submission_id,),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("submission must be ready_for_publish before it can be marked deployed")


def run_checked(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def host_command(skill_path: Path, slug: str, register: bool = False, check: bool = False) -> list[str]:
    command = [
        sys.executable,
        str(HOST_PATH),
        str(skill_path),
        "--profile",
        str(ROOT / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json"),
        "--out",
        str(ROOT / "containers" / slug),
    ]
    if register:
        command.append("--register")
    if check:
        command.append("--check")
    return command


def direct_modal_canary(slug: str, timeout_seconds: int = 240) -> None:
    profile = json.loads(
        (ROOT / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json").read_text(encoding="utf-8")
    )
    endpoint = str(profile["marketplace"]["deployment"]["default_endpoint"]).rstrip("/")
    token_id = os.environ.get("HOSTED_MODAL_PROXY_TOKEN_ID") or os.environ.get("WOVEN_MODAL_PROXY_TOKEN_ID")
    token_secret = os.environ.get("HOSTED_MODAL_PROXY_TOKEN_SECRET") or os.environ.get("WOVEN_MODAL_PROXY_TOKEN_SECRET")
    if not token_id or not token_secret:
        raise RuntimeError("Modal Proxy Token environment variables are required for the canary")
    headers = {
        "Content-Type": "application/json",
        "Modal-Key": token_id,
        "Modal-Secret": token_secret,
    }
    request = urllib.request.Request(
        endpoint + "/v1/runs",
        data=json.dumps(profile["happy_path"]["input"], ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 202:
            raise RuntimeError("Modal canary submit did not return 202")
        accepted = json.load(response)
    result_url = str(accepted.get("result_url") or "")
    if not result_url.startswith("/v1/runs/"):
        raise RuntimeError("Modal canary returned an invalid result URL")

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        poll = urllib.request.Request(endpoint + result_url, headers=headers)
        try:
            with urllib.request.urlopen(poll, timeout=30) as response:
                body = json.load(response)
                if response.status == 200:
                    from jsonschema import Draft202012Validator

                    Draft202012Validator(profile["output_schema"]).validate(body)
                    return
                if response.status != 202:
                    raise RuntimeError("Modal canary poll returned a non-retryable status")
        except urllib.error.HTTPError as error:
            if error.code != 202:
                raise
        time.sleep(2)
    raise RuntimeError("Modal canary timed out")


def deploy_reviewed_submission(skill_path: Path, slug: str) -> None:
    run_checked([sys.executable, "-m", "modal", "deploy", str(ROOT / "containers" / slug / "modal_app.py")])
    direct_modal_canary(slug)
    run_checked(host_command(skill_path, slug, register=True))
    run_checked(host_command(skill_path, slug, register=True, check=True))
    for script in ("test-workers.mjs", "test-router.mjs", "test-balance.mjs", "test-cost.mjs"):
        run_checked(["node", script], WORKER_ROOT)
    run_checked(["npx", "wrangler", "deploy"], WORKER_ROOT)


def process_row(row: dict[str, Any], repository: SubmissionRepository, deploy: bool) -> dict[str, Any]:
    submission_id = validate_submission_id(row.get("id", ""))
    try:
        validated = validate_submission(row.get("name"), row.get("content"))
    except SubmissionValidationError as error:
        repository.set_status(submission_id, "failed", error.code)
        return {"id": submission_id, "status": "failed", "failure_code": error.code}
    if row.get("source_sha256") != validated.source_sha256 or row.get("slug") != validated.slug:
        repository.set_status(submission_id, "failed", "source_identity_mismatch")
        return {
            "id": submission_id,
            "status": "failed",
            "failure_code": "source_identity_mismatch",
        }

    state, reason = evaluate_review_gate(
        validated, allow_matching_container=row.get("prior_status") == "ready_for_deploy"
    )
    if state != "ready_for_build":
        repository.set_status(submission_id, state, reason)
        return {"id": submission_id, "slug": validated.slug, "status": state, "failure_code": reason}

    try:
        with tempfile.TemporaryDirectory(prefix="omo-submission-") as temp_dir:
            skill_path = Path(temp_dir) / "SKILL.md"
            skill_path.write_text(validated.content, encoding="utf-8")
            run_checked(host_command(skill_path, validated.slug))
            repository.set_status(submission_id, "ready_for_deploy")
            if deploy:
                deploy_reviewed_submission(skill_path, validated.slug)
                repository.set_status(submission_id, "ready_for_publish")
    except subprocess.CalledProcessError:
        repository.set_status(submission_id, "failed", "build_or_deploy_failed")
        return {
            "id": submission_id,
            "slug": validated.slug,
            "status": "failed",
            "failure_code": "build_or_deploy_failed",
        }
    except Exception:
        repository.set_status(submission_id, "failed", "canary_or_internal_failed")
        return {
            "id": submission_id,
            "slug": validated.slug,
            "status": "failed",
            "failure_code": "canary_or_internal_failed",
        }

    return {
        "id": submission_id,
        "slug": validated.slug,
        "status": "ready_for_publish" if deploy else "ready_for_deploy",
    }


def dry_run_sample(path: Path) -> int:
    value = json.loads(path.read_text(encoding="utf-8"))
    validated = validate_submission(value.get("name"), value.get("content"))
    state, reason = evaluate_review_gate(validated)
    result = asdict(validated)
    result.pop("content")
    result.update({"status": state, "failure_code": reason})
    output(result)
    return 0


def export_for_review(repository: SubmissionRepository, submission_id: str, review_dir: Path) -> dict[str, Any]:
    row = repository.get(submission_id)
    if not row:
        raise ValueError("submission not found")
    validated = validate_submission(row.get("name"), row.get("content"))
    target_dir = review_dir.resolve() / submission_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "SKILL.md"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(target, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(validated.content)
    return {
        "id": submission_id,
        "slug": validated.slug,
        "status": row["status"],
        "source_sha256": validated.source_sha256,
        "review_path": str(target),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", help="Claim a specific queued/needs_review submission")
    parser.add_argument("--deploy", action="store_true", help="Run external Modal/Worker deployment gates")
    parser.add_argument("--dry-run", type=Path, metavar="SAMPLE_JSON", help="Validate a sample without DB writes")
    parser.add_argument("--export-review", help="Export one submission to a mode-0600 review file")
    parser.add_argument("--review-dir", type=Path, help="Destination directory used with --export-review")
    parser.add_argument("--mark-deployed", help="Mark ready_for_publish after Git/Vercel and billing canaries pass")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dry_run:
        return dry_run_sample(args.dry_run)
    if args.deploy and not args.id:
        raise ValueError("--deploy requires a reviewed submission --id")

    database_url = os.environ.get("NEON_DATABASE_URL", "").strip()
    repository = SubmissionRepository(database_url)
    try:
        if args.export_review:
            if not args.review_dir:
                raise ValueError("--review-dir is required with --export-review")
            submission_id = validate_submission_id(args.export_review)
            output(export_for_review(repository, submission_id, args.review_dir))
            return 0
        if args.mark_deployed:
            submission_id = validate_submission_id(args.mark_deployed)
            repository.mark_deployed(submission_id)
            output({"id": submission_id, "status": "deployed"})
            return 0
        submission_id = validate_submission_id(args.id) if args.id else None
        row = repository.claim(
            submission_id,
            include_review=bool(submission_id),
            include_ready=args.deploy,
        )
        if not row:
            output({"status": "idle", "message": "No queued submission."})
            return 0
        output(process_row(row, repository, args.deploy))
        return 0
    finally:
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
