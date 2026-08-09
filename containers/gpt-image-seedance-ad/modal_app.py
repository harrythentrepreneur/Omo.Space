"""Synchronous LLM + in-container Modal GPU canary for product-ad images."""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

try:
    import modal

    MODAL_SDK_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - exercised in SDK-free environments
    MODAL_SDK_AVAILABLE = False

    class _LocalImage:
        def uv_pip_install(self, *_packages: str) -> "_LocalImage":
            return self

        def add_local_dir(self, *_paths: Any, **_kwargs: Any) -> "_LocalImage":
            return self

    class _ImageFactory:
        @staticmethod
        def debian_slim(**_kwargs: Any) -> _LocalImage:
            return _LocalImage()

    class _Secret:
        @staticmethod
        def from_name(name: str) -> dict[str, str]:
            return {"name": name}

    class _App:
        def __init__(self, name: str):
            self.name = name

        def function(self, **_kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorate(function: Callable[..., Any]) -> Callable[..., Any]:
                function.remote = function  # type: ignore[attr-defined]
                function.local = function  # type: ignore[attr-defined]
                return function

            return decorate

    class _ModalFallback:
        App = _App
        Image = _ImageFactory
        Secret = _Secret

        @staticmethod
        def asgi_app(**_kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            return lambda function: function

    modal = _ModalFallback()  # type: ignore[assignment]


APP_NAME = "cognition-gpt-image-seedance-ad"
DEFAULT_LLM_BASE_URL = "https://opencode.ai/zen/go/v1"
DEFAULT_LLM_MODEL = "deepseek-v4-flash"
ESTIMATED_COST_USD = 0.22
BUYER_RUN_PRICE_USD = 1.10
IMAGE_VARIANTS = 3

LOCAL_ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = Path("/root/gpt_image_seedance_ad")


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


def _concept_schema() -> dict[str, Any]:
    return load_schema("output.json")["properties"]["concept"]


def parse_llm_json(raw: str) -> dict[str, Any]:
    """Recover one JSON object from optional fences/preamble and fail closed."""
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

    Draft202012Validator(_concept_schema()).validate(value)
    return value


def _new_openai_client() -> Any:
    """Create the provider client lazily; imports never require credentials."""
    from openai import OpenAI

    return OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
    )


def call_llm(payload: dict[str, Any], client: Any | None = None) -> dict[str, Any]:
    """Create the strict ad concept with one OpenAI-compatible completion."""
    llm = client if client is not None else _new_openai_client()
    response = llm.chat.completions.create(
        model=os.environ.get("LLM_MODEL", DEFAULT_LLM_MODEL),
        temperature=0.2,
        max_tokens=500,
        messages=[
            {"role": "system", "content": load_prompt("concept.txt")},
            {
                "role": "user",
                "content": "Create the ad concept for this input:\n"
                + json.dumps(payload, ensure_ascii=False, sort_keys=True),
            },
        ],
    )
    return parse_llm_json(response.choices[0].message.content)


ASPECT_DIMENSIONS = {
    "9:16": (576, 1024),
    "1:1": (1024, 1024),
    "16:9": (1024, 576),
}


def _mock_images_inside_container(prompt_text: str, aspect: str) -> list[dict[str, Any]]:
    """Create deterministic canary artifacts from inputs with no provider calls."""
    if not isinstance(prompt_text, str) or len(prompt_text.strip()) < 10:
        raise ValueError("prompt_text must be a non-empty generation prompt")
    if aspect not in ASPECT_DIMENSIONS:
        raise ValueError("unsupported image aspect")

    width, height = ASPECT_DIMENSIONS[aspect]
    digest = hashlib.sha256(f"{aspect}\0{prompt_text}".encode()).hexdigest()[:12]
    return [
        {
            "url": (
                "https://mock.cognition.market/gpt-image-seedance-ad/"
                f"MOCK-{digest}-{variant}.png"
            ),
            "width": width,
            "height": height,
            "aspect": aspect,
        }
        for variant in range(1, IMAGE_VARIANTS + 1)
    ]


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
provider_secret = modal.Secret.from_name("cognition-gpt-image-seedance-ad")


@app.function(
    image=runtime_image,
    secrets=[provider_secret],
    gpu="A10G",
    timeout=180,
    min_containers=0,
    max_containers=5,
    scaledown_window=2,
)
def generate_images_gpu(prompt_text: str, aspect: str) -> list[dict[str, Any]]:
    """Run the image-generation path inside an A10G Modal container."""
    # MOCK CANARY: this function really executes in the GPU container, but returns
    # deterministic placeholder artifacts so testing requires zero paid accounts.
    # TODO(Day 3): load a reviewed compact image model (for example a distilled
    # diffusion checkpoint) into this image and generate/upload the three pixels-on-
    # disk variants here. Keep inference local to this GPU Function; do not replace
    # it with a remote-image-API-only passthrough.
    return _mock_images_inside_container(prompt_text, aspect)


GpuRunner = Callable[[str, str], list[dict[str, Any]]]


def _run_gpu_remote(prompt_text: str, aspect: str) -> list[dict[str, Any]]:
    return generate_images_gpu.remote(prompt_text, aspect)


def execute_workflow(
    payload: dict[str, Any],
    *,
    llm_client: Any | None = None,
    gpu_runner: GpuRunner | None = None,
) -> dict[str, Any]:
    """Validate, plan with the LLM, execute the GPU step, and validate output."""
    validate_instance(payload, "input.json")
    concept = call_llm(payload, client=llm_client)
    run_gpu = gpu_runner or _run_gpu_remote
    images = run_gpu(concept["prompt_text"], payload["aspect"])
    result = {"concept": concept, "images": images}
    validate_instance(result, "output.json")
    return {
        "status": "completed",
        "result": result,
        "usage": {
            "estimated_cost_usd": ESTIMATED_COST_USD,
            "buyer_run_price_usd": BUYER_RUN_PRICE_USD,
        },
    }


def create_fastapi_app(
    llm_client: Any | None = None,
    gpu_runner: GpuRunner | None = None,
) -> Any:
    """Build the protected sync API with injectable offline test adapters."""
    from fastapi import FastAPI, HTTPException
    from jsonschema import ValidationError

    web = FastAPI(title="Cognition Cinematic Product Ad", version="0.1.0")

    @web.post("/v1/run", status_code=200)
    def run(body: Any) -> dict[str, Any]:
        try:
            validate_instance(body, "input.json")
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.message) from exc

        try:
            return execute_workflow(
                body, llm_client=llm_client, gpu_runner=gpu_runner
            )
        except (ValidationError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise HTTPException(
                status_code=502, detail="Workflow returned an invalid result"
            ) from exc

    return web


@app.function(
    image=runtime_image,
    secrets=[provider_secret],
    cpu=0.25,
    memory=1024,
    timeout=300,
    min_containers=0,
    max_containers=10,
    scaledown_window=2,
)
@modal.asgi_app(requires_proxy_auth=True)
def api() -> Any:
    return create_fastapi_app()
