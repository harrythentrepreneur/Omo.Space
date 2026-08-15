from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "one_shot_self_test.py"


def load_self_test():
    spec = importlib.util.spec_from_file_location("omo_one_shot_self_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample_profile() -> dict:
    return {
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "word": {"type": "string"},
                "dialect": {"type": "string"},
            },
            "required": ["word", "dialect"],
        },
        "self_test": {
            "cases": [
                {"input": {"word": "ship", "dialect": "en-US"}},
                {"input": {"word": "thought", "dialect": "en-GB"}},
            ]
        },
        "marketplace": {
            "examples": [{"input": {"word": "choir", "dialect": "en-AU"}}]
        },
        "happy_path": {"input": {"word": "ship", "dialect": "en-US"}},
    }


def test_discovers_three_unique_schema_valid_reviewed_cases() -> None:
    self_test = load_self_test()
    assert self_test.discover_cases(sample_profile()) == [
        {"word": "ship", "dialect": "en-US"},
        {"word": "thought", "dialect": "en-GB"},
        {"word": "choir", "dialect": "en-AU"},
    ]


def test_generic_semantic_checks_cover_counts_coverage_spans_and_input_items() -> None:
    self_test = load_self_test()
    assert self_test.semantic_issues(
        {
            "text": "The sheep",
            "num_sentences": 2,
            "phonics_patterns": ["sh"],
            "words": ["paper"],
        },
        {
            "input": "different",
            "sentences": [{"text": "one"}],
            "coverage": [],
            "occurrences": [{"text": "sh", "start": 0, "end": 2}],
            "items": [{"word": "other"}],
        },
    ) == [
        "COVERAGE_MISSING",
        "ECHO_MISMATCH",
        "INPUT_ITEM_MISSING",
        "REQUESTED_COUNT_MISMATCH",
        "SPAN_MISMATCH",
    ]


def test_result_file_is_new_mode_0600_and_contains_only_safe_result(tmp_path: Path) -> None:
    self_test = load_self_test()
    result = {"status": "blocked", "blocker": "SELF_TEST_SCHEMA_FAILED", "cases": 2}
    target = tmp_path / "nested" / "result.json"
    self_test.write_safe_result(target, result)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert json.loads(target.read_text()) == result
