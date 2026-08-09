#!/usr/bin/env python3
"""Mine Reddit for AI marketplace sentiment. Stage 1: RSS discovery via curl (serial, polite)."""
import re, html, json, time, os, subprocess, urllib.parse

OUT = '/tmp/market_sentiment'
os.makedirs(OUT, exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'

SUBS = ['PromptBase','ChatGPT','OpenAI','ClaudeAI','SideProject','indiehackers','nocode',
        'PromptEngineering','AI_Agents','n8n','Entrepreneur','PoeAI','FlowGPT','SaaS','automation']
QUERIES = ['PromptBase review','PromptBase earnings','GPT Store dead','GPT Store revenue',
           'Poe creators paid','Gumloop pricing','FlowGPT','sell prompts Etsy','n8n template',
           'AI marketplace scam','prompt marketplace worth it','GPT Store money','sell prompts',
           'make money prompts','Poe bot revenue','Poe subscription','Gumloop','Etsy prompts',
           'Coze','Replit marketplace','n8n sell workflow','prompt selling','prompt earnings']

def rss_search(sub, q):
    url = 'https://old.reddit.com/r/%s/search.rss?%s' % (sub, urllib.parse.urlencode(
        {'q': q, 'restrict_sr': '1', 'limit': '25', 'sort': 'relevance'}))
    try:
        r = subprocess.run(['curl', '-sL', '-A', UA, '--max-time', '30', url],
                           capture_output=True, text=True, timeout=40)
        data = r.stdout
        if '<entry>' not in data:
            return [], data[:120]
        titles = re.findall(r'<title>(.*?)</title>', data, re.S)
        links = re.findall(r'<link[^>]*href="(https://old\.reddit\.com/r/[^"]+)"', data)
        out = []
        for i, l in enumerate(links[2:]):
            t = titles[i+1] if i+1 < len(titles) else ''
            if '/comments/' in l:
                out.append({'sub': sub, 'query': q, 'title': html.unescape(t),
                            'url': l.split('?')[0].rstrip('/')})
        return out, 'ok'
    except Exception as e:
        return [], str(e)

def main():
    jobs = [(s, q) for s in SUBS for q in QUERIES]
    results = []
    fails = 0
    for i, (s, q) in enumerate(jobs):
        hits, note = rss_search(s, q)
        results.extend(hits)
        if not hits:
            fails += 1
        print(f'[{i+1}/{len(jobs)}] {s} | {q}: {len(hits)} {note[:60]}', flush=True)
        time.sleep(1.8)
    seen = {}
    for h in results:
        k = h['url']
        if k not in seen:
            seen[k] = h
        else:
            seen[k]['query'] = seen[k]['query'] + '|' + h['query']
    json.dump(list(seen.values()), open(f'{OUT}/threads.json', 'w'), indent=1)
    print('TOTAL UNIQUE:', len(seen), 'EMPTY:', fails, flush=True)

if __name__ == '__main__':
    main()
