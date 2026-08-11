"""Safe audio acquisition and deterministic FFmpeg media assembly.

All paths passed here are expected to live in a request-scoped directory.
Commands are argument arrays (never shell strings), and the command runner is
injectable so tests can assert exact FFmpeg/ffprobe contracts.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import os
import shutil
import socket
import subprocess
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urljoin, urlsplit

from PIL import Image, ImageDraw, ImageFont, ImageOps


FPS = 30
WIDTH = 1080
HEIGHT = 1920
SEMANTIC_FPS = 3
CELL_FRAMES = FPS // SEMANTIC_FPS
BLEND_FRAMES = 6
HOLD_FRAMES = CELL_FRAMES - BLEND_FRAMES
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_REDIRECTS = 3


class MediaError(RuntimeError):
    """A media input, subprocess, or output contract failed."""


class UnsafeAudioURLError(ValueError):
    """An audio URL failed the SSRF policy."""


@dataclass(frozen=True)
class AudioInfo:
    path: str
    source: str
    source_duration_seconds: float
    duration_seconds: float
    trimmed: bool
    codec: str
    sample_rate: int
    channels: int
    bytes: int


@dataclass(frozen=True)
class AssemblyResult:
    video_path: str
    frame_count: int
    duration_seconds: float
    pair_count: int
    mezzanine_path: str
    filter_method: str


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
Resolver = Callable[..., Sequence[tuple[Any, ...]]]
VisualValidator = Callable[[Path], Any]


def _run(
    command: Sequence[str | os.PathLike[str]],
    *,
    runner: CommandRunner = subprocess.run,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        return runner(
            [str(value) for value in command],
            check=True,
            capture_output=capture_output,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()[-1200:]
        raise MediaError(f"command failed ({exc.returncode}): {stderr}") from exc
    except FileNotFoundError as exc:
        raise MediaError(f"required executable is unavailable: {command[0]}") from exc


def _resolved_addresses(host: str, port: int, resolver: Resolver) -> set[ipaddress._BaseAddress]:
    try:
        records = resolver(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise UnsafeAudioURLError(f"audio host DNS resolution failed: {host}") from exc
    addresses: set[ipaddress._BaseAddress] = set()
    for record in records:
        sockaddr = record[4]
        if not sockaddr:
            continue
        try:
            address = ipaddress.ip_address(sockaddr[0].split("%", 1)[0])
        except ValueError as exc:
            raise UnsafeAudioURLError("resolver returned an invalid IP address") from exc
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        addresses.add(address)
    if not addresses:
        raise UnsafeAudioURLError(f"audio host has no resolved address: {host}")
    return addresses


def validate_https_audio_url(
    url: str,
    *,
    resolver: Resolver = socket.getaddrinfo,
) -> str:
    """Validate an HTTPS URL and every currently resolved target address."""
    if not isinstance(url, str) or not url or len(url) > 2048:
        raise UnsafeAudioURLError("audio_url must be a non-empty URL <= 2048 characters")
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise UnsafeAudioURLError("audio_url must use https")
    if not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeAudioURLError("audio_url must have a host and no userinfo")
    if parsed.fragment:
        raise UnsafeAudioURLError("audio_url fragments are not accepted")
    try:
        port = parsed.port or 443
    except ValueError as exc:
        raise UnsafeAudioURLError("audio_url has an invalid port") from exc
    if port != 443:
        raise UnsafeAudioURLError("audio_url must use HTTPS port 443")
    for address in _resolved_addresses(parsed.hostname, port, resolver):
        # is_global rejects loopback, private, link-local, multicast, reserved,
        # unspecified, documentation ranges, and other non-public addresses.
        if not address.is_global:
            raise UnsafeAudioURLError(f"audio_url resolves to non-public address {address}")
    return url


def download_https_audio(
    url: str,
    destination: Path,
    *,
    max_bytes: int = MAX_AUDIO_BYTES,
    max_redirects: int = MAX_REDIRECTS,
    resolver: Resolver = socket.getaddrinfo,
    client: Any | None = None,
) -> Path:
    """Download with manual, revalidated redirects and a hard decoded byte cap.

    Production egress should additionally be restricted by the container or an
    outbound proxy. DNS validation alone cannot eliminate every rebinding race.
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if not 0 <= max_redirects <= 5:
        raise ValueError("max_redirects must be in [0, 5]")
    try:
        import httpx
    except ImportError as exc:
        raise MediaError("httpx is required for audio_url acquisition") from exc
    owns_client = client is None
    http = client or httpx.Client(
        follow_redirects=False,
        timeout=httpx.Timeout(30.0, connect=10.0),
        trust_env=False,
        headers={"User-Agent": "omo-demello-awake/1"},
    )
    current = url
    try:
        for redirect_count in range(max_redirects + 1):
            validate_https_audio_url(current, resolver=resolver)
            with http.stream("GET", current, headers={"Accept": "audio/*"}) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    if redirect_count >= max_redirects:
                        raise UnsafeAudioURLError("audio_url exceeded redirect limit")
                    location = response.headers.get("location")
                    if not location:
                        raise UnsafeAudioURLError("audio redirect has no Location")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                length = response.headers.get("content-length")
                if length:
                    try:
                        if int(length) > max_bytes:
                            raise MediaError("audio download exceeds byte limit")
                    except ValueError as exc:
                        raise MediaError("invalid Content-Length from audio host") from exc
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type and not (
                    content_type.startswith("audio/")
                    or content_type in {"application/octet-stream", "video/mp4"}
                ):
                    raise MediaError(f"unsupported audio Content-Type: {content_type}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_name(destination.name + ".part")
                total = 0
                try:
                    with temporary.open("wb") as handle:
                        for chunk in response.iter_bytes(64 * 1024):
                            total += len(chunk)
                            if total > max_bytes:
                                raise MediaError("audio download exceeds byte limit")
                            handle.write(chunk)
                    if total == 0:
                        raise MediaError("audio download is empty")
                    os.replace(temporary, destination)
                finally:
                    temporary.unlink(missing_ok=True)
                return destination
        raise UnsafeAudioURLError("audio_url redirect handling failed")
    finally:
        if owns_client:
            http.close()


def acquire_audio(
    request: Mapping[str, Any],
    destination: Path,
    *,
    audio_refs: Mapping[str, Path],
    downloader: Callable[..., Path] = download_https_audio,
    max_bytes: int = MAX_AUDIO_BYTES,
) -> tuple[Path, str]:
    """Acquire exactly one URL or allowlisted ref; refs are never paths."""
    audio_url = request.get("audio_url")
    audio_ref = request.get("audio_ref")
    if bool(audio_url) == bool(audio_ref):
        raise MediaError("exactly one of audio_url or audio_ref is required")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if audio_ref:
        if not isinstance(audio_ref, str) or audio_ref not in audio_refs:
            raise MediaError("audio_ref is not allowlisted")
        source = Path(audio_refs[audio_ref]).resolve(strict=True)
        if not source.is_file() or source.stat().st_size > max_bytes:
            raise MediaError("allowlisted audio_ref is invalid or oversized")
        shutil.copyfile(source, destination)
        return destination, f"audio_ref:{audio_ref}"
    if not isinstance(audio_url, str):
        raise MediaError("audio_url must be a string")
    downloader(audio_url, destination, max_bytes=max_bytes)
    return destination, "audio_url"


def ffprobe_json(
    path: Path,
    *,
    count_frames: bool = False,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    command: list[str | Path] = ["ffprobe", "-v", "error"]
    if count_frames:
        command += ["-count_frames"]
    command += ["-show_format", "-show_streams", "-of", "json", path]
    result = _run(command, runner=runner, capture_output=True)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MediaError("ffprobe returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise MediaError("ffprobe JSON is not an object")
    return payload


def _duration(probe: Mapping[str, Any]) -> float:
    try:
        value = float(probe["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MediaError("media duration is unavailable") from exc
    if not math.isfinite(value) or value <= 0:
        raise MediaError("media duration is invalid")
    return value


def normalize_audio(
    source: Path,
    destination: Path,
    *,
    min_seconds: float,
    max_seconds: float,
    runner: CommandRunner = subprocess.run,
) -> AudioInfo:
    """Probe and normalize to mono 48 kHz AAC, trimming only the long tail."""
    if min_seconds <= 0 or max_seconds < min_seconds:
        raise ValueError("invalid duration bounds")
    source_probe = ffprobe_json(source, runner=runner)
    source_duration = _duration(source_probe)
    if source_duration + 0.02 < min_seconds:
        raise MediaError(
            f"audio duration {source_duration:.3f}s is below minimum {min_seconds:.3f}s"
        )
    target_duration = min(source_duration, max_seconds)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.stem + ".tmp" + destination.suffix)
    _run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-i", source, "-map", "0:a:0", "-vn",
            "-af", (
                "asetpts=PTS-STARTPTS,"
                f"apad=pad_dur={target_duration:.9f},"
                f"atrim=duration={target_duration:.9f},asetpts=PTS-STARTPTS"
            ),
            "-ac", "1", "-ar", "48000", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", temporary,
        ],
        runner=runner,
    )
    os.replace(temporary, destination)
    normalized_probe = ffprobe_json(destination, runner=runner)
    duration = _duration(normalized_probe)
    if duration + 0.05 < min_seconds or duration > max_seconds + 0.10:
        raise MediaError(f"normalized audio duration is outside bounds: {duration:.3f}s")
    stream = next(
        (value for value in normalized_probe.get("streams", []) if value.get("codec_type") == "audio"),
        None,
    )
    if not isinstance(stream, Mapping):
        raise MediaError("normalized audio has no audio stream")
    return AudioInfo(
        path=str(destination),
        source="normalized",
        source_duration_seconds=source_duration,
        duration_seconds=duration,
        trimmed=source_duration > max_seconds + 0.02,
        codec=str(stream.get("codec_name", "")),
        sample_rate=int(stream.get("sample_rate", 0)),
        channels=int(stream.get("channels", 0)),
        bytes=destination.stat().st_size,
    )


def delta_expression(progress: str = "(1-P)", k: float = 1.0) -> str:
    if k < 0:
        raise ValueError("delta acceleration cannot be negative")
    return (
        "if(eq(A,B),A,"
        f"A+(B-A)*clip({progress}*(1+{k:.6f}*abs(A-B)/255),0,1))"
    )


def _frame_count(path: Path, *, runner: CommandRunner) -> int:
    probe = ffprobe_json(path, count_frames=True, runner=runner)
    stream = next(
        (value for value in probe.get("streams", []) if value.get("codec_type") == "video"),
        None,
    )
    if not isinstance(stream, Mapping):
        raise MediaError("video stream is unavailable")
    raw = stream.get("nb_read_frames") or stream.get("nb_frames")
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise MediaError("video frame count is unavailable") from exc


def _audio_packet_duration(path: Path, *, runner: CommandRunner) -> float:
    """Measure the decoded audio timeline without relying on container metadata.

    Some ffprobe builds omit an MP4 audio stream's ``duration`` even though its
    packet timeline is complete. The last packet end timestamp is stable across
    those builds and still detects a genuinely truncated audio stream.
    """
    result = _run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "packet=pts_time,duration_time", "-of", "json", path,
        ],
        runner=runner,
        capture_output=True,
    )
    try:
        payload = json.loads(result.stdout)
        packets = payload["packets"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise MediaError("audio packet timeline is unavailable") from exc
    ends: list[float] = []
    for packet in packets if isinstance(packets, list) else []:
        try:
            ends.append(float(packet["pts_time"]) + float(packet.get("duration_time", 0)))
        except (KeyError, TypeError, ValueError):
            continue
    if not ends or not math.isfinite(max(ends)) or max(ends) <= 0:
        raise MediaError("audio packet timeline is invalid")
    return max(ends)


def _render_pair(
    source: Path,
    target: Path,
    output: Path,
    *,
    runner: CommandRunner,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    graph = output.with_suffix(".filter.txt")
    base = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1,format=gbrp"
    )
    graph.write_text(
        ";".join(
            [
                f"[0:v]{base}[a]",
                f"[1:v]{base}[b]",
                (
                    f"[a][b]xfade=transition=custom:duration={BLEND_FRAMES / FPS:.9f}:"
                    f"offset=0:expr='{delta_expression()}',trim=end_frame={CELL_FRAMES},"
                    "setpts=PTS-STARTPTS,format=gbrp[outv]"
                ),
            ]
        )
        + "\n"
    )
    temporary = output.with_name(output.stem + ".tmp.mkv")
    _run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-loop", "1", "-framerate", str(FPS), "-t", "0.5", "-i", source,
            "-loop", "1", "-framerate", str(FPS), "-t", "0.5", "-i", target,
            "-filter_complex_script", graph, "-map", "[outv]", "-frames:v", str(CELL_FRAMES),
            "-r", str(FPS), "-an", "-c:v", "ffv1", "-level", "3", "-g", "1",
            "-pix_fmt", "gbrp", temporary,
        ],
        runner=runner,
    )
    if _frame_count(temporary, runner=runner) != CELL_FRAMES:
        temporary.unlink(missing_ok=True)
        raise MediaError("pair mezzanine frame count mismatch")
    os.replace(temporary, output)


