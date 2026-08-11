#!/usr/bin/env python3
"""Deterministically hash the de Mello release tree without self-reference."""

from __future__ import annotations

import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache"}


def normalize_json(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if key == "release_hash":
                normalized[key] = "sha256:PENDING-DETERMINISTIC-COMPILER"
            elif key == "release_hash_short":
                normalized[key] = "PENDING-DETERMINISTIC-COMPILER"
            else:
                normalized[key] = normalize_json(item)
        return normalized
    if isinstance(value, list):
        return [normalize_json(item) for item in value]
    return value


def normalized_bytes(path: Path) -> bytes:
    value = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if path.suffix == ".json":
        parsed = normalize_json(json.loads(value))
        value = json.dumps(
            parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8") + b"\n"
    return value


def release_hash() -> str:
    digest = hashlib.sha256()
    for candidate in ROOT.rglob("*"):
        if candidate.is_symlink():
            raise RuntimeError(
                f"release tree contains a symlink: {candidate.relative_to(ROOT)}"
            )
    paths = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts)
        and path.suffix not in {".pyc", ".pyo"}
    )
    for path in paths:
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        body = normalized_bytes(path)
        digest.update(struct.pack(">Q", len(relative)))
        digest.update(relative)
        digest.update(struct.pack(">Q", len(body)))
        digest.update(body)
    return digest.hexdigest()


if __name__ == "__main__":
    os.write(1, (release_hash() + "\n").encode("ascii"))
