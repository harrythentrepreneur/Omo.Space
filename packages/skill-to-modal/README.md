# Skill to Modal compiler

This package is the small, deterministic compiler used to turn a reviewed
`SKILL.md` into a Modal candidate bundle. It treats the skill as untrusted
source material: Markdown is parsed and never executed. Existing checked-in
profiles continue to supply reviewed contracts. New supported creator uploads
first produce only a `pure_data` or `single_llm` workflow IR validated by the
machine schemas in `workflow-ir/`; `workflow_ir.py` deterministically compiles
that IR into the full trusted profile. The IR cannot select identity, source
hash, provider, credentials, runtime, resources, readiness, pricing, deployment
or release policy.

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/audio-symbolic-animation/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/audio-symbolic-animation.json \
  --out containers/audio-symbolic-animation
```

Add `--check` in CI to prove the generated bundle is current. Unknown or
unreviewed external capabilities are compile blockers and produce a
fail-closed `POST /v1/runs` endpoint; they are never silently mocked in the
deployed runtime. Offline tests may inject a mock executor to exercise the
complete request/result contract without keys, network access, or spend.

The automatic authoring allowlist admits two deterministic families:
`pure_data` uses only the reviewed bounded standard-library operation registry;
`single_llm` uses the compiler-pinned OpenAI-compatible adapter and model policy.
Both families receive compiler-owned runtime, resource, readiness, pricing and
release fields. Existing reviewed profiles—including complex fail-closed
profiles—remain compatible. Every other new capability is represented as a
typed unsupported blocker rather than a partially runnable profile.

## Reusable generator capabilities

The compiler owns a versioned capability registry and resolves only typed
signals from reviewed inputs, outputs, artifact declarations, and steps. It
emits the minimal selected set, registry/contract digests, generated pieces,
dependencies, tests, limits, and typed blockers in
`capability-manifest.json` (`cognition.capabilities/v2`). Current entries are:

- `input_adapters: ["whatsapp_zip"]` plus
  `input_adapter_config.whatsapp_zip` adds an exact-one-source input contract.
  The generated runtime accepts a base64 WhatsApp export ZIP, requires one
  `_chat.txt`, rejects unsafe/encrypted/oversized archives with typed errors,
  aliases participants, strips metadata, bounds the transcript, and makes one
  strict schema-validated extraction pass before the workflow. Relationship-
  book profiles should use this adapter because chat-export ZIPs are a natural
  source for the direct story fields.
- `artifact: {"type": "book_pdf", ...}` adds deterministic ReportLab book
  composition after the provider step, immutable run-scoped Modal Volume
  persistence, a checksum/page-count descriptor, and a short-lived signed PDF
  download route. Markdown and other reviewed outputs remain in the envelope.
- A PNG artifact with kind `chart`, `plot`, or `metrics_viz`, an output with
  the matching `artifact_type`, or a
  `visualization.render.chart` step selects deterministic chart generation
  through `tools/render/charts.py`. The generated runtime validates the bounded
  chart spec, verifies PNG bytes and dimensions, and persists a signed artifact.

Capabilities are materialized only when declared by a reviewed profile;
profiles without matching typed signals receive neither upload parsing nor
rendering. Unknown artifact or adapter needs emit `CAPABILITY_UNAVAILABLE` and
force submission and charging off; incomplete bindings fail closed as
`CONTRACT_INCOMPLETE`.
