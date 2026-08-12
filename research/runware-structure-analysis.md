# Runware Playground structure analysis

Analyzed 12 August 2026 from the founder's six original Runware screenshots at full resolution, plus the live Runware homepage and documentation. The screenshots are the primary source for the Playground structure; the public pages confirm the request/response and API language.

## Executive structure

Runware is a full-height application workspace, not a centered marketing form. Beneath a persistent global header, the product divides the viewport almost exactly **one-third / two-thirds**:

- **Left, about 1,005 px of a 3,020 px capture (33%)**: model identity, task tags, request mode, a dense independently scrolling form, and a sticky Generate/Reset action shelf.
- **Right, about 2,015 px (67%)**: an examples-first workspace with its own toolbar and independently scrolling, media-led two-column card gallery.
- A single 1 px rule separates the panes. Each pane owns its scroll position: screenshots 2/3 and 5/6 show the left form moving without changing the right examples; screenshots 1/3 show the right gallery moving while the request chrome stays put.

The hierarchy is important: examples are not helper copy tucked under inputs. They are the dominant default state of the output pane. The form answers “what can I provide?” while the gallery answers “what does a good request produce?” A per-card **Use example** action connects the two.

## Persistent shell and visual system

- Global header is approximately 107–125 px high in the 3,020 px-wide captures.
- Navigation: Runware mark; Models; Playground (active with a thin lime underline); Usage; OpenClaw; Account; Docs; Pricing; then search, balance/add funds, notifications, and user avatar.
- Canvas and panels use near-black charcoals; fine medium-gray 1 px borders create nearly all grouping.
- Soft white is used for primary text, gray for metadata, pale neon lime for primary/active states, cyan for capability tags, and muted olive for edit tags.
- Rounded rectangles repeat at every level: model selector, chips, tabs, inputs, cards, and CTAs. Major cards use roughly 18–20 px radii; inputs use roughly 12–14 px.
- The left pane uses about 46–48 px horizontal padding and 24–32 px vertical rhythm. The right gallery has about 48 px outer padding and a 30–32 px column gap.

## Screenshot 1 — 2.15.19 pm (LTX, upper form + upper examples)

**Left pane**

- A large outlined model selector shows a black square `LTX` thumbnail, `Lightricks / LTX-2.5 Pro`, a `Cmd /` shortcut badge, and up/down chevrons.
- Capability tags wrap beneath it: Text to Video, Image to Video, Video to Video, Audio to Video (cyan), then Edit and Extend (olive). Sliders, favorite, duplicate, and overflow icons sit to the right.
- The `REQUEST` bar has a bookmark and a segmented `Form / JSON` control. Form is filled lime; JSON remains dark.
- `Inputs` is an expanded accordion with a layers icon and add buttons for Audio, Frame Images, and Reference Images.
- `Core` is expanded with a sparkle icon. It contains a required `Prompt` label, circled info control, a very large textarea, and an assist/sparkle affordance at the textarea's lower-right.
- The next row begins Width × Height plus a Custom aspect-ratio selector. Width and height are numeric-looking controls with `px` suffixes.
- A bottom shelf stays fixed over the scrolling form: full-width lime **Generate** with lightning and `⌘ Enter` keycaps, followed by a full-width outlined Reset.

**Right pane**

- Local toolbar: selected `Examples` with count 17, then History, Pricing, Integrate, Schema, and Docs. At right are selected grid view, list view, alternate layout, a divider, and filters.
- Examples form a strict two-column grid. Each card has a large roughly 16:9 video preview, centered circular play button, and a dark `Use example` overlay at lower-right with lime play icon.
- A separate metadata footer shows model name on the left, model identifier on the right, cost on its own line, then a two-line clamped prompt.
- Visible examples: an ivory motion ident ($1.0914); Japanese washi making ($1.8117); offshore-wind VFX ($1.4552); oyster-farm animation ($3.3424).
- No code, response, or progress is visible. The examples gallery is the default response-side state.

