"""Credential-safe contracts for the concrete Issue #141 production controller."""
from __future__ import annotations

import importlib.util
import io
import json
import re
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools" / "host-skill" / "production_release_controller.py"
SHA = "a" * 40
ARTIFACT = "b" * 64
FINALIZATION_ID = "fin_" + "f" * 32
OLD_TARGET = "9" * 40
LATEST_GREEN = "8" * 40


def load_module():
    host = str(MODULE_PATH.parent)
    if host not in sys.path:
        sys.path.insert(0, host)
    spec = importlib.util.spec_from_file_location("production_release_controller", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Response:
    def __init__(self, body, status=200):
        self.status = status
        self._raw = json.dumps(body).encode()

    def read(self, size=-1):
        return self._raw if size < 0 else self._raw[:size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_github_latest_green_binds_first_trigger_then_current_main(tmp_path):
    mod = load_module()
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)
        if "/git/ref/heads/main" in request.full_url:
            return Response({"object": {"sha": SHA}})
        return Response({
            "id": 123, "run_attempt": 2, "name": mod.WORKFLOW_NAME, "path": mod.WORKFLOW_PATH,
            "head_sha": SHA, "conclusion": "success", "event": "push", "head_branch": "main",
            "status": "completed", "head_repository": {"full_name": mod.REPOSITORY},
        })

    adapter = mod.GitHubMainlineAdapter(tmp_path, SHA, 123, 2, "github-token", opener=opener)
    first = adapter.latest_green()
    second = adapter.latest_green()
    assert first.trigger_sha == first.target_sha == SHA
    assert second.trigger_sha == second.target_sha == SHA
    assert all("harrythentrepreneur/Omo.Space" in url for url in calls)
    assert any("/actions/runs/123/attempts/2" in url for url in calls)


def test_github_stale_trigger_is_preserved_for_core_supersession(tmp_path):
    mod = load_module()
    current = "c" * 40

    def opener(request, timeout):
        if "/git/ref/heads/main" in request.full_url:
            return Response({"object": {"sha": current}})
        return Response({
            "id": 123, "run_attempt": 2, "name": mod.WORKFLOW_NAME, "path": mod.WORKFLOW_PATH,
            "head_sha": SHA, "conclusion": "success", "event": "push", "head_branch": "main",
            "status": "completed", "head_repository": {"full_name": mod.REPOSITORY},
        })

    receipt = mod.GitHubMainlineAdapter(tmp_path, SHA, 123, 2, "github-token", opener=opener).latest_green()
    assert receipt.trigger_sha == SHA and receipt.target_sha == current


def test_github_trigger_run_attempt_mismatch_fails_closed(tmp_path):
    mod = load_module()

    def opener(request, timeout):
        if "/git/ref/heads/main" in request.full_url:
            return Response({"object": {"sha": SHA}})
        return Response({
            "id": 123, "run_attempt": 1, "name": mod.WORKFLOW_NAME, "path": mod.WORKFLOW_PATH,
            "head_sha": SHA, "conclusion": "success", "event": "push", "head_branch": "main",
            "status": "completed", "head_repository": {"full_name": mod.REPOSITORY},
        })

    adapter = mod.GitHubMainlineAdapter(tmp_path, SHA, 123, 2, "github-token", opener=opener)
    with pytest.raises(mod.ControllerError) as caught:
        adapter.latest_green()
    assert caught.value.code == "trigger_run_mismatch"


def test_finalization_store_uses_only_fixed_finalizer_routes_and_redacts_token():
    mod = load_module()
    assert mod.WORKER_BASE_URL == "https://omo.space"
    requests = []
    finalization = {
        "id": "fin_" + "1" * 32, "submission_id": "sub_12345678",
        "slug": "label-normalizer-canary", "runtime": "modal-hosted", "target_sha": SHA,
        "merge_sha": "c" * 40, "head_sha": "d" * 40, "source_sha256": "e" * 64,
        "artifact_hash": ARTIFACT, "lease_expires_at": "2099-01-01T00:00:00Z", "attempts": 1,
    }

    expected_targets = [
        {"slug": item["slug"], "source_sha256": item["sha256"]}
        for item in mod.CANARY_SOURCES
    ]

    def opener(request, timeout):
        requests.append(request)
        path = request.full_url
        if path.endswith("/claim"):
            assert json.loads(request.data) == {"target_sha": SHA, "targets": expected_targets}
            return Response({"ok": True, "finalization": finalization})
        if path.endswith("/registry-slugs"):
            return Response({"ok": True, "slugs": ["label-normalizer-canary"]})
        if path.endswith("/canary-identity"):
            return Response({"ok": True, "created": True})
        if path.endswith("/detail"):
            return Response({"ok": True, "finalization": {
                **finalization, "status": "completed", "submission_status": "ready_for_publish",
                "release_phase": "promoted",
            }})
        return Response({"ok": True})

    store = mod.HttpFinalizationStore("finalizer-secret", opener=opener)
    claim = store.claim(SHA)
    assert claim and store.required_registry_slugs() == {"label-normalizer-canary"}
    store.provision_canary_identity()
    assert store.submission_detail(claim.submission_id) == {
        "status": "ready_for_publish", "release_phase": "promoted",
    }
    assert all(request.headers.get("Authorization") == "Bearer finalizer-secret" for request in requests)
    assert all(request.full_url.startswith(mod.WORKER_BASE_URL) for request in requests)
    assert "finalizer-secret" not in repr(store.__dict__.keys())


def test_finalization_store_treats_only_literal_204_as_idle():
    mod = load_module()

    def malformed(request, timeout):
        return Response({"ok": False}, status=200)

    with pytest.raises(mod.ControllerError) as caught:
        mod.HttpFinalizationStore("token", opener=malformed).claim(SHA)
    assert caught.value.code == "invalid_finalizer_response"


def test_finalization_eligibility_is_exact_bounded_and_fail_closed():
    mod = load_module()
    boolean_fields = {
        "source_sha256_present", "published_slug_present", "workflow_version_present",
        "build_evidence_present", "release_issue_url_present", "release_pr_url_present",
        "release_pr_number_present", "release_branch_present", "release_head_sha_present",
        "release_merge_sha_present", "release_artifact_hash_present",
        "finalization_target_matches", "finalization_lease_expired", "finalization_available",
        "claimable",
    }
    row = {
        "submission_id": "sub_" + "1" * 32,
        "slug": "v02-release-label-sorter",
        "status": "ready_for_deploy",
        "release_phase": "merged_verified",
        "selected_runtime": "worker-native",
        "finalization_status": None,
        **{field: True for field in boolean_fields},
    }
    requests = []

    def opener(request, timeout):
        requests.append(request)
        return Response({"ok": True, "eligibility": [row]})

    result = mod.HttpFinalizationStore("token", opener=opener).eligibility(SHA)
    assert result == [row]
    expected_targets = [
        {"slug": item["slug"], "source_sha256": item["sha256"]}
        for item in mod.CANARY_SOURCES
    ]
    assert json.loads(requests[0].data) == {"target_sha": SHA, "targets": expected_targets}
    assert requests[0].full_url.endswith("/api/internal/finalizations/eligibility")

    for malformed in (
        {**row, "claimable": 1},
        {**row, "private": "must-not-pass"},
        {**row, "slug": "unrelated"},
    ):
        with pytest.raises(mod.ControllerError, match="invalid_finalizer_eligibility"):
            mod.HttpFinalizationStore(
                "token", opener=lambda request, timeout, value=malformed: Response({"ok": True, "eligibility": [value]})
            ).eligibility(SHA)


def test_finalization_eligibility_reports_only_bounded_failure_classes():
    mod = load_module()
    boolean_fields = {
        "source_sha256_present", "published_slug_present", "workflow_version_present",
        "build_evidence_present", "release_issue_url_present", "release_pr_url_present",
        "release_pr_number_present", "release_branch_present", "release_head_sha_present",
        "release_merge_sha_present", "release_artifact_hash_present",
        "finalization_target_matches", "finalization_lease_expired", "finalization_available",
        "claimable",
    }
    row = {
        "submission_id": "sub_" + "1" * 32, "slug": "v02-release-label-sorter",
        "status": "ready_for_deploy", "release_phase": "merged_verified",
        "selected_runtime": "worker-native", "finalization_status": None,
        **{field: True for field in boolean_fields},
    }
    row_two = {
        **row,
        "submission_id": "sub_" + "2" * 32,
        "slug": "v02-support-urgency-classifier",
    }
    cases = (
        (Response({}, status=500), "finalizer_eligibility_http_500"),
        (Response({"ok": False, "eligibility": []}), "invalid_finalizer_eligibility_envelope"),
        (Response({"ok": True, "eligibility": {}}), "invalid_finalizer_eligibility_rows"),
        (Response({"ok": True, "eligibility": [row, row, row]}), "invalid_finalizer_eligibility_count"),
        (Response({"ok": True, "eligibility": [{**row, "private": True}]}), "invalid_finalizer_eligibility_shape"),
        (Response({"ok": True, "eligibility": [{**row, "submission_id": "bad"}]}), "invalid_finalizer_eligibility_identity"),
        (Response({"ok": True, "eligibility": [{**row, "slug": "unrelated"}]}), "invalid_finalizer_eligibility_slug"),
        (Response({"ok": True, "eligibility": [{**row, "status": "unknown"}]}), "invalid_finalizer_eligibility_enum"),
        (Response({"ok": True, "eligibility": [{**row, "claimable": 1}]}), "invalid_finalizer_eligibility_boolean"),
        (Response({"ok": True, "eligibility": [row_two, row]}), "invalid_finalizer_eligibility_order"),
    )
    for response, code in cases:
        with pytest.raises(mod.ControllerError) as caught:
            mod.HttpFinalizationStore("token", opener=lambda request, timeout, value=response: value).eligibility(SHA)
        assert caught.value.code == code


def test_finalization_claim_preserves_only_bounded_http_status():
    mod = load_module()

    def unauthorized(request, timeout):
        raise mod.urllib.error.HTTPError(
            request.full_url, 401, "SENTINEL_MUST_NOT_ESCAPE", {}, io.BytesIO(b"SENTINEL_BODY")
        )

    with pytest.raises(mod.ControllerError) as caught:
        mod.HttpFinalizationStore("token", opener=unauthorized).claim(SHA)
    assert caught.value.code == "finalizer_claim_http_401"
    assert "SENTINEL" not in str(caught.value)


def test_finalization_resume_preserves_only_bounded_http_status():
    mod = load_module()

    def server_failure(request, timeout):
        raise mod.urllib.error.HTTPError(
            request.full_url, 500, "SENTINEL_MUST_NOT_ESCAPE", {}, io.BytesIO(b"SENTINEL_BODY")
        )

    with pytest.raises(mod.ControllerError) as caught:
        mod.HttpFinalizationStore("token", opener=server_failure).resume_completed(SHA)
    assert caught.value.code == "finalizer_resume_http_500"
    assert "SENTINEL" not in str(caught.value)


def test_failed_finalization_http_envelopes_are_exact_and_secret_free():
    mod = load_module()
    requests = []
    failed = {
        "id": "fin_" + "1" * 32, "status": "failed",
        "failure_code": "release_head_not_ancestor", "submission_id": "sub_12345678",
        "submission_status": "ready_for_deploy", "release_phase": "merged_verified",
        "target_sha": SHA, "source_sha256": "e" * 64, "head_sha": "d" * 40,
        "merge_sha": "c" * 40, "artifact_hash": ARTIFACT, "attempts": 1,
        "modal_receipt_present": False, "worker_receipt_present": False,
    }
    claim = {
        "id": "fin_" + "2" * 32, "submission_id": "sub_12345678",
        "slug": "label-normalizer-canary", "runtime": "modal-hosted", "target_sha": SHA,
        "merge_sha": "c" * 40, "head_sha": "d" * 40, "source_sha256": "e" * 64,
        "artifact_hash": ARTIFACT, "lease_expires_at": "2099-01-01T00:00:00Z", "attempts": 2,
    }

    def opener(request, timeout):
        requests.append(request)
        if request.full_url.endswith("/failed"):
            assert json.loads(request.data) == {"target_sha": SHA}
            return Response({"ok": True, "finalization": failed})
        if request.full_url.endswith("/resume-failed"):
            assert json.loads(request.data) == {
                "target_sha": SHA, "finalization_id": failed["id"],
            }
            return Response({"ok": True, "status": "ready_for_deploy"})
        raise AssertionError(request.full_url)

    store = mod.HttpFinalizationStore("finalizer-secret", opener=opener)
    for failure_code in (
        "release_head_not_ancestor",
        "modal_preflight_failed",
        "worker_preflight_failed",
        "public_preflight_failed",
    ):
        failed["failure_code"] = failure_code
        assert store.inspect_failed(SHA) == mod.FailedFinalization(**failed)
    assert store.resume_failed(SHA, failed["id"]) is True
    assert [request.full_url.rsplit('/', 1)[-1] for request in requests] == [
        "failed", "failed", "failed", "failed", "resume-failed",
    ]


def test_recovery_candidate_boundary_is_bounded_and_fail_closed():
    mod = load_module()
    requests = []

    def opener(request, timeout):
        requests.append(request)
        assert json.loads(request.data) == {}
        return Response({
            "ok": True,
            "recovery": {
                "target_sha": OLD_TARGET, "finalization_id": FINALIZATION_ID,
                "mode": "resume_no_effect",
            },
        })

    store = mod.HttpFinalizationStore("finalizer-secret", opener=opener)
    assert store.recovery_candidate() == mod.RecoveryCandidate(
        target_sha=OLD_TARGET, finalization_id=FINALIZATION_ID, mode="resume_no_effect",
    )
    assert requests[0].full_url.endswith("/api/internal/finalizations/recovery-candidate")

    legacy = mod.HttpFinalizationStore(
        "token", opener=lambda request, timeout: Response({"error": "not_found"}, status=404)
    )
    assert legacy.recovery_candidate() is None

    for recovery in (
        {"target_sha": "bad", "finalization_id": FINALIZATION_ID, "mode": "resume_no_effect"},
        {"target_sha": OLD_TARGET, "finalization_id": "bad", "mode": "resume_no_effect"},
        {"target_sha": OLD_TARGET, "finalization_id": FINALIZATION_ID, "mode": "unsafe"},
        {"target_sha": OLD_TARGET, "finalization_id": FINALIZATION_ID, "mode": "resume_no_effect", "secret": "SENTINEL"},
    ):
        malformed = mod.HttpFinalizationStore(
            "token", opener=lambda request, timeout, recovery=recovery: Response({"ok": True, "recovery": recovery})
        )
        with pytest.raises(mod.ControllerError, match="invalid_recovery_candidate"):
            malformed.recovery_candidate()


def test_automatic_recovery_uses_exact_safe_mode_before_normal_finalization(monkeypatch):
    mod = load_module()
    events = []
    mainline = SimpleNamespace()
    modal = SimpleNamespace()
    cloudflare = SimpleNamespace()

    no_effect_store = SimpleNamespace(
        recovery_candidate=lambda: mod.RecoveryCandidate(OLD_TARGET, FINALIZATION_ID, "resume_no_effect"),
        resume_failed=lambda target, finalization_id: events.append(("resume", target, finalization_id)) or True,
    )
    assert mod.recover_failed_before_run(mainline, no_effect_store, modal, cloudflare) == {
        "status": "ready_for_deploy", "target_sha": OLD_TARGET,
    }
    assert events == [("resume", OLD_TARGET, FINALIZATION_ID)]

    events.clear()
    receipt_store = SimpleNamespace(
        recovery_candidate=lambda: mod.RecoveryCandidate(OLD_TARGET, FINALIZATION_ID, "verify_then_retry"),
    )
    monkeypatch.setattr(
        mod, "recover_rolled_back_finalization",
        lambda *args: events.append(args) or {
            "status": "ready_for_deploy", "target_sha": LATEST_GREEN,
        },
    )
    assert mod.recover_failed_before_run(mainline, receipt_store, modal, cloudflare) == {
        "status": "ready_for_deploy", "target_sha": LATEST_GREEN,
    }
    assert events == [(mainline, receipt_store, modal, cloudflare, OLD_TARGET, FINALIZATION_ID)]


def test_failed_finalization_client_rejects_extra_or_malformed_safe_fields():
    mod = load_module()
    base = {
        "id": "fin_" + "1" * 32, "status": "failed", "failure_code": "worker_deploy_failed",
        "submission_id": "sub_12345678", "submission_status": "ready_for_deploy",
        "release_phase": "merged_verified", "target_sha": SHA, "source_sha256": "e" * 64,
        "head_sha": "d" * 40, "merge_sha": "c" * 40, "artifact_hash": ARTIFACT,
        "attempts": 1, "modal_receipt_present": False, "worker_receipt_present": False,
    }
    for body in ({**base, "receipt": {"secret": "leak"}}, {**base, "head_sha": "bad"}):
        store = mod.HttpFinalizationStore(
            "token", opener=lambda request, timeout, body=body: Response({"ok": True, "finalization": body})
        )
        with pytest.raises(mod.ControllerError, match="invalid_finalizer_response"):
            store.inspect_failed(SHA)


def recovery_plan(mod):
    def receipt(provider, target, environment, reused, version, previous):
        return {
            "artifact_hash": ARTIFACT, "environment": environment,
            "previous_version_id": previous, "provider": provider, "reused": reused,
            "rollback_token": previous, "status": "passed", "target": target,
            "target_sha": OLD_TARGET, "version_id": version,
        }
    return {
        "target_sha": OLD_TARGET, "finalization_id": FINALIZATION_ID,
        "modal": {"receipt": receipt("modal", mod.MODAL_TARGET, mod.MODAL_ENVIRONMENT, False, "modal-v7", "modal-v6"),
                  "expected_active_version_id": "modal-v7"},
        "cloudflare": {"receipt": receipt("cloudflare", mod.CLOUDFLARE_TARGET, "production", False, "cf-v9", "cf-v8"),
                       "expected_active_version_id": "cf-v8"},
    }


def test_recovery_store_boundary_sends_only_exact_generation_and_validates_plan():
    mod = load_module()
    requests = []
    plan = recovery_plan(mod)

    def opener(request, timeout):
        requests.append(request)
        assert json.loads(request.data) == {
            "target_sha": OLD_TARGET, "finalization_id": FINALIZATION_ID,
        }
        if request.full_url.endswith("/recovery-plan"):
            return Response({"ok": True, "recovery": plan})
        if request.full_url.endswith("/recover-rolled-back"):
            return Response({"ok": True, "status": "ready_for_deploy"})
        raise AssertionError(request.full_url)

    store = mod.HttpFinalizationStore("finalizer-secret", opener=opener)
    assert store.recovery_plan(OLD_TARGET, FINALIZATION_ID) == plan
    assert store.recover_rolled_back(OLD_TARGET, FINALIZATION_ID) is True
    assert [request.full_url.rsplit('/', 1)[-1] for request in requests] == [
        "recovery-plan", "recover-rolled-back",
    ]
    assert all(
        set(json.loads(request.data)) == {"target_sha", "finalization_id"}
        for request in requests
    )


def test_receipt_aware_recovery_verifies_ancestry_and_exact_provider_state_without_effects():
    mod = load_module()
    plan = recovery_plan(mod)
    events = []
    mainline = SimpleNamespace(
        latest_green=lambda: mod.GreenMain(LATEST_GREEN, LATEST_GREEN, mod.WORKFLOW_NAME, "push", "main", "success"),
        is_ancestor=lambda old, new: events.append(("ancestor", old, new)) or (old, new) == (OLD_TARGET, LATEST_GREEN),
        checkout_detached=lambda sha: events.append(("checkout", sha)) or ROOT,
    )
    store = SimpleNamespace(
        recovery_plan=lambda target, fid: events.append(("plan", target, fid)) or plan,
        recover_rolled_back=lambda target, fid: events.append(("recover", target, fid)) or True,
    )
    modal = SimpleNamespace(active_version=lambda checkout, sha: events.append(("modal_read", checkout, sha)) or "modal-v7")
    cloudflare = SimpleNamespace(active_version=lambda checkout, sha: events.append(("cloudflare_read", checkout, sha)) or "cf-v8")

    assert mod.recover_rolled_back_finalization(
        mainline, store, modal, cloudflare, OLD_TARGET, FINALIZATION_ID,
    ) == {
        "status": "ready_for_deploy", "target_sha": LATEST_GREEN,
    }
    assert events == [
        ("ancestor", OLD_TARGET, LATEST_GREEN), ("plan", OLD_TARGET, FINALIZATION_ID), ("checkout", LATEST_GREEN),
        ("modal_read", ROOT, LATEST_GREEN), ("cloudflare_read", ROOT, LATEST_GREEN), ("recover", OLD_TARGET, FINALIZATION_ID),
    ]


@pytest.mark.parametrize(("failure", "code"), [
    ("ancestor", "recovery_target_not_ancestor"),
    ("modal", "modal_recovery_readback_mismatch"),
    ("cloudflare", "cloudflare_recovery_readback_mismatch"),
])
def test_receipt_aware_recovery_mismatch_never_posts(failure, code):
    mod = load_module()
    plan = recovery_plan(mod)
    posts = []
    mainline = SimpleNamespace(
        latest_green=lambda: mod.GreenMain(LATEST_GREEN, LATEST_GREEN, mod.WORKFLOW_NAME, "push", "main", "success"),
        is_ancestor=lambda old, new: failure != "ancestor",
        checkout_detached=lambda sha: ROOT,
    )
    store = SimpleNamespace(
        recovery_plan=lambda target, fid: plan,
        recover_rolled_back=lambda target, fid: posts.append((target, fid)) or True,
    )
    modal = SimpleNamespace(active_version=lambda checkout, sha: "wrong" if failure == "modal" else "modal-v7")
    cloudflare = SimpleNamespace(active_version=lambda checkout, sha: "wrong" if failure == "cloudflare" else "cf-v8")
    with pytest.raises(mod.ControllerError) as caught:
        mod.recover_rolled_back_finalization(
            mainline, store, modal, cloudflare, OLD_TARGET, FINALIZATION_ID,
        )
    assert caught.value.code == code
    assert posts == []


def test_http_failures_are_mapped_to_secret_free_trust_boundary_stages(monkeypatch, tmp_path):
    mod = load_module()

    def network_failure(*args, **kwargs):
        raise mod.urllib.error.URLError("SENTINEL_MUST_NOT_ESCAPE")

    github = mod.GitHubMainlineAdapter(tmp_path, SHA, 123, 1, "token", opener=network_failure)
    with pytest.raises(mod.ControllerError) as caught:
        github.latest_green()
    assert caught.value.code == "github_http_failed" and "SENTINEL" not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__context__ is None

    store = mod.HttpFinalizationStore("token", opener=network_failure)
    with pytest.raises(mod.ControllerError) as caught:
        store.claim(SHA)
    assert caught.value.code == "finalizer_http_failed" and "SENTINEL" not in str(caught.value)

    def typed_failure(*args, **kwargs):
        raise mod.ControllerError("http_request_failed")

    monkeypatch.setattr(mod, "_request_json", typed_failure)
    claim = SimpleNamespace(
        id=FINALIZATION_ID, submission_id="sub_12345678", slug="label-normalizer-canary",
        runtime="modal-hosted", target_sha=SHA, artifact_hash=ARTIFACT,
    )
    modal = mod.ProductionModalAdapter({})
    with pytest.raises(mod.ControllerError) as caught:
        modal.canary(claim, ROOT, {})
    assert caught.value.code == "modal_canary_http_failed"

    public = object.__new__(mod.ProductionPublicAdapter)
    public.store, public.api_key = SimpleNamespace(), "omo_" + "1" * 32
    with pytest.raises(mod.ControllerError) as caught:
        public.verify_public(claim, ROOT)
    assert caught.value.code == "public_canary_http_failed"

    def non_http_failure(*args, **kwargs):
        raise mod.ControllerError("modal_result_url_invalid")

    monkeypatch.setattr(mod, "_request_json", non_http_failure)
    with pytest.raises(mod.ControllerError) as caught:
        mod._request_json_stage("modal_canary_http_failed", "https://example.invalid")
    assert caught.value.code == "modal_result_url_invalid"


def test_http_status_is_preserved_without_reading_or_retaining_error_body():
    mod = load_module()

    def bad_gateway(request, timeout):
        raise mod.urllib.error.HTTPError(
            request.full_url, 502, "SENTINEL_MUST_NOT_ESCAPE", {}, io.BytesIO(b"SENTINEL_BODY")
        )

    assert mod._request_json("https://example.invalid", opener=bad_gateway) == (502, None)


def test_modal_canary_requires_exact_terminal_fixture(monkeypatch):
    mod = load_module()
    claim = SimpleNamespace(submission_id="sub_12345678")
    calls = []
    responses = [
        (202, {"result_url": "/v1/runs/run-" + "1" * 32 + "?call_id=fc-test&access_token=" + "x" * 32}),
        (202, {"status": "running"}),
        (200, {
            "items": [
                {"identifier": "ITEM_GREEN_APPLE"},
                {"identifier": "ITEM_GREEN_APPLE"},
                {"identifier": "ITEM_CLASS_2B"},
            ],
            "input_count": 3, "unique_count": 2, "duplicate_count": 1,
        }),
    ]

    def request_json(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(mod, "_request_json", request_json)
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)
    adapter = mod.ProductionModalAdapter({
        "HOSTED_MODAL_PROXY_TOKEN_ID": "id", "HOSTED_MODAL_PROXY_TOKEN_SECRET": "secret",
    })
    assert adapter.canary(claim, ROOT, {}) == {"status": "passed"}
    assert calls[0][0].endswith("/v1/runs")
    assert calls[0][1]["headers"]["X-Omo-Owner-Id"] == "finalizer:sub_12345678"
    assert calls[1][0].startswith("https://omo-space--cognition-label-normalizer-canary-api.modal.run/v1/runs/")


def test_modal_canary_rejects_cross_origin_result_url_before_credentialed_poll(monkeypatch):
    mod = load_module()
    calls = []

    def request_json(url, **kwargs):
        calls.append((url, kwargs))
        return 202, {"result_url": "https://evil.example/steal?call_id=fc-test&access_token=" + "x" * 32}

    monkeypatch.setattr(mod, "_request_json", request_json)
    adapter = mod.ProductionModalAdapter({
        "HOSTED_MODAL_PROXY_TOKEN_ID": "id", "HOSTED_MODAL_PROXY_TOKEN_SECRET": "secret",
    })
    claim = SimpleNamespace(submission_id="sub_12345678")
    assert adapter.canary(claim, ROOT, {}) == {"status": "failed"}
    assert len(calls) == 1 and calls[0][0].startswith(mod.MODAL_CANARY_ORIGIN)
    assert calls[0][1]["opener"] == mod.MODAL_OPENER


def test_worker_smoke_reaches_worker_with_trusted_user_agent(monkeypatch):
    mod = load_module()
    requests = []

    def urlopen(request, timeout):
        requests.append(request)
        raise mod.urllib.error.HTTPError(request.full_url, 401, "unauthorized", {}, None)

    monkeypatch.setattr(mod.urllib.request, "urlopen", urlopen)
    adapter = mod.ProductionCloudflareAdapter({})
    assert adapter.smoke_worker(SimpleNamespace(), {}) == {"status": "passed"}
    assert len(requests) == 1
    assert requests[0].get_header("User-agent") == "OmoProductionFinalizer/1.0"
    assert requests[0].get_header("Accept") == "application/json"


def test_modal_failure_recovery_retains_exact_deployed_version_without_plan_rollback(monkeypatch):
    mod = load_module()
    adapter = mod.ProductionModalAdapter({})
    claim = SimpleNamespace(id="fin_" + "1" * 32, target_sha=SHA)
    adapter.checkouts[claim.id] = ROOT
    monkeypatch.setattr(adapter, "active_version", lambda checkout, sha: "v7")
    assert adapter.rollback(claim, {"version_id": "v7", "rollback_token": "v6"}) == {"status": "passed"}


def test_modal_deploy_reuses_existing_exact_tag_without_mutation(monkeypatch):
    mod = load_module()
    rows = [
        {"Version": "v5", "Tag": SHA},
        {"Version": "v4", "Tag": SHA},
        {"Version": "v3", "Tag": "c" * 40},
    ]
    calls = []

    class Transport:
        def run_json(self, call):
            calls.append(("read", call.argv))
            return rows

        def run(self, call):
            calls.append(("write", call.argv))
            raise AssertionError("existing exact tag must not redeploy")

    adapter = mod.ProductionModalAdapter({})
    monkeypatch.setattr(adapter, "_transport", lambda claim, checkout, mutate=False: Transport())
    claim = SimpleNamespace(
        id="fin_" + "1" * 32, slug="label-normalizer-canary",
        target_sha=SHA, artifact_hash=ARTIFACT,
    )
    receipt = adapter.deploy(claim, ROOT)
    assert receipt["status"] == "passed" and receipt["reused"] is True
    assert receipt["version_id"] == "v5"
    assert [kind for kind, _ in calls] == ["read", "read"]


def test_modal_deploy_rejects_changed_reuse_history_without_mutation(monkeypatch):
    mod = load_module()
    first = [{"Version": "v5", "Tag": SHA}, {"Version": "v4", "Tag": SHA}]
    second = list(reversed(first))
    reads, calls = [first, second], []

    class Transport:
        def run_json(self, call):
            calls.append("read")
            return reads.pop(0)

        def run(self, call):
            calls.append("write")
            raise AssertionError("changed reuse history must not deploy")

    adapter = mod.ProductionModalAdapter({})
    monkeypatch.setattr(adapter, "_transport", lambda claim, checkout, mutate=False: Transport())
    claim = SimpleNamespace(
        id="fin_" + "1" * 32, slug="label-normalizer-canary",
        target_sha=SHA, artifact_hash=ARTIFACT,
    )
    with pytest.raises(RuntimeError, match="production_readback_failed"):
        adapter.deploy(claim, ROOT)
    assert calls == ["read", "read"]


@pytest.mark.parametrize("baseline", [[], [{"Version": "v2"}]])
def test_modal_deploy_validates_baseline_before_mutation(monkeypatch, baseline):
    mod = load_module()
    calls = []

    class Transport:
        def run_json(self, call):
            calls.append("read")
            return baseline

        def run(self, call):
            calls.append("write")
            raise AssertionError("malformed baseline must not deploy")

    adapter = mod.ProductionModalAdapter({})
    monkeypatch.setattr(adapter, "_transport", lambda claim, checkout, mutate=False: Transport())
    claim = SimpleNamespace(
        id="fin_" + "1" * 32, slug="label-normalizer-canary",
        target_sha=SHA, artifact_hash=ARTIFACT,
    )
    with pytest.raises(RuntimeError, match="production_readback_failed"):
        adapter.deploy(claim, ROOT)
    assert calls == ["read"]


def test_public_canary_dispatch_poll_and_exact_replay(monkeypatch):
    mod = load_module()
    run_id = "run_" + "1" * 32
    expected = json.loads((ROOT / "containers/label-normalizer-canary/tests/cases.json").read_text())["happy_path"]["output"]
    terminal = {
        "run_id": run_id, "slug": "label-normalizer-canary",
        "status": "completed", "state": "succeeded", "cost_usd": 0.1,
        "result": expected,
    }
    responses = [
        (202, {"run_id": run_id}),
        (200, terminal),
        (200, {**terminal, "idempotent_replay": True}),
    ]
    calls = []

    def request_json(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(mod, "_request_json", request_json)
    store = SimpleNamespace(provision_canary_identity=lambda: None)
    adapter = mod.ProductionPublicAdapter(store, "omo_" + "1" * 32)
    claim = SimpleNamespace(
        id=FINALIZATION_ID, slug="label-normalizer-canary", runtime="modal-hosted",
        target_sha=SHA, artifact_hash=ARTIFACT,
    )
    adapter.preflight(claim)
    receipt = adapter.verify_public(claim, ROOT)
    assert receipt["status"] == "passed" and receipt["run_id"] == run_id
    assert receipt["slug"] == "label-normalizer-canary" and receipt["cost_cents"] == 10
    assert all(call[1]["headers"]["User-Agent"] == "OmoProductionFinalizer/1.0" for call in calls)
    assert all(call[1]["headers"]["Accept"] == "application/json" for call in calls)
    assert calls[0][1]["headers"]["Idempotency-Key"] == calls[2][1]["headers"]["Idempotency-Key"]
    assert calls[0][1]["payload"] == calls[2][1]["payload"]
    assert calls[1][0].endswith(run_id)
    assert all(call[1]["headers"]["X-Omo-Finalization-Id"] == FINALIZATION_ID for call in calls)


def test_legacy_public_canary_replay_must_match_terminal_billing(monkeypatch):
    mod = load_module()
    run_id = "run_" + "4" * 32
    expected = json.loads(
        (ROOT / "containers/label-normalizer-canary/tests/cases.json").read_text()
    )["happy_path"]["output"]
    terminal = {
        "run_id": run_id, "slug": "label-normalizer-canary",
        "status": "completed", "state": "succeeded", "cost_usd": 0.1,
        "result": expected,
    }
    responses = [
        (202, {"run_id": run_id}), (200, terminal),
        (200, {**terminal, "cost_usd": 0.09, "idempotent_replay": True}),
    ]
    monkeypatch.setattr(mod, "_request_json", lambda *args, **kwargs: responses.pop(0))
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)
    adapter = mod.ProductionPublicAdapter(SimpleNamespace(), "omo_" + "1" * 32)
    claim = SimpleNamespace(
        id=FINALIZATION_ID, slug="label-normalizer-canary", runtime="modal-hosted",
        target_sha=SHA, artifact_hash=ARTIFACT,
    )

    assert adapter.verify_public(claim, ROOT) == {"status": "failed"}


def test_public_canary_preflight_rejects_new_modal_claim_before_provisioning():
    mod = load_module()
    calls = []
    adapter = mod.ProductionPublicAdapter(
        SimpleNamespace(provision_canary_identity=lambda: calls.append("provision")),
        "omo_" + "1" * 32,
    )
    claim = SimpleNamespace(
        id=FINALIZATION_ID, slug="new-modal-workflow", runtime="modal-hosted",
        target_sha=SHA, artifact_hash=ARTIFACT,
    )

    with pytest.raises(mod.ControllerError) as caught:
        adapter.preflight(claim)

    assert caught.value.code == "public_canary_contract_invalid"
    assert calls == []


def test_public_canary_uses_exact_claim_fixture_schema_and_price(monkeypatch):
    mod = load_module()
    run_id = "run_" + "2" * 32
    output = {
        "priority": "high",
        "reason": "Customer is blocked from account access and needs urgent assistance.",
        "status": "completed",
        "run_id": run_id,
        "workflow_version": "gemini-ticket-priority-canary@1.0.0",
        "usage": {
            "provider": "gemini", "model": "gemini-2.5-flash", "llm_calls": 1,
            "prompt_tokens": 20, "completion_tokens": 10, "estimated_cost_usd": 0.001,
        },
    }
    terminal = {
        "run_id": run_id, "slug": "gemini-ticket-priority-canary",
        "status": "completed", "state": "succeeded", "billed_amount_usd": 0.1,
        "output": output,
    }
    responses = [
        (202, {"run_id": run_id}),
        (200, terminal),
        (200, {**terminal, "idempotent_replay": True}),
    ]
    calls = []

    def request_json(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(mod, "_request_json", request_json)
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)
    adapter = mod.ProductionPublicAdapter(SimpleNamespace(), "omo_" + "1" * 32)
    claim = SimpleNamespace(
        id=FINALIZATION_ID,
        slug="gemini-ticket-priority-canary",
        runtime="worker-native",
        target_sha=SHA,
        artifact_hash=ARTIFACT,
    )

    receipt = adapter.verify_public(claim, ROOT)
    assert receipt["status"] == "passed"
    assert receipt["run_id"] == run_id
    assert receipt["slug"] == "gemini-ticket-priority-canary"
    assert receipt["cost_cents"] == 10
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["output_sha256"])
    fixture = json.loads((ROOT / "containers/gemini-ticket-priority-canary/tests/cases.json").read_text())
    assert calls[0][1]["payload"] == {
        "slug": "gemini-ticket-priority-canary",
        "input": fixture["happy_path"]["input"],
    }
    assert calls[0][1]["payload"] == calls[2][1]["payload"]
    assert calls[0][1]["headers"]["Idempotency-Key"] == calls[2][1]["headers"]["Idempotency-Key"]
    assert calls[0][1]["headers"]["X-Omo-Finalization-Target-Sha"] == SHA
    assert calls[0][1]["headers"]["X-Omo-Finalization-Artifact-Hash"] == ARTIFACT
    assert all(call[1]["headers"]["X-Omo-Finalization-Id"] == FINALIZATION_ID for call in calls)


