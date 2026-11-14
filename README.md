# Mapa-Marte-LIA

Prototipo en Python de un mapa interactivo de Marte basado en fuentes de la
NASA. NASA Mars Trek se integra como mapa geoespacial principal; el proyecto
no inventa coordenadas ni clasifica rutas como seguras para astronautas.

## Ejecutar localmente

```bash
python3 app.py
```

Abre <http://127.0.0.1:8000>.

## Contenido

- `app.py`: servidor HTTP y página interactiva.
- `data/missions.json`: metadatos con enlaces de fuentes NASA.
- `/api/missions`: endpoint JSON de los puntos documentados.

Las capas cartográficas y los recorridos deben consultarse en
[NASA Mars Trek](https://trek.nasa.gov/marsbeta/) o en los mapas oficiales de
cada misión antes de incorporarse como datos locales.
