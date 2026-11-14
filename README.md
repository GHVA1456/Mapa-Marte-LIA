# Mapa-Marte-LIA

Prototipo en Python de un mapa interactivo de Marte basado en fuentes de la
NASA. La interfaz local funciona aunque NASA Mars Trek rechace una conexión
incrustada (`iframe`); el botón superior abre Mars Trek directamente en una
pestaña nueva. El proyecto no inventa coordenadas ni clasifica rutas como
seguras para astronautas.

## Ejecutar localmente

```bash
python3 app.py
```

Abre <http://127.0.0.1:8000>.

### Ejecutar desde VS Code

1. Instala la extensión oficial **Python** de Microsoft.
2. Abre esta carpeta en VS Code.
3. Pulsa `Ctrl+Shift+P`, busca **Python: Select Interpreter** y selecciona
   Python 3.
4. Abre `app.py` y pulsa el botón de ejecución, o presiona `F5`.
5. Si usas `F5`, selecciona **Ejecutar mapa de Marte**.

La configuración de `.vscode/launch.json` deja preparado el arranque y
mantiene el servidor en la terminal integrada. Después abre
<http://127.0.0.1:8000>.

## Contenido

- `app.py`: servidor HTTP y página interactiva.
- `data/missions.json`: metadatos con enlaces de fuentes NASA.
- `/api/missions`: endpoint JSON de los puntos documentados.

Las capas cartográficas y los recorridos deben consultarse en
[NASA Mars Trek](https://trek.nasa.gov/marsbeta/) o en los mapas oficiales de
cada misión antes de incorporarse como datos locales.

La demo incluye datos citados sobre atmósfera, temperatura, radiación RAD,
gravedad, polvo, hielo SHARAD, MOXIE, ECLSS y CHAPEA. Los valores de radiación
de RAD se muestran como dosis absorbida en `µGy/día`, tal como los publica NASA;
no se convierten automáticamente a `mSv`.