@pytest.mark.parametrize("mutation", ["slug", "billing", "output"])
def test_public_canary_replay_must_match_terminal_evidence(monkeypatch, mutation):
    mod = load_module()
    run_id = "run_" + "3" * 32
    output = {
        "priority": "high", "reason": "Customer access is blocked and needs urgent help.",
        "status": "completed", "run_id": run_id,
        "workflow_version": "gemini-ticket-priority-canary@1.0.0",
        "usage": {
            "provider": "gemini", "model": "gemini-2.5-flash", "llm_calls": 1,
            "prompt_tokens": 20, "completion_tokens": 10, "estimated_cost_usd": 0.001,
        },
    }
    terminal = {
        "run_id": run_id, "slug": "gemini-ticket-priority-canary",
        "status": "completed", "state": "succeeded", "billed_amount_usd": 0.1,
        "output": output,
    }
    replay = {**terminal, "idempotent_replay": True}
    if mutation == "slug":
        replay["slug"] = "other-workflow"
    elif mutation == "billing":
        replay["billed_amount_usd"] = 0.09
    else:
        replay["output"] = {**output, "priority": "low"}
    responses = [(202, {"run_id": run_id}), (200, terminal), (200, replay)]
    monkeypatch.setattr(mod, "_request_json", lambda *args, **kwargs: responses.pop(0))
    monkeypatch.setattr(mod.time, "sleep", lambda _: None)
    adapter = mod.ProductionPublicAdapter(SimpleNamespace(), "omo_" + "1" * 32)
    claim = SimpleNamespace(
        id=FINALIZATION_ID, slug="gemini-ticket-priority-canary", runtime="worker-native",
        target_sha=SHA, artifact_hash=ARTIFACT,
    )

    assert adapter.verify_public(claim, ROOT) == {"status": "failed"}


