import json,re,urllib.parse
items=json.load(open('/tmp/reddit_ddg_jina.json'))
rows=[]
for it in items:
 txt=it['text']
 # markdown sections beginning ## [title](url)
 parts=re.split(r'\n## \[',txt)
 for p in parts[1:]:
  m=re.match(r'([^\]]+)\]\(([^)]+)\)\n(.*)',p,re.S)
  if not m: continue
  title,url,body=m.groups()
  # Unwrap DDG redirect target
  if 'duckduckgo.com/l/?uddg=' in url:
   try: url=urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get('uddg',[url])[0]
   except: pass
  if 'reddit.com/r/' not in url: continue
  lines=[]
  for line in body.splitlines():
   line=line.strip()
   if not line or line.startswith('!['): continue
   # retain the visible text from Markdown links (search-result snippets are evidence)
   if line.startswith('['):
    mm=re.match(r'\[([^]]+)\]\([^)]*\)',line)
    if mm: line=mm.group(1)
   line=re.sub(r'\s+',' ',line)
   if line not in lines: lines.append(line)
  rows.append({'query':it['query'],'title':title,'url':url.rstrip('/'),'body_lines':lines[:6]})
# dedupe, merge queries and snippets
agg={}
for x in rows:
 a=agg.setdefault(x['url'],{'url':x['url'],'titles':[],'queries':[],'lines':[]})
 for f,v in [('titles',x['title']),('queries',x['query'])]:
  if v not in a[f]: a[f].append(v)
 for v in x['body_lines']:
  if v not in a['lines']: a['lines'].append(v)
res=list(agg.values())
print('UNIQUE',len(res))
open('/tmp/reddit_ddg_records.json','w').write(json.dumps(res,indent=2,ensure_ascii=False))
for a in res:
 print('\nURL',a['url'],'\nTITLE',a['titles'][0])
 for l in a['lines'][:4]: print(' ',l[:500])
