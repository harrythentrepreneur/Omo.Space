from __future__ import annotations

import http.client
import importlib.util
import io
import json
import os
import socket
import sys
import threading
import time
import urllib.error
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "modal_hermes_builder.py"
SMOKE_SCRIPT = SCRIPT.with_name("modal_hermes_smoke.py")


def load_builder():
    spec = importlib.util.spec_from_file_location("omo_modal_builder", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_modal_image_includes_trusted_gate_dependencies() -> None:
    builder = load_builder()
    source = SCRIPT.read_text(encoding="utf-8")
    assert builder.PYTEST_VERSION == "8.4.0"
    assert builder.JSONSCHEMA_VERSION == "4.26.0"
    assert builder.FASTAPI_VERSION == "0.109.0"
    assert 'f"pytest=={PYTEST_VERSION}"' in source
    assert 'f"jsonschema=={JSONSCHEMA_VERSION}"' in source
    assert 'f"fastapi=={FASTAPI_VERSION}"' in source


def test_modal_image_matches_worker_contract_node_runtime() -> None:
    builder = load_builder()
    source = SCRIPT.read_text(encoding="utf-8")
    assert builder.NODE_MAJOR == "22"
    assert 'modal.Image.from_registry(f"node:{NODE_MAJOR}-bookworm-slim", add_python="3.11")' in source
    assert '"nodejs"' not in source
    assert '"npm"' not in source
    assert 'import { DatabaseSync } from "node:sqlite"' in source
    assert '"node_sqlite": node_check.returncode == 0' in source
    assert '"node_major": NODE_MAJOR' in source
    assert '"ok": check.returncode == 0 and node_check.returncode == 0' in source


def test_credential_free_smoke_matches_worker_contract_node_runtime() -> None:
    source = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert 'NODE_MAJOR = "22"' in source
    assert 'modal.Image.from_registry(f"node:{NODE_MAJOR}-bookworm-slim", add_python="3.11")' in source
    assert '"nodejs"' not in source
    assert '"npm"' not in source
    assert 'import { DatabaseSync } from "node:sqlite"' in source
    assert '"node_sqlite": node_check.returncode == 0' in source
    assert '"ok": check.returncode == 0 and node_check.returncode == 0' in source


def test_builder_and_worker_base_revision_pins_match() -> None:
    builder = load_builder()
    wrangler = (SCRIPT.parents[2] / "site" / "deploy" / "wrangler.toml").read_text(encoding="utf-8")
    match = __import__("re").search(r'^OMO_BUILDER_BASE_REVISION = "([0-9a-f]{40})"$', wrangler, __import__("re").MULTILINE)
    assert match is not None
    assert match.group(1) == builder.ALLOWED_BASE_REVISION
    assert builder.ALLOWED_BASE_REVISION == "b88b00c282472f1547099bda65b1e91df07984fa"


def test_job_identity_is_exact_and_source_scoped() -> None:
    builder = load_builder()
    submission_id = "sub_abcdefgh12345678"
    source_hash = "a" * 64
    revision = builder.ALLOWED_BASE_REVISION
    dispatch_id = builder.expected_dispatch_id(submission_id, source_hash, revision)
    builder.validate_job_identity(submission_id, "safe-skill", source_hash, dispatch_id, revision)
    assert dispatch_id.startswith("dispatch_")
    assert dispatch_id != builder.expected_dispatch_id(submission_id, "b" * 64, revision)
    assert dispatch_id != builder.expected_dispatch_id(submission_id, source_hash, "d" * 40)


def test_job_identity_rejects_mismatched_dispatch() -> None:
    builder = load_builder()
    try:
        builder.validate_job_identity("sub_abcdefgh12345678", "safe-skill", "a" * 64, "dispatch_" + "b" * 32, "c" * 40)
    except ValueError as error:
        assert str(error) == "invalid builder job identity"
    else:
        raise AssertionError("mismatched dispatch identity was accepted")


def test_job_identity_rejects_unpinned_revision() -> None:
    builder = load_builder()
    revision = "c" * 40
    dispatch_id = builder.expected_dispatch_id("sub_abcdefgh12345678", "a" * 64, revision)
    try:
        builder.validate_job_identity("sub_abcdefgh12345678", "safe-skill", "a" * 64, dispatch_id, revision)
    except ValueError as error:
        assert str(error) == "invalid builder job identity"
    else:
        raise AssertionError("unpinned builder revision was accepted")


def test_dispatch_payload_is_exact_and_identifier_only() -> None:
    builder = load_builder()
    submission_id = "sub_abcdefgh12345678"
    source_hash = "a" * 64
    revision = builder.ALLOWED_BASE_REVISION
    payload = {
        "submission_id": submission_id,
        "slug": "safe-skill",
        "source_sha256": source_hash,
        "dispatch_id": builder.expected_dispatch_id(submission_id, source_hash, revision),
    }
    assert builder.parse_dispatch_payload(payload) == (
        submission_id, "safe-skill", source_hash, payload["dispatch_id"]
    )
    for forbidden in ("content", "user_id", "profile", "model", "token", "base_revision"):
        poisoned = dict(payload, **{forbidden: "not-allowed"})
        try:
            builder.parse_dispatch_payload(poisoned)
        except ValueError as error:
            assert str(error) == "invalid builder dispatch payload"
        else:
            raise AssertionError(f"dispatch accepted forbidden field: {forbidden}")


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        *,
        status: int = 200,
        content_type: str = "application/json",
        declared_length: int | None = None,
    ) -> None:
        self._body = io.BytesIO(body)
        self.status = status
        self.headers = {"Content-Type": content_type, "X-Upstream-Secret": "must-not-forward"}
        if declared_length is not None:
            self.headers["Content-Length"] = str(declared_length)
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class BlockingResponse(FakeResponse):
    def __init__(self) -> None:
        super().__init__(b"")
        self.started = threading.Event()
        self.released = threading.Event()

    def read(self, size: int = -1) -> bytes:
        self.started.set()
        self.released.wait(timeout=10)
        return b""

    def close(self) -> None:
        self.closed = True
        self.released.set()


