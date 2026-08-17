# PhonicsMaker core runtime source layer

This directory preserves the actual PhonicsMaker core engine for the Omo
runtime port. It is not a generic prompt wrapper and it is not registered or
deployed yet.

## Source of truth

- Source repository: `/root/work/phonicsmaker/core`
- Source commit: recorded in `SOURCE-PROVENANCE.json`
- Copied files: tracked engine/runtime source, templates, static assets,
  dependencies, entrypoints and source tests
- Excluded: `.env*`, draft/customer data, logs, caches and Git metadata

Every copied file is SHA-256 checked against the source checkout by
`tests/test_source_provenance.py`.

## Intended Omo placement

The next adapter will expose this source layer through a dedicated
`phonicsmaker_core` execution kind and Omo's authenticated submit/poll,
private artifact, billing and marketplace contracts. The adapter must preserve
the source teacher inputs and output artifacts; it must not replace the book,
worksheet, activity, audio, image or export engines with a single LLM prompt.

Current status: **source-preserved, adapter not built, not chargeable, not live**.
