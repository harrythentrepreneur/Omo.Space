"""Synchronous, single-LLM SEO audit container for the Cognition marketplace."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import modal
from jsonschema import Draft202012Validator


APP_NAME = "cognition-claude-seo-skill"
DEFAULT_LLM_BASE_URL = "https://opencode.ai/zen/go/v1"
DEFAULT_LLM_MODEL = "deepseek-v4-flash"
ESTIMATED_COST_USD = 0.0002
BUYER_RUN_PRICE_USD = 0.10

LOCAL_ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = Path("/root/claude_seo_skill")


def _asset_root() -> Path:
    """Use checked-in assets locally and copied assets in the Modal image."""
    if (LOCAL_ROOT / "schemas" / "input.json").is_file():
        return LOCAL_ROOT
    return IMAGE_ROOT


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    with (_asset_root() / "schemas" / name).open(encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return schema


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    return (_asset_root() / "prompts" / name).read_text(encoding="utf-8").strip()


def validate_instance(instance: Any, schema_name: str) -> None:
    """Validate without coercing, dropping, or inventing fields."""
    Draft202012Validator(load_schema(schema_name)).validate(instance)


def parse_llm_json(raw: str) -> dict[str, Any]:
    """Recover one JSON object from optional prose/fences, then validate it."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("LLM response must be a non-empty string")

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        closing_fence = cleaned.rfind("```")
        if first_newline < 0 or closing_fence <= first_newline:
            raise ValueError("LLM returned an incomplete JSON fence")
        cleaned = cleaned[first_newline + 1 : closing_fence].strip()

    start = cleaned.find("{")
    if start < 0:
        raise ValueError("LLM did not return a JSON object")

    try:
        value, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    except json.JSONDecodeError as exc:
        raise ValueError("LLM returned malformed JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("LLM output is not a JSON object")

    validate_instance(value, "output.json")
    return value


def _new_openai_client() -> Any:
    """Create the provider client lazily; importing this module needs no key."""
    from openai import OpenAI

    return OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
    )


def call_llm(payload: dict[str, Any], client: Any | None = None) -> dict[str, Any]:
    """Make the workflow's only OpenAI-compatible chat-completions call."""
    llm = client if client is not None else _new_openai_client()
    response = llm.chat.completions.create(
        model=os.environ.get("LLM_MODEL", DEFAULT_LLM_MODEL),
        temperature=0.2,
        max_tokens=500,
        messages=[
            {"role": "system", "content": load_prompt("audit.txt")},
            {
                "role": "user",
                "content": "Audit this business input:\n"
                + json.dumps(payload, ensure_ascii=False, sort_keys=True),
            },
        ],
    )
    return parse_llm_json(response.choices[0].message.content)


def execute_workflow(
    payload: dict[str, Any], *, llm_client: Any | None = None
) -> dict[str, Any]:
    """Validate first, execute one LLM call, and return a completed result."""
    validate_instance(payload, "input.json")
    result = call_llm(payload, client=llm_client)
    return {
        "status": "completed",
        "result": result,
        "usage": {
            "estimated_cost_usd": ESTIMATED_COST_USD,
            "buyer_run_price_usd": BUYER_RUN_PRICE_USD,
        },
    }


def create_fastapi_app(llm_client: Any | None = None) -> Any:
    """Build the protected synchronous API with an injectable test client."""
    from fastapi import FastAPI, HTTPException
    from jsonschema import ValidationError

    web = FastAPI(title="Claude SEO Skill", version="0.1.0")

    @web.post("/v1/run", status_code=200)
    def run(body: Any) -> dict[str, Any]:
        try:
            validate_instance(body, "input.json")
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc

        try:
            return execute_workflow(body, llm_client=llm_client)
        except (ValidationError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise HTTPException(
                status_code=502, detail="LLM returned an invalid response"
            ) from exc

    return web


runtime_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "modal==1.5.0",
        "fastapi==0.109.0",
        "openai==2.36.0",
        "jsonschema==4.26.0",
    )
    .add_local_dir(LOCAL_ROOT / "prompts", IMAGE_ROOT / "prompts", copy=True)
    .add_local_dir(LOCAL_ROOT / "schemas", IMAGE_ROOT / "schemas", copy=True)
)

app = modal.App(APP_NAME)
provider_secret = modal.Secret.from_name("cognition-claude-seo-skill")


@app.function(
    image=runtime_image,
    secrets=[provider_secret],
    cpu=0.25,
    memory=512,
    timeout=150,
    min_containers=0,
    max_containers=20,
    scaledown_window=2,
)
@modal.asgi_app(requires_proxy_auth=True)
def api() -> Any:
    return create_fastapi_app()