def test_strict_json_rejects_overflow_and_duplicate_http_fields():
    mod = load_module()

    with pytest.raises(ValueError):
        mod._strict_json_bytes(b'{"value":1e400}')
    with pytest.raises(mod.ControllerError) as duplicate:
        mod._safe_json_response(io.BytesIO(b'{"cost_usd":0.1,"cost_usd":0.2}'))
    with pytest.raises(mod.ControllerError) as overflow:
        mod._safe_json_response(io.BytesIO(b'{"cost_usd":1e400}'))

    assert duplicate.value.code == "http_response_invalid"
    assert overflow.value.code == "http_response_invalid"


def test_canary_json_read_cannot_be_swapped_to_symlink(monkeypatch, tmp_path):
    mod = load_module()
    root = tmp_path / "root"
    root.mkdir()
    target = root / "value.json"
    outside = tmp_path / "outside.json"
    target.write_text('{"value":"inside"}', encoding="utf-8")
    outside.write_text('{"value":"escape"}', encoding="utf-8")
    original_open = Path.open
    swapped = False

    def swapping_open(path, *args, **kwargs):
        nonlocal swapped
        if path == target:
            path.unlink()
            path.symlink_to(outside)
            swapped = True
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", swapping_open)
    try:
        value = mod._canary_json(root, "value.json")
    except mod.ControllerError:
        value = None

    assert swapped is False or value != {"value": "escape"}


