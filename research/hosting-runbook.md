# Omo SKILL.md hosting runbook

**Status:** agent-assisted production process, 2026-08-13. The reference proof
is `facebook-ads-copywriter`: its bundle, catalog profile, schema-driven form,
hosted Worker route, live marketplace listing, and real provider-backed Modal
run were produced by this process. Creator upload intake now has a real queue;
review, deploy credentials, canaries, and publication are intentionally still
agent gates rather than an unattended CI job. **Production schema gate:** live
logs prove `purchases` is absent, and the other additive tables are not proven
present. On 2026-08-13, Wrangler confirmed the `NEON_DATABASE_URL` secret name,
but the URL was not injected locally; managed credential policy prohibited
reading shell history or secret-bearing files, local `psql` was unavailable,
and the Worker had no protected migration route. The founder must securely
inject the URL for the command below or run it personally, then verify all 12
public table names.

## Site upload → queued → live (V1)

Before this version, `sell.html` and `creators.html` offered only signup and
waitlist flows. The otherwise-unlinked `host.html` looked like an uploader, but
`upload.js` stored only a filename/status in `localStorage` and animated a fake
“live” sequence. There was no `/api/submit`, submissions table, GitHub issue
handoff, or queue processor.

The real V1 is deliberately honest: **upload → queued → agent-assisted review
and deployment → live**. Uploaded Markdown is never executed. A file does not
become runnable until a trusted profile defines schemas, fixtures, provider and
secret names, bounded resources, pricing, marketplace copy, and the expected
Modal endpoint.

### One-time production setup

Apply the full additive schema before enabling checkout, top-up, or upload:

```bash
psql "$NEON_DATABASE_URL" -f site/deploy/schema.sql
cd site/deploy
npx wrangler deploy
```

The exact remaining schema step is:

```bash
cd /Users/yifan/marketplace
psql "$NEON_DATABASE_URL" -f site/deploy/schema.sql
psql "$NEON_DATABASE_URL" -c "SELECT to_regclass('public.purchases'), to_regclass('public.topup_sessions'), to_regclass('public.stripe_events'), to_regclass('public.stripe_topups'), to_regclass('public.submissions');"
```

The second command must return all five `public.*` table names. Do not paste the
connection string into chat, a command line, or the repository.

The production Worker needs its existing Clerk, Neon, provider, and Modal Proxy
Token secrets. Do not deploy `/api/submit` against Neon before the `submissions`
table exists.

### Every creator submission

1. A signed-in creator opens `host.html`, selects a public `.md` file of at
   most 200 KiB, and supplies a workflow name. `upload.js` reads the actual
   content and sends a Clerk bearer token to `POST /api/submit`. `file://`
   remains an explicit demo. During rollout only, HTTP 404/405/501 from an
   undeployed queue creates a clearly labelled local retry receipt containing
   metadata only; it never stores the Markdown or claims the item was queued.
2. The Worker requires scalar frontmatter `name` and `description`, derives the
   slug server-side, rejects mismatched names and private hosting, stores the
   content as untrusted data, and returns HTTP `202` with `{id, status:
   "queued"}`. Replaying identical content for the same creator returns the
   same queue record and never duplicates work.
3. An agent claims the oldest queued item:

```bash
python3 tools/host-skill/process-submissions.py
```

   Invalid content becomes `failed`; an existing package/container slug becomes
   `needs_review` with `slug_collision`; and a new slug without a reviewed
   profile becomes `needs_review` with `reviewed_profile_required`. No compile,
   command, provider call, registration, or spend occurs in those states.
4. For review, export only the selected record to a private local file. The
   command prints metadata and a SHA-256, never the Markdown itself:

```bash
python3 tools/host-skill/process-submissions.py \
  --export-review sub_… --review-dir /private/tmp/omo-review
```

   Review the Markdown as hostile input. Create
   `packages/skill-to-modal/profiles/<slug>.json` only after resolving exact
   input/output schemas, positive and negative fixtures, prompt, provider,
   secret names, runtime bounds, readiness, costs, UI, and deployment endpoint.
   A copied “nearest” profile is not approval.
