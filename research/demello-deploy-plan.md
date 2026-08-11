# de Mello Awake on Modal — deployment plan

Date: 2026-08-11  
Status: milestone-1 implementation plan; not a production traffic promotion

## Outcome and architectural boundary

Build one immutable, scale-to-zero Modal App named `omo-demello-awake-<release_hash>`. It accepts a private run envelope for a short audio input, transcribes it, directs a compact semantic drawing schedule, generates chained sumi-e keyframes, renders 3 fps authored drawing changes into a 30 fps H.264/AAC portrait MP4, validates it, persists the artifact, and returns typed usage/cost evidence.

This App is the execution plane, not the buyer-facing money or identity authority. `research/modal-optimization/round-5.md` remains authoritative: the Cloudflare Worker will authenticate the buyer, resolve the immutable release, canonicalize and hash input, quote, reserve funds, dispatch privately, checkpoint, settle, and expose the durable public `POST /v1/runs` / `GET /v1/runs/{run_id}` resources. The milestone App exposes a compatible private submit/status surface so it can be exercised before that Worker/MCP wiring lands.

The mega-agent blueprint is planned rather than implemented. This bundle follows its generated-container shape and records provenance, capability, release, schema, fixture, and QA assets so a future deterministic compiler can adopt it. It does not claim autopilot promotion, `PLATFORM_READY`, R2, Neon/D1, or 30 clean days.

## Repository layout

```text
containers/demello-awake/
  container.yaml
  modal_app.py
  workflow.py
  image_gen.py
  media.py
  pricing.py
  requirements.txt
  README.md
  cmd/runner/{go.mod,main.go}
  manifest/{SPEC.md,ART_PIPELINE_V3.md,VISUAL_SPEC.md,taste_frames_v3_vision_qa.md}
  prompts/{director.txt,frame.txt}
  schemas/{input.json,output.json,private-run.json}
  assets/sample-demello-10s.m4a
  tests/{cases.json,test_contract.py,test_pipeline.py}
  qa/.gitkeep
```

The final bundle will also include small compiler-shaped metadata (`provenance.json`, `capability-manifest.json`, and `release-manifest.json`) if it materially improves reproducibility without inventing a repository-wide compiler contract.

## Source reuse and rewrites

Copy verbatim as design evidence:

- `manifest/SPEC.md`
- `manifest/ART_PIPELINE_V3.md`
- `manifest/VISUAL_SPEC.md`
- `manifest/taste_frames_v3_vision_qa.md`
- one clipped 10–20 second real de Mello sample for a closed, reproducible `audio_ref` smoke test

Port, rather than copy blindly:

- the `qa_video.py` ffprobe checks: duration, H.264, AAC, 1080×1920, 30 fps, non-empty decode;
- the `normalize_white.py` invariants: pure/near-white field, low chroma, sparse dark-line mask;
- the V3 scheduling rules: three monotonic semantic cells per second, protected negative space, fixed opening/pivots/closing, and 0.20 second blend plus landing hold;
- the useful, clipping-safe parts of `animate_motion.py`, but with V3’s much smaller verb-driven camera budget instead of the older generic 2–14% presets;
- the pairwise, final-pass H.264/AAC and `+faststart` principles from the assemblers.

Rewrite:

- `transcribe.py`, because it hardcodes `/Users/yifan/demello`, scans a whole library, and loads a large local faster-whisper model. The hosted short-run adapter will call an OpenAI transcription model, with deterministic no-network fixtures in tests.
- `gen_frame.py` / `gen_v3_frames.py`, because they call a local Hermes/Codex ChatGPT-subscription provider and hardcode local paths. `image_gen.py` will call the real OpenAI Images endpoints with the V3 prompt language and sequential accepted-parent chaining.
- the story/span director into one strict, bounded OpenAI-compatible JSON step. OpenCode Go + `deepseek-v4-flash` is the preferred planner when `OPENCODE_GO_API_KEY` is present; a deterministic transcript-derived plan is the fail-closed local/test fallback. OpenAI is reserved for transcription and image generation.
- all orchestration and file handling into request-scoped work directories with no source-tree writes.

No 2.9 GB source tree, full podcast library, existing outputs, logs, caches, or absolute host paths enter the image.

## Request and result contracts

The workflow input requires exactly one of `audio_url` or `audio_ref`, plus `style` and `duration_bounds`:

