"""MARS-NAV: a glove-friendly 2D + 3D walk planner for Jezero's western delta.

Every coordinate, elevation, weather record and map tile comes from the NASA
and USGS sources listed in data/config.json. Run `python app.py` to build
the site in docs/ and open it in its own window, or `python app.py --build` to
only rebuild the page. The first run creates a virtual environment in .venv
and installs Folium and Plotly there; nothing is installed system-wide.
"""

import csv
import base64
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import venv
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

if sys.prefix == sys.base_prefix:  # not inside a virtual environment yet: create it and restart inside it
    if not VENV_PYTHON.exists():
        print("Creating the virtual environment in .venv (first run only)...")
        venv.create(VENV, with_pip=True)
    if subprocess.call([str(VENV_PYTHON), "-c", "import folium, plotly"], stderr=subprocess.DEVNULL):
        print("Installing Folium and Plotly into .venv...")
        subprocess.check_call([str(VENV_PYTHON), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")])
    sys.exit(subprocess.call([str(VENV_PYTHON), str(ROOT / "app.py"), *sys.argv[1:]]))

import folium
import plotly.graph_objects as go

DATA, OUT = ROOT / "data", ROOT / "docs"
CFG = json.loads((DATA / "config.json").read_text(encoding="utf-8"))
DEM, HAZARD = CFG["dem"], CFG["hazard"]
with (DATA / "jezero_ctx_dem.csv").open() as file:  # decimetres above the lowest cell, north row first
    GRID = [[(int(v) + DEM["offset_dm"]) / 10 for v in line.split(",")] for line in file]
ROWS, COLS = len(GRID), len(GRID[0])
SOUTH, EAST = DEM["north"] - ROWS * DEM["cell_deg"], DEM["west"] + COLS * DEM["cell_deg"]
KM_PER_DEG = math.pi * 3389.5 / 180  # Mars mean radius 3389.5 km
KM_PER_DEG_LON = KM_PER_DEG * math.cos(math.radians((SOUTH + DEM["north"]) / 2))
LEAFLET = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet"


def table(name):
    """Read a CSV from data/ as a list of dicts, numbers as floats."""
    def value(text):
        try:
            return float(text)
        except ValueError:
            return text
    with (DATA / name).open(encoding="utf-8") as file:
        return [{k: value(v) for k, v in row.items()} for row in csv.DictReader(file)]


def xy_km(p):
    """Kilometres east and north of the elevation grid's south-west corner."""
    return (p["lon"] - DEM["west"]) * KM_PER_DEG_LON, (p["lat"] - SOUTH) * KM_PER_DEG


def metres(a, b):
    return math.dist(xy_km(a), xy_km(b)) * 1000


def ground(p):
    """Bilinear elevation (m) from the USGS grid under a point."""
    c = min(max((p["lon"] - DEM["west"]) / DEM["cell_deg"] - 0.5, 0), COLS - 1.001)
    r = min(max((DEM["north"] - p["lat"]) / DEM["cell_deg"] - 0.5, 0), ROWS - 1.001)
    c0, r0 = int(c), int(r)
    top = GRID[r0][c0] + (GRID[r0][c0 + 1] - GRID[r0][c0]) * (c - c0)
    bottom = GRID[r0 + 1][c0] + (GRID[r0 + 1][c0 + 1] - GRID[r0 + 1][c0]) * (c - c0)
    return top + (bottom - top) * (r - r0)


def terrain_slope(p):
    """Slope in degrees of the 80 m USGS grid around a point."""
    d, shift = DEM["cell_deg"], lambda dlat, dlon: ground({"lat": p["lat"] + dlat, "lon": p["lon"] + dlon})
    east = (shift(0, d) - shift(0, -d)) / (2000 * d * KM_PER_DEG_LON)
    north = (shift(d, 0) - shift(-d, 0)) / (2000 * d * KM_PER_DEG)
    return math.degrees(math.atan(math.hypot(east, north)))


# Centre of every 40 m cell where the 20 m USGS model is steeper than the hazard limit.
STEEP = [{"lat": DEM["north"] - (run["row"] + 0.5) * HAZARD["cell_deg"], "lon": DEM["west"] + (c + 0.5) * HAZARD["cell_deg"]}
         for run in table("slope_hazard.csv") for c in range(int(run["col_start"]), int(run["col_end"]) + 1)]


def straight(a, b, step=100):
    """Points every ~100 m on the straight line from a to b: ground no rover has measured."""
    n = max(round(metres(a, b) / step), 1)
    return [{"lat": a["lat"] + (b["lat"] - a["lat"]) * i / n, "lon": a["lon"] + (b["lon"] - a["lon"]) * i / n} for i in range(1, n + 1)]


def make_route(spec, rover):
    """Build one candidate route and measure it against the rover record and the USGS model."""
    a, b = rover["north"][0], rover["north"][-1]
    driven = {"north": rover["north"], "south": rover["south"], "direct": [a]}[spec["id"]]
    points = [dict(p, verified=True) for p in driven] + ([] if spec["id"] == "north" else straight(driven[-1], b))
    for i, p in enumerate(points):
        if not p.setdefault("verified", False):
            p.update(sol=None, tilt_deg=None, elev_m=round(ground(p), 1))
        p["dist_m"] = round(points[i - 1]["dist_m"] + metres(points[i - 1], p)) if i else 0
        p["slope_deg"] = round(terrain_slope(p), 1)
        p["red_m"] = round(min(metres(p, cell) for cell in STEEP))
        p["notes"] = []
        p["notes_es"] = []
    points[0]["notes"].append(CFG["places"]["A"])
    points[-1]["notes"].append(CFG["places"]["B"])
    points[0]["notes_es"].append("Hábitat en el lugar de aterrizaje Octavia E. Butler, donde Perseverance llegó el 18 de febrero de 2021.")
    points[-1]["notes_es"].append("Three Forks, al pie del delta occidental. Perseverance completó aquí su depósito de diez tubos de muestras en enero de 2023 (JPL).")
    tilted = [p for p in points if p["verified"]]
    notable = [
        (max(points, key=lambda p: p["elev_m"]), "Highest point of this route.", "Punto más alto de la ruta."),
        (max(tilted, key=lambda p: p["tilt_deg"]), "Highest recorded rover tilt.", "Mayor inclinación registrada por el rover."),
        (min(points, key=lambda p: p["red_m"]), "Sampled point closest to a red-zone cell centre.", "Punto muestreado más cercano al centro de una celda roja."),
    ]
    if len(tilted) < len(points):
        notable.append((tilted[-1], "Last rover point. Beyond here the terrain is known only from orbit.",
                        "Último punto del rover. A partir de aquí el terreno se conoce por observaciones orbitales."))
    for point, en, es in notable:
        point["notes"].append(en)
        point["notes_es"].append(es)
    for before, p, after in zip(points, points[1:], points[2:]):
        (x0, y0), (x1, y1), (x2, y2) = xy_km(before), xy_km(p), xy_km(after)
        turn = (math.degrees(math.atan2(x2 - x1, y2 - y1) - math.atan2(x1 - x0, y1 - y0)) + 180) % 360 - 180
        if abs(turn) >= 40:
            p["notes"].append(f"Turn {'right' if turn > 0 else 'left'} about {abs(turn):.0f}° here.")
            direction_es = "derecha" if turn > 0 else "izquierda"
            p["notes_es"].append(f"Gira unos {abs(turn):.0f}° a la {direction_es}.")
    verified_m = sum(q["dist_m"] - p["dist_m"] for p, q in zip(points, points[1:]) if q["verified"])
    return dict(spec, points=points, length_m=points[-1]["dist_m"], verified_pct=round(100 * verified_m / points[-1]["dist_m"]),
                climb_m=round(sum(max(q["elev_m"] - p["elev_m"], 0) for p, q in zip(points, points[1:]))),
                max_tilt=max(p["tilt_deg"] for p in tilted), max_slope=max(p["slope_deg"] for p in points),
                min_red_m=min(p["red_m"] for p in points))


def thermal_image():
    image = OUT / "assets" / "themis-9-203-732.png"
    return "data:image/png;base64," + base64.b64encode(image.read_bytes()).decode("ascii")


def build_2d():
    """Leaflet map in Mars equirectangular coordinates: NASA imagery, CRISM images and red slope zones."""
    pad = 0.01  # the map cannot leave the A-to-B area covered by the elevation model
    m = folium.Map(crs="EPSG4326", tiles=None, min_zoom=12, max_zoom=18, max_bounds=True, min_lat=SOUTH - pad,
                   max_lat=DEM["north"] + pad, min_lon=DEM["west"] - pad, max_lon=EAST + pad)
    m.default_css = [("leaflet_css", LEAFLET + ".css")]  # skip Bootstrap and icon fonts we do not use
    m.default_js = [("leaflet", LEAFLET + ".js")]
    groups = {}
    folium.map.CustomPane("thermal", z_index=250, pointer_events=False).add_to(m)
    for layer in CFG["layers"]:
        if layer["group"] == "thermal":
            thermal = folium.raster_layers.ImageOverlay(
                thermal_image(), [[18.28125, 77.34375], [18.6328125, 77.6953125]],
                name=layer["name"], pane="thermal", opacity=1, pixelated=False,  # smooth, not blocky
                attr="NASA/JPL-Caltech/ASU · Mars Odyssey THEMIS",
            ).add_to(m)
            groups["thermal"] = [thermal.get_name()]
            continue
        tiles = folium.TileLayer(
            CFG["tiles"].replace("{id}", layer["id"]).replace("{ext}", layer["ext"]), name=layer["name"],
            attr="NASA/JPL-Caltech · USGS · Mars Trek", max_native_zoom=layer["zoom"], max_zoom=18,
            pane="thermal" if layer["group"] == "thermal" else "tilePane",
            **({"bounds": layer["bounds"]} if "bounds" in layer else {})).add_to(m)
        groups.setdefault(layer["group"], []).append(tiles.get_name())
    for scene in CFG["minerals"]:  # real CRISM mineral-indicator images, served by NASA's Planetary Data System
        image = folium.raster_layers.ImageOverlay(scene["url"], scene["bounds"], opacity=0.8, name=scene["name"], pixelated=False).add_to(m)
        groups[scene["group"]] = [image.get_name()]
    hazards, half = folium.FeatureGroup("Hazards").add_to(m), HAZARD["cell_deg"] / 2
    groups["hazards"] = [hazards.get_name()]
    for cell in STEEP:
        folium.Rectangle([(cell["lat"] - half, cell["lon"] - half), (cell["lat"] + half, cell["lon"] + half)], stroke=False,
                         fill_color="#f85149", fill_opacity=0.55, interactive=False).add_to(hazards)
    root = m.get_root()
    root.render()
    return root.header.render(), root.html.render(), root.script.render(), {"map": m.get_name(), "groups": groups}


def build_3d(traverse, routes):
    """Plotly terrain from the USGS CTX elevation model with every route draped on it."""
    def trace(points, name, colour, **style):
        xs, ys = zip(*map(xy_km, points))
        return go.Scatter3d(x=xs, y=ys, z=[ground(p) + 3 for p in points], name=name, hoverinfo="name", **style,
                            **({"line": {"color": colour, "width": 4}} if style["mode"] == "lines" else {}))

    inside = [p for p in traverse if DEM["west"] < p["lon"] < EAST and SOUTH < p["lat"] < DEM["north"]]
    ends = routes[0]["points"][::len(routes[0]["points"]) - 1]
    ax, ay = xy_km(ends[0])  # the 3D axes read distance from habitat A
    width_km, height_km = COLS * DEM["cell_deg"] * KM_PER_DEG_LON, ROWS * DEM["cell_deg"] * KM_PER_DEG
    relief_km = (max(map(max, GRID)) - min(map(min, GRID))) / 1000
    aspect = {k: {"x": 2, "y": 2 * height_km / width_km, "z": 2 * relief_km * k / width_km} for k in (1, 3, 5)}
    fig = go.Figure([
        go.Surface(x=[(c + 0.5) * DEM["cell_deg"] * KM_PER_DEG_LON for c in range(COLS)],
                   y=[(ROWS - r - 0.5) * DEM["cell_deg"] * KM_PER_DEG for r in range(ROWS)], z=GRID, name="Terrain",
                   colorscale=[[0, "#2a1711"], [0.35, "#8c3f24"], [0.7, "#d98a52"], [1, "#f7e2c0"]],
                   colorbar={"title": "Elevation (m)", "len": 0.6, "thickness": 14},
                   contours={"z": {"show": True, "start": -2700, "end": -2400, "size": 10, "color": "rgba(0,0,0,0.25)"}},
                   hovertemplate="Elevation %{z:.0f} m<extra></extra>"),
        trace(STEEP, f"Red zone: slope over {HAZARD['min_slope_deg']}°", None, mode="markers", marker={"size": 4, "color": "#f85149", "symbol": "square"}),
        trace(inside, "Perseverance traverse", "#ffffff", mode="lines", opacity=0.6),
        *[trace(r["points"], r["name"], r["colour"], mode="lines") for r in routes],
        trace(ends, "A / B", None, mode="markers+text", text=["A · Habitat", "B · Three Forks"], textposition="top center",
              textfont={"size": 16}, marker={"size": 7, "color": "#ffffff", "line": {"color": "#0e1117", "width": 2}}),
        trace(ends[:1], "Astronaut", None, mode="markers", marker={"size": 9, "color": "#39d0ff", "line": {"color": "#fff", "width": 2}}),
        go.Scatter3d(x=[], y=[], z=[], mode="lines", name="Ruta teórica / Theoretical route", line={"color": "#39d0ff", "width": 8}, hoverinfo="skip"),
        go.Scatter3d(x=[], y=[], z=[], text=[], mode="markers+text", name="P1 / P2", marker={"color": "#fff", "size": 7}, hoverinfo="skip", textposition="top center"),
        go.Scatter3d(x=[], y=[], z=[], mode="markers", name="Celdas de riesgo / Hazard cells", marker={"color": "#ff8e62", "size": 9, "symbol": "diamond"}, hovertemplate="%{text}<extra></extra>"),
        go.Scatter3d(x=[], y=[], z=[], mode="lines", name="Línea directa / Direct line", line={"color": "#fff", "width": 5, "dash": "dash"}, hoverinfo="skip"),
        go.Scatter3d(x=[], y=[], z=[], mode="lines", name="Cobertura CTX / CTX coverage", line={"color": "#e3b341", "width": 4}, hoverinfo="skip"),
        go.Scatter3d(x=[], y=[], z=[], mode="lines+markers", name="Tramo elegido / Selected segment", line={"color": "#ffdf70", "width": 12}, marker={"size": 5, "color": "#ffdf70"}, hoverinfo="skip"),
    ])
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0e1117", margin={"l": 0, "r": 0, "t": 0, "b": 0},
        legend={"x": 0.01, "y": 0.99, "bgcolor": "rgba(14,17,23,0.7)", "font": {"size": 14}}, font={"color": "#edf0f5"},
        scene={"xaxis": {"title": "East of habitat A (km)", "tickvals": [ax + k / 2 for k in range(-8, 3)], "ticktext": [f"{k / 2:g}" for k in range(-8, 3)]},
               "yaxis": {"title": "North of habitat A (km)", "tickvals": [ay + k / 2 for k in range(-4, 7)], "ticktext": [f"{k / 2:g}" for k in range(-4, 7)]},
               "zaxis_title": "Elevation (m)",
               "aspectmode": "manual", "aspectratio": aspect[3], "camera": {"eye": {"x": 0, "y": -1.5, "z": 1.1}}})
    html = fig.to_html(full_html=False, include_plotlyjs="cdn", div_id="plot3d",
                       config={"displaylogo": False, "responsive": True, "displayModeBar": False})
    return aspect, html


def nav(current, native):
    """One bar on every page: sections plus the EN / ES button, whose choice is remembered across the three pages."""
    style = ("font:700 17px system-ui;color:#fff;text-decoration:none;min-height:64px;padding:0 1.2rem;display:inline-flex;"
             "align-items:center;border-radius:.7rem;cursor:pointer;border:2px solid ")
    links = "".join(f'<a href="{page["file"]}" data-label-en="{page["label"]}" data-label-es="{page["label_es"]}" style="{style}'
                    f'{"#ff9d5c;background:#9b4e29" if page["file"] == current else "#46556b;background:#232c3a"}">{page["label"]}</a>'
                    for page in [CFG["guides"][0], CFG["map"], *CFG["guides"][1:]])
    script = """<script>(() => {
  const KEY = "marsnav.lang"; let memory = "%s";
  window.marsnavLang = () => { try { return localStorage.getItem(KEY) || memory; } catch { return memory; } };
  const button = document.getElementById("site-lang");
  const paint = () => { const es = marsnavLang() === "es"; button.textContent = es ? "ENGLISH" : "ESPAÑOL";
    document.querySelectorAll("nav[aria-label=Sections] a").forEach(a => { a.textContent = es ? a.dataset.labelEs : a.dataset.labelEn; }); };
  button.onclick = () => { memory = marsnavLang() === "es" ? "en" : "es"; try { localStorage.setItem(KEY, memory); } catch {} paint(); dispatchEvent(new Event("marsnav-lang")); };
  paint();
})();</script>""" % native
    return (f'<nav aria-label="Sections" style="display:flex;flex-wrap:wrap;gap:.6rem;padding:.7rem 1rem;background:#0e1117">{links}'
            f'<span style="flex:1"></span><button id="site-lang" type="button" style="{style}#39d0ff;background:#232c3a"></button></nav>{script}')


def build():
    """Write the static site to docs/: the survival guide as home page, the map and MARS SURVIVAL as sections."""
    traverse = table("perseverance_route.csv")
    rover = {"north": table("eva_route.csv"), "south": [p for p in traverse if p["sol"] <= CFG["south_until_sol"]]}
    routes = [make_route(spec, rover) for spec in CFG["routes"]]
    best = max(routes, key=lambda r: (r["verified_pct"], -r["length_m"]))  # most rover-proven ground, then shortest
    for r in routes:
        r["best"] = r is best
    head, body, script, names = build_2d()
    relief, plot3d = build_3d(traverse, routes)
    data = {**names, "relief": relief, "routes": routes, "traverse": [(p["lat"], p["lon"]) for p in traverse],
            "weather": table("meda_weather.csv"), "limits": CFG["limits"], "layers": CFG["layers"] + CFG["minerals"],
            "references": CFG["references"], "guides": CFG["guides"], "steep": [(c["lat"], c["lon"]) for c in STEEP], "hazard": HAZARD,
            "dem": {**DEM, "rows": ROWS, "cols": COLS, "grid": GRID, "m_per_deg": [KM_PER_DEG * 1000, KM_PER_DEG_LON * 1000]}}
    ground_layers = {
        "base": "JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0",
        "detail": "JEZ_hirise_soc_006_orthoMosaic_25cm_Eqc_latTs0_lon0_first_dd",
    }
    data["ground_textures"] = {}
    for key, layer_id in ground_layers.items():
        layer = next(layer for layer in CFG["layers"] if layer["id"] == layer_id)
        data["ground_textures"][key] = {
            "zoom": layer["zoom"],
            "url": CFG["tiles"].replace("{id}", layer_id).replace("{ext}", layer["ext"]),
        }
    thermal = next(layer for layer in CFG["layers"] if layer["group"] == "thermal")
    data["thermal_texture"] = {
        "image": thermal_image(),
        "bounds": [[18.28125, 77.34375], [18.6328125, 77.6953125]],
        "zoom": thermal["zoom"],
        "url": CFG["tiles"].replace("{id}", thermal["id"]).replace("{ext}", thermal["ext"]),
    }
    data["mineral_images"] = {}
    for scene in CFG["minerals"]:
        image = OUT / "assets" / f"crism-{scene['group']}.png"
        data["mineral_images"][scene["group"]] = "data:image/png;base64," + base64.b64encode(image.read_bytes()).decode("ascii")
    parts = {"NAV": nav(CFG["map"]["file"], CFG["map"]["lang"]), "MAP_HEAD": head, "MAP_BODY": body, "MAP_SCRIPT": script, "PLOT3D": plot3d, "DATA": json.dumps(data)}
    page = (ROOT / "template.html").read_text(encoding="utf-8")
    for key, value in parts.items():
        page = page.replace("{{" + key + "}}", value)
    OUT.mkdir(exist_ok=True)
    logbook = (ROOT / "logbook.html").read_text(encoding="utf-8")
    translations = json.loads((DATA / "translations.json").read_text(encoding="utf-8"))  # original text -> other language
    for guide in CFG["guides"]:  # copy each survival guide next to the map with the shared mission log on top
        source = (ROOT / guide["source"]).read_text(encoding="utf-8")
        words = json.dumps(translations.get(guide["file"], {}), ensure_ascii=False)
        top = nav(guide["file"], guide["lang"]) + logbook.replace("{{MAP}}", CFG["map"]["file"]).replace("{{NATIVE}}", guide["lang"]).replace("{{WORDS}}", words)
        (OUT / guide["file"]).write_text(re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + top, source, count=1), encoding="utf-8")
    (OUT / CFG["map"]["file"]).write_text(page, encoding="utf-8")
    print(f"Built {OUT / CFG['map']['file']} ({len(page) // 1024} KB). Best route: {best['name']}")
    for r in routes:
        print(f"  {r['name']}: {r['length_m'] / 1000:.2f} km, {r['verified_pct']}% rover-driven, closest red zone {r['min_red_m']} m")


