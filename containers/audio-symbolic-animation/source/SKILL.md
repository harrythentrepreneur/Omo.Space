---
name: audio-symbolic-animation
description: "Use when making a symbolic animation video from any audio."
metadata:
  version: "1.0"
  date: "2026-08-12"
---

# Audio → Symbolic Animation Video

Turn ANY audio (speech, story, teaching, poem, podcast excerpt) into a vertical
9:16 symbolic line-art animation video — one generated frame per second,
word-synced shot structure, quiet locked camera, original audio preserved.

This is the generalized version of the validated de Mello pipeline
(see ~/.hermes/skills/media/demello-video-pipeline/ — the reference
implementation; ~/demello/scripts/ holds working scripts you can copy).

## The ONE principle that makes or breaks the video

The through-line symbol must be a MECHANICAL STATE MACHINE, not an adjective.

- WORKS (validated: "Drop It", user: "I love it"): countable, embodied micro-
  steps the image model can hold frame-to-frame — threads 6→5→…→0, a hand
  opening, a serpent arriving ONCE, cords snapping. Every delta is a concrete
  visible event.
- FAILS (validated: "A New Way", user: "started great then got random"): scene-
  level abstractions — "the landscape simplifies", "the clutter recedes",
  "get ready for a surprise". The model re-decides what the adjective means
  every frame → elements appear and vanish randomly.

Rules: (a) one recurring symbol carries the argument; (b) its state changes are
countable and monotonic (never resurrect); (c) the anchor (character/object/
scene core) stays IDENTICAL from frame 1; (d) every per-frame delta is a
visible micro-event, never a mood word; (e) if meaning needs the SAME actor
later → strict identity locks; if it's a universal condition → controlled
state-congruent morphing is allowed and can even be beautiful.

## Workflow

1. INPUT + TRANSCRIBE: any audio file. Word-precise timestamps via
   faster-whisper: `WhisperModel('large-v3-turbo', device='cpu', compute_type='int8')`
   — pass the REPO NAME, not a .pt path. Save words + segment timings to JSON.
2. PASSAGE SELECTION (if audio > ~4 min): pick a self-contained unit with a
   strong opening question/statement and a clean landing — question → build →
   reversal → landing. Mark word anchors for the decisive beats.
3. CONCEPT: choose the through-line symbol + its mechanical state chain
   (e.g. candle: LIT → LOW → GUTTERING → OUT → one wisp). Choose the anchor
   (the subject of the animation) and whether it's a strict character or an
   abstract stand-in (see principle above).
4. SHOT SPINE (10-14 shots, ~12-25s each, boundaries word-anchored):
   1. WIDE establish: anchor + through-line symbol, icons readable
   2. CU/close: the first pressure/action
   3. MS→WIDE: the argument's main movement begins
   4. WIDE→CU: the crisis/turn (the catch moment)
   5. MS: the new state holds
   6. POV/WIDE/reverse: the predicament expands
   7. CU: the detail actor/object arrives
   8. MACRO: the through-line object reveals
   9. MS→CU: the decisive act + ONE pulse
   10. WIDE: old world recedes, symbol becomes dominant
   11. Residue: the symbol's final state alone (koan close)
   Framing grammar: WIDE=condition/system, CU=embodied struggle, MACRO=
   incarnated metaphor, final CU/WIDE=residue.
