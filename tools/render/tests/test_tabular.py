from __future__ import annotations

import math

import pytest

from tools.render.tabular import TabularError, analyze_csv, parse_csv, statistics


def test_comma_csv_parses_typed_cells_and_preserves_leading_zero() -> None:
    assert parse_csv("name,age,score,code\nAna,8,4.5,007\nBo,9,3,12\n") == [
        {"name": "Ana", "age": 8, "score": 4.5, "code": "007"},
        {"name": "Bo", "age": 9, "score": 3, "code": 12},
    ]


def test_quoted_commas_and_escaped_quotes() -> None:
    rows = parse_csv('name,note\nAda,"hello, world"\nBob,"said ""yes"""\n')
    assert rows == [{"name": "Ada", "note": "hello, world"}, {"name": "Bob", "note": 'said "yes"'}]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("name;value\nA;1\nB;2\n", [{"name": "A", "value": 1}, {"name": "B", "value": 2}]),
        ("name\tvalue\nA\t1\nB\t2\n", [{"name": "A", "value": 1}, {"name": "B", "value": 2}]),
    ],
)
def test_semicolon_and_tab_detection(text: str, expected: list[dict]) -> None:
    assert parse_csv(text) == expected


def test_numeric_statistics_and_linear_percentiles() -> None:
    result = analyze_csv("group,value\na,1\na,2\nb,3\nb,4\n")
    assert result["columns"] == ["group", "value"]
    assert result["row_count"] == 4
    assert result["stats"]["group"] == {"count": 4, "mode": "a"}
    numeric = result["stats"]["value"]
    assert numeric["count"] == 4
    assert numeric["sum"] == 10
    assert numeric["mean"] == 2.5
    assert numeric["median"] == 2.5
    assert numeric["min"] == 1
    assert numeric["max"] == 4
    assert numeric["stdev"] == pytest.approx(math.sqrt(5 / 3))
    assert numeric["percentiles"] == {"p25": 1.75, "p50": 2.5, "p75": 3.25}


def test_mixed_column_falls_back_honestly_to_categorical() -> None:
    result = analyze_csv("item,value\na,10\nb,unknown\nc,10\n")
    assert result["stats"]["value"] == {"count": 3, "mode": 10}
    assert result["notes"] == ["value: mixed numeric/text values treated as categorical"]


def test_required_numeric_mixed_column_is_typed_error() -> None:
    rows = parse_csv("item,value\na,10\nb,unknown\n")
    with pytest.raises(TabularError) as caught:
        statistics(rows, numeric_columns=["value"])
    assert caught.value.code == "NON_NUMERIC_COLUMN"


@pytest.mark.parametrize("text", ["", "a,b\n", " , \n1,2\n"])
def test_empty_tables_are_typed(text: str) -> None:
    with pytest.raises(TabularError) as caught:
        parse_csv(text)
    assert caught.value.code == "EMPTY_TABLE"


def test_one_numeric_value_is_insufficient_for_sample_stdev() -> None:
    with pytest.raises(TabularError) as caught:
        analyze_csv("name,value\na,1\n")
    assert caught.value.code == "INSUFFICIENT_DATA"


def test_empty_cells_are_excluded_and_noted_deterministically() -> None:
    result = analyze_csv("name,value\na,1\nb,\nc,3\n")
    assert result["stats"]["value"]["count"] == 2
    assert result["stats"]["value"]["mean"] == 2.0
    assert result["notes"] == ["value: excluded 1 empty value(s)"]
