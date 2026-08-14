"""Tests for the host-skill registration layer."""

from __future__ import annotations

import importlib.util
import json
import subprocess
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
    assert first["runtime"]["input_schema"] == manifest["input_schema"]
    assert first["runtime"]["output_schema"] == manifest["output_schema"]
    assert first["runtime"]["reviewed_source_sha256"] == manifest["source_sha256"]
    assert len(first["runtime"]["reviewed_source_sha256"]) == 64
    assert first["run_manifest"]["price_usd"] == pricing["display_price_usd"] == 0.1


def test_host_registration_preserves_compiler_materialized_adapter_and_artifact_schemas() -> None:
    skill = ROOT / "containers" / "woven-storybook-pipeline" / "source" / "SKILL.md"
    profile_path = (
        ROOT / "packages" / "skill-to-modal" / "profiles" / "woven-storybook-pipeline.json"
    )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    files = host.COMPILER.build_files(skill.read_text(encoding="utf-8"), profile)
    manifest = json.loads(files["manifest.json"])
    pricing = json.loads(files["pricing-report.json"])
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    input_schema = hosted["runtime"]["input_schema"]
    output_schema = hosted["runtime"]["output_schema"]

    assert "chat_zip" in input_schema["properties"]
    assert len(input_schema["oneOf"]) == 2
    assert {"artifact", "artifact_url"} <= set(output_schema["required"])
    assert hosted["run_manifest"]["input_schema"] == input_schema
    assert hosted["run_manifest"]["output_schema"] == output_schema


def test_host_registration_supports_owned_native_media_executor() -> None:
    slug = "japanese-style-story-video"
    skill = ROOT / "containers" / slug / "source" / "SKILL.md"
    profile_path = ROOT / "packages" / "skill-to-modal" / "profiles" / f"{slug}.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    files = host.COMPILER.build_files(skill.read_text(encoding="utf-8"), profile)
    manifest = json.loads(files["manifest.json"])
    pricing = json.loads(files["pricing-report.json"])
    hosted = host.build_hosted_profile(profile, manifest, pricing)

    assert hosted["catalog_managed"] is False
    assert hosted["runtime_placement"]["effective"] == "modal-hosted"
    assert hosted["runtime"]["protocol"] == "owner-scoped-async-v1"
    assert hosted["runtime"]["run_price_cents"] == 10
    assert hosted["runtime"]["input_schema"] == manifest["input_schema"]
    assert hosted["runtime"]["output_schema"] == manifest["output_schema"]
    assert hosted["server_catalog"]["model"] == "native-media"
    assert hosted["server_catalog"]["max_tokens"] == 0
    assert hosted["catalog"]["runManifest"] == (
        "run-manifests/japanese-style-story-video.json"
    )
    assert all(
        step["type"] == "pipeline" for step in hosted["catalog"]["workflow"]["steps"]
    )


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


def test_modal_endpoint_must_match_expected_omo_workspace() -> None:
    stale = "https://harrythentrepreneur--cognition-woven-storybook-pipeline-api.modal.run"
    with pytest.raises(ValueError, match="workspace"):
        host.validate_https_modal_endpoint(stale, expected_workspace="omo-space")

    endpoint = host.validate_https_modal_endpoint(
        "https://omo-space--cognition-woven-storybook-pipeline-api.modal.run",
        expected_workspace="omo-space",
    )
    assert endpoint.startswith("https://omo-space--")


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
    assert hosted["runtime"]["executor"] == {
        "spec_version": "omo.worker-single-llm/v1",
        "execution_kind": "single_llm",
        "operation": "chat.completions.strict_json",
        "provider": "opencode-go",
        "model": "deepseek-v4-flash",
        "system_prompt": profile["prompts"]["run.txt"],
        "workflow_version": profile["version"],
        "max_output_tokens": 1600,
        "temperature": 0.55,
        "timeout_seconds": 120,
    }
    assert "api_key_env" not in hosted["runtime"]["executor"]
    assert "base_url_env" not in hosted["runtime"]["executor"]
    assert "default_base_url" not in hosted["runtime"]["executor"]


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