5. BRIEF: one record per second (F000..F{N-1}, 1fps), each prompt =
   [FID @t FRAMING] + [CHANGE ONLY: one mechanical delta] + [identity line —
   keep the anchor EXACTLY as previous frame] + [world line — one world, fixed
   geometry] + [STATE ledger VALUES — the machine's current state, monotonic] +
   [style clause] + [portrait clause]. 700-900 chars. Include
   `generation_fps: 1` in the brief (the assembler requires it) and a `verb`
   per frame. Re-anchor at every shot boundary.
6. STYLE CLAUSE (default sumi-e; swap for any style): "Faint dry-brush sumi-e
   ink line art: thin 1-3px black strokes on pure white, recognizable iconic
   forms readable at a glance, sparse but not abstract, symbolic suggestion
   over depiction, no outlines, no anatomy detail, no hatching, no filled
   forms, no vector/clip-art look. BLACK INK ONLY: no seal, no stamp, no icon,
   no logo, no color anywhere. vertical 9:16 portrait."
7. GENERATE — ONE sequential chain, NEVER parallelize (image-to-image needs
   frame N+1 from frame N; parallel blocks poison parents). F000 text-to-image,
   the rest chained. On provider empty-response storms: patient single calls
   with 60-90s escalating backoff (slow single calls beat retry bursts; the
   rate limiter keys on request RATE, not volume). Auto-reject landscape
   outputs (orientation gate — width>height = delete + retry). Timeouts
   (~420s budget) are retryable, not fatal. ~40-60s per frame.

### Image generation mechanics (the provider layer)

- BACKEND: the Hermes openai-codex image-gen plugin (gpt-image via the user's
  ChatGPT SUBSCRIPTION / Codex OAuth — NEVER a paid per-image API; the
  subscription rate-limits (empty_response storms) but never bills per image).
- WRAPPER: scripts/gen_frame.py (reference impl in ~/demello/scripts/). It must
  run under the HERMES VENV python (~/.hermes/hermes-agent/venv/bin/python) —
  it loads the plugin registry; the system python3 lacks the plugins.
- COMMAND FORM:
  `venv/bin/python gen_frame.py "<prompt>" <prev.png|-> <out.png>`
  CRITICAL: pass `-` for the prev slot on the FIRST (text-to-image) frame —
  omitting it is an arg-order bug. All later frames chain image-to-image from
  the previous accepted PNG.
- PORTRAIT: the backend returns true 9:16 (~941x1672) when the prompt demands
  it, but occasionally returns LANDSCAPE (1672x941) — the orientation gate
  (width>height = delete + retry) is mandatory, never assume.
- SCRIPT SPLIT (durable convention): gen_frame.py runs under the HERMES VENV;
  all assemblers and morph scripts run under SYSTEM python3 (they import
  numpy, which the venv lacks). A subagent running an assembler with the venv
  python produces a failed render — re-run with python3.
8. CHECKPOINT (recommended for anything > 60 frames): generate F000-F005,
   contact sheet + 6s preview with sound, get user approval before the full
   chain. Preview build: per-frame `ffmpeg -loop 1 -framerate 30 -t 1 -i F.png
   -vf scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,
   format=yuv420p -r 30 -c:v libx264 c<i>.mp4` then concat + mux audio.
   NEVER use zoompan (collapses to 1 frame) or chained xfade (truncates).
9. ASSEMBLE: normalize near-white → exact white; assemble 30fps H.264/AAC
   faststart with delta-only morphs (unchanged pixels stay fixed; only changed
   ink evolves — expression: `if(eq(A,B),A,A+(B-A)*clip((1-P)*(1+K*abs(A-B)/255),0,1))`),
   locked camera (NO zoompan — user: "it is zooming weirdly"), duration ==
   audio ±0.2s, 1080x1920.
10. MUSIC (optional, user-approved standard): ambient track at 0.16 volume
    under the voice, 2.5s fade-in, 3.2s fade-out, atrim to video duration.
    Track must be ≥ video duration (else LOOP it with a ~2s crossfade seam:
    `[0:a]atrim=0:T1[a1];[0:a]atrim=0:T2[a2];[a1][a2]acrossfade=d=2`).
11. QA + DELIVERY: ffprobe (duration, 1080x1920, codecs, faststart), vision
    contact sheet (style holds, anchor identical, state chain monotonic, no
    icons), then ship with title/description/hashtags if for YouTube.

## Additional validated practices

- TITLE CARD (optional but recommended): typography-only opening overlay (0-2s,
  never extra timeline) — eyebrow + title in a clean font (the de Mello series
  uses Hiragino Mincho ProN with wide tracking and a vertical one-char kanji
  accent on the right edge, x≈938, from a scene_sheet.kanji_motif). NO seal/
  stamp/logo anywhere. Reference: ~/demello/scripts/make_title_card.py.
- TALKING-HEAD HOST / DIRECTOR'S CUT: when the source speaker is a known
  figure but the source has NO usable footage (audio-ripped talks), generate a
  style-consistent PORTRAIT of the speaker ONCE (identity-locked master +
  mouth states + one blink frame), drive the mouth from the audio RMS envelope
  (100ms steps: quiet=closed, medium=half, loud=open), add 1-2 blinks and 0.2%
  breathing, locked camera — then INTERCUT the portrait over the UNTOUCHED
  source audio at word-anchored moments (setup ~0-6s, one mid beat, landing
  last ~8-10s), 0.15s transitions. The portrait is generated once and reused
  for every video of that speaker.
- MID-RUN PARTIAL PREVIEW: during long chains the user asks "show me" — build a
  contact sheet sampled at shot boundaries, or render a PARTIAL video from the
  frames that exist using the assembler's hold-last flag (pads to the full
  audio duration with the last frame held). Label it a partial preview, never
  the delivery.