def test_public_canary_loads_completed_pure_data_contract():
    mod = load_module()

    contract = mod._claim_canary_contract(
        SimpleNamespace(slug="release-tag-sorter-canary"), ROOT
    )

    assert contract["execution_kind"] == "pure_data"
    assert contract["slug"] == "release-tag-sorter-canary"
    assert contract["cost_cents"] == 10


def test_public_canary_preserves_legacy_single_llm_schema():
    mod = load_module()

    contract = mod._claim_canary_contract(
        SimpleNamespace(slug="facebook-ads-copywriter"), ROOT
    )

    assert contract["execution_kind"] == "single_llm"
    assert contract["public_output_schema"] == contract["output_schema"]


def test_public_canary_rejects_non_object_profile_with_typed_error(tmp_path):
    mod = load_module()
    slug = "gemini-ticket-priority-canary"
    shutil.copytree(ROOT / "containers" / slug, tmp_path / "containers" / slug)
    profile_dir = tmp_path / "packages/skill-to-modal/profiles"
    profile_dir.mkdir(parents=True)
    (profile_dir / f"{slug}.json").write_text("[]", encoding="utf-8")

    with pytest.raises(mod.ControllerError) as caught:
        mod._claim_canary_contract(SimpleNamespace(slug=slug), tmp_path)

    assert caught.value.code == "public_canary_contract_invalid"


