# One Modal workflow, end to end: container-agent technical plan

**Status:** analysis and implementation plan only; no deployable files were created  
**Repository snapshot analyzed:** 2026-08-09  
**Target:** one API-activated workflow that starts compute on demand, completes the work, returns a typed result, and scales back to zero

## Executive decision

Build the full **HeyGen UGC workflow** first, not the cheapest pure-LLM listing.

The pure-LLM UGC Script Studio is the lower-risk smoke test, and its Cloudflare implementation already proves the prompt and output normalizer. It would prove that Modal can receive an HTTP request and call an LLM, but little else. The HeyGen workflow proves the pieces that matter before expanding to 15 workflows: ordered data flow, two provider adapters, an asynchronous paid API, idempotency, polling, schema validation, result retrieval, secret isolation, and quality gates. It remains CPU-only on Modal because DeepSeek and HeyGen are remote APIs; a Modal GPU would add cost without doing useful work.

The recommended first production shape is:

1. A persistent Modal deployment containing two scale-to-zero Functions: an authenticated FastAPI control endpoint and a background workflow runner.
2. `POST /v1/runs` validates input, spawns the runner, and immediately returns `202` with a Modal call ID.
3. The runner calls the repository's OpenAI-compatible DeepSeek route, submits one HeyGen v3 video job with an idempotency key, generates captions, polls HeyGen, validates the final object, and returns it.
4. `GET /v1/runs/{call_id}` returns `202` while running and the typed final JSON when complete.
5. With `min_containers=0` and `scaledown_window=2`, compute scales to zero after the work. The deployed App and its URL remain live; the App is **not** deployed and destroyed on every request.

For the later 15-workflow system, do not let an agent invent arbitrary Python or Dockerfiles per post. Let the agent produce a constrained, provenance-bearing `container.yaml`; validate it; and pass it to a deterministic compiler plus a small, reviewed provider-adapter runtime.

## 0. What exists in this repository, and what does not

### Existing pieces worth preserving

- [`site/deploy/cost-model.mjs`](../site/deploy/cost-model.mjs) defines LLM rates, approximate external API line items, `MARKUP = 1.25`, and `runPrice = max(cost * 1.25, 0.10)` rounded to cents.
- [`site/deploy/workflows.mjs`](../site/deploy/workflows.mjs) defines the concrete HeyGen UGC sequence: script LLM, avatar render, voiceover, and captions LLM.
- [`site/deploy/worker.js`](../site/deploy/worker.js) contains an actual OpenAI-compatible LLM adapter, request validation, JSON recovery/normalization, CORS handling, and the generic `/api/run` route.
- [`packages/ugc-script-studio/SKILL.md`](../packages/ugc-script-studio/SKILL.md) demonstrates useful SKILL.md metadata: name, description, inputs, outputs, runtime model, limits, version, and prose flow.
- [`site/ig-workflows.js`](../site/ig-workflows.js) and [`site/ig-more.js`](../site/ig-more.js) contain 21 listing objects with 22 LLM steps and 30 API-step declarations. Only two listings are LLM-only. Their current precomputed run prices range from `$0.10` to `$0.35`.
- [`site/deploy/DEPLOY.md`](../site/deploy/DEPLOY.md) documents the current Cloudflare demo surface and supplies useful smoke-test inputs.

### The central gap

The catalog `workflow` objects are **not executable workflow definitions yet**. They are prompt-and-cost declarations.

In particular:

- `api: "replicate_run"`, `api: "e2b_sandbox"`, or `api: "heygen_avatar_render"` identifies a price bucket but not an endpoint, model/version, request mapping, credential, retry policy, or result mapping.
- Listing `inputs` and `outputs` are arrays of display strings, not machine-valid JSON Schemas.
- Steps have no stable IDs, dependencies, input bindings, or output schemas.
- The catalog has no explicit final-output projection.
- `qty` is useful for cost estimation but does not specify whether to make calls serially, concurrently, or as a batch.
- System prompts live in several places. The hardened UGC prompt in `worker.js` is not the same shape as the script prompt in `workflows.mjs` (`shots` versus `lines`). This is already source-of-truth drift.
- The cost model counts `heygen_avatar_render` and `heygen_voiceover` separately. The current HeyGen v3 Create Video request accepts `script` and `voice_id` together, so those are two accounting line items but normally one provider mutation.

Therefore the missing product is not “a Docker wrapper.” It is a **canonical specification, validator/compiler, provider adapter registry, deployment controller, and QA gate**.

## 1. Correct Modal mental model

Modal's [`modal deploy`](https://modal.com/docs/guide/managing-deployments) creates a persistent App definition, image, Function definitions, and stable web URL. It does not keep a dedicated container running indefinitely.

```text
modal deploy once
      │
      ▼
persistent App + image + endpoint metadata
      │
      ├── first request ──► cold-start API container
      │                       │
      │                       └── spawn background runner container
      │                                  │
      │                                  └── LLM → HeyGen → validation
      │
      └── idle ───────────► containers scale to zero; endpoint remains addressable
```