def _render_hold(source: Path, output: Path, *, runner: CommandRunner) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.stem + ".tmp.mkv")
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},trim=end_frame={CELL_FRAMES},"
        "setpts=PTS-STARTPTS,setsar=1,format=gbrp"
    )
    _run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-loop", "1", "-framerate", str(FPS), "-t", "0.5", "-i", source,
            "-vf", vf, "-frames:v", str(CELL_FRAMES), "-r", str(FPS), "-an",
            "-c:v", "ffv1", "-level", "3", "-g", "1", "-pix_fmt", "gbrp", temporary,
        ],
        runner=runner,
    )
    if _frame_count(temporary, runner=runner) != CELL_FRAMES:
        temporary.unlink(missing_ok=True)
        raise MediaError("hold mezzanine frame count mismatch")
    os.replace(temporary, output)


def assemble_video(
    semantic_frames: Sequence[Path | str | Mapping[str, Any]],
    audio: Path,
    output: Path,
    work_dir: Path,
    *,
    duration_seconds: float,
    runner: CommandRunner = subprocess.run,
    encoder_preset: str = "fast",
    crf: int = 20,
    transition_mode: str = "difference-blend",
) -> AssemblyResult:
    """Render 3 fps authored cells using a declared topology policy.

    ``topology-step`` holds each fully redrawn semantic cell for ten delivery
    frames. It is intentionally used for procedural geometry: unlike a pixel
    crossfade, it cannot create two spatial copies of one moving story mark or
    gray ghost ink between them.
    """
    if not semantic_frames:
        raise ValueError("semantic frames are required")
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if transition_mode not in {"difference-blend", "topology-step"}:
        raise ValueError("unsupported transition_mode")
    paths: list[Path] = []
    for value in semantic_frames:
        path = Path(str(value["path"])) if isinstance(value, Mapping) else Path(value)
        if not path.is_file():
            raise MediaError(f"missing semantic frame: {path}")
        paths.append(path)
    expected_semantic = int(math.ceil(duration_seconds * SEMANTIC_FPS - 1e-9))
    if len(paths) != expected_semantic:
        raise MediaError(
            f"expected {expected_semantic} semantic frames for {duration_seconds:.3f}s; found {len(paths)}"
        )
    work_dir.mkdir(parents=True, exist_ok=True)
    pair_dir = work_dir / "pairs"
    cells: list[Path] = []
    if transition_mode == "topology-step":
        for index, source in enumerate(paths):
            cell = pair_dir / f"{index:03d}-redraw.mkv"
            _render_hold(source, cell, runner=runner)
            cells.append(cell)
    else:
        for index, source in enumerate(paths[:-1]):
            cell = pair_dir / f"{index:03d}.mkv"
            _render_pair(source, paths[index + 1], cell, runner=runner)
            cells.append(cell)
        final_hold = pair_dir / f"{len(paths) - 1:03d}-hold.mkv"
        _render_hold(paths[-1], final_hold, runner=runner)
        cells.append(final_hold)

    concat_path = work_dir / "semantic.ffconcat"
    concat_lines = ["ffconcat version 1.0"]
    for cell in cells:
        escaped = str(cell.resolve()).replace("'", "'\\''")
        concat_lines.extend([f"file '{escaped}'", f"duration {CELL_FRAMES / FPS:.9f}"])
    concat_path.write_text("\n".join(concat_lines) + "\n")
    mezzanine = work_dir / "semantic-ffv1.mkv"
    temporary_mezzanine = work_dir / "semantic-ffv1.tmp.mkv"
    _run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_path, "-map", "0:v:0",
            "-c:v", "copy", "-an", temporary_mezzanine,
        ],
        runner=runner,
    )
    os.replace(temporary_mezzanine, mezzanine)
    if _frame_count(mezzanine, runner=runner) != len(paths) * CELL_FRAMES:
        raise MediaError("semantic mezzanine frame count mismatch")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_name(output.stem + ".tmp.mp4")
    target_frames = max(1, round(duration_seconds * FPS))
    quantized_duration = target_frames / FPS
    filter_graph = ";".join(
        [
            (
                f"[0:v]fps={FPS},trim=end_frame={target_frames},"
                "setpts=PTS-STARTPTS,format=yuv420p[outv]"
            ),
            "[1:a]asetpts=PTS-STARTPTS[voice]",
            "[2:a]asetpts=PTS-STARTPTS[silence]",
            (
                "[voice][silence]amix=inputs=2:duration=longest:"
                "dropout_transition=0,volume=2,"
                f"atrim=duration={quantized_duration:.9f},"
                "asetpts=PTS-STARTPTS[outa]"
            ),
        ]
    )
    _run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-i", mezzanine, "-i", audio,
            "-f", "lavfi", "-i", (
                "anullsrc=channel_layout=mono:sample_rate=48000:"
                f"d={quantized_duration:.9f}"
            ),
            "-filter_complex", filter_graph, "-map", "[outv]", "-map", "[outa]",
            "-frames:v", str(target_frames), "-r", str(FPS), "-c:v", "libx264",
            "-preset", encoder_preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{quantized_duration:.9f}",
            "-movflags", "+faststart", temporary_output,
        ],
        runner=runner,
    )
    if _frame_count(temporary_output, runner=runner) != target_frames:
        temporary_output.unlink(missing_ok=True)
        raise MediaError("delivery frame count mismatch")
    os.replace(temporary_output, output)
    return AssemblyResult(
        video_path=str(output),
        frame_count=target_frames,
        duration_seconds=quantized_duration,
        pair_count=0 if transition_mode == "topology-step" else max(0, len(paths) - 1),
        mezzanine_path=str(mezzanine),
        filter_method=(
            "topology-preserving authored redraw: 10-frame semantic hold; "
            "no dissolve; fixed camera"
            if transition_mode == "topology-step"
            else (
                f"difference-preserving custom xfade: {BLEND_FRAMES} blend frames + "
                f"{HOLD_FRAMES} target landing frames; fixed camera"
            )
        ),
    )


