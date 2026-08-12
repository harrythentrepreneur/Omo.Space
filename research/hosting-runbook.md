# Omo SKILL.md hosting runbook

**Status:** production process, 2026-08-12. The reference proof is
`facebook-ads-copywriter`: its bundle, catalog profile, schema-driven form, and
hosted Worker route were produced by this process; its Modal endpoint completed
a real provider-backed run. The changed Cloudflare Worker is tested and
deploy-ready but still needs an existing Cloudflare OAuth session or
`CLOUDFLARE_API_TOKEN` before the production marketplace can use that route.

## What “the gig” is

`tools/host-skill/host.py` is the single entry point for every future hosted
deployment:

1. Parse a SKILL.md as untrusted Markdown; never execute it.
2. Infer its reviewed profile by the frontmatter `name`.
3. Deterministically generate schemas, prompt assets, `modal_app.py`, fixtures,
   contract tests, manifests, capability analysis, and pricing evidence.
4. Run the pipeline tests and the generated container contract tests offline.
5. Recalculate pricing from `site/deploy/cost-model.mjs` and reject drift.
6. With `--register`, generate the hosted profile, browser run manifest,
   catalog entry, and server-owned Modal routing registry.
7. Deploy the same generated container to Modal, canary it, then deploy the
   Worker registry and canary Omo billing.

“Any SKILL.md” means every skill can enter this analysis and review process. It
does not mean arbitrary Markdown is executed. The automatic ready path is a
bounded, schema-validated `single_llm` call. Media, browser, private-data,
native-code, or multi-provider skills must declare blockers and return
`503 WORKFLOW_NOT_READY` before spawn or spend until their assets are reviewed.

## New skill in under 15 minutes of agent time

Prerequisites: Python 3.12 with `pytest`, `modal`, `fastapi`, and `jsonschema`;
Node.js; an authenticated Modal CLI; the named Modal secret
`omo-skill-providers`; and a Modal Proxy Token already stored as Worker secrets.
Never put credential values in a profile, command transcript, or Git.

1. Add `packages/<slug>/SKILL.md` with one-line YAML `name` and `description`, a
   numbered `## Workflow`, an output contract, and hard rules.
2. Copy the closest reviewed JSON profile in
   `packages/skill-to-modal/profiles/`. Set exact schemas, fixtures, negative
   cases, prompt, resources, required environment-variable **names**, pricing
   estimate, readiness, and the `marketplace` block. Do not guess capabilities.
3. Compile, test, price, and register with one command:

```bash
python3 tools/host-skill/host.py packages/<slug>/SKILL.md --register
```

Successful output ends with JSON containing `status: ready_for_catalog`, the
source SHA-256, price, container manifest, and run manifest. Generated files
appear in:

```text
containers/<slug>/
site/run-manifests/<marketplace-slug>.json
site/deploy/hosted-skills.generated.mjs
site/ig-more.js  (only the marked generated block)
```

4. Prove there is no drift:

```bash
python3 tools/host-skill/host.py packages/<slug>/SKILL.md --register --check
git diff --check
```

5. Deploy the generated app:

```bash
python3 -m modal deploy containers/<slug>/modal_app.py
```

The reviewed `marketplace.deployment.default_endpoint` must match the URL Modal
prints. Update the profile and rerun `--register` if it does not.

6. Submit one safe fixture with the existing Proxy Token, then poll the returned
`result_url`. Keep values out of shell history; these are names only:

```bash
curl -X POST "$MODAL_ENDPOINT/v1/runs" \
  -H "Modal-Key: $MODAL_PROXY_TOKEN_ID" \
  -H "Modal-Secret: $MODAL_PROXY_TOKEN_SECRET" \
  -H 'Content-Type: application/json' \
  --data @safe-fixture.json
curl "$MODAL_ENDPOINT$RESULT_URL" \
  -H "Modal-Key: $MODAL_PROXY_TOKEN_ID" \
  -H "Modal-Secret: $MODAL_PROXY_TOKEN_SECRET"
```

Required evidence: `202 accepted`, then `200`; output passes the generated
schema; provider/model and token usage are present; no secret or provider error
body is logged.

7. Deploy the generic routing registry:

```bash
cd site/deploy
npx wrangler deploy
```

Wrangler must reuse an existing Cloudflare login or receive
`CLOUDFLARE_API_TOKEN` through the environment. Do not use `--temporary`, create
an account, or paste a token into a command.

8. Run a production billing canary with an existing signed-in account or its
existing `omo_` API key. Record only: balance before, HTTP states, Omo run ID,
output summary, billed amount, and balance after. Reuse one idempotency key only
for the identical request. Expected invariant for a $0.10 run:

```text
balance_after = balance_before - 0.10
```

Failures after reservation must settle once as `refunded`; schema-invalid input
must fail before debit or Modal dispatch. Never create an account for a canary.

## Review decisions and gates

- **Identity:** profile `name` and `slug` must match SKILL.md frontmatter.
- **Schemas:** Draft 2020-12, bounded strings/arrays, `additionalProperties:
  false`, a valid happy fixture, and negative fixtures.
- **Provider:** HTTPS OpenAI-compatible adapter, explicit model, prompt, token
  ceiling, timeout, rates, and named Modal secret.
- **Output:** provider JSON is extracted, validated against a restricted model
  schema, wrapped with run/usage metadata, then validated again.
- **Ingress:** Modal Proxy Token auth is mandatory; CLI deployment tokens are
  not ingress credentials.
- **Worker:** server-owned price, endpoint, schemas, and secret names come from
  `hosted-skills.generated.mjs`; client overrides are ignored.
- **Billing:** authenticate → validate → claim idempotency → reserve → dispatch →
  validate output → settle once. Terminal failure refunds once.
- **Pricing:** generated from the repository cost model, 5x launch markup, with
  the current $0.10 floor. Unpriced costs make the profile non-chargeable.
- **Promotion:** local tests, direct Modal canary, Worker deploy, and production
  ledger canary are four separate gates. Never report a later gate as complete
  because an earlier one passed.

## Full verification

Run contract files in separate pytest processes because all three are named
`test_contract.py`:

```bash
python3 -m pytest -q -p no:cacheprovider packages/skill-to-modal/tests tools/host-skill/tests
python3 -m pytest -q -p no:cacheprovider containers/audio-symbolic-animation/tests/test_contract.py
python3 -m pytest -q -p no:cacheprovider containers/woven-storybook-pipeline/tests/test_contract.py
python3 -m pytest -q -p no:cacheprovider containers/<slug>/tests/test_contract.py
node packages/skill-to-modal/verify-pricing.mjs audio-symbolic-animation woven-storybook-pipeline <slug>
cd site/deploy
node test-workers.mjs
node test-router.mjs
node test-balance.mjs
node test-cost.mjs
```

Also run `node --check` on the catalog, Worker, generated registry, and changed
test scripts, followed by `git diff --check` and `--register --check`.

## Current proof and remaining gate

Facebook Ads Copywriter deployed at
`https://harrythentrepreneur--cognition-facebook-ads-copywriter-api.modal.run`.
Authenticated direct evidence: submit `202`, poll `200`, three ads, one LLM
call, 349 prompt tokens, 780 completion tokens, estimated provider cost
`$0.00037646`; catalog price `$0.10`.

The production Worker deploy is currently blocked only by missing Cloudflare
authorization in this non-interactive environment. Wrangler reported that
`CLOUDFLARE_API_TOKEN` was absent; an OAuth attempt reached the existing-account
login page and was stopped. Consequently, the production Omo ledger canary is
not claimed. Once an existing Cloudflare session is authorized, run steps 7–8.
