# Omo prebuilt input UI library

**Status:** component and runtime design, 2026-08-12
**Scope:** the hosted Run page. This is intentionally a small registry, resolver, and fallback—not a general-purpose JSON Schema form framework.

## Decision

Compile every hostable skill into one run manifest. At runtime the Run page reads the manifest, walks `input_schema.properties` in declaration order, and resolves each property to one of the prebuilt controls below. JSON Schema remains the validation and transport contract; UI hints only select a better presentation. This replaces the current field-name heuristics and bespoke listing forms without making the compiler generate HTML.

The first library should contain 18 components:

1. `ShortTextField`
2. `LongTextField`
3. `SelectField`
4. `NumberField`
5. `BooleanField`
6. `UrlField`
7. `EmailField`
8. `FileUploadField`
9. `ImageUploadField`
10. `AudioUploadField`
11. `DateField`
12. `TagsListField`
13. `PairListField`
14. `RangeField`
15. `CodeField`
16. `MarkdownField`
17. `KeyValueMapField`
18. `HiddenConstField`

`ObjectGroup` is a resolver layout primitive, not a nineteenth input: it recursively groups an ordinary fixed-property object. `FallbackField` is the safety net, not a type authors deliberately choose.

## What the repository requires now

- Woven needs three long-text controls (`how_you_met`, `favorite_moments`, `inside_jokes`) and two enums (`style`, `length`). Its schema already supplies titles, descriptions, examples, defaults, lengths, and required state.
- Japanese Style Story Video is catalogued as audio + fixed style + duration. The practice animation schema makes the eventual contract concrete: a private audio artifact object, an integer duration enum, hidden `style: "sumi-e"`, and an optional passage hint.
- The current catalog arrays in `site/ig-more.js` are display labels, not typed contracts. They should become a temporary compatibility source only; the run UI should prefer the compiled manifest.

## Shared field anatomy

Every visible component is wrapped by the same `FieldFrame`:

- human label from `title`, falling back to title-cased property name;
- required marker when the parent object's `required` contains the property;
- one-sentence help from `description`;
- control with `name`, stable `id`, `aria-describedby`, and an example placeholder;
- optional constraint/meta line (for example “12–1,200 characters” or “MP3, M4A, WAV · up to 50 MB”);
- inline error reserved below the control so validation does not cause a large layout jump;
- touched-on-blur validation, then validate-all on Run; clear the error as soon as the value becomes valid.

Labels and descriptions are the instructions. Placeholders are short examples, never essential information. Required fields do not use placeholder text as their only cue.

## Type catalogue

Each “example card” below means one right-panel card with a short title, representative input payload, a compact “It makes” output preview, and a **Use example** action that fills the whole form. It is not a separate example for one field.

### 1. `ShortTextField`

- **UI:** `<input type="text">`; one line, no auto-grow. Use for names, titles, subjects, and short instructions.
- **Schema mapping:** `type: "string"` with no `format`, `enum`, or media encoding, and `ui.widget: "text"`; also the default string when `maxLength <= 160`.
- **Validation:** `required`, `minLength`, `maxLength`, `pattern`; normalize line endings but do not trim or rewrite user content before submission. Show remaining characters only when `maxLength` is present and below 500.
- **Mobile:** full width, 44 px minimum hit height, appropriate `autocomplete` where known.
- **Example card:** “Keepsake for Maya & Theo” → `{ "title": "Seven Years, Two Cities" }` → a named story draft.

### 2. `LongTextField`

- **UI:** `<textarea>` with a 4-row minimum and vertical resize; optional soft character counter.
- **Schema mapping:** string with `ui.widget: "textarea"`, or unformatted string with `maxLength > 160`; compiler may choose it for narrative fields even without a maximum.
- **Validation:** required/length/pattern. Preserve newlines. Do not silently truncate.
- **Mobile:** full width, 120 px minimum height; no horizontal resize or fixed columns.
- **Example card:** “The rainy bookshop” → complete Woven facts → a warm opening chapter.

### 3. `SelectField`

