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
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

from submission_queue import (
    ROOT,
    MAX_SUBMISSION_BYTES,
    SUBMISSION_ID_RE,
    SubmissionValidationError,
    evaluate_review_gate,
    safe_failure_code,
    validate_submission,
    validate_submission_id,
)


HOST_PATH = ROOT / "tools" / "host-skill" / "host.py"
WORKER_ROOT = ROOT / "site" / "deploy"
HTTP_TIMEOUT_SECONDS = 20
HTTP_MAX_RESPONSE_BYTES = 256 * 1024
DEFAULT_BUILD_WORKER_ORIGINS = {"https://omo.space", "https://www.omo.space"}
SAFE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFE_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_VERSION_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*@[0-9A-Za-z][0-9A-Za-z._:-]{0,79}$")
SAFE_POLICY_RE = re.compile(r"^[a-z][a-z0-9_:-]{2,127}$")
SAFE_RUNTIMES = {"auto", "worker-native", "modal-hosted"}
SAFE_SELECTED_RUNTIMES = {"worker-native", "modal-hosted"}
SAFE_PRIOR_STATUSES = {"queued", "needs_review", "ready_for_deploy"}
SUBMISSION_CLAIM_LEASE_SECONDS = 2 * 60 * 60
HOSTED_PROFILE_GLOB = "*/hosted-profile.json"
RELEASE_PHASES = {
    "compiled",
    "pr_open",
    "ci_passed",
    "merged_verified",
    "promoted",
    "failed",
}
SAFE_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REVIEW_ROOT_ENV = "OMO_BUILD_REVIEW_ROOT"
SAFE_GITHUB_URL_RE = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:issues|pull)/[1-9][0-9]{0,9}$")
EXPECTED_MODAL_WORKSPACE = "omo-space"
GITHUB_RELEASE_REPO = "harrythentrepreneur/Omo.Space"
GITHUB_RELEASE_BASE = "main"
REQUIRED_RELEASE_CHECKS = ("contracts",)
WORKER_REGISTRY_FILENAME = "hosted-skills.generated.mjs"
WORKER_DEPLOY_COMMAND = ("npx", "wrangler@4.123.0", "deploy")
LIVE_WORKER_BASE_URL = "https://cognition-demos.harrythentrepreneurr.workers.dev"
SAFE_FAILURE_STAGES = {
    "trusted_release",
    "trusted_compile",
    "trusted_register",
    "trusted_check",
    "worker_contracts",
    "release_issue_lookup",
    "release_issue_create",
    "release_worktree",
    "release_push",
    "release_pr_lookup",
    "release_pr_create",
    "release_pr_view",
    "release_merge",
    "release_command",
    "modal_deploy",
    "worker_dependencies",
    "worker_deploy",
    "worker_smoke",
}
WORKER_REGISTRY_MISSING_SLUG = "hosted_worker_registry_missing_slug"
WORKER_DEPLOY_FAILED = "hosted_worker_deploy_failed"
WORKER_LIVE_SMOKE_UNRESOLVED = "hosted_worker_registry_unresolved"
WORKER_LIVE_SMOKE_FAILED = "hosted_worker_live_smoke_failed"
WORKER_RELEASE_REMEDIATIONS = {
    WORKER_REGISTRY_MISSING_SLUG: (
        "Regenerate site/deploy/hosted-skills.generated.mjs from the reviewed release "
        "and verify each released slug has exactly one hosted runtime row."
    ),
    WORKER_DEPLOY_FAILED: (
        "Fix the pinned Wrangler deployment error, confirm cognition-demos is the target, "
        "and rerun the release promotion from R1."
    ),
    WORKER_LIVE_SMOKE_UNRESOLVED: (
        "Redeploy cognition-demos from the verified release checkout and rerun /api/run "
        "smoke checks until every released slug resolves in the live registry."
    ),
    WORKER_LIVE_SMOKE_FAILED: (
        "Restore a reachable cognition-demos /api/run endpoint that returns an auth or "
        "validation 4xx for the released slug, then rerun the release promotion from R1."
    ),
}
HOSTED_AUTH_NOT_CONFIGURED = "hosted_modal_auth_not_configured"
HOSTED_AUTH_INVALID = "hosted_modal_auth_invalid"
HOSTED_AUTH_REMEDIATIONS = {
    HOSTED_AUTH_NOT_CONFIGURED: (
        "Configure HOSTED_MODAL_PROXY_TOKEN_ID and HOSTED_MODAL_PROXY_TOKEN_SECRET "
        "for the deploy verifier and as Cloudflare Worker secrets from the same "
        "omo-space Modal Proxy Token pair."
    ),
    HOSTED_AUTH_INVALID: (
        "Create or select a current omo-space Modal Proxy Token, update both "
        "HOSTED_MODAL_PROXY_TOKEN_ID and HOSTED_MODAL_PROXY_TOKEN_SECRET in the "
        "Cloudflare Worker and deploy-verifier environments, then retry verification."
    ),
}

# R4 — open-source publish gate: every FREE released slug publishes its public
# contract (SKILL.md + LICENSE + manifest.json) to github.com/omo-space/skills
# under skills/<slug>/. Download is free (MIT); the paid product stays the
# hosted run on omo.space (research/oss-publish-spec.md, oss/POLICY.md).
OSS_REPO_URL = "https://github.com/omo-space/skills"
OSS_REPO_LOCAL = ROOT / ".." / "oss-publish" / "skills"
OSS_SKILL_REL = "skills/{slug}"
OSS_POLICY_URL = "https://github.com/omo-space/skills/blob/main/POLICY.md"
OSS_PREMIUM_EXCLUSIONS = {
    # The ONE premium exception (oss/POLICY.md): the flagship Phonics Book
    # Maker, whose SKILL.md is sold for $400, must NEVER be published. The
    # founder made woven-relationship-book-maker and everything else free.
    "illustrated-decodable-story-maker",
}
OSS_PUBLISH_REMEDIATIONS = {
    "oss_publish_clone_failed": (
        "R4 could not clone/fetch the omo-space/skills publish checkout. Restore "
        "network and push access to github.com/omo-space/skills, then rerun the "
        "release promotion from R4."
    ),
    "oss_publish_prepare_failed": (
        "R4 could not build the public artifacts (SKILL.md + LICENSE + manifest) "
        "for the released slug. Confirm containers/<slug>/source/SKILL.md, "
        "manifest.json, and pricing-report.json exist in the verified release "
        "tree, then rerun the release promotion from R4."
    ),
    "oss_publish_commit_failed": (
        "R4 could not commit skills/<slug> in the omo-space/skills checkout. "
        "Inspect the checkout state, then rerun the release promotion from R4."
    ),
    "oss_publish_push_failed": (
        "R4 could not push the publish commit to github.com/omo-space/skills main. "
        "Confirm the publisher has push access to the omo-space/skills repo, then "
        "rerun the release promotion from R4."
    ),
}
OSS_POLICY_HEADER = (
    "> **Omo open source.** This `SKILL.md` is published under the MIT License per the\n"
    "> [Omo open-source policy]({policy}). Download and reuse it freely; to run it\n"
    "> without setup, use the hosted run on [omo.space](https://omo.space) — pay per\n"
    "> run, no subscription.\n"
).format(policy=OSS_POLICY_URL)
OSS_PUBLISH_MECHANISM = "R4 oss publish gate (research/oss-publish-spec.md)"
OSS_GIT_IDENTITY = ("Omo OSS Publisher", "oss@omo.space")


class ReleaseBlocker(RuntimeError):
    """Typed, resumable release blocker safe to return as a verdict."""

    def __init__(self, code: str, gate: str, remediation: str):
        self.code = code
        self.gate = gate
        self.remediation = remediation
        super().__init__(code)


class HostedPathBlocker(ReleaseBlocker):
    """Typed, secret-free hosted verification blocker."""

    def __init__(self, code: str):
        if code not in HOSTED_AUTH_REMEDIATIONS:
            raise ValueError("invalid hosted path blocker")
        super().__init__(code, "modal_canary", HOSTED_AUTH_REMEDIATIONS[code])


class WorkerReleaseBlocker(ReleaseBlocker):
    """Typed blocker for the generated-registry, deploy, and live-smoke gates."""

    def __init__(self, code: str, gate: str, slugs: list[str]):
        if code not in WORKER_RELEASE_REMEDIATIONS:
            raise ValueError("invalid worker release blocker")
        self.slugs = tuple(slugs)
        super().__init__(code, gate, WORKER_RELEASE_REMEDIATIONS[code])


class StagedCalledProcessError(subprocess.CalledProcessError):
    """A subprocess failure with a secret-free release gate label."""

    def __init__(self, stage: str, error: subprocess.CalledProcessError):
        if stage not in SAFE_FAILURE_STAGES:
            raise ValueError("invalid failure stage")
        super().__init__(error.returncode, f"<{stage}>", output=None, stderr=None)
        self.stage = stage


class OssPublishBlocker(ReleaseBlocker):
    """Typed, fail-closed blocker for the R4 open-source publish gate."""

    def __init__(self, code: str):
        if code not in OSS_PUBLISH_REMEDIATIONS:
            raise ValueError("invalid oss publish blocker")
        super().__init__(code, "R4", OSS_PUBLISH_REMEDIATIONS[code])


