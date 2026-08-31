"""Protected error-only Worker tail workflow contract."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/trusted-builder-cron-diagnostic.yml"


def test_builder_tail_is_main_only_protected_read_only_and_bounded() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    value = yaml.safe_load(text)
    trigger = value.get(True) or value.get("on")
    assert trigger == {"workflow_dispatch": {}}
    assert value["permissions"] == {"contents": "read"}
    job = value["jobs"]["tail"]
    assert job["if"] == "github.repository == 'harrythentrepreneur/Omo.Space' && github.ref == 'refs/heads/main'"
    assert job["environment"] == "Production"
    assert "persist-credentials: false" in text
    assert "npm ci --ignore-scripts" in text
    assert "npx --no-install wrangler --version | grep -Fx '4.125.0'" in text
    assert "timeout 100s npx --no-install wrangler tail cognition-demos --format json --status error --env=\"\"" in text
    assert text.count("CLOUDFLARE_API_TOKEN:") == 1
    assert text.count("CLOUDFLARE_ACCOUNT_ID:") == 1
    assert "wrangler deploy" not in text.lower()
    assert "wrangler versions upload" not in text.lower()
    assert "pull_request_target" not in text
