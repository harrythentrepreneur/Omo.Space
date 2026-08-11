from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import os
import sys
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("demello_awake_modal_app", ROOT / "modal_app.py")
assert spec and spec.loader
modal_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modal_app)


def direct_input(minimum: int = 5, maximum: int = 5) -> dict:
    return {
        "audio_ref": "sample-demello-10s",
        "style": "sumi-e-awake-v3",
        "duration_bounds": {"min_seconds": minimum, "max_seconds": maximum},
    }


def call(app, method: str, path: str, **kwargs) -> httpx.Response:
    async def execute() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://private.example"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(execute())


def test_draft_2020_schemas_are_valid_and_three_happy_inputs_normalize() -> None:
    for schema in (
        modal_app.INPUT_SCHEMA,
        modal_app.PRIVATE_RUN_SCHEMA,
        modal_app.PIPELINE_RESULT_SCHEMA,
    ):
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"].endswith("2020-12/schema")
    for minimum, maximum in ((5, 5), (5, 12), (12, 20)):
        envelope = modal_app.normalize_submission(direct_input(minimum, maximum))
        assert envelope["release_hash"] == modal_app.RELEASE_DIGEST
        assert envelope["request_hash"] == modal_app.canonical_request_hash(envelope["input"])


def test_artifact_schemas_allow_full_three_fps_generation() -> None:
    output = json.loads((ROOT / "schemas" / "output.json").read_text(encoding="utf-8"))
    internal = json.loads((ROOT / "schemas" / "internal.json").read_text(encoding="utf-8"))
    generated = output["properties"]["frames_used"]["properties"]["generated"]
    accepted = internal["$defs"]["accepted_keyframes"]["properties"]
    assert generated["maximum"] >= 60
    assert accepted["count"]["maximum"] >= 60
    assert accepted["frames"]["maxItems"] >= 60


