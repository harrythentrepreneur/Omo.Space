from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "site" / "catalog.js"
PROFILE = ROOT / "packages" / "skill-to-modal" / "profiles" / "dummy-word-list-organizer.json"
HOSTED_PROFILE = ROOT / "containers" / "dummy-word-list-organizer" / "hosted-profile.json"
SLUG = "customer-feedback-theme-finder"


def test_promoted_customer_feedback_workflow_is_catalogued_and_visible():
    assert_catalogued_and_visible(SLUG)


def assert_catalogued_and_visible(slug: str) -> None:
    source = CATALOG.read_text(encoding="utf-8")
    generated_block = source.split("// host-skill:generated:start", 1)[1].split(
        "// host-skill:generated:end", 1
    )[0]
    visible_block = source.split("window.OMO_VISIBLE_SLUGS = [", 1)[1].split(
        "];", 1
    )[0]

    assert f'"slug": "{slug}"' in generated_block
    assert f"'{slug}'" in visible_block


def test_promoted_dummy_word_list_workflow_is_catalogued_and_visible():
    assert_catalogued_and_visible("dummy-word-list-organizer")


def test_promoted_release_tag_sorter_is_catalogued_and_visible():
    assert_catalogued_and_visible("release-tag-sorter-canary")


def test_promoted_dummy_publication_is_canonical_and_reproducible():
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    hosted = json.loads(HOSTED_PROFILE.read_text(encoding="utf-8"))

    assert profile["marketplace"]["catalog_managed"] is True
    assert profile["marketplace"]["storefront_visible"] is True
    assert hosted["catalog_managed"] is profile["marketplace"]["catalog_managed"]
    assert hosted["storefront_visible"] is profile["marketplace"]["storefront_visible"]
