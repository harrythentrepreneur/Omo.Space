"""Offline contract tests for the synchronous Claude SEO Skill container."""

from __future__ import annotations

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
        "claude_seo_skill_modal_app", ROOT / "modal_app.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modal_app = _load_module()


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


SCHEMAS = {name: _schema(name) for name in ("input.json", "output.json")}


class StubCompletions:
    def __init__(self, outputs: list[str]):
        self.outputs = iter(outputs)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=next(self.outputs))
                )
            ]
        )


class StubLLM:
    def __init__(self, outputs: list[str]):
        self.completions = StubCompletions(outputs)
        self.chat = SimpleNamespace(completions=self.completions)


def test_fixture_inventory_is_exact() -> None:
    assert len(CASES["happy_paths"]) == 3
    assert len(CASES["negative_cases"]) == 5
    assert {case["id"] for case in CASES["happy_paths"]} == {
        "ecommerce-brand",
        "local-service-business",
        "saas",
    }


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_document_is_valid_draft_2020_12(name: str) -> None:
    Draft202012Validator.check_schema(SCHEMAS[name])


@pytest.mark.parametrize("case", CASES["happy_paths"], ids=lambda case: case["id"])
def test_happy_input_fixture_matches_schema(case: dict) -> None:
    Draft202012Validator(SCHEMAS["input.json"]).validate(case["input"])


@pytest.mark.parametrize("case", CASES["happy_paths"], ids=lambda case: case["id"])
def test_happy_output_fixture_matches_schema(case: dict) -> None:
    Draft202012Validator(SCHEMAS["output.json"]).validate(case["output"])
    assert set(case["output"]) == {"findings", "quick_wins", "summary"}


@pytest.mark.parametrize(
    "case", CASES["negative_cases"], ids=lambda case: case["id"]
)
def test_negative_fixture_is_rejected(case: dict) -> None:
    errors = list(
        Draft202012Validator(SCHEMAS[case["schema"]]).iter_errors(case["instance"])
    )
    assert errors, case["reason"]


def test_oversized_fixture_really_exceeds_limit() -> None:
    case = next(
        case for case in CASES["negative_cases"] if case["id"] == "oversized-field"
    )
    assert len(case["instance"]["niche"]) > 200


@pytest.mark.parametrize(
    "raw",
    [
        '{"findings":[{"issue":"I","fix":"F","priority":"high"}],"quick_wins":["Q"],"summary":"S"}',
        '```json\n{"findings":[{"issue":"I","fix":"F","priority":"medium"}],"quick_wins":["Q"],"summary":"S"}\n```',
        '```\n{"findings":[{"issue":"I","fix":"F","priority":"low"}],"quick_wins":["Q"],"summary":"S"}\n```',
        'Here is the audit: {"findings":[{"issue":"I","fix":"F","priority":"high"}],"quick_wins":["Q"],"summary":"S"}',
        'Result follows. {"findings":[{"issue":"I","fix":"F","priority":"high"}],"quick_wins":["Q"],"summary":"S"} Done.',
    ],
)
def test_parser_recovers_valid_json_from_common_wrappers(raw: str) -> None:
    parsed = modal_app.parse_llm_json(raw)
    assert set(parsed) == {"findings", "quick_wins", "summary"}


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not json",
        "[1, 2, 3]",
        "{broken}",
        "```json\n{broken}\n```",
        "```json no newline or close",
    ],
)
def test_parser_rejects_empty_non_object_or_malformed_output(raw: str) -> None:
    with pytest.raises(ValueError):
        modal_app.parse_llm_json(raw)


def test_parser_rejects_extra_fields() -> None:
    raw = '{"findings":[{"issue":"I","fix":"F","priority":"high","score":9}],"quick_wins":["Q"],"summary":"S"}'
    with pytest.raises(ValidationError):
        modal_app.parse_llm_json(raw)


def test_parser_rejects_bad_priority_enum() -> None:
    bad = next(
        case
        for case in CASES["negative_cases"]
        if case["id"] == "bad-priority-enum"
    )
    with pytest.raises(ValidationError):
        modal_app.parse_llm_json(json.dumps(bad["instance"]))


def test_execute_workflow_uses_one_stubbed_call_and_no_key(monkeypatch) -> None:
    fixture = CASES["happy_paths"][0]
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    stub = StubLLM([json.dumps(fixture["output"])])

    response = modal_app.execute_workflow(fixture["input"], llm_client=stub)

    assert response == {
        "status": "completed",
        "result": fixture["output"],
        "usage": {
            "estimated_cost_usd": 0.0002,
            "buyer_run_price_usd": 0.10,
        },
    }
    assert len(stub.completions.calls) == 1
    call = stub.completions.calls[0]
    assert call["model"] == "deepseek-v4-flash"
    assert call["max_tokens"] == 500
    assert call["temperature"] == 0.2


def test_model_can_be_overridden_from_environment(monkeypatch) -> None:
    fixture = CASES["happy_paths"][1]
    monkeypatch.setenv("LLM_MODEL", "test-model")
    stub = StubLLM([json.dumps(fixture["output"])])

    modal_app.execute_workflow(fixture["input"], llm_client=stub)

    assert stub.completions.calls[0]["model"] == "test-model"


def test_prompt_contains_hardened_exact_shape_and_no_crawl_claim() -> None:
    prompt = modal_app.load_prompt("audit.txt")
    assert "Return EXACTLY this JSON" in prompt
    assert '"findings"' in prompt
    assert '"quick_wins"' in prompt
    assert '"priority":"high|medium|low"' in prompt
    assert "cannot browse or crawl" in prompt


def test_fastapi_surface_declares_only_synchronous_run_route() -> None:
    web = modal_app.create_fastapi_app(llm_client=StubLLM([]))
    workflow_routes = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in web.routes
        if route.path.startswith("/v1/")
    }
    assert workflow_routes == {("/v1/run", ("POST",))}


def _run_endpoint(web):
    return next(route.endpoint for route in web.routes if route.path == "/v1/run")


def test_run_endpoint_returns_completed_200_contract() -> None:
    fixture = CASES["happy_paths"][2]
    stub = StubLLM([json.dumps(fixture["output"])])
    web = modal_app.create_fastapi_app(llm_client=stub)
    route = next(route for route in web.routes if route.path == "/v1/run")

    response = route.endpoint(fixture["input"])

    assert route.status_code == 200
    assert response["status"] == "completed"
    assert response["result"] == fixture["output"]
    assert len(stub.completions.calls) == 1


@pytest.mark.parametrize(
    "case",
    [case for case in CASES["negative_cases"] if case["schema"] == "input.json"],
    ids=lambda case: case["id"],
)
def test_run_validates_input_before_llm(case: dict) -> None:
    from fastapi import HTTPException

    stub = StubLLM([])
    run = _run_endpoint(modal_app.create_fastapi_app(llm_client=stub))

    with pytest.raises(HTTPException) as exc_info:
        run(case["instance"])

    assert exc_info.value.status_code == 422
    assert stub.completions.calls == []


def test_invalid_provider_output_returns_502_without_leaking_body() -> None:
    from fastapi import HTTPException

    fixture = CASES["happy_paths"][0]
    run = _run_endpoint(modal_app.create_fastapi_app(StubLLM(["secret bad body"])))

    with pytest.raises(HTTPException) as exc_info:
        run(fixture["input"])

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "LLM returned an invalid response"