```json
{
  "audio_ref": "sample-demello-10s",
  "style": "sumi-e-awake-v3",
  "duration_bounds": {"min_seconds": 5, "max_seconds": 20}
}
```

`audio_url` is HTTPS-only, size-bounded, redirect-bounded, and rejects loopback, private, link-local, multicast, and reserved targets. `audio_ref` is an allowlisted server-owned identifier, never a filesystem path. Durations over the accepted maximum are trimmed; durations below the minimum fail before image spend.

Private submit:

- `POST /v1/runs` and compatibility alias `POST /run`;
- `Authorization: Bearer $API_SERVER_KEY` for this milestone;
- `Idempotency-Key` required;
- accepts either the direct input above for smoke testing or the future Worker envelope with server-owned `run_id`, `release_hash`, `request_hash`, validated input, and `max_cost_usd`;
- returns `202` with `run_id` and an internal status path; direct FunctionCall identifiers are only milestone transport evidence and must not cross the future public Worker boundary.

The completed status result contains at minimum:

```json
{
  "run_id": "...",
  "status": "completed",
  "video_url": "https://...",
  "contact_sheet_url": "https://...",
  "frames_used": {"generated": 4, "semantic": 36, "output": 360},
  "cost": {"measured_usd": 0.0, "guarded_price_usd": 0.10},
  "media": {"duration_seconds": 12.0, "video_codec": "h264", "audio_codec": "aac", "width": 1080, "height": 1920, "fps": 30}
}
```

Artifacts use exact `runs/<run_id>/...` keys. The target architecture is private R2 with exact-object, method-limited capabilities. R2 credentials are absent today, so milestone 1 uses the named `omo-demello-awake-artifacts` Modal Volume and a separate signed, expiring download route. That substitution is not sufficient for public paid traffic because Modal storage is not the durable Omo artifact plane described by Round 5.

## Pipeline DAG

1. `acquire-audio`: resolve the allowlisted ref or safely download HTTPS; probe, normalize to mono AAC/WAV, and enforce the duration bound.
2. `transcribe`: obtain English text through the pinned OpenAI transcription snapshot; no large model download on cold start. The hosted milestone uses the provider JSON transcript and derives its short semantic timing from the probed clip duration.
3. `direct-story`: produce a strict semantic schedule. One primary verb owns each second. Compile three monotonic micro-deltas per second.
4. `generate-keyframes`: use the pinned `gpt-image-2-2026-04-21` Image API snapshot. Generate F000 text-to-image; subsequent anchors use the last accepted image as an edit source. Prompts carry semantic meaning, one delta, protected anchors, white negative space, and the exact V3 style lock. Validate decode, portrait geometry, white-field ratio, chroma, and dark-line sparsity. Retry a provider failure at most twice without promoting a rejected parent.
5. `expand-semantic-frames`: derive exactly three authored cells per second from the accepted anchors. Image generation is intentionally lower than 3 paid calls/second for the first offering; the 3 fps cells preserve/land each generated semantic change and add bounded monotonic ink deltas. Report paid generated images separately from semantic cells.
6. `assemble`: use FFmpeg linear difference-preserving blends for roughly six of each ten 30 fps frames and a four-frame landing/hold. Keep opening, pivots, and closing fixed; any camera follow is at or below the V3 0.15–0.20% budget. Mux source audio, H.264 `yuv420p`, AAC, 1080×1920, 30 fps, `+faststart`.
7. `qa-and-persist`: ffprobe and decode; validate duration, streams, dimensions, frame rate, sparse monochrome style, checksum, byte size, and contact sheet; commit to the exact run path only after checks pass.

If the OpenAI image request is unavailable after bounded retries, the run may use the explicit procedural sumi-e generator only when fallback is enabled by the immutable release. The result sets `generation_provider=procedural-fallback` and accounts zero image-provider spend; documentation and QA must never describe it as an OpenAI-generated result.

## Go role

Go is useful at the deterministic boundary, not inside image/transcription clients or Pillow/FFmpeg media code. A small dependency-free Go binary is the container entry/adapter layer: it reads the immutable request JSON, rejects ambiguous invocation arguments, launches the Python workflow as a bounded subprocess, propagates cancellation/signals, and requires one typed result JSON. Modal’s Python SDK and FastAPI remain the thin ingress because Modal’s supported App/decorator surface is Python. This gives the founder a real Go-controlled execution boundary without rewriting proven Python media work or pretending Modal has a Go-native web deployment API.

