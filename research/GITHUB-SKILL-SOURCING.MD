# GITHUB-SKILL-SOURCING — discovery & verification playbook for Omo

**Status:** live as of 2026-08-16. First real scout run completed against the
GitHub API (all numbers below are from actual API responses, saved in
`/tmp/github-skill-scout/results.json`). The scout script is
`scripts/github-skill-scout.py` (read-only, uses `gh`'s existing auth; no
secrets, no writes, no pushes).

## 0. Operating rules (founder-mandated: reject-by-default)

- **Reject-by-default.** A candidate must PASS every gate, not most. Any hard
  gate failure ends it, with the reason recorded.
- **Stars are a first filter only.** A star count is never a recommendation.
  This run proves why: the pool is full of star-farmed and SEO-gamed repos.
- **Rejections are the normal, correct outcome.** Recording *why* is part of
  the deliverable. A small funnel (3–5 excellent skills) is success.
- **The mandatory vetting sequence** (stage 2 below) runs in fixed order:
  clear license → byte-identical to upstream → zero credential patterns →
  bounded runtime scope → **then** the machine's real-run proof. Nothing is
  hosted or listed without passing all of it.

---

## 1. Discovery sources (ranked, exact search strings)

The scout queries all of these via the GitHub search API (`gh api
search/repositories` + one `search/code` call).

