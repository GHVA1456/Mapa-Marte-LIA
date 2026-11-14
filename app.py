"""Mars EVA Map: a layered 2D + 3D planner for a walk at Jezero Crater.

Every coordinate, elevation and map tile comes from NASA sources listed in
data/config.json. Run `python app.py` to build docs/index.html and open it
locally, or `python app.py --build` to only regenerate the static page.
"""

import csv
import json
import math
import sys
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import folium
import plotly.graph_objects as go
from folium.plugins import Fullscreen, MousePosition

ROOT = Path(__file__).parent
DATA, OUT = ROOT / "data", ROOT / "docs"
CFG = json.loads((DATA / "config.json").read_text(encoding="utf-8"))
DEM = CFG["dem"]
KM_PER_DEG = math.pi * 3389.5 / 180  # Mars mean radius 3389.5 km
KM_PER_DEG_LON = KM_PER_DEG * math.cos(math.radians((DEM["south"] + DEM["north"]) / 2))
LEAFLET = "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet"
# Planning assumption (not a NASA limit): rover tilt at each waypoint as a slope proxy.
SLOPES = [(5, "#3fb950", "gentle"), (10, "#e3b341", "moderate"), (90, "#f85149", "steep")]


def table(name):
    """Read a CSV from data/ as a list of dicts of floats."""
    with (DATA / name).open(encoding="utf-8") as file:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(file)]


def slope(tilt):
    """Return (colour, label) for a tilt in degrees."""
    return next((colour, label) for limit, colour, label in SLOPES if tilt < limit)


def xy_km(p):
    """Kilometres east and north of the DEM's south-west corner."""
    return (p["lon"] - DEM["west"]) * KM_PER_DEG_LON, (p["lat"] - DEM["south"]) * KM_PER_DEG


def add_distance(points):
    """Add cumulative walking distance in metres to each waypoint."""
    total = 0.0
    for prev, p in zip([points[0]] + points, points):
        (x0, y0), (x1, y1) = xy_km(prev), xy_km(p)
        total += math.hypot(x1 - x0, y1 - y0) * 1000
        p["dist_m"] = total
    return points


def build_2d(route, eva):
    """Leaflet map in Mars equirectangular coordinates with NASA Trek layers."""
    m = folium.Map(location=[18.4525, 77.404], zoom_start=14, min_zoom=1, max_zoom=18,
                   crs="EPSG4326", tiles=None, control_scale=False)
    m.default_css = [("leaflet_css", LEAFLET + ".css")]  # skip Bootstrap and icon fonts we do not use
    m.default_js = [("leaflet", LEAFLET + ".js"), ("jquery", "https://code.jquery.com/jquery-3.7.1.min.js")]
    overlays = []
    for i, layer in enumerate(CFG["layers"]):
        local = "bounds" in layer  # high-resolution Jezero mosaics sit on top of the global base maps
        tiles = folium.TileLayer(
            CFG["tiles"].replace("{id}", layer["id"]).replace("{ext}", layer["ext"]),
            name=layer["name"], attr="NASA/JPL-Caltech · Mars Trek", overlay=local, show=local or i == 0,
            max_native_zoom=layer["zoom"], max_zoom=18, **({"bounds": layer["bounds"]} if local else {}),
        ).add_to(m)
        overlays += [tiles.get_name()] if local else []

    traverse = folium.FeatureGroup("Perseverance traverse · tilt by waypoint").add_to(m)
    folium.PolyLine([(p["lat"], p["lon"]) for p in route], color="#ffffff", weight=2, opacity=0.8).add_to(traverse)
    for p in route:
        colour, label = slope(p["tilt_deg"])
        folium.CircleMarker(
            (p["lat"], p["lon"]), radius=3, color=colour, fill=True, fill_opacity=1,
            tooltip=f"Sol {p['sol']:.0f} · {p['elev_m']:.0f} m · tilt {p['tilt_deg']:.1f}° ({label}) · odometer {p['odometer_m'] / 1000:.1f} km",
        ).add_to(traverse)

    walk = folium.FeatureGroup("EVA route · Three Forks to delta front").add_to(m)
    for a, b in zip(eva, eva[1:]):
        folium.PolyLine([(a["lat"], a["lon"]), (b["lat"], b["lon"])], color=slope(b["tilt_deg"])[0], weight=7).add_to(walk)
    for i, p in enumerate(eva):
        colour, label = slope(p["tilt_deg"])
        folium.CircleMarker(
            (p["lat"], p["lon"]), radius=6, color="#0e1117", weight=2, fill_color=colour, fill_opacity=1,
            popup=folium.Popup(
                f"<b>EVA waypoint {i + 1}/{len(eva)}</b><br>{p['lat']:.5f}°N, {p['lon']:.5f}°E<br>"
                f"Elevation {p['elev_m']:.1f} m · rover tilt {p['tilt_deg']:.1f}° ({label})<br>"
                f"{p['dist_m']:.0f} m from start · rover was here on sol {p['sol']:.0f}", max_width=260),
        ).add_to(walk)
    for p, text in ((eva[0], "START · Three Forks depot"), (eva[-1], "SCIENCE STOP · delta front")):
        folium.Marker((p["lat"], p["lon"]), icon=folium.DivIcon(html=f'<div class="tag">{text}</div>', icon_anchor=(-10, 10))).add_to(walk)

    places = folium.FeatureGroup("Reference sites").add_to(m)
    for site in CFG["sites"][1:]:
        point = route[0] if "traverse" in site["name"] else site
        folium.CircleMarker((point["lat"], point["lon"]), radius=7, color="#8bc7ff", weight=3, fill=True,
                            tooltip=site["name"], popup=folium.Popup(site["info"], max_width=260)).add_to(places)

    folium.LayerControl().add_to(m)
    Fullscreen().add_to(m)
    MousePosition(separator=" °N, ", suffix=" °E", num_digits=5).add_to(m)
    root = m.get_root()
    root.render()
    return root.header.render(), root.html.render(), root.script.render(), {"map": m.get_name(), "overlays": overlays}


