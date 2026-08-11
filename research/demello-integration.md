# de Mello Awake — Omo integration contract

Date: 2026-08-11  
Workflow: `demello-awake@0.1.0`  
Style: `sumi-e-awake-v3`

## Boundary

The Cloudflare Worker remains the only buyer-facing gateway and money authority. It authenticates the tenant, resolves an immutable release, validates/canonicalizes input, quotes, writes the durable run/outbox record, and only then dispatches to the release-specific Modal app. A promoted paid release would also reserve credits before dispatch. This milestone deliberately reserves and bills zero because `paid_traffic_ready:false`. Modal owns active execution and media QA; it does not own balances, tenant authorization, release selection, or settlement.

The milestone endpoint is private bearer-authenticated transport. It uses a Modal Volume plus five-minute signed artifact links because Proxy Token and exact-object R2 capabilities are not yet wired. Its responses explicitly report `paid_traffic_ready: false`; do not route paid buyer traffic to it yet.

## Deployed milestone release

- Release: `sha256:bdab144b977aee48ecb383041cd4eaa2a7ea454ea7577c15ece41f7d7f59861d`
- App: `omo-demello-awake-bdab144b977a`
- Base URL: `https://harrythentrepreneur--omo-demello-awake-bdab144b977a-api.modal.run`
- Submit: `POST /v1/runs` (alias: `POST /run`)
- Status: `GET /v1/runs/{run_id}`
- Authentication: `Authorization: Bearer $API_SERVER_KEY`
- Idempotency: required `Idempotency-Key`, 8–128 characters
- Result transport: short-lived signed `video_url` and `contact_sheet_url`

## Direct private smoke contract

The private request schema describes exactly one of `audio_ref` and `audio_url`; HTTPS URLs have DNS/IP/redirect/byte-limit validation. The exposed milestone also pins `DEMELLO_PROVIDER_LANE_ENABLED=0`, so in practice it rejects every `audio_url` before download or provider spend and accepts only `audio_ref=sample-demello-10s`. Bounds satisfy `5 <= min_seconds <= max_seconds <= 20`.

```json
{
  "audio_ref": "sample-demello-10s",
  "style": "sumi-e-awake-v3",
  "duration_bounds": {
    "min_seconds": 5,
    "max_seconds": 10
  }
}
```

Direct private smoke calls get a server-generated run ID, canonical request hash, and a $5 execution ceiling. They are not quotes and perform no reservation or settlement.

```bash
export DEMELLO_ENDPOINT='https://harrythentrepreneur--omo-demello-awake-bdab144b977a-api.modal.run'

curl --fail-with-body -X POST "$DEMELLO_ENDPOINT/v1/runs" \
  -H "Authorization: Bearer $API_SERVER_KEY" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-demello-001' \
  --data '{
    "audio_ref":"sample-demello-10s",
    "style":"sumi-e-awake-v3",
    "duration_bounds":{"min_seconds":5,"max_seconds":10}
  }'

curl --fail-with-body \
  -H "Authorization: Bearer $API_SERVER_KEY" \
  "$DEMELLO_ENDPOINT/v1/runs/<run_id>"
```

The initial response is `202` with `run_id`, `status_url`, and the milestone platform flags. A completed status includes:

```json
{
  "run_id": "run_...",
  "release_hash": "sha256:...",
  "request_hash": "...",
  "status": "completed",
  "video_url": "https://.../video.mp4?expires=...&signature=...",
  "contact_sheet_url": "https://.../contact-sheet.jpg?expires=...&signature=...",
  "frames_used": {"generated": 30, "semantic": 30, "output": 300},
  "cost": {"measured_usd": 0.0011, "guard_cost_usd": 0.003, "guarded_price_usd": 0.10},
  "media": {"duration_seconds": 10, "video_codec": "h264", "audio_codec": "aac", "width": 1080, "height": 1920, "fps": 30},
  "generation_provider": "procedural-fallback",
  "platform": {"paid_traffic_ready": false}
}
```

## Real Modal progress checkpoints

The Modal executor now polls the workflow's run-scoped
`runs/<run_id>/diagnostic.json` marker while the Go-controlled subprocess is
alive, commits each changed checkpoint to `status.json`, and exposes monotonic
`phase` plus `progress_pct` in `GET /v1/runs/{run_id}`. These are execution
checkpoints, not elapsed-time animation:

| Internal marker | Public phase | Percent |
|---|---|---:|
| accepted | `queued` | 2 |
| executor started | `starting` | 5 |
| `acquire` | `preparing` | 8 |
| `transcribe` | `transcribing` | 20 |
| `direct` | `directing` | 36 |
| `generate` | `generating` | 52 |
| `semantic` | `generating` | 70 |
| `assemble` | `assembling` | 82 |
| `qa` | `validating` | 94 |
| `contract` | `finalizing` | 98 |
| completed result committed | `delivered` | 100 |

The Worker normalizes these Modal-native phases into its smaller public state
machine. Its elapsed estimate remains only a labeled fallback for an older
release that returns no checkpoint.

