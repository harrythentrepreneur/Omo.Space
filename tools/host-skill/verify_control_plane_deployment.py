#!/usr/bin/env python3
"""Fail-closed attestation for one exact Cloudflare Worker deploy."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_VERSION_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
_SHA_RE = re.compile(r"[0-9a-f]{40}")
_SELECTOR_RE = re.compile(r"[0-9a-f]{40}")
_RECEIPT_RE = re.compile(r"^Current Version ID: ([0-9a-f-]+)$", re.MULTILINE)


def _valid_version_id(value: object) -> bool:
    return isinstance(value, str) and _VERSION_RE.fullmatch(value) is not None


def verify_deployment(
    *, deploy_log: str, deployment: object, version: object,
    expected_sha: str, expected_selector: str,
) -> dict[str, Any]:
    if not _SHA_RE.fullmatch(expected_sha) or not _SELECTOR_RE.fullmatch(expected_selector):
        raise ValueError("invalid expected identity")
    receipts = _RECEIPT_RE.findall(deploy_log)
    if len(receipts) != 1 or not _valid_version_id(receipts[0]):
        raise ValueError("invalid deploy receipt")
    receipt = receipts[0]

    if not isinstance(deployment, dict):
        raise ValueError("invalid deployment status")
    allocations = deployment.get("versions")
    if not isinstance(allocations, list) or len(allocations) != 1:
        raise ValueError("deployment is not a single-version allocation")
    allocation = allocations[0]
    if not isinstance(allocation, dict):
        raise ValueError("invalid allocation")
    percentage = allocation.get("percentage")
    if isinstance(percentage, bool) or not isinstance(percentage, (int, float)) or percentage != 100:
        raise ValueError("deployment is not allocated at 100 percent")
    if allocation.get("version_id") != receipt:
        raise ValueError("active version does not match deploy receipt")

    if not isinstance(version, dict) or version.get("id") != receipt:
        raise ValueError("version readback does not match deploy receipt")
    annotations = version.get("annotations")
    if not isinstance(annotations, dict) or annotations.get("workers/message") != f"omo-control-plane:{expected_sha}":
        raise ValueError("version annotation does not match source revision")
    resources = version.get("resources")
    bindings = resources.get("bindings") if isinstance(resources, dict) else None
    if not isinstance(bindings, list):
        raise ValueError("version bindings are missing")
    matches = [item for item in bindings if isinstance(item, dict) and item.get("name") == "OMO_BUILDER_BASE_REVISION"]
    if len(matches) != 1 or matches[0].get("type") != "plain_text" or matches[0].get("text") != expected_selector:
        raise ValueError("live Worker selector does not match reviewed revision")
    return {"allocation": 100, "selector": "verified", "version_id": receipt}


def _json_file(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy-log", type=Path, required=True)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--version", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-selector", required=True)
    args = parser.parse_args()
    result = verify_deployment(
        deploy_log=args.deploy_log.read_text(encoding="utf-8"),
        deployment=_json_file(args.deployment),
        version=_json_file(args.version),
        expected_sha=args.expected_sha,
        expected_selector=args.expected_selector,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
