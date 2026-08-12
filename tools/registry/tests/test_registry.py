from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from tools.registry import build_seed_data, export_catalog, import_tools


ROOT = Path(__file__).resolve().parents[3]


def _sqlite_registry() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE tools (
          slug TEXT PRIMARY KEY,
          tool_id TEXT NOT NULL UNIQUE,
          tier INTEGER NOT NULL,
          name TEXT NOT NULL,
          description TEXT NOT NULL,
          maker TEXT NOT NULL,
          owner_id TEXT,
          category TEXT NOT NULL,
          manifest TEXT NOT NULL,
          catalog_json TEXT NOT NULL,
          manifest_sha256 TEXT NOT NULL,
          price_cents INTEGER NOT NULL,
          status TEXT NOT NULL,
          version INTEGER NOT NULL,
          chargeable INTEGER NOT NULL,
          active INTEGER NOT NULL,
          runtime_family TEXT,
          runner_release TEXT NOT NULL,
          adapter_key TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
    )
    return connection


def _exported_tools(rendered: str) -> list[dict]:
    match = re.search(r"window\.OMO_REGISTRY_TOOLS = (\[.*\]);\n$", rendered, re.DOTALL)
    assert match
    return json.loads(match.group(1))


def test_seed_data_matches_both_source_inventories() -> None:
    phonics = json.loads(import_tools.PHONICS_PATH.read_text(encoding="utf-8"))
    current = json.loads(import_tools.CURRENT_PATH.read_text(encoding="utf-8"))
    reparsed = build_seed_data.parse_phonics_inventory(
        build_seed_data.PLAN.read_text(encoding="utf-8")
    )
    assert phonics == reparsed
    assert phonics["count"] == len(phonics["tools"]) == 96
    assert sum(tool["current_state"] in import_tools.PROMPT_STATES for tool in phonics["tools"]) == 93
    assert sum(tool["current_state"] in import_tools.HEAVY_STATES for tool in phonics["tools"]) == 3
    assert current["count"] == len(current["tools"]) == 24
    assert len({tool["slug"] for tool in current["tools"]}) == 24


def test_registry_rows_are_complete_versioned_and_honest() -> None:
    rows = import_tools.load_registry_rows()
    phonics = [row for row in rows if row["owner_id"] == "phonicsmaker"]
    current = [row for row in rows if row["manifest"]["source"] == "current_catalog"]
    assert len(rows) == 120
    assert len({row["slug"] for row in rows}) == 120
    assert len(phonics) == 96
    assert len(current) == 24
    assert sum(row["tier"] == 2 for row in phonics) == 93
    assert sum(row["tier"] == 1 for row in phonics) == 3
    assert {row["status"] for row in phonics} == {"draft", "review"}
    assert all(row["version"] == 1 and not row["chargeable"] and not row["active"] for row in phonics)
    assert all(row["catalog_json"]["price_cents"] is None for row in phonics)
    assert all(row["status"] == "live" and row["chargeable"] and row["active"] for row in current)
    assert all(row["catalog_json"]["price_cents"] == row["price_cents"] for row in current)


def test_tier_two_manifests_are_data_with_explicit_review_gates() -> None:
    tier_two = [row for row in import_tools.phonics_rows() if row["tier"] == 2]
    assert len(tier_two) == 93
    for row in tier_two:
        manifest = row["manifest"]
        assert manifest["spec_version"] == "omo.llm-tool/v1"
        assert manifest["prompt"]["review_status"] == "placeholder_requires_human_review"
        assert "NOT EXECUTABLE" in manifest["prompt"]["system_template"]
        assert manifest["model_policy"]["review_status"] == "provider_and_model_not_approved"
        assert manifest["pricing"]["chargeable"] is False
        for schema_name in ("input_schema", "output_schema"):
            schema = manifest[schema_name]
            assert schema["$schema"].endswith("draft/2020-12/schema")
            assert schema["type"] == "object"
            assert schema["additionalProperties"] is False


def test_heavy_manifests_use_owned_artifacts_and_drop_legacy_identity_fields() -> None:
    heavy = {row["slug"]: row for row in import_tools.phonics_rows() if row["tier"] == 1}
    assert set(heavy) == {
        "illustrated-decodable-story-maker",
        "phonics-story-editor",
        "phonics-story-edit-studio",
    }
    for row in heavy.values():
        serialized = json.dumps(row["manifest"], sort_keys=True)
        assert row["runtime_family"] == "omo-pdf@1"
        assert row["manifest"]["readiness"]["can_submit"] is False
        assert "user_email" not in serialized
        assert "debug_config" not in serialized
        assert "pdf_url" not in serialized
    editor_input = heavy["phonics-story-editor"]["manifest"]["input_schema"]
    assert "source_artifact_id" in editor_input["properties"]
    assert editor_input["oneOf"] == [{"required": ["command"]}, {"required": ["operations"]}]


def test_import_is_idempotent() -> None:
    rows = import_tools.load_registry_rows()
    connection = _sqlite_registry()
    try:
        import_tools.upsert_tools(connection, rows, dialect="sqlite")
        first = connection.execute(
            "SELECT slug, tool_id, manifest_sha256, price_cents, status FROM tools ORDER BY slug"
        ).fetchall()
        import_tools.upsert_tools(connection, rows, dialect="sqlite")
        second = connection.execute(
            "SELECT slug, tool_id, manifest_sha256, price_cents, status FROM tools ORDER BY slug"
        ).fetchall()
        assert first == second
        assert connection.execute("SELECT COUNT(*) FROM tools").fetchone()[0] == 120
    finally:
        connection.close()


def test_export_shape_and_honest_price_projection() -> None:
    source_rows = import_tools.load_registry_rows()
    database_rows = [
        {
            key: row[key]
            for key in (
                "slug",
                "tier",
                "name",
                "description",
                "maker",
                "category",
                "price_cents",
                "status",
                "chargeable",
                "active",
                "version",
                "catalog_json",
            )
        }
        for row in source_rows
    ]
    rendered = export_catalog.render_catalog_js(database_rows)
    exported = _exported_tools(rendered)
    assert len(exported) == 120
    assert all(
        set(tool)
        == {
            "slug",
            "title",
            "description",
            "maker",
            "category",
            "tier",
            "tierLabel",
            "status",
            "statusLabel",
            "chargeable",
            "active",
            "priceCents",
            "priceLabel",
            "version",
            "source",
        }
        for tool in exported
    )
    phonics = [tool for tool in exported if tool["source"] == "phonicsmaker"]
    live = [tool for tool in exported if tool["status"] == "live"]
    assert len(phonics) == 96 and all(tool["priceCents"] is None for tool in phonics)
    assert len(live) == 24 and all(tool["priceCents"] > 0 for tool in live)
    assert "system_template" not in rendered
    assert "adapter_key" not in rendered


def test_schema_and_registry_page_are_wired_without_touching_live_catalogs() -> None:
    schema = import_tools.registry_schema_sql()
    for field in (
        "slug",
        "tool_id",
        "tier",
        "manifest",
        "price_cents",
        "status",
        "version",
        "chargeable",
        "active",
    ):
        assert re.search(rf"\b{field}\b", schema)
    page = (ROOT / "site" / "registry.html").read_text(encoding="utf-8")
    assert '<script src="ig-registry.js"></script>' in page
    assert "tool.statusLabel" in page
    assert "tool.chargeable && tool.priceLabel" in page
    assert "Activation gated" in page