class PeriodicResponse(FakeResponse):
    def read(self, size: int = -1) -> bytes:
        time.sleep(0.03)
        return b"x"


class DelayedResponse(FakeResponse):
    def __init__(self, body: bytes, delay: float) -> None:
        super().__init__(body)
        self._delay = delay
        self._delayed = False

    def read(self, size: int = -1) -> bytes:
        if not self._delayed:
            self._delayed = True
            time.sleep(self._delay)
        return super().read(size)


class RecordingOpener:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.requests = []

    def open(self, request, timeout: float):
        self.requests.append((request, timeout))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class BlockingOpener:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.released = threading.Event()

    def open(self, request, timeout: float):
        self.started.set()
        self.released.wait(timeout=10)
        raise TimeoutError("blocked opener released")


def proxy_request(proxy, *, token: str, path: str = "/v1/chat/completions", body: dict | None = None, host: str = "attacker.invalid"):
    connection = http.client.HTTPConnection("127.0.0.1", proxy.port, timeout=3)
    payload = json.dumps(body or {"model": "gemini-2.5-flash", "messages": []}).encode()
    connection.request(
        "POST", path, body=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Host": host},
    )
    response = connection.getresponse()
    raw = response.read()
    headers = dict(response.getheaders())
    connection.close()
    return response.status, headers, raw


def test_hermes_environment_contains_only_ephemeral_proxy_credential(tmp_path: Path) -> None:
    builder = load_builder()
    permanent = "gemini-permanent-key-sentinel"
    local_token = "local-per-run-token"
    env = builder.hermes_environment(tmp_path, {
        "GEMINI_API_KEY": permanent,
        "BUILD_WORKER_TOKEN": "worker-secret",
        "GH_TOKEN": "github-secret",
        "TELEGRAM_BOT_TOKEN": "remove-me",
        "UNRELATED_SECRET": "remove-me-too",
    }, proxy_base_url="http://127.0.0.1:41823/v1", proxy_token=local_token)
    home = Path(env["HERMES_HOME"])
    config_text = (home / "config.yaml").read_text()
    config = json.loads(config_text)
    assert config["model"] == {
        "provider": "custom", "default": "gemini-2.5-flash",
        "base_url": "http://127.0.0.1:41823/v1", "api_key": local_token,
        "api_mode": "chat_completions",
    }
    assert config["memory"] == {"memory_enabled": False, "user_profile_enabled": False}
    assert config["gateway"]["enabled"] is False
    assert config["cron"]["enabled"] is False
    assert not (home / "auth.json").exists()
    serialized_env = json.dumps(env, sort_keys=True)
    assert permanent not in serialized_env
    assert permanent not in config_text
    assert "GEMINI_API_KEY" not in env
    assert "BUILD_WORKER_TOKEN" not in env
    assert "GH_TOKEN" not in env
    assert "TELEGRAM_BOT_TOKEN" not in env
    assert "UNRELATED_SECRET" not in env


