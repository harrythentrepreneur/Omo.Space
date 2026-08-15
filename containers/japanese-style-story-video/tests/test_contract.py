"""Generated offline contract tests for the owned procedural media executor."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "japanese_style_story_video_modal_app", ROOT / "modal_app.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modal_app = _load_module()
INPUT_SCHEMA = json.loads((ROOT / "schemas" / "input.json").read_text(encoding="utf-8"))
OUTPUT_SCHEMA = json.loads((ROOT / "schemas" / "output.json").read_text(encoding="utf-8"))


def _route(web, path: str):
    return next(route for route in web.routes if route.path == path)


def test_schema_documents_and_happy_fixture_are_valid() -> None:
    Draft202012Validator.check_schema(INPUT_SCHEMA)
    Draft202012Validator.check_schema(OUTPUT_SCHEMA)
    Draft202012Validator(INPUT_SCHEMA).validate(CASES["happy_path"]["input"])
    Draft202012Validator(OUTPUT_SCHEMA).validate(CASES["happy_path"]["output"])


@pytest.mark.parametrize("case", CASES["negative_cases"], ids=lambda case: case["id"])
def test_non_sample_inputs_fail_closed(case: dict) -> None:
    assert list(Draft202012Validator(INPUT_SCHEMA).iter_errors(case["input"])), case["reason"]


def test_manifest_is_ready_chargeable_and_resolves_owned_executor() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    capabilities = json.loads((ROOT / "capability-manifest.json").read_text(encoding="utf-8"))
    assert manifest["readiness"] == {
        "status": "ready",
        "can_submit": True,
        "blockers": [],
        "required_env_names": [],
    }
    assert manifest["pricing"]["chargeable"] is True
    assert manifest["pricing"]["display_price_usd"] == 0.10
    assert capabilities["decision"] == "approved"
    assert [item["name"] for item in capabilities["selected"]] == [
        "domain_state",
        "video_processing",
    ]
    assert capabilities["approved"] == [
        "domain_state@1.0.0",
        "video_processing@1.0.0",
    ]
    owned = capabilities["skill_owned_resources"]
    assert [item["id"] for item in owned] == ["japanese_procedural_sumi_e_v1"]
    assert owned[0]["digest"].startswith("sha256:")
    assert (ROOT / "resources" / "demello_resource" / "image_gen.py").is_file()
    assert (ROOT / "resources" / "demello_resource" / "workflow.py").is_file()
    assert (ROOT / "resources" / "demello_resource" / "media.py").is_file()
    assert (ROOT / "resources" / "demello_resource" / "assets" / "sample-demello-10s.m4a").is_file()


def test_procedural_renderer_is_deterministic_portrait_sumi_e(tmp_path: Path) -> None:
    _workflow, image_gen = modal_app._demello_modules()
    generator = image_gen.ProceduralSumiEGenerator(
        width=540, height=960, supersample=1
    )
    spec = {
        "frame_id": "G000",
        "second": 0,
        "role": "settle",
        "meaning": "taste the present moment",
        "verb": "open",
        "delta": "move the awareness aperture upward by 0.0025",
        "protected": ["main figure identity", "white margins"],
        "pivot": True,
    }
    first = generator.render(spec, 0, 30)
    second = generator.render(spec, 0, 30)
    assert first == second
    report = image_gen.validate_image_bytes(first, expected_size=(540, 960))
    assert report.passed is True
    assert report.portrait is True
    assert report.chroma_ratio == 0
    assert report.exact_white_ratio >= 0.85


def test_mock_executor_runs_exactly_once_without_media_effects() -> None:
    calls = []

    def executor(payload: dict) -> dict:
        calls.append(payload)
        return CASES["happy_path"]["output"]

    result = modal_app.execute_workflow(CASES["happy_path"]["input"], executor=executor)
    assert result == CASES["happy_path"]["output"]
    assert calls == [CASES["happy_path"]["input"]]


def test_owner_scoped_state_denies_cross_owner() -> None:
    token = "t" * 43
    run_id = modal_app.run_id_for("owner-a", token)
    state = modal_app.InMemoryDomainState(clock=lambda: 1000.0)
    assert state.create("owner-a", run_id)["status"] == "queued"
    assert state.transition("owner-a", run_id, "processing", "rendering", 25)["progress_pct"] == 25
    with pytest.raises(modal_app.DomainStateError, match="STATE_NOT_FOUND"):
        state.read_owned("owner-b", run_id)
    assert state.transition("owner-a", run_id, "done", "done", 100)["status"] == "done"


def test_async_proxy_surface_requires_owner_and_returns_202() -> None:
    observed = []
    web = modal_app.create_fastapi_app(
        spawn_runner=lambda envelope: observed.append(envelope) or "fc-owned-test"
    )
    submit = _route(web, "/v1/runs").endpoint
    accepted = asyncio.run(
        submit(CASES["happy_path"]["input"], "owner-test")
    )
    assert accepted["status"] == "accepted"
    assert accepted["call_id"] == "fc-owned-test"
    assert accepted["run_id"] == observed[0]["run_id"]
    assert observed[0]["owner_id"] == "owner-test"
    with pytest.raises(Exception) as exc_info:
        asyncio.run(submit(CASES["happy_path"]["input"], None))
    assert getattr(exc_info.value, "status_code", None) == 422


def test_poll_identity_is_bound_to_owner_and_token() -> None:
    owner = "owner-test"
    token = "t" * 43
    run_id = modal_app.run_id_for(owner, token)
    result = json.loads(json.dumps(CASES["happy_path"]["output"]))
    result["run_id"] = run_id
    web = modal_app.create_fastapi_app(lookup_result=lambda _call_id: result)
    poll = _route(web, "/v1/runs/{run_id}").endpoint
    completed = asyncio.run(poll(run_id, "fc-test-0001", token, owner))
    assert completed["run_id"] == run_id
    with pytest.raises(Exception) as exc_info:
        asyncio.run(poll(run_id, "fc-test-0001", token, "owner-other"))
    assert getattr(exc_info.value, "status_code", None) == 404
