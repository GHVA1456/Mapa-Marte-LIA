"""MARS-NAV: a glove-friendly 2D + 3D walk planner for Jezero's western delta.

Every coordinate, elevation, weather record and map tile comes from the NASA
and USGS sources listed in data/config.json. Run `python app.py` to build
docs/index.html and open it in its own window, or `python app.py --build` to
only rebuild the page. The first run creates a virtual environment in .venv
and installs Folium and Plotly there; nothing is installed system-wide.
"""

import csv
import json
import math
import os
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
DEM = CFG["dem"]
with (DATA / "jezero_ctx_dem.csv").open() as file:  # decimetres above the lowest cell, north row first
    GRID = [[(int(v) + DEM["offset_dm"]) / 10 for v in line.split(",")] for line in file]
ROWS, COLS = len(GRID), len(GRID[0])
SOUTH, EAST = DEM["north"] - ROWS * DEM["cell_deg"], DEM["west"] + COLS * DEM["cell_deg"]
KM_PER_DEG = math.pi * 3389.5 / 180  # Mars mean radius 3389.5 km
KM_PER_DEG_LON = KM_PER_DEG * math.cos(math.radians((SOUTH + DEM["north"]) / 2))
LEAFLET = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet"
# Planning assumption (not a NASA limit): rover tilt at each waypoint as a slope proxy.
SLOPES = [(5, "#3fb950", "gentle"), (10, "#e3b341", "moderate"), (90, "#f85149", "steep")]


def table(name):
    """Read a CSV from data/ as a list of dicts, numbers as floats."""
    def value(text):
        try:
            return float(text)
        except ValueError:
            return text
    with (DATA / name).open(encoding="utf-8") as file:
        return [{k: value(v) for k, v in row.items()} for row in csv.DictReader(file)]


def slope(tilt):
    """Return (colour, label) for a tilt in degrees."""
    return next((colour, label) for limit, colour, label in SLOPES if tilt < limit)


def xy_km(p):
    """Kilometres east and north of the elevation grid's south-west corner."""
    return (p["lon"] - DEM["west"]) * KM_PER_DEG_LON, (p["lat"] - SOUTH) * KM_PER_DEG


def latlon(points):
    return [(p["lat"], p["lon"]) for p in points]


def add_distance(points):
    """Add cumulative walking distance in metres to each waypoint."""
    total = 0.0
    for prev, p in zip([points[0]] + points, points):
        (x0, y0), (x1, y1) = xy_km(prev), xy_km(p)
        total += math.hypot(x1 - x0, y1 - y0) * 1000
        p["dist_m"] = round(total)
    return points


