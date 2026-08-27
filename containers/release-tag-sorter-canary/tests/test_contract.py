"""Offline contract tests for generated pure-data runtime release-tag-sorter-canary@1.0.0."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))


def _load_module():
    spec = importlib.util.spec_from_file_location("pure_data_modal_app", ROOT / "modal_app.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modal_app = _load_module()
INPUT_SCHEMA = json.loads((ROOT / "schemas" / "input.json").read_text(encoding="utf-8"))
OUTPUT_SCHEMA = json.loads((ROOT / "schemas" / "output.json").read_text(encoding="utf-8"))


def test_reviewed_fixture_executes_exactly() -> None:
    Draft202012Validator.check_schema(INPUT_SCHEMA)
    Draft202012Validator.check_schema(OUTPUT_SCHEMA)
    actual = modal_app.execute_workflow(CASES["happy_path"]["input"])
    assert actual == CASES["happy_path"]["output"]
    Draft202012Validator(OUTPUT_SCHEMA).validate(actual)


def test_negative_fixtures_fail_with_typed_reasons() -> None:
    for case in CASES["negative_cases"]:
        with pytest.raises(Exception) as error:
            modal_app.execute_workflow(case["input"])
        assert case["reason"] in str(error.value)


def test_runtime_has_no_dynamic_execution_or_external_effects() -> None:
    source = (ROOT / "modal_app.py").read_text(encoding="utf-8")
    assert "SKILL.md" not in source
    for forbidden in ("eval(", "exec(", "subprocess", "urllib", "requests", "modal.Secret"):
        assert forbidden not in source
    assert "@modal.asgi_app(requires_proxy_auth=True)" in source
