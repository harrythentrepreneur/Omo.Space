---
name: V02 Release Label Sorter
description: Clean and deterministically sort a bounded list of release labels for a production lifecycle proof.
---

# V02 Release Label Sorter

Build a `pure_data` workflow for a bounded list of release labels.

## Input

Accept a JSON object with exactly one required field:

- `labels`: an array containing 1 to 12 strings, each containing 1 to 60 printable ASCII characters before trimming.

No additional fields are allowed.

## Deterministic operation

For every label:

1. Trim surrounding ASCII whitespace.
2. Reject the value if it becomes empty.
3. Reject control characters.
4. Sort the cleaned list using ASCII case-insensitive order with raw ASCII bytes as the tie-break.

Preserve cleaned spelling and duplicates.

## Output

Return exactly:

- `status`: the constant string `completed`.
- `sorted_labels`: the cleaned, deterministically sorted array.

## Fixtures

Input:

```json
{"labels":[" Stable ","alpha","Beta"]}
```

Expected output:

```json
{"status":"completed","sorted_labels":["alpha","Beta","Stable"]}
```

A label containing only spaces must fail with `INVALID_VALUE`.

## Authority boundary

Use only the platform's bounded deterministic `omo.pure-data/v1` operations: `input.get`, `text_list.normalize_ascii`, `text_list.sort_ascii`, and `result.object`.

This workflow requests no provider, network, shell, filesystem, credential, secret, repository, deployment, or generated-code authority.
