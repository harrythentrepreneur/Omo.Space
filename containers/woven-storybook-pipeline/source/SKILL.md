---
name: woven-storybook-pipeline
description: WhatsApp chats to keepsake storybooks via Woven backend.
---

# Woven Storybook Pipeline

Turn WhatsApp chat exports into a beautiful, symbolic, TRUE relationship storybook. Built for the Woven product (keepsake books from real chats), backend in `/Users/yifan/woven/backend`.

## When to use

- User provides WhatsApp chat exports (txt/zip) and wants a storybook/keepsake book.
- User wants to regenerate a book on the fixed pipeline (P0+P1).
- User asks about costs, timing, or book quality gates.

## Core principles (non-negotiable)

- **Real names, real quotes, real evidence.** Never fabricate dialogue or quotes; quote pages use verbatim source messages. `pseudonymizeNames: false`.
- **Derive, never impose.** Symbols (max 2 primary + 1-3 secondary per volume) must come from actual chat evidence (e.g. 🥰, good-morning bookends, "potato", padel) — never imposed themes.
- **Story length = what the story is.** No page quotas. Natural mode: 8-16 chapters, 80-160 content beats (validator-enforced floor).
- **Privacy = medical-record care.** Real chats: private workspaces only (`/tmp/...`, mode 700), never in repo, never committed, delete raw `_chat.txt` when done, never print raw messages or keys.

## The pipeline (all in `/Users/yifan/woven/backend/src/`)

1. **Parse** (`chat.ts`): dual-format (old dash `01/06/24,` + iOS bracket `[11/4/2026, 06:47:05] Name: msg`), archive-wide locale inference (d/m/y vs m/d/y), hard gate: <99.5% parser acceptance → reject run. Timestamp-looking failures quarantined, never folded into message bodies.
2. **Month-balanced selection**: every month gets a quota floor, disjoint temporal buckets, coverage gate fails loudly if a month is missing. Direct-ID coverage is the selection gate's job.
3. **Essence** (`narrative.ts`, analysis calls): adversarial essence — core message + 2 primary + 1-3 secondary symbols, each derived from recurrence stats and disconfirming samples.
4. **Plan**: 8-16 chapters / 80-160 beats, each beat = scene/quote/milestone/punch role with evidence IDs. Deterministic rebalance (rebalancePlanRoles) fixes ratios, per-chapter minimums (milestone-or-punch + quote), same-type runs >3. Temporal gap-filler injects real IDs from uncovered months; archive-boundary injection puts first/last messages in first/last chapters.
5. **Continuity contracts** (`story-system.ts`): immutable per-chapter contracts (arc position, prior last beat, symbol state introduce→echo→transform→payoff, next opening requirements); chaining validator throws on gaps/contradictions.
6. **Chapters** (parallel, concurrency 5-6): writer honors role length contracts — scenes 5-8 sentences (truncate to 8), punch 1-3 (truncate to 3), milestone note 2-6 (keep ALL sentences; split before ledger pass), quote pages = verbatim message.
7. **Sparse book-level editorial** (2 passes, whole book): independent audit with honest semanticIssueCount; per-page issues preserved, never auto-reset to 0.
8. **Final gates** (all must PASS or run fails loudly): provenance (deterministic ledger 1:1 + IDs exist + quote bytes match), distribution (runs ≤3, per-chapter minimums, sentence bands scene 3-8/milestone 1-6/punch 1-3), continuity chain, month coverage, boundaries. Ratio bands are planning targets → ratioWarnings, NOT ship-blockers.
9. **Render** (`render.ts`) → HTML; PDF via headless Chrome `--print-to-pdf` + Ghostscript.

## Commands

```bash
cd /Users/yifan/woven
npx tsc --noEmit          # must be exit 0
npm run backend:test      # 43/43 must pass
node backend/src/server.ts   # on 127.0.0.1:4317
```

Kill stale server first: `kill $(lsof -i :4317 -P | grep LISTEN | awk '{print $2}' | head -1)`

API: `POST /analyze {demo:true}` (or file upload) → recap (aggregate only — counts, aliased participants, date range, month distribution, parser/selection diagnostics). `POST /generate {mode:'natural', async:true}` → jobId → poll `/job/:id` → `/book/:id` HTML.

Fixture (safe to run): `/Users/yifan/woven/backend/fixtures/demo-chat.txt` — fictional, ~300 msgs, 15 months.

