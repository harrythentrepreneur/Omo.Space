#!/usr/bin/env python3
"""Stage 2: fetch full old.reddit threads for SEO + skills research.
~75s cadence (quota 1/window, verified 2026-08-16). Checkpointed + resumable.
Writes parsed threads to /tmp/seo_skills_threads.json and verbatim quote blocks
to /tmp/seo_skills_quotes.md as it goes.

Usage: python3 research/seo_skills_fetch_threads.py
"""
import json, os, re, subprocess, time, html, sys

BASE = '/Users/yifan/marketplace/research'
CHECKPOINT = '/tmp/seo_skills_threads.json'
QUOTES_MD = '/tmp/seo_skills_quotes.md'
THREADS_JSON = '/tmp/seo_skills_threads_curated.json'  # list of {id, sub, title, lane, why}

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'

def load_cp():
    if os.path.exists(CHECKPOINT):
        return json.load(open(CHECKPOINT))
    return {}

def save_cp(cp):
    json.dump(cp, open(CHECKPOINT, 'w'), indent=1)

def fetch(url):
    r = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '60', '-D', '/tmp/fetch_headers.txt', url],
                       capture_output=True, text=True)
    return r.stdout

def parse_thread(page, tid):
    from bs4 import BeautifulSoup
    out = {'id': tid, 'post': None, 'comments': [], 'post_author': '', 'post_score': '',
           'post_date': '', 'comment_count': 0}
    soup = BeautifulSoup(page, 'html.parser')
    tm = soup.find('title')
    out['title'] = html.unescape(tm.get_text()).strip() if tm else ''
    entries = soup.select('div.entry')
    if entries:
        first = entries[0]
        md = first.select_one('div.md')
        if md:
            out['post'] = re.sub(r'\s+', ' ', md.get_text(' ', strip=True))[:4000]
        a = first.select_one('a.author')
        if a:
            out['post_author'] = html.unescape(a.get_text(strip=True))
        score_el = first.select_one('span.score')
        if score_el:
            out['post_score'] = score_el.get_text(strip=True)
        # post date from time tag
        tm2 = first.select_one('time')
        if tm2:
            out['post_date'] = tm2.get('title', '') or tm2.get('datetime', '')
    seen = set()
    for entry in entries:
        author_el = entry.select_one('a.author')
        body_el = entry.select_one('div.md')
        if not author_el or not body_el:
            continue
        author = html.unescape(author_el.get_text(strip=True))
        if author in ('AutoModerator',):
            continue
        text = re.sub(r'\s+', ' ', body_el.get_text(' ', strip=True)).strip()
        if len(text) < 15:
            continue
        key = (author, text[:80])
        if key in seen:
            continue
        seen.add(key)
        score_el = entry.select_one('span.score')
        score = score_el.get_text(strip=True) if score_el else '?'
        # relative date like "2 years ago" or absolute
        rel = ''
        t = entry.select_one('time')
        if t:
            rel = t.get('datetime', '') or t.get_text(strip=True)
        out['comments'].append({'author': author, 'score': score, 'date_rel': rel[:40], 'text': text[:1500]})
    out['comment_count'] = len(out['comments'])
    return out

def main():
    if not os.path.exists(THREADS_JSON):
        print('no curated threads file at %s' % THREADS_JSON, flush=True)
        sys.exit(1)
    threads = json.load(open(THREADS_JSON))
    cp = load_cp()
    done_ids = [tid for tid, v in cp.items() if v.get('ok')]
    remaining = [t for t in threads if t['id'] not in done_ids]
    print('remaining to fetch: %d' % len(remaining), flush=True)
    new_sections = []
    for t in remaining:
        tid, sub = t['id'], t['sub']
        url = 'https://old.reddit.com/r/%s/comments/%s/' % (sub, tid)
        print('fetch %s (r/%s, %s) ...' % (tid, sub, t.get('lane', '')), flush=True)
        try:
            h = fetch(url)
            if len(h) < 5000:
                print('  WARN short %db — retry after 80s' % len(h), flush=True)
                time.sleep(80)
                h = fetch(url)
            parsed = parse_thread(h, tid)
            parsed['sub'] = sub
            parsed['url'] = url
            parsed['lane'] = t.get('lane', '')
            parsed['why'] = t.get('why', '')
            parsed['ok'] = len(h) > 5000
            cp[tid] = parsed
            save_cp(cp)
            print('  ok: post=%s chars, %d comments' % (len(parsed.get('post') or ''), parsed['comment_count']), flush=True)
            if parsed['ok'] and parsed.get('title'):
                new_sections.append(parsed)
        except Exception as e:
            print('  ERROR %s' % e, flush=True)
        time.sleep(75)

    if new_sections:
        with open(QUOTES_MD, 'a') as f:
            f.write('\n\n---\n\n')
            for p in new_sections:
                f.write('### r/%s — %s\n' % (p['sub'], p.get('title', '')[:100]))
                f.write('URL: %s | posted: %s | post score: %s | comments: %d\n' % (
                    p['url'], p.get('post_date', '?'), p.get('post_score', '?'), p['comment_count']))
                if p.get('post'):
                    f.write('POST: "%s"\n' % p['post'][:800])
                for c in p.get('comments', [])[:12]:
                    f.write('- u/%s (%s, %s): "%s"\n' % (c['author'], c['score'], c['date_rel'], c['text'][:500]))
        print('\nappended %d thread sections to %s' % (len(new_sections), QUOTES_MD), flush=True)

if __name__ == '__main__':
    main()
