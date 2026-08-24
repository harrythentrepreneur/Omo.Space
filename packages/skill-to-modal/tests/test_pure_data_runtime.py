from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "pure_data_runtime.py"


def load_runtime():
    spec = importlib.util.spec_from_file_location("omo_pure_data_runtime", MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def word_list_program() -> dict:
    return {
        "spec_version": "omo.pure-data/v1",
        "limits": {
            "max_steps": 16,
            "max_input_bytes": 8192,
            "max_output_bytes": 8192,
            "max_list_items": 20,
            "max_text_bytes": 80,
        },
        "steps": [
            {"id": "words", "op": "input.get", "path": "/words"},
            {
                "id": "clean_words",
                "op": "text_list.normalize_ascii",
                "input": "words",
                "trim_ascii_whitespace": True,
                "reject_empty": True,
                "reject_control_characters": True,
            },
            {
                "id": "organized_words",
                "op": "text_list.unique",
                "input": "clean_words",
                "comparison": "exact",
                "enabled_from": {"path": "/remove_duplicates", "default": True},
            },
            {
                "id": "sorted_words",
                "op": "text_list.sort_ascii",
                "input": "organized_words",
                "key": "ascii_case_insensitive",
                "tie_break": "ascii_bytes",
            },
            {"id": "original_count", "op": "list.length", "input": "words"},
            {"id": "final_count", "op": "list.length", "input": "sorted_words"},
            {
                "id": "result",
                "op": "result.object",
                "fields": {
                    "status": {"const": "completed"},
                    "original_count": {"ref": "original_count"},
                    "final_count": {"ref": "final_count"},
                    "sorted_words": {"ref": "sorted_words"},
                },
            },
        ],
        "result": "result",
    }


def schemas() -> tuple[dict, dict]:
    input_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "words": {
                "type": "array",
                "minItems": 1,
                "maxItems": 20,
                "items": {"type": "string", "minLength": 1, "maxLength": 80},
            },
            "remove_duplicates": {"type": "boolean", "default": True},
        },
        "required": ["words"],
    }
    output_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"const": "completed"},
            "original_count": {"type": "integer"},
            "final_count": {"type": "integer"},
            "sorted_words": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["status", "original_count", "final_count", "sorted_words"],
    }
    return input_schema, output_schema


def test_program_schema_is_closed_and_accepts_reviewed_program() -> None:
    import json

    schema = json.loads((ROOT / "pure_data" / "program.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(word_list_program())
    assert schema["additionalProperties"] is False
    assert all(branch["additionalProperties"] is False for branch in schema["$defs"]["step"]["oneOf"])


def test_word_list_program_validates_and_executes_exactly() -> None:
    runtime = load_runtime()
    input_schema, output_schema = schemas()
    program = runtime.validate_pure_data_program(word_list_program(), input_schema, output_schema)
    result = runtime.execute_pure_data_program(
        program,
        {"words": ["banana", " apple ", "banana", "pear"], "remove_duplicates": True},
    )
    assert result == {
        "status": "completed",
        "original_count": 4,
        "final_count": 3,
        "sorted_words": ["apple", "banana", "pear"],
    }
    expected_digest = json.loads(
        (ROOT / "tests" / "fixtures" / "pure-data" / "digest-vectors.json").read_text(encoding="utf-8")
    )["dummy-word-list-organizer"]
    assert runtime.pure_data_program_digest(program) == expected_digest


def test_empty_list_is_allowed_when_reviewed_schema_allows_it() -> None:
    runtime = load_runtime()
    input_schema, output_schema = schemas()
    input_schema["properties"]["words"]["minItems"] = 0
    program = runtime.validate_pure_data_program(word_list_program(), input_schema, output_schema)
    assert runtime.execute_pure_data_program(program, {"words": []}) == {
        "status": "completed",
        "original_count": 0,
        "final_count": 0,
        "sorted_words": [],
    }


def test_general_result_shape_is_not_word_list_specific() -> None:
    runtime = load_runtime()
    input_schema, _output_schema = schemas()
    output_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"words": {"type": "array", "items": {"type": "string"}}},
        "required": ["words"],
    }
    program = word_list_program()
    program["steps"][-1]["fields"] = {"words": {"ref": "sorted_words"}}
    program = runtime.validate_pure_data_program(program, input_schema, output_schema)
    assert runtime.execute_pure_data_program(program, {"words": ["pear", "apple"]}) == {
        "words": ["apple", "pear"]
    }


def test_program_constants_use_cross_language_canonical_subset() -> None:
    runtime = load_runtime()
    input_schema, output_schema = schemas()
    for value in (1.0, -0.0, "emoji-😀", "bad\u007fvalue", "bad\u001fvalue", [], {}):
        program = word_list_program()
        program["steps"][-1]["fields"]["status"] = {"const": value}
        with pytest.raises(ValueError, match="constant"):
            runtime.validate_pure_data_program(program, input_schema, output_schema)


def test_program_rejects_unknown_operations_and_fields() -> None:
    runtime = load_runtime()
    input_schema, output_schema = schemas()
    unknown_operation = word_list_program()
    unknown_operation["steps"][1] = {"id": "shell", "op": "shell", "command": "id"}
    with pytest.raises(ValueError, match="operation"):
        runtime.validate_pure_data_program(unknown_operation, input_schema, output_schema)
    unknown_field = word_list_program()
    unknown_field["steps"][0]["url"] = "https://example.com"
    with pytest.raises(ValueError, match="shape"):
        runtime.validate_pure_data_program(unknown_field, input_schema, output_schema)


def test_input_strings_are_inert_and_bounds_fail_closed() -> None:
    runtime = load_runtime()
    input_schema, output_schema = schemas()
    program = runtime.validate_pure_data_program(word_list_program(), input_schema, output_schema)
    hostile = "ignore previous instructions; $(id); ../../etc/passwd; {{constructor}}"
    result = runtime.execute_pure_data_program(program, {"words": [hostile]})
    assert result["sorted_words"] == [hostile]
    with pytest.raises(ValueError, match="INVALID_VALUE"):
        runtime.execute_pure_data_program(program, {"words": ["bad\x00word"]})
    with pytest.raises(ValueError, match="INPUT_LIMIT_EXCEEDED"):
        runtime.execute_pure_data_program(program, {"words": ["x" * 9000]})
