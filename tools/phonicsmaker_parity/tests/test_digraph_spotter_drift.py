import json
from pathlib import Path

from tools.phonicsmaker_parity.evidence import build_drift_report
from tools.phonicsmaker_parity.harness import compare_contracts

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FIXTURE = ROOT / "tools/phonicsmaker_parity/fixtures/digraph-spotter-source.json"
OMO_INPUT = ROOT / "containers/digraph-spotter/schemas/input.json"
OMO_OUTPUT = ROOT / "containers/digraph-spotter/schemas/output.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_digraph_spotter_source_input_fields_are_derived():
    """The source fixture must capture the teacher-facing input contract we
    read from the real source (toolConfig.ts): textInput textarea required,
    digraphType enum, includeExplanations enum, no Omo transport/dialect."""
    src = _load(SOURCE_FIXTURE)
    props = src["input_contract"]["properties"]
    assert src["slug"] == "digraph-spotter"
    assert set(props) == {"textInput", "digraphType", "includeExplanations"}, sorted(props)
    assert props["textInput"]["ui_widget"] == "textarea"
    assert props["digraphType"]["enum"] == ["all", "consonant", "vowel"]
    assert props["includeExplanations"]["enum"] == ["yes", "no"]
    assert "dialect" not in props  # source has no dialect; Omo adds it (drift)


def test_digraph_spotter_output_rules_are_derived_from_prompt():
    src = _load(SOURCE_FIXTURE)
    out = src["output_contract"]
    assert out["type"] == "string"
    assert out["format"] == "markdown"
    assert any("double asterisks" in r for r in out["rules"])
    assert any("summary" in r for r in out["rules"])


def test_current_omo_digraph_spotter_input_proven_not_equal_to_source():
    source = _load(SOURCE_FIXTURE)["input_contract"]
    omo = _load(OMO_INPUT)
    report = compare_contracts(source, omo)
    assert not report.passed
    paths = {item["path"] for item in report.mismatches}
    # Omo renamed/reshaped the source fields -> drift must be recorded
    assert "$.properties.textInput" in paths  # missing in Omo (uses text)
    assert "$.properties.dialect" in paths  # extra in Omo (not in source)


def test_drift_evidence_report_is_reproducible_for_digraph_spotter():
    report = build_drift_report(ROOT, "digraph-spotter")
    assert report["status"] == "DRIFT_CONFIRMED"
    assert report["slug"] == "digraph-spotter"
    assert report["summary"]["parity_proven"] is False
    assert report["summary"]["input_mismatch_count"] > 0
    assert report["summary"]["output_mismatch_count"] > 0
