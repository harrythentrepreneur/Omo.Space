#!/usr/bin/env python3
"""Deterministic, bounded FFmpeg video primitives for generated workflows.

The module is storage-agnostic and accepts local, already-authorized paths.
Every subprocess receives an argv list, never a shell command. Clip titles are
validated as data but are intentionally not rendered or passed to FFmpeg.

Within one FFmpeg/libx264 build, fixed metadata, a fixed pixel format, constant
frame rate, and single-threaded encoding make repeated renders byte-stable in
practice. FFmpeg or codec-library upgrades may still change encoded bytes.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


MAX_INPUT_BYTES = 4 * 1024 * 1024 * 1024
MAX_SOURCE_SECONDS = 2 * 60 * 60
MAX_DIMENSION = 8192
MAX_OUTPUT_DIMENSION = 1280
MAX_CLIPS = 20
MAX_HIGHLIGHT_SECONDS = 10 * 60
PROBE_TIMEOUT_SECONDS = 20
RENDER_TIMEOUT_SECONDS = 10 * 60
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class MediaRenderError(ValueError):
    """A media input, bound, subprocess, or output contract failed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _error(code: str, message: str) -> MediaRenderError:
    return MediaRenderError(code, message)


def _path(value: str | os.PathLike[str], field: str) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        raise _error("INVALID_PATH", f"{field} must be a local path")
    result = Path(value)
    if not str(result):
        raise _error("INVALID_PATH", f"{field} must not be empty")
    return result


def _source_path(value: str | os.PathLike[str]) -> Path:
    source = _path(value, "src")
    try:
        stat = source.stat()
    except OSError as exc:
        raise _error("UNREADABLE_MEDIA", "source media is not readable") from exc
    if not source.is_file() or stat.st_size <= 0:
        raise _error("UNREADABLE_MEDIA", "source media must be a non-empty file")
    if stat.st_size > MAX_INPUT_BYTES:
        raise _error("INPUT_TOO_LARGE", "source media exceeds the 4 GiB bound")
    return source


def _destination_path(
    value: str | os.PathLike[str], *, suffixes: set[str], source: Path
) -> Path:
    destination = _path(value, "dest")
    if destination.suffix.lower() not in suffixes:
        expected = ", ".join(sorted(suffixes))
        raise _error("INVALID_DESTINATION", f"destination extension must be one of {expected}")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise _error("OUTPUT_WRITE_FAILED", "destination directory cannot be created") from exc
    try:
        if destination.resolve() == source.resolve():
            raise _error("INVALID_DESTINATION", "source and destination must differ")
    except OSError as exc:
        raise _error("INVALID_DESTINATION", "destination path cannot be resolved") from exc
    if destination.exists():
        raise _error("DESTINATION_EXISTS", "destination already exists")
    return destination


