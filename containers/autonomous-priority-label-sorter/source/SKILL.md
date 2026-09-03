---
name: Autonomous Priority Label Sorter
description: Clean and sort a bounded list of priority labels as an unattended production pipeline proof.
---

# Autonomous Priority Label Sorter

Build a `pure_data` workflow for a bounded list of priority labels. This is the third-generation unattended production proof.

## Input

Accept a JSON object with exactly one required field:

- `labels`: an array containing 1 to 10 strings, each containing 1 to 50 printable ASCII characters before trimming.

No additional fields are allowed.

## Deterministic operation

For every label:

1. Trim surrounding ASCII whitespace.
2. Reject the value if it becomes empty.
3. Reject control characters.
4. Sort the cleaned list using ASCII case-insensitive order with raw ASCII bytes as the tie-break.

Preserve cleaned spelling and duplicates. The result must not depend on locale, time, randomness, network access or external state.

## Output

Return exactly:

- `status`: the constant string `completed`.
- `sorted_labels`: the cleaned, deterministically sorted array.

## Fixture

Input:

```json
{"labels":[" Urgent ","backlog","Active"]}
```

Expected output:

```json
{"status":"completed","sorted_labels":["Active","backlog","Urgent"]}
```

## Authority boundary

Use only bounded deterministic `omo.pure-data/v1` operations: `input.get`, `text_list.normalize_ascii`, `text_list.sort_ascii`, and `result.object`.

This workflow requests no provider, network, shell, filesystem, credential, secret, repository, deployment or creator-authored executable code authority.
