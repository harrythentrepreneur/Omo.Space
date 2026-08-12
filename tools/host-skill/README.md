# host-skill

`host.py` is Omo's repeatable SKILL.md hosting command. It delegates bundle
generation to the reviewed `packages/skill-to-modal/compiler.py`, runs the
compiler and container test suites, verifies pricing against
`site/deploy/cost-model.mjs`, and optionally registers the result in the
storefront and generated Worker registry.

```bash
python3 tools/host-skill/host.py packages/facebook-ads-copywriter/SKILL.md --register
python3 tools/host-skill/host.py packages/facebook-ads-copywriter/SKILL.md --register --check
```

The SKILL.md is parsed as untrusted text and is never executed. A reviewed
profile at `packages/skill-to-modal/profiles/<slug>.json` is mandatory. Only
reviewed `single_llm` profiles can become runnable automatically; every other
execution kind stays fail-closed until its artifacts and capabilities are
materialized and reviewed.

See `research/hosting-runbook.md` for the complete deploy and canary procedure.
