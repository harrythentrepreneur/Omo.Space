import requests
from bs4 import BeautifulSoup
q='site:reddit.com PromptBase seller earnings'
r=requests.get('https://www.bing.com/search',params={'q':q,'count':20},headers={'User-Agent':'Mozilla/5.0'})
s=BeautifulSoup(r.text,'html.parser')
for a in s.find_all('a',href=True):
 h=a['href']
 if 'reddit' in h.lower() or 'PromptBase' in a.get_text(): print(h[:500], a.get_text(' ',strip=True)[:200])
