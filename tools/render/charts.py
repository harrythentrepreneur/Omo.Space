#!/usr/bin/env python3
"""Deterministic, dependency-light PNG chart rendering with Pillow."""

from __future__ import annotations

import io
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from PIL import Image, ImageDraw, ImageFont


DEFAULT_DIMENSIONS = (1000, 640)
MAX_SERIES = 20
MAX_POINTS = 5000
KINDS = {"line", "bar", "pie", "histogram"}
PALETTE = (
    "#2563EB", "#EA580C", "#059669", "#7C3AED", "#DC2626",
    "#0891B2", "#CA8A04", "#DB2777", "#4F46E5", "#65A30D",
    "#0F766E", "#C2410C", "#9333EA", "#BE123C", "#0369A1",
    "#A16207", "#047857", "#6D28D9", "#B91C1C", "#475569",
)
HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}\Z")

BACKGROUND = "#F8FAFC"
PLOT_BACKGROUND = "#FFFFFF"
INK = "#172033"
MUTED = "#64748B"
GRID = "#E2E8F0"
AXIS = "#94A3B8"


class ChartRenderError(ValueError):
    """The chart input is invalid or cannot be rendered safely."""


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        # Pillow ships this font as package data, avoiding host-font drift.
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - Pillow versions before scalable default fonts
        return ImageFont.load_default()


