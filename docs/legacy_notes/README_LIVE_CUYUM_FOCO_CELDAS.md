# Cuyum live - foco visual por zona/célula

Hotfix mínimo sobre el mapa Leaflet que ya funcionaba.

Cambios:

- Mantiene Leaflet/OpenStreetMap.
- Mantiene zoom controlado, navegación limitada y botón Centrar cobertura.
- No cambia backend de alertas, ESP32 ni lógica multicelda.
- Colorea sensores según la zona/célula a la que pertenecen.
- Colorea también aro, número y tarjeta lateral de cada zona.
- Agrega leyenda dinámica de zonas.
- Al tocar/clickear una zona, número, chip de leyenda o tarjeta lateral:
  - se resaltan sus sensores;
  - se atenúan los sensores de las demás zonas;
  - se conserva el mapa sin recalcular ni pedir más JSON.
- Tocar otra vez la misma zona o el mapa limpia el foco.

Sigue usando un solo JSON por ciclo:

- normal: según /api/public/live, típicamente 5 s;
- alerta: según /api/public/live, típicamente 1.5 s.

Archivos modificados:

- templates/live_cuyum.html
- static/live_cuyum.js
- static/live_cuyum.css
