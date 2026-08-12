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
