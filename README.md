<p align="center">
  <a href="https://omo.space" aria-label="Visit Omo">
    <img src="./site/logo-sweet-pastel.svg" width="224" alt="Omo — a peach bean and pine wordmark">
  </a>
</p>

# Omo — the AI workflow marketplace

<p align="center"><strong>Buy the result, not another subscription.</strong></p>

<p align="center">
  <a href="https://omo.space"><img src="https://img.shields.io/badge/live-omo.space-17352c?style=flat-square" alt="Omo is live at omo.space"></a>
  <a href="https://github.com/harrythentrepreneur/Omo.Space/releases/tag/v0.1.0"><img src="https://img.shields.io/badge/release-v0.1.0-ff8f70?style=flat-square" alt="Omo.Space v0.1.0"></a>
  <a href="https://github.com/harrythentrepreneur/Omo.Space/actions/workflows/generated-workflow-contracts.yml"><img src="https://github.com/harrythentrepreneur/Omo.Space/actions/workflows/generated-workflow-contracts.yml/badge.svg?branch=main" alt="Workflow contracts"></a>
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

## How it works

```text
Browser / API client
        |
        v
Vercel storefront at omo.space
        |
        | /api/*
        v
Cloudflare Worker control plane
  - authentication and workflow ownership
  - catalog, schemas and server-owned pricing
  - idempotency, credits, settlement and refunds
        |
        +----------------------+----------------------+
        |                                             |
        v                                             v
Worker-native adapter                         Modal Proxy Auth
                                                      |
                                                      v
                                            Generated Modal runtime
                                                      |
                                                      v
                                           Reviewed model/provider
        |                                             |
        +----------------------+----------------------+
                               v
                    authoritative result in Neon/D1
                               |
                               v
                      browser polling and replay
```

The storefront is a static Vercel deployment. The Cloudflare Worker owns
authentication, billing, workflow identity and lifecycle state. Modal is an
execution plane, not the public source of truth. Neon Postgres is the preferred
durable store, with D1 support and an in-memory mode for local tests.

Creator releases follow a separate trusted path:

```text
SKILL.md submission -> queue -> review -> deterministic compile -> tests and cost
  -> Git PR and CI -> exact-revision finalizer -> provider canaries -> promoted -> deployed
```

Every release generation is bound to an immutable target commit, source hash,
release head and merge commits, artifact hash and runtime. Provider effects are
recorded as canonical receipts before later promotion gates run.

## v0.1.0 release status

The first stable release was promoted from exact commit
[`15ac8fe`](https://github.com/harrythentrepreneur/Omo.Space/commit/15ac8fe27c3e81f95939e5acd80bdc0cbbf97fd7).
The production canary completed through the public Worker-to-Modal path,
returned the expected structured output, replayed idempotently and finished
with authoritative `completed`, `promoted` and `deployed` lifecycle evidence.

- [Read the full v0.1.0 release notes](https://github.com/harrythentrepreneur/Omo.Space/releases/tag/v0.1.0)
- [Read the complete changelog](./CHANGELOG.md)

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

Workflow readiness remains profile-specific. The marketplace release control
plane and canonical public canary are production-verified; each individual
workflow still carries its own capability, provider, artifact and pricing
evidence.

## Tech stack

- **Vercel** — static storefront, canonical routes and preview deployments.
- **Cloudflare Workers** — API routing, authentication, credits, workflow dispatch, and
  webhooks.
- **Clerk** — authentication and signed sessions.
- **Neon Postgres** — accounts, immutable credit ledger, runs, and purchases.
- **Modal** — scale-to-zero hosted workflow execution.
- **Stripe** — server-priced checkout and replay-safe top-up webhooks when live
  provider credentials are configured.

## Repository map

```text
.
├── site/                 # Static Omo storefront and schema-driven run UI
│   └── deploy/          # Cloudflare Worker, ledger schema, and API tests
├── containers/          # Generated and reviewed hosted workflow bundles
├── tools/host-skill/    # SKILL.md compile, test, price, and register pipeline
├── packages/skill-to-modal/ # Deterministic compiler and reviewed profiles
├── research/             # Runbooks, product research, and decision records
└── CHANGELOG.md          # Full project history through stable releases
```

## Tests

All suites run locally without production keys or paid provider calls.

| Suite | Coverage | Command |
| --- | ---: | --- |
| Balance and API keys | 22 checks | `node site/deploy/test-balance.mjs` |
| Worker router and ledger | 245 checks | `node site/deploy/test-router.mjs` |
| Cost model | 11 checks | `node site/deploy/test-cost.mjs` |
| Worker response parsing | 17 checks | `node site/deploy/test-workers.mjs` |
| Compiler, hosting and render pipeline | 383 checks at v0.1.0 | `python3 -m pytest -q -p no:cacheprovider packages/skill-to-modal/tests tools/host-skill/tests tools/render/tests` |
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

## Releases and changelog

- [Latest release: Omo.Space v0.1.0](https://github.com/harrythentrepreneur/Omo.Space/releases/tag/v0.1.0)
- [Project changelog](./CHANGELOG.md)
- [All releases](https://github.com/harrythentrepreneur/Omo.Space/releases)

## Contributing

Issues and pull requests are welcome. Start with an issue, assign an owner,
include tests with workflow changes, and merge only after review and green
checks. See [CONTRIBUTING.md](./CONTRIBUTING.md) for the short version.

## License

Omo is available under the [MIT License](./LICENSE).
