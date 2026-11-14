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
| Radiation | Curiosity RAD, 0.67 mSv/day | Dose for the EVA |

Glove-friendly design: every control is at least 64 px, there is nothing to
type or hover, waypoints are stepped with two large arrows that give heading
and distance to the next one, and a GO / NO-GO banner checks the plan against
daylight and an 8 h suit limit.

## Run it

```bash
pip install -r requirements.txt
python app.py
```

The first run installs Folium and Plotly by itself if they are missing, so the `pip` line is optional.
This builds `docs/index.html` and opens <http://127.0.0.1:8000>. Use
`python app.py --build` to only regenerate the page. An internet connection
is needed because map tiles load live from NASA Mars Trek.

In VS Code, install the recommended **Python** extension, open `app.py` and press `F5`.

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
- `data/eva_route.csv`: the 22 waypoints of the walk (landing site, then rover sols 379–414).
- `data/delta_front_route.csv`: optional climb onto the delta front (rover sols 606–648, reversed).
- `data/jezero_ctx_dem.csv`: 66 × 37 elevation grid, 80 m cells averaged from the 20 m USGS model, in decimetres; add `offset_dm` from `config.json`.
- `data/slope_hazard.csv`: runs of 40 m cells where the 20 m USGS model has a slope over 20°.
- `data/meda_weather.csv`: the latest MEDA sols in NASA's public weather feed.
- `data/config.json`: map layers, CRISM image addresses, limits and the reference list.

## Limits

The route is a planning sketch on rover-driven ground, not an approved
traverse. The straight line from A to B is 2.5 km but crosses Séítah; the
route around it is 4.9 km each way. CRISM images show spectral indicators,
not confirmed deposits. Wind, UV and MAVEN data are not included. Speed, the
8 h suit limit, the daylight margin and the tilt colours are editable assumptions.

## References and credits

All data sources are listed in the **Data & references** tab and in
`data/config.json`. Data: NASA/JPL-Caltech, USGS, ASU, University of Arizona,
MSSS, JHU/APL. Software: Python, Folium, Leaflet, Plotly.
AI assistance: Claude (Anthropic) helped write the code.

---

## Español: inicio rápido

```bash
pip install -r requirements.txt
python app.py
```

Se abre <http://127.0.0.1:8000> con el mapa 2D y 3D. Para publicarlo, activa
GitHub Pages en **Settings → Pages** con la rama `main` y la carpeta `/docs`.