Modal says base container boot is about one second, but full warm-up can take seconds to minutes if imports, image pulls, or model loading are heavy. The default maximum idle period before shutdown is 60 seconds; `scaledown_window` can be set from 2 seconds to 20 minutes. `min_containers=0` permits scale-to-zero. See [cold-start performance](https://modal.com/docs/guide/cold-start) and [autoscaling](https://modal.com/docs/guide/scale).

This leads to four design rules:

1. **Deploy once, invoke many times.** Never run `modal deploy` in the buyer's request path.
2. **Scale to zero, do not stop the App.** `modal app stop` destroys the deployment and stable URL; it is not a per-run cleanup operation.
3. **Do not promise “the container closes immediately.”** Configure `scaledown_window=2`; Modal controls the actual autoscaler and may reuse or terminate containers according to capacity.
4. **Use CPU for API orchestration.** Set `gpu` only when inference/rendering truly runs inside the Modal Function.

## 2. Container-agent pipeline

### 2.1 Control plane versus data plane

Separate the machinery that creates deployments from the machinery that handles buyer runs.

| Plane | Responsibilities | Trust level |
|---|---|---|
| Ingestion | Fetch an authorized post/repository/SKILL.md, preserve source evidence, transcribe, identify claimed steps | Untrusted content |
| Spec agent | Convert evidence into a draft canonical spec with confidence and unresolved fields | Constrained generation |
| Compiler | Parse, schema-check, resolve adapters, generate Modal source from reviewed templates, calculate a digest | Trusted deterministic code |
| Deployer | Build and deploy to a Modal staging environment using a service-user token | High privilege |
| Runtime | Validate input, execute allowlisted adapters, validate output, record usage | Production data plane |
| QA/publisher | Test the deployed endpoint, produce a signed report, promote catalog status | Controlled state mutation |

An extracted post must never directly become shell commands, a Dockerfile, Python code, package names, or secrets. Treat captions, transcripts, READMEs, and SKILL.md bodies as untrusted data, including instructions that look like agent directives.

### 2.2 End-to-end compilation flow

1. **Acquire and fingerprint the source**
   - Store source URL, source type, author, retrieval timestamp, content hash, license/permission state, raw caption/transcript/README, and referenced asset hashes.
   - Do not publish when rights or provenance are unresolved.

2. **Parse the workflow surface**
   - For a storefront object: read `slug`, `name`, `inputs`, `outputs`, `workflow.steps`, `runPrice`.
   - For SKILL.md: parse YAML frontmatter with a safe YAML parser, then extract the body sections as documentation/evidence.
   - For a repository: prefer an explicit manifest; otherwise inspect documented entrypoints and examples. Do not execute its code during extraction.

3. **Normalize into `container.yaml`**
   - Give every step a stable ID.
   - Replace display strings with JSON Schema.
   - Resolve provider and operation names through an allowlist.
   - Add data bindings, output schemas, retry/idempotency rules, timeouts, resource limits, egress domains, and the final projection.
   - Mark inferred values with confidence and provenance. Unresolved provider operations are compiler errors, not defaults.

4. **Static validation and policy**
   - Validate the spec against `container-spec.schema.json`.
   - Reject duplicate step IDs, dependency cycles, undeclared environment keys, secret-looking literals, unknown adapters/models, unbounded loops, arbitrary URLs, and resource/budget excess.
   - Confirm every final output is reachable from an input or step output.

5. **Resolve an execution plan**
   - Topologically sort steps.
   - Identify safe concurrency; for example, captions can run after HeyGen submission while rendering continues.
   - Convert logical cost steps to physical calls. For HeyGen v3, avatar rendering and synthesized voice are one create call but retain two ledger line items if that matches marketplace accounting.

6. **Generate a Modal App from reviewed templates**
   - Produce `modal_app.py` from a versioned runtime template.
   - Build a `modal.Image.debian_slim(...).uv_pip_install(...)`, or use a reviewed registry image when native/system dependencies require it.
   - Embed the immutable spec, prompt assets, and schema files into the image and label the result with `spec_hash`, source hash, compiler version, and workflow version.
   - Modal Images are already container images; a handwritten Dockerfile is optional, not the default.

7. **Wire secrets by name**
   - The generated code contains only `modal.Secret.from_name("cognition-ugc-heygen")`.
   - The deploy environment provides `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, and `HEYGEN_API_KEY` as environment variables.
   - Never bake secrets into the image, spec, prompt, logs, test fixtures, or endpoint response.

8. **Deploy to staging**
   - Authenticate CI with a Modal service-user token via `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`.
   - Run `modal deploy -e staging --tag <spec-hash> containers/ugc-heygen/modal_app.py`.
   - Record the deployment version and URL returned by Modal.

9. **Test the actual HTTPS surface**
   - Submit valid, invalid, boundary, retry, and provider-failure cases.
   - Validate status and final response bodies against the public schemas.
   - Enforce cost, latency, content, and artifact checks.

10. **Promote catalog state**
    - Store the immutable QA report.
    - Atomically switch a workflow from `staging` to `live` only when all required gates pass.
    - Keep the previous healthy version available for rollback. Modal deployment rollbacks are plan-dependent, so also retain reproducible source/spec tags.

### 2.3 Recommended deployment topology for one, then 15

For workflow #1, use one Modal App with one API Function and one runner Function. It is easy to understand and isolates secrets, limits, logs, and failures.

For 15 workflows, retain one logical deployment per workflow initially, but compile all of them against the **same runtime package and base image**. That prevents 15 forks of provider code. If image duplication or deployment management becomes painful, move to one multi-workflow runtime whose registry loads immutable specs by hash; do not make that optimization before workflow #1 is measured.

A Hermes profile belongs in the **control plane**, where it can select the extraction/spec agent's model, reasoning level, tools, and review policy. It should not be the production data-plane contract: profiles are broader, mutable agent configuration, whereas buyer runs need a small immutable DAG with bounded tools and a stable schema. If a profile materially affects extraction, record its version/hash in provenance. Never place Modal deployment authority or production provider secrets in the post-extraction agent's profile.

## 3. `SKILL.md → container` bridge

### 3.1 What can map automatically

The current UGC SKILL.md can supply:

| SKILL.md source | Container-spec target |
|---|---|
| `name`, `description`, `version` | identity and version |
| `metadata.bench.id` | slug |
| `metadata.bench.input_schema` | draft JSON Schema properties |
| `metadata.bench.output_schema` | draft output JSON Schema properties |
| `metadata.bench.runtime.model` | LLM model |
| `demo_caps` | token, step, and request policy |
| “How it works” body | human-readable step evidence |
| example input/output | seed QA case, never an automatic golden truth |

### 3.2 What cannot map safely without more information

A SKILL.md body is documentation, not an executable DAG. “Extract,” “draft,” and “deliver” might mean three LLM calls, one prompt with three reasoning phases, or local deterministic code. The current UGC SKILL.md also does not contain the hardened system prompt; that lives in `worker.js`.

The bridge should therefore behave as follows:

- If explicit executable metadata is present, compile it.
- If only prose is present, produce a `draft` spec and a list of unresolved questions.
- If `max_steps_per_session: 1`, default prose substeps to one LLM call unless the author explicitly defines provider calls.
- Never infer a paid external API from a tool name in prose and immediately publish it.
- Make the canonical spec the source of truth, then generate both Modal and any future Cloudflare adapter from it. Do not keep manually synchronized prompts in three files.

### 3.3 Minimal executable container spec

The requested core fields are present below, but an actually executable minimum also needs stable step IDs, bindings, adapter operations, timeouts/idempotency, resource policy, and tests. JSON Schema is used for contracts; free-form strings such as `"brief: product or topic"` are not sufficient.

```yaml
spec_version: cognition.container/v1
name: UGC HeyGen Video
slug: ugc-heygen-video
version: 0.1.0

source:
  kind: repository
  path: site/deploy/workflows.mjs
  content_hash: sha256:<filled-by-compiler>

image:
  base: debian-slim
  python: "3.12"
  packages:
    - fastapi[standard]
    - httpx
    - pydantic
    - jsonschema

gpu: null                 # remote DeepSeek + remote HeyGen; Modal GPU is unnecessary
resources:
  cpu: 0.25
  memory_mb: 512
  timeout_seconds: 1200
  min_containers: 0
  max_containers: 10
  scaledown_window_seconds: 2

endpoint:
  mode: async_job
  auth: modal_proxy_token
  submit_path: /v1/runs
  result_path: /v1/runs/{call_id}

env_keys:
  - LLM_API_KEY
  - LLM_BASE_URL
  - LLM_MODEL
  - HEYGEN_API_KEY

egress_allowlist:
  - opencode.ai             # or the approved LLM_BASE_URL host
  - api.heygen.com

input_schema:
  type: object
  additionalProperties: false
  required: [product_description, brand_voice, length_seconds, avatar_id, voice_id]
  properties:
    product_description: {type: string, minLength: 10, maxLength: 2000}
    brand_voice: {type: string, enum: [raw, honest, hype, luxury, funny]}
    length_seconds: {type: integer, enum: [15, 30, 60]}
    avatar_id: {type: string, minLength: 1, maxLength: 200}
    voice_id: {type: string, minLength: 1, maxLength: 200}

steps:
  - id: script
    type: llm
    provider: openai_compatible
    model: deepseek-v4-flash
    system_prompt: prompts/script.txt
    user_template: prompts/script-user.txt
    params: {max_output_tokens: 700, temperature: 0.2}
    input_bindings:
      product_description: $.input.product_description
      brand_voice: $.input.brand_voice
      length_seconds: $.input.length_seconds
    output_schema: schemas/script.json

  - id: video
    type: api
    provider: heygen
    operation: v3.videos.create_and_wait
    depends_on: [script]
    params:
      aspect_ratio: "9:16"
      resolution: 1080p
      poll_seconds: 10
      max_wait_seconds: 900
    input_bindings:
      avatar_id: $.input.avatar_id
      voice_id: $.input.voice_id
      script: $.steps.script.output
    idempotency_key: $.run.id
    cost_tags: [heygen_avatar_render, heygen_voiceover]
    output_schema: schemas/heygen-video.json

  - id: captions
    type: llm
    provider: openai_compatible
    model: deepseek-v4-flash
    depends_on: [script]
    system_prompt: prompts/captions.txt
    params: {max_output_tokens: 300, temperature: 0.2}
    input_bindings:
      script: $.steps.script.output
    output_schema: schemas/captions.json

output_projection:
  run_id: $.run.id
  status: {literal: completed}
  workflow_version: $.spec.version
  script: $.steps.script.output
  captions: $.steps.captions.output.captions
  video: $.steps.video.output
  usage: $.run.usage

output_schema:
  type: object
  additionalProperties: false
  required: [run_id, status, workflow_version, script, captions, video, usage]
  properties:
    run_id: {type: string}
    status: {const: completed}
    workflow_version: {type: string}
    script:
      type: object
      required: [hook, lines, cta]
      properties:
        hook: {type: string, minLength: 1}
        lines: {type: array, minItems: 1, items: {type: string, minLength: 1}}
        cta: {type: string, minLength: 1}
    captions: {type: array, minItems: 1, items: {type: string, minLength: 1}}
    video:
      type: object
      required: [video_id, video_url, duration_seconds]
      properties:
        video_id: {type: string}
        video_url: {type: string, format: uri}
        thumbnail_url: {type: [string, "null"], format: uri}
        subtitle_url: {type: [string, "null"], format: uri}
        duration_seconds: {type: number, minimum: 1, maximum: 90}
    usage:
      type: object
      required: [estimated_cost_usd, buyer_run_price_usd]
      properties:
        estimated_cost_usd: {type: number, minimum: 0}
        buyer_run_price_usd: {type: number, minimum: 0}

tests:
  - id: silk-pillowcase-happy-path
    input_fixture: tests/silk-pillowcase.input.json
    assertions:
      - schema: output_schema
      - semantic: captions_length_equals_script_lines
      - semantic: no_unsupported_product_claims
      - media: duration_within_requested_band

budget:
  max_estimated_cost_usd: 0.20
  max_provider_retries: 2
  max_total_steps: 3
```

The compiler should support only a small expression language for bindings (`$.input...`, `$.steps...`, `$.run...`, `$.spec...`) plus explicit literal values. Do not allow Python, shell, JavaScript, Jinja execution, or arbitrary network URLs inside a spec.

## 4. Workflow #1: HeyGen UGC end to end

### 4.1 Why this workflow

**Recommendation:** use the full HeyGen UGC path as workflow #1, while keeping a `render_video=false` or adapter-mock mode only in staging tests.

Reasons:

- It tests the reusable architecture rather than merely duplicating the existing Cloudflare LLM demo.
- Its repository cost is still small enough for controlled tests: about `$0.12045` per estimated run before Modal orchestration overhead.
- It exposes the asynchronous-job problem now, before 15 workflows depend on a synchronous endpoint assumption.
- It makes the catalog's cost-step versus executable-step mismatch visible and fixable.
- No Modal GPU is required, so cold start and infrastructure cost remain modest.

The pure-LLM UGC Script Studio remains the day-one canary: call the same script adapter with the same schema before spending HeyGen credits. It is a test mode of workflow #1, not a separate live product.

### 4.2 Public API contract

#### Submit

`POST /v1/runs`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "product_description",
    "brand_voice",
    "length_seconds",
    "avatar_id",
    "voice_id"
  ],
  "properties": {
    "product_description": {
      "type": "string",
      "minLength": 10,
      "maxLength": 2000
    },
    "brand_voice": {
      "type": "string",
      "enum": ["raw", "honest", "hype", "luxury", "funny"]
    },
    "length_seconds": {
      "type": "integer",
      "enum": [15, 30, 60]
    },
    "avatar_id": {"type": "string", "minLength": 1, "maxLength": 200},
    "voice_id": {"type": "string", "minLength": 1, "maxLength": 200}
  }
}
```

Successful submission:

```json
{
  "run_id": "6c66ea4f-985e-4e95-8eae-f0e31a0e5b80",
  "call_id": "fc-...",
  "status": "accepted",
  "result_url": "/v1/runs/fc-..."
}
```

HTTP status is `202`. Rejected input uses FastAPI's `422`; authentication failure is `401`; admission-control or per-user quota failure should be `429`.

Before accepting paid traffic, also require a client `Idempotency-Key` header. Store `tenant_id + key → request_hash + run_id + call_id` under a unique constraint. A repeat with the same body returns the original identifiers; reuse with a different body returns `409`. The code sketch below protects **runner retries** at HeyGen, but its compact in-memory submit example does not implement this durable client-request deduplication.

#### Poll result

`GET /v1/runs/{call_id}`

While running, return `202`:

```json
{"call_id": "fc-...", "status": "running"}
```

On success, return `200`:

```json
{
  "run_id": "6c66ea4f-985e-4e95-8eae-f0e31a0e5b80",
  "status": "completed",
  "workflow_version": "ugc-heygen@0.1.0",
  "script": {
    "hook": "I thought a $60 pillowcase was ridiculous.",
    "lines": [
      "Then I tried it for 30 nights.",
      "The silk feels cool, and the brand says it is hypoallergenic."
    ],
    "cta": "Try it for 30 nights and decide for yourself."
  },
  "captions": ["30 nights later", "cool silk, honest review"],
  "video": {
    "video_id": "vid_xyz789",
    "video_url": "https://files.heygen.ai/video/vid_xyz789.mp4",
    "thumbnail_url": "https://files.heygen.ai/thumb/vid_xyz789.jpg",
    "subtitle_url": "https://files.heygen.ai/srt/vid_xyz789.srt",
    "duration_seconds": 29.8
  },
  "usage": {
    "estimated_cost_usd": 0.12045,
    "buyer_run_price_usd": 0.15
  }
}
```

The result schema should allow provider URLs to be nullable while processing, but the **completed** result must require a video URL. The semantic validator must additionally require `captions.length === script.lines.length`; standard JSON Schema does not express that cross-array invariant cleanly.

HeyGen returns presigned media URLs. For a durable product, copy the final MP4, thumbnail, and subtitle to marketplace-owned object storage and return stable URLs. Returning the provider URL directly is acceptable only for the first smoke test.

### 4.3 Modal App sketch

This is a design sketch for a future file. Name the actual file `modal_app.py`, **not `modal.py`**, because a local `modal.py` can shadow the installed `modal` SDK during imports. Pin tested dependency versions before the real deployment.

The current Modal decorator is `@modal.fastapi_endpoint`; `@modal.web_endpoint` was its pre-`0.73.82` name. For a submit and status API, an ASGI FastAPI app is cleaner.

```python
# Future file: containers/ugc-heygen/modal_app.py
import json
import os
import time
import uuid

import modal

APP_NAME = "cognition-ugc-heygen"
WORKFLOW_VERSION = "ugc-heygen@0.1.0"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "fastapi[standard]",
        "httpx",
        "pydantic",
        "jsonschema",
    )
    # The compiler should add immutable prompt/spec/schema files here with copy=True.
)

app = modal.App(APP_NAME)
provider_secrets = modal.Secret.from_name("cognition-ugc-heygen")

SCRIPT_SYSTEM = """You are a UGC ad script writer for ecommerce brands.
Return exactly one JSON object with hook, lines (a flat string array), and cta.
Use only claims supported by the product description. Match the requested voice.
Output JSON only; no markdown or commentary."""

CAPTIONS_SYSTEM = """Write short on-screen captions for a UGC video.
Return exactly {"captions": ["one short caption per script line"]}.
captions must be a flat string array with the same length as script.lines.
Output JSON only; no markdown or commentary."""

SCRIPT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["hook", "lines", "cta"],
    "properties": {
        "hook": {"type": "string", "minLength": 1},
        "lines": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {"type": "string", "minLength": 1},
        },
        "cta": {"type": "string", "minLength": 1},
    },
}

CAPTIONS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["captions"],
    "properties": {
        "captions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": {"type": "string", "minLength": 1},
        }
    },
}


def parse_json_object(raw: str) -> dict:
    """Tolerate fences/prose, then fail closed if no JSON object is valid."""
    cleaned = raw.strip().removeprefix("```json").removeprefix("```")
    cleaned = cleaned.removesuffix("```").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("LLM did not return a JSON object")
    value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("LLM output is not an object")
    return value


def call_llm(system: str, user: str, max_tokens: int) -> dict:
    import httpx

    base = os.environ.get("LLM_BASE_URL", "https://opencode.ai/zen/go/v1")
    response = httpx.post(
        f"{base.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"},
        json={
            "model": os.environ.get("LLM_MODEL", "deepseek-v4-flash"),
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=90.0,
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]
    return parse_json_object(raw)


@app.function(
    image=image,
    secrets=[provider_secrets],
    cpu=0.25,
    memory=512,
    timeout=1200,
    min_containers=0,
    max_containers=10,
    scaledown_window=2,
)
def run_workflow(payload: dict) -> dict:
    """Background data-plane execution; one call produces one final typed result."""
    import httpx
    from jsonschema import validate

    run_id = payload.pop("_run_id")
    script_user = (
        f"Product: {payload['product_description']}\n\n"
        f"Brand voice: {payload['brand_voice']}\n"
        f"Length: {payload['length_seconds']} seconds\n\n"
        "Write the UGC ad script now."
    )
    script = call_llm(SCRIPT_SYSTEM, script_user, max_tokens=700)
    validate(instance=script, schema=SCRIPT_SCHEMA)

    spoken_text = " ".join([script["hook"], *script["lines"], script["cta"]])

    # Current HeyGen v3 accepts script and voice_id in the same video mutation.
    # Reuse run_id so a retried Modal execution cannot buy a duplicate render.
    create = httpx.post(
        "https://api.heygen.com/v3/videos",
        headers={
            "X-Api-Key": os.environ["HEYGEN_API_KEY"],
            "Idempotency-Key": f"ugc:{run_id}",
        },
        json={
            "type": "avatar",
            "avatar_id": payload["avatar_id"],
            "voice_id": payload["voice_id"],
            "script": spoken_text,
            "title": f"UGC run {run_id}",
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "output_format": "mp4",
        },
        timeout=60.0,
    )
    create.raise_for_status()
    video_id = create.json()["data"]["video_id"]

    # This LLM call can execute while HeyGen renders.
    captions = call_llm(
        CAPTIONS_SYSTEM,
        "Script lines:\n" + "\n".join(script["lines"]),
        max_tokens=300,
    )
    validate(instance=captions, schema=CAPTIONS_SCHEMA)
    if len(captions["captions"]) != len(script["lines"]):
        raise ValueError("captions must have the same length as script.lines")

    deadline = time.monotonic() + 900
    while True:
        status_response = httpx.get(
            f"https://api.heygen.com/v3/videos/{video_id}",
            headers={"X-Api-Key": os.environ["HEYGEN_API_KEY"]},
            timeout=30.0,
        )
        status_response.raise_for_status()
        video = status_response.json()["data"]
        if video["status"] == "completed":
            break
        if video["status"] == "failed":
            raise RuntimeError(
                f"HeyGen failed: {video.get('failure_code', 'unknown')}"
            )
        if time.monotonic() >= deadline:
            # Avoid confusing this terminal provider failure with the TimeoutError
            # used below to mean "FunctionCall has no result yet."
            raise RuntimeError("HEYGEN_TIMEOUT: no result within 900 seconds")
        time.sleep(10)

    result = {
        "run_id": run_id,
        "status": "completed",
        "workflow_version": WORKFLOW_VERSION,
        "script": script,
        "captions": captions["captions"],
        "video": {
            "video_id": video_id,
            "video_url": video["video_url"],
            "thumbnail_url": video.get("thumbnail_url"),
            "subtitle_url": video.get("subtitle_url"),
            "duration_seconds": video["duration"],
        },
        "usage": {
            # The real runtime must populate this from its versioned cost/usage
            # ledger; constants are shown only to connect the repository math.
            "estimated_cost_usd": 0.12045,
            "buyer_run_price_usd": 0.15,
        },
    }
    # In the real runtime, validate result against the embedded final schema here.
    return result


@app.function(
    image=image,
    min_containers=0,
    max_containers=20,
    scaledown_window=2,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app(requires_proxy_auth=True)
def api():
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, ConfigDict, Field
    from typing import Literal

    web = FastAPI(title="Cognition UGC HeyGen", version="0.1.0")

    class RunInput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        product_description: str = Field(min_length=10, max_length=2000)
        brand_voice: Literal["raw", "honest", "hype", "luxury", "funny"]
        length_seconds: Literal[15, 30, 60]
        avatar_id: str = Field(min_length=1, max_length=200)
        voice_id: str = Field(min_length=1, max_length=200)

    @web.post("/v1/runs", status_code=202)
    async def submit(body: RunInput):
        run_id = str(uuid.uuid4())
        payload = body.model_dump()
        payload["_run_id"] = run_id
        call = run_workflow.spawn(payload)
        return {
            "run_id": run_id,
            "call_id": call.object_id,
            "status": "accepted",
            "result_url": f"/v1/runs/{call.object_id}",
        }

    @web.get("/v1/runs/{call_id}")
    async def result(call_id: str):
        call = modal.FunctionCall.from_id(call_id)
        try:
            return call.get(timeout=0)
        except TimeoutError:
            return JSONResponse(
                {"call_id": call_id, "status": "running"}, status_code=202
            )
        except Exception:
            # Log a trace ID internally; do not expose provider bodies or secrets.
            return JSONResponse(
                {
                    "call_id": call_id,
                    "status": "failed",
                    "error": {"code": "RUN_FAILED"},
                },
                status_code=500,
            )

    return web
```

The sketch deliberately uses polling inside the runner for the first proof. The HTTP request does not remain open, so Modal's Web Function request behavior does not constrain the render duration. The runner does consume low-cost CPU/memory while sleeping. The production optimization is a HeyGen webhook plus durable run state, not a long-lived polling container.

Modal Web Functions are public by default. `requires_proxy_auth=True` makes the endpoint require a Modal Proxy Token. Do not remove it for convenience.

### 4.4 Secrets and identity

Create one Modal Secret named `cognition-ugc-heygen` containing:

| Key | Purpose | Note |
|---|---|---|
| `LLM_API_KEY` | OpenAI-compatible LLM authorization | Existing repository uses an opencode/Zen Go key |
| `LLM_BASE_URL` | API base, currently `https://opencode.ai/zen/go/v1` | Non-secret configuration can still live in the Secret for one atomic binding |
| `LLM_MODEL` | `deepseek-v4-flash` | This is a repository/provider alias; verify it is supported by the selected base URL |
| `HEYGEN_API_KEY` | HeyGen v3 authorization | Sent only as `X-Api-Key` server-side |

`avatar_id` and `voice_id` are identifiers, not secret keys. Accept them in the first test request; later, expose a buyer-safe listing choice or resolve approved defaults from the spec.

Modal Secrets are injected through the `secrets=[...]` Function option and appear as environment variables inside the container. See [Modal Secrets](https://modal.com/docs/guide/secrets). Use a Modal Proxy Token, created in workspace settings, to protect the HTTP surface; callers send `Modal-Key` and `Modal-Secret` headers or a combined bearer token. See [Proxy Tokens](https://modal.com/docs/guide/webhook-proxy-auth).

Do not log full request headers, provider error bodies, product URLs containing query credentials, raw API keys, or complete LLM/provider responses. Secret rotation should trigger an App rollover if clients are initialized at container startup.

### 4.5 Deploy and call

Future commands, after the planned files exist:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'modal>=1,<2' jsonschema pytest
modal setup
```

Create the provider Secret from exported local variables, or use the Modal dashboard. Do not paste literal values into a committed script:

```bash
modal secret create cognition-ugc-heygen \
  LLM_API_KEY="$LLM_API_KEY" \
  LLM_BASE_URL="https://opencode.ai/zen/go/v1" \
  LLM_MODEL="deepseek-v4-flash" \
  HEYGEN_API_KEY="$HEYGEN_API_KEY"
```

Iterate ephemerally, then deploy persistently:

```bash
modal serve containers/ugc-heygen/modal_app.py
modal deploy -e staging --tag ugc-heygen-0.1.0 \
  containers/ugc-heygen/modal_app.py
```

`modal deploy` prints the generated `modal.run` URL. With a Proxy Token created in Modal workspace settings:

```bash
BASE='https://<workspace>--cognition-ugc-heygen-api.modal.run'

curl -sS -X POST "$BASE/v1/runs" \
  -H "Modal-Key: $MODAL_PROXY_TOKEN_ID" \
  -H "Modal-Secret: $MODAL_PROXY_TOKEN_SECRET" \
  -H 'Content-Type: application/json' \
  --data-binary '{
    "product_description": "A $60 silk pillowcase, hypoallergenic, with a 30-day trial",
    "brand_voice": "raw",
    "length_seconds": 30,
    "avatar_id": "<approved-heygen-avatar-id>",
    "voice_id": "<approved-heygen-voice-id>"
  }'
```

Then poll the returned call ID:

```bash
curl -sS "$BASE/v1/runs/<call_id>" \
  -H "Modal-Key: $MODAL_PROXY_TOKEN_ID" \
  -H "Modal-Secret: $MODAL_PROXY_TOKEN_SECRET"
```

### 4.6 Runtime sequence and shutdown

1. First API request cold-starts the small FastAPI image if no warm container exists.
2. FastAPI/Pydantic validates the body before any paid call.
3. The API Function spawns `run_workflow` and returns `202`; it does not wait for video rendering.
4. The runner cold-starts, calls DeepSeek, validates the script, and calls `POST https://api.heygen.com/v3/videos` with one 24-hour HeyGen idempotency key.
5. The runner generates captions while the HeyGen job is processing, then polls `GET /v3/videos/{video_id}` until `completed` or `failed`.
6. The runner validates the final contract and finishes. The API Function later obtains the result via `modal.FunctionCall.from_id(call_id)`.
7. With no queued work and `min_containers=0`, each Function's pool can scale to zero. `scaledown_window=2` asks Modal to keep an idle container for at most two seconds, subject to autoscaler behavior.
8. The deployment and endpoint remain live for the next request.

HeyGen's [current Create Video API](https://developers.heygen.com/reference/create-video) is `POST /v3/videos`; status is [GET `/v3/videos/{video_id}`](https://developers.heygen.com/reference/get-video). The v3 create endpoint supports an `Idempotency-Key` with replay semantics for 24 hours. HeyGen's current Quick Start says v1/v2 support ends on 2026-10-31, so the repository should target v3 now rather than create new migration debt.

For production, replace polling with [HeyGen webhooks](https://developers.heygen.com/docs/webhooks): verify HMAC-SHA256 over raw bytes, reject stale timestamps, and deduplicate `Heygen-Event-Id`. A public callback cannot sit behind Modal Proxy Token auth unless HeyGen can send those credentials, so expose it as a separate public Web Function protected by HeyGen signature verification.

## 5. Autopilot: source post to tested live deployment

### 5.1 State machine

```text
DISCOVERED
  → EXTRACTED
  → SPEC_DRAFT
  → NEEDS_REVIEW | STATIC_VALIDATED
  → STAGING_DEPLOYED
  → TESTING
  → QA_FAILED ↺ bounded repair loop
  → APPROVED
  → LIVE
  → QUARANTINED or ROLLED_BACK when runtime monitors fail
```

Every transition should write an immutable event with actor, timestamp, source/spec/deployment hashes, costs, and evidence. `live` must be an explicit catalog state, not “the deploy command exited zero.”

### 5.2 Extraction paths

#### Instagram/TikTok post

1. Acquire the post only through an authorized/public mechanism consistent with platform terms.
2. Preserve the URL, caption, author, timestamp, transcript, visible tool names, and media evidence.
3. Extract **claims** separately from **implementation facts**. “Made with Kling” is not an API contract.
4. Identify inputs, outputs, human steps, provider steps, transformations, and missing information.
5. Generate a draft spec with per-field evidence and confidence. Any guessed paid step remains unresolved.

#### GitHub repository

1. Record commit SHA and license.
2. Prefer a checked-in container spec or SKILL.md.
3. Inspect dependency manifests, documented commands, API clients, tests, and sample contracts statically.
4. Build only in an isolated staging context with no production secrets and restricted egress.
5. Never treat a README instruction as permission to run install hooks or arbitrary code.

#### SKILL.md

1. Safe-parse frontmatter.
2. Convert type shorthand (`array[string]`, `enum [...]`) to draft JSON Schema.
3. Use the body as descriptive evidence.
4. Require an explicit executable step block or an approved prompt/adapter mapping before compilation.

### 5.3 Spec-generation agent output

The agent should return three objects, not just YAML:

- `container_spec`: the constrained draft.
- `provenance_map`: every important field mapped to source evidence and confidence.
- `unresolved`: missing provider operation, model, credential class, input/output field, license, or expected artifact.

The compiler must refuse to deploy a spec with unresolved paid operations or low-confidence required contracts. “Autopilot” means automated progress through known-safe states, not publishing guesses.

### 5.4 Deterministic pre-deploy gates

- Container-spec JSON Schema passes.
- DAG is acyclic and all bindings resolve.
- Every adapter/provider/model/operation is allowlisted.
- Dependencies are pinned and license/vulnerability policy passes.
- No secret literal or prompt-injection marker is promoted into code/config.
- Input sizes, output sizes, timeouts, retries, container counts, and maximum dollars per run are bounded.
- Network egress is limited to declared provider hosts.
- The cost estimate has all physical calls and a retry reserve.
- Generated source is reproducible from `spec_hash + compiler_version`.

### 5.5 Self-test loop

Use layered quality checks. A same-model “looks good” judgment is insufficient.

| Layer | Test | Pass condition |
|---|---|---|
| Build | Modal image builds and imports | No dependency/import failure |
| Contract | Submit/status endpoints | Expected status codes and JSON Schema |
| Negative input | Missing/extra fields, oversized text, bad enum | Rejected before provider calls |
| Deterministic semantics | Array types/lengths, required strings, URL/status fields | All invariants pass |
| Provider | LLM and HeyGen IDs/statuses | Calls succeed; 401/429/5xx normalized |
| Media | Download/read metadata or `ffprobe` | MP4 decodes, portrait ratio, expected duration band, audio present |
| Content | Claim grounding and safety rules | No claim absent from source input; CTA/voice/length rubric passes |
| Cross-modal | Transcribe rendered speech; compare with approved script | Similarity above threshold; no missing/extra material claims |
| Reliability | Same idempotency key twice; injected timeout/429 | One paid render, bounded retry/backoff |
| Cost | Usage ledger versus budget | Estimated and actual cost below per-run ceiling |
| Security | Auth, secret/log inspection, callback forgery | Unauthorized calls fail; no secret leakage; forged webhook rejected |

A suitable first gate is three happy-path fixtures plus six negative/failure cases. Media generation costs money, so run the full HeyGen test once per candidate spec hash; run LLM-only/mocked-provider tests on every compiler change.

The repair loop may adjust prompt wording, schema normalization, bindings, or adapter parameters, then redeploy staging and retest. Bound it to, for example, three attempts and `$1` total provider spend. It must never silently relax the public output schema merely to turn a failure green. When the bound is reached, move to `NEEDS_REVIEW` with the exact failed evidence.

Use a separate evaluator model or rule set for semantic scoring to reduce correlated self-grading errors. Deterministic validation remains authoritative; a judge score cannot override a malformed schema, unsupported claim, failed render, or cost overrun.

### 5.6 Publishing and runtime monitoring

Store a release record:

```json
{
  "workflow_slug": "ugc-heygen-video",
  "source_hash": "sha256:...",
  "spec_hash": "sha256:...",
  "compiler_version": "container-compiler@0.1.0",
  "modal_environment": "production",
  "modal_deployment_version": 7,
  "endpoint_url": "https://...modal.run",
  "qa_report_hash": "sha256:...",
  "published_at": "2026-08-...Z"
}
```

At runtime record per-step latency, provider request ID, retry count, token usage, actual/estimated cost, validation result, and redacted failure code under one `run_id`. Alert on schema-failure rate, provider 429/5xx, cost variance, p95 latency, duplicate renders, expired/unavailable media, and content-policy failures. Automatically quarantine rather than repeatedly spending on a broken paid workflow.

## 6. Cost and scaling analysis

### 6.1 What the repository model currently computes

`cost-model.mjs` estimates LLM input at roughly four characters per token, charges the configured maximum output tokens, adds fixed API line items, then computes:

```text
estimated COGS = sum(LLM estimates + API_STEP_COSTS × qty)
buyer run price = round_to_cents(max(estimated COGS × 1.25, $0.10))
```

The checked-in fixed API table is:

| Cost code | Estimated cost/call |
|---|---:|
| `heygen_avatar_render` | `$0.08` |
| `heygen_voiceover` | `$0.04` |
| `elevenlabs_tts` | `$0.03` |
| `modal_gpu_30s` | `$0.05` |
| `browserbase_session` | `$0.10` |
| `e2b_sandbox` | `$0.06` |
| `openai_image` | `$0.04` |
| `replicate_run` | `$0.06` |

A `1.25×` cost multiplier produces a 20% gross margin on revenue before rounding: `(1.25C - C) / 1.25C = 20%`. The `$0.10` floor makes margin much higher on very cheap workflows. Cent rounding can slightly reduce the intended markup.

For the checked-in HeyGen workflow:

| Step | Repository estimate |
|---|---:|
| script LLM (`700` max output) | `$0.00031` |
| `heygen_avatar_render` | `$0.08000` |
| `heygen_voiceover` | `$0.04000` |
| captions LLM (`300` max output) | `$0.00014` |
| **estimated COGS** | **`$0.12045`** |
| `COGS × 1.25` | `$0.1505625` |
| **buyer run price after cents rounding** | **`$0.15`** |
| gross dollars after modeled COGS | `$0.02955` |
| effective gross margin on the rounded price | `19.7%` |

For 15 identical HeyGen UGC runs—one run in each of 15 workflows, or 15 runs of this workflow—the repository math is:

```text
modeled COGS: 15 × $0.12045 = $1.80675
buyer revenue: 15 × $0.15 = $2.25
modeled gross dollars: $0.44325
```

This is a volume multiplier, not a deployment fee. Fifteen deployed scale-to-zero Apps have near-zero compute while unused; cost arrives when their containers execute, wait warm, store data, or call providers.

An illustrative one-call LLM step with the same rate/max-output scale costs about `$0.00031`, but `runPrice` floors it at `$0.10`. Fifteen such runs would be about `$0.00465` of modeled LLM COGS and `$1.50` of buyer revenue, before infrastructure, retries, payment fees, and support.

### 6.2 Limitations that must be fixed before money is trusted

- The HeyGen prices are repository comments labeled approximate. Reconcile them against the current account plan and actual invoice.
- The current HeyGen v3 request synthesizes voice within video creation. Confirm whether `$0.08 + $0.04` is intentionally two commercial units or stale double counting.
- Variable buyer input is not represented in the checked-in `workflow.steps[].user` strings, so the LLM estimator omits it.
- Maximum output tokens are a conservative proxy, not actual output usage.
- Retries, duplicate calls, failed renders, taxes, payment fees, storage, egress, and Modal CPU/memory are omitted.
- Unknown API steps silently default to `$0.05`; production compilation must reject unknown cost codes instead.
- A static price can become loss-making when provider prices or models change. Store cost-table version and reprice or pause affected listings.

The runtime should emit actual token/provider usage into a ledger, compare it with the estimate, and use the larger of estimated or recent p95 cost plus a retry reserve for pricing decisions.

### 6.3 `modal_gpu_30s` basis

The repository assigns `modal_gpu_30s = $0.05` for every 30-second unit without naming a GPU. This is a catalog planning SKU, not an auditable Modal invoice calculation.

Modal's public pricing page, checked 2026-08-09, listed the following GPU-only rates:

| GPU | Public rate/second | 30 seconds | Repository `$0.05` versus raw GPU |
|---|---:|---:|---:|
| T4 | `$0.000164` | `$0.00492` | `10.16×` |
| L4 | `$0.000222` | `$0.00666` | `7.51×` |
| H100 | `$0.001097` | `$0.03291` | `1.52×` |
| B200 | `$0.001736` | `$0.05208` | `0.96×` |

CPU and memory are additional. Modal listed `$0.0000131` per physical core-second and `$0.00000222` per GiB-second for standard Functions. Prices and plan terms can change; use [Modal's current pricing page](https://modal.com/pricing) as the source of truth.

The fix is to replace a single generic SKU with metered resource fields:

```text
modal_compute_cost =
  gpu_seconds × gpu_type_rate
  + cpu_core_seconds × cpu_rate
  + memory_gib_seconds × memory_rate
  + storage/egress where applicable
```

Keep `modal_gpu_30s` only as a conservative storefront estimate during migration, and record which GPU it assumes. A workflow that only calls external LLM and media APIs should have `gpu: null` and no `modal_gpu_30s` cost step.

### 6.4 Cold starts and 15-workflow capacity

- A small CPU image with only FastAPI/httpx/jsonschema should cold-start far faster than a GPU image loading model weights. Keep provider clients lazy and avoid downloads at startup.
- Default Modal idle maximum is 60 seconds. Setting 2 seconds minimizes warm-idle spend but maximizes the number of cold starts. Measure p50/p95 before choosing production values; 30–60 seconds may be a better buyer experience for bursty traffic.
- `min_containers=1` removes scale-from-zero latency but creates continuous cost. Keep `0` for the first workflow.
- Modal currently limits Web Functions to a 150-second HTTP request segment and may use redirects for longer work. The async submit/poll contract avoids depending on redirect behavior and CORS limitations. See [request timeouts](https://modal.com/docs/guide/webhook-timeouts).
- One async run can occupy an API container briefly and a runner container for the provider wait. Fifteen simultaneous runs can therefore briefly require more than 15 containers. Set `max_containers`, queue/admission limits, and per-user quotas deliberately.
- GPU concurrency is a workspace/plan constraint. The current Starter page advertises 10 GPU concurrency; 15 simultaneous GPU workflows would queue or require a higher limit. The chosen first workflow is CPU-only.
- Do not keep 15 separate large images. Reuse a shared base/runtime so Modal can reuse image layers and the compiler has one patch point.

## 7. Exact minimal build order for this week

This is the implementation sequence to use later; this analysis did not create these files.

### Day 1: freeze the contract and canary

Create:

```text
containers/ugc-heygen/
  container.yaml
  modal_app.py
  prompts/script.txt
  prompts/captions.txt
  schemas/input.json
  schemas/script.json
  schemas/captions.json
  schemas/output.json
  tests/cases.json
  tests/test_contract.py
```

Actions:

1. Choose one authoritative script shape. For this walkthrough it is `{hook, lines[], cta}`; do not mix it with the package worker's `{hook, shots[], captions[], cta}`.
2. Copy the exact approved prompts into prompt files and compute a spec hash.
3. Implement the LLM adapter and strict parser/validator.
4. Run the silk-pillowcase case in staging without HeyGen. Do not publish this canary as the final workflow.

### Day 2: account, keys, and authenticated Modal surface

The user/founder must provide:

- A Modal account/workspace and `modal setup` authorization, or CI service-user `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET`.
- A Modal staging environment and a Proxy Token ID/secret for endpoint calls.
- An LLM API key for the configured OpenAI-compatible base. The repository default expects opencode/Zen Go plus the `deepseek-v4-flash` alias; a direct DeepSeek key/base may require a different valid model name.
- A HeyGen account with v3 API access, `HEYGEN_API_KEY`, one approved `avatar_id`, and one `voice_id`.
- Proof that the selected avatar/voice and product material may be used for the intended commercial content.

Actions:

1. Install the Modal SDK in an isolated virtual environment.
2. Run `modal setup`.
3. Create the provider Modal Secret without committing values.
4. Create a Modal Proxy Token in workspace settings.
5. `modal serve` the FastAPI surface; verify `401` without proxy credentials and `422` for invalid JSON.

### Day 3: HeyGen v3 and idempotency

1. Implement `POST /v3/videos` and `GET /v3/videos/{video_id}`.
2. Use `run_id` as the HeyGen `Idempotency-Key`.
3. Add durable client-request idempotency keyed by tenant plus the request's `Idempotency-Key` header.
4. Submit one short test render; prove a repeated submission with the same key/body returns the same marketplace run and does not create a second paid video.
5. Normalize 401, 409/in-progress, 429 with `Retry-After`, 5xx, failed job, and timeout into stable internal error codes.
6. Persist the provider video ID as soon as it is received. For the first sketch it lives in the Function execution; before live payments, store run state durably.

### Day 4: quality, cost, and failure cases

1. Run contract and negative tests.
2. Validate MP4 decodability, portrait aspect ratio, duration, audio presence, and speech/script similarity.
3. Validate claim grounding against the original product description.
4. Compare actual token/provider cost with `$0.12045` and set a `$0.20` hard budget for the first version.
5. Inspect logs for secrets and raw sensitive payloads.

### Day 5: deploy and mark live

1. `modal deploy -e staging --tag <spec-hash> ...` and run the final smoke suite.
2. Deploy the identical spec/compiler output to production.
3. Record endpoint URL, deployment version, spec/source/compiler hashes, QA report, and exact cost-table version.
4. Point one non-public storefront/test client at it.
5. Mark the workflow live only after a real end-to-end render succeeds through the authenticated production URL.
6. Add spend and failure alerts before opening it broadly.

### Definition of done for workflow #1

- One authenticated POST accepts only the documented input.
- The POST returns `202` in seconds with `run_id`, `call_id`, and result URL.
- Retrying the same client request returns the same marketplace run, and retrying its provider mutation cannot buy a duplicate HeyGen render.
- Polling returns a final object that passes output JSON Schema and semantic invariants.
- The returned video decodes, has audio, is portrait, and is near requested duration.
- Generated claims are grounded in input.
- No secrets appear in repository, image, response, or logs.
- Actual cost and latency are recorded under the run ID.
- After idle, Modal reports zero warm containers; the endpoint still accepts the next request.
- A failed test cannot set catalog state to `live`.

## 8. Risks and mitigations

| Risk | Why it matters here | Required mitigation |
|---|---|---|
| Cold-start latency | Scale-to-zero adds latency on the first request | Small CPU image; lazy imports/clients; measure p95; tune `scaledown_window`; no GPU for API orchestration |
| Wrong lifecycle assumption | Destroying the App per run removes the endpoint and forces deployment work into requests | Deploy once; scale Function containers to zero; never call `modal app stop` per run |
| GPU cost ambiguity | `$0.05/30s` does not identify the device and can differ greatly from invoice | Meter GPU type/seconds; use `gpu: null` here; reconcile cost table regularly |
| Long asynchronous render | Synchronous HTTP can exceed practical request/CORS behavior | Submit/poll contract now; signed HeyGen webhook and durable state next |
| Duplicate paid work | Modal/provider retries after partial failure can create a second render | End-to-end run ID; HeyGen `Idempotency-Key`; persist provider ID; bounded retry policy |
| Secret leakage | Generated code, logs, or client payloads can expose paid keys | Named Modal Secrets; proxy auth; log redaction; no secrets in specs/images; rotation tests |
| Public endpoint by default | Modal Web Functions accept public traffic unless protected | `requires_proxy_auth=True`; per-user auth/quota at marketplace gateway |
| Cross-tenant result access | A caller with another run's call ID must not read its result | Store run ownership; authorize `run_id/call_id` on every status request; do not rely only on opaque IDs |
| Output schema drift | Models return fences, nested objects, missing arrays, or provider fields change | Strict parse + JSON Schema + semantic checks; version adapters; fail closed; fixtures from real responses |
| Prompt/source drift | Prompts currently differ between worker, workflow object, and SKILL.md | One canonical spec/prompt asset; generate all runtimes; hash and version every release |
| Catalog steps are cost tags | An `api` label does not specify executable behavior | Adapter registry with explicit operation/input/output schema; reject unresolved tags |
| Rate limits and concurrency | LLM, HeyGen, and Modal can all return 429 or queue | Admission control; per-provider semaphores; `Retry-After`; jittered bounded backoff; max containers; prepaid budget |
| Retry amplification | Function timeout plus configured retries can multiply wall time and cost | No blind workflow-level retries; step-level policy; idempotency; circuit breakers; hard dollar/time budgets |
| Expiring media URLs | A successful response can become unusable later | Copy outputs to owned object storage; checksum and store artifact metadata |
| FunctionCall is not durable business state | A call result alone is weak for order history, callbacks, or long retention | Persist `run_id → call_id/provider IDs/status/result` in a database or Modal Dict for MVP, then durable DB |
| Polling wastes compute | Runner is billed while sleeping during HeyGen render | Accept for first proof; move to verified webhooks/event-driven continuation |
| Source prompt injection | Posts/READMEs can tell the extraction agent to leak keys or execute code | Treat source as data; no deploy credentials in extraction stage; constrained schema; deterministic compiler |
| Supply-chain/RCE | Agent-selected packages or Dockerfiles can execute during build | Allowlisted pinned dependencies/images; isolated staging build; SBOM/signing/scanning; no arbitrary install scripts |
| Rights, consent, platform terms | Scraped workflows and avatar media may not be reusable commercially | Provenance/license gate; authorized access; avatar consent; human review before public listing |
| Unsupported product claims | UGC may invent medical/performance claims | Input-grounding rule, claim extraction, semantic QA, regulated-category policy |
| Same-model self-grading | Generator and judge can share the same blind spot | Deterministic gates plus separate evaluator/rubric and real artifact checks |
| Cost-model staleness | 20% modeled gross margin leaves little room for misses | Usage ledger, p95 pricing, retry reserve, provider price watcher, automatic pause/reprice |
| Fifteen code forks | Fixes and security patches drift | One canonical runtime/adapters/compiler; per-workflow immutable spec and prompt assets |
| File named `modal.py` | Can shadow the Modal Python package | Use `modal_app.py` |

## 9. Architecture after workflow #1

The scalable end state is a small marketplace control plane, not 15 bespoke autonomous containers:

```text
source connectors
      │
      ▼
extractor ──► evidence/provenance store
      │
      ▼
spec agent ──► draft container.yaml + unresolved fields
      │
      ▼
policy/contract/cost validator
      │
      ▼
deterministic compiler ──► shared runtime + immutable spec hash
      │
      ▼
Modal staging deploy ──► QA runner ──► signed QA report
      │                                  │
      └──────── reject/repair ◄──────────┘
                                         │ pass
                                         ▼
                         release registry/catalog live state
                                         │
                                         ▼
                    authenticated API gateway → Modal data plane
```

The agent's job is to understand and structure a workflow. The compiler's job is to make deployment reproducible. The runtime's job is to execute only reviewed adapters. The QA system's job is to prove the real deployed endpoint meets its contract. Keeping those jobs separate is what makes “do it for 15” operationally credible.

## 10. Primary technical references

Repository evidence:

- [`site/deploy/cost-model.mjs`](../site/deploy/cost-model.mjs)
- [`site/deploy/workflows.mjs`](../site/deploy/workflows.mjs)
- [`site/deploy/worker.js`](../site/deploy/worker.js)
- [`site/deploy/DEPLOY.md`](../site/deploy/DEPLOY.md)
- [`site/ig-workflows.js`](../site/ig-workflows.js)
- [`site/ig-more.js`](../site/ig-more.js)
- [`packages/ugc-script-studio/SKILL.md`](../packages/ugc-script-studio/SKILL.md)

Current provider documentation checked for this plan:

- Modal: [Web Functions](https://modal.com/docs/guide/webhooks), [Secrets](https://modal.com/docs/guide/secrets), [Images](https://modal.com/docs/guide/images), [GPU resources](https://modal.com/docs/guide/gpu), [cold starts](https://modal.com/docs/guide/cold-start), [autoscaling](https://modal.com/docs/guide/scale), [request timeouts](https://modal.com/docs/guide/webhook-timeouts), [deployments](https://modal.com/docs/guide/managing-deployments), [invoking deployed Functions](https://modal.com/docs/guide/trigger-deployed-functions), [Proxy Tokens](https://modal.com/docs/guide/webhook-proxy-auth), and [pricing](https://modal.com/pricing).
- HeyGen: [Quick Start](https://developers.heygen.com/docs/quick-start), [Create Video v3](https://developers.heygen.com/reference/create-video), [Get Video](https://developers.heygen.com/reference/get-video), and [webhooks](https://developers.heygen.com/docs/webhooks).

Provider interfaces and prices are time-sensitive. Pin the Modal SDK/compiler runtime used for the actual build, capture provider OpenAPI/schema versions, and re-run contract and cost tests before deployment.
