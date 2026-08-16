# REDDIT SKILL-SOURCING — finding genuinely good skill.md files via Reddit

**Research date:** 2026-08-16
**Commissioned by:** Omo (omo.space) — AI workflow marketplace; free-download skill.md per skill + paid hosted runs; open-source library github.com/omo-space/skills (102 skills, growing toward 30,000 listings).
**Method:** Old.reddit RSS search (29 queries across r/ClaudeAI, r/ChatGPTCoding, r/OpenAI, r/AI_Agents, r/LLMDevs, r/artificial, r/SomebodyMakeThis) + full-thread HTML fetches parsed with BeautifulSoup, 2026-08-16. Verbatim quotes only from fetched content; every quote attributed (subreddit, URL, poster, date). Reuses verified quotes from `research/skills-research-report.md` (fetched 2026-08-12, 13 quotes / 5 threads — marked [SRR]) and adds fresh 2026-08-16 material.
**Honesty rule:** this doc separates **promising** (real artifact + real adoption/community signal) from **unproven** (maker claims, star counts, launch posts). No quote is invented; where a claim comes only from a poster, it's flagged.

---

## TL;DR

1. **Reddit is a discovery layer, not a library.** Nobody posts full skill.md files in threads; they post skills, GitHub links, and directories. The recurring sharing threads (r/ClaudeAI "Drop your best Claude skills in here!", r/ChatGPTCoding "…now I can't stop using them") are the highest-signal hunting grounds.
2. **The quality signals that separate good from junk, per commenters:** (a) a *narrow trigger + concrete procedure + observable artifact*, (b) an *independent user report* of a run with a real output, (c) follow-up/iteration threads (v2, "learned the hard way"), (d) maintainer who responds to critique; against: persona-prompt skills, mega-skills (14–18 phases), simulated verification, star-count-shopping.
3. **The community itself says most skills are unvetted garbage** — multiple marketplace founders' origin stories quote exactly that complaint. This is Omo's wedge: verified execution + per-skill evidence, not another file directory.
4. **Monetization is unproven.** "Has anyone actually sold custom AI agent skills as a product?" — [1r0p33n](https://www.reddit.com/r/ClaudeAI/comments/1r0p33n/), 2026-02-10 — the top answer: "It is not worth anything. Once you have thought up a skill you might need, you can just have claude write it for you. It will be a free resource forever and **the only value will come from skills that have been battle-tested**" (u/modernizetheweb). No one in the fetched threads shows real skill-file sales. Agensi (the only named marketplace) grew users on $0 ads via content/SEO — and its traffic claims were publicly debunked with Ahrefs data (see A5).
5. **Standards are real but paths are fragmented**: SKILL.md is "quietly becoming the standard", but skills live in `.claude/skills/`, `.codex/skills/`, `.agents/skills/` — and commenters flag dependency management, quality floors, and security as open gaps Omo can own.

---

## A. Where people share agent skills / SKILL.md files on Reddit

### A1. Recurring sharing threads (highest signal — bookmark these)

- **r/ClaudeAI — "Drop your best Claude skills in here!"** — [1sx44bc](https://www.reddit.com/r/ClaudeAI/comments/1sx44bc/), posted 2026-04-27. "Please share the Claude skills that you often use and are best for your day to day use cases or in businesses…" — the canonical recurring sharing thread; commenters list the skills they actually keep.
- **r/ChatGPTCoding — "I used to think that skills were useless but now I've 360'd and can't stop using them. What are some of yours?"** — [1viulom](https://www.reddit.com/r/ChatGPTCoding/comments/1viulom/), posted 2026-08-08. Fresh, post-skepticism thread — commenters name the skills that converted them. The OP's framing is the clearest non-technical definition of a skill in the corpus:

> "Skills are just docs that claude refers to… There's not really one place where people can like rate skills from community members (maybe someone should vibe-code that, haha)"

— u/M0shka, same thread, 2026-08-08 — **direct, dated demand for a community skill-rating platform — Omo's niche, stated by a user.** (Commenters also recommend mattpocock/skills — u/jaquanor, 5 pts.)
- **r/ClaudeAI — "What are the best Claude skills to download for writing, research, and productivity?"** — [1rrsrjx](https://www.reddit.com/r/ClaudeAI/comments/1rrsrjx/), 2026-03-12.
- **r/ClaudeAI — "These are the claude skills we use everyday to run my freelance business. What are yours?"** — [1rp52eq](https://www.reddit.com/r/ClaudeAI/comments/1rp52eq/), 2026-03-09 — business-use skills, not hobby skills.
- **r/ClaudeAI — "What are the must-have Claude skills for marketers?"** — [1qi080n](https://www.reddit.com/r/ClaudeAI/comments/1qi080n/), ~2026-02 [SRR] — 24-upvote marketer demand thread naming brand voice, SEO orchestration.

### A2. "I built / I open-sourced" launch threads (higher noise, higher ceiling)

- **r/ClaudeAI — "I open-sourced 59 Claude Skills covering the full website lifecycle (brand, design, content, SEO, dev, ops)"** — [1sz5alu](https://www.reddit.com/r/ClaudeAI/comments/1sz5alu/), 2026-04-29.
- **r/ClaudeAI — "I've collected 2300+ Claude Skills into a searchable directory"** — [1on1wj7](https://www.reddit.com/r/ClaudeAI/comments/1on1wj7/), 2025-11-03 — the directory hubs get the upvotes; the *curation* is the product. The maker's own honesty is the most useful data point in the thread:

> "I haven't tested or validated each one yet (that's definitely going to be my main focus for the next phase of development)… at this stage, most of the content is probably AI-generated."

— u/TingXuSuan (skillsmp.com), same thread, 2025-11-03 — **even the biggest directories admit no validation. That is Omo's pitch, verbatim.**

> "who are the authors of the assets? How were the tested/validated? All the prompts, rules etc. sites ive seen look obviously filled with AI generated content"

— u/rm-rf-rm, same thread, 2025-11-03 — the question every directory gets asked and none can answer.

> "the curating / evaluating angle will be KEY to the longevity and utility value of this."

— u/Monarc73, same thread, 2025-11-03

> "we need a way to vote for them / measure downloads."

— u/maigpy, same thread, 2025-11-03 — **demand for per-skill rating/download signals (which Omo has natively: runs, saves, paid conversions).**

- **r/ClaudeAI — "I built skills-hub.ai, a free catalog of 2,400+ AI agent skills from Anthropic, Google…"** — [1rwl3jt](https://www.reddit.com/r/ClaudeAI/comments/1rwl3jt/), 2026-03-17.
- **r/ClaudeAI — "Ultimate Claude Skill.md: Auto-Builds ANY Full-Stack Web App Silently"** — [1qb1024](https://www.reddit.com/r/ClaudeAI/comments/1qb1024/), 2026-01-12, 167 upvotes — the cautionary mega-skill: commenters flagged "Massive scope bloat — 14-18 phases for every app (overkill for MVPs)" [SRR, u/kashaziz].
- **r/ClaudeAI — "I've been tracking what people are building with Claude Skills since launch - here's the wildest stuff I've seen"** — [1o9ph4u](https://www.reddit.com/r/ClaudeAI/comments/1o9ph4u/), 2025-10-18 — curation of community builds; great source of *what people actually build*.

### A3. Evaluation / critique threads (the trust layer)

- **r/ClaudeAI — "I tested 30+ community Claude Skills for a week. Here's what actually works (complete list + GitHub links)"** — [1ok9v3d](https://www.reddit.com/r/ClaudeAI/comments/1ok9v3d/), 2025-10-30 — **the single best model for Omo: a third party testing skills and reporting what works.** This is the "verified execution" pattern Reddit rewards. (Contested in-thread — see B2 "fake evaluation rigor".)
- **r/ClaudeAI — "I've been building Claude Skills for a month. Here's what I learned the hard way."** — [1rklufk](https://www.reddit.com/r/ClaudeAI/comments/1rklufk/), 2026-03-04 — 66 comments; the sub's auto-summary: "your 'Skill as a job description' analogy is a winner."

> "A prompt is a request. A Skill is a job description. That one reframe changed everything."

— u/uebersax, same thread, 2026-03-04 — **the most-cited definition of a good skill in the corpus.** (The thread's top comment, 121 pts, adds the build loop: "Load the skill-creator skill and let an agent do deep research on a topic (like SEO) and then hone in the skill until it's perfect." — u/mutual_disagreement.)

- **r/ClaudeAI — "Do Claude skills actually work?"** — [1ugrff7](https://www.reddit.com/r/ClaudeAI/comments/1ugrff7/), ~2026-03 [SRR] — skepticism + evidence thread; source of the "small, triggered procedures, not a second system prompt" quote.
- **r/ClaudeAI — "I was wrong about Agent Skills and how I refactor them"** — [1opxgq4](https://www.reddit.com/r/ClaudeAI/comments/1opxgq4/), 2025-11-06 — iteration/refactor insight thread.
- **r/LLMDevs — "Skill.md A/B testing"** — [1s90orv](https://www.reddit.com/r/LLMDevs/comments/1s90orv/), 2026-03-31 — SkillBench: A/B tests for Claude Code skills. The measurement layer exists as a hobby project.

### A4. Standards / ecosystem threads

- **r/ClaudeAI — "Agent Skills is now an open standard"** — [1ppw38d](https://www.reddit.com/r/ClaudeAI/comments/1ppw38d/), 2025-12-18 (official announcement).
- **r/ClaudeAI — "Understanding CLAUDE.md vs Skills vs Slash Commands vs Plugins"** — [1ped515](https://www.reddit.com/r/ClaudeAI/comments/1ped515/), 2025-12-04.
- **r/LLMDevs — "'Agent Skills' - The spec unified us. The paths divided us."** — [1qcihrv](https://www.reddit.com/r/LLMDevs/comments/1qcihrv/), 2026-01-14 — `.github/skills/` vs `.claude/skills/` vs `.codex/skills/` fragmentation.
- **r/AI_Agents — "SKILL.md is quietly becoming the standard for teaching AI agents new capabilities"** — [1stcu8e](https://www.reddit.com/r/AI_Agents/comments/1stcu8e/), 2026-04-23 — the standard-formation post: "Claude Code, OpenClaw, Codex CLI, Cursor, Gemini CLI — they're all converging on a shared file format called SKILL.md… now 20+ agents support it." (Poster is the Agensi founder — self-promotional, linked agensi.io resources; still the clearest statement of the convergence.) An enterprise demand in the same thread:

> "I ideally want an MCP server where i can define skills for various agents like dev, designer, qa, sdet… And then everyone on my team can use those standard skills. So that everyone in team need not to invent best skills and work can be uniform across team members and tools."

— u/Character-Western122, same thread, 2026-04-23 — **team/org skill management is an unserved enterprise need (matches r/AI_Agents 1vp5dwz).**

- **r/LLMDevs — "The 3 Types of Agent Skills Nobody Distinguishes (But Should)"** — [1sklgm5](https://www.reddit.com/r/LLMDevs/comments/1sklgm5/), 2026-04-13 — the taxonomy post (Alexa-style voice skills vs function wrappers vs agent behaviors). Best in-thread addition — the security-relevant axis:

> "the distinction I keep running into that nobody names: skills that are stateless vs skills that mutate external state. a skill that queries an API is totally different from one that posts or deletes something, but frameworks treat them the same and that's where things go sideways in prod"

— u/Low_Blueberry_6711, same thread, 2026-04-16 — **read vs mutate is the permission axis Omo's sandboxed run model already implements — and the community explicitly wants it surfaced.**

- **r/LLMDevs — "Agent skill plugins have a dependency-management gap"** — [1vk2yen](https://www.reddit.com/r/LLMDevs/comments/1vk2yen/), 2026-08-09 — skills depending on skills: an unsolved ecosystem problem.
- **r/ClaudeAI — "What is the most recommended website for browsing a catalog of downloadable skills?"** — [1qcj27k](https://www.reddit.com/r/ClaudeAI/comments/1qcj27k/), 2026-01-14 — names the aggregator landscape (skillsmp.com, claudeskills.ai, skillstore.io, claude-plugins.dev, smithery.ai/skills, skills.pub…). The community's pick: "https://claude-plugins.dev/skills is the most helpful besides the official Claude Skills" (u/StravuKarl, 23 pts). A directory founder's honest refusal to enter the space:

> "Does anyone actually find skill directories useful?… it feels like the vast-vast majority of Skills are themselves just vibe-coded prompts. I am not [sure] how valuable those are or how one would even filter/sort [them]."

— u/punkpeye (founder of Glama, an MCP index), same thread, 2026-01-15 — **a competitor explicitly declining to build a skills index because quality is unfilterable. Omo's verification layer is the missing filter.**

### A5. Marketplace-specific threads (Omo's competitive/adjacent space)

- **r/ClaudeAI — "Claude is my SEO strategist, content engine, and CTO. From 0 to 10,000 active users in 6 weeks, $0 on ads"** — [1syt37w](https://www.reddit.com/r/ClaudeAI/comments/1syt37w/), 2026-04-29 — Agensi founder's growth story (140 comments). **The community's verdict is the real data:** the sub's auto-summary reports "The consensus is that this is a spammy ad for OP's site, and the community is calling BS on the traffic stats. The top comments are roasting OP, with multiple users posting data from SEO tools like Ahrefs that show the website is a ghost town." Top comments:

> "All those words just for some more 'generic AI slop'"

— u/Polite_Jello_377 (241 pts), same thread

> "Simply saying. Spammer"

— u/paramarioh (224 pts), same thread

> "Tell me this entire post wasn't written by Claude/AI"

— u/DetrimentalContent (170 pts), same thread

> "you are probably talking to his 'reddit strategist agent' rn."

— u/lord-humus, same thread — **hard lesson for Omo: a growth-story post from an AI-built product gets profile-checked and Ahrefs-checked within hours. Never post unverifiable traffic claims; the community will pull the counter-data themselves.** The *method* in the post is still worth adopting (GSC-data → gap analysis → article targeting), just never the *claims*.

- **r/OpenAI — "I built a marketplace for AI agent skills and grew it to 17K users with $0 on ads. ChatGPT did all the…"** — [1tausi7](https://www.reddit.com/r/OpenAI/comments/1tausi7/), 2026-05-12 — same founder, same playbook (claims: 17K active users, 559K Google impressions/mo, 509 indexed pages in ~8 weeks; only 2 comments — low engagement = community fatigue with the pitch). The useful core: "I don't write content. I write data analysis prompts… I export my Google Search Console data…" — the GSC-driven content loop is the single most reproducible SEO tactic in this corpus (see REDDIT-AI-SEO-STRATEGY playbook rule 16).
- **r/AI_Agents — "Most AI agent 'skills' on GitHub are unvetted garbage. I built a marketplace to fix that."** — [1sumut0](https://www.reddit.com/r/AI_Agents/comments/1sumut0/), 2026-04-24. The problem statement every Omo doc should quote:

> "There are 800,000+ SKILL.md files on GitHub right now… Most are someone's personal config with hardcoded project paths that won't work for anyone else. A decent chunk are AI-generated slop that was never tested. Some are just broken YAML that the agent can't even parse. And then there are the actually dangerous ones. Researchers found skills with prompt injection buried in the instructions. Skills that quietly try to exfiltrate your project files. Skills that tell the agent to ignore its safety constraints."

— u/BadMenFinance (Agensi), same thread, 2026-04-24 — **the four failure classes: personal config, untested slop, broken YAML, malicious injection. This is the exact gap Omo's verification + sandboxed run addresses.** (Criticism in-thread: "you're also in the category you're dogging!" — u/Pitiful-Sympathy3927; "Vercel beat you to it ages ago skills.sh" — u/wewerecreaturres. And a useful tool link: [cisco-ai-defense/skill-scanner](https://github.com/cisco-ai-defense/skill-scanner) — u/Iron-Over.)

> "Our company trust skills from respected companies like Anthrophic or Databricks. Lot more governance scrutiny on unofficial Skills and MCP servers."

— u/RecalcitrantMonk, same thread, 2026-04-24 — **enterprise buyers already gate skills by publisher trust; Omo's creator-identity + verification is the marketplace answer to that gate.**

- **r/AI_Agents — "Before You Build a Company Marketplace for Agent Skills"** — [1vp5dwz](https://www.reddit.com/r/AI_Agents/comments/1vp5dwz/), 2026-08-15 — the cautionary data-driven thread (posted the day before this research). skills.sh lists **972,985 skills all-time**; the poster's thesis:

> "The public data shows why every company skill needs an owner, a clear home, and somebody who keeps it current."

— u/myfear3, same thread, 2026-08-15

> "every internal tool ends up with a dusty skills repo that nobody owns after the first six months"

— u/Ok-Prune-6415, same thread, 2026-08-15 — **maintenance/ownership is the lifecycle problem; Omo's versioned listings with last-verified dates directly answer it.**

- **r/claude — "I built a marketplace for skill.md skills because…"** — [1rkjqjf](https://www.reddit.com/r/claude/comments/1rkjqjf/), ~2025-06 [SRR] — 35-upvote launch; commenters asked for md previews and questioned quality vs self-generated prompts.

### A6. Where NOT to look

- **r/SomebodyMakeThis** — two queries ("AI agent", "agent skills") returned **0 results** on 2026-08-16; the sub is for *requests* ("somebody make this"), not skill sharing. Use it for *demand* (what people wish existed), not supply.
- **r/ChatGPTCoding "GPT skills"** — 1 result; the term people actually use is "skills", "SKILL.md", or "agent skills".
- Mega-skill/auto-builder threads (see 1qb1024) — high upvotes, low quality; commenters torch them.

---

## B. Signals that separate good skills from junk (as Reddit actually behaves)

### B1. Good-skill signals (converged across threads)

0. **The consensus "top-tier" skills are named explicitly.** In the 159-comment "Drop your best Claude skills" thread, the sub's auto-summary reports: "The big showdown is between GSD and Superpowers. Most agree they are the top-tier skills, but for different [reasons]" — u/ClaudeAI-mod-bot, [1sx44bc](https://www.reddit.com/r/ClaudeAI/comments/1sx44bc/), 2026-04-27. (GSD = "Getting Shit Done"; Superpowers = obra/superpowers, 271K★.) The **highest-scored single comment (241 pts)** is a meta-skill, which tells you what the community values most:

> "My most valuable skill is a meta-skill that observes my work sessions and logs skill improvement opportunities for all my skills (including itself) and then applies them in scheduled autonomous skill improvement sessions."

— u/rebelytics (241 pts), same thread, 2026-04-27 — [github.com/rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) — **the winning pattern is procedural, self-improving, and session-observing — not a static prompt.**

1. **Independent outcome report** — a non-maker poster describing a concrete run/output (the 165-upvote r/SideProject field test of coreyhaines31/marketingskills: "30 minutes, 4 skills, and I had a positioning doc, landing page copy, email sequence, and a product poster." [SRR, 2026-08-12 fetch]). Caveat: commenters suspected promotion — treat as public evidence, not a controlled test.
2. **Narrow trigger + concrete procedure + observable artifact** — "Skills work better as small, triggered procedures than as a second system prompt" (u/anasgoblins, r/ClaudeAI 1ugrff7 [SRR]).
3. **Real shared context** — "the shared context file is the actual insight here and it's underrated" (u/Deep_Ad1959, r/SideProject 1spqw1p [SRR]).
4. **Reusable company/business context** — "A Meta Ads skill that loads our ad account structure, naming conventions, campaign framework, and best practices so Claude doesn't need that context re-explained every time" (u/CommissionDry8792, r/ClaudeAI 1u8t66a [SRR]).
5. **Second-pass / enforcement behavior** — "The skill only earns its keep if it forces a real second pass over the finished draft, not just a list of tells described up front" (u/Ornery_Car6086, r/ClaudeAI 1u8t66a [SRR]).
6. **Maintainer responds to critique** — threads like 1rrkicy ("I maintain an open-source library of 181 agent skills. I would like to get your criticism") and 1opxgq4 (refactor confession) draw engagement; defensive/launch-only posters get called out.
7. **A specific, real job behind it** — "I have to convert pngs to .c files often, so I had Claude code make a skill to do the conversion" (u/_Wily-Wizard_, r/ClaudeAI 1ugrff7 [SRR]) — the job-to-skill ratio is the single most repeated good-skill pattern.
8. **Live-data hooks over static knowledge** — "You identified one piece that usually breaks workflows: data access to business data, marketing, performance, sales, whatever. When your hooks can work with real up to date information…" (u/ArielCoding, r/ClaudeAI 1ok9v3d, 2025-11-01) — **direct support for Omo's hosted-run model: skills wired to real, current data are the ones that survive.**
9. **Measured effect** — "tested 9 models with and without agent skills. Haiku 4.5 with a skill beat baseline Opus 4.7." ([1srpv7c](https://www.reddit.com/r/ClaudeAI/comments/1srpv7c/), 2026-04-21 — Tessl researcher, self-disclosed: treat as industry-research signal, not neutral).

### B2. Junk-skill signals (the community's own list)

- **Persona/system-prompt skills** — "a second system prompt" (same 1ugrff7 thread).
- **Mega-skills** — "Massive scope bloat — 14-18 phases for every app (overkill for MVPs)" (u/kashaziz on 1qb1024 [SRR]).
- **Simulated verification** — the "Universal Full-Stack Web App Builder" prompt required "realistic" commit hashes and "100% pass" claims; commenters flagged it (skills-research-report.md §2).
- **Unvetted GitHub files** — "Most AI agent 'skills' on GitHub are unvetted garbage" (1sumut0, 2026-04-24); "find a skill on GitHub, check if it's actually good (most aren't), figure out if the SKILL.md is even formatted right, then hope it doesn't break anything" (u/BadMenFinance, r/claude 1rkjqjf [SRR]).
- **Star-count shopping** — "All these 'agent specs' repos are hype. Not bad, just mainly hype and we should pick one that suits our needs and not based on stars." (u/Reebzy, r/SideProject 1spqw1p [SRR]); r/ClaudeAI 1stfoo7 "Why does this CLAUDE.md file have so many stars?" (2026-04-23).
- **Detectable AI-slop marketing** — "An ai written post about ai discovering your likely ai written website" (u/KanyeWestsPoo, r/juststart 1ve3olr, 2026-08) — the community profile-checks posters; a week of account history + a repo link is the tell.
- **Fake evaluation rigor** — even the well-received "I tested 30+ skills" post got challenged: "The fact that you can actually judge 30+ of anything in a week is stupid. Stop blog spamming and actually use something." (u/ryanchants, 10 pts, r/ClaudeAI 1ok9v3d, 2025-10-31); "Even the wiring screams AI FLUFF" (u/3lonMux, 6 pts, same thread) — **Omo's per-skill fixtures must survive this scrutiny: they need real inputs, real outputs, versioned runs, not vibes.**
- **Context bloat** — "Our AI agent was burning 55k tokens before it did any work. We deleted almost every tool and context u[p]" (r/LLMDevs [1stj4aj](https://www.reddit.com/r/LLMDevs/comments/1stj4aj/), 2026-04-23).

### B3. Engagement patterns to read (operational)

- **Follow-up threads** = the trust signal. 1ok9v3d (tested 30+ skills) was followed by skill makers iterating; 1rklufk ("learned the hard way") is a confession thread, which the sub rewards with detailed replies.
- **Comment ratio > upvote ratio** for launch threads = skepticism (people arguing), not adoption.
- **"Drop your best X" threads decay after ~2 weeks** — the recurring ones get re-asked monthly; Omo's agent should re-sweep them on a schedule.
- **The "actual numbers" moment** (u/NervousBasis8600's "37 sessions… one paying customer") always lands better than claims — for skills too: run-counts, cost, output receipts.

---

## C. Discovery methods — 10 exact search strings that work

Verified on 2026-08-16 against old.reddit RSS search (`old.reddit.com/r/<sub>/search.rss?q=<query>&restrict_sr=1&sort=relevance&limit=25`). Quoted phrases work; relevance sort surfaces the canonical threads.

**Sharing/hunting queries (run on r/ClaudeAI, r/ChatGPTCoding, r/AI_Agents):**
1. `SKILL.md` — broadest recall (25/25 entries on r/ClaudeAI, r/AI_Agents, r/LLMDevs, r/OpenAI).
2. `"Claude skills"` — the feature-name thread cluster (r/ClaudeAI, 25/25).
3. `"agent skills"` — the cross-agent cluster (r/ClaudeAI 25/25; r/LLMDevs 25/25; r/AI_Agents 25/25).
4. `"drop your best"` — finds the recurring sharing threads across subs (r/ClaudeAI hit 1sx44bc).
5. `"what are the best"` + subreddit — recommendation threads (r/ClaudeAI 1rrsrjx).

**Evaluation/trust queries:**
6. `"tested" skills` / `"what actually works"` — the tester threads (r/ClaudeAI 1ok9v3d).
7. `"learned the hard way"` — confession/lesson threads (r/ClaudeAI 1rklufk).

**Marketplace/ecosystem queries:**
8. `"skills marketplace"` — r/AI_Agents (7 entries; mixed signal — read titles, most are off-topic).
9. `"sell" skills` / `"sold" "agent skills"` — monetization reality check (r/ClaudeAI 1r0p33n).
10. `"SKILL.md is"` — the standardization takes (r/AI_Agents 1stcu8e; r/LLMDevs 1sklgm5 "The 3 Types of Agent Skills Nobody Distinguishes (But Should)").

**Dead strings (2026-08-16):** `"GPT skills"` on r/ChatGPTCoding (1 result), `"AI agent"` / `"agent skills"` on r/SomebodyMakeThis (0 results).

**Beyond search — the routing table that works:** RSS titles → curate top ~15 threads per theme → fetch full thread HTML (BeautifulSoup parse; ~75s cadence) → extract verbatim quotes with author/score/date → checkpoint everything. This exact pipeline produced this report and the 2026-08-12 skills report (same route; note the 2026-08-12 run hit 403s from a different IP — route availability varies by IP/day, keep the checkpointed pipeline).

---

## D. Starter list — 15 skill ideas / linked skills that look genuinely good

Each entry: what it is, where found (thread + date), why it looks good, evidence tier. Tier A = independent outcome report; B = real artifact + adoption; C = maker claim only. **Honest flags included.**

| # | Skill / idea | Source (Reddit thread, date) | Why it looks good | Tier |
|---|---|---|---|---|
| 1 | **MarketingSkills pack (ads, ad-creative, copywriting, cold-email, seo-audit, programmatic-seo, churn-prevention, offers)** — 44,020★ repo | [r/SideProject field test](https://www.reddit.com/r/SideProject/comments/1spqw1p/) (165 upvotes, 2026-07) [SRR] | Independent-ish user report: "30 minutes, 4 skills… positioning doc, landing page copy, email sequence, and a product poster." Commenters suspected promotion → reproduce, don't inherit | A (with caveat) |
| 2 | **unslop-text / unslop-ui — AI-slop flag & removal skills** | [r/ClaudeAI 1udl9hg](https://www.reddit.com/r/ClaudeAI/comments/1udl9hg/) (2026-06-23) + [1u9sgj3](https://www.reddit.com/r/ClaudeAI/comments/1u9sgj3/) (2026-06-19) | Built from a 90K-post / 3.2M-post Reddit analysis — data-grounded, narrow trigger, direct Omo humanizer synergy | B |
| 3 | **Humanizer (structure-level AI-prose editing)** | [r/ClaudeAI 1v9tse5](https://www.reddit.com/r/ClaudeAI/comments/1v9tse5/) (2026-07-29) | Same niche as Omo's humanizer play; open-source, MIT | B |
| 4 | **Meta Ads account-context skill** | [r/ClaudeAI 1u8t66a](https://www.reddit.com/r/ClaudeAI/comments/1u8t66a/) [SRR] | Company AI lead reports building it; validates the account-context pattern Omo's shared-brand-context product targets | B |
| 5 | **Prompt-writer skill ("writes accurate prompts for any AI tool… 600+ stars, 4000+ traffic")** | [r/ClaudeAI 1rxyarx](https://www.reddit.com/r/ClaudeAI/comments/1rxyarx/) (2026-03-19) | Real adoption numbers in-thread; narrow, self-referential, testable | B (maker-reported traffic) |
| 6 | **Site-lifecycle skill set (brand, design, content, SEO, dev, ops — 59 skills)** | [r/ClaudeAI 1sz5alu](https://www.reddit.com/r/ClaudeAI/comments/1sz5alu/) (2026-04-29) | Broad but job-scoped catalog; direct fit with Omo's marketing/coding categories | C (no independent test fetched) |
| 7 | **coding-posture (task-aware modes for coding agents, MIT)** | [r/LLMDevs 1uf2zy6](https://www.reddit.com/r/LLMDevs/comments/1uf2zy6/) (2026-06-25) | "One SKILL.md, research-backed" — the format/quality discipline Omo's compiler validates | C |
| 8 | **SkillBench — A/B testing for Claude Code skills** | [r/LLMDevs 1s90orv](https://www.reddit.com/r/LLMDevs/comments/1s90orv/) (2026-03-31) | The *measurement* layer — exactly the "verified execution" gap Omo sells | B |
| 9 | **Reddit-research-as-a-skill (replacing a complex agent)** | [r/AI_Agents 1viq7y9](https://www.reddit.com/r/AI_Agents/comments/1viq7y9/) (2026-08-08) | "I replaced a fairly complex Reddit research agent with a Codex skill… many 'agents' can be simply [replaced]" — the skills-over-agents thesis | B (poster report) |
| 10 | **5 skills to install before any agent project** | [r/AI_Agents 1roe8k8](https://www.reddit.com/r/AI_Agents/comments/1roe8k8/) (2026-03-08) | Curated starter set; comment engagement = what the sub actually installs | C |
| 11 | **3 Types of Agent Skills taxonomy** | [r/LLMDevs 1sklgm5](https://www.reddit.com/r/LLMDevs/comments/1sklgm5/) (2026-04-13) | The missing classification layer — Omo's category tree can be built on it | C (analysis, not artifact) |
| 12 | **CLAUDE.md → skill refactor thread (learned the hard way)** | [r/ClaudeAI 1rklufk](https://www.reddit.com/r/ClaudeAI/comments/1rklufk/) (2026-03-04) | Confession thread = the community's own quality rules (what not to ship) | — (guidance) |
| 13 | **9-model skill comparison (Haiku+skill > Opus baseline)** | [r/ClaudeAI 1srpv7c](https://www.reddit.com/r/ClaudeAI/comments/1srpv7c/) (2026-04-21) | Industry research (self-disclosed Tessl) — the best public argument that skills create measurable lift | B (self-disclosed) |
| 14 | **2300+ skill directory + skills-hub.ai 2400+ catalog** | [r/ClaudeAI 1on1wj7](https://www.reddit.com/r/ClaudeAI/comments/1on1wj7/) (2025-11-03), [1rwl3jt](https://www.reddit.com/r/ClaudeAI/comments/1rwl3jt/) (2026-03-17) | The existing supply indexes — Omo's source list for seeding; their weakness (no verification) is Omo's pitch | B (supply evidence) |
| 15 | **"Before You Build a Company Marketplace for Agent Skills"** | [r/AI_Agents 1vp5dwz](https://www.reddit.com/r/AI_Agents/comments/1vp5dwz/) (2026-08-15) | Data-driven warning: "every company skill needs an owner, a clear home, and somebody who keeps it current" — read before Omo builds marketplace ops | — (strategy) |
| 16 | **one-skill-to-rule-them-all (self-improving meta-skill)** | [r/ClaudeAI 1sx44bc](https://www.reddit.com/r/ClaudeAI/comments/1sx44bc/) (2026-04-27, 241-pt comment) → [github.com/rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) | The most-upvoted skill comment in the corpus; self-improvement loop pattern; repeated community interest in the thread | B (poster report + repo) |
| 17 | **reddit-pain-research-skill (research agent → skill)** | [r/AI_Agents 1viq7y9](https://www.reddit.com/r/AI_Agents/comments/1viq7y9/) (2026-08-08) → [github.com/haseebeqx/reddit-pain-research-skill](https://github.com/haseebeqx/reddit-pain-research-skill) | Replaces a "complex" multi-agent research pipeline with one Codex skill (harness-native: no separate loop/runtime); commenters: "90% of people on this sub are over engineering stuff codex and Claude can do" | B (poster report + repo) |
| 18 | **SkillBench (skill A/B testing tool)** | [r/LLMDevs 1s90orv](https://www.reddit.com/r/LLMDevs/comments/1s90orv/) (2026-03-31) → [github.com/Techfolk-AS/skill-bench](https://github.com/Techfolk-AS/skill-bench) | "Intuition about what makes a good SKILL.md or skill description is often wrong, so I wanted to actually test it" — measurement-first; commenter notes Claude's own skill-creator ships an eval harness | B (artifact + open-sourced) |

**Promising-but-unproven (explicit):** the marketplaces themselves (Agensi at 10K→17K users [1syt37w, 1tausi7] — user growth on $0 ads is real and SEO/content-driven, but the claims were publicly contested with Ahrefs data and *skill-file sales* revenue was never shown); "has anyone actually sold custom AI agent skills?" [1r0p33n] got no sales data in-thread — but one commenter gave the strongest monetization answer in the corpus, and it is the specificity thesis that matches Omo's hosted-run product:

> "the value lives in the specificity, not the format. A generic 'writing skill' is worth almost nothing because anyone can write that prompt in five minutes. A skill that encodes how a senior tax accountant actually reviews a return, or how a specific HVAC dispatcher triages an after-hours call, or how an experienced VA [works]…"

— u/Leading-Feature7966, [r/AI_Agents "Is there value in buying and selling skills created by real experts?"](https://www.reddit.com/r/AI_Agents/comments/1tfrf0n/), 2026-05-17

And the same thread independently proposes Omo's exact try-before-buy mechanic:

> "What if the marketplace had a built-in agent that lets you test any skill on your actual task before you pay? You see the output first, then decide if it's worth it."

— u/nothing786767 (OP), same thread, 2026-05-17 — **a real user inventing Omo's "free sample run" model on the spot.** (Counter-views in-thread: "Nah don't buy harness your own skills" — u/Dhairya15; "Yes it's called selling books" — u/Crafty_Disk_7026.)

Every star count is a discovery signal, not a quality badge (community consensus, see B2).

---

## E. Honest assessment — what's promising vs unproven for Omo

**Promising:**
- Reddit gives Omo a *curated source list* (D above), *quality language* (B1/B2), and *demand evidence* (the repeated "unvetted garbage" complaint + tester-thread success) for its verified-execution pitch.
- The recurring sharing threads are a reliable monthly re-sweep target for sourcing new skills.
- The "skills are small triggered procedures with shared context" consensus aligns exactly with Omo's skill format and its shared-context product.

**Unproven / risks:**
- **Willingness to pay for skill.md files** — no thread shows real paid transactions; the strongest marketplaces grow users, not file revenue. Omo's hosted-run monetization sidesteps this, but the docs must not claim file-sales demand.
- **AEO/slop backlash** — any Omo marketing that smells like low-authority AI slop gets torched in-thread (see 1ve3olr); all UGC/marketing must be real-proof-based.
- **Quality measurement** — SkillBench is a hobby tool; there is no community-standard skill benchmark. Omo's per-skill fixtures would be the first credible one — but that's an Omo claim to prove, not a Reddit fact.
- **Route instability** — old.reddit fetch availability varies by IP/day (403 on 2026-08-12, fine on 2026-08-16); the checkpointed pipeline is mandatory for repeat runs.

---

## Appendix — threads referenced (skills lane)

| Title (truncated) | Sub | Date | URL |
|---|---|---|---|
| Drop your best Claude skills in here! | ClaudeAI | 2026-04-27 | /r/ClaudeAI/comments/1sx44bc/ |
| I used to think that skills were useless but now I've 360'd | ChatGPTCoding | 2026-08-08 | /r/ChatGPTCoding/comments/1viulom/ |
| I tested 30+ community Claude Skills for a week. Here's what actually works | ClaudeAI | 2025-10-30 | /r/ClaudeAI/comments/1ok9v3d/ |
| I've collected 2300+ Claude Skills into a searchable directory | ClaudeAI | 2025-11-03 | /r/ClaudeAI/comments/1on1wj7/ |
| I've been building Claude Skills for a month. Here's what I learned the hard way | ClaudeAI | 2026-03-04 | /r/ClaudeAI/comments/1rklufk/ |
| What is the most recommended website for browsing a catalog of downloadable skills? | ClaudeAI | 2026-01-14 | /r/ClaudeAI/comments/1qcj27k/ |
| Most AI agent "skills" on GitHub are unvetted garbage. I built a marketplace to fix that | AI_Agents | 2026-04-24 | /r/AI_Agents/comments/1sumut0/ |
| Before You Build a Company Marketplace for Agent Skills | AI_Agents | 2026-08-15 | /r/AI_Agents/comments/1vp5dwz/ |
| Claude is my SEO strategist, content engine, and CTO. 0 to 10,000 active users in 6 weeks | ClaudeAI | 2026-04-29 | /r/ClaudeAI/comments/1syt37w/ |
| I built a marketplace for AI agent skills and grew it to 17K users with $0 on ads | OpenAI | 2026-05-12 | /r/OpenAI/comments/1tausi7/ |
| Has anyone actually sold custom AI agent skills as a product? | ClaudeAI | 2026-02-10 | /r/ClaudeAI/comments/1r0p33n/ |
| I replaced a fairly complex Reddit research agent with a Codex skill | AI_Agents | 2026-08-08 | /r/AI_Agents/comments/1viq7y9/ |
| SKILL.md is quietly becoming the standard for teaching AI agents new capabilities | AI_Agents | 2026-04-23 | /r/AI_Agents/comments/1stcu8e/ |
| The 3 Types of Agent Skills Nobody Distinguishes (But Should) | LLMDevs | 2026-04-13 | /r/LLMDevs/comments/1sklgm5/ |
| Skill.md A/B testing | LLMDevs | 2026-03-31 | /r/LLMDevs/comments/1s90orv/ |
| Hi, I have an important question about skills.md files (buy/sell expert skills?) | AI_Agents | 2026-05-17 | /r/AI_Agents/comments/1tfrf0n/ |
| Agent Skills is now an open standard | ClaudeAI | 2025-12-18 | /r/ClaudeAI/comments/1ppw38d/ |
| "Agent Skills" - The spec unified us. The paths divided us. | LLMDevs | 2026-01-14 | /r/LLMDevs/comments/1qcihrv/ |
| Agent skill plugins have a dependency-management gap | LLMDevs | 2026-08-09 | /r/LLMDevs/comments/1vk2yen/ |
| I open-sourced 59 Claude Skills covering the full website lifecycle | ClaudeAI | 2026-04-29 | /r/ClaudeAI/comments/1sz5alu/ |
| Our AI agent was burning 55k tokens before it did any work | LLMDevs | 2026-04-23 | /r/LLMDevs/comments/1stj4aj/ |
| tested 9 models with and without agent skills. Haiku 4.5 with a skill beat baseline Opus 4.7 | ClaudeAI | 2026-04-21 | /r/ClaudeAI/comments/1srpv7c/ |
| Why does this CLAUDE.md file have so many stars? | ClaudeAI | 2026-04-23 | /r/ClaudeAI/comments/1stfoo7/ |
| Found a GitHub repo 20k stars that turns AI into… (field test) | SideProject | 2026-07 | /r/SideProject/comments/1spqw1p/ [SRR] |
| What Claude skills have you built that are useful at work? | ClaudeAI | ~2026-03 | /r/ClaudeAI/comments/1u8t66a/ [SRR] |
| Do Claude skills actually work? | ClaudeAI | ~2026-03 | /r/ClaudeAI/comments/1ugrff7/ [SRR] |
| Ultimate Claude Skill.md: Auto-Builds ANY Full-Stack Web App Silently | ClaudeAI | 2026-01-12 | /r/ClaudeAI/comments/1qb1024/ [SRR] |
| I built a marketplace for skill.md skills because… (Agensi launch) | claude | ~2025-06 | /r/claude/comments/1rkjqjf/ [SRR] |
| What are the must-have Claude skills for marketers? | ClaudeAI | ~2026-02 | /r/ClaudeAI/comments/1qi080n/ [SRR] |
