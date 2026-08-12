# Omo at 100,000 tools: registry-first, Modal-offloaded architecture

**Status:** architecture and migration specification, 2026-08-13

**Scope:** research only. No site, Worker, container, database, or production changes.

**Baseline:** preserve the current marketplace and hosted-tool path while replacing per-slug code and catalog growth with generic contracts.

## Executive decision

At 100,000 listings, a tool is primarily a **versioned registry record**, not a deployment. Neon is the source of truth for identity, tier, active version, server-only execution manifest, publication state, and the one current `price_cents`. Private R2 objects hold immutable tool bundles and downloadable files. Cloudflare serves a derived, paginated catalog and may cache public projections. Modal supplies a handful of shared runners that scale by runtime family, plus isolated single-use execution for code that cannot safely run inside a shared process.

Do **not** create 100,000 Modal Apps. Modal's public documentation explains that Apps group Functions for atomic deployment and that each Function scales independently, including to zero; it does not promise that a workspace can or should operate 100,000 deployed Apps. Omo should have one logical `omo-runner` service, one `omo-llm-runner`, and a small allowlist of versioned runtime families. Existing per-tool Apps remain compatible during migration, and a per-tool App remains an exception for privileged or unusually isolated workloads—not the catalog unit.

The core split is:

| Tier | What the listing is | Execution and cost shape |
| --- | --- | --- |
| **1 — Modal runtime** | PDF, image, video, browser/native processing, multi-step work, or reviewed custom code | `omo-runner` selects a pinned runtime family and immutable bundle; declarative jobs use shared Functions, custom/untrusted code uses a single-use isolated Function or Sandbox. Modal compute and provider calls accrue only while work runs, except any deliberately warm pool. |
| **2 — pure LLM** | A strict schema, reviewed prompt, model policy, examples, and price; no custom code or binary rendering | One `omo-llm-runner` Function executes every tool from a signed manifest. Adding a tool is one registry version, zero Modal deployments. Cost is predominantly provider tokens. |
| **3 — content/download** | A catalog record plus immutable, versioned file metadata | No run and no Modal cold start. Checkout creates ownership; authenticated delivery resolves an opaque `file_id` to a private object and short-lived response. Cost is storage, egress, and payment operations. |
| **4 — external/hybrid** | A strict tool manifest referring to a reviewed provider operation such as Runware or HeyGen | A shared adapter registry owns credentials, hosts, retries, webhooks, idempotency, metering, and output normalization. The listing remains `chargeable:false` until its adapter operation and measured price pass gates. |

## 1. What the repository and Modal actually do today

The generated house container is real and worth preserving as a contract. For example, `containers/facebook-ads-copywriter/modal_app.py` declares one `modal.App`, a worker Function with `min_containers=0`, `max_containers=4`, and `scaledown_window=5`, plus a separate concurrent ASGI Function protected by `requires_proxy_auth=True`. `POST /v1/runs` validates before `run_workflow.spawn(...)`; polling resolves the `FunctionCall`; provider output and the final envelope are schema-validated. Other generated Phonics containers repeat the same shape. This proves the contract, not that the deployment must remain per slug.

The current generic Worker already builds a `Map` from `HOSTED_MODAL_SKILL_ROWS`, uses server-owned prices/endpoints/schemas, claims idempotency before dispatch, reserves credits, validates the terminal output, and settles or refunds. The scale problem is that the map is compiled into a JS module and every runnable tool has an endpoint; the billing state machine itself is the right foundation.

Repository scan note: at the time of this concurrent-worktree audit, `site/ig-workflows.js` plus `site/ig-more.js` contained 23 literal `slug:` rows while `research/skill-to-modal-pipeline.md` describes Facebook Ads Copywriter as the 24th listing. The migration must therefore use a slug/checksum parity gate rather than assuming a count.

Relevant Modal semantics, verified against current official documentation:

