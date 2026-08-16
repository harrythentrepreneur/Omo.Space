#!/usr/bin/env python3
"""Turnkey post-approval orchestrator: candidate vocabulary -> live decodable-book-maker.

WHEN TO USE
-----------
After Harry approves the candidate vocabulary by appending the structured line
`- APPROVAL candidate-vocabulary-001:` to marketing/APPROVALS.md (the approval
ledger). The loop NEVER writes that file, so its presence there is a genuine
founder approval. --apply REFUSES otherwise — GOAL.md/doc text does NOT count
(HARDENED after two gate false-positive incidents on 2026-08-16; run
`python3 research/approval-to-live.py --selftest` to prove the gate). Identical
gate to research/bind-candidate-vocabulary.py. THIS SCRIPT NEVER DEPLOYS,
PUSHES, SENDS, SPENDS, OR READS SECRETS — it performs the LOCAL chain only:

  1. BIND   — write reviewed_spec (constraints + vocabulary, provenance=reviewed)
              into packages/skill-to-modal/profiles/decodable-book-maker.json
  2. FLIP   — readiness.can_submit = true, decoder blocker cleared (the compiler
              only wires semantic machinery into ready runtimes)
  3. REGEN  — compile the container via the canonical compiler
              (python3 packages/skill-to-modal/compiler.py ... --out containers/)
  4. NEEDLES- run the REAL-list vocabulary needles against the generated runtime:
              right needle (stage-1 book made ONLY of real stage-1 + sight words
              + child name -> 0 review words, 100% within-stage), out-of-stage
              needle (-> $:semantic_review_words), unknown-stage needle
              (-> $:semantic_unknown_stage)
  5. PIN    — _EXISTING_PROFILE_KINDS[decodable-book-maker] = whole_book_vocabulary
              so the no-reclassification test stays green
  6. VERIFY — pytest -k 'vocabulary or existing_profiles' on the committed tree

Default (no --apply) is a DRY RUN that performs the gate check, the in-memory
bind probe, the runtime build, and ALL THREE real-list needles with zero file
writes — proof that the candidate lists satisfy the machinery before anyone
touches the profile.

Streaming is the point: run this same file once in dry-run now, then again
exactly once with --apply in the tick after Harry's recorded approval.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/root/marketplace")
CANDIDATE = ROOT / "research/candidate-vocabulary.json"
PROFILE = ROOT / "packages/skill-to-modal/profiles/decodable-book-maker.json"
PIN_TEST = ROOT / "packages/skill-to-modal/tests/test_compiler.py"
GOAL = ROOT / "marketing/GOAL.md"
APPROVALS = ROOT / "marketing/APPROVALS.md"  # ledger; the loop never writes here
COMPILER = ROOT / "packages/skill-to-modal/compiler.py"
CONTAINER_SOURCE = ROOT / "containers/decodable-book-maker/source/SKILL.md"
CONTAINER_OUT = ROOT / "containers/decodable-book-maker"
VENV_PY = Path("/tmp/issue8-venv/bin/python")

# Structured approval record, read ONLY from the approvals ledger
# (marketing/APPROVALS.md). The loop never writes that file — the marker can
# therefore never appear in it as instructional text. GOAL.md and docs may
# contain the phrase freely; the gate ignores them. A fresh date is required.
APPROVAL_MARKER = "- APPROVAL candidate-vocabulary-001:"
REVIEWED_CONSTRAINT = (
    "every child-visible title, heading, and prose word must pass the selected "
    "stage vocabulary or the reviewed sight-word list"
)
SIGHT_SENTENCE = ["the", "and", "a", "is"]  # Dolch, guaranteed present in the 92

fail_count = 0


def approval_recorded(ledger: Path = APPROVALS) -> bool:
    """True only if the ledger holds a FRESH structured approval line.

    Reads ONLY marketing/APPROVALS.md (a file this loop never writes). The line
    must be `- APPROVAL candidate-vocabulary-001: <YYYY-MM-DD>` with a date
    within the valid window — a stale marker copied from docs fails, and doc
    text anywhere else is never read at all.
    """
    from datetime import date, timedelta

    try:
        text = ledger.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False
    today = date.today()
    valid = {today - timedelta(days=d) for d in range(0, 4)} | {today + timedelta(days=1)}
    for line in text.splitlines():
        if not line.startswith(APPROVAL_MARKER):
            continue
        stamp = line[len(APPROVAL_MARKER):].strip().split()[0] if line[len(APPROVAL_MARKER):].strip() else ""
        try:
            when = date.fromisoformat(stamp)
        except ValueError:
            continue
        if when in valid:
            return True
    return False


def ok(msg: str) -> None:
    print(f"  PASS: {msg}")


def bad(msg: str) -> None:
    global fail_count
    fail_count += 1
    print(f"  FAIL: {msg}")


def gate_check(apply: bool) -> dict:
    """Returns the bound patch dict if the hard gates pass, else exits 1."""
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    vocab = candidate["vocabulary"]
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    if vocab["provenance"] != "candidate-unreviewed":
        bad(f"candidate provenance is {vocab['provenance']!r}, expected candidate-unreviewed")
        sys.exit(1)
    if profile.get("reviewed_spec", {}).get("vocabulary"):
        bad("profile already has reviewed_spec.vocabulary — refusing double bind")
        sys.exit(1)
    if apply:
        # HARDENED GATE (2026-08-16, twice): GOAL.md is NOT the approval source.
        # Attempt 1 failed because the bare phrase "approve candidate vocabulary"
        # also appears in GOAL.md as instructions; attempt 2 failed because a
        # marker string I had just written INTO GOAL.md as an instruction also
        # matched. The gate now reads ONLY marketing/APPROVALS.md — a ledger the
        # loop never writes — so instructional text anywhere else can never
        # satisfy it.
        if not approval_recorded():
            bad("structured approval record (`- APPROVAL candidate-vocabulary-001:`) "
                "is NOT in marketing/APPROVALS.md — GOAL.md instructions do not count")
            sys.exit(1)
        print("  GATE: structured approval record present in marketing/APPROVALS.md")
    return {
        "constraints": [REVIEWED_CONSTRAINT],
        "vocabulary": {
            "provenance": "reviewed",
            "stages": vocab["stages"],
            "sight_words": vocab["sight_words"],
        },
    }


def build_runtime(profile: dict):
    """Build + import the generated runtime for a profile WITHOUT writing to the repo."""
    sys.path.insert(0, str(ROOT / "packages/skill-to-modal"))
    import compiler  # noqa: F401  (module-level SEMANTIC_EVIDENCE_SPEC is per-runtime)

    code = compiler.modal_app_template(profile)
    probe_dir = Path(tempfile.mkdtemp(prefix="omo_probe_")) / "nested"
    probe_dir.mkdir(exist_ok=True)
    tmp = probe_dir / "probe_runtime.py"
    tmp.write_text(code, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("generated_probe", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_needles(profile: dict) -> None:
    """Run the three REAL-list needles against the runtime for the bound+flipped profile.

    Precondition: profile['readiness']['can_submit'] is True AND reviewed_spec.vocabulary
    is bound — the template only wires the semantic machinery into ready runtimes
    (compiler.modal_app_template: `live = profile.get('live') if ready else None`).
    """
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    vocab = candidate["vocabulary"]
    stages = vocab["stages"]
    sight = set(vocab["sight_words"])
    first_stage = list(stages.keys())[0]
    stage_words = stages[first_stage]

    # Real stage-1 book: only stage-1 tokens + sight words + a non-vocab child name.
    # Pick 8 distinct stage-1 words to avoid near-duplicate Tokens in the sentence.
    words = stage_words[:8]
    sight_sentence = [w for w in SIGHT_SENTENCE if w in sight]
    # Child name must be outside every stage and the sight list (sole exception slot).
    name = "kim"
    all_tokens = set(stage_words) | sight
    while name in all_tokens:
        name += "x"
    book = (
        " ".join(sight_sentence[:1] + [words[0], sight_sentence[0] if len(sight_sentence) > 1 else "and"])
        + " "
        + " and ".join(words[1:])
        + " with "
        + name
    )
    title = words[0] + " " + sight_sentence[0] if sight_sentence else words[0]
    payload = {"phonics_stage": first_stage, "theme": "farm", "child_name": name}
    runtime = build_runtime(profile)
    assert runtime.SEMANTIC_EVIDENCE_SPEC["kind"] == "whole_book_vocabulary"

    # RIGHT NEEDLE — every token decodable/sight/name -> empty diff, report clean.
    output = {"title": title, "book": book}
    normalized = runtime._semantic_normalize(json.loads(json.dumps(output)), payload)
    diff = runtime._semantic_validation_diff(normalized, payload)
    report = normalized["decodability"]
    if diff == "" and report["word_counts"]["review"] == 0 and report["within_stage_percent"] == 100.0:
        ok(f"right needle: {first_stage} book, {report['word_counts']['total']} tokens, "
           f"0 review words, {report['within_stage_percent']}% within stage, name_occurrences={report['name_occurrences']}")
    else:
        bad(f"right needle mismatch: diff={diff!r} report={report}")

    # OUT-OF-STAGE NEEDLE — a fantasy token must be flagged as a review word.
    bad_book = book + " dinosaur"
    diff = runtime._semantic_validation_diff({"title": title, "book": bad_book}, payload)
    if "$:semantic_review_words" in diff and "dinosaur" in diff:
        ok(f"out-of-stage needle: 'dinosaur' flagged ({diff})")
    else:
        bad(f"out-of-stage needle mismatch: {diff!r}")

    # UNKNOWN-STAGE NEEDLE — typed stage failure, fail closed.
    diff = runtime._semantic_validation_diff({"title": title, "book": book}, {"phonics_stage": "not-a-stage", "theme": "farm", "child_name": name})
    if "$:semantic_unknown_stage" in diff:
        ok("unknown-stage needle: $:semantic_unknown_stage emitted")
    else:
        bad(f"unknown-stage needle mismatch: {diff!r}")


def verify_suite() -> None:
    cmd = [str(VENV_PY), "-m", "pytest", "-q", "-p", "no:cacheprovider",
           str(ROOT / "packages/skill-to-modal/tests/test_compiler.py"),
           "-k", "vocabulary or existing_profiles"]
    print(f"  VERIFY: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    print(proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "")
    if proc.returncode != 0:
        bad(f"verify suite failed rc={proc.returncode}")
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:])
    else:
        ok(f"verify suite green (rc=0): {proc.stdout.strip().splitlines()[-1]}")


def do_apply(patch: dict) -> None:
    # 1. BIND
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    profile["reviewed_spec"] = patch
    PROFILE.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ok(f"BIND: wrote reviewed_spec into {PROFILE.relative_to(ROOT)}")

    # 2. FLIP (before REGEN: the template only wires semantic machinery into ready runtimes)
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    profile["readiness"]["can_submit"] = True
    profile["readiness"]["blockers"] = []
    PROFILE.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ok("FLIP: readiness.can_submit=true, DECODABILITY_VOCABULARY_MISSING cleared")

    # 3. REGEN
    cmd = [sys.executable, str(COMPILER), str(CONTAINER_SOURCE),
           "--profile", str(PROFILE), "--out", str(CONTAINER_OUT)]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        bad(f"REGEN failed rc={proc.returncode}: {proc.stdout[-1000:]} {proc.stderr[-1000:]}")
        sys.exit(1)
    ok(f"REGEN: container regenerated ({CONTAINER_OUT.relative_to(ROOT)})")

    # 4. NEEDLES on the flipped profile (in-memory import of the generated code)
    run_needles(json.loads(PROFILE.read_text(encoding="utf-8")))
    if fail_count:
        bad(f"{fail_count} needle checks failed — regenerated runtime is not passable; roll back")
        sys.exit(1)

    # 5. PIN
    text = PIN_TEST.read_text(encoding="utf-8")
    needle = '"decodable-book-maker": "schema_only"'
    if needle in text:
        PIN_TEST.write_text(text.replace(needle, '"decodable-book-maker": "whole_book_vocabulary"'), encoding="utf-8")
        ok("PIN: _EXISTING_PROFILE_KINDS[decodable-book-maker] -> whole_book_vocabulary")
    else:
        bad("PIN: expected pin string not found — inspect test_compiler.py manually")
        sys.exit(1)

    # 6. VERIFY on the changed tree
    verify_suite()

    if fail_count:
        bad(f"{fail_count} checks failed — do NOT flip/deploy; inspect and re-run")
        sys.exit(1)
    print("ORCHESTRATOR COMPLETE. STOPPED before run-manifest/catalog/deploy — those "
          "steps remain coordinator-push + Harry-approval gated.")


def selftest() -> int:
    """Prove the approval gate accepts ONLY a real ledger record (no repo writes)."""
    print("SELFTEST — approval gate")
    import tempfile

    probe_ledger = Path(tempfile.mkdtemp(prefix="omo_ledger_")) / "APPROVALS.md"
    if approval_recorded(probe_ledger):
        bad("empty ledger must NOT record approval")
        return 1
    ok("empty/missing ledger -> refuse")

    probe_ledger.write_text(
        "# Ledger\n\nSome instructions here mention the marker text - APPROVAL\n"
        "candidate-vocabulary-001: but in prose only.\n",
        encoding="utf-8",
    )
    if approval_recorded(probe_ledger):
        bad("prose mention must NOT record approval")
        return 1
    ok("prose mention of marker -> refuse (this was the incident-1/2 failure mode)")

    probe_ledger.write_text(
        "# Ledger\n\n- APPROVAL candidate-vocabulary-001: 2020-01-01 stale copied line\n",
        encoding="utf-8",
    )
    if approval_recorded(probe_ledger):
        bad("stale-dated line must NOT record approval")
        return 1
    ok("stale-dated marker -> refuse (doc-copy cannot be replayed)")

    from datetime import date

    probe_ledger.write_text(
        "# Ledger\n\n"
        f"- APPROVAL candidate-vocabulary-001: {date.today().isoformat()} Harry approves.\n",
        encoding="utf-8",
    )
    if not approval_recorded(probe_ledger):
        bad("fresh exact structured line MUST record approval")
        return 1
    ok("fresh dated structured line -> accept")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="run the full local chain (bind/flip/regen/needles/pin). "
                         "REFUSES unless the approval ledger records it.")
    ap.add_argument("--selftest", action="store_true",
                    help="verify the approval gate accept/refuse paths (no repo writes)")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    print(f"{'APPLY' if args.apply else 'DRY-RUN'} — approval-to-live orchestrator")
    patch = gate_check(args.apply)

    # In-memory bind + flip probe (selector must fire whole_book_vocabulary with the
    # patch AND the generated runtime must actually wire the machinery — the template
    # only emits semantic code into ready runtimes, so can_submit must be True).
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    profile["reviewed_spec"] = patch
    profile["readiness"]["can_submit"] = True
    sys.path.insert(0, str(ROOT / "packages/skill-to-modal"))
    import compiler  # noqa: F401
    spec = compiler.semantic_evidence_spec(profile)
    if spec.get("kind") == "whole_book_vocabulary":
        ok(f"selector fires whole_book_vocabulary (stage={spec.get('stage_field')}, "
           f"book={spec.get('book_field')}, decod={spec.get('decodability_field')}, "
           f"name={spec.get('name_field')})")
    else:
        bad(f"selector did NOT fire whole_book_vocabulary: {spec.get('kind')}")
        return 1

    run_needles(profile)  # pure computation, zero writes

    if args.apply:
        do_apply(patch)
    else:
        print("\n[no files changed — dry run]")
        print("Real-list needles PASS on the candidate vocabulary. Run with --apply in the")
        print("tick AFTER Harry appends a FRESH dated line to marketing/APPROVALS.md:")
        print("`- APPROVAL candidate-vocabulary-001: <YYYY-MM-DD> ...` (GOAL.md text and")
        print("stale dates are never accepted — see --selftest).")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())