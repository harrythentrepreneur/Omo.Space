import requests, urllib.parse, re, html, json, time
from bs4 import BeautifulSoup
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36'
queries=[
'site:reddit.com/r/ClaudeAI monetize OR sell workflow agent',
'site:reddit.com/r/ChatGPTCoding sell AI tool OR workflow',
'site:reddit.com/r/OpenAI GPT Store earnings creator',
'site:reddit.com/r/LocalLLaMA monetize agent OR prompt',
'site:reddit.com/r/SideProject AI automation sell',
'site:reddit.com/r/Entrepreneur AI agents make money',
'site:reddit.com/r/n8n sell workflow OR template',
'site:reddit.com/r/automation sell automation workflow',
'site:reddit.com/r/SaaS AI workflow customers pay',
'site:reddit.com/r/indiehackers AI agent monetize',
'site:reddit.com PromptBase seller earnings',
'site:reddit.com "dm me" workflow AI',
'site:reddit.com GitHub workflow "free" AI',
'site:reddit.com GPT Store "made" money',
'site:reddit.com AI prompts "sell" creator',
'site:reddit.com "no one" "GPT Store" money',
'site:reddit.com Poe bot monetization',
'site:reddit.com FlowGPT earnings creator',
'site:reddit.com AI automation "passive income"',
'site:reddit.com "sell my prompts"'
]
rows=[]
for q in queries:
 for engine in ['google','bing']:
  base='https://www.google.com/search' if engine=='google' else 'https://www.bing.com/search'
  try:
   r=requests.get(base,params={'q':q,'num':20},headers={'User-Agent':UA},timeout=25)
   print(engine, q, r.status_code, len(r.text))
   soup=BeautifulSoup(r.text,'html.parser')
   for a in soup.find_all('a',href=True):
    href=html.unescape(a['href'])
    # Google wraps /url?q= or /search?; Bing direct
    m=re.search(r'https?://(?:www\.)?reddit\.com/(?:r/|u/)[^&?#"<> ]+',href)
    if not m: continue
    url=m.group(0).replace('www.reddit.com','www.reddit.com').rstrip('/')
    # strip tracking, preserve post
    txt=' '.join(a.get_text(' ',strip=True).split())
    parent=a.parent
    context=' '.join(parent.parent.get_text(' ',strip=True).split()) if parent and parent.parent else txt
    rows.append({'query':q,'engine':engine,'url':url,'anchor':txt,'context':context[:1000]})
   time.sleep(.4)
  except Exception as e: print('ERR',engine,q,e)
# dedupe urls, retain combined
agg={}
for x in rows:
 k=x['url']
 if k not in agg: agg[k]={'url':k,'queries':[],'engines':[],'anchors':[],'contexts':[]}
 for fld,val in [('queries',x['query']),('engines',x['engine']),('anchors',x['anchor']),('contexts',x['context'])]:
  if val and val not in agg[k][fld]: agg[k][fld].append(val)
res=list(agg.values())
print('UNIQUE',len(res))
open('/tmp/reddit_web_results.json','w').write(json.dumps(res,indent=2,ensure_ascii=False))
for x in res[:80]: print('\nURL',x['url'],'\nA',x['anchors'][:2],'\nC',x['contexts'][:1])
