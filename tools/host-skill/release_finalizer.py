#!/usr/bin/env python3
"""Deterministic, credential-free trusted-release finalizer core.

This Phase 2 module accepts injected adapters only. It contains no provider SDK,
network client, credential lookup, shell deployment command, or production
adapter selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

SAFE_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SAFE_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXPECTED_WORKFLOW = "generated-workflow-contracts"
CHECKED_AT = "2026-08-21T00:00:00Z"


class FinalizerError(RuntimeError):
    """A typed, secret-free finalization failure."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GreenMain:
    trigger_sha: str
    target_sha: str
    workflow: str
    event: str
    branch: str
    conclusion: str


@dataclass(frozen=True)
class FinalizationClaim:
    id: str
    submission_id: str
    slug: str
    runtime: Literal["worker-native", "modal-hosted"]
    target_sha: str
    merge_sha: str
    head_sha: str
    source_sha256: str
    artifact_hash: str
    lease_expires_at: str
    attempts: int


class MainlineAdapter(Protocol):
    def latest_green(self) -> GreenMain: ...
    def is_ancestor(self, older: str, newer: str) -> bool: ...
    def read_blob(self, sha: str, path: str) -> bytes: ...
    def list_tree(self, sha: str, prefix: str) -> dict[str, bytes]: ...
    def checkout_detached(self, sha: str) -> Path: ...
    def checkout_head(self, checkout: Path) -> str: ...
    def registry_slug_count(self, sha: str, slug: str) -> int: ...
    def registry_slug_counts(self, sha: str, slugs: set[str]) -> dict[str, int]: ...


class FinalizationStore(Protocol):
    def claim(self, target_sha: str) -> FinalizationClaim | None: ...
    def resume_completed(self, target_sha: str) -> FinalizationClaim | None: ...
    def finalization_detail(self, finalization_id: str) -> dict[str, str]: ...
    def submission_detail(self, submission_id: str) -> dict[str, str]: ...
    def required_registry_slugs(self) -> set[str]: ...
    def advance(self, claim: FinalizationClaim, status: str, failure_code: str | None = None) -> None: ...
    def record_effect(self, claim: FinalizationClaim, operation: str, receipt: dict[str, object]) -> None: ...
    def promote(self, claim: FinalizationClaim, release_gates: dict[str, object]) -> None: ...
    def mark_deployed(self, submission_id: str) -> None: ...


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


def _validate_green(receipt: GreenMain) -> None:
    if (
        receipt.workflow != EXPECTED_WORKFLOW
        or receipt.event != "push"
        or receipt.branch != "main"
        or receipt.conclusion != "success"
        or not SAFE_GIT_SHA_RE.fullmatch(receipt.trigger_sha)
        or not SAFE_GIT_SHA_RE.fullmatch(receipt.target_sha)
    ):
        raise FinalizerError("invalid_green_main")


def _validate_claim_shape(claim: FinalizationClaim) -> None:
    if (
        not re.fullmatch(r"fin_[0-9a-f]{32}", claim.id)
        or not re.fullmatch(r"sub_[A-Za-z0-9_-]{8,100}", claim.submission_id)
        or not SAFE_SLUG_RE.fullmatch(claim.slug)
        or claim.runtime not in {"worker-native", "modal-hosted"}
        or not SAFE_GIT_SHA_RE.fullmatch(claim.target_sha)
        or not SAFE_GIT_SHA_RE.fullmatch(claim.merge_sha)
        or not SAFE_GIT_SHA_RE.fullmatch(claim.head_sha)
        or not SAFE_SHA256_RE.fullmatch(claim.source_sha256)
        or not SAFE_SHA256_RE.fullmatch(claim.artifact_hash)
        or claim.attempts < 1
    ):
        raise FinalizerError("invalid_claim")


