# Omo registry import

This directory owns the additive Phase 0 registry seed and the deterministic
browser-safe export. Neon is authoritative; `site/ig-registry.js` is generated
and contains no prompts, endpoints, provider configuration, or prices for
non-chargeable tools.

The 96-tool PhonicsMaker seed is generated from
`research/phonicsmaker-100-tools-plan.md`. The 24-row live parity snapshot is
projected from `site/ig-workflows.js` and `site/ig-more.js`. Rebuild and check:

```bash
python3 tools/registry/build_seed_data.py
python3 tools/registry/build_seed_data.py --check
python3 tools/registry/import_tools.py --dry-run
```

Apply only the marked additive registry DDL, then idempotently upsert all 120
rows without exposing the connection string:

```bash
python3 tools/registry/import_tools.py \
  --database-url-file /tmp/omo-neon-url.txt --apply-schema
python3 tools/registry/export_catalog.py \
  --database-url-file /tmp/omo-neon-url.txt --output site/ig-registry.js
```

The 93 Tier-2 manifests are data for the future shared `omo-llm-runner`; their
prompt is an explicit non-executable review placeholder. The three current
artifact-heavy story tools are Tier 1 and remain blocked on shared runtime,
private artifact, QA, and measured-pricing gates. The 24 live listings remain
on their existing dispatch path during this shadow migration.
