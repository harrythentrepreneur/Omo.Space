#!/usr/bin/env python3
"""Debug: why does the fixture-shaped profile now select schema_only?"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/root/marketplace/packages/skill-to-modal")
import compiler  # noqa: E402

fixture = json.loads(
    Path("/root/marketplace/packages/skill-to-modal/tests/fixtures/vocabulary-book-normalizer.json").read_text()
)
stages = fixture["vocabulary"]["stages"]
profile = json.loads(
    Path("/root/marketplace/packages/skill-to-modal/profiles/decodable-book-maker.json").read_text()
)
profile["slug"] = "vocabulary-book-normalizer"
profile["name"] = profile["slug"]
profile["input_schema"] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "phonics_stage": {"type": "string", "enum": sorted(stages)},
        "theme": {"type": "string"},
        "child_name": {"type": "string", "description": "Optional. A child's name; the sole special-word exception."},
    },
    "required": ["phonics_stage", "theme"],
}
profile["live"]["model_output_schema"] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "book": {"type": "string"},
        "decodability": {
            "type": "object",
            "properties": {
                "word_counts": {"type": "object"},
                "review_words": {"type": "array"},
                "sight_words": {"type": "array"},
            },
        },
    },
    "required": ["book"],
}
profile["semantic_normalizers"] = {}
profile["reviewed_spec"] = {
    "constraints": ["every child-visible title, heading, and prose word must pass the selected stage vocabulary or the reviewed sight-word list"],
    "vocabulary": fixture["vocabulary"],
}

output_properties = {
    **profile.get("output_schema", {}).get("properties", {}),
    **profile["live"]["model_output_schema"]["properties"],
}
print("MERGED output_properties keys:", list(output_properties.keys()))
for name, s in output_properties.items():
    print(f"  {name}: type={s.get('type')} maxLength={s.get('maxLength')} has_props={'properties' in s}")

# Recompute the selector's intermediate lists by hand.
stage_fields = [
    n for n, s in profile["input_schema"]["properties"].items()
    if s.get("type") == "string" and isinstance(s.get("enum"), list)
    and set(map(str, s["enum"])) == set(fixture["vocabulary"]["stages"])
]
print("stage_fields:", stage_fields)
book_fields = [
    n for n, s in output_properties.items()
    if s.get("type") == "string"
    and (n in {"book", "story", "text", "content"} or (s.get("maxLength") or 0) >= 500)
]
print("book_fields:", book_fields)
decod_fields = [
    n for n, s in output_properties.items()
    if isinstance(s, dict) and isinstance(s.get("properties"), dict)
    and {"word_counts", "review_words", "sight_words"} <= set(s["properties"])
]
print("decod_fields:", decod_fields)
spec = compiler.semantic_evidence_spec(profile)
print("FINAL kind:", spec.get("kind"))
