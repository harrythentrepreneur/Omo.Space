#!/usr/bin/env python3
"""Stage 1: RSS-search discovery for SEO-strategy + skill-sourcing research.
One request per ~75s (quota=1/window verified 2026-08-16). curl subprocess only.
Checkpointed at /tmp/seo_skills_rss.json. Resumable.
"""
import json, os, re, subprocess, time, html
import xml.etree.ElementTree as ET

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'
NS = {'a': 'http://www.w3.org/2005/Atom'}
OUT = '/tmp/seo_skills_rss.json'
SLEEP = 75

# (subreddit, query, lane)  lane: seo | skills
QUERIES = [
    # ---- Deliverable 1: AI/SEO strategy (lanes: programmatic, AIO, entity/EEAT, links, thin, reddit-rise)
    ('SEO', '"programmatic SEO"', 'seo'),
    ('SEO', '"AI Overviews"', 'seo'),
    ('SEO', '"E-E-A-T"', 'seo'),
    ('SEO', '"thin content"', 'seo'),
    ('SEO', '"internal linking"', 'seo'),
    ('SEO', '"AI search"', 'seo'),
    ('juststart', '"programmatic SEO"', 'seo'),
    ('juststart', '"AI Overviews"', 'seo'),
    ('juststart', '"Reddit SEO"', 'seo'),
    ('seogrowth', '"programmatic SEO"', 'seo'),
    ('seogrowth', '"AI Overviews"', 'seo'),
    ('TechSEO', '"AI Overviews"', 'seo'),
    ('TechSEO', 'LLM crawl', 'seo'),
    ('ChatGPT', '"AI Overviews"', 'seo'),
    ('artificial', '"AI search"', 'seo'),
    # ---- Deliverable 2: skill.md sourcing
    ('ClaudeAI', 'SKILL.md', 'skills'),
    ('ClaudeAI', '"Claude skills"', 'skills'),
    ('ClaudeAI', '"agent skills"', 'skills'),
    ('ChatGPTCoding', 'SKILL.md', 'skills'),
    ('ChatGPTCoding', '"GPT skills"', 'skills'),
    ('AI_Agents', 'SKILL.md', 'skills'),
    ('AI_Agents', '"agent skills"', 'skills'),
    ('AI_Agents', '"skills marketplace"', 'skills'),
    ('LLMDevs', 'SKILL.md', 'skills'),
    ('LLMDevs', '"agent skills"', 'skills'),
    ('SomebodyMakeThis', '"AI agent"', 'skills'),
    ('SomebodyMakeThis', '"agent skills"', 'skills'),
    ('OpenAI', 'SKILL.md', 'skills'),
    ('artificial', 'SKILL.md', 'skills'),
]

def load():
    if os.path.exists(OUT):
        return json.load(open(OUT))
    return {}

def fetch_one(sub, phrase):
    url = 'https://old.reddit.com/r/%s/search.rss' % sub
    q = phrase.replace(' ', '+').replace('"', '%22')
    u = '%s?q=%s&restrict_sr=1&limit=25&sort=relevance' % (url, q)
    r = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '40', '-D', '/tmp/rss_headers.txt', u],
                       capture_output=True, text=True)
    body = r.stdout
    headers = {}
    try:
        for line in open('/tmp/rss_headers.txt'):
            if ':' in line:
                k, v = line.split(':', 1)
                headers[k.strip().lower()] = v.strip()
    except Exception:
        pass
    entries = []
    if body.strip().startswith('<?xml') or '<entry>' in body:
        try:
            root = ET.fromstring(body)
            for e in root.findall('a:entry', NS):
                t = e.find('a:title', NS)
                l = e.find('a:link', NS)
                pid = e.find('a:id', NS)
                pub = e.find('a:published', NS)
                auth = e.find('a:author/a:name', NS)
                cont = e.find('a:content', NS)
                snippet = ''
                if cont is not None and cont.text:
                    snippet = re.sub(r'<[^>]+>', ' ', cont.text)
                    snippet = html.unescape(re.sub(r'\s+', ' ', snippet)).strip()[:500]
                entries.append({
                    'title': t.text if t is not None else '',
                    'url': l.attrib.get('href', '') if l is not None else '',
                    'id': pid.text if pid is not None else '',
                    'published': pub.text if pub is not None else '',
                    'author': auth.text if auth is not None else '',
                    'snippet': snippet,
                })
        except ET.ParseError:
            pass
    return body, headers, entries

def run_pass(results, pending):
    for sub, phrase, lane in pending:
        key = '%s::%s' % (sub, phrase)
        body, headers, entries = fetch_one(sub, phrase)
        status = 429
        m = re.search(r'HTTP/\S+\s+(\d+)', open('/tmp/rss_headers.txt').read() if os.path.exists('/tmp/rss_headers.txt') else '')
        if m:
            status = int(m.group(1))
        if not entries and status == 200 and len(body) < 500:
            status = 429  # empty body = rate-limited
        results[key] = {'status': status, 'sub': sub, 'phrase': phrase, 'lane': lane,
                        'entries': entries, 'reset': headers.get('x-ratelimit-reset', '')}
        json.dump(results, open(OUT, 'w'), ensure_ascii=False, indent=1)
        print('%s::%s -> %s entries=%d' % (sub, phrase, status, len(entries)), flush=True)
        # wait for quota reset if we got throttled
        wait = SLEEP
        if status == 429:
            try:
                wait = int(headers.get('x-ratelimit-reset', '60')) + 5
            except ValueError:
                wait = 80
        time.sleep(wait)

results = load()
pending = [(s, p, l) for (s, p, l) in QUERIES
           if '%s::%s' % (s, p) not in results or results.get('%s::%s' % (s, p), {}).get('status') != 200]
print('Pending: %d/%d' % (len(pending), len(QUERIES)), flush=True)
run_pass(results, pending)
failed = [(s, p, l) for (s, p, l) in QUERIES if results.get('%s::%s' % (s, p), {}).get('status') != 200]
for attempt in range(3):
    if not failed:
        break
    print('Retry pass %d: %d failed' % (attempt + 1, len(failed)), flush=True)
    time.sleep(95)
    run_pass(results, failed)
    failed = [(s, p, l) for (s, p, l) in QUERIES if results.get('%s::%s' % (s, p), {}).get('status') != 200]
print('DONE rss_stage1', flush=True)