def make_contact_sheet(
    semantic_frames: Sequence[Path | str | Mapping[str, Any]],
    output: Path,
    *,
    columns: int = 6,
    thumb_width: int = 180,
    thumb_height: int = 320,
) -> Path:
    if not semantic_frames:
        raise ValueError("semantic frames are required")
    if columns < 1:
        raise ValueError("columns must be positive")
    rows = math.ceil(len(semantic_frames) / columns)
    label_height = 24
    sheet = Image.new(
        "RGB",
        (columns * thumb_width, rows * (thumb_height + label_height)),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, value in enumerate(semantic_frames):
        if isinstance(value, Mapping):
            path = Path(str(value["path"]))
            label = f"{value.get('fid', f'F{index:03d}')} {value.get('verb', '')}".strip()
        else:
            path = Path(value)
            label = path.stem
        with Image.open(path) as source:
            thumb = ImageOps.fit(
                source.convert("RGB"),
                (thumb_width, thumb_height),
                method=Image.Resampling.LANCZOS,
            )
        x = (index % columns) * thumb_width
        y = (index // columns) * (thumb_height + label_height)
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y + thumb_height, x + thumb_width, y + thumb_height + label_height), fill="white")
        draw.text((x + 4, y + thumb_height + 5), label[:28], fill=(26, 26, 26), font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() in {".jpg", ".jpeg"}:
        sheet.save(output, format="JPEG", quality=92, optimize=True)
    else:
        sheet.save(output, format="PNG", optimize=True)
    return output


def _atom_order(path: Path) -> dict[str, Any]:
    # Delivery files are bounded short clips; reading them once is acceptable.
    data = path.read_bytes()
    moov = data.find(b"moov")
    mdat = data.find(b"mdat")
    return {"moov_offset": moov, "mdat_offset": mdat, "faststart": 0 <= moov < mdat}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_video_samples(
    video: Path,
    output_dir: Path,
    *,
    duration_seconds: float,
    count: int = 5,
    runner: CommandRunner = subprocess.run,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if count < 1:
        return []
    timestamps = [
        min(max(0.0, duration_seconds - 1.0 / FPS), duration_seconds * index / max(count - 1, 1))
        for index in range(count)
    ]
    paths: list[Path] = []
    for index, timestamp in enumerate(timestamps):
        path = output_dir / f"sample-{index:02d}.png"
        _run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-ss", f"{timestamp:.6f}", "-i", video, "-frames:v", "1", path,
            ],
            runner=runner,
        )
        if not path.is_file() or path.stat().st_size == 0:
            raise MediaError("failed to extract video QA sample")
        paths.append(path)
    return paths