def test_proxy_rejects_invalid_local_bearer_without_upstream_request() -> None:
    builder = load_builder()
    opener = RecordingOpener(FakeResponse(b'{"ok":true}'))
    with builder.GeminiInferenceProxy("permanent-key", "valid-local-token", opener=opener) as proxy:
        status, _headers, body = proxy_request(proxy, token="wrong-token")
    assert status == 401
    assert opener.requests == []
    assert b"wrong-token" not in body and b"permanent-key" not in body


def test_proxy_fixes_upstream_path_host_model_and_strips_headers() -> None:
    builder = load_builder()
    opener = RecordingOpener(FakeResponse(b'{"ok":true}'))
    with builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener) as proxy:
        rejected_path = proxy_request(proxy, token="local-token", path="/v1/models")
        rejected_target = proxy_request(
            proxy, token="local-token",
            body={"model": "gemini-2.5-flash", "messages": [], "base_url": "https://attacker.invalid/v1"},
        )
        rejected_model = proxy_request(proxy, token="local-token", body={"model": "other", "messages": []})
        status, headers, body = proxy_request(proxy, token="local-token", host="attacker.invalid")
    assert rejected_path[0] == 404
    assert rejected_target[0] == 400
    assert rejected_model[0] == 400
    assert status == 200 and body == b'{"ok":true}'
    assert "X-Upstream-Secret" not in headers
    assert len(opener.requests) == 1
    request, timeout = opener.requests[0]
    assert request.full_url == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert request.get_header("Authorization") == "Bearer permanent-key"
    assert request.get_header("Host") is None
    assert 0 < timeout <= builder.GEMINI_PROXY_TOTAL_TIMEOUT_SECONDS


def test_proxy_enforces_request_budget() -> None:
    builder = load_builder()
    opener = RecordingOpener(FakeResponse(b'{"ok":true}'))
    with builder.GeminiInferenceProxy(
        "permanent-key", "local-token", opener=opener, max_requests=1,
    ) as proxy:
        first = proxy_request(proxy, token="local-token")
        second = proxy_request(proxy, token="local-token")
    assert first[0] == 200
    assert second[0] == 429
    assert len(opener.requests) == 1


def test_proxy_maps_raw_upstream_errors_without_leaking_key_or_body() -> None:
    builder = load_builder()
    permanent = "permanent-key-sentinel"
    raw_error = b'provider failure permanent-key-sentinel RAW_ERROR_SENTINEL'
    error = urllib.error.HTTPError(
        builder.GEMINI_CHAT_COMPLETIONS_URL, 401, permanent, {}, io.BytesIO(raw_error)
    )
    opener = RecordingOpener(error)
    with builder.GeminiInferenceProxy(permanent, "local-token", opener=opener) as proxy:
        status, headers, body = proxy_request(proxy, token="local-token")
    assert status == 502
    assert headers["Content-Type"] == "application/json"
    assert json.loads(body)["error"]["code"] == "gemini_auth_failed"
    assert permanent.encode() not in body
    assert b"RAW_ERROR_SENTINEL" not in body


def test_proxy_rejects_success_body_that_reflects_permanent_key() -> None:
    builder = load_builder()
    permanent = "permanent-key-sentinel"
    opener = RecordingOpener(FakeResponse(b'{"debug":"permanent-key-sentinel"}'))
    with builder.GeminiInferenceProxy(permanent, "local-token", opener=opener) as proxy:
        status, _headers, body = proxy_request(proxy, token="local-token")
    assert status == 502
    assert json.loads(body)["error"]["code"] == "gemini_response_rejected"
    assert permanent.encode() not in body


def test_proxy_streams_bounded_success_response() -> None:
    builder = load_builder()
    payload = b"data: first\n\ndata: second\n\n"
    opener = RecordingOpener(FakeResponse(payload, content_type="text/event-stream"))
    with builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener) as proxy:
        status, headers, body = proxy_request(
            proxy, token="local-token",
            body={"model": "gemini-2.5-flash", "messages": [], "stream": True},
        )
    assert status == 200 and body == payload
    assert headers["Content-Type"] == "text/event-stream"
    assert headers["Content-Length"] == str(len(payload))
    assert int(headers["X-Content-Type-Options"] == "nosniff") == 1


