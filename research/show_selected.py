import json
rows=json.load(open('/tmp/reddit_ddg_records.json'))
slugs=['15uu1gi','143m97c','13kcazv','11zep52','13fl205','12aom6m','11f0pat','11kfsoa','1czml7r','17sglen','194ntpz','17t2tq6','197qkle','1940bd3','18v5iq0','17upjcm','198bk6p','17tiukp','1837mae','1dcwclq','1bvjjgc','1ci2van','170k91i','17g8p9e','1dj9c10','12yp1ce','1bl8esd','11sy43a','1drw1zf','1dpobt1','12az6yk','z9n56v','191ro5q','zpgodt']
for slug in slugs:
 for a in rows:
  if '/'+slug+'/' in a['url']:
   print('\n###',slug,a['url'],'\n',a['titles'][0])
   for l in a['lines']: print(l)
   break
