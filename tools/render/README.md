# Shared artifact renderer

`tools/render/runtime.py` is a local, deterministic compositor for the three
reviewed PhonicsMaker artifact workflows. It accepts a post-generation
`omo.education-artifact-manifest/v1` JSON document, writes real PDFs with
ReportLab, reopens them with pypdf, and emits byte count, SHA-256, MIME, and
page-count metadata.

The runtime has no network, billing, deployment, or authentication behavior.
It is deliberately separate from story/worksheet generation. The host must
validate the public workflow input schema, generate and QA the instructional
manifest, authorize any source artifacts/images, then invoke this compositor.

`tools/render/book.py` adds the reusable `omo.book-pdf/v1` contract for book and
keepsake workflows. It accepts a title, subtitle, Markdown chapters, page plan,
style metadata, and footer, then emits a deterministic ReportLab PDF with a
designed cover, keepsake map, chapter typography, justified body copy, running
heads, page numbers, and footer. It performs no provider, upload, storage,
authorization, or signing work; generated hosts own those boundaries.

## Outputs

- `phonics-worksheet-generator`: worksheet PDF and, when requested, a separate
  answer-key PDF derived from the same item answers.
- `illustrated-decodable-story-maker`: story PDF, canonical editable JSON, and
  JPEG thumbnail. Pages without an authorized image render text-only and the
  result includes an explicit warning.
- `phonics-story-edit-studio`: revised-story PDF, new canonical editable JSON,
  and JPEG thumbnail. `ArtifactStore` provides owner-scoped checksum-verified
  reads and content-addressed immutable writes for local testing.

The manifest schema is `render-manifest.schema.json`. The renderer also performs
runtime checks for increasing page numbers, bounded content, safe filenames,
answer completeness, and page overflow.

`CONTRACTS.md` records the exact three public input/output contracts and the
schema/prose inconsistencies that must be resolved before catalog readiness.

## Local use

```bash
python3 tools/render/runtime.py \
  tools/render/samples/smoke-worksheet.json \
  --output-dir /tmp/omo-render-output

python3 tools/render/smoke_test.py
python3 -m pytest -q -p no:cacheprovider tools/render/tests
```

For private local artifacts, add `--artifact-root /tmp/omo-artifacts
--owner-id owner-test --run-id run-123`. The returned `object_key` is then
owner-scoped and content-addressed; existing objects are never overwritten.

## Optional story illustrations

`image_bridge.py` uses the existing
`containers/demello-awake/image_gen.py::CodexSubscriptionImageAdapter`. The
owning runtime passes an access token and account ID from its secret plane;
the bridge uses `allow_refresh=False`, so it neither loads nor refreshes a
refresh token. If no
adapter is supplied, `populate_missing_story_images(..., adapter=None)` leaves
the pages text-only and returns a disclosure warning. The renderer never reads
or logs credentials and does not make image calls itself.
