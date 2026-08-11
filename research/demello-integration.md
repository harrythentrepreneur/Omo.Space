# de Mello Awake — Omo integration contract

Date: 2026-08-11  
Workflow: `demello-awake@0.1.0`  
Style: `sumi-e-awake-v3`

## Boundary

The Cloudflare Worker remains the only buyer-facing gateway and money authority. It authenticates the tenant, resolves an immutable release, validates/canonicalizes input, quotes, reserves credits, writes the durable run/outbox record, and only then dispatches to the release-specific Modal app. Modal owns active execution and media QA; it does not own balances, tenant authorization, release selection, or settlement.

The milestone endpoint is private bearer-authenticated transport. It uses a Modal Volume plus five-minute signed artifact links because Proxy Token and exact-object R2 capabilities are not yet wired. Its responses explicitly report `paid_traffic_ready: false`; do not route paid buyer traffic to it yet.

## Deployed milestone release

- App: `omo-demello-awake-aa5c370cafa9`
- Base URL: `https://harrythentrepreneur--omo-demello-awake-aa5c370cafa9-api.modal.run`
- Submit: `POST /v1/runs` (alias: `POST /run`)
- Status: `GET /v1/runs/{run_id}`
- Authentication: `Authorization: Bearer $API_SERVER_KEY`
- Idempotency: required `Idempotency-Key`, 8–128 characters
- Result transport: short-lived signed `video_url` and `contact_sheet_url`

## Direct private smoke contract

Exactly one of `audio_ref` and `audio_url` is accepted. The only bundled reference is `sample-demello-10s`; `audio_url` must be HTTPS and passes DNS/IP/redirect/byte-limit checks. Bounds satisfy `5 <= min_seconds <= max_seconds <= 20`.

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
export DEMELLO_ENDPOINT='https://harrythentrepreneur--omo-demello-awake-aa5c370cafa9-api.modal.run'

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

## Worker dispatch envelope

After quote and reservation, the Worker dispatches the canonical, server-owned envelope below. `request_hash` is the raw lowercase SHA-256 of canonical JSON input; `release_hash` includes the `sha256:` prefix. The endpoint recomputes the input hash and rejects mismatches.

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
4. Create a ten-minute quote at 10 cents and atomically create/replay the run, reserve credits, append the ledger event, and write the dispatch outbox row.
5. Dispatch the signed envelope to the pinned Modal base URL. Same tenant/key/hash replays; same key with a different hash is `409`.
6. Poll or consume signed checkpoints; on success, verify exact R2 artifacts and settle actual charge once. On terminal failure, release/refund once. Reconcile stale runs and paid effects.

No call that can incur Modal/provider cost may precede reservation.

## Guarded price

Successful delivered compute samples were `$0.00214633` (round 1, 122.368 s) and `$0.00111446` (refined deterministic lane, 63.538 s). With the small sample, empirical p95 is the maximum: `$0.00214633`. A 15% media tail is `$0.00246828`; the conservative static bound is `$0.003`.

```text
C_guard = max(0.003, 0.00214633, 0.00246828) = 0.003
price = ceil_to_cent(max(0.10, 0.003 / (1 - 0.80))) = $0.10
```

The 10-cent quote is only for the measured bundled/deterministic lane. Arbitrary customer audio currently requires OpenAI transcription and image credentials; it must be re-benchmarked with valid provider billing and accepted-output yield before enabling paid quotes.

## Exact work remaining in `site/deploy/worker.js` and MCP

No `site/` file was changed by this deployment. The separate Worker/MCP integration must still:

- add a server-owned catalog release row mapping `demello-awake` to the immutable Modal release, schemas, 10-cent policy, and $0.003 ceiling;
- expose buyer-facing `POST /v1/runs` and owner-only `GET /v1/runs/{id}` instead of dispatching paid work through the current demo `/api/run` path;
- add D1 quotes, runs, reservations, append-only ledger effects, dispatch outbox, events, settlement/release, replay conflict, and reconciliation;
- replace `API_SERVER_KEY`-only ingress with Modal Proxy Token plus a short-lived signed Worker capability;
- replace Modal Volume delivery with exact run-scoped R2 input/output capabilities, checksums, retention, and authorized downloads;
- pin provider-rate evidence and collect p50/p95 delivered-cost/latency history before broad traffic;
- keep MCP a thin client of the public Worker contract: submit, poll, and return the authorized Omo artifact URL; MCP must not call the private Modal URL or own money/state.

Modal’s documented mechanisms support protected web endpoints, persisted Volumes, deployed-function invocation, and generated webhook URLs, but the production boundary above follows Omo’s stricter Worker/D1/R2 contract rather than treating Modal state as the order ledger.
