"""Trusted non-Turing-complete interpreter for reviewed pure-data workflows."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any


SPEC_VERSION = "omo.pure-data/v1"
STEP_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
FIELD_RE = STEP_ID_RE
ASCII_WHITESPACE = " \t\r\n\f\v"
LIMIT_KEYS = {
    "max_steps",
    "max_input_bytes",
    "max_output_bytes",
    "max_list_items",
    "max_text_bytes",
}
LIMIT_RANGES = {
    "max_steps": (1, 16),
    "max_input_bytes": (1, 65_536),
    "max_output_bytes": (1, 65_536),
    "max_list_items": (1, 100),
    "max_text_bytes": (1, 1_000),
}
STEP_SHAPES = {
    "input.get": {"id", "op", "path"},
    "text_list.normalize_ascii": {
        "id", "op", "input", "trim_ascii_whitespace", "reject_empty", "reject_control_characters"
    },
    "text_list.unique": {"id", "op", "input", "comparison", "enabled_from"},
    "text_list.sort_ascii": {"id", "op", "input", "key", "tie_break"},
    "list.length": {"id", "op", "input"},
    "result.object": {"id", "op", "fields"},
}


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValueError("NON_CANONICAL_VALUE") from exc


def canonical_pure_data_program(program: dict[str, Any]) -> str:
    return _canonical_bytes(program).decode("ascii")


def pure_data_program_digest(program: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(program)).hexdigest()


def _require_closed_schema(schema: Any, name: str) -> dict[str, Any]:
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError(f"{name} must be an object schema")
    if schema.get("additionalProperties") is not False:
        raise ValueError(f"{name} must reject unknown fields")
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise ValueError(f"{name} properties and required fields are mandatory")
    return schema


def _pointer_field(path: Any) -> str:
    if not isinstance(path, str) or not path.startswith("/") or path.count("/") != 1:
        raise ValueError("pure-data paths must name one top-level field")
    field = path[1:]
    if not FIELD_RE.fullmatch(field):
        raise ValueError("pure-data path field is invalid")
    return field


def _validate_limits(limits: Any) -> dict[str, int]:
    if not isinstance(limits, dict) or set(limits) != LIMIT_KEYS:
        raise ValueError("pure-data limits must use the closed v1 shape")
    result: dict[str, int] = {}
    for key, (minimum, maximum) in LIMIT_RANGES.items():
        value = limits.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise ValueError(f"pure-data limit {key} is invalid")
        result[key] = value
    return result


def validate_pure_data_program(
    program: dict[str, Any], input_schema: dict[str, Any], output_schema: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(program, dict) or set(program) != {"spec_version", "limits", "steps", "result"}:
        raise ValueError("pure-data program must use the closed v1 shape")
    if program.get("spec_version") != SPEC_VERSION:
        raise ValueError("pure-data spec version is unsupported")
    input_contract = _require_closed_schema(input_schema, "input_schema")
    output_contract = _require_closed_schema(output_schema, "output_schema")
    limits = _validate_limits(program.get("limits"))
    steps = program.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= limits["max_steps"]:
        raise ValueError("pure-data steps exceed the reviewed bound")
    seen: dict[str, str] = {}
    result_fields: set[str] | None = None
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError("pure-data step must be an object")
        operation = step.get("op")
        if operation not in STEP_SHAPES:
            raise ValueError("pure-data operation is unsupported")
        if set(step) != STEP_SHAPES[operation]:
            raise ValueError("pure-data step shape is invalid")
        step_id = step.get("id")
        if not isinstance(step_id, str) or not STEP_ID_RE.fullmatch(step_id) or step_id in seen:
            raise ValueError("pure-data step id is invalid")
        if operation == "input.get":
            field = _pointer_field(step["path"])
            properties = input_contract["properties"]
            field_schema = properties.get(field)
            if field not in input_contract["required"] or not isinstance(field_schema, dict):
                raise ValueError("input.get must reference a required input field")
            seen[step_id] = "text_list" if field_schema.get("type") == "array" else "unknown"
        elif operation == "text_list.normalize_ascii":
            if seen.get(step["input"]) != "text_list":
                raise ValueError("normalize operation input reference is invalid")
            if any(step[key] is not True for key in (
                "trim_ascii_whitespace", "reject_empty", "reject_control_characters"
            )):
                raise ValueError("normalize operation policy must use safe v1 settings")
            seen[step_id] = "text_list"
        elif operation == "text_list.unique":
            if seen.get(step["input"]) != "text_list" or step.get("comparison") != "exact":
                raise ValueError("unique operation is invalid")
            condition = step.get("enabled_from")
            if not isinstance(condition, dict) or set(condition) != {"path", "default"}:
                raise ValueError("unique condition shape is invalid")
            field = _pointer_field(condition["path"])
            condition_schema = input_contract["properties"].get(field)
            if not isinstance(condition.get("default"), bool) or not isinstance(condition_schema, dict) or condition_schema.get("type") != "boolean":
                raise ValueError("unique condition must reference a boolean input")
            seen[step_id] = "text_list"
        elif operation == "text_list.sort_ascii":
            if (
                seen.get(step["input"]) != "text_list"
                or step.get("key") != "ascii_case_insensitive"
                or step.get("tie_break") != "ascii_bytes"
            ):
                raise ValueError("sort operation is invalid")
            seen[step_id] = "text_list"
        elif operation == "list.length":
            if seen.get(step["input"]) != "text_list":
                raise ValueError("length operation input reference is invalid")
            seen[step_id] = "integer"
        else:
            if index != len(steps) - 1:
                raise ValueError("result.object must be the final step")
            fields = step.get("fields")
            output_properties = output_contract["properties"]
            if not isinstance(fields, dict) or set(fields) != set(output_properties) or len(fields) > 32:
                raise ValueError("result.object fields must match output schema")
            for field, descriptor in fields.items():
                if not FIELD_RE.fullmatch(field) or not isinstance(descriptor, dict) or len(descriptor) != 1:
                    raise ValueError("result.object field shape is invalid")
                if "ref" in descriptor:
                    reference = descriptor["ref"]
                    if not isinstance(reference, str) or reference not in seen:
                        raise ValueError("result.object reference is invalid")
                elif "const" in descriptor:
                    value = descriptor["const"]
                    valid_constant = (
                        value is None
                        or isinstance(value, bool)
                        or (
                            isinstance(value, int)
                            and not isinstance(value, bool)
                            and abs(value) <= 9_007_199_254_740_991
                        )
                        or (
                            isinstance(value, str)
                            and all(32 <= ord(char) <= 126 for char in value)
                            and len(value.encode("ascii")) <= 200
                        )
                    )
                    if not valid_constant:
                        raise ValueError("result.object constant is invalid")
                else:
                    raise ValueError("result.object field source is invalid")
            seen[step_id] = "object"
            result_fields = set(fields)
    result_id = program.get("result")
    if not isinstance(result_id, str) or seen.get(result_id) != "object" or result_id != steps[-1]["id"]:
        raise ValueError("pure-data result reference is invalid")
    if result_fields != set(output_contract["required"]):
        raise ValueError("pure-data output schema must require every result field")
    return copy.deepcopy(program)


def _ascii_text_list(value: Any, limits: dict[str, int]) -> list[str]:
    if not isinstance(value, list) or not 0 <= len(value) <= limits["max_list_items"]:
        raise ValueError("INVALID_INPUT")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("INVALID_INPUT")
        try:
            encoded = item.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("INVALID_VALUE") from exc
        if len(encoded) > limits["max_text_bytes"]:
            raise ValueError("INVALID_VALUE")
        result.append(item)
    return result


def execute_pure_data_program(program: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    limits = _validate_limits(program.get("limits"))
    if not isinstance(payload, dict):
        raise ValueError("INVALID_INPUT")
    if len(_canonical_bytes(payload)) > limits["max_input_bytes"]:
        raise ValueError("INPUT_LIMIT_EXCEEDED")
    values: dict[str, Any] = {}
    for step in program["steps"]:
        operation = step["op"]
        if operation == "input.get":
            field = _pointer_field(step["path"])
            values[step["id"]] = _ascii_text_list(payload.get(field), limits)
        elif operation == "text_list.normalize_ascii":
            normalized = [item.strip(ASCII_WHITESPACE) for item in values[step["input"]]]
            if any(not item or any(ord(char) < 32 or ord(char) == 127 for char in item) for item in normalized):
                raise ValueError("INVALID_VALUE")
            values[step["id"]] = normalized
        elif operation == "text_list.unique":
            condition = step["enabled_from"]
            enabled = payload.get(_pointer_field(condition["path"]), condition["default"])
            if not isinstance(enabled, bool):
                raise ValueError("INVALID_INPUT")
            source = values[step["input"]]
            values[step["id"]] = list(dict.fromkeys(source)) if enabled else list(source)
        elif operation == "text_list.sort_ascii":
            source = values[step["input"]]
            values[step["id"]] = sorted(source, key=lambda item: (item.lower().encode("ascii"), item.encode("ascii")))
        elif operation == "list.length":
            values[step["id"]] = len(values[step["input"]])
        elif operation == "result.object":
            result: dict[str, Any] = {}
            for field, descriptor in step["fields"].items():
                result[field] = descriptor["const"] if "const" in descriptor else copy.deepcopy(values[descriptor["ref"]])
            values[step["id"]] = result
        else:
            raise ValueError("PROGRAM_OPERATION_INVALID")
    output = values[program["result"]]
    if not isinstance(output, dict) or len(_canonical_bytes(output)) > limits["max_output_bytes"]:
        raise ValueError("OUTPUT_LIMIT_EXCEEDED")
    return copy.deepcopy(output)