- BAD-PARENT-DRAW DIAGNOSIS: when ONE specific frame fails ~10+ times while
  others succeed, and the same prompt succeeds with a DIFFERENT parent — the
  parent image's CONTENT is the trigger. Fix: regenerate the parent from its
  grandparent (one call), then retry the target.
- VISION GATE: the parent agent has NO vision — dispatch a vision-capable
  subagent to view contact sheets and check: style holds, anchor identical,
  state chain monotonic, damage persists, no icons/seals. The audit may flag
  TECHNICAL failures; the USER owns aesthetics (see audit trap).
- BUDGET PLANNING: ~40-60s per frame + storm pauses; a 120-frame video is
  roughly 1.5-2h of generation. All generation draws on the subscription's
  image allowance — never imply per-image billing; count usage with
  `ls ~/.hermes/cache/images/*.png | wc -l`.
- STORAGE: when a version is superseded (e.g. pre-music render), replace it in
  place (mv) rather than keeping both; the user prefers deleting old copies.
- DELIVERY PACKAGE (required by the user for every finished video): a
  ready-to-post set — TITLE (emotional transformation + curiosity gap +
  authority suffix, ~30-55 chars), DESCRIPTION (hook question → what the audio
  says → the through-line symbol → an exact quote from the audio → CTA →
  5-8 hashtags), and HASHTAGS (primary topic tags + 1-2 channel tags).

## Pitfalls (all validated the hard way)

- ADJECTIVE DELTAS = randomness. Always countdowns/count-ups (7→0), never
  "more/less/looser/simpler".
- LANDSCAPE FRAMES: the provider sometimes returns 1672x941 — always check
  width>height and reject; portrait-only output or the video breaks.
- RANDOM FACES: gpt-image occasionally draws an unexplained face in organic
  content (flames, clouds). Fix: append "NO face, no facial features, no eyes,
  no nose, no mouth anywhere" to those frames' prompts, delete ONLY those
  frames, regenerate from the last accepted parent.
- PARALLEL CHAINS: kill any second gen process immediately; delete the frame
  dir and restart one sequential chain.
- RATE-LIMIT STORMS: empty_response floods mean slow down, not speed up.
- BROKEN PIPE / agent teardown mid-run: check pgrep + frame count; the chain
  often survived (tracker reports false deaths ~60s in).
- BRIEF MECHANICS: `generation_fps: 1` + a `verb` per frame or the assembler
  refuses; final cell's target_fid is None by design (use source_fid for the
  final hold).
- BACKGROUND NEAR-WHITE: normalize only pixels ≥250 → 255; never pad white
  around the canvas (exposes edges under motion).
- THE AUDIT TRAP: an automated vision audit may call beautiful symbolic drift
  "broken continuity" and order a restart. Audits flag TECHNICAL failures
  (orientation, icons, comprehension breaks); the user owns aesthetics.

## Reference implementation

- Working scripts (copy as needed): ~/demello/scripts/ — gen_frame.py (single
  image-gen call), patient_chain.py (generalized: argv brief outdir start;
  orientation gate + retryable timeouts), normalize_white.py, assemble_v9.py
  (generalized timeline from brief+audio), qa_video.py.
- The validated example of this exact skill: ~/demello/videos/07-drop-it.mp4
  (audio teaching → sumi-e animation, user-approved).
- The de Mello-specific skill: ~/.hermes/skills/media/demello-video-pipeline/
  (full pitfalls library + continuity discipline for character stories).
