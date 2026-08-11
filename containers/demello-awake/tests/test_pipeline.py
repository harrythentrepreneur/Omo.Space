from __future__ import annotations

import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from image_gen import ProceduralSumiEGenerator, validate_image_path  # noqa: E402
from workflow import (  # noqa: E402
    PipelineConfig,
    PipelineDependencies,
    Transcript,
    run_pipeline,
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
    first = Image.open(BytesIO(generator.render({}, 0, 30))).convert("L")
    last = Image.open(BytesIO(generator.render({}, 29, 30))).convert("L")
    first_box = first.point(lambda value: 255 if value < 100 else 0).getbbox()
    last_box = last.point(lambda value: 255 if value < 100 else 0).getbbox()
    assert first_box is not None and last_box is not None
    assert first_box[2] - first_box[0] > 700
    assert last_box[2] - last_box[0] < 80
    assert last_box[3] - last_box[1] < 80


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
    assert result["frames_used"] == {"generated": 3, "semantic": 15, "output": 150}
    assert result["media"]["video_codec"] == "h264"
    assert result["media"]["audio_codec"] == "aac"
    assert result["qa"]["checks"]["audio_duration"] is True
    assert abs(result["qa"]["audio_duration_seconds"] - 5.0) <= 0.10
    assert (result["media"]["width"], result["media"]["height"], result["media"]["fps"]) == (1080, 1920, 30)
    assert video.stat().st_size > 10_000
    assert contact.read_bytes().startswith(b"\xff\xd8")
    report = validate_image_path(contact)
    assert report.portrait is False
