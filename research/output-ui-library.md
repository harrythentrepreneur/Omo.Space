# Omo prebuilt output UI library

**Status:** component and runtime design, 2026-08-12
**Scope:** the hosted Run page. This is a small output registry, resolver, normalization contract, and safe fallback—not a general report builder or a remote component system.

## Decision

Compile every hostable skill's Draft 2020-12 `output_schema` into the run manifest and require the delivery Worker to normalize completed results into `omo.result/v1`. At runtime the Run page gives the schema, normalized result, optional presentation hints, artifact-link resolver, and manifest phases to one reusable output library. The library chooses prebuilt renderers; adding a compatible skill must not add skill-specific HTML to the Run page.

The v1 registry contains 12 deliberate components:

1. `PlainTextOutput`
2. `MarkdownOutput`
3. `ImageGalleryOutput`
4. `AudioPlayerOutput`
5. `VideoPlayerOutput`
6. `FileDownloadOutput`
7. `PdfDocumentOutput`
8. `ArchiveDownloadOutput`
9. `LinkCardOutput`
10. `JsonViewerOutput`
11. `ArtifactGridOutput`
12. `ProgressTimelineOutput`

`OutputGroup` recursively lays out fixed objects and scalar lists; it is a layout primitive rather than a thirteenth author-selected component. `FallbackOutput` is the safety net, not a type a skill author deliberately chooses.

## What the repository requires now

- **Woven Storybook** returns a `book` string described as Markdown, a `page_plan` string array, and a `usage` object. Until its schema declares `contentMediaType: "text/markdown"`, the compiled manifest needs a compatible output UI hint for `/book`. It resolves to `MarkdownOutput`; the page plan becomes an ordered `OutputGroup`; usage remains secondary metadata behind **View JSON**.
- **Audio Symbolic Animation** returns three private artifact references identified by `kind` plus media, delivery, and usage metadata. The delivery Worker resolves each `object_key` to an owner-authorized artifact URL. Its video becomes `VideoPlayerOutput`; transcript and frame brief become `FileDownloadOutput`; together they are an `ArtifactGridOutput`.
- **de Mello Awake** returns `video_url` and `contact_sheet_url` as generic `format: "uri"` strings. A URI alone cannot truthfully distinguish video from image. Its Worker should normalize them to `kind: "video"` and `kind: "image"`; a transitional manifest may declare compatible renderer hints. Do not add field-name matching to the browser.
- **UGC HeyGen** returns script/caption structures and a nullable video object. The video object becomes `VideoPlayerOutput` when present; a `null` video renders a clear “video not delivered” state while script and captions remain readable. Usage and notes are supporting data.
- The schema glob currently also contains **GPT Image Seedance Ad**, whose image array maps directly to `ImageGalleryOutput`, and **Claude SEO**, whose uniform findings and scalar arrays map through `OutputGroup` with raw JSON always available.

## Shared output anatomy

Every completed-result component sits inside the same `OutputFrame`:

- human label from artifact `title`/`label`, schema `title`, then a safe type label;
- delivery badge such as **Ready**, **3 files**, or **Signed link · 9 min**;
- inline preview when the browser can render the MIME safely;
- filename, MIME label, dimensions/duration where present, and human-readable byte size;
- a consistent action row ordered **Download**, **Copy**, then **Open in new tab** when those actions apply;
- a compact source/expiry line for signed or external delivery;
- an error slot for expired links, failed media decode, or blocked URL protocols;
- a **View JSON** disclosure at the result-group level for audit/debugging.

Buttons and links use native semantics, 44 px minimum targets, visible focus, and plain-language accessible names. Preview failure never removes the download path. Returned HTML is never executed; Markdown is parsed through the small allowlist renderer and sanitized before insertion.

## Type catalogue

### 1. `PlainTextOutput`

