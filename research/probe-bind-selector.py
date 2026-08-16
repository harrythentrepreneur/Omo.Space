#!/usr/bin/env python3
"""In-memory probe: does the REAL decodable-book-maker profile fire the
whole_book_vocabulary selector once the candidate vocabulary + constraints are
bound exactly as research/bind-candidate-vocabulary.py would write them?
Pure computation — no file writes, no container regen, no deploys."""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/root/marketplace/packages/skill-to-modal")
import compiler  # noqa: E402

candidate = json.loads(Path("/root/marketplace/research/candidate-vocabulary.json").read_text())
profile = json.loads(
    Path("/root/marketplace/packages/skill-to-modal/profiles/decodable-book-maker.json").read_text()
)

# 1. Unbound baseline: must stay schema_only (fail closed).
before = compiler.semantic_evidence_spec(profile)
print("BEFORE bind:", before.get("kind"))

# 2. Bind exactly as the script would: constraints + vocabulary (provenance flipped).
profile["reviewed_spec"] = {
    "constraints": [
        "every child-visible title, heading, and prose word must pass the selected "
        "stage vocabulary or the reviewed sight-word list"
    ],
    "vocabulary": {
        "provenance": "reviewed",
        "stages": candidate["vocabulary"]["stages"],
        "sight_words": candidate["vocabulary"]["sight_words"],
    },
}
after = compiler.semantic_evidence_spec(profile)
print("AFTER bind: ", after.get("kind"))
assert after.get("kind") == "whole_book_vocabulary", f"selector did NOT fire: {after}"
print("stage_field:", after.get("stage_field"))
print("book_field:", after.get("book_field"))
print("decodability_field:", after.get("decodability_field"))
print("name_field:", after.get("name_field"))
print("stages bound:", len(after.get("stages", {})))
print("sight_words bound:", len(after.get("sight_words", [])))
print("PROBE: PASS — real profile fires whole_book_vocabulary with the candidate bind")