def build_2d(route, eva, extra):
    """Leaflet map in Mars equirectangular coordinates with NASA Trek layers."""
    pad = 0.01  # the map cannot leave the A-to-B area covered by the elevation model
    m = folium.Map(crs="EPSG4326", tiles=None, min_zoom=12, max_zoom=18, max_bounds=True, min_lat=SOUTH - pad,
                   max_lat=DEM["north"] + pad, min_lon=DEM["west"] - pad, max_lon=EAST + pad)
    m.default_css = [("leaflet_css", LEAFLET + ".css")]  # skip Bootstrap and icon fonts we do not use
    m.default_js = [("leaflet", LEAFLET + ".js"), ("jquery", "https://code.jquery.com/jquery-3.7.1.min.js")]
    m.fit_bounds([[min(p["lat"] for p in eva), min(p["lon"] for p in eva)], [max(p["lat"] for p in eva), max(p["lon"] for p in eva)]])
    groups = {}
    for layer in CFG["layers"]:
        tiles = folium.TileLayer(
            CFG["tiles"].replace("{id}", layer["id"]).replace("{ext}", layer["ext"]), name=layer["name"],
            attr="NASA/JPL-Caltech · USGS · Mars Trek", max_native_zoom=layer["zoom"], max_zoom=18,
            **({"bounds": layer["bounds"]} if "bounds" in layer else {})).add_to(m)
        groups.setdefault(layer["group"], []).append(tiles.get_name())
    for scene in CFG["minerals"]:  # real CRISM mineral-indicator images, served by NASA's Planetary Data System
        image = folium.raster_layers.ImageOverlay(scene["url"], scene["bounds"], opacity=0.8, name=scene["name"]).add_to(m)
        groups[scene["group"]] = [image.get_name()]

    big = lambda html: folium.Popup(f'<div class="pop">{html}</div>', max_width=320)
    folium.PolyLine(latlon(route), color="#ffffff", weight=2, opacity=0.7, interactive=False).add_to(m)
    hazards = folium.FeatureGroup("Hazards").add_to(m)
    groups["hazards"] = [hazards.get_name()]
    cell, steep = CFG["hazard"]["cell_deg"], f"<b>RED ZONE · steep slope</b><br>Over {CFG['hazard']['min_slope_deg']}° in the USGS elevation model."
    for run in table("slope_hazard.csv"):
        north, west = DEM["north"] - run["row"] * cell, DEM["west"] + run["col_start"] * cell
        folium.Rectangle([(north - cell, west), (north, DEM["west"] + (run["col_end"] + 1) * cell)], stroke=False,
                         fill_color="#f85149", fill_opacity=0.55, popup=big(steep)).add_to(hazards)
    folium.PolyLine(latlon([eva[0], eva[-1]]), color="#f85149", weight=6, dash_array="4 16", popup=big(
        f"<b>NO-GO · direct line</b><br>{math.dist(xy_km(eva[0]), xy_km(eva[-1])):.1f} km straight across the Séítah "
        "sand ripples. Perseverance drove around their north side instead (JPL).")).add_to(hazards)
    folium.PolyLine(latlon(extra), color="#39d0ff", weight=6, dash_array="2 12", popup=big(
        f"<b>Optional leg · delta front</b><br>{extra[-1]['dist_m']} m climb onto the delta front, rover tilt up to "
        f"{max(p['tilt_deg'] for p in extra):.1f}°.")).add_to(m)
    folium.PolyLine(latlon(eva), color="#0e1117", weight=14, interactive=False).add_to(m)
    for a, b in zip(eva, eva[1:]):
        folium.PolyLine(latlon([a, b]), color=slope(b["tilt_deg"])[0], weight=8, interactive=False).add_to(m)
    for i, p in enumerate(eva):
        colour, label = slope(p["tilt_deg"])
        folium.CircleMarker(
            (p["lat"], p["lon"]), radius=11, color="#0e1117", weight=3, fill_color=colour, fill_opacity=1,
            popup=big(f"<b>Waypoint {i + 1} of {len(eva)}</b><br>{p['dist_m'] / 1000:.2f} km walked · "
                      f"{(eva[-1]['dist_m'] - p['dist_m']) / 1000:.2f} km to go<br>Elevation {p['elev_m']:.0f} m · "
                      f"tilt {p['tilt_deg']:.1f}° ({label})<br>Rover drove here on sol {p['sol']:.0f}")).add_to(m)
    for p, text in ((eva[0], "A · HABITAT · Octavia E. Butler Landing"), (eva[-1], "B · THREE FORKS · delta base")):
        folium.Marker((p["lat"], p["lon"]), icon=folium.DivIcon(html=f'<div class="tag">{text}</div>', icon_anchor=(-16, 16))).add_to(m)
    root = m.get_root()
    root.render()
    return root.header.render(), root.html.render(), root.script.render(), {"map": m.get_name(), "groups": groups}


def ground(p):
    """Bilinear elevation (m) from the USGS grid under a waypoint."""
    c = min(max((p["lon"] - DEM["west"]) / DEM["cell_deg"] - 0.5, 0), COLS - 1.001)
    r = min(max((DEM["north"] - p["lat"]) / DEM["cell_deg"] - 0.5, 0), ROWS - 1.001)
    c0, r0 = int(c), int(r)
    top = GRID[r0][c0] + (GRID[r0][c0 + 1] - GRID[r0][c0]) * (c - c0)
    bottom = GRID[r0 + 1][c0] + (GRID[r0 + 1][c0 + 1] - GRID[r0 + 1][c0]) * (c - c0)
    return top + (bottom - top) * (r - r0)