def test_proxy_undeclared_response_overflow_is_typed_before_success(monkeypatch) -> None:
    builder = load_builder()
    monkeypatch.setattr(builder, "GEMINI_PROXY_MAX_RESPONSE_BYTES", 8)
    opener = RecordingOpener(FakeResponse(b"0123456789"))
    with builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener) as proxy:
        status, _headers, body = proxy_request(proxy, token="local-token")
    assert status == 502
    assert json.loads(body)["error"]["code"] == "gemini_response_too_large"


def test_proxy_total_deadline_stops_periodic_upstream(monkeypatch) -> None:
    builder = load_builder()
    monkeypatch.setattr(builder, "GEMINI_PROXY_TOTAL_TIMEOUT_SECONDS", 0.08)
    response = PeriodicResponse(b"")
    opener = RecordingOpener(response)
    started = time.monotonic()
    with builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener) as proxy:
        status, _headers, body = proxy_request(proxy, token="local-token")
    assert time.monotonic() - started < 1
    assert status == 504
    assert json.loads(body)["error"]["code"] == "gemini_inference_timeout"
    assert response.closed


def test_proxy_inbound_deadline_is_cancelled_before_slow_valid_inference(monkeypatch) -> None:
    builder = load_builder()
    monkeypatch.setattr(builder, "GEMINI_PROXY_INBOUND_TOTAL_TIMEOUT_SECONDS", 0.05)
    opener = RecordingOpener(DelayedResponse(b'{"ok":true}', 0.12))
    with builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener) as proxy:
        status, _headers, body = proxy_request(proxy, token="local-token")
    assert status == 200
    assert body == b'{"ok":true}'


def test_proxy_exit_closes_blocked_upstream_and_waits_for_handler() -> None:
    builder = load_builder()
    response = BlockingResponse()
    opener = RecordingOpener(response)
    proxy = builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener)
    proxy.__enter__()
    result: list[object] = []

    def request() -> None:
        try:
            result.append(proxy_request(proxy, token="local-token"))
        except Exception as error:
            result.append(type(error).__name__)

    client = threading.Thread(target=request)
    client.start()
    assert response.started.wait(timeout=2)
    started = time.monotonic()
    proxy.__exit__(None, None, None)
    client.join(timeout=2)
    assert time.monotonic() - started < 2
    assert response.closed and not client.is_alive()


def test_proxy_rejects_excessive_headers() -> None:
    builder = load_builder()
    opener = RecordingOpener(FakeResponse(b'{"ok":true}'))
    with builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener) as proxy:
        connection = http.client.HTTPConnection("127.0.0.1", proxy.port, timeout=3)
        payload = json.dumps({"model": "gemini-2.5-flash", "messages": []}).encode()
        connection.request("POST", "/v1/chat/completions", body=payload, headers={
            "Authorization": "Bearer local-token",
            "Content-Type": "application/json",
            "X-Padding": "x" * (builder.GEMINI_PROXY_MAX_HEADER_BYTES + 1),
        })
        response = connection.getresponse()
        body = response.read()
        connection.close()
    assert response.status == 431
    assert json.loads(body)["error"]["code"] == "headers_too_large"
    assert opener.requests == []


def test_proxy_total_deadline_closes_slow_header_connection(monkeypatch) -> None:
    builder = load_builder()
    monkeypatch.setattr(builder, "GEMINI_PROXY_INBOUND_TOTAL_TIMEOUT_SECONDS", 0.2)
    opener = RecordingOpener(FakeResponse(b'{"ok":true}'))
    with builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener) as proxy:
        client = socket.create_connection(("127.0.0.1", proxy.port), timeout=2)
        request = (
            b"POST /v1/chat/completions HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\nAuthorization: Bearer local-token\r\n"
            b"Content-Length: 50\r\nContent-Type: application/json\r\n\r\n"
        )
        started = time.monotonic()
        for byte in request:
            try:
                client.send(bytes([byte]))
            except OSError:
                break
            time.sleep(0.01)
        assert time.monotonic() - started < 1
        client.close()
    assert opener.requests == []


