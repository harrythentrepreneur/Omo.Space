"""Modal/FastAPI Day-1 canary for the Cognition UGC HeyGen workflow.

Runtime pins (tested locally): modal==1.5.0, fastapi==0.109.0,
pydantic==2.13.3, openai==2.36.0, jsonschema==4.26.0.
Test pin: pytest==8.4.0.
"""

from __future__ import annotations

import json
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import modal
from jsonschema import Draft202012Validator


APP_NAME = "cognition-ugc-heygen"
WORKFLOW_VERSION = "ugc-heygen@0.1.0"
DEFAULT_LLM_BASE_URL = "https://opencode.ai/zen/go/v1"
DEFAULT_LLM_MODEL = "deepseek-v4-flash"
RENDER_VIDEO = False
CANARY_NOTE = (
    "Video rendering is disabled in the Day-1 canary (render_video=false)."
)

LOCAL_ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = Path("/root/ugc_heygen")


def _asset_root() -> Path:
    """Use checked-in assets locally and copied assets inside the Modal image."""
    if (LOCAL_ROOT / "schemas" / "input.json").is_file():
        return LOCAL_ROOT
    return IMAGE_ROOT


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    path = _asset_root() / "schemas" / name
    with path.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return schema


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    return (_asset_root() / "prompts" / name).read_text(encoding="utf-8").strip()


def validate_instance(instance: Any, schema_name: str) -> None:
    """Fail closed against a canonical checked-in Draft 2020-12 schema."""
    Draft202012Validator(load_schema(schema_name)).validate(instance)


def parse_llm_json(raw: str, schema_name: str) -> dict[str, Any]:
    """Recover one JSON object from optional fences/prose and validate exactly.

    Validation does not normalize, drop, or invent fields. In particular,
    additional properties are rejected by the output schemas.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("LLM response must be a non-empty string")

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        closing_fence = cleaned.rfind("```")
        if first_newline < 0 or closing_fence <= first_newline:
            raise ValueError("LLM returned an incomplete JSON fence")
        cleaned = cleaned[first_newline + 1 : closing_fence].strip()

    decoder = json.JSONDecoder()
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("LLM did not return a JSON object")

    try:
        value, _ = decoder.raw_decode(cleaned[start:])
    except json.JSONDecodeError as exc:
        raise ValueError("LLM returned malformed JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("LLM output is not a JSON object")

    validate_instance(value, schema_name)
    return value


def _new_openai_client() -> Any:
    """Construct the provider client lazily so imports never require keys."""
    from openai import OpenAI

    return OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
    )


def call_llm(
    *,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    output_schema: str,
    client: Any | None = None,
) -> dict[str, Any]:
    """Call an OpenAI-compatible chat-completions endpoint and parse JSON."""
    llm = client if client is not None else _new_openai_client()
    response = llm.chat.completions.create(
        model=os.environ.get("LLM_MODEL", DEFAULT_LLM_MODEL),
        temperature=0.2,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content
    return parse_llm_json(raw, output_schema)


def execute_canary(
    payload: dict[str, Any],
    *,
    llm_client: Any | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute only the script and captions steps; never call HeyGen."""
    validate_instance(payload, "input.json")
    current_run_id = run_id or str(uuid.uuid4())

    script_user = (
        f"Product description: {payload['product_description']}\n\n"
        f"Brand voice: {payload['brand_voice']}\n"
        f"Target length: {payload['length_seconds']} seconds\n\n"
        "Write the UGC ad script now."
    )
    script = call_llm(
        system_prompt=load_prompt("script.txt"),
        user_prompt=script_user,
        max_tokens=700,
        output_schema="script.json",
        client=llm_client,
    )

    captions_user = "Script JSON:\n" + json.dumps(script, ensure_ascii=False)
    captions_object = call_llm(
        system_prompt=load_prompt("captions.txt"),
        user_prompt=captions_user,
        max_tokens=300,
        output_schema="captions.json",
        client=llm_client,
    )
    captions = captions_object["captions"]
    if len(captions) != len(script["lines"]):
        raise ValueError("captions must have the same length as script.lines")

    if RENDER_VIDEO:
        raise RuntimeError("render_video=true is unavailable in the Day-1 canary")

    # TODO(Day 3): implement one idempotent HeyGen POST /v3/videos mutation,
    # followed by GET /v3/videos/{video_id} polling. Keep this disabled until
    # the paid adapter, durable state, and failure normalization are reviewed.
    result = {
        "run_id": current_run_id,
        "status": "completed",
        "workflow_version": WORKFLOW_VERSION,
        "script": script,
        "captions": captions,
        "video": None,
        "usage": {
            "estimated_cost_usd": 0.00045,
            "buyer_run_price_usd": 0.10,
        },
        "note": CANARY_NOTE,
    }
    validate_instance(result, "output.json")
    return result


runtime_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "modal==1.5.0",
        "fastapi==0.109.0",
        "pydantic==2.13.3",
        "openai==2.36.0",
        "jsonschema==4.26.0",
    )
    .add_local_dir(LOCAL_ROOT / "prompts", IMAGE_ROOT / "prompts", copy=True)
    .add_local_dir(LOCAL_ROOT / "schemas", IMAGE_ROOT / "schemas", copy=True)
)

app = modal.App(APP_NAME)
provider_secret = modal.Secret.from_name("cognition-ugc-heygen")


@app.function(
    image=runtime_image,
    secrets=[provider_secret],
    cpu=0.25,
    memory=512,
    timeout=1200,
    min_containers=0,
    max_containers=10,
    scaledown_window=2,
)
def run_workflow(payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Modal background runner for the LLM-only canary."""
    return execute_canary(payload, run_id=run_id)


SpawnRunner = Callable[[dict[str, Any], str], str]
LookupResult = Callable[[str], dict[str, Any]]


def create_fastapi_app(
    spawn_runner: SpawnRunner | None = None,
    lookup_result: LookupResult | None = None,
) -> Any:
    """Build the API, with injectable adapters for account-free local tests."""
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from jsonschema import ValidationError

    web = FastAPI(title="Cognition UGC HeyGen Canary", version="0.1.0")

    def default_spawn(payload: dict[str, Any], run_id: str) -> str:
        call = run_workflow.spawn(payload, run_id)
        return call.object_id

    def default_lookup(call_id: str) -> dict[str, Any]:
        call = modal.FunctionCall.from_id(call_id)
        return call.get(timeout=0)

    spawn = spawn_runner or default_spawn
    lookup = lookup_result or default_lookup

    @web.post("/v1/runs", status_code=202)
    async def submit(body: Any) -> dict[str, str]:
        try:
            validate_instance(body, "input.json")
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc

        run_id = str(uuid.uuid4())
        call_id = spawn(body, run_id)
        return {
            "run_id": run_id,
            "call_id": call_id,
            "status": "accepted",
            "result_url": f"/v1/runs/{call_id}",
        }

    @web.get("/v1/runs/{call_id}")
    async def get_result(call_id: str) -> Any:
        try:
            result = lookup(call_id)
            validate_instance(result, "output.json")
            return result
        except TimeoutError:
            return JSONResponse(
                {"call_id": call_id, "status": "running"}, status_code=202
            )
        except Exception:
            # Provider bodies and secret-bearing exception details stay internal.
            return JSONResponse(
                {
                    "call_id": call_id,
                    "status": "failed",
                    "error": {"code": "RUN_FAILED"},
                },
                status_code=500,
            )

    return web


@app.function(
    image=runtime_image,
    min_containers=0,
    max_containers=20,
    scaledown_window=2,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app(requires_proxy_auth=True)
def api() -> Any:
    return create_fastapi_app()