def _load_host_module() -> Any:
    spec = importlib.util.spec_from_file_location("omo_host_skill", HOST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load host-skill runtime classifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HOST_MODULE = _load_host_module()


def output(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def persist_review_source(validated: Any, submission_id: str, environ: dict[str, str] | None = None) -> Path | None:
    """Persist validated untrusted source only when a private review root is configured."""
    configured = str((environ or os.environ).get(REVIEW_ROOT_ENV, "")).strip()
    if not configured:
        return None
    root = Path(configured)
    try:
        root_stat = root.lstat()
    except OSError as error:
        raise RuntimeError("unsafe_review_root") from error
    if (
        not root.is_absolute()
        or root.is_symlink()
        or not root.is_dir()
        or root_stat.st_uid != os.geteuid()
        or (root_stat.st_mode & 0o777) != 0o700
    ):
        raise RuntimeError("unsafe_review_root")

    content = validated.content.encode("utf-8")
    if sha256_bytes(content) != validated.source_sha256:
        raise RuntimeError("source_identity_mismatch")
    target_dir = root / validate_submission_id(submission_id)
    try:
        os.mkdir(target_dir, 0o700)
        os.chmod(target_dir, 0o700)
        target = target_dir / "SKILL.md"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(target, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(target, 0o600)
    except OSError as error:
        raise RuntimeError("review_persistence_failed") from error
    if sha256_bytes(target.read_bytes()) != validated.source_sha256:
        raise RuntimeError("review_persistence_failed")
    return target.resolve(strict=True)


def allowed_worker_origins(environ: dict[str, str]) -> set[str]:
    origins = set(DEFAULT_BUILD_WORKER_ORIGINS)
    for origin in str(environ.get("BUILD_WORKER_ALLOWED_ORIGINS", "")).split(","):
        origin = origin.strip().rstrip("/")
        if origin:
            origins.add(origin)
    return origins


def validate_build_worker_base_url(base_url: str, environ: dict[str, str] | None = None) -> str:
    value = str(base_url or "").strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https":
        raise ValueError("BUILD_WORKER_BASE_URL must use HTTPS")
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in allowed_worker_origins(environ or os.environ):
        raise ValueError("BUILD_WORKER_BASE_URL origin is not allowlisted")
    if parsed.path not in ("", "/"):
        raise ValueError("BUILD_WORKER_BASE_URL must be an origin, not a path")
    return origin


def validate_claim_response(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError("invalid internal claim response")
    row = value.get("submission")
    if not isinstance(row, dict):
        raise RuntimeError("invalid internal claim response")
    required = ("id", "name", "slug", "content", "source_sha256", "requested_runtime", "prior_status")
    if any(key not in row for key in required):
        raise RuntimeError("invalid internal claim response")
    if not SUBMISSION_ID_RE.fullmatch(str(row["id"])):
        raise RuntimeError("invalid internal claim response")
    if not SAFE_SLUG_RE.fullmatch(str(row["slug"])) or len(str(row["slug"])) > 100:
        raise RuntimeError("invalid internal claim response")
    if not SAFE_SHA256_RE.fullmatch(str(row["source_sha256"])):
        raise RuntimeError("invalid internal claim response")
    if str(row["requested_runtime"]) not in SAFE_RUNTIMES or str(row["prior_status"]) not in SAFE_PRIOR_STATUSES | {"processing"}:
        raise RuntimeError("invalid internal claim response")
    content = row["content"]
    if not isinstance(content, str) or not content or len(content.encode("utf-8")) > MAX_SUBMISSION_BYTES:
        raise RuntimeError("invalid internal claim response")
    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "slug": str(row["slug"]),
        "content": content,
        "source_sha256": str(row["source_sha256"]),
        "requested_runtime": str(row["requested_runtime"]),
        "prior_status": str(row["prior_status"]),
    }


def _safe_detail_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) and not isinstance(value, list) else {}


def validate_detail_response(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError("invalid internal detail response")
    row = value.get("submission")
    if not isinstance(row, dict):
        raise RuntimeError("invalid internal detail response")
    forbidden = {"content", "source_content", "user_id", "userId", "approved_by", "approvedBy", "name"}
    if forbidden.intersection(row):
        raise RuntimeError("invalid internal detail response")
    required = ("id", "slug", "source_sha256", "selected_runtime", "status")
    if any(key not in row for key in required):
        raise RuntimeError("invalid internal detail response")
    if not SUBMISSION_ID_RE.fullmatch(str(row["id"])):
        raise RuntimeError("invalid internal detail response")
    if not SAFE_SLUG_RE.fullmatch(str(row["slug"])) or len(str(row["slug"])) > 100:
        raise RuntimeError("invalid internal detail response")
    if not SAFE_SHA256_RE.fullmatch(str(row["source_sha256"])):
        raise RuntimeError("invalid internal detail response")
    selected_runtime = str(row["selected_runtime"] or "")
    if selected_runtime not in SAFE_SELECTED_RUNTIMES:
        raise RuntimeError("invalid internal detail response")
    status = str(row["status"] or "")
    if status not in SAFE_PRIOR_STATUSES | {"ready_for_publish", "deployed", "processing", "failed"}:
        raise RuntimeError("invalid internal detail response")

    detail: dict[str, Any] = {
        "id": str(row["id"]),
        "slug": str(row["slug"]),
        "status": status,
        "source_sha256": str(row["source_sha256"]),
        "selected_runtime": selected_runtime,
    }
    for key in ("workflow_version", "published_slug"):
        text = str(row.get(key) or "").strip()
        if text:
            if key == "workflow_version" and not SAFE_VERSION_RE.fullmatch(text):
                raise RuntimeError("invalid internal detail response")
            if key == "published_slug" and not SAFE_SLUG_RE.fullmatch(text):
                raise RuntimeError("invalid internal detail response")
            detail[key] = text

    build_evidence = _safe_detail_object(row.get("build_evidence"))
    checks = [
        str(item).strip()
        for item in build_evidence.get("checks", [])
        if isinstance(item, str) and SAFE_POLICY_RE.fullmatch(str(item).strip())
    ][:20] if isinstance(build_evidence.get("checks"), list) else []
    if checks:
        detail["build_evidence"] = {"checks": checks}
        if SAFE_SHA256_RE.fullmatch(str(build_evidence.get("source_sha256") or "")):
            detail["build_evidence"]["source_sha256"] = str(build_evidence["source_sha256"])
        generated_at = str(build_evidence.get("generated_at") or "").strip()
        if generated_at and len(generated_at) <= 64:
            detail["build_evidence"]["generated_at"] = generated_at

    release = {
        "release_phase": row.get("release_phase"),
        "issue_url": row.get("release_issue_url"),
        "pr_url": row.get("release_pr_url"),
        "pr_number": row.get("release_pr_number"),
        "branch": row.get("release_branch"),
        "head_sha": row.get("release_head_sha"),
        "merge_sha": row.get("release_merge_sha"),
        "source_sha256": row.get("source_sha256"),
        "artifact_hash": row.get("release_artifact_hash"),
        "modal_app": row.get("modal_app"),
        "modal_url": row.get("modal_url"),
        "canary": row.get("canary_evidence"),
        "promotion_evidence": row.get("promotion_evidence"),
    }
    if row.get("release_phase"):
        normalized = normalize_release_metadata(release, require_promotion_evidence=False)
        detail.update({
            "release_phase": normalized.get("release_phase"),
            "release_issue_url": normalized.get("issue_url"),
            "release_pr_url": normalized.get("pr_url"),
            "release_pr_number": normalized.get("pr_number"),
            "release_branch": normalized.get("branch"),
            "release_head_sha": normalized.get("head_sha"),
            "release_merge_sha": normalized.get("merge_sha"),
            "release_artifact_hash": normalized.get("artifact_hash"),
            "modal_app": normalized.get("modal_app"),
            "modal_url": normalized.get("modal_url"),
        })
        if normalized.get("canary"):
            detail["canary_evidence"] = normalized["canary"]
        if normalized.get("release_gates"):
            detail["promotion_evidence"] = normalized["release_gates"]
    return {key: value for key, value in detail.items() if value is not None}


class HttpSubmissionRepository:
    """Private Worker queue adapter selected by BUILD_WORKER_* environment."""

    def __init__(self, base_url: str, token: str, environ: dict[str, str] | None = None):
        if not token:
            raise ValueError("BUILD_WORKER_TOKEN is required")
        self.base_url = validate_build_worker_base_url(base_url, environ)
        self._token = str(token)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(base_url={self.base_url!r}, token=<redacted>)"

    def close(self) -> None:
        return None

    def _post(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any] | None]:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "OmoBuildWorker/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
                status = int(getattr(response, "status", 0) or 0)
                if status == 204:
                    return status, None
                try:
                    raw = response.read(HTTP_MAX_RESPONSE_BYTES + 1)
                except TypeError:
                    raw = response.read()
        except urllib.error.HTTPError as error:
            if error.code == 204:
                return 204, None
            if error.code == 404:
                return 404, None
            raise RuntimeError(f"build worker request failed with HTTP {error.code}") from error
        except urllib.error.URLError as error:
            raise RuntimeError("build worker request failed") from error
        if len(raw) > HTTP_MAX_RESPONSE_BYTES:
            raise RuntimeError("build worker response too large")
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("build worker returned invalid JSON") from error
        if not isinstance(body, dict):
            raise RuntimeError("build worker returned invalid JSON")
        return status, body

    def claim(
        self, submission_id: str | None = None, include_review: bool = False, include_ready: bool = False
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {}
        if submission_id:
            payload["id"] = validate_submission_id(submission_id)
        if include_review:
            payload["include_review"] = True
        if include_ready:
            payload["include_ready"] = True
        status, body = self._post("/api/internal/submissions/claim", payload)
        if status == 204:
            return None
        if status != 200 or not body or body.get("ok") is not True:
            raise RuntimeError("invalid internal claim response")
        return validate_claim_response(body)

    def set_status(self, submission_id: str, status: str, failure_code: str | None = None) -> None:
        payload: dict[str, Any] = {"status": status}
        if failure_code:
            payload["failure_code"] = safe_failure_code(failure_code)
        response_status, body = self._post(f"/api/internal/submissions/{validate_submission_id(submission_id)}/status", payload)
        if response_status != 200 or not body or body.get("ok") is not True:
            raise RuntimeError("submission status transition was rejected")

    def resume_merged_release(self, submission_id: str, merge_sha: str) -> None:
        normalized_sha = str(merge_sha or "").strip().lower()
        if not SAFE_GIT_SHA_RE.fullmatch(normalized_sha):
            raise ValueError("invalid merge SHA")
        validated_id = validate_submission_id(submission_id)
        response_status, body = self._post(
            f"/api/internal/submissions/{validated_id}/resume-merged-release",
            {"merge_sha": normalized_sha},
        )
        if (
            response_status != 200
            or not body
            or body.get("ok") is not True
            or body.get("id") != validated_id
            or body.get("status") != "ready_for_deploy"
        ):
            raise RuntimeError("merged release recovery was rejected")

    def set_runtime_decision(self, submission_id: str, decision: dict[str, Any]) -> None:
        effective = str(decision.get("effective") or "")
        reason = str(decision.get("reason") or "")
        if effective not in SAFE_SELECTED_RUNTIMES or not SAFE_POLICY_RE.fullmatch(reason):
            raise ValueError("invalid runtime decision")
        payload = {
            "effective": effective,
            "reason": reason,
            "recommended": str(decision.get("recommended") or "") if decision.get("recommended") else None,
            "requested": str(decision.get("requested") or "") if decision.get("requested") else None,
            "compatible": bool(decision.get("compatible")),
        }
        response_status, body = self._post(f"/api/internal/submissions/{validate_submission_id(submission_id)}/runtime", payload)
        if response_status != 200 or not body or body.get("ok") is not True:
            raise RuntimeError("submission runtime transition was rejected")

    def set_deployment_metadata(
        self,
        submission_id: str,
        status: str,
        published_slug: str,
        workflow_version: str,
        build_evidence: dict[str, Any],
    ) -> None:
        if status not in {"ready_for_deploy", "ready_for_publish"}:
            raise ValueError("deployment metadata can only prepare publishable states")
        if not SAFE_SLUG_RE.fullmatch(published_slug) or not SAFE_VERSION_RE.fullmatch(workflow_version):
            raise ValueError("invalid deployment metadata")
        response_status, body = self._post(
            f"/api/internal/submissions/{validate_submission_id(submission_id)}/deployment",
            {
                "status": status,
                "published_slug": published_slug,
                "workflow_version": workflow_version,
                "build_evidence": build_evidence,
            },
        )
        if response_status != 200 or not body or body.get("ok") is not True:
            raise RuntimeError("submission deployment transition was rejected")

    def set_release_metadata(self, submission_id: str, release_metadata: dict[str, Any]) -> None:
        response_status, body = self._post(
            f"/api/internal/submissions/{validate_submission_id(submission_id)}/release",
            normalize_release_metadata(release_metadata),
        )
        if response_status != 200 or not body or body.get("ok") is not True:
            raise RuntimeError("submission release metadata transition was rejected")

    def get(self, submission_id: str) -> dict[str, Any] | None:
        response_status, body = self._post(f"/api/internal/submissions/{validate_submission_id(submission_id)}/detail", {})
        if response_status == 404:
            return None
        if response_status != 200 or not body or body.get("ok") is not True:
            raise RuntimeError("invalid internal detail response")
        return validate_detail_response(body)

    def mark_deployed(self, submission_id: str) -> None:
        response_status, body = self._post(
            f"/api/internal/submissions/{validate_submission_id(submission_id)}/deployed",
            {"deployed_by": "build_worker"},
        )
        if response_status != 200 or not body or body.get("ok") is not True:
            raise RuntimeError("submission deployed transition was rejected")


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
        params: list[Any] = list(claim_states)
        params.append(SUBMISSION_CLAIM_LEASE_SECONDS)
        lease_placeholder = "%s"
        where_id = "AND id = %s" if submission_id else ""
        if submission_id:
            params.append(submission_id)
        query = f"""
            WITH candidate AS (
              SELECT id, status AS prior_status FROM submissions
              WHERE (
                status IN ({state_placeholders})
                OR (
                  status = 'processing'
                  AND build_claimed_at IS NOT NULL
                  AND build_claimed_at ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}'
                  AND build_claimed_at::timestamptz < CURRENT_TIMESTAMP - ({lease_placeholder} * INTERVAL '1 second')
                )
              )
              AND slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'
              AND source_sha256 ~ '^[0-9a-f]{{64}}$'
              AND content IS NOT NULL
              AND octet_length(content) BETWEEN 1 AND {MAX_SUBMISSION_BYTES}
              {where_id}
              ORDER BY created_at ASC
              FOR UPDATE SKIP LOCKED
              LIMIT 1
            )
            UPDATE submissions AS submission
            SET status = 'processing',
                failure_code = NULL,
                build_claimed_at = CURRENT_TIMESTAMP,
                build_attempts = COALESCE(build_attempts, 0) + 1,
                build_evidence = NULL,
                updated_at = CURRENT_TIMESTAMP
            FROM candidate
            WHERE submission.id = candidate.id
            RETURNING submission.id, submission.name, submission.slug, submission.content,
                      submission.source_sha256, submission.requested_runtime, candidate.prior_status
        """
        with self.connection:
            cursor_kwargs = {}
            real_dict_cursor = getattr(self._extras, "RealDictCursor", None)
            if real_dict_cursor is not None:
                cursor_kwargs["cursor_factory"] = real_dict_cursor
            with self.connection.cursor(**cursor_kwargs) as cursor:
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

    def set_runtime_decision(self, submission_id: str, decision: dict[str, Any]) -> None:
        with self.connection:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE submissions
                    SET selected_runtime = %s,
                        runtime_policy = %s,
                        runtime_compatibility = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        decision.get("effective"),
                        decision.get("reason"),
                        json.dumps(
                            {
                                "recommended": decision.get("recommended"),
                                "requested": decision.get("requested"),
                                "compatible": bool(decision.get("compatible")),
                            },
                            sort_keys=True,
                        ),
                        submission_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("submission disappeared while its runtime decision was being updated")

    def set_deployment_metadata(
        self,
        submission_id: str,
        status: str,
        published_slug: str,
        workflow_version: str,
        build_evidence: dict[str, Any],
    ) -> None:
        if status not in {"ready_for_deploy", "ready_for_publish"}:
            raise ValueError("deployment metadata can only prepare publishable states")
        if not published_slug or not workflow_version or not build_evidence:
            raise ValueError("published_slug, workflow_version, and build_evidence are required")
        with self.connection:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE submissions
                    SET status = %s,
                        failure_code = NULL,
                        published_slug = %s,
                        workflow_version = %s,
                        build_evidence = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (
                        status,
                        published_slug,
                        workflow_version,
                        json.dumps(build_evidence, sort_keys=True),
                        submission_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("submission disappeared while deployment metadata was being updated")

    def set_release_metadata(self, submission_id: str, release_metadata: dict[str, Any]) -> None:
        metadata = normalize_release_metadata(release_metadata)
        with self.connection:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE submissions
                    SET release_phase = %s,
                        release_issue_url = %s,
                        release_pr_url = %s,
                        release_pr_number = %s,
                        release_branch = %s,
                        release_head_sha = %s,
                        release_merge_sha = %s,
                        release_artifact_hash = %s,
                        modal_app = %s,
                        modal_url = %s,
                        canary_evidence = %s,
                        promotion_evidence = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                      AND status IN ('ready_for_deploy', 'ready_for_publish')
                    """,
                    (
                        metadata.get("release_phase"),
                        metadata.get("issue_url"),
                        metadata.get("pr_url"),
                        metadata.get("pr_number"),
                        metadata.get("branch"),
                        metadata.get("head_sha"),
                        metadata.get("merge_sha"),
                        metadata.get("artifact_hash"),
                        metadata.get("modal_app"),
                        metadata.get("modal_url"),
                        json.dumps(metadata.get("canary") or {}, sort_keys=True),
                        json.dumps(metadata.get("release_gates") or {}, sort_keys=True),
                        submission_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("submission disappeared while release metadata was being updated")

    def get(self, submission_id: str) -> dict[str, Any] | None:
        with self.connection.cursor(cursor_factory=self._extras.RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT id,user_id,name,slug,content,source_sha256,requested_runtime,selected_runtime,
                       runtime_policy,runtime_compatibility,workflow_version,published_slug,build_evidence,
                       status,release_phase,release_issue_url,release_pr_url,release_pr_number,
                       release_branch,release_head_sha,release_merge_sha,release_artifact_hash,
                       modal_app,modal_url,canary_evidence,promotion_evidence,created_at,updated_at,deployed_at
                FROM submissions WHERE id = %s
                """,
                (submission_id,),
            )
            row = cursor.fetchone()
        return dict(row) if row else None

    def mark_deployed(self, submission_id: str) -> None:
        with self.connection:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE submissions
                    SET status = 'deployed',
                        failure_code = NULL,
                        updated_at = CURRENT_TIMESTAMP,
                        deployed_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                      AND status = 'ready_for_publish'
                      AND published_slug IS NOT NULL
                      AND workflow_version IS NOT NULL
                      AND build_evidence IS NOT NULL
                      AND release_phase = 'promoted'
                      AND finalization_status = 'completed'
                      AND finalization_source_sha256 = source_sha256
                      AND finalization_head_sha = release_head_sha
                      AND finalization_merge_sha = release_merge_sha
                      AND finalization_artifact_hash = release_artifact_hash
                      AND promotion_evidence::jsonb ->> 'status' = 'live'
                      AND promotion_evidence::jsonb -> 'R1' ->> 'status' = 'passed'
                      AND promotion_evidence::jsonb -> 'R2' ->> 'status' = 'passed'
                      AND promotion_evidence::jsonb -> 'R3' ->> 'status' = 'passed'
                      AND promotion_evidence::jsonb -> 'R4' ->> 'status' IN ('published', 'excluded_premium')
                    """,
                    (submission_id,),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("submission must be ready_for_publish with promoted release evidence before it can be marked deployed")


def run_checked(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def run_checked_at_stage(command: list[str], cwd: Path, stage: str) -> None:
    try:
        run_checked(command, cwd)
    except subprocess.CalledProcessError as error:
        raise StagedCalledProcessError(stage, error) from None


def run_capture(command: list[str], cwd: Path | None = None, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        command,
        cwd=cwd or ROOT,
        check=True,
        capture_output=True,
        text=text,
    )
    return completed.stdout


def normalize_release_slugs(slugs: list[str] | tuple[str, ...]) -> list[str]:
    normalized = sorted({str(slug).strip() for slug in slugs})
    if not normalized or any(not SAFE_SLUG_RE.fullmatch(slug) or len(slug) > 100 for slug in normalized):
        raise ValueError("invalid released slugs")
    return normalized


def verify_generated_worker_registry(
    slugs: list[str] | tuple[str, ...],
    worker_root: Path = WORKER_ROOT,
) -> dict[str, Any]:
    """R1: prove every release slug has one build-time hosted runtime row."""
    released_slugs = normalize_release_slugs(slugs)
    registry_path = worker_root / WORKER_REGISTRY_FILENAME
    try:
        source = registry_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise WorkerReleaseBlocker(WORKER_REGISTRY_MISSING_SLUG, "R1", released_slugs) from error
    server_catalog_marker = "export const HOSTED_SERVER_CATALOG_ROWS = ["
    runtime_source, marker, _server_catalog = source.partition(server_catalog_marker)
    if not marker:
        raise WorkerReleaseBlocker(WORKER_REGISTRY_MISSING_SLUG, "R1", released_slugs)
    counts = {
        slug: len(re.findall(rf'(?m)^    "{re.escape(slug)}",$', runtime_source))
        for slug in released_slugs
    }
    if any(count != 1 for count in counts.values()):
        failed = [slug for slug, count in counts.items() if count != 1]
        raise WorkerReleaseBlocker(WORKER_REGISTRY_MISSING_SLUG, "R1", failed)
    return {
        "status": "passed",
        "registry": WORKER_REGISTRY_FILENAME,
        "slug_counts": counts,
    }


def deploy_worker_registry(worker_root: Path = WORKER_ROOT) -> dict[str, Any]:
    """R2: deploy the build-time registry and fail closed on any Wrangler error."""
    try:
        run_checked(list(WORKER_DEPLOY_COMMAND), worker_root)
    except (OSError, subprocess.CalledProcessError) as error:
        raise WorkerReleaseBlocker(WORKER_DEPLOY_FAILED, "R2", []) from error
    return {
        "status": "passed",
        "worker": "cognition-demos",
        "wrangler": "4.123.0",
    }


def smoke_live_worker_registry(
    slugs: list[str] | tuple[str, ...],
    base_url: str = LIVE_WORKER_BASE_URL,
    timeout_seconds: int = HTTP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """R3: prove live /api/run resolves each slug without credentials or spend."""
    released_slugs = normalize_release_slugs(slugs)
    url = str(base_url).strip().rstrip("/") + "/api/run"
    results: dict[str, dict[str, Any]] = {}
    for slug in released_slugs:
        request = urllib.request.Request(
            url,
            data=json.dumps({"slug": slug, "fields": {}}, sort_keys=True).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "OmoReleaseRegistrySmoke/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                status = int(getattr(response, "status", 0) or 0)
                raw = response.read(HTTP_MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:
            status = int(error.code)
            raw = error.read(HTTP_MAX_RESPONSE_BYTES + 1)
        except (OSError, urllib.error.URLError) as error:
            raise WorkerReleaseBlocker(WORKER_LIVE_SMOKE_FAILED, "R3", [slug]) from error
        if len(raw) > HTTP_MAX_RESPONSE_BYTES:
            raise WorkerReleaseBlocker(WORKER_LIVE_SMOKE_FAILED, "R3", [slug])
        body_text = raw.decode("utf-8", errors="replace")
        if "unknown_catalog_slug" in body_text:
            raise WorkerReleaseBlocker(WORKER_LIVE_SMOKE_UNRESOLVED, "R3", [slug])
        if status < 400 or status >= 500:
            raise WorkerReleaseBlocker(WORKER_LIVE_SMOKE_FAILED, "R3", [slug])
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError as error:
            raise WorkerReleaseBlocker(WORKER_LIVE_SMOKE_FAILED, "R3", [slug]) from error
        if not isinstance(body, dict):
            raise WorkerReleaseBlocker(WORKER_LIVE_SMOKE_FAILED, "R3", [slug])
        error_code = str(body.get("error") or "")[:80]
        results[slug] = {"status": status, "error": error_code}
    return {
        "status": "passed",
        "endpoint": url,
        "slugs": results,
    }


def host_command(
    skill_path: Path,
    slug: str,
    profile_path: Path | None = None,
    register: bool = False,
    check: bool = False,
) -> list[str]:
    command = [
        sys.executable,
        str(HOST_PATH),
        str(skill_path),
        "--profile",
        str(profile_path or ROOT / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json"),
        "--out",
        str(ROOT / "containers" / slug),
    ]
    if register:
        command.append("--register")
    if check:
        command.append("--check")
    return command


def direct_modal_canary(slug: str, profile_path: Path, timeout_seconds: int = 240) -> None:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    endpoint = str(profile["marketplace"]["deployment"]["default_endpoint"]).rstrip("/")
    token_id = os.environ.get("HOSTED_MODAL_PROXY_TOKEN_ID") or os.environ.get("WOVEN_MODAL_PROXY_TOKEN_ID")
    token_secret = os.environ.get("HOSTED_MODAL_PROXY_TOKEN_SECRET") or os.environ.get("WOVEN_MODAL_PROXY_TOKEN_SECRET")
    if not token_id or not token_secret:
        raise HostedPathBlocker(HOSTED_AUTH_NOT_CONFIGURED)
    headers = {
        "Content-Type": "application/json",
        "Modal-Key": token_id,
        "Modal-Secret": token_secret,
    }
    if profile.get("skill_owned_resource"):
        headers["X-Omo-Owner-Id"] = "omo-release-canary"
    preflight = urllib.request.Request(endpoint + "/openapi.json", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(preflight, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError("Modal authenticated preflight did not return 200")
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            raise HostedPathBlocker(HOSTED_AUTH_INVALID) from error
        raise
    request = urllib.request.Request(
        endpoint + "/v1/runs",
        data=json.dumps(profile["happy_path"]["input"], ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status not in {200, 202}:
                raise RuntimeError("Modal canary submit did not return 200 or 202")
            accepted = json.load(response)
            if response.status == 200:
                from jsonschema import Draft202012Validator

                Draft202012Validator(profile["output_schema"]).validate(accepted)
                return
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            raise HostedPathBlocker(HOSTED_AUTH_INVALID) from error
        raise
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
            if error.code in {401, 403}:
                raise HostedPathBlocker(HOSTED_AUTH_INVALID) from error
            if error.code != 202:
                raise
        time.sleep(2)
    raise RuntimeError("Modal canary timed out")


def reviewed_runtime_kind_by_source_sha256(container_root: Path = ROOT / "containers") -> dict[str, str]:
    """Return generated, server-reviewed runtime kind keyed by reviewed source SHA."""
    runtime_by_source: dict[str, str] = {}
    for path in sorted(container_root.glob(HOSTED_PROFILE_GLOB)):
        try:
            hosted = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(hosted, dict) or hosted.get("schema_version") != "omo.hosted-profile/v1":
            continue
        runtime = hosted.get("runtime")
        if not isinstance(runtime, dict):
            continue
        source_sha256 = str(runtime.get("reviewed_source_sha256") or "").strip()
        kind = str(runtime.get("kind") or "modal-hosted").strip()
        if not SAFE_SHA256_RE.fullmatch(source_sha256) or kind not in SAFE_SELECTED_RUNTIMES:
            continue
        previous = runtime_by_source.get(source_sha256)
        if previous and previous != kind:
            raise RuntimeError("reviewed source hash has conflicting generated runtime kinds")
        runtime_by_source[source_sha256] = kind
    return runtime_by_source


def runtime_preference_for_reviewed_source(
    requested_runtime: str | None,
    source_sha256: str | None,
    runtime_by_source_sha256: dict[str, str] | None = None,
) -> str | None:
    """Inherit exact-match reviewed runtime only for auto; explicit requests pass through."""
    if requested_runtime not in SAFE_RUNTIMES and requested_runtime is not None:
        return requested_runtime
    if requested_runtime != "auto":
        return requested_runtime
    source = str(source_sha256 or "").strip()
    if not SAFE_SHA256_RE.fullmatch(source):
        return requested_runtime
    runtime_by_source = runtime_by_source_sha256 if runtime_by_source_sha256 is not None else reviewed_runtime_kind_by_source_sha256()
    inherited = runtime_by_source.get(source)
    return inherited if inherited in SAFE_SELECTED_RUNTIMES else requested_runtime


def reviewed_profile_artifact(
    slug: str,
    requested_runtime: str | None,
    temp_dir: Path,
    source_sha256: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    canonical_path = ROOT / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json"
    profile = promote_generated_candidate_for_release(
        json.loads(canonical_path.read_text(encoding="utf-8"))
    )
    effective_request = runtime_preference_for_reviewed_source(requested_runtime, source_sha256)
    if effective_request:
        profile["runtime_preference"] = effective_request
    decision = HOST_MODULE.decide_runtime_placement(profile)
    profile_path = temp_dir / f"{slug}.reviewed-profile.json"
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return profile_path, decision


def promote_generated_candidate_for_release(profile: dict[str, Any]) -> dict[str, Any]:
    promoted = json.loads(json.dumps(profile))
    market = promoted.get("marketplace")
    if not isinstance(market, dict):
        return promoted
    tags = market.get("tags")
    if (
        market.get("maker") == "Submitted skill"
        and isinstance(tags, list)
        and "generated-candidate" in tags
    ):
        market["catalog_managed"] = True
        market["storefront_visible"] = True
    return promoted


def generated_runtime_metadata(slug: str, profile_path: Path, expected_source_sha256: str) -> dict[str, Any]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    out = ROOT / "containers" / slug
    analysis = json.loads((out / "skill-analysis.json").read_text(encoding="utf-8"))
    generated_source_sha256 = str(analysis.get("source", {}).get("sha256") or "")
    if generated_source_sha256 != expected_source_sha256:
        raise RuntimeError("generated_source_hash_mismatch")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    pricing = json.loads((out / "pricing-report.json").read_text(encoding="utf-8"))
    hosted = HOST_MODULE.build_hosted_profile(
        profile,
        manifest,
        pricing,
    )
    decision = dict(hosted["runtime_placement"])
    if hosted["runtime"]["kind"] != decision["effective"]:
        raise RuntimeError("generated registry runtime diverged from reviewed runtime decision")
    workflow_version = f"{manifest['slug']}@{manifest['version']}"
    return {
        "decision": decision,
        "published_slug": hosted["runtime"]["slug"],
        "workflow_version": workflow_version,
        "build_evidence": {
            "checks": ["compile", "contract", "pricing"],
            "source_sha256": generated_source_sha256,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }


def release_branch_for_submission(submission_id: str, slug: str) -> str:
    return f"omo-release/{validate_submission_id(submission_id)}-{slug}"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def hash_release_artifact_entries(entries: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for rel, content in sorted(entries.items()):
        if "/__pycache__/" in rel or rel.endswith(".pyc"):
            continue
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).hexdigest().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def hash_release_artifacts(slug: str, root: Path = ROOT) -> str:
    container = root / "containers" / slug
    if not container.is_dir():
        raise RuntimeError("generated artifact directory is missing")
    entries: dict[str, bytes] = {}
    for path in sorted(candidate for candidate in container.rglob("*") if candidate.is_file()):
        rel = path.relative_to(root).as_posix()
        entries[rel] = path.read_bytes()
    return hash_release_artifact_entries(entries)


def release_allowlisted_paths(slug: str, root: Path = ROOT) -> list[str]:
    if not SAFE_SLUG_RE.fullmatch(slug):
        raise ValueError("invalid release slug")
    run_manifest_slugs = {slug}
    hosted_profile_path = root / "containers" / slug / "hosted-profile.json"
    if hosted_profile_path.is_file():
        try:
            hosted_profile = json.loads(hosted_profile_path.read_text(encoding="utf-8"))
            published_slug = str(hosted_profile.get("runtime", {}).get("slug") or "")
        except (OSError, json.JSONDecodeError, AttributeError):
            published_slug = ""
        if SAFE_SLUG_RE.fullmatch(published_slug):
            run_manifest_slugs.add(published_slug)
    candidates = [
        f"containers/{slug}",
        f"packages/skill-to-modal/profiles/{slug}.json",
        *(f"site/run-manifests/{manifest_slug}.json" for manifest_slug in sorted(run_manifest_slugs)),
        "site/catalog.js",
        "site/deploy/hosted-skills.generated.mjs",
        "site/deploy/schema.sql",
        "site/deploy/test-balance.mjs",
        "site/deploy/test-cost.mjs",
        "site/deploy/test-router.mjs",
        "site/deploy/test-workers.mjs",
        "site/deploy/worker.js",
        "site/upload.js",
        ".github/workflows/generated-workflow-contracts.yml",
    ]
    return [path for path in candidates if (root / path).exists()]


def copy_allowlisted_release_paths(slug: str, destination_root: Path, source_root: Path = ROOT) -> list[str]:
    copied: list[str] = []
    for rel in release_allowlisted_paths(slug, source_root):
        source = source_root / rel
        destination = destination_root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(source, destination)
        copied.append(rel)
    return copied


def slug_from_release_branch(branch: str) -> str:
    prefix = "omo-release/sub_"
    if not branch.startswith(prefix):
        raise ValueError("invalid release branch")
    tail = branch[len(prefix):]
    parts = tail.split("-")
    for index in range(1, len(parts)):
        candidate = "-".join(parts[index:])
        if SAFE_SLUG_RE.fullmatch(candidate) and (ROOT / "containers" / candidate).is_dir():
            return candidate
    match = re.fullmatch(r"[A-Za-z0-9_-]{8,100}-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)", tail)
    if match:
        return match.group("slug")
    raise ValueError("invalid release branch")


def normalize_release_metadata(
    value: dict[str, Any],
    *,
    require_promotion_evidence: bool = True,
) -> dict[str, Any]:
    phase = str(value.get("release_phase") or value.get("phase") or "").strip()
    if phase not in RELEASE_PHASES:
        raise ValueError("invalid release phase")
    metadata: dict[str, Any] = {"release_phase": phase}
    for key in ("source_sha256", "artifact_hash"):
        text = str(value.get(key) or "").strip().lower()
        if text:
            if not SAFE_SHA256_RE.fullmatch(text):
                raise ValueError(f"invalid release {key}")
            metadata[key] = text
    for key in ("head_sha", "merge_sha", "verified_merge_sha"):
        text = str(value.get(key) or "").strip().lower()
        if text:
            if not SAFE_GIT_SHA_RE.fullmatch(text):
                raise ValueError(f"invalid release {key}")
            metadata[key] = text
    branch = str(value.get("branch") or "").strip()
    if branch:
        if not re.fullmatch(r"omo-release/sub_[A-Za-z0-9_-]{8,100}-[a-z0-9]+(?:-[a-z0-9]+)*", branch):
            raise ValueError("invalid release branch")
        metadata["branch"] = branch
    slug = str(value.get("slug") or "").strip()
    if slug:
        if not SAFE_SLUG_RE.fullmatch(slug):
            raise ValueError("invalid release slug")
        metadata["slug"] = slug
    for key in ("issue_url", "pr_url"):
        text = str(value.get(key) or "").strip()
        if text:
            if not SAFE_GITHUB_URL_RE.fullmatch(text):
                raise ValueError(f"invalid release {key}")
            metadata[key] = text
    if value.get("pr_number") is not None:
        pr_number = int(value["pr_number"])
        if pr_number < 1:
            raise ValueError("invalid release pr_number")
        metadata["pr_number"] = pr_number
    modal_app = str(value.get("modal_app") or "").strip()
    if modal_app:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", modal_app):
            raise ValueError("invalid Modal app name")
        metadata["modal_app"] = modal_app
    modal_url = str(value.get("modal_url") or "").strip()
    if modal_url:
        metadata["modal_url"] = HOST_MODULE.validate_https_modal_endpoint(
            modal_url,
            expected_workspace=EXPECTED_MODAL_WORKSPACE,
        )
    canary = value.get("canary") or value.get("canary_evidence")
    if isinstance(canary, dict):
        safe_canary: dict[str, Any] = {}
        if str(canary.get("status") or "") in {"passed", "failed"}:
            safe_canary["status"] = str(canary["status"])
        checked_at = str(canary.get("checked_at") or canary.get("timestamp") or "").strip()
        if checked_at and len(checked_at) <= 64:
            safe_canary["checked_at"] = checked_at
        if safe_canary:
            metadata["canary"] = safe_canary
    release_gates = value.get("release_gates") or value.get("promotion_evidence")
    if isinstance(release_gates, dict):
        checked_at = str(release_gates.get("checked_at") or "").strip()
        safe_gates: dict[str, Any] = {}
        if release_gates.get("status") == "live" and checked_at and len(checked_at) <= 64:
            safe_gates = {"status": "live", "checked_at": checked_at}
            for name in ("R1", "R2", "R3", "R4"):
                gate = release_gates.get(name)
                status = str(gate.get("status") or "").strip() if isinstance(gate, dict) else ""
                allowed = {"published", "excluded_premium"} if name == "R4" else {"passed"}
                if status not in allowed:
                    safe_gates = {}
                    break
                safe_gates[name] = {"status": status}
        if safe_gates:
            metadata["release_gates"] = safe_gates
    if phase == "promoted" and require_promotion_evidence and "release_gates" not in metadata:
        raise ValueError("complete promotion evidence is required")
    return metadata


class GitHubReleaseAdapter:
    """GitHub release adapter with server-derived branch and PR identity.

    The controller is responsible for running this script in an approved context.
    Client-provided repo/branch/SHA values are never accepted by this adapter.
    """

    def __init__(
        self,
        command_runner: Any | None = None,
        scratch_root: Path | None = None,
        repo: str = GITHUB_RELEASE_REPO,
        base: str = GITHUB_RELEASE_BASE,
        required_checks: tuple[str, ...] = REQUIRED_RELEASE_CHECKS,
    ):
        if repo != GITHUB_RELEASE_REPO or base != GITHUB_RELEASE_BASE:
            raise ValueError("release adapter repo/base are fixed server-side")
        self.command_runner = command_runner or run_capture
        self.scratch_root = scratch_root
        self.repo = repo
        self.base = base
        self.required_checks = required_checks

    def _run(self, command: list[str], cwd: Path | None = None, text: bool = True) -> str | bytes:
        try:
            return self.command_runner(command, cwd=cwd, text=text)
        except subprocess.CalledProcessError as error:
            first = tuple(command[:3])
            if first == ("gh", "issue", "list"):
                stage = "release_issue_lookup"
            elif first == ("gh", "issue", "create"):
                stage = "release_issue_create"
            elif first == ("git", "worktree", "add") or first == ("git", "switch", "-C"):
                stage = "release_worktree"
            elif first == ("git", "push", "-u"):
                stage = "release_push"
            elif first == ("gh", "pr", "list"):
                stage = "release_pr_lookup"
            elif first == ("gh", "pr", "create"):
                stage = "release_pr_create"
            elif first == ("gh", "pr", "view"):
                stage = "release_pr_view"
            elif first == ("gh", "pr", "merge"):
                stage = "release_merge"
            else:
                stage = "release_command"
            raise StagedCalledProcessError(stage, error) from None

    def _json(self, command: list[str], cwd: Path | None = None) -> Any:
        raw = self._run(command, cwd=cwd)
        try:
            return json.loads(str(raw or ""))
        except json.JSONDecodeError as error:
            raise RuntimeError("release command returned invalid JSON") from error

    def _issue_for_submission(self, submission_id: str, slug: str) -> dict[str, Any]:
        title = f"Omo release: {submission_id} {slug}"
        existing = self._json([
            "gh", "issue", "list",
            "--repo", self.repo,
            "--state", "open",
            "--search", f"{submission_id} in:title",
            "--json", "number,url",
        ])
        if isinstance(existing, list) and existing:
            issue = existing[0]
            return {"number": int(issue["number"]), "url": str(issue["url"])}
        url = str(self._run([
            "gh", "issue", "create",
            "--repo", self.repo,
            "--title", title,
            "--body", f"Server-prepared release for submission `{submission_id}` / `{slug}`.",
        ])).strip()
        if not SAFE_GITHUB_URL_RE.fullmatch(url):
            raise RuntimeError("invalid release issue URL")
        return {"url": url, "number": int(url.rsplit("/", 1)[1])}

    def _pr_for_branch(self, branch: str, issue_number: int, release_request: dict[str, Any]) -> dict[str, Any]:
        existing = self._json([
            "gh", "pr", "list",
            "--repo", self.repo,
            "--state", "open",
            "--head", branch,
            "--json", "number,url,headRefOid",
        ])
        if isinstance(existing, list) and existing:
            pr = existing[0]
            return {"number": int(pr["number"]), "url": str(pr["url"]), "headRefOid": str(pr.get("headRefOid") or "")}
        body = (
            f"Closes #{issue_number}\n\n"
            f"submission: `{release_request['submission_id']}`\n"
            f"slug: `{release_request['slug']}`\n"
            f"source_sha256: `{release_request['source_sha256']}`\n"
            f"artifact_hash: `{release_request['artifact_hash']}`\n"
        )
        pr_url = str(self._run([
            "gh", "pr", "create",
            "--repo", self.repo,
            "--base", self.base,
            "--head", branch,
            "--title", f"Release {release_request['slug']} submission {release_request['submission_id']}",
            "--body", body,
        ])).strip()
        if not SAFE_GITHUB_URL_RE.fullmatch(pr_url):
            raise RuntimeError("invalid release PR URL")
        viewed = self._json([
            "gh", "pr", "view",
            "--repo", self.repo,
            pr_url,
            "--json", "number,url,headRefOid",
        ])
        if not isinstance(viewed, dict):
            raise RuntimeError("invalid release PR metadata")
        return {"number": int(viewed["number"]), "url": str(viewed["url"]), "headRefOid": str(viewed.get("headRefOid") or "")}

    def _prepare_worktree(self, branch: str, slug: str) -> tuple[Path, str]:
        scratch_parent = self.scratch_root or Path(tempfile.mkdtemp(prefix="omo-release-parent-"))
        scratch_parent.mkdir(parents=True, exist_ok=True)
        worktree = Path(tempfile.mkdtemp(prefix="omo-release-worktree-", dir=scratch_parent))
        self._run(["git", "fetch", "origin", self.base])
        self._run(["git", "worktree", "add", "--detach", str(worktree), f"origin/{self.base}"])
        self._run(["git", "switch", "-C", branch], cwd=worktree)
        copied = copy_allowlisted_release_paths(slug, worktree)
        if not copied:
            raise RuntimeError("release allowlist matched no files")
        self._run(["git", "add", *copied], cwd=worktree)
        self._run(
            [
                "git",
                "-c",
                "user.name=Omo Trusted Release",
                "-c",
                "user.email=omo-trusted-release@users.noreply.github.com",
                "commit",
                "-m",
                f"Release {slug}",
            ],
            cwd=worktree,
        )
        head_sha = str(self._run(["git", "rev-parse", "HEAD"], cwd=worktree)).strip().lower()
        if not SAFE_GIT_SHA_RE.fullmatch(head_sha):
            raise RuntimeError("invalid release head SHA")
        return worktree, head_sha

    def prepare_release(self, release_request: dict[str, Any]) -> dict[str, Any]:
        submission_id = validate_submission_id(str(release_request.get("submission_id") or ""))
        slug = str(release_request.get("slug") or "").strip()
        if not SAFE_SLUG_RE.fullmatch(slug):
            raise ValueError("invalid release slug")
        source_sha256 = str(release_request.get("source_sha256") or "").strip().lower()
        artifact_hash = str(release_request.get("artifact_hash") or "").strip().lower()
        if not SAFE_SHA256_RE.fullmatch(source_sha256) or not SAFE_SHA256_RE.fullmatch(artifact_hash):
            raise ValueError("release source/artifact hashes are required")
        branch = release_branch_for_submission(submission_id, slug)
        request = {**release_request, "submission_id": submission_id, "slug": slug, "branch": branch}
        issue = self._issue_for_submission(submission_id, slug)
        _worktree, head_sha = self._prepare_worktree(branch, slug)
        self._run(["git", "push", "-u", "origin", branch], cwd=_worktree)
        pr = self._pr_for_branch(branch, int(issue["number"]), request)
        return normalize_release_metadata({
            "release_phase": "pr_open",
            "issue_url": issue["url"],
            "pr_url": pr["url"],
            "pr_number": pr["number"],
            "branch": branch,
            "head_sha": pr.get("headRefOid") or head_sha,
            "source_sha256": source_sha256,
            "artifact_hash": artifact_hash,
        })

    def _pr_view(self, pr_number: int) -> dict[str, Any]:
        value = self._json([
            "gh", "pr", "view",
            "--repo", self.repo,
            str(pr_number),
            "--json", "number,url,state,baseRefName,headRefOid,mergeCommit,statusCheckRollup",
        ])
        if not isinstance(value, dict):
            raise RuntimeError("invalid release PR metadata")
        return value

    def _assert_required_checks_success(self, pr: dict[str, Any]) -> None:
        checks = pr.get("statusCheckRollup")
        if not isinstance(checks, list):
            raise RuntimeError("required_checks_not_successful")
        successful: set[str] = set()
        for check in checks:
            if not isinstance(check, dict):
                continue
            name = str(check.get("name") or check.get("context") or "").strip()
            conclusion = str(check.get("conclusion") or check.get("status") or "").upper()
            if name and conclusion in {"SUCCESS", "COMPLETED"}:
                successful.add(name)
        missing = [name for name in self.required_checks if name not in successful]
        if missing:
            raise RuntimeError("required_checks_not_successful")

    def merge_after_required_checks(self, release_metadata: dict[str, Any]) -> dict[str, Any]:
        metadata = normalize_release_metadata(release_metadata)
        pr_number = int(metadata.get("pr_number") or 0)
        if not pr_number:
            raise RuntimeError("release PR number is required")
        pr = self._pr_view(pr_number)
        if pr.get("baseRefName") != self.base or str(pr.get("headRefOid") or "").lower() != metadata.get("head_sha"):
            raise RuntimeError("release PR identity mismatch")
        self._assert_required_checks_success(pr)
        if pr.get("state") != "MERGED":
            self._run(["gh", "pr", "merge", "--repo", self.repo, str(pr_number), "--merge"])
        return self.verify_merged_release(metadata)

    def _tree_file(self, commit: str, path: str) -> bytes:
        raw = self._run(["git", "show", f"{commit}:{path}"], text=False)
        if isinstance(raw, str):
            return raw.encode("utf-8")
        return raw

    def _tree_artifact_hash(self, commit: str, slug: str) -> str:
        raw = self._run(["git", "ls-tree", "-r", "-z", "--name-only", commit, "--", f"containers/{slug}"])
        paths = [path for path in str(raw).split("\0") if path]
        entries = {path: self._tree_file(commit, path) for path in paths}
        if not entries:
            raise RuntimeError("verified merge artifact tree is empty")
        return hash_release_artifact_entries(entries)

    def verify_merged_release(self, release_metadata: dict[str, Any]) -> dict[str, Any]:
        metadata = normalize_release_metadata(release_metadata)
        pr_number = int(metadata.get("pr_number") or 0)
        branch = str(metadata.get("branch") or "")
        if not pr_number or not branch:
            raise RuntimeError("release PR metadata is required")
        slug = slug_from_release_branch(branch)
        pr = self._pr_view(pr_number)
        if pr.get("state") != "MERGED" or pr.get("baseRefName") != self.base:
            raise RuntimeError("verified_merge_required")
        if str(pr.get("headRefOid") or "").lower() != metadata.get("head_sha"):
            raise RuntimeError("release head SHA mismatch")
        merge = pr.get("mergeCommit")
        merge_sha = str(merge.get("oid") if isinstance(merge, dict) else "").strip().lower()
        if not SAFE_GIT_SHA_RE.fullmatch(merge_sha):
            raise RuntimeError("verified_merge_required")
        self._run(["git", "fetch", "origin", self.base])
        self._run(["git", "cat-file", "-e", f"{merge_sha}^{{commit}}"])
        self._run(["git", "merge-base", "--is-ancestor", merge_sha, f"origin/{self.base}"])
        source = self._tree_file(merge_sha, f"containers/{slug}/source/SKILL.md")
        source_sha256 = sha256_bytes(source)
        artifact_hash = self._tree_artifact_hash(merge_sha, slug)
        if source_sha256 != metadata.get("source_sha256") or artifact_hash != metadata.get("artifact_hash"):
            raise RuntimeError("verified merge source/artifact hash mismatch")
        return normalize_release_metadata({
            **metadata,
            "release_phase": "merged_verified",
            "merge_sha": merge_sha,
            "verified_merge_sha": merge_sha,
            "source_sha256": source_sha256,
            "artifact_hash": artifact_hash,
        })

    def checkout_verified_release(self, release_metadata: dict[str, Any]) -> Path:
        metadata = normalize_release_metadata(release_metadata)
        merge_sha = str(metadata.get("verified_merge_sha") or metadata.get("merge_sha") or "").strip()
        if not SAFE_GIT_SHA_RE.fullmatch(merge_sha) or metadata.get("release_phase") != "merged_verified":
            raise RuntimeError("verified_merge_required")
        scratch_parent = self.scratch_root or Path(tempfile.mkdtemp(prefix="omo-promote-parent-"))
        scratch_parent.mkdir(parents=True, exist_ok=True)
        worktree = Path(tempfile.mkdtemp(prefix="omo-promote-worktree-", dir=scratch_parent))
        self._run(["git", "worktree", "add", "--detach", str(worktree), merge_sha])
        return worktree


def assert_reviewed_runtime(profile_path: Path, selected_runtime: str) -> None:
    decision = HOST_MODULE.decide_runtime_placement(json.loads(profile_path.read_text(encoding="utf-8")))
    if decision["effective"] != selected_runtime:
        raise RuntimeError("reviewed runtime decision diverged from selected_runtime")


def assert_modal_workspace(profile_path: Path, selected_runtime: str) -> None:
    if selected_runtime != "modal-hosted":
        return
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    endpoint = profile.get("marketplace", {}).get("deployment", {}).get("default_endpoint")
    HOST_MODULE.validate_https_modal_endpoint(endpoint, expected_workspace=EXPECTED_MODAL_WORKSPACE)


def prepare_reviewed_release(skill_path: Path, slug: str, profile_path: Path, selected_runtime: str) -> None:
    assert_reviewed_runtime(profile_path, selected_runtime)
    assert_modal_workspace(profile_path, selected_runtime)
    if selected_runtime not in SAFE_SELECTED_RUNTIMES:
        raise RuntimeError("selected runtime must be worker-native or modal-hosted")
    run_checked_at_stage(
        host_command(skill_path, slug, profile_path=profile_path, register=True),
        ROOT,
        "trusted_register",
    )
    run_checked_at_stage(
        host_command(skill_path, slug, profile_path=profile_path, register=True, check=True),
        ROOT,
        "trusted_check",
    )
    for script in ("test-workers.mjs", "test-router.mjs", "test-balance.mjs", "test-cost.mjs"):
        run_checked_at_stage(["node", script], WORKER_ROOT, "worker_contracts")


def _oss_frontmatter_and_body(md: str) -> tuple[str, str]:
    """Return (frontmatter text incl. --- fences, body text after the closer)."""
    lines = md.splitlines(keepends=True)
    close_idx = None
    seen = 0
    for index, line in enumerate(lines):
        if line.strip() == "---":
            seen += 1
            if seen == 2:
                close_idx = index
                break
    if close_idx is None:
        return "", md
    return "".join(lines[: close_idx + 1]), "".join(lines[close_idx + 1 :])


def _oss_with_policy_header(md: str) -> str:
    """Insert the OSS policy header once, immediately after the frontmatter."""
    frontmatter, body = _oss_frontmatter_and_body(md)
    if "Omo open source" in body[:200]:
        return md  # idempotent: header already present
    return frontmatter + "\n" + OSS_POLICY_HEADER + "\n" + body.lstrip("\n")


def _oss_section(md: str, *headings: str) -> str | None:
    for heading in headings:
        match = re.search(rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s|\Z)", md, re.M)
        if match:
            return match.group(1).strip()
    return None


def _oss_bullets(text: str | None) -> list[str]:
    if not text:
        return []
    return [line.strip()[2:].strip() for line in text.splitlines() if line.strip().startswith("- ")]


def _oss_summary(text: str | None) -> str:
    if not text:
        return ""
    flat = " ".join(text.split())
    return flat[:180] + ("…" if len(flat) > 180 else "")


def _oss_git(repo_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _oss_git_or_raise(result: subprocess.CompletedProcess) -> None:
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, result.args)


def ensure_oss_repo_checkout(repo_dir: Path, repo_url: str) -> None:
    """Clone or refresh the dedicated omo-space/skills publish checkout."""
    if (repo_dir / ".git").exists():
        _oss_git_or_raise(_oss_git(repo_dir, "pull", "--ff-only", "origin", "main"))
    else:
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", repo_url, str(repo_dir)],
            capture_output=True,
            text=True,
            check=True,
        )


def _oss_commit_args(repo_dir: Path) -> list[str]:
    name = _oss_git(repo_dir, "config", "user.name").stdout.strip()
    email = _oss_git(repo_dir, "config", "user.email").stdout.strip()
    if name and email:
        return []
    publisher_name, publisher_email = OSS_GIT_IDENTITY
    return ["-c", f"user.name={publisher_name}", "-c", f"user.email={publisher_email}"]


def _oss_generated_readme(name: str, description: str, run_price: float | None) -> str:
    price_str = f"${run_price:.2f}" if run_price is not None else "see omo.space"
    return (
        "[![Omo](../../assets/logo.svg)](https://omo.space) · [All Omo Skills](../../README.md)\n\n"
        f"# {name}\n\nWhat this does: {description}\n\nOmo price: **{price_str} per run**.\n\n"
        "| Run it on Omo (one click) | Run it yourself (bring API keys + infrastructure per the SKILL.md) |\n"
        "| --- | --- |\n"
        "| [omo.space](https://omo.space) | [SKILL.md](SKILL.md) |\n"
    )


def build_oss_release_artifacts(slug: str, source_root: Path, repo_dir: Path) -> dict[str, bytes]:
    """Build the public SKILL.md (with policy header), LICENSE, README, and manifest.

    Reads the verified release tree only: containers/<slug>/source/SKILL.md
    (the compiled live contract), container manifest.json (version), and
    pricing-report.json (hosted run price). No private container internals
    (modal_app, hosted-profile, provider credentials) are ever published.
    """
    container = source_root / "containers" / slug
    skill_source = container / "source" / "SKILL.md"
    if not skill_source.exists():
        raise RuntimeError(f"missing oss publish source for {slug}")
    skill_md = skill_source.read_text(encoding="utf-8")

    container_manifest: dict[str, Any] = {}
    container_manifest_path = container / "manifest.json"
    if container_manifest_path.exists():
        try:
            container_manifest = json.loads(container_manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            container_manifest = {}
    pricing: dict[str, Any] = {}
    pricing_path = container / "pricing-report.json"
    if pricing_path.exists():
        try:
            pricing = json.loads(pricing_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pricing = {}

    per_skill_license = source_root / "oss" / slug / "LICENSE"
    license_path = per_skill_license if per_skill_license.exists() else repo_dir / "LICENSE"
    if not license_path.exists():
        raise RuntimeError(f"missing license source for {slug}")
    license_text = license_path.read_text(encoding="utf-8")

    readme_path = source_root / "oss" / slug / "README.md"
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
    else:
        description = str(container_manifest.get("description") or "").strip()
        if not description:
            description_match = re.search(r"^description:\s*(.+)$", skill_md, re.M)
            description = description_match.group(1).strip() if description_match else "A hosted Omo workflow."
        if not description.endswith("."):
            description += "."
        name = str(container_manifest.get("name") or "").strip()
        if not name or name == slug:
            name = slug.replace("-", " ").title()
        readme_text = _oss_generated_readme(name, description, pricing.get("display_price_usd"))

    version = str(container_manifest.get("version") or "0.1.0")
    name = str(container_manifest.get("name") or "").strip()
    if not name or name == slug:
        name = slug.replace("-", " ").title()
    run_price = pricing.get("display_price_usd")

    inputs = _oss_bullets(_oss_section(skill_md, "Inputs", "Input contract", "Input"))
    if not inputs:
        workflow = _oss_section(skill_md, "Workflow")
        if workflow:
            first_step = re.search(r"1\.\s+\*\*(.+?)\*\*\s*:?\s*([^\n]+)", workflow)
            if first_step:
                inputs = [f"{first_step.group(1).rstrip(': ').strip()}: {first_step.group(2).strip()[:160]}"]
    output_section = _oss_section(skill_md, "Output contract", "Outputs", "Output")
    outputs = _oss_bullets(output_section) or ([_oss_summary(output_section)] if output_section else [])

    published_skill = _oss_with_policy_header(skill_md)
    manifest = {
        "slug": slug,
        "name": name,
        "version": version,
        "license": "MIT",
        "policy": OSS_POLICY_URL,
        "hosted_run_price_usd": run_price,
        "inputs": inputs,
        "outputs": outputs,
        "source_sha256": sha256_bytes(published_skill.encode("utf-8")),
        "publish_mechanism": OSS_PUBLISH_MECHANISM,
    }
    return {
        "SKILL.md": published_skill.encode("utf-8"),
        "LICENSE": license_text.encode("utf-8"),
        "README.md": readme_text.encode("utf-8"),
        "manifest.json": (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    }


def publish_oss_release(slug: str, source_root: Path, environ: dict[str, str] | None = None) -> dict[str, Any]:
    """Publish one released FREE slug to github.com/omo-space/skills (R4 gate).

    Premium slugs (OSS_PREMIUM_EXCLUSIONS) return ``excluded_premium`` and
    never publish. The publish is idempotent: an identical re-release produces
    byte-identical artifacts and no new commit. Any clone/prepare/commit/push
    failure raises a typed OssPublishBlocker so the release fails closed.
    """
    environ = environ if environ is not None else os.environ
    if slug in OSS_PREMIUM_EXCLUSIONS:
        return {"status": "excluded_premium", "slug": slug}
    if not SAFE_SLUG_RE.fullmatch(slug):
        raise OssPublishBlocker("oss_publish_prepare_failed")
    repo_dir = Path(str(environ.get("OMO_OSS_REPO_DIR") or "").strip() or OSS_REPO_LOCAL)
    repo_url = str(environ.get("OMO_OSS_REPO_URL") or "").strip() or OSS_REPO_URL
    if repo_dir.resolve() in (ROOT.resolve(), ROOT.resolve().parent):
        raise OssPublishBlocker("oss_publish_prepare_failed")
    try:
        ensure_oss_repo_checkout(repo_dir, repo_url)
    except subprocess.CalledProcessError as error:
        raise OssPublishBlocker("oss_publish_clone_failed") from error
    try:
        artifacts = build_oss_release_artifacts(slug, source_root, repo_dir)
        manifest = json.loads(artifacts["manifest.json"])
    except (RuntimeError, json.JSONDecodeError) as error:
        raise OssPublishBlocker("oss_publish_prepare_failed") from error
    try:
        target_dir = repo_dir / OSS_SKILL_REL.format(slug=slug)
        target_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in artifacts.items():
            (target_dir / filename).write_bytes(content)
        _oss_git_or_raise(_oss_git(repo_dir, "add", "-A", f"skills/{slug}"))
        unchanged = _oss_git(repo_dir, "diff", "--cached", "--quiet")
        if unchanged.returncode == 0:
            return {
                "status": "up_to_date",
                "slug": slug,
                "version": manifest["version"],
                "source_sha256": manifest["source_sha256"],
            }
        if unchanged.returncode != 1:
            raise subprocess.CalledProcessError(unchanged.returncode, unchanged.args)
    except OSError as error:
        raise OssPublishBlocker("oss_publish_prepare_failed") from error
    except subprocess.CalledProcessError as error:
        raise OssPublishBlocker("oss_publish_prepare_failed") from error
    message = f"release({slug}): v{manifest['version']} oss publish"
    try:
        _oss_git_or_raise(
            _oss_git(repo_dir, *_oss_commit_args(repo_dir), "commit", "-m", message)
        )
    except subprocess.CalledProcessError as error:
        raise OssPublishBlocker("oss_publish_commit_failed") from error
    try:
        _oss_git_or_raise(_oss_git(repo_dir, "push", "origin", "HEAD:main"))
    except subprocess.CalledProcessError as error:
        raise OssPublishBlocker("oss_publish_push_failed") from error
    head = _oss_git(repo_dir, "rev-parse", "HEAD")
    return {
        "status": "published",
        "slug": slug,
        "version": manifest["version"],
        "commit": head.stdout.strip(),
        "source_sha256": manifest["source_sha256"],
    }


def deploy_merged_release(
    skill_path: Path,
    slug: str,
    profile_path: Path,
    release_metadata: dict[str, Any],
    release_adapter: Any,
) -> dict[str, Any]:
    try:
        verified = normalize_release_metadata(release_adapter.verify_merged_release(release_metadata))
    except ValueError as error:
        raise RuntimeError("verified_merge_required") from error
    if (
        verified.get("release_phase") != "merged_verified"
        or not verified.get("merge_sha")
        or verified.get("verified_merge_sha") != verified.get("merge_sha")
        or verified.get("source_sha256") != str(release_metadata.get("source_sha256") or "").strip().lower()
        or verified.get("artifact_hash") != str(release_metadata.get("artifact_hash") or "").strip().lower()
    ):
        raise RuntimeError("verified_merge_required")
    selected_runtime = str(release_metadata.get("selected_runtime") or "").strip()
    release_root = ROOT
    used_verified_checkout = False
    if hasattr(release_adapter, "checkout_verified_release"):
        release_root = release_adapter.checkout_verified_release(verified)
        used_verified_checkout = True
    release_profile_path = release_root / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json"
    if not used_verified_checkout or not release_profile_path.exists():
        release_profile_path = profile_path
    assert_reviewed_runtime(release_profile_path, selected_runtime)
    assert_modal_workspace(release_profile_path, selected_runtime)
    if selected_runtime == "modal-hosted":
        run_checked([sys.executable, "-m", "modal", "deploy", str(release_root / "containers" / slug / "modal_app.py")])
        direct_modal_canary(slug, release_profile_path)
    elif selected_runtime != "worker-native":
        raise RuntimeError("selected runtime must be worker-native or modal-hosted")
    worker_deploy_root = release_root / "site" / "deploy"
    registry_evidence = verify_generated_worker_registry([slug], worker_deploy_root)
    run_checked(["npm", "ci"], worker_deploy_root)
    deploy_evidence = deploy_worker_registry(worker_deploy_root)
    smoke_evidence = smoke_live_worker_registry([slug])
    if slug in OSS_PREMIUM_EXCLUSIONS:
        oss_evidence: dict[str, Any] = {"status": "excluded_premium", "slug": slug}
    else:
        oss_evidence = publish_oss_release(slug, release_root)
    return {
        **verified,
        "release_phase": "promoted",
        "release_gates": {
            "R1": registry_evidence,
            "R2": deploy_evidence,
            "R3": smoke_evidence,
            "R4": oss_evidence,
            "status": "live",
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }


def process_row(row: dict[str, Any], repository: SubmissionRepository, deploy: bool, release_adapter: Any | None = None) -> dict[str, Any]:
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
        validated, allow_matching_container=row.get("prior_status") in {"needs_review", "ready_for_deploy"}
    )
    if state != "ready_for_build":
        review_path = None
        if state == "needs_review" and reason == "reviewed_profile_required" and row.get("prior_status") not in {"needs_review", "processing"}:
            review_path = persist_review_source(validated, submission_id)
        repository.set_status(submission_id, state, reason)
        result = {"id": submission_id, "slug": validated.slug, "status": state, "failure_code": reason}
        if review_path is not None:
            result.update({"source_sha256": validated.source_sha256, "review_path": str(review_path)})
        return result

    try:
        with tempfile.TemporaryDirectory(prefix="omo-submission-") as temp_dir:
            skill_path = Path(temp_dir) / "SKILL.md"
            skill_path.write_text(validated.content, encoding="utf-8")
            profile_path, _decision = reviewed_profile_artifact(
                validated.slug,
                row.get("requested_runtime"),
                Path(temp_dir),
                source_sha256=validated.source_sha256,
            )
            run_checked_at_stage(
                host_command(skill_path, validated.slug, profile_path=profile_path),
                ROOT,
                "trusted_compile",
            )
            metadata = generated_runtime_metadata(validated.slug, profile_path, validated.source_sha256)
            decision = metadata["decision"]
            repository.set_runtime_decision(submission_id, decision)
            if deploy:
                prepare_reviewed_release(skill_path, validated.slug, profile_path, decision["effective"])
                release_request = {
                    "submission_id": submission_id,
                    "slug": validated.slug,
                    "published_slug": metadata["published_slug"],
                    "workflow_version": metadata["workflow_version"],
                    "selected_runtime": decision["effective"],
                    "source_sha256": validated.source_sha256,
                    "artifact_hash": hash_release_artifacts(validated.slug),
                    "branch": release_branch_for_submission(submission_id, validated.slug),
                }
                adapter = release_adapter or GitHubReleaseAdapter()
                release_metadata = normalize_release_metadata(adapter.prepare_release(release_request))
                repository.set_deployment_metadata(
                    submission_id,
                    "ready_for_deploy",
                    metadata["published_slug"],
                    metadata["workflow_version"],
                    metadata["build_evidence"],
                )
                repository.set_release_metadata(submission_id, release_metadata)
            else:
                repository.set_deployment_metadata(
                    submission_id,
                    "ready_for_deploy",
                    metadata["published_slug"],
                    metadata["workflow_version"],
                    metadata["build_evidence"],
                )
    except StagedCalledProcessError as error:
        repository.set_status(submission_id, "failed", "build_or_deploy_failed")
        return {
            "id": submission_id,
            "slug": validated.slug,
            "status": "failed",
            "failure_code": "build_or_deploy_failed",
            "failure_stage": error.stage,
        }
    except subprocess.CalledProcessError:
        repository.set_status(submission_id, "failed", "build_or_deploy_failed")
        return {
            "id": submission_id,
            "slug": validated.slug,
            "status": "failed",
            "failure_code": "build_or_deploy_failed",
            "failure_stage": "trusted_release",
        }
    except RuntimeError as error:
        failure_code = "generated_source_hash_mismatch" if str(error) == "generated_source_hash_mismatch" else "canary_or_internal_failed"
        repository.set_status(submission_id, "failed", failure_code)
        return {
            "id": submission_id,
            "slug": validated.slug,
            "status": "failed",
            "failure_code": failure_code,
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
        "status": "ready_for_merge" if deploy else "ready_for_deploy",
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


def release_metadata_from_row(row: dict[str, Any]) -> dict[str, Any]:
    metadata = {
        "release_phase": row.get("release_phase"),
        "issue_url": row.get("release_issue_url"),
        "pr_url": row.get("release_pr_url"),
        "pr_number": row.get("release_pr_number"),
        "branch": row.get("release_branch"),
        "head_sha": row.get("release_head_sha"),
        "merge_sha": row.get("release_merge_sha"),
        "source_sha256": row.get("source_sha256"),
        "artifact_hash": row.get("release_artifact_hash"),
        "modal_app": row.get("modal_app"),
        "modal_url": row.get("modal_url"),
        "canary": row.get("canary_evidence"),
        "promotion_evidence": row.get("promotion_evidence"),
        "selected_runtime": row.get("selected_runtime"),
    }
    normalized = normalize_release_metadata(metadata)
    if metadata.get("selected_runtime"):
        normalized["selected_runtime"] = str(metadata["selected_runtime"])
    return normalized


def repository_from_env(environ: dict[str, str]) -> Any:
    worker_base_url = str(environ.get("BUILD_WORKER_BASE_URL", "")).strip()
    worker_token = str(environ.get("BUILD_WORKER_TOKEN", "")).strip()
    if worker_base_url or worker_token:
        if not worker_base_url or not worker_token:
            raise ValueError("BUILD_WORKER_BASE_URL and BUILD_WORKER_TOKEN must be set together")
        return HttpSubmissionRepository(worker_base_url, worker_token, environ)
    database_url = str(environ.get("NEON_DATABASE_URL", "")).strip()
    return SubmissionRepository(database_url)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", help="Claim a specific queued/needs_review submission")
    parser.add_argument("--deploy", action="store_true", help="Run external Modal/Worker deployment gates")
    parser.add_argument("--prepare-release", action="store_true", help="Prepare/reuse the GitHub issue, release branch, and PR for a reviewed submission")
    parser.add_argument("--merge-verified-release", help="Merge one prepared release PR after required checks pass")
    parser.add_argument("--resume-merged-release", help="Resume one failed, merge-verified release through the private Worker bridge")
    parser.add_argument("--deploy-merged-release", help="Deploy one server-verified merged release from its merge tree")
    parser.add_argument("--dry-run", type=Path, metavar="SAMPLE_JSON", help="Validate a sample without DB writes")
    parser.add_argument("--export-review", help="Export one submission to a mode-0600 review file")
    parser.add_argument("--review-dir", type=Path, help="Destination directory used with --export-review")
    parser.add_argument("--mark-deployed", help="Mark ready_for_publish after Git/Vercel and billing canaries pass")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dry_run:
        return dry_run_sample(args.dry_run)
    prepare_release = bool(args.deploy or args.prepare_release)
    if prepare_release and not args.id:
        raise ValueError("--prepare-release requires a reviewed submission --id")

    repository = repository_from_env(os.environ)
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
        if args.merge_verified_release:
            submission_id = validate_submission_id(args.merge_verified_release)
            row = repository.get(submission_id)
            if not row:
                raise ValueError("submission not found")
            adapter = GitHubReleaseAdapter()
            merged = adapter.merge_after_required_checks(release_metadata_from_row(row))
            repository.set_release_metadata(submission_id, merged)
            output({"id": submission_id, **merged})
            return 0
        if args.resume_merged_release:
            submission_id = validate_submission_id(args.resume_merged_release)
            row = repository.get(submission_id)
            if not row:
                raise ValueError("submission not found")
            merge_sha = str(row.get("release_merge_sha") or "").strip().lower()
            if (
                row.get("status") != "failed"
                or row.get("release_phase") != "merged_verified"
                or not SAFE_GIT_SHA_RE.fullmatch(merge_sha)
            ):
                raise RuntimeError("submission is not a failed merge-verified release")
            if not hasattr(repository, "resume_merged_release"):
                raise RuntimeError("merged release recovery requires the private Worker bridge")
            repository.resume_merged_release(submission_id, merge_sha)
            output({"id": submission_id, "status": "ready_for_deploy", "release_phase": "merged_verified"})
            return 0
        if args.deploy_merged_release:
            raise RuntimeError(
                "deploy_merged_release requires the trusted finalizer controller; "
                "the legacy two-write promotion path is disabled"
            )
        submission_id = validate_submission_id(args.id) if args.id else None
        row = repository.claim(
            submission_id,
            include_review=bool(submission_id),
            include_ready=prepare_release,
        )
        if not row:
            output({"status": "idle", "message": "No queued submission."})
            return 0
        output(process_row(row, repository, prepare_release))
        return 0
    finally:
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
