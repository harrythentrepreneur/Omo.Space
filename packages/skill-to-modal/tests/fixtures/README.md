# Semantic test fixtures — provenance

The JSON fixtures in this directory are **deterministic synthetic** (2026-08-16).

The original fixtures recorded REAL provider outputs from the semantic-adapter,
batch-proof, and final-rerun runs, but they were never committed to git and
were lost when /tmp was wiped. They are not recoverable. These replacements
exercise the same contract shapes, evidence kinds, input/output structures,
and mutation needles as the originals so the full compiler suite is green and
reproducible from a fresh checkout.

They are NOT recorded provider outputs; do not cite them as such.

## generic-adapters.json (2026-08-16, semantic.contract_evidence_adapters/v1)

Right-needle inputs and semantic projections for the six generic
contract-evidence adapters (`grounded_numeric_copy`, `exact_field_projection`,
`constraint_coverage`, `policy_requirement_coverage`,
`rule_based_classification`, `placeholder_glossary_enforcement`). One case per
adapter; wrong-needle mutations live in the test code
(`test_generic_semantic_adapters_flag_wrong_needles` and its secondary
variant). Synthetic end-to-end — no provider call was made.