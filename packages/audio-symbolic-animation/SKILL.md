---
name: audio-symbolic-animation
description: "Turn an audio artifact into a portrait symbolic animation with a strictly sequential frame chain."
version: 1.0.0
metadata:
  bench:
    id: audio-symbolic-animation
    input_schema:
      audio_ref: string
      duration_seconds: number
    output_schema:
      video: string
      manifest: string
    runtime:
      class: media-sequential
      adapter: fixture-media-sequential-v1
      provider: provider-neutral
      operation: audio_symbolic_animation
      network: none
      generation_fps: 1
      checkpoint_frames: 6
      portrait_width: 360
      portrait_height: 640
      retry_attempts: 3
      retry_backoff_seconds: 0.01
---
# Audio → Symbolic Animation Video

Turn an audio artifact into a vertical 9:16 symbolic line-art animation, one generated frame per second, with the original audio preserved when an approved assembly path is available.

## Validated mechanics (non-negotiable)

- The recurring symbol is a mechanical state machine: countable, visible and monotonic. Never use adjective-only deltas and never resurrect a completed state.
- Keep the anchor and world geometry stable. Every frame has one visible micro-event and a verb.
- Build word-timestamp transcription, a monotonic symbol chain, and a deterministic one-frame-per-second brief.
- Generate F000 first and every later frame from the immediately preceding accepted frame. Never parallelize frame generation.
- Require portrait output (`width < height`); reject and retry landscape output.
- Retry sequentially with bounded escalating backoff. Automated fixtures use injected short/no-op sleep; production policy may use patient delays.
- Checkpoint accepted frames and support deterministic resume. For long work, preview the first checkpoint before continuing.
- Assemble locked-camera H.264/AAC portrait video without zoompan. Validate dimensions, codecs and duration against audio within ±0.2 seconds.
- Progress and artifacts must use the canonical public contract; never expose prompts, provider IDs, credentials or internal logs.

## Provider and privacy boundary

The generated package is a fixture-backed orchestration proof. It does not use browser sessions, personal OAuth, private chats or secret values. Production frame generation is blocked until an approved server-side provider adapter is configured and verified. Missing production dependencies return a machine-readable blocked result rather than fabricated media.
