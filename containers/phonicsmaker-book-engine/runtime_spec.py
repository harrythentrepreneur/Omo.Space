"""Pinned, secret-free build inputs for the PhonicsMaker Omo runtime."""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "packages/phonicsmaker-runtime/source/core"
RUNTIME_PYTHON = "3.12"
POETRY_VERSION = "2.1.3"

SYSTEM_PACKAGES = (
    "gcc",
    "ffmpeg",
    "curl",
    "build-essential",
    "libpq-dev",
    "libpango-1.0-0",
    "libpangocairo-1.0-0",
    "libpangoft2-1.0-0",
    "libcairo2",
    "libcairo2-dev",
    "libgdk-pixbuf-2.0-0",
    "libffi-dev",
    "libglib2.0-0",
    "libgl1",
    "libglib2.0-dev",
    "shared-mime-info",
    "fonts-dejavu-core",
    "fontconfig",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lock_sha256() -> str:
    return _sha256(SOURCE_ROOT / "poetry.lock")


def pyproject_sha256() -> str:
    return _sha256(SOURCE_ROOT / "pyproject.toml")


def install_plan() -> tuple[str, ...]:
    packages = " ".join(SYSTEM_PACKAGES)
    return (
        "apt-get update && apt-get install -y --no-install-recommends " + packages + " && rm -rf /var/lib/apt/lists/*",
        f"python -m pip install --no-cache-dir poetry=={POETRY_VERSION}",
        "test -f /opt/phonicsmaker/pyproject.toml && test -f /opt/phonicsmaker/poetry.lock",
        "cd /opt/phonicsmaker && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --only main",
    )
