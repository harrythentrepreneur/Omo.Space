#!/usr/bin/env python3
"""Concrete trusted production controller for Issue #141.

Targets, repository, branch, workflow, provider apps and public origin are fixed.
Only an immutable workflow-run identity is accepted from the CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from production_release_adapters import (
    CLOUDFLARE_TARGET,
    MODAL_ALLOWED_SLUG,
    MODAL_ENVIRONMENT,
    MODAL_TARGET,
    PUBLIC_ORIGIN,
    cloudflare_bundle_sha256,
    cloudflare_deploy_call,
    cloudflare_deployments_call,
    cloudflare_preflight_call,
    cloudflare_receipt,
    cloudflare_rollback_call,
    cloudflare_versions_call,
    modal_deploy_call,
    modal_history_call,
    modal_preflight_call,
    modal_receipt,
    modal_rollback_call,
)
from production_release_transport import ProductionCommandTransport
from release_finalizer import (
    DeploymentTargets,
    FinalizationClaim,
    FinalizerError,
    GreenMain,
    run_finalizer,
)

REPOSITORY = "harrythentrepreneur/Omo.Space"
WORKFLOW_PATH = ".github/workflows/generated-workflow-contracts.yml"
WORKFLOW_NAME = "generated-workflow-contracts"
BRANCH = "main"
WORKER_BASE_URL = "https://omo.space"
SAFE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SAFE_ID_RE = re.compile(r"^[1-9][0-9]{0,19}$")
REGISTRY_ROW_RE = re.compile(r'^  \[\n    "([a-z0-9]+(?:-[a-z0-9]+)*)",\n    \{$', re.MULTILINE)
MAX_HTTP_BYTES = 1024 * 1024
CANARY_SOURCE_MAX_BYTES = 200 * 1024
CANARY_SOURCE_SHA256 = "32a9e56a4c3ff57fce713d5341c48a5a1b54deee7cd7369a5cda7f9eb50fea0a"
TARGETS = DeploymentTargets(MODAL_TARGET, MODAL_ENVIRONMENT, CLOUDFLARE_TARGET, "production")
MODAL_CANARY_ORIGIN = "https://omo-space--cognition-label-normalizer-canary-api.modal.run"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


MODAL_OPENER = urllib.request.build_opener(_NoRedirect()).open


class ControllerError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _modal_result_url(value: object) -> str:
    raw = str(value or "").strip()
    parsed = None
    try:
        joined = urllib.parse.urljoin(MODAL_CANARY_ORIGIN + "/v1/runs", raw)
        parsed = urllib.parse.urlsplit(joined)
        query = urllib.parse.parse_qs(parsed.query, strict_parsing=True)
        valid = (
            parsed.scheme == "https" and parsed.hostname == urllib.parse.urlsplit(MODAL_CANARY_ORIGIN).hostname
            and parsed.port is None and parsed.username is None and parsed.password is None and not parsed.fragment
            and re.fullmatch(r"/v1/runs/run-[0-9a-f]{32}", parsed.path)
            and set(query) == {"call_id", "access_token"}
            and len(query["call_id"]) == len(query["access_token"]) == 1
            and re.fullmatch(r"fc-[A-Za-z0-9_-]{2,197}", query["call_id"][0])
            and re.fullmatch(r"[A-Za-z0-9_-]{32,200}", query["access_token"][0])
        )
    except ValueError:
        valid = False
    if not valid:
        raise ControllerError("modal_result_url_invalid")
    assert parsed is not None
    return urllib.parse.urlunsplit(parsed)


def _safe_json_response(response) -> dict[str, Any]:
    raw = response.read(MAX_HTTP_BYTES + 1)
    if len(raw) > MAX_HTTP_BYTES:
        raise ControllerError("http_response_too_large")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ControllerError("http_response_invalid") from None
    if not isinstance(value, dict):
        raise ControllerError("http_response_invalid")
    return value


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    opener=urllib.request.urlopen,
) -> tuple[int, dict[str, Any] | None]:
    data = None if payload is None else json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    request = urllib.request.Request(
        url, data=data, method=method,
        headers={"Accept": "application/json", "User-Agent": "OmoProductionFinalizer/1.0", **(headers or {})},
    )
    try:
        with opener(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 0) or 0)
            return status, None if status == 204 else _safe_json_response(response)
    except urllib.error.HTTPError as error:
        if isinstance(error.code, int) and 100 <= error.code <= 599:
            return error.code, None
        raise ControllerError("http_request_failed") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise ControllerError("http_request_failed") from None


def _request_json_stage(stage: str, *args, **kwargs) -> tuple[int, dict[str, Any] | None]:
    if stage not in {
        "github_http_failed", "finalizer_http_failed",
        "modal_canary_http_failed", "public_canary_http_failed",
    }:
        raise ControllerError("invalid_http_stage")
    mapped = False
    try:
        return _request_json(*args, **kwargs)
    except ControllerError as error:
        if not error.code.startswith("http_"):
            raise
        mapped = True
    if mapped:
        raise ControllerError(stage)
    raise ControllerError("invalid_http_stage")


class GitHubMainlineAdapter:
    def __init__(
        self, checkout: Path, trigger_sha: str, run_id: int, run_attempt: int,
        token: str, opener=urllib.request.urlopen,
    ):
        self.checkout = checkout.resolve()
        self.trigger_sha = trigger_sha
        self.token = token
        self.opener = opener
        self.calls = 0
        self.run_id, self.run_attempt = run_id, run_attempt
        if (not SAFE_SHA_RE.fullmatch(trigger_sha) or not token or
                not isinstance(run_id, int) or run_id < 1 or
                not isinstance(run_attempt, int) or run_attempt < 1):
            raise ControllerError("invalid_github_configuration")

    def _api(self, path: str) -> dict[str, Any]:
        status, body = _request_json_stage(
            "github_http_failed",
            f"https://api.github.com/repos/{REPOSITORY}{path}",
            headers={"Authorization": f"Bearer {self.token}", "X-GitHub-Api-Version": "2022-11-28"},
            opener=self.opener,
        )
        if status != 200 or not body:
            raise ControllerError("github_read_failed")
        return body

    def latest_green(self) -> GreenMain:
        ref = self._api(f"/git/ref/heads/{BRANCH}")
        sha = str(((ref.get("object") or {}).get("sha")) or "").lower()
        if not SAFE_SHA_RE.fullmatch(sha):
            raise ControllerError("github_read_failed")
        if self.calls == 0:
            run = self._api(f"/actions/runs/{self.run_id}/attempts/{self.run_attempt}")
            valid = (
                run.get("id") == self.run_id and run.get("run_attempt") == self.run_attempt
                and run.get("name") == WORKFLOW_NAME and run.get("path") == WORKFLOW_PATH
                and run.get("event") == "push" and run.get("status") == "completed"
                and run.get("conclusion") == "success" and run.get("head_branch") == BRANCH
                and str(run.get("head_sha") or "").lower() == self.trigger_sha
                and ((run.get("head_repository") or {}).get("full_name")) == REPOSITORY
            )
            if not valid:
                raise ControllerError("trigger_run_mismatch")
            trigger = self.trigger_sha
        else:
            if sha != self.trigger_sha:
                query = urllib.parse.urlencode({"branch": BRANCH, "event": "push", "status": "success", "per_page": "20"})
                runs = self._api(f"/actions/workflows/{urllib.parse.quote(WORKFLOW_PATH, safe='')}/runs?{query}")
                matched = [run for run in runs.get("workflow_runs", []) if isinstance(run, dict) and
                           str(run.get("head_sha") or "").lower() == sha and run.get("conclusion") == "success" and
                           run.get("event") == "push" and run.get("head_branch") == BRANCH]
                if not matched:
                    raise ControllerError("latest_main_not_green")
            trigger = sha
        self.calls += 1
        return GreenMain(trigger, sha, WORKFLOW_NAME, "push", BRANCH, "success")

    def _git(self, *args: str, text: bool = True) -> Any:
        result = subprocess.run(
            ["git", "-C", str(self.checkout), *args], shell=False, capture_output=True,
            timeout=60, check=False,
        )
        if result.returncode != 0 or len(result.stdout) > MAX_HTTP_BYTES:
            raise ControllerError("git_read_failed")
        return result.stdout.decode("utf-8") if text else result.stdout

    def is_ancestor(self, older: str, newer: str) -> bool:
        result = subprocess.run(
            ["git", "-C", str(self.checkout), "merge-base", "--is-ancestor", older, newer],
            shell=False, capture_output=True, timeout=30, check=False,
        )
        return result.returncode == 0

    def read_blob(self, sha: str, path: str) -> bytes:
        return self._git("show", f"{sha}:{path}", text=False)

    def list_tree(self, sha: str, prefix: str) -> dict[str, bytes]:
        raw = self._git("ls-tree", "-r", "--name-only", "-z", sha, "--", prefix, text=False)
        paths = [item.decode("utf-8") for item in raw.split(b"\0") if item]
        if len(paths) > 1000:
            raise ControllerError("artifact_tree_too_large")
        return {path: self.read_blob(sha, path) for path in paths}

    def checkout_detached(self, sha: str) -> Path:
        if self.checkout_head(self.checkout) != sha:
            raise ControllerError("checkout_head_mismatch")
        status = self._git("status", "--porcelain", "--untracked-files=all")
        if status:
            raise ControllerError("checkout_not_clean")
        return self.checkout

    def checkout_head(self, checkout: Path) -> str:
        value = self._git("rev-parse", "HEAD").strip().lower()
        return value if SAFE_SHA_RE.fullmatch(value) else ""

    def _registry_counts(self, sha: str) -> dict[str, int]:
        text = self.read_blob(sha, "site/deploy/hosted-skills.generated.mjs").decode("utf-8")
        counts: dict[str, int] = {}
        for slug in REGISTRY_ROW_RE.findall(text):
            counts[slug] = counts.get(slug, 0) + 1
        return counts

    def registry_slug_count(self, sha: str, slug: str) -> int:
        return self._registry_counts(sha).get(slug, 0)

    def registry_slug_counts(self, sha: str, slugs: set[str]) -> dict[str, int]:
        counts = self._registry_counts(sha)
        return {slug: counts.get(slug, 0) for slug in slugs}


class HttpFinalizationStore:
    def __init__(self, token: str, base_url: str = WORKER_BASE_URL, opener=urllib.request.urlopen):
        if not token or base_url != WORKER_BASE_URL:
            raise ControllerError("invalid_finalizer_store_configuration")
        self.token, self.base_url, self.opener = token, base_url, opener
        self.claims: dict[str, FinalizationClaim] = {}

    def _post(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any] | None]:
        return _request_json_stage(
            "finalizer_http_failed",
            self.base_url + path, method="POST", payload=payload,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            opener=self.opener,
        )

    def _claim(self, body: dict[str, Any] | None) -> FinalizationClaim | None:
        if not body or body.get("ok") is not True or not isinstance(body.get("finalization"), dict):
            raise ControllerError("invalid_finalizer_response")
        value = body["finalization"]
        try:
            claim = FinalizationClaim(
                id=value["id"], submission_id=value["submission_id"], slug=value["slug"],
                runtime=value["runtime"], target_sha=value["target_sha"], merge_sha=value["merge_sha"],
                head_sha=value["head_sha"], source_sha256=value["source_sha256"],
                artifact_hash=value["artifact_hash"], lease_expires_at=value["lease_expires_at"],
                attempts=int(value["attempts"]),
            )
        except (KeyError, TypeError, ValueError):
            raise ControllerError("invalid_finalizer_response") from None
        self.claims[claim.submission_id] = claim
        return claim

    def claim(self, target_sha: str) -> FinalizationClaim | None:
        status, body = self._post("/api/internal/finalizations/claim", {"target_sha": target_sha})
        if status == 204:
            return None
        if status != 200:
            code = f"finalizer_claim_http_{status}" if isinstance(status, int) and 100 <= status <= 599 else "finalizer_claim_failed"
            raise ControllerError(code)
        return self._claim(body)

    def resume_completed(self, target_sha: str) -> FinalizationClaim | None:
        status, body = self._post("/api/internal/finalizations/resume-completed", {"target_sha": target_sha})
        if status == 204:
            return None
        if status != 200:
            code = f"finalizer_resume_http_{status}" if isinstance(status, int) and 100 <= status <= 599 else "finalizer_resume_failed"
            raise ControllerError(code)
        return self._claim(body)

    def finalization_detail(self, finalization_id: str) -> dict[str, str]:
        status, body = self._post(f"/api/internal/finalizations/{finalization_id}/detail", {})
        if status != 200 or not body or body.get("ok") is not True or not isinstance(body.get("finalization"), dict):
            raise ControllerError("invalid_finalizer_response")
        return body["finalization"]

    def submission_detail(self, submission_id: str) -> dict[str, str]:
        claim = self.claims.get(submission_id)
        if not claim:
            raise ControllerError("invalid_finalizer_response")
        detail = self.finalization_detail(claim.id)
        return {"status": detail.get("submission_status", ""), "release_phase": detail.get("release_phase", "")}

    def required_registry_slugs(self) -> set[str]:
        status, body = self._post("/api/internal/finalizations/registry-slugs", {})
        slugs = body.get("slugs") if body else None
        if status != 200 or not isinstance(slugs, list) or any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(x)) for x in slugs):
            raise ControllerError("invalid_finalizer_response")
        return set(slugs)

    def provision_canary_identity(self) -> None:
        status, body = self._post("/api/internal/finalizations/canary-identity", {})
        if status != 200 or not body or body.get("ok") is not True:
            raise ControllerError("production_canary_provision_failed")

    def advance(self, claim: FinalizationClaim, status: str, failure_code: str | None = None) -> None:
        payload: dict[str, Any] = {"target_sha": claim.target_sha, "status": status}
        if failure_code:
            payload["failure_code"] = failure_code
        response_status, body = self._post(f"/api/internal/finalizations/{claim.id}/status", payload)
        if response_status != 200 or not body or body.get("ok") is not True:
            raise ControllerError("finalization_transition_failed")

    def record_effect(self, claim: FinalizationClaim, operation: str, receipt: dict[str, object]) -> None:
        status, body = self._post(
            f"/api/internal/finalizations/{claim.id}/effects",
            {"operation": operation, "target_sha": claim.target_sha, "receipt": receipt},
        )
        if status != 200 or not body or body.get("ok") is not True:
            raise ControllerError("finalization_effect_failed")

    def promote(self, claim: FinalizationClaim, release_gates: dict[str, object]) -> None:
        status, body = self._post(
            f"/api/internal/finalizations/{claim.id}/promote",
            {"target_sha": claim.target_sha, "release_gates": release_gates},
        )
        if status != 200 or not body or body.get("ok") is not True:
            raise ControllerError("finalization_promotion_failed")

    def mark_deployed(self, submission_id: str) -> None:
        status, body = self._post(
            f"/api/internal/submissions/{submission_id}/deployed", {"deployed_by": "trusted_finalizer"}
        )
        if status != 200 or not body or body.get("ok") is not True:
            raise ControllerError("finalization_deployed_failed")


class ProductionModalAdapter:
    def __init__(self, source_env: dict[str, str]):
        self.source_env = source_env
        self.checkouts: dict[str, Path] = {}

    def _transport(self, claim: FinalizationClaim, checkout: Path, mutate: bool = False):
        return ProductionCommandTransport(
            source_env=self.source_env, trusted_checkout=str(checkout), trusted_sha=claim.target_sha,
            allow_mutation=mutate,
        )

    def preflight(self, claim, checkout):
        self.checkouts[claim.id] = checkout
        rows = self._transport(claim, checkout).run_json(modal_preflight_call(checkout, claim.slug))
        names = {str(row.get("Name") or row.get("name") or "") for row in rows if isinstance(row, dict)}
        if MODAL_ENVIRONMENT not in names:
            raise ControllerError("modal_preflight_failed")

    def deploy(self, claim, checkout):
        transport = self._transport(claim, checkout, True)
        before = transport.run_json(modal_history_call(checkout, claim.slug))
        transport.run(modal_deploy_call(checkout, claim.slug, claim.target_sha))
        after = transport.run_json(modal_history_call(checkout, claim.slug))
        return asdict(modal_receipt(before, after, claim.slug, claim.target_sha, claim.artifact_hash))

    def canary(self, claim, checkout, deploy_receipt):
        endpoint = MODAL_CANARY_ORIGIN + "/v1/runs"
        payload = {"labels": [" Green Apple ", "green-apple", "Class 2B"], "prefix": "item"}
        owner = f"finalizer:{claim.submission_id}"
        headers = {
            "Content-Type": "application/json", "X-Omo-Owner-Id": owner,
            "Modal-Key": self.source_env.get("HOSTED_MODAL_PROXY_TOKEN_ID", ""),
            "Modal-Secret": self.source_env.get("HOSTED_MODAL_PROXY_TOKEN_SECRET", ""),
        }
        status, body = _request_json_stage(
            "modal_canary_http_failed",
            endpoint, method="POST", payload=payload, headers=headers, timeout=60, opener=MODAL_OPENER
        )
        if status != 202 or not body or not isinstance(body.get("result_url"), str):
            return {"status": "failed"}
        try:
            result_url = _modal_result_url(body["result_url"])
        except ControllerError:
            return {"status": "failed"}
        result = None
        for _ in range(30):
            poll_status, poll = _request_json_stage(
                "modal_canary_http_failed", result_url,
                headers=headers, timeout=30, opener=MODAL_OPENER
            )
            if poll_status == 200 and poll:
                result = poll
                break
            if poll_status != 202:
                return {"status": "failed"}
            time.sleep(1)
        identifiers = [item.get("identifier") for item in result.get("items", [])] if isinstance(result, dict) else []
        valid = (
            isinstance(result, dict) and result.get("input_count") == 3
            and result.get("unique_count") == 2 and result.get("duplicate_count") == 1
            and identifiers == ["ITEM_GREEN_APPLE", "ITEM_GREEN_APPLE", "ITEM_CLASS_2B"]
        )
        return {"status": "passed" if valid else "failed"}

    def rollback(self, claim, deploy_receipt):
        version = str(deploy_receipt.get("rollback_token") or "")
        checkout = self.checkouts.get(claim.id)
        if not checkout:
            raise ControllerError("rollback_checkout_missing")
        self._transport(claim, checkout, True).run(modal_rollback_call(checkout, claim.slug, version))
        return {"status": "passed"}


class ProductionCloudflareAdapter:
    def __init__(self, source_env: dict[str, str]):
        self.source_env = source_env
        self.checkouts: dict[str, Path] = {}

    def _transport(self, claim, checkout, mutate=False):
        return ProductionCommandTransport(
            source_env=self.source_env, trusted_checkout=str(checkout), trusted_sha=claim.target_sha,
            allow_mutation=mutate,
        )

    def preflight(self, claim, checkout):
        self.checkouts[claim.id] = checkout
        with tempfile.TemporaryDirectory(prefix="omo-worker-preflight-") as path:
            outdir = Path(path)
            os.chmod(outdir, 0o700)
            self._transport(claim, checkout).run(cloudflare_preflight_call(checkout, outdir))
            cloudflare_bundle_sha256(outdir)

    def verify_registry(self, claim, checkout):
        return {"status": "passed"}

    def deploy_worker(self, claim, checkout):
        transport = self._transport(claim, checkout, True)
        versions_before = transport.run_json(cloudflare_versions_call(checkout))
        deployments_before = transport.run_json(cloudflare_deployments_call(checkout))
        transport.run(cloudflare_deploy_call(checkout, claim.target_sha))
        versions_after = transport.run_json(cloudflare_versions_call(checkout))
        deployments_after = transport.run_json(cloudflare_deployments_call(checkout))
        return asdict(cloudflare_receipt(
            versions_before, versions_after, deployments_before, deployments_after,
            claim.target_sha, claim.artifact_hash,
        ))

    def smoke_worker(self, claim, deploy_receipt):
        request = urllib.request.Request(f"{PUBLIC_ORIGIN}/api/me", method="GET")
        try:
            urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as error:
            return {"status": "passed"} if error.code == 401 else {"status": "failed"}
        except Exception:
            return {"status": "failed"}
        return {"status": "failed"}

    def rollback_worker(self, claim, deploy_receipt):
        checkout = self.checkouts.get(claim.id)
        if not checkout:
            raise ControllerError("rollback_checkout_missing")
        self._transport(claim, checkout, True).run(
            cloudflare_rollback_call(checkout, str(deploy_receipt.get("rollback_token") or ""), claim.target_sha)
        )
        return {"status": "passed"}


class ProductionPublicAdapter:
    def __init__(self, store: HttpFinalizationStore, api_key: str):
        if not re.fullmatch(r"omo_[0-9a-f]{32}", api_key or ""):
            raise ControllerError("invalid_production_canary_key")
        self.store, self.api_key = store, api_key

    def preflight(self, claim):
        self.store.provision_canary_identity()

    def seed_submission(self, checkout: Path) -> dict[str, str]:
        self.store.provision_canary_identity()
        source_path = checkout / "containers" / "label-normalizer-canary" / "source" / "SKILL.md"
        try:
            resolved = source_path.resolve(strict=True)
        except OSError:
            raise ControllerError("production_canary_source_invalid")
        if resolved != source_path or not resolved.is_file():
            raise ControllerError("production_canary_source_invalid")
        try:
            size = resolved.stat().st_size
            if not 1 <= size <= CANARY_SOURCE_MAX_BYTES:
                raise ControllerError("production_canary_source_invalid")
            with resolved.open("rb") as handle:
                raw = handle.read(CANARY_SOURCE_MAX_BYTES + 1)
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != CANARY_SOURCE_SHA256:
                raise ControllerError("production_canary_source_invalid")
            source = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            raise ControllerError("production_canary_source_invalid") from None
        status, body = _request_json_stage(
            "public_canary_http_failed", f"{PUBLIC_ORIGIN}/api/submit", method="POST",
            payload={
                "name": "Label normalizer canary", "content": source,
                "visibility": "public", "runtime_preference": "modal-hosted",
            },
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"}, timeout=30,
        )
        submission_id = str((body or {}).get("id") or "")
        if status != 202 or (body or {}).get("slug") != MODAL_ALLOWED_SLUG or not re.fullmatch(
            r"sub_[0-9a-f]{32}", submission_id
        ):
            raise ControllerError("production_canary_seed_failed")
        return {"status": "queued", "submission_id": submission_id}

    def _dispatch(self, claim):
        key = hashlib.sha256(f"v0.1:{claim.target_sha}:{claim.artifact_hash}".encode()).hexdigest()[:40]
        payload = {"slug": MODAL_ALLOWED_SLUG, "input": {
            "labels": [" Green Apple ", "green-apple", "Class 2B"], "prefix": "item",
        }}
        headers = {"X-API-Key": self.api_key, "Idempotency-Key": f"v0.1-{key}", "Content-Type": "application/json"}
        return _request_json_stage(
            "public_canary_http_failed", f"{PUBLIC_ORIGIN}/api/run",
            method="POST", payload=payload, headers=headers, timeout=60,
        ), headers, payload

    def verify_public(self, claim, checkout):
        (status, body), headers, payload = self._dispatch(claim)
        if status != 202 or not body or not re.fullmatch(r"run_[0-9a-f]{32}", str(body.get("run_id") or "")):
            return {"status": "failed"}
        run_id = body["run_id"]
        terminal = None
        for _ in range(60):
            poll_status, poll = _request_json_stage(
                "public_canary_http_failed", f"{PUBLIC_ORIGIN}/api/run/{run_id}",
                headers={"X-API-Key": self.api_key}, timeout=30
            )
            if poll_status == 200 and poll and poll.get("status") in {"succeeded", "failed", "refunded"}:
                terminal = poll
                break
            time.sleep(2)
        if not terminal or terminal.get("status") != "succeeded":
            return {"status": "failed"}
        result = terminal.get("result") or terminal.get("output") or {}
        identifiers = [item.get("identifier") for item in result.get("items", [])] if isinstance(result, dict) else []
        if not (
            isinstance(result, dict) and result.get("input_count") == 3
            and result.get("unique_count") == 2 and result.get("duplicate_count") == 1
            and identifiers == ["ITEM_GREEN_APPLE", "ITEM_GREEN_APPLE", "ITEM_CLASS_2B"]
        ):
            return {"status": "failed"}
        (replay_status, replay), _, _ = self._dispatch(claim)
        if (replay_status not in {200, 202} or not replay or replay.get("run_id") != run_id or
                replay.get("idempotent_replay") is not True):
            return {"status": "failed"}
        return {"status": "passed"}

    def verify_publication(self, claim, checkout):
        request = urllib.request.Request(
            f"{PUBLIC_ORIGIN}/run.html?slug={MODAL_ALLOWED_SLUG}", headers={"User-Agent": "OmoProductionFinalizer/1.0"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read(256 * 1024)
                ok = response.status == 200 and MODAL_ALLOWED_SLUG.encode() in raw
        except Exception:
            ok = False
        return {"status": "published" if ok else "failed"}


def run_once(args, environ: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(environ or os.environ)
    checkout = Path(env.get("GITHUB_WORKSPACE", ".")) / "target"
    mainline = GitHubMainlineAdapter(
        checkout, args.trigger_sha, int(args.run_id), int(args.run_attempt),
        env.get("GITHUB_TOKEN", ""),
    )
    store = HttpFinalizationStore(env.get("RELEASE_FINALIZER_TOKEN", ""))
    modal = ProductionModalAdapter(env)
    cloudflare = ProductionCloudflareAdapter(env)
    public = ProductionPublicAdapter(store, env.get("PRODUCTION_CANARY_API_KEY", ""))
    result = run_finalizer(mainline, store, modal, cloudflare, public, targets=TARGETS)
    if result.get("status") == "idle":
        trusted_checkout = mainline.checkout_detached(result["target_sha"])
        seeded = public.seed_submission(trusted_checkout)
        return {**seeded, "status": "seeded", "target_sha": result["target_sha"]}
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trigger-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    args = parser.parse_args(argv)
    if not SAFE_SHA_RE.fullmatch(args.trigger_sha) or not SAFE_ID_RE.fullmatch(args.run_id) or not SAFE_ID_RE.fullmatch(args.run_attempt):
        print('{"error":"invalid_controller_input"}')
        return 2
    try:
        print(json.dumps(run_once(args), separators=(",", ":"), sort_keys=True))
        return 0
    except (ControllerError, FinalizerError) as error:
        print(json.dumps({"error": getattr(error, "code", "controller_failed")}, separators=(",", ":")))
        return 1
    except Exception:
        print('{"error":"controller_failed"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
