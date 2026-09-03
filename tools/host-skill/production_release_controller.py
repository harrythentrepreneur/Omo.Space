#!/usr/bin/env python3
"""Concrete trusted production controller for Issue #141.

Targets, repository, branch, workflow, provider apps and public origin are fixed.
Only an immutable workflow-run identity is accepted from the CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence

from production_release_adapters import (
    AdapterError,
    CLOUDFLARE_BUILDER_CRON,
    CLOUDFLARE_TARGET,
    MODAL_ALLOWED_SLUG,
    MODAL_ENVIRONMENT,
    MODAL_TARGET,
    PUBLIC_ORIGIN,
    cloudflare_active_version,
    cloudflare_target_present,
    cloudflare_bundle_sha256,
    cloudflare_deploy_call,
    cloudflare_deployments_call,
    cloudflare_preflight_call,
    cloudflare_receipt,
    cloudflare_rollback_call,
    cloudflare_versions_call,
    modal_deploy_call,
    modal_apps_call,
    modal_app_stopped,
    modal_app_state,
    modal_history_snapshot,
    modal_history_call,
    modal_preflight_call,
    modal_receipt,
    modal_rollback_call,
    modal_stop_call,
    modal_target,
)
from production_release_transport import ProductionCommandTransport
from host import COMPILER as HOST_COMPILER, pure_data_public_output_schema, single_llm_public_output_schema
from release_finalizer import (
    DeploymentTargets,
    FailedFinalization,
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
CANARY_CONTRACT_MAX_BYTES = 256 * 1024
MAX_PAID_CANARY_USD = Decimal("0.10")
CANARY_SOURCES = (
    {
        "name": "V02 Release Label Sorter",
        "slug": "v02-release-label-sorter",
        "path": "tools/host-skill/canaries/v02-release-label-sorter/SKILL.md",
        "sha256": "d52e7984117e3986f0ce2a1a765c01b57d9f9b2b029a2c493571641c5ac605e9",
    },
    {
        "name": "V02 Support Urgency Classifier",
        "slug": "v02-support-urgency-classifier",
        "path": "tools/host-skill/canaries/v02-support-urgency-classifier/SKILL.md",
        "sha256": "096a9402ae463392db8e840b1a2b256d2159d1a086d308c2831356df5c9a7d5c",
    },
)
AUTONOMY_PROOF_SOURCES = (
    {
        "name": "Autonomous Priority Label Sorter",
        "slug": "autonomous-priority-label-sorter",
        "path": "tools/host-skill/canaries/autonomous-priority-label-sorter/SKILL.md",
        "sha256": "f72d2583a0c0969956a58dda72c740e38930b4eef3cc35962f772f7ccbc26a1b",
    },
    {
        "name": "Autonomous Reply Urgency Classifier",
        "slug": "autonomous-reply-urgency-classifier",
        "path": "tools/host-skill/canaries/autonomous-reply-urgency-classifier/SKILL.md",
        "sha256": "26dbb34409f92ade194064d7f491ab4cbfca823fda90d095c54ae3a5f1dc4a51",
    },
)
SUBMISSION_SEED_SOURCES = CANARY_SOURCES + AUTONOMY_PROOF_SOURCES
CANARY_SOURCE_SLUGS = frozenset(item["slug"] for item in CANARY_SOURCES)
SUBMISSION_SEED_SLUGS = frozenset(item["slug"] for item in SUBMISSION_SEED_SOURCES)
MAX_FINALIZATION_TARGETS = 1000
TARGETS = DeploymentTargets("cognition-{slug}", MODAL_ENVIRONMENT, CLOUDFLARE_TARGET, "production")
MODAL_CANARY_ORIGIN = "https://omo-space--cognition-label-normalizer-canary-api.modal.run"


@dataclass(frozen=True)
class RecoveryCandidate:
    target_sha: str
    finalization_id: str
    mode: str


def derive_finalization_targets(mainline: Any, target_sha: str) -> list[dict[str, str]]:
    """Derive creator release identities from an exact trusted main tree.

    Generated files are parsed only as bounded data. No candidate module is
    imported or executed. The Worker still requires the exact slug/hash pair
    before an authoritative row can be claimed.
    """
    if not SAFE_SHA_RE.fullmatch(str(target_sha or "")):
        raise ControllerError("finalization_target_tree_invalid")
    try:
        tree: dict[str, bytes] = {}
        for prefix in ("containers", "packages/skill-to-modal/profiles", "site/run-manifests"):
            values = mainline.list_tree(target_sha, prefix)
            if not isinstance(values, dict):
                raise ValueError
            for path, raw in values.items():
                if not isinstance(path, str) or not isinstance(raw, bytes) or path in tree:
                    raise ValueError
                tree[path] = raw
        source_re = re.compile(r"^containers/([a-z0-9]+(?:-[a-z0-9]+)*)/source/SKILL\.md$")
        slugs = sorted(match.group(1) for path in tree if (match := source_re.fullmatch(path)))
        if not slugs or len(slugs) > MAX_FINALIZATION_TARGETS or len(slugs) != len(set(slugs)):
            raise ValueError
        targets: list[dict[str, str]] = []
        for slug in slugs:
            source = tree[f"containers/{slug}/source/SKILL.md"]
            if not 1 <= len(source) <= CANARY_SOURCE_MAX_BYTES:
                raise ValueError
            source_hash = hashlib.sha256(source).hexdigest()
            profile_raw = tree.get(f"packages/skill-to-modal/profiles/{slug}.json")
            if profile_raw is None:
                continue
            profile = _strict_json_bytes(profile_raw)
            # Legacy/manual profiles are outside the autonomous v2 creator
            # pipeline. They remain live but are never claimed by this path.
            if not isinstance(profile, dict) or profile.get("authoring_spec_version") != "omo.profile-authoring-spec/v2":
                continue
            hosted = _strict_json_bytes(tree[f"containers/{slug}/hosted-profile.json"])
            manifest = _strict_json_bytes(tree[f"containers/{slug}/manifest.json"])
            run_manifest = _strict_json_bytes(tree[f"site/run-manifests/{slug}.json"])
            runtime = hosted.get("runtime") if isinstance(hosted, dict) else None
            hosted_run = hosted.get("run_manifest") if isinstance(hosted, dict) else None
            if (
                profile.get("slug") != slug
                or profile.get("reviewed_source_sha256") != source_hash
                or not isinstance(manifest, dict) or manifest.get("slug") != slug
                or manifest.get("source_sha256") != source_hash
                or not isinstance(hosted, dict) or hosted.get("schema_version") != "omo.hosted-profile/v1"
                or hosted.get("generator") != "tools/host-skill/1.0.0"
                or not isinstance(runtime, dict) or runtime.get("slug") != slug
                or runtime.get("container_slug") != slug
                or not isinstance(run_manifest, dict) or run_manifest.get("slug") != slug
                or run_manifest.get("container_slug") != slug
                or run_manifest.get("ready") is not True or run_manifest.get("chargeable") is not True
                or hosted_run != run_manifest
            ):
                raise ValueError
            targets.append({"slug": slug, "source_sha256": source_hash})
        if not targets:
            raise ValueError
        return targets
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise ControllerError("finalization_target_tree_invalid") from None


def _validate_recovery_receipt(value: object, provider: str, target_sha: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ControllerError("invalid_recovery_plan")
    required = {
        "artifact_hash", "environment", "previous_version_id", "provider", "reused",
        "rollback_token", "status", "target", "target_sha", "version_id",
    }
    target_value = str(value.get("target") or "")
    if provider == "modal":
        slug = target_value.removeprefix("cognition-")
        try:
            expected_target = modal_target(slug)
        except AdapterError:
            raise ControllerError("invalid_recovery_plan") from None
    else:
        expected_target = CLOUDFLARE_TARGET
    expected_environment = MODAL_ENVIRONMENT if provider == "modal" else "production"
    previous = value.get("previous_version_id")
    reused = value.get("reused")
    version_re = r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
    if (
        set(value) != required or value.get("provider") != provider
        or value.get("target") != expected_target or value.get("environment") != expected_environment
        or value.get("target_sha") != target_sha or value.get("status") != "passed"
        or not re.fullmatch(r"[0-9a-f]{64}", str(value.get("artifact_hash") or ""))
        or not re.fullmatch(version_re, str(value.get("version_id") or ""))
        or type(reused) is not bool
        or (previous is not None and not re.fullmatch(version_re, str(previous)))
        or value.get("rollback_token") != previous
        or (reused is True and previous is not None)
        or (reused is False and previous is None)
    ):
        raise ControllerError("invalid_recovery_plan")
    return value


def _validate_recovery_plan(value: object, target_sha: str, finalization_id: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"target_sha", "finalization_id", "modal", "cloudflare"}
        or value.get("target_sha") != target_sha
        or value.get("finalization_id") != finalization_id
    ):
        raise ControllerError("invalid_recovery_plan")
    for provider in ("modal", "cloudflare"):
        item = value.get(provider)
        if not isinstance(item, dict) or set(item) != {"receipt", "expected_active_version_id"}:
            raise ControllerError("invalid_recovery_plan")
        receipt = _validate_recovery_receipt(item.get("receipt"), provider, target_sha)
        expected = receipt["version_id"] if provider == "modal" or receipt["reused"] else receipt["previous_version_id"]
        if item.get("expected_active_version_id") != expected:
            raise ControllerError("invalid_recovery_plan")
    return value


def recover_rolled_back_finalization(
    mainline, store, modal, cloudflare, target_sha: str, finalization_id: str,
) -> dict[str, str]:
    if not SAFE_SHA_RE.fullmatch(target_sha):
        raise ControllerError("invalid_recovery_target")
    latest = mainline.latest_green()
    if (
        latest.workflow != WORKFLOW_NAME or latest.event != "push" or latest.branch != BRANCH
        or latest.conclusion != "success" or latest.trigger_sha != latest.target_sha
        or not SAFE_SHA_RE.fullmatch(latest.target_sha)
    ):
        raise ControllerError("invalid_green_main")
    if not mainline.is_ancestor(target_sha, latest.target_sha):
        raise ControllerError("recovery_target_not_ancestor")
    plan = store.recovery_plan(target_sha, finalization_id)
    _validate_recovery_plan(plan, target_sha, finalization_id)
    checkout = mainline.checkout_detached(latest.target_sha)
    modal_name = str(plan["modal"]["receipt"].get("target") or "")
    modal_slug = modal_name.removeprefix("cognition-")
    if modal_target(modal_slug) != modal_name:
        raise ControllerError("modal_recovery_readback_mismatch")
    if modal.active_version(checkout, latest.target_sha, modal_slug) != plan["modal"]["expected_active_version_id"]:
        raise ControllerError("modal_recovery_readback_mismatch")
    if cloudflare.active_version(checkout, latest.target_sha) != plan["cloudflare"]["expected_active_version_id"]:
        raise ControllerError("cloudflare_recovery_readback_mismatch")
    if not store.recover_rolled_back(target_sha, finalization_id):
        raise ControllerError("recovery_conflict")
    return {"status": "ready_for_deploy", "target_sha": latest.target_sha}


def recover_failed_before_run(mainline, store, modal, cloudflare) -> dict[str, str] | None:
    candidate = store.recovery_candidate()
    if candidate is None:
        return None
    if candidate.mode == "resume_no_effect":
        if not store.resume_failed(candidate.target_sha, candidate.finalization_id):
            raise ControllerError("failed_finalization_resume_conflict")
        return {"status": "ready_for_deploy", "target_sha": candidate.target_sha}
    if candidate.mode == "verify_then_retry":
        return recover_rolled_back_finalization(
            mainline, store, modal, cloudflare, candidate.target_sha, candidate.finalization_id,
        )
    raise ControllerError("invalid_recovery_candidate")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


MODAL_OPENER = urllib.request.build_opener(_NoRedirect()).open


class ControllerError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _strict_json_bytes(raw: bytes) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate key")
            value[key] = item
        return value

    def finite_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("non-finite number")
        return parsed

    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=object_pairs,
        parse_float=finite_float,
        parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
    )


def _read_bounded_regular_file(root: Path, relative: str, maximum: int) -> bytes:
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise OSError("unsafe relative path")
    resolved_root = root.resolve(strict=True)
    root_fd = os.open(resolved_root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    current_fd = root_fd
    try:
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
            if index < len(parts) - 1:
                flags |= os.O_DIRECTORY
            next_fd = os.open(part, flags, dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        info = os.fstat(current_fd)
        if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= maximum:
            raise OSError("invalid regular file")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(current_fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) != info.st_size:
            raise OSError("file changed while reading")
        return raw
    finally:
        if current_fd != root_fd:
            os.close(current_fd)
        os.close(root_fd)


def _canary_json(checkout: Path, relative: str) -> Any:
    try:
        raw = _read_bounded_regular_file(checkout, relative, CANARY_CONTRACT_MAX_BYTES)
        return _strict_json_bytes(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise ControllerError("public_canary_contract_invalid") from None


def _schema_has_reference(value: Any) -> bool:
    if isinstance(value, dict):
        return "$ref" in value or "$dynamicRef" in value or any(
            _schema_has_reference(child) for child in value.values()
        )
    if isinstance(value, list):
        return any(_schema_has_reference(child) for child in value)
    return False


def _claim_canary_contract(claim: FinalizationClaim | str, checkout: Path) -> dict[str, Any]:
    slug = str(claim if isinstance(claim, str) else claim.slug or "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ControllerError("public_canary_contract_invalid")
    prefix = f"containers/{slug}"
    profile = _canary_json(checkout, f"packages/skill-to-modal/profiles/{slug}.json")
    hosted = _canary_json(checkout, f"{prefix}/hosted-profile.json")
    container_manifest = _canary_json(checkout, f"{prefix}/manifest.json")
    cases = _canary_json(checkout, f"{prefix}/tests/cases.json")
    input_schema = _canary_json(checkout, f"{prefix}/schemas/input.json")
    output_schema = _canary_json(checkout, f"{prefix}/schemas/output.json")
    happy = cases.get("happy_path") if isinstance(cases, dict) else None
    run_manifest = hosted.get("run_manifest") if isinstance(hosted, dict) else None
    catalog = hosted.get("catalog") if isinstance(hosted, dict) else None
    if not isinstance(profile, dict):
        raise ControllerError("public_canary_contract_invalid")
    compiler_owned_profile = (
        profile.get("execution_kind") == "pure_data"
        or HOST_COMPILER.is_supported_profile_authoring_spec_version(
            profile.get("authoring_spec_version")
        )
    )
    try:
        if profile.get("execution_kind") == "pure_data":
            public_output_schema = pure_data_public_output_schema(profile)
        elif (
            profile.get("execution_kind") == "single_llm"
            and compiler_owned_profile
        ):
            public_output_schema = single_llm_public_output_schema(profile)
        else:
            public_output_schema = output_schema
    except (KeyError, TypeError, ValueError):
        raise ControllerError("public_canary_contract_invalid") from None
    if (
        not isinstance(profile, dict) or profile.get("slug") != slug
        or profile.get("execution_kind") not in {"pure_data", "single_llm", "skill_builder"}
        or not isinstance(happy, dict) or set(happy) != {"input", "output"}
        or profile.get("happy_path") != happy
        or (compiler_owned_profile and profile.get("input_schema") != input_schema)
        or (compiler_owned_profile and profile.get("output_schema") != output_schema)
        or _schema_has_reference(input_schema) or _schema_has_reference(output_schema)
        or not isinstance(container_manifest, dict)
        or container_manifest.get("input_schema") != input_schema
        or container_manifest.get("output_schema") != output_schema
        or not isinstance(run_manifest, dict) or run_manifest.get("slug") != slug
        or run_manifest.get("container_slug") != slug or run_manifest.get("ready") is not True
        or run_manifest.get("chargeable") is not True
        or run_manifest.get("input_schema_source") != f"{prefix}/schemas/input.json"
        or run_manifest.get("output_schema_source") != f"{prefix}/schemas/output.json"
        or run_manifest.get("input_schema") != input_schema
        or run_manifest.get("output_schema") != public_output_schema
        or not isinstance(catalog, dict) or catalog.get("slug") != slug
    ):
        raise ControllerError("public_canary_contract_invalid")
    try:
        price = Decimal(str(run_manifest.get("price_usd")))
        catalog_price = Decimal(str(catalog.get("runPrice")))
    except (InvalidOperation, TypeError, ValueError):
        raise ControllerError("public_canary_contract_invalid") from None
    cost_cents = price * 100
    if (
        price != catalog_price or price <= 0 or price > MAX_PAID_CANARY_USD
        or cost_cents != cost_cents.to_integral_value()
    ):
        raise ControllerError("public_canary_contract_invalid")
    try:
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(input_schema)
        Draft202012Validator.check_schema(output_schema)
        Draft202012Validator(input_schema).validate(happy["input"])
        Draft202012Validator(output_schema).validate(happy["output"])
    except Exception:
        raise ControllerError("public_canary_contract_invalid") from None
    return {
        "slug": slug,
        "execution_kind": profile["execution_kind"],
        "transport_bound": compiler_owned_profile,
        "input": happy["input"],
        "expected_output": happy["output"],
        "output_schema": output_schema,
        "public_output_schema": public_output_schema,
        "price_usd": price,
        "cost_cents": int(cost_cents),
    }


def _modal_result_url(value: object, origin: str = MODAL_CANARY_ORIGIN) -> str:
    raw = str(value or "").strip()
    parsed = None
    try:
        joined = urllib.parse.urljoin(origin + "/v1/runs", raw)
        parsed = urllib.parse.urlsplit(joined)
        query = urllib.parse.parse_qs(parsed.query, strict_parsing=True)
        valid = (
            parsed.scheme == "https" and parsed.hostname == urllib.parse.urlsplit(origin).hostname
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
        value = _strict_json_bytes(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise ControllerError("http_response_invalid") from None
    if not isinstance(value, dict):
        raise ControllerError("http_response_invalid")
    return value


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: object | None = None,
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
        "cloudflare_schedule_http_failed",
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

    def trees_equal(self, left: str, right: str) -> bool:
        if not SAFE_SHA_RE.fullmatch(left) or not SAFE_SHA_RE.fullmatch(right):
            return False
        left_tree = self._git("rev-parse", f"{left}^{{tree}}").strip().lower()
        right_tree = self._git("rev-parse", f"{right}^{{tree}}").strip().lower()
        return bool(SAFE_SHA_RE.fullmatch(left_tree) and left_tree == right_tree)

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
    def __init__(
        self, token: str, base_url: str = WORKER_BASE_URL, opener=urllib.request.urlopen,
        targets: list[dict[str, str]] | None = None,
    ):
        if not token or base_url != WORKER_BASE_URL:
            raise ControllerError("invalid_finalizer_store_configuration")
        self.token, self.base_url, self.opener = token, base_url, opener
        self.claims: dict[str, FinalizationClaim] = {}
        raw_targets = targets if targets is not None else [
            {"slug": item["slug"], "source_sha256": item["sha256"]} for item in CANARY_SOURCES
        ]
        if not isinstance(raw_targets, list) or not 1 <= len(raw_targets) <= MAX_FINALIZATION_TARGETS:
            raise ControllerError("invalid_finalizer_store_configuration")
        normalized: list[dict[str, str]] = []
        seen: set[str] = set()
        for target in raw_targets:
            slug = str(target.get("slug") if isinstance(target, dict) else "")
            source_hash = str(target.get("source_sha256") if isinstance(target, dict) else "")
            if (
                not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)
                or not re.fullmatch(r"[0-9a-f]{64}", source_hash)
                or slug in seen
                or set(target) != {"slug", "source_sha256"}
            ):
                raise ControllerError("invalid_finalizer_store_configuration")
            seen.add(slug)
            normalized.append({"slug": slug, "source_sha256": source_hash})
        self.targets = sorted(normalized, key=lambda item: item["slug"])

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

    def _targets(self) -> list[dict[str, str]]:
        return [dict(item) for item in self.targets]

    def claim(self, target_sha: str) -> FinalizationClaim | None:
        status, body = self._post(
            "/api/internal/finalizations/claim",
            {"target_sha": target_sha, "targets": self._targets()},
        )
        if status == 204:
            return None
        if status != 200:
            code = f"finalizer_claim_http_{status}" if isinstance(status, int) and 100 <= status <= 599 else "finalizer_claim_failed"
            raise ControllerError(code)
        return self._claim(body)

    def eligibility(self, target_sha: str) -> list[dict[str, Any]]:
        status, body = self._post(
            "/api/internal/finalizations/eligibility",
            {"target_sha": target_sha, "targets": self._targets()},
        )
        rows = body.get("eligibility") if isinstance(body, dict) else None
        boolean_fields = {
            "source_sha256_present", "published_slug_present", "workflow_version_present",
            "build_evidence_present", "release_issue_url_present", "release_pr_url_present",
            "release_pr_number_present", "release_branch_present", "release_head_sha_present",
            "release_merge_sha_present", "release_artifact_hash_present",
            "finalization_target_matches", "finalization_lease_expired", "finalization_available",
            "claimable",
        }
        expected = {
            "submission_id", "slug", "status", "release_phase", "selected_runtime",
            "finalization_status", *boolean_fields,
        }
        if status != 200:
            code = f"finalizer_eligibility_http_{status}" if isinstance(status, int) and 100 <= status <= 599 else "finalizer_eligibility_failed"
            raise ControllerError(code)
        if not isinstance(body, dict) or set(body) != {"ok", "eligibility"} or body.get("ok") is not True:
            raise ControllerError("invalid_finalizer_eligibility_envelope")
        if not isinstance(rows, list):
            raise ControllerError("invalid_finalizer_eligibility_rows")
        if len(rows) > 100:
            raise ControllerError("invalid_finalizer_eligibility_count")
        target_slugs = {item["slug"] for item in self.targets}
        seen_ids: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != expected:
                raise ControllerError("invalid_finalizer_eligibility_shape")
            submission_id = str(row.get("submission_id") or "")
            if not re.fullmatch(r"sub_[A-Za-z0-9_-]{8,100}", submission_id) or submission_id in seen_ids:
                raise ControllerError("invalid_finalizer_eligibility_identity")
            if row.get("slug") not in target_slugs:
                raise ControllerError("invalid_finalizer_eligibility_slug")
            if (
                row.get("status") not in {"queued", "processing", "needs_review", "ready_for_deploy", "ready_for_publish", "deployed", "failed"}
                or row.get("release_phase") not in {"compiled", "pr_open", "ci_passed", "merged_verified", "promoted", "failed", None}
                or row.get("selected_runtime") not in {"worker-native", "modal-hosted", None}
                or row.get("finalization_status") not in {"claimed", "deploying_modal", "deploying_worker", "verifying_public", "failed", "completed", "rolled_back", "invalid", None}
            ):
                raise ControllerError("invalid_finalizer_eligibility_enum")
            if any(type(row.get(field)) is not bool for field in boolean_fields):
                raise ControllerError("invalid_finalizer_eligibility_boolean")
            seen_ids.add(submission_id)
        return rows

    def resume_completed(self, target_sha: str) -> FinalizationClaim | None:
        status, body = self._post("/api/internal/finalizations/resume-completed", {"target_sha": target_sha})
        if status == 204:
            return None
        if status != 200:
            code = f"finalizer_resume_http_{status}" if isinstance(status, int) and 100 <= status <= 599 else "finalizer_resume_failed"
            raise ControllerError(code)
        return self._claim(body)

    def inspect_failed(self, target_sha: str) -> FailedFinalization | None:
        status, body = self._post("/api/internal/finalizations/failed", {"target_sha": target_sha})
        if status == 204:
            return None
        if status != 200 or not body or body.get("ok") is not True or not isinstance(body.get("finalization"), dict):
            raise ControllerError("invalid_finalizer_response")
        value = body["finalization"]
        expected = {
            "id", "status", "failure_code", "submission_id", "submission_status", "release_phase",
            "target_sha", "source_sha256", "head_sha", "merge_sha", "artifact_hash", "attempts",
            "modal_receipt_present", "worker_receipt_present",
        }
        try:
            failed = FailedFinalization(**value)
        except (TypeError, ValueError):
            raise ControllerError("invalid_finalizer_response") from None
        if (
            set(value) != expected or not re.fullmatch(r"fin_[0-9a-f]{32}", failed.id)
            or not re.fullmatch(r"sub_[A-Za-z0-9_-]{8,100}", failed.submission_id)
            or failed.status != "failed" or failed.failure_code not in {
                "credential_preflight_failed", "modal_preflight_failed", "worker_preflight_failed",
                "public_preflight_failed", "modal_deploy_failed", "modal_canary_failed",
                "worker_deploy_failed", "worker_smoke_failed", "public_verification_failed",
                "superseded_main", "internal_finalizer_failed", "release_head_not_ancestor",
            }
            or failed.submission_status not in {"ready_for_deploy", "failed"}
            or failed.release_phase != "merged_verified" or failed.target_sha != target_sha
            or not SAFE_SHA_RE.fullmatch(failed.target_sha) or not SAFE_SHA_RE.fullmatch(failed.head_sha)
            or not SAFE_SHA_RE.fullmatch(failed.merge_sha)
            or not re.fullmatch(r"[0-9a-f]{64}", failed.source_sha256)
            or not re.fullmatch(r"[0-9a-f]{64}", failed.artifact_hash)
            or type(failed.attempts) is not int or failed.attempts < 1
            or type(failed.modal_receipt_present) is not bool or type(failed.worker_receipt_present) is not bool
        ):
            raise ControllerError("invalid_finalizer_response")
        return failed

    def resume_failed(self, target_sha: str, finalization_id: str) -> bool:
        status, body = self._post(
            "/api/internal/finalizations/resume-failed",
            {"target_sha": target_sha, "finalization_id": finalization_id},
        )
        if status != 200 or body != {"ok": True, "status": "ready_for_deploy"}:
            code = f"finalizer_failed_resume_http_{status}" if isinstance(status, int) and 100 <= status <= 599 else "finalizer_failed_resume_failed"
            raise ControllerError(code)
        return True

    def recovery_candidate(self) -> RecoveryCandidate | None:
        status, body = self._post("/api/internal/finalizations/recovery-candidate", {})
        if status in {204, 404}:
            return None
        value = body.get("recovery") if status == 200 and body and body.get("ok") is True else None
        if (
            not isinstance(value, dict) or set(value) != {"target_sha", "finalization_id", "mode"}
            or not SAFE_SHA_RE.fullmatch(str(value.get("target_sha") or ""))
            or not re.fullmatch(r"fin_[0-9a-f]{32}", str(value.get("finalization_id") or ""))
            or value.get("mode") not in {"resume_no_effect", "verify_then_retry"}
        ):
            raise ControllerError("invalid_recovery_candidate")
        return RecoveryCandidate(
            target_sha=value["target_sha"], finalization_id=value["finalization_id"], mode=value["mode"],
        )

    def recovery_plan(self, target_sha: str, finalization_id: str) -> dict[str, Any]:
        status, body = self._post(
            "/api/internal/finalizations/recovery-plan",
            {"target_sha": target_sha, "finalization_id": finalization_id},
        )
        if status != 200 or not body or body.get("ok") is not True:
            raise ControllerError("invalid_recovery_plan")
        plan = body.get("recovery")
        _validate_recovery_plan(plan, target_sha, finalization_id)
        return plan

    def recover_rolled_back(self, target_sha: str, finalization_id: str) -> bool:
        status, body = self._post(
            "/api/internal/finalizations/recover-rolled-back",
            {"target_sha": target_sha, "finalization_id": finalization_id},
        )
        if status != 200 or body != {"ok": True, "status": "ready_for_deploy"}:
            raise ControllerError("recovery_conflict")
        return True

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

    def active_version(self, checkout: Path, target_sha: str, slug: str = MODAL_ALLOWED_SLUG) -> str:
        transport = ProductionCommandTransport(
            source_env=self.source_env, trusted_checkout=str(checkout), trusted_sha=target_sha,
        )
        history = modal_history_snapshot(
            transport.run_json(modal_history_call(checkout, slug))
        )
        if not history:
            raise ControllerError("modal_recovery_readback_mismatch")
        return history[0][0]

    def deploy(self, claim, checkout):
        transport = self._transport(claim, checkout, True)
        state = modal_app_state(transport.run_json(modal_apps_call(checkout, claim.slug)), claim.slug)
        before = [] if state == "absent" else transport.run_json(modal_history_call(checkout, claim.slug))
        before_history = modal_history_snapshot(before)
        if state != "stopped" and any(tag == claim.target_sha for _, tag in before_history):
            after = transport.run_json(modal_history_call(checkout, claim.slug))
            return asdict(modal_receipt(
                before, after, claim.slug, claim.target_sha, claim.artifact_hash
            ))
        transport.run(modal_deploy_call(checkout, claim.slug, claim.target_sha))
        after = transport.run_json(modal_history_call(checkout, claim.slug))
        if modal_app_state(transport.run_json(modal_apps_call(checkout, claim.slug)), claim.slug) not in {"deployed", "running"}:
            raise AdapterError("production_readback_failed")
        if state == "stopped":
            after_history = modal_history_snapshot(after)
            if len(after_history) != len(before_history) + 1 or after_history[1:] != before_history:
                raise AdapterError("production_readback_failed")
            return asdict(modal_receipt([], [
                {"Version": after_history[0][0], "Tag": after_history[0][1]}
            ], claim.slug, claim.target_sha, claim.artifact_hash))
        return asdict(modal_receipt(before, after, claim.slug, claim.target_sha, claim.artifact_hash))

    def canary(self, claim, checkout, deploy_receipt):
        contract = _claim_canary_contract(claim, checkout)
        origin = f"https://omo-space--{modal_target(claim.slug)}-api.modal.run"
        endpoint = origin + "/v1/runs"
        payload = contract["input"]
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
            result_url = _modal_result_url(body["result_url"], origin)
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
        if not isinstance(result, dict):
            valid = False
        elif contract["execution_kind"] == "pure_data":
            valid = result == contract["expected_output"]
        else:
            try:
                from jsonschema import Draft202012Validator
                Draft202012Validator(contract["output_schema"]).validate(result)
                valid = True
            except Exception:
                valid = False
        return {"status": "passed" if valid else "failed"}

    def rollback(self, claim, deploy_receipt):
        checkout = self.checkouts.get(claim.id)
        if not checkout:
            raise ControllerError("rollback_checkout_missing")
        version = str(deploy_receipt.get("version_id") or "")
        if self.active_version(checkout, claim.target_sha, claim.slug) != version:
            raise ControllerError("modal_recovery_readback_mismatch")
        transport = self._transport(claim, checkout, True)
        previous = deploy_receipt.get("rollback_token")
        if previous is None:
            transport.run(modal_stop_call(checkout, claim.slug))
            if not modal_app_stopped(transport.run_json(modal_apps_call(checkout, claim.slug)), claim.slug):
                raise ControllerError("modal_recovery_readback_mismatch")
        else:
            transport.run(modal_rollback_call(checkout, claim.slug, str(previous)))
            history = modal_history_snapshot(transport.run_json(modal_history_call(checkout, claim.slug)))
            if not history or history[0][0] != previous:
                raise ControllerError("modal_recovery_readback_mismatch")
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

    def active_version(self, checkout: Path, target_sha: str) -> str:
        transport = ProductionCommandTransport(
            source_env=self.source_env, trusted_checkout=str(checkout), trusted_sha=target_sha,
        )
        return cloudflare_active_version(
            transport.run_json(cloudflare_deployments_call(checkout))
        )

    def verify_registry(self, claim, checkout):
        return {"status": "passed"}

    def _builder_schedules(self) -> list[str]:
        account_id = str(self.source_env.get("CLOUDFLARE_ACCOUNT_ID") or "")
        token = str(self.source_env.get("CLOUDFLARE_API_TOKEN") or "")
        if not re.fullmatch(r"[0-9a-f]{32}", account_id) or not token:
            raise ControllerError("invalid_cloudflare_configuration")
        status, body = _request_json_stage(
            "cloudflare_schedule_http_failed",
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{CLOUDFLARE_TARGET}/schedules",
            headers={"Authorization": f"Bearer {token}"}, timeout=30,
        )
        result = (body or {}).get("result")
        rows = result.get("schedules") if isinstance(result, dict) and set(result) == {"schedules"} else None
        if status != 200 or (body or {}).get("success") is not True or not isinstance(rows, list) or any(
            not isinstance(row, dict) or "cron" not in row for row in rows
        ):
            raise ControllerError("cloudflare_schedule_readback_failed")
        schedules = [str(row.get("cron") or "") for row in rows]
        if any(not value or len(value) > 64 for value in schedules):
            raise ControllerError("cloudflare_schedule_readback_failed")
        return schedules

    def ensure_builder_schedule(self, checkout: Path, target_sha: str) -> dict[str, object]:
        schedules = self._builder_schedules()
        if schedules == [CLOUDFLARE_BUILDER_CRON]:
            return {"status": "passed", "changed": False}
        account_id = str(self.source_env.get("CLOUDFLARE_ACCOUNT_ID") or "")
        token = str(self.source_env.get("CLOUDFLARE_API_TOKEN") or "")
        status, body = _request_json_stage(
            "cloudflare_schedule_http_failed",
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts/{CLOUDFLARE_TARGET}/schedules",
            method="PUT", payload=[{"cron": CLOUDFLARE_BUILDER_CRON}],
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=30,
        )
        if status != 200 or (body or {}).get("success") is not True:
            raise ControllerError("cloudflare_schedule_update_failed")
        if self._builder_schedules() != [CLOUDFLARE_BUILDER_CRON]:
            raise ControllerError("cloudflare_schedule_readback_failed")
        return {"status": "passed", "changed": True}

    def deploy_worker(self, claim, checkout):
        transport = self._transport(claim, checkout, True)
        versions_before = transport.run_json(cloudflare_versions_call(checkout))
        deployments_before = transport.run_json(cloudflare_deployments_call(checkout))
        if cloudflare_target_present(versions_before, claim.target_sha):
            versions_after = transport.run_json(cloudflare_versions_call(checkout))
            deployments_after = transport.run_json(cloudflare_deployments_call(checkout))
            return asdict(cloudflare_receipt(
                versions_before, versions_after, deployments_before, deployments_after,
                claim.target_sha, claim.artifact_hash,
            ))
        transport.run(cloudflare_deploy_call(checkout, claim.target_sha))
        self.ensure_builder_schedule(checkout, claim.target_sha)
        versions_after = transport.run_json(cloudflare_versions_call(checkout))
        deployments_after = transport.run_json(cloudflare_deployments_call(checkout))
        return asdict(cloudflare_receipt(
            versions_before, versions_after, deployments_before, deployments_after,
            claim.target_sha, claim.artifact_hash,
        ))

    def smoke_worker(self, claim, deploy_receipt):
        request = urllib.request.Request(
            f"{PUBLIC_ORIGIN}/api/me",
            headers={"User-Agent": "OmoProductionFinalizer/1.0", "Accept": "application/json"},
            method="GET",
        )
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
        if not re.fullmatch(r"fin_[0-9a-f]{32}", str(getattr(claim, "id", ""))):
            raise ControllerError("public_canary_contract_invalid")
        if getattr(claim, "runtime", None) not in {"worker-native", "modal-hosted"}:
            raise ControllerError("public_canary_contract_invalid")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(getattr(claim, "slug", "") or "")):
            raise ControllerError("public_canary_contract_invalid")
        self.store.provision_canary_identity()

    def seed_submissions(self, checkout: Path) -> list[dict[str, str]]:
        self.store.provision_canary_identity()
        seeded = []
        for spec in SUBMISSION_SEED_SOURCES:
            source_path = checkout / spec["path"]
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
                if len(raw) != size or hashlib.sha256(raw).hexdigest() != spec["sha256"]:
                    raise ControllerError("production_canary_source_invalid")
                source = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                raise ControllerError("production_canary_source_invalid") from None
            status, body = _request_json_stage(
                "public_canary_http_failed", f"{PUBLIC_ORIGIN}/api/submit", method="POST",
                payload={
                    "name": spec["name"], "content": source,
                    "visibility": "public", "runtime_preference": "worker-native",
                },
                headers={"X-API-Key": self.api_key, "Content-Type": "application/json"}, timeout=30,
            )
            submission_id = str((body or {}).get("id") or "")
            submission_status = str((body or {}).get("status") or "")
            if status not in {200, 202} or (body or {}).get("slug") != spec["slug"] or not re.fullmatch(
                r"sub_[0-9a-f]{32}", submission_id
            ) or submission_status not in {
                "queued", "processing", "needs_review", "ready_for_merge", "ready_for_deploy",
                "ready_for_publish", "deployed", "failed",
            } or (
                submission_status == "failed"
                and ((body or {}).get("duplicate") is not True or (body or {}).get("changed") is not False)
            ):
                raise ControllerError("production_canary_seed_failed")
            seeded.append({
                "slug": spec["slug"], "submission_id": submission_id,
                "submission_status": submission_status,
            })
        return seeded

    def retry_submission(self, submission_id: str, slug: str) -> dict[str, str]:
        if not re.fullmatch(r"sub_[0-9a-f]{32}", submission_id) or slug not in SUBMISSION_SEED_SLUGS:
            raise ControllerError("production_canary_retry_failed")
        status, body = _request_json_stage(
            "public_canary_http_failed", f"{PUBLIC_ORIGIN}/api/submissions/{submission_id}/retry",
            method="POST", payload={},
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"}, timeout=30,
        )
        submission = (body or {}).get("submission")
        if (
            status != 200 or (body or {}).get("ok") is not True or (body or {}).get("retried") is not True
            or not isinstance(submission, dict) or submission.get("id") != submission_id
            or submission.get("slug") != slug or submission.get("status") != "queued"
        ):
            raise ControllerError("production_canary_retry_failed")
        return {"status": "retried", "slug": slug, "submission_id": submission_id}

    def _dispatch(self, claim, contract):
        key = hashlib.sha256(
            f"v0.2:{claim.target_sha}:{claim.artifact_hash}:{contract['slug']}".encode()
        ).hexdigest()[:40]
        payload = {"slug": contract["slug"], "input": contract["input"]}
        headers = {
            "X-API-Key": self.api_key, "Idempotency-Key": f"v0.2-{key}",
            "X-Omo-Finalization-Target-Sha": claim.target_sha,
            "X-Omo-Finalization-Artifact-Hash": claim.artifact_hash,
            "X-Omo-Finalization-Id": claim.id,
            "Content-Type": "application/json", "Accept": "application/json",
            "User-Agent": "OmoProductionFinalizer/1.0",
        }
        return _request_json_stage(
            "public_canary_http_failed", f"{PUBLIC_ORIGIN}/api/run",
            method="POST", payload=payload, headers=headers, timeout=60,
        ), headers, payload

    def verify_public(self, claim, checkout):
        contract = _claim_canary_contract(claim, checkout)
        (status, body), headers, payload = self._dispatch(claim, contract)
        if status not in {200, 202} or not body or not re.fullmatch(
            r"run_[0-9a-f]{32}", str(body.get("run_id") or "")
        ):
            return {"status": "failed"}
        run_id = body["run_id"]
        terminal = body if status == 200 and body.get("status") in {"succeeded", "completed"} else None
        if terminal is None:
            for _ in range(60):
                poll_status, poll = _request_json_stage(
                    "public_canary_http_failed", f"{PUBLIC_ORIGIN}/api/run/{run_id}",
                    headers={
                        "X-API-Key": self.api_key, "Accept": "application/json",
                        "X-Omo-Finalization-Target-Sha": claim.target_sha,
                        "X-Omo-Finalization-Artifact-Hash": claim.artifact_hash,
                        "X-Omo-Finalization-Id": claim.id,
                        "User-Agent": "OmoProductionFinalizer/1.0",
                    }, timeout=30
                )
                if poll_status == 200 and poll and poll.get("status") in {"succeeded", "completed", "failed", "refunded"}:
                    terminal = poll
                    break
                time.sleep(2)
        if not terminal or terminal.get("status") not in {"succeeded", "completed"}:
            return {"status": "failed"}
        if terminal.get("slug") != contract["slug"] or terminal.get("state") != "succeeded":
            return {"status": "failed"}
        result = terminal.get("result") or terminal.get("output") or {}
        try:
            from jsonschema import Draft202012Validator
            Draft202012Validator(contract["public_output_schema"]).validate(result)
            business_fields = set(contract["output_schema"].get("properties", {}))
            business_result = {
                key: value for key, value in result.items() if key in business_fields
            } if isinstance(result, dict) else result
            Draft202012Validator(contract["output_schema"]).validate(business_result)
        except Exception:
            return {"status": "failed"}
        if contract["transport_bound"] and result.get("run_id") != run_id:
            return {"status": "failed"}
        if contract["execution_kind"] in {"pure_data", "skill_builder"} and business_result != contract["expected_output"]:
            return {"status": "failed"}
        try:
            billing_value = terminal.get("billed_amount_usd")
            if billing_value is None and contract["execution_kind"] == "skill_builder":
                billing_value = terminal.get("cost_usd")
            charged = Decimal(str(billing_value))
        except (InvalidOperation, TypeError, ValueError):
            return {"status": "failed"}
        observed_cents = charged * 100
        if charged != contract["price_usd"] or observed_cents != observed_cents.to_integral_value():
            return {"status": "failed"}
        (replay_status, replay), _, _ = self._dispatch(claim, contract)
        if (replay_status not in {200, 202} or not replay or replay.get("run_id") != run_id or
                replay.get("idempotent_replay") is not True):
            return {"status": "failed"}
        replay_billing = replay.get("billed_amount_usd")
        if replay_billing is None and contract["execution_kind"] == "skill_builder":
            replay_billing = replay.get("cost_usd")
        try:
            replay_charged = Decimal(str(replay_billing))
        except (InvalidOperation, TypeError, ValueError):
            return {"status": "failed"}
        replay_result = replay.get("result") or replay.get("output") or {}
        if (
            replay.get("slug") != contract["slug"]
            or replay.get("status") != "completed" or replay.get("state") != "succeeded"
            or replay_charged != charged or replay_result != result
        ):
            return {"status": "failed"}
        output_hash = hashlib.sha256(
            json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return {
            "status": "passed", "run_id": run_id, "slug": contract["slug"],
            "cost_cents": int(observed_cents), "output_sha256": output_hash,
        }

    def verify_balance_snapshot(self, checkout: Path) -> dict[str, Any]:
        status, body = _request_json_stage(
            "public_canary_http_failed", f"{PUBLIC_ORIGIN}/api/me",
            headers={
                "X-API-Key": self.api_key, "Accept": "application/json",
                "User-Agent": "OmoProductionFinalizer/1.0",
            }, timeout=30,
        )
        required = {
            "ok", "balance", "balance_usd", "balance_cents", "currency",
            "signup_granted", "api_key", "mock", "runs",
        }
        if status != 200 or not isinstance(body, dict) or set(body) != required:
            return {"status": "failed"}
        balance_cents = body.get("balance_cents")
        runs = body.get("runs")
        if (
            body.get("ok") is not True or body.get("currency") != "usd" or body.get("mock") is not False
            or type(balance_cents) is not int or balance_cents < 0
            or not isinstance(runs, list) or len(runs) > 50
            or not re.fullmatch(r"omo_[0-9a-f]{32}", str(body.get("api_key") or ""))
        ):
            return {"status": "failed"}
        try:
            if Decimal(str(body.get("balance"))) * 100 != balance_cents:
                return {"status": "failed"}
            if Decimal(str(body.get("balance_usd"))) * 100 != balance_cents:
                return {"status": "failed"}
        except (InvalidOperation, TypeError, ValueError):
            return {"status": "failed"}
        expected: dict[str, int] = {}
        for spec in CANARY_SOURCES:
            contract = _claim_canary_contract(spec["slug"], checkout)
            cents = contract["price_usd"] * 100
            if cents != cents.to_integral_value():
                return {"status": "failed"}
            expected[spec["slug"]] = int(cents)
        observed: dict[str, set[int]] = {slug: set() for slug in expected}
        for run in runs:
            if not isinstance(run, dict) or set(run) != {"slug", "cost_usd", "created_at"}:
                return {"status": "failed"}
            slug = run.get("slug")
            try:
                cents = Decimal(str(run.get("cost_usd"))) * 100
            except (InvalidOperation, TypeError, ValueError):
                return {"status": "failed"}
            if cents != cents.to_integral_value() or not isinstance(run.get("created_at"), str):
                return {"status": "failed"}
            if slug in observed:
                observed[slug].add(int(cents))
        if any(price not in observed[slug] for slug, price in expected.items()):
            return {"status": "failed"}
        return {
            "status": "passed", "currency": "usd", "balance_cents": balance_cents,
            "usage": [{"slug": slug, "cost_cents": expected[slug]} for slug in sorted(expected)],
        }

    def verify_publication(self, claim, checkout):
        contract = _claim_canary_contract(claim, checkout)
        request = urllib.request.Request(
            f"{PUBLIC_ORIGIN}/run.html?slug={contract['slug']}", headers={"User-Agent": "OmoProductionFinalizer/1.0"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read(256 * 1024)
                final = urllib.parse.urlsplit(response.geturl())
                query = urllib.parse.parse_qs(final.query, strict_parsing=True)
                ok = (
                    response.status == 200
                    and final.scheme == "https"
                    and final.hostname == urllib.parse.urlsplit(PUBLIC_ORIGIN).hostname
                    and final.port is None and final.username is None and final.password is None
                    and final.path == "/run" and not final.fragment
                    and query == {"slug": [contract["slug"]]}
                    and b"<title>Run a workflow | Omo</title>" in raw
                )
        except Exception:
            ok = False
        return {"status": "published" if ok else "failed"}


def run_once(args, environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = dict(environ or os.environ)
    checkout = Path(env.get("GITHUB_WORKSPACE", ".")) / "target"
    mainline = GitHubMainlineAdapter(
        checkout, args.trigger_sha, int(args.run_id), int(args.run_attempt),
        env.get("GITHUB_TOKEN", ""),
    )
    store = HttpFinalizationStore(
        env.get("RELEASE_FINALIZER_TOKEN", ""),
        targets=derive_finalization_targets(mainline, args.trigger_sha),
    )
    modal = ProductionModalAdapter(env)
    cloudflare = ProductionCloudflareAdapter(env)
    public = ProductionPublicAdapter(store, env.get("PRODUCTION_CANARY_API_KEY", ""))
    recover_failed_before_run(mainline, store, modal, cloudflare)
    if bool(getattr(args, "resume_failed", False)):
        result = run_finalizer(
            mainline, store, modal, cloudflare, public, targets=TARGETS, resume_failed=True
        )
    else:
        result = run_finalizer(mainline, store, modal, cloudflare, public, targets=TARGETS)
    if result.get("status") == "idle":
        eligibility = store.eligibility(result["target_sha"])
        trusted_checkout = mainline.checkout_detached(result["target_sha"])
        cloudflare.ensure_builder_schedule(trusted_checkout, result["target_sha"])
        seeded = public.seed_submissions(trusted_checkout)
        submissions = [
            public.retry_submission(item["submission_id"], item["slug"])
            if item["submission_status"] == "failed" else item
            for item in seeded
        ]
        seeded_result: dict[str, Any] = {
            "status": "seeded", "submissions": submissions,
            "eligibility": eligibility, "target_sha": result["target_sha"],
        }
        if (
            len(submissions) == len(SUBMISSION_SEED_SOURCES)
            and all(item.get("submission_status") == "deployed" for item in submissions)
        ):
            balance = public.verify_balance_snapshot(trusted_checkout)
            if not isinstance(balance, dict) or balance.get("status") != "passed":
                raise ControllerError("public_balance_readback_failed")
            seeded_result["balance_readback"] = balance
        return seeded_result
    if result.get("status") == "deployed":
        checkout = mainline.checkout_detached(result["target_sha"])
        balance = public.verify_balance_snapshot(checkout)
        if not isinstance(balance, dict) or balance.get("status") != "passed":
            raise ControllerError("public_balance_readback_failed")
        return {
            **result,
            "eligibility": store.eligibility(result["target_sha"]),
            "balance_readback": balance,
        }
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trigger-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--resume-failed", action="store_true")
    args = parser.parse_args(argv)
    if not SAFE_SHA_RE.fullmatch(args.trigger_sha) or not SAFE_ID_RE.fullmatch(args.run_id) or not SAFE_ID_RE.fullmatch(args.run_attempt):
        print('{"error":"invalid_controller_input"}')
        return 2
    try:
        print(json.dumps(run_once(args), separators=(",", ":"), sort_keys=True))
        return 0
    except (ControllerError, FinalizerError) as error:
        payload = {"error": getattr(error, "code", "controller_failed")}
        stage = getattr(error, "stage", None)
        if stage:
            payload["stage"] = stage
        print(json.dumps(payload, separators=(",", ":")))
        return 1
    except Exception:
        print('{"error":"controller_failed"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