- **UI:** readable paragraphs for ordinary prose; `<pre>` only when whitespace is declared meaningful. Long results use a soft max-height with **Show all** rather than truncating the downloadable value.
- **Schema mapping:** `type: "string"` with `format: "text"`, `contentMediaType: "text/plain"`, or no stronger media/format annotation; envelope `type: "text"` or `text_format: "plain"`.
- **Actions:** **Copy** and **Download .txt**. Never add **Open** for untrusted text.
- **Mobile:** one column, natural wrapping, no horizontal scroll except explicitly preformatted blocks.
- **Source:** result JSON for ordinary text; a small non-sensitive text data URI may be created locally only for download. Larger/private text is an artifact-plane URL.

### 2. `MarkdownOutput`

- **UI:** sanitized semantic headings, paragraphs, lists, emphasis, blockquotes, and links. Raw Markdown is available through a disclosure; arbitrary HTML, scripts, iframes, and event attributes are discarded.
- **Schema mapping:** string with `format: "markdown"`, `contentMediaType: "text/markdown"`, compatible `ui.outputs[path].renderer: "markdown"`, or envelope `type: "markdown"`/`text_format: "markdown"`.
- **Actions:** **Copy Markdown** and **Download .md**; safe links inside content may use **Open in new tab** with `rel="noopener noreferrer"`.
- **Mobile:** typography and action row stack; code blocks scroll internally without causing page overflow.
- **Source:** inline `text` in `omo.result/v1` when bounded, or an owner-authorized artifact URL for a large/private document.

### 3. `ImageGalleryOutput`

- **UI:** one image uses a large fitted preview; multiple images use an aspect-preserving grid. Clicking/tapping opens a focus-trapped zoom dialog with previous/next controls, alt text, filename, and download.
- **Schema mapping:** string with `format: "image-url"`; string/object with `contentMediaType` matching `image/*`; artifact `kind: "image"`; array of compatible items; envelope `type: "image" | "images"`.
- **Actions:** **Download**, **Copy link**, and **Open in new tab** for each image; the group can offer **Download all** only when the Worker supplies an archive or an approved bundling endpoint.
- **Mobile:** one-column or two-column thumbnail grid according to available width; zoom is a full-viewport dialog and never relies on hover.
- **Source:** Omo artifact-plane URL is preferred. A `data:image/*` URI is accepted only for a small, non-sensitive generated preview under the configured byte cap. External provider-signed links require allowlist and expiry handling.

### 4. `AudioPlayerOutput`

- **UI:** native `<audio controls preload="metadata">` plus filename, duration when known, MIME, size, and a decode-error message that preserves the download action.
- **Schema mapping:** string with `format: "audio-url"`; `contentMediaType: "audio/*"`; artifact `kind: "audio"`; envelope `type: "audio"`.
- **Actions:** **Download**, **Copy link**, and **Open in new tab** when the source is an HTTPS URL.
- **Mobile:** full-width native player; metadata and actions wrap below it.
- **Source:** owner-authorized artifact-plane URL or short-lived provider link. Data audio is allowed only for tiny public samples and is not the production path.

### 5. `VideoPlayerOutput`

- **UI:** inline `<video controls playsinline preload="metadata">` with a safe poster, captions track when supplied, and aspect ratio/duration metadata. Poster or fallback art remains visible until playback.
- **Schema mapping:** string with `format: "video-url"`; `contentMediaType: "video/*"`; artifact `kind: "video"`; a typed video object such as HeyGen's after normalization; envelope `type: "video"`.
- **Actions:** **Download video**, **Copy link**, and **Open in new tab**. Subtitle artifacts get their own download action.
- **Mobile:** player is full width, capped to viewport height, and preserves portrait or landscape aspect without cropping.
- **Source:** Omo artifact plane is preferred; current delivery may be a validated expiring provider URL. Never embed `javascript:`, arbitrary `blob:` from the server, or untrusted HTML players.

### 6. `FileDownloadOutput`

