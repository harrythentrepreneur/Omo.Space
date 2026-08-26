from __future__ import annotations

import copy
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
SCHEMA_ROOT = ROOT / "workflow-ir"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SCHEMA_KEYWORDS = {
    "$id", "$schema", "additionalProperties", "const", "default", "description", "enum",
    "examples", "items", "maxItems", "maxLength", "maximum", "minItems", "minLength",
    "minimum", "oneOf", "properties", "required", "title", "type",
}


class IRValidationError:
    __slots__ = ("code", "pointer")

    def __init__(self, code: str, pointer: str = "/") -> None:
        self.code = code
        self.pointer = pointer

    def __eq__(self, other: object) -> bool:
        return isinstance(other, IRValidationError) and (self.code, self.pointer) == (other.code, other.pointer)

    def __repr__(self) -> str:
        return f"IRValidationError(code={self.code!r}, pointer={self.pointer!r})"


class IRCompileResult:
    __slots__ = ("profile", "errors", "terminal_reason")

    def __init__(
        self,
        profile: dict[str, Any] | None,
        errors: tuple[IRValidationError, ...],
        terminal_reason: str | None = None,
    ) -> None:
        self.profile = profile
        self.errors = errors
        self.terminal_reason = terminal_reason

    @property
    def ok(self) -> bool:
        return self.profile is not None and not self.errors


def _error(
    code: str, pointer: str = "/", *, terminal_reason: str | None = None,
) -> IRCompileResult:
    return IRCompileResult(None, (IRValidationError(code, pointer),), terminal_reason)


def _pointer(path: Any) -> str:
    parts = []
    for item in path:
        text = str(item).replace("~", "~0").replace("/", "~1")
        parts.append(text)
    return "/" + "/".join(parts) if parts else "/"


def _all_json_values_safe(value: Any, *, depth: int = 0) -> bool:
    if depth > 20:
        return False
    if value is None or isinstance(value, (str, bool)):
        return True
    if isinstance(value, int):
        return abs(value) <= 1_000_000_000
    if isinstance(value, float):
        return math.isfinite(value) and abs(value) <= 1_000_000_000
    if isinstance(value, list):
        return len(value) <= 500 and all(_all_json_values_safe(item, depth=depth + 1) for item in value)
    if isinstance(value, dict):
        return len(value) <= 500 and all(
            isinstance(key, str) and len(key) <= 256 and _all_json_values_safe(item, depth=depth + 1)
            for key, item in value.items()
        )
    return False


def _schema_is_bounded(value: Any, *, depth: int = 0) -> bool:
    if depth > 12 or not isinstance(value, dict) or len(value) > 100:
        return False
    for key, item in value.items():
        if key not in SCHEMA_KEYWORDS:
            return False
        if key == "properties":
            if not isinstance(item, dict) or len(item) > 40:
                return False
            if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", str(name)) for name in item):
                return False
            if any(not _schema_is_bounded(child, depth=depth + 1) for child in item.values()):
                return False
        elif key == "items" and isinstance(item, dict):
            if not _schema_is_bounded(item, depth=depth + 1):
                return False
        elif key == "oneOf":
            if not isinstance(item, list) or not 1 <= len(item) <= 8:
                return False
            if any(not _schema_is_bounded(child, depth=depth + 1) for child in item):
                return False
    try:
        Draft202012Validator.check_schema(value)
    except Exception:
        return False
    if depth == 0:
        return value.get("type") == "object" and value.get("additionalProperties") is False
    return True


def _load_pure_data_runtime() -> Any:
    path = ROOT / "pure_data_runtime.py"
    spec = importlib.util.spec_from_file_location("omo_workflow_ir_pure_data_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("runtime unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate_ir(value: Any, schema_name: str) -> tuple[IRValidationError, ...]:
    if not _all_json_values_safe(value):
        return (IRValidationError("IR_VALUE_UNSAFE"),)
    schema = json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.absolute_path))
    if not errors:
        return ()
    first = errors[0]
    if first.validator == "additionalProperties":
        code = "IR_FORBIDDEN_FIELD"
    elif first.validator == "required":
        code = "IR_REQUIRED_FIELD"
    elif first.validator == "type":
        code = "IR_FIELD_TYPE"
    else:
        code = "IR_FIELD_VALUE"
    return (IRValidationError(code, _pointer(first.absolute_path)),)