def test_public_canary_rejects_schema_references_without_network(monkeypatch, tmp_path):
    mod = load_module()
    slug = "gemini-ticket-priority-canary"
    shutil.copytree(ROOT / "containers" / slug, tmp_path / "containers" / slug)
    profile_dir = tmp_path / "packages/skill-to-modal/profiles"
    profile_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "packages/skill-to-modal/profiles" / f"{slug}.json", profile_dir)
    schema_path = tmp_path / "containers" / slug / "schemas/output.json"
    schema_path.write_text(json.dumps({"$ref": "https://example.invalid/schema.json"}), encoding="utf-8")
    profile_path = profile_dir / f"{slug}.json"
    profile = json.loads(profile_path.read_text())
    profile["output_schema"] = {"$ref": "https://example.invalid/schema.json"}
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    calls = []
    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda *args, **kwargs: calls.append(args))
    claim = SimpleNamespace(slug=slug)

    with pytest.raises(mod.ControllerError) as caught:
        mod._claim_canary_contract(claim, tmp_path)

    assert caught.value.code == "public_canary_contract_invalid"
    assert calls == []


def test_public_canary_rejects_hosted_output_schema_drift(tmp_path):
    mod = load_module()
    slug = "gemini-ticket-priority-canary"
    shutil.copytree(ROOT / "containers" / slug, tmp_path / "containers" / slug)
    profile_dir = tmp_path / "packages/skill-to-modal/profiles"
    profile_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "packages/skill-to-modal/profiles" / f"{slug}.json", profile_dir)
    hosted_path = tmp_path / "containers" / slug / "hosted-profile.json"
    hosted = json.loads(hosted_path.read_text())
    hosted["run_manifest"]["output_schema"] = {"type": "object", "additionalProperties": True}
    hosted_path.write_text(json.dumps(hosted), encoding="utf-8")

    with pytest.raises(mod.ControllerError) as caught:
        mod._claim_canary_contract(SimpleNamespace(slug=slug), tmp_path)

    assert caught.value.code == "public_canary_contract_invalid"


