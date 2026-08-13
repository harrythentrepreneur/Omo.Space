"""Acceptance tests for the fixture-only audio-symbolic-animation runtime."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


modal_app = _load_module("audio_symbolic_animation_modal_app_acceptance", ROOT / "modal_app.py")


FIXTURE_INPUT = {
    "fixture_id": "tone-thread-3s",
    "style": "sumi-e",
    "duration_seconds": 3,
}


def test_declaration_is_fixture_only_media_sequential_and_modal_required() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    capabilities = json.loads((ROOT / "capability-manifest.json").read_text(encoding="utf-8"))
    assert manifest["runtime"]["classification"] == "media-sequential"
    assert manifest["runtime"]["modal_required"] is True
    assert manifest["runtime"]["availability"] == "production_blocked_fixture_preview_available"
    assert manifest["pricing"]["chargeable"] is False
    assert manifest["readiness"]["can_submit"] is False
    assert manifest["fixture_preview"]["can_submit"] is True
    assert capabilities["runtime_class"] == "media-sequential"
    assert capabilities["decision"] == "blocked"
    assert capabilities["availability"] == "production_blocked_fixture_preview_available"
    assert capabilities["fixture_preview"]["can_submit"] is True
    assert capabilities["production_image_provider"]["available"] is False


def test_invalid_input_is_rejected_before_spawn_or_fixture_work(tmp_path: Path) -> None:
    with pytest.raises(modal_app.InputRejected):
        modal_app.execute_workflow({"style": "sumi-e", "duration_seconds": 3}, work_root=tmp_path)
    assert not any(tmp_path.iterdir())


def test_provider_unavailable_fails_closed_without_artifacts(tmp_path: Path) -> None:
    with pytest.raises(modal_app.ProviderUnavailable):
        modal_app.execute_workflow(
            {"audio_ref": {"object_key": "private/upload.wav", "bytes": 1234}, "style": "sumi-e", "duration_seconds": 3},
            work_root=tmp_path,
        )
    assert not any(tmp_path.iterdir())


def test_deterministic_regeneration_produces_identical_artifacts(tmp_path: Path) -> None:
    first = modal_app.execute_workflow(FIXTURE_INPUT, work_root=tmp_path / "a")
    second = modal_app.execute_workflow(FIXTURE_INPUT, work_root=tmp_path / "b")
    assert first["status"] == second["status"] == "completed"
    assert first["transcript"]["sha256"] == second["transcript"]["sha256"]
    assert first["mechanical_brief"]["sha256"] == second["mechanical_brief"]["sha256"]
    assert [a["sha256"] for a in first["artifacts"]] == [a["sha256"] for a in second["artifacts"]]
    assert first["mechanical_brief"]["generation_fps"] == 1
    assert [frame["verb"] for frame in first["mechanical_brief"]["frames"]] == ["hold", "release", "open"]


def test_fixture_runtime_outputs_real_h264_aac_portrait_mp4(tmp_path: Path) -> None:
    result = modal_app.execute_workflow(FIXTURE_INPUT, work_root=tmp_path)
    video = tmp_path / result["artifacts_by_kind"]["video"]["object_key"]
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,width,height",
            "-of",
            "json",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(probe.stdout)
    streams = {stream["codec_type"]: stream for stream in data["streams"]}
    assert streams["video"]["codec_name"] == "h264"
    assert streams["video"]["width"] == 1080
    assert streams["video"]["height"] == 1920
    assert streams["audio"]["codec_name"] == "aac"
    assert abs(float(data["format"]["duration"]) - 3.0) <= 0.2


def test_modal_style_submit_poll_progress_artifacts_ttl_delete_and_replay(tmp_path: Path) -> None:
    web = modal_app.create_fastapi_app(work_root=tmp_path, require_proxy_auth=False)
    submit = next(route for route in web.routes if route.path == "/v1/fixture-runs").endpoint
    poll = next(route for route in web.routes if route.path == "/v1/fixture-runs/{run_id}" and "GET" in route.methods).endpoint
    delete = next(route for route in web.routes if route.path == "/v1/fixture-runs/{run_id}" and "DELETE" in route.methods).endpoint

    accepted = asyncio.run(submit(FIXTURE_INPUT, idempotency_key="fixture-replay-0001"))
    replay = asyncio.run(submit(FIXTURE_INPUT, idempotency_key="fixture-replay-0001"))
    assert accepted["status"] == "accepted"
    assert replay["idempotent_replay"] is True
    assert replay["run_id"] == accepted["run_id"]

    completed = asyncio.run(poll(accepted["run_id"]))
    assert completed["status"] == "completed"
    assert completed["progress"][-1]["stage"] == "complete"
    assert completed["artifacts_by_kind"]["video"]["ttl_seconds"] == 3600
    assert completed["artifacts_by_kind"]["video"]["delete_after"].endswith("Z")

    removed = asyncio.run(delete(accepted["run_id"]))
    assert removed["status"] == "deleted"
    missing = asyncio.run(poll(accepted["run_id"]))
    assert missing.status_code == 404
