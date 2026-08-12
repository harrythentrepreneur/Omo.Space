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


def test_existing_hand_managed_slug_is_not_duplicated() -> None:
    profile, manifest, pricing = compiled_inputs()
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    source = "window.OMO_CATALOG = [\n  { slug: 'facebook-ads-copywriter' }\n];\n"
    patched = host.patch_catalog(source, [hosted])
    assert patched.count("facebook-ads-copywriter") == 1


def test_registry_generation_is_deterministic_and_secret_free() -> None:
    profile, manifest, pricing = compiled_inputs()
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    first = host.render_registry([hosted])
    assert first == host.render_registry([hosted])
    assert "HOSTED_MODAL_PROXY_TOKEN_ID" in first
    assert "wk-" not in first and "ws-" not in first


def test_non_modal_endpoint_is_rejected() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["marketplace"]["deployment"]["default_endpoint"] = "https://example.com"
    with pytest.raises(ValueError, match=r"\*\.modal\.run"):
        host.build_hosted_profile(profile, manifest, pricing)