def _verify_provenance(
    mainline: MainlineAdapter,
    claim: FinalizationClaim,
    target_sha: str,
    required_registry_slugs: set[str],
) -> Path:
    _validate_claim_shape(claim)
    if claim.target_sha != target_sha:
        raise FinalizerError("claim_target_mismatch")
    if not mainline.is_ancestor(claim.head_sha, claim.merge_sha):
        raise FinalizerError("release_head_not_ancestor")
    if not mainline.is_ancestor(claim.merge_sha, target_sha):
        raise FinalizerError("release_merge_not_ancestor")

    source_path = f"containers/{claim.slug}/source/SKILL.md"
    try:
        source = mainline.read_blob(target_sha, source_path)
        entries = mainline.list_tree(target_sha, f"containers/{claim.slug}")
    except (KeyError, OSError) as error:
        raise FinalizerError("artifact_tree_missing") from error
    if hashlib.sha256(source).hexdigest() != claim.source_sha256:
        raise FinalizerError("source_hash_mismatch")
    if not entries or hash_release_artifact_entries(entries) != claim.artifact_hash:
        raise FinalizerError("artifact_hash_mismatch")

    checkout = mainline.checkout_detached(target_sha)
    if mainline.checkout_head(checkout) != target_sha:
        raise FinalizerError("checkout_head_mismatch")
    if mainline.registry_slug_count(target_sha, claim.slug) != 1:
        raise FinalizerError("registry_slug_mismatch")
    required = set(required_registry_slugs)
    required.add(claim.slug)
    counts = mainline.registry_slug_counts(target_sha, required)
    if set(counts) != required or any(counts.get(slug) != 1 for slug in required):
        raise FinalizerError("registry_snapshot_incomplete")
    return checkout


def _require_passed(receipt: object, code: str) -> None:
    if not isinstance(receipt, dict) or receipt.get("status") != "passed":
        raise FinalizerError(code)


_PHASE1_FAILURE_CODES = {
    "credential_preflight_failed",
    "modal_deploy_failed",
    "modal_canary_failed",
    "worker_deploy_failed",
    "worker_smoke_failed",
    "public_verification_failed",
    "superseded_main",
    "internal_finalizer_failed",
}


def _record_failure(store, claim: FinalizationClaim, code: str) -> str:
    safe_code = code if code in _PHASE1_FAILURE_CODES else "internal_finalizer_failed"
    try:
        store.advance(claim, "failed", safe_code)
    except Exception as error:
        raise FinalizerError("internal_finalizer_failed") from error
    return safe_code


def _resume_completed(store, claim: FinalizationClaim, target_sha: str) -> dict[str, str]:
    _validate_claim_shape(claim)
    if claim.target_sha != target_sha:
        raise FinalizerError("internal_finalizer_failed")
    finalization = store.finalization_detail(claim.id)
    submission = store.submission_detail(claim.submission_id)
    if finalization.get("status") != "completed" or submission.get("release_phase") != "promoted":
        raise FinalizerError("internal_finalizer_failed")
    if submission.get("status") == "ready_for_publish":
        store.mark_deployed(claim.submission_id)
        submission = store.submission_detail(claim.submission_id)
    if submission.get("status") != "deployed":
        raise FinalizerError("internal_finalizer_failed")
    return {"status": "deployed", "submission_id": claim.submission_id, "target_sha": target_sha}


def _new_deployment(receipt: object) -> bool:
    return isinstance(receipt, dict) and receipt.get("status") == "passed" and receipt.get("reused") is False


@dataclass(frozen=True)
class DeploymentTargets:
    modal_target: str
    modal_environment: str
    cloudflare_target: str
    cloudflare_environment: str


STAGING_TARGETS = DeploymentTargets(
    "cognition-staging-label-normalizer-canary", "omo-release-staging",
    "cognition-demos-staging", "staging",
)


