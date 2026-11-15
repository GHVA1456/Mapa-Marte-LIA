from pathlib import Path
import re, html, hashlib, zipfile
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode

root=Path.cwd()
paths=[root/'Proyecto Nasa Hackathon (pagina)/Nasa, Marte(guia de supervivencia).html',root/'docs/index.html']
protected={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'docs').glob('*.html') if p.name!='index.html'}
raw=Path('C:/Users/ajpal/.codex/attachments/e25186a7-e0c1-4d60-9c01-6b487a5b2049/Texto pegado.txt').read_text(encoding='utf-8-sig')
def clean(url):
 s=urlsplit(url.strip()); return urlunsplit((s.scheme,s.netloc,s.path,urlencode([(k,v) for k,v in parse_qsl(s.query) if not k.startswith('utm_')]),s.fragment))
def link(label,url):
 return '<a href="'+html.escape(clean(url),quote=True)+'" target="_blank" rel="noopener noreferrer">'+html.escape(label.strip())+'</a>'
refs=[];media=[]
for line in raw.splitlines():
 line=line.strip()
 if not line or line=='NASA Science+1' or line.startswith(('Estas son','C:/')): continue
 matches=list(re.finditer(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',line))
 if matches:
  output=''; pos=0
  for m in matches:
   output+=html.escape(re.sub(r'^(?:\d+\.|-)\s*','',line[pos:m.start()]))+link(m[1],m[2]);pos=m.end()
  output+=html.escape(line[pos:])
  (media if 'images.openai.com/' in line else refs).append('<li>'+output+'</li>')
 elif 'https://' in line:
  m=re.search(r'https?://\S+',line); refs.append('<li>'+html.escape(re.sub(r'^(?:\d+\.|-)\s*','',line[:m.start()]))+link(m.group(),m.group())+'</li>')
 # Non-citation headings and pasted search interface labels are not references.
assert len(refs)>30
refs=list(dict.fromkeys(refs));media=list(dict.fromkeys(media))
def bilingual(es,en): return '<span class="credits-es" lang="es">'+es+'</span><span class="credits-en" lang="en">'+en+'</span>'
panel='''<section class="panel" id="guide-credits">
<style>html[lang|="es"] #guide-credits .credits-en,html:not([lang|="es"]) #guide-credits .credits-es{display:none}#guide-credits details{margin:16px 0;padding:16px;border:1px solid #485466;border-radius:12px}#guide-credits summary{cursor:pointer;font-weight:bold}#guide-credits li{margin:14px 0;overflow-wrap:anywhere}#guide-credits a{overflow-wrap:anywhere}#guide-credits dt{font-weight:bold}#guide-credits dd{margin:0 0 12px}</style>
<!-- AI assistance disclosure: ChatGPT / Codex (OpenAI) and Claude (Anthropic) assisted with code.
The team estimates approximately 40% AI assistance across the project; this is a self-reported estimate, not a measured code attribution.
AI supported base-code development, debugging, content organization and bilingual presentation.
Observed Codex contributions include HTML/CSS/JavaScript integration, model-viewer integration, reference formatting and packaging.
Copilot is credited for general project assistance.
The project is not represented as entirely AI-generated. Scientific references remain separate from AI tool credits.
-->
<h2>'''+bilingual('Referencias, créditos y colaboración','References, credits and collaboration')+'''</h2>
<details><summary>'''+bilingual('Referencias institucionales, científicas y complementarias','Institutional, scientific and supplementary references')+'''</summary><p>'''+bilingual('Fuentes proporcionadas por el equipo. Se incluyen fuentes primarias y materiales de divulgación; los créditos de cada imagen también aparecen junto a ella.','Sources supplied by the team. The list includes primary sources and science communication materials; image credits also appear alongside each image.')+'''</p><ol>'''+''.join(refs)+'''</ol><h3>'''+bilingual('Colaborador: Irving Adair Romero Espinosa','Collaborator: Irving Adair Romero Espinosa')+'''</h3><dl data-no-translate><dt>'''+bilingual('Nombre','Name')+'''</dt><dd>Irving Adair Romero Espinosa</dd><dt>'''+bilingual('Participación','Role')+'''</dt><dd>'''+bilingual('Colaborador','Collaborator')+'''</dd><dt>'''+bilingual('Teléfono','Phone')+'''</dt><dd><a href="tel:7713517303">771 351 7303</a></dd><dt>'''+bilingual('Fecha','Date')+'''</dt><dd><time datetime="2026-11-14">14/11/2026</time></dd></dl></details>
<details><summary>'''+bilingual('Enlaces multimedia adicionales del documento','Additional multimedia links from the document')+'''</summary><p>'''+bilingual('Estos enlaces proceden del documento recibido y pueden ser temporales. No sustituyen la referencia a la publicación original.','These links come from the supplied document and may be temporary. They do not replace a citation to the original publication.')+'''</p><ul>'''+''.join(media)+'''</ul></details>
<details><summary>'''+bilingual('Uso de inteligencia artificial y créditos de desarrollo','AI use and development credits')+'''</summary>
<p>'''+bilingual('El equipo estima que aproximadamente el <strong>40 % del proyecto recibió asistencia de inteligencia artificial</strong>. Es una estimación declarada por el equipo, no una medición automática ni un porcentaje exacto de líneas de código. El proyecto no fue generado íntegramente por IA.','The team estimates that approximately <strong>40% of the project received AI assistance</strong>. This is a team-reported estimate, not an automated measurement or an exact percentage of code lines. The project was not entirely AI-generated.')+'''</p>
<p>'''+bilingual('Se reconoce el uso de <strong>ChatGPT / Codex (OpenAI) y Claude (Anthropic)</strong> como herramientas de apoyo al desarrollo del código base y a la elaboración del proyecto. La asistencia incluyó programación, revisión y depuración, organización de contenidos y presentación bilingüe. La dirección, las decisiones y la revisión final corresponden al equipo.','The team acknowledges <strong>ChatGPT / Codex (OpenAI) and Claude (Anthropic)</strong> as tools supporting base-code development and project preparation. Assistance included programming, review and debugging, content organization and bilingual presentation. Direction, decisions and final review remain the team’s responsibility.')+'''</p>
<p>'''+bilingual('En esta página, Codex apoyó la integración de HTML, CSS y JavaScript, el visor 3D del casco KM-1306, la presentación de referencias y el empaquetado de archivos. Copilot se acredita por su apoyo general al proyecto. Las herramientas de IA no sustituyen las fuentes científicas citadas.','On this page, Codex assisted with HTML, CSS and JavaScript integration, the KM-1306 helmet viewer, reference presentation and file packaging. Copilot is credited for general project assistance. AI tools do not replace the cited scientific sources.')+'''</p></details>

</section>'''
for path in paths:
 text=path.read_bytes().decode('utf-8'); nl='\r\n' if '\r\n' in text else '\n'
 blocks=list(re.finditer(r'<section class="panel"[^>]*>[\s\S]*?</section>',text));assert len(blocks)==6
 helmet=blocks[4].group()
 for old,new in [('Smart-Visor: modelo 3D del casco','KM-1306: modelo 3D del casco Smart-Visor'),('Smart-Visor: 3D helmet model','KM-1306: Smart-Visor 3D helmet model'),('Smart-Visor 3D helmet / Casco Smart-Visor 3D','KM-1306 3D helmet / Casco KM-1306 3D'),('Cargar casco 3D (61 MB)','Cargar KM-1306 en 3D (61 MB)'),('Load 3D helmet (61 MB)','Load KM-1306 in 3D (61 MB)'),('Modelo proporcionado por el equipo del proyecto:','KM-1306. Modelo proporcionado por el equipo del proyecto:'),('Model supplied by the project team:','KM-1306. Model supplied by the project team:')]: helmet=helmet.replace(old,new)
 new_panel=panel.replace('\n',nl)
 updated=text[:blocks[4].start()]+helmet+text[blocks[4].end():blocks[5].start()]+new_panel+text[blocks[5].end():]
 assert updated.replace(helmet,blocks[4].group(),1).replace(new_panel,blocks[5].group(),1)==text
 path.write_bytes(updated.encode('utf-8'))
for p,h in protected.items():assert hashlib.sha256(p.read_bytes()).hexdigest()==h
with zipfile.ZipFile(root/'Mapa-Marte-LIA-Netlify.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in (root/'docs').rglob('*'):
  if p.is_file():z.write(p,p.relative_to(root/'docs').as_posix())
with zipfile.ZipFile(root/'Mapa-Marte-LIA-Netlify.zip') as z:
 assert z.testzip() is None
 assert z.read('index.html')==paths[1].read_bytes()
print(f'Updated helmet name and last panel only. {len(refs)} reference entries, {len(media)} multimedia links. ZIP verified.')