def test_proxy_shutdown_allows_bounded_local_connection_drain() -> None:
    builder = load_builder()
    proxy = builder.GeminiInferenceProxy("permanent-key", "local-token")
    proxy.__enter__()
    left, right = socket.socketpair()
    with proxy._active_lock:
        proxy._active_connections.add(left)

    def finish_connection() -> None:
        time.sleep(2)
        with proxy._active_lock:
            proxy._active_connections.discard(left)

    finisher = threading.Thread(target=finish_connection)
    finisher.start()
    started = time.monotonic()
    proxy.__exit__(None, None, None)
    finisher.join(timeout=2)
    right.close()
    assert 1.5 <= time.monotonic() - started < 5


def test_proxy_shutdown_fails_closed_when_outbound_open_cannot_cancel() -> None:
    builder = load_builder()
    opener = BlockingOpener()
    proxy = builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener)
    proxy.__enter__()

    def request() -> None:
        try:
            proxy_request(proxy, token="local-token")
        except Exception:
            pass

    client = threading.Thread(target=request, daemon=True)
    client.start()
    assert opener.started.wait(timeout=2)
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="handlers did not terminate"):
        proxy.__exit__(None, None, None)
    assert time.monotonic() - started < 6
    opener.released.set()
    client.join(timeout=2)


def test_proxy_tracks_socket_before_handler_thread_starts(monkeypatch) -> None:
    builder = load_builder()
    opener = RecordingOpener(FakeResponse(b'{"ok":true}'))
    proxy = builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener)
    proxy.__enter__()
    real_start = threading.Thread.start
    captured: list[threading.Thread] = []
    accepted = threading.Event()

    def gated_start(thread: threading.Thread) -> None:
        if "process_request_thread" in thread.name:
            captured.append(thread)
            accepted.set()
            return
        real_start(thread)

    monkeypatch.setattr(threading.Thread, "start", gated_start)
    client = socket.create_connection(("127.0.0.1", proxy.port), timeout=2)
    payload = json.dumps({"model": "gemini-2.5-flash", "messages": []}).encode()
    client.sendall(
        b"POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1\r\n"
        b"Authorization: Bearer local-token\r\nContent-Type: application/json\r\n"
        + f"Content-Length: {len(payload)}\r\n\r\n".encode()
        + payload
    )
    assert accepted.wait(timeout=2) and captured
    with pytest.raises(RuntimeError, match="handlers did not terminate"):
        proxy.__exit__(None, None, None)
    assert opener.requests == []
    client.close()
    monkeypatch.setattr(threading.Thread, "start", real_start)
    for thread in captured:
        real_start(thread)
        thread.join(timeout=2)


def test_builder_declares_single_gemini_secret_without_nous_volume() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'SECRET_NAME = "omo-hermes-builder-gemini"' in source
    assert 'required = ("GEMINI_API_KEY", "BUILD_WORKER_BASE_URL", "BUILD_WORKER_TOKEN", "GH_TOKEN")' in source
    assert "NOUS_REFRESH_SECRET_NAME" not in source
    assert "NOUS_AUTH_VOLUME_NAME" not in source
    assert "nous_auth_volume" not in source
    assert "volumes={" not in source


def test_gemini_auth_preparation_exception_is_typed() -> None:
    builder = load_builder()
    assert builder.classify_builder_exception("hermes", RuntimeError("Gemini credential is missing")) == "gemini_auth_failed"
    assert builder.classify_builder_exception("checkout", RuntimeError("anything")) == "builder_internal_failed"


def test_builder_model_is_fixed_not_environment_selected() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'model = DEFAULT_MODEL' in source
    assert 'environ.get("OMO_BUILDER_MODEL"' not in source
    assert builder_model_from_source(source) == "gemini-2.5-flash"


def builder_model_from_source(source: str) -> str:
    match = __import__("re").search(r'^DEFAULT_MODEL = "([^"]+)"$', source, __import__("re").MULTILINE)
    assert match is not None
    return match.group(1)


def test_hermes_failure_classifier_is_closed_and_never_returns_raw_text() -> None:
    builder = load_builder()
    sentinel = "SENTINEL_MUST_NOT_ESCAPE"
    cases = {
        f"gemini_auth_failed {sentinel}": "gemini_auth_failed",
        f"401 unauthorized {sentinel}": "hermes_auth_failed",
        f"model gemini-2.5-flash not found {sentinel}": "hermes_model_failed",
        f"approval required {sentinel}": "hermes_approval_failed",
        f"maximum turns reached {sentinel}": "hermes_turn_limit",
        f"permission denied {sentinel}": "hermes_permission_failed",
        f"unexpected internal output {sentinel}": "hermes_unclassified",
    }
    for raw, expected in cases.items():
        reason = builder.classify_hermes_failure(raw)
        assert reason == expected and sentinel not in reason