def open_window(url):
    """Open the map as a program window (Edge or Chrome app mode); return the process, or None if neither exists."""
    folders = [os.environ.get(k, "") for k in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
    found = [Path(f) / sub for f in folders if f for sub in ("Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe")]
    found += [Path(p) for name in ("msedge", "google-chrome", "chromium", "chromium-browser") if (p := shutil.which(name))]
    found += [Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    for browser in found:
        if browser.exists():  # its own profile keeps the window a separate process we can wait for
            return subprocess.Popen([str(browser), f"--app={url}", f"--user-data-dir={VENV / 'window'}", "--window-size=1400,950", "--no-first-run"])
    webbrowser.open(url)


if __name__ == "__main__":
    build()
    if "--build" not in sys.argv:
        handler = partial(SimpleHTTPRequestHandler, directory=str(OUT))
        try:
            server = ThreadingHTTPServer(("127.0.0.1", 8000), handler)
        except OSError:  # port 8000 is busy: let the system pick a free one
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        url = f"http://127.0.0.1:{server.server_port}"
        threading.Thread(target=server.serve_forever, daemon=True).start()
        window = open_window(url)
        print(f"MARS-NAV running at {url}. " + ("Close the window to exit." if window else "Press Ctrl+C to exit."))
        try:
            window.wait() if window else threading.Event().wait()
        except KeyboardInterrupt:
            pass