def _run(command: Sequence[str | os.PathLike[str]], *, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [str(part) for part in command],
            check=True,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise _error("TOOL_UNAVAILABLE", f"required executable is unavailable: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise _error("MEDIA_TIMEOUT", "media subprocess exceeded its time bound") from exc
    except subprocess.CalledProcessError as exc:
        executable = Path(str(command[0])).name
        raise _error("MEDIA_SUBPROCESS_FAILED", f"{executable} could not process the media") from exc


def _probe_payload(source: Path) -> dict[str, Any]:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            source,
        ],
        timeout=PROBE_TIMEOUT_SECONDS,
    )
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise _error("INVALID_PROBE_RESPONSE", "ffprobe returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise _error("INVALID_PROBE_RESPONSE", "ffprobe response must be an object")
    return payload


def _positive_float(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise _error("INVALID_MEDIA", f"{field} is invalid")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise _error("INVALID_MEDIA", f"{field} is unavailable") from exc
    if not math.isfinite(result) or result <= 0:
        raise _error("INVALID_MEDIA", f"{field} is invalid")
    return result


def probe(src: str | os.PathLike[str]) -> dict[str, Any]:
    """Return bounded, typed metadata for one readable video file."""
    source = _source_path(src)
    payload = _probe_payload(source)
    streams = payload.get("streams")
    if not isinstance(streams, list):
        raise _error("INVALID_MEDIA", "ffprobe did not return media streams")
    video = next(
        (stream for stream in streams if isinstance(stream, Mapping) and stream.get("codec_type") == "video"),
        None,
    )
    if not isinstance(video, Mapping):
        raise _error("NON_VIDEO", "media has no video stream")
    try:
        width = int(video["width"])
        height = int(video["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _error("INVALID_MEDIA", "video dimensions are unavailable") from exc
    if not (0 < width <= MAX_DIMENSION and 0 < height <= MAX_DIMENSION):
        raise _error("VIDEO_DIMENSIONS_OUT_OF_BOUNDS", "video dimensions exceed the 8192px bound")
    format_data = payload.get("format")
    if not isinstance(format_data, Mapping):
        raise _error("INVALID_MEDIA", "media format metadata is unavailable")
    duration = _positive_float(format_data.get("duration") or video.get("duration"), "duration")
    codecs: dict[str, str] = {"video": str(video.get("codec_name") or "unknown")}
    audio = next(
        (stream for stream in streams if isinstance(stream, Mapping) and stream.get("codec_type") == "audio"),
        None,
    )
    if isinstance(audio, Mapping):
        codecs["audio"] = str(audio.get("codec_name") or "unknown")
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise _error("UNREADABLE_MEDIA", "source media changed during probe") from exc
    return {
        "duration": duration,
        "width": width,
        "height": height,
        "codecs": codecs,
        "size": size,
    }


def _bounded_source_info(source: Path) -> dict[str, Any]:
    info = probe(source)
    if info["duration"] > MAX_SOURCE_SECONDS:
        raise _error("DURATION_OUT_OF_BOUNDS", "source duration exceeds the 2 hour bound")
    return info


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error("INVALID_TIMECODE", f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise _error("INVALID_TIMECODE", f"{field} must be a finite number")
    return result


def _seconds(value: float) -> str:
    return f"{value:.9f}"


def _temporary_output(destination: Path) -> Path:
    try:
        handle = tempfile.NamedTemporaryFile(
            prefix=f".{destination.stem}-",
            suffix=destination.suffix,
            dir=destination.parent,
            delete=False,
        )
        path = Path(handle.name)
        handle.close()
        return path
    except OSError as exc:
        raise _error("OUTPUT_WRITE_FAILED", "temporary output cannot be created") from exc


def _unlink_quietly(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _publish_new(temporary: Path, destination: Path) -> None:
    try:
        if not temporary.is_file() or temporary.stat().st_size <= 0:
            raise _error("EMPTY_OUTPUT", "FFmpeg did not produce a non-empty output")
    except OSError as exc:
        raise _error("OUTPUT_WRITE_FAILED", "rendered output cannot be inspected") from exc
    try:
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise _error("DESTINATION_EXISTS", "destination already exists") from exc
    except OSError as exc:
        raise _error("OUTPUT_WRITE_FAILED", "rendered output could not be published") from exc
    finally:
        _unlink_quietly(temporary)


def _encode_args() -> list[str]:
    return [
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.0",
        "-threads",
        "1",
        "-x264-params",
        "threads=1:lookahead_threads=1:sliced_threads=0",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-map_metadata",
        "-1",
        "-map_chapters",
        "-1",
        "-metadata",
        "creation_time=1970-01-01T00:00:00Z",
        "-movflags",
        "+faststart",
        "-f",
        "mp4",
    ]


def normalize(
    src: str | os.PathLike[str],
    dest: str | os.PathLike[str],
    opts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Transcode to a deterministic 30fps H.264/AAC portrait/landscape MP4."""
    source = _source_path(src)
    destination = _destination_path(dest, suffixes={".mp4", ".mov"}, source=source)
    if opts is None:
        options: Mapping[str, Any] = {}
    elif isinstance(opts, Mapping):
        options = opts
    else:
        raise _error("INVALID_OPTIONS", "opts must be an object")
    unknown = set(options) - {"orientation", "max_dimension", "crf"}
    if unknown:
        raise _error("INVALID_OPTIONS", "opts contains unsupported fields")
    orientation = options.get("orientation", "landscape")
    if orientation not in {"portrait", "landscape"}:
        raise _error("INVALID_OPTIONS", "orientation must be portrait or landscape")
    maximum = options.get("max_dimension", MAX_OUTPUT_DIMENSION)
    if isinstance(maximum, bool) or not isinstance(maximum, int) or not 160 <= maximum <= MAX_OUTPUT_DIMENSION:
        raise _error("INVALID_OPTIONS", "max_dimension must be an integer in [160, 1280]")
    maximum -= maximum % 2
    crf = options.get("crf", 23)
    if isinstance(crf, bool) or not isinstance(crf, int) or not 18 <= crf <= 32:
        raise _error("INVALID_OPTIONS", "crf must be an integer in [18, 32]")
    target_width, target_height = (
        (maximum * 9 // 16, maximum) if orientation == "portrait" else (maximum, maximum * 9 // 16)
    )
    target_width -= target_width % 2
    target_height -= target_height % 2
    info = _bounded_source_info(source)
    duration = float(info["duration"])
    temporary = _temporary_output(destination)
    command: list[str | os.PathLike[str]] = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", source,
    ]
    has_audio = "audio" in info["codecs"]
    if not has_audio:
        command += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    command += [
        "-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0",
        "-vf",
        (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            "setsar=1,fps=30"
        ),
        "-af", f"aresample=48000,apad,atrim=duration={_seconds(duration)},asetpts=PTS-STARTPTS",
        "-t", _seconds(duration),
    ]
    command += _encode_args()
    # Replace the default CRF in the fixed encoder profile with the reviewed option.
    command[command.index("23")] = str(crf)
    command += [temporary]
    published = False
    try:
        _run(command, timeout=RENDER_TIMEOUT_SECONDS)
        _publish_new(temporary, destination)
        published = True
        result = probe(destination)
    except Exception:
        _unlink_quietly(temporary)
        if published:
            _unlink_quietly(destination)
        raise
    if result["width"] != target_width or result["height"] != target_height:
        _unlink_quietly(destination)
        raise _error("OUTPUT_VALIDATION_FAILED", "normalized dimensions do not match the contract")
    if result["codecs"].get("video") != "h264" or result["codecs"].get("audio") != "aac":
        _unlink_quietly(destination)
        raise _error("OUTPUT_VALIDATION_FAILED", "normalized codecs do not match H.264/AAC")
    return result


def _validated_clips(clips: Sequence[Mapping[str, Any]], duration: float) -> list[tuple[float, float, str]]:
    if isinstance(clips, (str, bytes)) or not isinstance(clips, Sequence):
        raise _error("INVALID_CLIPS", "clips must be an array")
    if not 1 <= len(clips) <= MAX_CLIPS:
        raise _error("INVALID_CLIPS", "clips must contain 1 to 20 items")
    validated: list[tuple[float, float, str]] = []
    total = 0.0
    previous_end = -1.0
    for index, clip in enumerate(clips):
        if not isinstance(clip, Mapping) or set(clip) != {"start_seconds", "end_seconds", "title"}:
            raise _error("INVALID_CLIP", f"clips[{index}] must contain start_seconds, end_seconds, and title")
        start = _number(clip["start_seconds"], f"clips[{index}].start_seconds")
        end = _number(clip["end_seconds"], f"clips[{index}].end_seconds")
        title = clip["title"]
        if not isinstance(title, str) or len(title) > 200:
            raise _error("INVALID_CLIP", f"clips[{index}].title must be a string of at most 200 characters")
        if start < 0 or end <= start or end > duration + 0.001:
            raise _error("TIMECODE_OUT_OF_RANGE", f"clips[{index}] is outside the source duration")
        if start < previous_end - 0.000001:
            raise _error("CLIPS_OVERLAP", f"clips[{index}] overlaps or is out of order")
        total += end - start
        if total > MAX_HIGHLIGHT_SECONDS + 0.000001:
            raise _error("HIGHLIGHTS_TOO_LONG", "highlight duration exceeds 10 minutes")
        validated.append((start, end, title))
        previous_end = end
    return validated


def cut_highlights(
    src: str | os.PathLike[str],
    dest: str | os.PathLike[str],
    clips: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Cut ordered, non-overlapping intervals and concatenate them exactly."""
    source = _source_path(src)
    destination = _destination_path(dest, suffixes={".mp4", ".mov"}, source=source)
    info = _bounded_source_info(source)
    selected = _validated_clips(clips, float(info["duration"]))
    total = sum(end - start for start, end, _ in selected)
    has_audio = "audio" in info["codecs"]
    filters: list[str] = []
    concat_inputs: list[str] = []
    for index, (start, end, _title) in enumerate(selected):
        filters.append(
            f"[0:v:0]trim=start={_seconds(start)}:end={_seconds(end)},"
            "setpts=PTS-STARTPTS,"
            "scale=w='if(gte(iw,ih),min(1280,iw),-2)':"
            "h='if(gte(iw,ih),-2,min(1280,ih))':flags=lanczos,"
            f"setsar=1,fps=30[v{index}]"
        )
        audio_input = "0:a:0" if has_audio else "1:a:0"
        audio_end = end if has_audio else end - start
        audio_start = start if has_audio else 0.0
        filters.append(
            f"[{audio_input}]atrim=start={_seconds(audio_start)}:end={_seconds(audio_end)},"
            f"asetpts=PTS-STARTPTS,aresample=48000[a{index}]"
        )
        concat_inputs.append(f"[v{index}][a{index}]")
    filters.append(
        "".join(concat_inputs) + f"concat=n={len(selected)}:v=1:a=1[vout][aout]"
    )
    temporary = _temporary_output(destination)
    command: list[str | os.PathLike[str]] = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", source,
    ]
    if not has_audio:
        command += ["-f", "lavfi", "-t", _seconds(total), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    command += [
        "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]", "-t", _seconds(total),
    ]
    command += _encode_args()
    command += [temporary]
    published = False
    try:
        _run(command, timeout=RENDER_TIMEOUT_SECONDS)
        _publish_new(temporary, destination)
        published = True
        result = probe(destination)
    except Exception:
        _unlink_quietly(temporary)
        if published:
            _unlink_quietly(destination)
        raise
    if abs(float(result["duration"]) - total) > 0.10:
        _unlink_quietly(destination)
        raise _error("OUTPUT_VALIDATION_FAILED", "highlight duration does not match selected clips")
    if result["codecs"].get("video") != "h264" or result["codecs"].get("audio") != "aac":
        _unlink_quietly(destination)
        raise _error("OUTPUT_VALIDATION_FAILED", "highlight codecs do not match H.264/AAC")
    return result


def extract_thumbnail(
    src: str | os.PathLike[str], dest_png: str | os.PathLike[str], at_seconds: float
) -> dict[str, Any]:
    """Decode the first exact frame at or after a validated timestamp to PNG."""
    source = _source_path(src)
    destination = _destination_path(dest_png, suffixes={".png"}, source=source)
    info = _bounded_source_info(source)
    at = _number(at_seconds, "at_seconds")
    if at < 0 or at >= float(info["duration"]):
        raise _error("TIMECODE_OUT_OF_RANGE", "at_seconds must be within the source duration")
    temporary = _temporary_output(destination)
    command: list[str | os.PathLike[str]] = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-i", source, "-ss", _seconds(at), "-map", "0:v:0", "-frames:v", "1",
        "-an", "-sn", "-dn", "-map_metadata", "-1", "-threads", "1",
        "-c:v", "png", "-compression_level", "9", "-pred", "mixed", "-f", "image2", temporary,
    ]
    published = False
    try:
        _run(command, timeout=RENDER_TIMEOUT_SECONDS)
        try:
            signature = temporary.read_bytes()[: len(PNG_SIGNATURE)]
        except OSError as exc:
            raise _error("OUTPUT_VALIDATION_FAILED", "thumbnail cannot be read") from exc
        if signature != PNG_SIGNATURE:
            raise _error("OUTPUT_VALIDATION_FAILED", "thumbnail is not a PNG")
        _publish_new(temporary, destination)
        published = True
    except Exception:
        _unlink_quietly(temporary)
        if published:
            _unlink_quietly(destination)
        raise
    try:
        size = destination.stat().st_size
    except OSError as exc:
        _unlink_quietly(destination)
        raise _error("OUTPUT_VALIDATION_FAILED", "thumbnail output cannot be inspected") from exc
    return {"width": info["width"], "height": info["height"], "size": size}


__all__ = [
    "MAX_CLIPS",
    "MAX_HIGHLIGHT_SECONDS",
    "MAX_OUTPUT_DIMENSION",
    "MediaRenderError",
    "cut_highlights",
    "extract_thumbnail",
    "normalize",
    "probe",
]
