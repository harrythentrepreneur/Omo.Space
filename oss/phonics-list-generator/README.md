[![Omo](https://omo.space/logo-sweet-pastel.svg)](https://omo.space) · [All Omo workflows](https://github.com/omo-space)

# Phonics Word List Generator

What this does: generates a bounded, dialect-aware phonics word list for selected target patterns, topic, and learner difficulty.

Omo price: **$0.30 per run**.

| Run it on Omo (one click, $0.30) | Run it yourself (you'll need these API keys + ~30 min setup) |
| --- | --- |
| Omo handles the hosted workflow, provider access, validation, target-coverage checks, structured output, privacy boundary, and billing. | Bring an LLM_API_KEY (or compatible provider key), a small JSON validator, and the workflow contract. This repository is not a finished standalone service; ~30 minutes is enough to wire a local proof of concept, while production QA takes longer. |

This produces original, teacher-reviewable examples. It does not claim curriculum alignment without reviewed evidence, and dialect or pronunciation variation should remain visible.

## Files

- SKILL.md — the full provider-agnostic workflow contract.
- LICENSE — MIT license.
- .gitignore — basic local-secret and generated-file exclusions.