## Screenshot 2 — 2.15.22 pm (LTX, lower form + same examples)

- Model/request chrome and examples remain fixed while the left form has scrolled down.
- The tail of the Prompt textarea remains visible, followed by the full Width × Height + Custom row.
- Duration is a full-width dropdown with filmstrip icon. FPS is a half-width dropdown with the same icon.
- Settings and API appear as collapsed accordion rows separated by rules.
- Generate and Reset remain fixed at the bottom, proving the action shelf does not scroll with fields.
- The right-side toolbar and same four example cards do not change.

## Screenshot 3 — 2.15.26 pm (LTX, right gallery scrolled)

- The left panel stays in its lower-form position. A tooltip under the star says `Save request to library`.
- The right pane has scrolled independently: its local toolbar is above the viewport and media begins under the global header.
- Newly visible example pairs are professional portrait / sewer-pipe product explainer, then chef's-knife macro / brass bird automaton; teal warehouse and archival portrait previews begin below.
- Card construction remains invariant: media-first preview, centered play, overlaid Use example, then model/slug/cost/truncated request.
- The small screenshot thumbnail at bottom-right is a macOS capture overlay, not product UI.

## Screenshot 4 — 2.15.32 pm (LTX, API accordion expanded)

- The left form is deeper in its scroll. `Settings` is expanded with an `+ Inference settings` button.
- `API` is expanded and exposes the actual transport fields in a two-column arrangement:
  - Task Type (required, `videoInference`)
  - Task UUID (required, UUID value)
  - Number of Results (stepper, value 1)
  - Output Format (selector, MP4, clear and chevron controls)
  - Webhook URL (full width) with placeholder `e.g. 'https://your-server.com/webhook'`
- Generate/Reset remain on the fixed shelf.
- The right gallery remains scrolled to the portrait/sewer and knife/automaton examples. No inline response block is visible.

## Screenshot 5 — 2.16.11 pm (MiniMax, upper form + upper examples)

**Left pane**

- The model selector changes to a pink/orange waveform thumbnail and `MiniMax / MiniMax H3`; the split and form architecture do not change.
- Capability tags are Text to Video, Image to Video, Video to Video, Audio to Video, and Edit.
- `Inputs` is expanded with Frame Images, Reference Audios, Reference Images, and Reference Videos; add controls wrap onto a second line.
- `Core` is expanded and focus-outlined lime. Prompt is required and uses the same large textarea and assist sparkle.
- Only Width/Height labels are visible before the sticky action shelf.

**Right pane**

- Examples is selected with count 4; the full History/Pricing/Integrate/Schema/Docs toolbar and layout controls are visible.
- Four media-led cards appear in two columns: underwater wreck, robotics team, amber specimen, and pottery studio.
- Their footers preserve the same model name / `minimax:h3@0` / cost / clamped prompt order.

## Screenshot 6 — 2.16.16 pm (MiniMax, lower form)

- Only the left form scroll position changes.
- Below the textarea tail is Width × Height + Custom, then a Duration stepper set to 5 and an empty Seed stepper; API is collapsed.
- The right example grid, local toolbar, and sticky action shelf remain in place.
- This pair most clearly proves the product's nested-scrolling model and the examples-first stability of the right pane.

## Field, control, and spacing inventory

- **Types**: large multiline prompt; numeric width/height with suffix; select/dropdowns for aspect, duration, FPS, output format, task type; steppers for duration/seed/results; URL input; media attachment buttons; collapsed advanced accordions.
- **Labels**: sentence/title case except the uppercase `REQUEST` section header; required fields use a small orange-red asterisk; circled info icons sit immediately after labels.
- **Placeholders/examples**: most empty Core controls show no readable placeholder in the captures. The Webhook URL is the one clear example placeholder. Guidance primarily comes from the example gallery rather than placeholder prose.
- **Buttons**: the primary Generate action is wide, lime, high contrast, and keyboard-aware. Reset is equally wide but outline-only. Use example is a dark floating pill over preview media.
- **Tabs**: Form/JSON is a two-option segmented control. The right toolbar is a flat horizontal navigation strip with only the active Examples item receiving a filled rounded background.
- **Status/progress**: none appears in the six screenshots. Runware's screenshots show pre-run browsing/form states only; any Omo progress treatment is an intentional extension, not a copied screenshot element.

