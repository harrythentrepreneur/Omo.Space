#!/usr/bin/env python3
"""Mine Brave search for BUYER-side Reddit threads: setup friction, API keys, cost fear."""
import requests, re, html, json, time
from bs4 import BeautifulSoup

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'
SUBS = ['ChatGPT', 'ClaudeAI', 'nocode', 'smallbusiness', 'Entrepreneur', 'ecommerce', 'automation', 'artificial', 'ArtificialInteligence', 'OpenAI', 'LocalLLaMA', 'n8n', 'AI_Agents', 'selfhosted']
PHRASES = [
    '"clone the repo" AI workflow',
    '"clone the repo" agent setup',
    '"install dependencies" AI tool',
    '"API key" setup "too complicated"',
    '"too complicated to set up" AI',
    '"just want to use it" AI workflow',
    '"just want to use it" agent github',
    '"pay per use" AI tool worth',
    '"AI tool for my business"',
    '"AI tool for my business" recommendation',
    '"deploy AI workflow"',
    '"run locally vs API"',
    '"scared of" API costs',
    '"API costs" scared OR afraid',
    'AI agent "setup" "gave up"',
    '"gave up" installing AI tool',
    '"can\'t figure out" "API key"',
    '"setup friction" AI tool reddit',
    '"too much setup" AI automation',
    '"no coding" "AI workflow" want',
    'buy AI workflow instead of building',
    '"don\'t want to code" AI agent',
    'want AI automation "without coding" small business',
    '"python" "requirements.txt" AI "too much"',
    '"docker" AI agent "too complicated"',
]

queries = []
for sub in SUBS:
    for p in PHRASES:
        queries.append(f'site:reddit.com/r/{sub} {p}')

rows = []
for i, q in enumerate(queries):
    try:
        r = requests.get('https://search.brave.com/search',
                         params={'q': q, 'source': 'web', 'offset': 0},
                         headers={'User-Agent': UA}, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        found = 0
        for a in soup.find_all('a', href=True):
            href = html.unescape(a['href'])
            if not re.match(r'https?://(?:www\.)?reddit\.com/(?:r|u)/', href):
                continue
            url = href.split('?')[0].rstrip('/')
            txt = ' '.join(a.get_text(' ', strip=True).split())
            if not txt:
                continue
            # skip subreddit root links, keep comments
            rows.append({'query': q, 'url': url, 'text': txt[:600]})
            found += 1
        print(f'{i:3d} [{r.status_code}] {q[:80]:80s} links={found}')
        time.sleep(0.6)
    except Exception as e:
        print(f'{i:3d} ERR {q[:60]} {e}')

# aggregate
agg = {}
for x in rows:
    a = agg.setdefault(x['url'], {'url': x['url'], 'queries': [], 'texts': []})
    if x['query'] not in a['queries']:
        a['queries'].append(x['query'])
    if x['text'] not in a['texts']:
        a['texts'].append(x['text'])
res = list(agg.values())
print('UNIQUE URLS:', len(res))
open('/tmp/buyer_brave.json', 'w').write(json.dumps(res, indent=2, ensure_ascii=False))