- **UI:** a compact file card with kind icon, human title, filename, MIME/type label, size, optional checksum suffix, expiry, and download state. Unknown extensions are treated as bytes, not previewed.
- **Schema mapping:** string with `format: "download" | "uri"` plus a non-preview `contentMediaType`; artifact-shaped object with `url`/`object_key`, `filename`, `mime`/`content_type`, and size; artifact kinds such as `file`, `transcript`, or `frame_brief`.
- **Actions:** **Download** is primary; **Copy link** and **Open in new tab** appear only for safe URLs. Text-like files may also have **Preview**.
- **Mobile:** icon, metadata, and actions stack; long filenames wrap anywhere without shrinking actions below 44 px.
- **Source:** normally an owner-authorized artifact URL. Private `object_key` values must be exchanged server-side; they are never shown as clickable paths. Small generated text may use a client-created data URI.

### 7. `PdfDocumentOutput`

- **UI:** PDF cover/page preview when an approved renderer or thumbnail exists; otherwise a document card with page count, filename, size, and a clear PDF badge. Do not depend on browser PDF embedding for the core path.
- **Schema mapping:** string/object with `contentMediaType: "application/pdf"`, `format: "pdf-url"`, artifact `kind: "pdf"`, or envelope `type: "pdf"`.
- **Actions:** **Download PDF**, **Open in new tab**, and **Copy link**.
- **Mobile:** thumbnail above metadata; actions stack. The PDF opens in a separate tab rather than a cramped nested viewer.
- **Source:** artifact-plane URL or validated signed HTTPS link; never inline a private PDF as a large data URI.

### 8. `ArchiveDownloadOutput`

- **UI:** archive card showing filename, compressed size, item count when provided, and a short list of included artifacts. The browser does not inspect or expand archives.
- **Schema mapping:** `contentMediaType: "application/zip" | "application/x-zip-compressed"`, `format: "zip-url"`, artifact `kind: "zip" | "archive"`, or envelope `type: "zip"`.
- **Actions:** **Download ZIP**, **Copy link**, and **Open in new tab** only when useful. For a bundle, this is the approved **Download all** target.
- **Mobile:** included-file list clamps with **Show all**; download remains full width.
- **Source:** built and scanned on the artifact plane, then delivered through an owner-authorized or short-lived signed URL. Never create a large ZIP in the browser.

### 9. `LinkCardOutput`

- **UI:** hostname, title, optional safe description, and a visibly truncated URL whose full value is available to assistive technology and copy. No remote Open Graph HTML is injected.
- **Schema mapping:** string with `format: "uri" | "url" | "uri-reference"` and no more specific media annotation; artifact `kind: "link"`; envelope `type: "link"`.
- **Actions:** **Open in new tab** and **Copy link**. **Download** appears only after the link has been normalized to an artifact.
- **Mobile:** hostname and URL wrap; actions stack or wrap without horizontal overflow.
- **Source:** public HTTPS URL or validated external signed link. `http:` is accepted only for same-origin local development; unsafe schemes render as escaped text.

### 10. `JsonViewerOutput`

- **UI:** readable key/value sections for small fixed objects, ordered lists for scalar arrays, compact cards for uniform object arrays, and an escaped pretty-JSON view for everything. Large trees are collapsed by depth, never silently dropped.
- **Schema mapping:** `type: "object" | "array"`; string with `format: "json"` or `contentMediaType: "application/json"`; envelope `type: "json"` or a populated `json` member.
- **Actions:** **Copy JSON**, **Download .json**, and **Expand/collapse**. There is no **Open** unless JSON is also an artifact.
- **Mobile:** summary rows become stacked definition blocks; JSON scrolls internally and wraps long strings when the pretty view is selected.
- **Source:** validated result JSON or a JSON artifact. Provider objects are escaped data, never templated HTML.

### 11. `ArtifactGridOutput`

