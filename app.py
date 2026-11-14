"""Local NASA-only Mars mission planning demonstrator."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).parent
MISSIONS_PATH = ROOT / "data" / "missions.json"
HOST = "127.0.0.1"
PORT = 8000
NASA_PREFIXES = (
    "https://www.nasa.gov/",
    "https://science.nasa.gov/",
    "https://trek.nasa.gov/",
    "https://ntrs.nasa.gov/",
    "https://ssd.jpl.nasa.gov/",
    "https://www.jpl.nasa.gov/",
    "https://www1.grc.nasa.gov/",
)


def load_missions() -> list[dict[str, str]]:
    with MISSIONS_PATH.open(encoding="utf-8") as file:
        missions = json.load(file)
    for item in missions:
        if not item.get("source", "").startswith(NASA_PREFIXES):
            raise ValueError(f"Non-NASA source found: {item.get('source')}")
    return missions


class MarsMapHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route == "/":
            self._send("text/html; charset=utf-8", render_page())
        elif route == "/api/missions":
            self._send("application/json; charset=utf-8", json.dumps(load_missions()))
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _send(self, content_type: str, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def render_page() -> str:
    return """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mars Mission Map | NASA data demonstrator</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;--bg:#0e1117;--panel:#171d27;--line:#344052;--accent:#ff9d5c;--blue:#8bc7ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#edf0f5;line-height:1.45}
