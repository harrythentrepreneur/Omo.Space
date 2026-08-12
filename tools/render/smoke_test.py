#!/usr/bin/env python3
"""Write and validate one real smoke-test PDF under /tmp."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.render.runtime import render_manifest  # noqa: E402


def main() -> int:
    manifest_path = ROOT / "tools" / "render" / "samples" / "smoke-worksheet.json"
    output_dir = Path("/tmp/omo-artifact-render-smoke")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = render_manifest(manifest, output_dir, run_id="smoke-render-001")
    pdf_path = output_dir / "smoke-worksheet.pdf"
    if not pdf_path.is_file() or pdf_path.stat().st_size <= 0:
        raise AssertionError("smoke PDF is missing or empty")
    page_count = len(PdfReader(str(pdf_path)).pages)
    if page_count != 1:
        raise AssertionError(f"expected 1 page, got {page_count}")
    print(json.dumps({
        "status": "passed",
        "pdf": str(pdf_path),
        "bytes": pdf_path.stat().st_size,
        "page_count": page_count,
        "sha256": result.artifacts[0].sha256,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