def test_output_artifact_schema_matches_completed_status_contract() -> None:
    schema = json.loads((ROOT / "schemas" / "output.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    completed = {
        "run_id": "run_abcdefgh",
        "release_hash": modal_app.RELEASE_DIGEST,
        "request_hash": "1" * 64,
        "status": "completed",
        "phase": "delivered",
        "progress_pct": 100,
        "video_url": "https://private.example/video.mp4",
        "contact_sheet_url": "https://private.example/contact.jpg",
        "frames_used": {"generated": 30, "semantic": 30, "output": 300},
        "cost": {
            "measured_usd": 0.001,
            "success_p95_usd": 0.001,
            "delivered_tail_usd": 0,
            "guard_cost_usd": 0.003,
            "guarded_price_usd": 0.1,
            "target_margin": 0.8,
            "tail_reserve": 0.15,
            "successful_sample_size": 1,
        },
        "media": {
            "duration_seconds": 10,
            "video_codec": "h264",
            "audio_codec": "aac",
            "width": 1080,
            "height": 1920,
            "fps": 30,
        },
        "generation_provider": "procedural-fallback",
        "platform": modal_app.MILESTONE_SECURITY,
    }
    Draft202012Validator(schema).validate(completed)


@pytest.mark.parametrize(
    "body",
    [
        {"style": "sumi-e-awake-v3", "duration_bounds": {"min_seconds": 5, "max_seconds": 5}},
        {**direct_input(), "audio_url": "https://example.com/a.mp3"},
        {**direct_input(), "style": "oil"},
        {**direct_input(), "unexpected": True},
        direct_input(12, 5),
        {**direct_input(), "audio_ref": "../../secret"},
    ],
)
def test_six_invalid_inputs_fail_closed(body: dict) -> None:
    with pytest.raises((ValidationError, ValueError)):
        modal_app.normalize_submission(body, resolver=lambda *_a, **_k: [])


def test_private_envelope_rejects_tampered_hash() -> None:
    workflow_input = direct_input()
    envelope = {
        "run_id": "run_12345678",
        "release_hash": modal_app.RELEASE_DIGEST,
        "request_hash": "0" * 64,
        "input": workflow_input,
        "max_cost_usd": 1.0,
    }
    with pytest.raises(ValueError, match="request_hash"):
        modal_app.normalize_submission(envelope)


def test_audio_url_rejects_private_dns_target() -> None:
    body = {**direct_input(), "audio_url": "https://media.example/a.mp3"}
    body.pop("audio_ref")
    resolver = lambda *_a, **_k: [(None, None, None, None, ("10.0.0.7", 443))]
    with pytest.raises(ValueError, match="non-public"):
        modal_app.normalize_submission(body, resolver=resolver)


def test_bearer_auth_alias_and_idempotent_submit(tmp_path: Path) -> None:
    spawned: list[dict] = []
    store = modal_app.FileRunStore(tmp_path)
    app = modal_app.create_fastapi_app(
        spawn_runner=lambda envelope: spawned.append(envelope) or "fc-hidden",
        store=store,
        auth_key_getter=lambda: "server-test-key",
    )
    headers = {"Authorization": "Bearer server-test-key", "Idempotency-Key": "idem-12345678"}
    assert call(app, "POST", "/v1/runs", json=direct_input()).status_code == 401
    assert call(app, "POST", "/v1/runs", json=direct_input(), headers={"Authorization": "Bearer wrong"}).status_code == 401
    first = call(app, "POST", "/run", json=direct_input(), headers=headers)
    replay = call(app, "POST", "/v1/runs", json=direct_input(), headers=headers)
    assert first.status_code == replay.status_code == 202
    assert first.json()["run_id"] == replay.json()["run_id"]
    assert first.json()["phase"] == "queued"
    assert first.json()["progress_pct"] == 2
    assert replay.json()["idempotent_replay"] is True
    assert len(spawned) == 1
    assert "fc-hidden" not in first.text


def test_idempotency_key_conflict_returns_409(tmp_path: Path) -> None:
    app = modal_app.create_fastapi_app(
        spawn_runner=lambda _envelope: "fc-hidden",
        store=modal_app.FileRunStore(tmp_path),
        auth_key_getter=lambda: "server-test-key",
    )
    headers = {"Authorization": "Bearer server-test-key", "Idempotency-Key": "idem-conflict-1"}
    assert call(app, "POST", "/v1/runs", json=direct_input(5, 5), headers=headers).status_code == 202
    assert call(app, "POST", "/v1/runs", json=direct_input(5, 12), headers=headers).status_code == 409


def test_status_and_signed_expiring_artifacts(tmp_path: Path) -> None:
    store = modal_app.FileRunStore(tmp_path)
    run_id = "run_abcdefgh"
    artifact_dir = tmp_path / "runs" / run_id
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "video.mp4").write_bytes(b"video")
    (artifact_dir / "contact-sheet.jpg").write_bytes(b"contact")
    store.set_status(
        run_id,
        {
            "run_id": run_id,
            "status": "completed",
            "release_hash": modal_app.RELEASE_DIGEST,
            "artifacts": {},
            "frames_used": {"generated": 2, "semantic": 15, "output": 150},
            "cost": {"measured_usd": 0.0, "guarded_price_usd": 0.1},
            "media": {"duration_seconds": 5.0, "video_codec": "h264", "audio_codec": "aac", "width": 1080, "height": 1920, "fps": 30},
            "platform": modal_app.MILESTONE_SECURITY,
        },
    )
    app = modal_app.create_fastapi_app(
        spawn_runner=lambda _envelope: "unused",
        store=store,
        auth_key_getter=lambda: "server-test-key",
        clock=lambda: 1_000_000.0,
    )
    response = call(app, "GET", f"/v1/runs/{run_id}", headers={"Authorization": "Bearer server-test-key"})
    assert response.status_code == 200
    video_url = response.json()["video_url"]
    artifact = call(app, "GET", video_url)
    assert artifact.status_code == 200 and artifact.content == b"video"
    expired = video_url.replace("expires=1000300", "expires=999999")
    assert call(app, "GET", expired).status_code == 403
    assert response.json()["platform"]["modal_proxy_token"] is False
    assert response.json()["platform"]["omo_r2_artifacts"] is False
    assert response.json()["phase"] == "delivered"
    assert response.json()["progress_pct"] == 100


