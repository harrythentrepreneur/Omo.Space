# de Mello Awake — Modal deployment and refinement record

Date: 2026-08-11  
Repository: `/Users/yifan/marketplace`  
Source evidence: `/Users/yifan/demello`  
Plan: `research/demello-deploy-plan.md`

## Outcome

The audio-to-drawing-video workflow is implemented as a release-hashed Modal app with a private asynchronous `POST /v1/runs` boundary, Go subprocess controller, Python media workflow, request-scoped work directories, strict media QA, a Modal Volume artifact milestone, and expiring signed result URLs.

Final release and endpoint will be recorded after the last visual candidate is frozen:

- Release: `sha256:aa5c370cafa96520c47f35b568b821805605796f8dfcc542516b94338d9c8123`
- Modal app: `omo-demello-awake-aa5c370cafa9`
- Endpoint: `https://harrythentrepreneur--omo-demello-awake-aa5c370cafa9-api.modal.run`
- Production traffic: **disabled** (`paid_traffic_ready: false`)

The working provider adapters target OpenAI transcription, optional OpenCode Go/DeepSeek directing, and OpenAI GPT Image generation/edit. The configured OpenAI credential returned `401 invalid_api_key` on a synthetic, non-private probe, so no private source was sent to it. The tested lane uses the bundled source transcript, deterministic director, and an explicitly disclosed procedural sumi-e-ish renderer. It is not evidence of OpenAI-generated art.

## Acceptance fixture and reproducibility

`audio_ref=sample-demello-10s` is a real 10-second excerpt copied from the de Mello source workflow. The runtime fixture is normalized mono 48 kHz AAC/M4A; the original MP3 is retained beside it as provenance. Its bundled transcript is sourced from the original V3 story evidence:

> puts it into his mouth and tastes it, and the story goes, and it tasted so sweet

The test request fixes style `sumi-e-awake-v3`, minimum 5 seconds, maximum 10 seconds. Procedural output is deterministic; the two latest successful remote renders produced identical video and contact-sheet hashes before the final visual refinement.

## Deployment candidates

| Candidate | Endpoint suffix | Result | Evidence/refinement |
|---|---|---|---|
| `7bcc11ab4ffc…` | `7bcc11ab4ffc` | ingress failed | Modal hydrates the entry module at `/root/modal_app.py`; added `/root/demello_awake` to the import path. |
| `d6b080e31ba5…` | `d6b080e31ba5` | run failed | OpenAI transcription returned a redacted provider failure. Added an allowlisted bundled transcript for the real fixture and kept arbitrary audio fail-closed. |
| `a0ec6ae89db6…` | `a0ec6ae89db6` | completed | First full visual loop; technically valid but creative QA failed. |
| `5f9b70d27796…` | `5f9b70d27796` | QA failed | First 30-state story-specific candidate exposed a Modal-only audio parity failure. |
| `7dbf4a06d71b…` | `7dbf4a06d71b` | QA failed | Added allowlisted diagnostic fields; isolated `audio_duration`. |
| `9ff55a37d634…` | `9ff55a37d634` | QA failed | Switched from stream metadata to packet-timeline measurement; confirmed a genuine short packet end. |
| `2194c2439831…` | `2194c2439831` | QA failed | Normalized the real fixture to AAC/M4A; short end persisted in final mux. |
| `09f7f99248e6…` | `09f7f99248e6` | QA failed | Safe diagnostic measured `7.978` seconds observed versus `10.000` expected. |
| `8259f9e88407…` | `8259f9e88407` | QA failed | Reset audio PTS before trim; FFmpeg 5.1 still exposed the shortened stream. |
| `66f9a29650cf…` | `66f9a29650cf` | completed | Mixed narration over an explicit silent ten-second clock; strict audio parity passed. |
| `1170fd01755f…` | `1170fd01755f` | completed | Standalone output/internal schemas were expanded and regression-tested for full 3 fps (30/60 generated states). |
| `aa5c370cafa9…` | `aa5c370cafa9` | completed | Final fixed-crop brush refinement: broken taste ripple, receding predicament, dot-only ending, and runtime-aligned private/output schemas. |

No failed candidate published a video as success. All failure responses used fixed error codes; provider bodies, paths, keys, and arbitrary exception text were not persisted. Diagnostic refinement stored only allowlisted phase/check names and numeric expected/observed durations.

## Visual loop 1 — deployed, reviewed, failed, refined

