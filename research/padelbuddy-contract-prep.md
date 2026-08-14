# PadelBuddy contract preparation

## What it is

PadelBuddy is an iPhone-first AI padel match-video analysis and highlight product, not a court-booking, player-community, or training-log app. A user selects or uploads match footage; the backend performs a two-stage Gemini analysis, detects rallies and shots, generates categorized and custom highlight videos plus thumbnails, and exposes private match results and opt-in public share pages. The product has device/user ownership, background progress polling, cloud media storage, daily video/cost quotas, retention, and premium subscription state.

Evidence inspected read-only: the profile's short `SOUL.md` and `memories/MEMORY.md`, its project-specific `padelbuddy-local-stack/SKILL.md`, and small README/runbook/config files in `/Users/yifan/padelbuddyai`. The separate `/Users/yifan/padelbuddy` directory appears to be only a placeholder README. No `~/Projects/*padel*` match was present. I intentionally skipped `.env`, `auth.json`, state/session databases, request dumps, logs, blocked scripts, and all other credential- or private-content-bearing files.

## Likely `SKILL.md` contract shape

The skill should describe one bounded job: turn one authorized padel match video into an owned match-analysis record and a set of playable highlight artifacts. It should declare:

- Inputs: an owner/run-scoped video reference; accepted containers/codecs; byte and duration limits; optional title/player selection and custom-highlight prompt; content/privacy classification and retention choice.
- Domain state: user/device owner, upload/session ID, match ID, status and progress, source checksum for deduplication, rallies/shots and category counts, generated artifact references, share-enabled/token state, subscription entitlement, usage/cost ledger, processing version, and failure/retry state.
- Steps: authorize and quota-check; create bounded multipart upload; verify media; normalize/transcode with FFmpeg; invoke the two-stage video-semantic pipeline; validate timecodes/categories; cut and thumbnail highlights; persist immutable media; update status; optionally create a revocable public share reference; notify in-app/local state when complete.
- Outputs: a typed match-analysis JSON record, optimized match video, category/custom highlight videos, thumbnails, diagnostics/cost metadata, and an optional share URL. It should never promise tactical truth, player identity, exact scoring, 4K output, or unlimited processing unless the acceptance evidence and quota contract support those claims.
- Failure and policy: fail closed on ownership, MIME/checksum/codec, quota/cost, empty or implausible detections, invalid time ranges, storage/persistence, and subscription ambiguity. Raw videos and prompts are untrusted private input and must not enter logs. Sharing, notifications, payment changes, production deployment, and external messages require explicit contract gates and appropriate user authorization.
- Acceptance tests: common iPhone and web video codecs; long uploads and resume; no-rally footage; invalid/overlapping timecodes; deterministic normalization; generated video/audio playback; every artifact URL authorized and range-readable; cross-user denial; duplicate upload; quota/cost cutoff; subscription webhook idempotency; retention cleanup; share enable/revoke; and provider failure/retry accounting.

Browser actions should be reserved for user-visible web/share-page and App Store/TestFlight verification. Core processing should use typed backend/storage/provider adapters, not browser automation. No booking or calendar API belongs in the contract based on the inspected evidence.

## Capability resolution

Capabilities that appear reusable or already represented in Omo's broader architecture:

- LLM/provider invocation and structured-output repair for bounded semantic results, although PadelBuddy specifically needs multimodal long-video support rather than text-only LLM execution.
- Semantic normalizers/validators for provider output, timecodes, categories, and media references.
- Private artifact ingestion/reader plus an owner-scoped artifact store; the current resolver document treats these as dependencies, not proven available implementations.
- Static PDF is not part of the core product. It is optional only if a future match report is explicitly declared. Likewise, `chart_generation` is optional for a declared metrics visualization, not implied by the current highlight workflow.
- Browser/UI verification can cover share pages and launch checks, but should not own domain state or processing.

Missing or product-critical shared capabilities:

- Bounded resumable/multipart video ingest with checksum, codec/container probing, private scratch, retention, and deduplication.
- FFmpeg media normalization, clip extraction, audio compatibility, thumbnails, and playable-output validation.
- Long-video multimodal model adapter with staged analysis, timeouts, retries, cost accounting, and schema/semantic gates.
- Durable domain-state store for upload, match, processing progress, artifacts, share state, usage, and idempotency, with tenant isolation.
- Object-storage adapter supporting private worker reads, authorized/public delivery policy, range requests, checksums, lifecycle cleanup, and stable URLs.
- Async job dispatch/progress reconciliation across stateless workers.
- Subscription-entitlement and webhook-idempotency adapter plus quota/cost-policy enforcement. Payments are an external side effect and should remain separately gated.
- Optional notification adapter. The inspected launch contract says push is not part of the current release, so notification resolution must remain absent unless a later reviewed contract declares it.

## Recommended one-shot build path

1. Normalize a narrow `padel_match_highlights/v1` contract with exact media bounds, artifacts, ownership, quotas, retention, and acceptance fixtures. Keep booking, community, training analytics, and push out until separately evidenced.
2. Resolve the private input/artifact plane and durable domain-state/idempotency capabilities first. A build without those must return a typed blocker rather than inline or leak media.
3. Resolve media probe/normalize, staged multimodal analysis, semantic validation, clip/thumbnail rendering, and async progress as composable shared capabilities. Pin provider/model and FFmpeg behavior in evidence.
4. Generate the backend workflow and mobile/web bindings from that contract, then run cheap local fixtures before a small real-provider acceptance set. Verify every emitted media artifact by decode/probe and authorized range-read.
5. Add subscription/quota enforcement only after webhook idempotency and entitlement reconciliation pass. Add optional sharing as an explicit user action; keep notification, publication, spending, production deployment, DNS, and App Store submission behind separate approvals.

This can be a one-shot generated product only if “one shot” means complete resolution or exact typed blockers. The current profile documents a working product and production architecture, but it does not turn its project-specific operational runbook into reusable registry capabilities by itself.
