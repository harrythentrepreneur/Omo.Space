from __future__ import annotations

import io
import math

import pytest
from PIL import Image

from tools.render.charts import ChartRenderError, render_chart_png


def chart_spec(kind: str = "line") -> dict:
    return {
        "title": "Messages by day",
        "kind": kind,
        "series": [
            {
                "label": "Alex",
                "points": [
                    {"x": "Mon", "y": 12},
                    {"x": "Tue", "y": 19},
                    {"x": "Wed", "y": 14},
                    {"x": "Thu", "y": 28},
                ],
            },
            {
                "label": "Sam",
                "points": [
                    {"x": "Mon", "y": 9},
                    {"x": "Tue", "y": 16},
                    {"x": "Wed", "y": 21},
                    {"x": "Thu", "y": 24},
                ],
            },
        ],
        "x_label": "Day",
        "y_label": "Messages",
        "colors": ["#2563EB", "#EA580C"],
    }


def test_renderer_is_byte_deterministic() -> None:
    assert render_chart_png(chart_spec()) == render_chart_png(chart_spec())


@pytest.mark.parametrize("kind", ["line", "bar", "pie", "histogram"])
def test_each_kind_renders_a_real_png(kind: str) -> None:
    result = render_chart_png(chart_spec(kind))
    assert result.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "PNG"
        assert image.size == (1000, 640)
        assert image.mode == "RGB"


def test_custom_dimensions_are_exact() -> None:
    spec = chart_spec("bar")
    spec["dimensions"] = [720, 480]
    with Image.open(io.BytesIO(render_chart_png(spec))) as image:
        assert image.size == (720, 480)


def test_single_series_pie_reserves_a_category_legend() -> None:
    spec = chart_spec("pie")
    spec["series"] = [spec["series"][0]]
    result = render_chart_png(spec)
    assert result.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.parametrize("bad_kind", ["scatter", "area", "", None])
def test_unknown_kind_is_rejected(bad_kind: object) -> None:
    spec = chart_spec()
    spec["kind"] = bad_kind
    with pytest.raises(ChartRenderError, match="kind must be one of"):
        render_chart_png(spec)


def test_empty_series_is_rejected() -> None:
    spec = chart_spec()
    spec["series"] = []
    with pytest.raises(ChartRenderError, match="series must be a non-empty array"):
        render_chart_png(spec)


def test_empty_points_are_rejected() -> None:
    spec = chart_spec()
    spec["series"][0]["points"] = []
    with pytest.raises(ChartRenderError, match="points must be a non-empty array"):
        render_chart_png(spec)


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_non_finite_values_are_rejected(bad_value: float) -> None:
    spec = chart_spec()
    spec["series"][0]["points"][0]["y"] = bad_value
    with pytest.raises(ChartRenderError, match="finite number"):
        render_chart_png(spec)


def test_series_limit_is_enforced() -> None:
    spec = chart_spec()
    spec["series"] = [
        {"label": f"Series {index}", "points": [{"x": 1, "y": index}]}
        for index in range(21)
    ]
    with pytest.raises(ChartRenderError, match="series exceeds 20"):
        render_chart_png(spec)


def test_total_point_limit_is_enforced() -> None:
    spec = chart_spec()
    spec["series"] = [
        {
            "label": "Too much data",
            "points": [{"x": index, "y": index % 17} for index in range(5001)],
        }
    ]
    with pytest.raises(ChartRenderError, match="exceeds 5000 total points"):
        render_chart_png(spec)


def test_invalid_dimensions_and_colors_are_typed_errors() -> None:
    spec = chart_spec()
    spec["dimensions"] = [200, 100]
    with pytest.raises(ChartRenderError, match="dimensions must be within"):
        render_chart_png(spec)
    spec = chart_spec()
    spec["colors"] = ["blue"]
    with pytest.raises(ChartRenderError, match="six-digit hex"):
        render_chart_png(spec)


def test_pie_rejects_negative_or_zero_total() -> None:
    spec = chart_spec("pie")
    spec["series"] = [{"label": "Bad", "points": [{"x": "A", "y": -1}]}]
    with pytest.raises(ChartRenderError, match="non-negative"):
        render_chart_png(spec)
    spec["series"] = [{"label": "Empty", "points": [{"x": "A", "y": 0}]}]
    with pytest.raises(ChartRenderError, match="positive total"):
        render_chart_png(spec)