def test_setpriv_launcher_starts_repeatedly_while_proxy_thread_is_active(tmp_path: Path) -> None:
    builder = load_builder()
    tmp_path.chmod(0o755)
    opener = RecordingOpener(FakeResponse(b'{"ok":true}'))
    started = time.monotonic()
    with builder.GeminiInferenceProxy("permanent-key", "local-token", opener=opener):
        for _ in range(12):
            returncode, _reason = builder.run_hermes_agent(
                [sys.executable, "-c", "raise SystemExit(0)"],
                tmp_path,
                os.environ,
                timeout_seconds=2,
            )
            assert returncode == 0
    assert time.monotonic() - started < 10


def test_hermes_runner_bounds_large_stderr_and_returns_only_classification(monkeypatch, tmp_path: Path) -> None:
    builder = load_builder()
    marker = "approval required SENTINEL_MUST_NOT_ESCAPE"
    returncode, reason = builder.run_hermes_agent(
        [sys.executable, "-c", f"import sys;sys.stderr.write({marker!r}+'x'*1600000);raise SystemExit(1)"],
        tmp_path,
        os.environ,
    )
    assert returncode == 1 and reason == "hermes_approval_failed"
    assert "SENTINEL" not in reason


def test_hermes_runner_continuous_stderr_cannot_starve_timeout(monkeypatch, tmp_path: Path) -> None:
    builder = load_builder()
    started = time.monotonic()
    returncode, reason = builder.run_hermes_agent(
        [sys.executable, "-c", "import os,sys; b=b'x'*8192\nwhile True: os.write(sys.stderr.fileno(),b)"],
        tmp_path,
        os.environ,
        timeout_seconds=0.25,
    )
    assert returncode == 124 and reason == "hermes_timeout"
    assert time.monotonic() - started < 3


def test_hermes_runner_kills_descendant_after_leader_exits(monkeypatch, tmp_path: Path) -> None:
    builder = load_builder()
    tmp_path.chmod(0o777)
    pid_path = tmp_path / "child.pid"
    child_code = "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)"
    parent_code = (
        "import pathlib,subprocess,sys;"
        f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}]);"
        f"pathlib.Path('child.pid').write_text(str(p.pid))"
    )
    returncode, _reason = builder.run_hermes_agent(
        [sys.executable, "-c", parent_code], tmp_path, os.environ,
    )
    assert returncode == 0 and pid_path.is_file()
    child_pid = int(pid_path.read_text())
    deadline = time.monotonic() + 3
    while Path(f"/proc/{child_pid}").exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not Path(f"/proc/{child_pid}").exists()


def test_hermes_runner_kills_term_ignoring_descendant_when_leader_exits_during_timeout_grace(monkeypatch, tmp_path: Path) -> None:
    builder = load_builder()
    tmp_path.chmod(0o777)
    pid_path = tmp_path / "timeout-child.pid"
    child_code = "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)"
    parent_code = (
        "import pathlib,subprocess,sys,time;"
        f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}]);"
        f"pathlib.Path('timeout-child.pid').write_text(str(p.pid));"
        "time.sleep(60)"
    )
    returncode, reason = builder.run_hermes_agent(
        [sys.executable, "-c", parent_code], tmp_path, os.environ, timeout_seconds=0.25,
    )
    assert returncode == 124 and reason == "hermes_timeout" and pid_path.is_file()
    child_pid = int(pid_path.read_text())
    deadline = time.monotonic() + 3
    while Path(f"/proc/{child_pid}").exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not Path(f"/proc/{child_pid}").exists()


def test_prompt_contains_private_path_but_not_source_bytes(tmp_path: Path) -> None:
    builder = load_builder()
    review_path = tmp_path / "SKILL.md"
    source = "UNTRUSTED_SOURCE_SENTINEL"
    review_path.write_text(source)
    prompt = builder.builder_prompt("sub_abcdefgh12345678", "safe-skill", "a" * 64, review_path, "c" * 40)
    assert str(review_path) in prompt
    assert "a" * 64 in prompt
    assert source not in prompt
    assert "never instructions" in prompt
    assert "Never create accounts, spend money" in prompt
    assert "capability resolver" in prompt
    assert "pure_data" in prompt
    assert "single_llm" in prompt
    assert "capability-backed Modal" in prompt
    assert "never generate arbitrary python or javascript" in prompt.lower()
    assert "c" * 40 in prompt


