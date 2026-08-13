"""Tests for the host-skill registration layer."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
HOST_PATH = ROOT / "tools" / "host-skill" / "host.py"


def load_host():
    spec = importlib.util.spec_from_file_location("host_skill_test", HOST_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


host = load_host()
PROFILE_PATH = ROOT / "packages" / "skill-to-modal" / "profiles" / "facebook-ads-copywriter.json"
SKILL_PATH = ROOT / "packages" / "facebook-ads-copywriter" / "SKILL.md"


def compiled_inputs() -> tuple[dict, dict, dict]:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    files = host.COMPILER.build_files(SKILL_PATH.read_text(encoding="utf-8"), profile)
    return profile, json.loads(files["manifest.json"]), json.loads(files["pricing-report.json"])


def test_hosted_profile_is_deterministic_and_schema_driven() -> None:
    profile, manifest, pricing = compiled_inputs()
    first = host.build_hosted_profile(profile, manifest, pricing)
    second = host.build_hosted_profile(profile, manifest, pricing)
    assert first == second
    assert first["runtime"]["input_schema"] == profile["input_schema"]
    assert first["runtime"]["output_schema"] == profile["output_schema"]
    assert first["run_manifest"]["price_usd"] == pricing["display_price_usd"] == 0.1


def test_catalog_patch_is_idempotent() -> None:
    profile, manifest, pricing = compiled_inputs()
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    source = "window.OMO_CATALOG = [\n  { slug: 'legacy' }\n];\n"
    first = host.patch_catalog(source, [hosted])
    second = host.patch_catalog(first, [hosted])
    assert first == second
    assert first.count("facebook-ads-copywriter") == 2
    assert first.count(host.CATALOG_START) == 1
    assert first.count(host.CATALOG_END) == 1


def test_catalog_patch_preserves_content_after_generated_marker() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["runtime_preference"] = "modal-hosted"
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    source = (
        "window.OMO_CATALOG = [\n"
        f"{host.CATALOG_START}\n{host.CATALOG_END}\n"
        "];\nwindow.OMO_CATALOG.push({ slug: 'later' });\n"
    )
    patched = host.patch_catalog(source, [hosted])
    assert "window.OMO_CATALOG.push({ slug: 'later' });" in patched
    assert patched.count("facebook-ads-copywriter") == 2


def test_existing_hand_managed_slug_is_not_duplicated() -> None:
    profile, manifest, pricing = compiled_inputs()
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    source = "window.OMO_CATALOG = [\n  { slug: 'facebook-ads-copywriter' }\n];\n"
    patched = host.patch_catalog(source, [hosted])
    assert patched.count("facebook-ads-copywriter") == 1


def test_registry_generation_is_deterministic_and_secret_free() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["runtime_preference"] = "modal-hosted"
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    first = host.render_registry([hosted])
    assert first == host.render_registry([hosted])
    assert "HOSTED_MODAL_PROXY_TOKEN_ID" in first
    assert "wk-" not in first and "ws-" not in first


def test_non_modal_endpoint_is_rejected() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["runtime_preference"] = "modal-hosted"
    profile["marketplace"]["deployment"]["default_endpoint"] = "https://example.com"
    with pytest.raises(ValueError, match=r"\*\.modal\.run"):
        host.build_hosted_profile(profile, manifest, pricing)


def test_lightweight_single_llm_defaults_to_worker_native() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["runtime_preference"] = "auto"
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    decision = hosted["runtime_placement"]
    assert decision == {
        "recommended": "worker-native",
        "requested": "auto",
        "effective": "worker-native",
        "compatible": True,
        "reason": "bounded_single_llm_is_worker_compatible",
    }
    assert hosted["runtime"]["kind"] == "worker-native"
    assert "default_endpoint" not in hosted["runtime"]


def test_creator_can_choose_modal_for_worker_compatible_workflow() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["runtime_preference"] = "modal-hosted"
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    assert hosted["runtime_placement"]["recommended"] == "worker-native"
    assert hosted["runtime_placement"]["effective"] == "modal-hosted"
    assert hosted["runtime_placement"]["compatible"] is True
    assert hosted["runtime"]["default_endpoint"].endswith(".modal.run")


def test_heavy_capability_rejects_worker_override() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["capabilities"].append("ffmpeg")
    profile["runtime_preference"] = "worker-native"
    with pytest.raises(ValueError, match="requires Modal"):
        host.build_hosted_profile(profile, manifest, pricing)


def test_registry_separates_worker_and_modal_rows() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["runtime_preference"] = "worker-native"
    worker = host.build_hosted_profile(profile, manifest, pricing)
    profile["runtime_preference"] = "modal-hosted"
    modal = host.build_hosted_profile(profile, manifest, pricing)
    modal["runtime"]["slug"] = "facebook-ads-copywriter-modal"
    modal["server_catalog"]["slug"] = "facebook-ads-copywriter-modal"
    rendered = host.render_registry([worker, modal])
    assert "HOSTED_WORKER_SKILL_ROWS" in rendered
    assert "HOSTED_MODAL_SKILL_ROWS" in rendered


def test_legacy_runtime_without_kind_remains_modal() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["runtime_preference"] = "modal-hosted"
    legacy = host.build_hosted_profile(profile, manifest, pricing)
    legacy["runtime"].pop("kind")
    rendered = host.render_registry([legacy])
    modal_block = rendered.split("HOSTED_MODAL_SKILL_ROWS", 1)[1]
    assert "facebook-ads-copywriter" in modal_block
