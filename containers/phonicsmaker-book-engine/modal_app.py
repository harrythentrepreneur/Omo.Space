"""Fail-closed Omo container shell for the source-compatible PhonicsMaker book engine."""

from pathlib import Path

import modal

from book_adapter import create_book_app
from runtime_spec import RUNTIME_PYTHON, SOURCE_ROOT, install_plan

ROOT = Path(__file__).resolve().parent
app = modal.App("cognition-phonicsmaker-core")

runtime_image = (
    modal.Image.debian_slim(python_version=RUNTIME_PYTHON)
    .add_local_file(SOURCE_ROOT / "pyproject.toml", "/opt/phonicsmaker/pyproject.toml", copy=True)
    .add_local_file(SOURCE_ROOT / "poetry.lock", "/opt/phonicsmaker/poetry.lock", copy=True)
)
for command in install_plan():
    runtime_image = runtime_image.run_commands(command)
runtime_image = (
    runtime_image
    .add_local_dir(SOURCE_ROOT, "/opt/phonicsmaker", copy=True)
    .add_local_file(ROOT / "book_adapter.py", "/opt/omo/book_adapter.py", copy=True)
    .add_local_file(ROOT / "engine_binding.py", "/opt/omo/engine_binding.py", copy=True)
    .add_local_dir(ROOT / "schemas", "/opt/omo/schemas", copy=True)
)


@app.function(image=runtime_image, min_containers=0, max_containers=20, scaledown_window=5)
@modal.concurrent(max_inputs=20)
@modal.asgi_app(requires_proxy_auth=True)
def api():
    return create_book_app()
