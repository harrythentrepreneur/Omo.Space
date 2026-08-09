from bs4 import BeautifulSoup
s=BeautifulSoup(open('/tmp/brave.html').read(),'html.parser')
for a in s.find_all('a',href=True):
 h=a['href']
 if 'reddit.com' in h:
  print('HREF',h,'TXT',a.get_text(' ',strip=True)[:500])
