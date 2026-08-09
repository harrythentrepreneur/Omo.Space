import json,re
rows=json.load(open('/tmp/reddit_ddg_records.json'))
keys=['promptbase','money','sell','pay','monetiz','workflow','github','free','store','marketplace','payout','sales','passive','dm','creator','agent','revenue']
for a in rows:
 blob=' '.join(a['titles']+a['lines']).lower()
 score=sum(1 for k in keys if k in blob)
 if score>=2 and any(x in a['url'] for x in ['/comments/']):
  print('\nURL',a['url'],'\nTITLE',a['titles'][0])
  for l in a['lines'][:6]: print(' ',l[:1200])
