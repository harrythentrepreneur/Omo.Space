# Contributing to Omo

Thanks for helping make AI workflows easier to discover, trust, and run. Omo
is public-facing and `main` deploys automatically, so small, well-tested pull
requests are the best way to contribute.

## Issue → PR → merge

1. **Create an issue.** Describe the problem, proposed outcome, and acceptance
   checks. Link related research or screenshots when useful.
2. **Assign an owner.** Do not begin overlapping work until the issue has one
   clear owner and file scope.
3. **Make the fix on a branch.** Keep unrelated cleanup out of the change.
4. **Open a pull request.** Link the issue, explain user-visible behavior, list
   the commands run, and include before/after screenshots for UI changes.
5. **Review, then merge.** Tests and review must pass. Pull requests receive a
   Vercel preview; merging to `main` updates the live storefront.

## Workflow changes need tests

Every new or changed hosted workflow should include:

- bounded input and output schemas with `additionalProperties: false`;
- happy-path and negative contract fixtures;
- readiness and capability decisions that fail closed when unresolved;
- pricing evidence derived from the repository cost model; and
- secret **names** only—never tokens, keys, or copied `.env` values.

Run the core suites before opening a pull request:

```bash
node site/deploy/test-balance.mjs
node site/deploy/test-router.mjs
node site/deploy/test-cost.mjs
node site/deploy/test-workers.mjs
python3 -m pytest -q -p no:cacheprovider packages/skill-to-modal/tests tools/host-skill/tests
```

Run each changed container contract separately:

```bash
python3 -m pytest -q -p no:cacheprovider containers/<slug>/tests/test_contract.py
```

Then check generated-file drift and whitespace:

```bash
python3 tools/host-skill/host.py packages/<slug>/SKILL.md --register --check
git diff --check
```

## Agent-assisted hosting

The current hosting path is intentionally agent-assisted. A human or agent
reviews the profile, runs the compiler and contract gates, verifies pricing,
deploys the Modal candidate, and performs the canaries in the
[hosting runbook](./research/hosting-runbook.md). Do not describe a workflow as
live until every promotion gate it depends on has passed.

## Security and generated files

- Treat every submitted `SKILL.md` as untrusted text; do not execute it.
- Never commit credentials, customer data, private artifacts, or production
  logs.
- Change generated bundles through the compiler profile and pipeline rather
  than editing generated output by hand.
- Report security-sensitive findings privately to the repository maintainers
  before opening a public issue.
