from pathlib import Path
import re, json, html, shutil, struct, hashlib, zipfile

root=Path.cwd()
source=root/'Proyecto Nasa Hackathon (pagina)/Nasa, Marte(guia de supervivencia).html'
published=root/'docs/index.html'
assets=root/'docs/assets/survival-guide'
sources=json.loads((assets/'sources.json').read_text())
protected={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'docs/map.html',root/'docs/mars-survival.html']}
images=[
 ('mars','Marte: vista global del planeta.','Mars: a global view.','NASA/JPL-Caltech'),
 ('dust','La atmósfera de Marte antes y durante una tormenta de polvo.','The Martian atmosphere before and during a dust storm.','NASA, James Bell (Cornell Univ.), Michael Wolff (Space Science Inst.), Hubble Heritage Team (STScI/AURA)'),
 ('dust','Comparación de Hubble que muestra el alcance de una tormenta global de polvo.','Hubble comparison showing the extent of a global dust storm.','NASA, James Bell (Cornell Univ.), Michael Wolff (Space Science Inst.), Hubble Heritage Team (STScI/AURA)'),
 ('radiation','Registro de Curiosity asociado a la tormenta solar de 2024; no es un mapa de dosis para astronautas.','Curiosity observation associated with the 2024 solar storm; this is not an astronaut dose map.','NASA/JPL-Caltech'),
 ('geology','Rocas y sedimentos del delta de Jezero; la imagen no mide percloratos.','Rocks and sediments in the Jezero delta; the image does not measure perchlorates.','RMI: NASA/JPL-Caltech/LANL/CNES/CNRS/ASU/MSSS; Mastcam-Z: NASA/JPL-Caltech/ASU/MSSS'),
 ('hazards','Mapa de peligros de aterrizaje de Jezero. No representa una ruta EVA certificada.','Jezero landing hazard map. It does not represent a certified EVA route.','NASA/JPL-Caltech'),
 ('jezero','Elipse prevista para el aterrizaje de Perseverance en Jezero.','Planned Perseverance landing ellipse in Jezero.','ESA/DLR/FU-Berlin/NASA/JPL-Caltech'),
 ('moxie','Ilustración de los componentes de MOXIE, demostrador de producción de oxígeno.','Illustration of MOXIE components, an oxygen-production demonstrator.','NASA/JPL-Caltech'),
 ('habitat','Construcción del hábitat análogo CHAPEA en la Tierra; no es un hábitat instalado en Marte.','Construction of the CHAPEA analog habitat on Earth; this is not a habitat on Mars.','ICON; fuente / source: NASA'),
 ('crew','Tripulación de CHAPEA al finalizar una simulación de aislamiento en la Tierra.','CHAPEA crew after an isolation simulation on Earth.','NASA/James Blair'),
 ('suits','NASA SUITS: investigación de interfaces para actividades extravehiculares.','NASA SUITS: research into interfaces for extravehicular activities.','NASA'),
 ('hazards','Ejemplo de cartografía de peligros de aterrizaje; los riesgos humanos requieren evaluaciones adicionales.','Example of landing hazard mapping; human risks require additional assessments.','NASA/JPL-Caltech'),
 ('jezero','Jezero como contexto geográfico de la exploración y planificación científica.','Jezero as the geographic context for exploration and science planning.','ESA/DLR/FU-Berlin/NASA/JPL-Caltech'),
]
def figure(item,lang,prefix):
 key,es,en,credit=item; data=sources[key]; caption=es if lang=='es' else en
 return f'<figure style="max-width:680px"><img loading="lazy" decoding="async" src="{prefix}{data["file"]}" alt="{html.escape(caption,quote=True)}"><figcaption>{html.escape(caption)}<br>{"Créditos" if lang=="es" else "Credits"}: {html.escape(credit)}. <a href="{data["page"]}" target="_blank" rel="noopener noreferrer">{"Referencia: ficha oficial de NASA" if lang=="es" else "Reference: official NASA page"}</a>.</figcaption></figure>'

