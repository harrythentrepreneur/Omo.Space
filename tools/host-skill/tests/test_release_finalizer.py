"""Credential-free contracts for the deterministic trusted release finalizer."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools" / "host-skill" / "release_finalizer.py"
COMPILER_PATH = ROOT / "packages" / "skill-to-modal" / "compiler.py"
AUTHORING_RECEIPT_PATH = (
    ROOT / "packages" / "skill-to-modal" / "profile-authoring-specs"
    / "release-tag-sorter-canary.json"
)


def load_finalizer():
    spec = importlib.util.spec_from_file_location("release_finalizer_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_compiler():
    spec = importlib.util.spec_from_file_location("release_finalizer_compiler_test", COMPILER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def artifact_hash(entries: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for rel, content in sorted(entries.items()):
        digest.update(rel.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).hexdigest().encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def authored_receipt(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()


def valid_authoring_receipt() -> bytes:
    return AUTHORING_RECEIPT_PATH.read_bytes()


def assembled_profile(receipt: bytes) -> dict[str, Any]:
    compiler = load_compiler()
    return compiler.assemble_profile_authoring_spec(
        json.loads(receipt),
        {
            "slug": "demo",
            "name": "Demo",
            "source_sha256": hashlib.sha256(SOURCE).hexdigest(),
        },
    )


TARGET = "a" * 40
HEAD = "b" * 40
MERGE = "c" * 40
NEW_TARGET = "d" * 40
SOURCE = b"# Demo\n"
ENTRIES = {
    "containers/demo/manifest.json": b'{"slug":"demo"}',
    "containers/demo/source/SKILL.md": SOURCE,
    "packages/skill-to-modal/profiles/demo.json": b'{"slug":"demo"}',
}


class Mainline:
    def __init__(self, mod, receipts=None):
        normal = mod.GreenMain(
            trigger_sha=TARGET,
            target_sha=TARGET,
            workflow="generated-workflow-contracts",
            event="push",
            branch="main",
            conclusion="success",
        )
        self.receipts = list(receipts or [normal, normal])
        self.calls: list[object] = []
        self.entries = dict(ENTRIES)
        self.checkout = Path("/fake/detached")
        self.checkout_sha = TARGET
        self.registry_counts = {"demo": 1, "already-live": 1}

    def latest_green(self):
        self.calls.append("latest_green")
        if len(self.receipts) > 1:
            return self.receipts.pop(0)
        return self.receipts[0]

    def is_ancestor(self, older, newer):
        self.calls.append(("ancestor", older, newer))
        return (older, newer) in {(HEAD, MERGE), (MERGE, TARGET)}

    def trees_equal(self, left, right):
        self.calls.append(("trees_equal", left, right))
        return False

    def read_blob(self, sha, path):
        self.calls.append(("read_blob", sha, path))
        return self.entries[path]

    def list_tree(self, sha, prefix):
        self.calls.append(("list_tree", sha, prefix))
        return {
            key: value for key, value in self.entries.items()
            if key == prefix or key.startswith(prefix + "/")
        }

    def checkout_detached(self, sha):
        self.calls.append(("checkout", sha))
        return self.checkout

    def checkout_head(self, checkout):
        return self.checkout_sha

    def registry_slug_count(self, sha, slug):
        self.calls.append(("registry", sha, slug))
        return self.registry_counts.get(slug, 0)

    def registry_slug_counts(self, sha, slugs):
        self.calls.append(("registry_all", sha, tuple(sorted(slugs))))
        return {slug: self.registry_counts.get(slug, 0) for slug in slugs}


class Store:
    def __init__(self, mod, runtime="worker-native"):
        self.claim_value = mod.FinalizationClaim(
            id="fin_" + "1" * 32,
            submission_id="sub_12345678",
            slug="demo",
            runtime=runtime,
            target_sha=TARGET,
            merge_sha=MERGE,
            head_sha=HEAD,
            source_sha256=hashlib.sha256(SOURCE).hexdigest(),
            artifact_hash=artifact_hash(ENTRIES),
            lease_expires_at="2099-01-01T00:00:00Z",
            attempts=1,
        )
        self.events: list[object] = []
        self.state = "claimed"
        self.submission_status = "ready_for_deploy"
        self.gates = None
        self.effects: dict[str, dict] = {}
        self.fail_on: str | None = None
        self.failed_inspection = None

    def claim(self, target_sha):
        self.events.append(("claim", target_sha))
        if self.state in {"completed", "failed"} or self.submission_status == "deployed":
            return None
        return self.claim_value

    def resume_completed(self, target_sha):
        self.events.append(("resume_completed", target_sha))
        if self.state == "completed" and self.claim_value.target_sha == target_sha:
            return self.claim_value
        return None

    def inspect_failed(self, target_sha):
        self.events.append(("inspect_failed", target_sha))
        return self.failed_inspection

    def resume_failed(self, target_sha, finalization_id):
        self.events.append(("resume_failed", target_sha, finalization_id))
        if (
            self.failed_inspection
            and self.failed_inspection.target_sha == target_sha
            and self.failed_inspection.id == finalization_id
        ):
            self.failed_inspection = None
            self.state = "requeued"
            self.submission_status = "ready_for_deploy"
            self.claim_value = replace(self.claim_value, id="fin_" + "2" * 32, attempts=2)
            return True
        return False

    def finalization_detail(self, finalization_id):
        self.events.append(("finalization_detail", finalization_id))
        return {"status": self.state}

    def submission_detail(self, submission_id):
        self.events.append(("submission_detail", submission_id))
        return {
            "status": self.submission_status,
            "release_phase": "promoted" if self.state == "completed" else "merged_verified",
        }

    def required_registry_slugs(self):
        return {"demo", "already-live"}

    def advance(self, claim, status, failure_code=None):
        self.events.append(("advance", status, failure_code))
        if self.fail_on == f"advance:{status}":
            raise RuntimeError("SENTINEL_STORE_FAILURE")
        self.state = status

    def promote(self, claim, release_gates):
        self.events.append(("promote", release_gates))
        if self.fail_on == "promote":
            raise RuntimeError("SENTINEL_STORE_FAILURE")
        self.gates = release_gates
        self.state = "completed"
        self.submission_status = "ready_for_publish"

    def record_effect(self, claim, operation, receipt):
        self.events.append(("record_effect", operation, receipt))
        if self.fail_on == f"record_effect:{operation}":
            raise RuntimeError("SENTINEL_STORE_FAILURE")
        self.effects[operation] = dict(receipt)

    def mark_deployed(self, submission_id):
        self.events.append(("deployed", submission_id))
        if self.fail_on == "deployed":
            raise RuntimeError("SENTINEL_STORE_FAILURE")
        self.submission_status = "deployed"


class Adapter:
    def __init__(self, name):
        self.name = name
        self.events: list[object] = []
        self.fail_on: str | None = None
        self.received_receipts: list[Any] = []
        self.reused = False

    def preflight(self, claim, checkout=None):
        self.events.append("preflight")
        if self.fail_on == "preflight":
            raise RuntimeError("SENTINEL_PREFLIGHT_FAILURE")

    def deploy(self, claim, checkout):
        self.events.append("deploy")
        return {
            "status": "failed" if self.fail_on == "deploy" else "passed",
            "provider": "modal",
            "target": "cognition-staging-label-normalizer-canary",
            "environment": "omo-release-staging",
            "target_sha": claim.target_sha,
            "artifact_hash": claim.artifact_hash,
            "version_id": "modal-v2",
            "previous_version_id": None if self.reused else "modal-v1",
            "reused": self.reused,
            "rollback_token": None if self.reused else "modal-v1",
        }

    def canary(self, claim, checkout, deploy_receipt=None):
        self.events.append("canary")
        self.received_receipts.append(deploy_receipt)
        return {"status": "failed" if self.fail_on == "canary" else "passed"}

    def rollback(self, claim, deploy_receipt):
        self.events.append("rollback")
        self.received_receipts.append(deploy_receipt)
        return {"status": "failed" if self.fail_on == "rollback" else "passed"}

    def verify_registry(self, claim, checkout):
        self.events.append("registry")
        return {"status": "failed" if self.fail_on == "registry" else "passed"}

    def deploy_worker(self, claim, checkout):
        self.events.append("deploy_worker")
        if self.fail_on == "deploy_worker_raise":
            raise RuntimeError("SENTINEL_WORKER_DEPLOY_FAILURE")
        return {
            "status": "failed" if self.fail_on == "deploy_worker" else "passed",
            "provider": "cloudflare",
            "target": "cognition-demos-staging",
            "environment": "staging",
            "target_sha": claim.target_sha,
            "artifact_hash": claim.artifact_hash,
            "version_id": "worker-v2",
            "previous_version_id": None if self.reused else "worker-v1",
            "reused": self.reused,
            "rollback_token": None if self.reused else "worker-v1",
        }

    def smoke_worker(self, claim, deploy_receipt=None):
        self.events.append("smoke_worker")
        self.received_receipts.append(deploy_receipt)
        return {"status": "failed" if self.fail_on == "smoke_worker" else "passed"}

    def rollback_worker(self, claim, deploy_receipt):
        self.events.append("rollback_worker")
        self.received_receipts.append(deploy_receipt)
        return {"status": "failed" if self.fail_on == "rollback_worker" else "passed"}

    def verify_public(self, claim, checkout):
        self.events.append("verify_public")
        if self.fail_on == "verify_public":
            return {"status": "failed"}
        return {
            "status": "passed",
            "run_id": "run_" + "1" * 32,
            "slug": claim.slug,
            "cost_cents": 10,
            "output_sha256": "d" * 64,
        }

    def verify_publication(self, claim, checkout):
        self.events.append("verify_publication")
        return {"status": "excluded_premium" if self.fail_on != "publication" else "failed"}


def components(runtime="worker-native", receipts=None):
    mod = load_finalizer()
    setattr(mod, "TRUSTED_LEGACY_PROFILE_DIGESTS", {
        "demo": (
            hashlib.sha256(SOURCE).hexdigest(),
            hashlib.sha256(ENTRIES["packages/skill-to-modal/profiles/demo.json"]).hexdigest(),
        ),
    })
    return mod, Mainline(mod, receipts), Store(mod, runtime), Adapter("modal"), Adapter("cloudflare"), Adapter("vercel")


def test_worker_native_success_skips_modal_and_completes_exact_order():
    mod, mainline, store, modal, cloudflare, vercel = components()
    result = mod.run_finalizer(mainline, store, modal, cloudflare, vercel)

    assert result == {"status": "deployed", "submission_id": "sub_12345678", "target_sha": TARGET}
    assert modal.events == []
    assert cloudflare.events == ["preflight", "registry", "deploy_worker", "smoke_worker"]
    assert vercel.events == ["preflight", "verify_public", "verify_publication"]
    assert [event[1] for event in store.events if event[0] == "advance"] == ["deploying_worker", "verifying_public"]
    assert store.events[-1] == ("submission_detail", store.claim_value.submission_id)
    assert store.submission_status == "deployed"
    assert store.gates == {
        "status": "live", "checked_at": "2026-08-21T00:00:00Z",
        "R1": {"status": "passed"},
        "R2": {
            "status": "passed", "run_id": "run_" + "1" * 32,
            "slug": store.claim_value.slug, "cost_cents": 10,
            "output_sha256": "d" * 64,
        },
        "R3": {"status": "passed"}, "R4": {"status": "excluded_premium"},
    }


def test_public_canary_receipt_is_persisted_in_promotion_evidence():
    mod, mainline, store, modal, cloudflare, _vercel = components()

    class EvidenceAdapter(Adapter):
        def verify_public(self, claim, checkout):
            self.events.append("verify_public")
            return {
                "status": "passed",
                "run_id": "run_" + "2" * 32,
                "slug": claim.slug,
                "cost_cents": 10,
                "output_sha256": "e" * 64,
            }

    vercel = EvidenceAdapter("vercel")

    result = mod.run_finalizer(mainline, store, modal, cloudflare, vercel)

    assert result["status"] == "deployed"
    assert store.gates is not None
    assert store.gates["R2"] == {
        "status": "passed",
        "run_id": "run_" + "2" * 32,
        "slug": store.claim_value.slug,
        "cost_cents": 10,
        "output_sha256": "e" * 64,
    }


@pytest.mark.parametrize(
    "mutation",
    [
        {"slug": "other-workflow"},
        {"cost_cents": 11},
        {"debug": "should-not-persist"},
    ],
)
def test_public_canary_receipt_rejects_mismatched_or_extra_evidence(mutation):
    mod, mainline, store, modal, cloudflare, _vercel = components()

    class InvalidEvidenceAdapter(Adapter):
        def verify_public(self, claim, checkout):
            receipt = {
                "status": "passed", "run_id": "run_" + "2" * 32,
                "slug": claim.slug, "cost_cents": 10,
                "output_sha256": "e" * 64,
            }
            receipt.update(mutation)
            return receipt

    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, InvalidEvidenceAdapter("vercel"))

    assert caught.value.code == "public_verification_failed"
    assert store.gates is None


def test_authored_release_hash_includes_profile_and_authoring_receipt():
    mod, mainline, store, modal, cloudflare, vercel = components()
    receipt = valid_authoring_receipt()
    mainline.entries.update({
        "packages/skill-to-modal/profiles/demo.json": json.dumps(assembled_profile(receipt)).encode(),
        "packages/skill-to-modal/profile-authoring-specs/demo.json": receipt,
    })
    store.claim_value = replace(
        store.claim_value,
        artifact_hash=artifact_hash(mainline.entries),
    )

    result = mod.run_finalizer(mainline, store, modal, cloudflare, vercel)

    assert result["status"] == "deployed"
    assert ("read_blob", MERGE, "packages/skill-to-modal/profiles/demo.json") in mainline.calls
    assert ("read_blob", MERGE, "containers/demo/source/SKILL.md") in mainline.calls
    assert ("list_tree", MERGE, "containers/demo") in mainline.calls
    assert (
        "list_tree",
        MERGE,
        "packages/skill-to-modal/profile-authoring-specs/demo.json",
    ) in mainline.calls


def test_authored_release_accepts_compiler_owned_catalog_promotion():
    mod, mainline, store, modal, cloudflare, vercel = components()
    receipt = valid_authoring_receipt()
    profile = assembled_profile(receipt)
    profile["marketplace"]["catalog_managed"] = True
    profile["marketplace"]["storefront_visible"] = True
    mainline.entries.update({
        "packages/skill-to-modal/profiles/demo.json": json.dumps(profile).encode(),
        "packages/skill-to-modal/profile-authoring-specs/demo.json": receipt,
    })
    store.claim_value = replace(
        store.claim_value,
        artifact_hash=artifact_hash(mainline.entries),
    )

    result = mod.run_finalizer(mainline, store, modal, cloudflare, vercel)

    assert result["status"] == "deployed"


def test_trusted_legacy_profile_pins_match_reviewed_tree():
    mod = load_finalizer()
    for slug, (source_digest, profile_digest) in mod.TRUSTED_LEGACY_PROFILE_DIGESTS.items():
        source = ROOT / "containers" / slug / "source" / "SKILL.md"
        profile = ROOT / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json"
        assert hashlib.sha256(source.read_bytes()).hexdigest() == source_digest
        assert hashlib.sha256(profile.read_bytes()).hexdigest() == profile_digest


def test_authoring_receipt_canonicalization_matches_trusted_compiler():
    mod = load_finalizer()
    compiler = load_compiler()
    value = {
        "schema_version": "omo.profile-authoring-spec/v1",
        "family": "pure_data",
        "input_schema": {
            "type": "object",
            "properties": {
                "zeta": {"type": "string", "enum": ["z", "a"]},
                "alpha": {"type": "string"},
            },
            "required": ["zeta", "alpha"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
    }
    compiler_bytes = compiler.canonical_profile_authoring_spec_bytes(value)

    assert mod._canonical_authoring_receipt(compiler_bytes) == compiler_bytes


@pytest.mark.parametrize("case", [
    "legacy_receipt",
    "unsupported_version",
    "receipt_digest",
    "receipt_missing_schema_version",
    "receipt_unsupported_schema_version",
    "malformed_schema_properties",
    "malformed_schema_items",
    "malformed_schema_required",
    "malformed_schema_enum",
    "profile_semantic_mismatch",
    "legacy_downgrade",
])
def test_authoring_evidence_must_match_producer_contract(case):
    mod, mainline, store, modal, cloudflare, vercel = components()
    valid_receipt = valid_authoring_receipt()
    receipt_value = json.loads(valid_receipt)
    if case == "receipt_missing_schema_version":
        receipt_value.pop("schema_version")
    elif case == "receipt_unsupported_schema_version":
        receipt_value["schema_version"] = "unknown/v9"
    elif case == "malformed_schema_properties":
        receipt_value["input_schema"]["properties"] = []
    elif case == "malformed_schema_items":
        receipt_value["input_schema"]["properties"]["tags"]["items"] = []
    elif case == "malformed_schema_required":
        receipt_value["input_schema"]["required"] = {}
    elif case == "malformed_schema_enum":
        receipt_value["input_schema"]["properties"]["tags"]["items"]["enum"] = {}
    receipt = authored_receipt(receipt_value)
    if case in {"legacy_receipt", "legacy_downgrade"}:
        profile: dict[str, Any] = {"slug": "demo"}
    else:
        profile = assembled_profile(valid_receipt)
        profile["authoring_spec_sha256"] = hashlib.sha256(receipt).hexdigest()
    if case == "unsupported_version":
        profile["authoring_spec_version"] = "unknown/v9"
    elif case == "receipt_digest":
        profile["authoring_spec_sha256"] = "0" * 64
    elif case == "profile_semantic_mismatch":
        profile["execution_kind"] = "single_llm"
        profile["capabilities"] = ["attacker-selected-capability"]
    elif case == "legacy_downgrade":
        profile["execution_kind"] = "single_llm"
        profile["capabilities"] = ["attacker-selected-capability"]
    mainline.entries["packages/skill-to-modal/profiles/demo.json"] = json.dumps(profile).encode()
    if case != "legacy_downgrade":
        mainline.entries["packages/skill-to-modal/profile-authoring-specs/demo.json"] = receipt
    hashed_entries = dict(mainline.entries)
    if case == "legacy_receipt":
        hashed_entries.pop("packages/skill-to-modal/profile-authoring-specs/demo.json")
    store.claim_value = replace(store.claim_value, artifact_hash=artifact_hash(hashed_entries))

    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)

    assert caught.value.code == "internal_finalizer_failed"
    assert modal.events == cloudflare.events == vercel.events == []


def test_explicit_production_targets_accept_only_production_receipts():
    mod, mainline, store, modal, cloudflare, vercel = components(runtime="modal-hosted")
    targets = mod.DeploymentTargets(
        "cognition-label-normalizer-canary", "main", "cognition-demos", "production"
    )

    def modal_deploy(claim, checkout):
        modal.events.append("deploy")
        return {
            "status": "passed", "provider": "modal", "target": targets.modal_target,
            "environment": targets.modal_environment, "target_sha": claim.target_sha,
            "artifact_hash": claim.artifact_hash, "version_id": "modal-v2",
            "previous_version_id": "modal-v1", "reused": False, "rollback_token": "modal-v1",
        }

    def worker_deploy(claim, checkout):
        cloudflare.events.append("deploy_worker")
        return {
            "status": "passed", "provider": "cloudflare", "target": targets.cloudflare_target,
            "environment": targets.cloudflare_environment, "target_sha": claim.target_sha,
            "artifact_hash": claim.artifact_hash, "version_id": "worker-v2",
            "previous_version_id": "worker-v1", "reused": False, "rollback_token": "worker-v1",
        }

    modal.deploy = modal_deploy
    cloudflare.deploy_worker = worker_deploy
    result = mod.run_finalizer(
        mainline, store, modal, cloudflare, vercel, targets=targets
    )
    assert result["status"] == "deployed"
    assert store.effects["modal_deploy"]["environment"] == "main"
    assert store.effects["worker_deploy"]["environment"] == "production"

    bad = dict(store.effects["worker_deploy"], target="cognition-demos-staging")
    with pytest.raises(mod.FinalizerError):
        mod._deployment_receipt(bad, store.claim_value, "cloudflare", targets)


def test_superseded_trigger_exits_before_claim_or_provider_effect():
    mod = load_finalizer()
    old = mod.GreenMain(TARGET, NEW_TARGET, "generated-workflow-contracts", "push", "main", "success")
    mod, mainline, store, modal, cloudflare, vercel = components(receipts=[old])

    result = mod.run_finalizer(mainline, store, modal, cloudflare, vercel)

    assert result == {"status": "superseded", "target_sha": NEW_TARGET}
    assert store.events == []
    assert modal.events == cloudflare.events == vercel.events == []


def test_main_advances_after_claim_without_provider_or_terminal_failure():
    mod = load_finalizer()
    current = mod.GreenMain(TARGET, TARGET, "generated-workflow-contracts", "push", "main", "success")
    advanced = replace(current, trigger_sha=NEW_TARGET, target_sha=NEW_TARGET)
    mod, mainline, store, modal, cloudflare, vercel = components(receipts=[current, advanced])

    result = mod.run_finalizer(mainline, store, modal, cloudflare, vercel)

    assert result == {"status": "superseded_after_claim", "target_sha": NEW_TARGET}
    assert store.events == [("claim", TARGET)]
    assert modal.events == cloudflare.events == vercel.events == []


def test_modal_hosted_runs_modal_before_worker():
    mod, mainline, store, modal, cloudflare, vercel = components(runtime="modal-hosted")
    result = mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert result["status"] == "deployed"
    assert modal.events == ["preflight", "deploy", "canary"]
    assert [event[1] for event in store.events if event[0] == "advance"] == [
        "deploying_modal", "deploying_worker", "verifying_public"
    ]
    assert modal.received_receipts[0]["provider"] == "modal"
    assert cloudflare.received_receipts[0]["provider"] == "cloudflare"
    assert store.effects["modal_deploy"] == modal.received_receipts[0]
    assert store.effects["worker_deploy"] == cloudflare.received_receipts[0]


def test_modal_canary_failure_rolls_back_new_modal_deployment():
    mod, mainline, store, modal, cloudflare, vercel = components(runtime="modal-hosted")
    modal.fail_on = "canary"
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "modal_canary_failed"
    assert modal.events == ["preflight", "deploy", "canary", "rollback"]
    assert modal.received_receipts[0] == modal.received_receipts[1]
    assert cloudflare.events == ["preflight"]


def test_worker_smoke_failure_rolls_back_worker_then_modal():
    mod, mainline, store, modal, cloudflare, vercel = components(runtime="modal-hosted")
    cloudflare.fail_on = "smoke_worker"
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "worker_smoke_failed"
    assert cloudflare.events[-1] == "rollback_worker"
    assert modal.events[-1] == "rollback"
    assert cloudflare.received_receipts[0] == cloudflare.received_receipts[1]


def test_reused_deployments_are_never_rolled_back():
    mod, mainline, store, modal, cloudflare, vercel = components(runtime="modal-hosted")
    modal.reused = True
    cloudflare.reused = True
    cloudflare.fail_on = "smoke_worker"
    with pytest.raises(mod.FinalizerError):
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert "rollback" not in modal.events
    assert "rollback_worker" not in cloudflare.events


@pytest.mark.parametrize(
    ("adapter_name", "field", "value"),
    [
        ("modal", "target_sha", NEW_TARGET),
        ("modal", "artifact_hash", "f" * 64),
        ("modal", "target", "cognition-label-normalizer-canary"),
        ("cloudflare", "provider", "modal"),
        ("cloudflare", "environment", "production"),
        ("cloudflare", "rollback_token", "other-version"),
        ("cloudflare", "reused", "false"),
    ],
)
def test_finalizer_rejects_unbound_or_malformed_deployment_receipts(adapter_name, field, value):
    mod, mainline, store, modal, cloudflare, vercel = components(runtime="modal-hosted")
    adapter = modal if adapter_name == "modal" else cloudflare
    method_name = "deploy" if adapter_name == "modal" else "deploy_worker"
    original = getattr(adapter, method_name)

    def malformed(*args):
        receipt = original(*args)
        receipt[field] = value
        return receipt

    setattr(adapter, method_name, malformed)
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "internal_finalizer_failed"
    assert not any(
        isinstance(event, tuple)
        and len(event) > 1
        and event[0] == "record_effect"
        and str(event[1]).startswith(adapter_name)
        for event in store.events
    )


def test_receipt_is_persisted_before_canary_and_smoke():
    mod, mainline, store, modal, cloudflare, vercel = components(runtime="modal-hosted")
    mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    modal_record = next(
        i for i, event in enumerate(store.events)
        if isinstance(event, tuple) and event[:2] == ("record_effect", "modal_deploy")
    )
    modal_canary = modal.events.index("canary")
    worker_record = next(
        i for i, event in enumerate(store.events)
        if isinstance(event, tuple) and event[:2] == ("record_effect", "worker_deploy")
    )
    assert modal_record >= 0 and worker_record > modal_record
    assert modal.received_receipts and modal_canary > modal.events.index("deploy")


def test_worker_rollback_failure_still_attempts_modal_rollback():
    mod, mainline, store, modal, cloudflare, vercel = components(runtime="modal-hosted")
    cloudflare.fail_on = "rollback_worker"
    vercel.fail_on = "verify_public"
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "internal_finalizer_failed"
    assert cloudflare.events[-1] == "rollback_worker"
    assert modal.events[-1] == "rollback"


@pytest.mark.parametrize("field", ["source_sha256", "artifact_hash", "target_sha"])
def test_immutable_provenance_mismatch_fails_before_provider_effect(field):
    mod, mainline, store, modal, cloudflare, vercel = components()
    store.claim_value = replace(store.claim_value, **{field: "f" * (64 if field.endswith("256") or field == "artifact_hash" else 40)})
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "internal_finalizer_failed"
    assert store.events[-1] == ("advance", "failed", "internal_finalizer_failed")
    assert modal.events == cloudflare.events == vercel.events == []


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("head_ancestry", "release_head_not_ancestor"),
        ("merge_ancestry", "release_merge_not_ancestor"),
        ("checkout", "checkout_head_mismatch"),
        ("registry", "registry_slug_mismatch"),
    ],
)
def test_provenance_guards_fail_before_provider_effect(mutation, code):
    mod, mainline, store, modal, cloudflare, vercel = components()
    if mutation == "head_ancestry":
        mainline.is_ancestor = lambda older, newer: False if (older, newer) == (HEAD, MERGE) else True
    elif mutation == "merge_ancestry":
        mainline.is_ancestor = lambda older, newer: False if (older, newer) == (MERGE, TARGET) else True
    elif mutation == "checkout":
        mainline.checkout_sha = NEW_TARGET
    else:
        mainline.registry_slug_count = lambda sha, slug: 2

    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    expected = "release_head_not_ancestor" if mutation == "head_ancestry" else "internal_finalizer_failed"
    assert caught.value.code == expected
    assert store.events[-1] == ("advance", "failed", expected)
    assert modal.events == cloudflare.events == vercel.events == []


@pytest.mark.parametrize(
    ("runtime", "adapter_name", "operation", "code"),
    [
        ("modal-hosted", "modal", "deploy", "modal_deploy_failed"),
        ("modal-hosted", "modal", "canary", "modal_canary_failed"),
        ("worker-native", "cloudflare", "registry", "internal_finalizer_failed"),
        ("worker-native", "cloudflare", "deploy_worker", "worker_deploy_failed"),
        ("worker-native", "cloudflare", "smoke_worker", "worker_smoke_failed"),
        ("worker-native", "vercel", "verify_public", "public_verification_failed"),
    ],
)
def test_adapter_failure_receipts_are_typed(runtime, adapter_name, operation, code):
    mod, mainline, store, modal, cloudflare, vercel = components(runtime=runtime)
    {"modal": modal, "cloudflare": cloudflare, "vercel": vercel}[adapter_name].fail_on = operation
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == code
    assert "SENTINEL" not in str(caught.value)
    assert store.events[-1] == ("advance", "failed", code)


def test_raised_worker_deploy_exception_is_typed_and_records_no_effect():
    mod, mainline, store, modal, cloudflare, vercel = components(runtime="worker-native")
    cloudflare.fail_on = "deploy_worker_raise"
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "worker_deploy_failed"
    assert store.events[-1] == ("advance", "failed", "worker_deploy_failed")
    assert not any(event[0] == "record_effect" for event in store.events)


def test_promotion_readback_mismatch_fails_before_deployed_transition():
    mod, mainline, store, modal, cloudflare, vercel = components()
    original_detail = store.finalization_detail

    def stale_detail(finalization_id):
        detail = original_detail(finalization_id)
        if store.state == "completed":
            return {"finalization_status": "verifying_public", "submission_status": "ready_for_deploy"}
        return detail

    store.finalization_detail = stale_detail
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "promotion_readback_mismatch"
    assert not any(event[0] == "deployed" for event in store.events)


def test_registry_snapshot_must_preserve_every_required_live_slug():
    mod, mainline, store, modal, cloudflare, vercel = components()
    mainline.registry_counts["already-live"] = 0
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "internal_finalizer_failed"
    assert store.events[-1] == ("advance", "failed", "internal_finalizer_failed")
    assert modal.events == cloudflare.events == vercel.events == []


def test_publication_receipt_is_required_and_never_fabricated():
    mod, mainline, store, modal, cloudflare, vercel = components()
    vercel.fail_on = "publication"
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "public_verification_failed"
    assert store.gates is None
    assert store.events[-1] == ("advance", "failed", "public_verification_failed")


def test_invalid_green_receipt_fails_before_claim():
    mod = load_finalizer()
    bad = mod.GreenMain(TARGET, TARGET, "other-workflow", "push", "main", "success")
    mod, mainline, store, modal, cloudflare, vercel = components(receipts=[bad])
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "invalid_green_main"
    assert store.events == []


def test_effect_journal_deduplicates_provider_effect_across_generation_ids():
    mod, _mainline, store, _modal, _cloudflare, _vercel = components()
    journal = mod.EffectJournal()
    first = journal.apply(store.claim_value, "worker_deploy")
    reclaimed = replace(store.claim_value, id="fin_" + "2" * 32, attempts=2)
    second = journal.apply(reclaimed, "worker_deploy")

    assert first == second
    assert first["status"] == "passed"
    assert first["provider"] == "cloudflare"
    assert first["target_sha"] == TARGET
    assert first["artifact_hash"] == store.claim_value.artifact_hash
    assert journal.events == [
        (store.claim_value.submission_id, TARGET, store.claim_value.artifact_hash, "worker_deploy")
    ]


def fake_scenario():
    return {
        "green_main": {
            "trigger_sha": TARGET,
            "target_sha": TARGET,
            "workflow": "generated-workflow-contracts",
            "event": "push",
            "branch": "main",
            "conclusion": "success",
        },
        "claim": {
            "id": "fin_" + "1" * 32,
            "submission_id": "sub_12345678",
            "slug": "demo",
            "runtime": "worker-native",
            "target_sha": TARGET,
            "merge_sha": MERGE,
            "head_sha": HEAD,
            "source_sha256": hashlib.sha256(SOURCE).hexdigest(),
            "artifact_hash": artifact_hash(ENTRIES),
            "lease_expires_at": "2099-01-01T00:00:00Z",
            "attempts": 1,
        },
        "artifacts": {key: value.decode() for key, value in ENTRIES.items()},
        "ancestor_pairs": [[HEAD, MERGE], [MERGE, TARGET]],
        "checkout_head": TARGET,
        "registry_count": 1,
    }


def test_fake_only_cli_runs_scenario_and_emits_sorted_json(tmp_path, capsys):
    mod = load_finalizer()
    setattr(mod, "TRUSTED_LEGACY_PROFILE_DIGESTS", {
        "demo": (
            hashlib.sha256(SOURCE).hexdigest(),
            hashlib.sha256(ENTRIES["packages/skill-to-modal/profiles/demo.json"]).hexdigest(),
        ),
    })
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(fake_scenario()), encoding="utf-8")

    assert mod.main(["--scenario", str(scenario_path)]) == 0
    output = capsys.readouterr().out.strip()
    assert output == json.dumps(
        {"status": "deployed", "submission_id": "sub_12345678", "target_sha": TARGET},
        sort_keys=True,
        separators=(",", ":"),
    )


@pytest.mark.parametrize("forbidden", ["token", "url", "account", "command", "workspace"])
def test_fake_only_cli_rejects_provider_or_credential_selection(tmp_path, forbidden, capsys):
    mod = load_finalizer()
    scenario = fake_scenario()
    scenario[forbidden] = "SENTINEL_MUST_NOT_ESCAPE"
    scenario_path = tmp_path / "bad.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")

    assert mod.main(["--scenario", str(scenario_path)]) == 2
    output = capsys.readouterr().out.strip()
    assert "SENTINEL" not in output
    assert output == '{"error":"invalid_scenario"}'


@pytest.mark.parametrize(
    ("adapter_name", "expected_code"),
    [
        ("modal", "modal_preflight_failed"),
        ("cloudflare", "worker_preflight_failed"),
        ("vercel", "public_preflight_failed"),
    ],
)
def test_every_preflight_failure_is_persisted_before_provider_effect(adapter_name, expected_code):
    runtime = "modal-hosted" if adapter_name == "modal" else "worker-native"
    mod, mainline, store, modal, cloudflare, vercel = components(runtime=runtime)
    {"modal": modal, "cloudflare": cloudflare, "vercel": vercel}[adapter_name].fail_on = "preflight"
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == expected_code
    assert store.events[-1] == ("advance", "failed", expected_code)
    assert "deploy" not in modal.events
    assert "deploy_worker" not in cloudflare.events
    assert "verify_public" not in vercel.events


@pytest.mark.parametrize("boundary", ["advance:deploying_worker", "promote", "deployed"])
def test_lifecycle_write_failures_are_typed_and_never_leak(boundary):
    mod, mainline, store, modal, cloudflare, vercel = components()
    store.fail_on = boundary
    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert caught.value.code == "internal_finalizer_failed"
    assert "SENTINEL" not in str(caught.value)
    if boundary != "deployed":
        assert store.events[-1] == ("advance", "failed", "internal_finalizer_failed")


def test_modal_hosted_has_one_global_preflight_and_effect_order():
    mod, mainline, store, modal, cloudflare, vercel = components(runtime="modal-hosted")
    journal: list[str] = []

    def wrap(obj, name):
        original = getattr(obj, name)
        def called(*args, **kwargs):
            journal.append(f"{obj.name if hasattr(obj, 'name') else 'store'}:{name}")
            return original(*args, **kwargs)
        setattr(obj, name, called)

    for adapter in (modal, cloudflare, vercel):
        for method in (
            ["preflight", "deploy", "canary"] if adapter is modal else
            ["preflight", "verify_registry", "deploy_worker", "smoke_worker"] if adapter is cloudflare else
            ["preflight", "verify_public", "verify_publication"]
        ):
            wrap(adapter, method)
    for method in ("advance", "promote", "finalization_detail", "submission_detail", "mark_deployed"):
        wrap(store, method)

    mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert journal == [
        "modal:preflight", "cloudflare:preflight", "vercel:preflight",
        "store:advance", "modal:deploy", "modal:canary",
        "store:advance", "cloudflare:verify_registry", "cloudflare:deploy_worker",
        "cloudflare:smoke_worker", "store:advance", "vercel:verify_public",
        "vercel:verify_publication", "store:promote", "store:finalization_detail",
        "store:submission_detail", "store:mark_deployed", "store:submission_detail",
    ]


class SimulatedCrash(BaseException):
    pass


@pytest.mark.parametrize(
    ("runtime", "operation"),
    [
        ("modal-hosted", "modal_deploy"),
        ("modal-hosted", "modal_canary"),
        ("worker-native", "registry_verify"),
        ("worker-native", "worker_deploy"),
        ("worker-native", "worker_smoke"),
        ("worker-native", "public_verify"),
        ("worker-native", "publication_verify"),
    ],
)
def test_crash_reclaim_new_generation_never_duplicates_provider_effect(runtime, operation):
    mod, mainline, first_store, _modal, _cloudflare, _vercel = components(runtime=runtime)

    class CrashJournal(mod.EffectJournal):
        crashed = False
        def apply(self, claim, requested):
            receipt = super().apply(claim, requested)
            if requested == operation and not self.crashed:
                self.crashed = True
                raise SimulatedCrash()
            return receipt

    journal = CrashJournal()
    modal = mod._FakeModal(journal)
    cloudflare = mod._FakeCloudflare(journal)
    vercel = mod._FakeVercel(journal)
    with pytest.raises(SimulatedCrash):
        mod.run_finalizer(mainline, first_store, modal, cloudflare, vercel)

    second_store = Store(mod, runtime)
    second_store.claim_value = replace(first_store.claim_value, id="fin_" + "9" * 32, attempts=2)
    result = mod.run_finalizer(mainline, second_store, modal, cloudflare, vercel)
    assert result["status"] == "deployed"
    assert journal.events.count((
        first_store.claim_value.submission_id, TARGET,
        first_store.claim_value.artifact_hash, operation,
    )) == 1


@pytest.mark.parametrize("crash_boundary", ["promote", "deployed"])
def test_committed_terminal_write_is_resumed_without_duplicate_provider_effect(crash_boundary):
    mod, mainline, store, _modal, _cloudflare, _vercel = components()
    journal = mod.EffectJournal()
    modal = mod._FakeModal(journal)
    cloudflare = mod._FakeCloudflare(journal)
    vercel = mod._FakeVercel(journal)

    if crash_boundary == "promote":
        original = store.promote
        def crash_after_promote(claim, gates):
            original(claim, gates)
            raise SimulatedCrash()
        store.promote = crash_after_promote
    else:
        original = store.mark_deployed
        def crash_after_deployed(submission_id):
            original(submission_id)
            raise SimulatedCrash()
        store.mark_deployed = crash_after_deployed

    with pytest.raises(SimulatedCrash):
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    first_effects = list(journal.events)

    if crash_boundary == "promote":
        store.promote = original
    else:
        store.mark_deployed = original
    result = mod.run_finalizer(mainline, store, modal, cloudflare, vercel)
    assert result == {"status": "deployed", "submission_id": "sub_12345678", "target_sha": TARGET}
    assert journal.events == first_effects


def test_squash_merge_with_exact_reviewed_tree_is_accepted():
    mod, mainline, store, modal, cloudflare, vercel = components()
    original = mainline.is_ancestor
    mainline.is_ancestor = lambda older, newer: False if (older, newer) == (HEAD, MERGE) else original(older, newer)
    mainline.trees_equal = lambda left, right: (left, right) == (HEAD, MERGE)

    result = mod.run_finalizer(mainline, store, modal, cloudflare, vercel)

    assert result["status"] == "deployed"


def test_squash_merge_with_different_tree_fails_closed_with_typed_code():
    mod, mainline, store, modal, cloudflare, vercel = components()
    mainline.is_ancestor = lambda older, newer: (older, newer) == (MERGE, TARGET)
    mainline.trees_equal = lambda left, right: False

    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)

    assert caught.value.code == "release_head_not_ancestor"
    assert store.events[-1] == ("advance", "failed", "release_head_not_ancestor")
    assert modal.events == cloudflare.events == vercel.events == []


def test_failed_generation_is_diagnosed_before_completed_resume_and_surfaces_typed_code():
    mod, mainline, store, modal, cloudflare, vercel = components()
    store.state = "failed"
    store.failed_inspection = mod.FailedFinalization(
        id=store.claim_value.id, submission_id=store.claim_value.submission_id,
        status="failed", failure_code="release_head_not_ancestor",
        submission_status="ready_for_deploy", release_phase="merged_verified",
        target_sha=TARGET, source_sha256=store.claim_value.source_sha256,
        head_sha=HEAD, merge_sha=MERGE, artifact_hash=store.claim_value.artifact_hash,
        attempts=1, modal_receipt_present=False, worker_receipt_present=False,
    )

    with pytest.raises(mod.FinalizerError) as caught:
        mod.run_finalizer(mainline, store, modal, cloudflare, vercel)

    assert caught.value.code == "release_head_not_ancestor"
    assert store.events == [("claim", TARGET), ("inspect_failed", TARGET)]
    assert modal.events == cloudflare.events == vercel.events == []


def test_controlled_failed_resume_uses_fresh_generation_then_runs_normally():
    mod, mainline, store, modal, cloudflare, vercel = components()
    store.state = "failed"
    failed_id = store.claim_value.id
    store.failed_inspection = mod.FailedFinalization(
        id=store.claim_value.id, submission_id=store.claim_value.submission_id,
        status="failed", failure_code="release_head_not_ancestor",
        submission_status="failed", release_phase="merged_verified",
        target_sha=TARGET, source_sha256=store.claim_value.source_sha256,
        head_sha=HEAD, merge_sha=MERGE, artifact_hash=store.claim_value.artifact_hash,
        attempts=1, modal_receipt_present=False, worker_receipt_present=False,
    )

    result = mod.run_finalizer(mainline, store, modal, cloudflare, vercel, resume_failed=True)

    assert result["status"] == "deployed"
    assert ("inspect_failed", TARGET) in store.events
    assert ("resume_failed", TARGET, failed_id) in store.events
