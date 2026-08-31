"""Protected control-plane Worker deployment workflow contracts."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "trusted-control-plane-deploy.yml"
PIN = "3a92372abf910f1ea26ba21d488a9ab5e6fc2b36"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_control_plane_deploy_is_main_only_environment_gated_and_secret_scoped() -> None:
    value = yaml.safe_load(workflow_text())
    trigger = value.get(True) or value.get("on")
    assert trigger == {"workflow_dispatch": {}}
    assert value["permissions"] == {"contents": "read"}
    job = value["jobs"]["deploy"]
    assert job["if"] == "github.repository == 'harrythentrepreneur/Omo.Space' && github.ref == 'refs/heads/main'"
    assert job["environment"] == "Production"
    assert job["concurrency"] == {"group": "trusted-control-plane-deploy", "cancel-in-progress": False}
    text = workflow_text()
    assert "persist-credentials: false" in text
    assert "CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}" in text
    assert "CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}" in text
    assert text.count("CLOUDFLARE_API_TOKEN:") == 2
    assert "pull_request_target" not in text


def test_control_plane_deploy_proves_exact_source_dry_run_deploy_and_live_pin() -> None:
    text = workflow_text()
    package = (ROOT / "site" / "deploy" / "package.json").read_text(encoding="utf-8")
    lock = (ROOT / "site" / "deploy" / "package-lock.json").read_text(encoding="utf-8")
    assert "ref: ${{ github.sha }}" in text
    assert "test \"$(git rev-parse HEAD)\" = \"$GITHUB_SHA\"" in text
    assert "npm ci --ignore-scripts" in text
    assert '"wrangler": "4.125.0"' in package
    assert '"node_modules/wrangler"' in lock and '"version": "4.125.0"' in lock
    assert "npx --no-install wrangler --version | grep -Fx '4.125.0'" in text
    assert "wrangler@" not in text
    assert "npx --no-install wrangler deploy --dry-run --keep-vars --env=\"\"" in text
    assert "npx --no-install wrangler deploy --keep-vars --env=\"\" --message \"omo-control-plane:$GITHUB_SHA\"" in text
    assert "tee \"$RUNNER_TEMP/deploy.log\"" in text
    assert "npx --no-install wrangler deployments status --json --env=\"\"" in text
    assert "npx --no-install wrangler versions view \"$version_id\" --json --env=\"\"" in text
    assert "verify_control_plane_deployment.py" in text
    assert "--deploy-log \"$RUNNER_TEMP/deploy.log\"" in text
    assert PIN in text
    assert "OMO_BUILDER_BASE_REVISION" in text
