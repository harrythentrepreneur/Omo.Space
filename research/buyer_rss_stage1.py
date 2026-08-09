#!/usr/bin/env python3
"""Stage 1: RSS-search buyer-side phrases. One request per 75s, retry 429s at the end. Checkpointed."""
import requests, json, time, xml.etree.ElementTree as ET, os

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'
NS = {'a': 'http://www.w3.org/2005/Atom'}
OUT = '/tmp/buyer_rss.json'
SLEEP = 75

QUERIES = [
    ('ClaudeAI', '"clone the repo"'), ('ClaudeAI', '"install dependencies"'),
    ('ClaudeAI', '"API key" setup'), ('ClaudeAI', '"too complicated"'),
    ('ClaudeAI', '"just want to use it"'), ('ClaudeAI', '"run locally"'),
    ('ChatGPT', '"clone the repo"'), ('ChatGPT', '"API key" setup'),
    ('ChatGPT', '"just want to use it"'), ('ChatGPT', '"pay per use"'),
    ('ChatGPT', 'scared of API costs'), ('nocode', '"API key"'),
    ('nocode', '"AI tool for my business"'), ('nocode', 'AI workflow "without coding"'),
    ('smallbusiness', '"AI tool for my business"'), ('smallbusiness', '"pay per use"'),
    ('smallbusiness', 'automation "too complicated"'), ('Entrepreneur', '"AI tool for my business"'),
    ('Entrepreneur', '"pay per use" AI'), ('ecommerce', '"AI tool" business'),
    ('automation', '"deploy AI workflow"'), ('automation', '"API costs"'),
    ('ArtificialInteligence', '"clone the repo"'), ('LocalLLaMA', '"too complicated"'),
    ('selfhosted', '"just want to use it"'), ('AI_Agents', '"deploy AI workflow"'),
    ('AI_Agents', '"API key" setup'), ('AI_Agents', 'setup "gave up"'),
]

def load():
    if os.path.exists(OUT):
        return json.load(open(OUT))
    return {}

def fetch_one(sub, phrase):
    url = f'https://old.reddit.com/r/{sub}/search.rss'
    params = {'q': phrase, 'restrict_sr': '1', 'limit': '25', 'sort': 'relevance'}
    try:
        r = requests.get(url, params=params, headers={'User-Agent': UA}, timeout=30)
        entries = []
        if r.status_code == 200 and r.text.strip().startswith('<?xml'):
            root = ET.fromstring(r.text)
            for e in root.findall('a:entry', NS):
                t = e.find('a:title', NS); l = e.find('a:link', NS)
                if t is not None and l is not None:
                    entries.append({'title': t.text, 'url': l.attrib.get('href', '')})
        return r.status_code, entries
    except Exception as ex:
        return 0, []

def run_pass(results, pending):
    for sub, phrase in pending:
        code, entries = fetch_one(sub, phrase)
        results[f'{sub}::{phrase}'] = {'status': code, 'entries': entries}
        print(f'{sub} :: {phrase} -> {code} entries={len(entries)}', flush=True)
        json.dump(results, open(OUT, 'w'), ensure_ascii=False)
        time.sleep(SLEEP)

results = load()
pending = [q for q in QUERIES if f'{q[0]}::{q[1]}' not in results or results[f'{q[0]}::{q[1]}'].get('status') != 200]
print(f'Pass 1 pending: {len(pending)}', flush=True)
run_pass(results, pending)
# retry failures
failed = [q for q in QUERIES if results.get(f'{q[0]}::{q[1]}', {}).get('status') != 200]
for attempt in range(3):
    if not failed:
        break
    print(f'Retry pass {attempt+1}: {len(failed)} failed', flush=True)
    time.sleep(90)
    run_pass(results, failed)
    failed = [q for q in QUERIES if results.get(f'{q[0]}::{q[1]}', {}).get('status') != 200]
print('DONE', flush=True)
