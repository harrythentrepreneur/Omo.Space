#!/usr/bin/env python3
"""
GitHub skill-scout — discover and score candidate SKILL.md repos for Omo.

Read-only. Uses `gh api` (the user's existing gh auth). No secrets, no writes,
no pushes. Scoring + gate model documented in research/GITHUB-SKILL-SOURCING.MD.

Philosophy (founder rule): reject-by-default. A candidate must PASS every hard
gate (license, structure, secret-filename scan, tree integrity) before it can
be recommended for vetting, and stars are only a first filter — never a
recommendation. Rejections are the normal outcome; each carries a recorded
reason.

Usage:
    python3 scripts/github-skill-scout.py [--out /tmp/github-skill-scout/results.json]
                                          [--limit 25] [--max-pool 70]
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

SEARCH_SLEEP = 2.5  # authenticated search API limit is 30/min; be polite

# ---------------------------------------------------------------------------
# Curated discovery queries (exact search strings, GitHub repo search syntax)
# ---------------------------------------------------------------------------
REPO_QUERIES = [
    ("org",     "org:anthropics skills",        "Canonical org repos (anthropics/skills + siblings)"),
    ("topic",   "topic:claude-skills",          "Topic: claude-skills"),
    ("topic",   "topic:ai-skills",              "Topic: ai-skills"),
    ("topic",   "topic:agent-skills",           "Topic: agent-skills"),
    ("awesome", "awesome claude skills",        "Awesome-list family (claude)"),
    ("awesome", "awesome agent skills",         "Awesome-list family (agent)"),
    ("readme",  "claude skills in:readme",      "READMEs documenting claude skills"),
    ("readme",  "agent skills in:readme",       "READMEs documenting agent skills"),
    ("readme",  "SKILL.md in:readme",           "READMEs documenting SKILL.md"),
]

CODE_QUERY = "filename:SKILL.md"  # code search: repos that actually ship SKILL.md files
CODE_MAX_ADD = 30                 # cap on code-search-only additions to the pool

FORCE_INCLUDE = ["anthropics/skills"]  # canonical repo, always evaluate

# ---------------------------------------------------------------------------
# Scoring model — weights sum to 100; used only to RANK candidates.
#   popularity 25 | recency 20 | license 15 | structure 20 | tests 10 | provenance 10
# Gates (pass/fail) decide admission; score never overrides a gate.
# ---------------------------------------------------------------------------

PERMISSIVE = {"mit", "apache-2.0"}
OSI_OTHER = {
    "bsd-2-clause", "bsd-3-clause", "bsd-3-clause-clear", "isc", "mpl-2.0",
    "gpl-2.0", "gpl-3.0", "lgpl-2.1", "lgpl-3.0", "agpl-3.0",
    "cc0-1.0", "unlicense", "0bsd", "wtfpl",
}


def band(v, bands):
    for lo, pts in bands:
        if v >= lo:
            return pts
    return 0


def score_popularity(stars, forks):
    s = band(stars, [(2000, 15), (500, 12), (100, 9), (20, 6), (1, 3)])
    f = band(forks, [(200, 10), (50, 7), (10, 4), (1, 2)])
    return s + f


def score_recency(pushed_at):
    days = (dt.datetime.now(dt.timezone.utc) -
            dt.datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))).days
    if days < 30:
        return 20, days
    if days < 90:
        return 16, days
    if days < 180:
        return 12, days
    if days < 365:
        return 8, days
    if days < 730:
        return 4, days
    return 0, days


def score_license(license_obj):
    if not license_obj:
        return 0, "none"
    key = (license_obj.get("spdx_id") or "").lower()
    if key in PERMISSIVE:
        return 15, key
    if key in OSI_OTHER:
        return 10, key
    if key in ("", "other", "no-license"):
        return 0, "none"
    return 4, key


def analyze_tree(tree):
    paths = [t.get("path", "") for t in tree.get("tree", [])]
    skill_paths = [p for p in paths if p.lower().endswith("skill.md")]
    test_re = re.compile(
        r"(^|/)(tests?|specs?)(/|$)|(_test\.py$|^test_.*\.py$|\.test\.[a-z]+$|"
        r"\.spec\.[a-z]+$|pytest\.ini$|jest\.config|vitest\.config|"
        r"\.github/workflows/.*test)", re.I)
    has_tests = any(test_re.search(p) for p in paths)
    has_ci = any(
        p.startswith(".github/workflows/") or p.startswith(".gitlab-ci")
        or p == ".travis.yml" for p in paths)
    # Credential-pattern filenames. Exclusions:
    #  - vendor/|node_modules/|dist/|... (dependency code, not the repo's payload)
    #  - .env.example/.env.sample/.env.template (committed templates are NOT leaks)
    risky_re = re.compile(
        r"(^|/)(\.env(\.|$)|\.env\.[a-z0-9]+$|id_rsa(\.pub)?$|.*\.pem$|.*\.p12$|"
        r"(^|/)credentials\.json$|service-account[^/]*\.json$|"
        r"(^|/)tokens?\.json$|(^|/)api[_-]?keys?\.(json|txt|env)$|"
        r"(^|/)secret[^/]*\.(json|txt|env)$)", re.I)
    safe_env = re.compile(r"\.env\.(example|sample|template|dist|example\.local|local\.example)$", re.I)
    dep_prefixes = ("vendor/", "node_modules/", ".venv/", "venv/", "third_party/",
                    "third-party/", "dist/", "build/", "target/", ".git/")
    risky = [p for p in paths if risky_re.search(p)
             and not safe_env.search(p)
             and not p.lower().startswith(dep_prefixes)]
    return skill_paths, has_tests, has_ci, risky, tree.get("truncated", False)


def frontmatter_status(md_text):
    if not md_text or not md_text.startswith("---"):
        return "missing"
    m = re.match(r"^---\s*\n(.*?)\n---", md_text, re.S)
    if not m:
        return "unparseable"
    fm = m.group(1)
    name = re.search(r"^name\s*:\s*\S", fm, re.M)
    desc = re.search(r"^description\s*:", fm, re.M)
    if name and desc:
        return "full"
    if name or desc:
        return "partial"
    return "bare"


def score_structure(skill_paths, fm_status):
    if not skill_paths:
        return 0, "no SKILL.md in tree"
    base = 10
    extra = {"full": 6, "partial": 3}.get(fm_status, 0)
    if len(skill_paths) >= 3:  # collection -> many hostable candidates
        extra += 4
    return min(20, base + extra), f"{len(skill_paths)} SKILL.md, fm={fm_status}"


def score_tests(has_tests, has_ci):
    if has_tests:
        return 10, "tests found"
    if has_ci:
        return 5, "CI only, no test files"
    return 0, "no tests/CI"


def score_provenance(owner_type, followers):
    if owner_type == "Organization":
        return 10, "org-owned"
    f = followers or 0
    return band(f, [(500, 8), (100, 6), (20, 4)]), f"user, {f} followers"


# ---------------------------------------------------------------------------
# gh plumbing
# ---------------------------------------------------------------------------

def gh_json(args, timeout=90):
    cmd = ["gh", "api", "-X", "GET"] + args
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"gh api failed: {' '.join(cmd)}\n{p.stderr[:400]}")
    return json.loads(p.stdout)


def search_repos(q, per_page=25, retries=2):
    for attempt in range(retries + 1):
        try:
            return gh_json(["search/repositories", "-f", f"q={q}",
                            "-f", "sort=stars", "-f", "order=desc",
                            "-f", f"per_page={per_page}"])["items"]
        except RuntimeError as e:
            if "rate limit" in str(e).lower() and attempt < retries:
                sys.stderr.write("  search rate limit hit; sleeping 60s\n")
                time.sleep(60)
                continue
            raise


def search_code(q, per_page=100, retries=2):
    for attempt in range(retries + 1):
        try:
            return gh_json(["search/code", "-f", f"q={q}",
                            "-f", f"per_page={per_page}"])["items"]
        except RuntimeError as e:
            if "rate limit" in str(e).lower() and attempt < retries:
                sys.stderr.write("  code-search rate limit hit; sleeping 60s\n")
                time.sleep(60)
                continue
            raise


def fetch_tree(full_name, branch, retries=3):
    """Recursive tree with branch fallbacks and retry-on-any-error (transient
    API hiccups must not silently zero a candidate's structure gate)."""
    for b in [branch, "HEAD", "master"]:
        for attempt in range(retries + 1):
            try:
                tree = gh_json([f"repos/{full_name}/git/trees/{b}?recursive=1"])
                return tree, b
            except RuntimeError as e:
                msg = str(e)
                if "404" in msg:
                    break  # branch doesn't exist; try next
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                sys.stderr.write(f"  [warn] tree {full_name}@{b} failed: {msg[:120]}\n")
    return None, None


def raw_fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "omo-skill-scout"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")[:4000]
    except Exception:
        return None


def classify_relevance(description, readme=""):
    blob = " ".join(x for x in [description or "", readme or ""] if x)
    if re.search(r"\bskill", blob, re.I):
        return "skills-focused", "description/README mentions skills"
    if re.search(r"\b(agent|claude|copilot|prompt|workflow)\b", blob, re.I):
        return "adjacent", "mentions agent/claude/prompt tooling, not skills per se"
    return "unclear", "no skill signal in description/README"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/github-skill-scout/results.json")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--max-pool", type=int, default=70)
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    pool = {}       # full_name -> merged repo dict
    sources = {}    # full_name -> set of source labels
    query_stats = []

    print("== GitHub skill-scout: discovery ==")
    for label, q, desc in REPO_QUERIES:
        try:
            items = search_repos(q)
        except RuntimeError as e:
            print(f"  [FAIL] {q}: {str(e)[:200]}")
            query_stats.append({"query": q, "status": "error", "total": None})
            continue
        query_stats.append({"query": q, "status": "ok",
                            "total": len(items), "source": label})
        print(f"  {label:8} {q!r:42} -> {len(items)} results")
        for it in items:
            fn = it["full_name"]
            if fn not in pool or it["stargazers_count"] > pool[fn].get("stargazers_count", 0):
                pool[fn] = it
            sources.setdefault(fn, set()).add(label)
        time.sleep(SEARCH_SLEEP)

    try:
        hits = search_code(CODE_QUERY)
        print(f"  code     {CODE_QUERY!r:42} -> {len(hits)} SKILL.md file hits")
        added = 0
        for h in hits:
            repo = h.get("repository") or {}
            fn = repo.get("full_name")
            if not fn:
                continue
            sources.setdefault(fn, set()).add("code-search")
            if fn not in pool:
                if added >= CODE_MAX_ADD:
                    continue
                pool[fn] = {"full_name": fn, "code_search_hit": True,
                            "skill_file_path": h.get("path")}
                added += 1
    except RuntimeError as e:
        print(f"  [FAIL] code search: {str(e)[:200]}")

    for fn in FORCE_INCLUDE:
        pool.setdefault(fn, {"full_name": fn, "force_include": True})
        sources.setdefault(fn, set()).add("canonical")

    # Enrich code-search-only / forced entries with full repo data
    print("== Enrichment ==")
    for fn in list(pool):
        r = pool[fn]
        if r.get("code_search_hit") or r.get("force_include") or "stargazers_count" not in r:
            try:
                pool[fn] = gh_json([f"repos/{fn}"])
            except RuntimeError as e:
                print(f"  [drop] {fn}: {str(e)[:150]}")
                del pool[fn]

    # Cap pool by stars (bound the run; full-list coverage noted in doc)
    ranked = sorted(pool.items(), key=lambda kv: kv[1].get("stargazers_count", 0),
                    reverse=True)
    if len(ranked) > args.max_pool:
        ranked = ranked[:args.max_pool]
        print(f"  (pool capped at {args.max_pool} by stars)")

    print("== Scoring + gates ==")
    out = []
    for fn, r in ranked:
        default_branch = r.get("default_branch", "main")
        skill_paths, has_tests, has_ci, risky, truncated = [], False, False, [], False
        tree, branch_used = fetch_tree(fn, default_branch)
        if tree is not None:
            skill_paths, has_tests, has_ci, risky, truncated = analyze_tree(tree)
        time.sleep(0.2)

        fm_status = "unknown"
        if skill_paths:
            best = next((p for p in skill_paths if p.lower() == "skill.md"),
                        next((p for p in skill_paths if p.lower() == "skills/skill.md"),
                             skill_paths[0]))
            text = raw_fetch(
                f"https://raw.githubusercontent.com/{fn}/{branch_used or 'HEAD'}/{best}")
            fm_status = frontmatter_status(text)

        owner = r.get("owner") or {}
        followers = None
        if owner.get("type") != "Organization" and owner.get("login"):
            try:
                followers = gh_json([f"users/{owner['login']}"]).get("followers")
            except RuntimeError:
                pass
            time.sleep(0.2)

        stars = r.get("stargazers_count", 0)
        forks = r.get("forks_count", 0)
        pushed = r.get("pushed_at") or r.get("updated_at") or ""
        created = r.get("created_at") or pushed

        pop_pts = score_popularity(stars, forks)
        rec_pts, days = score_recency(pushed)
        lic_pts, lic_key = score_license(r.get("license"))
        str_pts, str_reason = score_structure(skill_paths, fm_status)
        tst_pts, tst_reason = score_tests(has_tests, has_ci)
        prv_pts, prv_reason = score_provenance(owner.get("type"), followers)

        # ---- star-quality / provenance flags (stars are a first filter only) ----
        age_days = max(1, (now - dt.datetime.fromisoformat(
            created.replace("Z", "+00:00"))).days)
        velocity = stars / age_days
        star_flags = []
        if stars >= 30000 and age_days < 730 and velocity >= 150:
            star_flags.append(f"high-star-velocity (~{velocity:.0f}/day, repo {age_days}d old)")
        if stars >= 10000 and lic_key in ("none",):
            star_flags.append("stars-without-license")
        if stars >= 5000 and forks == 0:
            star_flags.append("stars-without-forks")
        # user-owned repo whose stars vastly exceed the author's reach = boost/star-farm suspect
        if owner.get("type") != "Organization":
            reach = (followers or 0)
            if stars >= 10000 and 0 < reach < 2000 and stars / reach >= 25:
                star_flags.append(
                    f"stars-exceed-author-reach ({stars // max(1, reach)}x author's {reach} followers)")
            elif stars >= 10000 and reach == 0:
                star_flags.append("stars-without-author-reach (author has 0 followers)")
        if star_flags:
            star_flags.append("stars are a first filter only — provenance MUST be vetted")

        # ---- relevance (skills-focused / adjacent / unclear) from description + README ----
        readme_text = raw_fetch(
            f"https://raw.githubusercontent.com/{fn}/{branch_used or 'HEAD'}/README.md")
        relevance, relevance_note = classify_relevance(r.get("description"), readme_text)
        repo_name = fn.split("/")[-1]
        is_awesome = bool(
            re.match(r"^awesome", repo_name, re.I)
            or re.search(r"curated list of awesome|awesome lists? (about|for|of)",
                         (r.get("description") or "") + " " + (readme_text or "")[:1500], re.I))

        signals = {
            "popularity": {"points": pop_pts, "stars": stars, "forks": forks},
            "recency": {"points": rec_pts, "pushed_days_ago": days},
            "license": {"points": lic_pts, "spdx": lic_key},
            "structure": {"points": str_pts, "detail": str_reason,
                          "skill_md_count": len(skill_paths),
                          "truncated_tree": truncated,
                          "tree_fetch_ok": tree is not None},
            "tests": {"points": tst_pts, "detail": tst_reason},
            "provenance": {"points": prv_pts, "detail": prv_reason},
            "relevance": {"verdict": relevance, "note": relevance_note},
            "is_awesome_list": is_awesome,
            "star_flags": star_flags,
            "secret_risk_files": risky,
            "created_at": created,
        }

        # ---- hard gates (reject-by-default: must pass EVERY gate) ----
        gates = {}
        if lic_key in PERMISSIVE:
            gates["license"] = {"pass": True, "reason": f"permissive ({lic_key}) — hostable"}
        elif lic_key in OSI_OTHER:
            gates["license"] = {"pass": True,
                                "reason": f"OSI but copyleft-ish ({lic_key}) — vet redistribution terms"}
        else:
            gates["license"] = {"pass": False,
                                "reason": "no verified license (or non-OSI) — cannot verify redistribution rights; reject unless upstream grants explicit permission"}

        if skill_paths:
            gates["structure"] = {"pass": True,
                                  "reason": f"{len(skill_paths)} SKILL.md file(s) in tree"}
        else:
            gates["structure"] = {"pass": False,
                                  "reason": ("no SKILL.md found in tree"
                                             + ("" if tree is not None else " (tree could not be fetched)"))}

        if risky:
            gates["secret"] = {"pass": False,
                               "reason": f"credential-pattern filenames in tree: {risky[:5]}"}
        else:
            gates["secret"] = {"pass": True, "reason": "no credential-pattern filenames in tree (content scan still required at vet)"}

        if tree is None:
            gates["tree"] = {"pass": False, "reason": "tree fetch failed — cannot verify contents"}
        elif truncated:
            gates["tree"] = {"pass": False, "reason": "tree truncated by API — cannot fully verify contents"}
        else:
            gates["tree"] = {"pass": True, "reason": "full tree fetched"}

        hard_fail = [k for k, v in gates.items() if not v["pass"]]

        soft_flags = []
        if relevance != "skills-focused":
            soft_flags.append(f"relevance:{relevance} — vet must confirm this is a skills repo, else reject")
        if is_awesome:
            soft_flags.append("awesome-list/directory (curated list of links, not a hostable skill) — categorize at vet, do not host as-is")
        if star_flags:
            soft_flags.append("provenance: " + "; ".join(star_flags))

        score = pop_pts + rec_pts + lic_pts + str_pts + tst_pts + prv_pts
        if risky:
            score = max(0, score - 15)

        if hard_fail:
            tier = "REJECT"
            tier_reason = "hard-gate failure: " + ", ".join(
                f"{k} ({gates[k]['reason']})" for k in hard_fail)
        elif score >= 65 and not soft_flags:
            tier = "BUILDER_TEST"
            tier_reason = "all gates pass, score >= 65, no soft flags — next step is the vet sequence"
        elif score >= 50:
            tier = "VET"
            tier_reason = "all hard gates pass; score below 65 or soft flags need vet review first: " + "; ".join(soft_flags)
        else:
            tier = "REJECT"
            tier_reason = "score below 50 despite passing gates — not worth vet bandwidth"

        reason = (f"{stars}★ {forks}⑂ pushed {days}d ago | {lic_key} | "
                  f"{str_reason} | {tst_reason} | {prv_reason} | {relevance_note}"
                  + (f" | SECRET-FLAG: {risky[:3]}" if risky else ""))

        out.append({
            "slug": fn.lower().replace("/", "-"),
            "repo": fn,
            "html_url": r.get("html_url", f"https://github.com/{fn}"),
            "description": (r.get("description") or "")[:200],
            "stars": stars,
            "forks": forks,
            "license": lic_key,
            "created_at": created,
            "updated_at": r.get("pushed_at") or r.get("updated_at"),
            "score": score,
            "tier": tier,
            "tier_reason": tier_reason,
            "reason": reason,
            "signals": signals,
            "gates": gates,
            "sources": sorted(sources.get(fn, [])),
        })

    tier_order = {"BUILDER_TEST": 0, "VET": 1, "REJECT": 2}
    out.sort(key=lambda c: (tier_order.get(c["tier"], 3), -c["score"]))

    # debug: locate anthropics/skills in the full sorted list
    for i, c in enumerate(out):
        if c["repo"] == "anthropics/skills":
            print(f"  [dbg] anthropics/skills at index {i}: score={c['score']} "
                  f"tier={c['tier']} gates={json.dumps(c['gates'])}")
    all_scored = list(out)
    top = out[:args.limit]

    rl = {}
    try:
        rl = gh_json(["rate_limit"])
    except RuntimeError:
        pass
    rate_info = {
        "search": rl.get("resources", {}).get("search", {}),
        "core": rl.get("resources", {}).get("core", {}),
    }

    result = {
        "generated_at": now.isoformat(),
        "scoring_model": "research/GITHUB-SKILL-SOURCING.MD (weights: popularity 25, recency 20, license 15, structure 20, tests 10, provenance 10; secret penalty -15; hard gates decide admission)",
        "queries": [qs for qs in query_stats if qs["status"] == "ok"],
        "query_errors": [qs for qs in query_stats if qs["status"] == "error"],
        "code_query": CODE_QUERY,
        "pool_size": len(ranked),
        "rate_limit_remaining": rate_info,
        "candidates": top,
        "all_scored": all_scored,
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n== Candidates ({len(top)} of {len(ranked)} pooled) ==")
    print(f"{'score':>5}  {'tier':<12} {'stars':>7} {'lic':<11}  repo")
    for c in top:
        print(f"{c['score']:>5}  {c['tier']:<12} {c['stars']:>7} {c['license']:<11}  {c['repo']}")
    rej = [c for c in top if c["tier"] == "REJECT"]
    print(f"\nREJECTED: {len(rej)}/{len(top)} (reasons recorded per candidate in results.json)")
    print(f"\nresults -> {args.out}")
    print(f"search remaining: {rate_info.get('search', {}).get('remaining')}/30/min, "
          f"core remaining: {rate_info.get('core', {}).get('remaining')}/5000/hr")


if __name__ == "__main__":
    main()
