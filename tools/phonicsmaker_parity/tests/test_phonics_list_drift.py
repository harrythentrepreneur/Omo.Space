import json
from pathlib import Path

from tools.phonicsmaker_parity.evidence import build_phonics_list_drift_report
from tools.phonicsmaker_parity.harness import compare_contracts

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FIXTURE = ROOT / "tools/phonicsmaker_parity/fixtures/phonics-list-generator-source.json"
OMO_INPUT = ROOT / "containers/phonics-list-generator/schemas/input.json"
OMO_OUTPUT = ROOT / "containers/phonics-list-generator/schemas/output.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_omo_phonics_list_input_is_proven_not_equal_to_source():
    source = _load(SOURCE_FIXTURE)["input_contract"]
    omo = _load(OMO_INPUT)
    report = compare_contracts(source, omo)

    assert not report.passed
    mismatch_paths = {item["path"] for item in report.mismatches}
    assert "$.properties.difficultyLevel" in mismatch_paths
    assert "$.properties.difficulty_level" in mismatch_paths
    assert "$.properties.dialect" in mismatch_paths
    assert "$.properties.word_count" in mismatch_paths


def test_current_omo_phonics_list_output_is_proven_not_equal_to_source():
    source = _load(SOURCE_FIXTURE)["output_contract"]
    omo = _load(OMO_OUTPUT)
    report = compare_contracts(source, omo)

    assert not report.passed
    assert any(item["path"] == "$.type" and item["kind"] == "contract" for item in report.mismatches)
    assert any(item["path"] == "$.format" and item["kind"] == "contract" for item in report.mismatches)


def test_drift_evidence_report_is_reproducible():
    report = build_phonics_list_drift_report(ROOT)

    assert report["status"] == "DRIFT_CONFIRMED"
    assert report["summary"]["parity_proven"] is False
    assert report["summary"]["input_mismatch_count"] > 0
    assert report["summary"]["output_mismatch_count"] > 0
