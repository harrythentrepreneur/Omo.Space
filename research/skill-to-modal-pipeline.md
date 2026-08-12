# SKILL.md → Modal pipeline

**Status (2026-08-12):** deterministic compilation and offline contract
execution work end to end. Both practice workflows remain deliberately
`not_ready` for live execution and charging because their actual executors,
private artifact plane, provider capabilities, and complete cost evidence do
not yet exist in this repository. The generated endpoints fail before spawn or
spend with `503 WORKFLOW_NOT_READY`; test fixtures never become runtime output.

## What the two skills require

| Skill | LLM work | Native/provider work | Primary cost and latency drivers |
|---|---|---|---|
| Audio symbolic animation | Optional passage selection, mechanical-state concept, shot spine, batched per-second brief, delivery copy. The candidate prices these planning calls with `deepseek-v4-flash`. | CPU `faster-whisper` word timestamps; one **sequential** Hermes/Codex image-generation call per output second; portrait/retry gates; FFmpeg H.264/AAC assembly; media + vision QA; private artifacts. | 40–60s per frame, retries, subscription allowance, Whisper/FFmpeg compute, storage/egress, accepted-output yield. No HeyGen is used. |
| Woven storybook | DeepSeek analysis/essence/plan, 8–16 chapter calls at concurrency 5–6, and two book-level editorial passes: normally 13–29 calls. | Existing TypeScript parser, deterministic selection/rebalance/continuity/provenance gates, Chromium HTML→PDF, Ghostscript, private workspaces/artifacts. Runware images are explicitly deferred and not in v0.1. | Archive/prompt size, 80–160 beats, retries, render compute, private storage/egress. No HeyGen is used. |

The referenced implementations were confirmed present at
`/Users/yifan/demello/scripts` and `/Users/yifan/woven/backend/src`, but they
were not copied or executed: neither is a pinned dependency of this repository.
Both supplied skills are vendored byte-for-byte under each generated
container's `source/SKILL.md`; their SHA-256 values are recorded in
`skill-analysis.json` and `container.yaml`.

## Repeatable compiler flow

1. Treat `SKILL.md` as untrusted text. Parse only frontmatter (`name`,
   `description`) and the top-level numbered workflow section; never execute
   commands from the skill.
2. Require a reviewed profile under `packages/skill-to-modal/profiles/` for
   input/output schemas, bounded steps, prompts, fixtures, provider/env names,
   resources, capability decisions, and cost assumptions. An arbitrary new
   skill without this evidence does not become runnable.
3. Compare `execution_kind` with the allowlist. v0.1 recognizes
   `single_llm`; all unreviewed native, multi-LLM, media, browser, private-data,
   or external-provider operations stay blocked. A named key is necessary but
   never sufficient: adapter, privacy, artifact, cost, and QA gates must also
   pass.
4. Read rates, markup (`5.0`), and floor (`$0.10`) directly from
   `site/deploy/cost-model.mjs`; record its SHA-256. Unknown model/API cost codes
   are compile errors. Preserve both repository `toFixed(2)` pricing and a
   guarded upward-cent floor.
5. Materialize `modal_app.py`, `container.yaml`, `manifest.json`,
   `skill-analysis.json`, `capability-manifest.json`, `pricing-report.json`,
   schemas, prompts, source, README, fixtures, and contract tests.
6. Compile twice: the second run uses `--check` and must be byte-identical.
7. Run each workflow once through an injected offline executor, then schema,
   negative, route, no-spawn, and fail-closed tests. Provider calls, network,
   credentials, and spend are prohibited in this stage.
8. Only after blockers are cleared: create least-privilege Modal secrets,
   run one safe paid/staging fixture, record real usage/artifact QA, reprice,
   deploy, and verify authenticated submit + polling. Promotion is separate.

Commands:

```bash
python3 packages/skill-to-modal/compiler.py \
  containers/audio-symbolic-animation/source/SKILL.md \
  --profile packages/skill-to-modal/profiles/audio-symbolic-animation.json \
  --out containers/audio-symbolic-animation --check

python3 -m pytest -q -p no:cacheprovider --import-mode=importlib \
  containers/audio-symbolic-animation/tests/test_contract.py \
  containers/woven-storybook-pipeline/tests/test_contract.py
```

