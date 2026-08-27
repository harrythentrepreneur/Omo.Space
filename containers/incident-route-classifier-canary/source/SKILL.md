---
name: Incident Route Classifier Canary
description: Classify a bounded incident summary into one of four operational routes.
---

# Incident Route Classifier Canary

Build a `single_llm` workflow that classifies a short operational incident summary into one closed route and gives a concise rationale.

## Input

Accept a JSON object with exactly:

- `summary`: a required string from 10 to 800 Unicode code points.
- `customer_impacting`: a required boolean.

No additional fields are allowed.

## Model task

Choose exactly one route:

- `security` — suspected credential exposure, unauthorized access, data exfiltration, malware, or deliberate abuse.
- `reliability` — outage, severe degradation, crash loop, unavailable dependency, timeout, or data-processing failure without evidence of abuse.
- `billing` — incorrect charge, payment, invoice, subscription, credit, or refund behavior without evidence of compromise.
- `support` — user guidance, configuration confusion, or ordinary product assistance that does not fit the other routes.

When more than one route appears plausible, prefer `security`, then `reliability`, then `billing`, then `support`.

## Output

Return exactly these domain fields:

- `route`: one of `security`, `reliability`, `billing`, or `support`; maximum 11 Unicode code points.
- `rationale`: one plain sentence from 10 to 240 Unicode code points grounded only in the supplied summary and impact flag.

Do not include transport fields; the platform owns those.

## Fixtures

Positive fixture:

Input:

```json
{"summary":"Several customers cannot open the dashboard because API requests time out.","customer_impacting":true}
```

Expected constraints:

- `route` is `reliability`.
- `rationale` mentions the observed timeout or dashboard unavailability and invents no facts.

Negative fixture:

```json
{"summary":"short","customer_impacting":false}
```

must fail input validation before any provider call.

## Authority boundary

Use the compiler-owned Gemini single-LLM transport, model, prompt boundary, credentials, input cap, corrective-call limit, pricing, resources and runtime placement. This workflow requests no provider URL, model selection, credential, secret name, network target, shell, filesystem, deployment, repository, branch, revision, release-policy, resource override, arbitrary executable code, or generated runtime code.
