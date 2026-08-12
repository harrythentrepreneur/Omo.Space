[![Omo](https://omo.space/logo-sweet-pastel.svg)](https://omo.space) · [All Omo workflows](https://github.com/omo-space)

# Syllable Splitter and Counter

What this does: splits a bounded list of English words into syllables and returns counts with explicit dialect and ambiguity notes.

Omo price: **$0.30 per run**.

| Run it on Omo (one click, $0.30) | Run it yourself (you'll need these API keys + ~30 min setup) |
| --- | --- |
| Omo handles the hosted workflow, provider access, input validation, dialect checks, structured output, privacy boundary, and billing. | Bring an LLM_API_KEY (or compatible provider key), a small JSON validator, and the workflow contract. This repository is not a finished standalone service; ~30 minutes is enough to wire a local proof of concept, while production QA takes longer. |

Syllabification and counts can vary by dialect or pronunciation. Review the returned ambiguity notes before classroom use.

## Files

- SKILL.md — the full provider-agnostic workflow contract.
- LICENSE — MIT license.
- .gitignore — basic local-secret and generated-file exclusions.
