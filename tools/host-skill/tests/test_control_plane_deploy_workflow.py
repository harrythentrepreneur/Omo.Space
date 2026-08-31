"""Protected control-plane Worker deployment workflow contracts."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "trusted-control-plane-deploy.yml"
PIN = "d0b5ace1116f1483c7e818cab775b68ab357e2a6"


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
    assert "ref: ${{ github.sha }}" in text
    assert "test \"$(git rev-parse HEAD)\" = \"$GITHUB_SHA\"" in text
    assert "npm ci --ignore-scripts" in text
    assert "npx wrangler@4.123.0 deploy --dry-run --keep-vars --env=\"\"" in text
    assert "npx wrangler@4.123.0 deploy --keep-vars --env=\"\"" in text
    assert "npx wrangler@4.123.0 deployments status --json --env=\"\"" in text
    assert "npx wrangler@4.123.0 versions view \"$version_id\" --json --env=\"\"" in text
    assert "${{ steps.allocation.outputs.version_id }}" not in text
    assert PIN in text
    assert "OMO_BUILDER_BASE_REVISION" in text
    assert "allocation" in text
