"""Offline contract tests for the deterministic SKILL.md loader."""

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
        "skill_md_to_hosted_workflow_modal_app", ROOT / "modal_app.py"
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


def test_schema_documents_and_profile_fixture_are_valid() -> None:
    Draft202012Validator.check_schema(INPUT_SCHEMA)
    Draft202012Validator.check_schema(OUTPUT_SCHEMA)
    Draft202012Validator(INPUT_SCHEMA).validate(CASES["happy_path"]["input"])
    Draft202012Validator(OUTPUT_SCHEMA).validate(CASES["happy_path"]["output"])


@pytest.mark.parametrize("case", CASES["negative_cases"], ids=lambda case: case["id"])
def test_invalid_requests_fail_input_schema(case: dict) -> None:
    assert list(Draft202012Validator(INPUT_SCHEMA).iter_errors(case["input"])), case["reason"]


def test_real_small_skill_compiles_and_prices_without_provider_calls() -> None:
    result = modal_app.execute_loader(CASES["happy_path"]["input"], run_id="run-" + "1" * 32)
    Draft202012Validator(OUTPUT_SCHEMA).validate(result)
    assert result["spec_version"] == "omo.result/v1"
    assert result["data"]["status"] == "ready"
    assert result["data"]["slug"] == "tiny-uppercase-helper"
    assert result["data"]["price_usd"] == 0.1
    assert result["data"]["chargeable"] is True
    assert result["data"]["manifest"]["readiness"]["can_submit"] is True
    assert result["data"]["test_summary"]["passed"] == 5
    assert result["data"]["test_summary"]["provider_calls"] == 0
    assert result["usage"]["provider_calls"] == 0
    assert result["usage"]["estimated_cost_usd"] == 0


def test_unknown_cost_is_typed_and_not_chargeable() -> None:
    payload = json.loads(json.dumps(CASES["happy_path"]["input"]))
    payload["options"]["model"] = "unknown-unpriced-model"
    result = modal_app.execute_loader(payload, run_id="run-" + "2" * 32)
    assert result["data"]["status"] == "blocked"
    assert result["data"]["price_usd"] is None
    assert result["data"]["chargeable"] is False
    assert [item["code"] for item in result["data"]["blockers"]] == ["COST_UNKNOWN"]


def test_credential_pattern_fails_before_compile_without_echo() -> None:
    payload = json.loads(json.dumps(CASES["happy_path"]["input"]))
    secret_value = "sk-" + "x" * 24
    payload["skill_md"] += "\npassword: " + secret_value
    result = modal_app.execute_loader(payload, run_id="run-" + "3" * 32)
    rendered = json.dumps(result)
    assert result["data"]["blockers"][0]["code"] == "CREDENTIAL_PATTERN"
    assert secret_value not in rendered


def test_missing_contract_is_a_typed_blocker() -> None:
    result = modal_app.execute_loader(
        {"skill_md": "---\nname: incomplete\ndescription: Missing machine contract.\n---\n\n## Workflow\n\n1. **Run:** Return data.\n"},
        run_id="run-" + "4" * 32,
    )
    assert result["data"]["status"] == "blocked"
    assert result["data"]["blockers"][0]["code"] == "CONTRACT_INCOMPLETE"


def test_submit_requires_owner_with_401_and_returns_owner_scoped_202() -> None:
    observed = []
    web = modal_app.create_fastapi_app(
        spawn_runner=lambda envelope: observed.append(envelope) or "fc-loader-test"
    )
    submit = _route(web, "/v1/runs").endpoint
    with pytest.raises(Exception) as exc_info:
        asyncio.run(submit(CASES["happy_path"]["input"], None))
    assert getattr(exc_info.value, "status_code", None) == 401
    accepted = asyncio.run(submit(CASES["happy_path"]["input"], "owner-test"))
    assert accepted["status"] == "accepted"
    assert accepted["call_id"] == "fc-loader-test"
    assert accepted["result_url"].startswith(f"/v1/runs/{accepted['run_id']}?call_id=fc-loader-test&access_token=")
    assert "/status?" in accepted["status_url"]
    assert "/result?" in accepted["separate_result_url"]
    assert observed[0]["owner_id"] == "owner-test"


def test_result_poll_is_bound_to_owner_and_returns_omo_envelope() -> None:
    owner = "owner-test"
    token = "t" * 43
    run_id = modal_app.run_id_for(owner, token)
    result = modal_app.execute_loader(CASES["happy_path"]["input"], run_id=run_id)
    web = modal_app.create_fastapi_app(lookup_result=lambda _call_id: result)
    poll = _route(web, "/v1/runs/{run_id}").endpoint
    completed = asyncio.run(poll(run_id, "fc-loader-test", token, owner))
    assert completed["spec_version"] == "omo.result/v1"
    assert completed["run_id"] == run_id
    with pytest.raises(Exception) as exc_info:
        asyncio.run(poll(run_id, "fc-loader-test", token, "owner-other"))
    assert getattr(exc_info.value, "status_code", None) == 404


def test_modal_surface_is_proxy_protected_and_has_no_secret_binding() -> None:
    source = (ROOT / "modal_app.py").read_text(encoding="utf-8")
    assert "@modal.asgi_app(requires_proxy_auth=True)" in source
    assert "modal.Secret" not in source
    assert ".add_local_file(" in source
    assert "cost-model.mjs" in source
    image_repository = Path("/root/skill_md_to_hosted_workflow/repository")
    assert modal_app._runtime_repository_root(Path("/root"), image_repository) == image_repository