def test_public_canary_rejects_nonfinite_price_with_typed_error(tmp_path):
    mod = load_module()
    slug = "gemini-ticket-priority-canary"
    shutil.copytree(ROOT / "containers" / slug, tmp_path / "containers" / slug)
    profile_dir = tmp_path / "packages/skill-to-modal/profiles"
    profile_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "packages/skill-to-modal/profiles" / f"{slug}.json", profile_dir)
    hosted_path = tmp_path / "containers" / slug / "hosted-profile.json"
    hosted = json.loads(hosted_path.read_text())
    hosted["run_manifest"]["price_usd"] = "NaN"
    hosted["catalog"]["runPrice"] = "NaN"
    hosted_path.write_text(json.dumps(hosted), encoding="utf-8")

    with pytest.raises(mod.ControllerError) as caught:
        mod._claim_canary_contract(SimpleNamespace(slug=slug), tmp_path)

    assert caught.value.code == "public_canary_contract_invalid"


def test_publication_verifies_canonical_run_redirect_and_title(monkeypatch):
    mod = load_module()

    class HtmlResponse:
        status = 200
        def read(self, size=-1):
            return b"<html><head><title>Run a workflow | Omo</title></head></html>"
        def geturl(self):
            return mod.PUBLIC_ORIGIN + "/run?slug=" + mod.MODAL_ALLOWED_SLUG
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda request, timeout: HtmlResponse())
    adapter = mod.ProductionPublicAdapter(SimpleNamespace(), "omo_" + "1" * 32)
    claim = SimpleNamespace(slug="label-normalizer-canary")
    assert adapter.verify_publication(claim, ROOT) == {"status": "published"}


