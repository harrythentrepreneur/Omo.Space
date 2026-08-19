import json
from pathlib import Path

from tools.phonicsmaker_parity.evidence import build_drift_report
from tools.phonicsmaker_parity.harness import compare_contracts

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FIXTURE = ROOT / "tools/phonicsmaker_parity/fixtures/decodable-sentence-creator-source.json"
OMO_INPUT = ROOT / "containers/decodable-sentence-creator/schemas/input.json"
OMO_OUTPUT = ROOT / "containers/decodable-sentence-creator/schemas/output.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_decodable_sentence_creator_source_input_fields_are_derived():
    src = _load(SOURCE_FIXTURE)
    props = src["input_contract"]["properties"]
    assert src["slug"] == "decodable-sentence-creator"
    assert set(props) == {"phonicsPattern", "numSentences", "sentenceLength", "includeSightWords"}
    assert props["phonicsPattern"]["ui_widget"] == "multi_select"
    assert props["phonicsPattern"]["items"]["enum"] == [
        "cvc", "cvcc", "ccvc", "long_a", "long_e", "long_i", "long_o", "long_u",
        "sh_digraph", "ch_digraph", "th_digraph", "wh_digraph", "ck_digraph",
        "ai_vowel_team", "ee_vowel_team", "oa_vowel_team",
    ]
    assert props["numSentences"]["minimum"] == 1
    assert props["numSentences"]["maximum"] == 5
    assert props["sentenceLength"]["enum"] == ["short", "medium", "long"]
    assert props["includeSightWords"]["enum"] == ["yes", "no"]
    assert "dialect" not in props


def test_decodable_sentence_creator_output_rules_are_derived_from_prompt():
    out = _load(SOURCE_FIXTURE)["output_contract"]
    assert out["type"] == "string"
    assert out["format"] == "markdown"
    assert any("one sentence per line" in rule for rule in out["rules"])
    assert any("no additional text" in rule for rule in out["rules"])


def test_current_omo_decodable_sentence_creator_input_is_proven_not_equal_to_source():
    source = _load(SOURCE_FIXTURE)["input_contract"]
    omo = _load(OMO_INPUT)
    report = compare_contracts(source, omo)
    assert not report.passed
    paths = {item["path"] for item in report.mismatches}
    assert "$.properties.phonicsPattern" in paths
    assert "$.properties.phonics_patterns" in paths
    assert "$.properties.dialect" in paths


def test_drift_evidence_report_is_reproducible_for_decodable_sentence_creator():
    report = build_drift_report(ROOT, "decodable-sentence-creator")
    assert report["status"] == "DRIFT_CONFIRMED"
    assert report["slug"] == "decodable-sentence-creator"
    assert report["summary"]["parity_proven"] is False
    assert report["summary"]["input_mismatch_count"] > 0
    assert report["summary"]["output_mismatch_count"] > 0
