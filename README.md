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

Glove-friendly design: every control is at least 64 px and there is nothing
to type or hover.

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
