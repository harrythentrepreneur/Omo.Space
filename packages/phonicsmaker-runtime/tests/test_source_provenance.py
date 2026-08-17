import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "packages/phonicsmaker-runtime"
MANIFEST = BUNDLE / "SOURCE-PROVENANCE.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_source_bundle_has_provenance_and_exact_file_hashes():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_repo"] == "/root/work/phonicsmaker/core"
    source_root = Path(manifest["source_repo"])
    current_commit = subprocess.check_output(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True
    ).strip()
    assert current_commit == manifest["source_commit"]
    assert len(manifest["files"]) >= 1
    assert manifest["source_commit"]

    for entry in manifest["files"]:
        relative = Path(entry["path"])
        assert not any(part in {".env", "draft_data", "logs", "__pycache__"} for part in relative.parts)
        copied = BUNDLE / "source/core" / relative
        source = source_root / relative
        assert source.is_file(), relative
        assert copied.is_file(), relative
        assert copied.stat().st_size == entry["bytes"], relative
        assert _sha256(source) == entry["sha256"], relative
        assert _sha256(copied) == entry["sha256"], relative


def test_source_bundle_does_not_contain_secret_or_customer_dump_paths():
    paths = [entry["path"] for entry in json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]]

    assert all(not path.startswith(".env") for path in paths)
    assert all("draft_data" not in path for path in paths)
    assert all("logs" not in path for path in paths)
