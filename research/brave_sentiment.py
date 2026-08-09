#!/usr/bin/env python3
"""Brave HTML search for reddit threads. Saves links to /tmp/brave_hits.json"""
import requests, re, html, json, time, sys, urllib.parse
from bs4 import BeautifulSoup
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'

QUERIES = [
 'site:reddit.com "PromptBase" review worth',
 'site:reddit.com "GPT Store" dead OR worthless OR useless',
 'site:reddit.com "GPT Store" revenue creators paid',
 'site:reddit.com Poe "bot creator" paid OR revenue',
 'site:reddit.com Gumloop pricing OR worth it',
 'site:reddit.com FlowGPT scam OR worthless OR "made money"',
 'site:reddit.com "sell prompts" Etsy',
 'site:reddit.com n8n template "sell" OR marketplace',
 'site:reddit.com "prompt marketplace" scam OR worth',
 'site:reddit.com "selling prompts" "made" OR earnings OR "no sales"',
 'site:reddit.com Coze marketplace OR monetize',
 'site:reddit.com "AI marketplace" "no one" OR dead OR scam',
 'site:reddit.com r/PromptBase review OR earnings OR payout',
 'site:reddit.com "promptbase" experience OR earnings',
]

def brave(q):
    r = requests.get('https://search.brave.com/search', params={'q': q, 'source': 'web'},
                     headers={'User-Agent': UA}, timeout=30)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, 'html.parser')
    hits = []
    for a in soup.find_all('a', href=True):
        h = html.unescape(a['href'])
        if not re.match(r'https?://(?:www\.)?(?:old\.)?reddit\.com/(?:r|u)/', h):
            continue
        url = h.split('?')[0].rstrip('/')
        txt = ' '.join(a.get_text(' ', strip=True).split())
        hits.append({'query': q, 'url': url, 'text': txt[:300]})
    return hits

def main():
    all_hits = []
    for i, q in enumerate(QUERIES):
        try:
            hits = brave(q)
            print(f'[{i+1}/{len(QUERIES)}] {q}: {len(hits)}', flush=True)
            all_hits.extend(hits)
        except Exception as e:
            print('ERR', q, e, flush=True)
        time.sleep(2.5)
    seen = {}
    for h in all_hits:
        if h['url'] not in seen:
            seen[h['url']] = h
    json.dump(list(seen.values()), open('/tmp/brave_hits.json', 'w'), indent=1, ensure_ascii=False)
    print('TOTAL UNIQUE:', len(seen), flush=True)

if __name__ == '__main__':
    main()
