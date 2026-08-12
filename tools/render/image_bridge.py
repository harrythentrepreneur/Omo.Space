"""Optional bridge to the existing ChatGPT-subscription image adapter.

Secrets are supplied by the owning host and are never logged. The bridge uses
the adapter's explicit no-refresh mode.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_PATH = ROOT / "containers" / "demello-awake" / "image_gen.py"


def codex_subscription_adapter(*, access_token: str, account_id: str, request: Any = None) -> Any:
    """Construct the existing adapter without allowing refresh-token fallback."""
    if not access_token or not account_id:
        raise ValueError("access_token and account_id are required")
    spec = importlib.util.spec_from_file_location("omo_demello_image_gen", ADAPTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load CodexSubscriptionImageAdapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module.CodexSubscriptionImageAdapter(
        access_token=access_token,
        account_id=account_id,
        allow_refresh=False,
        request=request,
        size="1024x1536",
        quality="medium",
    )


def populate_missing_story_images(
    manifest: Mapping[str, Any], output_dir: Path, *, adapter: Any | None
) -> tuple[dict[str, Any], list[str]]:
    """Generate missing page images, or preserve a disclosed text-only fallback."""
    updated = {key: value for key, value in manifest.items()}
    updated["pages"] = [dict(page) for page in manifest.get("pages", [])]
    warnings: list[str] = []
    if adapter is None:
        warnings.append("CodexSubscriptionImageAdapter unavailable; rendered text-only")
        return updated, warnings
    output_dir.mkdir(parents=True, exist_ok=True)
    prior: bytes | None = None
    for page in updated["pages"]:
        if page.get("image_path"):
            prior = Path(str(page["image_path"])).read_bytes()
            continue
        prompt = str(page.get("image_prompt") or "").strip()
        if not prompt:
            warnings.append(f"page {page.get('page_number')} has no image prompt; rendered text-only")
            continue
        image_bytes, _usage = adapter.generate(
            "Child-safe, original, text-free storybook illustration. " + prompt,
            parent=prior,
        )
        path = output_dir / f"page-{int(page['page_number']):02d}.png"
        path.write_bytes(image_bytes)
        page["image_path"] = str(path)
        prior = image_bytes
    return updated, warnings
