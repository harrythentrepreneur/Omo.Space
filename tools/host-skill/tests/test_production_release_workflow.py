"""Fail-closed contracts for the protected production finalizer workflow."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "trusted-release-trigger.yml"
EXPECTED_SECRETS = {
    "RELEASE_FINALIZER_TOKEN",
    "MODAL_TOKEN_ID",
    "MODAL_TOKEN_SECRET",
    "CLOUDFLARE_API_TOKEN",
    "CLOUDFLARE_ACCOUNT_ID",
    "HOSTED_MODAL_PROXY_TOKEN_ID",
    "HOSTED_MODAL_PROXY_TOKEN_SECRET",
    "PRODUCTION_CANARY_API_KEY",
}


def workflow():
    value = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_production_job_is_environment_protected_and_disabled_until_live_proof():
    data = workflow()
    job = data["jobs"]["finalize"]
    assert job["environment"] == "Production"
    assert job["needs"] == "evaluate"
    assert job["if"] == "needs.evaluate.outputs.eligible == 'true' && vars.ISSUE141_PRODUCTION_FINALIZER_ENABLED == 'true'"
    assert data["concurrency"] == {
        "group": "trusted-production-release", "cancel-in-progress": False,
    }


def test_production_job_uses_only_exact_environment_secrets_and_read_only_github_token():
    data = workflow()
    steps = data["jobs"]["finalize"]["steps"]
    finalizer = next(step for step in steps if step.get("name") == "Run deterministic production finalizer")
    env = finalizer["env"]
    assert set(env) == EXPECTED_SECRETS | {"GITHUB_TOKEN"}
    assert env["GITHUB_TOKEN"] == "${{ github.token }}"
    for name in EXPECTED_SECRETS:
        assert env[name] == "${{ secrets." + name + " }}"
    assert data["permissions"] == {"actions": "read", "contents": "read"}
    assert all("permissions" not in job for job in data["jobs"].values())


def test_exact_sha_checkout_and_controller_cli_have_no_user_selectable_target():
    data = workflow()
    steps = data["jobs"]["finalize"]["steps"]
    checkout = steps[0]
    assert checkout["with"]["ref"] == "${{ needs.evaluate.outputs.target_sha }}"
    assert checkout["with"]["persist-credentials"] is False
    assert checkout["with"]["fetch-depth"] == 0
    assert checkout["with"]["path"] == "target"
    command = steps[-1]["run"]
    assert "production_release_controller.py" in command
    assert "--trigger-sha" in command and "--run-id" in command and "--run-attempt" in command
    for forbidden in ("--repository", "--branch", "--target", "--provider", "--environment", "--url"):
        assert forbidden not in command


def test_every_action_is_immutable_and_evaluate_job_remains_credential_free():
    data = workflow()
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            uses = step.get("uses")
            if uses:
                sha = uses.rsplit("@", 1)[-1].split()[0]
                assert len(sha) == 40 and all(char in "0123456789abcdef" for char in sha)
    evaluate_text = yaml.safe_dump(data["jobs"]["evaluate"], sort_keys=True)
    assert "secrets." not in evaluate_text
    assert "pull_request_target" not in WORKFLOW.read_text(encoding="utf-8")