def _deployment_receipt(
    receipt: object, claim, provider: str, targets: DeploymentTargets = STAGING_TARGETS
) -> dict[str, object]:
    if is_dataclass(receipt) and not isinstance(receipt, type):
        value = asdict(receipt)
    elif isinstance(receipt, Mapping):
        value = dict(receipt)
    else:
        raise FinalizerError("internal_finalizer_failed")
    expected = {
        "modal": (targets.modal_target, targets.modal_environment),
        "cloudflare": (targets.cloudflare_target, targets.cloudflare_environment),
    }
    target, environment = expected[provider]
    required = {
        "status", "provider", "target", "environment", "target_sha", "artifact_hash",
        "version_id", "previous_version_id", "reused", "rollback_token",
    }
    previous = value.get("previous_version_id")
    reused = value.get("reused")
    if (
        set(value) != required
        or value.get("status") != "passed"
        or value.get("provider") != provider
        or value.get("target") != target
        or value.get("environment") != environment
        or value.get("target_sha") != claim.target_sha
        or value.get("artifact_hash") != claim.artifact_hash
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", str(value.get("version_id") or ""))
        or type(reused) is not bool
        or (previous is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", str(previous)))
        or value.get("rollback_token") != previous
        or (reused is False and previous is None)
        or (reused is True and previous is not None)
    ):
        raise FinalizerError("internal_finalizer_failed")
    return value


def _rollback_new_deployments(claim, modal, cloudflare, modal_receipt, worker_receipt) -> None:
    """Rollback only explicit newly-created staging deployments, in reverse order."""
    failed = False
    if _new_deployment(worker_receipt):
        try:
            _require_passed(cloudflare.rollback_worker(claim, worker_receipt), "internal_finalizer_failed")
        except Exception:
            failed = True
    if _new_deployment(modal_receipt):
        try:
            _require_passed(modal.rollback(claim, modal_receipt), "internal_finalizer_failed")
        except Exception:
            failed = True
    if failed:
        raise FinalizerError("internal_finalizer_failed")


def run_finalizer(
    mainline, store, modal, cloudflare, vercel, *, targets: DeploymentTargets = STAGING_TARGETS
) -> dict[str, str]:
    """Finalize at most one release through injected deterministic adapters."""
    green = mainline.latest_green()
    _validate_green(green)
    if green.trigger_sha != green.target_sha:
        return {"status": "superseded", "target_sha": green.target_sha}

    claim = store.claim(green.target_sha)
    if claim is None:
        resumed = store.resume_completed(green.target_sha)
        if resumed is None:
            return {"status": "idle", "target_sha": green.target_sha}
        return _resume_completed(store, resumed, green.target_sha)
    promoted = False
    modal_receipt = None
    worker_receipt = None
    try:
        checkout = _verify_provenance(
            mainline, claim, green.target_sha, store.required_registry_slugs()
        )

        latest = mainline.latest_green()
        _validate_green(latest)
        if latest.target_sha != green.target_sha or latest.trigger_sha != latest.target_sha:
            return {"status": "superseded_after_claim", "target_sha": latest.target_sha}

        # All identity/config preflights happen after supersession checks and before
        # the first provider effect or lifecycle advance.
        try:
            if claim.runtime == "modal-hosted":
                modal.preflight(claim, checkout)
            cloudflare.preflight(claim, checkout)
            vercel.preflight(claim)
        except Exception as error:
            raise FinalizerError("credential_preflight_failed") from error

        if claim.runtime == "modal-hosted":
            store.advance(claim, "deploying_modal")
            modal_receipt = modal.deploy(claim, checkout)
            _require_passed(modal_receipt, "modal_deploy_failed")
            modal_receipt = _deployment_receipt(modal_receipt, claim, "modal", targets)
            store.record_effect(claim, "modal_deploy", modal_receipt)
            _require_passed(modal.canary(claim, checkout, modal_receipt), "modal_canary_failed")
        store.advance(claim, "deploying_worker")
        r1 = cloudflare.verify_registry(claim, checkout)
        _require_passed(r1, "internal_finalizer_failed")
        worker_receipt = cloudflare.deploy_worker(claim, checkout)
        _require_passed(worker_receipt, "worker_deploy_failed")
        worker_receipt = _deployment_receipt(worker_receipt, claim, "cloudflare", targets)
        store.record_effect(claim, "worker_deploy", worker_receipt)
        r3 = cloudflare.smoke_worker(claim, worker_receipt)
        _require_passed(r3, "worker_smoke_failed")

        store.advance(claim, "verifying_public")
        public = vercel.verify_public(claim, checkout)
        _require_passed(public, "public_verification_failed")
        publication = vercel.verify_publication(claim, checkout)
        r4_status = publication.get("status") if isinstance(publication, dict) else None
        if r4_status not in {"published", "excluded_premium"}:
            raise FinalizerError("public_verification_failed")
        gates: dict[str, object] = {
            "status": "live",
            "checked_at": CHECKED_AT,
            "R1": {"status": "passed"},
            "R2": {"status": "passed"},
            "R3": {"status": "passed"},
            "R4": {"status": r4_status},
        }
        store.promote(claim, gates)
        promoted = True
        finalization = store.finalization_detail(claim.id)
        submission = store.submission_detail(claim.submission_id)
        if (
            finalization.get("status") != "completed"
            or submission.get("status") != "ready_for_publish"
            or submission.get("release_phase") != "promoted"
        ):
            raise FinalizerError("promotion_readback_mismatch")
        store.mark_deployed(claim.submission_id)
        deployed = store.submission_detail(claim.submission_id)
        if deployed.get("status") != "deployed" or deployed.get("release_phase") != "promoted":
            raise FinalizerError("deployed_readback_mismatch")
        return {"status": "deployed", "submission_id": claim.submission_id, "target_sha": green.target_sha}
    except FinalizerError as error:
        if not promoted:
            try:
                _rollback_new_deployments(claim, modal, cloudflare, modal_receipt, worker_receipt)
            except FinalizerError as rollback_error:
                _record_failure(store, claim, rollback_error.code)
                raise rollback_error from error
            safe_code = _record_failure(store, claim, error.code)
            if safe_code != error.code:
                raise FinalizerError(safe_code) from error
        raise
    except Exception as error:
        if not promoted:
            try:
                _rollback_new_deployments(claim, modal, cloudflare, modal_receipt, worker_receipt)
            except FinalizerError as rollback_error:
                _record_failure(store, claim, rollback_error.code)
                raise rollback_error from error
            _record_failure(store, claim, "internal_finalizer_failed")
        raise FinalizerError("internal_finalizer_failed") from error


class EffectJournal:
    """In-memory fake provider ledger keyed independently of lease generation."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str, str, str]] = []
        self._receipts: dict[tuple[str, str, str, str], dict[str, object]] = {}

    def apply(self, claim: FinalizationClaim, operation: str) -> dict[str, object]:
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", operation):
            raise FinalizerError("invalid_fake_operation")
        key = (claim.submission_id, claim.target_sha, claim.artifact_hash, operation)
        if key not in self._receipts:
            self.events.append(key)
            if operation == "modal_deploy":
                self._receipts[key] = {
                    "status": "passed",
                    "provider": "modal",
                    "target": "cognition-staging-label-normalizer-canary",
                    "environment": "omo-release-staging",
                    "target_sha": claim.target_sha,
                    "artifact_hash": claim.artifact_hash,
                    "version_id": "modal-v2",
                    "previous_version_id": "modal-v1",
                    "reused": False,
                    "rollback_token": "modal-v1",
                }
            elif operation == "worker_deploy":
                self._receipts[key] = {
                    "status": "passed",
                    "provider": "cloudflare",
                    "target": "cognition-demos-staging",
                    "environment": "staging",
                    "target_sha": claim.target_sha,
                    "artifact_hash": claim.artifact_hash,
                    "version_id": "worker-v2",
                    "previous_version_id": "worker-v1",
                    "reused": False,
                    "rollback_token": "worker-v1",
                }
            else:
                self._receipts[key] = {"status": "passed", "operation": operation}
        return dict(self._receipts[key])


class _ScenarioMainline:
    def __init__(self, scenario: dict[str, object]) -> None:
        self._green = GreenMain(**scenario["green_main"])
        self._artifacts = {
            str(path): str(content).encode("utf-8")
            for path, content in scenario["artifacts"].items()
        }
        self._ancestors = {tuple(pair) for pair in scenario["ancestor_pairs"]}
        self._checkout_head = str(scenario["checkout_head"])
        self._registry_count = int(scenario["registry_count"])

    def latest_green(self) -> GreenMain:
        return self._green

    def is_ancestor(self, older: str, newer: str) -> bool:
        return (older, newer) in self._ancestors

    def read_blob(self, sha: str, path: str) -> bytes:
        return self._artifacts[path]

    def list_tree(self, sha: str, prefix: str) -> dict[str, bytes]:
        return {path: value for path, value in self._artifacts.items() if path.startswith(prefix + "/")}

    def checkout_detached(self, sha: str) -> Path:
        return Path("/fake/detached")

    def checkout_head(self, checkout: Path) -> str:
        return self._checkout_head

    def registry_slug_count(self, sha: str, slug: str) -> int:
        return self._registry_count

    def registry_slug_counts(self, sha: str, slugs: set[str]) -> dict[str, int]:
        return {slug: self._registry_count for slug in slugs}


class _ScenarioStore:
    def __init__(self, claim: FinalizationClaim) -> None:
        self._claim = claim
        self._state = "claimed"
        self._submission_status = "ready_for_deploy"

    def claim(self, target_sha: str) -> FinalizationClaim | None:
        return self._claim

    def resume_completed(self, target_sha: str) -> FinalizationClaim | None:
        if self._state == "completed" and self._claim.target_sha == target_sha:
            return self._claim
        return None

    def finalization_detail(self, finalization_id: str) -> dict[str, str]:
        return {"status": self._state}

    def submission_detail(self, submission_id: str) -> dict[str, str]:
        return {
            "status": self._submission_status,
            "release_phase": "promoted" if self._state == "completed" else "merged_verified",
        }

    def required_registry_slugs(self) -> set[str]:
        return {self._claim.slug}

    def advance(self, claim: FinalizationClaim, status: str, failure_code: str | None = None) -> None:
        self._state = status

    def promote(self, claim: FinalizationClaim, release_gates: dict[str, object]) -> None:
        self._state = "completed"
        self._submission_status = "ready_for_publish"

    def record_effect(self, claim: FinalizationClaim, operation: str, receipt: dict[str, object]) -> None:
        return None

    def mark_deployed(self, submission_id: str) -> None:
        self._submission_status = "deployed"


class _FakeModal:
    def __init__(self, journal: EffectJournal) -> None:
        self._journal = journal

    def preflight(self, claim: FinalizationClaim, checkout: Path) -> None:
        return None

    def deploy(self, claim: FinalizationClaim, checkout: Path) -> dict[str, object]:
        return self._journal.apply(claim, "modal_deploy")

    def canary(self, claim: FinalizationClaim, checkout: Path, deploy_receipt=None) -> dict[str, str]:
        return self._journal.apply(claim, "modal_canary")

    def rollback(self, claim: FinalizationClaim, deploy_receipt) -> dict[str, str]:
        return self._journal.apply(claim, "modal_rollback")


class _FakeCloudflare:
    def __init__(self, journal: EffectJournal) -> None:
        self._journal = journal

    def preflight(self, claim: FinalizationClaim, checkout: Path) -> None:
        return None

    def verify_registry(self, claim: FinalizationClaim, checkout: Path) -> dict[str, str]:
        return self._journal.apply(claim, "registry_verify")

    def deploy_worker(self, claim: FinalizationClaim, checkout: Path) -> dict[str, object]:
        return self._journal.apply(claim, "worker_deploy")

    def smoke_worker(self, claim: FinalizationClaim, deploy_receipt=None) -> dict[str, str]:
        return self._journal.apply(claim, "worker_smoke")

    def rollback_worker(self, claim: FinalizationClaim, deploy_receipt) -> dict[str, str]:
        return self._journal.apply(claim, "worker_rollback")


class _FakeVercel:
    def __init__(self, journal: EffectJournal) -> None:
        self._journal = journal

    def preflight(self, claim: FinalizationClaim) -> None:
        return None

    def verify_public(self, claim: FinalizationClaim, checkout: Path) -> dict[str, str]:
        return self._journal.apply(claim, "public_verify")

    def verify_publication(self, claim: FinalizationClaim, checkout: Path) -> dict[str, str]:
        self._journal.apply(claim, "publication_verify")
        return {"status": "excluded_premium"}


_SCENARIO_KEYS = {
    "green_main", "claim", "artifacts", "ancestor_pairs", "checkout_head", "registry_count"
}
_FORBIDDEN_SCENARIO_KEYS = {"token", "secret", "url", "account", "command", "workspace", "provider"}


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in _FORBIDDEN_SCENARIO_KEYS or _contains_forbidden_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _load_scenario(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    if not raw or len(raw) > 256 * 1024:
        raise FinalizerError("invalid_scenario")
    try:
        scenario = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FinalizerError("invalid_scenario") from error
    if (
        not isinstance(scenario, dict)
        or set(scenario) != _SCENARIO_KEYS
        or _contains_forbidden_key(scenario)
        or not isinstance(scenario.get("green_main"), dict)
        or not isinstance(scenario.get("claim"), dict)
        or not isinstance(scenario.get("artifacts"), dict)
        or not isinstance(scenario.get("ancestor_pairs"), list)
    ):
        raise FinalizerError("invalid_scenario")
    return scenario


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one fake-only release finalization scenario")
    parser.add_argument("--scenario", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        scenario = _load_scenario(args.scenario)
        claim = FinalizationClaim(**scenario["claim"])
        journal = EffectJournal()
        result = run_finalizer(
            _ScenarioMainline(scenario),
            _ScenarioStore(claim),
            _FakeModal(journal),
            _FakeCloudflare(journal),
            _FakeVercel(journal),
        )
    except (FinalizerError, OSError, TypeError, ValueError, KeyError):
        print('{"error":"invalid_scenario"}')
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
