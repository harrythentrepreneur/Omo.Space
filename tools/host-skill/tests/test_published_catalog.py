from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "site" / "catalog.js"
SLUG = "customer-feedback-theme-finder"


def test_promoted_customer_feedback_workflow_is_catalogued_and_visible():
    source = CATALOG.read_text(encoding="utf-8")
    generated_block = source.split("// host-skill:generated:start", 1)[1].split(
        "// host-skill:generated:end", 1
    )[0]
    visible_block = source.split("window.OMO_VISIBLE_SLUGS = [", 1)[1].split(
        "];", 1
    )[0]

    assert f'"slug": "{SLUG}"' in generated_block
    assert f"'{SLUG}'" in visible_block