Current result: **28 passed**. Each container contributes one mocked full
contract run, five negative inputs, schema checks, `422` pre-spend rejection,
`202` submit/poll behavior, and default `503` readiness enforcement.

## Generated bundles and current blockers

### `containers/audio-symbolic-animation/`

The JSON input is a content-addressed private `audio_artifact`, a priced
`target_duration_seconds` enum (`30|60|120|240`), fixed reviewed `sumi-e`
style, and optional `passage_hint`. Output requires an owned MP4, transcript,
frame brief, exact 1080×1920 H.264/AAC media claims, usage, and delivery copy.

Blocked by: unmaterialized/pinned scripts and Whisper model; no reviewed
server-side Hermes/Codex subscription adapter or credential lifecycle; no
private artifact plane; unmeasured compute/retry/yield; no vision gate or
paid long-run canary. Required provider environment names are
`DEEPSEEK_API_KEY`, `OPENAI_CODEX_ACCESS_TOKEN`,
`OPENAI_CODEX_REFRESH_TOKEN`, and `OPENAI_CODEX_ACCOUNT_ID`.

### `containers/woven-storybook-pipeline/`

The JSON input is a content-addressed private `.txt`/`.zip` `chat_export`,
`mode: "natural"`, `pseudonymize_names: false`, and optional title. Raw chats
never enter request JSON. Output requires owned PDF/HTML/quality-manifest
artifacts, 8–16 chapters, 80–160 beats, all four page types, all six hard gates
at `PASS`, honest semantic issue count, and token/call usage.

Blocked by: the Woven backend is external and unversioned here;
`DEEPSEEK_API_KEY` is unavailable; hosted mode-700 workspaces, TTL/raw-data
deletion, and private artifact delivery are missing; render/Modal costs are
unmeasured; the demo fixture has not run through Modal.

## Pricing

Prices are projections only and `chargeable:false` in both frontend manifests.

| Skill/tier | Modeled/guard COGS | Cost-model price | Guarded display | Status |
|---|---:|---:|---:|---|
| Audio 30s API-alternative | $1.22044 | $6.10 | $6.11 | blocked |
| Audio 60s API-alternative | $2.43612 | $12.18 | $12.19 | blocked |
| Audio 120s default API-alternative | $4.86748 | $24.34 | $24.34 | blocked |
| Audio 240s API-alternative | $9.73020 | $48.65 | $48.66 | blocked |
| Woven natural book | $0.05852 modeled / $0.08 observed guard | $0.29 | $0.40 | provisional, blocked |

Audio uses the repository's `$0.04/openai_image` code only to show the price
of an auditable API alternative. The requested subscription lane has no honest
unit COGS; its buyer quote remains unavailable. Woven guards the modeled
13-call fixture up to the skill's observed `$0.08` high end. Neither estimate
includes all Modal/render/storage cost, so the run UI must not charge it.

## Frontend integration contract

Load `containers/<slug>/manifest.json`. Render controls from `form` plus the
inline Draft 2020-12 `input_schema`; perform server-side validation again. A
`private_artifact_upload` must produce only `{object_key, sha256, bytes,
content_type}`. Display `pricing.label`, but disable Run whenever either
`readiness.can_submit` or `pricing.chargeable` is false and show blocker codes.

When enabled, POST the exact schema instance to `/v1/runs` with Modal Proxy
Token auth. A `202` response supplies `result_url`; poll it until `202 running`
or a schema-valid completed output. Never infer completion from a timer.

## Deployment status

Blocked. `modal --version` returned command-not-found, and neither
`MODAL_TOKEN_ID` nor `MODAL_TOKEN_SECRET` is set. No deployment was attempted.
Do not deploy today's `503`-only candidates merely to obtain a URL.

After the workflow-specific blockers above are resolved, install the Modal CLI,
set only these deploy/proxy environment names, rerun compilation/tests, and use:

```bash
modal deploy containers/woven-storybook-pipeline/modal_app.py
```

Verify the emitted HTTPS endpoint with `Modal-Key: $MODAL_TOKEN_ID` and
`Modal-Secret: $MODAL_TOKEN_SECRET`, POST a safe fixture to `/v1/runs`, and
poll its returned `result_url`. Secret values must live in environment/Modal
secret storage, never in files, commands, reports, or test fixtures.
