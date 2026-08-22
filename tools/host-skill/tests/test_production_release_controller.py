"""Credential-safe contracts for the concrete Issue #141 production controller."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools" / "host-skill" / "production_release_controller.py"
SHA = "a" * 40
ARTIFACT = "b" * 64
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

    def opener(request, timeout):
        requests.append(request)
        path = request.full_url
        if path.endswith("/claim"):
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
        assert json.loads(request.data) == {"target_sha": SHA}
        if request.full_url.endswith("/failed"):
            return Response({"ok": True, "finalization": failed})
        if request.full_url.endswith("/resume-failed"):
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
    assert store.resume_failed(SHA) is True
    assert [request.full_url.rsplit('/', 1)[-1] for request in requests] == [
        "failed", "failed", "failed", "failed", "resume-failed",
    ]


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
        "target_sha": OLD_TARGET,
        "modal": {"receipt": receipt("modal", mod.MODAL_TARGET, mod.MODAL_ENVIRONMENT, True, "modal-v6", None),
                  "expected_active_version_id": "modal-v6"},
        "cloudflare": {"receipt": receipt("cloudflare", mod.CLOUDFLARE_TARGET, "production", False, "cf-v9", "cf-v8"),
                       "expected_active_version_id": "cf-v8"},
    }


def test_recovery_store_boundary_sends_only_target_sha_and_validates_plan():
    mod = load_module()
    requests = []
    plan = recovery_plan(mod)

    def opener(request, timeout):
        requests.append(request)
        assert json.loads(request.data) == {"target_sha": OLD_TARGET}
        if request.full_url.endswith("/recovery-plan"):
            return Response({"ok": True, "recovery": plan})
        if request.full_url.endswith("/recover-rolled-back"):
            return Response({"ok": True, "status": "ready_for_deploy"})
        raise AssertionError(request.full_url)

    store = mod.HttpFinalizationStore("finalizer-secret", opener=opener)
    assert store.recovery_plan(OLD_TARGET) == plan
    assert store.recover_rolled_back(OLD_TARGET) is True
    assert [request.full_url.rsplit('/', 1)[-1] for request in requests] == [
        "recovery-plan", "recover-rolled-back",
    ]
    assert all(set(json.loads(request.data)) == {"target_sha"} for request in requests)


def test_receipt_aware_recovery_verifies_ancestry_and_exact_provider_state_without_effects():
    mod = load_module()
    plan = recovery_plan(mod)
    events = []
    mainline = SimpleNamespace(
        latest_green=lambda: mod.GreenMain(LATEST_GREEN, LATEST_GREEN, mod.WORKFLOW_NAME, "push", "main", "success"),
        is_ancestor=lambda old, new: events.append(("ancestor", old, new)) or (old, new) == (OLD_TARGET, LATEST_GREEN),
    )
    store = SimpleNamespace(
        recovery_plan=lambda target: events.append(("plan", target)) or plan,
        recover_rolled_back=lambda target: events.append(("recover", target)) or True,
    )
    modal = SimpleNamespace(active_version=lambda: events.append("modal_read") or "modal-v6")
    cloudflare = SimpleNamespace(active_version=lambda: events.append("cloudflare_read") or "cf-v8")

    assert mod.recover_rolled_back_finalization(mainline, store, modal, cloudflare, OLD_TARGET) == {
        "status": "ready_for_deploy", "target_sha": LATEST_GREEN,
    }
    assert events == [
        ("ancestor", OLD_TARGET, LATEST_GREEN), ("plan", OLD_TARGET),
        "modal_read", "cloudflare_read", ("recover", OLD_TARGET),
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
    )
    store = SimpleNamespace(
        recovery_plan=lambda target: plan,
        recover_rolled_back=lambda target: posts.append(target) or True,
    )
    modal = SimpleNamespace(active_version=lambda: "wrong" if failure == "modal" else "modal-v6")
    cloudflare = SimpleNamespace(active_version=lambda: "wrong" if failure == "cloudflare" else "cf-v8")
    with pytest.raises(mod.ControllerError) as caught:
        mod.recover_rolled_back_finalization(mainline, store, modal, cloudflare, OLD_TARGET)
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
    claim = SimpleNamespace(submission_id="sub_12345678", target_sha=SHA, artifact_hash=ARTIFACT)
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
    responses = [
        (202, {"run_id": run_id}),
        (200, {"run_id": run_id, "status": "succeeded", "result": {
            "items": [
                {"identifier": "ITEM_GREEN_APPLE"}, {"identifier": "ITEM_GREEN_APPLE"},
                {"identifier": "ITEM_CLASS_2B"},
            ],
            "input_count": 3, "unique_count": 2, "duplicate_count": 1,
        }}),
        (200, {"run_id": run_id, "idempotent_replay": True}),
    ]
    calls = []

    def request_json(url, **kwargs):
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(mod, "_request_json", request_json)
    store = SimpleNamespace(provision_canary_identity=lambda: None)
    adapter = mod.ProductionPublicAdapter(store, "omo_" + "1" * 32)
    claim = SimpleNamespace(target_sha=SHA, artifact_hash=ARTIFACT)
    adapter.preflight(claim)
    assert adapter.verify_public(claim, ROOT) == {"status": "passed"}
    assert calls[0][1]["headers"]["Idempotency-Key"] == calls[2][1]["headers"]["Idempotency-Key"]
    assert calls[0][1]["payload"] == calls[2][1]["payload"]
    assert calls[1][0].endswith(run_id)


def test_public_canary_seed_uses_only_canonical_exact_checkout_source(monkeypatch):
    mod = load_module()
    calls = []

    def request_json_stage(stage, url, **kwargs):
        calls.append((stage, url, kwargs))
        return 202, {
            "id": "sub_" + "1" * 32, "slug": "label-normalizer-canary", "status": "failed",
            "duplicate": True, "changed": False,
        }

    monkeypatch.setattr(mod, "_request_json_stage", request_json_stage)
    provisioned = []
    adapter = mod.ProductionPublicAdapter(
        SimpleNamespace(provision_canary_identity=lambda: provisioned.append(True)),
        "omo_" + "1" * 32,
    )
    assert adapter.seed_submission(ROOT) == {
        "status": "queued", "submission_id": "sub_" + "1" * 32, "submission_status": "failed",
    }
    assert provisioned == [True]
    stage, url, kwargs = calls[0]
    source = (ROOT / "containers/label-normalizer-canary/source/SKILL.md").read_text()
    assert stage == "public_canary_http_failed" and url == mod.PUBLIC_ORIGIN + "/api/submit"
    assert kwargs["headers"] == {"X-API-Key": "omo_" + "1" * 32, "Content-Type": "application/json"}
    assert kwargs["payload"] == {
        "name": "Label normalizer canary", "content": source,
        "visibility": "public", "runtime_preference": "modal-hosted",
    }


def test_public_canary_retry_is_exact_owner_submission_only(monkeypatch):
    mod = load_module()
    submission_id = "sub_" + "1" * 32
    calls = []

    def request_json_stage(stage, url, **kwargs):
        calls.append((stage, url, kwargs))
        return 200, {"ok": True, "retried": True, "submission": {
            "id": submission_id, "slug": "label-normalizer-canary", "status": "queued",
        }}

    monkeypatch.setattr(mod, "_request_json_stage", request_json_stage)
    adapter = mod.ProductionPublicAdapter(SimpleNamespace(), "omo_" + "1" * 32)
    assert adapter.retry_submission(submission_id) == {"status": "retried", "submission_id": submission_id}
    assert calls == [("public_canary_http_failed", mod.PUBLIC_ORIGIN + f"/api/submissions/{submission_id}/retry", {
        "method": "POST", "payload": {},
        "headers": {"X-API-Key": "omo_" + "1" * 32, "Content-Type": "application/json"},
        "timeout": 30,
    })]


def test_public_canary_failed_seed_requires_idempotent_replay_evidence(monkeypatch):
    mod = load_module()
    monkeypatch.setattr(mod, "_request_json_stage", lambda *args, **kwargs: (202, {
        "id": "sub_" + "1" * 32, "slug": "label-normalizer-canary", "status": "failed",
        "duplicate": False, "changed": True,
    }))
    adapter = mod.ProductionPublicAdapter(
        SimpleNamespace(provision_canary_identity=lambda: None), "omo_" + "1" * 32,
    )
    with pytest.raises(mod.ControllerError, match="production_canary_seed_failed"):
        adapter.seed_submission(ROOT)


def test_public_canary_seed_rejects_parent_symlink_tamper_and_oversize(monkeypatch, tmp_path):
    mod = load_module()
    store = SimpleNamespace(provision_canary_identity=lambda: None)
    adapter = mod.ProductionPublicAdapter(store, "omo_" + "1" * 32)
    monkeypatch.setattr(mod, "_request_json_stage", lambda *args, **kwargs: pytest.fail("must not submit"))

    external = tmp_path / "external"
    external.mkdir()
    (external / "source").mkdir()
    (external / "source/SKILL.md").write_bytes(
        (ROOT / "containers/label-normalizer-canary/source/SKILL.md").read_bytes()
    )
    linked = tmp_path / "linked"
    (linked / "containers").mkdir(parents=True)
    (linked / "containers/label-normalizer-canary").symlink_to(external, target_is_directory=True)
    with pytest.raises(mod.ControllerError, match="production_canary_source_invalid"):
        adapter.seed_submission(linked)

    for name, raw in (("tampered", b"---\nname: label-normalizer-canary\n---\nwrong\n"),
                      ("oversized", b"x" * (mod.CANARY_SOURCE_MAX_BYTES + 1))):
        checkout = tmp_path / name
        source_dir = checkout / "containers/label-normalizer-canary/source"
        source_dir.mkdir(parents=True)
        (source_dir / "SKILL.md").write_bytes(raw)
        with pytest.raises(mod.ControllerError, match="production_canary_source_invalid"):
            adapter.seed_submission(checkout)


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

        def seed_submission(self, checkout):
            order.append(("seed", checkout))
            return {"status": "queued", "submission_id": "sub_" + "2" * 32}

    class Cloudflare:
        def __init__(self, env):
            pass

        def ensure_builder_schedule(self, checkout, sha):
            order.append(("schedule", checkout, sha))

    monkeypatch.setattr(mod, "GitHubMainlineAdapter", Mainline)
    monkeypatch.setattr(mod, "HttpFinalizationStore", lambda token: object())
    monkeypatch.setattr(mod, "ProductionModalAdapter", lambda env: object())
    monkeypatch.setattr(mod, "ProductionCloudflareAdapter", Cloudflare)
    monkeypatch.setattr(mod, "ProductionPublicAdapter", Public)
    monkeypatch.setattr(mod, "run_finalizer", lambda *args, **kwargs: order.append(("finalizer", SHA)) or {"status": "idle", "target_sha": SHA})
    result = mod.run_once(SimpleNamespace(trigger_sha=SHA, run_id="1", run_attempt="1"), {
        "GITHUB_WORKSPACE": str(tmp_path), "GITHUB_TOKEN": "token",
        "RELEASE_FINALIZER_TOKEN": "finalizer", "PRODUCTION_CANARY_API_KEY": "omo_" + "1" * 32,
    })
    assert order == [("finalizer", SHA), ("checkout", SHA), ("schedule", target, SHA), ("seed", target)]
    assert result == {"status": "seeded", "target_sha": SHA, "submission_id": "sub_" + "2" * 32}


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
