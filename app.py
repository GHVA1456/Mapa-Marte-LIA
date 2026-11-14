"""Starter server for a NASA-only Mars exploration map.

The geospatial base map is NASA Mars Trek. This project deliberately does not
invent coordinates or operationally safe routes.
"""

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


def load_missions() -> list[dict[str, str]]:
    """Load mission metadata whose source URLs are NASA domains."""
    with MISSIONS_PATH.open(encoding="utf-8") as file:
        missions = json.load(file)

    for mission in missions:
        source = mission.get("source", "")
        nasa_hosts = (
            "https://www.nasa.gov/",
            "https://science.nasa.gov/",
            "https://trek.nasa.gov/",
        )
        if not source.startswith(nasa_hosts):
            raise ValueError(f"Non-NASA source found: {source}")
    return missions


class MarsMapHandler(BaseHTTPRequestHandler):
    """Serve the local UI and a small NASA-sourced metadata endpoint."""

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        route = urlparse(self.path).path

        if route == "/":
            self._send_html(render_page())
        elif route == "/api/missions":
            self._send_json(load_missions())
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _send_html(self, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, body: object) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def render_page() -> str:
    """Return the initial UI; NASA Trek remains the authoritative map."""
    return """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mars Mission Map</title>
  <style>
    :root { color-scheme: dark; font-family: system-ui, sans-serif; }
    body { margin: 0; background: #10131a; color: #edf0f5; }
    header { padding: 1rem 1.25rem; border-bottom: 1px solid #303642; }
    main { display: grid; grid-template-columns: minmax(18rem, 24rem) 1fr;
           min-height: calc(100vh - 76px); }
    aside { padding: 1rem; overflow: auto; border-right: 1px solid #303642; }
    iframe { width: 100%; height: calc(100vh - 76px); border: 0; background: #000; }
    .notice { padding: .8rem; margin: 0 0 1rem; border: 1px solid #9b6b27;
              background: #2a2114; border-radius: .4rem; }
    .mission { padding: .7rem 0; border-top: 1px solid #303642; }
    a { color: #8bc7ff; }
    small { color: #adb5c2; }
    @media (max-width: 800px) {
      main { display: block; }
      iframe { height: 70vh; }
      aside { border-right: 0; }
    }
  </style>
</head>
<body>
  <header>
    <strong>Mars Mission Map</strong>
    <small>Prototipo basado en fuentes NASA</small>
  </header>
  <main>
    <aside>
      <div class="notice">
        <strong>Uso científico</strong>
        <p>La ruta mostrada por NASA Mars Trek no implica que sea segura para
        astronautas. Este prototipo no inventa coordenadas ni rutas operativas.</p>
      </div>
      <h2>Misiones y lugares NASA</h2>
      <div id="missions">Cargando datos NASA…</div>
      <h2>Limitaciones de misión</h2>
      <ul>
        <li>El retardo Tierra-Marte puede llegar aproximadamente a 22 minutos por sentido.</li>
        <li>Las misiones humanas requieren autonomía y autosuficiencia.</li>
        <li>El terreno puede incluir dunas, acantilados y rocas.</li>
      </ul>
      <p><small>Las limitaciones se documentarán con referencias NASA antes
      de convertirse en reglas de planificación.</small></p>
    </aside>
    <iframe title="NASA Mars Trek"
      src="https://trek.nasa.gov/marsbeta/"></iframe>
  </main>
  <script>
    fetch("/api/missions")
      .then(response => response.json())
      .then(missions => {
        document.querySelector("#missions").innerHTML = missions.map(mission => `
          <article class="mission">
            <strong>${mission.name}</strong>
            <p>${mission.description}</p>
            <a href="${mission.source}" target="_blank" rel="noreferrer">
              Fuente NASA
            </a>
          </article>
        `).join("");
      })
      .catch(() => {
        document.querySelector("#missions").textContent =
          "No se pudieron cargar los metadatos.";
      });
  </script>
</body>
</html>"""


if __name__ == "__main__":
    print(f"Mars Mission Map: http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), MarsMapHandler).serve_forever()
