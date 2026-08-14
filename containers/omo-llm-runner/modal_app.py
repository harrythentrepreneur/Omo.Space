"""Shared signed-manifest Tier-2 runtime for every pure-LLM Omo tool.

Tools are registry data. This app owns one protected Modal ingress and no
slug-specific code, prompt, endpoint, provider credential, or price switch.
Offline tests inject a provider callable and never read keys or use network.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import modal
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator, ValidationError


APP_NAME = "omo-llm-runner"
RUNNER_RELEASE = "omo-llm-runner@1"
SECRET_NAME = "omo-llm-runner-providers"
LOCAL_ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = Path("/root/omo_llm_runner")
MAX_REQUEST_BYTES = 512 * 1024
MAX_SYSTEM_TEMPLATE_BYTES = 24_000
ALLOWED_ADAPTERS = {("opencode-go", 1)}
ALLOWED_MODELS = {"deepseek-v4-flash"}
DEFAULT_BASE_URL = "https://opencode.ai/zen/go/v1"
ALLOWED_PROVIDER_HOSTS = {"opencode.ai"}
RUN_ID_RE = re.compile(r"^run_[A-Za-z0-9_-]{4,91}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
SAFE_TEMPLATE_TOKEN = "{{ input_json }}"


class RunnerContractError(ValueError):
    """Safe request/manifest rejection before provider spend."""


class RunnerNotReady(RuntimeError):
    """Safe environment configuration failure before provider spend."""


class ProviderCallError(RuntimeError):
    """Safe provider failure without response bodies or credentials."""


ProviderCall = Callable[
    [dict[str, Any], list[dict[str, str]], dict[str, Any]],
    tuple[dict[str, Any], dict[str, int], str],
]


def _asset_root() -> Path:
    return LOCAL_ROOT if (LOCAL_ROOT / "schemas" / "runner-request.json").is_file() else IMAGE_ROOT


@lru_cache(maxsize=None)
def load_json(relative_path: str) -> dict[str, Any]:
    path = _asset_root() / relative_path
    if _asset_root() == LOCAL_ROOT and relative_path == "schemas/manifest.json":
        path = LOCAL_ROOT.parents[1] / "manifests" / "llm-tools" / "manifest.schema.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict[str, Any]:
    schema = load_json(f"schemas/{name}")
    Draft202012Validator.check_schema(schema)
    return schema


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RunnerContractError("MANIFEST_NOT_CANONICAL_JSON") from exc


def _b64url_decode(value: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value or ""):
        raise RunnerContractError("MANIFEST_SIGNATURE_ENCODING_INVALID")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except Exception as exc:
        raise RunnerContractError("MANIFEST_SIGNATURE_ENCODING_INVALID") from exc


@lru_cache(maxsize=1)
def trusted_keys() -> dict[str, Ed25519PublicKey]:
    document = load_json("trusted-keys.json")
    if document.get("spec_version") != "omo.trusted-manifest-keys/v1":
        raise RunnerNotReady("TRUST_STORE_INVALID")
    keys: dict[str, Ed25519PublicKey] = {}
    for item in document.get("keys", []):
        if item.get("status") != "active" or item.get("algorithm") != "Ed25519-SHA256":
            continue
        raw = _b64url_decode(str(item.get("public_key") or ""))
        if len(raw) != 32:
            raise RunnerNotReady("TRUST_STORE_INVALID")
        keys[str(item.get("key_id") or "")] = Ed25519PublicKey.from_public_bytes(raw)
    if not keys:
        raise RunnerNotReady("NO_ACTIVE_MANIFEST_KEY")
    return keys


def validate_schema_policy(schema: dict[str, Any], label: str) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise RunnerContractError(f"{label}_SCHEMA_INVALID") from exc
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise RunnerContractError(f"{label}_SCHEMA_NOT_STRICT")
    if not isinstance(schema.get("properties"), dict) or not isinstance(schema.get("required"), list):
        raise RunnerContractError(f"{label}_SCHEMA_NOT_BOUNDED")
    encoded = canonical_json(schema)
    if len(encoded) > 100_000:
        raise RunnerContractError(f"{label}_SCHEMA_TOO_LARGE")


def verify_manifest(
    request_body: dict[str, Any],
    *,
    keyring: dict[str, Ed25519PublicKey] | None = None,
) -> dict[str, Any]:
    envelope = request_body["execution_manifest"]
    manifest_schema = load_json("schemas/manifest.json")
    try:
        Draft202012Validator(manifest_schema).validate(envelope)
    except ValidationError as exc:
        raise RunnerContractError("MANIFEST_SCHEMA_INVALID") from exc

    signature = envelope["signature"]
    if signature != request_body["manifest_signature"]:
        raise RunnerContractError("MANIFEST_SIGNATURE_MISMATCH")
    payload_bytes = canonical_json(envelope["payload"])
    digest = hashlib.sha256(payload_bytes).digest()
    digest_hex = digest.hex()
    if digest_hex != envelope["payload_sha256"] or digest_hex != request_body["manifest_sha256"]:
        raise RunnerContractError("MANIFEST_HASH_MISMATCH")
    keys = keyring if keyring is not None else trusted_keys()
    public_key = keys.get(signature["key_id"])
    if public_key is None:
        raise RunnerContractError("MANIFEST_KEY_UNTRUSTED")
    signature_bytes = _b64url_decode(signature["value"])
    if len(signature_bytes) != 64:
        raise RunnerContractError("MANIFEST_SIGNATURE_INVALID")
    try:
        public_key.verify(signature_bytes, digest)
    except InvalidSignature as exc:
        raise RunnerContractError("MANIFEST_SIGNATURE_INVALID") from exc

    payload = envelope["payload"]
    try:
        uuid.UUID(payload["tool_id"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise RunnerContractError("TOOL_ID_INVALID") from exc
    if (
        payload["tool_id"] != request_body["tool_id"]
        or payload["version"] != request_body["tool_version"]
        or payload["tier"] != 2
    ):
        raise RunnerContractError("MANIFEST_REQUEST_IDENTITY_MISMATCH")
    model_policy = payload["model_policy"]
    adapter = (model_policy["adapter_key"], model_policy["adapter_version"])
    if adapter not in ALLOWED_ADAPTERS:
        raise RunnerContractError("ADAPTER_NOT_ALLOWED")
    if model_policy["model"] not in ALLOWED_MODELS:
        raise RunnerContractError("MODEL_NOT_ALLOWED")
    if payload["artifact_policy"] != {"kind": "none", "max_bytes": 0}:
        raise RunnerContractError("ARTIFACT_REQUIRES_TIER_1")
    if len(payload["prompt"]["system_template"].encode("utf-8")) > MAX_SYSTEM_TEMPLATE_BYTES:
        raise RunnerContractError("SYSTEM_TEMPLATE_TOO_LARGE")
    validate_schema_policy(payload["input_schema"], "INPUT")
    validate_schema_policy(payload["output_schema"], "OUTPUT")
    return payload


def render_messages(payload: dict[str, Any], input_value: dict[str, Any]) -> list[dict[str, str]]:
    prompt = payload["prompt"]
    if prompt["template_engine"] != "omo-safe-template/v1":
        raise RunnerContractError("TEMPLATE_ENGINE_NOT_ALLOWED")
    user_template = prompt["user_template"]
    if user_template.count(SAFE_TEMPLATE_TOKEN) != 1:
        raise RunnerContractError("USER_TEMPLATE_INVALID")
    scrubbed = user_template.replace(SAFE_TEMPLATE_TOKEN, "")
    if "{{" in scrubbed or "}}" in scrubbed:
        raise RunnerContractError("USER_TEMPLATE_TOKEN_NOT_ALLOWED")
    user_prompt = user_template.replace(
        SAFE_TEMPLATE_TOKEN,
        canonical_json(input_value).decode("utf-8"),
    )
    return [
        {"role": "system", "content": payload["prompt"]["system_template"]},
        {"role": "user", "content": user_prompt},
    ]


def _extract_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderCallError("LLM_INVALID_JSON") from exc
    if not isinstance(parsed, dict):
        raise ProviderCallError("LLM_OUTPUT_NOT_OBJECT")
    return parsed


def _provider_completion(
    payload: dict[str, Any],
    messages: list[dict[str, str]],
    policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int], str]:
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise RunnerNotReady("MISSING_LLM_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    try:
        parsed_url = urllib.parse.urlsplit(base_url)
    except Exception as exc:
        raise RunnerNotReady("LLM_BASE_URL_INVALID") from exc
    if (
        parsed_url.scheme != "https:"
        or parsed_url.hostname not in ALLOWED_PROVIDER_HOSTS
        or parsed_url.username
        or parsed_url.password
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise RunnerNotReady("LLM_BASE_URL_NOT_ALLOWED")

    response_format: dict[str, Any]
    if policy["response_format"] == "json_schema":
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": re.sub(r"[^a-zA-Z0-9_-]", "_", payload["slug"])[:64],
                "strict": True,
                "schema": payload["output_schema"],
            },
        }
    else:
        response_format = {"type": "json_object"}
    request_document = {
        "model": policy["model"],
        "messages": messages,
        "temperature": policy["temperature"],
        "max_tokens": policy["max_output_tokens"],
        "response_format": response_format,
        "thinking": {"type": "disabled"},
    }
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=canonical_json(request_document),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "User-Agent": "Omo-LLM-Runner/1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=policy["timeout_seconds"]) as response:
            raw = response.read(policy["max_response_bytes"] + 1)
    except urllib.error.HTTPError as exc:
        raise ProviderCallError(f"LLM_HTTP_{exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderCallError("LLM_UNAVAILABLE") from exc
    if len(raw) > policy["max_response_bytes"]:
        raise ProviderCallError("LLM_RESPONSE_TOO_LARGE")
    try:
        document = json.loads(raw)
        content = document["choices"][0]["message"]["content"]
    except Exception as exc:
        raise ProviderCallError("LLM_RESPONSE_INVALID") from exc
    generated = _extract_json_object(str(content))
    usage = document.get("usage") or {}
    return (
        generated,
        {
            "prompt_tokens": max(0, int(usage.get("prompt_tokens") or 0)),
            "completion_tokens": max(0, int(usage.get("completion_tokens") or 0)),
        },
        str(document.get("model") or policy["model"]),
    )


def validate_runner_request(
    request_body: Any,
    *,
    keyring: dict[str, Ed25519PublicKey] | None = None,
) -> dict[str, Any]:
    if not isinstance(request_body, dict):
        raise RunnerContractError("REQUEST_NOT_OBJECT")
    if len(canonical_json(request_body)) > MAX_REQUEST_BYTES:
        raise RunnerContractError("REQUEST_TOO_LARGE")
    try:
        Draft202012Validator(load_schema("runner-request.json")).validate(request_body)
    except ValidationError as exc:
        raise RunnerContractError("REQUEST_SCHEMA_INVALID") from exc
    if not RUN_ID_RE.fullmatch(request_body["run_id"]):
        raise RunnerContractError("RUN_ID_INVALID")
    if not SHA256_RE.fullmatch(request_body["manifest_sha256"]):
        raise RunnerContractError("MANIFEST_HASH_INVALID")
    payload = verify_manifest(request_body, keyring=keyring)
    try:
        Draft202012Validator(payload["input_schema"]).validate(request_body["input"])
    except ValidationError as exc:
        raise RunnerContractError("INPUT_SCHEMA_INVALID") from exc
    return payload


def execute_request(
    request_body: dict[str, Any],
    *,
    provider_call: ProviderCall | None = None,
    keyring: dict[str, Ed25519PublicKey] | None = None,
) -> dict[str, Any]:
    payload = validate_runner_request(request_body, keyring=keyring)
    messages = render_messages(payload, request_body["input"])
    provider = provider_call or _provider_completion
    generated, token_usage, provider_model = provider(payload, messages, payload["model_policy"])
    try:
        Draft202012Validator(payload["output_schema"]).validate(generated)
    except ValidationError as exc:
        raise ProviderCallError("LLM_OUTPUT_SCHEMA_INVALID") from exc
    pricing = payload["pricing"]
    estimated_cost = (
        token_usage["prompt_tokens"] * pricing["input_rate_per_million_usd"]
        + token_usage["completion_tokens"] * pricing["output_rate_per_million_usd"]
    ) / 1_000_000
    if estimated_cost * 100 > pricing["max_provider_cost_cents"]:
        raise ProviderCallError("LLM_COST_CEILING_EXCEEDED")
    result = {
        "spec_version": "omo.result/v1",
        "run_id": request_body["run_id"],
        "tool_id": request_body["tool_id"],
        "tool_version": request_body["tool_version"],
        "status": "completed",
        "data": generated,
        "artifacts": [],
        "usage": {
            "adapter": "opencode-go@1",
            "provider": "opencode-go",
            "model": provider_model,
            "prompt_tokens": token_usage["prompt_tokens"],
            "completion_tokens": token_usage["completion_tokens"],
            "provider_calls": 1,
            "estimated_cost_usd": round(estimated_cost, 8),
        },
    }
    Draft202012Validator(load_schema("result.json")).validate(result)
    return result


def create_fastapi_app(
    provider_call: ProviderCall | None = None,
    *,
    keyring: dict[str, Ed25519PublicKey] | None = None,
) -> Any:
    from fastapi import Body, FastAPI
    from fastapi.responses import JSONResponse

    web = FastAPI(title=APP_NAME, version="1")

    @web.post("/v1/runs")
    async def submit(body: Any = Body(...)) -> Any:
        try:
            return execute_request(body, provider_call=provider_call, keyring=keyring)
        except RunnerContractError as exc:
            return JSONResponse(
                {"status": "rejected", "error": {"code": str(exc)}},
                status_code=422,
            )
        except RunnerNotReady as exc:
            return JSONResponse(
                {"status": "not_ready", "error": {"code": str(exc)}},
                status_code=503,
            )
        except ProviderCallError as exc:
            return JSONResponse(
                {"status": "failed", "error": {"code": str(exc)}},
                status_code=502,
            )

    @web.get("/healthz")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "runner_release": RUNNER_RELEASE}

    return web


runtime_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "modal==1.5.0",
        "fastapi==0.109.0",
        "jsonschema==4.26.0",
        "cryptography==45.0.5",
    )
    .add_local_dir(LOCAL_ROOT / "schemas", IMAGE_ROOT / "schemas", copy=True)
    .add_local_file(
        LOCAL_ROOT.parents[1] / "manifests" / "llm-tools" / "manifest.schema.json",
        str(IMAGE_ROOT / "schemas" / "manifest.json"),
        copy=True,
    )
    .add_local_file(LOCAL_ROOT / "trusted-keys.json", str(IMAGE_ROOT / "trusted-keys.json"), copy=True)
)

app = modal.App(APP_NAME)
runtime_secret = modal.Secret.from_name(SECRET_NAME)


@app.function(
    image=runtime_image,
    secrets=[runtime_secret],
    cpu=0.5,
    memory=512,
    timeout=150,
    min_containers=0,
    max_containers=8,
    scaledown_window=15,
)
@modal.concurrent(max_inputs=8, target_inputs=4)
@modal.asgi_app(requires_proxy_auth=True)
def api() -> Any:
    return create_fastapi_app()