- **UI:** native `<select>` for up to eight options; accessible button/listbox may replace it later for large or searchable sets. Display labels can differ from submitted values.
- **Schema mapping:** `enum` on string/number/integer; `oneOf` entries with `const` + `title`; `ui.widget: "select"` wins. A single-value enum resolves to `HiddenConstField`.
- **Validation:** required selection and exact membership. Preserve the enum's primitive type when serializing (for example `60`, not `"60"`).
- **Mobile:** native picker, full width; never a hover-only menu.
- **Example card:** “Warm, short keepsake” → `{ "style": "warm", "length": "short" }` → three concise chapters.

### 4. `NumberField`

- **UI:** `<input type="number">` with optional unit suffix; increment/decrement remains native. Integers use `step="1"` unless `multipleOf` says otherwise.
- **Schema mapping:** `type: "number" | "integer"` without enum and without `ui.widget: "range"`.
- **Validation:** required, finite number, integer fidelity, `minimum`/`maximum`, exclusive bounds, and `multipleOf`. Empty is not zero. Serialize to a number.
- **Mobile:** `inputmode="decimal"` or `numeric`; unit stays visible without shrinking the input below a usable width.
- **Example card:** “Five scene variations” → `{ "scene_count": 5 }` → five generated concepts.

### 5. `BooleanField`

- **UI:** real checkbox inside a large label row; visual treatment may look like a switch, but keyboard and checked semantics remain native. Description explains the consequence.
- **Schema mapping:** `type: "boolean"`.
- **Validation:** required means the key must be present, not that the value must be true. Use `const: true` only for mandatory consent.
- **Mobile:** the entire row is a 48 px tap target; no tiny standalone toggle.
- **Example card:** “Pseudonymize names” → `{ "pseudonymize_names": true }` → private, anonymized output.

### 6. `UrlField`

- **UI:** `<input type="url">`, with a link icon/prefix only if it does not obscure the value.
- **Schema mapping:** string with `format: "uri" | "url" | "uri-reference"`, or explicit `ui.widget: "url"`.
- **Validation:** required/length plus a URL parse; permit only manifest-declared protocols, defaulting to `https:` and `http:`. The server still validates and performs SSRF protections.
- **Mobile:** `inputmode="url"`, `autocapitalize="none"`, `spellcheck="false"`; allow wrapping only in the help/error text, not inside the control.
- **Example card:** “Audit a product page” → `{ "product_url": "https://example.com/products/travel-mug" }` → structured recommendations.

### 7. `EmailField`

- **UI:** `<input type="email">` with standard browser affordances.
- **Schema mapping:** string with `format: "email" | "idn-email"`, or `ui.widget: "email"`.
- **Validation:** browser email grammar plus schema lengths/pattern; do not claim mailbox existence.
- **Mobile:** `inputmode="email"`, `autocapitalize="none"`, `autocomplete="email"` only when the field actually identifies the user.
- **Example card:** “Send the research brief” → `{ "recipient": "maya@example.com" }` → a ready-to-send delivery package.

### 8. `FileUploadField`

- **UI:** dashed drop zone backed by `<input type="file">`; selected file row shows name, size, upload state, replace, and remove. The browser uploads to the private artifact service first, then writes only an artifact reference into run JSON.
- **Schema mapping:** string with `format: "binary"`, `contentEncoding: "base64"`, or `contentMediaType`; most importantly, an object such as `{object_key, sha256, bytes, content_type}` with `ui.widget: "private_artifact_upload"`.
- **Validation:** `accept`/content type, maximum bytes, one-file rule unless the schema is an array, non-empty upload, checksum/reference returned, and upload completion before Run. Never place raw private file bytes in request JSON.
- **Mobile:** large **Choose file** action; drop copy becomes secondary because drag-and-drop is uncommon. File row wraps safely.
- **Example card:** “Customer interview notes” → uploaded `.txt` → a themed insight report.

### 9. `ImageUploadField`

- **UI:** file drop zone plus local thumbnail, filename, dimensions when available, replace/remove. Optional multi-image version is an array rendered as a reorderable thumbnail list.
- **Schema mapping:** file contract plus `contentMediaType: "image/*"`, allowed image MIME enums, or `ui.widget: "image_upload"`.
- **Validation:** MIME, bytes, count, optional minimum/maximum width/height and aspect ratio; validate again after server decode because extensions are untrusted.
- **Mobile:** can offer camera/photo library through native file input; thumbnail never exceeds container width; reordering also has move buttons, not drag only.
- **Example card:** “Ceramic mug on white” → one product image → three ad-ready scene variations.