The e335 staging canary observed `2 → 5 → 8 → 52 → 70 → 82 → 94 → 100`
from submit through delivery. Fixture-backed transcription and direction are
effectively instantaneous, so a 750 ms external poll did not observe their 20
and 36 percent markers even though the workflow emitted them. The delivered
328,613-byte MP4 passed ffprobe as H.264, 1080×1920, 30 fps, 300 frames, exactly
10.000 seconds; the result disclosed `generation_provider:procedural-fallback`,
`guarded_price_usd:0.10`, and `paid_traffic_ready:false`.
The final bdab release is the same passing runtime plus a strict output-schema
declaration for the delivered `phase` and `progress_pct` fields; its build and
35 offline checks passed after that contract-only correction.

## Provider authentication

The tested ChatGPT-subscription recipe and negative public-API scope probes are
documented in `research/codex-subscription-auth.md`. The working image path is
the Codex Responses `image_generation` tool with
`OPENAI_CODEX_ACCESS_TOKEN` and `OPENAI_CODEX_ACCOUNT_ID`; it is not
`api.openai.com/v1/images/generations`. Optional memory-only refresh reads
`OPENAI_CODEX_REFRESH_TOKEN`. No secret value is stored in this repository.

Subscription image generation is real, but its response has no billable USD
meter, refresh-token rotation is not durable across scale-to-zero, and the
current arbitrary-audio transcription adapter still lacks a valid public API
credential. The typed runner preserves the distinct
`openai-codex-subscription` provider and incomplete cost evidence fails guarded
settlement closed. `paid_traffic_ready` therefore remains false.

The exposed Modal milestone additionally pins
`DEMELLO_PROVIDER_LANE_ENABLED=0`. Only `sample-demello-10s` reaches execution;
non-bundled audio is rejected before download or provider spend, preventing a
reserve/refund loop from becoming a provider-budget bypass.

## Worker dispatch envelope

After the $0.10 quote and zero-bill durable claim, the Worker dispatches the canonical, server-owned envelope below. `request_hash` is the raw lowercase SHA-256 of canonical JSON input; `release_hash` includes the `sha256:` prefix. The endpoint recomputes the input hash and rejects mismatches.

```json
{
  "run_id": "run_<server-generated>",
  "release_hash": "sha256:<64 lowercase hex>",
  "request_hash": "<64 lowercase hex>",
  "input": {
    "audio_ref": "sample-demello-10s",
    "style": "sumi-e-awake-v3",
    "duration_bounds": {"min_seconds": 5, "max_seconds": 10}
  },
  "max_cost_usd": 0.003
}
```

The future Worker sequence, consistent with `research/modal-optimization/round-5.md`, is:

1. Authenticate Clerk JWT or Omo API key; derive tenant server-side.
2. Resolve the immutable release and schemas server-side.
3. Validate/canonicalize input; compute `request_hash`.
4. Create a ten-minute quote at 10 cents and atomically create/replay the run and write the dispatch record. While the release remains nonpaid, `cost_cents`, reserved credit, and billed amount are all zero. A future paid promotion must reserve and append the debit ledger event atomically before dispatch.
5. Dispatch the signed envelope to the pinned Modal base URL. The raw caller key remains only in the account-scoped Worker record; Modal receives `omo-` plus SHA-256 of a stable namespace, owner identity, and caller key. This is deterministic for retries, distinct across tenants that choose the same key, and does not expose the tenant ID. Same tenant/key/hash replays; same account-scoped key with a different hash is `409`.
6. Poll or consume signed checkpoints; on success, verify exact R2 artifacts and settle actual charge once. On terminal failure, release/refund once. Reconcile stale runs and paid effects.

No arbitrary provider input reaches this milestone. Before any paid promotion, no call that can incur Modal/provider cost may precede a successful reservation.

## Guarded price

Successful delivered compute samples were `$0.00214633` (round 1, 122.368 s) and `$0.00111446` (refined deterministic lane, 63.538 s). With the small sample, empirical p95 is the maximum: `$0.00214633`. A 15% media tail is `$0.00246828`; the conservative static bound is `$0.003`.

```text
C_guard = max(0.003, 0.00214633, 0.00246828) = 0.003
price = ceil_to_cent(max(0.10, 0.003 / (1 - 0.80))) = $0.10
```

The 10-cent quote is only for the measured bundled/deterministic lane. Arbitrary customer audio currently requires OpenAI transcription and image credentials; it must be re-benchmarked with valid provider billing and accepted-output yield before enabling paid quotes.

## Implemented Worker contract

The server-owned listing slug is `japanese-style-story-video`; its own price is $29 and its measured bundled-lane run quote is $0.10. The buyer-facing routes are:

