#!/usr/bin/env python3
"""Generate compact registry seed data from the reviewed source inventories."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "research" / "phonicsmaker-100-tools-plan.md"
DATA_DIR = Path(__file__).resolve().parent / "data"
PHONICS_DATA = DATA_DIR / "phonicsmaker-tools.json"
CURRENT_DATA = DATA_DIR / "current-catalog.json"
EXTRACT_CURRENT = Path(__file__).resolve().parent / "extract-current-catalog.mjs"

ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|\s*(.*?)\s*->\s*(.*?)\s*\|\s*([APGES])\s*\|\s*"
    r"`([^`]+)`\s*\|\s*`(\{.*\})`\s*->\s*([^|]+?)\s*\|\s*\$(\d+(?:\.\d+)?)\s*\|$"
)
FAMILY_RE = re.compile(r"^### 1\.\d+ (.*?) — \d+$")
FAMILY_CATEGORIES = {
    "Foundational phonics and word study": "phonics",
    "Vocabulary, grammar and language mechanics": "language",
    "Reading, fluency and assessment": "reading",
    "Worksheets, quizzes and printables": "worksheets",
    "Writing, stories and literacy content": "writing",
    "Games and oral/creative activities": "activities",
    "Planning and teacher administration": "teacher-tools",
    "Cross-curricular/general utilities": "education",
    "Illustrated story generation and editing": "phonics",
}


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def parse_phonics_inventory(text: str) -> dict:
    family = ""
    tools: list[dict] = []
    for line in text.splitlines():
        family_match = FAMILY_RE.match(line)
        if family_match:
            family = family_match.group(1)
            continue
        row = ROW_RE.match(line)
        if not row:
            continue
        number, name, product, state, slug, input_sketch, output_kind, price = row.groups()
        tools.append(
            {
                "inventory_number": int(number),
                "slug": slug,
                "name": name,
                "description": f"Produces {product}.",
                "inventory_label": f"{name} -> {product}",
                "family": family,
                "category": FAMILY_CATEGORIES[family],
                "current_state": state,
                "input_sketch": input_sketch,
                "output_kind": output_kind,
                "planned_price_cents": int(Decimal(price) * 100),
            }
        )

    if len(tools) != 96:
        raise ValueError(f"expected 96 PhonicsMaker rows, found {len(tools)}")
    if [tool["inventory_number"] for tool in tools] != list(range(1, 97)):
        raise ValueError("PhonicsMaker inventory numbering is not contiguous")
    if len({tool["slug"] for tool in tools}) != 96:
        raise ValueError("PhonicsMaker inventory contains duplicate slugs")
    if sum(tool["current_state"] in {"A", "P"} for tool in tools) != 93:
        raise ValueError("expected 93 prompt tools")
    if sum(tool["current_state"] in {"G", "E", "S"} for tool in tools) != 3:
        raise ValueError("expected three existing artifact-heavy tools")

    return {
        "schema_version": "omo.registry-seed/phonicsmaker-v1",
        "source": str(PLAN.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "count": len(tools),
        "tools": tools,
    }


def extract_current_catalog() -> dict:
    result = subprocess.run(
        ["node", str(EXTRACT_CURRENT)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    tools = payload["tools"]
    if len(tools) != 24 or len({tool["slug"] for tool in tools}) != 24:
        raise ValueError("current catalog parity gate requires 24 unique listings")
    payload["schema_version"] = "omo.registry-seed/current-catalog-v1"
    payload["count"] = len(tools)
    return payload


def generated_payloads() -> dict[Path, bytes]:
    phonics_text = PLAN.read_text(encoding="utf-8")
    return {
        PHONICS_DATA: _json_bytes(parse_phonics_inventory(phonics_text)),
        CURRENT_DATA: _json_bytes(extract_current_catalog()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if committed seed data is stale")
    args = parser.parse_args()
    payloads = generated_payloads()
    stale: list[str] = []
    for output, expected in payloads.items():
        if args.check:
            if not output.exists() or output.read_bytes() != expected:
                stale.append(str(output.relative_to(ROOT)))
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(expected)
    if stale:
        raise SystemExit("stale registry seed data: " + ", ".join(stale))
    print("registry seed data is current" if args.check else "generated registry seed data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