def _marketplace(slug: str, name: str, description: str, promise: str, category: str, form: list[dict[str, str]]) -> dict[str, Any]:
    env_name = slug.replace("-", "_").upper() + "_MODAL_URL"
    fields = {item["field"]: {"widget": item["widget"]} for item in form}
    return {
        "catalog_managed": True,
        "storefront_visible": True,
        "category": category,
        "cover": None,
        "demo_cap": "Bounded compiler-owned workflow runtime",
        "deployment": {
            "default_endpoint": f"https://omo-space--cognition-{slug}-api.modal.run",
            "endpoint_env": env_name,
        },
        "description": description,
        "emoji": "⚙️",
        "example_in": "See the validated example input.",
        "example_out": ["Schema-validated result"],
        "examples": [],
        "free": False,
        "inputs": [item["field"] for item in form],
        "maker": "Omo",
        "maker_name": "Omo Studio",
        "niche": category,
        "outputs": ["Schema-validated result"],
        "phases": [{"id": "running", "label": "Running"}, {"id": "delivered", "label": "Delivered"}],
        "price_maintain": 0,
        "price_own": 0,
        "promise": promise,
        "runtime_preference": "auto",
        "slug": slug,
        "tags": [category, "compiler-owned"],
        "title": name,
        "ui": {"fields": fields, "order": [item["field"] for item in form]},
        "upvotes": 0,
        "version": "v1.0.0",
    }


def _workflow_contract_error(value: dict[str, Any], input_schema: dict[str, Any]) -> IRCompileResult | None:
    properties = input_schema.get("properties")
    if not isinstance(properties, dict):
        return _error("IR_SCHEMA_UNSAFE", "/input_schema")
    form_fields = [item.get("field") for item in value["form"]]
    if len(set(form_fields)) != len(form_fields) or set(form_fields) != set(properties):
        return _error("IR_FORM_INVALID", "/form")
    validator = Draft202012Validator(input_schema)
    for index, case in enumerate(value["negative_cases"]):
        try:
            accepted = not list(validator.iter_errors(case["input"]))
        except Exception:
            return _error("IR_NEGATIVE_CASE_INVALID", f"/negative_cases/{index}/input")
        if accepted:
            return _error("IR_NEGATIVE_CASE_INVALID", f"/negative_cases/{index}/input")
    return None


def _compile_pure_data(value: dict[str, Any], slug: str, name: str, source_sha256: str) -> IRCompileResult:
    input_schema = value["input_schema"]
    output_schema = value["output_schema"]
    if not _schema_is_bounded(input_schema) or not _schema_is_bounded(output_schema):
        return _error("IR_SCHEMA_UNSAFE")
    contract_error = _workflow_contract_error(value, input_schema)
    if contract_error is not None:
        return contract_error
    try:
        runtime = _load_pure_data_runtime()
        steps = value["program"].get("steps") if isinstance(value["program"], dict) else None
        if isinstance(steps, list) and any(
            isinstance(step, dict) and step.get("op") not in runtime.STEP_SHAPES
            for step in steps
        ):
            return _error("IR_OPERATION_UNSUPPORTED", "/program")
        program = runtime.validate_pure_data_program(value["program"], input_schema, output_schema)
    except Exception:
        return _error("IR_PROGRAM_INVALID", "/program")
    try:
        Draft202012Validator(input_schema).validate(value["happy_path"]["input"])
        Draft202012Validator(output_schema).validate(value["happy_path"]["output"])
    except Exception:
        return _error("IR_EXAMPLE_INVALID", "/happy_path")
    profile = {
        "apt_packages": [], "artifacts": [], "capabilities": [],
        "cost_drivers": ["bounded deterministic CPU"],
        "execution_kind": "pure_data",
        "form": copy.deepcopy(value["form"]),
        "happy_path": copy.deepcopy(value["happy_path"]),
        "input_schema": copy.deepcopy(input_schema),
        "inputs": [item["field"] for item in value["form"]],
        "marketplace": _marketplace(slug, name, value["description"], value["promise"], value["category"], value["form"]),
        "name": name,
        "negative_cases": copy.deepcopy(value["negative_cases"]),
        "output_schema": copy.deepcopy(output_schema),
        "outputs": ["schema-validated result"],
        "pricing": {
            "chargeable": True, "default_tier": "deterministic",
            "estimates": [{
                "guard_cost_usd": 0.02, "notes": ["zero provider calls"],
                "tier": "deterministic", "workflow": {"steps": []},
            }],
            "quote_status": "reviewed_deterministic", "unpriced_costs": [],
        },
        "prompts": {},
        "pure_data_program": program,
        "readiness": {"can_submit": True, "blockers": []},
        "required_env_names": [],
        "resources": {"cpu": 0.25, "memory_mb": 512, "timeout_seconds": 30, "max_containers": 1},
        "reviewed_source_sha256": source_sha256,
        "runtime_preference": "auto",
        "slug": slug,
        "steps": [{"id": "execute", "operation": "pure_data.execute", "readiness": "ready", "type": "native"}],
        "version": "1.0.0",
    }
    return IRCompileResult(profile, ())


