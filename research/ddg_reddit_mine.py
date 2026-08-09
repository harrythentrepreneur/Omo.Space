import requests, urllib.parse, re, json, time
queries=[
'site:reddit.com/r/PromptBase seller earnings payout',
'site:reddit.com/r/PromptEngineering sell prompts marketplace creator',
'site:reddit.com/r/midjourney selling on Promptbase',
'site:reddit.com/r/ChatGPT GPT Store money earnings creator',
'site:reddit.com/r/OpenAI GPT Store revenue creator',
'site:reddit.com/r/ChatGPTPro GPT Store monetize',
'site:reddit.com/r/ClaudeAI monetize custom GPT app',
'site:reddit.com/r/ClaudeAI workflow share GitHub',
'site:reddit.com/r/ChatGPTCoding sell agent workflow',
'site:reddit.com/r/LocalLLaMA make money AI agent',
'site:reddit.com/r/AI_Agents sell agent marketplace',
'site:reddit.com/r/n8n sell workflow template',
'site:reddit.com/r/n8n monetize workflow',
'site:reddit.com/r/automation sell automation workflow',
'site:reddit.com/r/SideProject AI marketplace creator sell',
'site:reddit.com/r/Entrepreneur AI automation agency money',
'site:reddit.com/r/indiehackers AI agent monetize',
'site:reddit.com/r/SaaS AI workflow marketplace',
'site:reddit.com/r/dalle2 selling prompts analysis',
'site:reddit.com/r/StableDiffusion making money from work',
'site:reddit.com/r/PoeAI bot monetization creator',
'site:reddit.com/r/FlowGPT earnings creator',
'site:reddit.com "dm me" workflow AI',
'site:reddit.com github workflow free AI agent',
'site:reddit.com "sell my prompts"',
'site:reddit.com "prompt marketplace" creator',
'site:reddit.com "no sales" PromptBase',
'site:reddit.com payment PromptBase seller',
'site:reddit.com passive income AI automation creator',
'site:reddit.com make money AI agents'
]
UA='Mozilla/5.0 (compatible; research)' 
alltext=[]
for i,q in enumerate(queries):
 url='https://r.jina.ai/http://html.duckduckgo.com/html/?'+urllib.parse.urlencode({'q':q})
 try:
  r=requests.get(url,headers={'User-Agent':UA},timeout=60)
  print(i,r.status_code,len(r.text),q)
  alltext.append({'query':q,'status':r.status_code,'text':r.text})
  time.sleep(1)
 except Exception as e: print('ERR',i,e); alltext.append({'query':q,'status':0,'text':''})
open('/tmp/reddit_ddg_jina.json','w').write(json.dumps(alltext,ensure_ascii=False))