def test_signed_video_and_contact_download_concurrently_from_memory(tmp_path: Path) -> None:
    store = modal_app.FileRunStore(tmp_path)
    run_id = "run_parallel_artifacts"
    artifact_dir = tmp_path / "runs" / run_id
    artifact_dir.mkdir(parents=True)
    video = b"video" * 128_000
    contact = b"contact" * 32_000
    (artifact_dir / "video.mp4").write_bytes(video)
    (artifact_dir / "contact-sheet.jpg").write_bytes(contact)
    store.set_status(
        run_id,
        {
            "run_id": run_id,
            "status": "completed",
            "release_hash": modal_app.RELEASE_DIGEST,
            "artifacts": {},
            "frames_used": {"generated": 30, "semantic": 30, "output": 300},
            "cost": {"measured_usd": 0.0, "guarded_price_usd": 0.1},
            "media": {"duration_seconds": 10.0},
            "platform": modal_app.MILESTONE_SECURITY,
        },
    )
    app = modal_app.create_fastapi_app(
        spawn_runner=lambda _envelope: "unused",
        store=store,
        auth_key_getter=lambda: "server-test-key",
        clock=lambda: 1_000_000.0,
    )

    async def download_both() -> tuple[httpx.Response, httpx.Response]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://private.example"
        ) as client:
            status = await client.get(
                f"/v1/runs/{run_id}",
                headers={"Authorization": "Bearer server-test-key"},
            )
            status.raise_for_status()
            payload = status.json()
            return tuple(
                await asyncio.gather(
                    client.get(payload["video_url"]),
                    client.get(payload["contact_sheet_url"]),
                )
            )  # type: ignore[return-value]

    video_response, contact_response = asyncio.run(download_both())
    assert video_response.status_code == contact_response.status_code == 200
    assert video_response.content == video
    assert contact_response.content == contact
    assert video_response.headers["content-length"] == str(len(video))
    assert contact_response.headers["content-length"] == str(len(contact))
    assert video_response.headers["cache-control"] == "private, no-store"


def test_api_artifact_buffer_budget_leaves_half_the_container_for_runtime() -> None:
    aggregate_artifact_bytes = (
        modal_app.MAX_ARTIFACT_BYTES * modal_app.MAX_API_CONCURRENT_INPUTS
    )
    container_bytes = modal_app.API_MEMORY_MIB * 1024 * 1024
    assert modal_app.MAX_API_CONCURRENT_INPUTS >= 2
    assert aggregate_artifact_bytes <= container_bytes // 2


def test_running_status_reads_real_monotonic_diagnostic_checkpoint(tmp_path: Path) -> None:
    store = modal_app.FileRunStore(tmp_path)
    run_id = "run_progress_abcdefgh"
    store.set_status(
        run_id,
        {
            "run_id": run_id,
            "status": "running",
            "phase": "starting",
            "progress_pct": 5,
            "release_hash": modal_app.RELEASE_DIGEST,
            "platform": modal_app.MILESTONE_SECURITY,
        },
    )
    marker = store.diagnostic_path(run_id)
    marker.write_text('{"phase":"generate"}\n', encoding="utf-8")
    status = store.get_status(run_id)
    assert status and status["phase"] == "generating"
    assert status["progress_pct"] == 52
    assert [value[1] for value in modal_app.PHASE_PROGRESS.values()] == sorted(
        value[1] for value in modal_app.PHASE_PROGRESS.values()
    )


def test_provider_mocked_runner_protocol_and_media_contract(monkeypatch, tmp_path: Path) -> None:
    for key in ("OPENAI_API_KEY", "OPENCODE_GO_API_KEY", "LLM_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    envelope = modal_app.normalize_submission(direct_input())
    checkpoints: list[tuple[str, int]] = []
    result = modal_app.run_go_adapter(
        envelope,
        artifact_root=tmp_path,
        runner_command=(sys.executable, str(Path(__file__).with_name("stub_go_adapter.py"))),
        python_entrypoint=str(Path(__file__).with_name("stub_workflow.py")),
        progress_callback=lambda phase, progress: checkpoints.append((phase, progress)),
    )
    modal_app.validate_schema(result, modal_app.PIPELINE_RESULT_SCHEMA)
    assert result["generation_provider"] == "procedural-fallback"
    assert sum(result["usage"]["provider_costs_usd"].values()) == 0
    assert result["media"] == {
        "duration_seconds": 5.0,
        "video_codec": "h264",
        "audio_codec": "aac",
        "width": 1080,
        "height": 1920,
        "fps": 30,
    }
    assert result["frames_used"] == {"generated": 2, "semantic": 15, "output": 150}
    assert checkpoints == [("generating", 52)]


def test_go_adapter_is_dependency_free_and_propagates_signals() -> None:
    source = (ROOT / "cmd" / "runner" / "main.go").read_text(encoding="utf-8")
    go_mod = (ROOT / "cmd" / "runner" / "go.mod").read_text(encoding="utf-8")
    assert "require " not in go_mod
    assert 'signal.Notify(signals' in source
    assert 'syscall.Kill(-command.Process.Pid' in source
    assert "DisallowUnknownFields" in source
    assert "request and result paths must differ" in source