def test_unknown_capability_fails_closed_to_modal() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["capabilities"].append("future-browser-capability")
    profile["runtime_preference"] = "auto"
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    assert hosted["runtime_placement"]["effective"] == "modal-hosted"
    assert hosted["runtime_placement"]["reason"] == "worker_executor_contract_not_satisfied"


@pytest.mark.parametrize(
    "mutate, match",
    [
        (lambda profile: profile["steps"][0].update({"provider": "deepseek"}), "provider"),
        (lambda profile: profile["steps"][0].update({"operation": "chat.completions"}), "operation"),
        (lambda profile: profile["steps"].append(dict(profile["steps"][0], id="second-call")), "reviewed_steps"),
        (lambda profile: profile.__setitem__("steps", []), "reviewed_steps"),
        (lambda profile: profile.__setitem__("apt_packages", ["ffmpeg"]), "apt_packages"),
        (lambda profile: profile.__setitem__("artifacts", [{"kind": "pdf"}]), "artifacts"),
        (lambda profile: profile["live"].pop("max_tokens"), "max_output_tokens"),
        (lambda profile: profile["live"].pop("temperature"), "temperature"),
        (lambda profile: profile["live"].pop("timeout_seconds"), "timeout_seconds"),
        (lambda profile: profile["input_schema"].__setitem__("oneOf", []), "schema_keywords"),
    ],
)
def test_worker_override_fails_closed_when_executor_contract_is_incomplete(mutate, match: str) -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["runtime_preference"] = "worker-native"
    mutate(profile)
    with pytest.raises(ValueError, match=match):
        host.build_hosted_profile(profile, manifest, pricing)


def test_legacy_source_profile_defaults_to_modal() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile.pop("runtime_preference", None)
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    assert hosted["runtime_placement"]["effective"] == "modal-hosted"
    assert hosted["runtime_placement"]["reason"] == "legacy_profile_defaults_to_modal"


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
    assert "reviewed_source_sha256" in rendered


def test_legacy_runtime_without_kind_remains_modal() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["runtime_preference"] = "modal-hosted"
    legacy = host.build_hosted_profile(profile, manifest, pricing)
    legacy["runtime"].pop("kind")
    rendered = host.render_registry([legacy])
    modal_block = rendered.split("HOSTED_MODAL_SKILL_ROWS", 1)[1]
    assert "facebook-ads-copywriter" in modal_block


def test_unknown_generated_runtime_kind_is_rejected() -> None:
    profile, manifest, pricing = compiled_inputs()
    profile["runtime_preference"] = "modal-hosted"
    hosted = host.build_hosted_profile(profile, manifest, pricing)
    hosted["runtime"]["kind"] = "edge-magic"
    with pytest.raises(ValueError, match="unsupported generated runtime kind"):
        host.render_registry([hosted])


def test_pricing_verifier_checks_the_requested_compiled_report(tmp_path: Path) -> None:
    profile, _manifest, pricing = compiled_inputs()
    report_path = tmp_path / "pricing-report.json"
    report_path.write_text(json.dumps(pricing), encoding="utf-8")
    command = [
        "node",
        str(ROOT / "packages" / "skill-to-modal" / "verify-pricing.mjs"),
        profile["slug"],
        "--report",
        str(report_path),
    ]
    assert subprocess.run(command, cwd=ROOT, check=False).returncode == 0

    pricing["estimates"][0]["modeled_cost_usd"] = 999.0
    report_path.write_text(json.dumps(pricing), encoding="utf-8")
    assert subprocess.run(command, cwd=ROOT, check=False).returncode != 0


def test_display_path_supports_output_outside_the_repository(tmp_path: Path) -> None:
    assert host.display_path(ROOT / "containers" / "example") == "containers/example"
    assert host.display_path(tmp_path / "manifest.json") == str(tmp_path / "manifest.json")
