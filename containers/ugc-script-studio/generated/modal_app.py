"""Generated deterministic Modal single-LLM runtime. Do not edit; regenerate."""
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import modal
from jsonschema import Draft202012Validator

APP_NAME = "cognition-ugc-script-studio"
ROOT = Path(__file__).parent
IMAGE_ROOT = Path("/root/ugc-script-studio")
DEFAULT_MODEL = 'deepseek-v4-flash'

def assets() -> Path:
    return ROOT if (ROOT / "schemas/input.json").exists() else IMAGE_ROOT

@lru_cache(None)
def schema(name: str) -> dict[str, Any]:
    value = json.loads((assets() / "schemas" / name).read_text())
    Draft202012Validator.check_schema(value)
    return value

def validate(value: Any, name: str) -> None:
    Draft202012Validator(schema(name)).validate(value)

def parse_output(raw: str) -> dict[str, Any]:
    if not isinstance(raw, str):
        raise ValueError("invalid provider JSON")
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first = cleaned.find("\n")
        last = cleaned.rfind("```")
        if first >= 0 and last > first:
            cleaned = cleaned[first + 1:last].strip()
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("invalid provider JSON")
    try:
        value, end = json.JSONDecoder().raw_decode(cleaned[start:])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid provider JSON") from exc
    if cleaned[start + end:].strip():
        raise ValueError("invalid provider JSON")
    validate(value, "output.json")
    return value

def execute(payload: dict[str, Any], client: Any = None) -> dict[str, Any]:
    validate(payload, "input.json")
    if client is None:
        from openai import OpenAI
        provider_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENCODE_GO_API_KEY")
        if not provider_key:
            raise KeyError("LLM_API_KEY")
        client = OpenAI(api_key=provider_key, base_url=os.environ.get("LLM_BASE_URL", "https://opencode.ai/zen/go/v1"))
    prompt = (assets() / "prompts/system.txt").read_text()
    response = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", DEFAULT_MODEL),
        temperature=0.3,
        max_tokens=900,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt + "\nReturn only one JSON object, without markdown fences or commentary."},
            {"role": "user", "content": json.dumps(payload, sort_keys=True)},
        ],
    )
    return {"status": "completed", "result": parse_output(response.choices[0].message.content), "usage": {"estimated_cost_usd": 0.001}}

def create_app(client: Any = None):
    from fastapi import FastAPI, HTTPException
    from jsonschema import ValidationError
    web = FastAPI(title="Cognition ugc-script-studio", version="1.0.0")

    @web.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "workflow": 'ugc-script-studio'}

    @web.post("/v1/run")
    def run(body: Any) -> dict[str, Any]:
        try:
            return execute(body, client)
        except ValidationError as exc:
            raise HTTPException(422, "Input does not match workflow schema") from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise HTTPException(502, "Provider returned an invalid response") from exc
    return web

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("modal==1.5.0", "fastapi==0.109.0", "openai==2.36.0", "jsonschema==4.26.0")
    .add_local_dir(ROOT / "schemas", IMAGE_ROOT / "schemas", copy=True)
    .add_local_dir(ROOT / "prompts", IMAGE_ROOT / "prompts", copy=True)
)
app = modal.App(APP_NAME)
provider_secret = modal.Secret.from_name("omo-keys")

@app.function(image=image, secrets=[provider_secret], cpu=0.25, memory=512, timeout=150)
def canary() -> dict[str, Any]:
    result = execute({"product_url": "https://example.com/silk-pillowcase", "brand_voice": "honest", "length": 30})
    print(json.dumps({"status": result["status"], "result_keys": sorted(result["result"])}))
    return result

@app.function(image=image, secrets=[provider_secret], cpu=0.25, memory=512, timeout=150, min_containers=0, max_containers=10, scaledown_window=2)
@modal.asgi_app(requires_proxy_auth=True)
def api():
    return create_app()
