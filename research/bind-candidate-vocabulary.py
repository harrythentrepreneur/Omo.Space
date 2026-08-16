#!/usr/bin/env python3
"""Turnkey bind for the CANDIDATE pilot-book vocabulary (decodable-book-maker).

Provenance rule (hard): the candidate file starts with
`provenance: candidate-unreviewed`. Binding means writing `reviewed_spec` into
the profile with provenance flipped to `reviewed`. That is a founder decision —
this script REFUSES --apply unless the candidate is still candidate-unreviewed
and prints a loud gate. The growth loop invokes --apply ONLY after Harry appends
a fresh dated line `- APPROVAL candidate-vocabulary-001: <YYYY-MM-DD>` to the
marketing/APPROVALS.md ledger (a file this loop never writes).

--apply performs ONLY the local profile edit (additive, reversible in git). It
does NOT regenerate containers, run provider calls, flip can_submit, deploy, or
push — those stay documented follow-ups for the tick that runs after approval.

Default (no --apply) is a dry run: it validates the candidate, cross-checks the
selector contract against the real profile, and prints the exact JSON patch.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path("/root/marketplace")
CANDIDATE = ROOT / "research/candidate-vocabulary.json"
PROFILE = ROOT / "packages/skill-to-modal/profiles/decodable-book-maker.json"

# From compiler._reviewed_semantic_promises + the whole_book_vocabulary selector.
PROMISE_PHRASES = (
    "stage vocabulary",
    "every child-visible",
    "sight-word list",
    "no review words",
)
# A constraints string that satisfies the selector; matches the fixture phrase.
REVIEWED_CONSTRAINT = (
    "every child-visible title, heading, and prose word must pass the selected "
    "stage vocabulary or the reviewed sight-word list"
)


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the profile edit (APPROVAL-GATED)")
    args = ap.parse_args()

    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    vocab = candidate["vocabulary"]
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))

    # 1. Candidate must still be unreviewed.
    if vocab["provenance"] != "candidate-unreviewed":
        return fail(f"candidate provenance is {vocab['provenance']!r}, expected candidate-unreviewed — already bound?")
    stages, sight = vocab["stages"], vocab["sight_words"]
    if not isinstance(sight, list) or not sight:
        return fail("sight_words must be a non-empty list")

    # 2. Stage keys must exactly match the profile input-schema enum.
    enum = None
    for schema in profile["input_schema"]["properties"].values():
        if isinstance(schema, dict) and isinstance(schema.get("enum"), list):
            enum = [str(e) for e in schema["enum"]]
            break
    if enum is None:
        return fail("no enum input field in profile input_schema")
    if list(stages.keys()) != enum:
        return fail(f"stage keys mismatch:\n  candidate: {list(stages.keys())}\n  profile:   {enum}")

    # 3. Token sanity on the candidate (mirrors validate-candidate-vocabulary.py).
    for name, words in stages.items():
        for w in words:
            if not re.fullmatch(r"[a-z]+", w):
                return fail(f"bad token {w!r} in stage {name}")
    for w in sight:
        if not re.fullmatch(r"[a-z]+", w):
            return fail(f"bad token {w!r} in sight_words")

    # 4. Static selector preconditions on the real profile (mirrors the
    #    compiler's merged-schema read: model_output_schema + output_schema).
    output_properties = {
        **profile.get("output_schema", {}).get("properties", {}),
        **profile["live"]["model_output_schema"]["properties"],
    }
    book_fields = [
        n for n, s in output_properties.items()
        if s.get("type") == "string"
        and (n in {"book", "story", "text", "content"} or (s.get("maxLength") or 0) >= 500)
    ]
    decod_fields = [
        n for n, s in output_properties.items()
        if isinstance(s, dict) and isinstance(s.get("properties"), dict)
        and {"word_counts", "review_words", "sight_words"} <= set(s["properties"])
    ]
    if len(book_fields) != 1:
        return fail(f"expected exactly 1 long-form book field, got {book_fields}")
    if len(decod_fields) != 1:
        return fail(f"expected exactly 1 decodability field, got {decod_fields}")
    if profile.get("reviewed_spec", {}).get("vocabulary"):
        return fail("profile already has reviewed_spec.vocabulary — refusing double bind")

    patch = {
        "constraints": [REVIEWED_CONSTRAINT],
        "vocabulary": {
            "provenance": "reviewed",
            "stages": stages,
            "sight_words": sight,
        },
    }
    print("DRY-RUN SELECTOR CONTRACT: PASS")
    print(f"  stage enum match: {list(stages.keys())}")
    print(f"  book field: {book_fields[0]} | decodability field: {decod_fields[0]}")
    print(f"  candidate stage counts: {[len(stages[k]) for k in stages]} | sight words: {len(sight)}")
    print(f"  promise phrase present in constraints: {REVIEWED_CONSTRAINT!r}")
    print("PATCH to apply (add to profile as reviewed_spec):")
    print(json.dumps(patch, indent=2))

    if not args.apply:
        print("\n[no files changed — dry run]")
        print("Follow-ups after Harry's approval (loop's next ticks): regen container via")
        print("compiler, re-run vocabulary needles on the real lists, flip can_submit, then")
        print("run-manifest + catalog row (deploy still coordinator/Harry-gated).")
        return 0

    # --apply is APPROVAL-GATED: requires a FRESH dated approval line in the
    # APPROVALS LEDGER (marketing/APPROVALS.md) — a file this loop NEVER writes.
    # Checking GOAL.md instead is INSUFFICIENT (found twice on 2026-08-16: the
    # bare phrase also appears there as instructional text, and a marker written
    # into GOAL.md as an instruction matched a substring gate). Doc text never
    # counts as approval, and a stale date (doc copy) is rejected too.
    from datetime import date, timedelta

    approvals = ROOT / "marketing/APPROVALS.md"
    try:
        ledger_text = approvals.read_text(encoding="utf-8")
    except FileNotFoundError:
        return fail("approvals ledger marketing/APPROVALS.md does not exist — refusing to bind")
    today = date.today()
    valid = {today - timedelta(days=d) for d in range(0, 4)} | {today + timedelta(days=1)}
    marker = "- APPROVAL candidate-vocabulary-001:"
    approved = False
    for line in ledger_text.splitlines():
        if not line.startswith(marker):
            continue
        stamp = line[len(marker):].strip().split()[0] if line[len(marker):].strip() else ""
        try:
            if date.fromisoformat(stamp) in valid:
                approved = True
                break
        except ValueError:
            continue
    if not approved:
        return fail(
            "a FRESH dated approval line (`- APPROVAL candidate-vocabulary-001: "
            "<YYYY-MM-DD>`) is NOT in marketing/APPROVALS.md — refusing to bind. "
            "GOAL.md/doc text and stale dates do NOT count as approval."
        )
    profile["reviewed_spec"] = patch
    PROFILE.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"BOUND: wrote reviewed_spec into {PROFILE}")
    print("Next: regen container, fixture needles on real lists, flip can_submit (loop ticks).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