| # | Source | Exact query / mechanism | Yields | Caveats |
|---|--------|------------------------|--------|---------|
| 1 | Canonical org repos | `org:anthropics skills` | anthropics/skills (169.6k★, the canonical skill repo), claude-plugins-official, k12-teacher-skills, launch-your-agent | **anthropics/skills has NO license** → rejected by our license gate for hosting (see §4). Canonical ≠ hostable. |
| 2 | GitHub topics | `topic:claude-skills`, `topic:ai-skills`, `topic:agent-skills` | Self-tagged skill repos; best signal-to-noise of all sources (38 of 70 pooled candidates came from topics) | Topic tags are self-assigned — gaming possible, less common. |
| 3 | Awesome-list family | `awesome claude skills`, `awesome agent skills` (+ `awesome openclaw skills` etc. for follow-ups) | The awesome-claude-skills family (ComposioHQ, VoltAgent…) and adjacent lists | **Most awesome lists fail our gates**: ComposioHQ/awesome-claude-skills (72.6k★) has no license; VoltAgent's lists contain no SKILL.md. Treat as lead *directories*, never as hostable skills. |
| 4 | README/description mentions | `claude skills in:readme`, `agent skills in:readme`, `SKILL.md in:readme` | Broadcast recall (33 of 70 pooled) | **Highest noise + gaming surface** — this is where star-farm repos enter (their READMEs are SEO'd to mention skills). Always flagged and vetted. |
| 5 | Direct file evidence | code search `filename:SKILL.md` | The only source that *proves* a SKILL.md exists | Results sorted by best-match, dominated by tiny repos; in this run its unique contributions all fell below the pool's star cutoff (0 unique top-70 candidates). Use as a recall backstop; see §4 limits. |
| 6 | Starred-"SKILL.md" repos (manual) | Browse the stargazers of known-good repos (anthropics/skills, obra/superpowers, pm-skills) → their own skill repos | Human-curated discovery of small gems | Not automatable cheaply via API; a curation-community activity. |
| 7 | Curation communities | r/ClaudeAI skill threads, skills directories (skillsmp, skiller, glama, devv.ai, agent-skills marketplaces), Discord | Lead generators only | Never proof. Verify everything yourself through the pipeline. |
| 8 | Canonical force-include | `anthropics/skills` always evaluated | Guarantees the canonical repo is scored every run | Its rejection (no license) is itself a useful signal each run. |

---

## 2. Verification score model

The score **ranks** candidates inside tiers; the **gates** decide admission.
A score never overrides a gate.

### Weights (100 pts total)

| Signal | Pts | Bands |
|--------|-----|-------|
| Popularity | 25 | stars: ≥2000→15, ≥500→12, ≥100→9, ≥20→6, ≥1→3 · forks: ≥200→10, ≥50→7, ≥10→4, ≥1→2 |
| Recency / maintenance | 20 | pushed <30d→20, <90d→16, <180d→12, <365d→8, <730d→4, else 0 |
| License clarity | 15 | MIT/Apache-2.0→15 (hostable) · other OSI (BSD/GPL/MPL/CC0/Unlicense…)→10 · custom→4 · none→0 |
| SKILL.md structure | 20 | ≥1 SKILL.md in tree→10 base · frontmatter name+description→+6 (partial +3) · ≥3 skill files (a collection)→+4 · cap 20 |
| Tests | 10 | test files in tree→10 · CI only→5 · none→0 |
| Author provenance | 10 | org-owned→10 · user: ≥500 followers→8, ≥100→6, ≥20→4, else 2 |
| Secret risk | **−15 penalty** | credential-pattern filenames in tree (vendor/ and `.env.example`-style templates excluded) |

### Hard gates (pass/fail — any failure ⇒ REJECT, reason recorded)

1. **License** — MIT/Apache-2.0 (hostable) or other-OSI (vet redistribution
   terms first). None/custom ⇒ reject: *cannot verify redistribution rights.*
2. **Structure** — ≥1 SKILL.md in the fetched tree. None ⇒ nothing to host.
3. **Secret filenames** — no credential-pattern filenames (`.env`, `*.pem`,
   `id_rsa`, `credentials.json`, `service-account*.json`, `tokens.json`…;
   dependency dirs and `.env.example` templates excluded).
4. **Tree integrity** — full recursive tree fetched and not truncated (a
   truncated/unfetchable tree ⇒ cannot verify contents ⇒ reject).

### Soft flags (force VET, do not auto-reject)

- **Relevance** — skills-focused / adjacent / unclear, from description +
  README. Non-skills repos (libraries, platforms, prompt packs) are flagged so
  the vet must confirm or reject.
- **Awesome-list / directory** — repo name or README signals a curated list,
  not hostable skills.
- **Star quality** (anti-farm heuristics, all metadata-derived):
  - high-star-velocity: ≥30k★ and <150★/day average on a <2-yr-old repo;
  - stars-without-license: ≥10k★ with no license;
  - stars-without-forks: ≥5k★ with 0 forks;
  - stars-exceed-author-reach: user-owned, ≥10k★, <2k followers, ≥25× follower
    count (a small author with a huge star count = boost suspect);
  - stars-without-author-reach: ≥10k★ with a 0-follower author.

### Tiers

- **BUILDER_TEST** — all hard gates pass **and** score ≥ 65 **and** no soft
  flags. Meaning: *this is worth the vet sequence, then the builder proof.* It
  is NOT a hosting recommendation.
- **VET** — hard gates pass but score 50–64 or any soft flag. Vet review
  first; most star-farm suspects land here.
- **REJECT** — any hard-gate failure, or score < 50 despite passing gates.
  Reason recorded; no further work.

### What the score cannot tell (honest limits)

- Frontmatter **contract quality** (inputs/outputs/schema completeness) —
  only the builder validates this.
- **Semantic sanity** of real outputs — unknown until a real provider run.
- **Real runtime behavior and cost** — unknown until compiled + run + priced.
- **Secret *content*** — the scout scans filenames only; file bodies and git
  history need a content scan (gitleaks or equivalent) at vet.
- **Byte-identity to upstream** — whether a repo is a fork/derivative farm or
  ships hidden payloads requires clone + hash + diff at vet.
- **Star authenticity** — flags are heuristics. A flag forces human review; it
  does not itself prove fraud (legit viral repos like obra/superpowers,
  mattpocock/skills also trip velocity flags — by design, they get a cheap
  provenance check).

---

## 3. Pipeline: scout → vet → BUILDER PROOF → host + list

```
SCOUT (automated) ──▶ VET (mandatory sequence) ──▶ BUILDER PROOF (machine) ──▶ HOST + LIST
  discovery              1. clear license              tools/host-skill/host.py     only if proof passed
  score + gates          2. byte-identical upstream      <SKILL.md> --register:
  flags + reasons        3. zero credential patterns      compile → contract tests
                         4. bounded runtime scope        → real run → schema-valid
                                                         → semantic sanity → priced
```

1. **Scout** — `scripts/github-skill-scout.py` (this deliverable). Queries,
   scores, gates, flags, records reasons → `results.json` (top 25) +
   `all_scored` (full pool). Funnel: ~200 raw hits → 70 pool → 25 output → 7
   BUILDER_TEST in run #1.
2. **Vet** — human/agent review in the founder-mandated order. **1. License:**
   verify the LICENSE *file* matches its SPDX metadata (metadata can lie) and
   check `THIRD_PARTY_NOTICES` for vendored code. **2. Byte-identical to
   upstream:** clone at the pinned commit, hash, diff against the reviewed
   source; a derived/fork repo must be byte-identical and attributed. **3.
   Zero credential patterns:** scan file *contents* and git history for keys,
   tokens, passwords (gitleaks or equivalent) — the scout's filename scan is
   only a first pass. **4. Bounded runtime scope:** inspect the skill's
   runtime claims — no arbitrary exec, no unbounded network egress, no
   filesystem writes outside the sandbox, no secret exfiltration.
3. **Builder proof — the real gate** (machine, not opinion): the one-shot
   builder compiles the SKILL.md (`tools/host-skill/host.py <SKILL.md>
   --register`), runs offline contract tests, then runs **real inputs** on a
   real provider, validates schema-valid output + semantic sanity, and prices
   it against the cost model. Any failure (e.g. `LLM_INVALID_OUTPUT`, schema
   violations — see `research/one-shot-rounds.md` for the repair history) ⇒
   reject with a recorded reason.
4. **Host + list only if the builder proof passed.** Nothing is hosted on
   stars or score. `anthropics/skills` at 169.6k★ is rejected at stage 1 —
   that is the model working, not a bug.

---

## 4. First real run — 2026-08-16 (all figures from live API responses)

Rerun: `python3 scripts/github-skill-scout.py --out /tmp/github-skill-scout/results.json`
(reads `--limit 25`, `--max-pool 70` by default; full data incl. every pooled
candidate under `all_scored`).

**Coverage:** 9 repo-search queries (205 hits) + code search `filename:SKILL.md`
(100 file hits) → dedupe → pool of 70 (capped by stars) → 25 output.

**Funnel:** 70 pooled → **7 BUILDER_TEST · 33 VET · 30 REJECT**. Reject-gate
breakdown: license 16 · structure 21 · secret 2. Rejection rate: 43% outright,
plus the VET tier (star-quality flags) that the vet stage will mostly confirm
as rejections. This is the reject-by-default design working.

### Top 10 (tier order, then score)

| # | Tier | Score | Repo | ★ stars | License | Why (signal summary) |
|---|------|-------|------|---------|---------|----------------------|
| 1 | BUILDER_TEST | 100 | K-Dense-AI/scientific-agent-skills | 33,611 | MIT | org-owned; 162 SKILL.md, fm=full; tests; pushed today; description/README skills-focused; no flags |
| 2 | BUILDER_TEST | 100 | anthropics/claude-plugins-official | 33,555 | Apache-2.0 | org-owned (Anthropic); 31 SKILL.md, fm=full; tests; pushed today; no flags |
| 3 | BUILDER_TEST | 98 | wshobson/agents | 38,843 | MIT | 180 SKILL.md, fm=full; tests; established skills author (2,147 followers); no flags |
| 4 | BUILDER_TEST | 94 | phuryn/pm-skills | 25,292 | MIT | 68 SKILL.md, fm=full; tests; author 1,073 followers; no flags |
| 5 | BUILDER_TEST | 94 | JimLiu/baoyu-skills | 25,031 | MIT | 22 SKILL.md, fm=full; tests; famous author (4,874 followers); no flags |
| 6 | BUILDER_TEST | 92 | alirezarezvani/claude-skills | 24,482 | MIT | 802 SKILL.md (largest haul); tests; first-file frontmatter probe failed → per-skill structural vet needed |
| 7 | BUILDER_TEST | 91 | Orchestra-Research/AI-Research-SKILLs | 11,729 | MIT | org-owned; 98 SKILL.md, fm=full; CI only (no test files); no flags |
| 8 | VET | 100 | NousResearch/hermes-agent | 231,166 | MIT | 198 SKILL.md, fm=full, tests, org-owned — but velocity flag (~594★/day) → provenance check (our own platform, will clear fast) |
| 9 | VET | 100 | nextlevelbuilder/ui-ux-pro-max-skill | 117,096 | MIT | 13 SKILL.md, tests — velocity flag (~454★/day); public star-boost controversy; vet must verify before any use |
| 10 | VET | 100 | browser-use/browser-use | 109,364 | MIT | 7 SKILL.md, tests, org-owned — velocity flag (~167★/day); primarily a browser-agent library, not a skills repo |

### Rejection highlights (each with its recorded reason)

- **anthropics/skills** — 169,588★, **no license** ⇒ REJECT (license gate):
  cannot verify redistribution rights. The most famous skills repo is *not
  hostable* without explicit upstream permission. (Exception path: founder
  obtains written permission from Anthropic, then re-vet.)
- **ComposioHQ/awesome-claude-skills** — 72,571★, **no license** ⇒ REJECT.
  Lesson: the awesome-claude-skills family is frequently unlicensed — treat
  the family as leads, not sources.
- **openclaw/openclaw** (386k★), **code-yeongyu/oh-my-openagent** (68k★),
  **multica-ai/andrej-karpathy-skills** (202k★, karpathy-bait), **caveman**
  (98k★) — all **no license** ⇒ REJECT.
- **public-apis** (460k★), **sindresorhus/awesome** (496k★),
  **Hack-with-Github/Awesome-Hacking**, **practical-tutorials/project-based-learning**
  — **no SKILL.md in tree** ⇒ REJECT (structure): directories, not skills.
- **firecrawl/firecrawl** — structure fail + `.env.local` filename hit ⇒ REJECT.
- Star-farm defense in action (all VET, most will be rejected at vet):
  **DietrichGebert/ponytail** (1,592★/day, 69× author reach), **affaan-m/ECC**
  (1,144★/day), **nexu-io/open-design** (791★/day), **garrytan/gstack**
  (816★/day), **Egonex-AI/Understand-Anything** (516★/day),
  **ayghri/i-have-adhd** (95× reach), **yusufkaraaslan/Skill_Seekers**
  (60× reach), **nidhinjs/prompt-master** (40× reach), **titanwings/colleague-skill**
  (43× reach).

### Honest limits of this run

- **Rate limits:** search API 30/min (authenticated), code search 10/min,
  core 5,000/hr. The script sleeps between calls and retries on 429/403; this
  run used ~350 core calls and ended with quota to spare.
- **Pool bias:** the pool is capped by stars (70/100), so small curated repos
  (and nearly all `filename:SKILL.md` code-search hits, which are tiny repos)
  were excluded. Topic/readme queries did cover the field, but a follow-up
  pass without a star cap would surface small gems.
- **Metadata vs reality:** repo license *metadata* can differ from the
  LICENSE *file*; the scout checks metadata only — vet verifies the file.
- **Score ≠ verdict:** frontmatter contract completeness, semantic quality,
  real runtime behavior, secret *content*, and byte-identity are all unknown
  until vet + builder proof. Every BUILDER_TEST row above is a *candidate*.

---

## 5. Recommended next step

Run the vet sequence + builder proof on the 7 BUILDER_TEST candidates, in
this order:

1. **anthropics/claude-plugins-official** — vendor provenance is the cleanest
   possible start (org-owned, Apache-2.0, tests, active today).
2. **K-Dense-AI/scientific-agent-skills** — org-owned, MIT, 162 skills,
   active today; biggest clean single-source haul.
3. **wshobson/agents** — 180 skills from an established skills author.
4. **JimLiu/baoyu-skills** — famous author, 22 skills, MIT.
5. **phuryn/pm-skills** — 68 product-manager skills, MIT.
6. **Orchestra-Research/AI-Research-SKILLs** — org-owned, 98 skills (CI only;
   add contract tests at build).
7. **alirezarezvani/claude-skills** — 802 skills is the largest extraction
   target, but requires per-skill structural vetting (frontmatter probe failed
   on the first file) — treat as a bulk-extraction job, not a quick win.

Expect a high rejection rate even inside BUILDER_TEST — that is the design.
Only skills that survive license → byte-identity → credential scan → bounded
scope → compile → real-run → schema-valid → semantic-sane → priced get hosted
and listed. If that yields 3–5 excellent skills, the scout did its job.

Follow-ups worth scheduling: (a) widen the pool (drop the star cap, paginate
topics) to catch small curated repos; (b) add a content-level secret scan
(gitleaks) to the vet stage; (c) pursue the explicit-permission path for
anthropics/skills if the founder wants canonical Anthropic skills hosted.
