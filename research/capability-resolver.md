# Capability Resolution Layer

**Status:** design only; intended integration point is `packages/skill-to-modal/compiler.py` after the current capability build lands.  
**Rule:** capabilities belong to the registry, never to an individual skill. A skill selects capabilities only through its reviewed execution contract.

## 1. Purpose and boundary

The compiler must turn a reviewed skill contract into the smallest runtime that can keep that contract. It must not infer product features from a skill name, slug, category, description, sales copy, examples, or tags. Those fields may help a human find a skill; they are not capability authority.

The resolver consumes a normalized, versioned contract containing:

- bounded input declarations, including media type, encoding/container, size/count limits, and trust/privacy class;
- bounded output and artifact declarations, including media type, schema, delivery form, and required validations;
- ordered execution steps with typed operations, tool/provider declarations, bindings, and resource needs;
- explicit promises and acceptance gates that have been translated into testable contract assertions; and
- declared providers, secret **names**, egress classes, cost drivers, and retention rules.

Free-form `SKILL.md` prose is untrusted source material. Before resolution, intake must either normalize its operational claims into the reviewed contract above or return `BLOCKED-CONTRACT_INCOMPLETE`. Marketing text is never scanned for triggers. The resolver does not weaken a promise, replace an output with a preview, or silently drop an input to fit today's platform.

## 2. Capability registry

The registry is a versioned, compiler-owned data set. Every entry follows one shape:

```yaml
name: stable_machine_name
version: semver
status: available | experimental | unavailable
triggers:
  all: []       # every signal must match
  any: []       # at least one signal must match when non-empty
  excludes: []  # conflicting signals make this entry ineligible
requires: []    # other registry capability names
generated_pieces:
  files: []
  runtime_steps: []
  tool_bindings: []
  packages: []
  resources: {}
  policy: []
tests: []
honest_limits: []
```

A trigger is a typed predicate over the normalized contract, not a keyword match. Examples are `inputs[*].content_media_type == application/zip`, `artifacts[*].content_media_type == application/pdf`, `steps[*].operation == archive.parse.whatsapp`, and `steps[*].provider == opencode-go`. Registry versions and the registry digest are included in resolution evidence so the same contract can be reproduced.

An entry is selectable only when its implementation is present, its declared dependencies resolve, and its registry tests are available. `experimental` or `unavailable` entries may explain a need but cannot make a build ready.

### 2.1 `book_pdf_renderer`

```yaml
name: book_pdf_renderer
version: 1.0.0
status: experimental
triggers:
  any:
    - artifacts[*].kind == book and artifacts[*].content_media_type == application/pdf
    - outputs[*].schema_version == omo.book-pdf/v1
    - steps[*].operation == artifact.render.book_pdf
requires:
  - artifact_store                 # must itself resolve for hosted delivery
generated_pieces:
  files:
    - generated renderer invocation module
    - output artifact declaration in workflow manifest
  runtime_steps:
    - validate the omo.book-pdf/v1 manifest
    - call tools.render.render_book_pdf
    - persist returned bytes through the resolved artifact store
    - return an owner-authorized artifact reference, not inline fake content
  tool_bindings:
    - tools.render.render_book_pdf
    - tools.render.pdf_page_count
  packages:
    - reportlab
    - pypdf
  resources:
    cpu: true
    gpu: false
    network: false_for_render
    writable_scratch: bounded_private
  policy:
    - validate MIME and %PDF magic
    - record byte length, SHA-256, and page count
tests:
  - identical reviewed input produces identical PDF bytes
  - valid PDF opens and page count is positive
  - invalid schema, empty prose, invalid style, and oversize fields fail closed
  - artifact metadata, ownership, checksum, and authorized download are verified
honest_limits:
  - the current shared primitive renders the reviewed keepsake-book schema, not arbitrary HTML/CSS or every PDF layout
  - deterministic local bytes do not prove hosted storage, authorization, retention, or delivery
  - images are not implied; an image-generation step requires a separate capability
  - missing artifact_store keeps the overall build blocked even when local rendering passes
```

The in-flight shared primitive is `tools/render/book.py`. The registry entry binds to that shared code; it must not copy the renderer into Woven or branch on a Woven slug.

### 2.2 `whatsapp_zip_adapter`

