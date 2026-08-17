import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "containers/phonicsmaker-book-engine/runtime_spec.py"
spec = importlib.util.spec_from_file_location("phonicsmaker_runtime_spec", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_runtime_spec_uses_the_preserved_source_lockfiles():
    assert module.SOURCE_ROOT.is_dir()
    assert (module.SOURCE_ROOT / "pyproject.toml").is_file()
    assert (module.SOURCE_ROOT / "poetry.lock").is_file()
    assert module.lock_sha256() == "ded39b829e9aac0f5c7dc170b99c0669e34014ecbdd10b6d5f5e386ae5244dea"
    assert module.pyproject_sha256() == "c94c0050425c595c5d25db84c10ea2415a526a121804bced5feccdfc1c256ca6"


def test_runtime_spec_contains_rendering_and_cv_system_dependencies():
    required = {
        "build-essential", "ffmpeg", "libpq-dev", "libpango-1.0-0",
        "libpangocairo-1.0-0", "libpangoft2-1.0-0", "libcairo2",
        "libcairo2-dev", "libgdk-pixbuf-2.0-0", "libffi-dev", "libglib2.0-0",
        "libgl1", "libglib2.0-dev", "shared-mime-info", "fonts-dejavu-core",
    }
    assert required <= set(module.SYSTEM_PACKAGES)


def test_runtime_spec_install_plan_is_locked_and_secret_safe():
    plan = module.install_plan()
    joined = "\n".join(plan)
    assert "poetry install --no-interaction --no-ansi --only main" in joined
    assert "poetry.lock" in joined
    assert ".env" not in joined
    assert "GEMINI_API_KEY" not in joined
    assert "RUNWARE_API_KEY" not in joined
    assert module.RUNTIME_PYTHON == "3.12"


def test_runtime_provenance_matches_the_source_bundle_manifest():
    manifest = json.loads((ROOT / "packages/phonicsmaker-runtime/SOURCE-PROVENANCE.json").read_text())
    by_path = {entry["path"]: entry for entry in manifest["files"]}
    assert by_path["poetry.lock"]["sha256"] == module.lock_sha256()
    assert by_path["pyproject.toml"]["sha256"] == module.pyproject_sha256()
