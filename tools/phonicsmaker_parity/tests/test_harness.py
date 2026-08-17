import json
from pathlib import Path

import pytest

from tools.phonicsmaker_parity.harness import compare_case, compare_contracts

ROOT = Path(__file__).resolve().parents[2]


def test_exact_case_passes_when_only_transport_fields_differ():
    source = {
        "input": {"phonemes": ["ch"], "topic": "farm", "difficultyLevel": "beginner"},
        "output": {"words": ["chick"], "coverage": ["ch"], "warnings": []},
        "artifacts": [
            {
                "role": "worksheet",
                "kind": "pdf",
                "filename": "result.pdf",
                "content_type": "application/pdf",
                "bytes": 12,
                "sha256": "a" * 64,
            }
        ],
    }
    omo = {
        "input": source["input"],
        "output": {
            **source["output"],
            "run_id": "run-12345678",
            "status": "completed",
            "usage": {"provider": "fixture"},
        },
        "artifacts": [{**source["artifacts"][0], "object_key": "private/run-123/result.pdf"}],
    }

    report = compare_case(source, omo)

    assert report.passed
    assert report.mismatches == []


def test_input_field_rename_is_not_parity():
    source = {"input": {"difficultyLevel": "beginner"}}
    omo = {"input": {"difficulty_level": "beginner"}}

    report = compare_case(source, omo)

    assert not report.passed
    assert any(m["kind"] == "input" and "difficultyLevel" in m["path"] for m in report.mismatches)


def test_extra_input_is_not_parity():
    source = {"input": {"phonemes": ["ch"]}}
    omo = {"input": {"phonemes": ["ch"], "dialect": "en-US"}}

    report = compare_case(source, omo)

    assert not report.passed
    assert any(m["kind"] == "input" and m["path"] == "$.input.dialect" for m in report.mismatches)


def test_logical_output_drift_is_not_hidden_by_transport_normalization():
    source = {"input": {}, "output": {"format": "markdown", "content": "* ch**ick**"}}
    omo = {"input": {}, "output": {"format": "json", "words": ["chick"]}}

    report = compare_case(source, omo)

    assert not report.passed
    assert any(m["kind"] == "output" for m in report.mismatches)


def test_artifact_hash_drift_fails_closed():
    source = {
        "input": {},
        "output": {},
        "artifacts": [{"role": "story", "kind": "pdf", "sha256": "a" * 64}],
    }
    omo = {
        "input": {},
        "output": {},
        "artifacts": [{"role": "story", "kind": "pdf", "sha256": "b" * 64}],
    }

    report = compare_case(source, omo)

    assert not report.passed
    assert any(m["kind"] == "artifact" and m["path"].endswith("sha256") for m in report.mismatches)


def test_contract_comparison_reports_renamed_and_extra_fields():
    source = {
        "properties": {
            "phonemes": {"type": "array"},
            "topic": {"type": "string"},
            "difficultyLevel": {"enum": ["beginner", "intermediate", "advanced"]},
        },
        "required": ["phonemes", "topic", "difficultyLevel"],
    }
    omo = {
        "properties": {
            "phonemes": {"type": "array"},
            "topic": {"type": "string"},
            "difficulty_level": {"enum": ["beginner", "intermediate", "advanced"]},
            "dialect": {"enum": ["en-US", "en-GB", "en-AU"]},
        },
        "required": ["phonemes", "topic", "difficulty_level", "dialect"],
    }

    report = compare_contracts(source, omo)

    assert not report.passed
    paths = {m["path"] for m in report.mismatches}
    assert "$.properties.difficultyLevel" in paths
    assert "$.properties.dialect" in paths
    assert "$.required" in paths