- **UI:** a responsive primary/secondary artifact grid. A playable video, audio file, first image, or PDF leads; supporting files use download cards. A bundle header reports count and total bytes; **Download all** points to a server-created archive.
- **Schema mapping:** array of artifact objects; `contains` constraints by `kind`; fixed object containing multiple artifact-bearing properties; envelope `type: "bundle"` or `artifacts.length > 1`.
- **Actions:** item-level actions plus **Download all** when an archive/bundle endpoint exists; **Copy result links** copies safe URLs only.
- **Mobile:** one column in semantic order—primary preview, then supporting artifacts. No masonry or drag-only interaction.
- **Source:** mixed safe sources are permitted, but every item states `source`. Prefer artifact-plane URLs and refresh expired signed links individually.

### 12. `ProgressTimelineOutput`

- **UI:** current phase label, determinate bar only when the server supplies `progress_pct`, indeterminate bar otherwise, ordered phase labels, elapsed time, and partial-artifact notices. It uses `role="status"`; the bar has progressbar semantics.
- **Schema mapping:** manifest `phases[]` plus run events, not the completed `output_schema`; envelope/event status `queued | running | completed | failed | cancelled`.
- **Actions:** **Cancel** only when the API exposes a legal cancel transition; **View partial result** only for validated, explicitly streamable text/artifacts; **Retry** only after a terminal retryable failure.
- **Mobile:** phase labels become a vertical or horizontally scroll-free list; current label is never reduced to color or an animation.
- **Source:** SSE is preferred, with authenticated polling as a fallback. The client never advances a pretend timer; it displays monotonic server sequence/progress.

### Layout primitive: `OutputGroup`

For a fixed object, hide transport-only fields such as `status` and `workflow_version` from the main visual but retain them in **View JSON**. Recursively render meaningful properties in declaration order. Scalar arrays become an ordered/unordered list according to `ui`; uniform object arrays become compact labeled cards. Media/artifact children delegate back to the registry. At 375 px every multi-column group stacks.

### Safety net: `FallbackOutput`

If no renderer matches, show escaped plain text when a useful textual value exists, then an escaped pretty-JSON disclosure. Provide **Copy** and **Download raw result**; if any safe artifact URLs can be extracted from validated artifact-shaped values, include **Download all** only through the Worker bundling endpoint. Never guess media from a property name, execute returned HTML, silently omit a required value, or fail the entire result because a preview is unknown. Emit an analytics warning with skill slug, schema ID, and JSON Pointer so the missing renderer is visible.

## Result envelope contract

The browser-facing success payload is intentionally small and stable:

```json
{
  "schema_version": "omo.result/v1",
  "run_id": "run_01K2W8N4R7J4",
  "status": "completed",
  "type": "bundle",
  "title": "Present-moment reflection",
  "text": "# A quieter beginning\n\nThe room softened...",
  "text_format": "markdown",
  "artifacts": [
    {
      "id": "artifact_video",
      "kind": "video",
      "url": "/v1/runs/run_01K2W8N4R7J4/artifacts/artifact_video",
      "filename": "reflection.mp4",
      "mime": "video/mp4",
      "size": 18420931,
      "source": "artifact",
      "poster_url": "/v1/runs/run_01K2W8N4R7J4/artifacts/poster",
      "duration_seconds": 30.1
    }
  ],
  "json": {
    "delivery": { "title": "Present-moment reflection" },
    "media": { "width": 1080, "height": 1920, "fps": 30 }
  }
}
```

Contract rules:

- `schema_version`, `run_id`, `status`, and `type` are required. `type` is one of `text`, `markdown`, `image`, `images`, `audio`, `video`, `file`, `pdf`, `zip`, `link`, `json`, or `bundle`.
- `text` is a string; `text_format` defaults to `plain`. It is bounded by the manifest and never contains trusted HTML.
- `artifacts` defaults to `[]`. Each item requires `kind`, `url`, `filename`, `mime`, and non-negative integer `size`; optional presentation metadata includes `id`, `title`, `alt`, `poster_url`, `duration_seconds`, `width`, `height`, `sha256`, `expires_at`, and `source`.
- `source` is `artifact`, `data`, or `external`. `artifact` is the preferred stable, owner-authorized Omo endpoint. `data` is permitted only for small, non-sensitive allowlisted MIME types. `external` must be an allowlisted HTTPS origin and may expire.
- A container may internally emit `object_key`, checksum, bytes, and MIME. The delivery Worker verifies ownership and output-schema validity, records the artifact, and replaces that transport reference with the browser-safe artifact URL. The browser never signs storage URLs or treats an `object_key` as downloadable.
- `json` contains useful structured output/metadata, not a duplicate of every transport field. The full schema-valid raw result may be retained under a server response `raw` member for debug-authorized callers; ordinary Run UI exposes it through **View JSON** only after redaction.
- Null optional media is not a failed run. The relevant component renders an honest unavailable state and the rest of the envelope continues.

The result envelope does not replace a skill's domain `output_schema`. The raw container result is validated against that schema first; normalization is a typed projection into the stable display contract. CI fixtures should validate both the domain output and the projected `omo.result/v1` envelope.

## Streaming and progress event contract

Run state arrives as ordered events. SSE example:

```text
event: progress
data: {"schema_version":"omo.run-event/v1","run_id":"run_01K2W8N4R7J4","sequence":7,"status":"running","phase":"assembling","label":"Assembling video","progress_pct":84}

event: artifact
data: {"schema_version":"omo.run-event/v1","run_id":"run_01K2W8N4R7J4","sequence":8,"status":"running","phase":"delivering","artifact":{"kind":"image","url":"/v1/runs/.../poster","filename":"poster.jpg","mime":"image/jpeg","size":428112}}

event: completed
data: {"schema_version":"omo.run-event/v1","run_id":"run_01K2W8N4R7J4","sequence":9,"status":"completed","result":{"schema_version":"omo.result/v1","type":"bundle","artifacts":[]}}
```

The client ignores duplicate/stale sequences, never decreases observed progress, and uses the manifest's phase label for a known phase ID. An absent `progress_pct` is indeterminate—not permission to invent a percentage. Partial text uses a separate bounded `text_delta` event only when the manifest declares streaming; it is shown as escaped text until the final schema-valid result arrives.

## Resolver and registry architecture

### Runtime flow

```text
GET compiled run manifest                 authenticated run events
        │                                          │
        ├── output_schema                          ├── phase/status/progress
        ├── ui.outputs                             └── completed raw result
        └── phases[]                                         │
                │                                             ▼
                └──────────────────────────────→ validate against output_schema
                                                              │
                                                              ▼
                                                  normalize to omo.result/v1
                                                              │
                                                              ▼
                                              resolve(schema, value, envelope, ui)
                                                              │
                                  ┌───────────────────────────┼─────────────────────┐
                                  ▼                           ▼                     ▼
                         registry renderer             OutputGroup          FallbackOutput
                                  │                           │                     │
                                  └───────────────────────────┴─────────────────────┘
                                                              │
                                                              ▼
                                               OutputFrame + safe actions
```

The registry is an ordered array of pure predicates and render functions, not a class hierarchy:

```js
const outputRegistry = [
  ['progress', isNonTerminalRun, ProgressTimelineOutput],
  ['bundle', isArtifactBundle, ArtifactGridOutput],
  ['video', isVideo, VideoPlayerOutput],
  ['audio', isAudio, AudioPlayerOutput],
  ['images', isImageCollection, ImageGalleryOutput],
  ['image', isImage, ImageGalleryOutput],
  ['pdf', isPdf, PdfDocumentOutput],
  ['archive', isArchive, ArchiveDownloadOutput],
  ['markdown', isMarkdown, MarkdownOutput],
  ['file', isDownloadableFile, FileDownloadOutput],
  ['link', isGenericUri, LinkCardOutput],
  ['json', isStructuredData, JsonViewerOutput],
  ['text', isText, PlainTextOutput]
];
```