def qa_video(
    video: Path,
    *,
    expected_duration_seconds: float,
    expected_frames: int,
    qa_dir: Path,
    runner: CommandRunner = subprocess.run,
    visual_validator: VisualValidator | None = None,
) -> dict[str, Any]:
    """Probe, fully decode, sample visual style, and checksum a delivery."""
    probe = ffprobe_json(video, count_frames=True, runner=runner)
    duration = _duration(probe)
    video_stream = next(
        (value for value in probe.get("streams", []) if value.get("codec_type") == "video"),
        None,
    )
    audio_stream = next(
        (value for value in probe.get("streams", []) if value.get("codec_type") == "audio"),
        None,
    )
    if not isinstance(video_stream, Mapping):
        raise MediaError("delivery has no video stream")
    frame_rate = str(video_stream.get("r_frame_rate", "0/1"))
    try:
        fps = float(Fraction(frame_rate))
    except (ValueError, ZeroDivisionError) as exc:
        raise MediaError("delivery frame rate is invalid") from exc
    frame_count = _frame_count(video, runner=runner)
    audio_duration = _audio_packet_duration(video, runner=runner)
    atoms = _atom_order(video)
    checks = {
        "duration": abs(duration - expected_duration_seconds) <= 0.10,
        "audio_duration": abs(audio_duration - expected_duration_seconds) <= 0.10,
        "frame_count": frame_count == expected_frames,
        "resolution": (
            int(video_stream.get("width", 0)) == WIDTH
            and int(video_stream.get("height", 0)) == HEIGHT
        ),
        "fps": abs(fps - FPS) < 1e-9,
        "video_h264": video_stream.get("codec_name") == "h264",
        "audio_aac": isinstance(audio_stream, Mapping) and audio_stream.get("codec_name") == "aac",
        "faststart": atoms["faststart"],
        "nonempty": video.is_file() and video.stat().st_size > 0,
    }
    _run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", video, "-f", "null", "-"],
        runner=runner,
    )
    visual_reports: list[Any] = []
    samples = extract_video_samples(
        video,
        qa_dir / "samples",
        duration_seconds=duration,
        runner=runner,
    )
    if visual_validator is not None:
        for sample in samples:
            report = visual_validator(sample)
            visual_reports.append(asdict(report) if hasattr(report, "__dataclass_fields__") else report)
        checks["visual_samples"] = all(bool(item.get("passed")) for item in visual_reports)
    passed = all(checks.values())
    result = {
        "passed": passed,
        "checks": checks,
        "duration_seconds": duration,
        "frame_count": frame_count,
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "fps": fps,
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name") if isinstance(audio_stream, Mapping) else None,
        "audio_duration_seconds": audio_duration,
        "bytes": video.stat().st_size,
        "sha256": _sha256_file(video),
        "visual_samples": visual_reports,
        **atoms,
    }
    if not passed:
        failed = ", ".join(name for name, ok in checks.items() if not ok)
        raise MediaError(
            f"delivery QA failed: {failed} | "
            f"audio_duration_seconds={audio_duration:.6f} | "
            f"expected_duration_seconds={expected_duration_seconds:.6f}"
        )
    return result


__all__ = [
    "AudioInfo",
    "AssemblyResult",
    "BLEND_FRAMES",
    "CELL_FRAMES",
    "FPS",
    "HEIGHT",
    "HOLD_FRAMES",
    "MAX_AUDIO_BYTES",
    "MediaError",
    "SEMANTIC_FPS",
    "UnsafeAudioURLError",
    "WIDTH",
    "acquire_audio",
    "assemble_video",
    "delta_expression",
    "download_https_audio",
    "extract_video_samples",
    "ffprobe_json",
    "make_contact_sheet",
    "normalize_audio",
    "qa_video",
    "validate_https_audio_url",
]
