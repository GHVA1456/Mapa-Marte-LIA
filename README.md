# MARS-NAV · Jezero Western Delta EVA map

An interactive 2D + 3D map an astronaut can use with pressurised gloves to
plan and follow a walk on Mars. Built in Python from NASA and USGS data only.
The walk goes from a habitat at Octavia E. Butler Landing (18.4446° N,
77.4509° E) to Three Forks at the base of Jezero's western delta, along the
tracks Perseverance drove around the Séítah sand ripples.

## What it shows

| Layer | Source | Use |
| --- | --- | --- |
| Base map | MRO HiRISE 25 cm and CTX 6 m mosaics (NASA/USGS, via Mars Trek) | The real ground |
| Hazards (red) | Slopes over 20° from the USGS Mars 2020 CTX elevation model; Séítah no-go line | Where not to walk |
| Minerals | MRO CRISM scene HRL000040FF, phyllosilicate and carbonate browse products (NASA PDS) | Science targets |
| Weather | MEDA on Perseverance, sols 1130–1133 (NASA) | Temperature, pressure, daylight |
| Thermal | Mars Odyssey THEMIS night infrared | Rock versus loose sand |
| Route | Perseverance waypoints, sols 13–2022 (NASA/JPL) | Position, elevation, tilt |

The program compares three ways from A to B and marks the best one, the one
with the most rover-driven ground:

| Route | Length | Rover-driven |
| --- | --- | --- |
| North loop (best) | 4.91 km | 100% |
| South, then west | 4.02 km | 44% |
| Direct line across Séítah | 2.55 km | 0% |

Interactive tools: route selector, point-by-point navigator with heading and
the reason each key point matters, a walk simulation with a scrubber, a tap
anywhere terrain inspector (elevation, slope, nearest red zone), a departure
time planner with a daylight bar, and a GO / NO-GO banner.

Use **ES / EN** in the map header to switch languages. For a quick demo,
compare the north route with the direct route, then change the departure time
to see how the estimated daylight margin changes. Select **Follow walk** and
press play to follow the simulated explorer with heading and distance cues.
In **3D**, the camera offers **Free view**, **Follow explorer**, and
**First person**. The first-person camera faces the direction of travel on
the CTX terrain, including on the return leg. It projects the Jezero CTX
orbital mosaic from NASA Mars Trek over the USGS relief when the imagery
loads. Throughout the walk from A (Octavia E. Butler Landing) to B (Three Forks),
the WebGL view requests nearby Mars Trek HiRISE imagery and aligns it to the
same terrain coordinates. The two buttons below the view open Mastcam-Z
reference photos. The Three Forks photo shows the sample depot in the area
on sol 693, after the sol 414 endpoint used for the route.
On compatible browsers, WebGL draws the terrain with depth testing
and interpolated shading. The simulated sun follows a local arc estimated
from the selected MEDA sol's sunrise and sunset. Both the first-person and
overview cameras reflect this lighting as the walk progresses.
The original CRISM PNGs in `docs/assets` are embedded in the generated page
for 3D mineral rendering. Their source URLs remain in `data/config.json`.
The original THEMIS tile `docs/assets/themis-9-203-732.png` is also embedded
for both 2D and 3D. Its geographic extent is 77.34375–77.6953125° E and
18.28125–18.6328125° N, covering every route. It comes from the configured
NASA Mars Trek THEMIS layer, tile matrix 9, row 203, column 732.
**View** switches between illustrative day and night lighting. Automatic mode
uses the simulated local time and sunrise/sunset for the selected historical
MEDA sol (1130–1133). MEDA reports temperature extremes for each sol. The
thermal map layer shows nighttime infrared imagery of the terrain. Terrain
figures summarize sampled route points, and red-zone distances are measured
to cell centres.

**Return to habitat** retraces the selected route from the simulated position.
Its ETA uses the assumed walking speed, the selected MEDA sol and the NASA GISS
Mars24 mean-sol conversion. A is a hypothetical habitat at the actual landing
site. Click a route segment or profile point to inspect its rover coverage and
USGS CTX terrain estimates. **Measure two points** uses the map coordinates for
local straight-line distance and bearing, and interpolates elevation only within
the CTX grid. The map links to the mission and terrain sources under Data Sources.