### 10. `AudioUploadField`

- **UI:** file drop zone with file metadata and an `<audio controls>` preview after selection/upload.
- **Schema mapping:** file contract plus audio MIME types, or `ui.widget: "audio_upload"`. This is the correct presentation for the practice schema's `audio_artifact` object.
- **Validation:** MIME, bytes, duration range when known, upload completion, and returned artifact reference. For the practice workflow: MP3/M4A/WAV and at most 50 MiB from its byte maximum.
- **Mobile:** full-width picker and native audio player; metadata stacks under the filename.
- **Example card:** “Present-moment reflection” → ten-second voice clip → vertical sumi-e animation plus frame artifacts.

### 11. `DateField`

- **UI:** `<input type="date">`; date-time is a separate future registry entry rather than overloading it.
- **Schema mapping:** string with `format: "date"`, or `ui.widget: "date"`.
- **Validation:** real calendar date, `formatMinimum`/`formatMaximum` when emitted, and any `const`/enum constraint. Submit canonical `YYYY-MM-DD`; never apply timezone conversion.
- **Mobile:** native date picker; label repeats the expected format in help text only where native support is weak.
- **Example card:** “Launch on 18 September” → `{ "launch_date": "2026-09-18" }` → a dated rollout plan.

### 12. `TagsListField`

- **UI:** token/chip input. Enter or comma commits an item; Backspace removes the last empty-adjacent item; each chip has a named remove button. Paste may split on newlines.
- **Schema mapping:** `type: "array"` with scalar `items`, especially unique strings; explicit `ui.widget: "tags"`. A plain vertical list presentation is available through `ui.widget: "list"`.
- **Validation:** `minItems`, `maxItems`, `uniqueItems`, and all `items` constraints. Do not de-duplicate silently; explain the duplicate.
- **Mobile:** chips wrap; input always keeps at least 120 px; add/remove targets are at least 36 px.
- **Example card:** “Eco launch themes” → `["quiet luxury", "recycled", "studio light"]` → a three-angle campaign.

### 13. `PairListField`

- **UI:** repeatable two-column rows with two labeled controls and remove; **Add pair** appends. Examples include before/after, term/definition, question/answer, or start/end.
- **Schema mapping:** array whose `items` is a two-property object, a two-item `prefixItems` tuple, or `ui.widget: "pair_list"`. Property titles become the two sublabels.
- **Validation:** array limits plus both child schemas; pair stays atomic, so an incomplete row is invalid rather than partly submitted.
- **Mobile:** each pair becomes a bordered one-column mini-card; remove button stays text-labeled and does not float over an input.
- **Example card:** “Myth vs fact” → two claim/correction pairs → a swipeable fact-check carousel.

### 14. `RangeField`

- **UI:** `<input type="range">` plus a synchronized numeric value bubble/field and visible endpoints. Arrow keys work; current value is announced.
- **Schema mapping:** number/integer with finite min and max plus `ui.widget: "range"`; never infer a slider solely from bounds because precision tasks need `NumberField`.
- **Validation:** numeric bounds and `multipleOf`/step. Clamp pointer interaction in the UI, but reject externally supplied out-of-range values.
- **Mobile:** full-width track with at least 44 px vertical interaction area; value appears above or beside without causing horizontal overflow.
- **Example card:** “Playfulness 70%” → `{ "playfulness": 70 }` → a lively but credible voice.

### 15. `CodeField`

- **UI:** monospace textarea with line numbers optional, tab inserts spaces, and a language badge. No heavy editor dependency in v1.
- **Schema mapping:** string with `format: "code"`, a recognized `contentMediaType` such as `application/json`, or `ui.widget: "code"`; `ui.language` controls the badge.
- **Validation:** string constraints plus syntax parse for declared JSON; other languages remain text unless a safe parser is already bundled.
- **Mobile:** monospace area scrolls internally for intentional long code, but the page itself never overflows; toolbar wraps.
- **Example card:** “Normalize webhook JSON” → sample payload → a validated transform and result.

