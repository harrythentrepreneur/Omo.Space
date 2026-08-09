"""Offline contract tests for the synchronous LLM + Modal-GPU canary."""

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
        "gpt_image_seedance_ad_modal_app", ROOT / "modal_app.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modal_app = _load_module()


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


SCHEMAS = {name: _schema(name) for name in ("input.json", "output.json")}
CONCEPT_SCHEMA = SCHEMAS["output.json"]["properties"]["concept"]


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


def _run_endpoint(web):
    return next(route.endpoint for route in web.routes if route.path == "/v1/run")


def test_fixture_inventory_is_exact() -> None:
    assert len(CASES["happy_paths"]) == 3
    assert len(CASES["negative_cases"]) == 5
    assert {case["id"] for case in CASES["happy_paths"]} == {
        "dtc-skincare-cinematic-9x16",
        "streetwear-bold-1x1",
        "coffee-premium-16x9",
    }


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_document_is_valid_draft_2020_12(name: str) -> None:
    Draft202012Validator.check_schema(SCHEMAS[name])


@pytest.mark.parametrize("case", CASES["happy_paths"], ids=lambda case: case["id"])
def test_happy_input_fixture_matches_schema(case: dict) -> None:
    Draft202012Validator(SCHEMAS["input.json"]).validate(case["input"])


@pytest.mark.parametrize("case", CASES["happy_paths"], ids=lambda case: case["id"])
def test_happy_concept_fixture_matches_nested_schema(case: dict) -> None:
    Draft202012Validator(CONCEPT_SCHEMA).validate(case["concept"])
    assert set(case["concept"]) == {
        "scene",
        "visual_style",
        "camera",
        "lighting",
        "prompt_text",
    }


@pytest.mark.parametrize("case", CASES["happy_paths"], ids=lambda case: case["id"])
def test_happy_output_fixture_matches_schema(case: dict) -> None:
    Draft202012Validator(SCHEMAS["output.json"]).validate(case["output"])
    assert len(case["output"]["images"]) == 3
    assert all("MOCK" in image["url"] for image in case["output"]["images"])


@pytest.mark.parametrize(
    "case", CASES["negative_cases"], ids=lambda case: case["id"]
)
def test_negative_input_fixture_is_rejected(case: dict) -> None:
    errors = list(
        Draft202012Validator(SCHEMAS["input.json"]).iter_errors(case["input"])
    )
    assert errors, case["reason"]


def test_oversized_fixture_really_exceeds_limit() -> None:
    case = next(
        case
        for case in CASES["negative_cases"]
        if case["id"] == "oversized-product-description"
    )
    assert len(case["input"]["product_description"]) == 2001


@pytest.mark.parametrize(
    "raw",
    [
        '{"scene":"S","visual_style":"V","camera":"C","lighting":"L","prompt_text":"A detailed product image prompt"}',
        '```json\n{"scene":"S","visual_style":"V","camera":"C","lighting":"L","prompt_text":"A detailed product image prompt"}\n```',
        '```\n{"scene":"S","visual_style":"V","camera":"C","lighting":"L","prompt_text":"A detailed product image prompt"}\n```',
        'Here is the concept: {"scene":"S","visual_style":"V","camera":"C","lighting":"L","prompt_text":"A detailed product image prompt"}',
        'Result follows. {"scene":"S","visual_style":"V","camera":"C","lighting":"L","prompt_text":"A detailed product image prompt"} Done.',
    ],
)
def test_parser_recovers_valid_json_from_common_wrappers(raw: str) -> None:
    parsed = modal_app.parse_llm_json(raw)
    assert parsed["scene"] == "S"
    assert set(parsed) == {
        "scene",
        "visual_style",
        "camera",
        "lighting",
        "prompt_text",
    }


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
    raw = (
        '{"scene":"S","visual_style":"V","camera":"C","lighting":"L",'
        '"prompt_text":"A detailed product image prompt","tagline":"invented"}'
    )
    with pytest.raises(ValidationError):
        modal_app.parse_llm_json(raw)


def test_parser_rejects_missing_fields() -> None:
    raw = '{"scene":"S","visual_style":"V","camera":"C","lighting":"L"}'
    with pytest.raises(ValidationError):
        modal_app.parse_llm_json(raw)


def test_call_llm_uses_catalog_defaults_and_strict_prompt(monkeypatch) -> None:
    fixture = CASES["happy_paths"][0]
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    stub = StubLLM([json.dumps(fixture["concept"])])

    result = modal_app.call_llm(fixture["input"], client=stub)

    assert result == fixture["concept"]
    assert len(stub.completions.calls) == 1
    call = stub.completions.calls[0]
    assert call["model"] == "deepseek-v4-flash"
    assert call["max_tokens"] == 500
    assert call["temperature"] == 0.2
    assert call["messages"][0]["content"] == modal_app.load_prompt("concept.txt")
    assert fixture["input"]["product_description"] in call["messages"][1]["content"]


def test_model_can_be_overridden_from_environment(monkeypatch) -> None:
    fixture = CASES["happy_paths"][1]
    monkeypatch.setenv("LLM_MODEL", "test-model")
    stub = StubLLM([json.dumps(fixture["concept"])])

    modal_app.call_llm(fixture["input"], client=stub)

    assert stub.completions.calls[0]["model"] == "test-model"


