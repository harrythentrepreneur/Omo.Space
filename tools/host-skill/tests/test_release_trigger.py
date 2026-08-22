"""Credential-free GitHub workflow-run trigger contracts."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "tools" / "host-skill" / "release_trigger.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "trusted-release-trigger.yml"
SHA = "a" * 40


def load_module():
    spec = importlib.util.spec_from_file_location("release_trigger", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def valid_event() -> dict:
    return {
        "action": "completed",
        "repository": {
            "full_name": "harrythentrepreneur/Omo.Space",
            "default_branch": "main",
        },
        "workflow_run": {
            "id": 123456789,
            "run_attempt": 1,
            "name": "generated-workflow-contracts",
            "path": ".github/workflows/generated-workflow-contracts.yml",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": SHA,
            "head_repository": {"full_name": "harrythentrepreneur/Omo.Space"},
        },
    }


def test_valid_completed_main_contract_is_eligible():
    mod = load_module()
    decision = mod.evaluate_event(valid_event())
    assert decision == mod.TriggerDecision(
        eligible=True,
        reason="eligible",
        target_sha=SHA,
        run_id=123456789,
        run_attempt=1,
    )
    assert json.loads(mod.decision_json(decision)) == {
        "eligible": True,
        "reason": "eligible",
        "run_attempt": 1,
        "run_id": 123456789,
        "target_sha": SHA,
    }
    assert mod.decision_json(decision) == json.dumps(
        json.loads(mod.decision_json(decision)), separators=(",", ":"), sort_keys=True
    )


@pytest.mark.parametrize(
    ("path", "value", "reason"),
    [
        (("action",), "requested", "wrong_action"),
        (("repository", "full_name"), "attacker/fork", "wrong_repository"),
        (("repository", "default_branch"), "develop", "wrong_default_branch"),
        (("workflow_run", "name"), "evil", "wrong_workflow"),
        (("workflow_run", "path"), ".github/workflows/evil.yml", "wrong_workflow_path"),
        (("workflow_run", "event"), "pull_request", "wrong_event"),
        (("workflow_run", "status"), "in_progress", "not_completed"),
        (("workflow_run", "conclusion"), "failure", "not_successful"),
        (("workflow_run", "head_branch"), "feature", "wrong_branch"),
        (("workflow_run", "head_sha"), "b" * 39, "invalid_head_sha"),
        (("workflow_run", "head_repository", "full_name"), "attacker/fork", "wrong_head_repository"),
        (("workflow_run", "id"), 0, "invalid_run_identity"),
        (("workflow_run", "run_attempt"), 0, "invalid_run_identity"),
    ],
)
def test_ineligible_or_invalid_trigger_never_returns_a_target(path, value, reason):
    mod = load_module()
    event = valid_event()
    cursor = event
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    decision = mod.evaluate_event(event)
    assert decision.eligible is False
    assert decision.reason == reason
    assert decision.target_sha is None


def test_extra_fields_are_ignored_but_never_echoed():
    mod = load_module()
    event = valid_event()
    event["secret"] = "SENTINEL_MUST_NOT_ESCAPE"
    event["workflow_run"]["display_title"] = "SENTINEL_MUST_NOT_ESCAPE"
    output = mod.decision_json(mod.evaluate_event(event))
    assert "SENTINEL" not in output
    assert "display_title" not in output


def test_cli_json_and_github_output_are_bounded(tmp_path, capsys):
    mod = load_module()
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(valid_event()), encoding="utf-8")
    assert mod.main(["--event", str(event_path), "--format", "json"]) == 0
    assert capsys.readouterr().out.strip() == (
        '{"eligible":true,"reason":"eligible","run_attempt":1,'
        '"run_id":123456789,"target_sha":"' + SHA + '"}'
    )
    assert mod.main(["--event", str(event_path), "--format", "github-output"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "eligible=true",
        "reason=eligible",
        f"target_sha={SHA}",
        "run_id=123456789",
        "run_attempt=1",
    ]


def test_cli_malformed_payload_fails_closed_without_echo(tmp_path, capsys):
    mod = load_module()
    event_path = tmp_path / "event.json"
    event_path.write_text('{"secret":"SENTINEL_MUST_NOT_ESCAPE"}', encoding="utf-8")
    assert mod.main(["--event", str(event_path), "--format", "json"]) == 2
    output = capsys.readouterr().out.strip()
    assert output == '{"error":"invalid_event"}'
    assert "SENTINEL" not in output


def test_workflow_separates_credential_free_trigger_from_protected_finalizer():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert workflow["name"] == "trusted-release-trigger"
    assert workflow["on"] == {
        "workflow_run": {
            "workflows": ["generated-workflow-contracts"],
            "types": ["completed"],
        }
    }
    assert workflow["permissions"] == {"actions": "read", "contents": "read"}
    assert "workflow_dispatch" not in text
    assert "pull_request_target" not in text
    assert "persist-credentials: false" in text
    assert "11d5960a326750d5838078e36cf38b85af677262" in text
    assert "github.event.workflow_run.head_sha" not in text
    assert "steps.trigger.outputs.target_sha" in text
    assert "git -C target rev-parse HEAD" in text

    evaluate = yaml.dump(workflow["jobs"]["evaluate"])
    assert "secrets." not in evaluate
    assert "wrangler" not in evaluate.lower()
    assert "modal" not in evaluate.lower()
    finalize = workflow["jobs"]["finalize"]
    assert finalize["environment"] == "Production"
    assert "ISSUE141_PRODUCTION_FINALIZER_ENABLED" in finalize["if"]
    assert "secrets.RELEASE_FINALIZER_TOKEN" in yaml.dump(finalize)