header{padding:1.2rem 1.5rem;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:1rem;align-items:center}
header small,.muted{color:#aeb8c7}main{max-width:1400px;margin:auto;padding:1rem;display:grid;gap:1rem}
.hero,.panel{background:var(--panel);border:1px solid var(--line);border-radius:.7rem;padding:1rem}
.hero{border-color:#9b6b27;background:linear-gradient(120deg,#2c2118,#171d27)}
.grid{display:grid;grid-template-columns:1.3fr 1fr;gap:1rem}.two{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
h1,h2,h3{margin-top:0}h1{font-size:clamp(1.5rem,3vw,2.4rem)}h2{color:var(--accent)}
a{color:var(--blue)}button,select,input{font:inherit;border:1px solid var(--line);border-radius:.4rem;padding:.55rem;background:#10151d;color:inherit}
button{cursor:pointer;background:#5d321d;border-color:#b56e3b}button:hover{background:#7c4528}
.map{position:relative;min-height:410px;overflow:hidden;border-radius:.5rem;background:#231b1c;
background-image:radial-gradient(circle at 42% 42%,#9f4f31 0 2%,transparent 2.2%),radial-gradient(circle at 70% 27%,#793b2d 0 5%,transparent 5.3%),radial-gradient(circle at 23% 68%,#713c32 0 7%,transparent 7.3%),linear-gradient(145deg,#9a4935,#3b2528 46%,#171a22)}
.map:after{content:"";position:absolute;inset:0;opacity:.22;background-image:repeating-radial-gradient(ellipse at 30% 20%,transparent 0 18px,#d88e62 19px 20px,transparent 21px 42px)}
.marker{position:absolute;z-index:1;transform:translate(-50%,-50%);background:var(--accent);color:#1b100b;border:2px solid #fff;border-radius:50%;width:1.35rem;height:1.35rem;text-align:center;font-weight:bold;cursor:pointer}
.marker span{position:absolute;left:1.4rem;top:-.3rem;white-space:nowrap;color:#fff;font-size:.8rem;text-shadow:0 1px 3px #000}
.legend{display:flex;gap:1rem;flex-wrap:wrap;font-size:.85rem;color:#c5cfdb}.legend i{display:inline-block;width:.7rem;height:.7rem;border-radius:50%;background:var(--accent)}
.facts{display:grid;grid-template-columns:repeat(2,1fr);gap:.6rem}.fact{padding:.7rem;background:#10151d;border-radius:.4rem}.fact strong{display:block;color:var(--accent);font-size:1.15rem}
.tabs{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:1rem}.tab{background:#10151d}.tab.active{background:#9b4e29}
.tabcontent{display:none}.tabcontent.active{display:block}.mission{padding:.7rem 0;border-top:1px solid var(--line)}
.checklist label{display:block;padding:.45rem 0}.source{font-size:.85rem}.warning{border-left:3px solid #e3b341;padding:.4rem .7rem;background:#241f13}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:.45rem;border-bottom:1px solid var(--line);vertical-align:top}
@media(max-width:850px){.grid,.two{grid-template-columns:1fr}header{display:block}.map{min-height:320px}}
</style>
</head>
<body>
<header><div><strong>MARS MISSION MAP</strong><br><small>NASA-only evidence interface · local mode</small></div>
<a href="https://trek.nasa.gov/marsbeta/" target="_blank" rel="noreferrer">Abrir NASA Mars Trek ↗</a></header>
<main>
<section class="hero"><h1>Planificación informada, no una promesa de seguridad</h1>
<p>El mapa externo puede bloquearse al incrustarlo. Esta vista local funciona sin
<code>trek.nasa.gov</code> y separa datos NASA observados de cualquier hipótesis de misión.</p>
<div class="warning"><strong>Regla de evidencia:</strong> las rutas de esta demo son
esquemas educativos; no son rutas aprobadas ni recomendaciones médicas u operativas.</div></section>
<section class="grid"><div class="panel"><h2>Selector de zona documentada</h2>
<select id="zone"><option value="jezero">Jezero Crater · Perseverance</option>
<option value="gale">Gale Crater · Curiosity</option><option value="utopia">Utopia Planitia · SHARAD</option></select>
<div class="map" id="map"><button class="marker" style="left:42%;top:43%" data-zone="jezero" title="Jezero">P<span>Jezero</span></button>
<button class="marker" style="left:68%;top:30%" data-zone="gale" title="Gale">G<span>Gale</span></button>
<button class="marker" style="left:25%;top:68%" data-zone="utopia" title="Utopia">U<span>Utopia</span></button></div>
<div class="legend"><span><i></i> lugar documentado por NASA</span><span>fondo esquemático, no topografía</span></div>
<p id="zone-info" class="muted"></p></div>
<div class="panel"><h2>Condiciones y límites</h2><div class="facts">
<div class="fact"><strong>95.3%</strong>CO₂ atmosférico</div><div class="fact"><strong>~6.1 mbar</strong>presión superficial</div>
<div class="fact"><strong>-65 °C</strong>temperatura mediana</div><div class="fact"><strong>~210 µGy/día</strong>GCR observada por RAD</div>
<div class="fact"><strong>3.7 m/s²</strong>gravedad ecuatorial</div><div class="fact"><strong>0–22 min</strong>retardo de comunicación</div>
</div><p class="muted">RAD publica una dosis absorbida en microgray/día; no se convierte
automáticamente a mSv porque la equivalencia depende del tipo de radiación y del factor de ponderación.</p></div></section>
<section class="panel"><div class="tabs"><button class="tab active" data-tab="hazards">Peligros</button>
<button class="tab" data-tab="isru">Supervivencia e ISRU</button><button class="tab" data-tab="calculator">Recursos</button>
<button class="tab" data-tab="emergency">Emergencias</button><button class="tab" data-tab="sources">Referencias</button></div>
<div id="hazards" class="tabcontent active"><div class="two">
<article><h3>Atmósfera y presión</h3><p>NASA describe una atmósfera extremadamente delgada, principalmente CO₂.
Sin un sistema presurizado y suministro de oxígeno, no hay condiciones respirables;
la baja presión hace que el agua hierva cerca de la temperatura corporal (ebullismo).
La interfaz lo marca como peligro inmediato, no como un cronómetro médico inventado.</p>
<h3>Temperatura y polvo</h3><p>NASA sitúa la temperatura mediana en -65 °C y el rango aproximado
entre 20 °C y -153 °C. El polvo puede permanecer meses en suspensión tras tormentas y
requiere control de entrada, filtros y protección de equipos.</p></article>
<article><h3>Radiación y gravedad</h3><p>El instrumento RAD de Curiosity observó unos 210 µGy/día de radiación
cósmica galáctica en superficie durante sus primeras mediciones. Los eventos solares
son variables; una tormenta exige refugio y evaluación de exposición.</p><p>Marte tiene
gravedad ecuatorial de 3.71 m/s². NASA estudia pérdida ósea, atrofia muscular y el
síndrome neuro-ocular asociado a vuelos espaciales (SANS) como riesgos de misiones largas.</p></article>
</div></div>
<div id="isru" class="tabcontent"><div class="two"><article><h3>Agua</h3><p>SHARAD, radar de MRO, detecta depósitos subsuperficiales ricos en hielo,
incluido un depósito estudiado en Utopia Planitia. La extracción es una opción de
arquitectura a validar, no una capacidad demostrada por esta web.</p><h3>Oxígeno</h3>
<p>MOXIE demostró separar oxígeno del CO₂ marciano. NASA estima que una misión humana
necesitaría una versión aproximadamente 100 veces mayor para producir propelente.</p></article>
<article><h3>Hábitat y soporte vital</h3><p>El concepto debe combinar refugio contra radiación,
control de polvo, presión y un ECLSS regenerativo. En la ISS, NASA ha demostrado una
recuperación de agua cercana al 98%; es una referencia tecnológica, no una garantía marciana.</p>
<h3>Autonomía humana</h3><p>CHAPEA simula aislamiento, recursos limitados, cultivos y retardos
de comunicación en un hábitat de 1,700 pies² con tripulaciones de cuatro personas.</p></article>
</div></div>
<div id="calculator" class="tabcontent"><h3>Estimador transparente de consumibles</h3>
<p class="muted">Supuestos editables para exploración educativa. No son requisitos oficiales de una misión Marte.</p>
<label>Astronautas <input id="crew" type="number" min="1" value="4"></label>
<label>Días <input id="days" type="number" min="1" value="30"></label>
<table><tbody><tr><th>Concepto</th><th>Resultado</th><th>Base</th></tr>
<tr><td>Agua de consumo/higiene</td><td id="water"></td><td>1 galón por astronauta/día (NASA ECLSS)</td></tr>
<tr><td>Agua no recuperada</td><td id="loss"></td><td>2% si se alcanza recuperación del 98% ISS</td></tr>
<tr><td>Oxígeno de respiración</td><td>Debe definirse con un modelo ECLSS validado</td><td>No inventado en esta demo</td></tr></tbody></table></div>
<div id="emergency" class="tabcontent"><h3>Checklist conceptual</h3><div class="checklist">
<label><input type="checkbox"> Tormenta de polvo: confirmar presión, potencia, visibilidad y estado de filtros.</label>
<label><input type="checkbox"> Evento solar: pasar al refugio designado y registrar tiempo de exposición.</label>
<label><input type="checkbox"> Despresurización: aislar el volumen, verificar sellos y abortar la EVA según el procedimiento de misión.</label>
<label><input type="checkbox"> Comunicación degradada: ejecutar el plan autónomo preacordado; no esperar una respuesta en tiempo real.</label>
</div><p class="muted">Los pasos son una estructura de interfaz, no un procedimiento certificado de vuelo.</p></div>
<div id="sources" class="tabcontent"><div id="missions">Cargando referencias NASA…</div></div></section>
</main>
<script>
const zones={jezero:"Jezero: delta antiguo de alto interés científico; NASA identifica dunas, acantilados y rocas como peligros de aterrizaje.",gale:"Gale: lugar de aterrizaje y recorrido de Curiosity; las rutas reales pertenecen a la misión rover.",utopia:"Utopia Planitia: SHARAD de MRO detectó un depósito subsuperficial rico en hielo; la accesibilidad humana no está demostrada."};
const zone=document.querySelector("#zone"),info=document.querySelector("#zone-info");
function setZone(){info.textContent=zones[zone.value];document.querySelectorAll(".marker").forEach(m=>m.style.outline=m.dataset.zone===zone.value?"3px solid white":"none")}
zone.addEventListener("change",setZone);document.querySelectorAll(".marker").forEach(m=>m.addEventListener("click",()=>{zone.value=m.dataset.zone;setZone()}));setZone();
document.querySelectorAll(".tab").forEach(button=>button.addEventListener("click",()=>{document.querySelectorAll(".tab,.tabcontent").forEach(x=>x.classList.remove("active"));button.classList.add("active");document.querySelector("#"+button.dataset.tab).classList.add("active")}));
function calculate(){const crew=Math.max(1,Number(document.querySelector("#crew").value)||1),days=Math.max(1,Number(document.querySelector("#days").value)||1),gallons=crew*days;document.querySelector("#water").textContent=`${gallons.toFixed(1)} gal (${(gallons*3.78541).toFixed(1)} L)`;document.querySelector("#loss").textContent=`${(gallons*.02).toFixed(1)} gal (${(gallons*.02*3.78541).toFixed(1)} L)`}document.querySelectorAll("#crew,#days").forEach(x=>x.addEventListener("input",calculate));calculate();
fetch("/api/missions").then(r=>r.json()).then(items=>document.querySelector("#missions").innerHTML=items.map(x=>`<article class="mission"><strong>${x.name}</strong><p>${x.description}</p><a class="source" href="${x.source}" target="_blank" rel="noreferrer">${x.source}</a></article>`).join("")).catch(()=>document.querySelector("#missions").textContent="No se pudieron cargar las referencias locales.");
</script></body></html>"""


if __name__ == "__main__":
    print(f"Mars Mission Map: http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), MarsMapHandler).serve_forever()