def _text(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChartRenderError(f"{field} must be a non-empty string")
    result = value.strip()
    if len(result) > maximum:
        raise ChartRenderError(f"{field} exceeds {maximum} characters")
    return result


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ChartRenderError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ChartRenderError(f"{field} must be a finite number")
    return result


def _x_value(value: Any, field: str) -> float | str:
    if isinstance(value, bool):
        raise ChartRenderError(f"{field} must be a finite number or non-empty string")
    if isinstance(value, (int, float)):
        return _finite(value, field)
    if isinstance(value, str) and value.strip():
        if len(value.strip()) > 100:
            raise ChartRenderError(f"{field} exceeds 100 characters")
        return value.strip()
    raise ChartRenderError(f"{field} must be a finite number or non-empty string")


def _dimensions(value: Any) -> tuple[int, int]:
    if value is None:
        return DEFAULT_DIMENSIONS
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise ChartRenderError("dimensions must be [width, height] integers")
    width, height = value
    if not 480 <= width <= 4096 or not 360 <= height <= 2160:
        raise ChartRenderError("dimensions must be within 480x360 and 4096x2160")
    return width, height


def _validate(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping):
        raise ChartRenderError("chart input must be an object")
    kind = spec.get("kind")
    if kind not in KINDS:
        raise ChartRenderError("kind must be one of: line, bar, pie, histogram")
    raw_series = spec.get("series")
    if not isinstance(raw_series, Sequence) or isinstance(raw_series, (str, bytes)) or not raw_series:
        raise ChartRenderError("series must be a non-empty array")
    if len(raw_series) > MAX_SERIES:
        raise ChartRenderError(f"series exceeds {MAX_SERIES} items")

    series: list[dict[str, Any]] = []
    total_points = 0
    for series_index, item in enumerate(raw_series):
        if not isinstance(item, Mapping):
            raise ChartRenderError(f"series[{series_index}] must be an object")
        label = _text(item.get("label"), f"series[{series_index}].label", 100)
        raw_points = item.get("points")
        if not isinstance(raw_points, Sequence) or isinstance(raw_points, (str, bytes)) or not raw_points:
            raise ChartRenderError(f"series[{series_index}].points must be a non-empty array")
        total_points += len(raw_points)
        if total_points > MAX_POINTS:
            raise ChartRenderError(f"chart exceeds {MAX_POINTS} total points")
        points: list[tuple[float | str, float]] = []
        for point_index, point in enumerate(raw_points):
            prefix = f"series[{series_index}].points[{point_index}]"
            if not isinstance(point, Mapping):
                raise ChartRenderError(f"{prefix} must be an object")
            x = _x_value(point.get("x"), f"{prefix}.x")
            y = _finite(point.get("y"), f"{prefix}.y")
            points.append((x, y))
        series.append({"label": label, "points": points})

    raw_colors = spec.get("colors")
    if raw_colors is None:
        colors = list(PALETTE)
    else:
        if not isinstance(raw_colors, Sequence) or isinstance(raw_colors, (str, bytes)) or not raw_colors:
            raise ChartRenderError("colors must be a non-empty array of hex colors")
        if len(raw_colors) > MAX_SERIES:
            raise ChartRenderError(f"colors exceeds {MAX_SERIES} items")
        colors = []
        for index, color in enumerate(raw_colors):
            if not isinstance(color, str) or not HEX_COLOR.fullmatch(color):
                raise ChartRenderError(f"colors[{index}] must be a six-digit hex color")
            colors.append(color.upper())

    if kind == "pie":
        values = [y for entry in series for _, y in entry["points"]]
        if any(value < 0 for value in values):
            raise ChartRenderError("pie values must be non-negative")
        if sum(values) <= 0:
            raise ChartRenderError("pie values must have a positive total")

    return {
        "title": _text(spec.get("title"), "title", 180),
        "kind": kind,
        "series": series,
        "x_label": _text(spec.get("x_label"), "x_label", 100),
        "y_label": _text(spec.get("y_label"), "y_label", 100),
        "colors": colors,
        "dimensions": _dimensions(spec.get("dimensions")),
    }


def _color(colors: list[str], index: int) -> str:
    return colors[index % len(colors)]


def _label(value: float | str) -> str:
    if isinstance(value, str):
        return value
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{value / 1_000_000:.1f}M".replace(".0M", "M")
    if magnitude >= 1_000:
        return f"{value / 1_000:.1f}k".replace(".0k", "k")
    if magnitude < 0.01:
        return f"{value:.2g}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _range(values: list[float], *, include_zero: bool = True) -> tuple[float, float]:
    low, high = min(values), max(values)
    if include_zero:
        low, high = min(low, 0.0), max(high, 0.0)
    if low == high:
        pad = abs(low) * 0.1 or 1.0
        low, high = low - pad, high + pad
    else:
        pad = (high - low) * 0.08
        low, high = low - pad, high + pad
    return low, high


def _layout(draw: ImageDraw.ImageDraw, spec: dict[str, Any]) -> tuple[tuple[int, int, int, int], int]:
    width, height = spec["dimensions"]
    title_font = _font(max(20, min(34, width // 34)), bold=True)
    title_box = draw.textbbox((0, 0), spec["title"], font=title_font)
    draw.text(((width - (title_box[2] - title_box[0])) / 2, 28), spec["title"], fill=INK, font=title_font)

    legend_width = 0
    pie_slices = sum(len(entry["points"]) for entry in spec["series"])
    if len(spec["series"]) > 1 or (spec["kind"] == "pie" and pie_slices > 1):
        legend_width = min(210, max(145, width // 5))
    left, top, right, bottom = 92, 92, width - 48 - legend_width, height - 82
    if right - left < 250:
        raise ChartRenderError("dimensions are too narrow for the requested series legend")
    return (left, top, right, bottom), legend_width


def _legend(
    draw: ImageDraw.ImageDraw,
    spec: dict[str, Any],
    plot: tuple[int, int, int, int],
    entries: list[tuple[str, str]] | None = None,
) -> None:
    entries = entries or [
        (entry["label"], _color(spec["colors"], index))
        for index, entry in enumerate(spec["series"])
    ]
    if not entries:
        return
    font = _font(12)
    x = plot[2] + 25
    y = plot[1] + 4
    max_y = plot[3] - 12
    for label, color in entries[:20]:
        if y > max_y:
            break
        draw.rounded_rectangle((x, y + 2, x + 12, y + 14), radius=3, fill=color)
        available = max(4, (spec["dimensions"][0] - x - 18) // 7)
        shown = label if len(label) <= available else label[: max(1, available - 1)] + "…"
        draw.text((x + 19, y), shown, fill=INK, font=font)
        y += 25


def _axes(
    draw: ImageDraw.ImageDraw,
    spec: dict[str, Any],
    plot: tuple[int, int, int, int],
    y_range: tuple[float, float],
    x_ticks: list[tuple[float, str]],
) -> None:
    left, top, right, bottom = plot
    font = _font(11)
    label_font = _font(13, bold=True)
    draw.rectangle(plot, fill=PLOT_BACKGROUND)
    y_low, y_high = y_range
    for index in range(6):
        fraction = index / 5
        y = round(bottom - fraction * (bottom - top))
        value = y_low + fraction * (y_high - y_low)
        draw.line((left, y, right, y), fill=GRID, width=1)
        text = _label(value)
        box = draw.textbbox((0, 0), text, font=font)
        draw.text((left - 10 - (box[2] - box[0]), y - 7), text, fill=MUTED, font=font)
    draw.line((left, top, left, bottom), fill=AXIS, width=2)
    draw.line((left, bottom, right, bottom), fill=AXIS, width=2)

    for x, text in x_ticks:
        draw.line((round(x), bottom, round(x), bottom + 5), fill=AXIS, width=1)
        shown = text if len(text) <= 14 else text[:13] + "…"
        box = draw.textbbox((0, 0), shown, font=font)
        draw.text((x - (box[2] - box[0]) / 2, bottom + 10), shown, fill=MUTED, font=font)

    box = draw.textbbox((0, 0), spec["x_label"], font=label_font)
    draw.text(((left + right - (box[2] - box[0])) / 2, spec["dimensions"][1] - 32), spec["x_label"], fill=INK, font=label_font)
    y_layer = Image.new("RGBA", (bottom - top + 1, 28), (0, 0, 0, 0))
    y_draw = ImageDraw.Draw(y_layer)
    y_draw.text((0, 4), spec["y_label"], fill=INK, font=label_font)
    rotated = y_layer.rotate(90, expand=True)
    draw._image.alpha_composite(rotated, (22, top + max(0, (bottom - top - rotated.height) // 2)))


def _numeric_x(series: list[dict[str, Any]]) -> bool:
    return all(not isinstance(x, str) for entry in series for x, _ in entry["points"])


def _xy(value: float, bounds: tuple[float, float], start: int, end: int, *, invert: bool = False) -> float:
    fraction = (value - bounds[0]) / (bounds[1] - bounds[0])
    return end - fraction * (end - start) if invert else start + fraction * (end - start)


def _render_line(draw: ImageDraw.ImageDraw, spec: dict[str, Any], plot: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = plot
    ys = [y for entry in spec["series"] for _, y in entry["points"]]
    y_range = _range(ys)
    numeric = _numeric_x(spec["series"])
    if numeric:
        xs = [float(x) for entry in spec["series"] for x, _ in entry["points"]]
        x_range = _range(xs, include_zero=False)
        x_ticks = [
            (_xy(x_range[0] + i * (x_range[1] - x_range[0]) / 4, x_range, left, right),
             _label(x_range[0] + i * (x_range[1] - x_range[0]) / 4))
            for i in range(5)
        ]
        x_pos = lambda value: _xy(float(value), x_range, left, right)
    else:
        categories = list(dict.fromkeys(str(x) for entry in spec["series"] for x, _ in entry["points"]))
        indexes = {value: index for index, value in enumerate(categories)}
        denominator = max(1, len(categories) - 1)
        x_pos = lambda value: left + indexes[str(value)] * (right - left) / denominator
        step = max(1, math.ceil(len(categories) / 6))
        x_ticks = [(x_pos(value), value) for value in categories[::step]]
    _axes(draw, spec, plot, y_range, x_ticks)
    for index, entry in enumerate(spec["series"]):
        color = _color(spec["colors"], index)
        points = [(round(x_pos(x)), round(_xy(y, y_range, top, bottom, invert=True))) for x, y in entry["points"]]
        if len(points) > 1:
            draw.line(points, fill=color, width=3, joint="curve")
        radius = 4
        for x, y in points:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=PLOT_BACKGROUND, outline=color, width=3)
    if len(spec["series"]) > 1:
        _legend(draw, spec, plot)


def _render_bar(draw: ImageDraw.ImageDraw, spec: dict[str, Any], plot: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = plot
    categories = list(dict.fromkeys(str(x) for entry in spec["series"] for x, _ in entry["points"]))
    if len(categories) > 60:
        raise ChartRenderError("bar charts support at most 60 categories")
    values_by_series = [{str(x): y for x, y in entry["points"]} for entry in spec["series"]]
    ys = [y for values in values_by_series for y in values.values()]
    y_range = _range(ys)
    group_width = (right - left) / len(categories)
    step = max(1, math.ceil(len(categories) / 8))
    x_ticks = [(left + (i + 0.5) * group_width, category) for i, category in enumerate(categories) if i % step == 0]
    _axes(draw, spec, plot, y_range, x_ticks)
    zero_y = _xy(0, y_range, top, bottom, invert=True)
    inner = group_width * 0.76
    bar_width = max(1.0, inner / len(spec["series"]))
    for category_index, category in enumerate(categories):
        group_left = left + category_index * group_width + (group_width - inner) / 2
        for series_index, values in enumerate(values_by_series):
            if category not in values:
                continue
            value_y = _xy(values[category], y_range, top, bottom, invert=True)
            x0 = group_left + series_index * bar_width
            x1 = x0 + max(1, bar_width - 1)
            draw.rectangle((round(x0), round(min(zero_y, value_y)), round(x1), round(max(zero_y, value_y))), fill=_color(spec["colors"], series_index))
    if len(spec["series"]) > 1:
        _legend(draw, spec, plot)


def _pie_entries(spec: dict[str, Any]) -> list[tuple[str, float, str]]:
    if len(spec["series"]) == 1:
        return [
            (str(x), y, _color(spec["colors"], index))
            for index, (x, y) in enumerate(spec["series"][0]["points"])
            if y > 0
        ]
    return [
        (entry["label"], sum(y for _, y in entry["points"]), _color(spec["colors"], index))
        for index, entry in enumerate(spec["series"])
        if sum(y for _, y in entry["points"]) > 0
    ]


def _render_pie(draw: ImageDraw.ImageDraw, spec: dict[str, Any], plot: tuple[int, int, int, int]) -> None:
    entries = _pie_entries(spec)
    if len(entries) > 20:
        raise ChartRenderError("pie charts support at most 20 slices")
    left, top, right, bottom = plot
    size = min(right - left, bottom - top) - 24
    x0 = left + (right - left - size) // 2
    y0 = top + (bottom - top - size) // 2
    box = (x0, y0, x0 + size, y0 + size)
    total = sum(value for _, value, _ in entries)
    start = -90.0
    for _, value, color in entries:
        end = start + 360.0 * value / total
        draw.pieslice(box, start=start, end=end, fill=color, outline=PLOT_BACKGROUND, width=3)
        start = end
    inner_pad = round(size * 0.31)
    draw.ellipse((x0 + inner_pad, y0 + inner_pad, x0 + size - inner_pad, y0 + size - inner_pad), fill=PLOT_BACKGROUND)
    total_font = _font(max(16, size // 18), bold=True)
    total_text = _label(total)
    text_box = draw.textbbox((0, 0), total_text, font=total_font)
    draw.text((x0 + (size - text_box[2]) / 2, y0 + (size - text_box[3]) / 2), total_text, fill=INK, font=total_font)
    _legend(draw, spec, plot, [(f"{label}  {value / total:.0%}", color) for label, value, color in entries])


def _render_histogram(draw: ImageDraw.ImageDraw, spec: dict[str, Any], plot: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = plot
    all_values = [y for entry in spec["series"] for _, y in entry["points"]]
    low, high = min(all_values), max(all_values)
    if low == high:
        low, high = low - 0.5, high + 0.5
    bin_count = min(20, max(5, round(math.sqrt(len(all_values)))))
    bin_width = (high - low) / bin_count
    counts: list[list[int]] = []
    for entry in spec["series"]:
        bins = [0] * bin_count
        for _, value in entry["points"]:
            index = min(bin_count - 1, int((value - low) / bin_width))
            bins[index] += 1
        counts.append(bins)
    y_range = (0.0, max(max(row) for row in counts) * 1.12 or 1.0)
    x_ticks = [
        (left + i * (right - left) / 4, _label(low + i * (high - low) / 4))
        for i in range(5)
    ]
    _axes(draw, spec, plot, y_range, x_ticks)
    group_width = (right - left) / bin_count
    bar_width = max(1.0, group_width * 0.9 / len(counts))
    for bin_index in range(bin_count):
        group_left = left + bin_index * group_width + group_width * 0.05
        for series_index, bins in enumerate(counts):
            value_y = _xy(bins[bin_index], y_range, top, bottom, invert=True)
            x0 = group_left + series_index * bar_width
            draw.rectangle((round(x0), round(value_y), round(x0 + max(1, bar_width - 1)), bottom), fill=_color(spec["colors"], series_index))
    if len(spec["series"]) > 1:
        _legend(draw, spec, plot)


def render_chart_png(chart: Mapping[str, Any]) -> bytes:
    """Validate a chart contract and return deterministic RGB PNG bytes."""
    spec = _validate(chart)
    image = Image.new("RGBA", spec["dimensions"], BACKGROUND)
    draw = ImageDraw.Draw(image)
    plot, _ = _layout(draw, spec)
    renderers = {
        "line": _render_line,
        "bar": _render_bar,
        "pie": _render_pie,
        "histogram": _render_histogram,
    }
    renderers[spec["kind"]](draw, spec, plot)
    output = io.BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=False, compress_level=9)
    return output.getvalue()


__all__ = ["ChartRenderError", "DEFAULT_DIMENSIONS", "render_chart_png"]
