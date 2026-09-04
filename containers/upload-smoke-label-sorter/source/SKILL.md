---
name: Upload Smoke Label Sorter
description: Deterministically sort a short label list without any AI provider.
---

# Upload Smoke Label Sorter

Build a `pure_data` workflow for a bounded list of labels. This is a deterministic upload-to-workflow smoke test and must not use Gemini, any other provider, network access, tools, code execution, credentials, or external state.

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
5. Preserve cleaned spelling and duplicates.

The result must not depend on locale, language settings, wall-clock time, randomness, or external state.

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
