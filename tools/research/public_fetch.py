#!/usr/bin/env python3
"""Bounded, credential-free fetching of public web pages.

Version 1 intentionally supports direct URL fetches only.  There is no stable,
general-purpose public search endpoint that needs neither credentials nor a
provider agreement, so ``search_snippets`` fails closed instead of scraping a
search engine.
"""

from __future__ import annotations

import hashlib
import socket
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from typing import Any


DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_BYTES = 256 * 1024
MAX_REDIRECTS = 3
USER_AGENT = "OmoPublicFetch/1.0"
DENIED_HOSTS = frozenset({
    "metadata.google.internal",
    "metadata.azure.internal",
    "instance-data.ec2.internal",
})


class PublicFetchError(RuntimeError):
    """A bounded fetch failed with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class _RedirectLimit(urllib.error.HTTPError):
    pass


@dataclass(frozen=True)
class _Policy:
    allowed_hosts: frozenset[str] | None
    allow_http: bool

    def validate(self, url: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme != "https" and not (self.allow_http and scheme == "http"):
            raise PublicFetchError("HTTP_ERROR", "only HTTPS URLs are allowed")
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host or parsed.username is not None or parsed.password is not None:
            raise PublicFetchError("HTTP_ERROR", "URL must contain a public host and no credentials")
        if host in DENIED_HOSTS or host.endswith(".internal"):
            raise PublicFetchError("HTTP_ERROR", "host is denied by fetch policy")
        if self.allowed_hosts is not None and host not in self.allowed_hosts:
            raise PublicFetchError("HTTP_ERROR", "host is not in the configured allowlist")


class _BoundedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, policy: _Policy, maximum: int) -> None:
        self.policy = policy
        self.maximum = maximum
        self.count = 0

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str):
        self.count += 1
        if self.count > self.maximum:
            raise _RedirectLimit(newurl, code, "redirect limit exceeded", headers, fp)
        self.policy.validate(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener(policy: _Policy) -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_BoundedRedirectHandler(policy, MAX_REDIRECTS))


def _read_bounded(response: Any, maximum: int = MAX_BYTES) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            if int(content_length) > maximum:
                raise PublicFetchError("TOO_LARGE", f"response exceeds {maximum} bytes")
        except ValueError:
            pass
    body = response.read(maximum + 1)
    if len(body) > maximum:
        raise PublicFetchError("TOO_LARGE", f"response exceeds {maximum} bytes")
    return body


def _request(opener: urllib.request.OpenerDirector, url: str, timeout: float) -> tuple[Any, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        response = opener.open(request, timeout=timeout)
        return response, _read_bounded(response)
    except PublicFetchError:
        raise
    except (TimeoutError, socket.timeout) as exc:
        raise PublicFetchError("FETCH_TIMEOUT", f"fetch timed out after {timeout:g}s") from exc
    except urllib.error.HTTPError as exc:
        raise PublicFetchError("HTTP_ERROR", f"HTTP request failed with status {exc.code}") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise PublicFetchError("FETCH_TIMEOUT", f"fetch timed out after {timeout:g}s") from exc
        raise PublicFetchError("HTTP_ERROR", f"HTTP request failed: {exc.reason}") from exc


def _robots_allowed(policy: _Policy, url: str, timeout: float) -> bool:
    opener = _opener(policy)
    parsed = urllib.parse.urlsplit(url)
    robots_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
    request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        response = opener.open(request, timeout=timeout)
        body = _read_bounded(response)
    except urllib.error.HTTPError as exc:
        # RFC 9309: 4xx means the robots file is unavailable, so crawling is allowed.
        if 400 <= exc.code < 500:
            return True
        raise PublicFetchError("HTTP_ERROR", f"robots.txt failed with status {exc.code}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise PublicFetchError("FETCH_TIMEOUT", f"robots.txt timed out after {timeout:g}s") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise PublicFetchError("FETCH_TIMEOUT", f"robots.txt timed out after {timeout:g}s") from exc
        # An unavailable robots file does not invent a deny rule.
        return True
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(body.decode("utf-8", errors="replace").splitlines())
    return parser.can_fetch(USER_AGENT, url)


def fetch_public_url(
    url: str,
    *,
    preview_chars: int = 4000,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    allowed_hosts: set[str] | frozenset[str] | None = None,
    allow_http: bool = False,
) -> dict[str, Any]:
    """Fetch one public URL and return bounded content evidence.

    ``allow_http`` exists for controlled local/test deployments; production
    callers should retain the HTTPS-only default.  ``timeout`` may be shortened
    but never raised above ten seconds.
    """

    if not isinstance(url, str) or not url:
        raise PublicFetchError("HTTP_ERROR", "url must be a non-empty string")
    if isinstance(preview_chars, bool) or not isinstance(preview_chars, int) or not 0 <= preview_chars <= 100_000:
        raise ValueError("preview_chars must be an integer from 0 to 100000")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 10:
        raise ValueError("timeout must be greater than zero and at most 10 seconds")
    normalized_hosts = None if allowed_hosts is None else frozenset(h.lower().rstrip(".") for h in allowed_hosts)
    policy = _Policy(normalized_hosts, allow_http)
    policy.validate(url)
    if not _robots_allowed(policy, url, float(timeout)):
        raise PublicFetchError("ROBOTS_DENIED", "robots.txt disallows this URL")
    opener = _opener(policy)
    response, body = _request(opener, url, float(timeout))
    final_url = response.geturl()
    policy.validate(final_url)
    content_type = response.headers.get_content_type() or "application/octet-stream"
    charset = response.headers.get_content_charset() or "utf-8"
    try:
        text = body.decode(charset, errors="replace")
    except LookupError:
        text = body.decode("utf-8", errors="replace")
    return {
        "url": url,
        "status": response.getcode(),
        "final_url": final_url,
        "content_type": content_type,
        "text_preview": text[:preview_chars],
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def search_snippets(query: str) -> list[dict[str, str]]:
    """Fail closed: v1 has no honest credential-free public search backend."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    raise PublicFetchError(
        "SEARCH_UNAVAILABLE",
        "v1 supports direct-URL fetch only; no credential-free public search endpoint is configured",
    )


__all__ = ["PublicFetchError", "fetch_public_url", "search_snippets"]