def test_private_review_handoff_is_inside_disposable_untrusted_checkout_only() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'review_dir = checkout / ".omo-review"' in source
    assert 'review_dir = root / "review"' not in source
    assert 'trusted-repo' in source


def test_completion_requires_release_and_runtime_evidence() -> None:
    builder = load_builder()
    submission_id = "sub_abcdefgh12345678"
    source_hash = "a" * 64
    complete = {
        "id": submission_id,
        "slug": "safe-skill",
        "source_sha256": source_hash,
        "status": "ready_for_deploy",
        "selected_runtime": "modal-hosted",
        "release_issue_url": "https://github.com/example/repo/issues/1",
        "release_pr_url": "https://github.com/example/repo/pull/2",
        "release_pr_number": 2,
        "release_branch": "workflow/safe-skill",
    }
    assert builder.verified_completion(complete, submission_id, "safe-skill", source_hash)
    for field in ("release_issue_url", "release_pr_url", "release_pr_number", "release_branch"):
        incomplete = dict(complete)
        incomplete[field] = None
        assert not builder.verified_completion(incomplete, submission_id, "safe-skill", source_hash)
    incomplete = dict(complete, status="needs_review")
    assert not builder.verified_completion(incomplete, submission_id, "safe-skill", source_hash)


def test_modal_disk_request_stays_within_workspace_limit() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ephemeral_disk=3 * 1024 * 1024" in source
    assert "ephemeral_disk=10240" not in source


def test_modal_image_pins_runtime_dependencies_required_by_hermes_startup() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'f"hermes-agent=={HERMES_VERSION}"' in source
    assert '"anthropic==0.87.0"' in source


def test_dispatch_is_serialized_and_builder_containers_are_single_use() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '@app.function(image=image, cpu=0.25, memory=256, timeout=30, max_containers=1)' in source
    assert source.count('@modal.concurrent(max_inputs=1)') >= 2
    assert "single_use_containers=True" in source
    assert source.index('"status": "accepted"') < source.index("build_submission.spawn(")


def test_untrusted_hermes_phase_has_no_terminal_or_github_release_authority() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"--toolsets", "file,skills"' in source
    assert '"--toolsets", "terminal,file,skills"' not in source
    assert 'trusted_processor.process_row(row, repository, deploy=True' in source
    assert 'prepare_trusted_checkout(root, checkout, base_revision, slug, token)' in source
    assert source.index('trusted_processor.process_row(row, repository, deploy=True') < source.index('verified_completion(detail')
    assert '"/usr/bin/setpriv", "--reuid", str(HERMES_UID)' in source
    assert '"--clear-groups", "--no-new-privs", "--", *argv' in source
    assert "preexec_fn=" not in source
    assert '"util-linux"' in source


def test_only_regular_bounded_json_profile_crosses_trust_boundary(tmp_path: Path) -> None:
    builder = load_builder()
    source = tmp_path / "source"
    trusted = tmp_path / "trusted"
    profile = source / "packages" / "skill-to-modal" / "profiles" / "safe-skill.json"
    profile.parent.mkdir(parents=True)
    profile.write_text('{"runtime": {"kind": "worker-native"}}', encoding="utf-8")
    copied = builder.copy_reviewed_profile(source, trusted, "safe-skill")
    assert copied.read_bytes() == profile.read_bytes()
    copied.write_text('{"old": true}', encoding="utf-8")
    copied_again = builder.copy_reviewed_profile(source, trusted, "safe-skill")
    assert copied_again.read_bytes() == profile.read_bytes()
    copied.unlink()
    profile.unlink()
    profile.symlink_to(source / "outside.json")
    try:
        builder.copy_reviewed_profile(source, trusted, "safe-skill")
    except RuntimeError as error:
        assert str(error) == "reviewed profile is unsafe"
    else:
        raise AssertionError("symlinked profile crossed the trust boundary")


