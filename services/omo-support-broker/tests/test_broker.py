import hashlib
import hmac
import importlib.util
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

MODULE_PATH = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("omo_support_broker", MODULE_PATH)
assert spec and spec.loader
broker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(broker)


def signed_headers(secret: str, body: bytes, timestamp: int, nonce: str) -> dict[str, str]:
    signature = hmac.new(secret.encode(), f"{timestamp}\n{nonce}\n".encode() + body, hashlib.sha256).hexdigest()
    return {"X-Omo-Timestamp": str(timestamp), "X-Omo-Nonce": nonce, "X-Omo-Signature": signature}


def setup_function():
    os.environ["OMO_SUPPORT_SHARED_SECRET"] = "test-shared-secret"
    os.environ["API_SERVER_KEY"] = "test-api-key"


def test_valid_signature_and_durable_replay_rejection(tmp_path, monkeypatch):
    monkeypatch.setattr(broker, "STATE_DB", tmp_path / "state.db")
    now = int(time.time())
    body = json.dumps({"message": "hello"}).encode()
    headers = signed_headers("test-shared-secret", body, now, "nonce_1234567890123456")
    assert broker.verify_request(headers, body, now=now)
    assert not broker.verify_request(headers, body, now=now)
    # A separate connection/process sees the same durable nonce claim.
    assert not broker.claim_nonce("nonce_1234567890123456", now)


def test_rejects_stale_and_modified_requests(tmp_path, monkeypatch):
    monkeypatch.setattr(broker, "STATE_DB", tmp_path / "state.db")
    now = int(time.time())
    body = b'{"message":"hello"}'
    stale = signed_headers("test-shared-secret", body, now - broker.CLOCK_SKEW - 1, "nonce_abcdefghijklmnop")
    assert not broker.verify_request(stale, body, now=now)
    fresh = signed_headers("test-shared-secret", body, now, "nonce_qrstuvwxyz123456")
    assert not broker.verify_request(fresh, body + b" ", now=now)


def test_session_identity_is_policy_and_support_scoped():
    first = broker.derive_hermes_session("user_alpha", "session_12345678")
    again = broker.derive_hermes_session("user_alpha", "session_12345678")
    other = broker.derive_hermes_session("user_beta", "session_12345678")
    assert first == again
    assert first != other
    assert first.startswith("omo_support_safe_")
    assert len(first) == len("omo_support_safe_") + 32


def test_profile_is_hard_pinned_and_outbound_request_has_no_tool_selection(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, limit):
            return json.dumps({"choices": [{"message": {"content": "Safe explanation"}}]}).encode()

    def fake_open(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(broker.urllib.request, "urlopen", fake_open)
    result = broker.call_hermes("user_alpha", "session_12345678", "diagnose this")
    request = captured["request"]
    outbound = json.loads(request.data)
    assert request.full_url.endswith("/p/omo-support/v1/chat/completions")
    assert request.headers["X-hermes-session-key"].startswith("omo-support:support-safe-v2:support:")
    assert "tools" not in outbound and "profile" not in outbound
    assert result == {
        "message": "Safe explanation",
        "session_id": "session_12345678",
        "profile": "omo-support",
        "mode": "support",
        "policy": "support-safe-v2",
    }
    assert captured["timeout"] == 90


def test_source_rejects_maintainer_and_action_payloads():
    source = MODULE_PATH.read_text()
    assert 'PROFILE = "omo-support"' in source
    assert 'payload.get("maintainer") is not None' in source
    assert 'payload.get("action") is not None' in source
    assert '"support_actions_disabled"' in source
    assert "import subprocess" not in source
    assert "GH_TOKEN" not in source
    assert "gh " not in source
