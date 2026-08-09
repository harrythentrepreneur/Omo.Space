import requests, json, urllib.parse, time
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36'
queries=['sell AI prompts','monetize AI workflow','monetize Claude','DM me workflow','share GitHub AI project','prompt marketplace','make money building agents','passive income AI automation','GPT Store earnings','PromptBase','Poe creator payout','FlowGPT','n8n workflow sell','sell automation','AI agents business']
out=[]
for q in queries:
  url='https://www.reddit.com/search.json?'+urllib.parse.urlencode({'q':q,'sort':'relevance','t':'all','limit':100,'raw_json':1})
  try:
    r=requests.get(url,headers={'User-Agent':UA},timeout=20)
    print('SEARCH',q,r.status_code,len(r.text))
    if r.status_code==200:
      data=r.json()
      for ch in data.get('data',{}).get('children',[]):
        d=ch.get('data',{})
        if d.get('permalink'):
          out.append({'id':d.get('id'),'url':'https://www.reddit.com'+d['permalink'],'subreddit':d.get('subreddit'),'title':d.get('title'),'created_utc':d.get('created_utc'),'selftext':d.get('selftext',''),'num_comments':d.get('num_comments',0),'score':d.get('score',0),'query':q})
    time.sleep(.5)
  except Exception as e: print('ERR',q,e)
seen={}
for x in out: seen[x['url']]=x
print('THREADS',len(seen))
open('/tmp/reddit_search.json','w').write(json.dumps(list(seen.values()),indent=2))
print(json.dumps(list(seen.values())[:5],indent=2)[:4000])
