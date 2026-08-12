# Phonics Worksheet Generator

What this does: creates a bounded, print-ready phonics worksheet and matching answer key from a declared teaching scope.

## Example

Input:

~~~json
{
  "grade": "k",
  "focus_type": "word_family",
  "focus_patterns": ["-at"],
  "activity": "sort",
  "page_count": 2,
  "difficulty": "practice",
  "dialect": "en-US",
  "print_mode": "blackline",
  "theme": "neutral",
  "include_answer_key": true
}
~~~

Output: a two-page blackline worksheet, a matching answer-key PDF generated from the same item manifest, and a content report with the checks performed.

Omo price: **$0.30 per run**.

| Run it on Omo (one click, $0.30) | Run it yourself (you'll need these API keys + ~30 min setup) |
| --- | --- |
| Omo handles the hosted workflow, provider access, validation, deterministic rendering, private artifact delivery, and billing. | Bring an LLM_API_KEY (or compatible provider key), private object-storage credentials if you need hosted artifacts, an approved asset/font bundle, and a deterministic PDF renderer. This repository is the workflow contract, not a finished standalone renderer; ~30 minutes is enough to wire a local proof of concept, while production QA takes longer. |

This is instructional material, not a diagnostic or clinical assessment. The workflow does not copy proprietary worksheets or claim curriculum alignment without reviewed evidence.

## Files

- SKILL.md — the full provider-agnostic workflow contract.
- LICENSE — MIT license.
- .gitignore — basic local-secret and generated-file exclusions.