## Live site and docs: related structural language

Reviewed [runware.ai](https://runware.ai/), [Runware Docs](https://runware.ai/docs), and [Platform introduction](https://runware.ai/docs/platform/introduction) on 12 August 2026.

- The homepage uses modality tabs followed by a code example with language tabs, a `POST /V1` label, monospace request code, Copy, and a compact `RESPONSE · 200 OK` result. This validates request/response as adjacent, inspectable product objects.
- The docs say Runware exposes a single endpoint and a shared request shape across image, video, audio, 3D, and text.
- The introduction's “One shape, every modality” module uses modality tabs above paired `→ REQUEST` and `← RESPONSE` JSON panels.
- Request samples are syntax-highlighted monospace JSON with stable identity fields (`taskType`, `taskUUID`, `model`) followed by task inputs. Responses echo identifying fields, add an output URL/value, and can include cost.
- “Your first request” uses TypeScript/Python/cURL/CLI/JSON language tabs and a Copy action. The “Anatomy of a request” block annotates fields rather than hiding the payload.
- Runware documentation uses a persistent top bar, left navigation rail, readable central article column, thin rules, and restrained card surfaces. It supports the same progressive disclosure as the Playground: human controls first, schema/code close at hand.

The live [GPT Image 1.5 model workbench](https://runware.ai/models/openai-gpt-image-1-5) confirms the screenshots' proportions and interaction model in measurable form:

- At 1,264 px, the principal columns are 421 px / 843 px—exactly one-third / two-thirds—with about 24 px internal gutters.
- The left accordion stack is Inputs / Core / Provider / API / Advanced, followed by full-width Generate and Reset controls.
- The right navigation extends the screenshot language to Examples (4), History, Pricing, Integrate, Schema, Readme, and Docs, plus grid/list/thumbnail display controls.
- The example area is a 2 × 2 grid with 16 px gaps. Cards are about 389 × 321 px: a roughly 387 × 218 px 16:9 preview, overlay actions including Use example, then a compact metadata body with model identifier, cost / runs per dollar, and a two-line prompt excerpt.
- Opening an example's details produces a large 90vw × 90vh modal. A large output and four-thumbnail rail occupy the left; a scrollable prompt/price/status/action column occupies the right. Request/Response tabs expose monospace JSON inside the same object, rather than navigating away.
- Selecting Form → JSON on the request side exposes a read-only, syntax-colored live payload.
- At 375 px the workbench becomes one column: input editor first, examples second. Cards reduce to one 351 px-wide column with 12 px page gutters and no horizontal overflow.
- The [GPT Image 1.5 docs examples](https://runware.ai/docs/models/openai-gpt-image-1-5/examples) repeat the same information order at documentation scale: named scenario, full preview, full prompt, language tabs, and Response JSON including task UUID, output URL, and cost.

## Translation to Omo run-design-2

Preserve the structure, not the dark skin:

1. Give inputs the narrower left rail and examples the wider right workspace.
2. Keep examples visible before a run and make each example actionable so it can fill the form.
3. Use a two-column card grid on desktop with compact visual preview, realistic input, and a small “what it made” result—not generic prompt tips.
4. Put the primary **Run it — ≈ $0.10** action at the bottom of the form.
5. Follow the examples with an explicit live request JSON, progress phases, response JSON, and friendly rendered result. This joins Runware's Playground hierarchy to the request/response language confirmed on its public site and docs.
6. Re-skin in Omo's light warm canvas, pine/mint/orange palette, DM Sans, white cards, thin rules, and subtle signature-cut corners.
7. At 375 px, remove sticky desktop behavior and stack in task order: Inputs → Examples → Request/Response/output.
