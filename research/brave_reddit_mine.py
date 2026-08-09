import requests, re, html, json, time, urllib.parse
from bs4 import BeautifulSoup
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'
queries=[
'site:reddit.com/r/PromptBase selling prompts earnings payout',
'site:reddit.com/r/PromptBase sell prompts money',
'site:reddit.com/r/PromptEngineering sell prompts marketplace creator',
'site:reddit.com/r/midjourney selling on Promptbase',
'site:reddit.com/r/ChatGPT GPT Store money earnings creator',
'site:reddit.com/r/OpenAI GPT Store revenue creator',
'site:reddit.com/r/ChatGPTPro GPT Store monetize',
'site:reddit.com/r/ClaudeAI sell workflow agent monetization',
'site:reddit.com/r/ClaudeAI share workflow GitHub',
'site:reddit.com/r/ChatGPTCoding sell agent workflow',
'site:reddit.com/r/LocalLLaMA make money agent',
'site:reddit.com/r/AI_Agents sell agent marketplace',
'site:reddit.com/r/n8n sell workflow template',
'site:reddit.com/r/n8n monetize workflow',
'site:reddit.com/r/automation sell automation',
'site:reddit.com/r/SideProject AI marketplace creator sell',
'site:reddit.com/r/Entrepreneur AI automation agency money',
'site:reddit.com/r/indiehackers AI agent monetize',
'site:reddit.com/r/SaaS workflow marketplace creator',
'site:reddit.com/r/artificial AI prompts sell',
'site:reddit.com/r/dalle2 selling prompts analysis',
'site:reddit.com/r/StableDiffusion making money from work',
'site:reddit.com/r/PoeAI bot monetization creator',
'site:reddit.com/r/FlowGPT earnings creator',
'site:reddit.com "dm me" AI workflow',
'site:reddit.com "github" "workflow" "free" AI',
'site:reddit.com "share" "workflow" "github" agent',
'site:reddit.com "sell my prompts" OR "selling prompts"',
'site:reddit.com "prompt marketplace" creator',
'site:reddit.com "no sales" PromptBase',
'site:reddit.com "payment" "PromptBase" seller',
'site:reddit.com "passive income" AI automation creator',
'site:reddit.com "make money" "AI agents"'
]
rows=[]
for i,q in enumerate(queries):
 try:
  r=requests.get('https://search.brave.com/search',params={'q':q,'source':'web','offset':0},headers={'User-Agent':UA},timeout=30)
  print(i,r.status_code,len(r.text),q)
  soup=BeautifulSoup(r.text,'html.parser')
  for a in soup.find_all('a',href=True):
   href=html.unescape(a['href'])
   if not re.match(r'https?://(?:www\.)?reddit\.com/(?:r|u)/',href): continue
   url=href.split('?')[0].rstrip('/')
   # page root title anchor or snippet anchors; retain all texts
   txt=' '.join(a.get_text(' ',strip=True).split())
   if not txt: continue
   rows.append({'query':q,'url':url,'text':txt})
  time.sleep(.6)
 except Exception as e: print('ERR',e)
# aggregate text
agg={}
for x in rows:
 a=agg.setdefault(x['url'],{'url':x['url'],'queries':[],'texts':[]})
 if x['query'] not in a['queries']: a['queries'].append(x['query'])
 if x['text'] not in a['texts']: a['texts'].append(x['text'])
res=list(agg.values())
print('UNIQUE',len(res))
open('/tmp/reddit_brave.json','w').write(json.dumps(res,indent=2,ensure_ascii=False))
for a in res:
 print('\nURL',a['url'])
 for t in a['texts'][:4]: print('  ',t[:1000])
