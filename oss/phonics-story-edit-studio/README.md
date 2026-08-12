# Phonics Story Edit Studio

What this does: applies bounded text, layout, highlighting, title, or approved image changes to an owned PhonicsMaker story without overwriting the source.

## Example

Input:

~~~json
{
  "source_story": {
    "object_key": "stories/otter-v1.json",
    "content_type": "application/json",
    "bytes": 48210,
    "sha256": "verified-source-checksum"
  },
  "operations": [
    {
      "operation": "change_story_title",
      "new_title": "The Otter at the Dock"
    },
    {
      "operation": "toggle_highlighting",
      "highlight": true
    }
  ],
  "output_filename": "otter-v2"
}
~~~

Output: a new versioned editable JSON file, a revised PDF, and QA metadata; the original story remains unchanged.

Omo price: **$0.30 per run**.

| Run it on Omo (one click, $0.30) | Run it yourself (you'll need these API keys + ~30 min setup) |
| --- | --- |
| Omo resolves ownership, validates operations, renders the revised private artifacts, preserves the source version, and handles billing. | Bring private object-storage credentials for the source/output artifacts. Add an IMAGE_PROVIDER_API_KEY only if you enable the optional scene-image operation; text/layout edits can be deterministic. This repository is the worker contract, not the browser editor or a complete renderer; ~30 minutes is enough to wire a local proof of concept, while production ownership and PDF QA take longer. |

Only explicit, validated operations are applied. Unknown operations, arbitrary URLs, and cross-user story IDs are rejected.

## Files

- SKILL.md — the full provider-agnostic workflow contract.
- LICENSE — MIT license.
- .gitignore — basic local-secret and generated-file exclusions.
