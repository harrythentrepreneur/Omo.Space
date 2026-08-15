from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from tools.render.video import (
    MediaRenderError,
    cut_highlights,
    extract_thumbnail,
    normalize,
    probe,
)


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg/ffprobe are required for media renderer tests",
)


@pytest.fixture()
def tiny_video(tmp_path: Path) -> Path:
    path = tmp_path / "tiny.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=160x90:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:duration=2:sample_rate=48000",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "1",
            "-c:a",
            "aac",
            "-shortest",
            path,
        ],
        check=True,
    )
    return path


def test_normalize_output_probe_and_repeatable_bytes(tiny_video: Path, tmp_path: Path) -> None:
    first = tmp_path / "normalized-a.mp4"
    second = tmp_path / "normalized-b.mp4"
    first_info = normalize(tiny_video, first, {"orientation": "portrait", "max_dimension": 320})
    second_info = normalize(tiny_video, second, {"orientation": "portrait", "max_dimension": 320})

    assert first_info == probe(first)
    assert first_info["width"] == 180
    assert first_info["height"] == 320
    assert first_info["codecs"] == {"video": "h264", "audio": "aac"}
    assert first.read_bytes() == second.read_bytes()


def test_highlight_cut_boundaries(tiny_video: Path, tmp_path: Path) -> None:
    output = tmp_path / "highlights.mp4"
    result = cut_highlights(
        tiny_video,
        output,
        [
            {"start_seconds": 0.20, "end_seconds": 0.70, "title": "first"},
            {"start_seconds": 1.00, "end_seconds": 1.60, "title": "second"},
        ],
    )

    assert result["duration"] == pytest.approx(1.10, abs=0.10)
    assert result["codecs"] == {"video": "h264", "audio": "aac"}


def test_thumbnail_signature_and_dimensions(tiny_video: Path, tmp_path: Path) -> None:
    output = tmp_path / "thumbnail.png"
    result = extract_thumbnail(tiny_video, output, 0.75)

    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(output) as image:
        assert image.size == (160, 90)
    assert result["width"] == 160
    assert result["height"] == 90


def test_out_of_range_timecodes_are_typed(tiny_video: Path, tmp_path: Path) -> None:
    with pytest.raises(MediaRenderError) as caught:
        cut_highlights(
            tiny_video,
            tmp_path / "invalid.mp4",
            [{"start_seconds": 1.5, "end_seconds": 2.5, "title": "invalid"}],
        )
    assert caught.value.code == "TIMECODE_OUT_OF_RANGE"

    with pytest.raises(MediaRenderError) as caught:
        extract_thumbnail(tiny_video, tmp_path / "invalid.png", 2.0)
    assert caught.value.code == "TIMECODE_OUT_OF_RANGE"

    with pytest.raises(MediaRenderError) as caught:
        cut_highlights(
            tiny_video,
            tmp_path / "overlap.mp4",
            [
                {"start_seconds": 0.1, "end_seconds": 0.8, "title": "first"},
                {"start_seconds": 0.7, "end_seconds": 1.2, "title": "overlap"},
            ],
        )
    assert caught.value.code == "CLIPS_OVERLAP"


def test_probe_non_video_is_typed(tmp_path: Path) -> None:
    source = tmp_path / "not-video.txt"
    source.write_text("plain text is not video\n", encoding="utf-8")

    with pytest.raises(MediaRenderError) as caught:
        probe(source)
    assert caught.value.code in {"MEDIA_SUBPROCESS_FAILED", "NON_VIDEO"}
