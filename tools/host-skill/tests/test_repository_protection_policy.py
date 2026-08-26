"""Repository-owned trusted-release protection contracts for Issue #141."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
WORKFLOWS = ROOT / ".github" / "workflows"
OWNERS = "@harrythentrepreneur @kaviru2"


def test_deployment_sensitive_paths_require_maintainer_review():
    lines = {
        line.strip()
        for line in CODEOWNERS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    required = {
        f"/.github/CODEOWNERS {OWNERS}",
        f"/.github/workflows/ {OWNERS}",
        f"/tools/host-skill/release_*.py {OWNERS}",
        f"/tools/host-skill/production_release_controller.py {OWNERS}",
        f"/tools/host-skill/process-submissions.py {OWNERS}",
        f"/tools/host-skill/*release*_adapters.py {OWNERS}",
        f"/tools/host-skill/*release*_transport.py {OWNERS}",
        f"/site/deploy/worker.js {OWNERS}",
        f"/site/deploy/wrangler.toml {OWNERS}",
        f"/site/deploy/package.json {OWNERS}",
        f"/site/deploy/package-lock.json {OWNERS}",
        f"/site/deploy/schema.sql {OWNERS}",
        f"/site/deploy/*d1-schema.sql {OWNERS}",
        f"/site/deploy/hosted-skills.generated.mjs {OWNERS}",
        f"/site/deploy/run-manifests/ {OWNERS}",
        f"/site/catalog.js {OWNERS}",
        f"/containers/*/modal_app.py {OWNERS}",
    }
    assert required <= lines


def test_all_github_actions_are_immutable_sha_pins():
    action_pattern = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
    sha_pattern = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
    actions: list[str] = []
    workflows = sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])
    for workflow in workflows:
        actions.extend(action_pattern.findall(workflow.read_text(encoding="utf-8")))
    assert actions
    assert all(sha_pattern.fullmatch(action) for action in actions), actions


def test_workflows_have_minimal_permissions_and_no_pr_target():
    workflows = sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])
    assert workflows
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        assert "pull_request_target" not in text
        expected = {"contents": "read"}
        if workflow.name == "trusted-release-trigger.yml":
            expected["actions"] = "read"
        elif workflow.name == "trusted-release-merge.yml":
            expected = {
                "actions": "read",
                "checks": "read",
                "contents": "write",
                "pull-requests": "write",
            }
        assert parsed.get("permissions") == expected
        assert all("permissions" not in job for job in parsed.get("jobs", {}).values())
    trigger = (WORKFLOWS / "trusted-release-trigger.yml").read_text(encoding="utf-8")
    assert "persist-credentials: false" in trigger