def test_public_canary_seed_uses_two_canonical_exact_checkout_sources(monkeypatch):
    mod = load_module()
    calls = []
    responses = iter([
        (202, {"id": "sub_" + "1" * 32, "slug": "v02-release-label-sorter", "status": "failed", "duplicate": True, "changed": False}),
        (202, {"id": "sub_" + "2" * 32, "slug": "v02-support-urgency-classifier", "status": "queued", "duplicate": False, "changed": True}),
    ])

    def request_json_stage(stage, url, **kwargs):
        calls.append((stage, url, kwargs))
        return next(responses)

    monkeypatch.setattr(mod, "_request_json_stage", request_json_stage)
    provisioned = []
    adapter = mod.ProductionPublicAdapter(
        SimpleNamespace(provision_canary_identity=lambda: provisioned.append(True)),
        "omo_" + "1" * 32,
    )
    assert adapter.seed_submissions(ROOT) == [
        {"slug": "v02-release-label-sorter", "submission_id": "sub_" + "1" * 32, "submission_status": "failed"},
        {"slug": "v02-support-urgency-classifier", "submission_id": "sub_" + "2" * 32, "submission_status": "queued"},
    ]
    assert provisioned == [True]
    assert [call[2]["payload"]["runtime_preference"] for call in calls] == ["worker-native", "worker-native"]
    assert [call[2]["payload"]["name"] for call in calls] == [
        "V02 Release Label Sorter", "V02 Support Urgency Classifier",
    ]
    assert [call[2]["payload"]["content"] for call in calls] == [
        (ROOT / "tools/host-skill/canaries/v02-release-label-sorter/SKILL.md").read_text(),
        (ROOT / "tools/host-skill/canaries/v02-support-urgency-classifier/SKILL.md").read_text(),
    ]
    assert all(call[0] == "public_canary_http_failed" and call[1] == mod.PUBLIC_ORIGIN + "/api/submit" for call in calls)


def test_public_canary_retry_is_exact_owner_submission_only(monkeypatch):
    mod = load_module()
    submission_id = "sub_" + "1" * 32
    calls = []

    def request_json_stage(stage, url, **kwargs):
        calls.append((stage, url, kwargs))
        return 200, {"ok": True, "retried": True, "submission": {
            "id": submission_id, "slug": "v02-release-label-sorter", "status": "queued",
        }}

    monkeypatch.setattr(mod, "_request_json_stage", request_json_stage)
    adapter = mod.ProductionPublicAdapter(SimpleNamespace(), "omo_" + "1" * 32)
    assert adapter.retry_submission(submission_id, "v02-release-label-sorter") == {
        "status": "retried", "slug": "v02-release-label-sorter", "submission_id": submission_id,
    }
    assert calls == [("public_canary_http_failed", mod.PUBLIC_ORIGIN + f"/api/submissions/{submission_id}/retry", {
        "method": "POST", "payload": {},
        "headers": {"X-API-Key": "omo_" + "1" * 32, "Content-Type": "application/json"},
        "timeout": 30,
    })]


def test_public_canary_failed_seed_requires_idempotent_replay_evidence(monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "_request_json_stage", lambda *args, **kwargs: (202, {
        "id": "sub_" + "1" * 32, "slug": "v02-release-label-sorter", "status": "failed",
        "duplicate": False, "changed": True,
    }))
    adapter = mod.ProductionPublicAdapter(
        SimpleNamespace(provision_canary_identity=lambda: None), "omo_" + "1" * 32,
    )
    with pytest.raises(mod.ControllerError, match="production_canary_seed_failed"):
        adapter.seed_submissions(ROOT)


def test_public_canary_seed_rejects_parent_symlink_tamper_and_oversize(monkeypatch, tmp_path):
    mod = load_module()
    store = SimpleNamespace(provision_canary_identity=lambda: None)
    adapter = mod.ProductionPublicAdapter(store, "omo_" + "1" * 32)
    monkeypatch.setattr(mod, "_request_json_stage", lambda *args, **kwargs: pytest.fail("must not submit"))

    external = tmp_path / "external"
    external.mkdir()
    (external / "SKILL.md").write_bytes(
        (ROOT / "tools/host-skill/canaries/v02-release-label-sorter/SKILL.md").read_bytes()
    )
    linked = tmp_path / "linked"
    (linked / "tools/host-skill/canaries").mkdir(parents=True)
    (linked / "tools/host-skill/canaries/v02-release-label-sorter").symlink_to(external, target_is_directory=True)
    with pytest.raises(mod.ControllerError, match="production_canary_source_invalid"):
        adapter.seed_submissions(linked)

    for name, raw in (("tampered", b"---\nname: label-normalizer-canary\n---\nwrong\n"),
                      ("oversized", b"x" * (mod.CANARY_SOURCE_MAX_BYTES + 1))):
        checkout = tmp_path / name
        source_dir = checkout / "tools/host-skill/canaries/v02-release-label-sorter"
        source_dir.mkdir(parents=True)
        (source_dir / "SKILL.md").write_bytes(raw)
        with pytest.raises(mod.ControllerError, match="production_canary_source_invalid"):
            adapter.seed_submissions(checkout)