def build_3d(route, eva):
    """Plotly terrain from the MOLA + HRSC elevation model with both routes draped on it."""
    with (DATA / "jezero_dem.csv").open() as file:
        grid = [[int(v) + DEM["offset_m"] for v in line.split(",")] for line in file]
    rows, cols = len(grid), len(grid[0])
    dx, dy = (DEM["east"] - DEM["west"]) / cols, (DEM["north"] - DEM["south"]) / rows

    def ground(p):
        """Bilinear DEM height under a waypoint, lifted so lines stay visible."""
        c = min(max((p["lon"] - DEM["west"]) / dx - 0.5, 0), cols - 1.001)
        r = min(max((DEM["north"] - p["lat"]) / dy - 0.5, 0), rows - 1.001)
        c0, r0 = int(c), int(r)
        top = grid[r0][c0] + (grid[r0][c0 + 1] - grid[r0][c0]) * (c - c0)
        bottom = grid[r0 + 1][c0] + (grid[r0 + 1][c0 + 1] - grid[r0 + 1][c0]) * (c - c0)
        return top + (bottom - top) * (r - r0) + 12

    def line(points, name, colour, width):
        xs, ys = zip(*map(xy_km, points))
        hover = [f"Sol {p['sol']:.0f}<br>Rover elevation {p['elev_m']:.0f} m<br>Tilt {p['tilt_deg']:.1f}°" for p in points]
        return go.Scatter3d(x=xs, y=ys, z=[ground(p) for p in points], mode="lines", name=name, text=hover,
                            hoverinfo="text+name", line={"color": colour, "width": width})

    labels = [(route[0], "Octavia E. Butler Landing"), (eva[0], "EVA: Three Forks to delta front"),
              (route[-1], f"Perseverance, sol {route[-1]['sol']:.0f}")]
    lx, ly = zip(*(xy_km(p) for p, _ in labels))
    width_km, height_km = (DEM["east"] - DEM["west"]) * KM_PER_DEG_LON, (DEM["north"] - DEM["south"]) * KM_PER_DEG
    relief_km = (max(map(max, grid)) - min(map(min, grid))) / 1000
    aspect = {k: {"x": 2, "y": 2 * height_km / width_km, "z": 2 * relief_km * k / width_km} for k in (1, 3, 6)}

    fig = go.Figure([
        go.Surface(x=[(c + 0.5) * dx * KM_PER_DEG_LON for c in range(cols)],
                   y=[(rows - r - 0.5) * dy * KM_PER_DEG for r in range(rows)], z=grid, name="Terrain",
                   colorscale=[[0, "#2a1711"], [0.35, "#8c3f24"], [0.7, "#d98a52"], [1, "#f7e2c0"]],
                   colorbar={"title": "Elevation (m)", "len": 0.6, "thickness": 12},
                   contours={"z": {"show": True, "start": -2700, "end": -1600, "size": 50, "color": "rgba(0,0,0,0.25)"}},
                   hovertemplate="%{x:.2f} km E, %{y:.2f} km N<br>Elevation %{z:.0f} m<extra></extra>"),
        line(route, "Perseverance traverse", "#ffffff", 4),
        line(eva, "EVA route", "#39d0ff", 10),
        go.Scatter3d(x=lx, y=ly, z=[ground(p) + 25 for p, _ in labels], mode="markers+text", name="Sites",
                     text=[t for _, t in labels], textposition="top center", hoverinfo="text",
                     marker={"size": 5, "color": "#39d0ff", "line": {"color": "#fff", "width": 1}}),
    ])
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0e1117", margin={"l": 0, "r": 0, "t": 0, "b": 0}, height=560,
        legend={"x": 0.01, "y": 0.99, "bgcolor": "rgba(14,17,23,0.7)"}, font={"color": "#edf0f5"},
        scene={"xaxis_title": "East (km)", "yaxis_title": "North (km)", "zaxis_title": "Elevation (m)",
               "aspectmode": "manual", "aspectratio": aspect[3], "camera": {"eye": {"x": 0.3, "y": -1.5, "z": 0.8}}},
    )
    return aspect, fig.to_html(full_html=False, include_plotlyjs="cdn", div_id="plot3d", config={"displaylogo": False, "responsive": True})


