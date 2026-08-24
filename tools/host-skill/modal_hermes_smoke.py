"""Credential-free smoke entrypoint for the exact Omo Hermes builder image."""
from __future__ import annotations

import modal

HERMES_VERSION = "0.18.2"
MODAL_VERSION = "1.3.4"
DEFAULT_MODEL = "deepseek-v4-pro"

smoke_app = modal.App("omo-hermes-builder-smoke")
image = (
    modal.Image.debian_slim(python_version="3.11")
    .env({"DEBIAN_FRONTEND": "noninteractive", "TZ": "UTC"})
    .apt_install("ca-certificates", "curl", "git", "nodejs", "npm")
    .pip_install(f"hermes-agent=={HERMES_VERSION}", f"modal=={MODAL_VERSION}")
)


@smoke_app.function(image=image, cpu=1.0, memory=1024, timeout=180)
def smoke() -> dict[str, object]:
    import subprocess
    import time

    started = time.monotonic()
    check = subprocess.run(["hermes", "--version"], text=True, capture_output=True, timeout=60, check=False)
    return {
        "ok": check.returncode == 0,
        "returncode": check.returncode,
        "hermes_version": HERMES_VERSION,
        "provider": "opencode-go",
        "model": DEFAULT_MODEL,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


@smoke_app.local_entrypoint()
def main() -> None:
    import json

    print(json.dumps(smoke.remote(), sort_keys=True))
