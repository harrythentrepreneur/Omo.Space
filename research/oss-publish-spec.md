# OSS Publish Gate (R4) — implementation spec

Canonical: this spec. Status: **implemented 2026-08-16 in
`tools/host-skill/process-submissions.py` (7 tests, 113/113 pass); first real
publish pushed (15 free skills, commit 104a2b3 on omo-space/skills)**.

## Goal

After a FREE skill passes the existing R1–R3 release gates, its release also
publishes the skill's contract to the public repo **github.com/omo-space/skills**
under `skills/<slug>/`. Download is free (MIT); the paid product stays the
hosted run on omo.space (pay per run, no subscription). Premium skills never
publish.

## Hook point

`tools/host-skill/process-submissions.py` → `deploy_merged_release()` — after
R3 (`smoke_evidence = smoke_live_worker_registry([slug])`, line ~1449) and
before the `return` (line ~1450). Add:

```python
release_gates = {"R1": ..., "R2": ..., "R3": ..., "status": "live", ...}
if slug not in OSS_PREMIUM_EXCLUSIONS:
    release_gates["R4"] = publish_oss_release(slug)   # raises OssPublishBlocker on failure
```

R4 is SKIP-ONLY for premium slugs (silent, never published); every FREE slug
must pass R4 or the release fails closed with a typed blocker.

## New constants

```python
OSS_REPO_URL = "https://github.com/omo-space/skills"
OSS_REPO_LOCAL = ROOT / ".." / "oss-publish" / "skills"     # local checkout (or /tmp clone)
OSS_SKILL_REL = "skills/{slug}"
OSS_POLICY_URL = "https://github.com/omo-space/skills/blob/main/POLICY.md"
OSS_PREMIUM_EXCLUSIONS = {
    "illustrated-decodable-story-maker",  # POLICY.md: flagship book maker, SKILL.md sold for $400 — the ONLY exclusion
}
```

Env overrides (hermetic tests + one-off publishes): `OMO_OSS_REPO_DIR` (checkout
path) and `OMO_OSS_REPO_URL` (clone/push source).

2026-08-16 founder decision: `woven-relationship-book-maker` (was $29 license),
`japanese-style-story-video`, and `decodable-book-maker` are **free to download**
now — all three shipped in the first publish. Everything is free except the
flagship.

## Artifacts published per release → `skills/<slug>/`

| File | Source | Notes |
| --- | --- | --- |
| `SKILL.md` | `containers/<slug>/source/SKILL.md` (the compiled live contract) | + policy header inserted after frontmatter (below) |
| `LICENSE` | `oss/<slug>/LICENSE` when present, else repo-root MIT | MIT per oss/POLICY.md |
| `manifest.json` | generated | schema below |
| `README.md` | `oss/<slug>/README.md` when present, else generated minimal storefront README | links back to omo.space |

Policy header (inserted once, immediately after the frontmatter `---`; idempotent
if already present):

```markdown
> **Omo open source.** This `SKILL.md` is published under the MIT License per the
> [Omo open-source policy](https://github.com/omo-space/skills/blob/main/POLICY.md).
> Download and reuse it freely; to run it without setup, use the hosted run on
> [omo.space](https://omo.space) — pay per run, no subscription.
```

## manifest.json schema

```json
{
  "slug": "phoneme-counter",
  "name": "Phoneme Counter",
  "version": "0.1.0",
  "license": "MIT",
  "policy": "https://github.com/omo-space/skills/blob/main/POLICY.md",
  "hosted_run_price_usd": 0.10,
  "inputs": ["`word`: one English word, 1-80 characters.", "..."],
  "outputs": ["Return one JSON object with `run_id`, ..."],
  "source_sha256": "<sha256 of the published SKILL.md incl. header>",
  "publish_mechanism": "R4 oss publish gate (research/oss-publish-spec.md)"
}
```

- `version`: `containers/<slug>/manifest.json` `version`.
- `hosted_run_price_usd`: `containers/<slug>/pricing-report.json`
  `display_price_usd` (authoritative); cross-check `site/catalog.js` `runPrice`.
- `inputs`/`outputs`: deterministic parse of the SKILL.md `## Inputs` /
  `## Output contract` sections (bullet lines). If there is no `## Inputs`
  section, derive from Workflow step 1 (`1. **Step name:** description`) —
  never leave empty without a documented reason (see facebook-ads-copywriter).

## Premium exclusion

- If `slug in OSS_PREMIUM_EXCLUSIONS` → skip R4 silently, note `"oss": "excluded_premium"`
  in the release evidence. Never publish, never create the folder.
- The exclusion set lives in ONE constant (no per-skill conditionals scattered).

## Idempotency

- Same path `skills/<slug>/` is overwritten on every release — never duplicated.
- `manifest.source_sha256` changes only when the published SKILL.md changes;
  unchanged re-releases produce byte-identical artifacts (no-op commit allowed
  via "no changes" detection).
- Publish flow: clone/fetch `omo-space/skills` → write/overwrite the 4 files →
  `git add -A skills/<slug>` → commit `release(<slug>): v<version> oss publish`
  → push to `main`. Any error raises a typed blocker with a remediation
  (`OSS_PUBLISH_CLONE_FAILED`, `OSS_PUBLISH_COMMIT_FAILED`, `OSS_PUBLISH_PUSH_FAILED`).

## Typed blockers

Mirror `WorkerReleaseBlocker` (process-submissions.py:132): new
`OssPublishBlocker(ReleaseBlocker)` with codes + remediations registered in an
`OSS_PUBLISH_REMEDIATIONS` dict. Blocker text must name the exact failing step
(clone/commit/push) and the resume point (rerun from R4).

## Known debt (pre-existing repo state)

1. The 2026-08-12 batch folders that predate R4 (beyond the 15 already
   published) still lack per-folder `LICENSE`, `manifest.json`, and the policy
   header → one-time backfill job (same artifact builder) on the next publish
   wave. The flagship was published in that batch by mistake and has been
   REMOVED (commit c2dd051); R4 must never re-publish it.
2. Resolved: first publish done (commit 104a2b3) — 12 staged slugs + the three
   newly-free extras, full format, root POLICY.md added.

## Proof of format (staged, not pushed)

`/tmp/oss-publish-staged/skills/<slug>/` — the 15 live free slugs staged by
`/tmp/stage_oss_publish.py` + the R4 artifact builder (SKILL.md + header +
LICENSE + manifest + README), all pushed in the first publish.