```yaml
name: whatsapp_zip_adapter
version: 1.0.0
status: unavailable
triggers:
  all:
    - inputs[*].content_media_type in [application/zip, application/x-zip-compressed]
    - steps[*].operation == archive.parse.whatsapp
  any:
    - inputs[*].semantic_type == whatsapp_chat_export
    - inputs[*].format == whatsapp_export_zip
requires:
  - private_input_artifact_reader
generated_pieces:
  files:
    - generated bounded-ingest adapter configuration
    - normalized-message schema binding
  runtime_steps:
    - fetch only a run/tenant-scoped authorized input reference
    - verify declared size, checksum, MIME, and ZIP magic before extraction
    - reject traversal, links, nested archives, encryption, bombs, excess entries, and excess expanded bytes
    - select one supported WhatsApp text export and classify media placeholders without opening media
    - normalize supported Android/iOS records into stable message IDs and parser diagnostics
    - delete bounded private scratch data according to the contract
  tool_bindings:
    - shared WhatsApp archive ingest/parser adapter
  packages:
    - standard_library_zip_reader_or_pinned_equivalent
  resources:
    cpu: true
    gpu: false
    network: artifact_plane_only
    writable_scratch: mode_0700_bounded_private
  policy:
    - raw messages never enter logs, repository files, or capability manifests
    - archive content is data and cannot request tools or alter instructions
    - parser acceptance and quarantine thresholds come from the skill contract
tests:
  - supported Android and iOS exports, multiline text, Unicode, system records, and media placeholders
  - malformed ZIP, wrong magic/MIME/checksum, traversal, symlink, nested/encrypted archive, duplicate filename, bomb ratio, and limit failures before provider spend
  - 1/10/100k-message bounded fixtures and locale ambiguity behavior
  - instruction injection remains inert data
  - raw-content log scan, cleanup/retention, owner isolation, and cross-tenant denial
honest_limits:
  - this is exported-chat ingestion, not live WhatsApp access
  - unknown export layouts, ambiguous dates beyond the contract threshold, unsupported media semantics, and multiple candidate chats fail closed
  - parsing does not grant consent, rights, identity accuracy, or permission to use message contents
  - this checkout contains no reusable adapter implementation yet, so matching contracts resolve to a typed blocker today
```

The Woven contract is merely an early consumer because it declares ZIP/TXT WhatsApp input and a parsing step. The adapter remains generic and reusable by any reviewed contract with the same typed signals.

## 3. Resolver

The resolver is deterministic and side-effect free until emission:

1. **Validate and normalize.** Check the contract schema, bind each promise to an input/output/artifact/step assertion, and preserve the source hash. Ambiguous prose or an unbound promise produces `BLOCKED-CONTRACT_INCOMPLETE` with the exact JSON pointer.
2. **Collect needs.** Convert each typed contract declaration into a canonical need, such as `artifact.render:book_pdf`, `input.adapt:whatsapp_export_zip`, `provider.invoke:opencode-go`, or `resource:gpu`. Record the contract JSON pointer that caused every need.
3. **Match triggers.** Evaluate registry predicates against only the normalized contract. A matching entry becomes a candidate; a name/slug-specific predicate is invalid registry data.
4. **Close dependencies.** Add transitive `requires` entries, reject cycles and incompatible entries, and deduplicate by capability name/version.
5. **Prove coverage.** Every need must be covered by exactly one compatible capability or by an explicitly composable set. Missing, unavailable, ambiguous, or conflicting coverage becomes a typed blocker. Resolution never proceeds with a substitute product.
6. **Minimize.** Remove any selected capability whose removal still covers every need and dependency. Break equivalent-set ties deterministically by reviewed priority, then capability name/version. The result is the minimal capability set, not every feature the platform knows.
7. **Assemble.** Merge generated files, runtime steps, tool bindings, packages, resource requests, policy guards, and tests. Collisions are `BLOCKED-CAPABILITY_CONFLICT` unless the registry explicitly defines composition.
8. **Emit.** Write the canonical capability manifest into the generated container alongside the other generated manifests. A blocked resolution may emit evidence, but must set `approved: []`, `decision: blocked`, `can_submit: false`, and `chargeable: false`.

Pseudocode:

```python
def resolve(contract, registry):
    normalized = validate_and_normalize(contract)
    needs = collect_typed_needs(normalized)
    selected = transitive_candidates(match_registry(normalized, registry))
    blockers = prove_complete_coverage(needs, selected, registry)
    if blockers:
        return blocked_manifest(normalized, needs, selected, blockers, registry.digest)
    minimal = minimize(selected, needs)
    assembly = compose_or_block(minimal)
    return approved_manifest(normalized, needs, minimal, assembly, registry.digest)
```

## 4. Typed blockers

Blockers are machine-readable and resumable:

```json
{
  "code": "MISSING_CAPABILITY",
  "missing_capability": "input.adapt:whatsapp_export_zip",
  "contract_pointer": "/steps/0",
  "evidence": "operation archive.parse.whatsapp over application/zip has no available registry implementation",
  "required_registry_action": "implement and approve whatsapp_zip_adapter",
  "resume_from": "capability-resolution",
  "retryable": true
}
```

Required codes are:

- `CONTRACT_INCOMPLETE`: an operational promise is absent, ambiguous, or not bound to a typed declaration;
- `MISSING_CAPABILITY`: no registry entry covers an exact need;
- `CAPABILITY_UNAVAILABLE`: an entry describes the need but its implementation/tests are not approved;
- `CAPABILITY_DEPENDENCY_MISSING`: a selected capability's dependency cannot resolve;
- `CAPABILITY_AMBIGUOUS`: multiple non-composable entries claim the same need without a reviewed preference;
- `CAPABILITY_CONFLICT`: selected generated pieces, policies, packages, or resources cannot be safely composed; and
- `CAPABILITY_TEST_FAILED`: the capability-specific generated gate did not pass.

The builder's top-level result may wrap these as `BLOCKED-CAPABILITY_REVIEW_REQUIRED`, but it must retain the inner code, exact missing capability, contract pointer, evidence, registry action, and resume point. It must never replace the failed workflow with a smaller preview while describing the original promise.

## 5. Emitted capability manifest

`capability-manifest.json` remains canonical JSON and should contain at least:

```json
{
  "schema_version": "cognition.capabilities/v2",
  "resolver_version": "1.0.0",
  "registry_digest": "sha256:...",
  "source_sha256": "...",
  "contract_digest": "sha256:...",
  "decision": "approved",
  "needs": [
    {"name": "artifact.render:book_pdf", "contract_pointer": "/artifacts/0"}
  ],
  "selected": [
    {"name": "book_pdf_renderer", "version": "1.0.0", "trigger_evidence": ["/artifacts/0"]}
  ],
  "generated": {
    "runtime_steps": [],
    "tool_bindings": [],
    "packages": [],
    "resources": {},
    "tests": []
  },
  "approved": ["book_pdf_renderer@1.0.0"],
  "blockers": []
}
```

For a blocked build, `decision` is `blocked`, `approved` is empty, `blockers` contains the typed records, and the workflow/run/pricing manifests must agree that submission and charging are disabled. Tests must assert this cross-manifest invariant.

## 6. Registry and resolver tests

The compiler suite needs contract-driven tests, not product-name tests:

- the same PDF artifact declaration resolves `book_pdf_renderer` for unrelated skill names and slugs;
- Woven with no PDF artifact declaration does not receive the PDF renderer merely because its prose says “storybook”;
- any reviewed WhatsApp ZIP parsing contract resolves `whatsapp_zip_adapter`; a generic ZIP bundle without `archive.parse.whatsapp` does not;
- combined WhatsApp ZIP → book PDF selects exactly the adapter, renderer, and their transitive artifact-plane dependencies;
- deleting a required entry yields the exact `MISSING_CAPABILITY` blocker and disables submit/charge;
- an unavailable entry yields `CAPABILITY_UNAVAILABLE`, not approval;
- unused capabilities are excluded, dependency cycles and generated-piece collisions fail closed, and resolution order does not change output bytes;
- marketing description, tags, examples, name, and slug mutations do not change resolution; and
- generated manifests include source/contract/registry digests, trigger pointers, tests, honest limits, and cross-manifest readiness agreement.

## 7. Growth loop

When a new contract exposes an uncovered need, stop that build with the exact typed blocker. Add one reviewed, versioned capability to the shared registry with typed triggers, reusable generated pieces, dependencies, tests, cost/resource treatment, security policy, and honest limits. Then rerun the original unchanged contract and the registry-wide regression suite.