def build_3d(route, eva, extra):
    """Plotly terrain from the USGS CTX elevation model with the routes draped on it."""
    def line(points, name, colour, width, dash="solid"):
        xs, ys = zip(*map(xy_km, points))
        return go.Scatter3d(x=xs, y=ys, z=[ground(p) + 3 for p in points], mode="lines", name=name,
                            hoverinfo="name", line={"color": colour, "width": width, "dash": dash})

    inside = [p for p in route if DEM["west"] < p["lon"] < EAST and SOUTH < p["lat"] < DEM["north"]]
    ends = [(eva[0], "A · Habitat"), (eva[-1], "B · Three Forks")]
    lx, ly = zip(*(xy_km(p) for p, _ in ends))
    width_km, height_km = COLS * DEM["cell_deg"] * KM_PER_DEG_LON, ROWS * DEM["cell_deg"] * KM_PER_DEG
    relief_km = (max(map(max, GRID)) - min(map(min, GRID))) / 1000
    aspect = {k: {"x": 2, "y": 2 * height_km / width_km, "z": 2 * relief_km * k / width_km} for k in (1, 3, 5)}

    cell, steep = CFG["hazard"]["cell_deg"], []
    for run in table("slope_hazard.csv"):  # centre of every 40 m cell steeper than the limit
        steep += [{"lat": DEM["north"] - (run["row"] + 0.5) * cell, "lon": DEM["west"] + (c + 0.5) * cell}
                  for c in range(int(run["col_start"]), int(run["col_end"]) + 1)]
    sx, sy = zip(*map(xy_km, steep))

    fig = go.Figure([
        go.Surface(x=[(c + 0.5) * DEM["cell_deg"] * KM_PER_DEG_LON for c in range(COLS)],
                   y=[(ROWS - r - 0.5) * DEM["cell_deg"] * KM_PER_DEG for r in range(ROWS)], z=GRID, name="Terrain",
                   colorscale=[[0, "#2a1711"], [0.35, "#8c3f24"], [0.7, "#d98a52"], [1, "#f7e2c0"]],
                   colorbar={"title": "Elevation (m)", "len": 0.6, "thickness": 14},
                   contours={"z": {"show": True, "start": -2700, "end": -2400, "size": 10, "color": "rgba(0,0,0,0.25)"}},
                   hovertemplate="Elevation %{z:.0f} m<extra></extra>"),
        go.Scatter3d(x=sx, y=sy, z=[ground(p) + 2 for p in steep], mode="markers", hoverinfo="name",
                     name=f"RED ZONE: slope over {CFG['hazard']['min_slope_deg']}°", marker={"size": 4, "color": "#f85149", "symbol": "square"}),
        line(inside, "Perseverance traverse", "#ffffff", 3),
        line([eva[0], eva[-1]], "NO-GO direct line (Séítah sand)", "#f85149", 8, "dash"),
        line(extra, "Optional leg: delta front", "#39d0ff", 8, "dot"),
        line(eva, "EVA route", "#3fb950", 12),
        go.Scatter3d(x=lx, y=ly, z=[ground(p) + 8 for p, _ in ends], mode="markers+text", name="A / B",
                     text=[t for _, t in ends], textposition="top center", textfont={"size": 16}, hoverinfo="text",
                     marker={"size": 7, "color": "#ffffff", "line": {"color": "#0e1117", "width": 2}}),
    ])
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0e1117", margin={"l": 0, "r": 0, "t": 0, "b": 0},
        legend={"x": 0.01, "y": 0.99, "bgcolor": "rgba(14,17,23,0.7)", "font": {"size": 14}}, font={"color": "#edf0f5"},
        scene={"xaxis_title": "East (km)", "yaxis_title": "North (km)", "zaxis_title": "Elevation (m)",
               "aspectmode": "manual", "aspectratio": aspect[3], "camera": {"eye": {"x": 0, "y": -1.5, "z": 1.1}}})
    html = fig.to_html(full_html=False, include_plotlyjs="cdn", div_id="plot3d",
                       config={"displaylogo": False, "responsive": True, "displayModeBar": False})
    return aspect, html


def build_profile(eva):
    """Elevation profile of the walk from rover-measured heights."""
    colours, classes = zip(*(slope(p["tilt_deg"]) for p in eva))
    fig = go.Figure(go.Scatter(
        x=[p["dist_m"] / 1000 for p in eva], y=[p["elev_m"] for p in eva], mode="lines+markers",
        line={"color": "#d98a52", "width": 3}, marker={"size": 14, "color": colours, "line": {"color": "#0e1117", "width": 2}},
        customdata=[(p["tilt_deg"], c) for p, c in zip(eva, classes)],
        hovertemplate="%{x:.2f} km<br>Elevation %{y:.0f} m<br>Tilt %{customdata[0]:.1f}° (%{customdata[1]})<extra></extra>"))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#171d27", plot_bgcolor="#171d27", height=320,
                      font={"size": 15}, margin={"l": 70, "r": 20, "t": 10, "b": 55},
                      xaxis_title="Distance from habitat (km)", yaxis_title="Elevation (m)")
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="profile", config={"displayModeBar": False, "responsive": True})


def build():
    """Write the static site to docs/index.html (the folder GitHub Pages serves)."""
    route, eva = table("perseverance_route.csv"), add_distance(table("eva_route.csv"))
    extra, weather = add_distance(table("delta_front_route.csv")), table("meda_weather.csv")
    head, body, script, names = build_2d(route, eva, extra)
    relief, plot3d = build_3d(route, eva, extra)
    data = {**names, "relief": relief, "eva": eva, "weather": weather, "limits": CFG["limits"],
            "layers": CFG["layers"] + CFG["minerals"], "references": CFG["references"]}
    parts = {"MAP_HEAD": head, "MAP_BODY": body, "MAP_SCRIPT": script, "PLOT3D": plot3d,
             "PROFILE": build_profile(eva), "DATA": json.dumps(data)}
    page = (ROOT / "template.html").read_text(encoding="utf-8")
    for key, value in parts.items():
        page = page.replace("{{" + key + "}}", value)
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(f"Built {OUT / 'index.html'} ({len(page) // 1024} KB)")


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