Resolution precedence is:

1. non-terminal run state → `ProgressTimelineOutput`;
2. validated `omo.result/v1` `type` and artifact `kind`/`mime`;
3. compatible `ui.outputs[path].renderer` hint;
4. schema `contentMediaType`, then specific/custom `format` (`markdown`, `image-url`, `audio-url`, `video-url`, `pdf-url`, `zip-url`);
5. artifact-object or artifact-array shape;
6. array/object/scalar JSON shape;
7. generic `format: "uri"` → `LinkCardOutput`;
8. `FallbackOutput`.

Envelope discriminants outrank visual hints because the delivery Worker has resolved ambiguous transport values. A UI hint may select only a schema-compatible renderer. Generic URI values stay links; the resolver never infers media from `/video_url`, filename extension alone, or descriptive prose. MIME is normalized to lowercase and parameters are removed before matching.

The resolver returns a serializable view model (`path`, `component`, `label`, `value`, `artifact`, `actions`, `metadata`, `children`, `source`) rather than HTML. Rendering, URL policy, artifact refresh, actions, and analytics remain separate services. Validate the whole raw result before showing success; a component-level preview error does not invalidate an otherwise valid delivery.

### Presentation hints

Schema defines valid data; presentation hints only remove ambiguity:

```json
{
  "ui": {
    "outputs": {
      "/book": { "renderer": "markdown", "primary": true },
      "/video_url": { "renderer": "video", "mime": "video/mp4" },
      "/contact_sheet_url": { "renderer": "image", "mime": "image/jpeg" },
      "/usage": { "placement": "metadata" }
    }
  }
}
```

The compiler rejects unknown renderer names, incompatible schema/renderer pairs, unsafe MIME/protocol claims, and two `primary` outputs. New schemas should prefer standard `contentMediaType`, Omo's registered URL formats, and the result envelope so most manifests need no hints.

## Practice-schema resolution

| Practice result | Normalized display | Notes |
|---|---|---|
| Woven `book` | `MarkdownOutput` | Transitional `/book` UI hint; add `contentMediaType: text/markdown` in a future schema revision. |
| Woven `page_plan[]` | `OutputGroup` ordered list | Scalar items remain readable; raw JSON stays available. |
| Animation `artifacts[]` | `ArtifactGridOutput` | Worker exchanges private `object_key` values for authorized URLs. |
| Animation `kind: video` | `VideoPlayerOutput` | `content_type: video/mp4` confirms the native player. |
| Animation transcript/frame brief | `FileDownloadOutput` / `JsonViewerOutput` | Preview JSON when fetched and valid; always retain download. |
| de Mello `video_url` | `VideoPlayerOutput` | Normalize in Worker or declare a `/video_url` output hint; URI alone is only a link. |
| de Mello `contact_sheet_url` | `ImageGalleryOutput` | Normalize to image artifact; do not infer from the property name in browser code. |
| UGC HeyGen `video` | `VideoPlayerOutput` or unavailable state | Use `thumbnail_url` as poster and `subtitle_url` as supporting artifact. |
| UGC script/captions | `OutputGroup` | Hook, lines, CTA, and captions are semantic text sections. |
| GPT Image Seedance `images[]` | `ImageGalleryOutput` | Worker supplies image MIME and filenames in envelope. |
| Claude SEO findings | `OutputGroup` + `JsonViewerOutput` | Uniform issue/fix/priority cards; full JSON is downloadable. |

## Run-page integration contract

The sibling Run page should load this library once and never branch on skill slug:

