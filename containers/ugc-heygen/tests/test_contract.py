"""Account-free contract tests for the UGC HeyGen Day-1 canary."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
CASES = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "ugc_heygen_modal_app", ROOT / "modal_app.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modal_app = _load_module()


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


SCHEMAS = {
    name: _schema(name)
    for name in ("input.json", "script.json", "captions.json", "output.json")
}


class StubCompletions:
    def __init__(self, outputs: list[str]):
        self.outputs = iter(outputs)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = next(self.outputs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class StubLLM:
    def __init__(self, outputs: list[str]):
        self.completions = StubCompletions(outputs)
        self.chat = SimpleNamespace(completions=self.completions)


def test_fixture_inventory_is_exact() -> None:
    assert len(CASES["happy_paths"]) == 3
    assert len(CASES["negative_cases"]) == 6
    assert {case["id"] for case in CASES["happy_paths"]} == {
        "silk-pillowcase-30s",
        "protein-powder-15s",
        "dtc-skincare-60s",
    }


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_document_is_valid_draft_2020_12(name: str) -> None:
    Draft202012Validator.check_schema(SCHEMAS[name])


@pytest.mark.parametrize("case", CASES["happy_paths"], ids=lambda case: case["id"])
def test_happy_path_contracts(case: dict) -> None:
    Draft202012Validator(SCHEMAS["input.json"]).validate(case["input"])
    Draft202012Validator(SCHEMAS["script.json"]).validate(case["script"])
    Draft202012Validator(SCHEMAS["captions.json"]).validate(case["captions"])
    Draft202012Validator(SCHEMAS["output.json"]).validate(case["output"])

    assert set(case["script"]) == {"hook", "lines", "cta"}
    assert "shots" not in case["script"]
    assert len(case["captions"]["captions"]) == len(case["script"]["lines"])
    assert case["output"]["video"] is None


@pytest.mark.parametrize(
    "case", CASES["negative_cases"], ids=lambda case: case["id"]
)
def test_negative_inputs_are_rejected(case: dict) -> None:
    errors = list(
        Draft202012Validator(SCHEMAS["input.json"]).iter_errors(case["input"])
    )
    assert errors, case["reason"]


def test_oversized_fixture_really_exceeds_limit() -> None:
    oversized = next(
        case
        for case in CASES["negative_cases"]
        if case["id"] == "oversized-product-description"
    )
    assert len(oversized["input"]["product_description"]) > 2000


@pytest.mark.parametrize(
    "raw",
    [
        '{"hook":"H","lines":["L"],"cta":"C"}',
        '```json\n{"hook":"H","lines":["L"],"cta":"C"}\n```',
        'Result: {"hook":"H","lines":["L"],"cta":"C"} done.',
    ],
)
def test_parser_recovers_json_without_changing_shape(raw: str) -> None:
    parsed = modal_app.parse_llm_json(raw, "script.json")
    assert parsed == {"hook": "H", "lines": ["L"], "cta": "C"}


@pytest.mark.parametrize("raw", ["", "not json", "[1, 2, 3]", "{broken}"])
def test_parser_rejects_non_object_or_malformed_output(raw: str) -> None:
    with pytest.raises(ValueError):
        modal_app.parse_llm_json(raw, "script.json")


def test_parser_rejects_extra_llm_fields() -> None:
    raw = '{"hook":"H","lines":["L"],"cta":"C","shots":[]}'
    with pytest.raises(ValidationError):
        modal_app.parse_llm_json(raw, "script.json")


def test_execute_canary_uses_two_stubbed_llm_calls_and_no_keys(monkeypatch) -> None:
    fixture = CASES["happy_paths"][0]
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    stub = StubLLM(
        [
            "```json\n" + json.dumps(fixture["script"]) + "\n```",
            json.dumps(fixture["captions"]),
        ]
    )

    result = modal_app.execute_canary(
        fixture["input"], llm_client=stub, run_id="stubbed-run"
    )

    Draft202012Validator(SCHEMAS["output.json"]).validate(result)
    assert result["run_id"] == "stubbed-run"
    assert result["video"] is None
    assert len(stub.completions.calls) == 2
    assert all(
        call["model"] == "deepseek-v4-flash" for call in stub.completions.calls
    )


def test_execute_canary_rejects_caption_line_mismatch() -> None:
    fixture = CASES["happy_paths"][0]
    stub = StubLLM(
        [
            json.dumps(fixture["script"]),
            json.dumps({"captions": ["only one"]}),
        ]
    )

    with pytest.raises(ValueError, match="same length"):
        modal_app.execute_canary(fixture["input"], llm_client=stub)


def test_fastapi_surface_declares_submit_and_poll_routes() -> None:
    web = modal_app.create_fastapi_app(
        spawn_runner=lambda _payload, _run_id: "fc-test",
        lookup_result=lambda _call_id: CASES["happy_paths"][0]["output"],
    )
    routes = {(route.path, tuple(sorted(route.methods or []))) for route in web.routes}
    assert ("/v1/runs", ("POST",)) in routes
    assert ("/v1/runs/{call_id}", ("GET",)) in routes


def _route_endpoint(web, path: str):
    return next(route.endpoint for route in web.routes if route.path == path)


def test_submit_endpoint_validates_then_returns_accepted_contract() -> None:
    fixture = CASES["happy_paths"][0]
    spawned: list[tuple[dict, str]] = []
    web = modal_app.create_fastapi_app(
        spawn_runner=lambda payload, run_id: spawned.append((payload, run_id))
        or "fc-test"
    )
    submit = _route_endpoint(web, "/v1/runs")

    response = asyncio.run(submit(fixture["input"]))

    assert response == {
        "run_id": response["run_id"],
        "call_id": "fc-test",
        "status": "accepted",
        "result_url": "/v1/runs/fc-test",
    }
    assert spawned == [(fixture["input"], response["run_id"])]


def test_submit_endpoint_rejects_invalid_input_before_spawn() -> None:
    from fastapi import HTTPException

    spawned: list[tuple[dict, str]] = []
    web = modal_app.create_fastapi_app(
        spawn_runner=lambda payload, run_id: spawned.append((payload, run_id))
        or "should-not-run"
    )
    submit = _route_endpoint(web, "/v1/runs")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(submit(CASES["negative_cases"][0]["input"]))

    assert exc_info.value.status_code == 422
    assert spawned == []


def test_poll_endpoint_returns_running_or_completed_contract() -> None:
    def still_running(_call_id: str):
        raise TimeoutError

    running_web = modal_app.create_fastapi_app(lookup_result=still_running)
    running_get = _route_endpoint(running_web, "/v1/runs/{call_id}")
    running = asyncio.run(running_get("fc-running"))
    assert running.status_code == 202
    assert json.loads(running.body) == {
        "call_id": "fc-running",
        "status": "running",
    }

    completed_fixture = CASES["happy_paths"][0]["output"]
    completed_web = modal_app.create_fastapi_app(
        lookup_result=lambda _call_id: completed_fixture
    )
    completed_get = _route_endpoint(completed_web, "/v1/runs/{call_id}")
    completed = asyncio.run(completed_get("fc-completed"))
    assert completed == completed_fixture
