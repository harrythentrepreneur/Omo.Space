# de Mello — Awake: Art / Animation Pipeline V3
**Status:** directing specification for the 3fps V3 pilot
**Scope:** semantic frame design, directed motion, prompt compilation, generation, interpolation, assembly, and QA
**Binding user directives:** every movement must be motivated by the story; the drawing must visibly evolve at three generated frames per second.
**Pilot:** Story 01, “They Never Wake Up,” 39.0 seconds, 117 generated frames.
## Executive rule
V3 is not “V2 with more camera motion.” V3 makes the drawing change three times per second, and assigns every change one authored motion verb tied to the spoken meaning. The camera is a quiet witness. The ink, posture, aperture, enclosure, and negative space carry the action.
## Eight key decisions
1. Generate exactly 117 semantic frames for the 39-second pilot: `F000` through `F116`, one frame every 1/3 second; no 3–5-second image holds during active speech.
2. Each second is a three-step action: default `settle → change → land`; use `anticipate → act → recover` for a pivot and `hold → breathe → hold` for literal silence.
3. A frame may introduce or move one semantic thing only. The prompt names one delta and protected anchors; it never asks for a new scene.
4. Re-anchor every 12 generated frames (four seconds), and immediately before/after a pivot, repair, or phase boundary. Re-anchoring restores geometry; it does not reset identity.
5. Replace generic camera presets with a small directed motion-verb vocabulary. Each second has one verb, one target element, one direction, and a measured amplitude.
6. Keep the camera fixed at the opening, closing, and decisive meaning beats; if it moves, it follows the through-line’s geometry and stays quieter than the drawing.
7. Use 0.20-second pairwise difference-preserving morphs between adjacent generated frames, then a short landing hold; do not use optical flow, routine wipes, or alternating pan presets.
8. Full 3fps is mandatory through 90 seconds. For longer stories, retain 3fps around active clauses and pivots, and use 1.5fps only in the low-change tail, never allowing an active semantic hold longer than one second.
# A. Diagnosis: why V7 reads as one scene
## A1. Actual V7 structure
The pilot video is 39.000 seconds, 1080×1920, 30fps, 1,170 output frames. Its brief contains 14 generated assets: `K000`–`K012` plus `closing_art`. The semantic anchors are:
| asset | time | next anchor | interval | authored event |
|---|---:|---:|---:|---|
| K000 | 2 | K001 | 4s | base closed eye / sleeper |
| K001 | 6 | K002 | 4s | life-line joins sleeper |
| K002 | 10 | K003 | 4s | life-line returns / cycle closes |
| K003 | 14 | K004 | 1s | torso releases upward |
| K004 | 15 | K005 | 4s | brief waking / slight eye opening |
| K005 | 19 | K006 | 5s | head-line coils and lowers figure |
| K006 | 24 | K007 | 4s | sleeping contour echoes at three scales |
| K007 | 28 | K008 | 3s | outer enclosure lengthens |
| K008 | 31 | K009 | 1s | enclosure stops short of closure |
| K009 | 32 | K010 | 3s | stopped enclosure opens into circle |
| K010 | 35 | K011 | 1s | circle gap widens |
| K011 | 36 | K012 | 1s | decisive standing / eye opening |
| K012 | 37 | closing_art | 1s | secondary marks recede to residue |
Thus the first 13 seconds after the title are represented by only three semantic drawings. The important “born asleep → live asleep → die asleep” argument is visually held across 4-second intervals; “brain → fall asleep” is held across five seconds. The output is 30fps, but the source drawing changes only 14 times.
The pilot's first 1-Hz probe also exposes the perception problem: the sampled grayscale delta is `0.000` from second 0→1 (title hold) and only `0.036` from second 16→17. Larger deltas cluster at authored keyframe boundaries. A 30fps export therefore does not imply 30fps visual evolution.
## A2. What the assembler preserves
1. `assemble_v7.py` gives each semantic pair its entire anchor-to-anchor interval.
2. `continuous_delta` morphs for 80% of a DRIFT interval, then settles. With a 4-second interval, most of the viewer’s time is still spent looking at nearly the same endpoint geometry.
3. `delta_settle` compresses CHANGE into eight output frames (`0.267s`); `held_delta` compresses PIVOT into an eight-frame hold, six-frame delta, and landing hold. The meaningful change is brief relative to the hold around it.
4. The custom delta expression preserves equal pixels exactly and moves only changed pixels toward the target. This is desirable for clean edits, but it also makes the unchanged eye, figure, horizon, and empty field dominate the interval.
5. A delta morph cannot invent semantic intermediate states. If K000 and K001 both show a closed eye and the same reclining figure, the dissolve only reveals a line arriving; it does not give the figure three motivated stages of being born, living, and dying.
6. `motion_manifest` assigns broad ranges such as `drift_follow`, `slow_push`, and `breath_hold`. `slow_push` is centered; `drift_follow` follows a note-derived axis, not the actual tangent of the through-line at that beat.
7. `animate_motion.py` contains large generic presets, while V7 constrains them to small ranges in `assemble_v7.py`. The remaining zoom/pan is a calm texture, not a directed action. It can make a clip move without telling the viewer why.
8. The eye is mostly protected and closed through K000–K003 and K005–K008. It changes meaning only at K004, K009–K012. The current through-line therefore behaves like a logo that watches a slow camera move rather than a living symbolic actor.
9. Prompt records are 1,163–1,666 characters, with repeated style lock, negatives, and anchor prose. The long prompt does not buy 117 usable micro-decisions; it buries the one allowed edit.
10. The brief correctly identifies the story thesis, but it maps connective words and dramatic clauses to the same broad camera language. “And,” “in their sleep,” and “never wake up” need different temporal force.
**Diagnosis:** V7 is not technically frozen. It is semantically under-sampled, directionally generic, and morph-dominated. The delta compositor preserves the scene that should have been changing; the camera supplies movement that is not attached to the words. V3 fixes the source schedule first and the camera second.
# B. The 3fps frame schedule
## B1. Canonical 39-second grid
Create 117 generated semantic frames:
```text
F000 @ 0.000s, F001 @ 0.333s, F002 @ 0.667s
F003 @ 1.000s, F004 @ 1.333s, F005 @ 1.667s
...
F114 @ 38.000s, F115 @ 38.333s, F116 @ 38.667s
```
Frame `F[n]` owns the following 1/3-second cell `[n/3, (n+1)/3)`. The editorial title is composited over the opening cells; it does not remove them from the generated chain. `F000` is the text-to-image identity frame, `F001`–`F116` are sequential image-to-image frames, and `F116` is the final meaningful black-ink state before the editorial seal/white cut. If a separate closing residue is required, it is an editorial reduction of `F116`, not an extra story hold.
The parent rule is strict: each frame uses the last accepted frame, never a rejected result and never an older ancestor, except that the re-anchor prompt may cite `F000` geometry as a QA reference.
## B2. Three micro-steps per second
The default second is `settle → change → land`:
- **slot 0 / settle:** inherit the last meaning, make the smallest anticipatory adjustment, and establish the direction of the next action.
- **slot 1 / change:** perform the one visible semantic edit; this is the strongest of the three deltas.
- **slot 2 / land:** finish that same edit, restore the protected geometry, and leave a readable endpoint for the next second.
Use `anticipate → act → recover` when the second contains a pivot, awakening, fall, or release. Use `hold → breathe → hold` only for silence or a deliberately arrested meaning. “Hold” still means a designed state, not permission for a generic camera drift.
The three frames are not three unrelated illustrations. They are three poses of one verb. A `descend` second is: figure begins yielding, figure lowers through the line’s pull, figure settles into the sleep contour. An `expand` second is: tip starts outward, enclosure reaches its new extent, tip lands with an intentional gap.
## B3. Micro-delta discipline
Every generated frame record must contain exactly one `delta` that answers: **which existing stroke changes, in what direction, by how much, and why now?**
- Divide the authored one-second amplitude into three monotonic micro-steps; never reverse direction between slots.
- The slot-1 delta may be up to 50% of the one-second total; slot 0 and slot 2 share the rest.
- Do not move the eye, figure, ground line, and enclosure in the same frame unless the brief labels it a PIVOT and names one coupled gesture.
- “More dynamic,” “camera drifts,” “make it interesting,” and “add energy” are invalid deltas.
- A delta must point to an existing named stroke or a single permitted new stroke. New strokes must be born from an existing stroke and remain subordinate to the through-line.
- State the endpoint: `tip ends at x=0.62, gap remains 0.08`, not `line grows a little`.
- Keep frame-to-frame changes perceptible at delivery scale but below redraw chaos. If the model cannot express the micro-delta, hold the source and retry with a simpler edit.
## B4. Normalized positional continuity
The scene sheet uses final-canvas normalized coordinates. For every ordinary adjacent pair:
- protected anchor centroid: ≤1.0% frame displacement;
- protected extent: ≤1.5% change;
- orientation: unchanged unless the verb explicitly targets it;
- through-line tangent: continuous; no unexplained kink greater than the authored delta;
- empty field: at least 85% white and the named side margins remain empty.
At a re-anchor or PIVOT, a protected centroid may reach 2.0% only when the brief explicitly authorizes the gesture. The cumulative anchor displacement from the latest re-anchor must stay under 3.0% across the next 12 frames. Use language such as: `eye center remains (0.50, 0.30) ±0.01; eye extent remains 0.34×0.10 ±0.015; central interval stays empty.`
## B5. Re-anchor cadence
Re-anchor every 12 generated frames (four seconds), at `F012, F024, F036, ...`, using the full scene sheet plus the next single delta. Twelve frames is short enough to bound chained image-to-image drift and long enough to avoid turning every frame into an expensive identity reset. Also re-anchor:
1. immediately before a PIVOT;
2. on the first frame after a PIVOT landing;
3. after any repaired frame;
4. at setup/escalation/twist/landing boundaries;
5. at each act boundary in stories longer than 90 seconds.
A re-anchor is still image-to-image from the last accepted frame. It restores anchor geometry and makes one authored edit; it never redraws a fresh scene.
## B6. Translating V2 beat types
| V2 type | V3 treatment |
|---|---|
| HOLD | Three near-identical semantic states for silence: `hold → breathe → hold`. Use no image call only for a verified literal silence with no state change; duplicate the accepted frame editorially, but never let active speech hold unchanged for >1s. |
| DRIFT | Three generated monotonic micro-steps per second. The line lengthens, bends, loosens, or recedes; no new noun icon. |
| CHANGE | Three frames around one operation: settle into it, perform it, land it. The target may transform an existing stroke but must keep the through-line. |
| PIVOT | `anticipate → act → recover`, often with a still first slot and a decisive middle slot. Re-anchor before and after; simplify rather than add detail. |
For the V3 Story 01 pilot, generate all 117 frames, including visually quiet seconds, so the team can calibrate whether “near-identical” is genuinely intentional. Production optimization comes only after the pilot passes the contact-sheet test.
## B7. Generation budget and adaptive rate
At the observed planning rate of approximately 40 seconds per image call:
| story length | 3fps calls | nominal generation time |
|---:|---:|---:|
| 20s | 60 | 40m |
| 39s pilot | 117 | 78m |
| 90s | 270 | 180m |
| 180s full 3fps | 540 | 360m |
Add 10–20% for retries and rejected frames. The 39-second pilot should therefore be budgeted at roughly 86–94 minutes, not the old 10–14-call V2 budget.
Adaptive production rule:
1. `D ≤ 90s`: full 3fps, including all spoken clauses and transitions.
2. `90s < D ≤ 180s`: full 3fps through 90s; use 1.5fps in low-change tail cells, but burst back to 3fps for every PIVOT, clause landing, awakening, fall, reveal, or visual birth.
3. `D > 180s`: divide into acts; each act opening, pivot, and landing is 3fps. Low-change connective tail may be 1.5fps, never 1fps during active speech.
4. At 1.5fps, interpolate/hold each source for two-thirds of a second, but schedule a generated frame at every semantic change; a long story is adaptive in density, not generically slow.
For a 180-second story, the simple 90s-plus-tail budget is about 405 calls / 270 minutes before retries, versus 540 calls / 360 minutes at full 3fps. The pilot remains full-rate because the user’s complaint is specifically about unchanging holds.
# C. Directed motion model
## C1. Motion-verb vocabulary
Each second chooses one verb, one target, one direction, and one normalized amplitude. The verb is selected from meaning, never from clip index or a direction-alternation cycle.
| verb | story use | drawing amplitude per second | camera rule |
|---|---|---:|---|
| `hold-breath` | silence, arrested realization, “never wake” | 0–0.2% | fixed; optional ≤0.05% breath |
| `settle` | land a prior change before the next clause | 0.2–0.4% | fixed |
| `descend` | fall, return to sleep, weight, surrender | figure/line y 0.8–1.5% | follow downward only if needed, ≤0.15% |
| `rise` | native awareness, standing, release upward | figure/line y 0.8–1.5% | fixed or ≤0.15% upward follow |
| `expand` | enclosure, awareness, social pattern becoming larger | extent/tip 1.0–2.0% | quiet push toward the growing tip, ≤0.20% |
| `contract` | narrowing, learned sleep, attention closing | extent/aperture 0.8–1.5% | quiet pull only if contraction is spatially meaningful |
| `drift-toward` | line approaches the subject or through-line | target distance 0.6–1.0% | pan toward target, ≤0.20% |
| `drift-away` | release, recession, loss of explanatory marks | target distance 0.6–1.0% | pan away only when the subject is being released |
| `coil` | thought bends inward; brain/conditioning encloses | curve length/turn 0.8–1.2% | fixed; the line must do the coiling |
| `uncoil` | release, seeing through the habit | gap/curve 0.8–1.5% | fixed; no zoom burst |
| `open` | eye, gate, aperture, possibility | gap/height 1.0–2.0% | fixed at the decisive opening |
| `close` | sleep, contraction, withheld awareness | gap/height 1.0–2.0% | fixed |
| `surge` | one decisive pivot only | 1.5–2.5% total, split across three frames | camera fixed; delta carries force |
| `recede` | secondary marks leave and meaning simplifies | line length/opacity region 1.0–2.0% | fixed; do not zoom out to manufacture exit |
## C2. Directed-motion rules
1. Write `verb → target → geometry → semantic reason` before writing a prompt: `descend → figure torso → y +0.012 → learned sleep takes hold`.
2. The through-line owns the path. If the eye is the symbol, its aperture, gaze direction, enclosing relation, or distance to the figure is the route the viewer follows.
3. Motion may follow a line’s tangent, curve, or endpoint; it may not pan in a generic left/right cycle.
4. One second has one primary verb. A secondary change is allowed only as a consequence of the same verb, such as `rise` causing the eye to `open` at a PIVOT.
5. Amplitude is a semantic budget, not a visual-effects setting. Divide the total by three and keep the sign consistent across the second.
6. If a camera move and a drawing move express the same action, reduce the camera to one quarter of the drawing amplitude. Never let both announce the beat equally.
7. “Stillness” is directed when it follows a failed motion, a silence, or a held realization. It is not a default preset filling missing direction.
8. No rotation, diagonal sweep, bloom, ink splash, particle field, or white wipe in routine animation. A rotation requires a written symbolic reason and a clipping test.
## C3. Camera policy
- Opening 0–2s: fixed camera; title and first question-symbol establish attention.
- During line action: fixed camera by default. If the through-line travels horizontally, pan no more than 0.20% per second toward its active endpoint; if it rises/descends, use no more than 0.15% follow.
- During a CHANGE: camera ≤0.15% while the drawing changes; do not counter-pan the authored movement.
- During a PIVOT: fixed camera, no zoom, no rotation. The eye opening, figure rise, or enclosure release must read as an event in the ink.
- During a HOLD: fixed camera; a 0.05–0.10% breathing scale is the ceiling and is omitted when it competes with silence.
- Closing 37–39s: fixed camera; secondary lines recede, residue settles, exact editorial seal lands, then white.
# D. Workflow
## D1. Compact 3fps brief schema
The directing agent writes semantic records, not 117 prose prompts. A compiler expands each `second` into three frame records and assigns `frame_id` and `t`.
```json
{
  "story_id": "01",
  "duration_s": 39.0,
  "generation_fps": 3,
  "scene_sheet": {"...": "immutable normalized anchors"},
  "seconds": [
    {
      "sec": 17,
      "phase": "escalation",
      "beat_type": "DRIFT",
      "spoken_meaning": "developed thought bends awareness inward",
      "verb": "coil",
      "target": "existing head-line above figure",
      "pattern": "settle-change-land",
      "micro": [
        {"role":"settle", "delta":"tip turns inward by 0.003 toward the head-line"},
        {"role":"change", "delta":"one turn forms and lowers 0.005 toward the figure"},
        {"role":"land", "delta":"coil stops with a clear 0.08 normalized gap"}
      ],
      "protected": ["eye", "figure identity", "ground line", "white interval"]
    }
  ]
}
```
Required fields are `sec`, `phase`, `beat_type`, `spoken_meaning`, `verb`, `target`, `pattern`, three monotonic `micro.delta` values, and `protected`. The compiler adds `frame_id`, `t_start`, `t_end`, `reanchor`, `parent_frame`, and the rendered prompt. It rejects missing verbs, duplicate targets, unresolved placeholders, non-monotonic deltas, and seconds without exactly three micro records.
## D2. Prompt compilation
1. Store the full style lock once as `STYLE_LOCK_V3`; do not repeat V2’s 1,000-character prompt prose in the brief.
2. Compile each frame from operation/meaning/delta/anchors/negative fields.
3. Append the short V3 style lock to every frame. Append the legacy verbose lock only to `F000`, re-anchors, PIVOTs, and repair retries if visual calibration requires it.
4. Keep transcript words in metadata. Send semantic meaning, not quoted speech or pseudo-text instructions.
5. Record every rendered prompt verbatim beside its source frame and parent checksum.
## D3. Finalized per-frame micro-delta prompt template
This is the canonical short body (approximately 300–450 characters after placeholder expansion; the compiler substitutes concrete values):
```text
F[NNN] @[T] [ROLE]. Meaning: [INTENT]. Change only: [DELTA]. Keep [ANCHORS] at [NORMALIZED_POS/SCALE], same crop and line identity; drift ≤1%. Protect [EMPTY_REGIONS]. Black ink on white, sparse flat sumi-e line, vertical 9:16. FORBID text, watermark, color, shading, extra figures, new scenery, camera change.
```
**Verbatim template policy:** `[ROLE]` is one of `settle`, `change`, `land`, `anticipate`, `act`, `recover`, `hold`, or `breathe`; `[DELTA]` is one concrete monotonic edit; `[ANCHORS]` names only the protected elements needed for this frame. `STYLE_LOCK_V3` is the stable compiler suffix: `Minimal Japanese sumi-e: thin black ink on pure white, sparse flat line, no shading/fill/texture, vertical 9:16, no text/watermark/color.`
## D4. Sequential generation and retry rules
1. Generate `F000` text-to-image from the approved scene sheet.
2. Generate `F001`–`F116` image-to-image from the last accepted frame, in order.
3. At every 12-frame re-anchor, include full normalized geometry and the next delta.
4. Validate PNG, dimensions, white-field ratio, chroma, and dark-line mask before promoting a frame to parent.
5. On provider failure, retry the same source and exact prompt with exponential backoff, at most twice.
6. On visual failure, quarantine the result; retry from the last accepted parent with one observed defect named. Never use a rejected frame as a parent.
7. If two repairs fail, simplify the delta, not the protected scene; a PIVOT or closing frame requires human review.
8. Parallelize stories, not frames within a chain. Never run two ffmpeg processes against one output.
## D5. Drift QA at 3fps granularity
Run adjacent-frame QA after every accepted candidate and cumulative QA every 12 frames:
- chroma in story art: fail;
- white field below 85%: fail;
- protected centroid >1.0% adjacent or >3.0% from the last re-anchor: flag/fail;
- protected extent >1.5% adjacent or >3.0% cumulative: flag;
- unexpected dark component outside the authored delta region: flag;
- changed dark-mask ratio above 0.20 for HOLD, 0.45 for DRIFT, or 0.75 for CHANGE: flag;
- through-line mask IoU below 0.90 on HOLD, 0.80 on DRIFT, or 0.60 on CHANGE: flag;
- semantic delta absent from the contact sheet: reject even when pixel QA passes.
For each 4-second block, review a 12-thumbnail strip with `frame_id`, spoken meaning, verb, delta, anchor boxes, and changed-mask overlay. The question is not “does it look smooth?” but “can a viewer tell what the line is doing and why?”
## D6. Assembly adaptation
Adapt the V7 pairwise FFV1 architecture rather than replacing it with optical flow:
- each adjacent pair owns a 1/3-second interval (10 output frames at 30fps);
- run a difference-preserving delta morph for 6 frames (`0.20s`);
- use the remaining 4 frames for the authored landing/hold, with no generic pan reversal;
- use `continuous_delta` for DRIFT, `delta_settle` for CHANGE, and a shorter `held_delta` only for a PIVOT;
- apply the verb-driven camera range after pair assembly, not as the primary change;
- keep opening/title fixed and closing/residue fixed;
- keep the exact vermilion seal editorial and after the line settles;
- render independent lossless pair mezzanines, then one final H.264/AAC pass;
- make timeline accounting exact: 117 source cells × 10 output frames = 1,170 video frames.
The V3 assembler must accept a generated-frame schedule, not only V2 `t_anchor` keyframes. It must emit a report with source/target IDs, verb, transition mode, pair frames, parent checksum, motion range, and QA status.
## D7. Pilot-first rollout
Do not generate all 117 frames blindly. Validate the directing system in slices while retaining the final 117-frame budget:
1. Compile the first 12 frames (0–4s) and generate them sequentially.
2. Review the 4-second contact strip for visible three-step evolution and anchor stability.
3. Assemble a 4-second proof with the 0.20s pair morph and compare it to the corresponding V7 hold.
4. Tune only amplitude, prompt specificity, or re-anchor wording; do not add generic camera motion to hide weak deltas.
5. Generate the next 12-frame block through the awakening pivot and review the `rise/open` direction.
6. Complete all 117 frames, assemble the 39s pilot, and run audio, duration, frame-count, faststart, visual, and semantic QA.
7. A/B V3 against V7 on: perceived change rate, story alignment, through-line continuity, calmness, artifact rate, and generation time.
8. Freeze defaults only after Story 01 and two additional stories pass the same contact-sheet gate.
# E. Concrete Story 01 V3 plan
## E1. Scene-sheet changes
1. Retain one eye, one tiny faceless figure, and one dawn horizon; remove any implication that a new icon is needed for breed, business, or government.
2. Fix eye center `(0.50, 0.30)`, extent `(0.34, 0.10)`; figure center starts `(0.40, 0.69)`, height `0.10`; horizon `y=0.74`.
3. Define the eye state curve explicitly: closed through second 14; slight opening across 14–16; closed/arrested while the coil and enclosure grow; half-open at “never wake”; decisive opening across 36–37.
4. Define the figure state curve explicitly: reclining at 0–14; rises one degree at 14–15; lowers during 17–20; remains within the repeated sleep contour through 31–35; stands across 36–37.
5. Define the enclosure gap as protected negative space until the release at 34–37. It must grow, stop, uncoil, and open; it must not become a filled circle.
6. Define the only support family as repeated sleeping contours at three scales. No children, ledger, government building, business symbol, or decorative scenery.
## E2. Directed second map: three deltas per second
The following map is the 39-second directing source. Each row expands to three frame records in the order shown; `—` means the line is intentionally held, not camera-drifted.
| sec | meaning / verb | slot 0 | slot 1 | slot 2 |
|---:|---|---|---|---|
| 0 | reserve question / hold-breath | white field holds | eye seed settles | eye seed lands |
| 1 | eye arrives / settle | upper curve appears | lower curve joins | closed eye lands |
| 2 | unexamined sleep / settle | figure contour begins | reclining torso completes | horizon contact lands |
| 3 | setup silence / hold-breath | hold | breathe 0.1% | hold |
| 4 | shared condition / descend | shoulder yields | torso lowers | sleep posture lands |
| 5 | born asleep / drift-toward | life-line extends right | reaches sleeper | joins contour |
| 6 | existence shaped by sleep / descend | line touches ground | line lowers toward figure | sleep contact lands |
| 7 | live asleep / hold-breath | eye remains closed | figure breathes once | same sleep lands |
| 8 | repeated sleep / descend | head lowers | torso follows | contour settles |
| 9 | die asleep / drift-away | life-line curves back | returns to original contour | cycle gap lands |
| 10 | cycle completes / contract | line nears sleeper | line meets contour | closed cycle lands |
| 11 | “but” recognition / hold-breath | stop all travel | white interval holds | arrested landing |
| 12 | truth settles / hold-breath | hold | tiny line breath | hold |
| 13 | certainty loosens / rise | torso releases 0.003 | shoulder lifts 0.005 | rise prepares |
| 14 | not born asleep / rise | torso lifts | figure reaches half-rise | eye stays closed, pose lands |
| 15 | born awake / surge + open | figure rises | eye gap opens one degree | waking gesture recovers |
| 16 | brief awareness / hold-breath | hold open gap | one quiet breath | do not widen |
| 17 | developed brain / coil | head-line bends inward | first turn lowers | coil lands above head |
| 18 | thought tightens / descend | coil contracts | figure yields downward | gap remains clear |
| 19 | fall asleep / descend | line pulls figure | torso lowers | reclining sleep lands |
| 20 | consequence / hold-breath | hold downward pose | white field breathes | hold |
| 21 | silence / hold-breath | no new stroke | no camera move | stillness lands |
| 22 | breed in sleep / expand | contour echo begins | second scale appears | echo lands |
| 23 | children in sleep / echo | echo shifts outward | third scale forms | three scales align |
| 24 | inherited sleep / descend | all scales lower 0.003 | contours settle together | pattern lands |
| 25 | bring them up / rise | smallest contour lifts | larger contours follow | inherited rise lands |
| 26 | raised in sleep / descend | contours sink together | sleep line thickens only by stroke count | descent lands |
| 27 | big business / expand | enclosure tip starts right | outer line lengthens | new extent lands |
| 28 | business in sleep / drift-toward | line approaches largest contour | wraps one side | open gap remains |
| 29 | government / expand | enclosure grows upward | follows outer tangent | civic extent lands |
| 30 | in their sleep / hold-breath | stop tip | half-open eye holds | arrested enclosure lands |
| 31 | die in sleep / contract | tip returns inward | nears largest contour | stop short of closure |
| 32 | never wake / hold-breath | tip stops | eye becomes half-open | no escape lands |
| 33 | silence / hold-breath | no line action | central emptiness holds | stillness lands |
| 34 | spirituality begins / uncoil | enclosure gap loosens | line releases claim | incomplete circle begins |
| 35 | spirituality is all / uncoil | circle gap widens | obsolete echoes recede | open circle lands |
| 36 | about / rise + open | figure lifts | eye opens decisively | standing pose lands |
| 37 | wake up / surge | eye/figure hold wake | circle releases around them | recovery is quiet |
| 38 | drunken moving around / recede | secondary marks recede | residue reduces | final circle and seal hold |
## E3. Numbered V3 rebuild plan
1. Freeze the revised Story 01 scene sheet and approve its normalized anchor boxes, eye state curve, figure state curve, and enclosure gap.
2. Convert `pilot_beats.json` into the 39-row directed second map above; remove generic `drift_follow`, `slow_push`, and `still_emphasis` labels from the directing source.
3. Compile each row into exactly three micro records and validate a 117-record frame brief: `F000`–`F116`, monotonic deltas, verb, role, protected anchors, re-anchor markers, and parent IDs.
4. Generate F000 as text-to-image, then generate F001–F011; stop for contact-sheet and drift QA before continuing.
5. Generate F012 as the first full re-anchor, then continue in 12-frame blocks. Re-anchor before F042/F045, F057/F060, F093/F096, and any repaired or pivot frame as well as the regular 12-frame cadence.
6. Assemble the first 12-frame proof with 10 output frames per source cell, six-frame delta morphs, four-frame landing holds, and no camera motion beyond the verb map.
7. Complete all 117 frames and create a V3 render report containing timings, checksums, drift metrics, changed-mask ratios, and rejection/retry history.
8. Review the final 39-second contact sheet against the spoken clauses. Reject any frame that is visually different but semantically unmotivated, or semantically correct but too small to read at 9:16 delivery.
9. A/B the V3 proof and V7 at normal phone size. The success condition is not “more movement”; it is three legible authored micro-states per second without losing the calm white field.
10. Keep V2 frozen as a comparison baseline. Promote V3 defaults only after Story 01, Stories 02–03, and the final QA report satisfy the acceptance gates.
## E4. V3 acceptance gates
- 117 generated frame records exist for the 39-second pilot, with no unresolved prompt placeholders.
- Every active second has one verb and three monotonic micro-deltas.
- No active speech interval exceeds one second with no semantic frame evolution.
- At least 90% of adjacent protected anchors remain within the 1% centroid threshold.
- No chroma, pseudo-text, extra figures, or unlisted scenery appears in story art.
- The eye, figure, life-line, enclosure, and closing residue read as one continuous argument.
- Camera movement is absent at the opening, pivots, and closing, and never exceeds the directed-motion budget elsewhere.
- The contact sheet makes the words “fall,” “open,” “enclose,” “stop,” and “wake” visibly distinct.
- Final output remains exactly 39.0s, 30fps, 1080×1920, 1,170 frames, with valid audio mux, faststart MP4, and editorial vermilion only at the seal.
- A reviewer can explain the reason for every visible movement without referring to a generic preset name.
## Appendix: print-ready motion-verb list
`hold-breath`, `settle`, `descend`, `rise`, `expand`, `contract`, `drift-toward`, `drift-away`, `coil`, `uncoil`, `open`, `close`, `surge`, `recede`.
## Appendix: print-ready micro-delta template
```text
F[NNN] @[T] [ROLE]. Meaning: [INTENT]. Change only: [DELTA]. Keep [ANCHORS] at [NORMALIZED_POS/SCALE], same crop and line identity; drift ≤1%. Protect [EMPTY_REGIONS]. Black ink on white, sparse flat sumi-e line, vertical 9:16. FORBID text, watermark, color, shading, extra figures, new scenery, camera change.
```