def test_exact_pinned_reviewed_profile_is_reused_without_authoring(tmp_path: Path) -> None:
    builder = load_builder()
    checkout = tmp_path / "repo"
    profile = checkout / "packages" / "skill-to-modal" / "profiles" / "safe-skill.json"
    profile.parent.mkdir(parents=True)
    source_sha256 = "a" * 64
    profile.write_text(
        json.dumps({
            "slug": "safe-skill",
            "reviewed_source_sha256": source_sha256,
            "execution_kind": "pure_data",
        }),
        encoding="utf-8",
    )

    assert builder.pinned_reviewed_profile(checkout, "safe-skill", source_sha256) == profile
    assert builder.pinned_reviewed_profile(checkout, "safe-skill", source_sha256.upper()) is None
    assert builder.pinned_reviewed_profile(checkout, "safe-skill", "b" * 64) is None
    source = SCRIPT.read_text(encoding="utf-8")
    selector = "if pinned_reviewed_profile(checkout, slug, source_sha256) is None:"
    assert selector in source
    assert source.index(selector) < source.index("with GeminiInferenceProxy(", source.index(selector))

    profile.unlink()
    profile.symlink_to(checkout / "outside.json")
    with pytest.raises(RuntimeError, match="pinned reviewed profile is unsafe"):
        builder.pinned_reviewed_profile(checkout, "safe-skill", source_sha256)


def test_dispatch_reservation_lease_recovers_stale_jobs() -> None:
    builder = load_builder()
    now = 10_000
    lease = builder.DISPATCH_LEASE_SECONDS
    assert builder.dispatch_is_duplicate({"status": "accepted", "started_at": now - lease + 1}, now)
    assert builder.dispatch_is_duplicate({"status": "running", "started_at": now - lease + 1}, now)
    assert not builder.dispatch_is_duplicate({"status": "accepted", "started_at": now - lease}, now)
    assert not builder.dispatch_is_duplicate({"status": "running", "started_at": now - lease - 1}, now)
    assert builder.dispatch_is_duplicate({"status": "completed", "started_at": 0}, now)
    assert not builder.dispatch_is_duplicate({"status": "failed", "started_at": now}, now)
    assert not builder.dispatch_is_duplicate({"status": "spawn_failed", "started_at": now}, now)
    assert not builder.dispatch_is_duplicate(None, now)


def test_safe_failure_stage_is_allowlisted() -> None:
    builder = load_builder()
    safe = builder._safe_result("failed", "dispatch_" + "a" * 32, "sub_abcdefgh12345678", stage="claim")
    release_safe = builder._safe_result(
        "failed", "dispatch_" + "a" * 32, "sub_abcdefgh12345678", stage="release_issue_lookup"
    )
    unsafe = builder._safe_result("failed", "dispatch_" + "a" * 32, "sub_abcdefgh12345678", stage="secret-value")
    assert safe["stage"] == "claim"
    assert release_safe["stage"] == "release_issue_lookup"
    assert "stage" not in unsafe


def test_processor_loader_resolves_siblings_and_restores_sys_path(tmp_path: Path) -> None:
    builder = load_builder()
    host_skill = tmp_path / "tools" / "host-skill"
    host_skill.mkdir(parents=True)
    (host_skill / "submission_queue.py").write_text("MARKER = 'sibling-loaded'\n", encoding="utf-8")
    processor_path = host_skill / "process-submissions.py"
    processor_path.write_text("from submission_queue import MARKER\n", encoding="utf-8")
    before = list(sys.path)
    previous_sibling = sys.modules.pop("submission_queue", None)
    try:
        module = builder.load_processor_module(processor_path)
        assert module.MARKER == "sibling-loaded"
        assert sys.path == before
    finally:
        sys.modules.pop("submission_queue", None)
        if previous_sibling is not None:
            sys.modules["submission_queue"] = previous_sibling


def test_sequential_processor_loads_keep_checkout_roots_isolated(tmp_path: Path) -> None:
    builder = load_builder()
    before = list(sys.path)
    previous_sibling = sys.modules.get("submission_queue")
    loaded = []
    for marker in ("authoring-root", "trusted-root"):
        host_skill = tmp_path / marker / "tools" / "host-skill"
        host_skill.mkdir(parents=True)
        (host_skill / "submission_queue.py").write_text(f"ROOT = {marker!r}\n", encoding="utf-8")
        processor_path = host_skill / "process-submissions.py"
        processor_path.write_text("from submission_queue import ROOT\n", encoding="utf-8")
        loaded.append(builder.load_processor_module(processor_path))
    assert loaded[0].ROOT == "authoring-root"
    assert loaded[1].ROOT == "trusted-root"
    assert sys.path == before
    assert sys.modules.get("submission_queue") is previous_sibling
