[![Omo](https://omo.space/logo-sweet-pastel.svg)](https://omo.space) · [All Omo workflows](https://github.com/omo-space)

# Phonics Reading Error Coach

What this does: turns one observed decoding attempt into a cautious, teacher-reviewable phonics confusion note with short practice ideas.

## Example

Input:

~~~json
{
  "misread_word": "ship",
  "target_word": "chip",
  "dialect": "en-US",
  "learner_stage": "developing",
  "detail": "teacher",
  "include_practice": true
}
~~~

Output: structured JSON identifying a possible initial-consonant substitution, explaining the contrast without claiming certainty, and returning at most two teacher-reviewable practice suggestions with teacher_review_required: true.

Omo price: **$0.30 per run**.

| Run it on Omo (one click, $0.30) | Run it yourself (you'll need these API keys + ~30 min setup) |
| --- | --- |
| Omo handles the hosted model call, input validation, structured output, privacy boundary, and billing. | Bring an LLM_API_KEY (or compatible provider key), a small JSON validator, and an educator-reviewed fixture set. There is no file-storage requirement for the basic note; ~30 minutes is enough to wire a local proof of concept, but educator evaluation is still required before classroom use. |

This is not an assessment, score, diagnosis, disability screen, or substitute for a qualified educator. One word attempt cannot establish a stable learner profile.

## Files

- SKILL.md — the full provider-agnostic workflow contract.
- LICENSE — MIT license.
- .gitignore — basic local-secret and generated-file exclusions.
