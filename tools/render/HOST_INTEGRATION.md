# host.py integration note

The renderer materializes the shared PDF/editable-artifact capability, but it
does not by itself make any profile ready. `host.py` currently delegates to the
compiler, and the compiler permits `can_submit: true` only for its allowlisted
`single_llm` execution kind. These three profiles are `complex_external` and
must remain fail-closed until each non-renderer gate below has evidence and a
reviewed execution kind/runtime.

## Recommended reviewed runtime boundary

Add a reviewed `education_artifact` execution kind to the compiler only after a
container runtime exists. That runtime should:

1. Validate the existing public input schema from the profile.
2. Create or resolve a reviewed `omo.education-artifact-manifest/v1` manifest.
3. Call `tools.render.runtime.render_manifest(manifest, request_dir,
   store=owner_store, run_id=run_id)`.
4. Map `RenderResult.artifacts` into the profile output schema, adding workflow
   content/QA/usage fields from the earlier steps.
5. Reopen every PDF, run the workflow-specific acceptance fixtures, write via
   the production private artifact plane, and only then return `completed`.

`host.py` should not contain compositor logic. It should keep compiling and
testing, and additionally run `tools/render/tests` plus a generated container
integration test when `profile.execution_kind == "education_artifact"`.

## Slug mapping

### `phonics-worksheet-generator`

- Public input is the profile schema: grade, focus type/patterns, activity,
  requested page count, difficulty, dialect, print mode, theme, answer-key
  flag, and teacher notes.
- A reviewed content-manifest step maps that input to renderer pages/items.
  Each item has a stable ID, prompt, and answer. `include_answer_key` passes
  through unchanged.
- The compositor returns `worksheet` and optional `answer_key` PDF descriptors.
- Still required before readiness: instructional content generation, approved
  assets/fonts policy, educator correctness/decodability fixtures, production
  private artifact storage, pricing, and container integration.

### `illustrated-decodable-story-maker`

- Public input is phonemes, story idea, difficulty, language variant,
  curriculum, 7-21 pages, highlighting flags, printable flag, and art style.
- Reviewed story generation maps it to title plus renderer story pages. Each
  page carries final text and an optional local authorized `image_path`.
- For missing images, the container may call `populate_missing_story_images`
  with a host-created `CodexSubscriptionImageAdapter`; absent credentials or a
  failed/withheld image tier must remain a disclosed text-only result, not a
  claimed illustrated/educator-approved success.
- The compositor returns PDF, editable JSON, and JPEG thumbnail descriptors.
- Still required before readiness: story generation, child-safety and image
  continuity/text checks, decodability/curriculum/educator acceptance,
  production private storage, complete measured cost/pricing, and container
  integration. Text-only fallback does not satisfy the advertised illustrated
  acceptance gate.

### `phonics-story-edit-studio`

- Public input is the existing owned JSON descriptor, bounded operations, and
  safe output filename.
- The host authenticates the owner, resolves the descriptor with the production
  artifact plane, verifies bytes/SHA/MIME/schema, and builds an
  `ArtifactStore`-equivalent request scope. `ArtifactStore` demonstrates the
  required local semantics but is not production authentication.
- Call `apply_edit_operations`; image regeneration stays rejected unless its
  separately reviewed tier supplies a replacement local image. Render the new
  manifest and write content-addressed new objects without mutating the source.
- The compositor returns revised PDF, editable JSON, and optional/extra
  thumbnail; the profile accepts two to three artifacts.
- Still required before readiness: production owner authorization and private
  storage, source-schema/version rules, operation-level unchanged-page QA,
  optional image-tier review, pricing, and container integration.

## Readiness change procedure

After the missing gates are implemented, update each reviewed profile from
placeholder operations to actual runtime operations, remove only resolved
blockers, add measured pricing, and set `can_submit` only after the compiler
allowlist/runtime and tests are reviewed. Then run `host.py --check`. Do not use
`--register` until the resulting manifest honestly reports `can_submit: true`.