raw=Path('C:/Users/ajpal/.codex/attachments/21c02ffa-0b16-4518-a70d-1fafcd72fb95/Texto pegado.txt').read_text(encoding='utf-8-sig')
raw=raw[raw.index('La Interfaz del Smart-Visor:'):raw.index('Referencias en Formato APA 7')]
raw=raw.replace('6.    Cómo llegan los 8 tipos de datos al visor del astronauta','Cómo llegan los datos al visor del astronauta').replace('7.     Para no saturar','Para no saturar').replace('image.png relativos al hábitat','en un sistema de referencia relativo al hábitat')
raw=raw.replace('Para que los jueces entiendan que es un sistema de ingeniería real, muestren este flujo en 4 pasos:', 'La propuesta se organiza en cuatro etapas de flujo de datos:')
raw=raw.replace('Este flujo está basado en la arquitectura real que usa la NASA en su laboratorio de trajes espaciales (SUITS y trajes xEMU):','El siguiente flujo describe la arquitectura conceptual del proyecto, inspirada en investigación de interfaces y trajes espaciales:')
raw=raw.replace('dividan el proceso en 4 pasos técnicos secuenciales.','el proceso se divide en cuatro pasos técnicos secuenciales.')
lines=[x.strip() for x in raw.splitlines() if x.strip()]
es=[]; i=0
while i<len(lines):
 line=lines[i]
 if line=='Tipo de Dato':
  headers=lines[i:i+3]; rows=lines[i+3:i+21]
  es.append('<div style="overflow-x:auto"><table><thead><tr>'+''.join('<th scope="col">'+html.escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>')
  for j in range(0,18,3): es.append('<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in rows[j:j+3])+'</tr>')
  es.append('</tbody></table></div>'); i+=21; continue
 heading= line.startswith(('La Interfaz','1. Proyección','2. Control','Ejemplo de Escenario','Cómo llegan','Cómo explicar','Paso 1:','Paso 2:','Paso 3:','Paso 4:'))
 tag='h2' if line.startswith('La Interfaz') else ('h3' if heading else 'p')
 es.append(f'<{tag}>{html.escape(line)}</{tag}>'); i+=1
english='''<h2>The Smart-Visor interface: optical waveguide HUD and neural voice control</h2>
<p>This project proposes a transparent augmented-reality display and an onboard voice assistant to help an astronaut access information while wearing stiff, pressurized EVA gloves.</p>
<h3>1. Visual display: optical waveguides and micro-LED arrays</h3>
<p>A transparent optical combiner in front of the eyes would display information without projecting onto the curved pressure bubble. Cyan, green and amber graphics would provide contrast against the Martian terrain. A route prepared at the habitat would appear as a three-dimensional overlay aligned with the ground.</p>
<h3>2. Hands-free interaction: eye tracking and onboard voice processing</h3>
<p>In this concept, cameras inside the helmet track gaze to highlight waypoints, menus and geological targets. A local language processor handles spoken commands to show or hide data layers while the astronaut holds tools. The proposed computing system is associated with the suit's Portable Life Support System (PLSS).</p>
<h3>Example operational sequence</h3>
<p>Before the EVA, the mission team loads a route and scientific targets for Jezero's western delta. The astronaut requests “Load route alpha,” and the visor displays the planned path. Gaze and voice can select geology or radiation layers. An emergency warning would prioritize critical information and propose a return route. Local radio beacons and deployed repeaters are proposed for positioning corrections; Perseverance is not an operational astronaut Wi-Fi beacon.</p>
<h3>How data would reach the visor</h3>
<p>The proposed layers combine archived orbital products, local observations and future suit sensors. Instrument names below are scientific precedents, not equipment already integrated into this helmet.</p>
<div style="overflow-x:auto"><table><thead><tr><th>Data</th><th>Source or proposed sensor</th><th>Proposed display</th></tr></thead><tbody>
<tr><td>Topography and imagery</td><td>HiRISE products; proposed stereo cameras and LiDAR.</td><td>Waypoints, route lines and terrain warnings.</td></tr>
<tr><td>Thermal and spectral</td><td>THEMIS and CRISM products; proposed infrared cameras.</td><td>Optional thermal and mineral layers, with measurement time and limitations.</td></tr>
<tr><td>Geophysics</td><td>RIMFAX and InSight as scientific precedents.</td><td>Subsurface or seismic information where supporting observations exist.</td></tr>
<tr><td>Atmosphere</td><td>MEDA as a precedent; proposed local weather station and suit barometer.</td><td>Pressure, temperature, wind and validated weather alerts.</td></tr>
<tr><td>Radiation</td><td>RAD as a precedent; proposed personal dosimeter.</td><td>Accumulated dose and warnings based on measurements.</td></tr>
<tr><td>Chemistry</td><td>SuperCam and PIXL as precedents for future analytical tools.</td><td>Sample composition only when supported by a suitable measurement.</td></tr>
</tbody></table></div>
<h3>Proposed technical architecture</h3>
<p>Orbital layers (MRO / Odyssey) provide mapping context. Surface nodes at the habitat or future rovers process local observations and communications. Proposed suit computing integrates positioning, sensor inputs and route data. The AR visor displays prioritized alerts and navigation cues.</p>
<h3>Step 1: route preparation at the habitat</h3>
<p>The mission team plans the traverse using terrain data and packages waypoints, exclusion polygons and scientific targets as JSON, GeoJSON or another agreed format. Coordinates must specify the Martian reference system; example slope thresholds require mission-specific validation.</p>
<h3>Step 2: transfer to the suit</h3>
<p>The concept allows a wired pre-EVA transfer or a local wireless update. Umbilical connections, Wi-Fi, UWB and disruption-tolerant networking are design options mentioned in the proposal, not verified capabilities of a deployed Mars suit.</p>
<h3>Step 3: spatial alignment</h3>
<p>Proposed visual SLAM and LiDAR compare local terrain observations with the planned route. Onboard processing estimates pose and generates the graphics. Uncertainty and loss of alignment must be considered before operational use.</p>
<h3>Step 4: internal transmission and display</h3>
<p>A proposed sealed power/data connection sends graphics to the helmet controller. Micro-LED projection and optical waveguides would place arrows, text and route lines in the astronaut's field of view. This model illustrates the concept; it does not implement tracking, sensors or a working HUD.</p>'''

helmet=Path('C:/Users/ajpal/Downloads/Casco (1).glb')
blob=helmet.read_bytes(); magic,version,length=struct.unpack_from('<4sII',blob)
assert magic==b'glTF' and version==2 and length==len(blob)
jsonsize=struct.unpack_from('<I',blob,12)[0]; gltf=json.loads(blob[20:20+jsonsize])
assert all(not x.get('uri') or x['uri'].startswith('data:') for x in gltf.get('buffers',[])+gltf.get('images',[]))
shutil.copyfile(helmet,assets/'casco.glb')

def fifth(prefix):
 note_es='Propuesta conceptual del equipo: el modelo 3D y la arquitectura descrita no son un casco operativo ni un sistema certificado por NASA. Los ejemplos de pendientes, temperaturas, detección química, alertas y enlaces de comunicaciones son escenarios de diseño, no mediciones del casco ni capacidades demostradas en Marte.'
 note_en='Team concept: the 3D model and architecture are not an operational helmet or a NASA-certified system. Example slopes, temperatures, chemical detection, alerts and communication links describe design scenarios, not helmet measurements or demonstrated capabilities on Mars.'
 return '''<section class="panel" id="smart-visor-panel">
<style>#smart-visor-panel model-viewer{display:block;width:100%;height:500px;max-height:70vh;background:#080d16;border:6px solid #0026ff;border-radius:12px;box-sizing:border-box}html[lang|="es"] #smart-visor-panel .visor-en,html:not([lang|="es"]) #smart-visor-panel .visor-es{display:none}#smart-visor-panel table{width:100%}#smart-visor-panel th,#smart-visor-panel td{padding:12px;vertical-align:top}#smart-visor-panel button{cursor:pointer;padding:12px 18px}</style>
<div class="visor-es" lang="es"><h2>Smart-Visor: modelo 3D del casco</h2><p>''' + note_es + '''</p></div>
<div class="visor-en" lang="en"><h2>Smart-Visor: 3D helmet model</h2><p>''' + note_en + '''</p></div>
<figure style="width:100%;max-width:900px">
<model-viewer id="smart-visor-model" camera-controls touch-action="pan-y" shadow-intensity="1" exposure="1" alt="Smart-Visor 3D helmet / Casco Smart-Visor 3D"></model-viewer>
<button type="button" id="smart-visor-load"><span class="visor-es">Cargar casco 3D (61 MB)</span><span class="visor-en">Load 3D helmet (61 MB)</span></button>
<button type="button" id="smart-visor-reset" hidden><span class="visor-es">Restablecer vista</span><span class="visor-en">Reset view</span></button>
<p id="smart-visor-status" role="status" aria-live="polite"></p>
<figcaption><span class="visor-es">Modelo proporcionado por el equipo del proyecto: Casco (1).glb. Arrastra para girar; usa la rueda o pellizca para acercar. Representación conceptual, no modelo oficial de NASA.</span><span class="visor-en">Model supplied by the project team: Casco (1).glb. Drag to orbit; scroll or pinch to zoom. Conceptual representation, not an official NASA model.</span> <a href="'''+prefix+'''casco.glb" download>GLB</a></figcaption></figure>
<div class="visor-es" lang="es">'''+''.join(es)+'''</div><div class="visor-en" lang="en">'''+english+'''</div>
<p><a href="https://www.nasa.gov/get-involved/spacesuit-user-interface-technologies-for-students-suits/" target="_blank" rel="noopener noreferrer">NASA SUITS — referencia de investigación / research reference</a></p>
<script>(()=>{const panel=document.getElementById('smart-visor-panel'),viewer=panel.querySelector('model-viewer'),load=panel.querySelector('#smart-visor-load'),reset=panel.querySelector('#smart-visor-reset'),status=panel.querySelector('[role=status]');let state='idle';const messages={idle:['',''],loading:['Cargando el modelo 3D…','Loading the 3D model…'],ready:['Modelo listo. Puedes girarlo y acercarlo.','Model ready. You can orbit and zoom.'],error:['No se pudo cargar el modelo. Reintenta o descarga el archivo GLB.','The model could not load. Retry or download the GLB file.']};function update(){status.textContent=messages[state][document.documentElement.lang.startsWith('es')?0:1]}new MutationObserver(update).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});viewer.addEventListener('load',()=>{state='ready';load.hidden=true;reset.hidden=false;update()});viewer.addEventListener('error',()=>{state='error';load.disabled=false;update()});viewer.addEventListener('progress',event=>{if(state==='loading'){update();status.textContent+=' '+Math.round(event.detail.totalProgress*100)+'%'}});load.addEventListener('click',async()=>{state='loading';load.disabled=true;update();try{await import('''+json.dumps(prefix+'model-viewer.min.js')+''');await customElements.whenDefined('model-viewer');viewer.src='''+json.dumps(prefix+'casco.glb')+'''}catch(error){state='error';load.disabled=false;update()}});reset.addEventListener('click',()=>{viewer.cameraOrbit='auto auto auto';viewer.cameraTarget='auto auto auto';viewer.fieldOfView='auto';viewer.jumpCameraToGoal()})})();</script>
</section>'''

for file in [published]:
 original=file.read_bytes(); text=original.decode('utf-8'); newline='\r\n' if '\r\n' in text else '\n'
 matches=list(re.finditer(r'<section class="panel"[^>]*>[\s\S]*?</section>',text)); assert len(matches)==6,len(matches)
 fourth=matches[3].group(); fifth_old=matches[4].group()
 prefix='../docs/assets/survival-guide/' if file==source else './assets/survival-guide/'
 n=[0]
 def insert(m):
  idx=n[0]%13; lang='es' if n[0]<13 else 'en'; n[0]+=1
  return m.group()+newline+figure(images[idx],lang,prefix)
 fourth=re.sub(r'<h3>\d+\.[^<]*</h3>',insert,fourth); assert n[0]==26,n
 result=text[:matches[3].start()]+fourth+text[matches[3].end():matches[4].start()]+fifth(prefix).replace('\n',newline)+text[matches[4].end():]
 # Outside the two requested panels, every byte must remain unchanged.
 normalized=result.replace(fourth,matches[3].group(),1).replace(fifth(prefix).replace('\n',newline),fifth_old,1)
 assert normalized==text
 file.write_bytes(result.encode('utf-8'))
 assert 'Emily Paola' not in result
for p,digest in protected.items(): assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
archive=root/'Mapa-Marte-LIA-Netlify.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in (root/'docs').rglob('*'):
  if p.is_file(): z.write(p,p.relative_to(root/'docs').as_posix())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert z.read('index.html')==published.read_bytes()
 assert z.read('assets/survival-guide/casco.glb')==blob
print('Updated panels 4 and 5 only; protected pages unchanged; GLB and ZIP verified.')
print('GLB meshes:',len(gltf.get('meshes',[])),'materials:',len(gltf.get('materials',[])))