- An App groups Functions for atomic deployment; Functions in it scale independently. With no live inputs, Functions normally have no running containers and no compute charge. [Modal Apps](https://modal.com/docs/guide/apps)
- A cold start is the wait for a new Function container plus its initialization. `scaledown_window`, `min_containers`, and `buffer_containers` trade cost for latency. `min_containers=0` permits scale-to-zero; a deployed App is not itself an always-running server. [Cold starts](https://modal.com/docs/guide/cold-start)
- `@modal.concurrent(max_inputs=..., target_inputs=...)` sets per-container input concurrency; excess demand causes more containers to start, subject to Function/container limits. CPU-heavy renderers should use low concurrency, while I/O-bound provider calls can use higher concurrency. [Input concurrency](https://modal.com/docs/guide/concurrent-inputs)
- Proxy Tokens protect ASGI/FastAPI/Web endpoints through `Modal-Key` and `Modal-Secret`. They are distinct from deployment/API tokens, matching the repository's current ingress pattern. [Proxy Tokens](https://modal.com/docs/guide/webhook-proxy-auth)
- Image operations are cached by layer. Stable OS/fonts/WeasyPrint/ffmpeg dependencies must precede changing tool material. [Modal Images](https://modal.com/docs/guide/images)
- Cloud bucket mounts support read-only Cloudflare R2/S3 mounts. Modal Volume v1 has explicit reload/commit semantics, recommends fewer than 50,000 files, and has a 500,000-inode limit; Volume v2 is more scalable but currently Beta. This makes immutable object storage, not one giant Volume, the safer registry artifact source. [Cloud bucket mounts](https://modal.com/docs/guide/cloud-bucket-mounts), [Volumes](https://modal.com/docs/guide/volumes)
- Modal Sandboxes are intended for isolated arbitrary code, can use prebuilt/named or registry images, and can block outbound network. Restricted Functions add `restrict_modal_access`, `single_use_containers`, and network controls for stateless code. [Sandboxes](https://modal.com/docs/guide/sandboxes), [Restricted Functions](https://modal.com/docs/guide/restricted-access)

The repository pins Modal `1.5.0` in generated images. Before implementation, confirm the chosen Sandbox, restricted-access, named-image, and network-policy APIs against that exact client version and the Omo Modal plan; the architecture must not depend on an undocumented App quota.

## 2. Tier 1 — one logical runner, not one App per tool

### 2.1 Decision and trade-offs

| Concern | 100,000 per-tool Apps | One universal shared interpreter | Recommended runtime-family runner |
| --- | --- | --- | --- |
| Deployment count | One deploy, endpoint, App object, and lifecycle per tool; operationally unbounded | A tool row requires no deploy | A tool row requires no deploy; only a new runtime family changes Modal code |
| Blast radius | Tool deploy is narrow | Runner defect can affect every tool | Versioned functions/releases and tool pinning bound the radius; blue/green runner releases |
| Cold starts | Warmth is fragmented across 100,000 identities | Traffic pools into one warm service | Traffic pools by runtime family; large families can have distinct warm policies |
| Image reuse | Modal can reuse identical layers, but every Function identity still starts separately | One potentially huge image | A few purpose-built images: light, PDF, media, browser/GPU as proven |
| Secrets | Easy per-App attachment, but 100,000 copies/references | Broad shared secrets are dangerous | Tool code receives no provider secret; trusted adapters bind secrets by capability family |
| Isolation | Strongest natural separation | A bad plugin can poison/reuse the process | Declarative first-party work shares Functions; custom/untrusted code is single-use and isolated |
| Debugging | Per-tool logs are easy | Logs are mixed | Every event carries `run_id`, `tool_id`, `tool_version`, `runtime`, and bundle hash |
| Rollback | Redeploy each App | Roll back the entire runner | Atomically move the tool's active-version pointer; runner releases are independently blue/green |

**Recommendation:** use one logical `omo-runner`, implemented initially as one stable ingress App with a small set of versioned runtime Functions. If deployment blast radius later warrants it, split those functions into three to six family Apps (`omo-runtime-light`, `omo-runtime-pdf`, `omo-runtime-media`, and so on). The important invariant is a finite runtime set—not one App per catalog row and not one enormous image.

Existing per-tool Apps are a supported `legacy_modal_app` execution target during migration. New per-tool Apps require an exception: a dedicated privileged secret boundary, a bespoke persistent service/model, regulatory isolation, or a workload whose dependencies cannot fit an approved runtime image. Expect tens or hundreds of exceptions, never 100,000.

### 2.2 The Tier-1 execution contract

The Worker's server-created request to the protected runner is:

```json
{
  "contract": "omo.runner-request/v1",
  "run_id": "run_...",
  "tool_id": "00000000-0000-4000-8000-000000000000",
  "tool_version": 7,
  "manifest_sha256": "<64 hex>",
  "manifest_signature": "<detached registry signature>",
  "execution_manifest": { "...": "server-only signed projection" },
  "input": { "...": "already schema-validated input" }
}
```

The client can supply only `slug`, `input`, and its idempotency key. It cannot supply a prompt, price, provider, endpoint, runtime, artifact URI, secret name, network rule, or output URL. The runner verifies the registry signature and hash, revalidates input, enforces its own resource ceilings, executes the exact pinned version, validates output, and returns `omo.result/v1`.

A Tier-1 execution manifest contains:

```text
spec_version, tool_id, slug, tool_version
execution_kind, runtime_family, runtime_version, entrypoint
bundle_uri, bundle_sha256, bundle_bytes, registry_signature
input_schema, output_schema, result_contract
resources {cpu, memory_mb, gpu?, timeout_seconds, max_output_bytes}
concurrency {per_container, per_tool, provider_budget_key}
capabilities [pdf, image, video, browser, artifact_read, artifact_write, ...]
adapters [{adapter_key, adapter_version, operation}]
network_policy {mode: blocked|adapter_only|reviewed_allowlist, hosts: []}
artifact_policy {input_roles, output_roles, max_bytes, retention_days}
observability {redaction_policy, content_logging: false}
```

Runtime names and capability/adapter keys are allowlisted by the runner. A signed manifest still cannot request an unknown image, arbitrary secret, unrestricted host, or resources beyond Omo policy.

Canonicalize manifests with a versioned JSON canonicalization rule, hash the exact bytes, and sign the hash with an offline/CI Ed25519 registry key. Runners contain only the public verification key. Transport Proxy Tokens authorize the Worker; the detached signature proves that the manifest passed registration and was not improvised at request time.

### 2.3 Artifact mechanism: immutable R2 bundles plus pinned runtime images

Use private Cloudflare R2 as the canonical tool-artifact store, addressed by content hash:

```text
tool-bundles/<tool_id>/<tool_version>/<bundle_sha256>.tar.zst
tool-files/<tool_id>/<tool_version>/<file_id>/<sha256>
run-artifacts/<user_partition>/<run_id>/<artifact_id>
```

The bundle is `omo.tool-bundle/v1`: exact schemas, prompts/templates, static assets, fixtures/provenance, and optionally a reviewed wheel or executable adapter. Neon stores the private URI, byte count, hash, and detached registry signature. The runner mounts the bucket read-only or performs a server-authenticated fetch, verifies bytes before extraction, rejects symlinks/path traversal, and caches the verified bundle on ephemeral container disk by hash. Mutable names such as `latest` are forbidden.

Do not use one Modal Volume as the source of truth for 100,000 tool directories. Its consistency and inode behavior add a mutable filesystem problem Omo does not need. A Volume may be a disposable runtime cache, never the registry or rollback authority.

Runtime images are built rarely and pinned separately from tool bundles:

| Runtime family | Stable contents | Intended jobs |
| --- | --- | --- |
| `omo-python-light@1` | Python, schema validation, artifact client, adapter RPC | bounded native transforms and orchestration |
| `omo-pdf@1` | light base + licensed fonts, WeasyPrint, Jinja2, Pillow, PDF/raster QA | PhonicsMaker worksheets, books, reports |
| `omo-media@1` | light base + ffmpeg and reviewed media libraries | audio/video transforms |
| `omo-browser@1` | browser runtime and explicit network policy | reviewed browser workflows only |
| bespoke pinned family | measured GPU/model or unusual native dependencies | exception approved through the same registry |

Build stable dependencies first and tool material last. Publish runtime images by immutable version/digest; tool rows pin `runtime_version`. A runtime upgrade adds a new version, canaries selected tools, then moves pointers. It never silently changes all bundles.

### 2.4 Trusted versus untrusted execution

There are two safe paths inside the logical runner:

1. **Declarative/first-party path.** The runtime owns the code and interprets reviewed steps such as `llm -> render_html -> weasyprint -> qa -> store`. Tool bundles contribute data/templates, not imported Python. This path reuses warm containers and provider adapters.
2. **Custom-code path.** The controller launches a single-use Restricted Function or Modal Sandbox from an allowlisted pinned image. It receives one bundle and one run-scoped input/output location, uses `block_network=True` by default, has no Modal resource access, and receives no raw provider credentials. If reviewed egress is essential, use an explicit allowlist or a brokered adapter operation. Terminate it after the result or timeout.

Third-party Markdown is never code. Third-party source code never imports into the shared runner process. A community tool that cannot fit the isolated path stays `needs_review`/`chargeable:false` or receives a separately approved per-tool App.

### 2.5 PhonicsMaker under this model

- The 93 prompt tools belong in Tier 2 once strict inputs/outputs, prompts, examples, provider policy, evaluation fixtures, and prices pass review. They do not need 93 generated Modal Apps.
- Worksheet, illustrated story, story editor, and Studio export belong in Tier 1 on `omo-pdf@1` plus the image/artifact adapters they actually require. Their bundles contain schemas, education policy, templates, fonts/assets references, and QA fixtures; the renderer/provider/storage code exists once.
- Anything lacking a private artifact plane, provider implementation, print/education QA, or measured cost remains `chargeable:false`, exactly as today.

## 3. Tier 2 — tools are data, executed by `omo-llm-runner`

### 3.1 Server-only manifest

One signed manifest row completely defines a pure-LLM tool. Required fields are:

```json
{
  "spec_version": "omo.llm-tool/v1",
  "tool_id": "00000000-0000-4000-8000-000000000000",
  "slug": "phonics-list-generator",
  "version": 3,
  "tier": 2,
  "input_schema": {},
  "output_schema": {},
  "prompt": {
    "system_template": "...reviewed text...",
    "user_template": "Use only this validated JSON input: {{ input_json }}",
    "few_shot": [{"input": {}, "output": {}}],
    "template_engine": "omo-safe-template/v1"
  },
  "model_policy": {
    "adapter_key": "openai-compatible-prod",
    "adapter_version": 2,
    "model": "<approved model id>",
    "temperature": 0.2,
    "max_output_tokens": 1200,
    "timeout_seconds": 60,
    "max_attempts": 2,
    "response_format": "json_schema"
  },
  "safety": {
    "policy_key": "education-default@1",
    "data_class": "ordinary",
    "log_input": false,
    "log_output": false
  },
  "artifact_policy": {"kind": "none", "max_bytes": 0},
  "pricing": {
    "price_cents": 10,
    "cost_model_sha256": "<64 hex>",
    "max_provider_cost_cents": 2
  }
}
```

Bounds are mandatory: strict Draft 2020-12 schemas, `additionalProperties:false`, bounded strings/arrays, bounded examples, output bytes, token ceiling, timeout, and retry count. Few-shot inputs and outputs are validated at registration. The safe template engine supports named substitutions and encoded `input_json`; it has no expression evaluation, includes, filesystem access, or arbitrary code.

The public catalog projection does not expose the system prompt, provider credential names, private examples, cost rates, or internal policies. `price_cents` is duplicated inside the signed execution projection only as an integrity assertion; `tools.price_cents` is the current billing authority.

### 3.2 Runner flow

The Worker sends the exact signed manifest version plus validated input to the Proxy-Token-protected `omo-llm-runner` endpoint. The runner:

1. verifies signature/hash, schema dialect, adapter/model allowlist, and global ceilings;
2. validates input again and renders the safe templates;
3. calls the adapter with structured-output mode and a server-owned credential;
4. validates the provider JSON against `output_schema`;
5. records bounded usage and estimated provider cost;
6. optionally materializes only a bounded UTF-8 text or JSON artifact; PDF/image/audio automatically requires Tier 1; and
7. validates and returns `omo.result/v1`.

All Tier-2 traffic shares the same Function, so calls naturally pool into fewer warm containers. This makes it **more likely** to be warm, not guaranteed: with `min_containers=0` it still scales to zero. Set `min_containers=1` only when measured p95 latency and revenue justify the idle cost; use `@modal.concurrent` for the I/O-bound provider wait and `max_containers` plus provider budgets to cap bursts.

### 3.3 Result contract

Every runner returns the same envelope:

```json
{
  "spec_version": "omo.result/v1",
  "run_id": "run_...",
  "tool_id": "00000000-0000-4000-8000-000000000000",
  "tool_version": 3,
  "status": "completed",
  "data": {},
  "artifacts": [
    {
      "artifact_id": "art_...",
      "role": "primary",
      "mime_type": "application/json",
      "bytes": 1234,
      "sha256": "<64 hex>"
    }
  ],
  "usage": {
    "adapter": "openai-compatible-prod@2",
    "provider": "...",
    "model": "...",
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "provider_calls": 1,
    "estimated_cost_usd": 0
  }
}
```

Artifacts contain opaque IDs, never durable object keys or provider URLs. The Worker associates them with `user_id` and `run_id`; authenticated artifact delivery issues a short-lived response. Tier-2 normally returns `artifacts:[]` and renders `data` directly.

## 4. Tier 3 and Tier 4

### 4.1 Downloads/content

Tier 3 is a purchase and entitlement path, not a fake run. The public listing includes filename, MIME type, byte count, version, license, preview metadata, and hash if desired; it never contains the storage key. The server maps `(tool_id, tool_version, file_id)` to a private immutable object.

Flow: authenticated checkout creates a pending purchase from server-owned `price_cents`; the signed Stripe webhook completes it exactly once and grants an entitlement; `GET /api/downloads/:slug/:file_id` checks the active user, entitlement, purchased version, and file record, then streams or redirects with a short expiry. Bundles grant several file/tool entitlements without inventing a product-specific database.

### 4.2 Shared external-provider adapters

Tier-4 manifests refer only to an allowlisted `adapter_key`, `adapter_version`, and `operation`. A small server-owned adapter registry defines:

```text
adapter_key, version, status, capabilities, operations
runner_family, implementation_version
secret_set_name (server-only), allowed_hosts
provider idempotency support, timeout/retry/rate-limit policy
poll/webhook normalizer, output schema family
cost units/rates, accepted-output-yield evidence, canary timestamp
```

The registry metadata may live in Neon, but adapter implementation selection remains an allowlisted map compiled into the runner; a tool row cannot introduce executable code, a URL, or a secret name. Adapters produce the normal result/artifact envelope. Missing adapter, unsupported operation, absent secret, stale cost evidence, failed canary, or incomplete output mapping means `can_submit:false` and `chargeable:false` before provider spend.

Provider credentials are environment- and capability-scoped (`omo-llm-prod`, `omo-images-prod`, `omo-video-prod`), not cloned per tool. Custom tool code never receives them. Adapter calls should carry Omo's `run_id` as the provider idempotency key where supported.

## 5. O(1) dispatch: one indexed registry lookup, four stable handlers

“O(1)” here means constant application logic independent of catalog size: no slug switch, generated 100,000-row JS map, or per-tool route. The indexed unique-slug query is logarithmic internally but effectively constant at this scale.

`POST /api/run` performs:

1. authenticate the Clerk user/API key; normalize the slug and bound the request;
2. fetch the active `published` tool by unique slug from Neon, including exact version, tier, signed execution manifest, `chargeable`, and `price_cents`;
3. validate input against that version; reject disabled, download-only, unsigned, unknown-tier, unsupported-runtime, or non-chargeable requests before reservation;
4. claim unique `(user_id, idempotency_key)` with a request hash and snapshot `tool_id`, version, tier, manifest hash, and price; an identical replay returns the existing run, while a different body conflicts;
5. atomically reserve the exact `tools.price_cents` through the existing ledger state machine;
6. choose one of four fixed handlers: Tier 1 -> `omo-runner`; Tier 2 -> `omo-llm-runner`; Tier 3 -> `409 DOWNLOAD_ONLY` with checkout/download links; Tier 4 -> the shared adapter runner; and
7. persist the Modal/provider call reference, poll or consume a signed callback, validate the exact-version result, then capture once or refund once.

The only endpoints the Worker may call come from an environment-owned runner allowlist such as `RUNNER_TARGETS[tier][runner_release]`. A database manifest cannot inject an arbitrary URL. During migration, an allowlisted `legacy_modal_app` target can resolve the current per-tool endpoint.

Registry lookup failure, signature/hash mismatch, cache disagreement, unknown version, missing runner configuration, or billing uncertainty fails closed. If no reservation occurred, no ledger event exists; if it occurred, one deterministic `run_refund:<run_id>` event restores it.

### Cache policy

Neon is authoritative. Initially query it on every run; 100,000 registry rows are small for a unique indexed lookup. Use Cloudflare KV first for public catalog/detail projections, where eventual consistency is acceptable. Only introduce a dispatch cache after load measurements, and then cache immutable version keys (`tool:<id>:v:<n>:<hash>`) plus a short-lived slug pointer. A cached row must carry the registry signature and expiry. KV must never calculate a price or silently override Neon; a price/version change invalidates the pointer through a transactional outbox event.

## 6. Neon registry and run data

### 6.1 `tools` is the current-state heart

This Postgres DDL is a design sketch, not a migration to run now:

```sql
CREATE TABLE tools (
  tool_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug                TEXT NOT NULL UNIQUE
                      CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  owner_id            TEXT,
  tier                SMALLINT NOT NULL CHECK (tier BETWEEN 1 AND 4),
  name                TEXT NOT NULL,
  summary             TEXT NOT NULL,
  category            TEXT NOT NULL,
  tags                TEXT[] NOT NULL DEFAULT '{}',
  status              TEXT NOT NULL
                      CHECK (status IN ('draft','review','ready','published','disabled','retired')),
  chargeable          BOOLEAN NOT NULL DEFAULT FALSE,
  version             BIGINT NOT NULL,
  manifest            JSONB NOT NULL,        -- canonical server-only active manifest
  catalog_json        JSONB NOT NULL,        -- safe public projection source
  manifest_sha256     CHAR(64) NOT NULL,
  manifest_signature  TEXT NOT NULL,
  price_cents         INTEGER NOT NULL CHECK (price_cents >= 0),
  runtime_family      TEXT,                  -- tier 1; allowlisted
  runner_release      TEXT NOT NULL DEFAULT 'stable',
  adapter_key         TEXT,                  -- tier 2/4; allowlisted
  published_at        TIMESTAMPTZ,
  deployed_at         TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  search_document     TSVECTOR GENERATED ALWAYS AS (
    to_tsvector('simple',
      coalesce(name,'') || ' ' || coalesce(summary,'') || ' ' ||
      coalesce(category,'') || ' ' || coalesce(array_to_string(tags,' '),''))
  ) STORED,
  CHECK (status <> 'published' OR published_at IS NOT NULL),
  CHECK (NOT chargeable OR status IN ('ready','published'))
);

CREATE INDEX tools_owner_status_idx ON tools (owner_id, status, updated_at DESC);
CREATE INDEX tools_status_published_idx ON tools (status, published_at DESC, tool_id);
CREATE INDEX tools_tier_status_idx ON tools (tier, status);
CREATE INDEX tools_search_idx ON tools USING GIN (search_document);
CREATE INDEX tools_tags_idx ON tools USING GIN (tags);
```

`catalog_json` is not a second source of truth; registration deterministically compiles it from `manifest`, and drift checks compare hashes. Separating it prevents `/api/catalog` from accidentally returning prompts, private artifact keys, provider configuration, or cost internals.

At 100,000 rows, these indexes are ordinary Postgres scale. Add `pg_trgm` for fuzzy name/slug search only after enabling and measuring the extension. Use `websearch_to_tsquery` and keyset cursors, not `%term%` scans or large `OFFSET`s.

### 6.2 Immutable versions and rollback

Never overwrite the only copy of a manifest. Keep an immutable history:

```sql
CREATE TABLE tool_versions (
  tool_id             UUID NOT NULL REFERENCES tools(tool_id),
  version             BIGINT NOT NULL,
  manifest            JSONB NOT NULL,
  catalog_json        JSONB NOT NULL,
  manifest_sha256     CHAR(64) NOT NULL,
  manifest_signature  TEXT NOT NULL,
  price_cents         INTEGER NOT NULL CHECK (price_cents >= 0),
  runtime_family      TEXT,
  runner_release      TEXT NOT NULL,
  adapter_key         TEXT,
  bundle_uri          TEXT,                 -- private, immutable object URI
  bundle_sha256       CHAR(64),
  status              TEXT NOT NULL CHECK (status IN ('candidate','canary','approved','rejected','retired')),
  created_by          TEXT NOT NULL,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  approved_at         TIMESTAMPTZ,
  deployed_at         TIMESTAMPTZ,
  PRIMARY KEY (tool_id, version)
);
```

Publishing is one transaction that inserts an approved version and copies its current projection into `tools`. A run snapshots `tool_id`, version, manifest hash, and price. Rollback copies a prior approved version into the active row; in-flight runs continue against their pinned version. Historical `tool_versions.price_cents` explains past versions, but `tools.price_cents` is the sole current quote and `run_requests.cost_cents` is the immutable per-run billing fact.

Use monotonic numeric versions for database ordering and optionally retain SemVer inside the manifest for human contracts. Do not reuse a version after rejection or rollback.

### 6.3 Files, purchases, and entitlements

```sql
CREATE TABLE tool_files (
  tool_id       UUID NOT NULL,
  tool_version  BIGINT NOT NULL,
  file_id       TEXT NOT NULL,
  role          TEXT NOT NULL,
  object_key    TEXT NOT NULL,              -- server-only
  filename      TEXT NOT NULL,
  mime_type     TEXT NOT NULL,
  bytes         BIGINT NOT NULL CHECK (bytes >= 0),
  sha256        CHAR(64) NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tool_id, tool_version, file_id),
  FOREIGN KEY (tool_id, tool_version) REFERENCES tool_versions(tool_id, version)
);

-- Add to the existing purchases transaction record:
-- purchase_id, user_id, tool_id, tool_version, completed_at.

CREATE TABLE entitlements (
  entitlement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         TEXT NOT NULL,
  tool_id         UUID NOT NULL REFERENCES tools(tool_id),
  tool_version    BIGINT NOT NULL,
  file_id         TEXT,                     -- NULL grants all files in that version
  purchase_id     UUID NOT NULL,
  granted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at      TIMESTAMPTZ,
  UNIQUE (user_id, tool_id, tool_version, file_id, purchase_id),
  FOREIGN KEY (tool_id, tool_version) REFERENCES tool_versions(tool_id, version)
);

CREATE INDEX entitlements_user_tool_idx
  ON entitlements (user_id, tool_id, tool_version) WHERE revoked_at IS NULL;
```

Keep Stripe session/event idempotency in `purchases`; entitlement rows describe access. This cleanly supports bundles, grants, refunds/revocations, and version-preserving re-downloads. It also avoids overloading a Stripe transaction row as the only authorization model.

### 6.4 Runs, retention, and partitioning

Tool count does not justify partitioning; run volume does. Evolve `run_requests` into the authoritative execution/billing state machine rather than adding per-tool run tables. Add `tool_id`, `tool_version`, `tier`, `manifest_sha256`, `runner_release`, `provider_call_id`, `finished_at`, and `expires_at`. For Neon-only evolution, use JSONB for bounded `input`, `result`, `artifact`, and `error` metadata; place large bodies and all binaries in the artifact store.

Keep these indexes:

```text
UNIQUE (user_id, idempotency_key)
(run_id) primary key
(user_id, created_at DESC)
(tool_id, created_at DESC)
partial (execution_status, dispatch_lease_expires_at, updated_at)
  WHERE execution_status IN ('queued','dispatching')
BRIN (created_at) once the table is very large and append-heavy
```

Do not partition on day one. Introduce monthly time partitions only after measured retention/vacuum/index pressure—e.g. tens of millions of rows or an active table above roughly 100 GB—and prove cross-partition idempotency remains globally enforced. Retain financial ledger/purchase/entitlement records per accounting policy. Expire bulky run inputs/results and progress detail on an explicit policy (for example 30–90 days by data class), preserving run ID, tool/version, price, usage totals, terminal state, hashes, and ledger references.

`credits_ledger` remains append-only and generic. Each debit/refund has a deterministic unique event ID. No tool-specific balance table and no recomputation of historical balances from today's price.

### 6.5 Registry outbox

Registration and cache/catalog invalidation must not be two uncoordinated writes. Add a small `registry_outbox` table in the same transaction as an active-version change. Consumers idempotently invalidate the KV slug pointer, refresh public detail/search projections, and trigger/check the static export. A failed consumer retries; the database version remains authoritative.

## 7. Catalog: database first, static-safe migration

### Decision

Make Neon the source of truth. Keep the static site as a **derived view**, not a second hand-edited catalog. Do not put 100,000 rich listings into `ig-more.js`, and do not make Cloudflare KV authoritative.

### Non-breaking migration from the current listings

1. **Inventory and import, no browser change.** Parse both current catalog arrays and generated hosted profiles into candidate `tools`/`tool_versions` rows. Produce a report of slug, listing hash, tier, version, price, and publication state. Stop on duplicate slug, price disagreement, missing manifest, or the current 23/24 count discrepancy.
2. **Shadow registry.** Read `/api/run` from the existing generated registry but compare every request's slug/version/price against Neon in logs/tests. No behavior changes until exact parity and fail-closed tests pass.
3. **Deterministic compatibility export.** Add a future build command such as `tools/export-catalog --format=current-js --check` that emits the exact existing browser shape and a revision/hash banner. Initially commit its output to the files the static site already loads. This preserves SEO, offline/static behavior, and the current 24 listings.
4. **Registry-backed dispatch.** Feature-flag `/api/run` to the indexed Neon lookup, first for Tier-2 canaries and then all generic hosted tools. Existing per-tool Apps use the legacy execution target until migrated.
5. **Paginated live catalog before bulk growth.** Add `GET /api/catalog?query=&category=&tier=&cursor=&limit=` and `GET /api/tools/:slug`. Return only `catalog_json`; cap `limit` and use keyset cursors. The home/static export becomes featured/popular rows and per-tool SEO shells, while browsing/search fetches pages. Do this before 1,000 listings, not after a 100,000-row JS file exists.
6. **Retire hand edits.** CI fails when the committed export differs from Neon's approved snapshot or when a human edits inside the generated region. `host.py --register --check` evolves into registry/version/export checks.

Build-time export is the compatibility bridge; the paginated API is the 100,000-tool catalog. KV may cache cursor pages and public details by catalog revision. Search uses Neon FTS first. A separate search service is not justified until measured relevance or p95 latency fails; its index would still be a derived projection rebuilt from Neon.

## 8. Scaling mechanics and cost

### Spin up, run, spin down

- Tier-1 declarative runtime Functions use `min_containers=0` for the long tail. The first call may queue for image/container initialization; Modal reuses a warm container while available and scales down after the configured window.
- Tier-1 isolated code creates one bounded Sandbox or single-use Restricted Function, executes the pinned bundle, persists only validated output/artifacts, and terminates it. This is the literal per-run spin-up/spin-down path without a per-tool App.
- Tier 2 pools all LLM traffic, so a warm container is likely at modest aggregate volume. One warm minimum can be bought only after latency economics justify it.
- Tier 3 starts no compute.
- Tier 4 pools calls by adapter/runtime family and applies provider budgets before scaling Modal containers.

Warmth is an SLO decision, not a listing property. Record `queued_ms`, `container_start_ms`, `bundle_load_ms`, `provider_ms`, `render_ms`, and `total_ms`. Keep a runtime family warm or preload a small hot bundle set only when its p95/SLO and contribution margin justify it.

### Concurrency and backpressure

Set limits at four layers:

1. Worker per-user and per-tool rate/parallelism quotas;
2. runtime `@modal.concurrent` and `max_containers` by I/O- or CPU-bound family;
3. adapter/provider token, request, image, video, and spend budgets; and
4. a global environment budget/circuit breaker.

Queue or return honest `429`/`503` with retry information when a limit is reached. Never let 100,000 independently autoscaling Apps stampede one provider account. Do not retry non-idempotent provider operations unless their adapter supplies a provider idempotency key or reconciliation path.

### Cost shape

| Tier | Marginal cost formula | Idle cost |
| --- | --- | --- |
| 1 | Modal CPU/GPU/memory seconds + provider units + artifact storage/egress + retry/accepted-output yield | zero with `min_containers=0`; explicit warm pools cost while provisioned |
| 2 | prompt/completion tokens + small shared HTTP/validation compute + optional artifact bytes | normally zero after scale-down; optionally one pooled warm container |
| 3 | object storage + egress + payment/support costs | storage persists; no Modal compute |
| 4 | third-party operation + polling/webhook/adapter compute + artifact egress + retry/yield | shared adapter can scale to zero; provider commitments may not |

Every approved version retains a `pricing-report` payload/hash with measured units, provider/runtime rates, retry/yield assumptions, margin rule, and timestamp. Registration compiles its display price into `tools.price_cents`; the Worker never prices from the client or reruns the cost formula at request time. Unknown cost, stale rate, missing yield, or margin below policy makes the version non-chargeable.

### Secrets

- Proxy Tokens authenticate Worker -> runner endpoints and may be environment-scoped.
- Registry signatures authenticate the exact manifest/version; transport authentication alone is not version integrity.
- Provider credentials belong only to adapter/runtime families and environments. Use dedicated metered production API accounts with budgets and rotation, not one secret per tool.
- Tier-1 custom code gets no provider credentials. It requests approved adapter operations through a broker or runs with reviewed network/secret exceptions.
- Artifact access uses read-only runtime credentials and run-scoped writes/opaque IDs where practical. No catalog or bundle contains a durable credential.

## 9. Registration, review, versioning, and rollback

The existing `host.py` and `process-submissions.py` remain the front door, but registration becomes tier-aware and registry-first:

1. **Claim safely.** Consumers claim submissions with a lease/`FOR UPDATE SKIP LOCKED`; retries are idempotent by submission/source hash. Twenty tools per week is review throughput, not database pressure.
2. **Treat source as hostile.** Parse Markdown; never execute it. Resolve a reviewed profile with identity, tier, schemas, fixtures, safety/data classification, capabilities, runtime/adapter needs, and marketplace copy.
3. **Classify:** Tier 2 generates a signed data manifest and no container; Tier 1 compiles an immutable bundle against an existing runtime family; Tier 3 scans/hashes/uploads files; Tier 4 resolves an existing ready adapter operation or stops.
4. **Test:** run schema lint, happy/negative fixtures, the house contract suite, tool-specific goldens/evals, output/artifact QA, prompt-injection checks, and security/network tests. Tool code tests run in the same isolated policy used in production.
5. **Price:** compile `pricing-report.json` into the candidate version and proposed `price_cents`. Unknown dependencies, providers, artifacts, storage/egress, retries, or accepted-output yield keep `chargeable:false`.
6. **Materialize:** upload the content-addressed bundle/files, build a new named runtime image only if a new family/version is approved, and insert an immutable `tool_versions` candidate. Tier 2 performs no Modal deploy.
7. **Canary:** call the exact candidate version directly, validate output and usage, then exercise Worker validation/idempotency/reserve/settle/refund in a non-production or explicitly approved environment. Promotion gates remain separate.
8. **Publish atomically:** in one database transaction, approve the version, copy it into `tools`, set `deployed_at`/`published_at`, and write a registry-outbox event. Publication remains an explicit gate; queue success is not “live.”
9. **Sync and verify:** refresh KV/public catalog and deterministic static export; check slug/version/price/manifest hashes and the current-site parity suite.

The honest gates from the existing pipeline remain mandatory: strict schemas, provider/adapter readiness, input validation before spawn, terminal output validation, private artifacts, measured pricing, Proxy Token ingress, direct canary, Worker tests, ledger canary, and explicit publish approval. Unsupported work returns `WORKFLOW_NOT_READY` before spend.

Rollback does not rebuild or redeploy the tool. Select a prior approved `tool_versions` row, atomically copy it into `tools`, and emit the outbox event. Retain bundles/runtime images until no active or retained run references them. A bad shared runner release rolls back through an environment-owned blue/green `runner_release` mapping, not by editing 100,000 rows in place.

## 10. Roadmap: current catalog to 100,000

| Phase | Listing scale | Work | Exit gate |
| --- | ---: | --- | --- |
| **0 — parity** | current ~24 | Add registry/version/export specifications and import current catalog/hosted profiles in shadow mode; resolve 23/24 discrepancy | exact slug/version/price/hash report; no site or dispatch behavior change |
| **1 — shared-runner canaries** | 25–100 | Deploy one `omo-llm-runner`; build `omo-runner` with light/PDF runtime; migrate 5–10 Phonics pure-LLM tools as rows and one fail-closed/then-ready PDF tool | direct + Worker + billing canaries, rollback rehearsal, no per-tool deploy for Tier 2 |
| **2 — registry dispatch/catalog API** | 100–1,000 | Switch generic `/api/run` to indexed Neon; deterministic static export; public paginated catalog/detail API; FTS; R2 bundle/file plane; shared adapter registry | parity/regression suite, p95 registry lookup budget, cache-staleness and fail-closed tests |
| **3 — safe code and operations** | 1,000–10,000 | Single-use restricted/Sandbox path, signed bundles, blue/green runner releases, outbox, quotas/circuit breakers, entitlement delivery, observability/retention | hostile-code/network/secret tests, provider stampede test, disaster/rollback drill |
| **4 — bulk catalog** | 10,000–100,000 | Batch manifest/content ingestion, cursor catalog, search relevance tuning, derived KV pages, runtime-family capacity tests, provider budgets, community policy if approved | 100k-row load test, no giant JS/map/switch, catalog/search SLO, zero cross-tool data leakage, billing reconciliation |

Do not manufacture 100,000 thin aliases to hit a count. Tier-2 row creation can be cheap, but publication still needs a distinct user contract, strict schema/output, evaluation evidence, demand/category review, and honest pricing.

## 11. Clean-code rule and anti-patterns

**Omo in one paragraph:** tools are immutable versioned registry records with one active projection; pure-LLM tools are data interpreted by one runner; heavy tools are small signed bundles executed on a finite set of shared Modal runtime images, with custom code isolated; external providers are shared reviewed adapters; dispatch is one indexed manifest lookup plus four fixed tier handlers; billing reads one current `price_cents` and snapshots it into a generic run ledger; artifacts are opaque private objects; and the static marketplace is a generated/public view of Neon, not the source.

Prohibit:

1. per-tool `if`/`switch` blocks, Worker routes, endpoint env vars, or pricing maps;
2. 100,000 Modal Apps, universal dependency images, or tool bundles named `latest`;
3. per-tool database/run tables or PhonicsMaker-specific tables in Omo;
4. raw provider calls, secret names, arbitrary endpoints, or durable object URLs in tool manifests/client payloads;
5. importing third-party code into a reused shared process;
6. using KV, `ig-more.js`, a Modal Volume, or a container image as the registry source of truth;
7. overwriting manifests instead of immutable version rows and pointer changes;
8. large request/results or binaries in Neon; and
9. charging when adapter, artifact, QA, cost, version, signature, or billing state is uncertain.

## 12. Founder decisions and recommendations

1. **Is the shared Tier-1 runner acceptable?** Recommend yes for first-party declarative bundles. Never import arbitrary community code into its process; use a single-use restricted Function/Sandbox. Reserve per-tool Apps for privileged/bespoke isolation. Confirm Modal plan/API support and load-test the isolated path before community code.
2. **Catalog authority:** recommend Neon-first, with deterministic static export as the non-breaking bridge and KV/API as derived reads. Do not choose KV or JS as authority.
3. **Search timing:** add the search column/index with the registry migration; ship paginated FTS before 1,000 tools. Delay a dedicated search service until Postgres relevance/p95 measurements require it.
4. **Tier-2 credentials:** use a dedicated metered production provider account/key with hard budgets, rate limits, audited terms, and a fallback adapter. Do not depend on a Codex subscription access token. Use `OPENCODE_GO_API_KEY` only if its production SLA, terms, model stability, and metering are explicitly approved.
5. **Who may supply tools?** Recommend first-party plus declarative community manifests/downloads initially. Third-party custom code requires provenance/licensing, static and dependency review, isolated execution, network/secret denial, abuse process, and stronger publication gates. The founder must decide whether “100,000” includes those uploads before enabling code submission.
6. **Modal capacity/commercial limits:** ask Modal to confirm workspace deployment, Function/Sandbox creation, concurrency, image, and log-retention quotas for Omo's forecast. The design avoids 100,000 Apps, but provider and account limits still need written capacity assumptions before a bulk launch.

## 13. Architecture acceptance tests

The implementation is ready to scale only when all are true:

- registering a Tier-2 tool changes one immutable registry version and zero Modal deployments;
- registering a Tier-1 tool using an existing family uploads one signed bundle and changes zero runtime deployments;
- `/api/run` contains no slug-specific dispatch and resolves any published slug through the same indexed path;
- a stale/tampered manifest, unknown adapter/runtime, insufficient balance, malformed input/output, or registry outage cannot charge or leak a result;
- idempotent replay returns the same run and a changed replay conflicts; terminal failure refunds exactly once;
- rollback is an active-version pointer transaction and leaves in-flight pinned runs valid;
- an untrusted bundle cannot reach Modal resources, another user's files, provider credentials, or the public network unless explicitly reviewed;
- catalog export/API/KV all identify their source registry revision and can be regenerated from Neon;
- the 100,000-row load test meets catalog/search/dispatch SLOs without a 100,000-row browser bundle or Worker map; and
- a complete artifact, billing, and registry audit can be traced by `run_id`, `tool_id`, version, manifest hash, bundle hash, and ledger event IDs without logging user content or secrets.