### 16. `MarkdownField`

- **UI:** textarea with **Write / Preview** tabs; preview is sanitized and never executes HTML. No full rich-text editor.
- **Schema mapping:** string with `format: "markdown"`, `contentMediaType: "text/markdown"`, or `ui.widget: "markdown"`.
- **Validation:** string constraints; sanitized preview is presentation, not a mutation of submitted Markdown.
- **Mobile:** tabs remain visible above a single full-width editor/preview; do not split editor and preview side by side.
- **Example card:** “Founder launch note” → structured Markdown brief → polished announcement copy.

### 17. `KeyValueMapField`

- **UI:** repeatable key/value rows with add/remove; optional key suggestions. Values use the schema's `additionalProperties` component recursively when practical.
- **Schema mapping:** `type: "object"` with `additionalProperties` as a schema and no fixed `properties`, or `ui.widget: "key_value"`.
- **Validation:** required/non-empty keys, unique keys, `minProperties`/`maxProperties`, `propertyNames`, and the value schema. Show duplicate key errors on both conflicting rows.
- **Mobile:** key and value stack within each row; destructive remove action is text-labeled.
- **Example card:** “Brand vocabulary” → `{ "customer": "member", "cheap": "accessible" }` → on-brand rewrites.

### 18. `HiddenConstField`

- **UI:** no editable control. A compact read-only summary may say “Style: sumi-e” when the fixed value helps the buyer understand the run.
- **Schema mapping:** `const`, or a one-value `enum`; explicit `ui.widget: "hidden"` with `value` is allowed only if it still validates against the schema.
- **Validation:** the resolver injects the value; reject any runtime mutation and validate it with the full payload. Never use hidden controls for security decisions.
- **Mobile:** no special behavior; read-only summaries wrap.
- **Example card:** “Sumi-e animation” includes `{ "style": "sumi-e" }` in the filled request while keeping it non-editable.

### Layout primitive: `ObjectGroup`

For `type: "object"` with fixed `properties`, render a labeled `<fieldset>` and recursively resolve its children. Use this for small semantic groups such as dimensions or contact details. Do not expose transport-shaped artifact objects as four manual inputs; a `ui.widget` override resolves those to an upload component. At 375 px any multi-column children stack.

### Safety net: `FallbackField`

If no registry predicate matches, render a normal `LongTextField` labeled “Advanced input”, plus a collapsed **Schema details** disclosure containing the exact property schema as escaped, read-only JSON. Accept JSON text when the unknown schema is non-string; parse it locally and then validate the result. Record an analytics warning with skill slug + property path so the missing component is visible. Never silently skip a required input and never use `innerHTML` for schema text.

## Resolver and registry architecture

### Runtime flow

```text
GET compiled run manifest
        │
        ├── examples[] ───────────────→ example-card gallery
        ├── price_usd ────────────────→ “Run it — ≈ $0.40”
        ├── phases[] ─────────────────→ progress labels
        ├── output_schema ────────────→ output renderer registry
        └── input_schema.properties
                    │ walk in declaration order
                    ▼
             resolve(path, schema, required, ui)
                    │
                    ├── registry predicate match → FieldFrame(Component)
                    ├── fixed object → ObjectGroup(children)
                    └── no match → FallbackField + raw schema disclosure
```

The registry is an ordered array, not a class hierarchy. Specific predicates come first (`const`, upload override, enum, formats, arrays/objects), then primitive defaults, then fallback.

```js
const fieldRegistry = [
  ['hidden', isConst, HiddenConstField],
  ['upload', isPrivateArtifact, FileUploadField],
  ['enum', hasEnum, SelectField],
  ['url', isUrl, UrlField],
  ['email', isEmail, EmailField],
  ['date', isDate, DateField],
  ['tags', isScalarArray, TagsListField],
  ['pairs', isPairArray, PairListField],
  ['map', isOpenMap, KeyValueMapField],
  ['boolean', isBoolean, BooleanField],
  ['number', isNumber, NumberField],
  ['long_text', isLongString, LongTextField],
  ['text', isString, ShortTextField]
];
```

Resolution precedence is:

1. `ui.fields[path].widget` override, if it names an allowed registry component and is schema-compatible;
2. `const`/single enum;
3. media/upload semantics;
4. multi-value enum/`oneOf` constants;
5. string formats/content type;
6. array/object shape;
7. primitive type;
8. `FallbackField`.

The resolver returns a small field model (`path`, `component`, `label`, `description`, `required`, `default`, `example`, `constraints`, `ui`) rather than HTML. Rendering, value collection, and validation are separate. Browser validation improves feedback, but the same complete JSON instance must be validated against Draft 2020-12 on the server before any provider call or spend.

### Per-listing overrides

Schema answers “what data is valid.” `ui` answers only “which compatible presentation is best.” Keep it optional and shallow:

```json
{
  "ui": {
    "order": ["audio_artifact", "passage_hint", "target_duration_seconds", "style"],
    "fields": {
      "audio_artifact": {
        "widget": "audio_upload",
        "accept": ["audio/mpeg", "audio/mp4", "audio/wav", "audio/x-wav"],
        "help": "Upload a short spoken reflection."
      },
      "passage_hint": { "widget": "textarea", "rows": 3 },
      "style": { "summary": true }
    }
  }
}
```

Overrides cannot weaken schema constraints, invent a value that fails the schema, mark a required field optional, or change transport types. The compiler rejects unknown widget names and incompatible pairs. Most listings should need no override beyond one media upload hint.

### Examples and example cards

Examples belong in the compiled manifest because they must match the exact versioned schema the form uses. Catalog data may author them, but the compiler copies, validates, and freezes them beside the schema. A card is whole-form data, not placeholder fragments:

```json
{
  "id": "rainy-bookshop",
  "title": "The rainy bookshop",
  "caption": "Warm · short keepsake",
  "input": {
    "how_you_met": "We reached for the same travel book on a rainy afternoon.",
    "favorite_moments": "Seven years, two cities, and adopting our corgi.",
    "inside_jokes": "Wrong turn, best view.",
    "style": "warm",
    "length": "short"
  },
  "output_preview": {
    "kind": "text",
    "label": "It makes",
    "text": "A warm three-chapter keepsake with a PDF-ready page plan."
  },
  "media": { "kind": "image", "url": "/covers/woven-3-pages.png", "alt": "Open keepsake book" }
}
```

The compiler validates every `input` against `input_schema`, verifies stable unique IDs, checks media URLs/alt text, and limits preview copy. **Use example** replaces the full form after a confirmation only when it would overwrite touched values; then it scrolls to Inputs on mobile. Schema property-level `examples[0]` supply placeholders when present. If absent, use a type-safe generic placeholder—never scrape prose with field-name regexes.

## Compiler-emitted run manifest

The minimum hostable contract is the five requested runtime values below. `schema_version` and `slug` make it cacheable and diagnosable; `ui` is optional.

```json
{
  "schema_version": "omo.run-manifest/v1",
  "slug": "woven-relationship-book-maker",
  "input_schema": { "type": "object", "properties": {}, "required": [] },
  "output_schema": { "type": "object", "properties": {}, "required": [] },
  "examples": [],
  "price_usd": 0.40,
  "phases": [
    { "id": "write", "label": "Writing your story" },
    { "id": "polish", "label": "Polishing without changing facts" },
    { "id": "deliver", "label": "Preparing your files" }
  ],
  "ui": { "order": [], "fields": {} }
}
```

Contract rules:

- `input_schema` and `output_schema` are inline Draft 2020-12 schemas. Do not require a second fetch or a filesystem path in the browser.
- `examples` defaults to `[]`; each input is compile-time schema-valid. Media is optional.
- `price_usd` is a finite non-negative number, already buyer-facing and guarded by pricing policy. Readiness/chargeability may remain deployment metadata outside this UI contract; an unavailable run must never expose an enabled Run button.
- `phases` is an ordered, honest set of user-readable progress labels. The server reports phase IDs; the client does not pretend progress with timers.
- `ui` is optional. Omit empty keys in production. It controls presentation only.

The existing container manifest can evolve without duplication by adding inline `output_schema`, `examples`, `price_usd`, and `phases`, while retaining endpoint/readiness/pricing evidence for execution. During migration, the compiler can derive `price_usd` from `pricing.display_price_usd`, but the browser should consume one canonical field.

