# de Mello Awake — Modal milestone scaffold

This bundle describes a scale-to-zero, CPU-only Modal workflow for a 5–20
second audio excerpt. It transcribes the audio, directs a strict 3 fps semantic
drawing schedule, generates a bounded chain of GPT Image 2 anchors, expands
authored sumi-e changes, assembles a 30 fps H.264/AAC portrait MP4, validates
the media, and commits the video and contact sheet under `runs/<run_id>/...`.

It is a private staging milestone, not a paid or public release. Its App name
is `omo-demello-awake-<release_hash_short>`; `release_hash.py` compiles the
normalized release tree and `release-manifest.json` records the twice-reproduced
digest. Deployment or QA success cannot move traffic.

## Contracts

`POST /v1/runs` and the milestone compatibility alias `POST /run` require:

- `Authorization: Bearer $API_SERVER_KEY`;
- `Idempotency-Key: <caller key>`;
- either direct input validated by `schemas/input.json`, or the future
  Worker-owned envelope validated by `schemas/private-run.json`.

Direct smoke input:

```json
{
  "audio_ref": "sample-demello-10s",
  "style": "sumi-e-awake-v3",
  "duration_bounds": {"min_seconds": 5, "max_seconds": 20}
}
```

Exactly one of `audio_url` and `audio_ref` is required. `audio_ref` is an
allowlisted server identifier, never a path. `audio_url` is HTTPS-only and is
subject to byte, redirect, DNS-rebinding, credential, loopback, private,
link-local, multicast, reserved, and unspecified-address checks.

Completed results follow `schemas/output.json`: expiring video/contact-sheet
URLs, exact run-scoped artifact keys and hashes, generated/semantic/output
frame counts, H.264/AAC media facts, physical and provider usage, guarded-cost
evidence, exact providers/models, and explicit director/image fallback use.

## Provider and runtime pins

- Modal `1.5.0`, Python 3.12, FastAPI, strict Draft 2020-12 JSON Schema,
  httpx/OpenAI, Pillow, NumPy, FFmpeg/ffprobe, and a small Go runner boundary.
- OpenAI transcription:
  `gpt-4o-mini-transcribe-2025-12-15` at
  `/v1/audio/transcriptions`.
- Preferred director: OpenCode Go `deepseek-v4-flash`; the deterministic local
  director is disclosed when used. A redaction-safe tiny probe returned HTTP
  200, model `deepseek-v4-flash`, exact output `OK`, stop finish, and usage.
- Preferred image anchors in private staging: the ChatGPT-subscription Codex
  Responses `image_generation` tool at
  `https://chatgpt.com/backend-api/codex/responses`. Chained requests include
  the last accepted parent as an input image; a rejected image never becomes a
  parent. A scoped API key can still use the pinned GPT Image 2 generation/edit
  adapter. Each image gets at most two retries.
- Procedural sumi-e fallback is release-enabled for milestone resilience only.
  A fallback result says `generation_provider=procedural-fallback` and reports
  zero OpenAI image spend; it is never described as OpenAI-generated.

The OpenAI endpoint/model declarations were checked against the official
[GPT Image 2 model page](https://developers.openai.com/api/docs/models/gpt-image-2)
and [GPT-4o mini Transcribe model page](https://developers.openai.com/api/docs/models/gpt-4o-mini-transcribe)
on 2026-08-11.

## Secrets and artifacts

The milestone Modal Secret is named `omo-demello-awake` and binds
`API_SERVER_KEY`; optional provider bindings are `OPENAI_CODEX_ACCESS_TOKEN`,
`OPENAI_CODEX_ACCOUNT_ID`, `OPENAI_CODEX_REFRESH_TOKEN`, `OPENAI_API_KEY`, and
`OPENCODE_GO_API_KEY`. Values must never appear in source, images, fixtures,
responses, or logs. Subscription token refresh is memory-only, so a controlled
external rotation owner remains required after scale-to-zero.

The tested request/auth matrix and exact secret-safe recipe are in
`research/codex-subscription-auth.md`. Subscription image output is real, but
the response has no billable USD meter and arbitrary audio transcription still
requires a valid public API credential. Those gaps keep
`paid_traffic_ready:false`.

The deployed milestone sets `DEMELLO_PROVIDER_LANE_ENABLED=0` and admits only
the bundled `sample-demello-10s` procedural lane. Non-bundled input is rejected
before download or any provider call. Enabling that flag requires a new release
with reconciled provider pricing, durable credentials, and accepted-output QA.

Milestone artifacts use the named `omo-demello-awake-artifacts` Modal Volume
and an expiring signed download route. That is not the durable paid artifact
contract. Paid traffic requires exact-object R2 upload/finalize, ownership,
checksum, encryption, quarantine, retention/deletion, and authorized-download
capabilities.

## Verification expectations

The eventual runtime/test owners should run strict schema checks, at least
three happy and six negative/failure fixtures, zero-spend invalid-input tests,
SSRF/redirect tests, provider replay/retry tests, a tiny synthetic-audio
pipeline, ffprobe/full-decode checks, cost fail-closed tests, Python import
checks, the Go build in the Modal image, and `git diff --check`.

The first real staging candidate must complete the allowlisted 10-second sample
twice, preserve measured cold/warm latency and delivered cost, and receive a
fresh visual review against `manifest/VISUAL_SPEC.md` and
`manifest/ART_PIPELINE_V3.md`. Refinement creates a new release hash.

## Paid-traffic blockers

- Modal Proxy Token plus short-lived replay-protected Worker capability;
- Worker-owned durable run state, ownership checks, signed checkpoints, and
  no buyer-visible Modal FunctionCall identity;
- approved Neon-versus-D1 ADR, transactional reservation/ledger, effect
  acknowledgement, settlement/refund, and reconciliation;
- R2 artifact plane and retention/deletion policy;
- reconciled provider rates, pre-phase hard cost debits, real accepted-output
  benchmark, signed QA, rollback drill, and separate human promotion.
