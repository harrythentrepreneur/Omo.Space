"""Credential-free smoke entrypoint for the exact Omo Hermes builder image."""
from __future__ import annotations

import modal

HERMES_VERSION = "0.18.2"
MODAL_VERSION = "1.3.4"
NODE_MAJOR = "22"
DEFAULT_MODEL = "gemini-2.5-flash"

smoke_app = modal.App("omo-hermes-builder-smoke")
image = (
    modal.Image.from_registry(f"node:{NODE_MAJOR}-bookworm-slim", add_python="3.11")
    .env({"DEBIAN_FRONTEND": "noninteractive", "TZ": "UTC"})
    .apt_install("ca-certificates", "curl", "git")
    .pip_install(f"hermes-agent=={HERMES_VERSION}", f"modal=={MODAL_VERSION}")
)


@smoke_app.function(image=image, cpu=1.0, memory=1024, timeout=180)
def smoke() -> dict[str, object]:
    import subprocess
    import time

    started = time.monotonic()
    check = subprocess.run(["hermes", "--version"], text=True, capture_output=True, timeout=60, check=False)
    node_check = subprocess.run(
        [
            "node", "--input-type=module", "--eval",
            'import { DatabaseSync } from "node:sqlite"; new DatabaseSync(":memory:").close();',
        ],
        text=True, capture_output=True, timeout=60, check=False,
    )
    return {
        "ok": check.returncode == 0 and node_check.returncode == 0,
        "returncode": check.returncode,
        "hermes_version": HERMES_VERSION,
        "node_major": NODE_MAJOR,
        "node_sqlite": node_check.returncode == 0,
        "provider": "gemini",
        "model": DEFAULT_MODEL,
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


@smoke_app.local_entrypoint()
def main() -> None:
    import json

    print(json.dumps(smoke.remote(), sort_keys=True))
