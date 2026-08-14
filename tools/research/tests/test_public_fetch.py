from __future__ import annotations

import contextlib
import hashlib
import http.server
import threading
import time

import pytest

from tools.research.public_fetch import PublicFetchError, fetch_public_url, search_snippets


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/robots.txt":
            self._send(200, b"User-agent: *\nDisallow: /private\n")
        elif self.path == "/page":
            self._send(200, "caf\u00e9 public evidence".encode(), "text/plain; charset=utf-8")
        elif self.path == "/private":
            self._send(200, b"must not be fetched")
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/page")
            self.end_headers()
        elif self.path.startswith("/loop/"):
            index = int(self.path.rsplit("/", 1)[1])
            self.send_response(302)
            self.send_header("Location", f"/loop/{index + 1}")
            self.end_headers()
        elif self.path == "/large":
            self._send(200, b"x" * (256 * 1024 + 1))
        elif self.path == "/missing":
            self._send(404, b"missing")
        elif self.path == "/slow":
            time.sleep(0.2)
            self._send(200, b"late")
        else:
            self._send(404, b"unknown")

    def _send(self, status: int, body: bytes, content_type: str = "text/plain") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        with contextlib.suppress(BrokenPipeError):
            self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def server_url():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


def fetch_local(server_url: str, path: str, **kwargs):
    return fetch_public_url(
        server_url + path,
        allowed_hosts={"127.0.0.1"},
        allow_http=True,
        **kwargs,
    )


def test_fetch_returns_exact_contract_and_preview(server_url: str) -> None:
    result = fetch_local(server_url, "/page", preview_chars=4)
    body = "caf\u00e9 public evidence".encode()
    assert result == {
        "url": server_url + "/page",
        "status": 200,
        "final_url": server_url + "/page",
        "content_type": "text/plain",
        "text_preview": "caf\u00e9",
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def test_robots_denial_is_typed(server_url: str) -> None:
    with pytest.raises(PublicFetchError) as caught:
        fetch_local(server_url, "/private")
    assert caught.value.code == "ROBOTS_DENIED"


def test_one_redirect_is_followed(server_url: str) -> None:
    result = fetch_local(server_url, "/redirect")
    assert result["status"] == 200
    assert result["final_url"] == server_url + "/page"


def test_more_than_three_redirects_is_http_error(server_url: str) -> None:
    with pytest.raises(PublicFetchError) as caught:
        fetch_local(server_url, "/loop/0")
    assert caught.value.code == "HTTP_ERROR"


def test_oversize_body_is_typed(server_url: str) -> None:
    with pytest.raises(PublicFetchError) as caught:
        fetch_local(server_url, "/large")
    assert caught.value.code == "TOO_LARGE"


def test_http_failure_and_timeout_are_typed(server_url: str) -> None:
    with pytest.raises(PublicFetchError) as caught:
        fetch_local(server_url, "/missing")
    assert caught.value.code == "HTTP_ERROR"
    with pytest.raises(PublicFetchError) as caught:
        fetch_local(server_url, "/slow", timeout=0.03)
    assert caught.value.code == "FETCH_TIMEOUT"


def test_https_default_and_search_partial_fail_closed(server_url: str) -> None:
    with pytest.raises(PublicFetchError) as caught:
        fetch_public_url(server_url + "/page")
    assert caught.value.code == "HTTP_ERROR"
    with pytest.raises(PublicFetchError) as caught:
        search_snippets("bounded public research")
    assert caught.value.code == "SEARCH_UNAVAILABLE"
