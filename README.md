# Mars EVA Map · Jezero Crater

An interactive, layered 2D + 3D map for planning a walk on Mars, built in
Python from NASA mission data. It combines orbital imagery, thermal and
topographic maps with the ground truth recorded by the Perseverance rover,
and plans an EVA from the Three Forks sample depot up to the Jezero delta
front along ground the rover has already driven.

## What it shows

| Data type | Mission / instrument | Use in the map |
| --- | --- | --- |
| Optical | Viking, MRO CTX (6 m), MRO HiRISE (25 cm) | Base map and high-resolution overlay |
| Thermal | Mars Odyssey THEMIS day and night IR | Rock versus loose dust or sand |
| Topographic | MGS MOLA + Mars Express HRSC (200 m) | Shaded relief and the 3D terrain |
| In situ | Perseverance waypoints, sols 13–2022 | Route, elevation and rover tilt |
| Radiation | Curiosity RAD | Dose estimate for the EVA and the stay |

- **2D map**: switch NASA layers, fade the high-resolution overlay, click any waypoint.
- **3D terrain**: the western delta and crater rim with both routes draped on it.
- **Planner**: EVA time, radiation dose, oxygen and water for the crew.
- **Hazards, ISRU, emergency checklists and references** in the lower tabs.

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
- `data/eva_route.csv`: the 11 waypoints of the EVA (rover sols 606–648, walked in reverse).
- `data/jezero_dem.csv`: 84 × 36 elevation grid sampled from the Mars Trek MOLA + HRSC image service; add `offset_m` from `config.json` to get metres.
- `data/config.json`: map layers, sites and the reference list.

## Limits

The EVA is a planning sketch, not an approved traverse. Rover tilt is a proxy
for slope, and the tilt colours, walking speed and stop time are assumptions
you can edit. The 3D terrain is 200 m per pixel, too coarse to show boulders.

## References and credits

All data sources are listed in the **Data & references** tab and in
`data/config.json`. Data: NASA/JPL-Caltech, USGS, ASU, University of Arizona,
MSSS, ESA/DLR/FU Berlin (HRSC). Software: Python, Folium, Leaflet, Plotly.
AI assistance: Claude (Anthropic) helped write the code.

---

## Español: inicio rápido

```bash
pip install -r requirements.txt
python app.py
```

Se abre <http://127.0.0.1:8000> con el mapa 2D y 3D. Para publicarlo, activa
GitHub Pages en **Settings → Pages** con la rama `main` y la carpeta `/docs`.
