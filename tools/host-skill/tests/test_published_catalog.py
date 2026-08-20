import importlib.util
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "site" / "catalog.js"
REGISTRY = ROOT / "site" / "deploy" / "hosted-skills.generated.mjs"
SITEMAP = ROOT / "site" / "sitemap.xml"


def published_state() -> dict:
    script = """
import fs from 'node:fs';
import vm from 'node:vm';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync('site/catalog.js', 'utf8'), context, { filename: 'catalog.js' });
const registry = await import(pathToFileURL(path.resolve('site/deploy/hosted-skills.generated.mjs')).href);
process.stdout.write(JSON.stringify({
  catalog: context.window.OMO_CATALOG,
  visible: context.window.OMO_VISIBLE_SLUGS,
  runtimeSlugs: [
    ...registry.HOSTED_WORKER_SKILL_ROWS.map((row) => row[0]),
    ...registry.HOSTED_MODAL_SKILL_ROWS.map((row) => row[0]),
  ],
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def catalog_managed_runtime_slugs() -> set[str]:
    slugs: set[str] = set()
    for path in sorted((ROOT / "containers").glob("*/hosted-profile.json")):
        hosted = json.loads(path.read_text(encoding="utf-8"))
        if hosted.get("catalog_managed", True):
            slugs.add(hosted["runtime"]["slug"])
    return slugs


def test_generated_runtime_registry_matches_all_hosted_profiles() -> None:
    spec = importlib.util.spec_from_file_location("host_skill", ROOT / "tools" / "host-skill" / "host.py")
    assert spec is not None and spec.loader is not None
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    profiles = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((ROOT / "containers").glob("*/hosted-profile.json"))
    ]

    assert REGISTRY.read_text(encoding="utf-8") == host.render_registry(profiles)


def test_every_catalog_managed_runtime_has_complete_public_surface() -> None:
    state = published_state()
    by_slug = {listing["slug"]: listing for listing in state["catalog"]}
    visible = set(state["visible"])
    registry = set(state["runtimeSlugs"])
    sitemap = SITEMAP.read_text(encoding="utf-8")

    for slug in catalog_managed_runtime_slugs():
        assert slug in by_slug, f"{slug} missing from catalog"
        assert slug in visible, f"{slug} hidden from public catalog"
        assert slug in registry, f"{slug} missing from generated runtime registry"
        listing = by_slug[slug]
        assert listing.get("runManifest") == f"run-manifests/{slug}.json"
        assert listing.get("status") == "ready"
        assert listing.get("active") is True
        assert listing.get("chargeable") is True
        assert (ROOT / "site" / listing["runManifest"]).is_file()
        assert (ROOT / "site" / "workflows" / slug / "index.html").is_file()
        assert f"https://omo.space/workflows/{slug}/" in sitemap


def test_every_visible_workflow_is_runnable_and_has_public_assets() -> None:
    state = published_state()
    by_slug = {listing["slug"]: listing for listing in state["catalog"]}
    sitemap = SITEMAP.read_text(encoding="utf-8")

    for slug in state["visible"]:
        listing = by_slug[slug]
        assert slug in set(state["runtimeSlugs"])
        assert listing.get("runManifest"), f"{slug} is visible without a run manifest"
        assert listing.get("status") == "ready"
        assert listing.get("active") is True
        assert listing.get("chargeable") is True
        assert (ROOT / "site" / listing["runManifest"]).is_file()
        assert (ROOT / "site" / "workflows" / slug / "index.html").is_file()
        assert f"https://omo.space/workflows/{slug}/" in sitemap


def test_blocked_previews_are_not_publicly_projected() -> None:
    state = published_state()
    visible = set(state["visible"])
    blocked = {
        listing["slug"]
        for listing in state["catalog"]
        if listing.get("status") == "coming-soon"
        or listing.get("active") is False
        or listing.get("chargeable") is False
    }

    assert blocked
    assert blocked.isdisjoint(visible)
