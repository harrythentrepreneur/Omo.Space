"""Generated offline contract tests: no keys, network, or spend."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import base64
import io
import zipfile

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location('woven_storybook_pipeline_modal_app', ROOT / "modal_app.py")
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
    expected = [f"{item['name']}@{item['version']}" for item in capabilities["selected"]]
    assert capabilities["approved"] == (expected if EXPECTED_READY else [])
    assert capabilities["schema_version"] == "cognition.capabilities/v2"
    assert capabilities["registry_digest"].startswith("sha256:")
    assert capabilities["contract_digest"].startswith("sha256:")


def _chat_zip(entries: dict[str, str]) -> dict[str, str]:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    return {
        "filename": "whatsapp-export.zip",
        "content_base64": base64.b64encode(buffer.getvalue()).decode("ascii"),
    }


def _synthetic_chat() -> str:
    return "\n".join([
        "1/2/20, 9:00 AM - Alice: Remember the rainy bookshop where we met?",
        "1/2/20, 9:01 AM - Bob: And reaching for the same travel book.",
        "2/3/21, 8:00 PM - Alice: Two cities and the tiny apartment were worth it.",
        "2/3/21, 8:01 PM - Bob: Wrong turn, best view. Always.",
        "3/4/22, 7:00 PM - Alice: The corgi stole another sock.",
        "3/4/22, 7:01 PM - Bob: Our smoke-alarm serenade still wins.",
    ])


def _story_result_without_artifact(*, llm_calls: int) -> dict:
    result = json.loads(json.dumps(CASES["happy_path"]["output"]))
    result.pop("artifact", None)
    result.pop("artifact_url", None)
    result["usage"]["llm_calls"] = llm_calls
    return result


def test_direct_fields_run_materializes_a_real_signed_pdf(tmp_path: Path) -> None:
    result = modal_app.execute_workflow(
        CASES["happy_path"]["input"],
        executor=lambda _payload: _story_result_without_artifact(llm_calls=1),
        artifact_root=tmp_path,
        artifact_signing_key="offline-test-signing-key",
        clock=lambda: 1_700_000_000,
    )
    descriptor = result["artifact"]
    path = tmp_path / descriptor["object_key"]
    assert path.read_bytes().startswith(b"%PDF-")
    assert path.stat().st_size == descriptor["bytes"]
    assert descriptor["page_count"] >= 4
    assert "expires=1700003600" in result["artifact_url"]
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)


def test_whatsapp_zip_derives_fields_then_runs_and_materializes_pdf(tmp_path: Path) -> None:
    request = {"chat_zip": _chat_zip({"_chat.txt": _synthetic_chat()})}
    derived = CASES["happy_path"]["input"]
    observed = {}

    def extractor(messages: list[dict]) -> dict:
        observed["messages"] = messages
        return derived

    def story_executor(payload: dict) -> dict:
        observed["payload"] = payload
        return _story_result_without_artifact(llm_calls=2)

    result = modal_app.execute_workflow(
        request,
        executor=story_executor,
        input_extractor=extractor,
        artifact_root=tmp_path,
        artifact_signing_key="offline-test-signing-key",
        clock=lambda: 1_700_000_000,
    )
    assert observed["payload"] == derived
    assert observed["messages"][0]["sender"] == "Participant 1"
    assert observed["messages"][1]["sender"] == "Participant 2"
    assert (tmp_path / result["artifact"]["object_key"]).is_file()
    assert result["artifact"]["page_count"] >= 4


def test_whatsapp_zip_without_chat_file_is_a_typed_error() -> None:
    with pytest.raises(modal_app.InputAdapterError, match="WHATSAPP_CHAT_NOT_FOUND"):
        modal_app._parse_whatsapp_zip(_chat_zip({"notes.txt": "not an export"}))


def test_oversized_whatsapp_zip_is_rejected_before_decode() -> None:
    oversized = "A" * ((((modal_app.WHATSAPP_MAX_ZIP_BYTES + 2) // 3) * 4) + 4)
    with pytest.raises(modal_app.InputAdapterError, match="WHATSAPP_ZIP_TOO_LARGE"):
        modal_app._parse_whatsapp_zip({
            "filename": "too-large.zip",
            "content_base64": oversized,
        })


def test_whatsapp_adapter_prompt_is_strict_and_treats_messages_as_hostile_data() -> None:
    prompt = (ROOT / modal_app.WHATSAPP_PROMPT_PATH).read_text(encoding="utf-8")
    assert "hostile quoted data" in prompt
    assert "Do not invent" in prompt
