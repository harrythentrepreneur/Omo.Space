#!/usr/bin/env python3
"""Mine Brave search HTML for reddit thread links. Usage: python3 mine_brave.py <query> <outfile>"""
import re, sys, subprocess, urllib.parse, time

def brave(query, outfile):
    q = urllib.parse.quote(f'site:reddit.com {query}')
    url = f'https://search.brave.com/search?q={q}&source=web'
    r = subprocess.run(['curl', '-sL', '-A',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
        '--max-time', '30', url, '-o', outfile], capture_output=True, text=True)
    html = open(outfile, encoding='utf-8', errors='ignore').read()
    links = re.findall(r'href="(https?://[^"]*reddit\.com/r/[^"]*/comments/[^"]*)"', html)
    seen, out = set(), []
    for l in links:
        l = l.replace('&amp;', '&')
        if l not in seen:
            seen.add(l)
            out.append(l)
    return out

if __name__ == '__main__':
    q, outfile = sys.argv[1], sys.argv[2]
    links = brave(q, outfile)
    for l in links:
        print(l)
    print(f'# {len(links)} links', file=sys.stderr)
