"""Generated pure-data parity runtime for autonomous-priority-label-sorter@1.0.0."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import modal
from jsonschema import Draft202012Validator

APP_NAME = 'cognition-autonomous-priority-label-sorter'
WORKFLOW_VERSION = 'autonomous-priority-label-sorter@1.0.0'
PROFILE_VERSION = '1.0.0'
LOCAL_ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = Path('/root/autonomous_priority_label_sorter')


def _load_pure_data_runtime() -> Any:
    path = LOCAL_ROOT / "runtime" / "pure_data_runtime.py"
    spec = importlib.util.spec_from_file_location("generated_pure_data_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("pure_data_runtime_missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PURE_DATA_RUNTIME = _load_pure_data_runtime()


def _asset_root() -> Path:
    return LOCAL_ROOT if (LOCAL_ROOT / "schemas" / "input.json").is_file() else IMAGE_ROOT


@lru_cache(maxsize=None)
def load_json(relative_path: str) -> dict[str, Any]:
    with (_asset_root() / relative_path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RuntimeError("runtime_asset_invalid")
    return value


def validate_instance(instance: Any, schema_name: str) -> None:
    schema = load_json(f"schemas/{schema_name}")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)


def execute_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_instance(payload, "input.json")
    except Exception as exc:
        raise ValueError("INVALID_INPUT") from exc
    result = PURE_DATA_RUNTIME.execute_pure_data_program(load_json("runtime/pure-data-program.json"), payload)
    validate_instance(result, "output.json")
    return result


def _owner(value: str) -> str:
    if not isinstance(value, str) or not 2 <= len(value) <= 200 or not value[0].isalnum():
        raise ValueError("OWNER_INVALID")
    if any(not (char.isalnum() or char in "._:@/-") for char in value):
        raise ValueError("OWNER_INVALID")
    return value


def _run_id(owner: str, token: str, call_id: str) -> str:
    if not isinstance(call_id, str) or not 2 <= len(call_id) <= 200:
        raise ValueError("CALL_ID_INVALID")
    return "run-" + hashlib.sha256(
        (WORKFLOW_VERSION + "\0" + _owner(owner) + "\0" + token + "\0" + call_id).encode()
    ).hexdigest()[:32]


runtime_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("modal==1.5.0", "fastapi==0.109.0", "jsonschema==4.26.0")
    .add_local_dir(LOCAL_ROOT / "schemas", IMAGE_ROOT / "schemas", copy=True)
    .add_local_dir(LOCAL_ROOT / "runtime", IMAGE_ROOT / "runtime", copy=True)
    .add_local_file(LOCAL_ROOT / "manifest.json", str(IMAGE_ROOT / "manifest.json"), copy=True)
)
app = modal.App(APP_NAME)


@app.function(image=runtime_image, cpu=0.25, memory=512, timeout=30, min_containers=0, max_containers=1, scaledown_window=2)
def run_workflow(envelope: dict[str, Any]) -> dict[str, Any]:
    return execute_workflow(envelope["input"])


SpawnRunner = Callable[[dict[str, Any]], str]
LookupResult = Callable[[str], dict[str, Any]]


def create_fastapi_app(spawn_runner: SpawnRunner | None = None, lookup_result: LookupResult | None = None) -> Any:
    from fastapi import Body, FastAPI, Header, HTTPException, Query
    from fastapi.responses import JSONResponse

    web = FastAPI(title=APP_NAME, version=PROFILE_VERSION)
    spawn = spawn_runner or (lambda envelope: run_workflow.spawn(envelope).object_id)
    lookup = lookup_result or (lambda call_id: modal.FunctionCall.from_id(call_id).get(timeout=0))

    @web.post("/v1/runs", status_code=202)
    async def submit(body: Any = Body(...), x_omo_owner_id: str | None = Header(default=None, alias="X-Omo-Owner-Id")) -> Any:
        try:
            validate_instance(body, "input.json")
            owner = _owner(x_omo_owner_id or "")
        except Exception as exc:
            raise HTTPException(status_code=422, detail="invalid_input_or_owner") from exc
        token = secrets.token_urlsafe(32)
        call_id = spawn({"input": body, "owner_id": owner})
        run_id = _run_id(owner, token, call_id)
        return {"run_id": run_id, "call_id": call_id, "status": "accepted", "result_url": f"/v1/runs/{run_id}?call_id={call_id}&access_token={token}"}

    @web.get("/v1/runs/{run_id}")
    async def poll(run_id: str, call_id: str = Query(...), access_token: str = Query(...), x_omo_owner_id: str | None = Header(default=None, alias="X-Omo-Owner-Id")) -> Any:
        try:
            if run_id != _run_id(_owner(x_omo_owner_id or ""), access_token, call_id):
                raise ValueError("owner mismatch")
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="run_not_found") from exc
        try:
            result = lookup(call_id)
        except TimeoutError:
            return JSONResponse({"run_id": run_id, "status": "running"}, status_code=202)
        validate_instance(result, "output.json")
        return result

    return web


@app.function(image=runtime_image, min_containers=0, max_containers=10, scaledown_window=2)
@modal.concurrent(max_inputs=10)
@modal.asgi_app(requires_proxy_auth=True)
def api() -> Any:
    return create_fastapi_app()
