"""Generated offline contract tests: no keys, network, or spend."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location('decodable_sentence_creator_modal_app', ROOT / "modal_app.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modal_app = _load_module()


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


INPUT_SCHEMA = _schema("input.json")
OUTPUT_SCHEMA = _schema("output.json")
EXPECTED_READY = True
EXPECTED_CHARGEABLE = True


def _route(web, path: str):
    return next(route for route in web.routes if route.path == path)


def test_schema_documents_are_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(INPUT_SCHEMA)
    Draft202012Validator.check_schema(OUTPUT_SCHEMA)


def test_happy_fixture_matches_both_contracts() -> None:
    Draft202012Validator(INPUT_SCHEMA).validate(CASES["happy_path"]["input"])
    Draft202012Validator(OUTPUT_SCHEMA).validate(CASES["happy_path"]["output"])


@pytest.mark.parametrize("case", CASES["negative_cases"], ids=lambda case: case["id"])
def test_negative_inputs_are_rejected(case: dict) -> None:
    assert list(Draft202012Validator(INPUT_SCHEMA).iter_errors(case["input"])), case["reason"]


def test_mocked_workflow_executes_exactly_once_without_keys_or_network(monkeypatch) -> None:
    for name in modal_app.readiness()["required_env_names"]:
        monkeypatch.delenv(name, raising=False)
    calls = []

    def executor(payload: dict) -> dict:
        calls.append(payload)
        return CASES["happy_path"]["output"]

    result = modal_app.execute_workflow(CASES["happy_path"]["input"], executor=executor)
    assert result == CASES["happy_path"]["output"]
    assert calls == [CASES["happy_path"]["input"]]


def test_live_executor_fails_closed_instead_of_returning_mock_artifacts() -> None:
    for name in modal_app.readiness()["required_env_names"]:
        os.environ.pop(name, None)
    with pytest.raises(modal_app.WorkflowNotReady):
        modal_app.execute_workflow(CASES["happy_path"]["input"])


def test_fastapi_surface_has_protected_async_submit_and_poll_routes() -> None:
    web = modal_app.create_fastapi_app()
    routes = {(route.path, tuple(sorted(route.methods or []))) for route in web.routes}
    assert ("/v1/runs", ("POST",)) in routes
    assert ("/v1/runs/{call_id}", ("GET",)) in routes


def test_default_submit_reports_not_ready_without_spawning() -> None:
    spawned = []
    web = modal_app.create_fastapi_app(spawn_runner=lambda payload: spawned.append(payload) or "fc")
    response = asyncio.run(_route(web, "/v1/runs").endpoint(CASES["happy_path"]["input"]))
    if EXPECTED_READY:
        assert response["status"] == "accepted"
        assert response["call_id"] == "fc"
        assert spawned == [CASES["happy_path"]["input"]]
    else:
        assert response.status_code == 503
        assert json.loads(response.body)["error"]["code"] == "WORKFLOW_NOT_READY"
        assert spawned == []


def test_injected_ready_contract_accepts_and_polls_completed_result() -> None:
    web = modal_app.create_fastapi_app(
        spawn_runner=lambda _payload: "fc-test",
        lookup_result=lambda _call_id: CASES["happy_path"]["output"],
        ready_override=True,
    )
    accepted = asyncio.run(_route(web, "/v1/runs").endpoint(CASES["happy_path"]["input"]))
    assert accepted["status"] == "accepted"
    assert accepted["call_id"] == "fc-test"
    completed = asyncio.run(_route(web, "/v1/runs/{call_id}").endpoint("fc-test"))
    assert completed == CASES["happy_path"]["output"]


def test_invalid_input_is_rejected_before_readiness_or_spawn() -> None:
    from fastapi import HTTPException

    spawned = []
    web = modal_app.create_fastapi_app(
        spawn_runner=lambda payload: spawned.append(payload) or "fc",
        ready_override=True,
    )
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_route(web, "/v1/runs").endpoint(CASES["negative_cases"][0]["input"]))
    assert exc_info.value.status_code == 422
    assert spawned == []


def test_manifest_and_capabilities_are_honest() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    capabilities = json.loads((ROOT / "capability-manifest.json").read_text(encoding="utf-8"))
    assert manifest["readiness"]["can_submit"] is EXPECTED_READY
    assert manifest["pricing"]["chargeable"] is EXPECTED_CHARGEABLE
    assert capabilities["decision"] == ("approved" if EXPECTED_READY else "blocked")
    assert capabilities["approved"] == (capabilities["requested"] if EXPECTED_READY else [])