5. Requeue/process the reviewed item without external deployment first:

```bash
python3 tools/host-skill/process-submissions.py --id sub_…
```

   This runs `host.py` without `--register`, which compiles the container, runs
   compiler/host and generated contract tests, and verifies pricing. Any failure
   stops before Modal and sets a bounded failure code. Success becomes
   `ready_for_deploy`.
6. The agent starts the external promotion gates:

```bash
python3 tools/host-skill/process-submissions.py --id sub_… --deploy
```

   In order, the script reruns the local gate, deploys the generated Modal app,
   submits and polls the reviewed happy fixture with the existing Proxy Token,
   validates the result schema, runs `host.py --register` and
   `--register --check`, runs all four Worker suites, then deploys the Worker.
   Registration writes the hosted profile, run manifest, generated Worker
   registry, and marked catalog entry only after the direct Modal canary passes.
   Success is `ready_for_publish`, not yet `deployed`.
7. Review the diff; run the full verification below; commit and push to `main`.
   Confirm the Vercel production listing/run manifest, then perform one signed-in
   Omo billing canary (balance before, run, terminal valid output, exact debit,
   balance after). Only then record the live state:

```bash
python3 tools/host-skill/process-submissions.py --mark-deployed sub_…
```

The queue consumer is not a daemon and cannot invent a reviewed profile. An Omo
agent runs it and owns the review/canary/publish decisions. Fully automatic CI
may later claim approved profiles, but must preserve the same gates and may not
turn arbitrary uploaded Markdown into executable code.

## What “the gig” is

`tools/host-skill/host.py` is the single entry point for every future hosted
deployment:

1. Parse a SKILL.md as untrusted Markdown; never execute it.
2. For a new supported upload, validate a small workflow-specific IR and
   deterministically materialize the trusted profile. Existing reviewed profiles
   remain valid inputs.
3. Deterministically generate schemas, prompt assets, `modal_app.py`, fixtures,
   contract tests, manifests, capability analysis, and pricing evidence.
4. Run the pipeline tests and the generated container contract tests offline.
5. Recalculate pricing from `site/deploy/cost-model.mjs` and reject drift.
6. With `--register`, generate the hosted profile, browser run manifest,
   catalog entry, and server-owned Modal routing registry.
7. Deploy the same generated container to Modal, canary it, then deploy the
   Worker registry and canary Omo billing.

“Any SKILL.md” means every skill can enter this analysis and review process. It
does not mean arbitrary Markdown is executed. New automatic authoring is limited
to machine-validated `pure_data` and `single_llm` IRs. The compiler, not the
model, owns identity, source binding, runtime/provider/resources, readiness,
pricing and release policy. Media, browser, private-data, native-code or other
unsupported capabilities produce exact typed blockers before spawn or spend.

## New reviewed skill in under 15 minutes of agent time

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
site/catalog.js  (only the marked generated block)
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

## Current proof and remaining gates

Facebook Ads Copywriter deployed at
`https://harrythentrepreneur--cognition-facebook-ads-copywriter-api.modal.run`.
Authenticated direct evidence: submit `202`, poll `200`, three ads, one LLM
call, 349 prompt tokens, 780 completion tokens, estimated provider cost
`$0.00037646`; catalog price `$0.10`.

The upload queue code is locally testable without credentials. A production
upload is not available until the founder securely supplies the Neon connection
string to this environment or runs the exact migration above; the secret stored
in Wrangler cannot be read back and local `psql` is unavailable. Live checkout
currently fails closed with HTTP 503 and expires the unpaid Stripe Session when
`purchases` cannot be recorded; top-up has the same fail-safe. Every new
workflow still requires its own reviewed profile,
provider/Modal credentials, direct canary, Worker deploy, Vercel publication,
and Omo billing canary. Audio symbolic animation remains fail-closed on its
documented Whisper/media/artifact/cost blockers.
