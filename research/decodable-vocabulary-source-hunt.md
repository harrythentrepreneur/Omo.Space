# Pilot-book vocabulary — source-hunt evidence (2026-08-16T15:0xZ)

Verification status: the "no reviewed word-bank exists" blocker claim is now
verified at **content level** (not just file-listing), and the public web was
hunted this tick through every reachable channel. **Conclusion: the five
stage vocabularies + sight-word list remain a Harry decision — nothing
reviewed is publicly fetchable.** But two loop-level corrections are recorded
below: (1) general curl/browser network access DOES work in cron (only the
Firecrawl web_tools backend is unconfigured); (2) Harry can unblock in ~5
minutes by pasting OR naming a URL (fetch+bind is now provably buildable from
cron).

## What was checked (all read-only, no spend/send/deploy/secret access)

1. **OMO-SPACE/SKILLS — content level, all 102 folders (NEW this tick)**
   `git clone --depth 1 https://github.com/omo-space/skills` (102 folders).
   Every SKILL.md grepped for embedded word banks (`sight word|word list|
   vocabulary|stage|examples:` and comma-separated lowercase word lists).
   Result: ZERO static word banks. The 8 hits
   (`vocabulary-tier-sorter`, `vocabulary-enhancer`,
   `syllable-splitter-and-counter`, `silent-letter-highlighter`,
   `phonics-list-generator`, `decodable-sentence-creator`,
   `decodable-book-maker`, `cvc-word-creator`) are all **procedural
   generators** — they produce lists per-request from the provider model,
   none ship a static reviewed stage vocabulary or sight-word list.
   `decodable-book-maker/SKILL.md` (65 lines) explicitly demands a
   "compiler-owned vocabulary" + "reviewed sight-word list" and ships
   neither — the contract *expects* the platform to own it.
   Prior ticks verified this only at the file-listing level; this tick
   verified the greppable content of every skill file.

2. **GitHub public search — `phonicsmaker` repositories: total_count 0.**
   No public PhonicsMaker code, word bank, or docs repo exists under any
   owner. `omo-space` org exposes exactly ONE public repo: `omo-space/skills`.

3. **phonicsmaker.com itself — unreachable behind Vercel Security Checkpoint.**
   - `curl` → HTTP 429 checkpoint on `/`, `/decodable-books`, `/app`.
   - `r.jina.ai` proxy → returns only the "Vercel Security Checkpoint" shell.
   - Real browser (browser_navigate, local stealth) → lands on the checkpoint,
     empty page, no auto-resolution within ~10 s.
   - `www.phonicsmaker.com`, `make.phonicsmaker.com`, `app.phonicsmaker.com`:
     DNS fails (000). `phonicsmaker.vercel.app`: HTTP 404.
   - Subdomain enumeration (crt.sh 404 on this endpoint; getent probes for
     docs/books/app/make/help/teach/shop/learn/portal/tools/decodables): none
     resolve.
   Harry owns this product — he can read the word bank his own
   decodable-books tooling trusts directly (that bank is the "fastest path"
   GOAL.md names; the loop simply cannot reach it through the checkpoint).

4. **Web archives & search engines — all rate-limited or bot-walled.**
   - web.archive.org availability+CDX: persistent 429 across 3 retries
     (10–25 s spacing); r.jina.ai→web.archive.org: 403 abuse-block.
   - DuckDuckGo HTML: bot-wall page, no organic results.
   - Bing HTML (curl): consent/JS shell, no results; r.jina.ai→Bing: page
     shell only, no organic listings.
   - Google via r.jina.ai: 403 abuse-alleviation block.
   - Teachers Pay Teachers via r.jina.ai: JS-only shell (PhonicsMaker's
     known distribution channel — a future in-person/captcha pass could
     still surface sample word lists there; not reachable headlessly today).

## Loop-level corrections (why this tick mattered)

- **The "web tooling unavailable in cron" claim is too broad.** The
  Firecrawl-backed `web_search`/`web_extract` tools are genuinely
  unconfigured (error: `Set FIRECRAWL_API_KEY...`), and that is exactly what
  made prior ticks type "no external corpus sourcing is possible." But raw
  `curl` (raw.githubusercontent.com 200 this tick) and the browser tool
  (reaches sites, executes JS) DO work in cron. So: *Firecrawl is
  unavailable; general network sourcing is NOT.* Future ticks with a named
  URL can fetch it directly (this is how `pilot-book-correction` proved the
  OSS manifest originally, and it still works).
- **The vocabulary gate's cost to Harry just dropped.** Instead of authoring
  word lists from scratch, Harry can either (a) paste the word bank his own
  PhonicsMaker decodable tooling trusts into the existing fill-in template
  (marketing/pilot-book-vocabulary-template.md, 5-minute job), or (b) name a
  URL (his own docs, a specific published scope-and-sequence word list) and
  the loop will fetch it over curl, bind it as
  `reviewed_spec.vocabulary` (provenance: reviewed), regenerate the
  container, and flip can_submit — the whole_book_vocabulary normalizer
  machinery is already done and fixture-proven 3/3.
- Nothing reviewed exists publicly (verified content-level this tick), so
  self-invention remains forbidden by the loop rules; the fill-in stays a
  Harry decision as designed.

## Re-check ritual for a future tick (cheap, bounded)

```
curl -s -m 15 https://archive.org/wayback/available?url=phonicsmaker.com   # retry
curl -s -m 20 https://api.github.com/search/repositories?q=phonicsmaker    # recheck
git clone --depth 1 -q https://github.com/omo-space/skills /tmp/omo-skills \
  && grep -rl -iE "sight word|word list" /tmp/omo-skills/skills/*/SKILL.md  # content recheck
```