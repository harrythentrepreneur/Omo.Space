from __future__ import annotations

import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from image_gen import (  # noqa: E402
    ProceduralSumiEGenerator,
    expand_semantic_frames,
    validate_image_path,
)
from workflow import (  # noqa: E402
    PipelineConfig,
    PipelineDependencies,
    Transcript,
    WorkflowError,
    _provider_cost_evidence,
    run_pipeline,
    run_from_files,
)


def test_real_audio_fixture_is_bounded_and_has_audio() -> None:
    fixture = ROOT / "assets" / "sample-demello-10s.m4a"
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(fixture),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    assert 10 <= duration <= 11


def test_procedural_story_finishes_as_one_ink_dot_on_white() -> None:
    generator = ProceduralSumiEGenerator()
    frames = [
        Image.open(BytesIO(generator.render({}, index, 30))).convert("L")
        for index in range(30)
    ]
    first, last = frames[0], frames[-1]
    first_box = first.point(lambda value: 255 if value < 100 else 0).getbbox()
    last_box = last.point(lambda value: 255 if value < 100 else 0).getbbox()
    assert first_box is not None and last_box is not None
    assert first_box[2] - first_box[0] > 700
    assert last_box[2] - last_box[0] < 80
    assert last_box[3] - last_box[1] < 80
    assert all(set(frame.get_flattened_data()) == {26, 255} for frame in frames)

    # Wide topology has separate tiger, mice/branch, hanging figure, and berry;
    # the middle insert replaces it with a readable face/berry contact crop.
    def dark_pixels(frame: Image.Image, box: tuple[int, int, int, int]) -> int:
        return sum(value < 100 for value in frame.crop(box).get_flattened_data())

    assert dark_pixels(first, (45, 220, 440, 700)) > 3_000  # tiger + cliff
    assert dark_pixels(first, (310, 550, 850, 790)) > 2_000  # two mice + branch
    assert dark_pixels(first, (440, 680, 820, 1550)) > 3_000  # grip + robe
    assert dark_pixels(first, (730, 1050, 900, 1320)) > 350  # leafed berry
    assert dark_pixels(frames[10], (260, 360, 820, 1320)) > 5_000  # profile/contact


def test_dense_authored_frames_never_crossfade_one_moving_dot(tmp_path: Path) -> None:
    anchors = tmp_path / "anchors"
    anchors.mkdir()
    generated: list[dict[str, object]] = []
    for index, x in enumerate((260, 540, 820)):
        image = Image.new("RGB", (1080, 1920), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((x - 22, 600 - 22, x + 22, 600 + 22), fill=(26, 26, 26))
        path = anchors / f"G{index:03d}.png"
        image.save(path)
        generated.append(
            {"frame_id": f"G{index:03d}", "second": index / 3, "path": str(path)}
        )

    frames = expand_semantic_frames(
        generated,
        [],
        1.0,
        tmp_path / "semantic",
    )
    assert [frame["transition_mode"] for frame in frames] == ["authored-redraw"] * 3
    for frame, expected_x in zip(frames, (260, 540, 820)):
        image = Image.open(str(frame["path"])).convert("L")
        box = image.point(lambda value: 255 if value < 100 else 0).getbbox()
        assert box is not None
        assert box[2] - box[0] < 60
        assert abs((box[0] + box[2]) / 2 - expected_x) <= 2
        assert set(image.get_flattened_data()) == {26, 255}


def test_five_second_procedural_pipeline_produces_delivery_contract(tmp_path: Path) -> None:
    request = {
        "run_id": "run_local_pipeline_001",
        "audio_ref": "sample-demello-10s",
        "style": "sumi-e-awake-v3",
        "duration_bounds": {"min_seconds": 5, "max_seconds": 5},
        "max_cost_usd": 1.0,
    }
    transcript = Transcript(
        text="Wake up and see how awareness opens into the world.",
        segments=(),
        language="en",
        duration_seconds=5.0,
        model="offline-test",
        usage={"cost_usd": 0.0},
    )
    result = run_pipeline(
        request,
        PipelineConfig(
            artifact_root=tmp_path / "artifacts",
            work_root=tmp_path / "work",
            audio_refs={"sample-demello-10s": ROOT / "assets" / "sample-demello-10s.m4a"},
            allow_procedural_fallback=True,
        ),
        PipelineDependencies(
            transcriber=lambda _audio: transcript,
            director=lambda _transcript, _duration: (_ for _ in ()).throw(RuntimeError("offline")),
        ),
    )
    video = tmp_path / "artifacts" / "runs" / request["run_id"] / "video.mp4"
    contact = tmp_path / "artifacts" / "runs" / request["run_id"] / "contact-sheet.jpg"
    assert result["generation_provider"] == "procedural-fallback"
    assert result["frames_used"] == {"generated": 15, "semantic": 15, "output": 150}
    assert result["assembly"]["pair_count"] == 0
    assert "no dissolve" in result["assembly"]["filter_method"]
    assert result["media"]["video_codec"] == "h264"
    assert result["media"]["audio_codec"] == "aac"
    assert result["qa"]["checks"]["audio_duration"] is True
    assert abs(result["qa"]["audio_duration_seconds"] - 5.0) <= 0.10
    assert (result["media"]["width"], result["media"]["height"], result["media"]["fps"]) == (1080, 1920, 30)
    assert video.stat().st_size > 10_000
    assert contact.read_bytes().startswith(b"\xff\xd8")
    report = validate_image_path(contact)
    assert report.portrait is False


def test_provider_lane_is_rejected_before_any_external_effect(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEMELLO_PROVIDER_LANE_ENABLED", raising=False)
    run_id = "run_provider_gate_001"
    artifact_root = tmp_path / "artifacts"
    request_path = tmp_path / "request.json"
    result_path = tmp_path / "result.json"
    request_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "input": {
                    "audio_url": "https://media.example/customer.m4a",
                    "style": "sumi-e-awake-v3",
                    "duration_bounds": {"min_seconds": 5, "max_seconds": 10},
                },
                "max_cost_usd": 5,
                "artifact_root": str(artifact_root),
                "run_artifact_dir": str(artifact_root / "runs" / run_id),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(WorkflowError, match="provider-backed input lane"):
        run_from_files(request_path, result_path)
    assert not result_path.exists()
    assert not artifact_root.exists()


def test_every_used_provider_component_must_have_cost_evidence() -> None:
    rich = {
        "generation_provider": "chatgpt-codex-image-generation",
        "transcription": {"usage": {"cost_usd": 0.01}},
        "director": {"provider": "deepseek-v4-flash", "usage": {}},
        "image_generation": {"usage": {"cost_complete": False}},
    }
    costs, complete = _provider_cost_evidence(rich)
    assert costs == {"transcription": 0.01}
    assert complete is False