Do not add a conditional for the requesting skill, patch its generated container, infer from its marketing copy, or narrow its promised job. The sequence is always:

```text
contract need -> typed blocker -> generic registry capability -> shared tests -> resolve again
```

That is how the registry grows from the first Woven PDF/WhatsApp cases into image, audio, video, browser, domain-state, or future adapters without turning the compiler into a list of product exceptions.

### 2.3 `chart_generation`

```yaml
name: chart_generation
version: 1.0.0
status: experimental
triggers:
  any:
    - artifacts[*].kind in [chart, plot, metrics_viz] and artifacts[*].content_media_type == image/png
    - outputs[*].artifact_type in [chart, plot, metrics_viz]
    - steps[*].operation == visualization.render.chart
requires:
  - artifact_store                 # must itself resolve for hosted delivery
generated_pieces:
  files:
    - generated chart-render invocation step
    - PNG artifact declaration in the workflow manifest
  runtime_steps:
    - validate the bounded chart input contract
    - call tools.render.charts.render_chart_png
    - verify PNG magic and exact declared dimensions
    - persist returned bytes through the resolved artifact store
    - return an owner-authorized artifact reference
  tool_bindings:
    - tools.render.charts.render_chart_png
  packages:
    - Pillow
  resources:
    cpu: true
    gpu: false
    network: false_for_render
    writable_scratch: none
  policy:
    - accept only line, bar, pie, and histogram chart kinds
    - reject non-finite values, more than 20 series, and more than 5000 total points
    - record image dimensions, byte length, SHA-256, and image/png MIME
tests:
  - identical reviewed input produces identical PNG bytes
  - line, bar, pie, and histogram fixtures decode as real PNG images
  - unknown kinds, empty series, non-finite values, invalid colors/dimensions, and data-bound violations fail closed with ChartRenderError
  - PNG signature and exact requested dimensions are verified
  - artifact ownership, checksum, and authorized download are verified at integration time
honest_limits:
  - rendering is deterministic and static; interactive charts, animation, hover state, and client-side filtering are not supported
  - the primitive accepts at most 20 series and 5000 total points, with additional readability bounds for pie slices and bar categories
  - local PNG bytes do not prove hosted storage, authorization, retention, or delivery
  - missing artifact_store keeps the overall build blocked even when local rendering passes
```

### 2.4 `video_processing`

```yaml
name: video_processing
version: 1.0.0
status: experimental
triggers:
  any:
    - steps[*].operation in [media.video.normalize, media.video.cut_highlights, media.video.extract_thumbnail, ffmpeg.h264_aac_portrait, ffmpeg.h264_aac_landscape]
    - steps[*].tool in [ffmpeg, ffprobe]
    - artifacts[*].content_media_type in [video/mp4, video/quicktime]
    - inputs[*].content_media_type matches video/*
requires:
  - artifact_store
  - ffmpeg_runtime                  # pinned ffmpeg and ffprobe in the runtime image
generated_pieces:
  files:
    - generated bounded media-step invocation module
    - video and thumbnail artifact declarations in the workflow manifest
  runtime_steps:
    - resolve one authorized run-scoped local source artifact
    - probe duration, dimensions, codecs, and byte size before render
    - invoke tools.render.video normalize, cut_highlights, or extract_thumbnail for the exact reviewed operation
    - validate H.264/AAC output, PNG thumbnails, declared dimensions, duration, byte count, and checksum
    - persist only validated outputs through the resolved artifact store
  tool_bindings:
    - tools.render.video.probe
    - tools.render.video.normalize
    - tools.render.video.cut_highlights
    - tools.render.video.extract_thumbnail
  packages: []
  resources:
    cpu: true
    gpu: false
    network: artifact_plane_only
    writable_scratch: bounded_run_private
  policy:
    - install pinned ffmpeg and ffprobe binaries in the runtime image
    - pass paths and generated numeric filters only through argv lists; media metadata, filenames, and clip titles remain inert data
    - allow at most 20 highlight clips and 10 minutes of selected output from a source no longer than 2 hours
    - cap normalized output at 1280px, validate timecodes against ffprobe duration, and reject overlap or reordering
    - record media type, dimensions, duration, codecs, byte length, SHA-256, and renderer/FFmpeg versions
tests:
  - a generated two-second lavfi fixture normalizes to bounded H.264/AAC and probes successfully
  - repeated normalization is byte-identical within the pinned FFmpeg/libx264 image
  - exact highlight intervals concatenate to the expected bounded duration; overlap, invalid order, excess count, excess total, and out-of-range timecodes fail with MediaRenderError
  - exact timestamp extraction produces a PNG with the source dimensions and correct signature
  - unreadable, non-video, oversized, overlong, and over-dimension media fail closed before artifact publication
  - artifact ownership, immutable checksum, authorized download, scratch cleanup, and full-decode validation pass at integration time
honest_limits:
  - the shared primitive performs CPU-only normalization, exact re-encoded cuts, concatenation, and thumbnail extraction; it does not provide GPU effects, generative VFX, motion graphics, title-card layout, speech recognition, or image generation
  - generated-frame-sequence plus source-audio assembly and full visual-contract QA remain specialized executor work; selecting this capability alone does not materialize the de Mello media engine
  - normalization and cuts use H.264/AAC at a bounded resolution; arbitrary codec preservation and lossless editing are not promised
  - bytes are deterministic where possible only within the same pinned FFmpeg, libx264, architecture, and invocation; encoder or container-library upgrades may change bytes despite fixed metadata and single-threaded encoding
  - highlight jobs are limited to 20 clips and 10 minutes total, normalized sources to 2 hours and 8192px input dimensions, and normalized output to 1280px
  - local media bytes do not prove hosted storage, authorization, retention, delivery, progress reporting, or full workflow readiness
  - missing artifact_store or ffmpeg_runtime keeps the overall build blocked even when local rendering passes
```

