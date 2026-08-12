---
name: woven-storybook-pipeline
description: "Private document pipeline declaration; fail closed until source and privacy controls are approved."
version: 1.0.0
metadata:
  bench:
    id: woven-storybook-pipeline
    input_schema:
      document_ref: string
    output_schema:
      status: string
    runtime:
      class: private-document-pipeline
      adapter: unavailable-private-source-v1
      source_repository: unavailable
      data_mode: fixture-only
      privacy_isolation: required
      retention_controls: required
      real_data_approval: required
---
# Woven Storybook Pipeline

Transform private message exports into an evidence-grounded keepsake storybook. This repository contains only a sanitized workflow declaration, not the referenced implementation or any chat data.

## Core mechanics retained as specification

- Never fabricate dialogue: quotes must match source bytes and every visible claim needs provenance.
- Parse with a high acceptance gate; quarantine timestamp-like failures rather than folding them into messages.
- Preserve month coverage, archive boundaries, chapter continuity, monotonic symbol state and page-role distribution.
- Derive symbols from recurrence evidence and disconfirming samples; never impose themes.
- Validate provenance, distribution, continuity, temporal coverage and rendering before delivery.

## Fail-closed privacy boundary

The external source repository is unavailable. Development must remain fixture-only. Real documents require isolated private workspaces, explicit retention/deletion controls and approval before processing. The compiler must return stable unsupported reason codes and must not create a runtime package.
