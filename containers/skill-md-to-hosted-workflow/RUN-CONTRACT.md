# Skill.md to Hosted Workflow — V1 run contract

Status: draft only; not active, chargeable, registered, or deployed.

This document defines how one paid marketplace run will map to the existing builder pipeline after the coordinator approves the builder hosting gate. It is a contract, not a runnable container. V1 may use a manual operator path or an intake bridge behind the same observable state machine. No `modal_app.py`, deployment claim, or fabricated automation is included here.

## Service boundary

One run accepts one `SKILL.md` document and returns one build result. The submitted document is hostile data: the intake and builder must never execute, import, evaluate, source, install from, or follow commands embedded in it. The service may parse bounded text and generate files in an isolated build workspace.

The intended customer price is USD $5.00 per run. Typical provider calls have sub-cent economics; the price also covers intake validation, compilation work, tests, pricing, hosting attempts, and a typed result. The product-level hosting bar is approximately 70% across a rolling submission set, not a promise that every individual skill will become live.

## Paid-run state mapping

1. **Queue.** After payment authorization and validation, the intake bridge creates an idempotent run record and returns `status: "queued"`. A repeated delivery of the same paid request must claim the existing run rather than charge or enqueue twice.
2. **Claim.** One worker or operator atomically claims the run, records the builder version and resume point, and moves it to `status: "building"`.
3. **Build.** The builder parses the document as untrusted text, derives a listing/profile, validates schemas, estimates provider cost, runs the applicable offline and provider tests, and attempts the approved hosting path. External accounts, credentials, network services, or media renderers are never assumed to exist.
4. **Result.** A successful hosting gate returns `status: "live"`, the canonical slug and listing URL, and build metadata. An unsupported or incomplete build returns `status: "blocked"` with one typed blocker containing the exact reason, retained evidence, and the precise resume point. There are no silent skips.

Queue and claim may be automated while build and result recording remain manual in V1. The bridge must expose the same statuses and output schema either way. Manual completion does not justify marking a listing live until the coordinator's activation gate passes.

## Intake validation

Validation happens before queueing and before any build tool sees the document.

- Require `skill_md` to be a string from 1 through 20,000 Unicode characters.
- Reject NUL bytes and malformed request JSON.
- Treat all content, including front matter and fenced code, as inert data.
- Reject likely credentials rather than redacting and continuing. At minimum, scan case-insensitively for PEM private-key headers, cloud/provider access-key formats, bearer or basic authorization values, JWT-like tokens, assignments or YAML fields named `api_key`, `apikey`, `access_token`, `refresh_token`, `client_secret`, `password`, or `passwd`, and common secret prefixes such as `sk-`, `ghp_`, `github_pat_`, `xox[baprs]-`, and `AKIA` followed by key material.
- A credential-pattern rejection must occur before payment capture where the payment flow allows it. If discovered only after capture, fail closed and use the refund policy below.
- Never print the matching value. Evidence may name only the pattern class and character range, for example `bearer authorization pattern at characters 418–462`.
- Optional text fields are display hints, not instructions: `display_name` is at most 120 characters and `category` is at most 80 characters. `price_guidance_usd` is advisory, from 0 through 10,000, and cannot override the builder's honest cost/pricing review.

## Input schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "skill_md": {
      "type": "string",
      "minLength": 1,
      "maxLength": 20000,
      "description": "The complete SKILL.md content. Treated as hostile data and never executed."
    },
    "display_name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 120
    },
    "category": {
      "type": "string",
      "minLength": 1,
      "maxLength": 80
    },
    "price_guidance_usd": {
      "type": "number",
      "minimum": 0,
      "maximum": 10000
    }
  },
  "required": ["skill_md"]
}
```

The JSON Schema enforces shape and bounds. The credential-pattern checks above are a separate semantic validation gate and are mandatory.

## Output schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "status": {
      "enum": ["queued", "building", "blocked", "live"]
    },
    "listing_url": {
      "type": ["string", "null"],
      "format": "uri"
    },
    "slug": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100,
      "pattern": "^[a-z0-9][a-z0-9-]*$"
    },
    "typed_blocker": {
      "anyOf": [
        { "type": "null" },
        {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "reason": { "type": "string", "minLength": 1, "maxLength": 500 },
            "evidence": {
              "type": "array",
              "minItems": 1,
              "maxItems": 20,
              "items": { "type": "string", "minLength": 1, "maxLength": 1000 }
            },
            "resume_point": { "type": "string", "minLength": 1, "maxLength": 500 }
          },
          "required": ["reason", "evidence", "resume_point"]
        }
      ]
    },
    "build_meta": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "version": { "type": "string", "minLength": 1, "maxLength": 100 },
        "cost": {
          "type": "number",
          "minimum": 0,
          "description": "Measured provider cost in USD; this is not the customer price."
        },
        "tests_passed": {
          "type": "array",
          "maxItems": 100,
          "items": { "type": "string", "minLength": 1, "maxLength": 200 }
        }
      },
      "required": ["version", "cost", "tests_passed"]
    }
  },
  "required": ["status", "listing_url", "slug", "typed_blocker", "build_meta"]
}
```

State invariants:

- `typed_blocker` must be non-null exactly when `status` is `blocked`.
- `listing_url` must be a canonical HTTPS Omo workflow URL when `status` is `live`; it may be null otherwise.
- `tests_passed` names only tests that actually completed successfully.
- `cost` records measured provider cost in USD, including zero; it does not report or imply the $5 customer charge.

## Typed blockers, refunds, and resume

Expected blockers include a required external account, an unavailable or unapproved media renderer, a missing platform capability, unsafe credential-bearing input, an unsupported runtime, or a failed quality/hosting gate. The response must name the exact blocker, retain non-secret evidence, and identify the next safe pipeline step in `resume_point`.

If a paid run ends `blocked` without a hosted listing, Omo refunds the $5.00 build fee. The run record and non-secret build evidence remain available for resumption from the recorded point after the blocker is cleared. Resumption does not silently charge or retry: any new charge, if applicable, must be disclosed and authorized before work resumes. Provider usage already incurred is not separately billed to the customer.

## Activation gate

This draft must remain absent from `OMO_VISIBLE_SLUGS` and from the live-only sitemap. It cannot accept payment, be dispatched, or claim a live URL until the coordinator confirms the builder hosting gate and explicitly activates the listing.
