"""Fail-closed Omo container shell for the source-compatible PhonicsMaker book engine.

The source engine binding is intentionally not enabled in this first slice. The
container cannot produce a mock book; it returns PHONICSMAKER_ENGINE_NOT_BOUND
until the private artifact/provider boundary is implemented and reviewed.
"""

from pathlib import Path

import modal

from book_adapter import create_book_app

ROOT = Path(__file__).resolve().parent
app = modal.App("cognition-phonicsmaker-core")

runtime_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("fastapi==0.109.0", "jsonschema==4.26.0", "modal==1.5.0")
    .add_local_file(ROOT / "book_adapter.py", "/root/phonicsmaker/book_adapter.py", copy=True)
    .add_local_dir(ROOT / "schemas", "/root/phonicsmaker/schemas", copy=True)
)


@app.function(image=runtime_image, min_containers=0, max_containers=20, scaledown_window=5)
@modal.concurrent(max_inputs=20)
@modal.asgi_app(requires_proxy_auth=True)
def api():
    return create_book_app()
