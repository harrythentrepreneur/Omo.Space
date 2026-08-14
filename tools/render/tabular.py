#!/usr/bin/env python3
"""Deterministic CSV parsing and descriptive statistics, without an LLM."""

from __future__ import annotations

import csv
import io
import math
import re
import statistics as stdlib_statistics
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


DELIMITERS = (",", ";", "\t")
INTEGER = re.compile(r"[+-]?(?:0|[1-9][0-9]*)\Z")
FLOAT = re.compile(r"[+-]?(?:(?:[0-9]+\.[0-9]*)|(?:[0-9]*\.[0-9]+)|(?:[0-9]+[eE][+-]?[0-9]+)|(?:[0-9]+\.[0-9]*[eE][+-]?[0-9]+))\Z")


class TabularError(ValueError):
    """A table operation failed with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _typed_cell(value: str) -> int | float | str:
    value = value.strip()
    if INTEGER.fullmatch(value):
        # Preserve identifiers whose leading zero is meaningful.
        unsigned = value.lstrip("+-")
        if len(unsigned) == 1 or not unsigned.startswith("0"):
            return int(value)
    if FLOAT.fullmatch(value):
        parsed = float(value)
        if math.isfinite(parsed):
            return parsed
    return value


def _delimiter(text: str) -> str:
    sample = text[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters="".join(DELIMITERS)).delimiter
    except csv.Error:
        first_nonempty = next((line for line in sample.splitlines() if line.strip()), "")
        counts = [(first_nonempty.count(delimiter), -index, delimiter) for index, delimiter in enumerate(DELIMITERS)]
        count, _, delimiter = max(counts)
        return delimiter if count else ","


def parse_csv(text: str) -> list[dict[str, int | float | str]]:
    """Parse CSV-like text into header-keyed rows with conservative cell typing."""

    if not isinstance(text, str) or not text.strip():
        raise TabularError("EMPTY_TABLE", "table is empty")
    reader = csv.reader(io.StringIO(text), delimiter=_delimiter(text), strict=True)
    try:
        records = list(reader)
    except csv.Error as exc:
        raise TabularError("EMPTY_TABLE", f"table could not be parsed: {exc}") from exc
    if not records or not any(cell.strip() for cell in records[0]):
        raise TabularError("EMPTY_TABLE", "table has no header")
    columns = [cell.strip() for cell in records[0]]
    if any(not column for column in columns):
        raise TabularError("EMPTY_TABLE", "table contains a blank column name")
    if len(set(columns)) != len(columns):
        raise TabularError("EMPTY_TABLE", "table contains duplicate column names")
    rows: list[dict[str, int | float | str]] = []
    for line_number, record in enumerate(records[1:], start=2):
        if not record or not any(cell.strip() for cell in record):
            continue
        if len(record) != len(columns):
            raise TabularError("EMPTY_TABLE", f"row {line_number} has {len(record)} cells; expected {len(columns)}")
        rows.append(dict(zip(columns, (_typed_cell(cell) for cell in record), strict=True)))
    if not rows:
        raise TabularError("EMPTY_TABLE", "table has no data rows")
    return rows


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def _stable_mode(values: Sequence[Any]) -> Any:
    counts = Counter(values)
    highest = max(counts.values())
    candidates = [value for value, count in counts.items() if count == highest]
    return min(candidates, key=lambda value: (type(value).__name__, str(value)))


def statistics(
    rows: Sequence[Mapping[str, Any]],
    *,
    numeric_columns: Iterable[str] | None = None,
    percentiles: Sequence[float] = (25, 50, 75),
) -> dict[str, Any]:
    """Compute deterministic numeric statistics and categorical modes.

    Empty-string cells are treated as missing. Mixed columns are categorical
    unless explicitly required through ``numeric_columns``, in which case they
    fail with ``NON_NUMERIC_COLUMN``.
    """

    if not rows:
        raise TabularError("EMPTY_TABLE", "table has no data rows")
    columns = list(rows[0].keys())
    if not columns or any(list(row.keys()) != columns for row in rows):
        raise TabularError("EMPTY_TABLE", "rows must share one ordered set of columns")
    requested = set(numeric_columns or ())
    unknown = requested.difference(columns)
    if unknown:
        raise TabularError("NON_NUMERIC_COLUMN", f"unknown numeric column: {sorted(unknown)[0]}")
    checked_percentiles: list[float] = []
    for value in percentiles:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
            raise ValueError("percentiles must contain finite values from 0 to 100")
        checked_percentiles.append(float(value))

    output: dict[str, dict[str, Any]] = {}
    notes: list[str] = []
    for column in columns:
        present = [row[column] for row in rows if row[column] != ""]
        numeric = [value for value in present if isinstance(value, (int, float)) and not isinstance(value, bool)]
        is_numeric = bool(present) and len(numeric) == len(present)
        if column in requested and not is_numeric:
            raise TabularError("NON_NUMERIC_COLUMN", f"column {column!r} contains non-numeric values")
        if is_numeric:
            if len(numeric) < 2:
                raise TabularError("INSUFFICIENT_DATA", f"column {column!r} needs two values for sample stdev")
            values = [float(value) for value in numeric]
            output[column] = {
                "count": len(values),
                "sum": sum(numeric),
                "mean": stdlib_statistics.fmean(values),
                "median": stdlib_statistics.median(numeric),
                "min": min(numeric),
                "max": max(numeric),
                "stdev": stdlib_statistics.stdev(values),
                "percentiles": {f"p{value:g}": _percentile(values, value) for value in checked_percentiles},
            }
        else:
            output[column] = {
                "count": len(present),
                "mode": _stable_mode(present) if present else None,
            }
            if present and numeric:
                notes.append(f"{column}: mixed numeric/text values treated as categorical")
        missing = len(rows) - len(present)
        if missing:
            notes.append(f"{column}: excluded {missing} empty value(s)")
    return {"columns": columns, "row_count": len(rows), "stats": output, "notes": notes}


def analyze_csv(
    text: str,
    *,
    numeric_columns: Iterable[str] | None = None,
    percentiles: Sequence[float] = (25, 50, 75),
) -> dict[str, Any]:
    """Parse and summarize a CSV-like string in one deterministic call."""

    return statistics(parse_csv(text), numeric_columns=numeric_columns, percentiles=percentiles)


__all__ = ["TabularError", "analyze_csv", "parse_csv", "statistics"]
