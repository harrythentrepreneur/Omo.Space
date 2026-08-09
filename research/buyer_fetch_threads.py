#!/usr/bin/env python3
"""Bench — buyer-side thread fetcher.
Fetches old.reddit.com thread HTML at a safe ~75s cadence, parses post +
comments, extracts verbatim quotes, and appends to research/reddit-buyer-side.md.
Checkpointed: skips already-fetched thread IDs.

Usage: python3 research/buyer_fetch_threads.py
"""
import json, os, re, subprocess, time, html

BASE = '/Users/yifan/marketplace/research'
CHECKPOINT = '/tmp/buyer_threads.json'

# (thread_id, sub, title_fragment, why)
THREADS = [
    ('1tksu4c', 'automation', 'cost per month to run an automation for a client',
     'creator economics: what hosting/running actually costs clients'),
    ('1syx57h', 'automation', 'charging 500 dollars a month for a tool that renames files',
     'creator economics: pricing a simple automation'),
    ('1sqfktl', 'nocode', 'Does asking for an API key kill your conversion',
     'buyer friction: API-key fear in no-code tools'),
    ('16cmk3h', 'ecommerce', 'What AI tools are you using in your business',
     'buyer demand: ecom owners using AI tools'),
    ('1uipyf2', 'smallbusiness', 'What business task do you still copy/paste',
     'buyer pain: manual workflows in small business'),
    ('1n94lno', 'Entrepreneur', 'Tried a bunch of AI tools for my business',
     'buyer pain: AI tool trial fatigue'),
    ('1lvjomi', 'ClaudeAI', 'Getting CC to install dependencies',
     'buyer friction: setup/install pain'),
    ('1smvx6v', 'automation', 'What automations actually make money',
     'creator economics: what clients pay for'),
]

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'

def load_cp():
    if os.path.exists(CHECKPOINT):
        return json.load(open(CHECKPOINT))
    return {}

def save_cp(cp):
    json.dump(cp, open(CHECKPOINT, 'w'), indent=1)

def fetch(url):
    r = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '60', url],
                       capture_output=True, text=True)
    return r.stdout

def parse_thread(page):
    """Extract post + comments from old.reddit HTML.
    Pattern (validated by subagent): BeautifulSoup div.entry > div.md for bodies,
    a.author for authors, span.score for scores."""
    from bs4 import BeautifulSoup
    out = {'post': None, 'comments': []}
    soup = BeautifulSoup(page, 'html.parser')
    tm = soup.find('title')
    out['title'] = html.unescape(tm.get_text()).strip() if tm else ''

    # post body: first div.md that is a sibling of the title (inside the first entry)
    entries = soup.select('div.entry')
    if entries:
        first_md = entries[0].select_one('div.md')
        if first_md:
            out['post'] = re.sub(r'\s+', ' ', first_md.get_text(' ', strip=True))[:3000]

    # comments: every div.entry with an author link and a div.md
    seen = set()
    for entry in entries:
        author_el = entry.select_one('a.author')
        body_el = entry.select_one('div.md')
        if not author_el or not body_el:
            continue
        author = html.unescape(author_el.get_text(strip=True))
        text = re.sub(r'\s+', ' ', body_el.get_text(' ', strip=True)).strip()
        if len(text) < 15:
            continue
        key = (author, text[:80])
        if key in seen:
            continue
        seen.add(key)
        score_el = entry.select_one('span.score')
        score = score_el.get_text(strip=True) if score_el else '?'
        out['comments'].append({'author': author, 'score': score, 'text': text[:1200]})
    return out

def main():
    cp = load_cp()
    collected = []
    for tid, sub, frag, why in THREADS:
        if tid in cp:
            print(f'skip {tid} (already done)')
            collected.append(cp[tid])
            continue
        url = f'https://old.reddit.com/r/{sub}/comments/{tid}/'
        print(f'fetch {tid} ({sub}) ...', flush=True)
        try:
            h = fetch(url)
            if len(h) < 5000:
                print(f'  WARN short response {len(h)}b — sleeping and retrying once', flush=True)
                time.sleep(75)
                h = fetch(url)
            parsed = parse_thread(h)
            parsed['id'] = tid
            parsed['sub'] = sub
            parsed['url'] = url
            parsed['why'] = why
            cp[tid] = parsed
            save_cp(cp)
            collected.append(parsed)
            n = len(parsed.get('comments', []))
            print(f'  ok: {n} comments, post={len(parsed.get("post") or "")} chars', flush=True)
        except Exception as e:
            print(f'  ERROR {e}', flush=True)
        time.sleep(75)  # reddit throttle

    # write markdown sections
    md_path = os.path.join(BASE, 'reddit-buyer-side.md')
    with open(md_path) as f:
        md = f.read()

    sections = []
    for p in collected:
        lines = [f"### r/{p['sub']} — {p.get('title','')[:90]}", f"URL: {p['url']}"]
        if p.get('post'):
            lines.append(f"Post: {p['post'][:600]}")
        for c in p.get('comments', [])[:10]:
            lines.append(f"- u/{c['author']} ({c['score']}): \"{c['text'][:400]}\"")
        sections.append('\n'.join(lines))

    if sections:
        new_block = '\n\n---\n\n## Thread deep-dives (fetched 2026-08-08)\n\n' + '\n\n'.join(sections)
        # insert before the '## Top 5 insights' if present else append
        marker = '## Top 5 insights for Bench'
        if marker in md:
            md = md.replace(marker, new_block + '\n\n' + marker)
        else:
            md = md.rstrip() + '\n' + new_block + '\n'
        with open(md_path, 'w') as f:
            f.write(md)
        print(f'\nWROTE {len(sections)} thread sections to {md_path}')

if __name__ == '__main__':
    main()
