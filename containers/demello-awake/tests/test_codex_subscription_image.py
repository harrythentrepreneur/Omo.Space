from __future__ import annotations

import base64
import io
import json
import sys
import time
from pathlib import Path

import pytest
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from image_gen import (  # noqa: E402
    CODEX_IMAGE_PROVIDER,
    CodexSubscriptionImageAdapter,
    ImageGenerationError,
    _codex_sse_image_result,
    generate_keyframes,
)


def sparse_portrait_png() -> bytes:
    image = Image.new("RGB", (256, 384), "white")
    draw = ImageDraw.Draw(image)
    draw.line((80, 90, 180, 260), fill="black", width=4)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_injected_codex_adapter_decodes_without_credentials() -> None:
    raw = sparse_portrait_png()
    calls: list[dict] = []

    def request(**kwargs):
        calls.append(kwargs)
        return {"data": [{"b64_json": base64.b64encode(raw).decode("ascii")}]}

    adapter = CodexSubscriptionImageAdapter(request=request)
    decoded, usage = adapter.generate("ink line")
    assert decoded == raw
    assert usage == {}
    assert calls[0]["edit"] is False
    assert adapter.model == CODEX_IMAGE_PROVIDER


def test_subscription_usage_is_explicitly_incomplete(tmp_path: Path) -> None:
    raw = sparse_portrait_png()
    adapter = CodexSubscriptionImageAdapter(
        request=lambda **_kwargs: {
            "data": [{"b64_json": base64.b64encode(raw).decode("ascii")}]
        }
    )
    result = generate_keyframes(
        [
            {
                "frame_id": "G000",
                "second": 0,
                "delta": "extend the existing ink line",
            }
        ],
        tmp_path,
        adapter=adapter,
        max_retries=0,
    )
    assert result.provider == CODEX_IMAGE_PROVIDER
    assert result.usage["cost_complete"] is False
    assert result.usage["measured_cost_usd"] is None


def test_codex_sse_extracts_final_image_without_network() -> None:
    encoded = base64.b64encode(sparse_portrait_png()).decode("ascii")
    lines = [
        "event: response.output_item.done",
        "data: "
        + json.dumps(
            {
                "type": "response.output_item.done",
                "item": {"type": "image_generation_call", "result": encoded},
            }
        ),
        'data: {"type":"response.completed"}',
    ]
    assert _codex_sse_image_result(lines) == encoded


def test_codex_sse_failure_and_missing_secret_errors_are_redacted(monkeypatch) -> None:
    with pytest.raises(ImageGenerationError, match="reported failure"):
        _codex_sse_image_result(['data: {"type":"response.failed"}'])

    for key in (
        "OPENAI_CODEX_ACCESS_TOKEN",
        "OPENAI_CODEX_ACCOUNT_ID",
        "OPENAI_CODEX_REFRESH_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)
    adapter = CodexSubscriptionImageAdapter()
    with pytest.raises(ImageGenerationError, match="OPENAI_CODEX_ACCESS_TOKEN"):
        adapter._refresh_if_needed()
    with pytest.raises(ImageGenerationError, match="OPENAI_CODEX_ACCOUNT_ID"):
        adapter._http_request(prompt="test", parent=None)


def test_unexpired_access_token_does_not_require_refresh() -> None:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": int(time.time()) + 3600}).encode()
    ).rstrip(b"=").decode()
    token = f"{header}.{payload}.signature"
    adapter = CodexSubscriptionImageAdapter(access_token=token, account_id="acct-test")
    assert adapter._refresh_if_needed() == token