Release `a0ec6ae89db6…`, run `run_58b529b5f97c045165d7809124e7fa0d`:

- workflow latency: `122.367659 s`;
- measured delivered Modal compute: `$0.00214633`;
- media: 10.000 s, H.264/AAC, 1080×1920, 30 fps;
- counts: 4 generated anchors, 30 semantic blends, 300 output frames;
- video: 273,142 bytes, SHA-256 `062e0adad6e591e4de7973cb86c29a36ff03429ecc52219fd20435a5c20e75cf`;
- contact sheet: 69,982 bytes, SHA-256 `2362fd…`;
- defect: downloaded AAC ended at 7.978 s even though the video ended at 10.000 s.

Fresh XHigh review verdict: **FAIL**. Mechanical white/monochrome checks passed, but the output was a generic eye, horizon, and stick figure. None of the tiger/branch/two-mice/hanging-man/berry/taste/sweetness motifs appeared. Six of 29 adjacent semantic comparisons were effectively unchanged and the sparse-anchor blends created gray ghost contours.

Refinement:

- replaced generic eye imagery with the source story’s predicament and taste beats;
- generated one deterministic drawing for every 3 fps semantic cell instead of blending four sparse anchors into 30 nominal states;
- added branch, tiger, exactly two mice, hanging man, moving leafed berry, mouth contact/taste ripple, and sweetness dot;
- thresholded provider images to a white/black field;
- made audio packet parity a hard QA condition.

## Visual loop 2 — deployed, reviewed, qualified pass, refined again

Release `1170fd01755f…`, run `run_bc3b625eb26e5636f07c75092503ad54`:

- workflow latency: `63.538157 s`;
- phase latency: acquire 1.098349, direct 0.000349, generate 4.178615, semantic expansion 10.986071, assembly 42.304342, QA 4.949060 seconds;
- measured delivered Modal compute: `$0.00111446`;
- counts: 30 generated, 30 semantic, 300 output frames;
- video: 416,251 bytes, SHA-256 `4c40586153452aa6ac28180f907949d6904404096042ed4a8d81b813c4837611`;
- contact sheet: SHA-256 `d2516ad67ab5847931ca63f1728155639ffd149b568c28284e6c5f677dfc1baf`;
- ffprobe: video 10.000 s, audio 9.962 s, H.264/yuv420p + AAC, 1080×1920, 30 fps, 300 frames;
- QA: duration, packet-audio parity, frame count, resolution, fps, codecs, faststart, full decode, nonempty output, and five visual samples all passed.

Fresh XHigh review verdict: **qualified PASS for the narrow “generated drawing frames with motion” milestone; FAIL against the full aspirational visual spec.** It confirmed 30 distinct semantic source frames, 290 unique decoded output frames, story-directed berry/taste/sweetness motion, and no long holds. It also found uniform vector/stick styling, weak tiger/mice readability, two abrupt wide/close cuts, and gray doubled contours during those cuts.

Refinement:

- eliminated the wide/close/wide cuts and retained one fixed composition for all 30 semantic frames;
- enlarged the tiger face, exactly two inward-facing mice, hanging figure, and leafed berry;
- changed uniform contours to deterministic tapered/irregular brush strokes;
- kept all motion inside the established drawing: berry rises, taste ripple expands/contracts, sweetness dot travels and settles;
- aligned standalone private-run/output schemas with the actual runtime envelope and completed status response.

## Visual loop 3 — final evidence

Release `aa5c370cafa9…`, run `run_d13f72368c7ca652db0e6c165bfe8b3b`:

- stable endpoint: `https://harrythentrepreneur--omo-demello-awake-aa5c370cafa9-api.modal.run`;
- workflow latency: `57.418150 s`;
- phase latency: acquire 0.912240, direct 0.000178, generate 3.931365, semantic expansion 9.932938, assembly 37.740537, QA 4.881488 seconds;
- measured delivered Modal compute: `$0.00100711`;
- counts: 30 generated, 30 semantic, 300 output frames;
- ffprobe: video 10.000 s, H.264/yuv420p, 1080×1920, 30 fps, 300 frames; audio AAC mono 48 kHz, 9.962 s;
- video: 328,613 bytes, SHA-256 `ac4bd5739d903e4b71fc9a233034bb8cbe37a590a0e95e41b9f25e8efc95cd3b`;
- contact sheet: SHA-256 `81e5d7033e673eb31de50876f1c9f79fef3341e7d664facca8f121a14d6561d6`;
- runtime QA: all duration/audio parity/frame count/resolution/fps/codec/faststart/full-decode/nonempty/visual-sample checks passed;
- fresh XHigh visual verdict: **PASS for the deployment acceptance gate and reasonable authorized procedural sumi-e-ish fallback**. It confirmed exactly 30 authored states, 287 non-duplicate adjacent transitions, a fixed congruent crop, all required story motifs, a progressive recession, and a dot-only white field through F026–F029. It found no unwanted ghost characters, crop jumps, generic camera movement, text, watermark, color, gradients, gray fills, extra figures/fruit/dots/ripples, or other forbidden artifacts. The separate aspirational gap is that the frames are deterministic procedural line art, not ChatGPT/OpenAI sequential image-to-image generation, and remain cleaner/more iconic than organic brush-textured sumi-e.

