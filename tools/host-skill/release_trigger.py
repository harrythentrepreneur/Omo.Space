#!/usr/bin/env python3
"""Validate a GitHub workflow_run event for credential-free release triggering."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

EXPECTED_REPOSITORY = "harrythentrepreneur/Omo.Space"
EXPECTED_WORKFLOW = "generated-workflow-contracts"
EXPECTED_WORKFLOW_PATH = ".github/workflows/generated-workflow-contracts.yml"
EXPECTED_BRANCH = "main"
MAX_EVENT_BYTES = 256 * 1024
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class TriggerDecision:
    eligible: bool
    reason: str
    target_sha: str | None = None
    run_id: int | None = None
    run_attempt: int | None = None


def _decision(reason: str) -> TriggerDecision:
    return TriggerDecision(eligible=False, reason=reason)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def evaluate_event(event: Any) -> TriggerDecision:
    """Reduce an untrusted workflow_run payload to a bounded decision."""
    root = _mapping(event)
    repository = _mapping(root.get("repository"))
    run = _mapping(root.get("workflow_run"))
    head_repository = _mapping(run.get("head_repository"))

    if root.get("action") != "completed":
        return _decision("wrong_action")
    if repository.get("full_name") != EXPECTED_REPOSITORY:
        return _decision("wrong_repository")
    if repository.get("default_branch") != EXPECTED_BRANCH:
        return _decision("wrong_default_branch")
    if run.get("name") != EXPECTED_WORKFLOW:
        return _decision("wrong_workflow")
    if run.get("path") != EXPECTED_WORKFLOW_PATH:
        return _decision("wrong_workflow_path")
    if run.get("event") != "push":
        return _decision("wrong_event")
    if run.get("status") != "completed":
        return _decision("not_completed")
    if run.get("conclusion") != "success":
        return _decision("not_successful")
    if run.get("head_branch") != EXPECTED_BRANCH:
        return _decision("wrong_branch")
    target_sha = str(run.get("head_sha") or "").strip().lower()
    if not GIT_SHA_RE.fullmatch(target_sha):
        return _decision("invalid_head_sha")
    if head_repository.get("full_name") != EXPECTED_REPOSITORY:
        return _decision("wrong_head_repository")
    run_id = run.get("id")
    run_attempt = run.get("run_attempt")
    if (not isinstance(run_id, int) or isinstance(run_id, bool) or run_id < 1 or
            not isinstance(run_attempt, int) or isinstance(run_attempt, bool) or run_attempt < 1):
        return _decision("invalid_run_identity")
    return TriggerDecision(
        eligible=True,
        reason="eligible",
        target_sha=target_sha,
        run_id=run_id,
        run_attempt=run_attempt,
    )


def evaluate_scheduled_runs(runs_payload: Any, ref_payload: Any) -> TriggerDecision:
    """Select a real successful contracts run for the exact current main commit."""
    ref = _mapping(ref_payload)
    ref_object = _mapping(ref.get("object"))
    target_sha = str(ref_object.get("sha") or "").strip().lower()
    if (
        ref.get("ref") != f"refs/heads/{EXPECTED_BRANCH}"
        or ref_object.get("type") != "commit"
        or not GIT_SHA_RE.fullmatch(target_sha)
    ):
        return _decision("invalid_main_ref")
    root = _mapping(runs_payload)
    runs = root.get("workflow_runs")
    if not isinstance(runs, list) or len(runs) > 100:
        return _decision("invalid_runs_payload")
    eligible: list[TriggerDecision] = []
    for candidate in runs:
        decision = evaluate_event({
            "action": "completed",
            "repository": {"full_name": EXPECTED_REPOSITORY, "default_branch": EXPECTED_BRANCH},
            "workflow_run": candidate,
        })
        if decision.eligible and decision.target_sha == target_sha:
            eligible.append(decision)
    if not eligible:
        return _decision("no_green_main_run")
    return max(eligible, key=lambda item: (item.run_id or 0, item.run_attempt or 0))


def decision_json(decision: TriggerDecision) -> str:
    return json.dumps(asdict(decision), separators=(",", ":"), sort_keys=True)


def github_output(decision: TriggerDecision) -> str:
    lines = [
        f"eligible={'true' if decision.eligible else 'false'}",
        f"reason={decision.reason}",
    ]
    if decision.eligible:
        lines.extend([
            f"target_sha={decision.target_sha}",
            f"run_id={decision.run_id}",
            f"run_attempt={decision.run_attempt}",
        ])
    return "\n".join(lines)


def _load_event(path: Path) -> Any:
    if not path.is_file() or path.stat().st_size > MAX_EVENT_BYTES:
        raise ValueError("invalid_event")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--event", type=Path)
    source.add_argument("--runs", type=Path)
    parser.add_argument("--ref", type=Path)
    parser.add_argument("--format", choices=("json", "github-output"), default="json")
    args = parser.parse_args(argv)
    try:
        if args.event is not None:
            if args.ref is not None:
                raise ValueError("invalid_event")
            event = _load_event(args.event)
            if not isinstance(event, dict) or not isinstance(event.get("workflow_run"), dict):
                raise ValueError("invalid_event")
            decision = evaluate_event(event)
        else:
            if args.ref is None:
                raise ValueError("invalid_event")
            decision = evaluate_scheduled_runs(_load_event(args.runs), _load_event(args.ref))
        output = decision_json(decision) if args.format == "json" else github_output(decision)
        print(output)
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
        print('{"error":"invalid_event"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