## Submission and validation lifecycle

1. Initialize each field from schema `default`, then inject const values. Do not fill property examples as actual values.
2. When an example is used, replace the form model with its validated `input`.
3. On Run, collect typed values: numbers stay numbers, unchecked booleans are `false` when present, optional empty fields are omitted, arrays/objects remain structured, and upload components contribute only artifact references.
4. Validate the complete object client-side. Focus the first invalid field and show an error summary linked to every invalid field.
5. Submit the exact object. Server-side validation is authoritative and occurs before execution/spend.
6. Map `422` errors by JSON Pointer back to fields; unknown/global errors appear above the button without erasing input.

## Price and progress

Format `price_usd` as USD with two decimals and place it in the primary action: **Run it — ≈ $0.40**. The approximation mark communicates that the displayed price is the guarded run quote; it is not permission to charge a different amount after the click. The backend must authorize the actual charge against that quote or return a new quote before execution. Zero can read **Run it — free**.

Disable Run for unavailable/uncharged manifests and explain why; never show a price as purchasable when readiness says otherwise. Use server-reported `phases[].id` to update progress. A progress bar may be indeterminate; the label must be truthful.

## Output renderer registry

Treat output the same way as input: schema-driven renderers with a safe raw fallback.

- `string` + Markdown format/content type → sanitized rendered Markdown with **Copy** and **Download .md**.
- ordinary `string` → readable paragraphs/preformatted text depending on content; **Copy**.
- scalar arrays → list/chips; arrays of objects → compact cards or table only when property shapes are uniform.
- artifact reference/object with URL + media/content type → owned, signed link; image/audio/video get native preview plus **Download**. Never render arbitrary returned HTML.
- fixed object → titled definition sections recursively; keep raw JSON behind **View JSON**.
- unknown/mixed output → escaped pretty JSON and **Download JSON**.

Artifact URLs are output data, not trusted markup. Allow `https:` (and same-origin test URLs locally), show filename/type/size when available, use `rel="noopener noreferrer"` for external links, and let signed URL expiry errors request a refreshed link. Validate the completed `output.json` against `output_schema` before displaying a success state.

For Woven, `book` becomes sanitized Markdown and `page_plan` a readable ordered list. For the animation schema, its artifact collection becomes one video player/download plus transcript and frame-brief downloads; media/delivery details render as metadata. Raw JSON always remains available for debugging.

## Mobile and accessibility baseline

- At 800 px and below, order is Inputs → Examples → Run state/output; remove sticky/nested desktop scroll.
- At 375 px, use 14 px page gutters, one-column example cards, and no document-level horizontal overflow.
- Controls use a 44 px minimum interactive height, visible focus, explicit labels, error association, and native semantics.
- Repeatable controls provide add/remove/move buttons usable without drag. Uploads work without drag-and-drop.
- Example application and file upload state are announced through a polite live region. Progress uses `role="status"`; errors use an assertive summary only after submission.
- Respect reduced motion and never rely on color alone for required, selected, error, or progress state.

## What not to build yet

- No drag-and-drop form builder, plugin runtime, remote component loading, or per-skill generated HTML.
- No giant schema library dependency until real manifests prove the small resolver insufficient.
- No conditional-schema UI (`if/then/else`, complex `oneOf`, circular `$ref`) in v1. Unsupported constructs go to `FallbackField` and block automatic promotion until reviewed.
- No bespoke visual editor, color picker, geographic picker, credential/password field, or rich-text editor until a real hostable skill requires it.

## Acceptance criteria for implementation

- The two practice manifests render without property-name heuristics: Woven as 3 textareas + 2 selects; animation as audio upload + optional textarea + duration select + fixed style.
- Every required property is visible or deterministically injected; an unsupported required property cannot disappear.
- All example payloads pass the input schema in CI.
- Desktop keeps the compact input rail and example workspace; 375 px has no horizontal overflow.
- Run shows `≈ price_usd`; output is validated then rendered by schema with raw JSON fallback.
- Adding a compatible container requires compiling its manifest, not editing Run-page HTML.