## Verification ritual (after ANY change)

```bash
cd /Users/yifan/woven && npm run typecheck && npm run test && npm run backend:test && npm run build && hermes verify --json
```

Then a live fixture run: analyze → generate natural → poll → check manifest: provenance PASS, distribution PASS, editorial PASS, continuity PASS, semanticIssueCount honest (>0 is fine), page types all four non-zero, cost ~$0.03-0.08, ~210-380s.

## LLM call mechanics (deepseek.ts)

- **Model**: DeepSeek V4 Flash via the opencode endpoint (OpenAI-compatible). Config lives in `backend/src/deepseek.ts`; credentials (`DEEPSEEK_API_KEY`) load from `/Users/yifan/woven/.env.local` (mode 600, never print).
- **chatCompletion(system, user, {label, maxTokens, temperature, validate})** — every LLM call goes through this one function. Returns `{content, usage}`.
- **maxTokens per call** (proven config): analysis base 6000; adversarial essence 7200; planner 16000; chapter writing `min(16000, max(8000, beats×900))`; book editorial 12000 (bumped to 16000 on schema retry). Hard cap 16k tokens per call.
- **Retry/escalation**: attempts escalate 2^attempt. Schema-invalid JSON or validator failure → retry with a REPAIR hint that embeds the SPECIFIC validation error ("Previous attempt failed this check: <exact message>. Fix exactly that") — without the specific hint the model repeats the same mistake all 3 attempts.
- **JSON contract**: every call returns strict JSON via `parseModelJson`; `jsonShapeValidator` enforces the shape. Model output must include claimLedger rows (SPARSE — only INTERPRETATION/SYMBOL/ambiguous sentences; DIRECT/SAFE_COMPRESSION rows are derived deterministically after writing, never duplicated in model output).
- **Concurrency**: `mapWithConcurrency` writes chapters in parallel (configured 5-6, provider-aware). Editorial runs as ONE book-level sparse audit (2 passes), not per-chapter loops.
- **Telemetry**: every call logs `[woven:deepseek]` JSON — label, attempt, durationMs, promptChars, maxTokens, outcome (success/schema_retry/failed), httpStatus, promptTokens, completionTokens. Per-label timing: analysis ~20-35s, plan ~30-35s, chapter write ~25-40s, book editorial ~30-90s (2 passes). Critical path ≈ 210-380s for an 80-page book.
- **Per-call cost tracking**: `mergeUsage(...usages)` aggregates prompt/completion tokens into the manifest; `estimatedUsd` computed from token counts. Real chat (24k msgs) ≈ 13-29 calls / $0.03-0.08 per book.
- **Model choice**: generation = DeepSeek V4 flash (opencode endpoint, key in .env.local). Delegated agent missions (analysis, design) = ChatGPT SOL @ xhigh reasoning effort — these are HERMES delegation calls, not backend calls.

## Costs (DeepSeek v4 flash via opencode endpoint)

- Fixture book: ~$0.033-0.05, 13 calls, ~210-380s.
- Real chat (24k msgs): ~$0.07-0.08/book.
- Images (P2, Runware): FLUX.2 klein 9B $0.00078/img, 4B $0.00060/img; ~20 images ≈ $0.012-0.016 → total book ≈ $0.09.
- Never run real chats through the server except in the private /tmp workspace; fixture only for dev runs.

## Pitfalls (hard-won)

- **Ledger 1:1 is sacred**: every visible sentence needs one ledger entry (provenance gate). If you truncate body/note, truncate the ledger the same way. Milestone notes: split into sentences BEFORE normalizeLedger, keep all sentences, ledger per sentence.
- **Punch pages**: writer+editorial both only handled `scene` for body — punch pages shipped EMPTY. Any new page type needs the body path in BOTH writeChapter and applyEditorialRevision.
- **Don't trust model retries**: the plan validator must only throw on what code can't repair (invalid roles, quote missing quoteMessageId). Everything else → deterministic rebalance, else retries burn and the whole run dies.
- **Repair hints**: schema-retry in deepseek.ts must include the SPECIFIC validation error, else the model repeats the same mistake 3×.
- **Temporal gates**: gap-filler injects into the chapter ending BEFORE the gap (extends end forward, keeps monotonic); boundary injection (first/last messages into first/last chapters) is required even when a middle chapter touches those months.
- **Ratio bands are targets**: deterministic fixes legitimately shift the mix; failing ratios go to ratioWarnings, only structure fails the gate.
- **Sentence count ≠ array length**: model embeds multiple sentences per array item; truncate by splitSentences count.
- **Server restarts**: after any edit, kill + restart before a fixture run; stale server logs look identical to live failures.

