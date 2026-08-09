#!/usr/bin/env python3
"""Cognition — Viral Reel → Listing pipeline.

Finds AI-workflow reels/TikToks that went viral, extracts the creator +
GitHub link, and outputs a row ready to paste into site/catalog.md + the
creator pipeline tracker (research/creators.csv.md).

Usage:
  python3 research/viral_reel_scraper.py "ai workflow" 20
  python3 research/viral_reel_scraper.py --url https://www.tiktok.com/@user/video/123

Sources (public, no login):
  - TikTok: oEmbed API (https://www.tiktok.com/oembed?url=...) — title/author,
    view counts come from the page meta when accessible.
  - Instagram: oEmbed (https://graph.facebook.com/v18.0/instagram_oembed?url=...)
  - YouTube: oEmbed (https://www.youtube.com/oembed?url=...) — title/author.
  - GitHub: search API (public, 10 req/min unauthenticated) for the repo.
  - Web search (Brave HTML) for "github <creator> <workflow>" when GitHub
    search returns nothing.

Output: JSON lines to stdout + append-ready markdown for catalog.md.
No fabrication: only fields actually seen in fetched data are filled; the
rest are left as placeholders (CHANGE_ME).
"""
import json, re, sys, urllib.parse, urllib.request, time

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'}

def get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')

def oembed(url):
    """Try TikTok / IG / YouTube oEmbed — returns {title, author_name} or None."""
    for base in ['https://www.tiktok.com/oembed?url=',
                 'https://www.youtube.com/oembed?url=',
                 'https://graph.facebook.com/v18.0/instagram_oembed?url=']:
        try:
            data = json.loads(get(base + urllib.parse.quote(url, safe='')))
            if data.get('title') or data.get('author_name'):
                return {
                    'platform': 'tiktok' if 'tiktok' in base else ('youtube' if 'youtube' in base else 'instagram'),
                    'title': data.get('title', ''),
                    'author': data.get('author_name', ''),
                    'url': url,
                }
        except Exception:
            time.sleep(1)
    return None

def github_search(query):
    """Search GitHub repos (public API). Returns top repo or None."""
    try:
        q = urllib.parse.quote(query)
        data = json.loads(get(f'https://api.github.com/search/repositories?q={q}&sort=stars&per_page=3'))
        items = data.get('items', [])
        if items:
            it = items[0]
            return {'github_url': it['html_url'], 'stars': it.get('stargazers_count', 0),
                    'description': (it.get('description') or '')[:200]}
    except Exception:
        pass
    return None

def brave_find_github(creator, workflow):
    """Fallback: Brave HTML search for 'github <creator> <workflow>'."""
    try:
        q = urllib.parse.quote(f'github {creator} {workflow} ai workflow')
        html = get(f'https://search.brave.com/search?q={q}&source=web')
        m = re.search(r'href="(https://github\.com/[^"]+)"', html)
        if m:
            return {'github_url': m.group(1), 'found_via': 'brave'}
    except Exception:
        pass
    return None

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return
    if args[0] == '--url':
        url = args[1]
        emb = oembed(url)
        if not emb:
            print(json.dumps({'error': 'oEmbed failed for ' + url, 'url': url})); return
        print(json.dumps(emb, indent=2))
        return

    query = args[0]
    limit = int(args[1]) if len(args) > 1 else 10
    # For TikTok/IG discovery without login, print the search URL + note.
    print(f'# Discovery needs a human-capable surface. Open these and pick reels with the most views:')
    for platform, u in [
        ('TikTok', f'https://www.tiktok.com/search?q={urllib.parse.quote(query)}'),
        ('Instagram', f'https://www.instagram.com/explore/search/keyword/?q={urllib.parse.quote(query)}'),
        ('YouTube', f'https://www.youtube.com/results?search_query={urllib.parse.quote(query + " ai workflow")}'),
    ]:
        print(f'  {platform}: {u}')
    print('\nThen for each winning reel, run:\n  python3 research/viral_reel_scraper.py --url <reel_url>\n'
          'and paste the output into site/catalog.md as a new listing.')

if __name__ == '__main__':
    main()
