# Semantic test fixtures — provenance

The three JSON fixtures in this directory are **deterministic synthetic reconstructions** (2026-08-16).

The original fixtures recorded REAL provider outputs from the semantic-adapter, batch-proof, and final-rerun runs, but they were never committed to git and were lost when /tmp was wiped. They are not recoverable. These replacements exercise the same contract shapes, evidence kinds, input/output structures, and mutation needles as the originals so the full compiler suite is green and reproducible from a fresh checkout.

They are NOT recorded provider outputs; do not cite them as such.