In 2D or 3D, **Measure two points** compares a dashed direct line with the
shortest route through adjacent CTX grid cells that avoid mapped slope hazards.
Select an orange cell to inspect the slope threshold. The custom elevation
profile highlights segments on the map, and its return estimate uses the
selected speed, departure, stop duration and historical MEDA sol. **CTX coverage**
outlines the grid and shades its exterior in 2D.

The top controls also operate in the 3D overview. A and B focus the explorer,
Route restores the overall view, and Hazards toggles slope markers. Thermal
and Minerals project the source imagery onto the elevation surface when the
source permits image loading. Selecting these terrain layers in first person
opens the 3D overview. Thermal and mineral imagery are selected one at a time.

Glove-friendly design: every control is at least 64 px and there is nothing
to type or hover.

## One site, three sections

`app.py` builds the whole site in `docs/`, with one bar at the top to move between sections:

- `index.html`: the survival guide, the home page.
- `map.html`: the MARS-NAV map.
- `mars-survival.html`: the MARS SURVIVAL page.

The guides are copied from the sources listed in `data/config.json`, with the
mission log from `logbook.html` on top. The first landing site marked on the
map starts sol 0; the map and the guides read and write the same log in the
browser's storage, so open them from the same site (the local server, Netlify
or GitHub Pages).

## Run it

```bash
python app.py
```

On Windows you can also double-click `run.bat`. The first run creates a
virtual environment in `.venv`, installs Folium and Plotly inside it, builds
`docs/index.html` and opens the map in its own window (Edge or Chrome app
mode, or your default browser if neither is installed). Close the window to
exit. Use `python app.py --build` to only regenerate the page. An internet
connection is needed because map tiles load live from NASA.

In VS Code, install the recommended **Python** extension, open `app.py` and press `F5`.

## Embed it in another page

`docs/index.html` is a self-contained page. Put it next to your page and add
`<iframe src="index.html" style="width:100%;height:100vh;border:0"></iframe>`.

## Publish it (GitHub Pages)

1. Merge this code into `main`.
2. On GitHub: **Settings → Pages → Build and deployment → Deploy from a branch**.
3. Choose branch `main`, folder `/docs`, then **Save**.
4. The site appears at <https://ghva1456.github.io/Mapa-Marte-LIA/> after a minute or two.

After changing code or data, run `python app.py --build` and commit `docs/index.html`.

## How it works

```
NASA data (data/*.csv, data/config.json)
        │  app.py: Folium (2D) + Plotly (3D) + template.html
        ▼
docs/index.html  ──►  browser loads map tiles from trek.nasa.gov
```

- `data/perseverance_route.csv`: rover waypoints about every 200 m, from NASA's `M20_waypoints.json`.
- `data/eva_route.csv`: the 22 rover waypoints of the north route (landing site, then sols 379–414).
- `data/jezero_ctx_dem.csv`: 66 × 37 elevation grid, 80 m cells averaged from the 20 m USGS model, in decimetres; add `offset_dm` from `config.json`.
- `data/slope_hazard.csv`: runs of 40 m cells where the 20 m USGS model has a slope over 20°.
- `data/meda_weather.csv`: the latest MEDA sols in NASA's public weather feed.
- `data/config.json`: map layers, CRISM image addresses, limits and the reference list.

## Limits

No route is an approved traverse. Stretches no rover has driven are drawn
as straight lines and measured only against the 80 m USGS grid. CRISM images are shown without interpretation.
Wind, UV, radiation and MAVEN data are not included. Speed, the
8 h suit limit, the daylight margin and the tilt colours are editable assumptions.

## References and credits

All data sources are listed in the **Data & references** tab and in
`data/config.json`. Data: NASA/JPL-Caltech, USGS, ASU, University of Arizona,
MSSS, JHU/APL. Software: Python, Folium, Leaflet, Plotly.
AI assistance: Claude (Anthropic) helped write the code.

---

## Español: inicio rápido

```bash
python app.py
```

La primera vez crea el entorno virtual `.venv`, instala las librerías y abre
el mapa en su propia ventana (en Windows también sirve doble clic en `run.bat`). Para publicarlo, activa
GitHub Pages en **Settings → Pages** con la rama `main` y la carpeta `/docs`.