### 2.5 `domain_state`

```yaml
name: domain_state
version: 1.0.0
status: experimental
triggers:
  any:
    - steps[*].execution_mode in [async, long_running]
    - outputs[*].kind in [run_status, progress]
    - runtime.ownership_scope == per_run
requires: []
generated_pieces:
  files:
    - generated per-run state schema and transition adapter
    - generated submit/status response bindings
  runtime_steps:
    - create one owner-scoped record with run_id, owner_id, status, phase, progress_pct, timestamps, version, and expires_at
    - apply typed compare-and-set transitions queued -> processing -> done or blocked
    - reject unknown, stale, backward, cross-owner, and post-terminal transitions
    - expose only owner-authorized status fields and artifact references
    - expire records and associated runner state according to the reviewed retention contract
  tool_bindings:
    - runner.domain_state.create
    - runner.domain_state.transition
    - runner.domain_state.read_owned
    - runner.domain_state.expire
  packages: []
  resources:
    cpu: true
    gpu: false
    network: runner_state_plane_only
    writable_scratch: none_or_runner_managed
  policy:
    - run_id is opaque, unique, and never accepted as proof of ownership
    - status is exactly queued, processing, done, or blocked; terminal states are immutable
    - progress_pct is an integer from 0 to 100 and monotonic, with phase and updated_at recorded on every transition
    - every mutation is owner/run scoped, typed, version checked, idempotent where replayed, and auditable without payload or credential logging
    - expires_at is mandatory and cleanup cannot cross the owning run or tenant
tests:
  - queued -> processing -> done and queued -> processing -> blocked are accepted with monotonic progress
  - skipped, backward, post-terminal, stale-version, invalid-progress, and unknown-run transitions fail with typed state errors
  - idempotent replay returns the same state while conflicting replay fails closed
  - concurrent compare-and-set leaves one valid transition and no torn record
  - cross-owner read/write denial, expiry behavior, status-field redaction, and run isolation pass for in-memory and DB-backed adapters
  - a long-running media fixture can submit, poll monotonic progress, reach a terminal state, and retrieve only its own validated artifacts
honest_limits:
  - the runner may implement the record in memory for single-process tests or in a reviewed database for durable hosted work; in-memory state does not survive restart or coordinate replicas
  - this capability models run lifecycle and progress, not queues, worker leasing, billing, refunds, artifact storage, authentication, or provider retries
  - progress reports reviewed checkpoints rather than continuous completion estimates
  - expiry is retention enforcement, not proof that external provider or artifact copies were deleted
  - records contain identifiers and status only; credentials and reusable cross-run secrets are never stored in domain state
```

