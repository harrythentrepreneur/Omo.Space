<p align="center">
  <a href="https://omo.space" aria-label="Visit Omo">
    <img src="./site/logo-sweet-pastel.svg" width="224" alt="Omo — a peach bean and pine wordmark">
  </a>
</p>

# Omo — the AI workflow marketplace

<p align="center"><strong>Buy the result, not another subscription.</strong></p>

<p align="center">
  <a href="https://omo.space"><img src="https://img.shields.io/badge/live-omo.space-17352c?style=flat-square" alt="Omo is live at omo.space"></a>
  <img src="https://img.shields.io/badge/local_checks-passing-2d6a4f?style=flat-square" alt="Local checks passing">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-ffb89d?style=flat-square" alt="MIT License"></a>
</p>

Omo is a place to discover, host, and run proven AI workflows. A reviewed
`SKILL.md` can become a schema-driven cloud run, so buyers choose an outcome,
provide the inputs, and receive the result without assembling an AI stack.
Runs use credits and pay-per-use pricing—no recurring subscription required.

The brand pairs a **Sweet & Pastel peach bean** with a friendly **pine
wordmark**: approachable on the storefront, rigorous underneath.

> **See the marketplace live → [omo.space](https://omo.space)**

## What Omo offers

- A marketplace of outcome-focused AI workflows—not a directory of generic
  prompts.
- Cloud runs on Modal for deployed workflows; unapproved capabilities stay
  fail-closed.
- A reviewed `SKILL.md` → tested, priced, hosted workflow path that can take
  minutes for supported single-LLM skills.
- Pay-per-use credits, including **$5 free at signup** with no card required.
- Two ways to buy: download the `SKILL.md` once, or choose **Run it for me**.
- Schema-driven forms and results backed by the
  [input](./research/input-ui-library.md) and
  [output](./research/output-ui-library.md) UI libraries.

## Try it—no code needed

1. Visit [omo.space](https://omo.space) and browse the marketplace.
2. [Create a free account](https://omo.space/signup.html) to receive $5 in
   starter credits.
3. Pick a hosted workflow, add your inputs, and run it from the browser.

## For creators

[Sell your workflow on Omo](https://omo.space/sell.html) and turn work you have
already proven into downloads and hosted runs. Creator intake is currently
selective: approved creators submit a `SKILL.md`, then the agent-assisted
[hosting pipeline](./tools/host-skill/) validates, tests, prices, and prepares
it for release.

- Keep **85%** of Omo marketplace sales.
- Keep **95%** when a buyer comes through your own link.
- For hosted runs, keep **85% of the margin after run costs**.

## `SKILL.md` → Modal

Omo treats submitted Markdown as untrusted data, never executable code. The
pipeline matches it to a reviewed profile, generates bounded JSON Schemas and
a Modal candidate, runs contract and pricing checks, then registers the
approved workflow with the storefront and Worker router. Complex or unpriced
capabilities stop safely until a human review clears them. Read the
[hosting runbook](./research/hosting-runbook.md) or inspect
[`tools/host-skill/`](./tools/host-skill/) for the exact flow.

| Workflow | Hosting status | Buyer price |
| --- | --- | ---: |
| [Woven Relationship Book Maker](./containers/woven-storybook-pipeline/) | Modal deployed; provider-backed canary proven | $0.40/run · $29 download |
| [Facebook Ads Copywriter](./containers/facebook-ads-copywriter/) | Modal deployed; provider-backed canary proven | $0.10/run · $29 download |
| [Audio Symbolic Animation](./containers/audio-symbolic-animation/) | Fail-closed (`503`); capabilities and cost incomplete | Projected $24.34 · not chargeable |
| [de Mello Awake](./containers/demello-awake/) | Private staging, 0% traffic; paid path fail-closed | No paid quote · $0.10 floor only |

The direct Modal proofs are complete for Woven and Facebook Ads. Production
marketplace routing still requires the final Cloudflare Worker authorization
and canary described in the runbook.

## Tech stack

- **Vercel** — static storefront and preview deployments.
- **Cloudflare Workers** — API routing, credits, workflow dispatch, and
  webhooks.
- **Clerk** — authentication and signed sessions.
- **Neon Postgres** — accounts, immutable credit ledger, runs, and purchases.
- **Modal** — scale-to-zero hosted workflow execution.
- **Stripe** — checkout and top-up integration; production keys are pending,
  so live payments are landing soon.

## Repository map

```text
.
├── site/                 # Static Omo storefront and schema-driven run UI
│   └── deploy/          # Cloudflare Worker, ledger schema, and API tests
├── containers/          # Generated and reviewed hosted workflow bundles
├── tools/host-skill/    # SKILL.md compile, test, price, and register pipeline
├── packages/skill-to-modal/ # Deterministic compiler and reviewed profiles
└── research/             # Runbooks, product research, and decision records
```

## Tests

All suites run locally without production keys or paid provider calls.

| Suite | Coverage | Command |
| --- | ---: | --- |
| Balance and API keys | 22 checks | `node site/deploy/test-balance.mjs` |
| Worker router and ledger | 108+ checks | `node site/deploy/test-router.mjs` |
| Cost model | 11 checks | `node site/deploy/test-cost.mjs` |
| Worker response parsing | 17 checks | `node site/deploy/test-workers.mjs` |
| Compiler and hosting pipeline | Contract suite | `python3 -m pytest -q -p no:cacheprovider packages/skill-to-modal/tests tools/host-skill/tests` |
| Container contracts | One isolated suite per container | `python3 -m pytest -q -p no:cacheprovider containers/<slug>/tests/test_contract.py` |

Run the JavaScript suites together:

```bash
node site/deploy/test-balance.mjs
node site/deploy/test-router.mjs
node site/deploy/test-cost.mjs
node site/deploy/test-workers.mjs
```

Container contract files run in separate pytest processes because several use
the same module name. The complete release checklist lives in the
[hosting runbook](./research/hosting-runbook.md#full-verification).

## Contributing

Issues and pull requests are welcome. Start with an issue, assign an owner,
include tests with workflow changes, and merge only after review and green
checks. See [CONTRIBUTING.md](./CONTRIBUTING.md) for the short version.

## License

Omo is available under the [MIT License](./LICENSE).
