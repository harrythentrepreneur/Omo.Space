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


def test_controller_cli_rejects_every_user_selectable_or_malformed_identity(capsys):
    mod = load_module()
    assert mod.main(["--trigger-sha", "bad", "--run-id", "1", "--run-attempt", "1"]) == 2
    assert "invalid_controller_input" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        mod.main(["--trigger-sha", SHA, "--run-id", "1", "--run-attempt", "1", "--target", "evil"])