### 2.6 `research.collect:public_search_fetch`

```yaml
name: research.collect:public_search_fetch
version: 1.0.0
status: experimental
scope: PARTIAL  # v1 is direct-URL fetch only; public query search is unavailable
triggers:
  all:
    - steps[*].operation == research.web.collect
  any:
    - inputs[*].semantic_type == public_url
    - steps[*].operation == research.fetch.public_url
  excludes:
    - inputs[*].trust_class in [private, credentialed]
    - steps[*].requires_authenticated_session == true
requires:
  - reviewed_network_egress_policy
generated_pieces:
  files:
    - tools/research/public_fetch.py
  runtime_steps:
    - validate an HTTPS URL against the optional host allowlist and secret-host denylist
    - fetch and enforce robots.txt for the requested path
    - follow at most three policy-valid redirects with a ten-second timeout per GET
    - read at most 256 KiB and return URL/status/final URL/content type/preview/SHA-256 evidence
  tool_bindings:
    - tools.research.public_fetch.fetch_public_url
  packages:
    - python_standard_library
  resources:
    network: bounded_public_https
    credentials: false
    shell: false
  policy:
    - HTTPS by default; HTTP is an explicit local-fixture/testing override
    - no URL userinfo, credentials, provider calls, or shell execution
    - redirects are revalidated against scheme, denylist, and optional allowlist
tests:
  - local http.server fixture proves response contract, preview, and SHA-256
  - robots denial, HTTP failure, timeout, oversize body, and redirect limit return typed errors
  - HTTPS default and unavailable search mode fail closed
honest_limits:
  - PARTIAL: v1 does not turn a free-form query into search results
  - no stable general-purpose search endpoint requiring neither a key nor provider agreement is configured; search_snippets returns SEARCH_UNAVAILABLE
  - robots unavailability follows RFC 9309-style behavior; a 4xx robots response does not invent a deny rule
  - this fetch primitive does not establish source authority, truth, citation quality, or permission beyond robots policy
```

Implementation tests: `tools/research/tests/test_public_fetch.py` (seven tests,
local fixture server only; no real network).

### 2.7 `tabular.statistics`

```yaml
name: tabular.statistics
version: 1.0.0
status: experimental
triggers:
  all:
    - inputs[*].semantic_type == tabular_dataset
  any:
    - steps[*].operation == tabular.parse
    - steps[*].operation == statistics.compute
  excludes:
    - inputs[*].content_media_type not_in [text/csv, text/tab-separated-values, text/plain]
requires: []
generated_pieces:
  files:
    - tools/render/tabular.py
  runtime_steps:
    - detect comma, semicolon, or tab delimiter and parse standard CSV quoting
    - conservatively type finite integers/floats while preserving leading-zero identifiers as strings
    - compute numeric count/sum/mean/median/min/max/sample stdev and linear-interpolated percentiles
    - compute deterministic categorical mode and emit notes for missing or mixed values
  tool_bindings:
    - tools.render.tabular.parse_csv
    - tools.render.tabular.statistics
    - tools.render.tabular.analyze_csv
  packages:
    - python_standard_library
  resources:
    network: false
    credentials: false
    llm: false
  policy:
    - malformed/empty tables and inconsistent row shapes fail closed
    - explicitly numeric mixed columns fail with NON_NUMERIC_COLUMN
    - sample stdev with fewer than two numeric observations fails with INSUFFICIENT_DATA
tests:
  - comma, semicolon, and tab fixtures plus quoted commas and escaped quotes
  - integer/float typing, leading-zero preservation, mixed-type fallback, and empty values
  - exact descriptive statistics, sample stdev, deterministic mode, and linear percentiles
  - EMPTY_TABLE, NON_NUMERIC_COLUMN, and INSUFFICIENT_DATA typed failures
honest_limits:
  - input is in-memory delimited text, not XLSX, a database, or an unbounded streaming dataset
  - dialect detection is limited to comma, semicolon, and tab; ambiguous input falls back deterministically to comma
  - mixed numeric/text columns are categorical unless the caller explicitly requires numeric data
  - percentiles use the documented inclusive-endpoint linear interpolation method; no inferential statistics are implied
```

Implementation tests: `tools/render/tests/test_tabular.py` (nine tests covering
the requested fixtures and typed failures).