def _single_llm_output_schema(model_schema: dict[str, Any], slug: str) -> dict[str, Any]:
    schema = copy.deepcopy(model_schema)
    properties = schema["properties"]
    properties.update({
        "run_id": {"type": "string", "minLength": 8},
        "status": {"const": "completed"},
        "workflow_version": {"const": f"{slug}@1.0.0"},
        "usage": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "provider": {"const": "opencode-go"},
                "model": {"type": "string", "minLength": 1},
                "llm_calls": {"const": 1},
                "prompt_tokens": {"type": "integer", "minimum": 0},
                "completion_tokens": {"type": "integer", "minimum": 0},
                "estimated_cost_usd": {"type": "number", "minimum": 0},
            },
            "required": [
                "provider", "model", "llm_calls", "prompt_tokens",
                "completion_tokens", "estimated_cost_usd",
            ],
        },
    })
    schema["required"] = list(schema["required"]) + ["run_id", "status", "workflow_version", "usage"]
    return schema


def _compile_single_llm(value: dict[str, Any], slug: str, name: str, source_sha256: str) -> IRCompileResult:
    input_schema = value["input_schema"]
    model_schema = value["model_output_schema"]
    if not _schema_is_bounded(input_schema) or not _schema_is_bounded(model_schema):
        return _error("IR_SCHEMA_UNSAFE")
    contract_error = _workflow_contract_error(value, input_schema)
    if contract_error is not None:
        return contract_error
    if not isinstance(model_schema.get("properties"), dict) or not isinstance(model_schema.get("required"), list):
        return _error("IR_SCHEMA_UNSAFE", "/model_output_schema")
    reserved = {"run_id", "status", "workflow_version", "usage"}
    if reserved.intersection(model_schema["properties"]):
        return _error("IR_RESERVED_OUTPUT_FIELD", "/model_output_schema/properties")
    try:
        Draft202012Validator(input_schema).validate(value["happy_path"]["input"])
        Draft202012Validator(model_schema).validate(value["happy_path"]["output"])
    except Exception:
        return _error("IR_EXAMPLE_INVALID", "/happy_path")
    output_schema = _single_llm_output_schema(model_schema, slug)
    happy_output = copy.deepcopy(value["happy_path"]["output"])
    happy_output.update({
        "run_id": f"run-fixture-{slug}",
        "status": "completed",
        "workflow_version": f"{slug}@1.0.0",
        "usage": {
            "provider": "opencode-go", "model": "deepseek-v4-flash", "llm_calls": 1,
            "prompt_tokens": 800, "completion_tokens": 400, "estimated_cost_usd": 0.0003,
        },
    })
    profile = {
        "apt_packages": [], "artifacts": [],
        "capabilities": ["opencode-go-chat-completions", "schema-validated-json-output"],
        "cost_drivers": ["one bounded compiler-owned schema-validated model call"],
        "execution_kind": "single_llm",
        "form": copy.deepcopy(value["form"]),
        "happy_path": {"input": copy.deepcopy(value["happy_path"]["input"]), "output": happy_output},
        "input_schema": copy.deepcopy(input_schema),
        "inputs": [item["field"] for item in value["form"]],
        "live": {
            "api_key_env": "LLM_API_KEY", "base_url_env": "LLM_BASE_URL",
            "default_base_url": "https://opencode.ai/zen/go/v1",
            "default_model": "deepseek-v4-flash", "max_tokens": 1600,
            "modal_secret_name": "omo-skill-providers", "model_env": "LLM_MODEL",
            "model_output_schema": copy.deepcopy(model_schema), "prompt": "run.txt",
            "provider": "opencode-go", "temperature": 0.2, "timeout_seconds": 120,
        },
        "marketplace": _marketplace(slug, name, value["description"], value["promise"], value["category"], value["form"]),
        "name": name,
        "negative_cases": copy.deepcopy(value["negative_cases"]),
        "output_schema": output_schema,
        "outputs": ["schema-validated result"],
        "pricing": {
            "chargeable": True, "default_tier": "standard",
            "estimates": [{
                "notes": ["one bounded compiler-owned model call"], "tier": "standard",
                "workflow": {"steps": [{
                    "estimated_input_tokens": 1100, "max_output_tokens": 1600,
                    "model": "deepseek-v4-flash", "role": "generate", "type": "llm",
                }]},
            }],
            "quote_status": "cost_model", "unpriced_costs": [],
        },
        "prompts": {"run.txt": value["prompt"]},
        "readiness": {"can_submit": True, "blockers": []},
        "required_env_names": ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"],
        "resources": {"cpu": 1.0, "memory_mb": 512, "timeout_seconds": 180, "max_containers": 4},
        "reviewed_source_sha256": source_sha256,
        "runtime_preference": "auto",
        "slug": slug,
        "steps": [{
            "id": "generate", "operation": "chat.completions.strict_json", "prompt": "run.txt",
            "provider": "opencode-go", "readiness": "ready", "type": "llm",
        }],
        "version": "1.0.0",
    }
    return IRCompileResult(profile, ())