- `POST /api/run` — Clerk bearer or owning `omo_` API key plus `Idempotency-Key`; quotes $0.10 but reserves/bills $0 while `paid_traffic_ready:false`, dispatches the bundled sample to Modal, and returns HTTP 202 with `{run_id,status,phase,progress_pct,progress_source,status_url,quoted_cost_usd,billed_amount_usd,billing_mode,paid_traffic_ready}`.
- `GET /api/run/{run_id}` — owner-only polling; refreshes Modal status, advances monotonic progress, settles a delivered result exactly once, and returns `video_url` plus `contact_sheet_url`.
- `POST /api/run/{run_id}/progress` — optional server-to-server checkpoint ingress protected by `DEMELLO_PROGRESS_WEBHOOK_SECRET`. The currently deployed Modal release can be polled and does not require this callback.

The durable `run_requests` record remains the idempotency/billing authority. Its uniqueness scope is `(user_id,idempotency_key)`; the opaque derived Modal key bridges that scope safely into Modal's global idempotency namespace. The additive `run_progress` table holds phase, percentage, progress source, Modal status, and terminal artifact metadata. Its atomic UPSERT keeps phase, percentage, and source from the same winning checkpoint; lower polls cannot relabel higher progress. Explicit dispatch rejection, Modal failure, and timeout transition to `refunded`; an idempotent credit refund is appended only if a debit exists. Successful delivery transitions to `succeeded`; terminal compare-and-set results are re-read so a late failure or completion race cannot overwrite the authoritative result.

Public phases are `reserved → running → transcribing → directing → generating → assembling → delivered`. Modal-native phases are normalized to this set. When the private status response has no checkpoint, elapsed-time progress is capped below 100 and labeled `progress_source:"derived"`; it is never described as real telemetry. A valid Modal or authenticated webhook checkpoint takes precedence and cannot be downgraded by the estimate.

Before successful settlement, the Worker validates both artifact URLs against the exact pinned Modal origin and exact `/v1/artifacts/{run_id}/{object}` path, requires one ten-digit `expires` and one lowercase 64-hex `signature`, enforces a short TTL window, and verifies the HMAC over the exact object. An unusable video or contact-sheet URL fails the run before settlement.

### Worker configuration (secret values never go in source)

- `DEMELLO_MODAL_BEARER` — required secret; same value as Modal `API_SERVER_KEY` for this milestone.
- `DEMELLO_MODAL_URL` — optional override; defaults to the pinned `bdab144b977a` app URL above.
- `DEMELLO_RELEASE_HASH` — optional override; defaults to the full pinned `sha256:bdab…861d` digest.
- `DEMELLO_MAX_COST_USD` — optional guarded ceiling, default `$0.003`.
- `DEMELLO_EXPECTED_RUN_SECONDS` — optional derived-progress horizon, default 90 seconds.
- `DEMELLO_RUN_TIMEOUT_SECONDS` — optional run/reconciliation timeout, default 1300 seconds.
- `DEMELLO_PROGRESS_WEBHOOK_SECRET` — optional independent bearer for checkpoint callbacks.

### Buyer-facing curl loop

```bash
export OMO_API_BASE='https://omo.best'

RUN_JSON=$(curl --fail-with-body -sS -X POST "$OMO_API_BASE/api/run" \
  -H "Authorization: Bearer $OMO_API_KEY" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demello-buyer-0001' \
  --data '{
    "slug":"japanese-style-story-video",
    "fields":{
      "audio_ref":"sample-demello-10s",
      "style_hint":"sumi-e",
      "duration_bounds":{"min_seconds":5,"max_seconds":10}
    }
  }')

# Copy run_id from RUN_JSON, then poll until status is delivered or failed.
curl --fail-with-body -sS \
  -H "Authorization: Bearer $OMO_API_KEY" \
  "$OMO_API_BASE/api/run/<run_id>"
```

Hosted pre-admission dispatches only `audio_ref=sample-demello-10s`. An arbitrary HTTPS URL is rejected before durable claim, reservation, or Modal/provider spend. If a topic/loose-text compatibility input is retained, the Worker returns an explicit `input_notice` that speech was not synthesized and substitutes only the bundled sample; it never labels the topic as generated narration. The listing and dashboard expose the sample-only hosted contract.

MCP stays a thin REST client: `omo_run_helper` returns the run ID and initial progress, `omo_get_run_progress` polls status, and `omo_get_run_result` returns the delivered URLs. It never calls Modal or mutates balances directly for this slug.

## Remaining production blockers

This integration makes the private milestone callable and testable, but it does not make the milestone paid-traffic-ready. `platform.paid_traffic_ready` remains false. Production still requires Modal Proxy Token plus short-lived replay-protected Worker capability (replacing the shared private bearer), exact-object Omo R2 artifact capabilities and retention policy (replacing the Modal Volume), a durable dispatch outbox/reconciler beyond request-time polling, provider-rate and accepted-output benchmark evidence for arbitrary customer audio, signed QA, and explicit human promotion.

Modal’s protected endpoints and Volume are suitable for this milestone. The Worker remains the order ledger and money authority; Modal status is execution evidence, not the source of balances or tenant ownership.
