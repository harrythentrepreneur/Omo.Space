#!/usr/bin/env python3
"""Mine Reddit for AI marketplace sentiment. Stage 1: RSS discovery. Stage 2: thread fetch+parse."""
import requests, re, html, json, time, os, sys, urllib.parse

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'
OUT = '/tmp/market_sentiment'
os.makedirs(OUT, exist_ok=True)

SUBS = ['PromptBase','ChatGPT','OpenAI','ClaudeAI','SideProject','indiehackers','nocode',
        'PromptEngineering','AI_Agents','n8n','LocalLLaMA','Entrepreneur','PoeAI','FlowGPT',
        'StableDiffusion','midjourney','artificial','SaaS','automation','ChatGPTCoding','dalle2']
QUERIES = ['PromptBase review','PromptBase earnings','GPT Store dead','GPT Store revenue',
           'Poe creators paid','Gumloop pricing','FlowGPT','sell prompts Etsy','n8n template',
           'AI marketplace scam','prompt marketplace worth it','GPT Store money','sell prompts',
           'make money prompts','prompt marketplace','Poe bot revenue','Poe subscription creators',
           'Gumloop','Etsy prompts','Coze','Replit marketplace','n8n sell workflow','prompt selling']
SORTS = ['relevance','top']

def rss_search(sub, q, sort):
    url = f'https://old.reddit.com/r/{sub}/search.rss'
    params = {'q': q, 'restrict_sr': '1', 'limit': '25', 'sort': sort}
    r = requests.get(url, params=params, headers={'User-Agent': UA}, timeout=30)
    if r.status_code != 200:
        return []
    data = r.text
    # entries: <entry><title>..</title><link href="...comments/ID/..." />
    titles = re.findall(r'<title>(.*?)</title>', data, re.S)
    links = re.findall(r'<link[^>]*href="(https://old\.reddit\.com/r/[^"]+/comments/[a-z0-9]+/[^"]*)"', data)
    # first two links are self/search; entries alternate title/link
    out = []
    for i, l in enumerate(links[2:]):
        t = titles[i+2] if i+2 < len(titles) else ''
        if '/comments/' in l:
            out.append({'sub': sub, 'query': q, 'sort': sort, 'title': html.unescape(t), 'url': l.split('?')[0].rstrip('/')})
    return out

def fetch_thread(url):
    """Fetch old.reddit thread HTML, return parsed dict."""
    r = requests.get(url, headers={'User-Agent': UA}, timeout=30)
    if r.status_code != 200:
        return {'url': url, 'status': r.status_code}
    d = r.text
    post = {}
    m = re.search(r'<a class="title may-blank[^"]*" href="[^"]*"[^>]*>(.*?)</a>', d, re.S)
    post['title'] = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else ''
    m = re.search(r'data-author="([^"]+)"[^>]*data-subreddit="([^"]+)"', d)
    post['author'] = m.group(1) if m else ''
    post['subreddit'] = m.group(2) if m else ''
    # post selftext: first md div after the thing_t3 block
    m = re.search(r'id="thing_t3_[^"]*".*?<div class="md">(.*?)</div>', d, re.S)
    post['selftext'] = html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1))).strip() if m else ''
    # comments
    comments = []
    for cm in re.finditer(r'id="thing_t1_([a-z0-9]+)"[^>]*data-author="([^"]+)"[^>]*>.*?<div class="score unvoted" title="(-?\d+)".*?<div class="md">(.*?)</div>', d, re.S):
        body = html.unescape(re.sub(r'<[^>]+>', ' ', cm.group(4))).strip()
        comments.append({'id': cm.group(1), 'author': cm.group(2), 'score': int(cm.group(3)), 'body': body})
    return {'url': url, 'status': 200, 'post': post, 'comments': comments, 'raw_len': len(d)}

def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else 'discover'
    if stage == 'discover':
        results = []
        for sub in SUBS:
            for q in QUERIES:
                for sort in SORTS:
                    try:
                        hits = rss_search(sub, q, sort)
                        for h in hits:
                            h['sub'] = sub
                            results.append(h)
                        print(f'{sub} | {q} | {sort}: {len(hits)}', flush=True)
                    except Exception as e:
                        print(f'ERR {sub} {q} {sort}: {e}', flush=True)
                    time.sleep(1.2)
        # dedupe
        seen = {}
        for h in results:
            k = h['url']
            if k not in seen:
                seen[k] = h
            else:
                seen[k]['query'] = seen[k]['query'] + '|' + h['query']
        json.dump(list(seen.values()), open(f'{OUT}/threads.json', 'w'), indent=1)
        print('TOTAL UNIQUE:', len(seen))
    elif stage == 'fetch':
        threads = json.load(open(f'{OUT}/threads.json'))
        # priority: marketplace-keyword in title or sub in marketplace-ish set
        KW = re.compile(r'promptbase|gpt store|poe|gumloop|flowgpt|n8n|etsy|coze|replit|marketplace|sell|revenue|earnings|money|paid|creators|scam|worth', re.I)
        MP_SUBS = {'PromptBase','PoeAI','FlowGPT','n8n','AI_Agents','nocode','indiehackers','SideProject','Entrepreneur','SaaS','automation'}
        prio = []
        for t in threads:
            score = 0
            if KW.search(t.get('title','')): score += 2
            if t.get('sub','') in MP_SUBS: score += 1
            if 'PromptBase' in t.get('query','') or 'GPT Store' in t.get('query','') or 'Gumloop' in t.get('query','') or 'Poe' in t.get('query','') or 'FlowGPT' in t.get('query','') or 'n8n' in t.get('query',''): score += 1
            prio.append((score, t['url'], t))
        prio.sort(key=lambda x: -x[0])
        urls = []
        for s, u, t in prio:
            if s >= 2 and u not in urls:
                urls.append(u)
            if len(urls) >= 70: break
        print('FETCHING', len(urls), 'threads')
        parsed = []
        for i, u in enumerate(urls):
            try:
                p = fetch_thread(u)
                parsed.append(p)
                print(f'[{i+1}/{len(urls)}] {p.get("post",{}).get("title","")[:80]} | comments={len(p.get("comments",[]))}', flush=True)
            except Exception as e:
                print(f'ERR {u}: {e}', flush=True)
            time.sleep(2.0)
        json.dump(parsed, open(f'{OUT}/threads_parsed.json', 'w'), indent=1)
        print('SAVED', len(parsed))

if __name__ == '__main__':
    main()
