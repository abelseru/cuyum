# Cuyum live - ajuste mínimo Leaflet

Hotfix mínimo sobre el mapa Leaflet que ya funcionaba mejor.

Cambios:
- Mantiene Leaflet y OpenStreetMap fijo, sin zoom ni navegación libre.
- Cambia colores de sensores y zonas para evitar verde/naranja.
- Sensores: celeste con borde blanco.
- Zonas: azul/violeta con numeración oscura y clara.
- Si una zona informa más sensores que los puntos ubicables recibidos, agrega puntos visuales alrededor del centro de la zona para que el mapa no contradiga la tarjeta de la zona.
- Si varios sensores caen superpuestos, los separa apenas solo para visualización.

No toca la lógica de alerta, scoring, ESP32 ni multicelda. Los puntos de respaldo son solo visuales.
