# de Mello 30 Stories — Visual Pipeline Spec (v1) — "Sumi-e Shadows"

## Goal
For each of the 30 stories: a 9:16 (1080x1920) video on a WHITE background,
Japanese line-art (sumi-e / ink brush) style, where the imagery evolves every
second, each new state deriving from the previous one (congruency), with smooth
transitions. Paired with the story's audio mp3.

## Style lock (every prompt, every frame — branding, do not drift)
- "Minimalist Japanese sumi-e ink line art, thin black brush strokes on pure
  white background, generous negative space, subtle single accent of muted
  vermilion (only as a tiny seal/stamp mark), flat, no shading, no color fills,
  no texture, no text, no letters, no watermark, vertical 9:16 composition,
  elegant, calm, meditative, symbolic, faint."
- ONE consistent accent color only: #C8402C vermilion seal (optional, small).
- Never: photorealism, gradients, gray fills, western cartoon, 3D, borders.

## Congruency mechanism (CRITICAL)
Frame N+1 is generated FROM frame N (image-to-image):
- In the ChatGPT web session: attach the previous frame image and prompt
  "Continue this exact drawing: <evolution instruction>. Keep the same
  characters, line weight, and composition; only <specific change>."
- Result: characters/scenes persist and morph naturally — "the new animation
  draws upon the last generation".
- Fallback if image-edit is unavailable in the UI: prompt re-anchoring (repeat
  style lock + carry a persistent "scene sheet" of established motifs in the prompt).

## Image generation — SUBSCRIPTION ONLY (user directive, hard rule)
- NEVER use the paid OpenAI Images API (gpt-image-1 API billing). 
- Generate inside the user's ChatGPT subscription (chatgpt.com web UI) via
  ego-browser automation (reuses the user's logged-in ChatGPT session; the
  codex backend token cannot reach chatgpt.com/backend-api — 403 verified).
- Pipeline per story: ego-browser task space -> ChatGPT chat -> for each frame:
  attach previous frame (or style-locked text for frame 1) -> prompt evolution
  -> wait for generation -> download PNG -> close/dismiss.
- Download images to art/frames/<id>/NNN.png.

## Frame budget (default, adjustable)
- 1 keyframe per ~5 seconds of story audio + 1 opening frame (title/theme motif).
- Each keyframe's animation = slow ken-burns drift + ink-flow wash + per-second
  micro-morph via ffmpeg (zoompan + xfade). Per-second visual change is achieved
  by the animated transition, not by 60 separate generations.
- OPTION (premium, only if user approves): true 1fps generation — 1 image per
  second. Cost roughly 5x the default. Default is keyframes + animation.

## Visual brief per story (produced by the visual-brief agent)
For each story in stories.json, produce art/prompts/brief-<id>.json:
{
  "id": "01",
  "title": "...",
  "style_lock": "<the style lock string above>",
  "scenes": [
    {"t_start": 0, "t_end": 8, "motifs": ["mountain", "small figure"], "action": "figure stands at cliff edge",
     "evolution_from_previous": "the mountain grows closer; mist rises"},
    ...
  ],
  "opening_motif": "...", "closing_motif": "..."
}
Rules for the brief agent:
- scenes map 1:1 to the story's beats (use story_text + timestamps from manifest)
- every scene except the first MUST name what it carries over from the previous
  scene (evolution_from_previous) — this is what makes generation congruent
- 2-5 motifs per scene max, symbolic (tiger, rope, boat, wave, moon, gate...)
- no text, no people's faces in detail (silhouettes/figures ok)

## Assembly (per story)
1. Generate frames (gen_frames.py): brief -> N pngs (1024x1536, white bg)
2. Animate: for each frame, 5s clip via zoompan (slow drift), then xfade chain
   (1s crossfade between clips) -> silent video track at 30fps 1080x1920
3. Mux with story audio (ffmpeg -i video -i story.mp3 -c:v libx264 -c:a aac)
4. Output: videos/01-<slug>.mp4

## Cost control (user directive: flag API-only costs first)
- Image generation uses the ChatGPT SUBSCRIPTION via chatgpt.com web UI
  (ego-browser). NO paid API calls for images — user directive, hard rule.
- Default keyframe budget: ~10-14 images/story -> ~300-420 images total
- Pilot: build story 01 completely, report quality + time, THEN scale to 29.