The local host currently has no Go toolchain. The Modal image installs Go only in the image build stage and compiles the static runner; the deployed build is the authoritative Go compile gate. Python tests exercise the same runner protocol with a stub executable locally.

## Modal image and runtime

- Debian slim, Python 3.12, pinned Modal/FastAPI/httpx/jsonschema/Pillow/numpy dependencies.
- `apt_install`: FFmpeg and Go toolchain; compile `cmd/runner` during image build.
- CPU-only: 1 CPU, 2 GiB RAM, 20 minute hard timeout, `min_containers=0`, bounded max containers, measured scaledown window.
- Named secret `omo-demello-awake` containing only references injected at runtime: `OPENAI_API_KEY`, `OPENCODE_GO_API_KEY`, and `API_SERVER_KEY`. No values in source, image layers, responses, or logs.
- Declared provider egress: `api.openai.com`, `opencode.ai`; buyer audio hosts are additionally subject to runtime SSRF validation until the Worker replaces URLs with exact R2 refs.
- Named Volume `omo-demello-awake-artifacts`, mounted write-once/read-many for this milestone.

## Release and test loop

Each deploy candidate receives a source-derived short hash and App identity `omo-demello-awake-<hash>`. Refinement creates a new candidate name; it does not silently promote traffic. The final report records the exact deployed release and previous candidates.

Local gates:

- Draft 2020-12 schemas and container spec checks;
- at least three happy input fixtures and six negative/failure cases;
- mocked provider contract tests with zero paid calls;
- tiny synthetic audio end-to-end pipeline test;
- Python compile/import checks, Go compile in Modal build, and `git diff --check`;
- unchanged existing suites: `node site/deploy/test-balance.mjs`, `node site/deploy/test-router.mjs`, `node site/deploy/test-cost.mjs`.

Deployed loop, at least twice:

1. deploy immutable candidate;
2. submit the real 10–20 second `audio_ref` sample and poll to completion;
3. download MP4 and contact sheet; run local ffprobe/decode and record cold/warm latency and usage;
4. have a fresh GPT-5.6 Sol/XHigh reviewer inspect extracted frames against `VISUAL_SPEC.md` and the V3 QA rubric;
5. change only evidence-backed prompt, motion, frame-budget, or QA parameters; repeat under a new release hash.

Acceptance requires a real playable H.264/AAC 1080×1920 30 fps output whose duration fits the request, generated sparse black-on-white drawing frames, motivated motion/semantic change visible in the contact sheet, measured delivered cost/latency, and a clean test gate.

## Cost and pricing

Record provider usage returned by APIs, image count/quality/size, transcription/director usage, wall and active phase times, retries, Modal CPU/RAM estimate, and artifact bytes. Two runs are evidence, not a statistically mature p95; use the maximum successful delivered cost as the provisional p95 and state the sample size.

Per Round 5:

```text
C_guard = max(C_static, C_success_p95,
              max(C_delivered_7d, C_delivered_30d) * (1 + tail_reserve))
price = ceil_to_cent(max($0.10, C_guard / (1 - 0.80)))
```

Use a 15% remote-media tail reserve until 30 clean days. Unknown price units fail closed. The response’s guarded price is evidence for a server-authored quote; the Modal App never selects, reserves, debits, or settles a buyer balance.

## Known milestone gaps before paid Worker traffic

- replace bearer-only Modal auth with a Modal Proxy Token plus a short-lived, replay-protected Worker capability;
- replace FunctionCall/milestone status transport with Worker-owned durable run state and non-enumerating tenant authorization;
- replace Modal Volume delivery with Omo-owned R2 exact-object upload/finalize and authorized download;
- complete the chosen Neon-versus-D1 ADR and ledger/checkpoint implementation;
- add durable idempotency/effect acknowledgements, quote reservation, max-cost enforcement, settlement/refund, reconciliation, retention/deletion, rate/abuse limits, and kill switch;
- have the future deterministic mega-agent compiler reproduce the bundle twice byte-identically, produce lock/SBOM/signatures, and pass `PLATFORM_READY`; separate human authorization must promote traffic.
