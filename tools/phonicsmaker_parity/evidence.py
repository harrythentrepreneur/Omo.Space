"""Generate sanitized evidence for a known PhonicsMaker/Omo contract pair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .harness import compare_contracts


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_phonics_list_drift_report(root: Path) -> dict[str, Any]:
    source_path = root / "tools/phonicsmaker_parity/fixtures/phonics-list-generator-source.json"
    input_path = root / "containers/phonics-list-generator/schemas/input.json"
    output_path = root / "containers/phonics-list-generator/schemas/output.json"
    source = _load(source_path)
    input_report = compare_contracts(source["input_contract"], _load(input_path))
    output_report = compare_contracts(source["output_contract"], _load(output_path))
    return {
        "status": "DRIFT_CONFIRMED",
        "fixture_kind": source["fixture_kind"],
        "slug": source["slug"],
        "source_provenance": source["provenance"],
        "omo_paths": {
            "input_schema": str(input_path.relative_to(root)),
            "output_schema": str(output_path.relative_to(root)),
        },
        "rules": {
            "matching_omo_name_is_not_parity": True,
            "teacher_input_names_and_output_contracts_are_exact": True,
            "transport_fields_are_not_involved_in_this_contract_check": True,
        },
        "input_contract_report": input_report.to_dict(),
        "output_contract_report": output_report.to_dict(),
        "summary": {
            "input_mismatch_count": len(input_report.mismatches),
            "output_mismatch_count": len(output_report.mismatches),
            "parity_proven": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_phonics_list_drift_report(args.root)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