def test_run_once_seeds_only_after_idle_and_clean_checkout_validation(monkeypatch, tmp_path):
    mod = load_module()
    order = []
    target = tmp_path / "target"
    target.mkdir()

    class Mainline:
        def __init__(self, checkout, *args):
            assert checkout == target

        def checkout_detached(self, sha):
            order.append(("checkout", sha))
            return target

    class Public:
        def __init__(self, store, key):
            assert key == "omo_" + "1" * 32

        def seed_submissions(self, checkout):
            order.append(("seed", checkout))
            return [
                {"slug": "v02-release-label-sorter", "submission_id": "sub_" + "2" * 32, "submission_status": "queued"},
                {"slug": "v02-support-urgency-classifier", "submission_id": "sub_" + "3" * 32, "submission_status": "queued"},
            ]

    class Cloudflare:
        def __init__(self, env):
            pass

        def ensure_builder_schedule(self, checkout, sha):
            order.append(("schedule", checkout, sha))

    store = SimpleNamespace(eligibility=lambda sha: order.append(("eligibility", sha)) or [{
        "submission_id": "sub_" + "2" * 32,
        "slug": "v02-release-label-sorter",
        "status": "ready_for_deploy",
        "release_phase": "merged_verified",
        "selected_runtime": "worker-native",
        "claimable": False,
    }])
    monkeypatch.setattr(mod, "GitHubMainlineAdapter", Mainline)
    monkeypatch.setattr(mod, "HttpFinalizationStore", lambda token: store)
    monkeypatch.setattr(mod, "ProductionModalAdapter", lambda env: object())
    monkeypatch.setattr(mod, "ProductionCloudflareAdapter", Cloudflare)
    monkeypatch.setattr(mod, "ProductionPublicAdapter", Public)
    monkeypatch.setattr(
        mod, "recover_failed_before_run",
        lambda *args: order.append(("recovery", SHA)) or None,
    )
    monkeypatch.setattr(mod, "run_finalizer", lambda *args, **kwargs: order.append(("finalizer", SHA)) or {"status": "idle", "target_sha": SHA})
    result = mod.run_once(SimpleNamespace(trigger_sha=SHA, run_id="1", run_attempt="1"), {
        "GITHUB_WORKSPACE": str(tmp_path), "GITHUB_TOKEN": "token",
        "RELEASE_FINALIZER_TOKEN": "finalizer", "PRODUCTION_CANARY_API_KEY": "omo_" + "1" * 32,
    })
    assert order == [
        ("recovery", SHA), ("finalizer", SHA), ("eligibility", SHA), ("checkout", SHA),
        ("schedule", target, SHA), ("seed", target),
    ]
    assert result == {
        "status": "seeded", "target_sha": SHA,
        "eligibility": [{
            "submission_id": "sub_" + "2" * 32,
            "slug": "v02-release-label-sorter",
            "status": "ready_for_deploy",
            "release_phase": "merged_verified",
            "selected_runtime": "worker-native",
            "claimable": False,
        }],
        "submissions": [
            {"slug": "v02-release-label-sorter", "submission_id": "sub_" + "2" * 32, "submission_status": "queued"},
            {"slug": "v02-support-urgency-classifier", "submission_id": "sub_" + "3" * 32, "submission_status": "queued"},
        ],
    }


def test_run_once_deployed_includes_bounded_eligibility_snapshot(monkeypatch, tmp_path):
    mod = load_module()
    eligibility = [{
        "submission_id": "sub_" + "2" * 32,
        "slug": "v02-release-label-sorter",
        "status": "ready_for_deploy",
        "release_phase": "merged_verified",
        "selected_runtime": "worker-native",
        "claimable": False,
    }]
    store = SimpleNamespace(eligibility=lambda sha: eligibility if sha == SHA else None)
    monkeypatch.setattr(mod, "GitHubMainlineAdapter", lambda *args: object())
    monkeypatch.setattr(mod, "HttpFinalizationStore", lambda token: store)
    monkeypatch.setattr(mod, "ProductionModalAdapter", lambda env: object())
    monkeypatch.setattr(mod, "ProductionCloudflareAdapter", lambda env: object())
    monkeypatch.setattr(mod, "ProductionPublicAdapter", lambda store, key: object())
    monkeypatch.setattr(mod, "recover_failed_before_run", lambda *args: None)
    monkeypatch.setattr(mod, "run_finalizer", lambda *args, **kwargs: {
        "status": "deployed", "submission_id": "sub_" + "3" * 32, "target_sha": SHA,
    })

    result = mod.run_once(SimpleNamespace(trigger_sha=SHA, run_id="1", run_attempt="1"), {
        "GITHUB_WORKSPACE": str(tmp_path), "GITHUB_TOKEN": "token",
        "RELEASE_FINALIZER_TOKEN": "finalizer", "PRODUCTION_CANARY_API_KEY": "omo_" + "1" * 32,
    })

    assert result == {
        "status": "deployed", "submission_id": "sub_" + "3" * 32,
        "target_sha": SHA, "eligibility": eligibility,
    }


def test_cloudflare_builder_schedule_is_applied_and_read_back_exactly(monkeypatch):
    mod = load_module()
    responses = [
        (200, {"success": True, "result": {"schedules": []}}),
        (200, {"success": True, "result": {"schedules": [{"cron": "*/1 * * * *"}]}}),
        (200, {"success": True, "result": {"schedules": [{"cron": "*/1 * * * *"}]}}),
    ]
    requests = []

    def request_json_stage(stage, url, **kwargs):
        requests.append((stage, url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(mod, "_request_json_stage", request_json_stage)
    adapter = mod.ProductionCloudflareAdapter({
        "CLOUDFLARE_ACCOUNT_ID": "a" * 32, "CLOUDFLARE_API_TOKEN": "token",
    })
    assert adapter.ensure_builder_schedule(ROOT, SHA) == {"status": "passed", "changed": True}
    assert len(requests) == 3 and all(item[0] == "cloudflare_schedule_http_failed" for item in requests)
    assert all(item[1].endswith("/workers/scripts/cognition-demos/schedules") for item in requests)
    assert requests[1][2]["method"] == "PUT"
    assert requests[1][2]["payload"] == [{"cron": "*/1 * * * *"}]
    assert requests[1][2]["headers"] == {
        "Authorization": "Bearer token", "Content-Type": "application/json",
    }
    responses.append((200, {"success": True, "result": {"schedules": [{"cron": "*/1 * * * *"}]}}))
    assert adapter.ensure_builder_schedule(ROOT, SHA) == {"status": "passed", "changed": False}
    assert len(requests) == 4


def test_cloudflare_schedule_http_stage_is_allowlisted_without_exposing_response():
    mod = load_module()
    status, body = mod._request_json_stage(
        "cloudflare_schedule_http_failed", "https://api.cloudflare.com/client/v4/test",
        opener=lambda request, timeout: Response({"success": True, "result": []}),
    )
    assert status == 200 and body == {"success": True, "result": []}


def test_controller_cli_rejects_every_user_selectable_or_malformed_identity(capsys):
    mod = load_module()
    assert mod.main(["--trigger-sha", "bad", "--run-id", "1", "--run-attempt", "1"]) == 2
    assert "invalid_controller_input" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        mod.main(["--trigger-sha", SHA, "--run-id", "1", "--run-attempt", "1", "--target", "evil"])