## Real chat data & identity handling

- Real chats NEVER live in the repo. Workspaces: `/tmp/woven-old-chats/` (origin archive, 29,445 msgs, Jun 2025–Jun 2026), `/tmp/woven-product-run/` (main chat, 24,414 msgs, Apr–Aug 2026), both mode 700, `_chat.txt` mode 600. Delete raw `_chat.txt` when a phase is done.
- **Participant normalization**: contact suffixes + hidden Unicode markers must be stripped — "Adila 🤍 (old Number 2)" → "Adila" (U+200E left-to-right marks leak into names and broke symbolism once). `pseudonymizeNames: false` — real names (Harry, Adila 🤍) go in the books.
- **Title**: explicit override ("Harry & Adila: Our Story") defeats the model's title-truncation bug; validatedBookTitle enforces length/completeness.
- Chat stats for context: main chat Harry 13,853 / Adila 🤍 9,261 msgs, 🥰 4,855 uses; old chat Harry 15,493 / "Adila 🤍 (old Number 2)" 13,952.

## API surface & privacy contract (P0, server.ts)

- `POST /analyze` → recap ONLY: analysisId (opaque UUID, not guessable), counts, aliased participants, date range, month distribution, parserDiagnostics, selectionDiagnostics. NEVER returns message text or selected messages.
- `POST /generate {mode, async}` → jobId; poll `GET /job/:id`; `GET /book/:id` → HTML. Demo mode (`demo:true`) blocked when `nodeEnv === 'production'`.
- Privacy: TTL cleanup for analyses/jobs/books, `DELETE /analysis/:id` + `DELETE /book/:id`, restricted CORS (allowedOrigins option — never wildcard).
- App reads counts/participants for the recap screen — keep those fields if the shape changes.

## Book delivery workflow (founder loop)

1. Generate book → render HTML → PDF via headless Chrome `--print-to-pdf` + Ghostscript (sizes: ~80pp ≈ 2.5MB, 400pp ≈ 5.3MB).
2. Deliver PDF to `/Users/yifan/Downloads/Woven-Story-<name>.pdf`, open in Preview.
3. Founder reads it page-by-page and gives feedback — that feedback drives the next revision. Never skip this loop; the founder's taste is the final gate.
4. Images come ONLY after the founder approves a book (P2).

## Image phase (P2 — DEFERRED, do NOT build yet)

- **Founder decision: images are NOT needed for P2 right now. Do not implement, do not spend Runware credits, do not generate images for books.** Revisit only when the founder explicitly asks for the image phase.
- When/if it resumes: key `RUNWARE_API_KEY` in `/Users/yifan/woven/.env.local` (mode 600); FLUX.2 klein 9B $0.00078/img or 4B $0.00060/img (FLUX.1 klein 8B NOT in catalog); compute-based billing, `includeCost` flag for exact cost.
- ONE versioned "congruent cute style" master prefix for ALL images in a book: `WOVEN_CUTE_STYLE_V1` — consistency is the whole aesthetic.
- ~15-25 images per ~80-page book (not one per page): only where the storyteller finds a good fit. ~20 images ≈ $0.012-0.016 → total book ≈ $0.09.
- render.ts currently has NO shared style prefix (76 illustration proposals vs ~20 wanted) — the eventual image phase must add it.
- Images come ONLY after the founder approves a book.

## Two-volume run procedure (P1)

Volume I "The Beginning" (old chat archive) + Volume II "The Bridge" (main chat archive). Each volume: own analyze → own essence (derived from ITS archive only) → own symbol system (max 2 primary + 1-3 secondary) → own continuity contracts → own book. The combined product gets a unifying prologue/bridge frame. Run volumes sequentially; never reuse Volume I's essence for Volume II.

## Two-volume architecture (P1 scope)

Volume I "The Beginning" (old chat) + Volume II "The Bridge" (main chat) — each with its OWN essence/symbol system derived from its own archive. Continuity contracts chain chapters within a volume; volumes get a unifying frame.
