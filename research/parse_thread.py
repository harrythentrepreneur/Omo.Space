#!/usr/bin/env python3
"""Parse old.reddit thread HTML into post + comments."""
import re, html, json, sys

def parse_thread(d, url):
    post = {}
    m = re.search(r'<a class="title[^"]*"[^>]*href="[^"]*"[^>]*>(.*?)</a>', d, re.S)
    post['title'] = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else ''
    m = re.search(r'data-author="([^"]+)"[^>]*data-subreddit="([^"]+)"', d)
    post['author'] = m.group(1) if m else ''
    post['subreddit'] = m.group(2) if m else ''
    m = re.search(r'id="thing_t3_[^"]*".*?<div class="md">(.*?)</div>', d, re.S)
    post['selftext'] = html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1))).strip() if m else ''
    m = re.search(r'<div class="score unvoted" title="(-?\d+)"', d)
    post['score'] = int(m.group(1)) if m else 0
    comments = []
    for cm in re.finditer(r'id="thing_t1_([a-z0-9]+)"[^>]*data-author="([^"]+)"[^>]*>', d):
        start = cm.end()
        nxt = d.find('thing_t1_', start)
        seg = d[start:nxt] if nxt != -1 else d[start:]
        sc = re.search(r'<span class="score[^"]*" title="(-?\d+)"', seg)
        md = re.search(r'<div class="md">(.*?)</div>', seg, re.S)
        if not md:
            continue
        body = html.unescape(re.sub(r'<[^>]+>', ' ', md.group(1))).strip()
        body = re.sub(r'\s+', ' ', body)
        if not body:
            continue
        comments.append({'id': cm.group(1), 'author': cm.group(2),
                         'score': int(sc.group(1)) if sc else 0, 'body': body})
    return {'url': url, 'post': post, 'comments': comments}

if __name__ == '__main__':
    d = open(sys.argv[1]).read()
    p = parse_thread(d, sys.argv[2] if len(sys.argv) > 2 else '')
    out = sys.argv[3] if len(sys.argv) > 3 else '/tmp/parsed_thread.json'
    json.dump(p, open(out, 'w'), indent=1, ensure_ascii=False)
    print('saved', out, '| comments:', len(p['comments']))
