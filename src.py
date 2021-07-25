import asyncio
import re
import http.cookiejar
import urllib.request, urllib.parse
import soup, web

cj = http.cookiejar.CookieJar()
handler = urllib.request.HTTPCookieProcessor(cj)
od = urllib.request.build_opener(handler)

def match(title, *args):
    for arg in args:
        if arg.lower() not in title.lower():
            return False
    return True

async def open(url, data=None):
    UA = 'Mozilla/5.0 (Maemo; Linux armv7l; rv:10.0.1) Gecko/20100101 Firefox/10.0.1 Fennec/10.0.1'
    return await web.open(url, data, { 'User-Agent': UA }, od.open)

async def get(url):
    return soup.parse((await open(url)).decode())

async def rentanadviser(*args):
    BASE = 'https://www.rentanadviser.com/en/subtitles'
    query = urllib.parse.urlencode({ 'src': ' '.join(args) })
    html = await get(f'{BASE}/subtitles4songs.aspx?{query}')
    links = html.next('div', id='tablecontainer')

    for link in links.find('a'):
        if match(link.text(), *args):
            href = link.attrs['href']
            html = await get(f'{BASE}/{href}&type=lrc')

            return (await open(f'{BASE}/{href}&type=lrc', urllib.parse.urlencode({
                '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$btnlyrics',
                '__EVENTVALIDATION': html.next('input', id='__EVENTVALIDATION').attrs['value'],
                '__VIEWSTATE': html.next('input', id='__VIEWSTATE').attrs['value']
            }).encode())).decode()

async def megalobiz(*args):
    BASE = 'https://www.megalobiz.com'
    query = urllib.parse.urlencode({ 'qry': ' '.join(args), 'display': 'more' })
    html = await get(f'{BASE}/search/all?{query}')
    links = html.next('div', id='list_entity_container')

    for link in links.find('a', **{ 'class': ['entity_name'] }):
        if match(link.text(), *args):
            html = await get(BASE + link.attrs['href'])
            lrc = html.next('div', **{ 'class': ['lyrics_details'] })
            return lrc.next('span').text()

async def syair(*args):
    BASE = 'https://www.syair.info'
    query = urllib.parse.urlencode({ 'q': ' '.join(args) })
    html = await get(f'{BASE}/search?{query}')
    links = html.next('div', **{ 'class': ['sub'] })

    if links is not None:
        for link in links.find('div', **{ 'class': ['li'] }):
            link = link.next('a')
            if match(link.text(), *args):
                html = await get(BASE + link.attrs['href'])
                for link in html.find('a'):
                    if '?download' in link.attrs['href']:
                        html = await get(link.attrs['href'])
                        for link in html.find('a'):
                            if 'download.syair.info' in link.attrs['href']:
                                return (await open(link.attrs['href'])).decode()

regex = re.compile(r'\[(\d\d:\d\d.\d\d)\]([^\r\n]+)')

async def search(*args):
    tasks = []
    results = []
    tasks.append(asyncio.create_task(rentanadviser(*args)))
    tasks.append(asyncio.create_task(megalobiz(*args)))
    tasks.append(asyncio.create_task(syair(*args)))

    for task in tasks:
        try:
            lrc = await task
            if lrc != None:
                results.append(lrc)
        except:
            continue
            
    if len(results) > 0:
        return results[0]

def parse(data):
    for match in regex.finditer(data):
        tm = match[1].split(':')
        tm = int(tm[0]) * 60 + float(tm[1])
        tx = match[2].strip()
        yield (tm, tx)

def parse_adjust(data, duration):
    data = list(parse(data))
    delta = max(data[-1][0] - duration, 0) / 1.5
    for i in range(len(data)):
        data[i] = (data[i][0] - delta, data[i][1])
    return (data, int(delta * 1000))