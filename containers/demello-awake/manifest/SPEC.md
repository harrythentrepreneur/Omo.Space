# de Mello 30 Stories — Manifest Spec (v1)

The story-selection agent reads the transcripts in /Users/yifan/demello/transcripts/
and produces /Users/yifan/demello/manifest/stories.json with EXACTLY 30 entries.

## Rules
- Every story must be an actual ANTHONY DE MELLO parable/story told in his own
  recorded voice (source file must exist in /Users/yifan/demello/audio/source/).
- Stories must be self-contained: a clear setup, twist/teaching, and punchline,
  so a listener can follow it without prior context.
- STORIES MUST BE TOLD END-TO-END: clip the span from where Anthony starts the
  story to where he lands the teaching/punchline — complete narrative arcs,
  NOT mid-passage excerpts (no truncating before the point lands).
- 30 DISTINCT stories — no repeats of the same parable (even if told in several
  files, pick the best single recording of each).
- Prefer the 1986 Awareness conference (tRREgz-K8Io), then Rediscovery of Life
  (fgZBAvVNC0), then WOYDS (dxJGApodXuc), then podcast episodes.
- Duration range: 20 SECONDS to 3 MINUTES (user-confirmed). A few may be
  shorter (~10-20s) only if the story is genuinely complete in that span.
  Start/end at speech boundaries (pause points; use segment timestamps); trim
  silences/pauses at edges.

## Output schema (stories.json)
{
  "stories": [
    {
      "id": "01",
      "title": "Short punchy title",
      "source_file": "audio/source/youtube/tRREgz-K8Io.mp3",
      "start_s": 1234.5,
      "end_s": 1330.2,
      "duration_s": 95.7,
      "story_text": "verbatim transcript of the story (clean)",
      "theme": "attachment / awareness / love / fear / ego ...",
      "moral": "one-line teaching",
      "visual_seed": "5-10 words: the core image of the story (for the art agent)",
      "symbols": ["list of 3-6 symbolic motifs usable in line art, e.g. tiger, cliff, strawberry"]
    }
  ]
}

## Quality gates (agent must self-check before writing the file)
1. 30 entries, ids 01..30, durations 60-150s
2. Every source_file exists; start/end within file duration
3. story_text non-empty, matches transcript wording at those timestamps
4. Titles unique; themes diverse (don't pick 10 attachment stories)
5. moral + visual_seed + symbols filled for every story

Write the file, then print a one-line summary per story (id | title | src | duration).