## Media and artifact verification

The final acceptance artifact must satisfy all of the following, and its evidence is recorded above or in the final loop:

```text
video codec       h264
pixel format      yuv420p
canvas            1080x1920
rate              30/1
video duration    10.000000 s
video frames      300
audio codec       aac
audio parity      within 0.100 s of video
faststart         true (moov before mdat)
full decode       ffmpeg -f null succeeds
```

Signed Modal artifact URLs expire after five minutes. The durable milestone copy is in `omo-demello-awake-artifacts/runs/<run_id>/`; this Volume is deliberately not presented as the final Omo R2 artifact plane.

## Cost and guarded price

Successful delivered samples used for this milestone:

| Run | Workflow seconds | Delivered cost |
|---|---:|---:|
| visual loop 1 | 122.367659 | `$0.00214633` |
| visual loop 2 | 63.538157 | `$0.00111446` |
| visual loop 3 | 57.418150 | `$0.00100711` |

For two samples, empirical p95 is the maximum: `$0.00214633`. The remote-media tail reserve is 15%, giving `$0.00246828`. The release keeps a conservative `$0.003` static bound.

```text
C_guard = max(C_static, C_success_p95, C_delivered_tail)
        = max(0.003, 0.00214633, 0.00246828)
        = 0.003

buyer_price = ceil_to_cent(max(0.10, 0.003 / (1 - 0.80)))
            = $0.10
```

This price applies only to the measured deterministic fixture lane. Provider-backed arbitrary audio has not been priced because the supplied OpenAI credential is invalid and accepted-output yield is unknown.

## Acceptance gate

| Gate | Status | Evidence |
|---|---|---|
| Stable Modal function | PASS | `omo-demello-awake-aa5c370cafa9`; endpoint recorded above. |
| Real audio returns playable MP4 | PASS | Real de Mello fixture; ffprobe/full decode/strict runtime QA evidence above. |
| Drawing frames with motivated motion | PASS | Fresh XHigh review of the downloaded final artifact confirmed 30 story-authored 3 fps states, 287 moving transitions, fixed crop, required motifs, recession, and dot-only ending. |
| Measured cost + guarded price | PASS | Delivered samples, p95/tail/static guard, and 10-cent result above. |
| Curl + integration contract | PASS | `research/demello-integration.md`. |
| Container syntax/contracts + diff check | PASS | 26 pytest checks, all JSON Schemas valid, Python compile clean, `node --check` clean, `git diff --check` clean; normalized tree hash reproduces `aa5c370…`. |
| Existing site/deploy suites | PASS | `test-balance` 22/22, `test-router` 49/49, `test-cost` 11/11; tests were read-only and no `site/` file changed. |

## Honest limitations and production blockers

- The accepted fixture lane is a disclosed procedural fallback, not OpenAI/ChatGPT-generated art. Arbitrary audio currently fails closed at OpenAI transcription until a valid project key is installed and tested.
- The full OpenAI path is implemented against `gpt-4o-mini-transcribe-2025-12-15` and `gpt-image-2-2026-04-21`, with sequential image edits, but has not produced a successful artifact in this environment.
- Private bearer auth and Modal Volume are milestone substitutes. Proxy Token + signed Worker capability, D1 business state, and R2 exact-object delivery remain blockers for paid traffic.
- The Go binary is the bounded API/subprocess control layer; Python remains the appropriate media/provider orchestration layer. FFmpeg remains the native rendering engine.
- The mega-agent/autopilot compiler is still planned. This release follows its `containers/omo-<slug>/` scaffold shape and immutable release naming, but it was manually compiled, reviewed, and deployed; it was not auto-promoted.
