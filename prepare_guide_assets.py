from pathlib import Path
import requests, re, json, html, concurrent.futures

OUT = Path('docs/assets/survival-guide')
OUT.mkdir(parents=True, exist_ok=True)
pages = {
 'mars': 'https://science.nasa.gov/mars/facts/',
 'dust': 'https://science.nasa.gov/asset/hubble/a-global-dust-storm-on-mars/',
 'radiation': 'https://science.nasa.gov/photojournal/curiosity-sees-specks-caused-by-2024-solar-storm-while-recording-a-wind-gust-on-mars/',
 'moxie': 'https://science.nasa.gov/photojournal/components-of-moxie-illustration/',
 'habitat': 'https://www.nasa.gov/humans-in-space/chapea/habitat/',
 'crew': 'https://www.nasa.gov/image-article/nasas-chapea-crew-returns-to-earth/',
 'suits': 'https://www.nasa.gov/get-involved/spacesuit-user-interface-technologies-for-students-suits/',
}
def download(item):
 key,url=item
 r=requests.get(url,timeout=60); r.raise_for_status()
 tags=re.findall(r'<meta\b[^>]*>',r.text,re.I)
 tag=next(t for t in tags if re.search(r'(?:property|name)=[\"\']og:image[\"\']',t))
 img=html.unescape(re.search(r'content=[\"\']([^\"\']+)',tag).group(1))
 data=requests.get(img,timeout=90); data.raise_for_status()
 ext='.png' if 'png' in data.headers.get('Content-Type','') else '.jpg'
 name=key+ext; (OUT/name).write_bytes(data.content)
 return key,dict(page=url,image=img,file=name)
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
 results=dict(pool.map(download,pages.items()))
(OUT/'sources.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
url='https://unpkg.com/@google/model-viewer@4.1.0/dist/model-viewer.min.js'
r=requests.get(url,timeout=90); r.raise_for_status(); (OUT/'model-viewer.min.js').write_bytes(r.content)
print(json.dumps(results,indent=2))

