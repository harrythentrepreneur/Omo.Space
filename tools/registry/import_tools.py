#!/usr/bin/env python3
"""Build and idempotently import Omo registry rows into Neon."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import stat
import uuid
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
SCHEMA_PATH = ROOT / "site" / "deploy" / "schema.sql"
TEMPLATES_PATH = HERE / "manifest-templates.json"
PHONICS_PATH = DATA_DIR / "phonicsmaker-tools.json"
CURRENT_PATH = DATA_DIR / "current-catalog.json"
REGISTRY_NAMESPACE = uuid.UUID("8b3b56ad-8be6-49b7-9c40-3c67290152b0")
SEED_TIMESTAMP = "2026-08-13T00:00:00+06:00"
SCHEMA_START = "-- registry:tools:start"
SCHEMA_END = "-- registry:tools:end"
PROMPT_STATES = {"A", "P"}
HEAVY_STATES = {"G", "E", "S"}
VALID_STATUSES = {"draft", "review", "live", "disabled"}

COLUMNS = (
    "slug",
    "tool_id",
    "tier",
    "name",
    "description",
    "maker",
    "owner_id",
    "category",
    "manifest",
    "catalog_json",
    "manifest_sha256",
    "price_cents",
    "status",
    "version",
    "chargeable",
    "active",
    "runtime_family",
    "runner_release",
    "adapter_key",
    "created_at",
    "updated_at",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _tool_id(slug: str) -> str:
    return str(uuid.uuid5(REGISTRY_NAMESPACE, slug))


def _schema_base(slug: str, direction: str, title: str) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://omo.space/schemas/{slug}/{direction}.json",
        "title": title,
        "type": "object",
        "additionalProperties": False,
    }


def _split_sketch(sketch: str) -> list[tuple[str, str]]:
    if not sketch.startswith("{") or not sketch.endswith("}"):
        raise ValueError(f"invalid inventory input sketch: {sketch}")
    fields: list[tuple[str, str]] = []
    for item in sketch[1:-1].split(","):
        for alternative in item.split("|"):
            name, kind = alternative.strip().split(":", 1)
            fields.append((name, kind))
    return fields


def _field_schema(kind: str) -> dict:
    if kind == "s":
        return {"type": "string", "minLength": 1, "maxLength": 4000}
    if kind == "s[]":
        return {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 200},
            "minItems": 1,
            "maxItems": 32,
        }
    if kind == "i":
        return {"type": "integer", "minimum": 1, "maximum": 100}
    if kind == "b":
        return {"type": "boolean"}
    if kind == "e":
        return {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "x-omo-review-required": "replace with the recovered source enum before activation",
        }
    if kind == "o":
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
            "x-omo-review-required": "recover the bounded object properties before activation",
        }
    if kind == "o[]":
        return {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {},
                "x-omo-review-required": "recover operation properties before activation",
            },
            "minItems": 1,
            "maxItems": 64,
        }
    raise ValueError(f"unsupported inventory type {kind}")


def _input_schema(tool: dict) -> dict:
    slug = tool["slug"]
    schema = _schema_base(slug, "input", f"{tool['name']} input")
    properties = {name: _field_schema(kind) for name, kind in _split_sketch(tool["input_sketch"])}
    schema.update(
        {
            "description": (
                "Draft schema projected from the reviewed inventory. Exact enum values, defaults, "
                "and optionality remain an activation gate."
            ),
            "properties": properties,
            "required": list(properties),
            "x-omo-review-status": "schema_sketch_not_approved_for_execution",
        }
    )

    if slug == "phonics-story-editor":
        schema["properties"] = {
            "source_artifact_id": {
                "type": "string",
                "minLength": 8,
                "maxLength": 200,
                "description": "Opaque ID for an artifact owned by the authenticated Omo user.",
            },
            "command": {"type": "string", "minLength": 3, "maxLength": 4000},
            "operations": {
                "type": "array",
                "minItems": 1,
                "maxItems": 64,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "operation": {"type": "string", "minLength": 1, "maxLength": 100},
                        "target": {"type": "string", "maxLength": 200},
                        "value": {"type": ["string", "number", "boolean", "null"]},
                    },
                    "required": ["operation"],
                },
            },
        }
        schema["required"] = ["source_artifact_id"]
        schema["oneOf"] = [{"required": ["command"]}, {"required": ["operations"]}]
    elif slug == "phonics-story-edit-studio":
        schema["properties"]["source_artifact_id"]["description"] = (
            "Opaque ID for an artifact owned by the authenticated Omo user."
        )
        schema["properties"]["story_data"] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "story_title": {"type": "string", "minLength": 1, "maxLength": 200},
                "phonemes": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1, "maxLength": 20},
                    "maxItems": 32,
                },
                "pages": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 24,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "pageNumber": {"type": "integer", "minimum": 0, "maximum": 24},
                            "objects": {"type": "array", "maxItems": 100, "items": {"type": "object"}},
                        },
                        "required": ["pageNumber", "objects"],
                    },
                },
            },
            "required": ["story_title", "pages"],
        }
    return schema


def _list_output_schema(tool: dict) -> dict:
    schema = _schema_base(tool["slug"], "output", f"{tool['name']} output")
    schema.update(
        {
            "properties": {
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {"type": "string", "minLength": 1, "maxLength": 300},
                            "detail": {"type": "string", "maxLength": 1200},
                        },
                        "required": ["label"],
                    },
                },
                "notes": {
                    "type": "array",
                    "maxItems": 20,
                    "items": {"type": "string", "maxLength": 500},
                },
            },
            "required": ["items", "notes"],
        }
    )
    return schema


def _analysis_output_schema(tool: dict) -> dict:
    schema = _schema_base(tool["slug"], "output", f"{tool['name']} output")
    schema.update(
        {
            "properties": {
                "summary": {"type": "string", "minLength": 1, "maxLength": 1200},
                "findings": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "text": {"type": "string", "minLength": 1, "maxLength": 500},
                            "explanation": {"type": "string", "maxLength": 1200},
                        },
                        "required": ["text", "explanation"],
                    },
                },
            },
            "required": ["summary", "findings"],
        }
    )
    return schema


def _draft_output_schema(tool: dict) -> dict:
    schema = _schema_base(tool["slug"], "output", f"{tool['name']} output")
    schema.update(
        {
            "properties": {
                "title": {"type": "string", "minLength": 1, "maxLength": 200},
                "body_markdown": {"type": "string", "minLength": 1, "maxLength": 20000},
                "notes": {
                    "type": "array",
                    "maxItems": 20,
                    "items": {"type": "string", "maxLength": 500},
                },
            },
            "required": ["title", "body_markdown", "notes"],
        }
    )
    return schema


def _artifact_output_schema(tool: dict) -> dict:
    schema = _schema_base(tool["slug"], "output", f"{tool['name']} result")
    schema.update(
        {
            "properties": {
                "spec_version": {"const": "omo.result/v1"},
                "run_id": {"type": "string", "minLength": 8, "maxLength": 200},
                "tool_id": {"const": _tool_id(tool["slug"])},
                "tool_version": {"const": 1},
                "status": {"const": "completed"},
                "data": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "summary": {"type": "string", "maxLength": 1200},
                        "content_report": {"type": "array", "maxItems": 50, "items": {"type": "string"}},
                    },
                    "required": ["summary", "content_report"],
                },
                "artifacts": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "artifact_id": {"type": "string", "minLength": 8, "maxLength": 200},
                            "role": {"enum": ["pdf", "thumbnail", "editable_json"]},
                            "mime_type": {"type": "string", "minLength": 3, "maxLength": 100},
                            "bytes": {"type": "integer", "minimum": 1, "maximum": 52428800},
                            "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                        },
                        "required": ["artifact_id", "role", "mime_type", "bytes", "sha256"],
                    },
                },
                "usage": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "provider_calls": {"type": "integer", "minimum": 0, "maximum": 100},
                        "estimated_cost_usd": {"type": "number", "minimum": 0},
                    },
                    "required": ["provider_calls", "estimated_cost_usd"],
                },
            },
            "required": [
                "spec_version",
                "run_id",
                "tool_id",
                "tool_version",
                "status",
                "data",
                "artifacts",
                "usage",
            ],
        }
    )
    return schema


def _output_schema(tool: dict) -> dict:
    kind = tool["output_kind"][0]
    if kind == "L":
        return _list_output_schema(tool)
    if kind == "R":
        return _analysis_output_schema(tool)
    if kind == "D":
        return _draft_output_schema(tool)
    if kind == "F":
        return _artifact_output_schema(tool)
    raise ValueError(f"unsupported output kind {tool['output_kind']}")


def _phonics_manifest(tool: dict, templates: dict) -> dict:
    tier = 2 if tool["current_state"] in PROMPT_STATES else 1
    manifest = copy.deepcopy(templates["llm" if tier == 2 else "runtime"])
    manifest.update(
        {
            "tool_id": _tool_id(tool["slug"]),
            "slug": tool["slug"],
            "version": 1,
            "tier": tier,
            "source": "phonicsmaker_inventory",
            "source_contract": tool["current_state"],
            "input_schema": _input_schema(tool),
            "output_schema": _output_schema(tool),
            "pricing": {
                "planned_price_cents": tool["planned_price_cents"],
                "chargeable": False,
                "quote_status": "inventory_estimate_not_billing_authority",
            },
            "publication": {
                "active": False,
                "honest_gate": "provider adapter, exact schema/prompt review, evaluation, and QA required",
            },
        }
    )
    return manifest


def _catalog_projection(
    *, tool: dict, tier: int, status: str, chargeable: bool, price_cents: int, source: str
) -> dict:
    return {
        "slug": tool["slug"],
        "title": tool["name"],
        "description": tool["description"],
        "maker": tool["maker"] if "maker" in tool else "PhonicsMaker",
        "category": tool["category"],
        "tier": tier,
        "tier_label": {1: "Tier 1 · Shared runtime", 2: "Tier 2 · Pure LLM", 3: "Tier 3 · Download"}[tier],
        "status": status,
        "status_label": {
            "live": "Live",
            "review": "Coming soon — in review",
            "draft": "Coming soon — draft",
            "disabled": "Unavailable",
        }[status],
        "chargeable": chargeable,
        "price_cents": price_cents if chargeable and status == "live" else None,
        "source": source,
    }


def _row(
    *,
    slug: str,
    tier: int,
    name: str,
    description: str,
    maker: str,
    owner_id: str | None,
    category: str,
    manifest: dict,
    catalog_json: dict,
    price_cents: int,
    status: str,
    chargeable: bool,
    active: bool,
    runtime_family: str | None,
    adapter_key: str | None,
) -> dict:
    canonical_manifest = _canonical_json(manifest)
    return {
        "slug": slug,
        "tool_id": _tool_id(slug),
        "tier": tier,
        "name": name,
        "description": description,
        "maker": maker,
        "owner_id": owner_id,
        "category": category,
        "manifest": manifest,
        "catalog_json": catalog_json,
        "manifest_sha256": hashlib.sha256(canonical_manifest.encode("utf-8")).hexdigest(),
        "price_cents": price_cents,
        "status": status,
        "version": 1,
        "chargeable": chargeable,
        "active": active,
        "runtime_family": runtime_family,
        "runner_release": "stable",
        "adapter_key": adapter_key,
        "created_at": SEED_TIMESTAMP,
        "updated_at": SEED_TIMESTAMP,
    }


def phonics_rows() -> list[dict]:
    source = _read_json(PHONICS_PATH)
    templates = _read_json(TEMPLATES_PATH)
    rows: list[dict] = []
    for tool in source["tools"]:
        tier = 2 if tool["current_state"] in PROMPT_STATES else 1
        status = "review" if tool["current_state"] in {"A", "G", "E", "S"} else "draft"
        manifest = _phonics_manifest(tool, templates)
        projection = _catalog_projection(
            tool=tool,
            tier=tier,
            status=status,
            chargeable=False,
            price_cents=tool["planned_price_cents"],
            source="phonicsmaker",
        )
        rows.append(
            _row(
                slug=tool["slug"],
                tier=tier,
                name=tool["name"],
                description=tool["description"],
                maker="PhonicsMaker",
                owner_id="phonicsmaker",
                category=tool["category"],
                manifest=manifest,
                catalog_json=projection,
                price_cents=tool["planned_price_cents"],
                status=status,
                chargeable=False,
                active=False,
                runtime_family="omo-pdf@1" if tier == 1 else None,
                adapter_key="openai-compatible-prod" if tier == 2 else None,
            )
        )
    return rows


def _current_tier(tool: dict) -> int:
    if tool["listing_type"] == "download":
        return 3
    steps = set(tool["workflow_step_types"])
    if "llm" in steps and steps <= {"llm", "pipeline"} and tool["slug"] != "japanese-style-story-video":
        return 2
    return 1


def current_catalog_rows() -> list[dict]:
    source = _read_json(CURRENT_PATH)
    rows: list[dict] = []
    for tool in source["tools"]:
        tier = _current_tier(tool)
        price_cents = tool["license_price_cents"] if tier == 3 else tool["run_price_cents"]
        manifest = {
            "spec_version": "omo.legacy-shadow-tool/v1",
            "tool_id": _tool_id(tool["slug"]),
            "slug": tool["slug"],
            "version": 1,
            "tier": tier,
            "source": "current_catalog",
            "migration_mode": "shadow_registry_existing_path_unchanged",
            "execution_kind": "download" if tier == 3 else ("legacy_llm" if tier == 2 else "legacy_workflow"),
            "legacy_contract": {
                "run_manifest": tool["run_manifest"],
                "workflow_step_types": tool["workflow_step_types"],
                "input_schema_status": "existing_live_contract_not_migrated",
            },
            "pricing": {
                "price_cents": price_cents,
                "license_price_cents": tool["license_price_cents"],
                "chargeable": True,
                "quote_status": "existing_live_catalog",
            },
            "publication": {"active": True, "status": "live"},
        }
        normalized = {
            **tool,
            "maker": tool["maker"],
        }
        projection = _catalog_projection(
            tool=normalized,
            tier=tier,
            status="live",
            chargeable=True,
            price_cents=price_cents,
            source="current_catalog",
        )
        projection["license_price_cents"] = tool["license_price_cents"]
        rows.append(
            _row(
                slug=tool["slug"],
                tier=tier,
                name=tool["name"],
                description=tool["description"],
                maker=tool["maker"],
                owner_id=tool["maker_handle"] or None,
                category=tool["category"],
                manifest=manifest,
                catalog_json=projection,
                price_cents=price_cents,
                status="live",
                chargeable=True,
                active=True,
                runtime_family="legacy-worker@1" if tier == 1 else None,
                adapter_key="legacy-worker" if tier == 2 else None,
            )
        )
    return rows


def load_registry_rows() -> list[dict]:
    rows = phonics_rows() + current_catalog_rows()
    validate_rows(rows)
    return rows


def validate_rows(rows: Iterable[dict]) -> None:
    materialized = list(rows)
    if len(materialized) != 120:
        raise ValueError(f"expected 120 registry rows, found {len(materialized)}")
    slugs = [row["slug"] for row in materialized]
    if len(set(slugs)) != len(slugs):
        raise ValueError("registry contains duplicate slugs")
    for row in materialized:
        if not row["slug"] or re.search(r"\s", row["slug"]):
            raise ValueError(f"invalid slug {row['slug']!r}")
        if row["status"] not in VALID_STATUSES:
            raise ValueError(f"invalid status for {row['slug']}")
        if row["status"] != "live" and (row["chargeable"] or row["active"]):
            raise ValueError(f"non-live row is active or chargeable: {row['slug']}")
        expected_hash = hashlib.sha256(_canonical_json(row["manifest"]).encode("utf-8")).hexdigest()
        if row["manifest_sha256"] != expected_hash:
            raise ValueError(f"manifest hash drift for {row['slug']}")
        public_price = row["catalog_json"]["price_cents"]
        if bool(row["chargeable"]) != (public_price is not None):
            raise ValueError(f"public price honesty mismatch for {row['slug']}")


def registry_schema_sql() -> str:
    source = SCHEMA_PATH.read_text(encoding="utf-8")
    if SCHEMA_START not in source or SCHEMA_END not in source:
        raise ValueError("registry schema markers are missing")
    return source.split(SCHEMA_START, 1)[1].split(SCHEMA_END, 1)[0].strip()


def _record_values(row: dict) -> tuple:
    return tuple(
        _canonical_json(row[column]) if column in {"manifest", "catalog_json"} else row[column]
        for column in COLUMNS
    )


def upsert_tools(connection: Any, rows: Iterable[dict], *, dialect: str = "postgres") -> None:
    materialized = list(rows)
    validate_rows(materialized)
    assignments = ", ".join(
        f"{column}=excluded.{column}" for column in COLUMNS if column not in {"slug", "created_at"}
    )
    if dialect == "postgres":
        placeholders = ["%s"] * len(COLUMNS)
        for column in ("manifest", "catalog_json"):
            placeholders[COLUMNS.index(column)] = "%s::jsonb"
        sql = (
            f"INSERT INTO tools ({', '.join(COLUMNS)}) VALUES ({', '.join(placeholders)}) "
            f"ON CONFLICT (slug) DO UPDATE SET {assignments}"
        )
    elif dialect == "sqlite":
        sql = (
            f"INSERT INTO tools ({', '.join(COLUMNS)}) VALUES ({', '.join(['?'] * len(COLUMNS))}) "
            f"ON CONFLICT (slug) DO UPDATE SET {assignments}"
        )
    else:
        raise ValueError(f"unsupported database dialect: {dialect}")
    cursor = connection.cursor()
    try:
        cursor.executemany(sql, [_record_values(row) for row in materialized])
    finally:
        cursor.close()
    connection.commit()


def _database_url(path: Path) -> str:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise PermissionError("database URL file must not be accessible by group or others")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("database URL file is empty")
    return value


def connect_from_file(path: Path) -> Any:
    import psycopg2

    return psycopg2.connect(_database_url(path), connect_timeout=15)


def apply_registry_schema(connection: Any) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute(registry_schema_sql())
    finally:
        cursor.close()
    connection.commit()


def database_counts(connection: Any) -> dict[str, int]:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
              COUNT(*) AS total,
              COUNT(*) FILTER (WHERE owner_id = 'phonicsmaker') AS phonicsmaker,
              COUNT(*) FILTER (WHERE manifest->>'source' = 'current_catalog') AS current_catalog,
              COUNT(*) FILTER (WHERE status = 'live') AS live,
              COUNT(*) FILTER (WHERE chargeable) AS chargeable
            FROM tools
            """
        )
        total, phonicsmaker, current, live, chargeable = cursor.fetchone()
    finally:
        cursor.close()
    return {
        "total": int(total),
        "phonicsmaker": int(phonicsmaker),
        "current_catalog": int(current),
        "live": int(live),
        "chargeable": int(chargeable),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-file", type=Path, help="mode-600 file containing the Neon URL")
    parser.add_argument("--apply-schema", action="store_true", help="apply only the additive tools schema block")
    parser.add_argument("--dry-run", action="store_true", help="validate and report without a database write")
    args = parser.parse_args()
    rows = load_registry_rows()
    if args.dry_run:
        print(json.dumps({"valid": True, "rows": len(rows), "phonicsmaker": 96, "current_catalog": 24}))
        return 0
    if not args.database_url_file:
        parser.error("--database-url-file is required unless --dry-run is used")
    connection = connect_from_file(args.database_url_file)
    try:
        if args.apply_schema:
            apply_registry_schema(connection)
        upsert_tools(connection, rows)
        print(json.dumps(database_counts(connection), sort_keys=True))
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
