# Cuyum live - cell_00 trazable

Hotfix mínimo para que la célula local `cell_00` se muestre en el mapa como una célula Cuyum completa, no como puntos visuales ficticios.

Cambios:

- El frontend deja de crear sensores falsos `cell_00_visual_*`.
- El mapa muestra solamente sensores reales recibidos por `/api/public/live`.
- `public_live.py` completa los sensores locales con nombre, coordenadas públicas de visualización y scoring disponible.
- Los popups muestran nombre, código, zona, estado, calidad y tipo de ubicación.
- Si una coordenada viene de `sensor_geo_overrides.json`, queda marcada como ubicación pública aproximada.
- Se mantiene Leaflet, zoom controlado, navegación limitada y 1 JSON por ciclo.

No toca:

- ESP32
- lógica de alertas
- lectores SeedLink
- multicelda
- arranque