def test_prompt_is_hardened_and_based_on_image_plus_language_workflow() -> None:
    prompt = modal_app.load_prompt("concept.txt")
    assert "image + language" in prompt
    assert "15-second cinematic product ad" in prompt
    assert "Return EXACTLY this JSON object" in prompt
    assert '"prompt_text"' in prompt
    assert "no Markdown fences" in prompt
    assert "Never invent" in prompt


@pytest.mark.parametrize(
    ("aspect", "dimensions"),
    [("9:16", (576, 1024)), ("1:1", (1024, 1024)), ("16:9", (1024, 576))],
)
def test_mock_gpu_image_path_returns_three_aspect_correct_markers(
    aspect: str, dimensions: tuple[int, int]
) -> None:
    images = modal_app._mock_images_inside_container(
        "A sufficiently detailed product image generation prompt", aspect
    )

    assert len(images) == 3
    assert all("MOCK" in image["url"] for image in images)
    assert {(image["width"], image["height"]) for image in images} == {dimensions}
    assert {image["aspect"] for image in images} == {aspect}


def test_mock_gpu_image_path_is_deterministic() -> None:
    args = ("A sufficiently detailed product image generation prompt", "1:1")
    assert modal_app._mock_images_inside_container(*args) == (
        modal_app._mock_images_inside_container(*args)
    )


@pytest.mark.parametrize(
    ("prompt", "aspect"),
    [("short", "1:1"), ("A sufficiently detailed product prompt", "4:3")],
)
def test_mock_gpu_image_path_rejects_invalid_arguments(prompt: str, aspect: str) -> None:
    with pytest.raises(ValueError):
        modal_app._mock_images_inside_container(prompt, aspect)


def test_execute_workflow_uses_mocked_llm_and_gpu_without_accounts(monkeypatch) -> None:
    fixture = CASES["happy_paths"][2]
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    stub = StubLLM([json.dumps(fixture["concept"])])
    gpu_calls: list[tuple[str, str]] = []

    def gpu_stub(prompt_text: str, aspect: str) -> list[dict]:
        gpu_calls.append((prompt_text, aspect))
        return fixture["output"]["images"]

    response = modal_app.execute_workflow(
        fixture["input"], llm_client=stub, gpu_runner=gpu_stub
    )

    assert response == {
        "status": "completed",
        "result": fixture["output"],
        "usage": {
            "estimated_cost_usd": 0.22,
            "buyer_run_price_usd": 1.10,
        },
    }
    assert gpu_calls == [(fixture["concept"]["prompt_text"], "16:9")]


def test_execute_workflow_validates_gpu_output() -> None:
    fixture = CASES["happy_paths"][0]
    stub = StubLLM([json.dumps(fixture["concept"])])

    with pytest.raises(ValidationError):
        modal_app.execute_workflow(
            fixture["input"],
            llm_client=stub,
            gpu_runner=lambda _prompt, _aspect: [{"url": "not enough fields"}],
        )


def test_fastapi_surface_declares_only_post_run() -> None:
    web = modal_app.create_fastapi_app(StubLLM([]), lambda _prompt, _aspect: [])
    workflow_routes = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in web.routes
        if route.path.startswith("/v1/")
    }
    assert workflow_routes == {("/v1/run", ("POST",))}


def test_run_endpoint_returns_synchronous_completed_200_contract() -> None:
    fixture = CASES["happy_paths"][1]
    stub = StubLLM([json.dumps(fixture["concept"])])
    web = modal_app.create_fastapi_app(
        stub, lambda _prompt, _aspect: fixture["output"]["images"]
    )
    route = next(route for route in web.routes if route.path == "/v1/run")

    response = route.endpoint(fixture["input"])

    assert route.status_code == 200
    assert response["status"] == "completed"
    assert response["result"] == fixture["output"]
    assert response["usage"]["buyer_run_price_usd"] == 1.10


@pytest.mark.parametrize(
    "case", CASES["negative_cases"], ids=lambda case: case["id"]
)
def test_run_validates_input_before_llm_or_gpu(case: dict) -> None:
    from fastapi import HTTPException

    stub = StubLLM([])
    gpu_calls: list[tuple[str, str]] = []
    run = _run_endpoint(
        modal_app.create_fastapi_app(
            stub,
            lambda prompt, aspect: gpu_calls.append((prompt, aspect)) or [],
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        run(case["input"])

    assert exc_info.value.status_code == 422
    assert stub.completions.calls == []
    assert gpu_calls == []


def test_invalid_llm_output_returns_502_without_leaking_provider_body() -> None:
    from fastapi import HTTPException

    fixture = CASES["happy_paths"][0]
    run = _run_endpoint(
        modal_app.create_fastapi_app(
            StubLLM(["secret malformed provider body"]),
            lambda _prompt, _aspect: fixture["output"]["images"],
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        run(fixture["input"])

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Workflow returned an invalid result"
    assert "secret" not in exc_info.value.detail


def test_source_declares_real_a10g_function_and_day_3_model_todo() -> None:
    source = (ROOT / "modal_app.py").read_text(encoding="utf-8")
    assert 'gpu="A10G"' in source
    assert "def generate_images_gpu" in source
    assert "generate_images_gpu.remote" in source
    assert "TODO(Day 3)" in source
    assert "remote-image-API-only passthrough" in source


def test_source_uses_named_secret_and_protected_asgi_endpoint() -> None:
    source = (ROOT / "modal_app.py").read_text(encoding="utf-8")
    assert 'modal.Secret.from_name("cognition-gpt-image-seedance-ad")' in source
    assert "@modal.asgi_app(requires_proxy_auth=True)" in source
    assert "sk-" not in source