def build_profile(eva):
    """Elevation profile of the EVA from rover-measured heights."""
    colours, classes = zip(*(slope(p["tilt_deg"]) for p in eva))
    fig = go.Figure(go.Scatter(
        x=[p["dist_m"] for p in eva], y=[p["elev_m"] for p in eva], mode="lines+markers",
        line={"color": "#d98a52"}, marker={"size": 11, "color": colours, "line": {"color": "#0e1117", "width": 2}},
        customdata=[(p["tilt_deg"], c, p["sol"]) for p, c in zip(eva, classes)],
        hovertemplate="%{x:.0f} m from start<br>Elevation %{y:.1f} m<br>Tilt %{customdata[0]:.1f}° (%{customdata[1]})<br>Rover sol %{customdata[2]:.0f}<extra></extra>"))
    low, high = min(p["elev_m"] for p in eva), max(p["elev_m"] for p in eva)
    fig.update_layout(template="plotly_dark", paper_bgcolor="#171d27", plot_bgcolor="#171d27", height=300,
                      margin={"l": 60, "r": 20, "t": 10, "b": 45}, xaxis_title="Distance walked from Three Forks (m)",
                      yaxis={"title": "Elevation (m, rover)", "range": [low - 5, high + 5]})
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id="profile", config={"displaylogo": False, "responsive": True})


def build():
    """Write the static site to docs/index.html (the folder GitHub Pages serves)."""
    route, eva = table("perseverance_route.csv"), add_distance(table("eva_route.csv"))
    head, body, script, names = build_2d(route, eva)
    climbs = [max(b["elev_m"] - a["elev_m"], 0) for a, b in zip(eva, eva[1:])]
    relief, plot3d = build_3d(route, eva)
    data = {**names, "relief": relief, "sites": CFG["sites"], "references": CFG["references"],
            "eva": {"distance_m": round(eva[-1]["dist_m"]), "climb_m": round(sum(climbs), 1),
                    "max_tilt": max(p["tilt_deg"] for p in eva), "waypoints": len(eva),
                    "steep": sum(p["tilt_deg"] >= SLOPES[1][0] for p in eva)}}
    parts = {"MAP_HEAD": head, "MAP_BODY": body, "MAP_SCRIPT": script, "PLOT3D": plot3d,
             "PROFILE": build_profile(eva), "DATA": json.dumps(data)}
    page = (ROOT / "template.html").read_text(encoding="utf-8")
    for key, value in parts.items():
        page = page.replace("{{" + key + "}}", value)
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(f"Built {OUT / 'index.html'} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    build()
    if "--build" not in sys.argv:
        url = "http://127.0.0.1:8000"
        print(f"Mars EVA Map running at {url} (Ctrl+C to stop)")
        webbrowser.open(url)
        ThreadingHTTPServer(("127.0.0.1", 8000), partial(SimpleHTTPRequestHandler, directory=OUT)).serve_forever()