def safe_ir_feedback(result: IRCompileResult) -> dict[str, Any]:
    """Return only fixed typed fields safe to feed back to an authoring model."""
    allowed = {
        "IR_EXAMPLE_INVALID", "IR_FIELD_TYPE", "IR_FIELD_VALUE", "IR_FORBIDDEN_FIELD", "IR_FORM_INVALID",
        "IR_JSON_INVALID", "IR_NEGATIVE_CASE_INVALID", "IR_PROGRAM_INVALID", "IR_REQUIRED_FIELD", "IR_RESERVED_OUTPUT_FIELD", "IR_ROOT_TYPE",
        "IR_SCHEMA_UNSAFE", "IR_VALUE_UNSAFE", "IR_FAMILY_UNSUPPORTED",
        "IR_OPERATION_UNSUPPORTED", "IR_CAPABILITY_UNSUPPORTED",
    }
    errors = [
        {"code": item.code, "pointer": item.pointer}
        for item in result.errors
        if item.code in allowed and re.fullmatch(r"/(?:[A-Za-z0-9_~.-]+/)*[A-Za-z0-9_~.-]*", item.pointer)
    ][:8]
    terminal = any(
        item["code"] in {
            "IR_FAMILY_UNSUPPORTED", "IR_OPERATION_UNSUPPORTED", "IR_CAPABILITY_UNSUPPORTED",
        }
        for item in errors
    )
    return {
        "terminal": terminal,
        "reason": (result.terminal_reason or "unsupported_capability") if terminal else "workflow_ir_validation_failed",
        "errors": errors or [{"code": "IR_JSON_INVALID", "pointer": "/"}],
    }


def compile_workflow_ir(raw: Any, *, slug: Any, name: Any, source_sha256: Any) -> IRCompileResult:
    if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
        return _error("IR_IDENTITY_INVALID", "/slug")
    if not isinstance(name, str) or not name.strip() or len(name) > 160:
        return _error("IR_IDENTITY_INVALID", "/name")
    if not isinstance(source_sha256, str) or not SHA256_RE.fullmatch(source_sha256):
        return _error("IR_IDENTITY_INVALID", "/source_sha256")
    if not isinstance(raw, str) or len(raw.encode("utf-8", errors="ignore")) > 256 * 1024:
        return _error("IR_JSON_INVALID")
    try:
        value = json.loads(raw, parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, json.JSONDecodeError, ValueError, TypeError):
        return _error("IR_JSON_INVALID")
    if not isinstance(value, dict):
        return _error("IR_ROOT_TYPE")
    version = value.get("schema_version")
    schemas = {
        "omo.workflow-ir/pure-data-v1": "pure-data-v1.schema.json",
        "omo.workflow-ir/single-llm-v1": "single-llm-v1.schema.json",
        "omo.workflow-ir/unsupported-v1": "unsupported-v1.schema.json",
    }
    if version not in schemas:
        return _error("IR_FAMILY_UNSUPPORTED", "/schema_version")
    errors = _validate_ir(value, schemas[version])
    if errors:
        return IRCompileResult(None, errors)
    if version == "omo.workflow-ir/unsupported-v1":
        capability = value["missing_capability"]
        return _error(
            "IR_CAPABILITY_UNSUPPORTED", "/missing_capability",
            terminal_reason=f"unsupported_capability:{capability}",
        )
    if version == "omo.workflow-ir/pure-data-v1":
        return _compile_pure_data(value, slug, name, source_sha256)
    return _compile_single_llm(value, slug, name, source_sha256)