```js
const output = OmoOutputLibrary.mount({
  root: document.querySelector('[data-run-output]'),
  schema: manifest.output_schema,
  ui: manifest.ui && manifest.ui.outputs,
  phases: manifest.phases,
  resolveArtifact: ({ runId, artifactId }) =>
    api.get(`/v1/runs/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(artifactId)}`),
  onAction: analytics.track
});

runEvents.on('event', event => output.update(event));
runRequest.then(response => output.complete(response.result, response.raw_output));
```

`mount` renders the initial ready state. `update` accepts monotonic `omo.run-event/v1` events. `complete` validates the raw output against the manifest schema, verifies the normalized envelope, resolves safe actions, and renders the result. `destroy` removes listeners and revokes locally created object URLs. The integration surface accepts plain objects and callbacks so it can be implemented in the current dependency-free Run page and later wrapped by any framework.

## URL, artifact, and content safety

- Permit `https:` everywhere and same-origin `http:` only in local development. Allow small `data:` values only for an explicit MIME/size list. Reject `javascript:`, `file:`, server-supplied `blob:`, credentials in URLs, and protocol-relative URLs.
- External links always use `target="_blank"` and `rel="noopener noreferrer"`. Downloads use server-provided `Content-Disposition`; the browser-suggested filename is sanitized and cannot contain a path.
- Signed URL expiry does not turn success into failure. The renderer calls the artifact refresh endpoint once, replaces the URL, and presents **Refresh link** if authorization/retention prevents refresh.
- Prefer stable owner-authorized artifact endpoints over exposing raw R2/provider signatures. Never leak storage keys, bearer tokens, hashes used as credentials, internal platform flags, or unredacted provider payloads in the friendly output.
- Native image/audio/video/PDF rendering is MIME-gated. HTML and SVG returned by a skill download as files by default; they are not inserted into the Run page DOM.
- Copy actions copy the actual text or safe URL, not hidden markup. Download-all is server-created, scanned, bounded, and owner-authorized.

## Mobile and accessibility baseline

- At 800 px and below, the Run page order is Inputs → Examples → Progress/Output. Output grids collapse without nested desktop scroll regions.
- At 375 px, page gutters are 14 px, component previews and schema/debug panes stack, media width is `100%`, filenames wrap, and the document has no horizontal overflow.
- Image zoom uses a real dialog with focus return, Escape close, named controls, and non-empty alt text. Media retains native controls and captions when available.
- Progress is announced politely by phase, not on every percent tick. Completion and terminal errors are announced once. Reduced-motion users get no sweeping or simulated animation.
- Status, selected state, expiry, and errors never rely on color alone. Every action remains keyboard reachable with a visible focus ring.

## What not to build yet

- No per-skill templates, generated HTML, remote renderer modules, iframes, arbitrary HTML results, or giant schema-rendering dependency.
- No browser-side archive generation for production artifacts, no client signing of artifact URLs, and no scraping provider pages for previews.
- No table-first rendering for arbitrary object arrays; use cards unless the schema is uniform and narrow enough to remain usable at 375 px.
- No pretending that `format: "uri"` identifies media. Add a normalized artifact kind, content type, or compatible UI hint.
- No final “success” state before the raw result and normalized envelope validate.

## Acceptance criteria

- Every requested output class has one prebuilt renderer and a visible sample in `site/run-output-library.html`, with its selecting JSON beside it.
- Woven, Audio Symbolic Animation, de Mello Awake, and UGC HeyGen resolve through the registry/envelope without Run-page slug branches. The two additional repository output schemas also have a defined path.
- Unknown results remain inspectable and downloadable through `FallbackOutput`; a required value is never silently omitted.
- Artifact URLs are owner-authorized, protocol/MIME checked, refreshable, and safe external links use `noopener noreferrer`.
- Progress uses server events and manifest phase labels, not timers pretending to be execution state.
- Desktop and 375 px have no document-level horizontal overflow; all controls are keyboard/touch usable.
- Adding a compatible container requires compiling its manifest and emitting `omo.result/v1`, not editing Run-page HTML.
