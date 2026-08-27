---
name: Release Tag Sorter Canary
description: Clean and deterministically sort a bounded list of software release tags.
---

# Release Tag Sorter Canary

Build a `pure_data` workflow for a bounded list of software release tags.

## Input

Accept a JSON object with exactly one required field:

- `tags`: an array containing 1 to 20 strings, each from 1 to 80 Unicode code points.

No additional fields are allowed.

## Deterministic operation

For every tag:

1. Trim surrounding ASCII whitespace.
2. Reject the value if it becomes empty.
3. Reject control characters.
4. Sort the cleaned list using ASCII case-insensitive order with raw ASCII bytes as the tie-break.

Preserve the cleaned spelling and preserve duplicates. Do not infer semantic-version precedence.

## Output

Return exactly:

- `status`: the constant string `completed`.
- `sorted_tags`: the cleaned, deterministically sorted array containing 1 to 20 strings.

## Fixtures

Positive fixture:

Input:

```json
{"tags":[" v2.0.0 ","V1.0.0","beta_1"]}
```

Expected output:

```json
{"status":"completed","sorted_tags":["beta_1","V1.0.0","v2.0.0"]}
```

Negative fixture:

```json
{"tags":[" "]}
```

must fail with `INVALID_VALUE`.

## Authority boundary

Use only the platform's existing bounded deterministic `omo.pure-data/v1` operations:

- `input.get`
- `text_list.normalize_ascii`
- `text_list.sort_ascii`
- `result.object`

This workflow requests no provider, model, network, shell, filesystem, credential, secret, pricing, resource, deployment, repository, branch, revision, release-policy, or generated-code authority.
