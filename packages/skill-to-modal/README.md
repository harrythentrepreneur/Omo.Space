# Skill to Modal compiler

This package is the small, deterministic compiler used to turn a reviewed
`SKILL.md` into a Modal candidate bundle. It treats the skill as untrusted
source material: Markdown is parsed, never executed, and a checked-in profile
must supply the schemas, bounded steps, capability decisions, test fixtures,
and pricing evidence.

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

The current allowlist admits only `single_llm` candidates with a reviewed
OpenAI-compatible operation. The two practice skills are intentionally marked
`complex_external` and `not_ready`.

## Reusable generator capabilities

Reviewed profiles may opt into two bounded, default-off capabilities:

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

Capabilities are materialized only when declared by a reviewed profile;
profiles without these fields receive neither upload parsing nor rendering.
