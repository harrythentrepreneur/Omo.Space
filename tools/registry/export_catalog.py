#!/usr/bin/env python3
"""Export the browser-safe marketplace projection from Neon's tools registry."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

try:
    from .import_tools import ROOT, connect_from_file
except ImportError:  # Direct script execution.
    from import_tools import ROOT, connect_from_file


DEFAULT_OUTPUT = ROOT / "site" / "ig-registry.js"
TIER_LABELS = {
    1: "Tier 1 · Shared runtime",
    2: "Tier 2 · Pure LLM",
    3: "Tier 3 · Download",
    4: "Tier 4 · External adapter",
}
STATUS_LABELS = {
    "live": "Live",
    "review": "Coming soon — in review",
    "draft": "Coming soon — draft",
    "disabled": "Unavailable",
}


def fetch_rows(connection: Any) -> list[dict]:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT slug, tier, name, description, maker, category, price_cents,
                   status, chargeable, active, version, catalog_json
            FROM tools
            ORDER BY CASE WHEN manifest->>'source' = 'phonicsmaker_inventory' THEN 0 ELSE 1 END,
                     name, slug
            """
        )
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        cursor.close()


def public_rows(database_rows: Iterable[dict]) -> list[dict]:
    result: list[dict] = []
    for row in database_rows:
        status = str(row["status"])
        chargeable = bool(row["chargeable"]) and status == "live"
        catalog = row.get("catalog_json") or {}
        if isinstance(catalog, str):
            catalog = json.loads(catalog)
        result.append(
            {
                "slug": row["slug"],
                "title": row["name"],
                "description": row["description"],
                "maker": row["maker"],
                "category": row["category"],
                "tier": int(row["tier"]),
                "tierLabel": TIER_LABELS[int(row["tier"])],
                "status": status,
                "statusLabel": STATUS_LABELS[status],
                "chargeable": chargeable,
                "active": bool(row["active"]),
                "priceCents": int(row["price_cents"]) if chargeable else None,
                "priceLabel": f"${int(row['price_cents']) / 100:.2f} per run" if chargeable else None,
                "version": int(row["version"]),
                "source": catalog.get("source", "registry"),
            }
        )
    return result


def render_catalog_js(database_rows: Iterable[dict]) -> str:
    tools = public_rows(database_rows)
    canonical = json.dumps(tools, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    revision = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    meta = {
        "schemaVersion": "omo.public-registry/v1",
        "revision": f"sha256:{revision}",
        "count": len(tools),
        "phonicsmakerCount": sum(row["source"] == "phonicsmaker" for row in tools),
        "liveCount": sum(row["status"] == "live" for row in tools),
    }
    meta_json = json.dumps(meta, ensure_ascii=False, indent=2).replace("</", "<\\/")
    tools_json = json.dumps(tools, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return (
        "// GENERATED from Neon tools registry. Do not hand-edit.\n"
        f"// Registry revision: {meta['revision']}\n"
        f"window.OMO_REGISTRY_META = {meta_json};\n"
        f"window.OMO_REGISTRY_TOOLS = {tools_json};\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="fail if the committed export differs")
    args = parser.parse_args()
    connection = connect_from_file(args.database_url_file)
    try:
        rendered = render_catalog_js(fetch_rows(connection))
    finally:
        connection.close()
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"stale registry export: {args.output}")
        print(f"registry export is current: {args.output} ({rendered.count(chr(10))} lines)")
        return 0
    args.output.write_text(rendered, encoding="utf-8")
    print(f"exported registry catalog to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
